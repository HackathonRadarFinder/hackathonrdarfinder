# External items required before calling team integration complete

Local implementation, schema-adapter work, 17 unit tests, labeled-practice evaluation, and a synthetic scale smoke test have been run. These external items remain unverified and must not be represented as complete:

1. **Actual Unstop export:** only the collection summary (6,766 total; 253 open; 6,513 closed/past; 5,017 with prize) was available. The row-level CSV/JSON is needed for actual field-level audit, real duplicate counts, and real-data behavior.
2. **Foundation Team confirmation:** `SCHEMA_COMPATIBILITY.md` maps the available Module 2.3 canonical fields. The team still must confirm the final shared database/table contract.
3. **GitHub `develop` branch:** no authenticated GitHub write capability was available in this workspace. No remote commit or pull request is claimed. Apply/review the package in `backend/modules/2.4-dedup` on `develop` after repository access is connected.
4. **Live policy checks:** the local dataset audit checks URL structure only; it does not fetch live pages or independently verify robots.txt/terms compliance.

The included `labeled_pairs_20.csv` was transcribed from the available repository preview and contains `example.com` practice records. Its 20/20 score is only on this small practice set, not evidence of real-world accuracy.
