import contextlib, importlib.machinery, importlib.util, io, json, os, subprocess, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


binary = Path(os.environ.get('KNOW_TEST_BIN', Path(__file__).parent / 'bin/know'))


def load_module():
    loader = importlib.machinery.SourceFileLoader('know_test', str(binary))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


class KnowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='know-test-')
        self.addCleanup(self.temporary.cleanup)
        self.know = load_module()
        self.know.directory = self.temporary.name
        self.path = Path(self.temporary.name)

    def call(self, function, **arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            getattr(self.know, function)(SimpleNamespace(**arguments))
        return output.getvalue()

    def note(self, text, kind='fact', replaces=()):
        return self.call('note', a=[text], kind=kind, replaces=list(replaces))

    def test_failed_insert_is_replayed_before_the_next_id(self):
        with patch.object(self.know, 'insert', side_effect=RuntimeError('injected write failure')):
            with self.assertRaisesRegex(RuntimeError, '#0 is saved in the journal'):
                self.note('first note must survive')
        self.assertEqual(self.note('second note'), '#1\n')
        self.assertEqual(len(self.know.read_journal(str(self.path / 'log'))), 2)
        self.assertIn('first note must survive', self.call('wake', n=18))
        self.assertIn('2 notes', self.call('doctor'))

    def test_failed_journal_sync_reports_uncertainty_and_doctor_confirms_replay(self):
        with patch.object(self.know.os, 'fsync', side_effect=OSError('injected sync failure')):
            with self.assertRaisesRegex(RuntimeError, 'persistence is uncertain; run know doctor before retrying'):
                self.note('unconfirmed write')
        self.assertIn('replayed 1', self.call('doctor'))
        self.assertEqual(self.note('next note'), '#1\n')

    def test_doctor_replays_missing_database_without_rewriting_journal(self):
        self.note('recover this note')
        original = (self.path / 'log').read_bytes()
        (self.path / 'db').unlink()
        (self.path / 'db-wal').unlink(missing_ok=True)
        self.assertIn('replayed 1', self.call('doctor'))
        self.assertEqual((self.path / 'log').read_bytes(), original)

    def test_duplicate_conflict_is_refused_before_any_replay(self):
        journal = '#0 2026-11-14 first\n#0 2026-11-14 second\n'
        (self.path / 'log').write_text(journal)
        with self.assertRaisesRegex(ValueError, 'conflicting duplicate ID #0'):
            self.call('doctor')
        self.assertFalse((self.path / 'db').exists())
        self.assertEqual((self.path / 'log').read_text(), journal)

    def test_duplicate_metadata_conflict_is_refused(self):
        self.note('same text')
        record = json.loads((self.path / 'log').read_text())
        record['k'] = 'a'
        with (self.path / 'log').open('a') as output:
            output.write(json.dumps(record) + '\n')
        with self.assertRaisesRegex(ValueError, 'conflicting duplicate ID #0'):
            self.call('doctor')

    def test_duplicate_json_fields_and_unknown_replacements_are_refused(self):
        for content in ('{"i":0,"i":1,"d":"2026-11-14","t":"ambiguous","k":"f","x":[]}\n', '{"i":2,"d":"2026-11-14","t":"missing target","k":"f","x":[1]}\n'):
            (self.path / 'log').write_text(content)
            with self.assertRaises(ValueError):
                self.call('doctor')
            self.assertFalse((self.path / 'db').exists())

    def test_import_rejects_invalid_sources_without_partial_import(self):
        with tempfile.TemporaryDirectory(prefix='know-source-') as directory:
            source = Path(directory) / 'source'
            for content in ('#0 2026-11-14 valid\nbroken\n', '#0 2026-11-14 valid\n#1 2026-11-14 partial', '#0 2026-11-14 one\n#0 2026-11-14 two\n'):
                source.write_text(content)
                with self.assertRaises(ValueError):
                    self.call('load', a=[str(source)])
                self.assertFalse((self.path / 'log').exists())
                self.assertEqual(source.read_text(), content)

    def test_legacy_import_and_identical_duplicates_preserve_long_notes(self):
        with tempfile.TemporaryDirectory(prefix='know-source-') as directory:
            source = Path(directory) / 'source'
            content = '#0 2026-11-14 ' + 'long legacy note ' * 25 + '\n'
            source.write_text(content * 2)
            self.assertEqual(self.call('load', a=[str(source)]), 'imported 1\n')
            self.assertEqual(source.read_text(), content * 2)
            self.assertIn('long legacy note', self.call('wake', n=18))

    def test_import_cannot_overwrite_an_unindexed_journal(self):
        (self.path / 'log').write_text('#0 2026-11-14 existing\n')
        with tempfile.TemporaryDirectory(prefix='know-source-') as directory:
            source = Path(directory) / 'source'
            source.write_text('#0 2026-11-14 imported\n')
            with self.assertRaisesRegex(ValueError, 'empty store'):
                self.call('load', a=[str(source)])
        self.assertIn('existing', self.call('wake', n=18))

    def test_replacements_must_exist_and_cannot_repeat(self):
        self.note('old fact')
        for replacements in ([0, 0], [42], [-1]):
            with self.assertRaises(ValueError):
                self.note('new fact', replaces=replacements)
        self.assertEqual(len(self.know.read_journal(str(self.path / 'log'))), 1)

    def test_rebuild_preserves_journal_and_repairs_a_corrupt_index(self):
        self.note('first fact')
        self.note('replacement fact', replaces=[0])
        original = (self.path / 'log').read_bytes()
        (self.path / 'db').write_bytes(b'corrupt index')
        (self.path / 'db-wal').write_bytes(b'stale wal')
        (self.path / 'db-shm').write_bytes(b'stale shared memory')
        self.assertIn('rebuilt 2 notes', self.call('rebuild'))
        self.assertEqual((self.path / 'log').read_bytes(), original)
        self.assertIn('1 current facts', self.call('doctor'))
        self.assertFalse(list(self.path.glob('.db-rebuild-*')))
        self.assertFalse((self.path / 'db-shm').exists())

    def test_rebuild_refuses_a_bad_journal_before_touching_index(self):
        self.note('first fact')
        with (self.path / 'log').open('a') as output:
            output.write('truncated')
        original = (self.path / 'db').read_bytes()
        with self.assertRaisesRegex(ValueError, 'incomplete final record'):
            self.call('rebuild')
        self.assertEqual((self.path / 'db').read_bytes(), original)
        self.assertFalse(list(self.path.glob('.db-rebuild-*')))

    def test_index_mismatch_refuses_writes(self):
        self.note('authoritative fact')
        with self.know.index(str(self.path / 'db')) as (connection, cursor):
            cursor.execute('UPDATE n SET t = ? WHERE i = 0', ('wrong index text',))
            connection.commit()
        original = (self.path / 'log').read_bytes()
        with self.assertRaisesRegex(ValueError, 'index differs from journal'):
            self.note('must not append')
        self.assertEqual((self.path / 'log').read_bytes(), original)

    def test_missing_journal_never_discards_database(self):
        self.note('must survive')
        (self.path / 'log').unlink()
        with self.assertRaisesRegex(ValueError, 'journal is missing'):
            self.note('must not append')
        self.assertFalse((self.path / 'log').exists())
        with self.assertRaisesRegex(ValueError, 'journal is missing'):
            self.call('rebuild')

    def test_history_labels_and_activity_without_embeddings(self):
        self.note('old fact')
        self.note('new fact', replaces=[0])
        self.note('start of a turn', kind='activity')
        history = self.call('wake', n=18)
        self.assertIn('old fact [replaced]', history)
        self.assertIn('start of a turn [activity]', history)
        self.assertIn('old fact [replaced]', self.call('grep', a=['old fact'], n=18))
        self.call('ask', a=['new fact'], n=1, min_score=-1)
        with self.know.store() as (_, cursor, _, _):
            self.assertEqual(self.know.rows(cursor, 'SELECT i FROM n WHERE e IS NOT NULL'), [(1,)])

    def test_start_prints_prior_newest_notes_then_saves(self):
        for i in range(4):
            self.note(f'note {i}')
        output = self.call('start', a=['session intent'], kind='activity', replaces=[], n=2)
        self.assertEqual(output.splitlines()[:2], ['#2 ' + self.know.datetime.date.today().isoformat() + ' note 2', '#3 ' + self.know.datetime.date.today().isoformat() + ' note 3'])
        self.assertEqual(output.splitlines()[2], 'saved #4')
        self.assertIn('session intent [activity]', self.call('wake', n=1))

    def test_concurrent_writers_get_unique_ids(self):
        environment = dict(os.environ, KNOW_DIR=str(self.path), PYTHONDONTWRITEBYTECODE='1')
        processes = [subprocess.Popen([str(binary), 'note', f'writer {i}'], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(6)]
        results = [process.communicate(timeout=20) for process in processes]
        self.assertTrue(all(process.returncode == 0 for process in processes), results)
        self.assertEqual({output.strip() for output, _ in results}, {f'#{i}' for i in range(6)})
        self.assertIn('6 notes', self.call('doctor'))

    def test_retrieval_positive_negative_and_corrected_facts(self):
        self.note('T3 Code starts through the pxpipe proxy using t3px.')
        self.note('T3 Code opens normally from Mod+D using its desktop entry. Pxpipe and t3px were removed.', replaces=[0])
        self.note('know usage rules are in ~/AGENTS.md and ~/.agents/skills/know/SKILL.md.')
        self.note('Agent Chrome runs headless on port 9223. Visible Chrome is for Ed.')
        self.note('Sway configuration is ~/.config/sway/config; mirror edits to ~/i/144126/dotfiles/sway/config.')
        self.note('Use TypeScript and pnpm for JavaScript projects; use pipx for Python tools. Never npm or npx.')
        self.note('The streaming voice tool ends a phrase after 540 milliseconds of silence.')
        self.note('Where are the know usage rules written?', kind='activity')
        positives = [('How do I start T3 Code normally?', 1), ('Where are know rules written?', 2), ('Which port does the agent browser use?', 3), ('Where do I edit Sway settings?', 4), ('Which JavaScript package manager should I use?', 5), ('How long is the voice phrase silence timeout?', 6)]
        for query, expected in positives:
            with self.subTest(query=query):
                result = self.call('ask', a=[query], n=1, min_score=self.know.minimum_similarity)
                self.assertTrue(result.startswith(f'#{expected} '), result)
        for query in ('What is the PostgreSQL backup schedule on Mars?', 'What is the name of my pet iguana?', 'Which dentist appointment did I book for Tuesday?', 'Where is the backup schedule for our Oracle database?', "Where is Ed's ukulele kept?"):
            with self.subTest(query=query):
                self.assertIn('no strong match', self.call('ask', a=[query], n=9, min_score=self.know.minimum_similarity))
        result = self.call('ask', a=['Where are know rules written?'], n=9, min_score=-1)
        self.assertNotIn('#0 ', result)
        self.assertNotIn('#7 ', result)

    def test_replaced_neighbours_cannot_crowd_out_current_facts(self):
        for i in range(12):
            self.note(f'T3 Code pxpipe launcher setup revision {i}')
        self.call('ask', a=['T3 Code pxpipe launcher setup'], n=9, min_score=-1)
        self.note('T3 Code opens normally; pxpipe was removed.', replaces=range(12))
        result = self.call('ask', a=['T3 Code pxpipe launcher setup'], n=1, min_score=-1)
        self.assertTrue(result.startswith('#12 '), result)

    def test_semantic_only_allows_a_paraphrase_without_shared_words(self):
        self.note('Purchase provisions before departure.')
        query = 'Buy groceries ahead of leaving.'
        self.assertIn('no strong match', self.call('ask', a=[query], n=1, min_score=-1))
        self.assertTrue(self.call('ask', a=[query], n=1, min_score=-1, semantic_only=True).startswith('#0 '))

    def test_doctor_detects_stale_embeddings(self):
        self.note('Agent Chrome runs headless on port 9223.')
        self.call('ask', a=['Agent Chrome port'], n=1, min_score=-1)
        self.assertIn('ok:', self.call('doctor', check_vectors=True))
        vector = json.loads(self.know.embed(['Agent Chrome runs headless on port 9223.'])[0])
        with self.know.store() as (connection, cursor, _, _):
            cursor.execute('UPDATE n SET e = vector32(?) WHERE i = 0', (json.dumps([-v for v in vector]),))
            connection.commit()
        with self.assertRaisesRegex(ValueError, 'differs from the current model'):
            self.call('doctor', check_vectors=True)


if __name__ == '__main__':
    unittest.main()
