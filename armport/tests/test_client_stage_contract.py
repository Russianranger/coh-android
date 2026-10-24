"""Compile and execute the app's real pure-Java stage validator, without an APK."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ClientStageContract(unittest.TestCase):
    def test_actual_app_stage_acceptance(self):
        with tempfile.TemporaryDirectory() as output:
            subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                            '-d', output,
                            str(ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java'),
                            str(Path(__file__).with_name('java') / 'ArmPortAcceptanceTest.java')], check=True)
            result = subprocess.run(['java', '-cp', output,
                                     'io.github.russianranger.cohclientinteractive.ArmPortAcceptanceTest'],
                                    check=True, text=True, capture_output=True)
            self.assertIn('13 passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
