"""Bounded source serialization, silent dependency and append-only proofs."""
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import discover_client_appearance_assets as discovery
import prepare_client_appearance_assets as producer
from test_client_visual_sweep import original_texture


class AppearanceSourceEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'source.json'
        self.raw = b'{"files":{"exact":{"bytes":7}},"format":1}\n'
        self.pin = producer.pin_bytes(self.raw)
        mock = patch.object(producer, 'MANIFEST_PIN', self.pin)
        mock.start(); self.addCleanup(mock.stop)

    def envelope(self, packed=None):
        packed = gzip.compress(self.raw, mtime=0) if packed is None else packed
        return {'format': 1, 'scope': producer.SOURCE_MANIFEST_SCOPE, 'encoding': 'gzip+base64',
            'decoded': self.pin, 'gzip': producer.pin_bytes(packed),
            'data': base64.b64encode(packed).decode('ascii')}

    def write(self, value):
        self.path.write_bytes(producer.canonical(value)+b'\n')

    def test_source_envelope_and_plaintext_preserve_exact_runtime_bytes(self):
        self.path.write_bytes(self.raw)
        self.assertEqual(producer.manifest_bytes(self.path), self.raw)
        self.write(self.envelope())
        self.assertEqual(producer.manifest_bytes(self.path), self.raw)

    def test_corrupted_stream_rejected_before_decode(self):
        value = self.envelope(); value['gzip']['sha256'] = '0'*64; self.write(value)
        with patch.object(producer.zlib, 'decompressobj', side_effect=AssertionError('untrusted decode')):
            with self.assertRaisesRegex(ValueError, 'gzip stream differs'):
                producer.manifest_bytes(self.path)

    def test_gzip_crc_trailing_or_multiple_streams_are_rejected(self):
        packed = gzip.compress(self.raw, mtime=0)
        bad_crc = bytearray(packed); bad_crc[-8] ^= 1
        for bad in (bytes(bad_crc), packed+b'x', packed+gzip.compress(b'other', mtime=0)):
            self.write(self.envelope(bad))
            with self.subTest(bad=len(bad)), self.assertRaises(ValueError):
                producer.manifest_bytes(self.path)

    def test_decoded_overflow_is_bounded_and_rejected(self):
        self.write(self.envelope(gzip.compress(self.raw+b'x'*4096, mtime=0)))
        with self.assertRaisesRegex(ValueError, 'decoded source bytes differ or exceed bound'):
            producer.manifest_bytes(self.path)

    def test_envelope_schema_duplicate_fields_and_source_links_are_rejected(self):
        value = self.envelope(); value['ignored'] = True; self.write(value)
        with self.assertRaisesRegex(ValueError, 'metadata differs'): producer.manifest_bytes(self.path)
        raw = producer.canonical(self.envelope())
        self.path.write_bytes(b'{"format":1,'+raw[1:])
        with self.assertRaisesRegex(ValueError, 'duplicate fields'): producer.manifest_bytes(self.path)
        target = self.path.with_name('target.json'); target.write_bytes(self.raw)
        self.path.unlink(); self.path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'linked appearance manifest'): producer.manifest_bytes(self.path)

    def test_source_and_encoded_bounds_reject_before_decode(self):
        self.write(self.envelope())
        with patch.object(producer, 'MAX_SOURCE_MANIFEST_BYTES', 8):
            with self.assertRaisesRegex(ValueError, 'envelope exceeds bound'): producer.manifest_bytes(self.path)
        with patch.object(producer, 'MAX_SOURCE_GZIP_BYTES', 8):
            with self.assertRaisesRegex(ValueError, 'encoded source stream exceeds bound'): producer.manifest_bytes(self.path)


class AppearanceDependencyTests(unittest.TestCase):
    def test_new_console_pass_retains_material_and_postworld_costume_witnesses(self):
        raw = ('Texture Trick "X_NewArmor" references missing texture "NewArmor_Mask".\n'
            'CUSTOM TEXTURE ERROR: female wants nonexistent texture FACE_Skin_BF_45Asian2 as texture 0 on bone Head.\n'
            "BAD DATA: Custom Geometry GEO_FACE_Cigarette in player_library/BM_FACE.geo doesn't exist!\n"
            'Reading Police_Drone.txt\n').encode()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'console'; path.write_bytes(raw)
            requests = discovery.console_requests(path)
        self.assertEqual(requests['source_console'], producer.pin_bytes(raw))
        self.assertEqual(set(requests['textures']), {'x_newarmor', 'newarmor_mask', 'face_skin_bf_45asian2'})
        self.assertEqual(requests['geometry']['data/player_library/bm_face.geo'][0]['model'], 'GEO_FACE_Cigarette')
        self.assertEqual(requests['observed_enttype_names'], ['police_drone.txt'])

    def test_silent_enttype_graphics_and_relative_fx_particle_texture_are_traced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); data = root/'upstream/i24/data'
            (data/'ent_types').mkdir(parents=True); (data/'fx/generic').mkdir(parents=True)
            (data/'sequencers').mkdir()
            (data/'ent_types/police_drone.txt').write_text('Graphics player_library/G_Police_Drone.geo\nFx Generic/FX_policedrone.fx\n')
            (data/'fx/generic/fx_policedrone.fx').write_text('Part1 :RedLightCenter.part\n')
            (data/'fx/generic/redlightcenter.part').write_text('TextureName spark\n')
            requests = discovery.enttype_fx_requests(root, {}, ['police_drone.txt'])
        self.assertIn('data/player_library/g_police_drone.geo', requests['geometry'])
        self.assertIn('spark', requests['textures'])
        self.assertEqual(requests['source_file_count'], 3)
        self.assertFalse(requests['unresolved_source_edges'])

    def test_native_fx_arrays_splat_and_inner_cape_layers_are_followed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); data = root/'upstream/i24/data'
            (data/'ent_types').mkdir(parents=True); (data/'fx/generic').mkdir(parents=True)
            (data/'sequencers').mkdir()
            (data/'ent_types/actor.txt').write_text('OneShotFX generic/first.fx generic/second.fx\nOnClickFx generic/third.fx\nContinuingFx generic/second.fx\n')
            (data/'fx/generic/first.fx').write_text('Splat first_splat second_splat\nCape :exact.cape\n')
            (data/'fx/generic/second.fx').write_text('Part1 Generic\\\\exact.part\n')
            (data/'fx/generic/third.fx').write_text('Geom Parent\n')
            (data/'fx/generic/exact.cape').write_text('InnerTex1 cape_liner\nInnerTex2 cape_mask\n')
            (data/'fx/generic/exact.part').write_text('Name unused_identifier.part\nTextureName particle_leaf\n')
            requests = discovery.enttype_fx_requests(root, {}, ['actor.txt'])
        self.assertEqual(set(requests['textures']), {'first_splat', 'second_splat', 'cape_liner', 'cape_mask', 'particle_leaf'})
        self.assertFalse(requests['unresolved_source_edges'])
        self.assertEqual(requests['source_file_count'], 6)

    def test_individual_cached_leaf_keeps_actual_receipt_when_group_boundaries_change(self):
        row, _, stored = original_texture()
        name = 'data/'+row['path']
        proof = {'content_range': 'bytes 490-'+str(509+len(stored))+'/10000',
            'bytes': len(stored)+20, 'sha256': hashlib.sha256(bytes(10)+stored+bytes(10)).hexdigest()}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/hashlib.sha256(name.encode()).hexdigest()
            path.write_bytes(stored); path.with_suffix('.download').write_bytes(discovery.canonical(proof))
            result = discovery.reusable_records({name: row}, temporary)
            self.assertEqual(result[name]['source_download_content_range'], proof['content_range'])
            self.assertEqual(result[name]['source_download_sha256'], proof['sha256'])
            changed = dict(row, md5_table='0'*32)
            self.assertEqual(discovery.reusable_records({name: changed}, temporary), {})
            proof['content_range'] = proof['content_range'].replace('/10000', '/9999')
            path.with_suffix('.download').write_bytes(discovery.canonical(proof))
            self.assertEqual(discovery.reusable_records({name: row}, temporary), {})

    def test_exact_original_material_closure_keeps_all_native_leaves(self):
        one, _, _ = original_texture('texture_library/test/one.texture')
        two, _, _ = original_texture('texture_library/test/two.texture')
        files = {one['path']: one, two['path']: two}
        requests = {'textures': {'one': [{'scope': 'actual_new_costume', 'target': 'one'}],
            'two': [{'scope': 'actual_new_costume', 'target': 'two'}]}}
        result = discovery.dependency_plan(files, requests, {'data/'+one['path']}, {})
        self.assertEqual(set(result['selected']), {'data/'+two['path']})
        self.assertEqual(set(result['existing_leaf_dependencies']), {'data/'+one['path']})
        with patch.object(discovery, 'MAX_PAYLOAD_BYTES', discovery.BASE_PAYLOAD_BYTES+1):
            with self.assertRaisesRegex(ValueError, 'composed assets exceed'): discovery.dependency_plan(files, requests, set(), {})

    def test_raw_stream_retention_checks_encoded_bytes_not_only_decoded_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); old, same, changed = (root/name for name in ('old.zip', 'same.zip', 'changed.zip'))
            raw = b'accepted-original'*1000
            producer.baseline.donor.write_zip_members(old, [('data/texture_library/a.texture', raw, raw, zipfile.ZIP_STORED)])
            same.write_bytes(old.read_bytes())
            with zipfile.ZipFile(changed, 'w', compression=zipfile.ZIP_DEFLATED) as output:
                output.writestr('data/texture_library/a.texture', raw)
            value = {'files': {'data/texture_library/a.texture': producer.pin_bytes(raw)},
                'appearance_extension': {'files': {}}}
            with patch.object(producer.baseline, 'ARCHIVE_PIN', producer.pin(old)), patch.object(producer.baseline, 'FILE_COUNT', 1):
                self.assertEqual(producer.verify_preserved(same, old, value)['retained_encoded_streams'], 1)
                with self.assertRaisesRegex(ValueError, 'changes an accepted encoded stream'):
                    producer.verify_preserved(changed, old, value)


if __name__ == '__main__':
    unittest.main()
