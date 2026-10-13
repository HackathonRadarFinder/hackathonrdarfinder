# Phase 2: prediction research and readiness

Discovery was committed with authorization as
`9bc2b2a2260c0aa9f14831e8652449ccfafcdb59`, after matching all 22 files to the
handover inventory, checking credentials/artifacts, reviewing the staged diff
and passing `git diff --cached --check`. The worktree was clean after that commit.
Phase 2 changes are separate, uncommitted work on `feature/automatic-discovery`.
No push, merge, deployment, live scraping or live database modification occurred.

## Available evidence and result

`backend/data/prediction-editions-v1.json` is a derived dataset of **three real
historical Megathon editions**, copied from the existing reviewed source-backed
manifest: 2022-10-22, 2025-10-11 and 2026-10-10. It preserves titles, organizer,
source URLs, descriptions, day precision and original observation timestamps.
Its canonical source-manifest checksum is independently verified. The separate
reviewed edition map identifies Megathon as one series, distinct from HackHarvard
and MIT Policy Hackathon; grouping does not rely on organizer-name similarity.
The full manifest has five editions, including two future confirmed catalog events.

All five source records were observed on **October 13, 2026**. They do not provide
historical point-in-time evidence for earlier forecast dates. Missing 2023/2024
editions are not manufactured. Actual-occurrence outcomes are not confirmed by
this dataset; its labels are source-announced start dates.

Observed Megathon intervals are **1085 and 364 days**, with a mean/median of
724.5 days. All three dates are in October. This describes sparse observations,
not an established annual schedule or a probability distribution. Observed year
gaps are three years and one year, so observed editions are not consecutive.

Real evaluation result: **insufficient_history**, **zero valid held-out editions**,
null MAE, null window coverage and null confidence for every model. No neural
model was trained, saved or promoted. No publication approval exists. Internal
candidate dates may be inspected by researchers, but are uncalibrated comparisons
and never enter the public catalog or event database.

## Implemented evaluation

- Dataset validation checks explicit series/edition identities, source/title/
  organizer consistency, checksums, observed/collected timestamps and edition
  years. Unreviewed sources, duplicate edition identities and conflicting records
  are quarantined. Fixed curated data is checked against its original source
  facts; an imported export cannot backdate it to create fictional evaluation.
- Observation-aware snapshots reuse `ai.discovery_history.as_of`. Features contain
  only earlier editions observed by the forecast cutoff. Target editions, future
  observations, later date revisions and already-announced targets are excluded.
  Future scheduled events do not become training history or outcome labels.
- The existing mean-gap prediction function is compared with median-gap, last-gap
  and seasonal-anniversary baselines. Its heuristic confidence is discarded.
  Calendar overflow and unsupported history suppress candidate generation.
- Default retrospective forecast time is 90 days before each target; explicit
  cutoffs can be supplied. Each model scores at most once per target and predicts
  the next edition, without skipping intervening editions. Lead times and cutoff
  selection are research protocol choices, not accuracy guarantees.
- Optional neural evaluation reuses the existing MLP pipeline and date features.
  Each research fit needs at least 30 earlier available edition labels from the
  same reviewed series. It refits only before the current cutoff, disables random
  early-stopping validation and neither loads nor writes pickle model artifacts.
  Test doubles verify training-time boundaries; they are not model-accuracy evidence.
- Residual windows use only earlier outcome labels available before the forecast.
  At least 30 earlier residuals are required for an empirical 80% residual window;
  at least 20 subsequent scored windows are required for a research coverage report.
  Undercoverage is reported. Temporal residuals do not establish exchangeability
  or calibrated public confidence; confidence remains null and publication false.
- Reports calculate held-out announced-date MAE and date-window coverage. Explicit
  independently reviewed actual-occurrence labels, when supplied, also support
  separate actual-date MAE and coverage. Announced-date windows are not claimed to
  be calibrated actual-occurrence intervals. No negative occurrence labels are
  inferred from a source's silence, so the legacy occurrence classifier is not trained.

## Run offline evaluation

PowerShell from the release worktree:

```powershell
Set-Location 'C:\Users\nakul\OneDrive\Documents\Desktop\hackathonradarfinder\.release-local'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = (Resolve-Path backend).Path
$predictionOutput = Join-Path $env:TEMP ('radar-prediction-' + [guid]::NewGuid().ToString() + '.json')
& '..\backend\.venv\Scripts\python.exe' -B -m workers.evaluate_predictions --input backend/data/prediction-editions-v1.json --output $predictionOutput --neural
```

This command is independent of DATABASE_URL, SECRET_KEY and application settings;
it performs no database connections or network requests. Existing output files
are never overwritten. Omit `--input` to evaluate all five reviewed manifest
records, or pass a version-1 discovery-history export. `--as-of` accepts a UTC
evaluation ceiling (never a future claim); repeat `--cutoff` for explicit forecast
cutoffs. `--neural` requests research fitting only when sufficient real temporal
labels exist; it does not override evidence requirements.

`--actual-outcomes` accepts a separately reviewed JSON list. Each entry requires
an approved `source_url`, `confirmed_actual: true`, a nonblank `review_basis`,
`actual_start_date` and `observed_at`. Occurrence must precede observation,
observation must precede evaluation, and source entries must be unique. This is
an operator-attested offline input, not an automatic verification of source text.
No such real outcome file is currently available; do not invent one.

The output contains source observations, the edition-review checksum, family
patterns, model comparisons, temporal fold evidence, metric sample counts,
calibration status and publication blockers. It contains no account data.

## API and frontend

The existing public `/predictions/catalog` and React prediction cards retain their
eligibility gate; no unsupported forecast is published. New public
`GET /predictions/readiness` returns counts and a reason more evidence is needed,
without candidate dates or confidence scores. React displays that readiness.
`GET /predictions/research` requires a database-backed administrator or
data-scientist role and returns detailed internal evidence and comparisons.
Ordinary accounts and spoofed token roles are denied.

The discovery demo remains at http://127.0.0.1:5176 with backend 8021. Use the
[discovery startup/shutdown instructions](AUTOMATIC-DISCOVERY.md). Backend restart
is required after route changes; demo accounts are disposable. No dependency or
migration change was required for Phase 2. Use the verified Python environment.

## Remaining work before credible public prediction

1. Obtain approved, dated historical observations with reviewed series/edition
   identities and sufficiently complete history. Current source approval restrictions remain.
2. Collect reviewed actual-occurrence outcomes and evaluate enough genuinely
   out-of-time editions. Keep uncertain/censored outcomes explicit.
3. Compare model errors with baselines, assess actual date-window coverage and
   calibration on independent evidence, then obtain model-publication approval.
4. Only after those gates pass, implement approved model promotion/publication.

No production release, accuracy claim or confidence level is supported by the
current evidence. The unavailable states and null metrics are the expected result.

## Phase 2 file inventory

```text
backend/ai/discovery_history.py
backend/ai/temporal_prediction.py
backend/app/api/routes/predictions.py
backend/app/services/curated_validation.py
backend/data/prediction-editions-v1.json
backend/data/prediction-families-v1.json
backend/tests/test_temporal_prediction.py
backend/workers/evaluate_predictions.py
backend/workers/ingest_curated.py
docs/operations/AI-PREDICTION-PHASE2.md
docs/operations/AUTOMATIC-DISCOVERY.md
frontend/src/LivePlatform.jsx
frontend/src/services/apiClient.js
frontend/tests/curated.acceptance.mjs
```

Shared manifest validation was extracted without changing ingestion behavior so
offline prediction work no longer imports database/application configuration.
Discovery history's ORM import is now lazy for the same reason.
