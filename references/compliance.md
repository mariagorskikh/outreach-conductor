# Compliance: the basics

This is not legal advice. It is the floor this skill holds to. The user is responsible for
their own outreach and should check the rules where they and their recipients are.

## Autonomous sending makes this the skill's job

In `autonomous` mode the skill sends on the user's behalf, so deliverability and compliance
are its job on every send: the `compliance.footer` (a physical postal address and an opt-out
line where the law asks for one) is added by `week.py send-queue`, opt-outs are checked before
every batch, bounces are counted after every batch, and any warning stops sending. If the
config has no footer and the recipients are in a place that requires one, set it during
setup; do not send commercial email without it there.

## Email

- **CAN-SPAM (US).** Honest sender name and address. No misleading subject lines (no fake
  "Re:" or "Fwd:"). A valid physical postal address in commercial email. A clear way to opt
  out, honored within 10 business days. Applies to business-to-business email too.
- **GDPR and ePrivacy (EU, UK).** Cold business email usually relies on legitimate interest.
  That means: the email is relevant to the person's professional role, you collect only what
  you need (name, work address, role, company), you say where you got their details if asked,
  you honor objections and erasure requests promptly, and you keep a record. Some countries
  (for example Germany) are stricter on unsolicited email; check before including them.
- **CASL (Canada).** Stricter than CAN-SPAM; cold commercial email needs implied consent such
  as a published business address and a relevant message.
- **Opt-outs are permanent.** Anyone who says stop, unsubscribe, not interested, or remove me
  goes on the do-not-contact list (`icp.exclude_files`) and is never drafted again, in any
  channel.
- **Deliverability is part of compliance.** Authenticate the sending domain (SPF, DKIM,
  DMARC). Keep bounces under 3%. Warm new domains slowly. Do not send hundreds a day from a
  fresh mailbox.

## LinkedIn and other platforms

- Follow each platform's user agreement. LinkedIn prohibits most automated activity and
  scraping. This skill ranks people; the user sends invites by hand or through a tool they
  have chosen, configured as `linkedin.invite_tool`, and are responsible for. The skill never
  drives LinkedIn itself.
- Respect rate limits and any warning the platform shows. A warning means stop, not retry.
- Never create fake accounts, never use someone else's account, never bypass a captcha or
  checkpoint.

## Data

- Store prospect data only as long as it is useful. Do not copy whole provider records into
  your files; keep the fields you need and the source URL.
- Keep `config.yaml`, `.env`, the state folder and all CSV exports out of version control
  (the bundled `.gitignore` does this).
- Never put personal data in URLs or query strings.
