# LinkedIn: the weekly top prospects

Only when `linkedin.enabled` is true. This skill picks and ranks people. The user sends the
invites themselves, or approves an exact list for a tool they run. Never automate LinkedIn
beyond what its terms allow.

## The weekly cap

- `linkedin.weekly_invite_cap` (default 50) and `linkedin.daily_invite_cap` (default 15).
  LinkedIn's real limits vary by account and change without notice. New or quiet accounts get
  much lower limits. Stay well under them.
- Keep a ledger at `linkedin.ledger_path` (CSV: `date, linkedin_url, name, result`). Results:
  `sent`, `already_connected`, `already_pending`, `no_profile`, `stopped`.
- At kickoff, count the last 7 days of `sent` in the ledger. The week's number is the cap
  minus that count. Say it in the kickoff message.
- On any warning from LinkedIn (a limit notice, a captcha, a checkpoint, "unusual activity",
  a phone verification), stop everything, record `stopped` in the ledger, lower the cap to
  what was sent in the 7 days before the stop, and tell the user. No raise without their go.

## Who goes on the list

`week.py top N` ranks the week's `ready`, `drafted` and `created` rows plus last week's
queue, by:

1. a real tie or a named mutual;
2. fit score (highest first);
3. bucket warmth (the order in `bucket_precedence`);
4. a verified email (small boost);
5. waited a week already in the queue (small boost).

It keeps only titles matching `linkedin.title_pattern` (decision makers by default) with a
profile URL. It skips people already connected or pending, anyone in the ledger, customers
and investors.

## Reading profiles

Reading hundreds of profiles through one browser session is slow and visible. Read the
relationship state and mutuals only for warm rows, event rows, and the top of the ranking.
Pace reads (one every few seconds), keep people searches low per session, and stop on any
challenge page. Everyone else gets `linkedin_degree: unknown`.

A first-degree connection at a company you are about to cold email is a warm path: say so
next to that draft. A direct message may beat the email. Never message someone who was
already emailed this week unless the user says so for that person.

## The user's go

Post `linkedin-top<N>.csv` (rank, name, title, company, fit, bucket, degree, mutuals, ties,
one-line why, emailed this week) with the counts. One go covers that exact list for the week.
Invites are sent by the user, or by a tool the user runs and has approved, inside the cap,
best first, spread over the week. Notes on invites are optional; default none.

At the end of the week, `week.py carry` writes every listed person with no ledger row to next
week's `linkedin-queue.csv`, and next week's `top` gives them a small boost.
