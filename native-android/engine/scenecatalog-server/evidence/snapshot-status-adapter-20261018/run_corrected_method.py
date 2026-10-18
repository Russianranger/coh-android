#!/usr/bin/env python3
"""Run only the corrected three-case adapter method; no old control replay."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import test_snapshot_status_adapter as tests

suite=unittest.TestSuite([tests.SnapshotStatusAdapter('test_native_exception_restores_original_before_final_binding')])
result=unittest.TextTestRunner(resultclass=tests.ControlledResult,verbosity=1).run(suite)
print(json.dumps(tests.case_counts(result),sort_keys=True))
raise SystemExit(0 if result.wasSuccessful() else 1)
