# Deduplication and Entity Resolution

## Objective

The objective of this module is to identify duplicate hackathon events from different sources and maintain a clean master database without storing duplicate records.

## Features

- **Exact Registration Link Matching:** Identifies duplicate events by comparing their registration links.
- **Fuzzy Title Matching:** Compares event titles using an 80% similarity threshold.
- **Organizer Comparison:** Checks whether the events have the same organizer.
- **Date Comparison:** Allows a difference of up to two days between event start dates.
- **Location Comparison:** Checks whether the events take place at the same location.
- **Duplicate Detection:** Identifies duplicate event records using the above conditions.
- **Entity Resolution:** Combines information from duplicate records into a canonical event record.
- **Provenance Tracking:** Maintains source information and source IDs for merged events.
- **Evaluation:** Measures duplicate detection accuracy using labeled test data.

## Files

- `dedup.py` - Contains functions to normalize event details, compare event records, and identify duplicates.
- `evaluate.py` - Evaluates duplicate detection predictions against labeled test data.
- `master_db.py` - Loads, saves, and updates the master database and merges duplicate event information.
- `labeled_pairs_20.csv` - Contains 20 sample event pairs with labels for testing duplicate detection.
- `requirements.txt` - Lists the dependencies required by the module.

## Duplicate Detection Logic

The module follows these steps:

1. Normalize registration links and event details.
2. Check whether both events have the same non-empty registration link.
3. If the registration links do not match, compare event titles.
4. Check whether the organizers and locations match.
5. Check whether the event start dates differ by no more than two days.
6. Identify the events as duplicates when the required matching conditions are satisfied.

For fuzzy matching, the title similarity must be greater than 80%, along with matching organizer, date, and location details.

## Entity Resolution and Provenance

When duplicate events are identified, their information is merged into a canonical event record.

The module preserves source IDs and source information so that the origins of the merged event data can be tracked. Missing information in the canonical record can be filled using information from another duplicate record.

## Testing

The file `labeled_pairs_20.csv` contains sample event pairs and their expected duplicate labels.

To evaluate the duplicate detection logic, run the following command from the `2.4-dedup` folder in a Python environment:

```bash
python evaluate.py
```

The evaluation program displays:

- Total number of evaluated pairs
- Number of correct predictions
- Prediction accuracy as a percentage

**Note:** The CSV contains sample testing data. Actual project data should be used for final evaluation when it becomes available. The reported accuracy depends on the matching logic and the test data.

## Dependencies

The module uses Python standard library modules, including `re`, `csv`, `json`, `pathlib`, `difflib`, and `urllib.parse`.

No external Python packages are required for the current implementation.
