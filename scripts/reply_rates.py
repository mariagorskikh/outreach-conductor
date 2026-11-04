#!/usr/bin/env python3
"""Which first-touch emails get replies and meetings: rates by opener, subject, length, bucket, angle, fit.

  reply_rates.py [--config PATH] [--sends sends.csv] [--since DATE] [--until DATE]
                 [--min-n 30] [--dims col1,col2] [--no-join] [--out report.md]

Input: a CSV with one row per first-touch email. Required columns: date, to, subject.
Optional: body, replied, meeting, bounced, and any other column you want to segment by (--dims).
Booleans accept true/false, yes/no, 1/0.

Every week's prospects.jsonl under the state folder is joined by email, so bucket, angle,
fit score, address rung and creative touch become segments automatically (skip with --no-join).

Output: a Markdown report (stdout, and --out), plus one headline line appended to
<state_dir>/history.jsonl. Read only on everything else. Standard library only.
"""
import argparse
import csv
import datetime as dt
import glob
import io
import json
import math
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oc_config import get, load_config, resolve, state_root  # noqa: E402

TRUE = {"true", "yes", "y", "1", "t"}
SIGNOFF = re.compile(r"\n\s*(best|thanks|thank you|cheers|regards|kind regards|warmly|all the best),?\s*\n", re.I)
OPENERS = [
    ("congrats", r"congrat"),
    ("saw-post-or-launch", r"\b(saw|read|loved|enjoyed) your (post|blog|launch|talk|article|podcast|thread|video)"),
    ("event", r"\b(we were both at|met at|great (meeting|to meet) you|nice (meeting|to meet) you|at .* last (night|week))"),
    ("saw-building", r"\bsaw (you|that you)('re| are| guys are| were) (building|working on|launching)"),
    ("mutual", r"\b(we're both connected|mutual|introduced|suggested i reach out|referred)"),
    ("credential-first", r"^(i'm|i am|my name is|i run|i lead|i'm the)\b"),
]
GENERIC_GREETING = re.compile(r"^(hi|hey|hello|dear|good (morning|afternoon))\b", re.I)


def wilson_low(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / n
    den = 1 + z * z / n
    return max(0.0, (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / den)


def truthy(v):
    return str(v or "").strip().lower() in TRUE


def body_only(text):
    return SIGNOFF.split(text or "", maxsplit=1)[0]


def opener(text, extra):
    lines = [l.strip() for l in body_only(text).splitlines() if l.strip()]
    if lines and GENERIC_GREETING.match(lines[0]) and len(lines[0]) < 40:
        lines = lines[1:]
    s = (lines[0] if lines else "").lower()
    if not s:
        return "no body"
    for name, pat in list(extra.items()) + OPENERS:
        if re.search(pat, s, re.I):
            return name
    if s.rstrip().endswith("?"):
        return "question"
    return "other"


def length_band(text):
    n = len(re.findall(r"\b\w+\b", body_only(text)))
    return "<60" if n < 60 else "60-89" if n < 90 else "90-119" if n < 120 else "120-159" if n < 160 else "160+"


def subject_feats(subj, company):
    s = (subj or "").strip()
    low = s.lower()
    out = {"subject length": "1-3 words" if len(s.split()) <= 3 else "4-7 words" if len(s.split()) <= 7 else "8+ words",
           "subject question": "question" if s.endswith("?") else "statement"}
    if company:
        out["subject names company"] = "names company" if company.lower() in low else "no company name"
    if re.match(r"^(re|fwd?):", low):
        out["subject fake reply"] = "fake re/fwd (stop this)"
    return out


def load_join(cfg):
    """email -> prospect row, from every week's prospects.jsonl."""
    out = {}
    for p in sorted(glob.glob(os.path.join(state_root(cfg), "*", "prospects.jsonl"))):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                if r.get("email"):
                    out[r["email"].strip().lower()] = r
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--sends", help="CSV export of first-touch sends (default: learning.sends_csv)")
    ap.add_argument("--since", default=(dt.date.today() - dt.timedelta(days=60)).isoformat())
    ap.add_argument("--until")
    ap.add_argument("--min-n", type=int)
    ap.add_argument("--dims", default="", help="extra CSV columns to segment by, comma separated")
    ap.add_argument("--no-join", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    cfg = load_config(a.config)
    min_n = a.min_n or int(get(cfg, "learning.min_n", 30))
    extra_openers = get(cfg, "learning.opener_patterns", {}) or {}
    path = a.sends or resolve(cfg, get(cfg, "learning.sends_csv", "data/sends.csv"))
    if not os.path.exists(path):
        sys.exit(f"no sends CSV at {path}; export your sent first-touch emails (see references/learning.md)")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    missing = {"date", "to", "subject"} - set(rows[0].keys() if rows else [])
    if missing:
        sys.exit(f"{path} is missing columns: {', '.join(sorted(missing))}")
    join = {} if a.no_join else load_join(cfg)
    dims_extra = [x.strip() for x in a.dims.split(",") if x.strip()]
    has_body = any((r.get("body") or "").strip() for r in rows)
    has_meeting = "meeting" in rows[0]

    sends = []
    for r in rows:
        d = (r.get("date") or "")[:10]
        if not d or d < a.since or (a.until and d > a.until):
            continue
        to = (r.get("to") or "").strip().lower()
        p = join.get(to, {})
        try:
            y, w, _ = dt.date.fromisoformat(d).isocalendar()
            wk = f"{y}-W{w:02d}"
        except ValueError:
            continue
        dims = {"send week": wk}
        if has_body:
            body = r.get("body") or ""
            dims["opener"] = opener(body, extra_openers)
            dims["length (words)"] = length_band(body)
            dims["bullets"] = "bullets" if re.search(r"(?m)^\s*[-*\u2022]\s+\S", body_only(body)) else "no bullets"
        dims.update(subject_feats(r.get("subject"), p.get("company") or r.get("company")))
        if join:
            dims["bucket"] = p.get("bucket") or "not from this skill"
            dims["angle"] = p.get("angle") or "not from this skill"
            dims["fit score"] = str(p.get("fit_score") or "unrated")
            dims["address rung"] = p.get("email_status") or "unknown"
            if any(x.get("creative_touch") for x in join.values()):
                dims["creative touch"] = "yes" if p.get("creative_touch") else "no"
        for col in dims_extra:
            dims[col] = (r.get(col) or "").strip() or "(blank)"
        sends.append({"replied": truthy(r.get("replied")), "met": truthy(r.get("meeting")),
                      "bounced": truthy(r.get("bounced")), "dims": dims})
    if not sends:
        sys.exit("no sends in range")

    n = len(sends)
    tr, tm, tb = (sum(s[k] for s in sends) for k in ("replied", "met", "bounced"))
    out = io.StringIO()
    out.write(f"# Reply rates, first touches {a.since} to {a.until or 'now'}\n\n")
    out.write(f"{n} sends, {tr} replied ({tr / n:.1%}), {tm} met ({tm / n:.1%}), {tb} bounced ({tb / n:.1%}).\n")
    if not has_meeting:
        out.write("No `meeting` column in the export, so meeting rates read 0.\n")
    out.write(f"Rates with n under {min_n} are hints. 'low' is the 95% Wilson lower bound of the reply rate.\n")
    out.write("Recent sends can still get replies; the latest week's numbers will rise.\n")
    if tb / n > float(get(cfg, "email.bounce_stop", 0.03)):
        out.write(f"\n**Bounce rate {tb / n:.1%} is above email.bounce_stop. Pause sending and draft verified addresses only.**\n")

    ranked = []
    all_dims = []
    for s in sends:
        for k in s["dims"]:
            if k not in all_dims:
                all_dims.append(k)
    for dim in all_dims:
        g = defaultdict(lambda: [0, 0, 0, 0])
        for s in sends:
            if dim not in s["dims"]:
                continue
            x = g[s["dims"][dim]]
            x[0] += 1
            x[1] += s["replied"]
            x[2] += s["met"]
            x[3] += s["bounced"]
        out.write(f"\n## {dim}\n\n| segment | n | replied | rate | low | met | met rate | bounced |\n"
                  "|---|---|---|---|---|---|---|---|\n")
        keyf = (lambda kv: kv[0]) if dim == "send week" else (lambda kv: -kv[1][0])
        for seg, (k, rep, met, bnc) in sorted(g.items(), key=keyf):
            low = wilson_low(rep, k)
            hint = " (hint)" if k < min_n else ""
            out.write(f"| {seg}{hint} | {k} | {rep} | {rep / k:.1%} | {low:.1%} | {met} | {met / k:.1%} | {bnc} |\n")
            if k >= min_n and dim != "send week" and len(g) > 1:
                ranked.append((low, rep / k, dim, seg, k))
    ranked.sort(reverse=True)
    out.write(f"\n## Strongest segments (n at least {min_n}, by lower bound)\n\n")
    for low, rate, dim, seg, k in ranked[:8]:
        out.write(f"- {dim} = {seg}: {rate:.1%} of {k} (low {low:.1%})\n")
    if not ranked:
        out.write("- none yet: no segment has enough sends\n")
    out.write("\n## Weakest segments\n\n")
    for low, rate, dim, seg, k in sorted(ranked, key=lambda x: x[1])[:6]:
        out.write(f"- {dim} = {seg}: {rate:.1%} of {k}\n")
    out.write("\nWrite 'Change next week' from these, per references/learning.md.\n")
    text = out.getvalue()

    root = state_root(cfg)
    os.makedirs(root, exist_ok=True)
    by_week = {}
    for s in sends:
        wk = by_week.setdefault(s["dims"]["send week"], [0, 0, 0])
        wk[0] += 1
        wk[1] += s["replied"]
        wk[2] += s["met"]
    hist = {"run_at": dt.datetime.now().isoformat(timespec="seconds"), "since": a.since, "until": a.until,
            "sends": n, "replied": tr, "met": tm, "bounced": tb, "by_week": by_week}
    with open(os.path.join(root, "history.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(hist) + "\n")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(text)
        print(f"wrote {a.out}", file=sys.stderr)
    print(text)


if __name__ == "__main__":
    main()
