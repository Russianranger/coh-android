"""Unexecuted current-consumer fixtures; no native or device qualification claim.

The donor is the authenticated public .36 APK. Its last unused PE byte is
changed solely to exercise the closed, source-frozen wrapper/admission gates.
Neither this PE nor a synthetic successful connection is ever executed.
"""
import copy
from contextlib import contextmanager
import hashlib
import json
import os
import shutil
from pathlib import Path
import sys
import tempfile
import zipfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(ROOT/'tools/android/interactive'), str(ROOT/'tools')]
import native_startup_metadata_contract as metadata
import native_startup_component_migration as migration
import native_map_startup_contract as startup
import local_character_server as character
import character_zoning as zoning
import server_cache_package as caches
import server_animation_package as animation
import server_fx_catalog as fx
import atlas_beacon_package as beacon
import game_diagnostic as game
import client_startup_diagnostic as client
import test_server_cache_package as cache_fixture
from test_native_startup_metadata_contract import fixture
import test_saved_map_startup as saved_map_fixture


_CONTROLLED_SOURCE_REVIEWS = {}
_CONTROLLED_DERIVATIONS = {}


def synthetic_package(compatibility=None, maps=(1, 5), qualification_material=None):
    _, members, raw, authority = fixture('mapserver')
    authority = copy.deepcopy(authority)
    authority['compatibility'] = copy.deepcopy(compatibility or {})
    qualification = {'artifact_zip': {'bytes': 100, 'sha256': 'a'*64},
        'members': {'controlled.json': {'bytes': 10, 'sha256': 'b'*64}},
        'required_receipt_values': {'controlled.json': {'status': 'unexecuted_unit_fixture'}}}
    if qualification_material is not None: qualification = copy.deepcopy(qualification_material)
    authority['materials']['qualification'] = qualification
    with patch.dict(metadata.COMPONENT_AUTHORITIES, {'mapserver': authority}):
        package = metadata.unique_json(migration.wrap_manifest(members['game-package.json'], 'mapserver', authority))
    review = {'format': 1, 'kind': 'mapserver',
        'component_authority_sha256': metadata.canonical_sha(authority),
        'qualification_artifact_zip': qualification['artifact_zip'],
        'qualification_receipts': {name: {'pin': pin,
            'required_values': qualification['required_receipt_values'][name]} for name, pin in qualification['members'].items()},
        'qualified_maps': list(maps), 'attempt_environment': metadata.ATTEMPT_ENVIRONMENTS['mapserver'],
        'scope': {'old_native_producer_relabelled': False, 'behavioral_collision_validated': False,
            'physical_timing_validated': False}}
    return package, authority, review, raw


def owned_cache_provider_fixture(root, generation='1', *, actual_server_donor=False):
    """Actual owned file/archive reads with 191 controlled, unexecuted BIN proofs."""
    root = Path(root); assets = root/'assets'; assets.mkdir()
    work = root/'client-work'; work.mkdir(); (work/'data').mkdir(); (work/'data/bin').mkdir()
    imported = root/'imported'; imported.mkdir(); data = imported/'data'; data.mkdir()
    complete = f'generation=generation-{generation*32}\ncontract.sha256={"c"*64}\ncount={client.DATA_COUNT}\nbytes={client.DATA_BYTES}\n'
    (imported/'complete.properties').write_text(complete)
    client_payloads = {'data/bin/sequencers.bin': cache_fixture.parse6()}
    client_payloads.update({f'data/bin/fixture_{index:03d}.bin': cache_fixture.parse6(body=index.to_bytes(4, 'little')) for index in range(190)})
    client_manifest = {'format': 1, 'role': 'actual_client_generated_caches',
        'source_commit': client.SOURCE, 'data_commit': client.DATA, 'executable_sha256': client.EXE_SHA,
        'asset_archive_sha256': client.ASSET_ARCHIVE_SHA, 'reference_run_id': 36088012664,
        'prerequisites_manifest_sha256': client.PREREQUISITES_MANIFEST_SHA,
        'generated_noncache_outputs': [], 'normalized_mtime_epoch': client.CACHE_EPOCH,
        'files': {name: {**caches.pin_bytes(raw), 'schema_crc': caches.inspect_parse6(raw)['schema_crc']}
            for name, raw in client_payloads.items()}}
    client_raw = metadata.encoded(client_manifest)
    with zipfile.ZipFile(assets/'client-caches.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in [('client-cache-manifest.json', client_raw), *client_payloads.items()]:
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)); entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, raw)
    prerequisites = Path(os.environ.get('COH_METADATA_TEST_PREREQUISITES_DONOR',
        '/workspace/scratch/5d16603ca7ff/native037-recovery/public-asset-cache-donor/client-prerequisites.zip'))
    if not prerequisites.is_file() or caches.file_pin(prerequisites) != {'bytes': 18757,
            'sha256': 'cc8bd66c482233a8d5ee7f33e51015bb5981f993cad014378b3861550b520e0e'}:
        raise AssertionError('Exact authenticated .36 prerequisite archive required; no skipped substitute')
    shutil.copyfile(prerequisites, assets/'client-prerequisites.zip')
    if actual_server_donor:
        original_client = Path(os.environ.get('COH_METADATA_TEST_CLIENT_CACHE_DONOR',
            '/workspace/scratch/5d16603ca7ff/native037-recovery/public-asset-cache-donor/client-caches.zip'))
        if not original_client.is_file() or caches.file_pin(original_client) != {'bytes': 27071659,
                'sha256': '5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'}:
            raise AssertionError('Exact public client-cache component required; no skipped substitute')
        shutil.copyfile(original_client, assets/'client-caches.zip')
        with zipfile.ZipFile(assets/'client-caches.zip') as archive:
            client_manifest = client.cache_manifest(archive); client_raw = archive.read('client-cache-manifest.json')
            client_payloads = {name: archive.read(name) for name in client_manifest['files'] if name.startswith('data/bin/')}
        if caches.pin_bytes(client_raw) != {'bytes': 20195,
                'sha256': 'e5bc9ff306f90f96b6d34d4d481b30804af078b0e07845dafd71f7324dff6352'} or len(client_payloads) != 98:
            raise AssertionError('Original public client manifest and eligible data/bin census differ')
    if actual_server_donor:
        donor = Path(os.environ.get('COH_METADATA_TEST_SERVER_CACHE_DONOR',
            '/workspace/scratch/5d16603ca7ff/native037-recovery/public-asset-cache-donor/server-caches.zip'))
        if not donor.is_file():
            raise AssertionError('Exact public Assets 1.0.0 server-cache component required; no skipped substitute')
        if caches.file_pin(donor) != {'bytes': 29825263, 'sha256': '7439d4557ae9fd74bb4bb4a324b6a676829387124be0817eb1da3c8adff10b17'}:
            raise AssertionError('Actual public server-cache component bytes differ')
        shutil.copyfile(donor, assets/'server-caches.zip')
        server_manifest = caches.verify_archive(assets/'server-caches.zip')
        if len(server_manifest['files']) != 93:
            raise AssertionError('Exact public server-cache payload census differs')
    else:
        server_manifest = cache_fixture.synthetic_archive(assets/'server-caches.zip')
    with zipfile.ZipFile(assets/'server-caches.zip') as archive:
        server_raw = archive.read(caches.MANIFEST)
    if actual_server_donor and caches.pin_bytes(server_raw) != {'bytes': 39041,
            'sha256': '4e1a4c9c148509ef34245768f64ca2be4bb83659db845c6ef94ed594666b3fff'}:
        raise AssertionError('Exact original public server-cache manifest differs')
    archives = {'client-caches.zip': {'archive': caches.file_pin(assets/'client-caches.zip'), 'manifest': caches.pin_bytes(client_raw)},
        'server-caches.zip': {'archive': caches.file_pin(assets/'server-caches.zip'), 'manifest': caches.pin_bytes(server_raw)}}
    (assets/'asset-pack-manifest.json').write_bytes(metadata.encoded({'format': 1, 'id': 'controlled-unexecuted-assets',
        'version': '1.0.0', 'files': {'runtime/'+name: row['archive'] for name, row in archives.items()}}))
    imported_identity = client.import_identity(data)
    receipt = {'format': 1, 'source_data': str(data), 'import': imported_identity,
        'cache_archive_sha256': archives['client-caches.zip']['archive']['sha256'],
        'prerequisites_archive_sha256': 'cc8bd66c482233a8d5ee7f33e51015bb5981f993cad014378b3861550b520e0e',
        'prerequisites_manifest_sha256': client.PREREQUISITES_MANIFEST_SHA,
        'normalized_mtime_epoch': client.CACHE_EPOCH, 'content_identity_sha256': 'e'*64}
    (work/'client-work.json').write_bytes(metadata.encoded(receipt))
    projection = {'policy': 'exact_source_bound_native_excluded_texture_directory_v2', 'excluded_top_level_directories': ['texture_library'],
        'native_consumer_sha256': fixture('mapserver')[3]['native_record']['sha256'],
        'native_source_path': 'MapServer/src/svr/svr_init.c', 'native_source_sha256': '398081161ebe9e9253b326e8a5f94f502a7bc0a9974a442f1ce83a46ee0f9ae3',
        'retained_texture_exclusion_source_sha256': character.SERVER_TEXTURE_EXCLUSION_SOURCE,
        'client_inputs_modified': False}
    partial = synthetic_package({'server_texture_projection': projection})
    with synthetic_review(partial): portable = caches.portable_metadata_provider(receipt, partial[0], None)
    eligible = {}; qualified = {}; outputs = {}; schemas = {}
    # The recovered public donor has 93 exact server outputs. Remaining
    # cache bodies are actual public bytes; new native qualification rows are
    # controlled and explicitly unexecuted.
    selected_clients = list(client_payloads)[:191-len(server_manifest['files'])]
    for name in selected_clients:
        raw = client_payloads[name]; (work/name).write_bytes(raw)
        eligible[name] = {'archive': 'client-caches.zip', 'member': name}
        schema = metadata.canonical_sha({'kind': 'Parse6', 'original_manifest_record': client_manifest['files'][name]})
        outputs[name] = caches.pin_bytes(raw); schemas[name] = {'kind': 'Parse6', 'schema_identity_sha256': schema}
        qualified[name] = {'schema_identity_sha256': schema, 'output_sha256': outputs[name]['sha256'],
            'identifier_inputs_sha256': 'f'*64, 'loader_decisions_sha256': '1'*64}
    for name, record in server_manifest['files'].items():
        eligible[name] = {'archive': 'server-caches.zip', 'member': name}
        schema = metadata.canonical_sha({'kind': record['kind'], 'original_manifest_record': record})
        outputs[name] = {key: record[key] for key in ('bytes', 'sha256')}
        schemas[name] = {'kind': record['kind'], 'schema_identity_sha256': schema}
        qualified[name] = {'schema_identity_sha256': schema, 'output_sha256': record['sha256'],
            'identifier_inputs_sha256': 'f'*64, 'loader_decisions_sha256': '1'*64}
    historical = {'client-caches.zip': {key: client_manifest[key] for key in ('format', 'role', 'source_commit', 'data_commit',
        'executable_sha256', 'asset_archive_sha256', 'reference_run_id', 'prerequisites_manifest_sha256', 'normalized_mtime_epoch')},
        'server-caches.zip': {key: server_manifest[key] for key in ('identity', 'native_generation', 'native_consumption')}}
    proof = {'format': 1, 'role': 'native_metadata_cache_consumer_parity',
        'previous_shipping_consumer_sha256': partial[0][metadata.WRAPPER]['receipt']['previous_native_record']['sha256'],
        'current_consumer_sha256': partial[0]['files']['MapServer.exe']['sha256'], 'native_ID_tables_observed': False,
        'qualified_per_bin': qualified, 'observed_native_bin_paths': sorted(qualified)}
    # These named controls are deliberately different from the shipping .36
    # predecessor. They are controlled/unexecuted, never relabelled as native runs.
    controls = [{'bytes': 7475200, 'sha256': '8'*64}, {'bytes': 7480320, 'sha256': '9'*64}]
    # Only the real committed review has source authority in production.
    # This independently patched test document retains its exact limited scope.
    source_document = json.loads((ROOT/'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json').read_bytes())
    for key, row in zip(('unobserved_control', 'observed_Map'), controls):
        source_document['observed_control'][key]['sha256'] = row['sha256']
        source_document['observed_control'][key]['size'] = row['bytes']
    source_document['metadata_candidate']['native'] = copy.deepcopy(partial[0]['files']['MapServer.exe'])
    source_raw = metadata.encoded(source_document)
    source_descriptor = {'repository': 'Russianranger/coh-android', 'commit': '1'*40,
        'path': 'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json',
        'git_blob': hashlib.sha1(b'blob '+str(len(source_raw)).encode()+b'\0'+source_raw).hexdigest(),
        'content': caches.pin_bytes(source_raw), 'scope': copy.deepcopy(startup.SOURCE_ONLY_REVIEW_SCOPE)}
    _CONTROLLED_SOURCE_REVIEWS[metadata.canonical_sha(source_descriptor)] = {
        'descriptor': source_descriptor, 'document': source_document}
    proof.update(actual_tested_control_consumers=controls,
        actual_tested_candidate=metadata.native_record_pin(partial[0]['files']['MapServer.exe']),
        source_compatibility_review=source_descriptor)
    # Separate controlled derivation source/raw-input authority. These report
    # pins are unexecuted fixtures; original donor pins below are actual bytes.
    derivation = {'derivation_source': {'repository_commit': '2'*40,
            'path': 'tools/android/interactive/controlled_unexecuted_normalizer.py',
            'git_blob': '3'*40, 'pin': {'bytes': 32, 'sha256': '4'*64}},
        'raw_inputs': {
            'preload': {'repository_commit': '5'*40, 'run_id': 1, 'artifact_id': 2,
                'artifact_zip': {'bytes': 100, 'sha256': '6'*64},
                'member': 'controlled-unexecuted-preload.json', 'member_pin': {'bytes': 32, 'sha256': '7'*64}},
            'native_world': {'repository_commit': '5'*40, 'run_id': 3, 'artifact_id': 4,
                'artifact_zip': {'bytes': 100, 'sha256': '8'*64},
                'member': 'controlled-unexecuted-world.json', 'member_pin': {'bytes': 32, 'sha256': '9'*64}},
            'client_cache_manifest': {'component_zip': archives['client-caches.zip']['archive'],
                'member': 'client-cache-manifest.json', 'member_pin': archives['client-caches.zip']['manifest'],
                'origin': 'exact_public_Assets_1_0_0_component'},
            'server_cache_manifest': {'component_zip': archives['server-caches.zip']['archive'],
                'member': 'server-cache-manifest.json', 'member_pin': archives['server-caches.zip']['manifest'],
                'origin': 'exact_public_Assets_1_0_0_component'}},
        'scope': copy.deepcopy(startup.RUNTIME_CACHE_DERIVATION_SCOPE)}
    proof['derivation'] = startup.runtime_cache_derivation_statement(derivation)
    proof_name = 'controlled.json'; proof_raw = metadata.encoded(proof); (assets/proof_name).write_bytes(proof_raw)
    derivation['output'] = {'filename': proof_name, 'pin': caches.pin_bytes(proof_raw)}
    _CONTROLLED_DERIVATIONS[metadata.canonical_sha(derivation)] = copy.deepcopy(derivation)
    runtime_recipe = {'policy': 'authenticated_immutable_provider_and_original_cache_v1', 'portable_provider': portable,
        'archives': archives, 'eligible_bins': eligible, 'qualified_per_bin': qualified,
        'derived_native_proof': derivation, 'source_compatibility_review': source_descriptor}
    bin_recipe = {'format': 1, 'role': 'exact_original_bin_source_and_schema_recipe', 'portable_provider': portable,
        'archives': archives, 'eligible_origins': eligible, 'output_pins': outputs, 'schemas': schemas}
    cache = {'policy': 'exact_provider_recipe_and_native_consumer_parity',
        'previous_consumer_sha256': proof['previous_shipping_consumer_sha256'], 'current_consumer_sha256': proof['current_consumer_sha256'],
        'provider_identity_sha256': metadata.canonical_sha(portable), 'bin_recipe_identity_sha256': metadata.canonical_sha(bin_recipe),
        'original_proof_sha256': metadata.canonical_sha(historical), 'qualified_per_bin': qualified, 'eligible_bin_paths': sorted(qualified)}
    result = synthetic_package({'server_texture_projection': projection, 'runtime_cache_context': runtime_recipe,
        'cache': cache})
    executable = root/'MapServer.exe'; executable.write_bytes(result[3])
    return {'data': result, 'executable': executable, 'assets': assets, 'worktree': work, 'game_data': data, 'receipt': receipt}



@contextmanager
def synthetic_review(package_data):
    _, authority, review, _ = package_data
    descriptor = authority.get('compatibility', {}).get('runtime_cache_context', {}).get('source_compatibility_review')
    source_review = _CONTROLLED_SOURCE_REVIEWS.get(metadata.canonical_sha(descriptor)) if descriptor is not None else None
    derivation = authority.get('compatibility', {}).get('runtime_cache_context', {}).get('derived_native_proof')
    frozen_derivation = _CONTROLLED_DERIVATIONS.get(metadata.canonical_sha(derivation)) if derivation is not None else None
    with patch.object(metadata, 'ACTIVATION_IMPLEMENTED', True), \
            patch.dict(metadata.COMPONENT_AUTHORITIES, {'mapserver': authority}), \
            patch.dict(metadata.REVIEWED_EXECUTION_AUTHORITIES, {'mapserver': review}), \
            patch.object(startup, 'SOURCE_ONLY_COMPATIBILITY_REVIEW', source_review), \
            patch.object(startup, 'RUNTIME_CACHE_PROOF_DERIVATION', frozen_derivation):
        yield


class NativeMetadataMapActivationTests(unittest.TestCase):
    def path(self, raw):
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-map-metadata-unit-')))
        path = root/'MapServer.exe'; path.write_bytes(raw)
        return path

    def test_production_review_and_activation_stay_absent(self):
        self.assertFalse(metadata.ACTIVATION_IMPLEMENTED)
        self.assertIsNone(metadata.COMPONENT_AUTHORITIES['mapserver'])
        self.assertIsNone(metadata.REVIEWED_EXECUTION_AUTHORITIES['mapserver'])
        self.assertIsNone(startup.SOURCE_ONLY_COMPATIBILITY_REVIEW)
        self.assertIsNone(startup.RUNTIME_CACHE_PROOF_DERIVATION)
        package, _, _, raw = synthetic_package()
        with self.assertRaisesRegex(ValueError, 'disabled'):
            startup.verify_current_map(self.path(raw), package)

    def test_actual_consumer_and_historical_startup_producer_remain_distinct(self):
        data = synthetic_package(); package, _, _, raw = data
        original = metadata.unique_json(fixture('mapserver')[1]['game-package.json'])
        before = metadata.encoded(package)
        with synthetic_review(data):
            self.assertEqual(startup.embedded_receipt(package), startup.embedded_receipt(original))
            proof = startup.verify_current_map(self.path(raw), package)
            self.assertEqual(proof['actual_mapserver_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertNotEqual(proof['actual_mapserver_sha256'], proof['historical_startup_producer']['mapserver_sha256'])
            self.assertTrue(proof['parser_or_definition_sources_changed'])
            self.assertEqual(proof['current_execution']['native_producer'], data[1]['materials']['producer'])
            self.assertFalse(proof['cache_donor_identity_preserved'])
            self.assertFalse(proof['behavioral_collision_validated'])
            self.assertFalse(proof['physical_loading_gain_validated'])
        self.assertEqual(metadata.encoded(package), before)

    def test_loopback_listener_and_progress_use_restored_receipt_with_current_attribution(self):
        data = synthetic_package(); package = data[0]
        original = metadata.unique_json(fixture('mapserver')[1]['game-package.json'])
        with synthetic_review(data):
            self.assertEqual(game.game_loopback_contract(package), game.game_loopback_contract(original))
            self.assertEqual(game.game_listener_contract(package), game.game_listener_contract(original))
            current = game.mapserver_progress_contract(package)
            historical = game.mapserver_progress_contract(original)
            self.assertEqual(current['contract'], historical['contract'])
            self.assertEqual(current['producer'], historical['producer'])
            self.assertEqual(current['current_consumer']['current_consumer_sha256'], package['files']['MapServer.exe']['sha256'])
            self.assertNotEqual(current['producer']['mapserver_sha256'], current['current_consumer']['current_consumer_sha256'])
            self.assertEqual(current['current_consumer']['native_producer'], data[1]['materials']['producer'])

    def test_changed_native_bytes_and_changed_old_receipt_fail_without_mutating_package(self):
        data = synthetic_package(); package = data[0]
        with synthetic_review(data):
            with self.assertRaisesRegex(ValueError, 'Actual native consumer bytes differ'):
                startup.verify_current_map(self.path(b'not the qualified current executable'), package)
            changed = copy.deepcopy(package)
            changed['native_map_startup']['receipt']['physical_timing_validated'] = True
            with self.assertRaises(ValueError): startup.embedded_receipt(changed)

    def test_missing_actual_cache_context_keeps_distinct_full_validation_generation(self):
        data = synthetic_package(); package, _, _, raw = data
        path = self.path(raw)
        owner = object.__new__(character.LocalCharacterServer)
        owner.map_package = package; owner.map_package_dir = path.parent; owner.creation_report = {}
        with synthetic_review(data):
            self.assertEqual(owner.data_cache_native_package(), package)
            self.assertFalse(owner.creation_report['server_data_cache_native_consumer']['original_generation_reused'])
            with self.assertRaisesRegex(ValueError, 'Actual metadata provider'):
                caches.verify_mapserver_compatibility(path, package)

    def test_cache_reuse_requires_provider_recipe_original_proof_and_every_bin_fact(self):
        old = metadata.unique_json(fixture('mapserver')[1]['game-package.json'])
        current_sha = fixture('mapserver')[3]['native_record']['sha256']
        context = {'provider_identity_sha256': '1'*64, 'bin_recipe_identity_sha256': '2'*64,
            'original_proof_sha256': '3'*64, 'qualified_per_bin': {'bin/sequencers.bin': {
                'schema_identity_sha256': '4'*64, 'output_sha256': '5'*64,
                'identifier_inputs_sha256': '6'*64, 'loader_decisions_sha256': '7'*64}}}
        bridge = {'policy': 'exact_provider_recipe_and_native_consumer_parity',
            'previous_consumer_sha256': old['files']['MapServer.exe']['sha256'],
            'current_consumer_sha256': current_sha, 'eligible_bin_paths': sorted(context['qualified_per_bin']), **context}
        data = synthetic_package({'cache': bridge}); path = self.path(data[3])
        with synthetic_review(data):
            result = caches.verify_mapserver_compatibility(path, data[0], metadata_cache_context=context)
            self.assertTrue(result['cache_donor_identity_preserved'])
            self.assertTrue(result['parser_or_definition_sources_changed'])
            for key in context:
                changed = copy.deepcopy(context)
                if key == 'qualified_per_bin': changed[key]['bin/sequencers.bin']['identifier_inputs_sha256'] = '0'*64
                else: changed[key] = '0'*64
                with self.subTest(key=key), self.assertRaises(ValueError):
                    caches.verify_mapserver_compatibility(path, data[0], metadata_cache_context=changed)

    def test_animation_pack_requires_independent_exact_original_pack_and_certificate(self):
        old = metadata.unique_json(fixture('mapserver')[1]['game-package.json'])
        certificate = startup.embedded_receipt(old)['build_input']['animation_certificate']
        document = {'identity': animation.identity(), 'pigg': certificate['original_animation_pack']}
        bridge = {'policy': 'exact_original_animation_pack_and_certificate',
            'current_consumer_sha256': fixture('mapserver')[3]['native_record']['sha256'],
            'original_animation_identity': animation.identity(), 'original_animation_pack': document['pigg'],
            'certificate_sha256': startup.compact_sha(certificate)}
        data = synthetic_package({'animation': bridge}); path = self.path(data[3])
        with synthetic_review(data):
            proof = animation.verify_runtime(path.parent, document, mapserver_package=data[0])
            self.assertTrue(proof['historical_animation_certificate_preserved'])
            self.assertFalse(proof['physical_loading_gain_validated'])
            changed = copy.deepcopy(document); changed['pigg']['sha256'] = '0'*64
            with self.assertRaises(ValueError): animation.verify_runtime(path.parent, changed, mapserver_package=data[0])

    def test_collision_sdk_native_closure_graph_and_selected_world_are_independently_bound(self):
        old = metadata.unique_json(fixture('mapserver')[1]['game-package.json'])
        bridge = {'policy': 'exact_retained_collision_sdk_geometry_and_graph',
            'current_consumer_sha256': fixture('mapserver')[3]['native_record']['sha256'],
            'retained_collision_sources': beacon.RETAINED_COLLISION_SOURCES,
            'retained_native_files_sha256': metadata.canonical_sha({name: row for name, row in old['files'].items() if name != 'MapServer.exe'}),
            'graph_manifests': {'1': beacon.MANIFEST_SHA256, '5': '8'*64}}
        data = synthetic_package({'collision': bridge}); path = self.path(data[3])
        with synthetic_review(data):
            for map_id, digest in ((1, beacon.MANIFEST_SHA256), (5, '8'*64)):
                proof = startup.verify_metadata_collision_graph(path, data[0], map_id=map_id,
                    manifest_sha256=digest, retained_collision_sources=beacon.RETAINED_COLLISION_SOURCES)
                self.assertEqual(proof['map_id'], map_id)
                self.assertFalse(proof['behavioral_collision_validated'])
            for map_id, digest in ((101, beacon.MANIFEST_SHA256), (5, '0'*64)):
                with self.subTest(map_id=map_id), self.assertRaises(ValueError):
                    startup.verify_metadata_collision_graph(path, data[0], map_id=map_id,
                        manifest_sha256=digest, retained_collision_sources=beacon.RETAINED_COLLISION_SOURCES)

    def test_texture_exclusion_requires_explicit_current_consumer_source_proof(self):
        data = synthetic_package({'server_texture_projection': {
            'policy': 'exact_source_bound_native_excluded_texture_directory_v2',
            'excluded_top_level_directories': ['texture_library'],
            'native_consumer_sha256': fixture('mapserver')[3]['native_record']['sha256'],
            'native_source_path': 'MapServer/src/svr/svr_init.c',
            'native_source_sha256': '398081161ebe9e9253b326e8a5f94f502a7bc0a9974a442f1ce83a46ee0f9ae3',
        'retained_texture_exclusion_source_sha256': character.SERVER_TEXTURE_EXCLUSION_SOURCE,
            'client_inputs_modified': False}})
        with synthetic_review(data):
            result = character.server_input_projection(data[0])
            self.assertTrue(result['native_bytes_changed'])
            self.assertFalse(result['client_inputs_modified'])

    def test_zoning_launch_is_single_selected_world_owned_path_and_attempt_environment(self):
        data = synthetic_package()
        for map_id in (5, 1, 101):
            harness = saved_map_fixture.SavedMapStartupTests(methodName='runTest'); self.addCleanup(harness.doCleanups)
            value = harness.instance(map_id); value.map_package = data[0]
            _, kings = harness.fake_launch(value)
            (kings/'MapServer.exe').write_bytes(data[3]); (value.runtime/'MapServer.exe').write_bytes(data[3])
            value.prepare_atlas_runtime = Mock(return_value=value.runtime)
            value.owner.wine_env[metadata.ATTEMPT_ENVIRONMENTS['mapserver']] = 'foreign-inherited'
            inherited = value.owner.wine_env.copy()
            with synthetic_review(data), patch.object(character.game, 'check_game_port'):
                if map_id == 101:
                    with self.assertRaisesRegex(ValueError, 'lacks fresh native metadata world qualification'):
                        value._spawn_map(map_id)
                    value.ctx.start.assert_not_called()
                else:
                    value._spawn_map(map_id)
                    value.ctx.start.assert_called_once()
                    _, argv = value.ctx.start.call_args.args
                    env = value.ctx.start.call_args.kwargs['env']
                    self.assertEqual(argv[argv.index('-map_id')+1], str(map_id))
                    self.assertEqual(argv[argv.index('-udp')+1], str(zoning.MAPS[map_id]['port']))
                    self.assertEqual(env[metadata.ATTEMPT_ENVIRONMENTS['mapserver']], '1')
                    self.assertEqual(set(value.maps), {map_id})
            self.assertEqual(value.owner.wine_env, inherited)

    def test_dbquery_and_retained_attempts_remove_inherited_switch_without_changing_shared_env(self):
        name = metadata.ATTEMPT_ENVIRONMENTS['mapserver']
        owner = object.__new__(game.GameDiagnostic); owner.wine_env = {name: '1'}
        environment = owner.game_environment('MapServer.exe')
        self.assertNotIn(name, environment); self.assertEqual(owner.wine_env, {name: '1'})
        self.assertIsNone(metadata.apply_attempt_environment({}, 'mapserver', Path('/unused'), environment, map_id=101))
        harness = saved_map_fixture.SavedMapStartupTests(methodName='runTest'); self.addCleanup(harness.doCleanups)
        value = harness.instance(5); value.owner.wine_env = {name: '1'}
        value._query_start(['-getstatus', '5', '1'], 'unit-only')
        self.assertNotIn(name, value.ctx.start.call_args.kwargs['env'])
        self.assertEqual(value.owner.wine_env, {name: '1'})

    def test_fx_projection_requires_fresh_current_consumer_ids_and_preserves_old_manifest(self):
        # Controlled original-projection metadata only; no FX decode/native pass.
        manifest = {'projected': fx.PROJECTED, 'native_qualification': {'scope': 'unexecuted_original_fixture'}}
        bridge = {'policy': 'exact_original_server_fx_projection_and_native_ids',
            'current_consumer_sha256': fixture('mapserver')[3]['native_record']['sha256'],
            'projected': fx.PROJECTED, 'historical_native_qualification_sha256': metadata.canonical_sha(manifest['native_qualification']),
            'all_native_ids_equal': True, 'all_records_source_compatible': True}
        data = synthetic_package({'fx': bridge}); path = self.path(data[3]); before = copy.deepcopy(manifest)
        with synthetic_review(data):
            proof = fx.verify_consumer(path.parent, data[0], projection_manifest=manifest)
            self.assertTrue(proof['historical_fx_receipt_preserved'])
            self.assertFalse(proof['native_fx_loader_source_unchanged'])
            with self.assertRaises(ValueError): fx.verify_consumer(path.parent, data[0])
        self.assertEqual(manifest, before)

    def provider_fixture(self, generation='1', *, actual_server_donor=False):
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-owned-cache-unit-')))
        return owned_cache_provider_fixture(root, generation, actual_server_donor=actual_server_donor)

    def construct_provider(self, owned):
        return caches.construct_native_metadata_context(owned['data'][0], owned['executable'],
            assets=owned['assets'], worktree=owned['worktree'], game_data=owned['game_data'], receipt=owned['receipt'])

    def test_live_common_path_constructs_191_exact_bins_and_portable_content_recipe(self):
        first = self.provider_fixture('1', actual_server_donor=True)
        second = self.provider_fixture('2', actual_server_donor=True)
        with synthetic_review(first['data']): one = self.construct_provider(first)
        with synthetic_review(second['data']): two = self.construct_provider(second)
        self.assertEqual(one['context'], two['context'])
        self.assertEqual(one['evidence']['authenticated_original_bin_count'], 191)
        self.assertNotEqual(one['evidence']['local_owner_fingerprints'], two['evidence']['local_owner_fingerprints'])
        self.assertFalse(one['evidence']['physical_timing_validated'])
        self.assertFalse(one['evidence']['behavioral_collision_validated'])
        self.assertFalse(one['evidence']['native_ID_tables_observed'])
        self.assertEqual(one['evidence']['original_bin_body_bytes_read'], 0)
        self.assertEqual(one['evidence']['current_private_bin_body_bytes_read'], 0)
        owner = object.__new__(character.LocalCharacterServer)
        owner.map_package = first['data'][0]; owner.map_package_dir = first['executable'].parent
        owner.owner = SimpleNamespace(work=first['worktree'], args=SimpleNamespace(assets=first['assets'], game_data=first['game_data']))
        owner.ctx = SimpleNamespace(check=Mock()); owner.creation_report = {}
        with synthetic_review(first['data']):
            owner.prepare_native_metadata_cache_context(first['receipt'])
            self.assertEqual(owner.native_metadata_cache_context, one['context'])
            self.assertTrue(owner.creation_report['native_metadata_cache_context']['portable_identity_excludes_path_generation_owner'])
            self.assertNotEqual(owner.data_cache_native_package(), owner.map_package)
            generation = owner.creation_report['server_data_cache_native_consumer']
            self.assertEqual(generation['authenticated_original_donor_bins'], 191)
            self.assertFalse(generation['all_private_or_device_generated_bins_current_native_ids_qualified'])
            self.assertFalse(generation['geobin_or_collision_bodies_current_native_ids_qualified'])
            self.assertTrue(generation['ordinary_native_freshness_loader_retained'])
            current_projection = character.server_input_projection(owner.map_package)
            historical_projection = owner.cache_generation_projection(current_projection)
            self.assertEqual(historical_projection['native_consumer_sha256'], character.SERVER_TEXTURE_EXCLUSION_MAP)
            self.assertEqual(current_projection['native_consumer_sha256'], owner.map_package['files']['MapServer.exe']['sha256'])
            self.assertFalse(historical_projection['native_bytes_changed'])
            owner.native_metadata_cache_context = None
            self.assertEqual(owner.cache_generation_projection(current_projection), current_projection)

    def test_changed_existing_private_bin_is_unobserved_and_preserved_for_native_freshness(self):
        owned = self.provider_fixture(); leaf = owned['worktree']/'data/bin/sequencers.bin'
        changed = cache_fixture.parse6(body=b'BAD!'); leaf.write_bytes(changed)
        with synthetic_review(owned['data']): result = self.construct_provider(owned)
        self.assertEqual(result['evidence']['current_private_bin_body_bytes_read'], 0)
        self.assertFalse(result['evidence']['current_private_or_device_generated_bin_body_equality_claimed'])
        self.assertEqual(leaf.read_bytes(), changed)

    def test_missing_archive_fresh_proof_or_changed_import_cannot_construct_bridge(self):
        for name in ('server-caches.zip', 'controlled.json', 'import'):
            owned = self.provider_fixture()
            if name == 'import':
                path = owned['game_data'].parent/'complete.properties'; path.write_text(path.read_text().replace('c'*64, 'b'*64))
            else: (owned['assets']/name).unlink()
            before = (owned['worktree']/'data/bin/sequencers.bin').read_bytes()
            with self.subTest(name=name), synthetic_review(owned['data']), self.assertRaises((ValueError, OSError)):
                self.construct_provider(owned)
            self.assertEqual((owned['worktree']/'data/bin/sequencers.bin').read_bytes(), before)

    def test_current_path_missing_recipe_reports_bounded_fallback_before_checkout(self):
        data = synthetic_package(); path = self.path(data[3])
        owner = object.__new__(character.LocalCharacterServer)
        owner.map_package = data[0]; owner.map_package_dir = path.parent; owner.creation_report = {}
        owner.owner = SimpleNamespace(work=path.parent, args=SimpleNamespace(assets=path.parent, game_data=path.parent))
        owner.ctx = SimpleNamespace(check=Mock())
        with synthetic_review(data): owner.prepare_native_metadata_cache_context({})
        self.assertIsNone(owner.native_metadata_cache_context)
        self.assertFalse(owner.creation_report['native_metadata_cache_context']['original_cache_generation_reused'])
        self.assertIn('recipe is not frozen', owner.creation_report['native_metadata_cache_context']['reason'])

    def test_game_and_zoning_queries_scrub_both_attempt_switches_in_copies(self):
        both = dict.fromkeys(metadata.ATTEMPT_ENVIRONMENTS.values(), '1')
        owner = object.__new__(game.GameDiagnostic); owner.wine_env = both.copy()
        self.assertFalse(set(both).intersection(owner.game_environment('MapServer.exe')))
        self.assertEqual(owner.wine_env, both)
        harness = saved_map_fixture.SavedMapStartupTests(methodName='runTest'); self.addCleanup(harness.doCleanups)
        value = harness.instance(5); value.owner.wine_env = both.copy()
        value._query_start(['-getstatus', '5', '1'], 'controlled-query')
        self.assertFalse(set(both).intersection(value.ctx.start.call_args.kwargs['env']))
        self.assertEqual(value.owner.wine_env, both)

    def test_context_reads_only_original_manifests_and_reuses_same_operation_archive_hash(self):
        owned = self.provider_fixture(actual_server_donor=True)
        original_read = zipfile.ZipFile.read
        def bounded_read(archive, name, *args, **kwargs):
            path = name.filename if isinstance(name, zipfile.ZipInfo) else name
            if path.lower().endswith('.bin'):
                raise AssertionError('Context must not decompress original BIN bodies')
            return original_read(archive, name, *args, **kwargs)
        with synthetic_review(owned['data']), patch.object(zipfile.ZipFile, 'read', bounded_read), \
                patch.object(caches, 'verify_archive', side_effect=AssertionError('No duplicate full server cache verifier')):
            cold = self.construct_provider(owned); warm = self.construct_provider(owned)
        self.assertEqual(cold['context'], warm['context'])
        self.assertNotIn(cold['evidence']['previous_shipping_consumer_sha256'],
            [row['sha256'] for row in cold['evidence']['actual_tested_control_consumers']])
        self.assertFalse(cold['evidence']['committed_source_compatibility_review']['scope']['runtime_activation_allowed'])
        self.assertEqual(cold['evidence']['original_bin_body_bytes_read'], 0)
        self.assertEqual(warm['evidence']['archive_payload_bytes_hashed'], 0)
        self.assertTrue(all(row['same_operation_full_hash_reused'] for row in warm['evidence']['archive_observations']))
        self.assertEqual(cold['evidence']['eligible_original_bin_bytes_authenticated_by_exact_archive_and_manifest'], 789405231)
        self.assertEqual(cold['evidence']['original_manifest_unique_bytes'], 59236)
        self.assertEqual(cold['evidence']['original_manifest_bytes_read_including_repeated_validation'], 79431)
        self.assertEqual([row for row in cold['evidence']['archive_observations'] if row['archive'] == 'client-caches.zip'][0]
            ['member_reads']['client-cache-manifest.json'], {'reads': 2, 'bytes': 40390})
        self.assertEqual(cold['evidence']['decompressed_original_archive_member_bytes_read'],
            warm['evidence']['decompressed_original_archive_member_bytes_read'])

    def test_mutated_archive_cannot_reuse_the_operation_witness_or_change_player_caches(self):
        owned = self.provider_fixture(); before = (owned['worktree']/'data/bin/sequencers.bin').read_bytes()
        with synthetic_review(owned['data']): self.construct_provider(owned)
        path = owned['assets']/'server-caches.zip'; raw = path.read_bytes(); path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with synthetic_review(owned['data']), self.assertRaisesRegex(ValueError, 'archive SHA differs'):
            self.construct_provider(owned)
        self.assertEqual((owned['worktree']/'data/bin/sequencers.bin').read_bytes(), before)

    def test_shipping_predecessor_cannot_replace_actual_control_without_independent_audit(self):
        owned = self.provider_fixture()
        package, authority, review, raw = owned['data']
        proof_path = owned['assets']/'controlled.json'
        proof = metadata.unique_json(proof_path.read_bytes())
        # Even a newly frozen normalized proof cannot change the independent
        # source audit's actual controls to make shipping lineage look tested.
        proof['actual_tested_control_consumers'] = [{
            'bytes': 7475200, 'sha256': proof['previous_shipping_consumer_sha256']}]
        forged = metadata.encoded(proof); proof_path.write_bytes(forged)
        authority = copy.deepcopy(authority)
        derivation = authority['compatibility']['runtime_cache_context']['derived_native_proof']
        derivation['output']['pin'] = caches.pin_bytes(forged)
        _CONTROLLED_DERIVATIONS[metadata.canonical_sha(derivation)] = copy.deepcopy(derivation)
        with patch.dict(metadata.COMPONENT_AUTHORITIES, {'mapserver': authority}):
            manifest = migration.wrap_manifest(fixture('mapserver')[1]['game-package.json'], 'mapserver', authority)
        review = copy.deepcopy(review)
        review['component_authority_sha256'] = metadata.canonical_sha(authority)
        owned['data'] = (metadata.unique_json(manifest), authority, review, raw)
        with synthetic_review(owned['data']), self.assertRaisesRegex(ValueError, 'actual tested controls or candidate'):
            self.construct_provider(owned)

    def actual_preload_107_controlled_adapter_fixture(self):
        """Real preload subset/PE bytes; authority and missing world gate stay controlled."""
        owned = self.provider_fixture(actual_server_donor=True)
        research_path = Path('/workspace/scratch/5d16603ca7ff/publication-037-evidence/actual-preload-107-cache-subset-research.json')
        research_raw = research_path.read_bytes()
        self.assertEqual(caches.pin_bytes(research_raw), {'bytes': 70722,
            'sha256': 'fa566ee62b2fa46d5d85a841ba0b6474bb8104da2da3d37364b5c90fbe90fbcb'})
        research = metadata.unique_json(research_raw)
        self.assertFalse(research['scope']['native_world_gate_passed'])
        self.assertFalse(research['scope']['normalizer_committed_and_independently_reviewed'])
        self.assertFalse(research['scope']['runtime_authority_created'])
        descriptor, document, _ = self.committed_real_source_review()
        producer_zip = Path('/workspace/scratch/5d16603ca7ff/native037-recovery/source-audit-11790609618.zip')
        self.assertEqual(caches.file_pin(producer_zip), {'bytes': 3307410,
            'sha256': '69bfc9f44e5304eae786d0668ba30f183f5b99a58586f8db7861f697d8e23aab'})
        with zipfile.ZipFile(producer_zip) as archive:
            native_raw = archive.read('MapServer-prefetch.exe')
            producer_members = {name: caches.pin_bytes(archive.read(name)) for name in archive.namelist()}
        self.assertEqual(caches.pin_bytes(native_raw), research['actual_tested_candidate'])
        package, authority, review, _ = owned['data']; authority = copy.deepcopy(authority)
        authority['native_record'] = copy.deepcopy(document['metadata_candidate']['native'])
        authority['materials']['producer'] = {'repository_commit': document['metadata_candidate']['source_commit'],
            'run_id': 38350813669, 'artifact_id': 11790609618,
            'artifact_zip': caches.file_pin(producer_zip), 'members': producer_members}
        compatibility = authority['compatibility']; recipe = compatibility['runtime_cache_context']
        compatibility['server_texture_projection']['native_consumer_sha256'] = research['actual_tested_candidate']['sha256']
        recipe['eligible_bins'] = copy.deepcopy(research['eligible_bins'])
        recipe['qualified_per_bin'] = copy.deepcopy(research['qualified_per_bin'])
        recipe['source_compatibility_review'] = descriptor
        _CONTROLLED_SOURCE_REVIEWS[metadata.canonical_sha(descriptor)] = {'descriptor': descriptor, 'document': document}
        derivation = copy.deepcopy(recipe['derived_native_proof'])
        # The real preload/donor descriptors remain exact. The separately named
        # unexecuted world/normalizer fixture is never presented as actual CI.
        for key, row in research['raw_inputs'].items(): derivation['raw_inputs'][key] = copy.deepcopy(row)
        proof = {'format': 1, 'role': 'native_metadata_cache_consumer_parity',
            'derivation': startup.runtime_cache_derivation_statement(derivation),
            'previous_shipping_consumer_sha256': document['shipping_036']['MapServer']['sha256'],
            'current_consumer_sha256': research['actual_tested_candidate']['sha256'],
            'actual_tested_control_consumers': [research['actual_tested_control']],
            'actual_tested_candidate': research['actual_tested_candidate'],
            'source_compatibility_review': descriptor, 'native_ID_tables_observed': False,
            'qualified_per_bin': research['qualified_per_bin'], 'observed_native_bin_paths': research['observed_native_bin_paths'],
            'controlled_adapter_fixture': True, 'actual_native_world_and_normalizer_review_pending': True}
        proof_raw = metadata.encoded(proof); (owned['assets']/'controlled.json').write_bytes(proof_raw)
        derivation['output']['pin'] = caches.pin_bytes(proof_raw)
        recipe['derived_native_proof'] = derivation
        _CONTROLLED_DERIVATIONS[metadata.canonical_sha(derivation)] = copy.deepcopy(derivation)
        outputs, schemas = {}, {}
        for archive_name in ('client-caches.zip', 'server-caches.zip'):
            with zipfile.ZipFile(owned['assets']/archive_name) as archive:
                manifest_name = 'client-cache-manifest.json' if archive_name.startswith('client') else caches.MANIFEST
                files = metadata.unique_json(archive.read(manifest_name))['files']
            for name, origin in recipe['eligible_bins'].items():
                if origin['archive'] != archive_name: continue
                outputs[name] = {key: files[name][key] for key in ('bytes', 'sha256')}
                schemas[name] = {'kind': files[name].get('kind', 'Parse6'),
                    'schema_identity_sha256': recipe['qualified_per_bin'][name]['schema_identity_sha256']}
        bin_recipe = {'format': 1, 'role': 'exact_original_bin_source_and_schema_recipe',
            'portable_provider': recipe['portable_provider'], 'archives': recipe['archives'],
            'eligible_origins': recipe['eligible_bins'], 'output_pins': outputs, 'schemas': schemas}
        compatibility['cache'].update(current_consumer_sha256=research['actual_tested_candidate']['sha256'],
            qualified_per_bin=recipe['qualified_per_bin'], eligible_bin_paths=sorted(recipe['eligible_bins']),
            bin_recipe_identity_sha256=metadata.canonical_sha(bin_recipe))
        with patch.dict(metadata.COMPONENT_AUTHORITIES, {'mapserver': authority}):
            package = metadata.unique_json(migration.wrap_manifest(fixture('mapserver')[1]['game-package.json'], 'mapserver', authority))
        review = copy.deepcopy(review); review['component_authority_sha256'] = metadata.canonical_sha(authority)
        owned['executable'].write_bytes(native_raw); owned['data'] = (package, authority, review, native_raw)
        return owned, research

    def test_actual107_preload_rows_use_exact_native_identities_in_controlled_pending_world_adapter(self):
        owned, research = self.actual_preload_107_controlled_adapter_fixture()
        before = (owned['worktree']/'data/bin/sequencers.bin').read_bytes()
        with synthetic_review(owned['data']):
            result = self.construct_provider(owned)
            self.assertEqual(result['context']['qualified_per_bin'], research['qualified_per_bin'])
            self.assertEqual(result['evidence']['authenticated_original_bin_count'], 107)
            self.assertEqual(sum(name.startswith('data/bin/') for name in result['evidence']['eligible_bin_paths']), 22)
            self.assertEqual(sum(name.startswith('data/server/bin/') for name in result['evidence']['eligible_bin_paths']), 85)
            self.assertEqual(result['evidence']['actual_tested_control_consumers'], [research['actual_tested_control']])
            self.assertEqual(result['evidence']['actual_tested_candidate'], research['actual_tested_candidate'])
            self.assertEqual(result['evidence']['runtime_cache_proof_derivation']['raw_inputs']['preload'], research['raw_inputs']['preload'])
            omitted = [row['name'] for row in research['omissions'] if 'name' in row]
            self.assertEqual(len(omitted), 17)
            self.assertFalse(set(omitted).intersection(result['context']['qualified_per_bin']))
            for name in (omitted[0], 'data/bin/unobserved_fixture.bin'):
                changed = copy.deepcopy(result['context'])
                changed['qualified_per_bin'][name] = copy.deepcopy(next(iter(research['qualified_per_bin'].values())))
                with self.subTest(extra=name), self.assertRaisesRegex(ValueError, 'per-BIN outputs'):
                    startup.verify_metadata_cache_context(owned['executable'], owned['data'][0], changed)
        self.assertEqual((owned['worktree']/'data/bin/sequencers.bin').read_bytes(), before)
        self.assertIsNone(startup.RUNTIME_CACHE_PROOF_DERIVATION)
        self.assertIsNone(metadata.REVIEWED_EXECUTION_AUTHORITIES['mapserver'])
        self.assertFalse(metadata.ACTIVATION_IMPLEMENTED)

    def test_derived_proof_authority_is_separate_nonrecursive_and_closed_in_production(self):
        owned = self.provider_fixture(); package, authority, _, _ = owned['data']
        descriptor = authority['compatibility']['runtime_cache_context']['derived_native_proof']
        proof = metadata.unique_json((owned['assets']/descriptor['output']['filename']).read_bytes())
        self.assertNotIn('output', proof['derivation'])
        self.assertEqual(proof['derivation'], startup.runtime_cache_derivation_statement(descriptor))
        self.assertNotEqual(descriptor['output']['pin'], authority['materials']['qualification']['members']['controlled.json'])
        self.assertFalse(descriptor['scope']['original_artifact_membership_claimed'])
        self.assertFalse(descriptor['scope']['shipping_bytes_executed_claimed'])
        self.assertIsNone(startup.RUNTIME_CACHE_PROOF_DERIVATION)
        with self.assertRaisesRegex(ValueError, 'derivation is not frozen'):
            startup.inspect_runtime_cache_derivation(descriptor)
        with synthetic_review(owned['data']):
            self.assertEqual(startup.inspect_runtime_cache_derivation(descriptor), descriptor)

    def test_derivation_source_raw_inputs_output_and_scope_tampering_are_rejected(self):
        owned = self.provider_fixture()
        descriptor = owned['data'][1]['compatibility']['runtime_cache_context']['derived_native_proof']
        mutations = {
            'source_commit': lambda d: d['derivation_source'].__setitem__('repository_commit', '0'*40),
            'source_path': lambda d: d['derivation_source'].__setitem__('path', 'tools/another.py'),
            'source_blob': lambda d: d['derivation_source'].__setitem__('git_blob', '0'*40),
            'source_pin': lambda d: d['derivation_source']['pin'].__setitem__('sha256', '0'*64),
            'preload_zip': lambda d: d['raw_inputs']['preload']['artifact_zip'].__setitem__('sha256', '0'*64),
            'world_receipt': lambda d: d['raw_inputs']['native_world']['member_pin'].__setitem__('sha256', '0'*64),
            'client_manifest': lambda d: d['raw_inputs']['client_cache_manifest']['member_pin'].__setitem__('sha256', '0'*64),
            'server_zip': lambda d: d['raw_inputs']['server_cache_manifest']['component_zip'].__setitem__('sha256', '0'*64),
            'output': lambda d: d['output']['pin'].__setitem__('sha256', '0'*64),
            'membership': lambda d: d['scope'].__setitem__('original_artifact_membership_claimed', True),
            'native_tables': lambda d: d['scope'].__setitem__('native_ID_tables_observed', True),
            'shipping_execution': lambda d: d['scope'].__setitem__('shipping_bytes_executed_claimed', True)}
        for name, mutate in mutations.items():
            changed = copy.deepcopy(descriptor); mutate(changed)
            with self.subTest(name=name), patch.object(startup, 'RUNTIME_CACHE_PROOF_DERIVATION', descriptor), self.assertRaises(ValueError):
                startup.inspect_runtime_cache_derivation(changed)
        malformed = []
        changed = copy.deepcopy(descriptor); changed['raw_inputs']['server_cache_manifest']['run_id'] = 1; malformed.append(changed)
        changed = copy.deepcopy(descriptor); changed['raw_inputs']['native_world']['run_id'] = True; malformed.append(changed)
        changed = copy.deepcopy(descriptor); changed['derivation_source']['path'] = 'tools/../untrusted.py'; malformed.append(changed)
        changed = copy.deepcopy(descriptor); changed['raw_inputs'].pop('preload'); malformed.append(changed)
        changed = copy.deepcopy(descriptor); changed['scope']['original_artifact_membership_claimed'] = True; malformed.append(changed)
        for index, changed in enumerate(malformed):
            with self.subTest(malformed=index), patch.object(startup, 'RUNTIME_CACHE_PROOF_DERIVATION', changed), self.assertRaises(ValueError):
                startup.inspect_runtime_cache_derivation(changed)

    def test_derived_flat_output_tampering_preserves_current_private_bins(self):
        owned = self.provider_fixture(); leaf = owned['worktree']/'data/bin/sequencers.bin'; before = leaf.read_bytes()
        proof_path = owned['assets']/'controlled.json'
        proof = metadata.unique_json(proof_path.read_bytes()); proof['native_ID_tables_observed'] = True
        proof_path.write_bytes(metadata.encoded(proof))
        with synthetic_review(owned['data']), self.assertRaisesRegex(ValueError, 'proof bytes differ'):
            self.construct_provider(owned)
        self.assertEqual(leaf.read_bytes(), before)

    def committed_real_source_review(self):
        path = ROOT/'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json'
        raw = path.read_bytes()
        self.assertEqual(caches.pin_bytes(raw), {'bytes': 15614,
            'sha256': 'e5a268b0fbae23230e518f8dcbb49fdccdcdd998293de61b133cc7b5bbf1fd44'})
        descriptor = {'repository': 'Russianranger/coh-android',
            'commit': '1b8da4eb850c0e7c4f4ef0a49e43e15ac948ca2e',
            'path': 'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json',
            'git_blob': '6b6d373a275029476f28c77cc5fcfe010e58b9bb',
            'content': caches.pin_bytes(raw), 'scope': copy.deepcopy(startup.SOURCE_ONLY_REVIEW_SCOPE)}
        document = metadata.unique_json(raw)
        controls = [metadata.native_record_pin(document['observed_control'][name])
            for name in ('unobserved_control', 'observed_Map')]
        kwargs = {'previous_shipping_consumer_sha256': document['shipping_036']['MapServer']['sha256'],
            'actual_tested_control_consumers': controls,
            'actual_tested_candidate': metadata.native_record_pin(document['metadata_candidate']['native'])}
        return descriptor, document, kwargs

    def test_actual_committed_source_record_is_independent_and_cannot_authorize_execution(self):
        descriptor, document, kwargs = self.committed_real_source_review()
        self.assertIsNone(startup.SOURCE_ONLY_COMPATIBILITY_REVIEW)
        with self.assertRaisesRegex(ValueError, 'source-only compatibility review is not frozen'):
            startup.inspect_committed_source_review(descriptor, **kwargs)
        with patch.object(startup, 'SOURCE_ONLY_COMPATIBILITY_REVIEW', {'descriptor': descriptor, 'document': document}):
            inspected = startup.inspect_committed_source_review(descriptor, **kwargs)
        self.assertFalse(inspected['scope']['runtime_activation_allowed'])
        self.assertFalse(inspected['scope']['shipping_predecessor_execution_validated'])
        self.assertFalse(inspected['scope']['behavioral_collision_validated'])
        self.assertFalse(inspected['native_execution_or_physical_results_added_by_source_review'])
        self.assertEqual([row['sha256'] for row in inspected['actual_tested_control_consumers']],
            ['77c1f245132b76668e9f689bec26699ec980382c1079f000314d24b149e089ea',
             'fbfcf1d80a41a80aaeecb1a0ec275daffed2a9e1ba25df3f16e23b16a51a493d'])

    def test_committed_review_commit_path_blob_content_scope_and_control_substitution_rejected(self):
        descriptor, document, kwargs = self.committed_real_source_review()
        authority = {'descriptor': descriptor, 'document': document}
        for key in ('commit', 'path', 'git_blob', 'content', 'scope'):
            changed = copy.deepcopy(descriptor)
            if key == 'content': changed[key]['sha256'] = '0'*64
            elif key == 'scope': changed[key]['shipping_predecessor_execution_validated'] = True
            elif key == 'path': changed[key] = 'docs/android-evidence/another.json'
            else: changed[key] = '0'*40
            with self.subTest(key=key), patch.object(startup, 'SOURCE_ONLY_COMPATIBILITY_REVIEW', authority), self.assertRaises(ValueError):
                startup.inspect_committed_source_review(changed, **kwargs)
        changed = copy.deepcopy(kwargs)
        changed['actual_tested_control_consumers'] = [metadata.native_record_pin(document['shipping_036']['MapServer'])]
        with patch.object(startup, 'SOURCE_ONLY_COMPATIBILITY_REVIEW', authority), self.assertRaisesRegex(ValueError, 'actual tested controls'):
            startup.inspect_committed_source_review(descriptor, **changed)
        changed_authority = copy.deepcopy(authority)
        changed_authority['document']['metadata_candidate']['build_input']['native_execution_validated'] = True
        with patch.object(startup, 'SOURCE_ONLY_COMPATIBILITY_REVIEW', changed_authority), self.assertRaisesRegex(ValueError, 'content or Git blob'):
            startup.inspect_committed_source_review(descriptor, **kwargs)


if __name__ == '__main__': unittest.main()
