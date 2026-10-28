# Factual review: 28 October 2026

## Scope and evidence boundary

All 25 local pilot candidates were inspected across nine factual fields (225 checks), with public canonical-page access attempted for each. Public search and readable public AMP/organizer pages supplied additional research. No direct source collector, authenticated/private API, anti-bot bypass, registration submission or email was used. Research extracts may be cached; source crawl dates are not observation dates. Relative countdowns were not used to establish deadlines.

Results: 48 primary-supported fields, 9 conflicting fields, 10 indexed leads, 3 explicitly unknown fields and 155 unverified fields. These are AI research findings, not human approval. The six existing source/review files retain their original SHA-256 values, including the approval ledger and acquisition evidence.

## Required review outputs (local, deliberately untracked)

Generated datasets remain under `backend/radar_collector/output/factual-review-20261028/`, as required by the Git exclusion rule:

- `packet/FACTUAL_REVIEW.md`: all 25 candidates with field-by-field claims, corrected proposals, exact evidence links, timestamps and blockers.
- `packet/corrected_worksheet.csv`: 225 rows. Unverified/conflicting values are blank in the proposed-value column. Every human-approval cell is NO.
- `packet/awaiting_human_approval.csv`: BID AND CODE and Hacknauts 2.0. These are factual drafts, not importable approved records.
- `packet/blocked_candidates.csv`: 23 candidates needing further factual decisions.
- `packet/field_review.json`: source acquisition evidence, provider attribution and permission references preserved per record.
- `research_observations.json`, `immutable_input_hashes.json`, `packet/manifest.json`: research input, original-file hashes and reproducibility metadata.
- `historical_research.json`: three retrospective Megathon editions and isolated baseline evaluation, with actual present-day observation times.

These worksheet headers are intentionally rejected by `load_approved`; a shortlist cannot bypass the reviewed-public importer. No newly corrected CSV was promoted to approved status. Existing AI-only `reviewed.csv` still requires a real human approval before persistent application. Today, 25 candidates remain in review files, zero new records were staged to persistent PostgreSQL and zero were published. One existing AI-reviewed record was imported only into disposable SQLite for acceptance and that database was removed.

## Confirmed corrections and unresolved conflicts

- **BID AND CODE:** the public [listing](https://unstop.com/hackathons/bid-and-code-design-frontend-competition-by-acm-university-school-of-information-communication-and-technology-1773221/amp) identifies GGSIPU USICT ACM Student Chapter, an online phase on 29-31 October and an on-campus finale on 2 November. Proposed mode is Hybrid and the finale venue is TnP Room, USIC&T. Dates remain day precision. Registration at 29 October 00:00 IST converts to 28 October 18:30 UTC. The organizer site was inaccessible; cash prize remains unknown in the corrected worksheet.
- **Code Sprint:** its [listing](https://unstop.com/hackathons/code-sprint-university-of-petroleum-energy-studies-upes-dehradun-1770690/amp) supports online building from 15 October to 15 November and a Dehradun finale on 22 November. Preserve the INR 30000 cash-versus-INR 100000 broader reward conflict. The similar Elite Coders listing has a separate ID/organizer; do not merge automatically.
- **Hybrid Micro Mouse:** indexed Alliance University identity does not establish exact event dates. The word Hybrid describes the robotics task and does not independently establish participation mode. Keep the schedule unverified and prioritize the claimed 28 October deadline for human checking.
- **WCC Forge 48:** the [organizer page](https://wecodecoders.in/events/wcc-forge-48) now describes rounds extending through 10 November, unlike earlier 48-hour listing evidence. Its 29 October 23:59 IST cutoff differs from the API claim. Preserve both schedule and deadline conflicts, including changed final-round fee terms.
- **Pinaka CTF:** the [organizer](https://pinakactf.com/) lists an online qualifier and a later NFSU Chennai finale. The worksheet proposes a Hybrid overall range, 31 October-28 November, at day precision. Exact registration cutoff and cash-versus-benefit scope remain conflicting.
- **HAXLR8 3.0:** the [college announcement](https://mitmysore.in/haxlr8-3-0/) supports 6-7 November at MIT Mysore and INR 40000. The current indexed 2 November registration cutoff differs from the prior 30 October claim. Original URL mapping, cutoff and explicit mode need confirmation.
- **Prompts to Profit:** the [listing](https://unstop.com/hackathons/prompts-to-profit-hackathon-amalthea-2026-iit-gandhinagar-1774722/amp) establishes an IIT Gandhinagar first round, followed by online and Gurgaon stages. Do not label the entire series as a single offline Gandhinagar event; overall end date is unknown.
- **Agentic AI / AI Product:** different cached/indexed versions disagree on event dates. Preserve this conflict under each exact listing ID; do not infer currently active availability from a provider deadline.
- **Math-O-Stellar / Sea of Secrets:** indexed descriptions identify a mathematics assessment and CTF respectively. Human scope review is needed; advertised goodies, credits and subscriptions must not become cash totals.
- **Hacknauts 2.0:** the [original page](https://hacknauts26.devfolio.co/) reconfirms Causmic Club, GNDEC Ludhiana, in-person mode and 14-15 November. The 30 October PPT cutoff is not a verified registration cutoff. Cash-only prize stays unknown.

All remaining candidates have individual field-level rows and access notes in the local packet; no unavailable primary page is labeled verified. Brabble attribution remains attached; [API-row reuse terms](https://brabble.ai/docs) do not authorize direct upstream scraping or replace factual human approval.

## Human decisions needed

1. Confirm or reject BID AND CODE and Hacknauts facts, including omitted unknowns and day-only timing. If approved, create an actual dated human attestation bound to the final normalized event digest and precision, preserving the AI identity and provider evidence.
2. Obtain authoritative clarification of WCC, Pinaka, HAXLR8, Agentic AI and AI Product schedule/cutoff conflicts. Never select one conflicting date silently.
3. Clarify Code Sprint versus Elite Coders event identity and cash-versus-benefit claims.
4. Decide whether mathematical contests, CTFs and design competitions belong in the public hackathon scope.
5. For the remaining unavailable fields/pages, provide readable current organizer evidence; blanks are not permission to invent values.

## ML research

Retrospectives independently support Megathon [2022](https://ecell.iiit.ac.in/events/hackathons/megathon-22.html), [2023](https://www.iiit.ac.in/outreach-events/) and [2025](https://blogs.iiit.ac.in/monthly_news/megathon-2025-2/). New notes retain today's acquisition time; their note checksums are explicitly not HTML hashes. They form an isolated three-edition research dataset, not an expanded trusted production manifest. Baseline evaluation has zero valid folds because these observations were unavailable at the historical forecast cutoffs. No MAE/calibration is claimed. The existing production evidence remains five editions, one recurring series and public forecasts disabled.

## Reproduce locally

From `backend`:

```powershell
.venv/Scripts/python.exe -m workers.build_factual_review_packet --candidates radar_collector/output/brabble-pilot/pilot_candidates.csv --observations radar_collector/output/factual-review-20261028/research_observations.json --out radar_collector/output/factual-review-20261028/packet
```

This command reads only local evidence and writes the separate packet; it does not connect to a database or create review approval. The untracked research inputs must be retained locally; generated datasets are intentionally absent from Git.
