# Agents: running wide without losing work

A weekly run is many independent pieces of research. Subagents make it fast. They also make
it fragile. These rules are what keep a big run from dying halfway with nothing saved.

## Lessons that cost whole runs

- **Cap parallel agents** at `volume.max_parallel_agents` (default 8). Too many at once hits
  session limits and kills every agent mid-flight. Run waves: when one finishes, start the
  next.
- **Search APIs share one rate limit.** If every scout fans out its own batch of searches,
  they all hit the same rate limit and die before they write anything. Brief every agent:
  searches one at a time, a few seconds apart, back off on a rate-limit error, **no
  sub-agents of its own**.
- **Write as you go.** Every agent appends one JSON line per company to its own file in the
  week folder as soon as that company is done, and re-reads the file first so it skips what
  is already there. A killed agent then costs nothing.
- **Synthesize before you run out.** Agents tend to keep searching until their context or
  time is gone, then die with nothing written. Give each a stop condition (a row count or a
  time) and tell it to write and report when it hits it. If one runs long, message it: "STOP
  searching, cancel any background work, write what you have to <file>, reply with the
  count." Do the same for yourself: merge and save state before your own context gets tight.
- **One writer per file.** `prospects.jsonl` is written only by `week.py` in the main
  session. Agents write `scout-*.jsonl`, `verify-*.jsonl`, `enrich-*.jsonl`, `draft-*.jsonl`,
  `review-*.jsonl`, and `week.py merge` folds them in.
- **Shared quotas are counted centrally.** Search calls, paid lookups, browser profile reads.
  Give each agent its share in the brief.
- **One browser, one driver.** If a browser session with the user's logins is used, only one
  agent (or the main session) drives it at a time.
- **Agents report counts, not dumps.** Found, kept, dropped by reason, the file path.

## The waves

| Phase | Agents | Each does | Writes |
|---|---|---|---|
| 1 Find | one scout per bucket and angle slice, in waves | about 1.5x its slice quota in candidates, from `sources.md` | `scout-<slice>.jsonl` |
| 2 Verify | waves, about 8 companies each | `verification.md` sections 1 to 4 | `verify-<n>.jsonl` |
| 3 Enrich | the main session or one enrichment agent | `enrichment.md` | `enrich-<n>.jsonl` |
| 4 Draft | waves, about 10 rows each | per-person research and the draft | `draft-<n>.jsonl` |
| 4b Review | one fresh reviewer per 50 drafts | the review questions and the sample re-check | `review-<n>.jsonl` (verdict, fixes in `new_text`, `new_subject`) |

## Agent brief (fill per slice)

```
You are a <scout|verifier|writer|reviewer> for the weekly outreach run, week <W>, slice <S>.
Read first (absolute paths): <skill dir>/SKILL.md, <skill dir>/references/<file>.md,
<skill dir>/config.yaml<, and for writers the sender's example emails at <path>>.
Week folder: <absolute path>.
Input: <file or query list>.
Output: append one JSON line per company to <path> as soon as it is done. Re-read <path>
first and skip companies already there.
Rules: one person per company; legit or out; never guess a fact; no sub-agents; searches one
at a time, a few seconds apart, back off on rate limits; your search share is <N>.
Do not email, message, invite, RSVP or post anything. Sending is done only by the main
session, after the self-review gate.
Stop at <N> rows or <time>, then reply with counts (found, kept, dropped by reason) and the
file path.
```

## Resume

`STATE.md` in the week folder lists every wave with its agents, files and status. After a
crash: `week.py merge` every agent file, `week.py status`, and restart only the slices with
no file or a short file.
