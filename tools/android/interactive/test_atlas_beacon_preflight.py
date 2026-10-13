"""Draft runner regression tests; not native or APK qualification."""
import contextlib
import io
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import qualify_atlas_beacon_preflight as preflight


class HistoricalFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.document = {'source_files': {}, 'donor': {}}
        for name in preflight.HELPERS:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'# exact fixture\r\nvalue = 1\r\n')
            self.document['source_files'][name] = preflight.pin(target)
        self.donor = self.root / 'donor.apk'
        self.donor.write_bytes(b'unit-test-donor-only')
        self.document['donor']['apk'] = preflight.pin(self.donor)
        self.package = SimpleNamespace(ROOT=self.root, DONOR_APK_NAME='donor.apk',
            DONOR_APK=preflight.pin(self.donor))

    def scope(self):
        return preflight.historical_inputs(self.package, self.source, self.document, self.donor)

    def test_original_artifact_and_two_sources_authenticate_exact_bytes(self):
        directory = Path(os.environ.get('COH_BEACON_PREFLIGHT_FIXTURE_DIRECTORY', str(Path(__file__).parent)))
        value = preflight.qualification(directory / 'coh-ui-beacon-qualification-original.zip')
        preflight.verify_helpers(directory / 'historical-source', value)
        self.assertEqual(value['repository_commit'], preflight.ORIGINAL_COMMIT)

    def test_wrong_qualification_artifact_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Exact original'):
            preflight.qualification(self.donor)

    def test_scoped_helper_copy_preserves_crlf_bytes_and_restores_root(self):
        original = self.package.ROOT
        with self.scope():
            self.assertNotEqual(self.package.ROOT, original)
            for name in preflight.HELPERS:
                self.assertEqual((self.package.ROOT / name).read_bytes(), (self.source / name).read_bytes())
            self.assertEqual((self.package.ROOT / 'out/ui-beacon-donor/donor.apk').read_bytes(), self.donor.read_bytes())
        self.assertEqual(self.package.ROOT, original)

    def test_root_is_restored_after_case_failure(self):
        original = self.package.ROOT
        with self.assertRaisesRegex(RuntimeError, 'case failed'):
            with self.scope():
                raise RuntimeError('case failed')
        self.assertEqual(self.package.ROOT, original)

    def test_changed_helper_is_refused_before_test_execution(self):
        (self.source / preflight.HELPERS[0]).write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError, 'source bytes differ'):
            with self.scope():
                self.fail('Must not admit changed historical inputs')

    def test_changed_staged_helper_is_refused_after_test_execution(self):
        with self.assertRaisesRegex(ValueError, 'source bytes differ'):
            with self.scope():
                (self.package.ROOT / preflight.HELPERS[0]).write_bytes(b'foreign')
        self.assertEqual(self.package.ROOT, self.root)

    def test_changed_donor_is_refused_before_test_execution(self):
        self.donor.write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError, 'Exact original .13 APK'):
            with self.scope():
                self.fail('Must not admit changed donor')

    def test_linked_helper_is_refused(self):
        path = self.source / preflight.HELPERS[0]
        moved = path.with_suffix('.original')
        path.rename(moved)
        path.symlink_to(moved)
        with self.assertRaisesRegex(ValueError, 'linked preflight input'):
            preflight.verify_helpers(self.source, self.document)

    def test_linked_helper_parent_is_refused(self):
        parent = self.source / 'android/guest'
        moved = self.source / 'actual-guest'
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Linked historical source parent'):
            preflight.verify_helpers(self.source, self.document)

    def test_current_case_failure_and_skip_never_become_passes(self):
        class Failing(unittest.TestCase):
            def runTest(self):
                self.fail('must remain failed')
        class Skipping(unittest.TestCase):
            def runTest(self):
                self.skipTest('unavailable')
        for case in (Failing(), Skipping()):
            with self.subTest(case=type(case).__name__), contextlib.redirect_stdout(io.StringIO()), \
                    self.assertRaisesRegex(ValueError, 'failed or skipped'):
                preflight.execute([case], 'current')


if __name__ == '__main__':
    unittest.main()
