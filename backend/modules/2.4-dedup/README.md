
# Deduplication and Entity Resolution

## Objective
To identify duplicate hackathon events and maintain a clean master database.

## Features
- Exact registration link matching
- Fuzzy title matching with 80% similarity threshold
- Organizer, date, and location comparison
- Merge duplicate event information
- Evaluate duplicate detection results

## Files
- `dedup.py` - Detects duplicate events.
- `evaluate.py` - Evaluates predictions.
- `master_db.py` - Manages master event records.
- `labeled_pairs_20.csv` - Sample testing data.
- `requirements.txt` - Lists dependencies.

## Testing
The CSV contains sample data for testing. Actual project data can be used when provided by the team.
