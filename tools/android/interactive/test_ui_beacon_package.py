"""Exercise actual extraction and fail-closed UI/beacon/save payload boundaries."""
import contextlib
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_ui_beacon_apk as package
import test_reopen_startup_repair_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as prior:
        apk = prior[0]; donor = copy.deepcopy(prior[2])
        donor.update(payloads=copy.deepcopy(prior[3]), runtime_manifest=copy.deepcopy(prior[4]))
        with zipfile.ZipFile(apk) as archive:
            donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        visual_directory = folder/'ui-assets'; visual_directory.mkdir()
        for name in package.VISUAL_ASSETS: (visual_directory/name).write_bytes(('ui-sweep-'+name).encode())
        visual = {'format': 1, 'manifest': {'files_sha256': 'b'*64},
            'files': {name: pin((visual_directory/name).read_bytes()) for name in package.VISUAL_ASSETS}}
        beacon_directory = folder/'beacon-assets'; beacon_directory.mkdir()
        for name in package.BEACON_ASSETS: (beacon_directory/name).write_bytes(('native-graph-'+name).encode())
        beacons = {'format': 1, 'manifest': {'native': 'full-readback-and-world-crc'},
            'files': {name: pin((beacon_directory/name).read_bytes()) for name in package.BEACON_ASSETS}}
        for name in package.HELPERS|package.ADDED_HELPERS:
            (folder/'android/guest'/name).write_bytes(('reviewed-authored-'+name).encode())
        with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
                mock.patch.object(package, 'validate_visual_package', return_value=visual), \
                mock.patch.object(package, 'validate_visual_superset'), mock.patch.object(package, 'verify_visual_streams'), \
                mock.patch.object(package, 'validate_beacons', return_value=beacons):
            runtime, payloads, preflight, _, _ = package.extract_and_repair(apk, donor, folder/'ui-beacon-files', COMMIT,
                visual_directory, beacon_directory)
            output = folder/'ui-beacon.apk'
            with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
                for name in payloads: archive.write(folder/'ui-beacon-files'/name, name)
                for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                    archive.writestr(name, original.read(name))
                archive.writestr('AndroidManifest.xml', b'version-only-update')
            yield output, apk, donor, payloads, runtime, preflight, visual_directory, beacon_directory


def qualification():
    contract = package.module('ui_beacon_test_qualification', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE, 'repository_commit': COMMIT,
        'donor': package.donor_link(), 'checks': {name: True for name in package.CHECKS},
        **{name: False for name in ('physical_gameplay_validated', 'physical_client_timing_validated',
            'physical_visual_assets_validated', 'native_dbserver_recompiled', 'native_client_recompiled',
            'native_mapserver_recompiled', 'java_or_dex_recompiled', 'asset_reimport_required')},
        'test_suites': {name: {'status': 'passed', 'skipped': 0, 'tests_run': 1} for name in contract.TEST_MODULES},
        'tests_run': len(contract.TEST_MODULES), 'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'source_files': {name: pin(b'source') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures': sorted(package.previous.prior.levelup_postgresql_fixtures())}


class UiBeaconPackagingTests(unittest.TestCase):
    def verify(self, values):
        return package.verify_derivative(values[0], values[2], values[3], COMMIT, values[6], values[7])

    def test_new_version_and_exact_successful_public_donor(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.14', 29))
        self.assertEqual(package.donor_link()['run_id'], 37324515114)
        self.assertEqual(package.DONOR_APK['sha256'], '81f199d6380faa09261a85efea6fd3abca6ed58749b8cc68c75d1cd579d454a4')
        self.assertEqual((len(package.REPLACED_PAYLOADS), len(package.ADDED_PAYLOADS)), (7, 3))

    def test_real_extraction_conserves65_unchanged_payloads_and_adds_only_server_beacon_module_and_data(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            self.assertEqual(self.verify(values), values[4])
            self.assertEqual(len(values[3]), 75)
            self.assertEqual(len(set(values[2]['payloads'])-package.REPLACED_PAYLOADS), 65)
            self.assertEqual(values[5], values[2]['server_payload_extraction_preflight'])
            with zipfile.ZipFile(values[0]) as current, zipfile.ZipFile(values[1]) as donor:
                for name in set(values[2]['payloads'])-package.REPLACED_PAYLOADS:
                    self.assertEqual(current.read(name), donor.read(name), name)
                for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                    self.assertEqual(current.read(name), donor.read(name))
            for name in ('levelup_ui_repair', 'reopen_startup_repair', 'task_gate_required', 'startup_only_reopen'):
                self.assertEqual(values[4][name], values[2]['runtime_manifest'][name])
            self.assertFalse(values[4]['ui_beacon']['native_mapserver_recompiled'])

    def test_game_dbserver_mapserver_dlls_world_caches_animations_and_launcher_cannot_change(self):
        names = ('client-runtime.zip', 'game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
            'server-caches.zip', 'client-caches.zip', 'atlas-world-supplement.zip', 'server-animations.pigg',
            'character-avatar-defaults.zip', 'startup-dbserver.exe', 'startup-dbserver-manifest.json',
            'client_interactive_diagnostic.py', 'texture_header_index.py', 'client-launcher.exe')
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'foreign'); values[3][member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_source_bound_helpers_ui_and_beacon_bytes_must_match_actual_inputs(self):
        for name in package.UPDATES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'foreign'); values[3][member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'Authored helper|Qualified UI|Qualified beacon'): self.verify(values)

    def test_extra_missing_unreviewed_or_unchanged_required_replacements_are_rejected(self):
        for mutation in ('add', 'delete', 'unchanged'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if mutation == 'add': values[3]['assets/runtime/foreign.py'] = pin(b'foreign')
                elif mutation == 'delete': values[3].pop('assets/runtime/atlas-beacons.zip')
                else:
                    name = 'assets/runtime/client_visual_assets.py'; values[3][name] = values[2]['payloads'][name]
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_android_shell_and_unknown_archive_members_are_rejected(self):
        for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml', 'assets/runtime/foreign.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if name.endswith('foreign.py'):
                    with zipfile.ZipFile(values[0], 'a') as archive: archive.writestr(name, b'foreign')
                else: replace_member(values[0], name, b'foreign')
                with self.assertRaises(ValueError): self.verify(values)

    def test_manifest_history_and_beacon_proof_cannot_be_relabelled(self):
        for key in ('levelup_ui_repair', 'reopen_startup_repair', 'task_gate_required', 'startup_only_reopen', 'ui_beacon'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                runtime = copy.deepcopy(values[4]); runtime[key] = 'foreign'; raw = package.shared.encoded(runtime)
                member = 'assets/runtime/runtime-manifest.json'; replace_member(values[0], member, raw); values[3][member] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'provenance'): self.verify(values)

    def test_append_only_visual_inventory_refuses_old_texture_replacement_and_non_ui_additions(self):
        before = {f'data/texture_library/old/{n}.texture': pin(str(n).encode()) for n in range(9613)}
        donor = {'_visual_manifest': {'files': before, 'files_sha256': 'f'*64}}
        visual = {'manifest': {'files': {**before, 'data/texture_library/ui/new.texture': pin(b'new')}}}
        self.assertEqual(package.validate_visual_superset(donor, visual)['retained_files'], 9613)
        for mutate in ('replace', 'delete', 'geo', 'unchanged'):
            bad = copy.deepcopy(visual)
            if mutate == 'replace': bad['manifest']['files'][next(iter(before))] = pin(b'foreign')
            elif mutate == 'delete': bad['manifest']['files'].pop(next(iter(before)))
            elif mutate == 'geo': bad['manifest']['files']['data/geo/foreign.geo'] = pin(b'foreign')
            else: bad['manifest']['files'] = before
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): package.validate_visual_superset(donor, bad)

    def test_actual_public_saved_character_delta_is_closed_to_reviewed_normalization_and_beacons(self):
        donor = package.ROOT/'out/ui-beacon-donor'/package.DONOR_APK_NAME
        self.assertTrue(donor.is_file(), 'Exact public 0.13.13 donor required')
        with zipfile.ZipFile(donor) as archive:
            for name in ('native_training_save.py', 'local_character_server.py'):
                current = (package.ROOT/'android/guest'/name).read_bytes()
                self.assertTrue(package.validate_guest_delta(name, archive.read('assets/runtime/'+name), current)['all_other_ast_nodes_retained'])
                with self.assertRaises(ValueError): package.validate_guest_delta(name, archive.read('assets/runtime/'+name), current+b'\nimport foreign\n')

    def test_required_geometry_source_proof_and_cache_key_cannot_be_changed_or_moved_after_checkout(self):
        donor = package.ROOT/'out/ui-beacon-donor'/package.DONOR_APK_NAME
        current = (package.ROOT/'android/guest/local_character_server.py').read_text()
        source_start = current.index('        required_geometry = None\n')
        source_end = current.index('        # Wine FolderCache', source_start)
        source_block = current[source_start:source_end]
        late = "        beacon_archive = self.owner.args.assets / 'atlas-beacons.zip'\n"
        mutations = {
            'late_source_proof': current.replace(source_block, '', 1).replace(late, source_block+late, 1),
            'server_instead_of_client_source': current.replace(
                'self.owner.work, self.owner.args.assets, self.ctx)',
                'self.runtime, self.owner.args.assets, self.ctx)', 1),
            'dynamic_receipt_in_identity': current.replace(
                "required_geometry = geometry_preparation['identity']", 'required_geometry = geometry_preparation', 1),
            'missing_geometry_key': current.replace("            identity['required_geometry'] = required_geometry\n", '            pass\n', 1),
        }
        with zipfile.ZipFile(donor) as archive:
            before = archive.read('assets/runtime/local_character_server.py')
            self.assertTrue(package.validate_guest_delta('local_character_server.py', before, current.encode())['all_other_ast_nodes_retained'])
            for name, source in mutations.items():
                self.assertNotEqual(source, current, name)
                with self.subTest(name=name), self.assertRaises(ValueError):
                    package.validate_guest_delta('local_character_server.py', before, source.encode())

    def test_qualification_requires_every_current_suite_and_real_postgresql_fixture(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            self.assertEqual(package.validate_qualification(qualification(), COMMIT)['status'], 'passed')
            for mutation in ('missing', 'profile_suite', 'profile_source', 'skip', 'fail', 'count', 'native', 'physical', 'pg', 'source'):
                value = qualification(); first = next(iter(value['test_suites']))
                if mutation == 'missing': value['test_suites'].pop(first)
                elif mutation == 'profile_suite': value['test_suites'].pop('test_beacon_runtime_profiles')
                elif mutation == 'profile_source': value['source_files'].pop('tools/android/interactive/test_beacon_runtime_profiles.py')
                elif mutation == 'skip': value['test_suites'][first]['skipped'] = 1
                elif mutation == 'fail': value['test_suites'][first]['status'] = 'failed'
                elif mutation == 'count': value['tests_run'] += 1
                elif mutation == 'native': value['native_mapserver_recompiled'] = True
                elif mutation == 'physical': value['physical_gameplay_validated'] = True
                elif mutation == 'pg': value['postgresql_levelup_fixtures'] = []
                else: value['source_files'].pop(next(iter(value['source_files'])))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): package.validate_qualification(value, COMMIT)

    def test_native_package_receipt_preserves_actual_generation_provenance_and_owned_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            producer = mock.Mock()
            producer.canonical.side_effect = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
            digest = lambda value: package.hashlib.sha256(producer.canonical(value)).hexdigest()
            required = {f'data/object_library/atlas/leaf-{index:03}.geo': pin(b'geometry') for index in range(406)}
            required_source = {name: {**value, 'source_kind': 'synthetic-original-visual-geometry'}
                for name, value in required.items()}
            geo = {**required_source, 'data/player_library/retained.geo': pin(b'player-geometry')}
            world, visual_source = pin(b'world-manifest'), pin(b'public-0.13.13-visual-manifest')
            common = {'data/maps/city_zones/city_01_01/city_01_01.txt': pin(b'Atlas-world'),
                **{f'data/maps/fixture-{index}.txt': pin(b'finite-input') for index in range(5230)}}
            native = {'full_world_crc': '0x12345678', 'native_pathfinder_successes': 32,
                'native_full_graph_readback_verified': True, 'fresh_ordinary_world_crc_verified': True}
            selected = {**common, **required}
            profiles = {name: {'native': native, 'input_files_sha256': digest(selected)}
                for name in ('required_geometry_cold', 'client_visual_reopen')}
            manifest = {'format': 3, 'role': 'authentic_native_atlas_beacon_graph', 'runtime_graph_readback': True,
                'physical_npc_pathing_validated': False, 'native': native,
                'input_files': common, 'input_files_sha256': digest(common),
                'required_geometry_files': required, 'input_profiles': profiles,
                'input_identity': {'world_manifest': world, 'visual_source_manifest': visual_source,
                    'visual_geometry_sha256': digest(geo), 'visual_object_geometry_sha256': digest(required_source),
                    'required_geometry_sha256': digest(required)}}
            producer.PRIMARY_RECOVERY = {'repository_commit': 'b'*40, 'run_conclusion': 'failure',
                'graph': pin(b'synthetic-native-generated-graph')}
            producer.PRIMARY_GENERATION_SOURCES = {'tools/original-fixture-only.py': pin(b'original-source')}
            producer.QUALIFICATION_VISUAL_ARCHIVE = pin(b'synthetic-full-visual-archive')
            producer.QUALIFICATION_VISUAL_MANIFEST = pin(b'synthetic-full-visual-manifest')
            producer.validate_package.return_value = manifest
            (directory/'atlas-beacon-manifest.json').write_text(json.dumps(manifest))
            (directory/'atlas-beacons.zip').write_bytes(b'qualified-native-graph')
            report = {'format': 3, 'repository_commit': 'c'*40, 'generator': pin(b'host-only-Win32-generator'),
                'cleanup_complete': True, 'owned_roles': 0, 'native_worker_spawning_allowed': False,
                'qualification_mode': 'recovered_primary_fresh_proofs',
                'graph_origin': {'kind': 'recovered_primary_native_generation', 'source': producer.PRIMARY_RECOVERY,
                    'generation_sources': producer.PRIMARY_GENERATION_SOURCES, 'original_run_conclusion': 'failure',
                    'primary_generation_server_returncode': 0, 'original_owned_roles': 4,
                    'original_cleanup_complete': True, 'original_native_worker_spawning_allowed': False,
                    'fresh_qualification_still_required': True},
                'profile_verification_processes': 2, 'profile_proofs': profiles,
                'cold_mirror': {'required_geometry_installed_before_mirror': True,
                    'created_before_full_visual_overlay_and_readback': True,
                    'readonly_inputs_hardlinked': True, 'private_cache_roots': ['data/bin', 'data/geobin', 'data/server']},
                'profile_cache_isolation': {name: {'policy': 'empty_private_geobin_before_fresh_readback',
                    'remaining_geometry_cache_files': 0} for name in profiles},
                'qualification_visual': {'archive': producer.QUALIFICATION_VISUAL_ARCHIVE,
                    'manifest': producer.QUALIFICATION_VISUAL_MANIFEST, 'files': 10401,
                    'retained_files': 9613, 'added_original_textures': 788, 'required_geometry_files': 406},
                'evidence': {'evidence/server.log': pin(
                    b'COH_ATLAS_BEACON_FRESH_WORLD_V1 crc=0x12345678\n'
                    b'COH_ATLAS_BEACON_NATIVE_V1 crc=0x12345678 combat=2000 connected=1900 ground=5000 raised=100 blocks=100 paths=32\n')}}
            guest = mock.Mock(); guest.read_manifest.return_value = manifest
            guest.ARCHIVE_BYTES = (directory/'atlas-beacons.zip').stat().st_size
            guest.ARCHIVE_SHA256 = pin((directory/'atlas-beacons.zip').read_bytes())['sha256']
            donor = {'_visual_manifest': {'files': geo}, 'payloads': {
                'assets/runtime/atlas-world-supplement-manifest.json': world,
                'assets/runtime/client-visual-manifest.json': visual_source}}
            report_path = directory/'atlas-beacon-generation-report.json'
            with mock.patch.object(package, 'module', side_effect=lambda name, path: producer if name == 'native_atlas_beacon_producer' else guest):
                report_path.write_text(json.dumps(report))
                validated = package.validate_beacons(directory, COMMIT, donor)
                self.assertEqual(validated['generation'], report)
                self.assertEqual(validated['manifest'], manifest)
                self.assertNotEqual(validated['generation'], validated['manifest'])
                self.assertNotEqual(digest(required_source), digest(required))
                self.assertTrue(all(set(row) == {'bytes', 'sha256'} for row in validated['manifest']['required_geometry_files'].values()))
                for field, wrong in (('cleanup_complete', False), ('owned_roles', 4),
                        ('qualification_mode', 'new_generation'), ('native_worker_spawning_allowed', True)):
                    value = dict(report); value[field] = wrong; report_path.write_text(json.dumps(value))
                    with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'ownership/cleanup'):
                        package.validate_beacons(directory, COMMIT, donor)
                for mutation, message in (('profile_count', 'isolated native'), ('cold_cache_shared', 'isolated native'),
                        ('geometry_after_mirror', 'isolated native'), ('missing_profile', 'Both exact'),
                        ('none_profile', 'Both exact'), ('cold_crc', 'Fresh native profile'),
                        ('cold_input_hash', 'Fresh native profile'), ('cold_missing_geometry', 'Fresh native profile'),
                        ('foreign_required', 'exact shipped'), ('source_required_hash', 'exact shipped'),
                        ('physical_required_hash', 'exact shipped'), ('required_extra_metadata', 'exact shipped'),
                        ('legacy_optional', 'exact shipped'), ('origin_source', 'Original native'),
                        ('origin_roles', 'Original native'), ('origin_cleanup', 'Original native'),
                        ('origin_success_relabel', 'Original native'), ('shared_geobin', 'empty private'),
                        ('missing_isolation', 'empty private'), ('foreign_full_visual', 'visual proof source'),
                        ('legacy_format', 'proof scope')):
                    changed, changed_report = copy.deepcopy(manifest), copy.deepcopy(report)
                    if mutation == 'profile_count': changed_report['profile_verification_processes'] = 1
                    elif mutation == 'cold_cache_shared': changed_report['cold_mirror']['private_cache_roots'] = []
                    elif mutation == 'geometry_after_mirror': changed_report['cold_mirror']['required_geometry_installed_before_mirror'] = False
                    elif mutation == 'missing_profile': changed['input_profiles'].pop('required_geometry_cold')
                    elif mutation == 'none_profile': changed['input_profiles']['base_world'] = changed['input_profiles'].pop('required_geometry_cold')
                    elif mutation == 'cold_crc': changed['input_profiles']['required_geometry_cold']['native'] = {**native, 'full_world_crc': '0x87654321'}
                    elif mutation == 'cold_input_hash': changed['input_profiles']['required_geometry_cold']['input_files_sha256'] = 'f'*64
                    elif mutation == 'cold_missing_geometry': changed['input_profiles']['required_geometry_cold']['input_files_sha256'] = digest(common)
                    elif mutation == 'foreign_required':
                        changed['required_geometry_files'].pop(next(iter(required)))
                        changed['required_geometry_files']['data/object_library/foreign.geo'] = pin(b'foreign')
                    elif mutation == 'source_required_hash': changed['input_identity']['visual_object_geometry_sha256'] = digest(required)
                    elif mutation == 'physical_required_hash': changed['input_identity']['required_geometry_sha256'] = digest(required_source)
                    elif mutation == 'required_extra_metadata': changed['required_geometry_files'] = copy.deepcopy(required_source)
                    elif mutation == 'legacy_optional': changed['optional_input_files'] = copy.deepcopy(required)
                    elif mutation == 'origin_source': changed_report['graph_origin']['source'] = {'repository_commit': 'f'*40}
                    elif mutation == 'origin_roles': changed_report['graph_origin']['original_owned_roles'] = 0
                    elif mutation == 'origin_cleanup': changed_report['graph_origin']['original_cleanup_complete'] = False
                    elif mutation == 'origin_success_relabel': changed_report['graph_origin']['original_run_conclusion'] = 'success'
                    elif mutation == 'shared_geobin': changed_report['profile_cache_isolation']['required_geometry_cold']['remaining_geometry_cache_files'] = 1
                    elif mutation == 'missing_isolation': changed_report['profile_cache_isolation'].pop('client_visual_reopen')
                    elif mutation == 'foreign_full_visual': changed_report['qualification_visual']['archive'] = pin(b'foreign-visual')
                    elif mutation == 'legacy_format': changed['format'] = 2
                    if mutation not in ('profile_count', 'cold_cache_shared', 'geometry_after_mirror',
                            'origin_source', 'origin_roles', 'origin_cleanup', 'origin_success_relabel',
                            'shared_geobin', 'missing_isolation', 'foreign_full_visual'):
                        changed_report['profile_proofs'] = changed['input_profiles']
                    (directory/'atlas-beacon-manifest.json').write_text(json.dumps(changed))
                    producer.validate_package.return_value = changed; guest.read_manifest.return_value = changed
                    report_path.write_text(json.dumps(changed_report))
                    with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, message):
                        package.validate_beacons(directory, COMMIT, donor)
                (directory/'atlas-beacon-manifest.json').write_text(json.dumps(manifest))
                producer.validate_package.return_value = manifest; guest.read_manifest.return_value = manifest
                report_path.write_text(json.dumps(report)); guest.ARCHIVE_SHA256 = 'f'*64
                with self.assertRaisesRegex(ValueError, 'archive pin'): package.validate_beacons(directory, COMMIT, donor)

    def test_existing_release_is_never_replaced(self):
        api = mock.Mock(); api.request.return_value = {'id': 1}
        assets = tuple(Path(name) for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME)); base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            with self.assertRaisesRegex(ValueError, 'Existing release'): package.publish_release(api, {'repository_commit': COMMIT}, assets, 'notes')
        self.assertFalse(any(call.kwargs.get('method') in ('POST', 'PATCH') for call in api.request.call_args_list))

    def test_workflow_uses_native_generation_and_exact_donor_then_sdk_identity_checks(self):
        source = (package.ROOT/package.WORKFLOW).read_text()
        for expected in ('run-id: 37324515114', 'C:/bcn-src', '--work C:/bcn-run', '--target MapServer', '--timeout-seconds 5400',
                'generate_atlas_beacons.py', 'reference-inputs-receipt.json', 'COH_ATLAS_BEACON_REUSE_RUN_ID',
                '35.0.0', 'android-35/android.jar', 'coh-client-interactive.jks', package.APK_NAME):
            self.assertIn(expected, source)
        native_job = source.split('  beacons:\n', 1)[1].split('  qualify:\n', 1)[0]
        self.assertLess(native_job.index('core.autocrlf false'), native_job.index('actions/checkout@'))
        self.assertIn('actions/setup-java@v4', native_job)
        self.assertIn("java-version: '17'", native_job)
        self.assertIn('Collect host build and role evidence on the repository drive', native_job)
        self.assertIn('Copy-Item -LiteralPath $entry.source', native_job)
        evidence_upload = native_job.split('name: coh-ui-beacon-generation-evidence', 1)[1]
        self.assertNotIn('C:/', evidence_upload)
        self.assertIn('out/ui-beacon-native/evidence/', evidence_upload)
        self.assertIn('host-only-beacon-generator.pdb', native_job)
        self.assertIn('native-internal', native_job)
        self.assertIn('$count -ge 128', native_job)
        self.assertIn('$total + $file.Length -gt 268435456', native_job)
        self.assertIn('Verify successful native reuse against current producers world and frozen guest pins', native_job)
        self.assertIn("producer.validate_package(directory, os.environ['GITHUB_SHA'])", native_job)
        self.assertIn("report['repository_commit'] != run['head_sha']", native_job)
        self.assertIn("guest.read_manifest(directory / 'atlas-beacon-manifest.json')", native_job)
        self.assertIn("guest.ARCHIVE_SHA256", native_job)
        self.assertIn('timeout-minutes: 10', source)
        self.assertIn('for attempt in range(3):', source)
        self.assertIn('time.monotonic() + 160', source)
        self.assertIn('urlopen(request, timeout=20)', source)
        self.assertIn('--apk out/ui-beacon-public/'+package.APK_NAME, source)
        self.assertIn('build_ui_beacon_apk.py audit', source)
        self.assertLess(source.index('build_ui_beacon_apk.py audit'), source.index('Record only completed public SDK and payload audit'))
        self.assertIn('coh-ui-beacon-public-byte-audit', source)
        for forbidden in ('--target DbServer', 'discover_client_visual_assets.py', 'prepare_client_appearance_assets.py'):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__': unittest.main(verbosity=2)
