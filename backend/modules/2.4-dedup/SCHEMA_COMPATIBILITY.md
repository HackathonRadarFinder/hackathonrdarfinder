# Module 2.3 → Module 2.4 schema compatibility

This mapping is based on the available Module 2.3 project documentation. It is a local compatibility check, **not final confirmation from the Foundation Team**.

| Module 2.3 canonical field | Module 2.4 handling |
|---|---|
| `title` | Required for matching and preserved in canonical output |
| `organizer` | Preserved and used as supporting match evidence |
| `description` | Preserved; longest non-empty description selected within a duplicate group |
| `start_date` | Normalized to `YYYY-MM-DD`; used in match rules |
| `end_date` | Normalized and preserved |
| `location` | Preserved and used as supporting match evidence |
| `mode` | Preserved |
| `registration_link` | Normalized for equality; original value retained |
| `prize` | Preserved; highest numeric value selected when merging |
| `tags` | Accepts arrays or comma-separated values; merged case-insensitively |
| `source_id` | Preserved in source IDs/provenance; stable per source listing |
| `source_name` | Accepted as source alias and emitted on canonical record |
| `status` | Preserved as received; source status vocabulary is not forcibly rewritten |

Extra Module 2.4 fields include `canonical_event_id`, `source_ids`, `provenance`, and `registration_deadline`. The local SQLite adapter also stores provenance in `event_source_links` and adds event metadata columns. The shared database owner must approve the final table/field contract before deployment.

## Verification
- A unit test checks `source_name`, `source_id`, and tag preservation in the canonical JSON object.
- A migration test checks additive SQLite columns for metadata without dropping prior rows.
- Full unit suite and labeled-pair evaluation results are recorded in `VERIFICATION.txt`.
