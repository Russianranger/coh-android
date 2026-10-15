"""Exact derivative station-clock staging keeps the historical bridge intact."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest

import map_startup_monorail_budget as budget


class NativeBudgetSourceTests(unittest.TestCase):
    def fixture(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-monorail-budget-source-')))
        for name, raw in budget.monorail.overlay_bytes().items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (root / budget.monorail.RECEIPT).write_text(json.dumps(budget.monorail.expected_receipt()))
        return root

    def test_only_one_timeout_literal_changes_and_original_bridge_remains_unchanged(self):
        originals = budget.monorail.overlay_bytes()
        patched = budget.patch_source(originals[budget.SOURCE])
        self.assertEqual(patched.replace(budget.NEW, budget.OLD), originals[budget.SOURCE])
        self.assertEqual(len(patched), len(originals[budget.SOURCE]))
        self.assertEqual(hashlib.sha256(patched).hexdigest(), budget.PATCHED_SOURCE_SHA256)
        self.assertEqual(budget.monorail.overlay_bytes(), originals)
        self.assertEqual(budget.monorail.CONTRACT['station_preparation_timeout_seconds'], 600)
        self.assertEqual(budget.CONTRACT['station_preparation_timeout_seconds'], 720)
        expected_contract = copy.deepcopy(budget.monorail.CONTRACT)
        expected_contract['station_preparation_timeout_seconds'] = 720
        self.assertEqual(budget.CONTRACT, expected_contract)

    def test_changed_duplicate_or_already_patched_native_source_is_refused(self):
        raw = budget.monorail.overlay_bytes()[budget.SOURCE]
        for changed in (raw + b'\n', raw.replace(b'250UL', b'200UL'), raw + budget.OLD,
                        raw.replace(budget.OLD, budget.NEW), raw.replace(b'THORHERO', b'CHANGED')):
            with self.subTest(changed=changed[-20:]), self.assertRaises(ValueError):
                budget.patch_source(changed)

    def test_stage_receipt_binds_only_changed_bridge_and_retains_exact_header(self):
        root = self.fixture()
        before = {name: (root / name).read_bytes() for name in budget.monorail.OVERLAY_FILES}
        historical_receipt = (root / budget.monorail.RECEIPT).read_bytes()
        receipt = budget.apply_budget_overlay(root)
        self.assertEqual(receipt, budget.expected_receipt())
        self.assertEqual(set(receipt['patched_sha256']), {budget.SOURCE})
        self.assertEqual((root / budget.HEADER).read_bytes(), before[budget.HEADER])
        self.assertEqual((root / budget.monorail.RECEIPT).read_bytes(), historical_receipt)
        self.assertEqual(json.loads((root / budget.RECEIPT).read_bytes()), receipt)
        self.assertEqual(receipt['build_targets'], ['MapServer'])
        self.assertEqual(receipt['contract']['disabled_by_default'], True)
        self.assertFalse(receipt['physical_startup_timing_validated'])

    def test_changed_prerequisite_receipt_cannot_enable_new_native_budget(self):
        root = self.fixture()
        path = root / budget.monorail.RECEIPT
        receipt = json.loads(path.read_bytes())
        receipt['contract']['station_preparation_timeout_seconds'] = 720
        path.write_text(json.dumps(receipt))
        before = (root / budget.SOURCE).read_bytes()
        with self.assertRaisesRegex(ValueError, 'historical monorail prerequisite'):
            budget.apply_budget_overlay(root)
        self.assertEqual((root / budget.SOURCE).read_bytes(), before)

    def test_changed_native_source_or_linked_header_is_refused_before_write(self):
        root = self.fixture()
        path = root / budget.SOURCE
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'staged input differs'):
            budget.apply_budget_overlay(root)
        root = self.fixture()
        path = root / budget.HEADER
        original = path.with_name('saved.h')
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaisesRegex(ValueError, 'staged input differs'):
            budget.apply_budget_overlay(root)

    def test_repeat_overlay_and_immutable_repo_staging_are_refused(self):
        root = self.fixture()
        budget.apply_budget_overlay(root)
        with self.assertRaisesRegex(ValueError, 'already staged'):
            budget.apply_budget_overlay(root)
        for root in (budget.ROOT, budget.ROOT / 'upstream/ouroboros'):
            with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'Immutable'):
                budget.apply_budget_overlay(root)


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        # Keep Linux source qualification separate from real Windows execution.
        # The native script compiles and executes the actual pinned C bridge.
        sys.argv = [str(budget.ROOT / 'tools/android/game/test_map_startup_monorail_budget.py'),
                    *['--evidence' if arg == '--native-evidence' else arg for arg in sys.argv[1:]]]
        runpy.run_path(sys.argv[0], run_name='__main__')
        raise SystemExit('Native Windows fixture unexpectedly returned without qualification')
    unittest.main()
