# Verification: legit company, working website, right person, never contacted

Every row passes all four checks, with evidence written into the row, before it can be
`ready`. `week.py gate` refuses a row with an empty required field.

## 1. The company is legit

| Field | Pass when |
|---|---|
| `stage`, `total_raised`, `last_round`, `last_round_date` | a public round with a source (press, investor page, database snippet), **or** |
| `team_size` | 3 or more real people visible (company page, team page, profiles) |
| `legit_evidence` | one line with the source URL, for example "Seed 4M led by X, 2026-05 (news.example/...)" or "7 people on the company page" |

Drop: solo side projects with no funding, agencies and consultancies (unless they are your
ICP), student projects, "stealth" with no product, dead, pivoted or acquired companies,
competitors, and anything in `icp.disqualifiers`.

## 2. The website works and sells into your ICP

- Load the home page today. It answers, the product is described, it is not parked, not
  "coming soon", not a broken template, not an unrelated pivot. A bot wall (403) is not
  death; read it another way before dropping.
- **It must say what you sell into.** Write `fit_sentence`: what this company would do with
  your product, in one sentence, naming the system or workflow when the site names it. If you
  cannot write it from the site, the row is out.
- Record `website_ok: true`, `website_checked_at`, and `systems` (only tools, platforms or
  workflows the site, docs, job posts or a talk name; never a guess).

## 3. The right person, and the research bar

- **Role:** the first role in `icp.target_roles` the company has. Current role verified on a
  profile or the team page (`role_source`), never from an old sheet. One person per company.
- **A real profile is required.** `linkedin_url` (or another public profile) taken from a
  page, never constructed from the name. The profile name and current company match the row.
- **Ties to the sender:** relationship degree, named mutuals, shared past (same employer,
  school and years, community, event). Only ties you can point at. A surname is not evidence.
  Fill `linkedin_degree`, `mutuals`, `ties`, `tie_source`.
- **Fit:** `fit_score` 1 to 5 and `fit_reason` from `icp.fit_rubric`, from facts. Rows at
  `icp.min_fit_score` only fill a bucket after its higher scores are used.

The research bar, before a person appears in any batch. Know and be able to show:

1. The company is real and alive today.
2. Funding and stage with a date, or "nothing public" said explicitly.
3. What they sell and who their end customer is, in your own words.
4. Why your product fits, concretely. If you cannot write that sentence, they do not belong.
5. The person's current role, verified.
6. Rough team size or traction.

A job title and a buzzword are not research. If the user asks for 30 and only 8 pass, hand
over 8 and say why.

## 4. Never contacted, never met, nobody else at the company either

Run every source on the company (domain and name) and on every co-founder, not only on the
person. A co-founder who was emailed makes the company contacted. Record in `dedupe` which
sources were checked and what they returned.

| # | Source | How |
|---|---|---|
| 1 | CRM | the snapshot from `week.py crm-pull` (merge already checks it by domain and name), plus a lookup of the contact's full timeline when a hit is unclear |
| 2 | Sent mail | search the domain, the brand, the person's full name, and any address on file; people write from more than one domain |
| 3 | Drafts | the drafts folder: another session or teammate may have drafted to them today |
| 4 | LinkedIn and other DMs | an existing message thread means a conversation already happened; read it before anything else |
| 5 | Calendar and meeting notes | a past meeting, a booked meeting, or a meeting note means "already met" (see below) |
| 6 | Outreach logs and earlier batches | every earlier draft file and send log in the state folder and elsewhere; ignore master research sheets, they match everyone |
| 7 | Sequencing tools | sends from a sequencing or bulk email tool often never show in the mailbox |
| 8 | Stop lists | anyone who opted out, anyone the user trashed a draft to, `icp.exclude_files` |
| 9 | Customers and investors | never in a cold batch |
| 10 | This week | `week.py merge` and `week.py uniq` catch two rows or two drafts for one company |

### The already-met rule

Never write to someone as a stranger after the sender has spoken with them. A stale
scheduling thread is not evidence that the meeting did not happen: booking tools move the
conversation out of email. Check the calendar (past and future), meeting notes, and every
thread with the person and their company, not just the one in front of you.

| State | Evidence | What you may write |
|---|---|---|
| Already spoke | past meeting, meeting note, a "great chatting" follow-up | nothing cold; drop from the batch and report it |
| Meeting booked | future calendar event, booking confirmation | nothing; report under "booked" |
| Mid-conversation | the sender wrote in the last few days, or the ball is with them | nothing; it belongs to the sender |
| Never met | nothing in the sources above | proceed |

An event bucket row is the exception: meeting at the event is the point of the email. A call
afterwards still removes them.

Rows removed here stay in the file as `dropped` with `drop_reason` ("emailed 2026-03-04, CRM",
"met 2026-03-20, calendar") and are listed in the report. Silent drops repeat next week.

## Statuses (`week.py` enforces the order)

`candidate` > `verified` (sections 1 to 4 pass) > `ready` (address found and per-person
research done) > `drafted` (draft in the row, lint clean) > `created` (draft id) > `sent`
(from real sends only). Side exits: `hold` (fixable: no address, unsure role, review held it)
and `dropped` (out for good this week).
