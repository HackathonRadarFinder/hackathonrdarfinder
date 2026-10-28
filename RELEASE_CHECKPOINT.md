# Current release checkpoint

PR #100 targets main from release/main-history-bridge-20261029. Verified release head before the raw-storage repair: 034b4716c523a195825d5af6312f6a486160dd5c. Its CI run 40734796936 and Module 2.4 run 40734796812 passed. PR is draft and mergeable; never merge it automatically.

Remote develop: 768302a59b83e832d57541bf433f90c2f8a32ee4. Remote main: d968e3978284b557a255fee5a9051b206ec3a5ea. GitHub comparisons confirm that the bridge preserves both histories and has exactly the develop application files (zero file differences). Local worktree remains on feat/2026-10-28-automated-deployment at 61f6605; do not assume local branch refs are current.

Release-critical repair: Compose used RAW_DATA_DIR, but the organizer collector reads COLLECTOR_RAW_DATA_DIR. Both Compose files now use the correct key inside the persistent collector snapshot volume. A focused regression checks the actual Settings loader and mount. Direct read-only configuration checks pass; no unnecessary image rebuild or full suite was run. New repair CI must pass before owner review/merge.

Verified evidence reused: focused backend 91 passed; institutional/provenance set 30 passed; provider/transport set 14 passed; operations 67 passed; owned PostgreSQL 13 passed; browser 30 checks/22 axe scans; admin release journey 7 checks; college directory/filter browser 5 checks. These overlap. Production Compose scheduler, overlap prevention, interrupted-run recovery, restart persistence and backup/restore passed in an owned disposable stack. Current local readiness and ML suppression endpoints passed again.

Persistent data: 5 events, 3 users, 3 saved items, 1362 institutions across 33 states/UTs; selected-value hashes unchanged. Verified institution/event associations: 0; upcoming verified associations: 0. No guesses/reimport. Collector was healthy and idle with no enabled live source. No new real collection/publication is claimed.

Remaining external requirements: authorized Brabble API key and current source policy; real fact-bound human publication approval; sufficient historical evidence for public ML; owner merge/deployment authorization and production hosting/DNS/private secrets. SMTP is disabled and is not a launch blocker.

Preserve backend/.env, database volumes, generated review evidence and untracked hackathon_radar_scraper/. Also preserve the unrelated untracked accidental terminal-output file; never stage it. Original main history remains reachable as a bridge ancestor.

If local restricted test execution is needed later: automatic approval review failed because usage capacity was exhausted. The rejected elevated preflight/provider test command was not executed; it was not judged unsafe. Do not bypass that approval check. Existing successful exact-release CI supplies broader verification; the new configuration regression must be checked by repair CI.
