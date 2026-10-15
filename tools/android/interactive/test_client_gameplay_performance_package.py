"""Real nested ZIP/extraction boundary with externally produced Game substituted."""
import contextlib
import copy
import fnmatch
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import urllib.error
import zipfile

import build_client_gameplay_performance_apk as package
import test_client_scene_performance_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as prior:
        apk = prior[0]; donor = copy.deepcopy(prior[2])
        donor.update(payloads=copy.deepcopy(prior[3]), runtime_manifest=copy.deepcopy(prior[4]),
            native_client_scene_performance=copy.deepcopy(prior[7]))
    with zipfile.ZipFile(apk) as archive:
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        with zipfile.ZipFile(io.BytesIO(archive.read('assets/runtime/client-runtime.zip'))) as client:
            manifest = json.loads(client.read('client-package.json'))
            donor['_client_members'] = package.startup.startup.client_member_pins(client)
    donor['_native_client_manifest'] = manifest
    for name in package.HELPERS: (folder/'android/guest'/name).write_bytes(('reviewed-gameplay-'+name).encode())
    directory = folder/'gameplay-native'; directory.mkdir()
    raw = b'actual-source-bound-gameplay-Game'; (directory/'CityOfHeroes.exe').write_bytes(raw)
    record = dict(manifest['files']['CityOfHeroes.exe'], size=len(raw), sha256=pin(raw)['sha256'])
    native = {'format': 1, 'repository_commit': COMMIT, 'files': {'CityOfHeroes.exe': record},
        'base_client_executable': manifest['files']['CityOfHeroes.exe']}
    # Source/native production proof is in the separate native and typed
    # contract suites. Here every actual nested ZIP byte is verified.
    with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
            mock.patch.object(package, 'validate_native', return_value=native), \
            mock.patch.object(package.shared.native_contract, 'client_contract'):
        runtime, payloads, preflight = package.extract_and_repair(apk, donor, folder/'gameplay-files', COMMIT, directory)
        output = folder/'gameplay.apk'
        with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
            for name in payloads: archive.write(folder/'gameplay-files'/name, name)
            for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                archive.writestr(name, original.read(name))
            archive.writestr('AndroidManifest.xml', b'version-only-update')
        yield output, apk, donor, payloads, runtime, preflight, directory, native


def qualification():
    q = package.module('gameplay_test_qualification', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE, 'repository_commit': COMMIT,
        'donor': package.donor_link(), 'checks': {name: True for name in package.CHECKS},
        **{name: False for name in package.FALSE_FLAGS}, 'native_client_recompiled': True,
        'native_client_compiled_in_current_run': True, 'native_client_package_reused': False,
        'actual_native_ancestry_validation': copy.deepcopy(package.ACTUAL_NATIVE_ANCESTRY_CHECKS),
        'requested_gameplay_cap': 30, 'diagnostic_only_texture_repeat_bounding': True,
        'test_suites': {name: {'status': 'passed', 'skipped': 0, 'tests_run': 1} for name in q.TEST_MODULES},
        'tests_run': len(q.TEST_MODULES), 'check_suites': copy.deepcopy(q.CHECK_SUITES),
        'source_files': {name: pin(b'source') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures': sorted(package.retained.levelup_postgresql_fixtures())}


class ClientGameplayPerformancePackageTests(unittest.TestCase):
    def verify(self, values):
        return package.verify_derivative(values[0], values[2], values[3], COMMIT, values[6])

    def test_next_version_from_exact_public_0_13_16_donor(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.17', 32))
        self.assertEqual(package.DONOR_RUN_ID, 37559820885)
        self.assertEqual(package.DONOR_BUILD, {'bytes': 4994538, 'sha256': '1135803a6a5bb68364d2baa3d94e7e4bbd148d0e7840fdc8b8a67e46c456bad6'})
        self.assertEqual((len(package.REPLACED_PAYLOADS), len(package.ADDED_PAYLOADS)), (7, 0))

    def test_frozen_upstream_source_pins_cannot_be_exempted_by_new_source_inventory(self):
        name = 'upstream/ouroboros/Game/src/game.c'
        self.assertIn(name, package.SOURCE_FILES)
        self.assertNotIn(name, package.REVIEWED_DONOR_SOURCE_CHANGES)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); target = folder/name
            target.parent.mkdir(parents=True); target.write_bytes(b'accepted frozen source')
            donor = {'qualification': {'source_files': {name: pin(target.read_bytes())}}}
            with mock.patch.object(package, 'ROOT', folder):
                package.validate_retained_sources(donor)
                target.write_bytes(b'foreign upstream source')
                with self.assertRaises(ValueError): package.validate_retained_sources(donor)

    def test_actual75_outer_members68_retained_and_all20_client_dependencies_conserved(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            self.assertEqual(self.verify(values), values[4]); self.assertEqual(len(values[3]), 75)
            self.assertEqual(values[5], values[2]['server_payload_extraction_preflight'])
            with zipfile.ZipFile(values[0]) as current, zipfile.ZipFile(values[1]) as donor:
                for name in set(values[3])-package.REPLACED_PAYLOADS: self.assertEqual(current.read(name), donor.read(name))
                for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'): self.assertEqual(current.read(name), donor.read(name))
                with zipfile.ZipFile(io.BytesIO(current.read('assets/runtime/client-runtime.zip'))) as client:
                    for name, expected in values[2]['_client_members'].items():
                        if name not in ('CityOfHeroes.exe', 'client-package.json'): self.assertEqual(pin(client.read(name)), expected)
            for key in ('thor_performance', 'ui_beacon', 'client_startup_followup', 'client_scene_performance', 'startup_only_reopen', 'task_gate_required'):
                self.assertEqual(values[4][key], values[2]['runtime_manifest'][key])

    def test_server_visual_beacon_runtime_cache_and_unreviewed_helper_mutations_rejected(self):
        for name in ('game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'server-caches.zip',
                'client-caches.zip', 'atlas-beacons.zip', 'atlas-beacon-manifest.json', 'client-visual-assets.zip',
                'client-visual-manifest.json', 'startup-dbserver.exe', 'client-launcher.exe',
                'local_character_server.py', 'character_server_data_cache.py', 'local_login_server.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'foreign'); values[3][member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_nested_game_dll_history_missing_extra_or_duplicate_members_rejected(self):
        for mutation in ('game', 'dll', 'history', 'scene_history', 'missing', 'extra', 'duplicate'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                with zipfile.ZipFile(values[0]) as apk, zipfile.ZipFile(io.BytesIO(apk.read('assets/runtime/client-runtime.zip'))) as client:
                    contents = {entry.filename: client.read(entry) for entry in client.infolist()}
                if mutation == 'game': contents['CityOfHeroes.exe'] = b'foreign'
                elif mutation == 'dll': contents['fixture-0.dll'] = b'foreign'
                elif mutation == 'history':
                    manifest = json.loads(contents['client-package.json']); manifest['client_loading']['manifest_sha256'] = 'f'*64
                    contents['client-package.json'] = package.shared.encoded(manifest)
                elif mutation == 'scene_history':
                    manifest = json.loads(contents['client-package.json']); manifest['client_scene_performance']['manifest_sha256'] = 'f'*64
                    contents['client-package.json'] = package.shared.encoded(manifest)
                elif mutation == 'missing': contents.pop('fixture-0.dll')
                elif mutation == 'extra': contents['foreign.dll'] = b'foreign'
                rewritten = io.BytesIO()
                with zipfile.ZipFile(rewritten, 'w') as archive:
                    for name, raw in contents.items(): archive.writestr(name, raw)
                    if mutation == 'duplicate': archive.writestr('CityOfHeroes.exe', b'foreign')
                member = 'assets/runtime/client-runtime.zip'; replace_member(values[0], member, rewritten.getvalue()); values[3][member] = pin(rewritten.getvalue())
                with self.assertRaises(ValueError): self.verify(values)

    def test_authored_helpers_and_android_shell_remain_bound(self):
        for name in (*('assets/runtime/'+name for name in package.HELPERS), 'classes.dex', 'resources.arsc'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                replace_member(values[0], name, b'foreign')
                if name in values[3]: values[3][name] = pin(b'foreign')
                with self.assertRaises(ValueError): self.verify(values)

    def test_actual_typed_native_ancestry_output_matches_exact_qualification_contract(self):
        import test_client_gameplay_performance_contract as contract_tests
        fixture = contract_tests.ClientGameplayPerformanceContractTests(
            'test_upgrade_preserves_generated_cache_private_inputs_and_all_previous_wrappers')
        try:
            fixture.setUp()
            donor_package = copy.deepcopy(fixture.donor)
            produced_package = fixture.derivative()
            native = produced_package['client_gameplay_performance']['manifest']
            donor = {'_native_client_manifest': donor_package,
                'immutable_donor_provenance': {'native_responsiveness':
                    donor_package['native_responsiveness']['receipt']}}
            actual = contract_tests.validate_actual_native_ancestry(donor, native)
            self.assertEqual(actual, package.ACTUAL_NATIVE_ANCESTRY_CHECKS)
            self.assertTrue(actual['actual_scene_Game_predecessor_verified'])
            receipt = qualification(); receipt['actual_native_ancestry_validation'] = actual
            receipt['source_files'] = {name: package.builder().file_pin(package.ROOT/name)
                for name in package.SOURCE_FILES}
            package.validate_qualification(receipt, COMMIT)
            changed = copy.deepcopy(receipt)
            changed['actual_native_ancestry_validation'].pop('actual_scene_Game_predecessor_verified')
            with self.assertRaises(ValueError): package.validate_qualification(changed, COMMIT)
        finally:
            fixture.doCleanups()

    def test_complete_source_bound_retained_suites_and_seven_postgresql_fixtures_required(self):
        receipt = qualification()
        with mock.patch.object(package, 'builder'):
            package.validate_qualification(receipt, COMMIT)
            for mutation in ('skip', 'suite', 'source', 'pg', 'native_reused', 'actual_ancestry'):
                changed = copy.deepcopy(receipt)
                if mutation == 'skip': next(iter(changed['test_suites'].values()))['skipped'] = 1
                elif mutation == 'suite': changed['test_suites'].pop(next(iter(changed['test_suites'])))
                elif mutation == 'source': changed['source_files'].pop(next(iter(package.SOURCE_FILES)))
                elif mutation == 'pg': changed['postgresql_levelup_fixtures'] = []
                elif mutation == 'actual_ancestry': changed['actual_native_ancestry_validation']['rejected_foreign_variants'] = []
                else: changed['native_client_package_reused'] = True
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): package.validate_qualification(changed, COMMIT)

    def test_workflow_builds_only_game_then_fresh_process_and_separate_public_audits(self):
        source = (package.ROOT/package.WORKFLOW).read_text()
        self.assertIn('windows-2025-vs2026', source); self.assertIn('--parallel --target Game', source)
        for forbidden in ('--target MapServer', '--target DBServer', 'generate_atlas_beacons.py', 'prepare_client_appearance_assets.py'):
            self.assertNotIn(forbidden, source)
        self.assertIn('coh-client-scene-performance-packaging-evidence', source); self.assertIn('run-id: 37559820885', source)
        self.assertIn("PYTHONHASHSEED: '73417'", source); self.assertIn("PYTHONHASHSEED: '1716'", source)
        self.assertIn('cancel-in-progress: true', source)
        self.assertLess(source.index('Fresh-process SDK source payload'), source.index('Publish only the newly qualified'))
        public = source.split('  public-audit:', 1)[1]
        self.assertIn('contents: read', public); self.assertNotIn('contents: write', public)
        self.assertIn('Download actual public APK checksum and testing notes', public)
        self.assertIn('Existing performance release differs', source); self.assertIn('gameplay_performance_push', source)
        from classify_storage_cleanup_change import GAMEPLAY_PERFORMANCE_SOURCES
        block = source.split('    paths:\n', 1)[1].split('  workflow_dispatch:', 1)[0]
        patterns = [line.split('      - ', 1)[1] for line in block.splitlines() if line.startswith('      - ')]
        for name in GAMEPLAY_PERFORMANCE_SOURCES:
            with self.subTest(source=name):
                self.assertTrue(any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns),
                    'Every source that can suppress an old pipeline must trigger its current owner')

    def test_superseded_head_blocks_release_creation_and_publication(self):
        for scenario in ('current', 'stale_before_creation', 'stale_during_upload'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); assets = tuple(folder/name for name in
                    (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
                for path in assets: path.write_bytes(b'fully-verified-release-fixture')
                report = dict(pin(assets[0].read_bytes()), repository_commit=COMMIT)
                api = mock.Mock(); heads = []

                def request(path, data=None, **kwargs):
                    if path == '/git/ref/heads/'+package.BRANCH:
                        heads.append(path)
                        stale = scenario == 'stale_before_creation' or (scenario == 'stale_during_upload' and len(heads) > 1)
                        return {'ref': 'refs/heads/'+package.BRANCH,
                            'object': {'type': 'commit', 'sha': 'b'*40 if stale else COMMIT}}
                    if path.startswith(('/releases/tags/', '/git/ref/tags/')):
                        raise urllib.error.HTTPError('https://api.github.com', 404, 'Not Found', {}, None)
                    if path == '/releases':
                        return {'id': 1, 'draft': True, 'prerelease': True, 'tag_name': package.RELEASE_TAG}
                    if path.startswith('/releases/1/assets?'):
                        record = pin(data.read_bytes())
                        return {'state': 'uploaded', 'name': data.name, 'size': record['bytes'], 'digest': 'sha256:'+record['sha256']}
                    self.assertEqual(path, '/releases/1')
                    return {'id': 1, 'draft': False, 'prerelease': True, 'tag_name': package.RELEASE_TAG,
                        'html_url': 'https://github.com/'+package.REPOSITORY+'/releases/tag/'+package.RELEASE_TAG}

                api.request.side_effect = request
                if scenario == 'current':
                    self.assertIn(package.RELEASE_TAG, package.publish_release(api, report, assets, 'qualified notes'))
                    self.assertEqual(len(heads), 2)
                else:
                    with self.assertRaisesRegex(ValueError, 'superseded'):
                        package.publish_release(api, report, assets, 'qualified notes')
                    self.assertFalse(any(call.kwargs.get('method') == 'PATCH' for call in api.request.call_args_list))
                    if scenario == 'stale_before_creation':
                        self.assertFalse(any(call.kwargs.get('method') == 'POST' for call in api.request.call_args_list))


if __name__ == '__main__': unittest.main()
