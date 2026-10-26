import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'scripts'),
               str(Path(__file__).resolve().parents[1] / 'replay')]
import client_errors
import compare_errors


class ErrorComparison(unittest.TestCase):
    def test_same_commit_shared_missing_files_and_present_geometry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for target in ('arm64', 'i686'):
                folder = root / target
                run = folder / 'id1-a'
                run.mkdir(parents=True)
                (folder / 'report.json').write_text(json.dumps(dict(target=target, source_commit='same')))
                (run / 'client-stdio.txt').write_text('')
                texts = ["Geometry A in player_library/MISSING.geo doesn't exist!",
                         "Geometry B in player_library/PRESENT.geo doesn't exist!",
                         "Group Streets/Root\ncan't find member Streets/Sign"]
                if target == 'arm64':
                    texts.append('Port-specific failure')
                (run / 'zone-trace.jsonl').write_text(''.join(
                    json.dumps(dict(stage='client.error', text=text)) + '\n' for text in texts))
                errors = client_errors.inventory(run / 'client-stdio.txt', run / 'client-errors.json',
                                                 run / 'zone-trace.jsonl')
                data = folder / 'data'
                (data / 'player_library').mkdir(parents=True)
                (data / 'player_library/Present.geo').write_bytes(b'present geometry')
                (data / 'object_library/Streets').mkdir(parents=True)
                (data / 'object_library/Streets/Signs.rootnames').write_text('Def Sign\n Obj Sign\nDefEnd\n')
                lookup = client_errors.geometry_lookup(errors, data)
                self.assertEqual(lookup['player_library/present.geo'][0]['sha256'],
                                 hashlib.sha256(b'present geometry').hexdigest())
                (run / 'error-geometry-files.json').write_text(json.dumps(lookup))
                (run / 'error-assets.json').write_text(json.dumps(client_errors.asset_lookup(errors, data)))
            result = compare_errors.compare(root, 'same')
            self.assertEqual(result['shared_missing_geometry_files'], ['player_library/missing.geo'])
            self.assertEqual(len(result['shared']), 3)
            self.assertEqual(result['shared_missing_group_geometry'], ['object_library/streets/signs.geo'])
            self.assertEqual(len(result['arm64_only']), 1)
            self.assertFalse(result['error_free'])
            self.assertFalse(result['m3_replay_complete'])
            with self.assertRaisesRegex(ValueError, 'same source commit'):
                compare_errors.compare(root, 'different')
            (root / 'i686/id1-a/error-geometry-files.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Incomplete actual-runtime'):
                compare_errors.compare(root, 'same')
