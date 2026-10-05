"""Finite host-only producer closure; gameplay algorithms remain immutable."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

import prepare_atlas_beacon_generator_source as producer


class AtlasBeaconSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.receipt = producer.expected()

    def test_source_scope_and_active_algorithms_are_exact(self):
        receipt = self.receipt
        self.assertEqual(set(receipt['source_sha256']), set(producer.FILES))
        self.assertEqual(set(receipt['patched_sha256']), set(producer.FILES))
        self.assertEqual(receipt['contract']['map_list_count'], 1)
        self.assertEqual(receipt['contract']['worker_count'], 1)
        self.assertFalse(receipt['contract']['shippable_gameplay_binary'])
        for name, digest in receipt['retained_algorithm_sha256'].items():
            self.assertEqual(producer.progress.sha256(producer.ROOT/'upstream/ouroboros'/name), digest)
        text = (producer.ROOT/'upstream/ouroboros/MapServer/src/beacon/beaconConnection.c').read_text()
        self.assertIn('void beaconProcessCombatBeacons(int doGenerate, int doProcess){\n    #if 0', text)

    def test_patch_contains_no_warning_suppression_and_has_real_readback(self):
        patch = (producer.ROOT/producer.PATCH).read_text()
        additions = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        for call in ('beaconDoesTheBeaconFileMatchTheMap(0)', 'beaconReload()', 'beaconPathFind(search',
                     'assert(paths == 32)', 'ipFromString("127.0.0.1")'):
            self.assertIn(call, additions)
        self.assertNotIn('THIS MAP HAS NOT BEEN BEACONIZED', additions)
        self.assertNotIn('beaconProcessCombatBeacons(', additions)
        self.assertNotIn('RegReader', additions)

    def test_containment_patch_applies_without_changing_algorithm_files(self):
        with tempfile.TemporaryDirectory(prefix='coh-beacon-stage-test-') as temporary:
            stage = Path(temporary)
            for name in producer.FILES + producer.RETAINED:
                target = stage/name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((producer.ROOT/'upstream/ouroboros'/name).read_bytes())
            producer.apply_patch(stage, (producer.ROOT/producer.PATCH).read_bytes())
            for name, digest in self.receipt['patched_sha256'].items():
                self.assertEqual(producer.progress.sha256(stage/name), digest)
            for name, digest in self.receipt['retained_algorithm_sha256'].items():
                self.assertEqual(producer.progress.sha256(stage/name), digest)


if __name__ == '__main__': unittest.main()
