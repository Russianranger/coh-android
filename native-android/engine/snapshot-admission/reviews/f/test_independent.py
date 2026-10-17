#!/usr/bin/env python3
"""Independent black-box hostile-container controls; never extracts members."""
import argparse
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--module', '--admit', dest='module', type=Path, required=True)
parser.add_argument('--archive', '--capture-zip', dest='archive', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
args, remainder = parser.parse_known_args()
module_before = hashlib.sha256(args.module.read_bytes()).hexdigest()
trust_before = hashlib.sha256(args.module.with_name('capture-trust.json').read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('reviewed_admission', args.module)
admit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = admit
spec.loader.exec_module(admit)
with zipfile.ZipFile(args.archive) as z:
    authentic = [(i.filename, z.read(i)) for i in z.infolist()]

class IndependentContainers(unittest.TestCase):
    def check_zip(self, transform=lambda rows: rows, compression=zipfile.ZIP_DEFLATED,
                  mutate_info=None, expect=True):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'input.zip'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(path, 'w', compression=compression) as z:
                    for name, raw in transform(list(authentic)):
                        info = zipfile.ZipInfo(name)
                        info.compress_type = compression
                        info.external_attr = (stat.S_IFREG | 0o600) << 16
                        if mutate_info:
                            mutate_info(info)
                        z.writestr(info, raw)
            if expect:
                return admit.validate_archive(path)
            with self.assertRaises(admit.AdmissionError):
                admit.validate_archive(path)

    def test_authentic_scope_and_frozen_result(self):
        result = admit.validate_archive(args.archive)
        self.assertTrue(result.offline_analysis_only)
        for field in ('live_groups_transaction', 'physical_generation_verified',
                      'graph_publication_authorized', 'actor_publication_authorized',
                      'renderer_authorized', 'world_authority'):
            self.assertIs(getattr(result, field), False)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.world_authority = True

    def test_retained_capture_cleanup_receipts(self):
        data = dict(authentic)
        receipt = json.loads(data['capture/capture-receipt.json'])
        binding = json.loads(data['capture/snapshot-binding.json'])
        for flag in ('cleanup_verified', 'owned_process_groups_absent',
                     'source_runtime_unchanged', 'passed'):
            self.assertIs(receipt[flag], True)
        self.assertEqual(receipt['wine_prefix_cleanup'],
                         dict(private_fresh_prefix=True, kill_exit_code=0, wait_exit_code=0))
        self.assertEqual(receipt['retained_failed_outputs'], [])
        self.assertIs(receipt['hard_process_memory_cap_established'], False)
        self.assertIs(receipt['log_limits_polled_not_kernel_enforced'], True)
        for row in receipt['diagnostics']:
            payload = data['capture/' + row['file']]
            self.assertEqual(row['bytes'], len(payload))
            self.assertEqual(row['sha256'], hashlib.sha256(payload).hexdigest())
        self.assertEqual(len(receipt['diagnostics']), 19)
        for kind, name in (('catalog', 'catalog.cohcat'), ('snapshot', 'runtime.cohrts')):
            payload = data['capture/' + name]
            identity = dict(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
            self.assertEqual(receipt[kind], identity)
            self.assertEqual(binding[kind], identity)

    def test_deflate_metadata_repack(self):
        self.check_zip()

    def test_duplicate_member(self):
        self.check_zip(lambda r: r + [r[0]], expect=False)

    def test_missing_member(self):
        self.check_zip(lambda r: r[1:], expect=False)

    def test_unknown_member(self):
        self.check_zip(lambda r: r + [('extra', b'')], expect=False)

    def test_hostile_names(self):
        for name in ('../outside', '/absolute', 'C:/outside', 'capture/../runtime.cohrts',
                     'capture\\runtime.cohrts', './capture/runtime.cohrts'):
            with self.subTest(name=name):
                self.check_zip(lambda r: [(name, r[0][1])] + r[1:], expect=False)

    def test_member_content_drift(self):
        self.check_zip(lambda r: [(r[0][0], bytes([r[0][1][0] ^ 1]) + r[0][1][1:])] + r[1:], expect=False)

    def test_member_size_drift(self):
        self.check_zip(lambda r: [(r[0][0], r[0][1] + b'x')] + r[1:], expect=False)

    def test_symlink_refused(self):
        self.check_zip(mutate_info=lambda i: setattr(i, 'external_attr', (stat.S_IFLNK | 0o777) << 16), expect=False)

    def test_special_modes_refused(self):
        for mode in (stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFBLK, stat.S_IFCHR):
            with self.subTest(mode=mode):
                self.check_zip(mutate_info=lambda i: setattr(i, 'external_attr', (mode | 0o600) << 16), expect=False)

    def test_bzip2_refused_before_decode(self):
        self.check_zip(compression=zipfile.ZIP_BZIP2, expect=False)

    def test_lzma_refused_before_decode(self):
        self.check_zip(compression=zipfile.ZIP_LZMA, expect=False)

    def test_archive_bound(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'oversized.zip'
            with p.open('wb') as stream:
                stream.truncate(admit.MAX_ARCHIVE + 1)
            with self.assertRaises(admit.AdmissionError):
                admit.validate_archive(p)

    def test_truncated_zip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'truncated.zip'
            p.write_bytes(args.archive.read_bytes()[:-30])
            with self.assertRaises(admit.AdmissionError):
                admit.validate_archive(p)

    def test_duplicate_json_keys_refused(self):
        with self.assertRaises(admit.AdmissionError):
            admit.decode(b'{"passed": false, "passed": true}')

    def test_nonfinite_json_refused(self):
        for value in (b'NaN', b'Infinity', b'-Infinity'):
            with self.subTest(value=value), self.assertRaises(admit.AdmissionError):
                admit.decode(b'{"generation":' + value + b'}')

suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentContainers)
result = unittest.TextTestRunner(verbosity=2).run(suite)
stable = (module_before == hashlib.sha256(args.module.read_bytes()).hexdigest() and
          trust_before == hashlib.sha256(args.module.with_name('capture-trust.json').read_bytes()).hexdigest())
args.receipt.write_text(json.dumps({
    'schema': 'coh-independent-snapshot-review-v1',
    'validator_sha256': hashlib.sha256(args.module.read_bytes()).hexdigest(),
    'trust_sha256': hashlib.sha256(args.module.with_name('capture-trust.json').read_bytes()).hexdigest(),
    'archive_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
    'tests_run': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors),
    'source_stable': stable, 'passed': result.wasSuccessful() and stable,
    'memory_claim': 'No process RSS or kernel memory-cap measurement performed.',
    'real_server_executed': False, 'live_world_accepted': False,
}, indent=2) + '\n')
raise SystemExit(0 if result.wasSuccessful() and stable else 1)
