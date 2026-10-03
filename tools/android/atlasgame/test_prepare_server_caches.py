"""Synthetic observer records exercise failures; they are never native evidence."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import os
import subprocess
from unittest import mock

MODULE = Path(__file__).with_name('prepare_server_caches.py')
spec = importlib.util.spec_from_file_location('qualified_server_cache_generator_tests', MODULE)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def phase_stdout(session='1' * 32, pid=12, done=True, exit_code=0):
    events = [b'COH_SERVER_CACHE_LAUNCH_V1 ' + json.dumps({'session_id': session, 'pid': pid}).encode(),
              b'COH_SERVER_CACHE_CONSOLE_V1 ' + json.dumps({'session_id': session, 'pid': pid, 'owned': True}).encode()]
    if done:
        events.extend([b'470 arcs, 957 contacts, 3528 tasks', b'46930 spawn definitions', generator.DONE])
    events += [b'COH_SERVER_CACHE_ESCAPE_V1 ' + json.dumps({'session_id': session, 'pid': pid, 'sent': True}).encode(),
               b'COH_SERVER_CACHE_EXIT_V1 ' + json.dumps({'session_id': session, 'pid': pid,
                                                        'exit_code': exit_code, 'escape_sent': True}).encode()]
    return b'\n'.join(events) + b'\n'


class ServerCacheNativeObserverTests(unittest.TestCase):
    def test_owned_fresh_console_normal_exit_receipt(self):
        receipt = generator.phase_receipt(phase_stdout(), b'started 2026-10-03 03:00:00\n',
                                           'generation', '1' * 32, 0, True)
        self.assertTrue(receipt['console_owned'])
        self.assertEqual(receipt['native_errors']['status'], 'no_native_data_errors')
        self.assertFalse(receipt['native_errors']['queued_error_drain_claimed'])

    def test_missing_done_wrong_session_pid_and_nonzero_exit_rejected(self):
        cases = [phase_stdout(done=False), phase_stdout(session='2' * 32), phase_stdout(exit_code=1),
                 phase_stdout().replace(b'"owned": true', b'"owned": false'),
                 phase_stdout().replace(b'"sent": true', b'"sent": false'),
                 phase_stdout().replace(b'46930 spawn definitions', b'46929 spawn definitions'),
                 phase_stdout() + phase_stdout()]
        for stdout in cases:
            with self.subTest(stdout=stdout), self.assertRaises(ValueError):
                generator.phase_receipt(stdout, b'', 'consumption', '1' * 32, 0, True)
        with self.assertRaises(ValueError):
            generator.phase_receipt(phase_stdout(), b'', 'generation', '1' * 32, 0, False)

    def test_native_error_immediate_callback_and_fileerror_are_not_hidden(self):
        for stdout, stderr in ((phase_stdout(), b'Spawn has invalid power\n'),
                               (b'ERRORLOG FILEERROR: defs/broken.powers\n' + phase_stdout(), b''),
                               (phase_stdout(), b'Could not find appropriate game data dir\n'),
                               (phase_stdout() + b'COH_SERVER_CACHE_TIMEOUT_V1\n', b'')):
            with self.subTest(stdout=stdout, stderr=stderr), self.assertRaises(ValueError):
                generator.phase_receipt(stdout, stderr, 'generation', '1' * 32, 0, True)

    def test_exact_normal_tsr_exit_diagnostics_are_classified_only_after_success(self):
        diagnostics = b'Quitting: Z:\\private\\runtime\\MapServer.exe  -tsr2 -assertmode 8256 \nFlushing log files to disk\n'
        self.assertEqual(generator.phase_receipt(phase_stdout(), diagnostics, 'generation', '1' * 32, 0, True)
                         ['native_exit_code'], 0)
        for stderr in (diagnostics.replace(b'-tsr2', b'-production'), diagnostics + b'Could not find appropriate game data dir\n'):
            with self.assertRaises(ValueError):
                generator.phase_receipt(phase_stdout(), stderr, 'generation', '1' * 32, 0, True)

    def test_host_layout_matches_guest_empty_tools_discovery_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'data').mkdir()
            receipt = generator.prepare_runtime_layout(root)
            self.assertTrue((root / 'tools').is_dir())
            self.assertEqual(list((root / 'tools').iterdir()), [])
            self.assertFalse(receipt['external_data_roots'])
            with self.assertRaises(ValueError): generator.prepare_runtime_layout(root)

    def trace(self, lines):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.12'; path.write_text(lines)
            return generator.trace_receipt([path], '/private/runtime', {'data/server/bin/powers.bin': {}},
                                            ['data/defs/powers/sample.powers'])

    def test_trace_requires_successful_content_read_not_metadata_attempt(self):
        result = self.trace('openat(AT_FDCWD, "/private/runtime/data/server/bin/powers.bin", O_RDONLY) = 3\n'
                            'read(3</private/runtime/data/server/bin/powers.bin>, "abc", 3) = 3\n'
                            'read(3</private/runtime/data/server/bin/powers.bin>, "", 3) = 0\n'
                            'pread64(3</private/runtime/data/server/bin/powers.bin>, "abc", 3, 0) = 3\n'
                            'read(4</private/runtime/data/defs/powers/sample.powers>, 0x123, 10) = -1 EIO\n')
        self.assertEqual(result['cache_content_reads']['data/server/bin/powers.bin'], 6)
        self.assertEqual(result['source_content_reads'], [])
        self.assertEqual(result['cache_writes'], [])

    def test_trace_source_payload_and_mapped_message_reads_detected(self):
        result = self.trace('read(4</private/runtime/data/defs/powers/sample.powers>, "bad", 3) = 3\n'
                            'mmap(NULL, 4096, PROT_READ, MAP_PRIVATE, 5</private/runtime/data/texts/English/Contacts/foo.ms>, 0) = 0xabc\n')
        self.assertEqual(len(result['source_content_reads']), 2)
        self.assertEqual(result['cache_content_reads']['data/server/bin/powers.bin'], 0)

    def test_persisted_message_scope_covers_non_ms_leaf_but_allows_uncached_command(self):
        result = self.trace('read(5</private/runtime/data/texts/English/powers.txt>, "abc", 3) = 3\n'
                            'read(5</private/runtime/data/texts/English/Contacts/custom.def>, "ab", 2) = 2\n'
                            'read(5</private/runtime/data/texts/English/Contacts/saved.BAK>, "a", 1) = 1\n'
                            'read(5</private/runtime/data/texts/English/cmdMessagesServer.ms>, "a", 1) = 1\n')
        self.assertEqual(result['source_content_reads'], [
            {'path': 'data/texts/english/contacts/custom.def', 'bytes': 2},
            {'path': 'data/texts/english/powers.txt', 'bytes': 3}])

    def test_trace_i386_mmap2_and_resumed_source_reads_detected(self):
        result = self.trace('read(4</private/runtime/data/defs/powers/sample.powers>,  <unfinished ...>\n'
                            '<... read resumed>"bad", 3) = 3\n'
                            'mmap2(NULL, 4096, PROT_READ, MAP_PRIVATE, 5</private/runtime/data/texts/English/Contacts/foo.ms>, 0) = 0xabc\n')
        self.assertEqual(len(result['source_content_reads']), 2)
        self.assertEqual(result['source_content_reads'][0]['bytes'], 3)
        self.assertEqual(self.trace('read(4</private/runtime/data/defs/powers/sample.powers>, <unfinished ...>\n'
                                    '<... read resumed>0x123, 3) = -1 EIO\n')['source_content_reads'], [])
        with self.assertRaises(ValueError):
            self.trace('<... read resumed>"bad", 3) = 3\n')
        with self.assertRaises(ValueError):
            self.trace('read(4</private/runtime/data/defs/powers/sample.powers>, <unfinished ...>\n')

    def test_persistent_identifier_reads_recorded_without_claiming_source_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.12'; name = 'data/server/db/templates/badges.attribute'
            path.write_text('read(4</private/runtime/' + name + '>, "id", 2) = 2\n')
            result = generator.trace_receipt([path], '/private/runtime', {}, [name], [name])
            self.assertEqual(result['source_content_reads'], [])
            self.assertEqual(result['identifier_content_reads'], [{'path': name, 'bytes': 2}])

    def test_trace_cache_write_rename_and_unlink_detected(self):
        result = self.trace('write(3</private/runtime/data/server/bin/powers.bin>, "x", 1) = 1\n'
                            'rename("/private/runtime/data/server/bin/temp.bin", "/private/runtime/data/server/bin/powers.bin") = 0\n'
                            'unlink("/private/runtime/data/server/bin/powers.bin") = 0\n')
        self.assertEqual(result['cache_writes'], [{'path': 'data/server/bin/powers.bin', 'bytes': 3}])

    def test_snapshot_detects_noncache_changes_ignores_allowed_bin_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory); leaf = data / 'defs/item.def'; leaf.parent.mkdir(); leaf.write_bytes(b'input')
            before = generator.data_snapshot(data)
            cache = data / 'server/bin/powers.bin'; cache.parent.mkdir(parents=True); cache.write_bytes(b'cache')
            self.assertEqual(before, generator.data_snapshot(data))
            leaf.write_bytes(b'changed')
            self.assertNotEqual(before, generator.data_snapshot(data))

    def test_native_consumption_dates_match_android_seed_without_touching_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); cache = root / 'data/server/bin/messages-en.bin'
            cache.parent.mkdir(parents=True); cache.write_bytes(b'cache bytes')
            source = root / 'data/source.ms'; source.write_bytes(b'source'); original = source.stat().st_mtime_ns
            files = {'data/server/bin/messages-en.bin': {}}
            before = generator.pin(cache)
            generator.normalize_shipped_cache_dates(root, files)
            self.assertEqual(generator.cache_state(root, files)['data/server/bin/messages-en.bin']['mtime_ns'],
                             generator.package.EPOCH * 10**9)
            self.assertEqual(generator.pin(cache), before)
            self.assertEqual(source.stat().st_mtime_ns, original)

    def test_forbidden_definition_scope_is_derived_from_cache_payload_not_claimed_report(self):
        fixture_path = generator.ROOT / 'tools/android/interactive/test_server_cache_package.py'
        fixture_spec = importlib.util.spec_from_file_location('server_scope_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(fixture_spec); fixture_spec.loader.exec_module(fixture)
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'cache.zip'; manifest = fixture.synthetic_archive(archive)
            self.assertEqual(generator.archive_source_paths(archive, manifest['files']),
                             ['data/defs/powers/test.powers'])

    def test_empty_absent_wineserver_cleanup_requires_wait_and_unheld_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {'WINEPREFIX': str(root / 'owned-prefix')}
            with mock.patch.object(generator.subprocess, 'run', side_effect=[
                    subprocess.CompletedProcess(['wineserver', '-k'], 1), subprocess.CompletedProcess(['wineserver', '-w'], 0)]), \
                 mock.patch.object(generator, 'prove_prefix_server_unlocked', return_value={'status': 'prefix_server_lock_unheld'}):
                generator.stop_owned_prefix(env, root)
                self.assertEqual(json.loads((root / 'wine-helpers-stop.json').read_text())['kill_exit_code'], 1)
            with mock.patch.object(generator.subprocess, 'run', return_value=subprocess.CompletedProcess(['wineserver'], 2)):
                with self.assertRaises(ValueError): generator.stop_owned_prefix(env, root)
            with mock.patch.object(generator.subprocess, 'run', side_effect=[
                    subprocess.CompletedProcess(['wineserver', '-k'], 1), subprocess.CompletedProcess(['wineserver', '-w'], 1)]):
                with self.assertRaises(ValueError): generator.stop_owned_prefix(env, root)

    def test_prefix_quiescence_uses_real_posix_first_byte_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); prefix = root / 'prefix'; prefix.mkdir()
            base = root / 'server-base'; base.mkdir(mode=0o700)
            info = prefix.stat(); server = base / f'server-{info.st_dev:x}-{info.st_ino:x}'; server.mkdir(mode=0o700)
            lock = server / 'lock'; lock.write_bytes(b''); lock.chmod(0o600)
            self.assertEqual(generator.prove_prefix_server_unlocked(prefix, base)['status'], 'prefix_server_lock_unheld')
            code = 'import fcntl,sys,time; f=open(sys.argv[1],"r+"); fcntl.lockf(f,fcntl.LOCK_EX,1); print("locked",flush=True); time.sleep(30)'
            holder = subprocess.Popen([sys.executable, '-c', code, str(lock)], stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(holder.stdout.readline().strip(), 'locked')
                with self.assertRaises(BlockingIOError): generator.prove_prefix_server_unlocked(prefix, base)
            finally:
                holder.terminate(); holder.wait(timeout=10); holder.stdout.close()


if __name__ == '__main__':
    unittest.main()
