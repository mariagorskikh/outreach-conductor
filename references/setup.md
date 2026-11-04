# First-run setup: the interview

Run this when `config.yaml` does not exist, or when the user says the ICP, offer or mix has
changed. Ask in small groups, not one long form. Offer a sensible default for every question
so the user can just say "yes".

Write the answers into a copy of `config.example.yaml` named `config.yaml`, show the user the
filled file, and get a yes before Phase 0.

## 1. The sender

- Whose name goes on the emails, and their role?
- The company name and its website?
- A booking link, if they want one in emails to people they already know? (Default: no link
  in a first cold email.)
- Where can I read 10 to 30 emails you actually sent that got replies? A folder of `.md` or
  `.txt` files, a CSV export, or paste them. Save them to `sender.sent_examples_path`.
- Anything you never want to see in an email? (Words, phrases, claims.) These go into
  `sender.banned_phrases`.

Then read the examples yourself and write 5 to 10 `sender.voice_notes`: sentence length,
greeting, sign-off, how they open, whether they use bullets, how they close, typical length
in words. Show the notes to the user. Their corrections win.

## 2. The offer

- In one sentence, what do you sell and to whom?
- What problem does it solve that the prospect already feels?
- Two or three proof points you are allowed to say (a customer type, a result, a credential).
  Only things the user confirms are true and public.

## 3. The ICP

- Who is a great customer? Describe the company: what it does, stage, size, region.
- What signals on their website or in the news show they need you?
- Who is definitely not a customer (competitors, wrong stage, wrong model)?
- Which roles do you write to, in order of preference? Which roles never?
- Name 3 to 5 real customers or great fits. These become seeds for look-alike search.
- Competitor domains to always exclude?
- Any do-not-contact list (CSV with a `domain` or `email` column)?

Write a 1 to 5 fit rubric into `icp.fit_rubric` from the answers. 5 means "would buy this
quarter if they saw it". 3 means "plausible, not urgent". Below `icp.min_fit_score` is out.

## 4. Volume and mix

- How many drafts a week do you want to review and send? Default 100. Recommend 50 to 200.
  Say plainly: a smaller number of well researched drafts beats a big number of thin ones,
  and every draft needs the user's own review before it goes out.
- Buckets (who, and how you reach them). Suggest a starting mix, for example:
  `warm` (a real connection) 10%, `events` (people met or seen at events) 10%,
  `region-a` 30%, `core` 50%. Each bucket gets a share and a short description. Warm buckets
  get `requires: [warm_path]`, event buckets get `requires: [event.name, event.date]`.
- Angles (what you pitch). One per product use case or segment, with a share. The shares
  steer sourcing, not the pitch: the pitch always follows what the company actually does.

## 5. Data and tools

- Where is your CRM? Default: a CSV file at `crm.path` (columns in
  `examples/crm.example.csv`). If they use a real CRM, set `crm.type` to `command` and ask
  for an export command and an import command (any script or CLI that prints CSV and reads
  JSON). Never store API keys in the config; use environment variables.
- Which research tools do you have? Web search is enough to start. Optional: a company
  database, an enrichment tool, a search API, a news feed, event platforms.
- Where do drafts go? Your email client's drafts folder through a connector, or a Markdown
  hand-off file you paste from.
- Is there a weekly budget for paid enrichment credits? Default 0 (free sources only).

## 6. LinkedIn

- Do you want a weekly list of top people to connect with? Default yes.
- Weekly cap? Default 50, daily 15. Tell the user LinkedIn's real limits change and are often
  lower for new or low-activity accounts. Stay well under them. The user sends the invites or
  approves a specific list.

## 7. Learning

- Can you export your sent mail weekly as CSV (date, to, subject, body, replied, meeting,
  bounced)? Your email client, CRM or sequencing tool usually can. Set `learning.sends_csv`.
  Without it the skill still works; it just cannot learn from replies.

## After the interview

Write `config.yaml`, then run `python3 scripts/week.py --help` and `python3
scripts/week.py init` to confirm the config parses. Fix any error before Phase 1.
