"""Offline smoke tests for Module 2.4. Run: python -m unittest -v"""
import json
import tempfile
import unittest
from pathlib import Path
from dedup import SAMPLE, map_record, compare, cluster, merge_group, normalize_link, same_location
from integrate_pipeline import read_events
from master_db import save_master

class DedupTests(unittest.TestCase):
    def test_sample_cluster_merges_two_pairs(self):
        events=[map_record(r,i) for i,r in enumerate(SAMPLE)]
        groups, uncertain=cluster(events)
        self.assertEqual(len(events),7)
        self.assertEqual(len(groups),5)
        self.assertEqual(len(events)-len(groups),2)

    def test_same_registration_url_is_duplicate(self):
        a={"title":"Event A","organizer":"Org","start_date":"2026-01-01","location":"Online","registration_link":"https://x.test/register?utm_source=a"}
        b={"title":"Different wording","organizer":"Org","start_date":"2026-01-01","location":"Online","registration_link":"https://x.test/register"}
        self.assertEqual(compare(a,b)[0],"duplicate")

    def test_malformed_port_does_not_crash_normalization(self):
        self.assertEqual(normalize_link("https://example.test:bad/register"), "example.test/register")

    def test_tracking_parameters_and_slash_normalized(self):
        self.assertEqual(
            normalize_link("https://www.example.test/register/?utm_source=x&fbclid=abc"),
            normalize_link("http://example.test/register")
        )

    def test_missing_locations_are_not_equal_evidence(self):
        self.assertFalse(same_location("", ""))
        a={"title":"AI Hackathon","organizer":"Org","start_date":"2026-01-01","location":"","registration_link":"https://a.test/1"}
        b={"title":"AI Hackathon","organizer":"Org","start_date":"2026-01-02","location":"","registration_link":"https://b.test/2"}
        self.assertNotEqual(compare(a,b)[0], "duplicate")

    def test_iso_timestamp_and_unstop_fields_preserved(self):
        rec=map_record({"source_name":"Unstop","event_id":"abc","event_name":"AI Sprint",
                        "start_date":"2026-10-20T10:00:00+05:30","end_date":"2026-10-21T18:00:00+05:30",
                        "registration_deadline":"2026-10-18T23:59:00+05:30","mode":"Online","status":"Open"}, 0)
        self.assertEqual(rec["start_date"], "2026-10-20")
        self.assertEqual(rec["end_date"], "2026-10-21")
        self.assertEqual(rec["registration_deadline"], "2026-10-18")
        self.assertEqual(rec["mode"], "Online")
        self.assertEqual(rec["status"], "Open")

    def test_module23_canonical_schema_tags_and_source_fields(self):
        raw = {"title": "AI Hackathon", "source_id": "unstop-123", "source_name": "Unstop",
               "start_date": "2026-11-10", "tags": ["AI", "Technology", "AI"]}
        rec = map_record(raw, 0)
        self.assertEqual(rec["source"], "Unstop")
        self.assertEqual(rec["tags"], ["AI", "Technology"])
        canonical = merge_group([rec], 1)
        self.assertEqual(canonical["source_id"], "unstop-123")
        self.assertEqual(canonical["source_name"], "Unstop")
        self.assertEqual(canonical["tags"], ["AI", "Technology"])

    def test_title_synonym_expo_exhibition(self):
        a={"title":"AI Expo","organizer":"Tech Club","start_date":"2026-12-02","location":"Chennai","registration_link":"https://a.test/1"}
        b={"title":"AI Exhibition","organizer":"Tech Club","start_date":"2026-12-03","location":"Chennai","registration_link":"https://b.test/1"}
        self.assertEqual(compare(a,b)[0], "duplicate")

    def test_generic_shared_title_words_do_not_merge_different_events(self):
        a={"title":"Unique Event Alpha","organizer":"Organizer Alpha","start_date":"2026-11-10","location":"Hyderabad","registration_link":"https://a.test/1"}
        b={"title":"Unique Event Beta","organizer":"Organizer Beta","start_date":"2026-11-10","location":"Hyderabad","registration_link":"https://b.test/1"}
        self.assertEqual(compare(a,b)[0], "not_duplicate")

    def test_generic_organizer_suffix_does_not_hide_mismatch(self):
        a={"title":"Cloud Summit","organizer":"Cloud Org","start_date":"2026-11-22","location":"Chennai","registration_link":"https://a.test/1"}
        b={"title":"Design Contest","organizer":"Design Org","start_date":"2026-11-25","location":"Chennai","registration_link":"https://b.test/1"}
        self.assertEqual(compare(a,b)[0], "not_duplicate")

    def test_different_year_is_not_duplicate(self):
        a={"title":"HackFest 2025","organizer":"TechClub","start_date":"2025-03-15","location":"Bengaluru","registration_link":"https://x.test/2025"}
        b={"title":"HackFest 2026","organizer":"TechClub","start_date":"2026-03-14","location":"Bengaluru","registration_link":"https://x.test/2026"}
        self.assertEqual(compare(a,b)[0],"not_duplicate")

    def test_pipeline_json_reader(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"valid_events.json"
            p.write_text(json.dumps([{"title":"One"}]),encoding="utf-8")
            self.assertEqual(len(read_events(p)),1)

    def test_json_api_wrapper_reader(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"unstop_export.json"
            p.write_text(json.dumps({"data":{"results":[{"event_name":"API Hackathon","start_date":"2026-10-15"}]}}),encoding="utf-8")
            from dedup import load
            rows=load(str(p))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]["title"],"API Hackathon")

    def test_sqlite_saves_provenance(self):
        events=[map_record(r,i) for i,r in enumerate(SAMPLE[:2])]
        groups,_=cluster(events)
        master=[merge_group(g,101+i) for i,g in enumerate(groups)]
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"test.db"
            stats=save_master(master,db_path=str(db))
            self.assertEqual(stats["total"],1)
            self.assertEqual(stats["new"],1)


    def test_sqlite_persists_tags_and_source_name(self):
        import sqlite3, json
        rec = map_record({"title":"Schema Event", "source_id":"schema-1", "source_name":"Unstop",
                          "start_date":"2026-11-10", "tags":["AI", "Python"]}, 0)
        canonical = merge_group([rec], 1)
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "schema.db"
            save_master([canonical], db_path=str(db))
            con = sqlite3.connect(db)
            row = con.execute("SELECT tags, source_name FROM canonical_events").fetchone()
            con.close()
        self.assertEqual(json.loads(row[0]), ["AI", "Python"])
        self.assertEqual(row[1], "Unstop")

    def test_sqlite_preserves_unstop_metadata_and_migrates_old_db(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "old.db"
            con = sqlite3.connect(db)
            con.executescript("""CREATE TABLE canonical_events (
                canonical_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, organizer TEXT, start_date TEXT, location TEXT,
                registration_link TEXT, description TEXT, prize TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE event_source_links (
                link_id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_event_id INTEGER NOT NULL REFERENCES canonical_events(canonical_event_id),
                source TEXT, source_id TEXT NOT NULL UNIQUE, source_url TEXT,
                first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);""")
            con.commit(); con.close()
            event = {
                "title":"Metadata Test", "organizer":"Club", "start_date":"2026-10-20",
                "end_date":"2026-10-21", "registration_deadline":"2026-10-18",
                "mode":"Online", "status":"Open", "location":"Online",
                "registration_link":"https://example.test/apply", "description":"",
                "prize":"", "provenance":[{"source":"Unstop", "source_id":"u-123", "url":"https://unstop.com/event/123"}]
            }
            save_master([event], db_path=str(db))
            con = sqlite3.connect(db)
            row = con.execute("SELECT end_date, registration_deadline, mode, status, tags, source_name FROM canonical_events").fetchone()
            con.close()
            self.assertEqual(row, ("2026-10-21", "2026-10-18", "Online", "Open", "[]", ""))

    def test_dataset_audit_counts_and_duplicate_links(self):
        from validate_dataset import audit
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"mini_unstop.json"
            p.write_text(json.dumps([                {"source":"unstop","source_id":"u1","title":"AI Hackathon","organizer":"Club","start_date":"2026-10-20","end_date":"2026-10-21","registration_deadline":"2026-10-18","mode":"Online","registration_link":"https://example.test/register?utm_source=x","source_url":"https://unstop.com/event/1","prize":"10000"},                {"source":"unstop","source_id":"u2","title":"AI Hackathon","organizer":"Club","start_date":"2026-10-20","end_date":"2026-10-21","registration_deadline":"2026-10-18","mode":"Online","registration_link":"https://example.test/register","source_url":"https://unstop.com/event/2","prize":""}            ]),encoding="utf-8")
            report, groups=audit(p)
            self.assertEqual(report["total_records"],2)
            self.assertEqual(report["exact_normalized_registration_link_duplicate_groups"],1)
            self.assertEqual(len(groups),1)

if __name__=="__main__": unittest.main()
