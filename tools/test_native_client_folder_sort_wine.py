import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import qualify_native_client_folder_sort_wine as q

class PairedAdmission(unittest.TestCase):
    def fixture(self, root):
        imported = root / 'original'; imported.mkdir(); work = root / 'work'; work.mkdir()
        data = work / 'data'; data.mkdir(); (data / 'fx').mkdir()
        source = imported / 'one.fx'; source.write_bytes(b'original source'); source.chmod(0o444)
        (data / 'fx' / 'one.fx').symlink_to(source)
        return imported, work, source

    def test_provider_same_bytes_and_membership_rehash_equal(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary))
            a = q.provider_snapshot(work, imported); b = q.provider_snapshot(work, imported)
            self.assertEqual(a, b); self.assertTrue(a['complete_bytes_rehashed'])
            self.assertFalse(a['persistent_authority_created'])

    def test_changed_source_even_same_size_is_not_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary))
            before = q.provider_snapshot(work, imported)
            source.chmod(0o600); source.write_bytes(b'changed! source'); source.chmod(0o444)
            self.assertNotEqual(before, q.provider_snapshot(work, imported))

    def test_same_bytes_changed_target_date_is_not_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary))
            before = q.provider_snapshot(work, imported); info = source.stat()
            os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000000))
            self.assertNotEqual(before, q.provider_snapshot(work, imported))

    def test_same_bytes_changed_readonly_permissions_is_not_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary))
            before = q.provider_snapshot(work, imported); source.chmod(0o440)
            self.assertNotEqual(before, q.provider_snapshot(work, imported))

    def auxiliary_fixture(self, root):
        work = root / 'aux-work'; work.mkdir(); assets = root / 'assets'; assets.mkdir()
        (work / 'tools').mkdir(); (work / 'piggs').mkdir()
        for name in ('server-animations.pigg', 'server-animation-manifest.json', 'client-launcher.exe',
                     'client-probe.exe', 'observer.py'):
            (assets / name).write_bytes(name.encode()); (assets / name).chmod(0o400)
        (work / 'piggs/server-animations.pigg').symlink_to(assets / 'server-animations.pigg')
        (work / 'piggs/client-animation-link.json').write_bytes(b'owned animation receipt')
        (work / 'client-work.json').write_bytes(b'owned native prerequisite receipt')
        for name in q.TEXTURE_AUXILIARY:
            (work / name).write_bytes(name.encode()); (work / name).chmod(0o400)
        fixture = {'supplements': {'client_animation_package': {'pigg': q.pin(assets / 'server-animations.pigg')}},
                   'launcher': q.pin(assets / 'client-launcher.exe'),
                   'packaged_guest_sources': {'observer.py': q.pin(assets / 'observer.py')}}
        return work, assets, fixture

    def test_immutable_auxiliary_census_rehashes_animation_helpers_and_texture_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, assets, fixture = self.auxiliary_fixture(Path(temporary))
            with patch.object(q.baseline, 'CLIENT_PROBE', q.pin(assets / 'client-probe.exe')):
                before = q.auxiliary_snapshot(work, assets, fixture)
                self.assertEqual(before, q.auxiliary_snapshot(work, assets, fixture))
                self.assertIn('piggs/server-animations.pigg', before['stable_inputs'])
                self.assertEqual(set(before['native_texture_binding']), set(q.TEXTURE_AUXILIARY))
                self.assertTrue(before['shader_and_extracted_prerequisite_inputs_covered_by_data_census'])

    def test_same_bytes_auxiliary_dates_and_modes_change_census(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, assets, fixture = self.auxiliary_fixture(Path(temporary))
            with patch.object(q.baseline, 'CLIENT_PROBE', q.pin(assets / 'client-probe.exe')):
                before = q.auxiliary_snapshot(work, assets, fixture)
                source = assets / 'server-animations.pigg'; info = source.stat()
                os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000000))
                dated = q.auxiliary_snapshot(work, assets, fixture); self.assertNotEqual(before, dated)
                source.chmod(0o440); self.assertNotEqual(dated, q.auxiliary_snapshot(work, assets, fixture))

    def test_unexpected_or_retargeted_animation_pig_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, assets, fixture = self.auxiliary_fixture(Path(temporary))
            with patch.object(q.baseline, 'CLIENT_PROBE', q.pin(assets / 'client-probe.exe')):
                (work / 'piggs/extra.pigg').write_bytes(b'unknown')
                with self.assertRaisesRegex(ValueError, 'membership'): q.auxiliary_snapshot(work, assets, fixture)
                (work / 'piggs/extra.pigg').unlink()
                link = work / 'piggs/server-animations.pigg'; link.unlink()
                link.symlink_to(assets / 'observer.py')
                with self.assertRaisesRegex(ValueError, 'resource link'): q.auxiliary_snapshot(work, assets, fixture)

    def test_texture_binding_mutation_changes_only_stage_census(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, assets, fixture = self.auxiliary_fixture(Path(temporary))
            with patch.object(q.baseline, 'CLIENT_PROBE', q.pin(assets / 'client-probe.exe')):
                before = q.auxiliary_snapshot(work, assets, fixture)
                pack = work / q.TEXTURE_AUXILIARY[0]; pack.chmod(0o600); pack.write_bytes(b'new binding'); pack.chmod(0o400)
                after = q.auxiliary_snapshot(work, assets, fixture)
                self.assertEqual(before['stable_inputs'], after['stable_inputs'])
                self.assertNotEqual(before['native_texture_binding'], after['native_texture_binding'])

    def test_auxiliary_helper_content_mutation_rejected_against_fixture_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, assets, fixture = self.auxiliary_fixture(Path(temporary))
            with patch.object(q.baseline, 'CLIENT_PROBE', q.pin(assets / 'client-probe.exe')):
                helper = assets / 'observer.py'; helper.chmod(0o600); helper.write_bytes(b'changed helper'); helper.chmod(0o400)
                with self.assertRaisesRegex(ValueError, 'Authenticated auxiliary'): q.auxiliary_snapshot(work, assets, fixture)

    def test_unrelated_source_link_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); imported, work, source = self.fixture(root)
            outside = root / 'outside'; outside.write_bytes(b'other'); outside.chmod(0o444)
            leaf = work / 'data/fx/one.fx'; leaf.unlink(); leaf.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'escaped'): q.provider_snapshot(work, imported)

    def test_writable_imported_link_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary)); source.chmod(0o600)
            with self.assertRaisesRegex(ValueError, 'writable'): q.provider_snapshot(work, imported)

    def test_directory_alias_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary))
            (work / 'data/fx/ONE.FX').symlink_to(source)
            with self.assertRaisesRegex(ValueError, 'Aliased'): q.provider_snapshot(work, imported)

    def test_ordinary_directory_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary))
            (work / 'data/fx2').symlink_to(imported, target_is_directory=True)
            with self.assertRaises(ValueError): q.provider_snapshot(work, imported)

    def test_cache_exclusion_does_not_exclude_identifier_or_other_source(self):
        self.assertTrue(q.cached(Path('bin/one.bin')))
        self.assertTrue(q.cached(Path('server/bin/one.bin')))
        self.assertFalse(q.cached(Path('server/db/one.attribute')))
        self.assertFalse(q.cached(Path('bin2/one.bin')))

    def test_identifier_changes_alter_provider_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary))
            ids = work / 'data/one.dbidmap'; ids.write_bytes(b'id1')
            before = q.provider_snapshot(work, imported); ids.write_bytes(b'id2')
            self.assertNotEqual(before, q.provider_snapshot(work, imported))

    def test_private_bin_changes_kept_outside_original_provider_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            imported, work, source = self.fixture(Path(temporary))
            cache = work / 'data/bin'; cache.mkdir(); leaf = cache / 'one.bin'; leaf.write_bytes(b'old')
            before = q.provider_snapshot(work, imported); leaf.write_bytes(b'new')
            self.assertEqual(before, q.provider_snapshot(work, imported))

    def test_constructor_row_requires_actual_bounded_sorted_execution(self):
        row = 'COH_CLIENT_FOLDER_METADATA_SORT_V1 entries=6852 capacity_bytes=2654208 reason=sorted arrival_inversions=2918 callback_absent=1 limit=16384 bounded_rows=256'
        self.assertEqual(q.parse_constructor(row)[0]['entries'], 6852)
        for changed in (row.replace('entries=6852', 'entries=16385'), row.replace('capacity_bytes=2654208', 'capacity_bytes=5308417'),
                        row.replace('callback_absent=1', 'callback_absent=0'), row.replace('reason=sorted', 'reason=unknown')):
            with self.subTest(changed=changed), self.assertRaises(ValueError): q.parse_constructor(changed)

    def test_constructor_absent_or_only_fallback_is_not_optimization_success(self):
        with self.assertRaises(ValueError): q.parse_constructor('Loaded all data!')
        row = 'COH_CLIENT_FOLDER_METADATA_SORT_V1 entries=128 capacity_bytes=41472 reason=allocation_failure arrival_inversions=10 callback_absent=1 limit=16384 bounded_rows=256'
        with self.assertRaises(ValueError): q.parse_constructor(row)

    def test_current_texture_counts_not_simulated_connection(self):
        value = q.logical_counts('COH_TEXTURE_INDEX_V1 hits=38986 ordinary_reads=0\n[INFO] Loaded grouplibs: 3224 files, 75433 names\n')
        self.assertEqual(value['texture_header_hits'], 38986)
        with self.assertRaises(ValueError): q.logical_counts('COH_TEXTURE_INDEX_V1 hits=38986 ordinary_reads=0\nCOH_TEXTURE_INDEX_V1 hits=1 ordinary_reads=0')

    def test_native_DLL_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); path = root / 'cg.dll'; path.write_bytes(b'new')
            with self.assertRaisesRegex(ValueError, 'changed'):
                q.native_closure(root, {'cg.dll': {'size': 3, 'sha256': '0' * 64}})

    def test_complete_renderer_dictionary_required_before_exact_paired_comparison(self):
        actual = {'vendor': 'Mesa', 'renderer': 'llvmpipe', 'gl_version': '4.5', 'renderer_classification': 'software'}
        phase = {'evidence': {'current_native_evidence': {'graphics_observation': actual}}}
        self.assertEqual(q.renderer_identity(phase), actual)
        actual.pop('gl_version')
        with self.assertRaisesRegex(ValueError, 'renderer identity'): q.renderer_identity(phase)

    def test_candidate_environment_retains_quality_and_diagnostics(self):
        env = q.environment(Path('/owned/prefix'), {'COH_TEXTURE_HEADER_ID': 'a' * 64})
        self.assertEqual(env['COH_CLIENT_GRAPHICS_PROFILE'], 'performance')
        self.assertEqual(env['COH_CLIENT_GAMEPLAY_FPS'], '30')
        self.assertEqual(env['COH_CLIENT_FOLDER_METADATA_SORT'], '1')
        self.assertEqual(env['COH_CLIENT_RENDER_PIPELINE'], '0')
        self.assertEqual(env['WINEPREFIX'], '/owned/prefix')

if __name__ == '__main__': unittest.main()
