import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from reviewed_asset_coverage import load_manifest, coverage, SOURCES
from stage_reviewed_files import stage_archive


class ReviewedFiles(unittest.TestCase):
    def test_compressed_manifest_pins_and_ambiguous_texture_are_enforced(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pin = dict(bytes=1, sha256=hashlib.sha256(b'x').hexdigest())
            def doc(files):
                return dict(files=files, file_count=len(files), payload_bytes=len(files), archive={})
            value = doc({'data/texture_library/a/SAME.texture': pin,
                         'data/texture_library/b/SAME.texture': pin})
            raw = json.dumps(value).encode(); packed = gzip.compress(raw)
            wrapper = dict(encoding='gzip+base64', data=base64.b64encode(packed).decode(),
                           decoded=dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()),
                           gzip=dict(bytes=len(packed), sha256=hashlib.sha256(packed).hexdigest()))
            p = root / (SOURCES[0] + '-manifest.json'); p.write_text(json.dumps(wrapper))
            for source in SOURCES[1:]:
                (root / (source + '-manifest.json')).write_text(json.dumps(doc({})))
            result = coverage(dict(run=1, source_commit='a'*40, missing_geometry=[], missing_textures=['same']), root)
            self.assertEqual(result['ambiguous']['missing_textures'], ['same'])
            self.assertFalse(any(result['selected'].values()))
            wrapper['decoded']['sha256'] = '0' * 64; p.write_text(json.dumps(wrapper))
            with self.assertRaisesRegex(ValueError, 'Decoded manifest identity'):
                load_manifest(p)

    def test_selected_archive_payload_and_existing_collision_are_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); archive = root / 'a.zip'; output = root / 'out'
            name = 'data/player_library/a.geo'; content = b'original'
            pin = dict(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
            with zipfile.ZipFile(archive, 'w') as z: z.writestr(name, content)
            document = dict(files={name: pin}, archive=dict(bytes=archive.stat().st_size,
                            sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
            stage_archive(archive, document, {name: pin}, output)
            (output / 'player_library/a.geo').write_bytes(b'conflict')
            with self.assertRaisesRegex(ValueError, 'collision'):
                stage_archive(archive, document, {name: pin}, output)
            document['archive']['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'archive identity'):
                stage_archive(archive, document, {name: pin}, output)
