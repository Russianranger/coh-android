"""Run the actual staged bind policy/parser against real TCP and UDP sockets.

Linux uses a small Win32 API shim; Windows builds against actual Winsock/MSVC.
Neither variant establishes Android execution or network-namespace isolation.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_wine_dbserver_source as wine

ENVIRONMENT = 'COH_WINE_DB_LOOPBACK_ONLY'
ACK = ('COH_WINE_DB_LOOPBACK_ONLY=1 active: IPv4 listener binds restricted to loopback; '
       'endpoint verification required')


class LoopbackBindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cl' if os.name == 'nt' else 'cc')
        if not compiler:
            raise unittest.SkipTest('Native loopback contracts require a C compiler')
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-loopback-contract-')
        cls.build = Path(cls.temporary.name)
        try:
            receipt = wine.expected_wine_receipt()
            for name in set(wine.WINE_FILES).union(receipt['postgresql_build_input']['patched_sha256']):
                target = cls.build / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / 'upstream/ouroboros' / name, target)
            wine.apply_patch(cls.build, (ROOT / 'patches/postgresql/0001-dbserver-postgresql.patch').read_bytes())
            wine.apply_patch(cls.build, wine.patch_bytes(ROOT))
            source = (cls.build / 'libs/UtilitiesLib/src/network/sock.c').read_text()
            fragment = source[source.index('/* States: 0=default/unbound'):source.index('\nvoid    sockSetBlocking')]
            (cls.build / 'loopback_source_fragment.inc').write_text(fragment)
            overlay = ROOT / 'database/wine-dbserver/overlay/DBServer/src'
            tests = ROOT / 'database/wine-dbserver/tests'
            cls.binary = cls.build / ('loopback-contract.exe' if os.name == 'nt' else 'loopback-contract')
            sources = [str(tests / 'loopback_bind_contract.c'), str(overlay / 'wine_loopback.c')]
            if os.name == 'nt':
                command = [compiler, '/nologo', '/W4', '/WX', '/O2', '/MT', '/D_WIN32_WINNT=0x0601',
                           f'/I{cls.build}', f'/I{overlay}', *sources, 'ws2_32.lib', f'/Fe:{cls.binary}']
            else:
                shutil.copyfile(tests / 'loopback_portable_windows.h', cls.build / 'windows.h')
                command = [compiler, '-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                           '-I' + str(cls.build), '-I' + str(overlay), *sources, '-o', str(cls.binary)]
            result = subprocess.run(command, cwd=cls.build, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
        except BaseException:
            cls.temporary.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_contract(self, value='1', *, kind='tcp', address='wildcard', timing='normal', corruption='none', code=0):
        env = {key: item for key, item in os.environ.items() if key.upper() != ENVIRONMENT}
        if value is not None:
            env[ENVIRONMENT] = value
        result = subprocess.run([str(self.binary), kind, address, timing, corruption], env=env,
                                cwd=self.build, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        report = json.loads(lines[-1])
        markers = [line for line in lines[:-1] if line]
        self.assertNotIn(' active:', result.stderr, 'Acknowledgement must be flushed to stdout')
        self.assertNotIn(' bind verified:', result.stderr, 'Endpoint records must be flushed to stdout')
        return report, ''.join(line + '\n' for line in markers) + result.stderr

    def test_default_keeps_wildcard_bind_and_no_extra_winsock_observation(self):
        for kind in ('tcp', 'udp'):
            with self.subTest(kind=kind):
                report, stderr = self.run_contract(None, kind=kind)
                self.assertEqual((report['status'], report['bound'], report['address'], report['name_calls']), (0, 1, 0, 0))
                self.assertGreater(report['port'], 0)
                self.assertEqual(report['bind_error'], report['reference_error'])
                self.assertEqual(stderr, '')

    def test_default_bind_failure_returns_without_fatal_policy(self):
        for kind in ('tcp', 'udp'):
            with self.subTest(kind=kind):
                report, stderr = self.run_contract(None, kind=kind, address='occupied')
                self.assertEqual((report['status'], report['bound'], report['bind_calls'], report['name_calls']), (0, 0, 1, 0))
                self.assertEqual(report['bind_error'], report['reference_error'])
                self.assertNotEqual(report['bind_error'], 12345)
                self.assertEqual(stderr, '')

    def test_wildcard_tcp_udp_use_actual_loopback_ephemeral_endpoints(self):
        for kind in ('tcp', 'udp'):
            with self.subTest(kind=kind):
                report, stderr = self.run_contract(kind=kind)
                self.assertEqual((report['status'], report['bound'], report['address'], report['name_calls']), (1, 1, 0x7f000001, 1))
                self.assertGreater(report['port'], 0)
                self.assertEqual(report['requested_port'], 0)
                self.assertEqual(stderr, ACK + '\n' + f'{ENVIRONMENT} bind verified: protocol={kind} address=127.0.0.1 port={report["port"]}\n')

    def test_explicit_loopback_and_requested_ports_are_preserved(self):
        for kind in ('tcp', 'udp'):
            for address, expected in (('loopback', 0x7f000001), ('secondary', 0x7f000002), ('requested', 0x7f000001)):
                with self.subTest(kind=kind, address=address):
                    report, _ = self.run_contract(kind=kind, address=address)
                    self.assertEqual(report['address'], expected)
                    self.assertEqual(report['bound'], 1)
                    if address == 'requested':
                        self.assertGreater(report['requested_port'], 0)
                        self.assertEqual(report['port'], report['requested_port'])

    def test_invalid_environment_never_enables_or_binds(self):
        for value in ('', '0', '01', 'true', ' 1', '1 ', '1\n', '1' * 4096):
            with self.subTest(value=value[:10], length=len(value)):
                report, stderr = self.run_contract(value)
                self.assertEqual(report['status'], -1)
                self.assertEqual(report['error'], report['invalid_parameter'])
                self.assertEqual(report['bind_calls'], 0)
                self.assertEqual(stderr, '')

    def test_activation_after_any_bind_attempt_is_refused(self):
        for timing in ('late', 'late-failed'):
            with self.subTest(timing=timing):
                report, stderr = self.run_contract(timing=timing)
                self.assertEqual(report['status'], -1)
                self.assertEqual(report['error'], report['invalid_state'])
                self.assertEqual((report['bind_calls'], report['name_calls']), (1, 0))
                self.assertEqual(stderr, '')

    def test_repeat_activation_is_refused_without_second_ack(self):
        report, stderr = self.run_contract(timing='repeat')
        self.assertEqual(report['status'], -1)
        self.assertEqual(report['error'], report['invalid_state'])
        self.assertEqual(report['bind_calls'], 0)
        self.assertEqual(stderr, ACK + '\n')

    def assert_fatal_closed(self, report, stderr):
        self.assertEqual(report['fatal'], 2)
        self.assertTrue(report['closed_before_exit'])
        self.assertEqual(report['close_calls'], 1)
        self.assertTrue(stderr.startswith(ACK + '\n'))
        self.assertIn(ENVIRONMENT + ' binding failed:', stderr)
        self.assertNotIn('bind verified:', stderr)

    def test_nonloopback_family_and_null_inputs_cannot_reach_bind(self):
        for kind in ('tcp', 'udp'):
            for address in ('nonloopback', 'family', 'null'):
                with self.subTest(kind=kind, address=address):
                    report, stderr = self.run_contract(kind=kind, address=address, code=2)
                    self.assert_fatal_closed(report, stderr)
                    self.assertEqual((report['bind_calls'], report['name_calls']), (0, 0))

    def test_unavailable_requested_socket_cannot_be_ignored(self):
        for kind in ('tcp', 'udp'):
            with self.subTest(kind=kind):
                report, stderr = self.run_contract(kind=kind, address='occupied', code=2)
                self.assert_fatal_closed(report, stderr)
                self.assertEqual((report['bind_calls'], report['name_calls']), (1, 0))

    def test_endpoint_observation_failures_close_before_exit(self):
        for kind in ('tcp', 'udp'):
            for corruption in ('fail-name', 'wrong-ip', 'wrong-loopback', 'wrong-port', 'zero-port', 'wrong-family', 'short-name',
                               'fail-type', 'wrong-type', 'short-type'):
                with self.subTest(kind=kind, corruption=corruption):
                    report, stderr = self.run_contract(kind=kind, address='requested', corruption=corruption, code=2)
                    self.assert_fatal_closed(report, stderr)
                    self.assertEqual((report['bind_calls'], report['name_calls']), (1, 1))


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        sys.argv.remove('--require-windows')
        if os.name != 'nt' or not shutil.which('cl'):
            raise SystemExit('Windows loopback contracts require an initialized x86 MSVC environment')
    unittest.main(verbosity=2)
