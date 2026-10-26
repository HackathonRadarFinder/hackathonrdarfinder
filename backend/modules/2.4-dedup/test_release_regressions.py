"""Disposable, synthetic release regressions; no production data or collection."""
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from dedup import cluster, compare, map_record, merge_group
from integrate_pipeline import read_events, run_pipeline
from master_db import save_master


def event(**changes):
    raw = dict(title="Buildathon 2026", organizer="Tech Club", start_date="2026-11-12",
               location="Online", source="alpha", source_id="1",
               registration_link="https://example.test/apply")
    raw.update(changes)
    return map_record(raw, 0)


class ReleaseRegressions(unittest.TestCase):
    def test_annual_editions_reusing_url_stay_separate(self):
        self.assertEqual(compare(event(), event(title="Buildathon 2027", start_date="2027-11-12"))[0], "not_duplicate")
        self.assertEqual(compare(event(title="Buildathon"), event(title="Buildathon", start_date="2027-11-12"))[0], "not_duplicate")

    def test_numeric_ids_are_scoped_to_host(self):
        a = event(registration_link="https://a.test/event-123456", start_date="")
        b = event(registration_link="https://b.test/event-123456", start_date="")
        self.assertNotEqual(compare(a, b)[0], "duplicate")

    def test_missing_date_cannot_bridge_editions(self):
        rows = [event(title="Buildathon", start_date="2026-11-12"),
                event(title="Buildathon", start_date=""),
                event(title="Buildathon", start_date="2027-11-12")]
        groups, review = cluster(rows)
        self.assertEqual(len(groups), 2)
        self.assertTrue(review)

    def test_scoped_source_identity_cross_batch_and_history(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "master.db"
            first = merge_group([event()], 101)
            save_master([first], db)
            other = merge_group([event(source="beta", source_id="1", description="More details")], 101)
            self.assertEqual(save_master([other], db)["total"], 1)
            save_master([other], db)
            separate = merge_group([event(source="gamma", source_id="1", title="Separate", start_date="2027-01-01")], 101)
            self.assertEqual(save_master([separate], db)["total"], 2)
            with closing(sqlite3.connect(db)) as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM event_source_links").fetchone()[0], 3)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM event_versions WHERE canonical_event_id=?", (first["canonical_event_id"],)).fetchone()[0], 2)

    def test_conflicting_source_reuse_rolls_back(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "master.db"
            save_master([merge_group([event()], 1)], db)
            with self.assertRaisesRegex(ValueError, "conflicting edition"):
                save_master([merge_group([event(start_date="2027-11-12", title="Buildathon 2027")], 1)], db)
            with closing(sqlite3.connect(db)) as con:
                self.assertEqual(con.execute("SELECT start_date FROM canonical_events").fetchone()[0], "2026-11-12")

    def test_invalid_pipeline_records_never_write_database(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for row in ({}, {"title": "Missing identity"},
                        {"title": "Bad date", "source": "alpha", "source_id": "1", "start_date": "invalid"},
                        {"title": "Bad alias date", "source": "alpha", "source_id": "1", "date_start": "invalid"},
                        {"title": "Reversed dates", "source": "alpha", "source_id": "1", "start_date": "2026-11-10", "end_date": "2026-11-09"}):
                (root / "valid_events.json").write_text(json.dumps([row]), encoding="utf-8")
                with self.assertRaises(ValueError):
                    run_pipeline(root, root / "out", root / "master.db")
                self.assertFalse((root / "master.db").exists())

    def test_empty_pipeline_is_explicitly_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "valid_events.json").write_text("[]", encoding="utf-8")
            result = run_pipeline(root, root / "out", root / "master.db")
            self.assertIn("skipped", result["message"])
            self.assertFalse((root / "master.db").exists())

    def test_missing_malformed_and_non_object_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "valid_events.json"
            with self.assertRaises(FileNotFoundError):
                read_events(path)
            for contents in ("{", "null", "[1]", '{"events":"wrong"}'):
                path.write_text(contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_events(path)

    def test_persisted_canonical_ids_are_exported(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "valid_events.json"
            path.write_text(json.dumps([event()]), encoding="utf-8")
            run_pipeline(root, root / "out", root / "master.db")
            first = json.loads((root / "out/master_events.json").read_text())[0]["canonical_event_id"]
            path.write_text(json.dumps([event(source_id="2", title="Separate", start_date="2027-01-01")]), encoding="utf-8")
            run_pipeline(root, root / "out", root / "master.db")
            second = json.loads((root / "out/master_events.json").read_text())[0]["canonical_event_id"]
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
