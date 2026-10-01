"""The small costume supplement stays separate from accepted imported assets."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('avatar_package_test', HERE/'prepare_character_avatar_assets.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class AvatarPackageTests(unittest.TestCase):
    def test_reviewed_payload_and_honest_provenance(self):
        document = package.verify(package.ROOT/'assets'/package.ARCHIVE,
                                  package.ROOT/'assets'/package.MANIFEST)
        self.assertEqual(21, len(document['files']))
        self.assertEqual(2980122, sum(item['bytes'] for item in document['files'].values()))
        self.assertFalse(document['provenance']['source_archive_sha256_verified'])
        contract = package.bundle_contract()
        for flag in ('imported_assets_modified', 'prepared_caches_modified',
                     'runtime_visual_validated', 'gameplay_validated'):
            self.assertIs(contract[flag], False)

    def test_staging_copies_the_reviewed_pair_and_refuses_existing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            result = package.prepare(output)
            self.assertEqual(package.bundle_contract(), result)
            self.assertEqual({package.ARCHIVE, package.MANIFEST}, {p.name for p in output.iterdir()})
            self.assertEqual(package.ARCHIVE_PIN, package.pin(output/package.ARCHIVE))
            self.assertEqual(package.MANIFEST_PIN, package.pin(output/package.MANIFEST))
            with self.assertRaisesRegex(ValueError, 'already exists'):
                package.prepare(output)

    def test_preexisting_manifest_does_not_leave_partial_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output/package.MANIFEST).write_text('existing')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                package.prepare(output)
            self.assertFalse((output/package.ARCHIVE).exists())
            self.assertEqual('existing', (output/package.MANIFEST).read_text())

    def test_payload_and_metadata_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            package.prepare(output)
            archive, manifest = output/package.ARCHIVE, output/package.MANIFEST
            original = archive.read_bytes()
            archive.write_bytes(original + b'changed')
            with self.assertRaisesRegex(ValueError, 'archive differs'):
                package.verify(archive, manifest)
            archive.write_bytes(original)
            document = json.loads(manifest.read_text())
            document['gameplay_validated'] = True
            manifest.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, 'manifest differs'):
                package.verify(archive, manifest)

    def test_linked_input_or_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            linked_archive = output/package.ARCHIVE
            linked_archive.symlink_to(package.ROOT/'assets'/package.ARCHIVE)
            with self.assertRaisesRegex(ValueError, 'linked avatar input'):
                package.verify(linked_archive, package.ROOT/'assets'/package.MANIFEST)
            linked_directory = output/'linked-directory'
            linked_directory.symlink_to(output, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'regular directory'):
                package.prepare(linked_directory)


if __name__ == '__main__':
    unittest.main()
