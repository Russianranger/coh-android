"""Execute the actual portable C parsers used by the Win32 launcher bridge."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class BridgeProtocolTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'Native bridge contract requires a C compiler')
    def test_actual_bounded_frame_pid_command_and_child_argument_contracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / 'bridge-contract'
            subprocess.run([shutil.which('cc'), '-std=c99', '-Wall', '-Wextra', '-Werror',
                            str(ROOT / 'database/wine-game/bridge_protocol_contract.c'),
                            '-o', str(executable)], check=True, capture_output=True, timeout=30)
            result = subprocess.run([str(executable)], check=True, capture_output=True,
                                    text=True, timeout=10)
            self.assertIn('PASS bounded bridge frame, PID, command and child-argument contracts', result.stdout)


if __name__ == '__main__':
    unittest.main()
