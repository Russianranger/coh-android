"""Run the real CI shell block with a failing control process, under bash -e."""
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


def control_block():
    workflow = (ROOT / '.github/workflows/armport-build.yml').read_text()
    step = workflow.split('      - name: Prove collision triangles preserve the native grid\n', 1)[1]
    return textwrap.dedent(step.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0])


def run_control(block, result):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        script = root / 'armport/tests/polycell_allocation.py'
        script.parent.mkdir(parents=True)
        script.write_text(f'print("injected control output")\nraise SystemExit({result})\n')
        shell = root / 'step.sh'
        shell.write_text(block)
        return subprocess.run(['bash', '-e', str(shell)], cwd=root,
            env=dict(os.environ, RUNNER_TEMP=tmp), capture_output=True, text=True)


class GridWorkflowGate(unittest.TestCase):
    def test_failed_control_fails_step_despite_successful_tee(self):
        result = run_control(control_block(), 23)
        self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
        self.assertIn('injected control output', result.stdout)
        self.assertNotIn('::notice', result.stdout)

    def test_successful_control_emits_evidence_notice(self):
        result = run_control(control_block(), 0)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('::notice title=ArmPort native grid allocation::injected control output%0A', result.stdout)
