# Drafting: every email reads like the sender wrote just that one

The sender's own sent emails are the model. `sender.voice_notes`, `sender.banned_phrases`
and the examples at `sender.sent_examples_path` own every word. When this file and the
sender's newest real emails disagree, the emails win and this file gets fixed.

## Before drafting starts (once per run)

1. Pick 3 to 5 example emails per shape (cold, event follow-up, warm intro) from the sender's
   sent examples, preferring ones that got replies. Writers get the real emails in their
   brief, not a summary of them.
2. Read last week's "Change next week" lines and any edits the user made to last week's
   drafts. A change they made twice is now a rule.

## Shape per bucket

Set these in the config under each bucket's `shape`. Sensible defaults:

| Bucket | Opener | Body |
|---|---|---|
| warm | the real connection, said plainly ("We're both connected to {mutual}") | short; the ask is a conversation |
| events | the event and when ("we were both at {event} last week") | short; no hard pitch |
| regional | as core, plus the region's own rules from the config | |
| core | the first true opener from the order below | the configured pitch shape |

**Opener order for cold** (use the first one that is true and current):

1. A real milestone from the last 3 months, said simply ("Congrats on the seed round!").
2. A post, launch or talk of theirs from the last 2 weeks ("Saw your post on ...").
3. What they build, in their own words ("Saw you're building {what they do}").

Never invent a hook. A row whose hook cannot be made true and current gets the plain opener
(3). `hook_source` must be a URL or the word `plain`.

## What a good cold draft looks like

- Under about 120 words in the body. Shorter usually wins; let `reply_rates.py` tell you.
- One idea. One clear, low-friction ask (by default a statement of interest in a quick
  chat, not a demand for a meeting).
- The subject names their company, product or the system they work with. Generic subjects
  lose.
- Proof only from `offer.proof_points`. Never their numbers, customers or internal names.
- Name a system only when their site, docs, a job post or a talk names it; otherwise
  describe the category ("the scheduling system your clinics use").
- No fake "Re:" or "Fwd:" subjects, no false urgency, no fake familiarity.
- No em dashes or en dashes, no stacked adjectives, no "I hope this finds you well", no
  "I wanted to reach out", nothing in `sender.banned_phrases`.

## Personal, every time

Each writer does separate research for each row: the person's background, what the company
does in one sentence, the context, and the one real tie. A writer with 10 rows does 10
separate pieces of research. `hook_source` and `tie_source` are URLs.

## No repeats (`week.py uniq`, before any draft is created)

It fails on:

- two rows for one company (domain) or one person;
- two identical subjects;
- a non-template sentence that appears in more than 3 drafts (or 1% of the week, whichever
  is larger): writers copying each other;
- the same bullet set, word for word, in more than 5 drafts of one angle.

Lines that may repeat are listed in `drafting.template_lines` in the config (greeting,
sign-off, a fixed credential line, a fixed pitch line). Everything else must be written for
that person.

`uniq` does not see earlier weeks. Those are caught at merge time, because every drafted
person goes into the CRM tagged `draft-not-sent` (`week.py crm --apply`), and next week's
merge drops their company. So `week.py crm --apply` is not optional.

## Lint

Before review, check every draft mechanically. If the user has a linter, use it. Otherwise
check at least: no em or en dashes (and none of their HTML entities), no banned phrases, no
placeholder left (`{`, `}`, `TODO`, `[Name]`), every link resolves and is the real URL (not a
tracking redirect), the first name matches the recipient, the company name is spelled as on
their site, body length inside the configured limit.

## Review at volume

- A fresh reviewer (an agent that did not write the drafts) per slice of about 50. It reads
  each draft against the sender's newest real emails and asks:
  1. Would the sender plausibly have written this exact email?
  2. Is the hook true, current and sourced?
  3. Is the person's role current?
  4. Is every claim about the prospect checkable on their own pages?
  5. Is every claim about the sender's product in `offer`?
  6. Does it read naturally out loud?
  7. Is there exactly one ask?
  8. Would the recipient know in one line why they got it?
- The reviewer re-checks the hook and the role for a sample of 10 per slice against the live
  pages. One false hook in the sample sends the whole slice back to its writer.
- Up to three rounds. A draft still failing after three is `hold` with the reason.
- Every warm and event draft is reviewed individually, not sampled.

## Optional creative touch

`creative_touch` in the config lets the user add a small, personal extra (a custom image, a
short personalized video, a hand-made mockup) to a small share of top prospects, default 0%.
If enabled: only top fit rows, never more than about 5% of the week, only when you are sure
of the person's identity, and the user approves the idea and every asset before it is
attached. Measure it as its own segment in `reply_rates.py`.

## Creating them

`week.py batch --out drafts-<week>.json` writes rows with to, cc, subject, text, first,
company, bucket, angle, email_status, hook_source, tie_source. Create drafts in the user's
email client in chunks of about 50, verify each one was created with the right recipient and
body, then `week.py ids <created.json>` writes the draft ids back. If links get rewritten by
a connector, fix it or fall back to the hand-off file.

`week.py export-drafts` writes `drafts-<week>.md`, grouped by bucket: To, Subject, body,
draft id, LinkedIn degree and mutuals, the tie, the address rung, and the review result.
