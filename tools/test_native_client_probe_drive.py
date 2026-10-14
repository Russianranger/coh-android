"""Actual host FD/link guards with synthetic census; no Wine/SDK execution."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import native_client_probe_drive as drive
import test_native_client_census_observed_bridge as fixtures


def packet(extra=None):
    rows = {'': [fixtures.projection(branch, 16, 0) for branch in drive.bridge.BRANCHES]}
    rows.update({branch: [] for branch in drive.bridge.BRANCHES})
    rows['texture_library'] = [fixtures.projection('.named', 3), fixtures.projection('ordinary.geo'),
                               fixtures.projection('thing.texture')]
    if extra:
        extra(rows)
    for current in rows.values():
        current.sort(key=lambda row: row[44:304].split(b'\0', 1)[0].lower())
    return fixtures.census(rows)


class DriveTests(unittest.TestCase):
    def paths(self, base):
        prefix, work = base/'prefix', base/'work'
        prefix.mkdir(mode=0o700); (prefix/'dosdevices').mkdir()
        (work/'data').mkdir(parents=True)
        info = prefix.lstat()
        return prefix, work, [info.st_dev, info.st_ino, info.st_uid]

    def context(self, base, value=None):
        prefix, work, identity = self.paths(base)
        return drive.MappedProbeDrive(prefix, work, identity, value or packet())

    def test_admit_check_and_close_preserve_exact_owned_mapping_and_all_false(self):
        with tempfile.TemporaryDirectory() as temporary:
            context = self.context(Path(temporary))
            with mock.patch.object(drive.startup, 'process_census', return_value=[]) as census:
                admitted = context.admit()
            self.assertEqual(census.call_count, 2)
            self.assertEqual(context.native_root, 'X:/data')
            link = context.prefix/'dosdevices/x:'
            self.assertEqual(os.readlink(link), str(context.work))
            with mock.patch.object(drive.startup, 'process_census', side_effect=AssertionError('active check cannot census')):
                checked = context.check()
            self.assertEqual(checked['successful_identity_checks'], 2)
            self.assertTrue(checked['created_exclusively'])
            self.assertEqual(checked['work_identity'], drive._identity(context.work.stat()))
            self.assertEqual(checked['data_identity'], drive._identity((context.work/'data').stat()))
            for key in drive.FALSE_AUTHORITY:
                self.assertIs(admitted[key], False)
                self.assertIs(admitted['source_path_observation'][key], False)
            descriptors = [fd for fd, _ in context._held.values()] + [context._target_fd]
            context.close(); context.close()
            self.assertTrue(link.is_symlink())
            self.assertEqual(context.report()['held_directory_count'], 0)
            self.assertTrue(context.report()['held_directory_identities'])
            for fd in descriptors:
                with self.assertRaises(OSError): os.fstat(fd)
            with self.assertRaises(ValueError): context.check()
            with self.assertRaises(ValueError): context.admit()

    def test_existing_x_drive_aliases_and_double_colon_never_overwritten(self):
        for name in ('x:', 'X:', 'x::', 'X::'):
            with tempfile.TemporaryDirectory() as temporary:
                context = self.context(Path(temporary)); link = context.prefix/'dosdevices'/name
                link.symlink_to('/unrelated-preserved')
                with mock.patch.object(drive.startup, 'process_census', return_value=[]), self.assertRaises(ValueError):
                    context.admit()
                self.assertEqual(os.readlink(link), '/unrelated-preserved')
                self.assertFalse(context.report()['created_exclusively'])
                self.assertEqual(context._held, {})

    def test_live_or_unreadable_prefix_census_refuses_creation_and_closes_handles(self):
        for outcome in ([{'pid': 9}], None, ValueError('unreadable census')):
            with tempfile.TemporaryDirectory() as temporary:
                context = self.context(Path(temporary))
                arguments = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
                with mock.patch.object(drive.startup, 'process_census', **arguments), self.assertRaises(ValueError):
                    context.admit()
                self.assertFalse((context.prefix/'dosdevices/x:').is_symlink())
                self.assertEqual(context._held, {})

    def test_prefix_becoming_live_after_creation_retains_owned_alias_but_closes_handles(self):
        with tempfile.TemporaryDirectory() as temporary:
            context = self.context(Path(temporary))
            with mock.patch.object(drive.startup, 'process_census', side_effect=[[], [{'pid': 9}]]), self.assertRaises(ValueError):
                context.admit()
            self.assertTrue((context.prefix/'dosdevices/x:').is_symlink())
            self.assertTrue(context.report()['created_exclusively'])
            self.assertEqual(context._held, {})

    def test_link_retarget_replacement_or_case_alias_terminally_refused(self):
        for mode in ('retarget', 'replace-same-target', 'casealias', 'doublecolon'):
            with tempfile.TemporaryDirectory() as temporary:
                context = self.context(Path(temporary)); link = context.prefix/'dosdevices/x:'
                with mock.patch.object(drive.startup, 'process_census', return_value=[]): context.admit()
                if mode in ('retarget', 'replace-same-target'):
                    link.unlink(); link.symlink_to('/unrelated' if mode == 'retarget' else context.work)
                else:
                    (context.prefix/'dosdevices'/('X:' if mode == 'casealias' else 'x::')).symlink_to(context.work)
                with self.assertRaises(ValueError): context.check()
                self.assertEqual(context._held, {})
                self.assertTrue(link.is_symlink())

    def test_replaced_prefix_dosdevices_work_data_and_ancestor_refused(self):
        for label in ('prefix', 'dosdevices', 'work', 'data', 'ancestor'):
            with tempfile.TemporaryDirectory() as temporary:
                outer = Path(temporary); base = outer/'owned'; base.mkdir()
                context = self.context(base)
                with mock.patch.object(drive.startup, 'process_census', return_value=[]): context.admit()
                target = {'prefix': context.prefix, 'dosdevices': context.prefix/'dosdevices',
                          'work': context.work, 'data': context.work/'data', 'ancestor': base}[label]
                target.rename(target.with_name(target.name+'-old')); target.mkdir(mode=0o700)
                with self.assertRaises(ValueError): context.check()
                self.assertEqual(context._held, {})

    def test_symlinked_directory_or_ancestor_admission_refused(self):
        for label in ('prefix', 'dosdevices', 'work', 'data', 'ancestor'):
            with tempfile.TemporaryDirectory() as temporary:
                outer = Path(temporary); base = outer/'owned'; base.mkdir()
                prefix, work, identity = self.paths(base)
                target = {'prefix': prefix, 'dosdevices': prefix/'dosdevices',
                          'work': work, 'data': work/'data', 'ancestor': base}[label]
                old = target.with_name(target.name+'-old'); target.rename(old); target.symlink_to(old, target_is_directory=True)
                context = drive.MappedProbeDrive(prefix, work, identity, packet())
                with mock.patch.object(drive.startup, 'process_census', return_value=[]), self.assertRaises(OSError): context.admit()
                self.assertEqual(context._held, {})

    def test_modes_identity_and_owned_uid_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            prefix, work, identity = self.paths(Path(temporary))
            for invalid in ([0, 0, os.geteuid()], [True, identity[1], identity[2]], [*identity[:2], identity[2]+1]):
                if invalid[0] is True or invalid[2] != os.geteuid():
                    with self.assertRaises(ValueError): drive.MappedProbeDrive(prefix, work, invalid, packet())
                else:
                    context = drive.MappedProbeDrive(prefix, work, invalid, packet())
                    with mock.patch.object(drive.startup, 'process_census', return_value=[]), self.assertRaises(ValueError): context.admit()
            context = drive.MappedProbeDrive(prefix, work, identity, packet()); prefix.chmod(0o755)
            with mock.patch.object(drive.startup, 'process_census', return_value=[]), self.assertRaises(ValueError): context.admit()
            prefix.chmod(0o700); context = drive.MappedProbeDrive(prefix, work, identity, packet())
            with mock.patch.object(drive.startup, 'process_census', return_value=[]): context.admit()
            work.chmod(0o750)
            with self.assertRaises(ValueError): context.check()

    def test_exclusive_creation_race_and_open_failure_close_all_handles(self):
        for stage in ('symlink', 'mapped_open'):
            with tempfile.TemporaryDirectory() as temporary:
                context = self.context(Path(temporary)); real_open = drive.os.open
                def opened(path, *args, **kwargs):
                    if path == 'x:': raise OSError('injected mapped open failure')
                    return real_open(path, *args, **kwargs)
                patch = mock.patch.object(drive.os, 'symlink', side_effect=FileExistsError('raced')) if stage == 'symlink' else mock.patch.object(drive.os, 'open', side_effect=opened)
                with mock.patch.object(drive.startup, 'process_census', return_value=[]), patch, self.assertRaises(OSError): context.admit()
                self.assertEqual(context._held, {})
                self.assertIsNone(context._target_fd)
                self.assertEqual((context.prefix/'dosdevices/x:').is_symlink(), stage == 'mapped_open')

    def test_complete_path_census_keeps_dot_nontexture_empty_and_alias_bounds(self):
        def extend(rows):
            rows['texture_library'].append(fixtures.projection('.dir', 16, 0))
            rows['texture_library/.dir'] = [fixtures.projection('file.geo', alternate='FILE~1.GEO')]
            rows['fx'] = [fixtures.projection('empty', 16, 0)]
            rows['fx/empty'] = []
        value = drive._path_observation(packet(extend))
        self.assertEqual(value['source_rows'], value['path_counts']['row'])
        self.assertEqual(value['path_counts']['dot_alias'], 2*(value['source_directories']-1))
        self.assertEqual(value['path_counts']['wildcard'], value['source_directories']-1)
        self.assertEqual(value['path_counts']['projected_short_alias'], 1)
        self.assertTrue(value['all_constructed_paths_below_MAX_PATH'])
        self.assertFalse(value['root_enumeration_claimed'])
        self.assertLess(value['maximum_path_characters'], 260)
        self.assertEqual(drive._path_observation(drive.bridge.decode(packet())), drive._path_observation(packet()))

    def test_path_limits_include_wildcard_dot_aliases_and_all_long_nontexture_rows(self):
        for relative_length, accepted in ((248, True), (249, False)):
            # X:/data + '/' =8; the synthesized /.. requires3 more characters.
            name = 'a'*(relative_length-len('texture_library/'))
            def extend(rows):
                rows['texture_library'] = [fixtures.projection(name, 16, 0)]
                rows['texture_library/'+name] = []
            if accepted:
                value = drive._path_observation(packet(extend)); self.assertEqual(value['maximum_path_characters'], 259)
            else:
                with self.assertRaises(ValueError): drive._path_observation(packet(extend))
        for length, accepted in ((235, True), (236, False)):
            def extend(rows): rows['texture_library'] = [fixtures.projection('n'*length)]
            if accepted:
                value = drive._path_observation(packet(extend)); self.assertEqual(value['maximum_path_characters'], 259)
            else:
                with self.assertRaises(ValueError): drive._path_observation(packet(extend))

    def test_namespace_admission_precedes_generation_then_single_borrowed_packet_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            prefix, work, identity = self.paths(Path(temporary))
            context = drive.MappedProbeDrive(prefix, work, identity)
            with mock.patch.object(drive.startup, 'process_census', return_value=[]): before = context.admit()
            self.assertFalse(before['path_census_admitted'])
            self.assertIsNone(before['source_path_observation'])
            self.assertTrue(before['link']['identity'])
            with self.assertRaises(ValueError): unused = context.native_root
            context.check()  # Namespace-only checks remain available.
            current = packet(); bound = context.bind_census(current)
            self.assertIs(context._view.packet, current)
            self.assertTrue(bound['path_census_admitted'])
            self.assertEqual(context.native_root, 'X:/data')
            self.assertEqual(context.require_census()['generation'], drive.bridge.decode(current).generation)
            self.assertEqual(before['link']['identity'], bound['link']['identity'])
            with self.assertRaises(ValueError): context.bind_census(current)
            self.assertEqual(context.report()['held_directory_count'], 0)
            self.assertTrue(context.report()['path_census_previously_bound'])

    def test_failed_census_binding_terminally_closes_held_namespace_without_deleting_alias(self):
        with tempfile.TemporaryDirectory() as temporary:
            prefix, work, identity = self.paths(Path(temporary))
            context = drive.MappedProbeDrive(prefix, work, identity)
            with mock.patch.object(drive.startup, 'process_census', return_value=[]): context.admit()
            with self.assertRaises(ValueError): context.bind_census(packet()[:-1])
            self.assertEqual(context._held, {})
            self.assertTrue((prefix/'dosdevices/x:').is_symlink())
            self.assertFalse(context.report()['path_census_admitted'])
            with self.assertRaises(ValueError): context.bind_census(packet())

    def test_incomplete_mutable_or_unsafe_census_cannot_create_mapping(self):
        for mutate in (lambda rows: rows.pop('scripts.loc'),
                       lambda rows: rows.__setitem__('scripts.loc', [fixtures.projection('bad.')]),
                       lambda rows: rows['texture_library'].append(fixtures.projection('Thing.texture')),
                       lambda rows: rows.__setitem__('extra', [])):
            with tempfile.TemporaryDirectory() as temporary:
                prefix, work, identity = self.paths(Path(temporary))
                with self.assertRaises(ValueError): drive.MappedProbeDrive(prefix, work, identity, packet(mutate))
                self.assertFalse((prefix/'dosdevices/x:').is_symlink())
        for value in (bytearray(packet()), None, packet()[:-1]):
            with self.assertRaises(ValueError): drive._path_observation(value)

    def test_canonical_disjoint_host_paths_and_no_generic_drive_selection(self):
        for value in ('relative', '/tmp/../work', '//tmp/work', '/tmp/back\\slash', '/tmp/c:drive', '/', '/tmp/./work'):
            with self.assertRaises(ValueError): drive._absolute(value)
        with tempfile.TemporaryDirectory() as temporary:
            prefix, work, identity = self.paths(Path(temporary))
            for target in (prefix, prefix/'dosdevices', prefix.parent):
                with self.assertRaises(ValueError): drive.MappedProbeDrive(prefix, target, identity, packet())
        self.assertEqual(drive.LINK_NAME, 'x:')
        self.assertEqual(drive.NATIVE_ROOT, 'X:/data')


if __name__ == '__main__':
    unittest.main()
