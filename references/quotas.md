# Quotas: buckets, angles, the funnel

All numbers come from `config.yaml`. `week.py init` turns them into `plan.json` for the week.
If the user changes the mix, change the config, not the scripts.

## Buckets (who, and how you reach them)

A bucket is about the relationship and the channel: a warm connection, someone met at an
event, a region with its own rules, the core cold pool. Each has a `share` of the weekly
volume and an optional `requires` list of fields a row must carry before it can be `ready`.

Example from `config.example.yaml`, at 100 drafts a week:

| Bucket | Share | Drafts | Requires | Notes |
|---|---|---|---|---|
| `warm` | 10% | 10 | `warm_path` | a real connection with evidence; never backfilled with cold rows |
| `events` | 10% | 10 | `event.name`, `event.date` | the email names the event; attended within 60 days |
| `region-a` | 30% | 30 | | a region with its own wording rules (language, hosting, time zones) |
| `core` | 50% | 50 | | the main cold pool |

A row belongs to exactly one bucket. When a company fits two, the order in
`bucket_precedence` decides (warmest first). `week.py merge` enforces it.

## Angles (what you pitch)

An angle is a use case or segment. Shares steer **sourcing**: how many scouts look for each
kind of company. They never force a pitch. The angle follows what the company actually does.
Rows in a bucket with `angles: false` (for example, event follow-ups) carry an angle for the
pitch line but do not count against angle quotas.

## The funnel

At a multiplier of 2 and 100 drafts:

| Stage | Target | Why |
|---|---|---|
| Candidates found | about 200 | about half fail the legit bar or the dedupe |
| Verified (legit, right person, never contacted) | about 125 | some will have no usable address or fail review |
| Ready (address found, research done) | about 105 | margin for review holds |
| Drafted and created | 100 | |
| Address on a verified rung | at least 80% of drafts | the rest are clearly marked guesses, or held |
| LinkedIn top prospects | up to the weekly cap | |

## Shortfalls and backfill

- Search a bucket at least twice (two scout waves with different queries) before calling its
  pool dry.
- A dry bucket backfills into the bucket named in its `backfill_to`, keeping the angle mix.
- A bucket with `backfill: never` (warm) is left short. Never fill a warm bucket with cold
  emails.
- A dry angle backfills into the angles listed in `angle_backfill`, in order.
- Name every shortfall and backfill in the report with its reason, for example: "events: 6 of
  10, only 2 events attended since last week; 4 moved to core".

## Report template (`report.md` and the chat hand-off)

```
Week <YYYY-Www>: <N> sent, <N> drafts created (plan <P>)

Bucket      plan  drafted  verified-email  held  dropped
<bucket>     ...      ...             ...   ...      ...

Angle       plan  drafted
<angle>      ...      ...

Candidates researched: <N>; dropped <N> (top reasons: ...)
Email: <X>% on a verified rung (by rung: ...)
Credits: <tool> used <N>, balance <N>; purchases: none
Sent: <N> over <N> days (cap <N>/day); bounced <N>; opt-outs added <N>; stops hit: <none or which>
LinkedIn: <N> chosen, <N> already connected, <N> sent so far (by the user or the invite tool), cap <N>
Removed by the gates: <N> already contacted, <N> already met, <N> excluded, <N> competitors
Learned from last week: <three changes, with the numbers behind them>
Waiting for a yes (money only): <none, or the amount and what it buys>
Drafts file: <state_dir>/<week>/drafts-<week>.md
```
