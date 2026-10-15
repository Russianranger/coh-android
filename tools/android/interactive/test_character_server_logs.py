"""Character logs retain full bounded evidence without widening login-only mode."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import character_creation_diagnostic as character
import client_startup_diagnostic as startup


class CharacterServerLogTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.runtime = self.root/'runtime'; self.runtime.mkdir()
        self.target = self.root/'evidence'; self.target.mkdir()
        self.context = SimpleNamespace(report={}, secrets=['private-test-secret'])
        owner = SimpleNamespace(root=self.root, ctx=self.context,
                                args=SimpleNamespace(session_id='f'*32))
        self.value = server.LocalCharacterServer(owner)
        self.value.runtime = self.runtime

    def write_log(self, name, data):
        path = self.runtime/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        return path

    def contents(self):
        with zipfile.ZipFile(self.target/'character-server-logs.zip') as archive:
            return json.loads(archive.read('manifest.json')), {name: archive.read(name)
                for name in archive.namelist() if name != 'manifest.json'}

    def test_over_two_mib_complete_bytes_redaction_hashes_and_current_entity_path_are_retained(self):
        raw = b'ordinary diagnostic\n' * 160000 + b'\xff legacy\nprivate-test-secret\n'
        self.write_log('logs/mapserver/error.log', raw)
        entity = b'261001 01:29:50 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 marker\n'
        self.write_log('logs/dbserver/entity_2026-10-01-01-00-00.log', entity)
        with patch.object(server.login.LocalLoginServer, 'collect', side_effect=AssertionError('login collector used')):
            self.value.collect(self.target)
        manifest, contents = self.contents()
        expected = raw.replace(b'private-test-secret', b'[redacted]')
        self.assertEqual(contents['logs/mapserver/error.log'], expected)
        self.assertEqual(contents['logs/dbserver/entity_2026-10-01-01-00-00.log'], entity)
        pin = manifest['files']['logs/mapserver/error.log']
        self.assertEqual(pin['source_bytes'], len(raw)); self.assertEqual(pin['exported_bytes'], len(expected))
        self.assertEqual(pin['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(pin['exported_sha256'], hashlib.sha256(expected).hexdigest())
        self.assertTrue(pin['redacted']); self.assertFalse(pin['truncated'])
        self.assertEqual(manifest['collection_phase'], 'closed_server_logs')
        proof = self.context.report['character_server_logs']
        self.assertEqual(proof['file_count'], 2); self.assertFalse(proof['truncated'])
        self.assertEqual(proof['sha256'], server.base.file_hash(self.target/proof['path']))

    def test_live_append_is_explicit_snapshot_then_closed_collection_replaces_it(self):
        path = self.write_log('logs/mapserver/entity.log', b'first\n')
        self.value.map_process = Mock(); self.value.map_process.process.poll.return_value = None
        original_fdopen = os.fdopen
        class AppendAfterRead:
            def __init__(inner, descriptor, *args, **kwargs): inner.file = original_fdopen(descriptor, *args, **kwargs)
            def __enter__(inner): return inner
            def __exit__(inner, *args): inner.file.close()
            def read(inner, limit):
                raw = inner.file.read(limit)
                with path.open('ab') as output: output.write(b'after\n')
                return raw
        with patch.object(server.os, 'fdopen', side_effect=AppendAfterRead):
            self.value.collect_server_logs(self.target)
        manifest, contents = self.contents()
        self.assertEqual(contents['logs/mapserver/entity.log'], b'first\n')
        self.assertEqual(manifest['collection_phase'], 'live_snapshot')
        self.assertEqual(manifest['files']['logs/mapserver/entity.log']['appended_bytes_after_snapshot'], 6)
        self.value.map_process.process.poll.return_value = 0
        self.value.collect_server_logs(self.target)
        manifest, contents = self.contents()
        self.assertEqual(contents['logs/mapserver/entity.log'], b'first\nafter\n')
        self.assertEqual(manifest['collection_phase'], 'closed_server_logs')
        self.assertEqual(manifest['files']['logs/mapserver/entity.log']['appended_bytes_after_snapshot'], 0)

    def test_linked_and_hardlinked_logs_are_refused(self):
        original = self.root/'outside'; original.write_bytes(b'private')
        path = self.runtime/'bad.log'; path.symlink_to(original)
        with self.assertRaises(OSError): self.value.collect_server_logs(self.target)
        path.unlink(); os.link(original, path)
        with self.assertRaises(server.base.DiagnosticError): self.value.collect_server_logs(self.target)
        self.assertFalse((self.target/'character-server-logs.zip').exists())
        self.assertEqual(original.read_bytes(), b'private')

    def test_all_source_bounds_fail_without_truncation_or_replacing_previous_archive(self):
        self.write_log('a.log', b'original'); self.value.collect_server_logs(self.target)
        archive = self.target/'character-server-logs.zip'; previous = archive.read_bytes()
        for case in ('file_size', 'total_size', 'count'):
            with self.subTest(case=case):
                for path in self.runtime.glob('*.log'): path.unlink()
                if case == 'count':
                    for index in range(129): (self.runtime/(str(index)+'.log')).touch()
                else:
                    count = 1 if case == 'file_size' else 5
                    size = server.SERVER_LOG_FILE_LIMIT + (1 if case == 'file_size' else 0)
                    for index in range(count):
                        with (self.runtime/(str(index)+'.log')).open('wb') as output: output.truncate(size)
                with self.assertRaises(server.base.DiagnosticError): self.value.collect_server_logs(self.target)
                self.assertEqual(archive.read_bytes(), previous)
                self.assertFalse(list(self.target.glob('character-server-logs.tmp-*')))

    def test_archive_failure_keeps_primary_atlas_console_and_remains_failure(self):
        path = self.runtime/'oversized.log'
        with path.open('wb') as output: output.truncate(server.SERVER_LOG_FILE_LIMIT+1)
        self.value.map_process = Mock(); self.value.map_process.text.return_value = 'Program crash detected\n'
        self.value.map_process.process.poll.return_value = 1
        with self.assertRaises(server.base.DiagnosticError): self.value.collect(self.target)
        self.assertEqual((self.target/'character-atlas-console.txt').read_text(), 'Program crash detected\n')
        self.assertNotIn('character_server_logs', self.context.report)


class CharacterExportBudgetTests(unittest.TestCase):
    def test_default_144_mib_stays_bounded_and_character_256_mib_accepts_larger_capture(self):
        self.assertEqual(startup.CLIENT_EVIDENCE_LIMIT, 144*1024*1024)
        self.assertEqual(character.CHARACTER_EVIDENCE_LIMIT, 256*1024*1024)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); capture = root/'capture'; capture.mkdir()
            with (capture/'large.bin').open('wb') as output: output.truncate(145*1024*1024)
            args = SimpleNamespace(state=root); context = SimpleNamespace(report={}, secrets=[])
            with self.assertRaisesRegex(server.base.DiagnosticError, 'Capture export exceeded bound'):
                startup.persist_report(args, context, capture)
            startup.persist_report(args, context, capture, evidence_limit=character.CHARACTER_EVIDENCE_LIMIT)
            with zipfile.ZipFile(root/'report.zip') as archive:
                self.assertEqual(archive.getinfo('client-evidence/large.bin').file_size, 145*1024*1024)

    def test_character_override_preserves_seventy_file_cap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); capture = root/'capture'; capture.mkdir()
            for index in range(71): (capture/str(index)).touch()
            for limit in (startup.CLIENT_EVIDENCE_LIMIT, character.CHARACTER_EVIDENCE_LIMIT):
                with self.subTest(limit=limit), self.assertRaisesRegex(server.base.DiagnosticError, 'Capture export exceeded bound'):
                    startup.persist_report(SimpleNamespace(state=root), SimpleNamespace(report={}, secrets=[]), capture,
                                           evidence_limit=limit)


if __name__ == '__main__': unittest.main()
