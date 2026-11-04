# outreach-conductor

A Claude Code skill that runs a weekly outbound cycle like a careful researcher would, just
faster. It finds companies that match your ideal customer profile, verifies each company and
the right person, researches them, removes anyone you already contacted or met, writes
personalized email drafts in your own voice, picks a short list of people to connect with on
LinkedIn, logs everything to your CRM, and learns from last week's reply rates.

It produces **drafts**. You review and send. It never sends email or LinkedIn invites on its
own unless you approve a specific batch in chat.

## Why it exists

Most outbound automation optimizes for volume and gets ignored. This skill is built around
the opposite: a verification ladder, a per-person research bar, a dedupe gate across every
place you might have talked to someone, drafting rules copied from emails you actually sent,
a no-repeat check, and a review loop. Volume is a config setting (default 100 a week).
Quality is not.

## Requirements

- [Claude Code](https://claude.com/claude-code) with web search.
- Python 3.9 or newer (standard library only; PyYAML is used if installed).
- Optional: an email connector for creating drafts, a company database or enrichment tool,
  a search API, a CRM with a CLI or API. None are required. A CSV file works as the CRM.

## Install

```bash
git clone https://github.com/mariagorskikh/outreach-conductor ~/.claude/skills/outreach-conductor
```

## Configure

Either let the skill interview you on first run ("run weekly outreach" with no config starts
the interview), or do it by hand:

```bash
cd ~/.claude/skills/outreach-conductor
cp config.example.yaml config.yaml
mkdir -p data voice
cp examples/sent-examples.example.md voice/sent-examples.md   # then paste your real emails
```

Then edit `config.yaml`: your name and voice notes, your offer, your ICP and fit rubric,
buckets and angles with their shares, the weekly volume, your CRM, and the LinkedIn cap.
Keep API keys in environment variables, never in the config.

Check it parses:

```bash
python3 scripts/week.py init
```

Environment variables:

| Variable | What it does |
|---|---|
| `OUTREACH_CONDUCTOR_CONFIG` | path to a config file outside the skill folder |
| `OUTREACH_STATE_DIR` | where week folders live (default `state/` next to the config) |

## Example prompts

- "Run this week's outreach."
- "Set up outreach-conductor for my company." (starts the interview)
- "Find and draft 50 prospects in the events and warm buckets only."
- "Resume the outreach run." (picks up from the state folder)
- "Who should I connect with on LinkedIn this week?"
- "What got replies last month? Update next week's plan."

## How it works

1. **Kickoff.** Reads the config and your example emails, snapshots the CRM, reads last
   week's reply rates, and posts a short plan.
2. **Find.** Parallel scout agents search per bucket and angle (look-alikes of your best
   customers first, then fresh signals like funding and launches) and write candidates to
   files as they go.
3. **Verify.** Each company must be real, funded or staffed, with a working site that sells
   into your ICP. The right person must have a real profile. Every candidate is checked
   against your CRM, sent mail, drafts, message threads, calendar and opt-out lists.
4. **Enrich.** Finds addresses on a ladder from proven to guessed, and keeps at least 80% on
   a verified rung.
5. **Draft.** Writers research each person and write in your voice. A no-repeat check, a
   lint, and a fresh reviewer per slice of 50 catch copy-paste, false hooks and AI tells.
6. **Hand off.** Drafts go to your email client or a Markdown file, people go to your CRM
   tagged `draft-not-sent`, and a ranked LinkedIn list waits for your go.
7. **Learn.** After you send, `reply_rates.py` measures reply and meeting rates by opener,
   subject, length, bucket and angle, and the next week's briefs change accordingly.

Everything for a week lives in `state/<YYYY-Www>/`, so a run can stop and resume across
sessions without redoing work.

## What's in the box

```
SKILL.md                    the conductor: rules, phases, resume
config.example.yaml         every company-specific setting
references/
  setup.md                  first-run interview
  quotas.md                 buckets, angles, funnel, backfill, report template
  sources.md                where candidates come from (tool agnostic)
  verification.md           legit bar, research bar, dedupe and already-met gates
  enrichment.md             address ladder, verified share, bounces
  drafting.md               shapes, no-repeat check, lint, review loop
  linkedin.md               ranking, weekly cap, safety stops
  agents.md                 parallel subagents without losing work
  learning.md               reply-rate loop
  compliance.md             CAN-SPAM, GDPR basics, opt-outs, platform terms
scripts/
  week.py                   state folder: init, merge, gate, status, batch, uniq, ids,
                            export-drafts, top, carry, crm
  reply_rates.py            reply and meeting rates from a CSV export of sends
  oc_config.py              config loader (PyYAML optional)
examples/                   CRM, sends, opt-out and ledger CSVs, a sent-examples template
```

## Compliance

You are responsible for your outreach. Read `references/compliance.md`. In short: honest
subjects and sender, a physical address and opt-out in commercial email, honor every opt-out
permanently, keep bounces low, and never automate LinkedIn or any platform beyond what its
terms allow.

## License

MIT. See `LICENSE`.
