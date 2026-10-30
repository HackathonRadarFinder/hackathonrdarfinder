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



## Latest Local Verification

Run date: 2026-10-21  
Environment: Windows PowerShell, Python 3.14.6, project virtual environment.

| Test | Actual result | Status |
|---|---|---|
| Python syntax compilation (`py_compile`) | No output or errors for the six requested Python files | PASS |
| Included 20-pair evaluation set | 20 pairs evaluated; 18 correct predictions; 90.00% accuracy | PASS (practice dataset only) |
| Automated unit suite (`test_module24.py`) | Collection failed: `ImportError: cannot import name 'SAMPLE' from 'dedup'`. No tests executed. | BLOCKED |
| Dataset validator (`validate_dataset.py --help`) | Import failed because `dedup.py` does not provide the imported `load` function. | BLOCKED |

### Notes on the latest run

- The evaluation script initially reported an empty CSV header because `labeled_pairs_20.csv` started with a blank line. After removing the leading blank line, evaluation completed successfully.
- The 90.00% result applies only to the included 20 example.com practice pairs. It does not establish real-world deduplication accuracy.
- The unit-test and dataset-validator import errors require investigation. No changes to the core deduplication implementation were made as part of these checks.
- Syntax compilation confirms that the files parse; it does not prove that their functions work correctly.



## Confirmed Test Compatibility Issues

During local verification, the automated test suite could not be collected because `test_module24.py` imports names that are not available in the current module implementation.

Confirmed mismatches:

1. `test_module24.py` imports `SAMPLE`, `map_record`, `compare`, `cluster`, `merge_group`, and `same_location` from `dedup.py`. These names are not defined in the current `dedup.py`, which provides functions including `normalize_text`, `normalize_link`, `similarity`, `dates_match`, `are_duplicates`, and `find_duplicates`.
2. The test file imports `read_events` from `integrate_pipeline.py`, but that file is absent from the Module 2.4 directory.
3. The tests import `save_master` from `master_db.py`, but the current file instead defines `load_events`, `save_events`, `merge_events`, and `update_master_db`.
4. `validate_dataset.py` imports `load` from `dedup.py`, but that function is not defined there.

**Impact:** The existing automated test suite and dataset validator cannot run successfully against the current module interfaces. These checks remain blocked until the test and implementation interfaces are aligned.

**Recommended follow-up:** Confirm with the module owner whether the test file and validator target an older implementation or whether the missing functions and pipeline module are intended to be part of the current design. Keep the core deduplication implementation unchanged until the owner confirms the expected interface.
