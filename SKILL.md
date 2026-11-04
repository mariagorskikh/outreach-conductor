---
name: outreach-conductor
description: Runs a weekly outbound cycle end to end. Finds candidate companies that match your ICP, verifies the company, the website and the right person, researches each person, dedupes against your CRM, sent mail and drafts, writes personalized email drafts in your own voice, queues a short list of LinkedIn connection requests, runs quality gates, logs everything to your CRM, and learns from last week's reply rates. Uses parallel subagents and a resumable state folder per week. Drafts only; it never sends unless you approve a specific batch. Use when the user says "weekly outreach", "run the outreach cycle", "this week's prospects", "find, verify and draft", "build this week's outbound", "prospect and draft emails", "outbound conductor", or asks for a full week of researched prospects, drafts and LinkedIn connects.
---

# Outreach conductor

One weekly cycle, one state folder, one set of quality gates. The goal is a batch of drafts
where every single one reads like the sender wrote it after ten minutes of research. Volume is
a setting. Quality is not.

## Before anything else

1. Find the config. Look for `config.yaml` next to this file, or the path in
   `OUTREACH_CONDUCTOR_CONFIG`. If it does not exist, run the first-run interview in
   `references/setup.md`, write `config.yaml` from `config.example.yaml`, and show the user
   the result before doing any outreach work.
2. Read the config fully. Everything company specific lives there: the ICP, the buckets and
   their shares, the angles, the sender's voice notes and example emails, the CRM type, data
   sources, the LinkedIn cap and the weekly draft volume.
3. Read the sender's example sent emails (`sender.sent_examples_path`). Drafts copy what the
   sender actually sends, not what a style guide says.
4. Read last week's `report.md` in the state folder, if there is one, and carry its
   "Change next week" lines into this week's briefs.

## Reference files

| File | What it holds |
|---|---|
| `references/setup.md` | the first-run interview and how to fill `config.yaml` |
| `references/quotas.md` | buckets, angles, the funnel, backfill rules, the report template |
| `references/sources.md` | where candidates come from, by bucket, tool agnostic |
| `references/verification.md` | the legit bar, the right person, the research bar, the dedupe gate |
| `references/enrichment.md` | the email address ladder, the verified share rule, bounces |
| `references/drafting.md` | drafting gates, the no-repeat check, lint and the review loop |
| `references/linkedin.md` | choosing the top prospects, the weekly cap, safety stops |
| `references/agents.md` | fan-out: waves, briefs, write-as-you-go, resume, rate limits |
| `references/learning.md` | the reply-rate loop and how it changes next week |
| `references/compliance.md` | CAN-SPAM, GDPR basics, opt-outs, platform terms |
| `scripts/week.py` | the state folder: init, merge, gate, status, batch, uniq, top, carry, crm |
| `scripts/reply_rates.py` | reply and meeting rates by segment, from a CSV export of sends |

Run scripts with `python3 scripts/<name>.py --help`. They use the standard library only
(PyYAML is used if installed, otherwise a built-in YAML subset reader).

## Hard rules (never bend, at any volume)

1. **Drafts only.** This skill never sends an email, a LinkedIn invite or a DM by itself. It
   may send only a specific batch the user has approved in chat, by count and by list, in this
   session. One approval covers one batch, not the next one.
2. **One person per company, and a company already contacted is out.** Any earlier email,
   DM, invite thread, meeting, reply or draft to anyone there removes the whole company.
3. **Legit or out.** Funded, or at least three real people on the team. A working website that
   clearly sells into your ICP. A real person with a findable profile. No exceptions to hit a
   number.
4. **The right person.** Use `icp.target_roles` in order. Never anyone in `icp.never_roles`
   (by default: interns, advisors, former founders, people who left).
5. **The sender's voice wins on every word.** Drafts follow `sender.voice_notes` and the
   example emails. Short. No AI tells. No em dashes or en dashes. Real links only.
6. **No repeats.** No two drafts to one company. No draft to anyone with an earlier draft. No
   two drafts that read alike. `week.py uniq` must pass before drafts are created.
7. **Quality over count.** If the configured number of good prospects does not exist this
   week, hand over fewer and say where the pool ran dry. Padding is the failure this skill
   exists to prevent.
8. **A draft is not a touch.** Drafts are tagged `draft-not-sent` in the CRM. Touches are
   logged only from real sends.
9. **Never guess facts.** Only name a system, customer, round or milestone you can point at
   with a URL. A guessed fact costs more than a plain opener.
10. **Compliance.** Follow `references/compliance.md`. Honor every opt-out. Stay inside each
    platform's limits and terms.

## Spending

Paid enrichment or data credits are spent only inside `spending.weekly_budget` in the config.
Show credits used and balance left in the kickoff and the hand-off. Anything above the budget,
any purchase, and any new payment method needs the user's yes in chat. Never type card
numbers or passwords.

## The weekly cycle

A full run can span several sessions and days. Always pass `--week` to `week.py` with the week
the run started in, so a run that crosses Monday keeps one folder. Keep `STATE.md` in the week
folder current (what is done, what is running, counts) so a new session can resume.

**Phase 0. Kickoff.**
1. `week.py init` creates `<state_dir>/<YYYY-Www>/` with `plan.json` built from the config.
2. `week.py crm-pull` saves a fresh CRM snapshot for dedupe.
3. If there is a sends export, run `reply_rates.py` (`references/learning.md`) and read last
   week's report.
4. Pool health: how many unsent drafts from earlier weeks are still sitting there? If it is
   more than about one week's volume, say so first. More drafts on top only go stale.
5. One short message to the user: last week's results, what changes this week, the plan per
   bucket, expected credit spend, the LinkedIn number for the week. Then start. Wait only if
   something needs a yes (spend above budget, a LinkedIn number above the cap).

**Phase 1. Find candidates** (`references/sources.md`, `references/agents.md`). Scouts per
bucket and angle write candidate rows as they go. `week.py add` merges them, drops excluded
domains, competitors and companies already in the CRM, and tags bucket and angle. Aim for
`volume.candidate_multiplier` times the quota in every bucket (default 2x).

**Phase 2. Verify the company and the person** (`references/verification.md`). Verifiers take
slices of about 8 companies: live site, funding or team, what they sell, the fit sentence,
the right person with a real profile, ties to the sender, and the full dedupe. Failures go to
`dropped` with a reason. About half survive. That is expected.

**Phase 3. Find and verify addresses** (`references/enrichment.md`). Free sources first, then
any configured enrichment tool. Target: at least `volume.verified_email_min` (default 80%) of
ready rows on a verified rung.

**Phase 4. Draft** (`references/drafting.md`). Writers take about 10 ready rows each, do the
per-person research, and write the draft into the row. Then for the whole week:
`week.py gate --apply`, `week.py batch`, the lint, a fresh reviewer per slice of about 50,
`week.py uniq`, fixes, and the checks again.

**Phase 5. Create the drafts.** Put them where the user sends from: their email client as
drafts (through a connector if one is configured) or a hand-off file they paste from. Write
draft ids back with `week.py ids`. Log every person to the CRM with the week's tags and no
touches (`week.py crm`, then `--apply`).

**Phase 6. LinkedIn** (`references/linkedin.md`). Only if `linkedin.enabled`. `week.py top N`
ranks the best prospects and writes `linkedin-top<N>.csv`. Show it to the user with the
counts. Invites go out only after their go on that exact list, by hand or through a tool the
user runs, inside `linkedin.weekly_invite_cap`. At the end of the week `week.py carry` rolls
the unsent rest into next week.

**Phase 7. Hand-off.** `week.py status`, `week.py export-drafts`, and `report.md` (template in
`references/quotas.md`): counts against the plan, verified address share, every hold and drop
with the reason, credits spent, the LinkedIn plan, and the drafts file. Then stop. The user
reviews and sends.

**After the user sends.** Next run: log real sends and replies as CRM touches from their
mailbox or a CSV export, learn from their edits to the drafts (a change they made twice
becomes a voice note), and measure with `reply_rates.py`. If hard bounces pass
`email.bounce_stop` (default 3%) of sends, tell the user to pause and draft only verified
addresses next week.

## When the run is cut short

The state folder is the run. Every phase resumes from `prospects.jsonl` (`week.py status`
shows where each row is). Never restart a phase from scratch. Never re-research a row that is
already `ready`. A new session reads `STATE.md`, runs `week.py status`, merges any agent files
that were not merged, and continues the earliest unfinished phase.

## What to say in the hand-off

Lead with the number drafted against the plan and the one-line reason for any shortfall.
Then the table from `references/quotas.md`. Then the people the gates removed, grouped by
reason. Then the file path of the drafts. Do not pad the message with process narration.
