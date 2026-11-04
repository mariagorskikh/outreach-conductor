---
name: outreach-conductor
description: Runs a weekly outbound cycle end to end, on its own. Finds candidate companies that match your ICP, verifies the company, the website and the right person, researches each person, dedupes against your CRM, sent mail and drafts, writes personalized emails in your own voice, runs a self-review gate, sends them from your own mailbox in daily batches inside your caps (or creates drafts if no sender is configured), ranks a short list of LinkedIn connection requests, logs everything to your CRM, and learns from last week's reply rates. Asks setup questions once; after that it only asks before spending money. Uses parallel subagents and a resumable state folder per week. Use when the user says "weekly outreach", "run the outreach cycle", "this week's prospects", "find, verify and draft", "build this week's outbound", "prospect and email", "outbound conductor", or asks for a full week of researched prospects, emails and LinkedIn connects.
---

# Outreach conductor

One weekly cycle, one state folder, one set of quality gates. The goal is a batch of emails
where every single one reads like the sender wrote it after ten minutes of research. Volume is
a setting. Quality is not.

## How this skill runs

- **Ask once, up front.** On the first run, or when `config.yaml` is missing or a needed value
  is blank, ask the setup questions in `references/setup.md` in one short batch, write the
  config, and continue. Later runs ask nothing. If a required fact is genuinely missing and
  cannot be found, ask one short question and keep working on everything else meanwhile.
- **Then do everything.** With `autonomy.mode: autonomous` (the default) the skill finds,
  verifies, writes, self-reviews, and then acts: sends the emails (or creates drafts when
  `email.send_via` is `none`), hands the LinkedIn list to the configured invite tool, and
  writes the CRM. No approval step. The self-review gate below replaces it.
- **Money is the only approval.** Anything that spends money waits for the user's explicit
  yes in chat: paid enrichment or data credits above `spending.weekly_budget`, buying any
  list, tool, domain or mailbox, upgrading any plan. Free sources need nothing. Spending less
  or pausing needs no approval.
- **Hard stops are not approvals, they are stops.** See "Hard stops" below. On a stop, halt
  that action, finish whatever else is safe, and report.
- **`autonomy.mode: review`** restores the old per-action gates (see "Review mode").

## Before anything else

1. Find the config: `config.yaml` next to this file, or the path in
   `OUTREACH_CONDUCTOR_CONFIG`. If it does not exist, run the setup interview, write
   `config.yaml` from `config.example.yaml`, run `week.py init` to check it parses, and go on.
2. Read the config fully. Everything company specific lives there: the ICP, buckets, angles,
   the voice notes, the CRM, sources, the sender, caps, the footer, the budget.
3. Read the sender's example sent emails (`sender.sent_examples_path`). Emails copy what the
   sender actually sends, not what a style guide says.
4. Read last week's `report.md` in the state folder, if there is one, and carry its
   "Change next week" lines into this week's briefs.

## Reference files

| File | What it holds |
|---|---|
| `references/setup.md` | the one-time setup questions and how to fill `config.yaml` |
| `references/quotas.md` | buckets, angles, the funnel, backfill rules, the report template |
| `references/sources.md` | where candidates come from, by bucket, tool agnostic |
| `references/verification.md` | the legit bar, the right person, the research bar, the dedupe gate |
| `references/enrichment.md` | the email address ladder, the verified share rule, bounces |
| `references/drafting.md` | drafting gates, the no-repeat check, lint and the review loop |
| `references/sending.md` | the send loop: daily batches, pacing, footer, bounce stop, logging |
| `references/linkedin.md` | choosing the top prospects, the weekly cap, safety stops |
| `references/agents.md` | fan-out: waves, briefs, write-as-you-go, resume, rate limits |
| `references/learning.md` | the reply-rate loop and how it changes next week |
| `references/compliance.md` | CAN-SPAM, GDPR basics, opt-outs, platform terms |
| `scripts/week.py` | the state folder: init, merge, gate, status, batch, uniq, send-queue, sent, top, carry, crm |
| `scripts/reply_rates.py` | reply and meeting rates by segment, from a CSV export of sends |

Run scripts with `python3 scripts/<name>.py --help`. They use the standard library only
(PyYAML is used if installed, otherwise a built-in YAML subset reader). Scripts never send
anything themselves and default to dry runs. The agent passes `--apply` or `--reviewed`
itself once the self-review gate passes.

## Hard rules (never bend, at any volume)

1. **One person per company, and a company already contacted is out.** Any earlier email,
   DM, invite thread, meeting, reply or draft to anyone there removes the whole company.
2. **Legit or out.** Funded, or at least three real people on the team. A working website that
   clearly sells into your ICP. A real person with a findable profile. No exceptions to hit a
   number.
3. **The right person.** Use `icp.target_roles` in order. Never anyone in `icp.never_roles`.
4. **The sender's voice wins on every word.** Follow `sender.voice_notes` and the example
   emails. Short. No AI tells. No em dashes or en dashes. Real links only.
5. **No repeats.** No two emails to one company. No email to anyone with an earlier draft or
   send. No two emails that read alike. `week.py uniq` must pass before anything is created.
6. **Quality over count.** If the configured number of good prospects does not exist this
   week, send fewer and say where the pool ran dry. Padding is the failure this skill exists
   to prevent.
7. **A draft is not a touch.** Drafts are tagged `draft-not-sent` in the CRM. Touches are
   logged only from real sends (`week.py sent`, then `week.py crm --apply`).
8. **Never guess facts.** Only name a system, customer, round or milestone you can point at
   with a URL. A guessed fact costs more than a plain opener.
9. **Compliance on every send.** Follow `references/compliance.md`: footer, opt-outs,
   deliverability, platform terms. Autonomous sending makes this the skill's job.

## The self-review gate (before every outward action)

Nothing goes out until all of these pass for the batch:

1. `week.py gate --apply`, `week.py uniq`, and the lint in `references/drafting.md` pass.
2. A fresh reviewer per slice of about 50 re-reads each email as its recipient would, and
   re-checks the hook and the role for a sample of 10 against the live pages. Every warm and
   event email is read individually. One false hook sends the slice back.
3. Every fact has a source URL, every link resolves to the real page, every first name and
   company spelling matches.
4. Fix, then run the checks again. Up to three rounds. A row that still fails is `hold`.

Only then does the agent pass `--reviewed` to `week.py send-queue` and act.

## Hard stops

Halt that action, record why, keep doing whatever else is safe, and put it in the report:

- **Bounce stop.** Hard bounces above `email.bounce_stop` (default 3%) of sends. `week.py
  sent` writes `SENDING_PAUSED` in the state folder; `send-queue` refuses until the user
  removes it after fixing addresses. Next week drafts only verified rungs.
- **Platform warnings.** Any limit notice, captcha, checkpoint, "unusual activity", login,
  2FA or re-auth prompt, or a mail provider's sending limit or spam warning.
- **Opt-outs.** Anyone who said stop, in any channel, goes to the do-not-contact list and is
  never emailed or invited again.
- **Payment or billing forms.** Never filled in. Never type card numbers or passwords.
- **Never inventing facts.** A row that cannot be made true is held, not sent.

## Spending

Paid enrichment or data credits are spent only inside `spending.weekly_budget`. Show credits
used and balance left in the report. Above the budget, any purchase (a list, a tool, a domain,
a mailbox), and any plan upgrade: ask once in chat with the amount and what it buys, keep
going on free sources while you wait, and spend only after an explicit yes.

## The weekly cycle

A full run can span several sessions and days. Always pass `--week` to `week.py` with the week
the run started in, so a run that crosses Monday keeps one folder. Keep `STATE.md` in the week
folder current (what is done, what is running, counts) so a new session can resume.

**Phase 0. Kickoff.** `week.py init`, then `week.py crm-pull` for a fresh CRM snapshot. Log
last week's real sends, replies and bounces (`references/sending.md`), run `reply_rates.py`
(`references/learning.md`), and read last week's report. If more than about a week of unsent
drafts is sitting in the mailbox, send or clear those first. Write the plan per bucket, the
expected credit spend and the LinkedIn number into `STATE.md`. Then start; do not wait.

**Phase 1. Find candidates** (`references/sources.md`, `references/agents.md`). Scouts per
bucket and angle write candidate rows as they go. `week.py add` merges them, drops excluded
domains, competitors and companies already in the CRM, and tags bucket and angle. Aim for
`volume.candidate_multiplier` times the quota in every bucket (default 2x).

**Phase 2. Verify the company and the person** (`references/verification.md`). Verifiers take
slices of about 8 companies: live site, funding or team, what they sell, the fit sentence,
the right person with a real profile, ties to the sender, and the full dedupe. Failures go to
`dropped` with a reason. About half survive. That is expected.

**Phase 3. Find and verify addresses** (`references/enrichment.md`). Free sources first, then
any configured enrichment tool inside the budget. Target: at least
`volume.verified_email_min` (default 80%) of ready rows on a verified rung.

**Phase 4. Draft and self-review** (`references/drafting.md`). Writers take about 10 ready
rows each, do the per-person research, and write the email into the row. Then the
self-review gate above for the whole week.

**Phase 5. Send** (`references/sending.md`). If `email.send_via` names a connector: each
business day, `week.py send-queue --reviewed` builds that day's list inside
`email.daily_send_cap` (opt-outs removed, `compliance.footer` added, unverified addresses
left out unless `email.send_guesses`), the agent sends them one by one from the user's own
mailbox spread through `email.business_hours`, checks each one left the outbox, and records
them with `week.py sent`. If `send_via` is `none`, create drafts in the mailbox (or the
hand-off file) and write draft ids back with `week.py ids`; say plainly that nothing was sent.
Then `week.py crm --apply`: sends as touches, drafts as `draft-not-sent`.

**Phase 6. LinkedIn** (`references/linkedin.md`). Only if `linkedin.enabled`. `week.py top N`
ranks the best prospects and writes `linkedin-top<N>.csv`. If `linkedin.invite_tool` is set,
hand it the list inside `linkedin.weekly_invite_cap` and `daily_invite_cap`; otherwise the
list is for the user to send by hand. The skill never drives LinkedIn itself beyond the
platform's terms. At the end of the week `week.py carry` rolls the rest into next week.

**Phase 7. Report.** `week.py status`, `week.py export-drafts`, and `report.md` (template in
`references/quotas.md`). One summary to the user, after the fact.

## Review mode

With `autonomy.mode: review`, the old gates apply on top of the self-review gate:

- Drafts only. The skill never sends an email, a LinkedIn invite or a DM by itself. It may
  send only a specific batch the user has approved in chat, by count and by list, in this
  session. One approval covers one batch, not the next one.
- The setup interview shows the filled `config.yaml` and waits for a yes before Phase 0.
- The kickoff message waits for a go on the plan.
- The LinkedIn list is posted with counts and invites go out only after the user's go on
  that exact list.
- The hand-off ends the run: the user reviews and sends. Next run logs what they sent and
  learns from their edits (a change they made twice becomes a voice note).

## When the run is cut short

The state folder is the run. Every phase resumes from `prospects.jsonl` (`week.py status`
shows where each row is). Never restart a phase from scratch. Never re-research a row that is
already `ready`. Never re-send a row that is `sent`. A new session reads `STATE.md`, runs
`week.py status`, merges any agent files that were not merged, and continues the earliest
unfinished phase, including the rest of a send batch.

## What to say in the report

Lead with the number sent (or drafted) against the plan and the one-line reason for any
shortfall. Then the table from `references/quotas.md`. Then everything that went out: the full
text of each email or a path to `drafts-<week>.md` with it, recipients, send times, the
LinkedIn list and what the invite tool did. Then everything skipped or held, grouped by
reason, every hard stop hit, and any money question still waiting for a yes. No process
narration.
