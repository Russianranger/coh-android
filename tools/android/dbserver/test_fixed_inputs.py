"""Check the real Windows fixed-input opt-in parser and its acknowledgment."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
OVERLAY = ROOT / 'database/wine-dbserver/overlay/DBServer/src'
CONTRACT = ROOT / 'database/wine-dbserver/tests/fixed_inputs_windows_contract.c'
ENVIRONMENT = 'COH_WINE_DB_FIXED_INPUTS'
ACK = ('COH_WINE_DB_FIXED_INPUTS=1 active: directory monitoring disabled; '
       'initial reads and lookup mode preserved')


@unittest.skipUnless(os.name == 'nt', 'fixed-input environment contract requires Windows')
class FixedInputsWindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cl'):
            raise RuntimeError('x86 MSVC environment must be initialized for fixed-input tests')
        cls.build = tempfile.TemporaryDirectory(prefix='coh-fixed-inputs-build-')
        cls.binary = Path(cls.build.name) / 'fixed-inputs-contract.exe'
        try:
            subprocess.run(['cl', '/nologo', '/W4', '/WX', '/O2', '/MT',
                            '/D_WIN32_WINNT=0x0601', f'/I{OVERLAY}', str(CONTRACT),
                            str(OVERLAY / 'wine_fixed_inputs.c'), f'/Fe:{cls.binary}'],
                           cwd=cls.build.name, check=True)
        except BaseException:
            cls.build.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def run_contract(self, value=None, *, late_cache=False):
        env = {key: value for key, value in os.environ.items()
               if key.upper() != ENVIRONMENT}
        if value is not None:
            env[ENVIRONMENT] = value
        with tempfile.TemporaryDirectory(prefix='coh-fixed-inputs-case-') as directory:
            command = [str(self.binary)]
            if late_cache:
                command.append('--late-cache')
            result = subprocess.run(command, cwd=directory, env=env, capture_output=True,
                                    text=True, timeout=10, check=True)
            self.assertEqual(list(Path(directory).iterdir()), [],
                             'the startup option must not create any files')
        return json.loads(result.stdout), result.stderr

    def test_absent_option_never_calls_library_or_acknowledges(self):
        for late_cache in (False, True):
            with self.subTest(late_cache=late_cache):
                result, stderr = self.run_contract(late_cache=late_cache)
                self.assertEqual(result['status'], 0)
                self.assertEqual(result['hook_calls'], 0)
                self.assertEqual(stderr, '')

    def test_exact_one_calls_library_once_then_acknowledges(self):
        result, stderr = self.run_contract('1')
        self.assertEqual(result['status'], 1)
        self.assertEqual(result['hook_calls'], 1)
        self.assertEqual(stderr, ACK + '\n')

    def test_invalid_options_never_call_library_or_acknowledge(self):
        for value in ('', '0', '01', 'true', ' 1', '1 ', '1\n', '1' * 4096):
            with self.subTest(value=value[:24], length=len(value)):
                result, stderr = self.run_contract(value)
                self.assertEqual(result['status'], -1)
                self.assertEqual(result['error'], result['invalid_parameter'])
                self.assertEqual(result['hook_calls'], 0)
                self.assertEqual(stderr, '')

    def test_existing_cache_refusal_does_not_acknowledge_activation(self):
        result, stderr = self.run_contract('1', late_cache=True)
        self.assertEqual(result['status'], -1)
        self.assertEqual(result['error'], result['invalid_state'])
        self.assertEqual(result['hook_calls'], 1)
        self.assertEqual(stderr, '')


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        sys.argv.remove('--require-windows')
        if os.name != 'nt' or not shutil.which('cl'):
            raise SystemExit('Windows contracts require an initialized x86 MSVC environment')
    unittest.main(verbosity=2)
