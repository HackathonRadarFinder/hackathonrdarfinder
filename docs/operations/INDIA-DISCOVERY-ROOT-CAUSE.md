# Discovery audit before implementation

Baseline: c71df5672626cb0bcb27a86a24f2e2da95a696a5; 2026-10-19.

The five-event catalog is an intentionally bounded reviewed snapshot. No
production collection failure was established. `collect_source` supports only
`curated-v1` and the single governed Unstop JSON endpoint. There is no college
directory, general page/feed/sitemap parser, or announcement review queue.

The worker is inert without `DISCOVERY_ENABLED=true`. Live collection additionally
requires `--allow-live`, enabled/due source configuration, an unexpired reviewed
policy with `terms_permit=true`, and transport/robots approval. Registering a
source never starts collection. Sources default to disabled; missing permission
is not a configuration defect to bypass. Demo scheduling only rereads the local
five-record snapshot. Failures are recorded with a safe generic error, and a
crashed writer deliberately leaves a lock for operator review. No live source
approval, running nationwide worker or failed real ingestion was supplied.

Existing strengths to preserve: bounded SSRF-resistant HTTP transport, robots,
rate limits/retry, raw-document storage, atomic validation/ingestion, durable
writer lock, URL/source deduplication, immutable versions and observation evidence.

Directory research found official AISHE and UGC listings. AISHE's published
website policy requires permission for reproduction/reuse beyond download:
https://aishe.gov.in/website-policies/ . Its directory is at
https://dashboard.aishe.gov.in/hedirectory . UGC publishes listings at
https://www.ugc.gov.in/universitydetails/university . Public access alone is not
recorded as collection/reuse approval. No nationwide export is imported and no
institution website is guessed from search results. Approved exports and source
permissions are required for real pilot collection. Implementation and offline
tests can proceed independently of that external approval.
