"""Ensure staged files cannot silently diverge from the verified inventory."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from inspect_asset_formats import inspect_formats


def inventory(path, data):
    return {'status': 'archive_integrity_verified_runtime_compatibility_unverified',
            'archives': [{'archive': 'fixture.pigg', 'entries': [{
                'path': path, 'size': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}]}]}


class StagingTrustTests(unittest.TestCase):
    def test_same_size_modified_payload_is_rejected_before_format_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'track.anim').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                inspect_formats(inventory('track.anim', b'initial'), root)

    def test_parent_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Unsafe inventory path'):
                inspect_formats(inventory('../track.anim', b''), Path(tmp))

    def test_symlinked_parent_cannot_escape_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / 'staging'
            root.mkdir()
            outside = base / 'outside'
            outside.mkdir()
            (outside / 'track.anim').write_bytes(b'')
            (root / 'linked').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'inside staging'):
                inspect_formats(inventory('linked/track.anim', b''), root)


if __name__ == '__main__':
    unittest.main()
