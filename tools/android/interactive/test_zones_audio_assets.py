"""Check actual frozen audio inventories across all 72 original resource archives."""
import hashlib
import json
from pathlib import PurePosixPath
import unittest
import prepare_zones_audio_assets as audio
import prepare_zones_world_assets as zones

class AudioScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=audio.ROOT/'assets'/audio.MANIFEST
        cls.document=json.loads(cls.path.read_bytes())
        cls.world=zones.frozen_manifest(audio.ROOT)

    def test_actual_audio_manifest_and_fifteen_source_archives_have_exact_identity(self):
        self.assertEqual(audio.pin(self.path),audio.MANIFEST_PIN)
        self.assertEqual(audio.pin(audio.ROOT/'assets'/audio.METADATA),audio.METADATA_PIN)
        metadata=json.loads((audio.ROOT/'assets'/audio.METADATA).read_bytes())
        self.assertEqual(len(metadata),15)
        self.assertEqual(self.document['frozen_metadata_archives'],metadata)
        self.assertEqual(len({row['archive'].casefold() for row in metadata}),15)
        self.assertTrue(all(row['archive'].startswith('sound') for row in metadata))
        self.assertEqual(self.document['archive'],{'filename':audio.ARCHIVE,**audio.ARCHIVE_PIN})
        self.assertEqual(self.document['provenance'],{'filename':audio.PROVENANCE,**audio.PROVENANCE_PIN})

    def test_append_does_not_replace_verified_zones_and_native_names_are_unambiguous(self):
        old={name:row for name,row in self.world['files'].items() if name.endswith('.ogg')}
        new=self.document['files']
        self.assertEqual(len(old),4042);self.assertEqual(len(new),2177)
        self.assertFalse(set(old)&set(new))
        combined=set(old)|set(new)
        self.assertEqual(len({PurePosixPath(name).stem.casefold() for name in combined}),6219)
        self.assertTrue(all(name.startswith('data/sound/ogg/') and len(name.removeprefix('data/'))+1<80 for name in combined))
        self.assertEqual(self.document['base_zones_archive_pin'],zones.ARCHIVE_PIN)
        self.assertEqual(self.document['base_zones_manifest_pin'],zones.MANIFEST_PIN)
        self.assertEqual(hashlib.sha256(audio.canonical(new)).hexdigest(),self.document['files_sha256'])

    def test_previously_omitted_kings_row_ambient_and_music_files_are_present(self):
        expected={'data/sound/ogg/kingsrow/kingsamb1_loop.ogg',
            'data/sound/ogg/kingsrow/kingsrowsirens_loop.ogg','data/sound/ogg/music/kingsrowsector.ogg'}
        self.assertLessEqual(expected,set(self.document['files']))
        self.assertTrue(self.document['original_payloads_verified'])
        self.assertFalse(self.document['physical_playback_verified'])
        self.assertFalse(self.document['full_dynamic_source_dependency_closure'])
