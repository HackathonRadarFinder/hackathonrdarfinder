"""Batch rollback and competing writers use disposable SQLite files only."""
import copy
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from dedup import merge_group
from integrate_pipeline import run_pipeline
from master_db import save_master
from test_release_regressions import event


class AtomicIngestionTests(unittest.TestCase):
    def test_late_conflict_rolls_back_new_records_links_history_and_input_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'master.db'
            original = merge_group([event(description='Approved existing facts')], 101)
            save_master([original], db)
            batch = [merge_group([event(source_id='new', title='Unrelated', start_date='2028-01-01')], 999),
                     merge_group([event(title='Buildathon 2027', start_date='2027-11-12')], 1000)]
            before = copy.deepcopy(batch)
            with self.assertRaisesRegex(ValueError, 'conflicting edition'):
                save_master(batch, db)
            self.assertEqual(batch, before)
            with closing(sqlite3.connect(db)) as connection:
                self.assertEqual(connection.execute('SELECT title,description FROM canonical_events').fetchall(),
                                 [('Buildathon 2026', 'Approved existing facts')])
                for table in ('event_source_links', 'event_versions'):
                    self.assertEqual(connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 1)

    def test_concurrent_first_imports_resolve_cross_source_identity_once(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'master.db'
            ready = Barrier(4)

            def ingest(index):
                item = merge_group([event(source=f'source-{index}', source_id='same-scoped-id')], 101)
                ready.wait(timeout=10)
                save_master([item], db)
                save_master([item], db)
                return item['canonical_event_id']

            with ThreadPoolExecutor(max_workers=4) as executor:
                ids = list(executor.map(ingest, range(4)))
            self.assertEqual(len(set(ids)), 1)
            with closing(sqlite3.connect(db)) as connection:
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM canonical_events').fetchone()[0], 1)
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM event_source_links').fetchone()[0], 4)
                self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_output_replace_failure_restores_both_artifacts_and_rolls_back_db(self):
        import integrate_pipeline
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, db = root / 'valid_events.json', root / 'out', root / 'master.db'
            source.write_text(json.dumps([event()]), encoding='utf-8')
            run_pipeline(root, output, db)
            before = {name: (output / name).read_bytes() for name in ('master_events.json', 'uncertain_pairs.json')}
            source.write_text(json.dumps([event(source_id='2', title='Other', start_date='2028-01-01')]), encoding='utf-8')
            replace = integrate_pipeline.os.replace
            count = 0

            def fail_second(*args):
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError('synthetic output replacement failure')
                return replace(*args)

            with patch.object(integrate_pipeline.os, 'replace', side_effect=fail_second):
                with self.assertRaises(OSError):
                    run_pipeline(root, output, db)
            for name, contents in before.items():
                self.assertEqual((output / name).read_bytes(), contents)
            with closing(sqlite3.connect(db)) as connection:
                self.assertEqual(connection.execute('SELECT title FROM canonical_events').fetchall(), [('Buildathon 2026',)])
            self.assertEqual(list(output.glob('.radar-*')), [])

    def test_concurrent_pipeline_outputs_match_their_persisted_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ready = Barrier(2)

            def ingest(index):
                incoming = root / f'input-{index}'
                incoming.mkdir()
                (incoming / 'valid_events.json').write_text(json.dumps([
                    event(source=f'platform-{index}', source_id='1')]), encoding='utf-8')
                ready.wait(timeout=10)
                return run_pipeline(incoming, root / 'out', root / 'master.db')

            with ThreadPoolExecutor(max_workers=2) as executor:
                list(executor.map(ingest, range(2)))
            exported = json.loads((root / 'out/master_events.json').read_text(encoding='utf-8'))
            with closing(sqlite3.connect(root / 'master.db')) as connection:
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM canonical_events').fetchone()[0], 1)
                self.assertEqual(connection.execute('SELECT canonical_event_id FROM canonical_events').fetchone()[0],
                                 exported[0]['canonical_event_id'])


if __name__ == '__main__':
    unittest.main()
