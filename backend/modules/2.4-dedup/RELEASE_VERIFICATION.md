# 26 October 2026 release integration

Integrated the canonical API and runnable pipeline from PR #95 (commit
`6da1317eaa0ada4e5312eaed77ce959aff690fd6`), then repaired release regressions:

- Conflicting edition years/dates take precedence over a reused registration URL.
- Numeric URL suffixes are scoped to a host. Incompatible cluster members require review.
- SQLite provenance identity is `(source, source_id)`, with a preserving migration
  for the older globally unique source-ID table.
- Later batches can resolve a new listing to an existing event. Ambiguous existing
  matches and conflicting reused source identities raise errors for manual review.
- Canonical metadata/provenance changes append snapshots to `event_versions`;
  unchanged reruns do not create a new version.
- Production pipeline inputs require titles, real source names and stable source IDs;
  invalid dates and malformed structures fail, and empty input explicitly reports a skip.
- JSON output uses persisted canonical IDs and is written after successful persistence.
- The standalone CI workflow installs the pinned rapidfuzz dependency and tests the module.

Run from this directory:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -v
python evaluate.py
```

All 33 discovered module tests pass with Python 3.12 and rapidfuzz. Compilation passes.
The 20 labeled examples are illustrative (`example.com` URLs), not an independent
real-world accuracy benchmark. The run returned 20 correct, zero false positives,
and zero false negatives. This does not establish production entity-resolution accuracy.
Foundation Team schema confirmation and genuine reviewed labeled data remain external
acceptance items from Issue #91. No collection permissions are implied.

This module's disposable SQLite store is distinct from the application PostgreSQL
catalog. Publication must pass the application's existing human review/import flow;
running this module does not itself publish events to the web catalog.
