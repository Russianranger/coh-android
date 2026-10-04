"""Qualify staged explicit and client UDP bindings with real native sockets.

Linux uses the existing narrow Win32 shim. --require-windows requires x86 MSVC
and actual Winsock, and cannot silently substitute the portable test.
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
import prepare_game_loopback_source as game

ENVIRONMENT = 'COH_GAME_LOOPBACK_ONLY'
ACK = 'COH_GAME_LOOPBACK_ONLY=1 active: IPv4 loopback binding policy'


class GameLoopbackBindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cl' if os.name == 'nt' else 'cc')
        if not compiler:
            raise unittest.SkipTest('Native loopback contracts require a C compiler')
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-loopback-contract-')
        cls.build = Path(cls.temporary.name)
        try:
            receipt = game.expected_game_receipt()
            for name in game.GAME_FILES:
                target = cls.build / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / 'upstream/ouroboros' / name, target)
            game.apply_patch(cls.build, game.patch_bytes(ROOT))
            source = (cls.build / 'libs/UtilitiesLib/src/network/sock.c').read_text()
            fragment = source[source.index('/* States: 0=default/unbound'):source.index('\nvoid    sockSetBlocking')]
            (cls.build / 'loopback_source_fragment.inc').write_text(fragment)
            source = (cls.build / 'libs/UtilitiesLib/src/network/net_link.c').read_text()
            start = source.index('static int netOpenSocketUdp(NetLink *link,const char *address,int port){')
            fragment = source[start:source.index('\n}', start) + 2]
            (cls.build / 'game_udp_source_fragment.inc').write_text(fragment)
            tests = ROOT / 'database/game-loopback/tests'
            cls.binary = cls.build / ('game-loopback-contract.exe' if os.name == 'nt' else 'game-loopback-contract')
            sources = [str(tests / 'loopback_bind_contract.c')]
            if os.name == 'nt':
                command = [compiler, '/nologo', '/W4', '/WX', '/O2', '/MT', '/D_WIN32_WINNT=0x0601',
                           f'/I{cls.build}', *sources, 'ws2_32.lib', f'/Fe:{cls.binary}']
            else:
                shutil.copyfile(ROOT / 'database/wine-dbserver/tests/loopback_portable_windows.h', cls.build / 'windows.h')
                command = [compiler, '-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                           '-I' + str(cls.build), *sources, '-o', str(cls.binary)]
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


    def test_console_records_fit_initial_stock_console_width(self):
        self.assertLess(len(ACK), 80)
        record = ENVIRONMENT + ' bind verified: protocol=udp address=127.0.0.1 port=65535'
        self.assertLess(len(record), 80)

    def test_actual_Atlas_udp7001_listener(self):
        report, record = self.run_contract(kind='udp', address='atlas')
        self.assertEqual((report['address'], report['port'], report['requested_port']), (0x7f000001, 7001, 7001))
        self.assertIn('protocol=udp address=127.0.0.1 port=7001', record)

    def test_actual_client_udp_path_binds_before_send_and_receives_round_trip(self):
        report, record = self.run_contract(kind='udp', address='implicit')
        self.assertEqual((report['before_result'], report['before_address']), (0, 0x7f000001))
        self.assertGreater(report['before_port'], 0)
        self.assertEqual((report['before_port'], report['port'], report['peer_port']),
                         (report['port'], report['port'], report['port']))
        self.assertEqual((report['address'], report['peer_address']), (0x7f000001, 0x7f000001))
        self.assertEqual((report['bytes_received'], report['bind_calls'], report['name_calls']), (3, 1, 1))
        self.assertIn('protocol=udp address=127.0.0.1', record)

    def test_default_client_udp_remains_implicit_with_unchanged_datagram_transfer(self):
        report, record = self.run_contract(None, kind='udp', address='implicit')
        self.assertEqual((report['status'], report['before_port'], report['address']), (0, 0, 0))
        self.assertEqual((report['bind_calls'], report['name_calls'], report['bytes_received']), (0, 0, 3))
        self.assertGreater(report['port'], 0)
        self.assertEqual(record, '')

    def test_client_udp_attempt_prevents_late_activation(self):
        report, record = self.run_contract(kind='udp', address='implicit', timing='late')
        self.assertEqual((report['status'], report['error']), (-1, report['invalid_state']))
        self.assertEqual((report['bind_calls'], report['name_calls']), (0, 0))
        self.assertEqual(record, '')

    def test_client_udp_invalid_environment_fails_before_socket_creation(self):
        for value in ('', '0', '01', 'true', '1 '):
            with self.subTest(value=value):
                report, record = self.run_contract(value, kind='udp', address='implicit')
                self.assertEqual((report['status'], report['error']), (-1, report['invalid_parameter']))
                self.assertEqual((report['bind_calls'], report['name_calls']), (0, 0))
                self.assertEqual(record, '')

    def test_client_udp_unverified_endpoint_closes_before_first_datagram(self):
        for corruption in ('fail-name', 'wrong-ip', 'zero-port', 'wrong-family', 'fail-type', 'wrong-type'):
            with self.subTest(corruption=corruption):
                report, record = self.run_contract(kind='udp', address='implicit', corruption=corruption, code=2)
                self.assert_fatal_closed(report, record)


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        sys.argv.remove('--require-windows')
        if os.name != 'nt' or not shutil.which('cl'):
            raise SystemExit('Windows loopback contracts require an initialized x86 MSVC environment')
    unittest.main(verbosity=2)
