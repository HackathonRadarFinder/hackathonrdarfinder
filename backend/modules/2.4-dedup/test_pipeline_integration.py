"""End-to-end tests for Module 2.3 JSON -> Module 2.4 outputs and SQLite."""
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from integrate_pipeline import read_events, run_pipeline


class PipelineIntegrationTests(unittest.TestCase):
    def test_valid_events_flow_to_json_and_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "module_2_3" / "output"
            incoming.mkdir(parents=True)
            (incoming / "valid_events.json").write_text(json.dumps([
                {"source": "Unstop", "source_id": "u-101", "source_name": "Unstop",
                 "title": "AI Hackathon", "organizer": "Tech Club", "start_date": "2026-11-10",
                 "location": "Online", "registration_link": "https://example.test/register?utm_source=a",
                 "tags": ["AI"], "source_url": "https://unstop.com/event/101"},
                {"source": "Other", "source_id": "o-101", "source_name": "Other",
                 "title": "AI Hackathon", "organizer": "Tech Club", "start_date": "2026-11-10",
                 "location": "Online", "registration_link": "https://example.test/register",
                 "tags": ["AI", "Python"], "source_url": "https://other.test/event/101"}
            ]), encoding="utf-8")
            (incoming / "expired_events.json").write_text(json.dumps([
                {"source": "Unstop", "source_id": "expired-1", "title": "Expired event",
                 "start_date": "2025-01-01", "registration_link": "https://expired.test/1"}
            ]), encoding="utf-8")

            output = root / "out"
            db = root / "master.db"
            result = run_pipeline(incoming, output, db)

            self.assertEqual(result["input"], 2)
            self.assertEqual(result["canonical"], 1)
            self.assertEqual(result["duplicates_merged"], 1)
            self.assertTrue((output / "master_events.json").exists())
            self.assertTrue((output / "uncertain_pairs.json").exists())
            master = json.loads((output / "master_events.json").read_text(encoding="utf-8"))
            self.assertEqual(len(master), 1)
            self.assertEqual(len(master[0]["provenance"]), 2)

            con = sqlite3.connect(db)
            try:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0], 1)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM event_source_links").fetchone()[0], 2)
            finally:
                con.close()

    def test_expired_events_are_excluded_unless_flag_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "input"
            incoming.mkdir()
            (incoming / "valid_events.json").write_text(json.dumps([
                {"source": "Fixture", "source_id": "v-1", "title": "Valid event", "start_date": "2026-11-10"}
            ]), encoding="utf-8")
            (incoming / "expired_events.json").write_text(json.dumps([
                {"source": "Fixture", "source_id": "e-1", "title": "Expired event", "start_date": "2025-01-01"}
            ]), encoding="utf-8")
            result = run_pipeline(incoming, root / "out", root / "master.db", include_expired=False)
            self.assertEqual(result["input"], 1)
            included = run_pipeline(incoming, root / "out", root / "master.db", include_expired=True)
            self.assertEqual(included["input"], 2)

    def test_reader_rejects_non_object_list_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.json"
            path.write_text(json.dumps(["not an event object"]), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_events(path)

    def test_reader_supports_wrapped_events_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.json"
            path.write_text(json.dumps({"events": [{"title": "Wrapped event"}]}), encoding="utf-8")
            self.assertEqual(read_events(path), [{"title": "Wrapped event"}])

    def test_rerun_is_idempotent_for_source_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "input"
            incoming.mkdir()
            (incoming / "valid_events.json").write_text(json.dumps([
                {"source": "Unstop", "source_id": "idem-1", "source_name": "Unstop",
                 "title": "AI Hackathon", "organizer": "Tech Club", "start_date": "2026-11-10",
                 "location": "Online", "registration_link": "https://example.test/idem"}
            ]), encoding="utf-8")
            db = root / "master.db"
            out = root / "out"
            first = run_pipeline(incoming, out, db)
            second = run_pipeline(incoming, out, db)
            self.assertEqual(first["canonical"], 1)
            self.assertEqual(second["canonical"], 1)
            con = sqlite3.connect(db)
            try:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0], 1)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM event_source_links").fetchone()[0], 1)
            finally:
                con.close()

    def test_missing_required_valid_input_is_not_silent_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                run_pipeline(root / "missing-input", root / "out", root / "master.db")

    def test_cross_platform_editions_keep_schema_and_persisted_ids_on_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                {"platform": "Unstop", "event_id": "shared-42", "event_name": "Buildathon 2026",
                 "organiser": "Tech Club", "date_start": "2026-11-10", "date_end": "2026-11-12",
                 "last_date_to_register": "2026-11-09", "delivery_mode": "Online",
                 "event_status": "upcoming", "tags": ["AI"], "city": "Delhi",
                 "apply_link": "https://example.test/annual", "event_url": "https://unstop.com/event/42"},
                {"platform": "Devfolio", "event_id": "shared-42", "event_name": "Buildathon 2027",
                 "organiser": "Tech Club", "date_start": "2027-11-10", "date_end": "2027-11-12",
                 "last_date_to_register": "2027-11-09", "delivery_mode": "Online",
                 "event_status": "upcoming", "tags": ["Python"], "city": "Delhi",
                 "apply_link": "https://example.test/annual", "event_url": "https://devfolio.co/event/42"},
            ]
            (root / "valid_events.json").write_text(json.dumps(rows), encoding="utf-8")
            first = run_pipeline(root, root / "out", root / "master.db")
            exported = json.loads((root / "out/master_events.json").read_text(encoding="utf-8"))
            self.assertEqual(first["canonical"], 2)
            self.assertEqual({event["end_date"] for event in exported}, {"2026-11-12", "2027-11-12"})
            self.assertEqual({event["registration_deadline"] for event in exported}, {"2026-11-09", "2027-11-09"})
            self.assertTrue(all(event["mode"] == "Online" and event["status"] == "upcoming" for event in exported))
            ids = {event["title"]: event["canonical_event_id"] for event in exported}
            rerun = run_pipeline(root, root / "out", root / "master.db")
            self.assertEqual(rerun["stats"]["total"], 2)
            repeated = json.loads((root / "out/master_events.json").read_text(encoding="utf-8"))
            self.assertEqual({event["title"]: event["canonical_event_id"] for event in repeated}, ids)
            with closing(sqlite3.connect(root / "master.db")) as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM event_source_links").fetchone()[0], 2)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM event_versions").fetchone()[0], 2)
                self.assertEqual(set(con.execute("SELECT canonical_event_id FROM canonical_events")), {(value,) for value in ids.values()})

    def test_conflicting_persistence_preserves_previous_json_and_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {"source": "Unstop", "source_id": "annual-1", "title": "Buildathon 2026",
                   "organizer": "Tech Club", "start_date": "2026-11-10", "location": "Online",
                   "registration_link": "https://example.test/annual"}
            source = root / "valid_events.json"
            source.write_text(json.dumps([row]), encoding="utf-8")
            run_pipeline(root, root / "out", root / "master.db")
            before = {name: (root / "out" / name).read_bytes() for name in ("master_events.json", "uncertain_pairs.json")}
            row.update(title="Buildathon 2027", start_date="2027-11-10")
            source.write_text(json.dumps([row]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting edition"):
                run_pipeline(root, root / "out", root / "master.db")
            for name, expected in before.items():
                self.assertEqual((root / "out" / name).read_bytes(), expected)
            with closing(sqlite3.connect(root / "master.db")) as con:
                self.assertEqual(con.execute("SELECT title,start_date FROM canonical_events").fetchall(), [("Buildathon 2026", "2026-11-10")])
                self.assertEqual(con.execute("SELECT COUNT(*) FROM event_versions").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
