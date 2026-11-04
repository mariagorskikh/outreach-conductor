# Sources: where candidates come from

Every source gives candidates, not prospects. Everything found here still goes through
`verification.md`. Start with what is already on disk and in the CRM (researched before,
cheap to re-check), then go wide.

The tools are up to the user. Web search alone is enough to run this skill. Company databases
(for example Apollo, Crunchbase, PitchBook), search APIs (for example Exa), and event
platforms make it faster. Use whatever `sources` in the config lists, and nothing that
requires a login the user has not set up.

## The highest-yield moves, in order

1. **Look-alikes of real customers.** Take each seed in `icp.seed_customers` and search for
   similar companies ("companies like X", a find-similar API, the same investor's portfolio,
   competitors listed on review sites). This beats keyword search by a wide margin.
2. **Signals in the last 90 days.** Funding announcements, launches, new product pages, job
   posts that reveal the need (the job post names the tool or problem you solve), conference
   talks, public posts by founders about the pain.
3. **Directories and portfolios.** Accelerator batches, investor portfolio pages, industry
   associations, marketplace and integration directories (who lists an integration with the
   system your product sits next to).
4. **Events.** Attendee lists the user can legitimately see (events they attended or hosted),
   speaker lists, sponsor lists.
5. **Launch sites and communities.** Product launch sites, developer forums, newsletters that
   cover your segment.
6. **What is already on disk.** Earlier research sheets, the CRM rows with a high fit score
   and no outreach, lists the user liked before.

## Per bucket

- **Warm.** Start from the user's own network: first-degree connections at target companies,
  mutuals the user actually knows, shared past employers or schools the profile states,
  people met at events or on calls, and investors or customers who can introduce. Every row
  needs `warm_path` with evidence (`linkedin-1st`, `mutual:<name>`, `shared-org:<what>`,
  `met:<where, when>`, `intro:<who>`). No evidence, no row.
- **Events.** Only events the user attended or hosted. Save each event's guest list to
  `events/<event-slug>.json` in the week folder before research, so a lost browser tab costs
  nothing. Prefer events from the last 3 weeks; skip anything older than 60 days. Stay read
  only on event platforms: never RSVP, message guests, or follow anyone for the user.
- **Regional buckets.** Search in the local language too. Use local startup news, local
  accelerators and investor portfolios. Record `country` from the site's legal page.
- **Core.** Look-alikes, signals, directories, in that order.

## Search hygiene

- One search at a time per agent, a few seconds apart. Back off on rate limits.
- Write candidates to the scout file as you go, not at the end.
- Record `source` for every row (the query, the seed, or the page). It feeds the learning loop.

## Scout output (one JSON object per line, appended as you go)

```json
{"bucket":"core","angle":"angle-one","company":"Example Co","domain":"example.org",
 "website":"https://example.org","source":"look-alike of seed-customer.example",
 "why":"sells X to mid-size clinics and names the system their staff log into","country":"US"}
```

For event rows add `"event":{"name":"...","date":"YYYY-MM-DD","url":"...","attended_evidence":"..."}`
plus `"person_name"` and `"person_profile"` from the guest list.

`week.py add <files>` merges scout files into `prospects.jsonl`. It dedupes by registrable
domain and normalized company name, drops excluded domains, competitors and companies already
in the CRM snapshot, and keeps the first row.
