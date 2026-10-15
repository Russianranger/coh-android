"""Actual-client guest evidence, immutable data isolation and archive tests."""
import argparse
import copy
import ctypes as C
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_startup_diagnostic as guest

SESSION = '0123456789abcdef0123456789abcdef'


def pe_bytes():
    value = bytearray(512)
    value[:2] = b'MZ'
    struct.pack_into('<I', value, 60, 128)
    value[128:132] = b'PE\0\0'
    struct.pack_into('<H', value, 132, 0x14c)
    struct.pack_into('<H', value, 152, 0x10b)
    return bytes(value)


def package(path, *, changed_name=None, manifest_extra=None):
    contents = {'CityOfHeroes.exe': pe_bytes() + b'\0'*(9432576-512)}
    contents.update({f'fixture{i}.dll': pe_bytes() for i in range(20)})
    files = {name: {'size': len(value), 'sha256': hashlib.sha256(value).hexdigest(),
                    'pe_machine': 0x14c} for name, value in contents.items()}
    manifest = {'format': 1, 'role': 'actual_graphical_client', 'source_commit': guest.SOURCE,
                'data_commit': guest.DATA, 'reference_run_id': 36088012664, 'files': files}
    if manifest_extra: manifest.update(manifest_extra)
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in contents.items():
            archive.writestr(changed_name if name == 'fixture0.dll' and changed_name else name, value)
        archive.writestr('client-package.json', json.dumps(manifest))
    return files['CityOfHeroes.exe']['sha256']


def cache_package(path, *, changed_name=None, epoch=guest.CACHE_EPOCH):
    def pascal(value):
        raw = struct.pack('<H',len(value)) + value
        return raw + b'\0' * (-len(raw) % 4)
    dependencies = struct.pack('<I',1) + pascal(b'textures/a.texture') + struct.pack('<I',epoch)
    body = b'fixture'
    value = (b'CrypticS' + struct.pack('<I',0x12345678) + pascal(b'Parse6') + pascal(b'Files1')
        + struct.pack('<I',len(dependencies)) + dependencies + struct.pack('<I',len(body)) + body)
    name = changed_name or 'data/bin/sequencers.bin'
    manifest = {'format': 1, 'role': 'actual_client_generated_caches', 'source_commit': guest.SOURCE,
        'data_commit': guest.DATA, 'executable_sha256': guest.EXE_SHA,
        'asset_archive_sha256': guest.ASSET_ARCHIVE_SHA, 'reference_run_id': 36088012664,
        'prerequisites_manifest_sha256': guest.PREREQUISITES_MANIFEST_SHA,
        'generated_noncache_outputs': [],
        'normalized_mtime_epoch': guest.CACHE_EPOCH, 'files': {name: {
            'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest(), 'schema_crc': '12345678'}}}
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr(name,value)
        archive.writestr('client-cache-manifest.json',json.dumps(manifest))
    return manifest


class EvidenceTests(unittest.TestCase):
    def test_exact_current_pid_and_registry_required(self):
        output = 'Renderer initialization complete\nLoaded all data!\n'
        registry = '    GameProgress    REG_SZ    game_mainLoop\n'
        windows = [{'title': 'City of Heroes : PID: 44', 'mapped': True, 'width': 800, 'height': 600}]
        launch = {'session_id': SESSION, 'pid': 44}
        result = guest.startup_evidence(output, registry, windows, launch)
        self.assertTrue(result['startup_observed'])
        self.assertTrue(result['renderer_initialized'])
        self.assertFalse(result['menu_visual_validated'])
        for records, reg, identity in [(windows, '', launch), ([], registry, launch),
                (windows, registry, {'pid': 45}), (windows, registry, None)]:
            self.assertFalse(guest.startup_evidence(output, reg, records, identity)['startup_observed'])
        windows[0]['mapped'] = False
        self.assertFalse(guest.startup_evidence(output, registry, windows, launch)['startup_observed'])

    def test_world_map_title_retains_exact_owned_pid_and_canonical_path(self):
        output = 'Renderer initialization complete\nLoaded all data!\n'
        registry = '    GameProgress    REG_SZ    game_mainLoop\n'
        launch = {'session_id': SESSION, 'pid': 656}
        title = 'City of Heroes : City_Zones/City_01_01/City_01_01.txt  PID: 656'
        window = {'window_id': 20971523, 'title': title, 'mapped': True, 'width': 800, 'height': 600}
        evidence = guest.startup_evidence(output, registry, [window], launch)
        self.assertTrue(evidence['startup_observed'])
        self.assertEqual(evidence['client_windows'], [window])
        for invalid in [title.replace('656', '657'), title.replace('656', '6560'),
                title.replace('.txt', '.exe'), title.replace('City_Zones/', '../City_Zones/'),
                title.replace('City_Zones/', '/City_Zones/'), title.replace('City_Zones/', 'maps/../City_Zones/'),
                title.replace('City_Zones/', 'C:/City_Zones/'), title.replace('/', '\\'),
                title.replace('  PID:', ' PID:'), title+' extra', title+'\n',
                'Other game : City_Zones/City_01_01/City_01_01.txt  PID: 656']:
            with self.subTest(title=invalid):
                result = guest.startup_evidence(output, registry, [dict(window, title=invalid)], launch)
                self.assertFalse(result['client_window_observed'])
        for identity in [None, {'pid': True}, {'pid': '656'}, {'pid': 0}]:
            with self.subTest(identity=identity):
                self.assertFalse(guest.current_client_title(title, identity))
        for changed in [dict(window, mapped=False), dict(window, width=1)]:
            self.assertFalse(guest.startup_evidence(output, registry, [changed], launch)['startup_observed'])
        self.assertFalse(guest.startup_evidence(output, '', [window], launch)['startup_observed'])

    def test_marker_is_single_session_bound_and_strict_pid(self):
        text = guest.LAUNCH_MARKER + json.dumps({'session_id': SESSION, 'pid': 44})
        self.assertEqual(guest.parse_launch(text, SESSION)['pid'], 44)
        self.assertIsNone(guest.parse_launch('not a launch', SESSION))
        for invalid in [text+'\n'+text, text.replace(SESSION, 'f'*32),
                guest.LAUNCH_MARKER + json.dumps({'session_id': SESSION, 'pid': True})]:
            with self.assertRaises(guest.base.DiagnosticError): guest.parse_launch(invalid, SESSION)

    def test_capture_geometry_and_masks_are_bounded(self):
        buffer = C.create_string_buffer(bytes([0,0,255,0,0,255,0,0]))
        image = guest.XImage(width=2, height=1, data=C.cast(buffer,C.c_void_p), byte_order=0,
            bytes_per_line=8, bits_per_pixel=32, red_mask=0xff0000, green_mask=0xff00, blue_mask=0xff)
        ppm, colors = guest.ppm_from_ximage(image)
        self.assertEqual(ppm, b'P6\n2 1\n255\n\xff\0\0\0\xff\0')
        self.assertEqual(colors, 2)
        for field, value in [('width', 1025), ('bytes_per_line', 4), ('red_mask', 0xffff), ('data', None)]:
            broken = guest.XImage.from_buffer_copy(image)
            setattr(broken, field, value)
            with self.assertRaises(guest.base.DiagnosticError): guest.ppm_from_ximage(broken)

    def test_console_attachment_belongs_to_current_child(self):
        launch = {'session_id': SESSION, 'pid': 44}
        marker = guest.CONSOLE_MARKER + json.dumps(dict(launch, attached=True))
        self.assertTrue(guest.console_identity(marker, launch)['attached'])
        self.assertIsNone(guest.console_identity('', launch))
        for output, identity in [(marker+'\n'+marker, launch), (marker, None),
                (marker, dict(launch, pid=45)), (marker, dict(launch, session_id='f'*32)),
                (marker.replace('true', 'false'), launch)]:
            with self.assertRaises(guest.base.DiagnosticError): guest.console_identity(output, identity)

    def test_no_producer_gameplay_claims(self):
        result = guest.startup_evidence('Loaded all data!', '', [], None)
        self.assertFalse(result['menu_visual_validated'])
        self.assertFalse(result['startup_observed'])


class ConsoleBudgetTests(unittest.TestCase):
    def test_owned_console_preserves_exact_bound_and_overflow_still_fails(self):
        # Exercise the real pipe reader at a scaled bound without allocating the
        # production 128 MiB budget in every focused test run.
        output_limit = 128*1024
        with tempfile.TemporaryDirectory() as temporary, patch.object(guest.base, 'OUTPUT_LIMIT', output_limit):
            for size, overflow in ((output_limit, False), (output_limit+1, True)):
                with self.subTest(size=size):
                    context = guest.base.Context(Path(temporary))
                    command = [sys.executable, '-c',
                        "import sys; sys.stdout.buffer.write(b'x'*int(sys.argv[1])+b'END')", str(size-3)]
                    child = context.start('actual-coh-client', command)
                    try:
                        child.process.wait(timeout=10)
                        child.reader.join(3); child.writer.join(3)
                        self.assertFalse(child.reader.is_alive())
                        self.assertEqual(child.overflow, overflow)
                        self.assertLessEqual(len(child.output), output_limit)
                        if overflow:
                            with self.assertRaises(guest.base.DiagnosticError): context.check()
                        else:
                            context.check()
                            self.assertEqual(len(child.output), size)
                            self.assertTrue(child.output.endswith(b'END'))
                    finally:
                        child.stop()

    def test_console_export_preserves_raw_bytes_without_decode_expansion(self):
        with tempfile.TemporaryDirectory() as temporary:
            diagnostic = guest.ClientStartupDiagnostic.__new__(guest.ClientStartupDiagnostic)
            diagnostic.client = SimpleNamespace(output=bytearray(b'prefix\xff\xfe\n'))
            diagnostic.capture_dir = Path(temporary)
            diagnostic.ctx = SimpleNamespace(report={})
            diagnostic.observer = diagnostic.work = None
            diagnostic.save_evidence()
            exported = (diagnostic.capture_dir/'client-console.log').read_bytes()
            self.assertEqual(exported, bytes(diagnostic.client.output))
            self.assertEqual(diagnostic.ctx.report['client_console']['bytes'], len(exported))
            self.assertEqual(diagnostic.ctx.report['client_console']['sha256'], hashlib.sha256(exported).hexdigest())


class StartupObservationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.elapsed = 0.0
        def sleep(seconds): self.elapsed = round(self.elapsed + seconds, 6)
        clock = SimpleNamespace(monotonic=lambda: self.elapsed, sleep=sleep)
        patched = patch.object(guest, 'time', clock); patched.start(); self.addCleanup(patched.stop)
        patched = patch.object(guest.base, 'validate_runtime_probe', return_value={})
        patched.start(); self.addCleanup(patched.stop)
        observer = Mock()
        observer.windows.return_value = [{'title': 'City of Heroes : PID: 44',
            'mapped': True, 'width': 800, 'height': 600}]
        patched = patch.object(guest, 'XObserver', return_value=observer)
        patched.start(); self.addCleanup(patched.stop)
        self.output = (guest.LAUNCH_MARKER + json.dumps({'session_id': SESSION, 'pid': 44}) + '\n'
            + guest.CONSOLE_MARKER + json.dumps({'session_id': SESSION, 'pid': 44, 'attached': True})
            + '\nRenderer initialization complete\nLoaded all data!\n')
        self.registry = '    GameProgress    REG_SZ    game_mainLoop\n'
        diagnostic = guest.ClientStartupDiagnostic.__new__(guest.ClientStartupDiagnostic)
        diagnostic.args = SimpleNamespace(wine=root/'wine', assets=root, session_id=SESSION,
            startup_timeout_seconds=900, observation_seconds=5)
        diagnostic.work = root
        diagnostic.presentation_socket = root/'view.sock'
        diagnostic.wine_env = {'DISPLAY': ':100'}
        diagnostic.startup_complete = False
        diagnostic.initialize = Mock(); diagnostic.start_wine = Mock()
        diagnostic.mark_wine_ready = Mock(); diagnostic.save_evidence = Mock()
        diagnostic.capture = Mock(return_value={'distinct_colors_capped': 16})
        diagnostic.xserver = Mock(); diagnostic.xserver.process.poll.return_value = None
        child = Mock(); child.process.poll.return_value = None
        child.text.side_effect = lambda: self.output
        diagnostic.ctx = Mock(report={})
        diagnostic.ctx.start.return_value = child
        diagnostic.ctx.run.side_effect = lambda label, *a, **kw: {
            'output': self.registry if label == 'client-progress-registry' else ''}
        self.diagnostic = diagnostic

    def test_missing_console_fails_at_120_seconds_between_progress_polls(self):
        self.output = guest.LAUNCH_MARKER + json.dumps({'session_id': SESSION, 'pid': 44}) + '\n'
        self.registry = ''
        # A slow progress query makes 120 seconds fall between five-second polls.
        run = self.diagnostic.ctx.run.side_effect
        def delayed_registry(label, *args, **kwargs):
            if label == 'client-progress-registry': self.elapsed += .2
            return run(label, *args, **kwargs)
        self.diagnostic.ctx.run.side_effect = delayed_registry
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'within 120 seconds'):
            self.diagnostic.execute()
        self.assertEqual(self.elapsed, 120.0)
        self.assertFalse(self.diagnostic.startup_complete)

    def test_truncation_arriving_during_final_capture_cannot_pass(self):
        def capture(label):
            if label == 'client-observed': self.output += 'COH_CLIENT_CONSOLE_TRUNCATED_V1\n'
            return {'distinct_colors_capped': 16}
        self.diagnostic.capture.side_effect = capture
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'exceeded observation budget'):
            self.diagnostic.execute()
        self.assertFalse(self.diagnostic.startup_complete)
        self.assertFalse(any(call.kwargs.get('bounded_live_observation')
                             for call in self.diagnostic.ctx.passed.call_args_list))


class WorktreeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assets = self.root / 'assets'; self.assets.mkdir()
        self.work = self.root / 'work'; self.work.mkdir()
        self.data = self.root / 'generation' / 'data'; self.data.mkdir(parents=True)
        self.context = Mock()
        self.identity = {'receipt_sha256': 'f'*64, 'generation': 'generation-'+'1'*32}
        self.exesha = package(self.assets / 'client-runtime.zip')
        self.pin = patch.object(guest, 'EXE_SHA', self.exesha); self.pin.start(); self.addCleanup(self.pin.stop)
        self.prerequisite_contents = {name: name.encode('ascii') for name in guest.PREREQUISITES}
        prerequisite_pins = {name: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
                             for name, value in self.prerequisite_contents.items()}
        prerequisite_manifest = {'format': 1, 'role': 'actual_client_prerequisites',
            'source_commit': guest.SOURCE, 'data_commit': guest.DATA, 'reference_run_id': 36088012664,
            'schema_run_id': 36088012666, 'ordinary_comparison_run_id': 36176806895,
            'files': prerequisite_pins}
        raw = json.dumps(prerequisite_manifest).encode()
        self.prerequisite_manifest = raw
        for name, value in [('PREREQUISITES', prerequisite_pins),
                            ('PREREQUISITES_MANIFEST_SHA', hashlib.sha256(raw).hexdigest())]:
            patched = patch.object(guest,name,value);patched.start();self.addCleanup(patched.stop)
        with zipfile.ZipFile(self.assets/'client-prerequisites.zip','w') as archive:
            archive.writestr('client-prerequisites-manifest.json',raw)
            for name, value in self.prerequisite_contents.items(): archive.writestr(name,value)
        cache_package(self.assets/'client-caches.zip')
        for name in ['textures/a.texture', 'defs/test.dbidmap', 'bin/cache.bin', 'server/bin/server.bin', 'geobin/map.bin']:
            path = self.data / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'input')
        self.count = patch.object(guest, 'DATA_COUNT', 5); self.count.start(); self.addCleanup(self.count.stop)
        self.size = patch.object(guest, 'DATA_BYTES', 25); self.size.start(); self.addCleanup(self.size.stop)

    def change_wrapper_commit(self):
        path = self.assets / 'client-runtime.zip'
        with zipfile.ZipFile(path) as archive:
            members = {info.filename: archive.read(info) for info in archive.infolist()}
        manifest = json.loads(members['client-package.json'])
        manifest['repository_commit'] = 'c' * 40
        members['client-package.json'] = json.dumps(manifest).encode()
        with zipfile.ZipFile(path, 'w') as archive:
            for name, value in members.items(): archive.writestr(name, value)

    def test_wrapper_commit_update_preserves_generated_caches_without_rescanning(self):
        work, _ = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        generated = work / 'data/bin/generated-after-play.bin'
        generated.write_bytes(b'valuable generated cache'); before = generated.stat()
        self.change_wrapper_commit()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('Must not rescan input tree')):
            again, saved = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertEqual(work, again); self.assertTrue(work.exists())
        retained = again / generated.relative_to(work)
        self.assertEqual(retained.read_bytes(), b'valuable generated cache')
        self.assertEqual((retained.stat().st_ino, retained.stat().st_mtime_ns), (before.st_ino, before.st_mtime_ns))
        self.assertTrue(saved['reused']); self.assertTrue(saved['wrapper_only_migration'])
        self.assertTrue(saved['generated_cache_bytes_preserved'])

    def test_wrapper_migration_validates_binaries_before_mutating(self):
        work, _ = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        target = work / 'CityOfHeroes.exe'; target.chmod(0o600); target.write_bytes(b'changed')
        self.change_wrapper_commit()
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Cached client binary'):
            guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertTrue(work.exists())
        self.assertEqual(len(list(self.work.iterdir())), 1)

    def test_wrapper_migration_recovers_interrupted_receipt_write(self):
        work, _ = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        (work / 'data/bin/generated.bin').write_bytes(b'keep')
        self.change_wrapper_commit()
        with patch.object(guest.base, 'private_write', side_effect=OSError('interrupted atomic marker update')):
            with self.assertRaises(OSError):
                guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('Must not rescan input tree')):
            again, saved = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertTrue(saved['wrapper_only_migration'])
        self.assertEqual((again / 'data/bin/generated.bin').read_bytes(), b'keep')

    def test_inputs_readonly_caches_isolated_and_repeat_skips_inventory(self):
        work, receipt = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertFalse(receipt['reused'])
        self.assertEqual(receipt['linked_files'], 1)
        self.assertEqual(receipt['copied_writable_files'], 4)
        linked = work/'data/textures/a.texture'
        self.assertTrue(linked.is_symlink())
        self.assertEqual(linked.resolve(), self.data/'textures/a.texture')
        self.assertEqual(stat.S_IMODE(linked.stat().st_mode), 0o444)
        self.assertEqual(int(linked.stat().st_mtime),guest.CACHE_EPOCH)
        self.assertTrue(receipt['imported_metadata_normalized'])
        self.assertTrue(receipt['imported_input_bytes_unchanged'])
        self.assertEqual(receipt['prepared_cache_files'],1)
        self.assertEqual(receipt['prepared_prerequisite_files'],3)
        for name, contents in self.prerequisite_contents.items():
            self.assertEqual((work/name).read_bytes(),contents)
            self.assertEqual(int((work/name).stat().st_mtime),guest.CACHE_EPOCH)
            self.assertEqual(stat.S_IMODE((work/name).stat().st_mode),0o444)
            self.assertFalse((self.data/Path(name).relative_to('data')).exists())
        self.assertEqual(receipt['cache_archive_sha256'],hashlib.sha256((self.assets/'client-caches.zip').read_bytes()).hexdigest())
        self.assertEqual(int((work/'data/bin/sequencers.bin').stat().st_mtime),guest.CACHE_EPOCH)
        for name in ['defs/test.dbidmap','bin/cache.bin','server/bin/server.bin','geobin/map.bin']:
            target = work/'data'/name
            self.assertEqual(int(target.stat().st_mtime),guest.CACHE_EPOCH)
            self.assertFalse(target.is_symlink()); target.write_bytes(b'generated')
            self.assertEqual((self.data/name).read_bytes(), b'input')
        with patch.object(guest.os,'scandir',side_effect=AssertionError('Must not rescan all inputs')):
            again, saved = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertEqual(again, work); self.assertTrue(saved['reused'])

    def test_linked_input_or_extra_input_fails_atomically(self):
        (self.data/'escape').symlink_to(self.data/'textures/a.texture')
        with self.assertRaisesRegex(guest.base.DiagnosticError,'Linked immutable'):
            guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertEqual(list(self.work.iterdir()), [])
        (self.data/'escape').unlink(); (self.data/'extra').write_bytes(b'x')
        with self.assertRaises(guest.base.DiagnosticError):
            guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_reused_executable_and_linked_cache_rejected(self):
        work,_ = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        target = work/'CityOfHeroes.exe'; target.chmod(0o600); target.write_bytes(b'changed')
        with self.assertRaisesRegex(guest.base.DiagnosticError,'Cached client binary'):
            guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)

    def test_prepared_cache_dates_and_paths_are_checked(self):
        cache_package(self.assets/'client-caches.zip',epoch=guest.CACHE_EPOCH-30)
        with self.assertRaisesRegex(guest.base.DiagnosticError,'source timestamp differs'):
            guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertEqual(list(self.work.iterdir()),[])
        cache_package(self.assets/'client-caches.zip',changed_name='data/bin/../sequencers.bin')
        with zipfile.ZipFile(self.assets/'client-caches.zip') as archive:
            with self.assertRaises(guest.base.DiagnosticError): guest.cache_manifest(archive)

    def test_prerequisite_payload_change_fails(self):
        with zipfile.ZipFile(self.assets/'client-prerequisites.zip','w') as archive:
            archive.writestr('client-prerequisites-manifest.json',self.prerequisite_manifest)
            for name,value in self.prerequisite_contents.items(): archive.writestr(name,b'x'+value[1:])
        with self.assertRaisesRegex(guest.base.DiagnosticError,'prerequisite payload differs'):
            guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertEqual(list(self.work.iterdir()),[])

    def test_prerequisites_are_hash_checked_on_reuse(self):
        work,_ = guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        target = work/next(iter(self.prerequisite_contents))
        target.chmod(0o600);target.write_bytes(b'changed')
        with self.assertRaisesRegex(guest.base.DiagnosticError,'Cached client prerequisite differs'):
            guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)

    def test_cache_preflight_reserves_space_before_touching_inputs(self):
        with patch.object(guest.shutil,'disk_usage',return_value=argparse.Namespace(free=1)):
            with self.assertRaisesRegex(guest.base.DiagnosticError,'Insufficient space'):
                guest.prepare_worktree(self.work,self.data,self.assets,self.identity,self.context)
        self.assertEqual(list(self.work.iterdir()),[])
        self.assertNotEqual(int((self.data/'textures/a.texture').stat().st_mtime),guest.CACHE_EPOCH)

    def test_cache_inventory_excludes_inputs_and_stops_at_bound(self):
        private = self.root / 'private'
        cache = private / 'data' / 'bin'
        cache.mkdir(parents=True)
        (private / 'data' / 'defs').mkdir()
        (private / 'data' / 'defs' / 'input.def').write_bytes(b'not inventoried')
        (cache / 'first.bin').write_bytes(b'123')
        (cache / 'second.bin').write_bytes(b'12345')
        result = guest.cache_inventory(private, guest.time.monotonic()+3)
        self.assertFalse(result['truncated'])
        self.assertEqual({row['path'] for row in result['files']}, {'data/bin/first.bin','data/bin/second.bin'})
        self.assertEqual(sum(row['bytes'] for row in result['files']), 8)
        limited = guest.cache_inventory(private, guest.time.monotonic()+3, entry_limit=1)
        self.assertTrue(limited['truncated'])
        self.assertEqual(len(limited['files']), 1)
        (cache / 'linked.bin').symlink_to(cache / 'first.bin')
        with self.assertRaises(guest.base.DiagnosticError): guest.cache_inventory(private, guest.time.monotonic()+3)

    def test_archive_traversal_server_and_wrong_donor_rejected(self):
        for name in ['../outside', 'MapServer.exe']:
            self.exesha = package(self.assets/'client-runtime.zip',changed_name=name)
            with zipfile.ZipFile(self.assets/'client-runtime.zip') as archive:
                with self.assertRaises(guest.base.DiagnosticError): guest.archive_manifest(archive)
        package(self.assets/'client-runtime.zip',manifest_extra={'reference_run_id':1})
        with zipfile.ZipFile(self.assets/'client-runtime.zip') as archive:
            with self.assertRaises(guest.base.DiagnosticError): guest.archive_manifest(archive)


class ManifestAndLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.args = argparse.Namespace(state=self.root/'state', assets=self.root/'assets',
            socket_dir=self.root/'socket', game_data=self.root/'generation/data',
            session_id=SESSION, startup_timeout_seconds=900, observation_seconds=30,
            timeout_seconds=1620, wine=Path('/opt/wine/bin/wine'), wineserver=Path('/opt/wine/bin/wineserver'))

    def test_arguments_reject_traversal_and_unbounded_durations(self):
        guest.validate_args(self.args)
        for field,value in [('game_data',Path('../x')),('startup_timeout_seconds',901),
                ('observation_seconds',True),('session_id','f'*31)]:
            invalid = copy.copy(self.args); setattr(invalid,field,value)
            with self.assertRaises(guest.base.DiagnosticError): guest.validate_args(invalid)

    def test_import_receipt_is_required_and_bound(self):
        self.args.game_data.mkdir(parents=True)
        receipt = self.args.game_data.parent/'complete.properties'
        receipt.write_text('generation=generation-'+'1'*32+'\ncontract.sha256='+'a'*64+
            '\ncount=173011\nbytes=2977730517\n')
        identity=guest.import_identity(self.args.game_data)
        self.assertEqual(identity['file_count'],173011)
        receipt.write_text(receipt.read_text()+'count=173011\n')
        with self.assertRaises(guest.base.DiagnosticError): guest.import_identity(self.args.game_data)

    def test_presentation_base_does_not_start_database(self):
        context = guest.base.Context(self.args.state)
        diagnostic = guest.ClientStartupDiagnostic(self.args, context)
        self.assertIsNone(diagnostic.pg)
        self.assertTrue(diagnostic.cleanup_status['postgres_graceful'])
        self.assertIsInstance(diagnostic,guest.presentation.PresentationDiagnostic)
        self.assertEqual(diagnostic.cleanup(), [])

    def test_export_includes_exact_capture_and_report(self):
        self.args.state.mkdir()
        capture=self.root/'captures'; capture.mkdir(); (capture/'screen.ppm').write_bytes(b'P6\n1 1\n255\n\xff\0\0')
        context=guest.base.Context(self.args.state)
        context.report.update(status='failed',passed=False)
        guest.persist_report(self.args,context,capture)
        with zipfile.ZipFile(self.args.state/'report.zip') as archive:
            self.assertEqual(set(archive.namelist()),{'latest-report.json','client-evidence/screen.ppm'})
            self.assertEqual(archive.read('client-evidence/screen.ppm'),(capture/'screen.ppm').read_bytes())
            self.assertFalse(json.loads(archive.read('latest-report.json'))['passed'])
        (capture/'linked').symlink_to(capture/'screen.ppm')
        with self.assertRaises(guest.base.DiagnosticError): guest.persist_report(self.args,context,capture)

    def test_large_console_bundle_retains_exact_limit_and_rejects_excess(self):
        limit = patch.object(guest, 'CLIENT_EVIDENCE_LIMIT', 144*1024)
        limit.start(); self.addCleanup(limit.stop)
        self.args.state.mkdir()
        capture = self.root/'large-captures'; capture.mkdir()
        console = capture/'client-console.log'
        with console.open('wb') as stream: stream.truncate(128*1024)
        with (capture/'other-evidence.bin').open('wb') as stream:
            stream.truncate(guest.CLIENT_EVIDENCE_LIMIT-console.stat().st_size)
        context = guest.base.Context(self.args.state)
        guest.persist_report(self.args, context, capture)
        with zipfile.ZipFile(self.args.state/'report.zip') as archive:
            self.assertEqual(archive.getinfo('client-evidence/client-console.log').file_size, 128*1024)
            self.assertEqual(sum(info.file_size for info in archive.infolist() if info.filename.startswith('client-evidence/')),
                             guest.CLIENT_EVIDENCE_LIMIT)
        with console.open('ab') as stream: stream.write(b'x')
        with self.assertRaises(guest.base.DiagnosticError): guest.persist_report(self.args, context, capture)


if __name__ == '__main__': unittest.main()
