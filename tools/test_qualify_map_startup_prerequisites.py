"""Offline owner never approves shipping code or rewrites historical evidence."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import qualify_map_startup_prerequisites as lane


class OfflineQualificationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-offline-boundary-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.patches = [mock.patch.object(lane, 'ROOT', self.root)]
        self.historical = {}
        for name in lane.BOUNDARY_FILES:
            raw = ('immutable:' + name).encode()
            self.historical[name] = raw
            self.write(name, raw)
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def write(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def boundary(self, tracked=(), untracked=()):
        def git(command, **kwargs):
            if command[1:3] == ['diff', '--name-only']:
                return '\n'.join(tracked)
            if command[1] == 'ls-files':
                return '\n'.join(untracked)
            if command[1] == 'show':
                return self.historical[command[2].split(':', 1)[1]]
            raise AssertionError('Unexpected git operation: ' + repr(command))
        with mock.patch.object(lane.subprocess, 'check_output', side_effect=git):
            return lane.frozen_sources()

    def test_authorized_production_change_is_observed_without_shipping_authority(self):
        name = 'android/interactive/src/main/java/ClientRuntime.java'
        raw = b'authorized successor change'
        self.write(name, raw)
        value = self.boundary(tracked=[name])
        self.assertFalse(value['existing_production_sources_unchanged'])
        self.assertTrue(value['production_changes_observed'])
        self.assertFalse(value['successor_shipping_qualified'])
        self.assertEqual(value['production_change_policy'],
                         'observe_only_requires_separate_shipping_owner_acceptance')
        self.assertEqual(value['changed_production_sources'][name], {
            'state': 'present', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'qualified_by_this_lane': False})

    def test_untracked_new_native_source_is_observed_without_approval(self):
        name = 'database/future-native/overlay/MapServer/future.c'
        self.write(name, b'new native source')
        value = self.boundary(untracked=[name])
        self.assertTrue(value['production_changes_observed'])
        self.assertFalse(value['changed_production_sources'][name]['qualified_by_this_lane'])
        self.assertFalse(value['successor_shipping_qualified'])

    def test_deleted_production_file_remains_an_unqualified_change(self):
        name = 'android/native/removed.c'
        value = self.boundary(tracked=[name])
        self.assertEqual(value['changed_production_sources'][name],
                         {'state': 'deleted', 'qualified_by_this_lane': False})
        self.assertFalse(value['existing_production_sources_unchanged'])

    def test_only_exact_prototype_owned_paths_are_excluded(self):
        owned = 'tools/qualify_map_startup_prerequisites.py'
        foreign = 'database/map-startup-physics/qualification/unreviewed.cpp'
        self.write(owned, b'qualifier')
        self.write(foreign, b'not an owned prototype')
        value = self.boundary(tracked=[owned], untracked=[foreign])
        self.assertNotIn(owned, value['changed_production_sources'])
        self.assertIn(foreign, value['changed_production_sources'])
        self.assertFalse(value['successor_shipping_qualified'])

    def test_unchanged_production_does_not_confer_shipping_qualification(self):
        value = self.boundary()
        self.assertTrue(value['existing_production_sources_unchanged'])
        self.assertFalse(value['production_changes_observed'])
        self.assertFalse(value['successor_shipping_qualified'])
        self.assertEqual(set(value['immutable_evidence_pins']), set(lane.BOUNDARY_FILES))

    def test_changed_published_guide_native_publication_or_historical_51_test_record_fails(self):
        for name, raw in self.historical.items():
            with self.subTest(name=name):
                path = self.write(name, raw + b'changed')
                with self.assertRaisesRegex(ValueError, 'Immutable published'):
                    self.boundary()
                path.write_bytes(raw)

    def test_linked_immutable_proof_is_rejected_even_when_bytes_match(self):
        name = 'docs/android-evidence/client-map-startup-0.13.32-native.json'
        target = self.write('outside/proof.json', self.historical[name])
        path = self.root / name
        path.unlink()
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Missing or linked'):
            self.boundary()

    def test_linked_foreign_production_path_is_reported_without_reading_target(self):
        name = 'android/native/linked.c'
        path = self.root / name
        path.parent.mkdir(parents=True)
        path.symlink_to(self.root / 'missing-private-target')
        value = self.boundary(tracked=[name])
        self.assertEqual(value['changed_production_sources'][name],
                         {'state': 'linked', 'qualified_by_this_lane': False})

    def test_source_pins_refuse_unreviewed_sibling_and_linked_owned_input(self):
        owned = 'database/offline/fixture.h'
        foreign = 'database/offline/unreviewed.cpp'
        self.write(owned, b'fixture')
        with mock.patch.object(lane, 'PROTOTYPE_FILES', frozenset({owned})), \
                mock.patch.object(lane, 'DEPENDENCY_FILES', ()), \
                mock.patch.object(lane, 'SOURCE_DIRS', ('database/offline',)):
            self.assertEqual(lane.source_pins()[owned]['bytes'], 7)
            foreign_path = self.write(foreign, b'foreign')
            with self.assertRaisesRegex(ValueError, 'Unreviewed offline prototype'):
                lane.source_pins()
            foreign_path.unlink()
            target = self.write('outside/header.h', b'fixture')
            path = self.root / owned
            path.unlink()
            path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'Missing or linked'):
                lane.source_pins()


if __name__ == '__main__':
    unittest.main()
