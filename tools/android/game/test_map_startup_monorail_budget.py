"""Actual x86 Win32 station bridge with deterministic elapsed-clock fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import secrets
import shutil
import subprocess
import struct
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import map_startup_monorail_budget as budget

SESSION = '0123456789abcdef0123456789abcdef'
FIXTURE = 'database/map-startup/tests/monorail_budget_contract.c'
CLOCK_PRELUDE = (b'#include "wine_monorail.h"\n'
                 b'DWORD WINAPI cohMonorailFixtureTick(void);\n'
                 b'#define GetTickCount cohMonorailFixtureTick\n')


def pin(path):
    raw = Path(path).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class WindowsNativeBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != 'nt' or not shutil.which('cl'):
            raise RuntimeError('Genuine initialized x86 Windows MSVC required; native budget acceptance never skips')
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-native-monorail-clock-')
        cls.directory = Path(cls.temporary.name)
        originals = budget.monorail.overlay_bytes()
        cls.executables = {}
        for label, raw in (('historical', originals[budget.SOURCE]), ('candidate', budget.patch_source(originals[budget.SOURCE]))):
            target = cls.directory / label
            target.mkdir()
            # Parse Windows' real imported API declarations before substituting
            # just this bridge's elapsed clock. Transport APIs remain genuine.
            (target / 'wine_monorail.c').write_bytes(CLOCK_PRELUDE + raw)
            (target / 'wine_monorail.h').write_bytes(originals[budget.HEADER])
            executable = target / 'monorail-clock.exe'
            subprocess.run(['cl', '/nologo', '/W4', '/WX', '/O2', '/MT', '/D_CRT_SECURE_NO_WARNINGS',
                f'/I{target}', str(target / 'wine_monorail.c'),
                str(ROOT / FIXTURE), f'/Fe:{executable}'], cwd=target, check=True, capture_output=True, text=True)
            binary = executable.read_bytes()
            pe = struct.unpack_from('<I', binary, 0x3c)[0]
            if binary[:2] != b'MZ' or binary[pe:pe + 4] != b'PE\0\0' or struct.unpack_from('<H', binary, pe + 4)[0] != 0x14c:
                raise RuntimeError('Actual x86 PE32 native bridge fixture required')
            cls.executables[label] = executable
        cls.native_executable = cls.executables['candidate'].read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def start(self, *, label='candidate', token=SESSION):
        environment = os.environ.copy()
        for key in (budget.CONTRACT['environment_variable'], budget.CONTRACT['reply_environment_variable']):
            environment.pop(key, None)
        reply = self.directory / ('reply-' + secrets.token_hex(8) + '.txt')
        if token is not None:
            environment[budget.CONTRACT['environment_variable']] = token
            environment[budget.CONTRACT['reply_environment_variable']] = str(reply)
        child = subprocess.Popen([str(self.executables[label])], env=environment, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        child.lines = queue.Queue()
        def read():
            for row in child.stdout:
                if row.strip(): child.lines.put(row.strip())
        child.reader = threading.Thread(target=read, daemon=True)
        child.reader.start()
        self.addCleanup(self.close, child)
        status = self.receive(child).split()
        self.assertEqual(status[0], 'STATUS')
        return child, reply, status

    def close(self, child):
        if child.poll() is None: child.terminate()
        child.wait(timeout=10)
        child.reader.join(timeout=10)
        for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def receive(self, child):
        try: return child.lines.get(timeout=5)
        except queue.Empty: raise AssertionError('Actual native station fixture failed to flush its result')

    def send(self, child, command):
        child.stdin.write(command + '\n')
        child.stdin.flush()
        return self.receive(child)

    def request(self, child):
        event = self.send(child, 'request')
        self.assertIn('kind=station_request', event)
        self.assertEqual(self.receive(child), 'REQUEST 1')
        request = re.search(r'\brequest=([1-9][0-9]*) ', event)
        self.assertIsNotNone(request)
        return int(request[1])

    def reply(self, path, status, request_sequence=1, **changes):
        fields = dict(session=SESSION, pid=int(status[2]), request=request_sequence, target=5)
        fields.update(changes)
        raw = ('COH_MONORAIL_REPLY_V1 session={session} pid={pid} request={request} target={target} ready=1\n').format(**fields)
        path.write_bytes(raw.encode('ascii'))
        return raw

    def departed(self, child):
        event = self.send(child, 'poll')
        self.assertIn('kind=station_departure', event)
        self.assertEqual(self.receive(child), 'POLL 1')
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')

    def test_historical_600_second_bridge_reproduces_failure_at_650_seconds(self):
        child, path, status = self.start(label='historical')
        request = self.request(child)
        self.send(child, 'advance 650000')
        self.reply(path, status, request)
        self.assertEqual(self.send(child, 'poll'), 'POLL -1')
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')

    def test_candidate_pending_request_accepts_exact_reply_at_650_seconds(self):
        child, path, status = self.start()
        request = self.request(child)
        self.send(child, 'advance 650000')
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')
        self.reply(path, status, request)
        self.send(child, 'advance 250')
        self.departed(child)

    def test_native_boundary_is_inclusive_720_seconds_and_expires_afterward(self):
        child, path, status = self.start()
        request = self.request(child)
        self.reply(path, status, request)
        self.send(child, 'advance 720000')
        self.departed(child)
        child, path, status = self.start()
        request = self.request(child)
        self.reply(path, status, request)
        self.send(child, 'advance 720001')
        self.assertEqual(self.send(child, 'poll'), 'POLL -1')
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')

    def test_wrong_token_pid_request_target_and_extra_bytes_cannot_authorize(self):
        child, path, status = self.start()
        request = self.request(child)
        self.send(child, 'advance 650000')
        for changed in ({'session': 'a' * 32}, {'pid': int(status[2]) + 1},
                        {'request': request + 1}, {'target': 1}):
            self.reply(path, status, request, **changed)
            self.send(child, 'advance 250')
            self.assertEqual(self.send(child, 'poll'), 'POLL 0')
        raw = self.reply(path, status, request)
        path.write_bytes((raw + 'extra').encode('ascii'))
        self.send(child, 'advance 250')
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')
        self.reply(path, status, request)
        self.send(child, 'advance 250')
        self.departed(child)

    def test_cancel_and_retry_require_new_native_request_sequence(self):
        child, path, status = self.start()
        first = self.request(child)
        self.reply(path, status, first)
        self.assertEqual(self.send(child, 'request'), 'REQUEST 0')
        self.assertEqual(self.send(child, 'cancel'), 'CANCELLED')
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')
        second = self.request(child)
        self.assertGreater(second, first)
        self.send(child, 'advance 250')
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')
        self.reply(path, status, second)
        self.send(child, 'advance 250')
        self.departed(child)

    def test_expired_request_and_late_old_reply_do_not_authorize_new_request(self):
        child, path, status = self.start()
        first = self.request(child)
        self.send(child, 'advance 720001')
        self.assertEqual(self.send(child, 'poll'), 'POLL -1')
        self.reply(path, status, first)
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')
        second = self.request(child)
        self.assertGreater(second, first)
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')
        self.reply(path, status, second)
        self.send(child, 'advance 250')
        self.departed(child)

    def test_unsigned_gettickcount_wrap_retains_correct_elapsed_lifetime(self):
        child, path, status = self.start()
        self.send(child, 'tick 4294967280')
        request = self.request(child)
        self.send(child, 'advance 650000')
        self.reply(path, status, request)
        self.departed(child)

    def test_disabled_and_malformed_tokens_never_create_station_request(self):
        for token, expected in ((None, '0'), ('bad', '-1'), ('F' * 32, '-1')):
            child, _, status = self.start(token=token)
            self.assertEqual(status[1], expected)
            self.assertEqual(self.send(child, 'request'), 'REQUEST 0')

    def test_foreign_character_or_route_is_refused_and_foreign_poll_cancels(self):
        child, path, status = self.start()
        self.assertEqual(self.send(child, 'foreignrequest'), 'FOREIGN 0 0 0')
        request = self.request(child)
        self.reply(path, status, request)
        self.assertEqual(self.send(child, 'foreignpoll'), 'POLL -1')
        self.assertEqual(self.send(child, 'poll'), 'POLL 0')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-windows', action='store_true')
    parser.add_argument('--evidence', type=Path)
    args, extra = parser.parse_known_args()
    if os.name != 'nt' or not shutil.which('cl'):
        raise SystemExit('Real initialized x86 Windows MSVC required; genuine native budget acceptance cannot be simulated')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WindowsNativeBudgetTests))
    passed = result.wasSuccessful() and not result.skipped and result.testsRun == 9
    receipt = {'format': 1, 'role': 'native_map_startup_monorail_budget_fixtures',
        'status': 'passed' if passed else 'failed', 'platform': 'win32', 'architecture': 'x86',
        'tests_run': result.testsRun, 'skipped': len(result.skipped), 'errors': len(result.errors),
        'failures': len(result.failures), 'original_source_sha256': budget.BASE_SOURCE_SHA256,
        'candidate_source_sha256': budget.PATCHED_SOURCE_SHA256,
        'compiled_clock_instrumentation': {'bytes': len(CLOCK_PRELUDE),
            'sha256': hashlib.sha256(CLOCK_PRELUDE).hexdigest(),
            'scope': 'GetTickCount_calls_in_actual_bridge_only_transport_APIs_retained'},
        'elapsed_clock': 'deterministic_GetTickCount_actual_Win32_transport',
        'historical_650_seconds_timeout_reproduced': passed,
        'candidate_650_seconds_authorization_verified': passed,
        '720_second_boundary_and_expiry_verified': passed,
        'wrong_identity_cancel_retry_late_reply_and_wrap_verified': passed,
        'native_source_executed': passed, 'physical_thor_execution_validated': False,
        'physical_startup_timing_validated': False,
        'sources': {name: pin(ROOT / name) for name in ('tools/map_startup_monorail_budget.py',
            'tools/android/game/test_map_startup_monorail_budget.py', FIXTURE,
            'database/monorail/overlay/' + budget.SOURCE, 'database/monorail/overlay/' + budget.HEADER)}}
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        binary = args.evidence.with_suffix('.exe')
        if hasattr(WindowsNativeBudgetTests, 'native_executable'):
            binary.write_bytes(WindowsNativeBudgetTests.native_executable)
            receipt['native_binary'] = pin(binary)
            receipt['native_binary_file'] = binary.name
        args.evidence.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, sort_keys=True))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
