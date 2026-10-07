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
import zipfile

import build_client_scene_performance_apk as package
import test_thor_performance_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as prior:
        apk = prior[0]; donor = copy.deepcopy(prior[2])
        donor.update(payloads=copy.deepcopy(prior[3]), runtime_manifest=copy.deepcopy(prior[4]))
    with zipfile.ZipFile(apk) as archive:
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        with zipfile.ZipFile(io.BytesIO(archive.read('assets/runtime/client-runtime.zip'))) as client:
            manifest = json.loads(client.read('client-package.json'))
            contents = {entry.filename: client.read(entry) for entry in client.infolist()}
    accepted = {'files': {'CityOfHeroes.exe': copy.deepcopy(manifest['files']['CityOfHeroes.exe'])},
        'build_input': {'accepted': 'source-chain'}}
    manifest['client_startup_followup'] = {'manifest': accepted,
        'manifest_sha256': package.shared.native_contract.canonical_sha(accepted)}
    contents['client-package.json'] = package.shared.encoded(manifest)
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, 'w') as archive:
        for name, raw in contents.items(): archive.writestr(name, raw)
    replace_member(apk, 'assets/runtime/client-runtime.zip', nested.getvalue())
    donor['payloads']['assets/runtime/client-runtime.zip'] = pin(nested.getvalue())
    donor['_native_client_manifest'] = manifest
    with zipfile.ZipFile(io.BytesIO(nested.getvalue())) as archive:
        donor['_client_members'] = package.startup.startup.client_member_pins(archive)
    donor['immutable_donor_provenance'] = {'native_responsiveness': donor['native_responsiveness'],
        'native_client_startup_followup': accepted}
    donor['runtime_manifest']['client_startup_followup'] = {'native_manifest_sha256': manifest['client_startup_followup']['manifest_sha256']}
    for value in (donor['_client_verification'], donor['runtime_manifest']):
        value['files']['client-runtime.zip'] = donor['payloads']['assets/runtime/client-runtime.zip']
    client_raw = package.shared.encoded(donor['_client_verification'])
    donor['runtime_manifest']['files']['client-manifest.json'] = pin(client_raw)
    for name, raw in (('client-manifest.json', client_raw), ('runtime-manifest.json', package.shared.encoded(donor['runtime_manifest']))):
        replace_member(apk, 'assets/runtime/'+name, raw); donor['payloads']['assets/runtime/'+name] = pin(raw)
    for name in package.HELPERS: (folder/'android/guest'/name).write_bytes(('reviewed-scene-'+name).encode())
    directory = folder/'scene-native'; directory.mkdir()
    raw = b'actual-source-bound-scene-Game'; (directory/'CityOfHeroes.exe').write_bytes(raw)
    record = dict(manifest['files']['CityOfHeroes.exe'], size=len(raw), sha256=pin(raw)['sha256'])
    native = {'format': 1, 'repository_commit': COMMIT, 'files': {'CityOfHeroes.exe': record},
        'base_client_executable': manifest['files']['CityOfHeroes.exe']}
    # Actual native production/source proof is exercised in the separate native
    # and guest-contract suites. This fixture checks every real nested byte.
    with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
            mock.patch.object(package, 'validate_native', return_value=native), \
            mock.patch.object(package.shared.native_contract, 'client_contract'):
        runtime, payloads, preflight = package.extract_and_repair(apk, donor, folder/'scene-files', COMMIT, directory)
        output = folder/'scene.apk'
        with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
            for name in payloads: archive.write(folder/'scene-files'/name, name)
            for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                archive.writestr(name, original.read(name))
            archive.writestr('AndroidManifest.xml', b'version-only-update')
        yield output, apk, donor, payloads, runtime, preflight, directory, native


def qualification():
    q = package.module('scene_test_qualification', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE, 'repository_commit': COMMIT,
        'donor': package.donor_link(), 'checks': {name: True for name in package.CHECKS},
        **{name: False for name in package.FALSE_FLAGS}, 'native_client_recompiled': True,
        'native_client_compiled_in_current_run': True, 'native_client_package_reused': False,
        'actual_native_ancestry_validation': copy.deepcopy(package.ACTUAL_NATIVE_ANCESTRY_CHECKS),
        'test_suites': {name: {'status': 'passed', 'skipped': 0, 'tests_run': 1} for name in q.TEST_MODULES},
        'tests_run': len(q.TEST_MODULES), 'check_suites': copy.deepcopy(q.CHECK_SUITES),
        'source_files': {name: pin(b'source') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures': sorted(package.previous.previous.previous.prior.levelup_postgresql_fixtures())}


class ClientScenePerformancePackageTests(unittest.TestCase):
    def verify(self, values):
        return package.verify_derivative(values[0], values[2], values[3], COMMIT, values[6])

    def test_next_version_from_exact_public_0_13_15_donor(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.16', 31))
        self.assertEqual(package.DONOR_RUN_ID, 37411543214)
        self.assertEqual(package.DONOR_BUILD, {'bytes': 4878263, 'sha256': 'd71a3ee8b83a9bd1d2749e4efa37682dd915d36a1a6c2009e091bfb687974f39'})
        self.assertEqual((len(package.REPLACED_PAYLOADS), len(package.ADDED_PAYLOADS)), (7, 0))

    def test_actual_staged_native_chain_keeps_all_frozen_inputs_and_rejects_changed_sources(self):
        native = package.native_producer
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'source'; expected = native.stage(SimpleNamespace(output=source))
            self.assertEqual(native.validate_source(source)[0], expected)
            for name in ('Game/src/game.c', 'Common/seq/gfxtree.c', 'Game/src/cohClientFrameTiming.h',
                    'libs/UtilitiesLib/src/utils/textparser.c', native.base.RECEIPT):
                target = source/name; raw = target.read_bytes(); target.write_bytes(raw+b'foreign')
                with self.subTest(name=name), self.assertRaises((ValueError, json.JSONDecodeError)):
                    native.validate_source(source)
                target.write_bytes(raw)
            self.assertEqual(native.validate_source(source)[0], expected)

    def test_recomputed_native_ancestry_accepts_proven_pg_encoding_only(self):
        import hashlib
        from test_client_scene_performance_contract import bind_source_digests, foreign_source_variants
        baseline = package.native_producer.base.base.base.baseline
        received = {name: baseline.expected_source_receipt(name, {'progress_build_input':
            __import__('prepare_mapserver_progress_source').expected_progress_receipt()})
            if name == 'character_events' else baseline.expected_source_receipt(name, {}) for name in baseline.INPUTS}
        accepted = copy.deepcopy(received)
        pg = accepted['character_events']['progress_build_input']['game_build_input']['postgresql_build_input']
        for name in pg['overlay_sha256']:
            raw = (package.ROOT/'database/postgresql/overlay'/name).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            pg['overlay_sha256'][name] = hashlib.sha256(raw).hexdigest()
        bind_source_digests(accepted)
        before = copy.deepcopy((received, accepted))
        self.assertTrue(package.validate_native_source_ancestry(received, accepted))
        self.assertTrue(package.validate_native_source_ancestry(accepted, received))
        for name, changed in foreign_source_variants(received):
            with self.subTest(mutation=name), self.assertRaises(ValueError): package.validate_native_source_ancestry(changed, accepted)
        self.assertEqual((received, accepted), before)

    def test_fresh_native_package_verification_reads_actual_cmake_flags_even_with_recomputed_pin(self):
        native = package.native_producer; baseline = native.base.base.base.baseline
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); (directory/'CityOfHeroes.exe').write_bytes(b'new-Game')
            (directory/native.CHECKS).write_text('{"fixture":"checks"}')
            record = dict(native.BASE_GAME, sha256='a'*64)
            manifest = {'format': 1, 'role': native.ROLE, 'repository_commit': COMMIT,
                'source_commit': baseline.contract.SOURCE, 'data_commit': baseline.contract.DATA,
                'configuration': 'OptDebug', 'architecture': 'Win32', 'build_targets': ['Game'],
                'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
                'cache_encoding_changed': False, 'retained_native_dependencies_changed': False,
                'replacement_scope': 'CityOfHeroes.exe_only', 'build_input': {'fixture': 'recipe'},
                'base_client_executable': native.BASE_GAME, 'schema_sources_sha256': {},
                'retained_source_inputs': {key: {} for key in baseline.INPUTS},
                'files': {'CityOfHeroes.exe': record}, 'windows_qualification': {'fixture': 'checks'},
                'run_url': 'https://github.com/Russianranger/coh-android/actions/runs/123'}
            with mock.patch.object(native, 'expected_receipt', return_value={'fixture': 'recipe'}), \
                    mock.patch.object(native, 'file_record', return_value=record), mock.patch.object(native, 'validate_checks'), \
                    mock.patch.object(baseline, 'schema_pins', return_value={}), \
                    mock.patch.object(baseline, 'expected_source_receipt', side_effect=lambda key, received: received):
                good = 'COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n'
                bad = (good.replace('=OFF', '=ON'), good.replace('=Win32', '=x64'),
                    good+'COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n',
                    good.replace('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n', ''),
                    good.replace('CMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n', ''))
                for cache in (good, *bad):
                    (directory/'CMakeCache.txt').write_text(cache)
                    manifest['cmake_cache'] = pin((directory/'CMakeCache.txt').read_bytes())
                    (directory/native.MANIFEST).write_text(json.dumps(manifest))
                    if cache == good: self.assertEqual(native.validate_package(directory, COMMIT), manifest)
                    else:
                        with self.subTest(actual_cache=cache), self.assertRaisesRegex(ValueError, 'Actual CMake cache'):
                            native.validate_package(directory, COMMIT)

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
            for key in ('thor_performance', 'ui_beacon', 'client_startup_followup', 'startup_only_reopen', 'task_gate_required'):
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
        for mutation in ('game', 'dll', 'history', 'missing', 'extra', 'duplicate'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                with zipfile.ZipFile(values[0]) as apk, zipfile.ZipFile(io.BytesIO(apk.read('assets/runtime/client-runtime.zip'))) as client:
                    contents = {entry.filename: client.read(entry) for entry in client.infolist()}
                if mutation == 'game': contents['CityOfHeroes.exe'] = b'foreign'
                elif mutation == 'dll': contents['fixture-0.dll'] = b'foreign'
                elif mutation == 'history':
                    manifest = json.loads(contents['client-package.json']); manifest['client_loading']['manifest_sha256'] = 'f'*64
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
        self.assertIn('coh-thor-performance-packaging-evidence', source); self.assertIn('run-id: 37411543214', source)
        self.assertIn("PYTHONHASHSEED: '73416'", source); self.assertIn("PYTHONHASHSEED: '1615'", source)
        self.assertLess(source.index('Fresh-process SDK source payload'), source.index('Publish only the newly qualified'))
        public = source.split('  public-audit:', 1)[1]
        self.assertIn('contents: read', public); self.assertNotIn('contents: write', public)
        self.assertIn('Download actual public APK checksum and testing notes', public)
        self.assertIn('Existing performance release differs', source); self.assertIn('scene_performance_push', source)
        from classify_storage_cleanup_change import SCENE_PERFORMANCE_SOURCES
        block = source.split('    paths:\n', 1)[1].split('  workflow_dispatch:', 1)[0]
        patterns = [line.split('      - ', 1)[1] for line in block.splitlines() if line.startswith('      - ')]
        for name in SCENE_PERFORMANCE_SOURCES:
            with self.subTest(source=name):
                self.assertTrue(any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns),
                    'Every source that can suppress an old pipeline must trigger its current owner')


if __name__ == '__main__': unittest.main()
