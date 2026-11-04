# Learning: what got replies, and what changes next week

`scripts/reply_rates.py` turns a CSV export of first-touch sends into reply and meeting rates
by segment, with sample sizes and a confidence bound, so the next week's briefs follow
evidence instead of taste.

## The input

A CSV at `learning.sends_csv` (or `--sends`). One row per first-touch email. Columns:

| Column | Required | Notes |
|---|---|---|
| `date` | yes | ISO date of the send |
| `to` | yes | recipient address |
| `subject` | yes | |
| `body` | no | enables opener, length and bullet features |
| `replied` | no | true or false; a reply from the person, not an auto-reply or bounce |
| `meeting` | no | true when a meeting with that person or company followed |
| `bounced` | no | true or false |
| any other | no | pass with `--dims col1,col2` to segment by it |

Most email clients, CRMs and sequencing tools can export this. An example is in
`examples/sends.example.csv`.

The script also joins every week's `prospects.jsonl` in the state folder by email, so
bucket, angle, fit score, address rung and creative touch become segments automatically.

## Run it

```bash
python3 scripts/reply_rates.py --since 2026-01-01 --out state/<week>/reply-rates.md
python3 scripts/reply_rates.py --sends my-export.csv --min-n 20 --dims industry,region
```

It reports reply and meeting rates with n and a 95% Wilson lower bound, by: opener family,
subject features, length band, bullets or not, bucket, angle, fit score, address rung, send
week, and any extra columns. Segments under `--min-n` (default 30) are marked "hint". Each
run appends a headline row to `history.jsonl` in the state folder.

## Turning numbers into changes (every run)

Write three to five lines under "Change next week" in `report.md`, each with the numbers
behind it:

- A shape, opener or subject feature that clearly beats the others (its lower bound is above
  the other's rate, n of 30 or more): prefer it in next week's briefs.
- One that is clearly worse: stop using it, and add a line to the config's
  `sender.banned_phrases` or `drafting.avoid` with the numbers.
- A bucket or angle with a much better meeting rate: propose shifting up to 10 points of
  next week's quota toward it. Say so in the kickoff. A bigger shift is the user's call.
- **Never change the sender's voice from numbers alone.** A wording change goes to the user
  as a proposal. Only their yes, or their own edits, changes `sender.voice_notes`.

## Small numbers lie

At 100 sends a week, most segments are hints for a month. Do not flip the strategy on one
week of data. Look at the trend in `history.jsonl` and wait for n.

## The user's edits are the other half

Compare the drafts you created with what the user actually sent (from the sends export
`body` column). A change they made twice becomes a voice note or a banned phrase. Record
each learned rule with the date in the config, so the next run starts from it.
