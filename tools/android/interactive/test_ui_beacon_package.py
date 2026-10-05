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

    def test_real_extraction_conserves72_old_payloads_and_adds_only_server_beacon_module_and_data(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            self.assertEqual(self.verify(values), values[4])
            self.assertEqual(len(values[3]), 75)
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

    def test_qualification_requires_every_current_suite_and_real_postgresql_fixture(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            self.assertEqual(package.validate_qualification(qualification(), COMMIT)['status'], 'passed')
            for mutation in ('missing', 'skip', 'fail', 'count', 'native', 'physical', 'pg', 'source'):
                value = qualification(); first = next(iter(value['test_suites']))
                if mutation == 'missing': value['test_suites'].pop(first)
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
            geo = {'data/object_library/atlas.geo': pin(b'geometry')}
            world = pin(b'world-manifest')
            manifest = {'role': 'authentic_native_atlas_beacon_graph', 'runtime_graph_readback': True,
                'physical_npc_pathing_validated': False, 'input_identity': {'world_manifest': world,
                    'visual_geometry_sha256': package.hashlib.sha256(package.shared.encoded(geo)).hexdigest()}}
            # Match the producer's canonical encoding (no indentation/newline).
            producer = mock.Mock()
            producer.canonical.side_effect = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
            manifest['input_identity']['visual_geometry_sha256'] = package.hashlib.sha256(producer.canonical(geo)).hexdigest()
            producer.validate_package.return_value = manifest
            (directory/'atlas-beacon-manifest.json').write_text(json.dumps(manifest))
            (directory/'atlas-beacons.zip').write_bytes(b'qualified-native-graph')
            report = {'repository_commit': 'b'*40, 'generator': pin(b'host-only-Win32-generator'),
                'cleanup_complete': True, 'owned_roles': 4, 'native_worker_spawning_allowed': False,
                'evidence': {'evidence/server.log': pin(b'native-CRC-readback-and-path-witness')}}
            guest = mock.Mock(); guest.read_manifest.return_value = manifest
            guest.ARCHIVE_BYTES = (directory/'atlas-beacons.zip').stat().st_size
            guest.ARCHIVE_SHA256 = pin((directory/'atlas-beacons.zip').read_bytes())['sha256']
            donor = {'_visual_manifest': {'files': geo}, 'payloads': {'assets/runtime/atlas-world-supplement-manifest.json': world}}
            report_path = directory/'atlas-beacon-generation-report.json'
            with mock.patch.object(package, 'module', side_effect=lambda name, path: producer if name == 'native_atlas_beacon_producer' else guest):
                report_path.write_text(json.dumps(report))
                validated = package.validate_beacons(directory, COMMIT, donor)
                self.assertEqual(validated['generation'], report)
                self.assertEqual(validated['manifest'], manifest)
                self.assertNotEqual(validated['generation'], validated['manifest'])
                for field, wrong in (('cleanup_complete', False), ('owned_roles', 5), ('native_worker_spawning_allowed', True)):
                    value = dict(report); value[field] = wrong; report_path.write_text(json.dumps(value))
                    with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'ownership/cleanup'):
                        package.validate_beacons(directory, COMMIT, donor)
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
        for expected in ('run-id: 37324515114', 'C:/bcn-src', '--target MapServer', '--timeout-seconds 5400',
                'generate_atlas_beacons.py', 'reference-inputs-receipt.json', 'COH_ATLAS_BEACON_REUSE_RUN_ID',
                '35.0.0', 'android-35/android.jar', 'coh-client-interactive.jks', package.APK_NAME):
            self.assertIn(expected, source)
        native_job = source.split('  beacons:\n', 1)[1].split('  qualify:\n', 1)[0]
        self.assertIn('actions/setup-java@v4', native_job)
        self.assertIn("java-version: '17'", native_job)
        for forbidden in ('--target DbServer', 'discover_client_visual_assets.py', 'prepare_client_appearance_assets.py'):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__': unittest.main(verbosity=2)
