#!/usr/bin/env python3
"""State for one week of outreach: one row per company in <state_dir>/<week>/prospects.jsonl.

  week.py init                          create the week folder with plan.json, STATE.md, prospects.jsonl
  week.py crm-pull                      snapshot the CRM to crm.csv for dedupe (csv path, or crm.export_command)
  week.py add FILES...                  merge scout/verify/enrich/draft/review JSONL files into prospects.jsonl
  week.py merge FILES...                same as add
  week.py gate [--apply]                check required fields; --apply advances verified -> ready, else hold
  week.py status                        counts per bucket, angle, status and address rung against plan.json
  week.py batch --out F [--status S]    draft rows as JSON (to, cc, subject, text, ...) for creating drafts
  week.py uniq [F]                      repeats across the week's drafts; exits 1 on any FAIL
  week.py ids F                         write draft ids (rows with key + draft_id) back; status -> created
  week.py export-drafts [--out F]       hand-off Markdown of drafted/created rows, grouped by bucket
  week.py top N [--out F]               rank LinkedIn top prospects -> linkedin-top<N>.csv
  week.py carry                         roll unsent LinkedIn top prospects into next week's queue
  week.py send-queue --out F [--reviewed] [--date D]
                                        today's send list: drafted/created rows, inside email.daily_send_cap,
                                        opt-outs removed, footer added; refuses while sending is paused
  week.py sent F                        record real sends (rows with key, sent_at, optional bounced); status -> sent;
                                        pauses sending when hard bounces pass email.bounce_stop
  week.py crm [--apply]                 log people to the CRM with tags; touches only for real sends

Global options go before the command: --config PATH, --week YYYY-Www (default: current ISO week).
Only this script writes prospects.jsonl. Agents write their own JSONL files and `add` folds them in.
Rows key on the registrable domain. Standard library only.

Sending: this script never sends anything. `send-queue` without --reviewed is a dry run. The agent passes
--reviewed only after the batch was approved (by the user in review mode, by the self-review gate in
autonomous mode). The actual send happens through the user's configured mail connector (email.send_via).
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import shlex
import subprocess
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oc_config import get, load_config, resolve, state_root  # noqa: E402

STATUS_ORDER = ["candidate", "verified", "ready", "drafted", "created", "sent"]
SIDE = {"hold", "dropped"}
VERIFIED_RUNGS = {"proven-thread", "proven-list", "verified-public", "tool-verified", "verified-other"}
RUNGS = VERIFIED_RUNGS | {"pattern-from-verified", "guess"}
PERSONAL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "me.com",
            "proton.me", "protonmail.com", "aol.com", "live.com"}
SECOND_LEVEL = {"co.uk", "org.uk", "ac.uk", "com.au", "co.il", "co.in", "com.br", "co.jp", "co.nz", "com.sg",
                "co.za", "com.mx", "com.tr", "com.cn", "com.hk", "co.kr"}
CONTACTED_STATUS = {"contacted", "replied", "meeting", "customer", "investor", "do-not-contact", "unsubscribed",
                    "bounced", "lost"}
DEFAULT_TITLES = (r"\bcto\b|chief technology|co-?founder|\bfounder\b|\bceo\b|chief executive|"
                  r"\bvp\b|vice president|head of")
CFG = {}


# ---------------------------------------------------------------- helpers

def week_id(s=None):
    if s:
        if not re.match(r"^\d{4}-W\d{2}$", s):
            sys.exit("--week must look like 2026-W07")
        return s
    y, w, _ = dt.date.today().isocalendar()
    return f"{y}-W{w:02d}"


def wdir(a):
    return os.path.join(state_root(CFG), week_id(a.week))


def need_dir(a):
    d = wdir(a)
    if not os.path.isdir(d):
        sys.exit(f"no week folder at {d}; run `week.py init` first")
    return d


def reg_domain(x):
    if not x:
        return ""
    x = str(x).strip().lower()
    if "@" in x:
        x = x.split("@", 1)[1]
    x = re.sub(r"^[a-z]+://", "", x).split("/")[0].split(":")[0]
    x = re.sub(r"^www\d?\.", "", x)
    parts = [p for p in x.split(".") if p]
    if len(parts) >= 3 and ".".join(parts[-2:]) in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else x


def norm_name(s):
    s = (s or "").lower()
    s = re.sub(r"\b(inc|llc|ltd|limited|gmbh|ag|sas|sarl|bv|oy|ab|corp|corporation|co)\b\.?", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def norm_url(u):
    u = (u or "").strip().lower().split("?")[0].split("#")[0].rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def row_key(r):
    if not (r.get("domain") or r.get("website") or r.get("email") or r.get("company")) and r.get("person_profile"):
        return "person:" + norm_url(r["person_profile"])
    dom = reg_domain(r.get("domain") or r.get("website") or "")
    if not dom and r.get("email") and reg_domain(r["email"]) not in PERSONAL:
        dom = reg_domain(r["email"])
    return dom or ("name:" + norm_name(r.get("company")) if r.get("company") else "")


def load_rows(d):
    p = os.path.join(d, "prospects.jsonl")
    rows = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                rows[r["key"]] = r
    return rows


def save_rows(d, rows):
    p = os.path.join(d, "prospects.jsonl")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        for r in rows.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(p + ".tmp", p)


def read_jsonl(p):
    txt = open(p, encoding="utf-8").read().strip()
    if txt.startswith("["):
        return json.loads(txt)
    out = []
    for i, line in enumerate(txt.splitlines()):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"  {os.path.basename(p)} line {i + 1}: bad JSON ({e}), skipped")
    return out


def rank(s):
    return STATUS_ORDER.index(s) if s in STATUS_ORDER else -1


def buckets():
    return get(CFG, "buckets", []) or []


def bucket_cfg(name):
    return next((b for b in buckets() if b.get("name") == name), {})


def precedence():
    p = get(CFG, "bucket_precedence") or [b.get("name") for b in buckets()]
    return [x for x in p if x]


def field(r, dotted):
    cur = r
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def plan_numbers():
    total = int(get(CFG, "volume.drafts_per_week", 100))
    mult = float(get(CFG, "volume.candidate_multiplier", 2))
    bs = buckets()
    if not bs:
        sys.exit("config has no buckets")
    share_sum = sum(float(b.get("share") or 0) for b in bs)
    if abs(share_sum - 1) > 0.01:
        print(f"WARNING: bucket shares add up to {share_sum:.2f}, not 1.0")
    b_n = {b["name"]: round(total * float(b.get("share") or 0)) for b in bs}
    angles = get(CFG, "angles", []) or []
    a_n = {}
    for b in bs:
        if b.get("angles") is False or not angles:
            continue
        a_n[b["name"]] = {a["name"]: round(b_n[b["name"]] * float(a.get("share") or 0)) for a in angles}
    return {"total": total, "candidates": round(total * mult), "buckets": b_n, "angles": a_n,
            "verified_min": float(get(CFG, "volume.verified_email_min", 0.8))}


# ---------------------------------------------------------------- commands

def cmd_init(a):
    d = wdir(a)
    os.makedirs(d, exist_ok=True)
    plan = plan_numbers()
    plan["week"] = week_id(a.week)
    plan["created"] = dt.datetime.now().isoformat(timespec="seconds")
    plan["config"] = CFG["_path"]
    json.dump(plan, open(os.path.join(d, "plan.json"), "w"), indent=1)
    st = os.path.join(d, "STATE.md")
    if not os.path.exists(st):
        open(st, "w").write(f"# Outreach {plan['week']}\n\nPhase: 0 kickoff\n\n## Waves\n\n## Notes\n")
    if not os.path.exists(os.path.join(d, "prospects.jsonl")):
        open(os.path.join(d, "prospects.jsonl"), "w").close()
    print(d)
    print(json.dumps(plan, indent=1))


def cmd_crm_pull(a):
    d = need_dir(a)
    typ = get(CFG, "crm.type", "csv")
    if typ == "command":
        cmd = get(CFG, "crm.export_command")
        if not cmd:
            sys.exit("crm.type is command but crm.export_command is empty")
        body = subprocess.run(shlex.split(cmd), check=True, capture_output=True, text=True).stdout
    else:
        p = resolve(CFG, get(CFG, "crm.path", "data/crm.csv"))
        if not os.path.exists(p):
            print(f"no CRM file at {p} yet; starting with an empty snapshot")
            body = "email,name,company,website,linkedin_url,title,status,last_contacted,tags,fit_score\n"
        else:
            body = open(p, encoding="utf-8").read()
    open(os.path.join(d, "crm.csv"), "w", encoding="utf-8").write(body)
    print(f"crm.csv: {sum(1 for _ in csv.DictReader(io.StringIO(body)))} contacts")


def exclusions():
    """domain set and email set from icp.competitors, icp.exclude_domains and icp.exclude_files."""
    doms = {reg_domain(x) for x in (get(CFG, "icp.competitors", []) or []) + (get(CFG, "icp.exclude_domains", []) or [])}
    emails = set()
    for f in get(CFG, "icp.exclude_files", []) or []:
        p = resolve(CFG, f)
        if not os.path.exists(p):
            continue
        for c in csv.DictReader(open(p, encoding="utf-8")):
            for k, v in c.items():
                if not v or not k:
                    continue
                k = k.strip().lower()
                if k in ("domain", "website"):
                    doms.add(reg_domain(v))
                elif k == "email":
                    emails.add(v.strip().lower())
                    if reg_domain(v) not in PERSONAL:
                        doms.add(reg_domain(v))
    doms.discard("")
    return doms, emails


def crm_index(d):
    """domain -> reason and normalized company -> reason, for companies already in play in the CRM snapshot."""
    p = os.path.join(d, "crm.csv")
    if not os.path.exists(p):
        return None, None
    by_dom, by_name = {}, {}
    for c in csv.DictReader(open(p, encoding="utf-8")):
        tags = (c.get("tags") or "").lower()
        status = (c.get("status") or "").strip().lower()
        reason = None
        if (c.get("last_contacted") or "").strip():
            reason = f"crm: contacted {c['last_contacted'][:10]}"
        elif status in CONTACTED_STATUS:
            reason = f"crm: {status}"
        elif "draft-not-sent" in tags:
            reason = "crm: drafted in another batch"
        if not reason:
            continue
        for x in (c.get("email"), c.get("website")):
            dom = reg_domain(x)
            if dom and dom not in PERSONAL:
                by_dom.setdefault(dom, reason)
        if c.get("company"):
            by_name.setdefault(norm_name(c["company"]), reason)
    return by_dom, by_name


def cmd_merge(a):
    d = need_dir(a)
    rows = load_rows(d)
    by_dom, by_name = crm_index(d)
    if by_dom is None:
        print("WARNING: no crm.csv yet; run `week.py crm-pull` before trusting this merge")
    ex_dom, ex_email = exclusions()
    competitors = {reg_domain(x) for x in get(CFG, "icp.competitors", []) or []}
    order = precedence()
    names = {norm_name(r.get("company")): k for k, r in rows.items() if r.get("company")}
    c = Counter()
    for p in a.files:
        for r in read_jsonl(p):
            k = row_key(r)
            if not k:
                c["no key"] += 1
                continue
            if k not in rows and r.get("company") and norm_name(r["company"]) in names:
                k = names[norm_name(r["company"])]          # same company under another domain
            if r.get("new_text") or r.get("new_subject"):     # a reviewer's fix replaces the draft text
                dr = dict(r.get("draft") or {})
                if r.get("new_text"):
                    dr["text"] = r.pop("new_text")
                if r.get("new_subject"):
                    dr["subject"] = r.pop("new_subject")
                r["draft"] = dr
            if k in rows:
                cur = rows[k]
                nb, cb = r.get("bucket"), cur.get("bucket")
                if nb in order and cb in order and order.index(nb) < order.index(cb):
                    cur["bucket"] = nb                        # warmest bucket wins
                for f, v in r.items():
                    if f in ("key", "status", "bucket"):
                        continue
                    if not r.get("status") and f in ("company", "domain", "angle") and cur.get(f):
                        continue                              # a second scout hit never re-files the company
                    if v not in (None, "", [], {}):
                        cur[f] = {**cur[f], **v} if isinstance(v, dict) and isinstance(cur.get(f), dict) else v
                ns = r.get("status")
                if ns and (ns in SIDE or rank(ns) > rank(cur.get("status"))):
                    cur["status"] = ns
                c["updated"] += 1
            else:
                r["key"] = k
                r.setdefault("domain", "" if ":" in k else k)
                r.setdefault("status", "candidate")
                r["added_at"] = dt.datetime.now().isoformat(timespec="seconds")
                rows[k] = r
                if r.get("company"):
                    names[norm_name(r["company"])] = k
                c["new"] += 1
            r2 = rows[k]
            dom = r2.get("domain") or ""
            why = None
            if dom and dom in competitors:
                why = "competitor"
            elif (dom and dom in ex_dom) or (r2.get("email") or "").lower() in ex_email:
                why = "excluded (do-not-contact or exclude list)"
            elif by_dom and (dom in by_dom or norm_name(r2.get("company")) in (by_name or {})):
                why = by_dom.get(dom) or by_name.get(norm_name(r2.get("company")))
            if why and r2.get("status") not in ("created", "sent"):
                if r2.get("status") != "dropped":
                    c["dropped: " + why.split(" 2")[0]] += 1
                r2["status"], r2["drop_reason"] = "dropped", why
    save_rows(d, rows)
    print(", ".join(f"{k} {v}" for k, v in c.items()) or "nothing to merge")
    print(f"prospects.jsonl: {len(rows)} rows")


def missing_for(r, target):
    m = []
    need = ["company", "domain", "website", "bucket", "what_they_sell", "fit_sentence", "fit_score",
            "fit_reason", "person_name", "first", "title", "role_source", "legit_evidence", "dedupe"]
    if get(CFG, "angles"):
        need.append("angle")
    for f in need:
        if r.get(f) in (None, "", [], {}):
            m.append(f)
    if not (r.get("linkedin_url") or r.get("profile_url")):
        m.append("linkedin_url or profile_url")
    if r.get("website_ok") is not True:
        m.append("website_ok")
    try:
        team = int(re.sub(r"[^0-9].*$", "", str(r.get("team_size") or "0").strip()) or 0)
    except ValueError:
        team = 0
    if not (r.get("total_raised") or r.get("last_round") or team >= 3):
        m.append("funding or team_size>=3")
    try:
        if int(r.get("fit_score") or 0) < int(get(CFG, "icp.min_fit_score", 3)):
            m.append("fit_score below icp.min_fit_score")
    except (TypeError, ValueError):
        m.append("fit_score")
    for req in bucket_cfg(r.get("bucket")).get("requires") or []:
        if field(r, req) in (None, "", [], {}):
            m.append(req)
    never = [x.lower() for x in get(CFG, "icp.never_roles", []) or []]
    if any(n and n in (r.get("title") or "").lower() for n in never):
        m.append("title is in icp.never_roles")
    if target in ("ready", "drafted"):
        if not r.get("email"):
            m.append("email")
        if r.get("email_status") not in RUNGS:
            m.append("email_status")
        if not r.get("hook_source"):
            m.append("hook_source (URL, or 'plain')")
    if target == "drafted":
        dr = r.get("draft") or {}
        for f in ("subject", "text"):
            if not dr.get(f):
                m.append("draft." + f)
    return m


def cmd_gate(a):
    d = need_dir(a)
    rows = load_rows(d)
    c, reasons = Counter(), Counter()
    for r in rows.values():
        s = r.get("status")
        if s == "hold" and not (r.get("hold_reason") or "").startswith("missing:"):
            c["hold (review or manual, left alone)"] += 1
            continue
        if s in ("candidate", "verified", "ready", "hold"):
            target = "ready" if s in ("verified", "hold", "ready") and r.get("email") else "verified"
            miss = missing_for(r, target)
            if not miss:
                if a.apply and rank(target) > rank(s):
                    r["status"] = target
                    r.pop("hold_reason", None)
                c["pass " + target] += 1
            else:
                reasons.update(miss)
                if a.apply and s in ("verified", "ready"):
                    r["status"], r["hold_reason"] = "hold", "missing: " + ", ".join(miss)
                c["fail " + target] += 1
        elif s == "drafted":
            miss = missing_for(r, "drafted")
            c["drafted ok" if not miss else "drafted incomplete"] += 1
            reasons.update(miss)
    if a.apply:
        save_rows(d, rows)
    print(", ".join(f"{k} {v}" for k, v in sorted(c.items())) or "no rows to gate")
    if reasons:
        print("most often missing:", ", ".join(f"{k} {v}" for k, v in reasons.most_common(12)))


def cmd_status(a):
    d = need_dir(a)
    rows = load_rows(d)
    plan = json.load(open(os.path.join(d, "plan.json")))
    by, ang = defaultdict(Counter), defaultdict(Counter)
    rung, drops = Counter(), Counter()
    for r in rows.values():
        b, s = r.get("bucket") or "?", r.get("status") or "?"
        by[b][s] += 1
        if s in ("drafted", "created", "sent"):
            by[b]["_out"] += 1
            if b in plan["angles"]:
                ang[b][r.get("angle") or "?"] += 1
            rung[r.get("email_status") or "none"] += 1
        if s == "dropped":
            drops[(r.get("drop_reason") or "?").split(" 2")[0][:40]] += 1
    cols = ["candidate", "verified", "ready", "drafted", "created", "sent", "hold", "dropped"]
    print(f"Week {plan['week']}: {sum(by[b]['_out'] for b in by)} drafted, created or sent (plan {plan['total']}, "
          f"{len(rows)} rows, candidate target {plan['candidates']})\n")
    print(f"{'bucket':<12}{'plan':>6}{'out':>6}  " + "".join(f"{x[:9]:>10}" for x in cols))
    for b in list(plan["buckets"]) + [x for x in by if x not in plan["buckets"]]:
        print(f"{b:<12}{plan['buckets'].get(b, 0):>6}{by[b]['_out']:>6}  " + "".join(f"{by[b][x]:>10}" for x in cols))
    if plan["angles"]:
        print("\nangles (out / plan):")
        for b, ap in plan["angles"].items():
            print(f"  {b:<12}" + "  ".join(f"{k} {ang[b][k]}/{v}" for k, v in ap.items()))
    out = sum(rung.values())
    ver = sum(v for k, v in rung.items() if k in VERIFIED_RUNGS)
    if out:
        flag = "OK" if ver / out >= plan["verified_min"] else f"BELOW {int(plan['verified_min'] * 100)}%"
        print(f"\nemail verified: {ver}/{out} = {ver / out:.0%} ({flag}); "
              + ", ".join(f"{k} {v}" for k, v in rung.most_common()))
    if drops:
        print("\ndropped by reason: " + ", ".join(f"{k} {v}" for k, v in drops.most_common(10)))


def to_batch_row(r):
    dr = r.get("draft") or {}
    return {
        "key": r["key"], "to": r.get("email"), "cc": r.get("cc") or "", "subject": dr.get("subject"),
        "text": dr.get("text"), "first": r.get("first"), "person_name": r.get("person_name"),
        "company": r.get("company"), "bucket": r.get("bucket"), "angle": r.get("angle"),
        "email_status": r.get("email_status"), "hook_source": r.get("hook_source"), "tie_source": r.get("tie_source"),
        "ties": r.get("ties"), "linkedin_degree": r.get("linkedin_degree"), "mutuals": r.get("mutuals"),
        "creative_touch": bool(r.get("creative_touch")), "review": r.get("review"), "draft_id": r.get("draft_id"),
    }


def cmd_batch(a):
    d = need_dir(a)
    want = set(a.status.split(","))
    out = [to_batch_row(r) for r in load_rows(d).values() if r.get("status") in want]
    bad = [b["key"] for b in out if not (b["to"] and b["subject"] and b["text"])]
    if bad:
        sys.exit(f"{len(bad)} rows lack to/subject/text (fix or hold them): {', '.join(bad[:10])}")
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{a.out}: {len(out)} rows")


def template_re():
    lines = [re.escape(x.strip().lower()) for x in get(CFG, "drafting.template_lines", []) or [] if str(x).strip()]
    return re.compile("^(" + "|".join(lines) + ")", re.I) if lines else None


def sentences(text, tmpl):
    out = []
    for line in (text or "").splitlines():
        if re.match(r"\s*[-*\u2022]\s+", line):
            continue                                      # bullets are judged as a set
        line = line.strip()
        if not line or (tmpl and tmpl.match(line)):
            continue
        for s in re.split(r"(?<=[.!?])\s+", line):
            s = re.sub(r"\s+", " ", s.strip().lower())
            if len(s) > 25 and not (tmpl and tmpl.match(s)):
                out.append(s)
    return out


def bullet_set(text):
    return tuple(sorted(re.sub(r"\s+", " ", l.strip().lstrip("-*\u2022 ").lower()) for l in (text or "").splitlines()
                        if re.match(r"\s*[-*\u2022]\s+", l)))


def cmd_uniq(a):
    d = need_dir(a)
    if a.file:
        items = json.load(open(a.file, encoding="utf-8"))
    else:
        items = [to_batch_row(r) for r in load_rows(d).values() if r.get("status") in ("drafted", "created")]
    tmpl = template_re()
    fails, warns = [], []
    seen_to, seen_dom, seen_subj = {}, {}, {}
    sent_count, bul = Counter(), defaultdict(Counter)
    for it in items:
        who = it.get("company") or it.get("to")
        to = (it.get("to") or "").lower()
        dom = it.get("key") or reg_domain(to)
        if to and to in seen_to:
            fails.append(f"same recipient twice: {to} ({seen_to[to]}, {who})")
        seen_to[to] = who
        if dom in seen_dom:
            fails.append(f"same company twice: {dom} ({seen_dom[dom]}, {who})")
        seen_dom[dom] = who
        subj = re.sub(r"\s+", " ", (it.get("subject") or "").strip().lower())
        if subj in seen_subj:
            fails.append(f"identical subject: '{it.get('subject')}' ({seen_subj[subj]}, {who})")
        seen_subj[subj] = who
        sent_count.update(set(sentences(it.get("text"), tmpl)))
        b = bullet_set(it.get("text"))
        if b:
            bul[it.get("angle") or "?"][b] += 1
        if re.search("[\u2013\u2014]|&[mn]dash;|&#821[12];", (it.get("text") or "") + (it.get("subject") or "")):
            fails.append(f"em or en dash in draft to {who}")
    max_sent, max_bul = max(3, len(items) // 100), max(5, len(items) // 100)
    for s, n in sent_count.most_common():
        if n <= max_sent:
            break
        fails.append(f"sentence in {n} drafts: \"{s[:110]}\"")
    for ang, cnt in bul.items():
        for b, n in cnt.items():
            if n > max_bul:
                fails.append(f"same bullets in {n} {ang} drafts: {' | '.join(x[:40] for x in b)}")
            elif n > 2:
                warns.append(f"same bullets in {n} {ang} drafts: {' | '.join(x[:40] for x in b)}")
    print(f"{len(items)} drafts checked: {len(fails)} FAIL, {len(warns)} WARN")
    for f in fails:
        print("FAIL", f)
    for w in warns:
        print("WARN", w)
    sys.exit(1 if fails else 0)


def cmd_ids(a):
    d = need_dir(a)
    rows = load_rows(d)
    n = 0
    for b in json.load(open(a.file, encoding="utf-8")):
        k = b.get("key")
        if b.get("draft_id") and k in rows:
            rows[k]["draft_id"] = b["draft_id"]
            rows[k]["status"] = "created"
            n += 1
    save_rows(d, rows)
    print(f"{n} rows marked created")


def cmd_export(a):
    d = need_dir(a)
    wk = week_id(a.week)
    rows = [r for r in load_rows(d).values() if r.get("status") in ("drafted", "created")]
    label = bool(get(CFG, "email.label_guesses", True))
    out = [f"# Drafts {wk}\n", f"{len(rows)} drafts. Each passed the self-review gate; check any you want before sending.\n"]
    for b in precedence() + sorted({r.get("bucket") or "?" for r in rows} - set(precedence())):
        group = [r for r in rows if (r.get("bucket") or "?") == b]
        if not group:
            continue
        out.append(f"\n## {b} ({len(group)})\n")
        for r in sorted(group, key=lambda r: -int(r.get("fit_score") or 0)):
            dr = r.get("draft") or {}
            guess = label and r.get("email_status") not in VERIFIED_RUNGS
            out.append(f"\n### {r.get('person_name')}, {r.get('title')}, {r.get('company')}\n")
            out.append(f"- To: {r.get('email')}" + (f" (unverified: {r.get('email_status')})" if guess else ""))
            if r.get("cc"):
                out.append(f"- Cc: {r['cc']}")
            out.append(f"- Subject: {dr.get('subject')}")
            meta = [f"fit {r.get('fit_score')}", f"angle {r.get('angle') or '-'}"]
            if r.get("linkedin_degree"):
                meta.append(f"LinkedIn degree {r['linkedin_degree']}")
            if r.get("mutuals"):
                meta.append("mutuals: " + ", ".join(r["mutuals"] if isinstance(r["mutuals"], list) else [r["mutuals"]]))
            if r.get("ties"):
                meta.append(f"tie: {r['ties']}")
            if r.get("draft_id"):
                meta.append(f"draft id {r['draft_id']}")
            if r.get("review"):
                meta.append(f"review: {r['review']}")
            out.append("- " + "; ".join(str(x) for x in meta))
            out.append("\n```\n" + (dr.get("text") or "").strip() + "\n```")
    path = a.out or os.path.join(d, f"drafts-{wk}.md")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"{path}: {len(rows)} drafts")


def ledger_urls(results=None):
    p = resolve(CFG, get(CFG, "linkedin.ledger_path", "data/linkedin-ledger.csv"))
    urls = set()
    if os.path.exists(p):
        for c in csv.DictReader(open(p, encoding="utf-8")):
            if results is None or (c.get("result") or "") in results:
                urls.add(norm_url(c.get("linkedin_url")))
    return urls


def li_score(r, order):
    s = 0.0
    if r.get("ties") or r.get("mutuals"):
        s += 3
    try:
        s += {5: 3, 4: 2, 3: 0.5}.get(int(r.get("fit_score") or 0), 0)
    except (TypeError, ValueError):
        pass
    b = r.get("bucket")
    if b in order and len(order) > 1:
        s += 2 * (1 - order.index(b) / (len(order) - 1))
    if r.get("email_status") in VERIFIED_RUNGS:
        s += 0.5
    if r.get("status") == "queued":
        s += 1
    return s


def cmd_top(a):
    d = need_dir(a)
    rows = load_rows(d)
    asked = ledger_urls()
    title_ok = re.compile(get(CFG, "linkedin.title_pattern") or DEFAULT_TITLES, re.I)
    q = os.path.join(d, "linkedin-queue.csv")
    have = {norm_url(r.get("linkedin_url")) for r in rows.values()}
    if os.path.exists(q):
        for c in csv.DictReader(open(q, encoding="utf-8")):
            u = norm_url(c.get("linkedin_url"))
            if u and u not in have:
                rows["queued:" + u] = {
                    "person_name": c.get("name"), "title": c.get("title"), "company": c.get("company"),
                    "fit_score": c.get("fit"), "bucket": c.get("bucket"), "linkedin_degree": c.get("degree"),
                    "mutuals": [m for m in (c.get("mutuals") or "").split("; ") if m], "ties": c.get("ties"),
                    "fit_sentence": c.get("why"), "linkedin_url": c.get("linkedin_url"), "status": "queued"}
    order = precedence()
    pool = []
    for r in rows.values():
        url = norm_url(r.get("linkedin_url"))
        if r.get("status") not in ("ready", "drafted", "created", "queued") or not url:
            continue
        if r.get("customer") or r.get("investor") or str(r.get("linkedin_degree")) in ("1", "pending"):
            continue
        if url in asked or not title_ok.search(r.get("title") or ""):
            continue
        pool.append(r)
    pool.sort(key=lambda r: li_score(r, order), reverse=True)
    top = pool[: a.n]
    out = a.out or os.path.join(d, f"linkedin-top{a.n}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "name", "title", "company", "fit", "bucket", "degree", "mutuals", "ties", "why",
                    "emailed_this_week", "linkedin_url"])
        for i, r in enumerate(top, 1):
            mut = r.get("mutuals") or []
            w.writerow([i, r.get("person_name"), r.get("title"), r.get("company"), r.get("fit_score"), r.get("bucket"),
                        r.get("linkedin_degree"), "; ".join(mut if isinstance(mut, list) else [mut]), r.get("ties") or "",
                        (r.get("fit_sentence") or "")[:120], "yes" if r.get("status") == "created" else "",
                        r.get("linkedin_url")])
    cap = get(CFG, "linkedin.weekly_invite_cap", 50)
    print(f"{out}: {len(top)} of {len(pool)} eligible (weekly invite cap {cap}; sent by hand or linkedin.invite_tool)")


def cmd_carry(a):
    d = need_dir(a)
    src = sorted(f for f in os.listdir(d) if f.startswith("linkedin-top") and f.endswith(".csv"))
    if not src:
        sys.exit("no linkedin-top*.csv in this week")
    done = ledger_urls({"sent", "already_connected", "already_pending", "no_profile"})
    rows = [c for c in csv.DictReader(open(os.path.join(d, src[-1]), encoding="utf-8"))
            if norm_url(c.get("linkedin_url")) not in done]
    y, w = map(int, week_id(a.week).split("-W"))
    ny, nw, _ = (dt.date.fromisocalendar(y, w, 1) + dt.timedelta(days=7)).isocalendar()
    nd = os.path.join(state_root(CFG), f"{ny}-W{nw:02d}")
    os.makedirs(nd, exist_ok=True)
    with open(os.path.join(nd, "linkedin-queue.csv"), "w", newline="", encoding="utf-8") as f:
        if rows:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)
    print(f"{len(rows)} unsent top prospects queued for {ny}-W{nw:02d}")


def pause_file():
    return os.path.join(state_root(CFG), "SENDING_PAUSED")


def all_sent_rows():
    root = state_root(CFG)
    out = []
    if not os.path.isdir(root):
        return out
    for wk in sorted(os.listdir(root)):
        d = os.path.join(root, wk)
        if os.path.isdir(d) and re.match(r"^\d{4}-W\d{2}$", wk):
            out += [r for r in load_rows(d).values() if r.get("status") == "sent"]
    return out


def bounce_check():
    """Write SENDING_PAUSED when hard bounces pass email.bounce_stop (after at least 20 sends)."""
    sent = all_sent_rows()
    n, b = len(sent), sum(1 for r in sent if r.get("bounced"))
    stop = float(get(CFG, "email.bounce_stop", 0.03))
    if n >= 20 and b / n > stop and not os.path.exists(pause_file()):
        open(pause_file(), "w").write(
            f"paused {dt.datetime.now().isoformat(timespec='seconds')}: {b} of {n} sends bounced "
            f"({b / n:.1%}), above email.bounce_stop {stop:.0%}. Fix addresses, then delete this file to resume.\n")
        print(f"SENDING PAUSED: {b} of {n} bounced ({b / n:.1%} > {stop:.0%}); see {pause_file()}")
    return n, b


def footer_for(r):
    foot = (get(CFG, "compliance.footer") or "").strip()
    if not foot:
        return ""
    regions = get(CFG, "compliance.footer_regions", "all")
    if regions in (None, "", "all") or (r.get("country") or "").upper() in {str(x).upper() for x in regions}:
        return foot
    return ""


def cmd_send_queue(a):
    d = need_dir(a)
    if os.path.exists(pause_file()):
        sys.exit("sending is paused: " + open(pause_file(), encoding="utf-8").read().strip())
    bounce_check()
    if os.path.exists(pause_file()):
        sys.exit("sending is paused by the bounce stop; no queue written")
    day = a.date or dt.date.today().isoformat()
    cap = int(get(CFG, "email.daily_send_cap", 50))
    already = sum(1 for r in all_sent_rows() if (r.get("sent_at") or "")[:10] == day)
    room = max(0, cap - already)
    ex_dom, ex_email = exclusions()
    send_guesses = bool(get(CFG, "email.send_guesses", False))
    skipped = Counter()
    pool = []
    rows = load_rows(d)
    for r in sorted(rows.values(), key=lambda r: -int(r.get("fit_score") or 0)):
        if r.get("status") not in ("drafted", "created"):
            continue
        email = (r.get("email") or "").strip().lower()
        if not email:
            skipped["no address"] += 1
        elif email in ex_email or reg_domain(email) in ex_dom:
            skipped["opt-out or excluded"] += 1
        elif str(r.get("review") or "").lower().startswith(("hold", "fail")):
            skipped["review held it"] += 1
        elif r.get("email_status") not in VERIFIED_RUNGS and not send_guesses:
            skipped["unverified address (email.send_guesses is false)"] += 1
        else:
            pool.append(r)
    queue = pool[:room]
    if len(pool) > room:
        skipped[f"over today's cap ({cap}, {already} sent already)"] += len(pool) - room
    out = []
    for r in queue:
        b = to_batch_row(r)
        foot = footer_for(r)
        if foot and foot not in (b["text"] or ""):
            b["text"] = (b["text"] or "").rstrip() + "\n\n" + foot
        out.append(b)
    print(f"{len(out)} to send on {day} (cap {cap}, {already} already sent today, {len(pool)} eligible)")
    for k, v in skipped.items():
        print(f"  skipped {v}: {k}")
    if not a.reviewed:
        print("dry run; pass --reviewed once the batch is approved (by the user in review mode, "
              "by the self-review gate in autonomous mode)")
        return
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{a.out}: {len(out)} rows; spread them through email.business_hours, then record with `week.py sent`")


def cmd_sent(a):
    d = need_dir(a)
    rows = load_rows(d)
    n = 0
    for b in read_jsonl(a.file):
        k = b.get("key")
        if k not in rows or not b.get("sent_at"):
            continue
        r = rows[k]
        r["status"] = "sent"
        r["sent_at"] = b["sent_at"]
        for f in ("message_id", "bounced"):
            if b.get(f) not in (None, ""):
                r[f] = b[f]
        n += 1
    save_rows(d, rows)
    print(f"{n} rows marked sent")
    total, bounced = bounce_check()
    print(f"all weeks: {total} sent, {bounced} bounced")


CRM_COLS = ["email", "name", "company", "website", "linkedin_url", "title", "location", "status", "last_contacted",
            "tags", "fit_score", "fit_reason", "notes", "source"]


def crm_contacts(rows, wk):
    out = []
    for r in rows.values():
        if r.get("status") in ("dropped", "candidate", "queued") or not (r.get("email") or r.get("linkedin_url")):
            continue
        tags = ["outreach-conductor", f"wk-{wk}", f"bucket-{r.get('bucket')}"]
        if r.get("angle"):
            tags.append(f"angle-{r['angle']}")
        if r.get("status") == "created":
            tags.append("draft-not-sent")             # a draft is never a touch
        if r.get("status") == "sent":
            tags.append("sent")                       # a real send is a touch
            if r.get("bounced"):
                tags.append("bounced")
        if r.get("email_status"):
            tags.append("email-" + r["email_status"])
        if r.get("creative_touch"):
            tags.append("creative-touch")
        out.append({"email": r.get("email") or "", "name": r.get("person_name") or "", "company": r.get("company") or "",
                    "website": r.get("website") or "", "linkedin_url": r.get("linkedin_url") or "",
                    "title": r.get("title") or "", "location": r.get("country") or "", "fit_score": r.get("fit_score") or "",
                    "fit_reason": r.get("fit_reason") or "", "notes": r.get("fit_sentence") or "",
                    "last_contacted": (r.get("sent_at") or "")[:10] if r.get("status") == "sent" else "",
                    "source": "outreach-conductor", "add_tags": tags})
    return out


def cmd_crm(a):
    d = need_dir(a)
    wk = week_id(a.week)
    contacts = crm_contacts(load_rows(d), wk)
    path = os.path.join(d, "crm-import.json")
    json.dump({"contacts": contacts}, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    nsent = sum(1 for c in contacts if "sent" in c["add_tags"])
    print(f"{path}: {len(contacts)} contacts ({nsent} real sends logged as touches; drafts are never touches)")
    if not a.apply:
        print("dry run; pass --apply to write")
        return
    if get(CFG, "crm.type", "csv") == "command":
        cmd = get(CFG, "crm.import_command")
        if not cmd:
            sys.exit("crm.type is command but crm.import_command is empty")
        subprocess.run(shlex.split(cmd) + [path], check=True)
        return
    p = resolve(CFG, get(CFG, "crm.path", "data/crm.csv"))
    existing, order = {}, []
    cols = list(CRM_COLS)
    if os.path.exists(p):
        rd = csv.DictReader(open(p, encoding="utf-8"))
        cols += [c for c in (rd.fieldnames or []) if c not in cols]
        for c in rd:
            k = (c.get("email") or "").lower() or norm_url(c.get("linkedin_url"))
            existing[k] = c
            order.append(k)
    added = updated = 0
    for c in contacts:
        k = c["email"].lower() or norm_url(c["linkedin_url"])
        tags = c.pop("add_tags")
        cur = existing.get(k)
        if cur is None:
            cur = {col: "" for col in cols}
            existing[k] = cur
            order.append(k)
            added += 1
        else:
            updated += 1
        for f, v in c.items():
            if v not in ("", None) and not (cur.get(f) or "").strip():
                cur[f] = str(v)                       # never overwrite what is there
        if c.get("last_contacted") and c["last_contacted"] > (cur.get("last_contacted") or ""):
            cur["last_contacted"] = c["last_contacted"]   # a newer real send moves the touch date
        old = [t for t in (cur.get("tags") or "").split(";") if t.strip()]
        if "sent" in tags:
            old = [t for t in old if t != "draft-not-sent"]
        cur["tags"] = ";".join(old + [t for t in tags if t not in old])
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p + ".tmp", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        wr.writeheader()
        for k in order:
            wr.writerow(existing[k])
    os.replace(p + ".tmp", p)
    print(f"{p}: {added} added, {updated} updated (empty fields and tags only)")


def main():
    global CFG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--week")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("init")
    sp.add_parser("crm-pull")
    for name in ("add", "merge"):
        sp.add_parser(name).add_argument("files", nargs="+")
    sp.add_parser("gate").add_argument("--apply", action="store_true")
    sp.add_parser("status")
    p = sp.add_parser("batch")
    p.add_argument("--out", required=True)
    p.add_argument("--status", default="drafted")
    sp.add_parser("uniq").add_argument("file", nargs="?")
    sp.add_parser("ids").add_argument("file")
    sp.add_parser("export-drafts").add_argument("--out")
    p = sp.add_parser("top")
    p.add_argument("n", type=int)
    p.add_argument("--out")
    sp.add_parser("carry")
    p = sp.add_parser("send-queue")
    p.add_argument("--out", required=True)
    p.add_argument("--reviewed", action="store_true",
                   help="the batch passed approval: the user's in review mode, the self-review gate in autonomous mode")
    p.add_argument("--date", help="YYYY-MM-DD the cap counts against (default today)")
    sp.add_parser("sent").add_argument("file")
    sp.add_parser("crm").add_argument("--apply", action="store_true")
    a = ap.parse_args()
    CFG = load_config(a.config)
    {"init": cmd_init, "crm-pull": cmd_crm_pull, "add": cmd_merge, "merge": cmd_merge, "gate": cmd_gate,
     "status": cmd_status, "batch": cmd_batch, "uniq": cmd_uniq, "ids": cmd_ids, "export-drafts": cmd_export,
     "top": cmd_top, "carry": cmd_carry, "send-queue": cmd_send_queue, "sent": cmd_sent,
     "crm": cmd_crm}[a.cmd](a)


if __name__ == "__main__":
    main()
