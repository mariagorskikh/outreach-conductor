# Enrichment: an address for everyone who passed verification

Only rows that passed `verification.md` get enriched. Never pay to enrich a company you have
not verified.

## The ladder, per row (record the rung in `email_status`)

Verified rungs:

1. `proven-thread`: an address the person has written from before (an existing thread).
2. `proven-list`: an address from an event the user hosted, or a form the person filled in.
3. `verified-public`: the address on their site, legal page, code repository, press release,
   or a public post where they wrote it.
4. `tool-verified`: an enrichment tool (for example Apollo, Hunter, or a sequencing tool's
   finder) returns it with a verified status. Unverified or "catch-all" results do not count.
5. `verified-other`: any other solid source (a co-founder gave it, a second enrichment source
   confirms it). Write the source in `email_source`.

Unverified rungs:

6. `pattern-from-verified`: the exact pattern (`first.last@`) copied from a verified teammate
   at the same domain, after checking the domain has an MX record.
7. `guess`: `first@domain` with an MX record and no evidence against it.

Never probe a mail server (SMTP RCPT tricks). Never buy or reveal phone numbers. Never use
personal addresses unless the person published them for business contact.

## The verified share rule

- At least `volume.verified_email_min` (default 80%) of the week's drafts must be on rungs 1
  to 5. `week.py status` prints the share and flags it when it is below.
- Below the line, enrich harder (a second tool, a teammate's verified address for the
  pattern) before drafting more guesses.
- Rungs 6 and 7 may be drafted only when the row is otherwise strong (top fit score or a
  real tie). They are sent only when `email.send_guesses` is true (default false: they stay
  as drafts). Whether they are labelled in the hand-off is `email.label_guesses`.
- A guess never goes to a domain that bounced before, or where two people at the company
  share a first name.

## Credits

- Run enrichment in one dedicated agent or in the main session, not across every agent:
  hundreds of tool calls fill context fast, and one place keeps the credit count honest.
- Before Phase 3, check balances. Estimate the week's need. Inside
  `spending.weekly_budget`, go ahead. Above it, ask once in chat with the amount, keep working
  on free sources meanwhile, and spend only after an explicit yes. Free sources need nothing.
- Write `enrich-<n>.jsonl` and a credit log line per call batch.

## Bounces

Next week's run reads bounces before drafting: from the sends export (`bounced` column) or
from bounce notifications in the mailbox. A bounced address is dead; the row gets a new
person or a new address from rung 1. A domain with a bounce gets no guesses. If hard bounces
pass `email.bounce_stop` (default 3%) of sends, `week.py sent` pauses sending by itself
(`SENDING_PAUSED`), the report says so, and next week drafts only verified rungs. High bounce
rates damage the sender's domain for months.
