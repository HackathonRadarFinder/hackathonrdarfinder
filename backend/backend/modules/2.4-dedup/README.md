# Module 2.4: Deduplication, Entity Resolution & Provenance

Finds the same event listed on different sites (Unstop, Devfolio, Meetup, aggregators), merges
them into one canonical event, keeps the source URLs as proof, and saves the result to a master database.

## How it works
1. **Level 1 (exact):** same `registration_link` after cleaning the URL (no `www`, trailing `/`, `utm_` params).
   Also the same numeric source ID in both URLs (aggregators reuse the original site's ID) with a similar title.
2. **Level 2 (fuzzy):** title similarity (rapidfuzz) + start date within 2 days + same location + organizer check.
   - similarity >= 80, date and location match -> Duplicate
   - similarity >= 65 and dates within 7 days -> Uncertain (manual review)
   - otherwise -> Not duplicate
   - different year in the title, or clearly different organizers -> Not duplicate
3. **Merge:** duplicates are grouped (union-find) into one record with a `canonical_event_id`; best title, description and prize are kept.
4. **Provenance:** every source listing keeps its `source`, `source_id`, `source_url` and the dates it was seen.
5. **Master DB:** saved to SQLite (`canonical_events`, `event_source_links`). Re-running does not create duplicates.

## Setup
```
pip install -r requirements.txt
```

## Run
```
python dedup.py                 # built-in sample data
python dedup.py events.csv      # your own CSV or JSON
python dedup.py events.csv --db # also save to master_events.db
python evaluate.py labeled_pairs_20.csv   # check the rules against labeled pairs
```
Outputs: `master_events.json`, `uncertain_pairs.json`, `master_events.db`.

## Input format
CSV or JSON with: source, source_id, source_url, title, organizer, start_date, location,
registration_link, description, prize. Other field names (name, date_start, url, host, ...) are mapped
through `FIELD_MAP` at the top of `dedup.py`; dates like `27-01-2026` are converted to `2026-01-27`.

## Files
- `dedup.py` matching, clustering, merging
- `master_db.py` saves canonical events + provenance to SQLite
- `evaluate.py` tests the rules on `labeled_pairs_20.csv`
- `labeled_pairs_20.csv` 20 labeled pairs (`data_type` = real or practice)

## Status and limits
- 14 of the 20 labeled pairs are from real listings, 6 are practice pairs; accuracy is 19/19 on the non-uncertain pairs.
- Waiting on the Module 2.3 output format and the Foundation Team's DB schema; the DB schema here is an assumption.
