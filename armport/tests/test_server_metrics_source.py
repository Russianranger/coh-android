#!/usr/bin/env python3
"""Source identity and lineage checks; no compiler or device execution."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/scripts'))
import prepare_server_metrics_source as source

UPSTREAM_ROOT = Path(os.environ.get('ARMPORT_SERVER_BASELINE_ROOT', ROOT)).resolve()


def find_startup_receipt(value):
    if isinstance(value, dict):
        if value.get('build_role') == 'map_startup_certified_animation':
            return value
        for child in value.values():
            result = find_startup_receipt(child)
            if result is not None:
                return result
    if isinstance(value, list):
        for child in value:
            result = find_startup_receipt(child)
            if result is not None:
                return result
    return None


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(prefix='coh-server-source-test-')
        cls.baseline = Path(cls.storage.name) / 'baseline'
        progress, _ = source.modules(UPSTREAM_ROOT)
        progress.prepare(cls.baseline, UPSTREAM_ROOT)
        cls.base = json.loads((cls.baseline / progress.RECEIPT).read_text())
        cls.receipt = source.expected_receipt('retained_progress', cls.base, UPSTREAM_ROOT)
        publication = UPSTREAM_ROOT / 'docs/android-evidence/client-map-startup-0.13.32-publication.json'
        cls.startup_base = find_startup_receipt(json.loads(publication.read_text()))
        assert cls.startup_base is not None

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-server-source-case-')
        self.stage = Path(self.temporary.name)
        names = set(self.receipt['retained_sha256']) | set(self.receipt['source_sha256'])
        names.update(self.receipt['baseline_receipts_sha256'])
        for name in names:
            target = self.stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.baseline / name, target)

    def tearDown(self):
        self.temporary.cleanup()

    def apply(self, **kwargs):
        return source.apply_metrics(self.stage, 'retained_progress', UPSTREAM_ROOT, **kwargs)

    def test_apply_preserves_predecessor_receipts_and_progress_hooks(self):
        old_receipts = {name: (self.stage / name).read_bytes()
                        for name in self.receipt['baseline_receipts_sha256']}
        old_loop = (self.stage / source.SVR).read_text()
        result = self.apply(required_baseline_receipt=self.base)
        self.assertEqual(result, self.receipt)
        self.assertEqual(source.verify_prepared(self.stage, UPSTREAM_ROOT), result)
        new_loop = (self.stage / source.SVR).read_text()
        self.assertEqual(new_loop.count('cohMapProgressMark('), old_loop.count('cohMapProgressMark('))
        self.assertIn('armportServerMetricsTickBegin();', new_loop)
        self.assertLess(new_loop.index('armportServerMetricsTickBegin();'),
                        new_loop.index('cohMapProgressMark(COH_MAP_STAGE_LOOP_PRE_TICK);'))
        self.assertLess(new_loop.index('cohMapProgressMark(COH_MAP_STAGE_SLEEP_DONE);'),
                        new_loop.index('armportServerMetricsLoopEnd();'))
        for name, data in old_receipts.items():
            self.assertEqual((self.stage / name).read_bytes(), data)
        with self.assertRaisesRegex(ValueError, 'already staged'):
            self.apply()

    def test_changed_preimage_refused_before_any_write(self):
        path = self.stage / source.SVR
        path.write_bytes(path.read_bytes() + b'/* changed input */\n')
        before = (self.stage / source.FILE).read_bytes()
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.apply()
        self.assertEqual((self.stage / source.FILE).read_bytes(), before)
        self.assertFalse((self.stage / source.IMPL).exists())
        self.assertFalse((self.stage / source.RECEIPT).exists())

    def test_existing_header_and_linked_header_refused(self):
        path = self.stage / source.HEADER
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'already exists or is linked'):
            self.apply()
        path.unlink()
        path.symlink_to(self.stage / 'missing')
        with self.assertRaisesRegex(ValueError, 'already exists or is linked'):
            self.apply()

    def test_wrong_donor_and_unexpected_lineage_refused(self):
        changed = copy.deepcopy(self.base)
        changed['runtime_validation'] = 'accepted'
        with self.assertRaisesRegex(ValueError, 'donor baseline'):
            self.apply(required_baseline_receipt=changed)
        (self.stage / 'character-events-build-input.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Unexpected source lineage'):
            self.apply()

    def test_actual_retained_donor_eol_profile_is_reproduced_before_overlays(self):
        path = UPSTREAM_ROOT / 'docs/android-evidence/mapserver-progress-package-36630872719.json'
        donor = json.loads(path.read_text())['inputs']['mapserver_progress']['manifest']['build_input']
        fresh = self.stage / 'actual-donor-source'
        receipt = source.prepare(fresh, 'retained_progress', UPSTREAM_ROOT,
                                 required_baseline_receipt=donor)
        self.assertEqual(receipt['baseline_receipt'], donor)
        pg = donor['game_build_input']['postgresql_build_input']
        for name, wanted in pg['overlay_sha256'].items():
            self.assertEqual(source.digest((fresh / name).read_bytes()), wanted)
        self.assertEqual(source.verify_prepared(fresh, UPSTREAM_ROOT), receipt)

    def test_post_stage_source_or_receipt_tamper_refused(self):
        self.apply()
        path = self.stage / source.IMPL
        old = path.read_bytes()
        path.write_bytes(old + b'\n')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            source.verify_prepared(self.stage, UPSTREAM_ROOT)
        path.write_bytes(old)
        path = self.stage / self.receipt['baseline_receipt_name']
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Baseline receipt changed'):
            source.verify_prepared(self.stage, UPSTREAM_ROOT)

    def test_contract_pin_and_json_type_tamper_refused(self):
        for field, value in [('format', True), ('native_execution_validated', True),
                             ('patch', {'path': source.PATCH, 'sha256': '0' * 64})]:
            changed = copy.deepcopy(self.receipt)
            changed[field] = value
            with self.assertRaisesRegex(ValueError, 'receipt differs'):
                source.validate_receipt(changed, UPSTREAM_ROOT)

    def test_published_host_report_binds_exact_source_and_host_scope(self):
        path = ROOT / 'armport/evidence/server-metrics-host-checks.json'
        document = json.loads(path.read_text())
        source.validate_test_report(document, self.receipt, UPSTREAM_ROOT)
        for key, value in [('shipping_binary_executed', True),
                           ('unpatched_control_failed', False),
                           ('build_input_sha256', '0' * 64),
                           ('positive_cases', ['window'])]:
            changed = copy.deepcopy(document)
            changed[key] = value
            with self.assertRaisesRegex(ValueError, 'report identity differs'):
                source.validate_test_report(changed, self.receipt, UPSTREAM_ROOT)

    def test_certified_startup_receipt_and_720_second_budget_retained(self):
        receipt = source.expected_receipt('thor_certified_startup', self.startup_base, UPSTREAM_ROOT)
        self.assertEqual(receipt['baseline_receipt'], self.startup_base)
        self.assertEqual(receipt['baseline_receipt']['contract']['native_station_prepare_seconds'], 720)
        self.assertEqual(receipt['retained_sha256']['MapServer/src/svr/wine_monorail.c'],
                         self.startup_base['monorail_budget']['patched_sha256']['MapServer/src/svr/wine_monorail.c'])
        _, startup = source.modules(UPSTREAM_ROOT)
        self.assertEqual(receipt['retained_sha256'][startup.TABLE],
                         self.startup_base['animation_certificate']['generated_table']['sha256'])
        inputs, images = source.native_images('thor_certified_startup', self.startup_base, UPSTREAM_ROOT)
        self.assertEqual(images[source.SVR], source.patch_loop(inputs[source.SVR]))
        self.assertIn(b'cohMonorailInit', images[source.SVR])
        changed = copy.deepcopy(self.startup_base)
        changed['contract']['native_station_prepare_seconds'] = 600
        with self.assertRaisesRegex(ValueError, 'Baseline source receipt differs'):
            source.expected_receipt('thor_certified_startup', changed, UPSTREAM_ROOT)
        # The real pinned animation table is required for full staging. This
        # receipt-only test must never imply it generated or executed that data.
        self.assertFalse(receipt['native_execution_validated'])

    def test_modern_generation_refuses_cached_validator_from_another_root(self):
        _, startup = source.modules(UPSTREAM_ROOT)
        target = self.stage / 'never-created'
        with mock.patch.object(startup.certificate, 'ROOT', self.stage / 'different-root'):
            with self.assertRaisesRegex(ValueError, 'modules were imported from another root'):
                source.prepare(target, 'thor_certified_startup', UPSTREAM_ROOT,
                               required_baseline_receipt=self.startup_base)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream-root', type=Path, default=UPSTREAM_ROOT)
    args, rest = parser.parse_known_args()
    UPSTREAM_ROOT = args.upstream_root.resolve()
    unittest.main(argv=[sys.argv[0], *rest])
