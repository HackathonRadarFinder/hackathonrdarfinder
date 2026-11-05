# Automated college website discovery: review-first pilot

This pilot fills the **discovery gap**, not the public event catalog. The
production directory has 54,522 AISHE college records but no verified websites
or event URLs. Names, state, and district alone are insufficient permission or
evidence to crawl a college's website.

## Current automated sources

- `backend/workers/college_website_candidates.py` reads a small rotating
  slice of the **public** `/institutions` API, searches Wikidata entity
  names and inspects Wikidata `P856` (official website) claims.
- Suggestions include the matching college's AISHE identifier, state,
  district, Wikidata record, candidate URL and a name similarity score.
- Nothing is fetched from college websites. A Wikidata P856 value is **not**
  verification of an institution's site or of permission to crawl it.
- The output is a JSON **review artifact**; no Supabase writes, permission
  updates, account data, collector registrations, or public event publication.
- Hard limits: 5 pages or 100 candidate lookups per run, sequential requests,
  bounded response sizes, descriptive bot user-agent, and rate-limit compliance.
  Upstream failures are reported in the summary, not silently passed off as
  verification.

To run the pilot in the repository root:

```powershell
python backend/workers/college_website_candidates.py --pages 3 --max-colleges 50 --out college-website-candidates.json
```

GitHub Actions workflow `college-website-candidates.yml` uploads the
candidate JSON for review. **GitHub cron scheduling works on the default
branch only**; the workflow must exist on the default branch to run on
schedule, even though the production Render branch is currently different.
This distinction must be resolved before claiming the GitHub schedule is
active. A separate ChatGPT daily research task can report newly found event
candidates in the interim.

The manual initial event packet is at
`backend/data/discovery/college-hackathon-candidates-2026-11-06.json`.
Those three official-site events are review candidates, not database entries.

## How to graduate verified sources into the existing collector

1. Match the website candidate to the AISHE institution using independent
   official evidence, not name similarity alone. Confirm the real HTTPS domain
   and that the website belongs to the stated college.
2. Locate one or more specific college event pages, technical-club feeds,
   RSS feeds, official JSON endpoints, or allowed sitemaps. Verify collection
   rights and robots rules and document a policy basis.
3. Update the institution website and `event_urls` through the **reviewed**
   directory workflow without overwriting the separate public owner
   publication record or asserting AISHE reuse rights.
4. Register an authorized `SourcePolicy` through protected
   `PUT /admin/discovery/sources`, with `institution_id`, exact verified
   event URL, adapter (`official-html-v1`, `rss-v1`,
   `sitemap-v1`, or `events-json-v1`), review timestamps,
   reference and `terms_permit=true` only when supported.
5. Run `workers.discovery --allow-live` from an explicitly enabled,
   dedicated scheduler. The existing extractor stages records as
   `discovery_announcements.status=pending`; a human reviewer confirms
   organizer, event date, registration link and evidence before publication.

Never treat a discovered event or an AISHE directory row as approval to scrape
or redistribute. Missing dates should remain unknown. Keep requests bounded,
use rate-limit backoff, and do not publish personal information.
