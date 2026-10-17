"""Negative controls of receipt consistency, using exact immutable retained inputs."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import verify_capture as v

class CaptureAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[4]
        cls.corpus = Path(os.environ.get('COH_CAPTURE_CORPUS', str(cls.repo / 'native-android/corpus/server-catalog/runtime-snapshot-38977202310')))
        cls.runtime = v.load_archive(cls.corpus / 'evidence.zip', v.PINS['evidence.zip'])
        cls.compiled = v.load_archive(cls.corpus / 'win32-compile.zip', v.PINS['win32-compile.zip'])

    def changed(self, name, change):
        data = self.runtime.copy()
        body = json.loads(data[name])
        change(body)
        data[name] = json.dumps(body).encode()
        return data

    def refuse(self, data):
        with self.assertRaises(ValueError):
            v.audit(data, self.compiled, self.repo)

    def test_exact(self):
        out = v.audit(self.runtime, self.compiled, self.repo)
        self.assertTrue(out['passed'])
        self.assertFalse(out['live_world_admitted'])

    def test_cleanup(self):
        self.refuse(self.changed('capture/capture-receipt.json', lambda d: d.update(cleanup_verified=False)))

    def test_live_claim(self):
        self.refuse(self.changed('capture/capture-receipt.json', lambda d: d.update(live_groups_transaction=True)))

    def test_unchanged_inventory(self):
        self.refuse(self.changed('capture/capture-receipt.json', lambda d: d['source_runtime_inventory'].update(files=0)))

    def test_generation_mismatch(self):
        self.refuse(self.changed('capture/capture-receipt.json', lambda d: d.update(generation=20261015)))

    def test_diagnostic_identity_mismatch(self):
        self.refuse(self.changed('runtime-graph-diagnostic.json', lambda d: d['capture_pins'].update(source_sha256='0' * 64)))

    def test_source_map(self):
        self.refuse(self.changed('capture/capture-receipt.json', lambda d: d['source_sha256'].pop(next(iter(d['source_sha256'])))))

    def test_catalog_bytes(self):
        data = self.runtime.copy()
        data['capture/catalog.cohcat'] = data['capture/catalog.cohcat'][:-1]
        self.refuse(data)

    def test_sidecar_bytes(self):
        data = self.runtime.copy()
        data['capture/runtime.cohrts'] = data['capture/runtime.cohrts'][:-1]
        self.refuse(data)

    def test_disagreeing_sanitizer(self):
        self.refuse(self.changed('runtime-graph-diagnostic.json', lambda d: d['captured']['asan'].update(root_matrices_verified=0)))

    def test_all_modes_wrong_crc(self):
        def change(d):
            for mode in d['captured'].values():
                mode['source_defs_crc'] = 0
        self.refuse(self.changed('runtime-graph-diagnostic.json', change))

    def test_world_claim(self):
        def change(d):
            d['world_authority'] = True
            for mode in d['captured'].values():
                mode['world_authority'] = True
        self.refuse(self.changed('runtime-graph-diagnostic.json', change))

    def test_diagnostic_log_corruption(self):
        data = self.runtime.copy()
        data['capture/diagnostic-00.txt'] += b'x'
        self.refuse(data)

    def test_compile_PE_corruption(self):
        data = self.compiled.copy()
        data['MapServer.exe'] = data['MapServer.exe'][:-1]
        with self.assertRaises(ValueError):
            v.audit(self.runtime, data, self.repo)

    def test_archive_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'changed.zip'
            b = bytearray((self.corpus / 'evidence.zip').read_bytes())
            b[len(b)//2] ^= 1
            p.write_bytes(b)
            with self.assertRaisesRegex(ValueError, 'archive hash'):
                v.load_archive(p, v.PINS['evidence.zip'])

    def test_archive_bound_before_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'oversize.zip'
            p.write_bytes(b'x')
            with self.assertRaisesRegex(ValueError, 'archive size'):
                v.load_archive(p, v.PINS['evidence.zip'])

if __name__ == '__main__':
    unittest.main()
