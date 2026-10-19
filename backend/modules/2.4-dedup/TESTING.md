# Module 2.4 Testing Report

Run date: 2026-10-16
Scope: local package tests only. The real 6,766-row Unstop export and the team's final shared schema were not available.

| Test ID | Scenario | Expected result | Actual result | Status |
|---|---|---|---|---|
| T01 | Python syntax compilation | All module files compile | Passed | PASS |
| T02 | Automated unit suite | All tests pass | 17/17 passed | PASS |
| T03 | Included 20-pair evaluation set | Predictions match labels | 20/20 correct; example.com practice pairs only | PASS (practice only) |
| T04 | Synthetic scale smoke test | Merge 30 known exact-link duplicates from 6,796 inputs | 6,766 canonical records; 30 merged; 0 uncertain; ~2.89 sec | PASS (synthetic only) |
| T05 | Built-in sample | 7 records, 2 duplicate merges | 5 canonical records | PASS |
| T06 | Module 2.3-style integration smoke | 3 input records, 1 duplicate merge | 2 canonical events | PASS |
| T07 | SQLite provenance/idempotency | Preserve source links; rerun does not duplicate canonical rows | Passed | PASS |
| T08 | SQLite additive migration | Add missing metadata columns without losing existing rows | Passed | PASS |
| T09 | URL normalization | Ignore tracking parameters and trailing slash variations | Passed | PASS |
| T10 | Missing location evidence | Two blank locations must not alone imply a match | Passed | PASS |
| T11 | Year/organizer guardrails | Clearly different year or organizer should not merge | Passed | PASS |
| T12 | Unstop field preservation | Preserve supported date, status, mode, prize and source metadata | Unit test passed | PASS (fixture only) |

## Issues / limitations

1. Real-data testing is BLOCKED until the row-level Unstop CSV/JSON export is supplied. Summary counts alone cannot establish duplicate precision/recall or actual field completeness.
2. Module 2.3 compatibility is only a local smoke test against the documented/assumed shape. Foundation Team must confirm the final shared schema.
3. The 20/20 labeled-pair score is not real-world accuracy: the included set uses example.com practice records.
4. The synthetic 6,796-row test is a scale smoke test, not the actual Unstop dataset.
5. Live URL, robots.txt and terms-of-service checks are not performed by this package's structural URL audit.
6. GitHub remote branch/PR status is not verified or changed by this run.

## Required follow-up

- Obtain the actual Unstop export and run `python dedup.py <file.csv-or-json>`; review `master_events.json`, `uncertain_pairs.json`, and dataset audit output.
- Obtain labeled duplicate/non-duplicate pairs from independent real listings and report precision, recall, F1, and uncertain/manual-review count.
- Get Foundation Team approval for shared field/table contract.
- Confirm target branch with Bhumika; current instruction recorded by the user was to use `develop`, not `main`. Commit/push and PR creation still require GitHub account access.
