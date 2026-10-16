from pathlib import Path
import importlib.util
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("android_batch", Path(__file__).parents[1] / "run_android_batch.py")
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class IndependentSuites(unittest.TestCase):
    def test_protocol_failure_does_not_skip_adapter(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(batch.subprocess, "run", side_effect=[SimpleNamespace(returncode=1), SimpleNamespace(returncode=0)]) as run:
                result = batch.run_suites("adb", "emulator-5554", Path(temporary))
            self.assertEqual(run.call_count, 2)
            self.assertIn("run_adapter_android.py", run.call_args_list[1].args[0][1])
            self.assertFalse(result["passed"])
            self.assertEqual(result["suites"]["world-adapter"]["driver_exit_code"], 0)

    def test_adapter_failure_fails_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(batch.subprocess, "run", side_effect=[SimpleNamespace(returncode=0), SimpleNamespace(returncode=2)]):
                result = batch.run_suites("adb", "emulator-5554", Path(temporary))
            self.assertFalse(result["passed"])
            self.assertEqual(result["suites"]["protocol"]["driver_exit_code"], 0)
