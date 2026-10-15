"""Presentation-specific producer, provenance and shutdown contracts.

These host checks do not claim WGL, Android surface or game execution.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import presentation_diagnostic as guest

SESSION = '0123456789abcdef0123456789abcdef'


def producer(duration=30):
    return {'format': 1, 'status': 'passed', 'failure_stage': '', 'session_id': SESSION,
        'width': 800, 'height': 600, 'frames': duration*2, 'duration_seconds': duration,
        'pointer_bits': 32, 'frame_contract': 1, 'readback_verified': True,
        'renderer': 'llvmpipe (LLVM)', 'vendor': 'Mesa', 'gl_version': '4.3',
        'software_rendering': True, 'android_surface_validated': False, 'game_validated': False}


def output(record=None, frames=None):
    value = record or producer()
    records = frames if frames is not None else [{'session_id': SESSION, 'frame': i} for i in range(1, 61)]
    return '\n'.join(guest.FRAME_MARKER + json.dumps(item) for item in records) + '\n' + guest.MARKER + json.dumps(value)


class ProducerTests(unittest.TestCase):
    def test_exact_completed_trace(self):
        self.assertEqual(guest.validate_producer(output(), SESSION, 30), producer())

    def test_missing_duplicate_disordered_or_cross_session_frame_rejected(self):
        complete = [{'session_id': SESSION, 'frame': i} for i in range(1, 61)]
        variants = [complete[:-1], [complete[0]] + complete, complete[::-1]]
        wrong = copy.deepcopy(complete)
        wrong[10]['session_id'] = 'f'*32
        variants.append(wrong)
        wrong = copy.deepcopy(complete)
        wrong[0]['frame'] = True
        variants.append(wrong)
        for records in variants:
            with self.subTest(records=len(records)), self.assertRaises(guest.base.DiagnosticError):
                guest.validate_producer(output(frames=records), SESSION, 30)

    def test_stale_geometry_count_identity_and_excess_claim_rejected(self):
        for key, value in [('session_id', 'f'*32), ('width', 640), ('frames', 59),
                ('frames', True), ('status', 'failed'), ('readback_verified', False),
                ('android_surface_validated', True), ('game_validated', True),
                ('renderer', ''), ('software_rendering', 'yes')]:
            record = producer()
            record[key] = value
            with self.subTest(field=key), self.assertRaises(guest.base.DiagnosticError):
                guest.validate_producer(output(record), SESSION, 30)

    def test_missing_or_duplicate_terminal_result_rejected(self):
        for value in ['', output() + '\n' + guest.MARKER + json.dumps(producer())]:
            with self.assertRaises(guest.base.DiagnosticError):
                guest.validate_producer(value, SESSION, 30)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.assets = Path(self.temporary.name)
        pe = bytearray(512)
        pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 128)
        pe[128:132] = b'PE\0\0'
        struct.pack_into('<H', pe, 132, 0x14c)
        struct.pack_into('<H', pe, 152, 0x10b)
        self.manifest = {'format': 1, 'scope': guest.SCOPE, 'files': {}}
        for name in guest.REQUIRED:
            value = bytes(pe) if name.endswith(('.exe', '.dll')) else b'fixture\n'
            (self.assets / name).write_bytes(value)
            self.manifest['files'][name] = {'sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)}
        self.write_manifest()

    def write_manifest(self):
        (self.assets / 'presentation-manifest.json').write_text(json.dumps(self.manifest))

    def test_all_required_digests_and_pe32_are_checked(self):
        self.assertEqual(set(guest.verify_assets(self.assets)), guest.REQUIRED)
        (self.assets / 'presentation-probe.exe').write_bytes(b'changed')
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'digest differs'):
            guest.verify_assets(self.assets)

    def test_missing_transitive_import_is_rejected(self):
        del self.manifest['files']['game_evidence.py']
        self.write_manifest()
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'inventory differs'):
            guest.verify_assets(self.assets)

    def test_wrong_machine_even_with_correct_digest_is_rejected(self):
        path = self.assets / 'presentation-probe.exe'
        data = bytearray(path.read_bytes())
        struct.pack_into('<H', data, 132, 0x8664)
        path.write_bytes(data)
        self.manifest['files'][path.name]['sha256'] = hashlib.sha256(data).hexdigest()
        self.write_manifest()
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'PE32'):
            guest.verify_assets(self.assets)

    def test_linked_input_and_path_escape_rejected(self):
        path = self.assets / 'game_evidence.py'
        path.unlink()
        path.symlink_to(self.assets / 'game_diagnostic.py')
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'linked'):
            guest.verify_assets(self.assets)
        path.unlink()
        path.write_bytes(b'fixture\n')
        self.manifest['files']['../outside'] = self.manifest['files']['game_evidence.py']
        self.write_manifest()
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Unsafe'):
            guest.verify_assets(self.assets)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.args = argparse.Namespace(state=self.root / 'state', assets=self.root / 'assets',
            socket_dir=self.root / 'socket', session_id=SESSION, duration_seconds=30, timeout_seconds=900,
            wine=Path('/opt/wine/bin/wine'), wineserver=Path('/opt/wine/bin/wineserver'))

    def test_argument_bounds(self):
        guest.validate_args(self.args)
        for field, bad in [('session_id', 'ABCDEF'*5+'AB'), ('session_id', '../x'),
                ('duration_seconds', 29), ('duration_seconds', 121), ('duration_seconds', True),
                ('state', Path('/')), ('socket_dir', Path('relative'))]:
            args = copy.copy(self.args)
            setattr(args, field, bad)
            with self.subTest(field=field), self.assertRaises(guest.base.DiagnosticError):
                guest.validate_args(args)

    def test_device_owner_and_no_postgres_cleanup(self):
        context = guest.base.Context(self.args.state)
        diagnostic = guest.PresentationDiagnostic(self.args, context)
        self.assertIsInstance(diagnostic.wine_owner, guest.DeviceWineProcessOwner)
        self.assertEqual(diagnostic.wine_env[diagnostic.wine_owner.ENV_KEY],
                         diagnostic.wine_owner.environment[diagnostic.wine_owner.ENV_KEY])
        self.assertIsNone(diagnostic.pg)
        self.assertTrue(diagnostic.cleanup_status['postgres_graceful'])
        self.assertEqual(diagnostic.cleanup(), [])

    def test_latched_inspection_failure_still_fails(self):
        context = guest.base.Context(self.args.state)
        diagnostic = guest.PresentationDiagnostic(self.args, context)
        diagnostic.wine_started = True
        diagnostic.wine_owner.receipt.update(complete=True, remaining=0, inspection_failures=1)
        with patch.object(guest.base.Diagnostic, 'cleanup', return_value=[]):
            self.assertIn('ownership inspection', diagnostic.cleanup()[0])
        diagnostic.lock.close()

    def test_execution_has_no_database_or_odbc_path(self):
        context = guest.base.Context(self.args.state)
        diagnostic = guest.PresentationDiagnostic(self.args, context)
        child = Mock()
        child.process.poll.return_value = 0
        child.process.returncode = 0
        child.reader.is_alive.return_value = False
        child.text.return_value = output()
        context.start = Mock(return_value=child)
        context.record = Mock()
        context.run = Mock(return_value={'output': guest.base.RUNTIME_MARKER})
        diagnostic.initialize = Mock()
        diagnostic.start_wine = Mock()
        diagnostic.mark_wine_ready = Mock()
        with patch.object(guest.base, 'validate_runtime_probe', return_value={'pointer_bits': 32}):
            diagnostic.execute()
        self.assertEqual(context.run.call_args.args[0], 'runtime-probe')
        self.assertEqual(context.start.call_args.args[0], 'presentation-probe')
        self.assertEqual(context.report['frames_emitted'], 60)
        diagnostic.lock.close()

    def test_support_archive_is_exact_redacted_report(self):
        import zipfile
        self.args.state.mkdir()
        context = guest.base.Context(self.args.state)
        context.secrets = ['private-secret']
        context.report['note'] = 'private-secret'
        guest.persist_report(self.args, context)
        value = (self.args.state / 'latest-report.json').read_bytes()
        self.assertNotIn(b'private-secret', value)
        with zipfile.ZipFile(self.args.state / 'report.zip') as archive:
            self.assertEqual(archive.namelist(), ['latest-report.json'])
            self.assertEqual(archive.read('latest-report.json'), value)


class NativeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        source = ROOT / 'android/native/presentation-probe.c'
        fixture = root / 'fixture.c'
        fixture.write_text('#define COH_PRESENTATION_PROBE_TEST\n#include ' + json.dumps(str(source)) + r'''
int main(int argc, char **argv) {
    unsigned int i, seconds=0; unsigned char rgb[3];
    if (argc < 2) return 2;
    if (!strcmp(argv[1], "args")) { printf("%d", parse_arguments(argc-1, argv+1, &seconds)); }
    else if (!strcmp(argv[1], "bits")) {
        for (i=0;i<128;++i) printf("%u",session_bit("0123456789abcdef0123456789abcdef",i));
        putchar('\n'); for(i=0;i<16;++i) printf("%u",frame_bit(129,i));
    } else if (!strcmp(argv[1], "bars")) {
        for(i=0;i<8;++i) { bar_rgb(i/4+1,i%4,rgb); printf("%u,%u,%u;",rgb[0],rgb[1],rgb[2]); }
    } else if (!strcmp(argv[1], "renderer")) printf("%d%d%d",software_renderer("LLVMPIPE"),software_renderer("zink lavapipe"),software_renderer("Adreno"));
    else if (!strcmp(argv[1], "json")) json_string("a\"b\\c\n");
    else return 3;
    return 0;
}
''')
        cls.exe = root / 'fixture'
        subprocess.run([shutil.which('cc') or 'gcc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        str(fixture), '-o', str(cls.exe)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_fixture(self, *args):
        return subprocess.check_output([str(self.exe), *args], text=True, timeout=10)

    def test_native_strict_cli(self):
        self.assertEqual(self.run_fixture('args', SESSION, '60'), '1')
        for session, duration in [(SESSION.upper(), '60'), (SESSION, '29'), (SESSION, '121'),
                (SESSION, '060'), (SESSION, '+60'), (SESSION, '60x'), (SESSION[:-1], '60')]:
            self.assertEqual(self.run_fixture('args', session, duration), '0')

    def test_native_bit_order_matches_viewer_contract(self):
        session_bits, frame_bits = self.run_fixture('bits').splitlines()
        self.assertEqual(session_bits, ''.join(f'{int(c,16):04b}' for c in SESSION))
        self.assertEqual(frame_bits, f'{129:016b}')

    def test_native_bars_parity_and_renderer_scope(self):
        self.assertEqual(self.run_fixture('bars'),
            '255,255,255;0,0,255;0,255,0;255,0,0;255,0,0;0,255,0;0,0,255;255,255,255;')
        self.assertEqual(self.run_fixture('renderer'), '110')
        self.assertEqual(json.loads(self.run_fixture('json')), 'a"b\\c\n')


if __name__ == '__main__':
    unittest.main()
