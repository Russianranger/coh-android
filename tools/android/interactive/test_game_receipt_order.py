"""Exercise the real public .28 receipts against unchanged guest validators."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import repair_game_receipt_order as repair
import native_monorail_contract as monorail
import native_responsiveness_contract as retained


class GameReceiptOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (repair.ROOT/repair.DONOR_GAME_FIXTURE).read_bytes()
        cls.original = json.loads(cls.raw)

    def test_real_public_028_reproduces_both_guest_startup_failures(self):
        self.assertEqual(repair.pin(self.raw), repair.DONOR_MANIFEST)
        with self.assertRaisesRegex(repair.game.base.DiagnosticError, 'Game listener donor receipt bytes differ'):
            repair.game.game_listener_contract(self.original)
        with self.assertRaisesRegex(ValueError, 'Candidate MapServer producer manifest differs'):
            repair.game.mapserver_progress_contract(self.original)

    def test_original_receipt_bytes_are_independently_authenticated(self):
        originals = repair.original_receipts()
        for name, original in originals.items():
            self.assertEqual(original, self.original['inputs'][name]['manifest'])
            self.assertEqual(self.original['inputs'][name]['manifest_sha256'], repair.RECEIPTS[name])
        candidate_raw = (repair.ROOT/repair.CANDIDATE_FIXTURE).read_bytes()
        self.assertEqual(repair.pin(candidate_raw), repair.CANDIDATE_RECEIPT)
        self.assertEqual(retained.validate_receipt(json.loads(candidate_raw)),
                         retained.embedded_receipt(self.original))

    def test_repair_changes_only_key_order_and_passes_all_real_guest_contracts(self):
        raw = repair.repair_manifest(self.raw)
        self.assertNotEqual(raw, self.raw)
        value = json.loads(raw)
        self.assertEqual(value, self.original)
        self.assertEqual(repair.game.game_listener_contract(value), repair.game.evidence.GAME_LOOPBACK_METADATA)
        self.assertIsNotNone(repair.game.game_loopback_contract(value))
        self.assertEqual(repair.game.mapserver_progress_contract(value), monorail.progress_contract(value))
        self.assertEqual(monorail.embedded_receipt(value), value['native_monorail']['receipt'])
        for name, original in repair.original_receipts().items():
            encoded = json.dumps(value['inputs'][name]['manifest'], indent=2)+'\n'
            if name == 'loopback_game':
                encoded = encoded.replace('\n', '\r\n')
            self.assertEqual(hashlib.sha256(encoded.encode()).hexdigest(), repair.RECEIPTS[name])
            self.assertEqual(list(value['inputs'][name]['manifest']), list(original))

    def test_malformed_or_rehashed_donor_changes_are_rejected(self):
        for name, mutate in {
            'native': lambda p: p['files']['MapServer.exe'].update(sha256='f'*64),
            'listener': lambda p: p['inputs']['loopback_game']['manifest'].update(extra=True),
            'events': lambda p: p['inputs']['mapserver_progress']['manifest'].update(extra=True),
            'original-hash': lambda p: p['inputs']['mapserver_progress'].update(manifest_sha256='f'*64),
            'unknown-package-value': lambda p: p.update(extra=True),
        }.items():
            value = copy.deepcopy(self.original)
            mutate(value)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Exact public .28 game manifest required'):
                repair.repair_manifest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())

    def test_unchanged_validators_reject_mutations_after_repair(self):
        repaired = json.loads(repair.repair_manifest(self.raw))
        mutations = {
            'native-bytes': lambda p: p['files']['MapServer.exe'].update(sha256='f'*64),
            'listener-metadata': lambda p: p['inputs']['loopback_game']['manifest']['variants']['creation'].update(extra=True),
            'events-metadata': lambda p: p['inputs']['mapserver_progress']['manifest'].update(extra=True),
            'schema-provenance': lambda p: p['native_monorail']['receipt'].update(schema_sources_sha256={}),
            'events-original-hash': lambda p: p['inputs']['mapserver_progress'].update(manifest_sha256='f'*64),
        }
        for name, mutate in mutations.items():
            value = copy.deepcopy(repaired)
            mutate(value)
            with self.subTest(name=name), self.assertRaises((ValueError, repair.game.base.DiagnosticError)):
                repair.game.game_listener_contract(value)
                repair.game.mapserver_progress_contract(value)

    def test_repair_is_deterministic_across_fresh_hash_seed_processes(self):
        script = '''
import json,sys
sys.path.insert(0,sys.argv[1])
import repair_game_receipt_order as r
print(json.dumps(r.pin(r.repair_manifest((r.ROOT/r.DONOR_GAME_FIXTURE).read_bytes())),sort_keys=True))
'''
        outputs = []
        for seed in ('1', '73422'):
            result = subprocess.run([sys.executable, '-c', script, str(Path(repair.__file__).parent)],
                env=dict(os.environ, PYTHONHASHSEED=seed), capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            outputs.append(result.stdout)
        self.assertEqual(outputs[0], outputs[1])


if __name__ == '__main__':
    unittest.main()
