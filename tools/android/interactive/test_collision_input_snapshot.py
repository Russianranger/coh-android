"""Collision inventory safety and operation counts; no native graph is simulated."""
import contextlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
SPEC = importlib.util.spec_from_file_location(
    'collision_snapshot_test_package', ROOT / 'android/guest/atlas_beacon_package.py')
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)

SCOPES = (
    ('data/object_library', ('.geo', '.txt')),
    ('data/maps/city_zones/city_01_01', ('.txt',)),
    ('data/tricks', ('.txt',)))
ERRORS = (ValueError, package.world.client.base.DiagnosticError)


class Context:
    def __init__(self, cancel_after=None):
        self.checks = 0
        self.cancel_after = cancel_after

    def check(self):
        self.checks += 1
        if self.cancel_after is not None and self.checks >= self.cancel_after:
            raise InterruptedError('fixture cancellation')


def retained_inventory(runtime, selected, scopes, context):
    """Retain the old resolver/rglob/resolver/fingerprint work for comparison.

    This is a test reference, never a second shipping implementation. It covers
    the old successful inventory path and preserves the actual old calls whose
    operation counts matter, rather than asserting filesystem wall-clock time.
    """
    targets = package.actual_targets(runtime, selected, context)
    actual, seen = {}, set()
    for scope, suffixes in scopes:
        sentinel = scope + '/.atlas-beacon-inventory'
        root = package.actual_targets(runtime, (sentinel,), context)[sentinel].parent
        package.require(root.is_dir() and not root.is_symlink(), 'Private source directory required')
        for path in root.rglob('*'):
            context.check()
            relative = path.relative_to(runtime).as_posix()
            folded = relative.casefold()
            package.require(folded not in seen, 'Case-conflicting source inventory')
            seen.add(folded)
            package.require(not (path.is_symlink() and path.is_dir()), 'Linked source directory')
            if path.suffix.casefold() in suffixes and not path.is_dir():
                actual[folded] = relative
    package.require(set(actual) == {name.casefold() for name in selected}, 'Source inventory differs')
    package.require(all(actual[name.casefold()] == path.relative_to(runtime).as_posix()
                        for name, path in targets.items()), 'Provider paths differ')
    return package.fingerprints(runtime, selected, context, immutable_input=True), targets


class CollisionInputSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='coh-collision-snapshot-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir()
        self.selected = {
            'data/object_library/group/Building.GEO': {'bytes': 8},
            'data/object_library/group/Building.txt': {'bytes': 9},
            'data/' + package.MAP: {'bytes': 10},
            'data/tricks/Trick.txt': {'bytes': 11},
        }
        self.required = {'data/object_library/group/Building.GEO'}
        for name, record in self.selected.items():
            self.write(name, b'x' * record['bytes'])
        self.write('data/object_library/unreferenced/notes.ini', b'irrelevant metadata', mode=0o600)

    def write(self, name, raw, *, mode=0o444):
        path = self.runtime / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(mode)
        return path

    def snapshot(self, context=None):
        return package.collision_input_snapshot(
            self.runtime, self.selected, SCOPES, context or Context(), required=self.required)

    def assert_common_fingerprints(self, expected, observed):
        self.assertEqual(set(expected), set(observed))
        # The new proof may add fields. All old physical identity fields must
        # still agree, including the exact resolved directory and leaf spelling.
        for name, record in expected.items():
            self.assertEqual(record, {key: observed[name][key] for key in record})

    def mixed_case_directories(self):
        for source, destination in (
                ('data/object_library/group', 'data/object_library/Group'),
                ('data/object_library', 'data/Object_Library'),
                ('data/maps/city_zones/city_01_01', 'data/maps/city_zones/City_01_01'),
                ('data/maps/city_zones', 'data/maps/City_Zones'),
                ('data/maps', 'data/Maps'),
                ('data/tricks', 'data/Tricks'),
                ('data', 'Data')):
            (self.runtime / source).rename(self.runtime / destination)

    def test_exact_snapshot_matches_retained_inventory_with_mixed_case_directories(self):
        self.mixed_case_directories()
        old, old_targets = retained_inventory(self.runtime, self.selected, SCOPES, Context())
        observed, targets = self.snapshot()
        self.assert_common_fingerprints(old, observed)
        self.assertEqual(targets, old_targets)
        self.assertEqual(observed['data/object_library/group/Building.GEO']['path'],
                         'Data/Object_Library/Group/Building.GEO')
        self.assertFalse((self.runtime / 'data').exists())

    def test_readonly_imported_leaf_links_retain_target_identity_and_logical_path(self):
        name = next(iter(self.selected))
        path = self.runtime / name
        donor = self.root / 'readonly-donor.geo'
        path.rename(donor)
        path.symlink_to(donor)
        old, _ = retained_inventory(self.runtime, self.selected, SCOPES, Context())
        observed, targets = self.snapshot()
        self.assert_common_fingerprints(old, observed)
        self.assertEqual(observed[name]['inode'], donor.stat().st_ino)
        self.assertEqual(observed[name]['path'], name)
        self.assertTrue(targets[name].is_symlink())
        donor.chmod(0o644)
        with self.assertRaisesRegex(ERRORS, 'immutable leaf permissions'):
            self.snapshot()

    def test_selected_duplicate_leaf_diagnostic_is_independent_of_scandir_order(self):
        target = self.runtime / 'data/object_library/group/Building.GEO'
        duplicate = target.with_name('building.geo')
        duplicate.write_bytes(target.read_bytes()); duplicate.chmod(0o444)
        original = package.os.scandir
        for variant_first in (False, True):
            @contextlib.contextmanager
            def ordered(path):
                with original(path) as entries:
                    captured = list(entries)
                if Path(path) == target.parent:
                    captured.sort(key=lambda entry: entry.name == target.name,
                                  reverse=not variant_first)
                yield iter(captured)
            with self.subTest(variant_first=variant_first), \
                    mock.patch.object(package.os, 'scandir', side_effect=ordered):
                with self.assertRaisesRegex(package.world.client.base.DiagnosticError,
                                            'case-conflicting world destination'):
                    self.snapshot()

    def test_target_resolution_occurs_once_for_scope_sentinels_only(self):
        calls = []
        original = package.actual_targets

        def resolve(runtime, names, context):
            calls.append(tuple(names))
            self.assertTrue(all(name.endswith('/.collision-inventory') for name in names))
            return original(runtime, names, context)

        with mock.patch.object(package, 'actual_targets', side_effect=resolve), \
                mock.patch.object(package, 'fingerprints', side_effect=AssertionError('Duplicate fingerprint resolver')):
            observed, targets = self.snapshot()
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), len(SCOPES))
        self.assertEqual(set(observed), set(self.selected))
        self.assertEqual(set(targets), set(self.selected))

    def test_operation_counts_remove_provider_resolution_without_latency_assertions(self):
        # Add a nested finite provider set to make repeated resolution material.
        for index in range(32):
            name = 'data/object_library/deep/group%d/leaf%d.geo' % (index // 4, index)
            self.selected[name] = {'bytes': 4}
            self.write(name, b'geom')
        original_resolve = package.actual_targets
        original_stat, original_lstat = Path.stat, Path.lstat

        def measured(operation):
            counts = {'resolver_calls': 0, 'resolved_names': 0, 'path_stats': 0}

            def resolve(runtime, names, context):
                names = tuple(names)
                counts['resolver_calls'] += 1
                counts['resolved_names'] += len(names)
                return original_resolve(runtime, names, context)

            def observed_stat(path, *args, **kwargs):
                counts['path_stats'] += 1
                return original_stat(path, *args, **kwargs)

            def observed_lstat(path, *args, **kwargs):
                counts['path_stats'] += 1
                return original_lstat(path, *args, **kwargs)

            with mock.patch.object(package, 'actual_targets', side_effect=resolve), \
                    mock.patch.object(Path, 'stat', new=observed_stat), \
                    mock.patch.object(Path, 'lstat', new=observed_lstat):
                result = operation()
            return result, counts

        (old, old_targets), old_counts = measured(
            lambda: retained_inventory(self.runtime, self.selected, SCOPES, Context()))
        (observed, targets), new_counts = measured(self.snapshot)
        self.assert_common_fingerprints(old, observed)
        self.assertEqual(old_targets, targets)
        self.assertEqual(old_counts['resolved_names'], 2 * len(self.selected) + len(SCOPES))
        self.assertEqual(new_counts['resolved_names'], len(SCOPES))
        self.assertEqual(old_counts['resolver_calls'], 2 + len(SCOPES))
        self.assertEqual(new_counts['resolver_calls'], 1)
        self.assertLess(new_counts['path_stats'], old_counts['path_stats'])
        print('collision snapshot operation counts:', {'old': old_counts, 'new': new_counts})

    def test_case_conflicting_declarations_and_selected_leaf_spellings_are_refused(self):
        name = next(iter(self.selected))
        self.selected[name.swapcase()] = self.selected[name]
        with self.assertRaisesRegex(ERRORS, 'Case-conflicting collision source declaration'):
            self.snapshot()
        self.selected.pop(name.swapcase())
        (self.runtime / name).rename(self.runtime / name.casefold())
        with self.assertRaisesRegex(ERRORS, 'Case-conflicting world leaf'):
            self.snapshot()

    def test_case_conflicting_unselected_directories_and_irrelevant_leaves_are_refused(self):
        parent = self.runtime / 'data/object_library/unreferenced'
        first, second = parent / 'Nested', parent / 'nested'
        first.mkdir()
        second.mkdir()
        with self.assertRaisesRegex(ERRORS, 'Case-conflicting Atlas source inventory'):
            self.snapshot()
        first.rmdir()
        second.rmdir()
        self.write('data/object_library/unreferenced/NOTES.INI', b'case alias')
        with self.assertRaisesRegex(ERRORS, 'Case-conflicting Atlas source inventory'):
            self.snapshot()

    def test_selected_provider_case_alias_is_refused(self):
        name = next(iter(self.selected))
        self.write(name.casefold(), b'case alias')
        with self.assertRaisesRegex(ERRORS, '[Cc]ase-conflicting world (destination|leaf)'):
            self.snapshot()

    def test_directory_links_are_refused_even_when_unrelated_to_selected_suffixes(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'secret.geo').write_bytes(b'outside remains untouched')
        link = self.runtime / 'data/object_library/unreferenced/irrelevant.ini'
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ERRORS, 'Linked collision source directory'):
            self.snapshot()
        self.assertEqual((outside / 'secret.geo').read_bytes(), b'outside remains untouched')

    def test_linked_scope_ancestor_is_refused(self):
        directory = self.runtime / 'data/object_library'
        outside = self.root / 'object_library'
        directory.rename(outside)
        directory.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ERRORS, 'Linked or non-directory world destination'):
            self.snapshot()

    def test_writable_selected_leaves_are_refused(self):
        for name in self.selected:
            with self.subTest(name=name):
                path = self.runtime / name
                path.chmod(0o644)
                with self.assertRaisesRegex(ERRORS, 'immutable leaf permissions'):
                    self.snapshot()
                path.chmod(0o444)

    def test_missing_required_geometry_and_other_missing_providers_are_distinguished(self):
        name = next(iter(self.required))
        path = self.runtime / name
        path.unlink()
        with self.assertRaisesRegex(ERRORS, 'Every required original Atlas geometry'):
            self.snapshot()
        self.write(name, b'geometry')
        (self.runtime / ('data/' + package.MAP)).unlink()
        with self.assertRaisesRegex(ERRORS, 'no qualified native profile'):
            self.snapshot()

    def test_warm_snapshot_still_enumerates_extra_providers_and_case_conflicts(self):
        first, _ = self.snapshot()
        second, _ = self.snapshot()
        self.assertEqual(first, second)
        extra = self.write('data/object_library/unreferenced/extra.geo', b'unproved provider')
        with self.assertRaisesRegex(ERRORS, 'no qualified native profile'):
            self.snapshot()
        extra.unlink()
        self.write('data/object_library/unreferenced/NOTES.INI', b'irrelevant alias')
        with self.assertRaisesRegex(ERRORS, 'Case-conflicting Atlas source inventory'):
            self.snapshot()

    def test_inventory_provider_bound_remains_enforced(self):
        with mock.patch.object(package, 'MAX_INPUTS', len(self.selected) - 1):
            with self.assertRaisesRegex(ERRORS, 'inventory exceeds proof bound'):
                self.snapshot()

    def test_cancellation_during_scan_stops_without_reading_payloads(self):
        context = Context(cancel_after=7)
        before = sorted(path.relative_to(self.runtime).as_posix() for path in self.runtime.rglob('*'))
        with mock.patch.object(package, 'pin', side_effect=AssertionError('Inventory must not hash payloads')):
            with self.assertRaisesRegex(InterruptedError, 'fixture cancellation'):
                self.snapshot(context)
        self.assertEqual(context.checks, context.cancel_after)
        after = sorted(path.relative_to(self.runtime).as_posix() for path in self.runtime.rglob('*'))
        self.assertEqual(after, before)

    @contextlib.contextmanager
    def mutate_after_directory_scan(self, target, mutate):
        """Mutate after the real directory stream closes but before final checks."""
        original = package.os.scandir
        mutated = []

        @contextlib.contextmanager
        def observed(path):
            with original(path) as entries:
                yield entries
            if Path(path) == target and not mutated:
                mutate()
                mutated.append(True)

        with mock.patch.object(package.os, 'scandir', side_effect=observed):
            yield mutated

    def test_added_leaf_during_directory_scan_is_refused(self):
        parent = self.runtime / 'data/object_library/group'
        with self.mutate_after_directory_scan(parent, lambda: self.write(
                'data/object_library/group/late.geo', b'late unproved source')) as mutated:
            with self.assertRaisesRegex(ERRORS, 'directory changed'):
                self.snapshot()
        self.assertEqual(mutated, [True])

    def test_same_content_directory_swap_during_scan_is_refused(self):
        parent = self.runtime / 'data/object_library/group'
        replacement = self.root / 'replacement'
        shutil.copytree(parent, replacement)
        old_state = parent.stat()
        os.utime(replacement, ns=(old_state.st_atime_ns, old_state.st_mtime_ns))

        def swap():
            parent.rename(self.root / 'original-group')
            replacement.rename(parent)

        with self.mutate_after_directory_scan(parent, swap) as mutated:
            with self.assertRaisesRegex(ERRORS, 'directory changed'):
                self.snapshot()
        self.assertEqual(mutated, [True])

    def test_same_size_leaf_mutation_after_fingerprint_is_refused(self):
        name = 'data/object_library/group/Building.GEO'
        path = self.runtime / name
        previous = path.stat()
        parent_state = path.parent.stat()

        def mutate():
            path.chmod(0o644)
            path.write_bytes(b'z' * previous.st_size)
            os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
            path.chmod(0o444)
            # Mutating the existing leaf does not change directory timestamps;
            # end-of-pass directory checks alone cannot prove immutable inputs.
            self.assertEqual(path.parent.stat().st_mtime_ns, parent_state.st_mtime_ns)

        with self.mutate_after_directory_scan(path.parent, mutate) as mutated:
            with self.assertRaisesRegex(ERRORS, '(input|leaf|source).*changed|changed.*(input|leaf|source)'):
                self.snapshot()
        self.assertEqual(mutated, [True])

    def test_previously_scanned_directory_swap_is_refused_at_final_anchor(self):
        parent = self.runtime / 'data/object_library/group'
        replacement = self.root / 'replacement'
        shutil.copytree(parent, replacement)
        last_scope = self.runtime / 'data/tricks'
        original_scandir = package.os.scandir
        group_scanned = False
        mutated = []

        @contextlib.contextmanager
        def observed_scan(path):
            nonlocal group_scanned
            with original_scandir(path) as entries:
                yield entries
            if Path(path) == parent:
                group_scanned = True
            if Path(path) == last_scope and group_scanned and not mutated:
                # The collision walk has completed the earlier group and now
                # reached its last scope. Resolver metadata-call counts may
                # change; they must not move this mutation before the scan.
                parent.rename(self.root / 'original-group')
                replacement.rename(parent)
                mutated.append(True)

        with mock.patch.object(package.os, 'scandir', side_effect=observed_scan):
            with self.assertRaisesRegex(ERRORS, 'directory changed before inventory completion'):
                self.snapshot()
        self.assertEqual(mutated, [True])


if __name__ == '__main__':
    unittest.main()
