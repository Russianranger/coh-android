"""New deterministic adapter controls; no Windows or network execution."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
WINDOWS=HERE/'windows'


class DbUdpWinsockTests(unittest.TestCase):
    def test_full_width_handles_datagrams_truncation_and_failed_cleanup(self):
        with tempfile.TemporaryDirectory() as name:
            for mode,flags in (
                ('release',['-O2']),
                ('asan_ubsan',['-O1','-g','-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer','-fno-pie','-no-pie'])):
                target=Path(name)/mode
                subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                    '-DCOH_DB_WIN_TEST','-I'+str(ROOT/'native-android/include'),
                    *flags,WINDOWS/'db_udp_winsock.c',WINDOWS/'test_db_udp_winsock.c',
                    '-o',target],check=True,capture_output=True)
                result=subprocess.run([target],check=True,capture_output=True,timeout=10,
                    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                        UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
                self.assertEqual(json.loads(result.stdout),dict(passed=True,checks=65,
                    real_windows_execution=False,real_db_login_verified=False))
                self.assertEqual(result.stderr,b'')

    def test_unchanged_ordinary_udp_translation_unit_compiles_under_private_adapter(self):
        with tempfile.TemporaryDirectory() as name:
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2',
                '-DCOH_DB_WIN_TEST','-I'+str(ROOT/'native-android/include'),
                '-I'+str(WINDOWS/'compat'),'-c',WINDOWS/'wrapped_db_udp.c',
                '-o',Path(name)/'udp.o'],check=True,capture_output=True)


if __name__=='__main__':unittest.main()
