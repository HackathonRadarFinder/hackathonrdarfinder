# Unstop dataset review — 15 October 2026

## Supplied collection summary

- Source: `unstop.com/hackathons` public listing; API endpoint reported as `/api/public/opportunity/search-result`
- Collected at: 2026-10-15 20:04 IST
- Total records: 6,766
- Open: 253
- Closed/past: 6,513
- Records with prize listed: 5,017
- Records with registration deadline: 6,766
- Records with end date: 6,766
- Dates reported in IST; `Scraped At` reported in UTC
- Collector reports robots.txt checked, 1–2 seconds between requests, identified User-Agent, no login or bypass

## Arithmetic and completeness observations

- Open + closed/past = 253 + 6,513 = 6,766 (counts reconcile).
- 1,749 records have no listed prize (6,766 − 5,017). The summary says this can mean the organizer did not enter a prize amount; this is not automatically a data error.
- The summary reports deadlines and end dates on all records, but this must be checked against the actual exported file before treating it as verified field completeness.

## What this summary does not prove

The summary alone cannot establish the actual number of duplicate records, URL validity, field-level accuracy, timestamp parsing, policy compliance for every request, or real-data precision/recall. No row-level Unstop export was included in the material available for this review. The collection method is recorded as the collector's report, not independently verified here.

## Module 2.4 compatibility work completed

- Added support for ISO date-time strings and normalized start date, end date, and registration deadline to `YYYY-MM-DD`.
- Added mapping/preservation for `end_date`, `registration_deadline`, `mode`, and `status`.
- Added common Unstop/API field aliases for event title, organizer, and public URL.
- Added JSON import support for common wrapper keys (`events`, `opportunities`, `results`, `data`, `items`, `records`) and UTF-8 BOM-safe CSV/JSON reads.
- Improved URL normalization to ignore common tracking parameters, normalize host case, `www`, default HTTP(S) ports, repeated/trailing slashes, and query ordering.
- Fixed missing locations so two blank locations are not treated as positive evidence of a match.
- Added tests for timestamp fields, wrapper JSON, tracking URL normalization, and missing-location behavior.

## Verification results

- Python compilation: passed.
- Unit tests: 14/14 passed, including database migration/metadata persistence, dataset audit, and matching edge cases (see `VERIFICATION.txt`).
- Performance: candidate generation was parity-checked against brute force on 500 synthetic records (no duplicate/uncertain candidates omitted); 6,766 synthetic records processed in 5.76 seconds in this environment. This is not a benchmark of the actual Unstop dataset.
- Repo-preview labeled pairs: 20/20 predictions correct on the included example.com practice pairs only; this is not real-world accuracy.
- Four-row synthetic smoke sample: 4/4 predictions correct.
- Built-in sample: 7 input records -> 5 canonical records (2 merged duplicates).
- Real 6,766-row Unstop export: NOT run because only the collection summary, not the row-level CSV/JSON export, was available.

## Next real-data validation

Run `python dedup.py path/to/unstop_export.csv` or `python dedup.py path/to/unstop_export.json` from this folder. Review `master_events.json` and `uncertain_pairs.json`. Then evaluate against the team's actual labeled-pairs file; do not present the practice-set 100% result as real-world accuracy.


## Added next-step tooling

`validate_dataset.py` now audits a real row-level CSV/JSON export offline. It reports missing required fields, structurally malformed URLs, source/mode/status counts, and exact normalized registration-link duplicate groups. It does not make HTTP requests, confirm a URL is live, or certify robots/terms compliance. Run it when the actual file is available:

```powershell
python validate_dataset.py "C:/path/to/unstop_export.json" --out-dir unstop_audit_output
```

The real 6,766-row export is still not present in this working session, so the script has only been tested with synthetic mini-data.
