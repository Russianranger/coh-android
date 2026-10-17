#!/usr/bin/env python3
"""Read-only independent review of three already-completed hosted artifacts.

No compilation, native execution, extraction, service startup or workflow action.
All source comparisons use exact published Git blobs, never mutable checkout files.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import zipfile

REVISION = '3e8b5c9f5b794b58a66c6d8c62a593b926a10873'
CATALOG_SHA = '61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763'
SNAPSHOT_SHA = 'c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02'
PE_SHA = '41c09bafba7e216fd62c3ec4d07f58e7947b9e811d960bb85daffa2b73d56cd3'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(raw):
    return {'bytes': len(raw), 'sha256': digest(raw)}


def archive(path, expected_size, expected_sha):
    assert path.stat().st_size == expected_size
    raw = path.read_bytes()
    assert digest(raw) == expected_sha
    z = zipfile.ZipFile(io.BytesIO(raw))
    infos = z.infolist()
    names = [i.filename for i in infos]
    assert len(names) == len(set(names)) and z.testzip() is None
    assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n for n in names)
    assert all(not i.flag_bits & 1 and stat.S_IFMT(i.external_attr >> 16) != stat.S_IFLNK and i.file_size <= 16 * 1024**2 for i in infos)
    assert sum(i.file_size for i in infos) <= 64 * 1024**2
    return z, dict(identity(raw), members=len(infos), uncompressed_bytes=sum(i.file_size for i in infos), crc_verified=True, member_paths_verified=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source-controls-zip', 'compile-zip', 'runtime-zip', 'repository', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    source, source_zip = archive(a.source_controls_zip, 21689, 'b891edf82b9290aec1a46f1b0218ae241cbb613b568fec1a8586f6ef409d9f09')
    build, build_zip = archive(a.compile_zip, 3298274, '2d6444b5f7ac3a1b06cc841fe15710d298c9a913a09f0de658f8dc9b945743df')
    runtime, runtime_zip = archive(a.runtime_zip, 2024961, '8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d')
    def blob(name):
        return subprocess.check_output(['git', '-C', str(a.repository), 'show', REVISION + ':' + name])
    def load(z, name):
        assert z.getinfo(name).file_size <= 8 * 1024**2
        return json.loads(z.read(name))
    def pinned(values, prefix='', lf=False):
        for name, expected in values.items():
            raw = blob(prefix + name)
            assert digest(raw.replace(b'\r\n', b'\n') if lf else raw) == expected, name
    producer = load(source, 'producer.json')
    assert producer['passed'] and producer['source_revision'] == REVISION and producer['source_unchanged_before_after']
    assert producer['runtime_executed'] is False and producer['live_groups_transaction'] is False
    for name, expected in producer['source_sha256'].items():
        path = name.removeprefix('dependency/') if name.startswith('dependency/') else ('native-android/engine/scenecatalog/' + name[len('catalog/'):] if name.startswith('catalog/') else 'native-android/engine/scenecatalog-server/' + name)
        assert digest(blob(path)) == expected, name
    pinned(producer['original_sha256_lf'], 'upstream/ouroboros/', True)
    for name, expected in producer['fixtures'].items():
        assert identity(source.read('fixtures/' + name)) == expected
    assert producer['control_tests'] == 10
    assert [(r['producer']['checks'], r['sink']['checks']) for r in producer['modes']] == [(311, 247)] * 3
    compiled = load(build, 'compile-only-receipt.json')
    assert compiled['passed'] and compiled['source_revision'] == REVISION and compiled['source_git_status_porcelain'] == []
    assert compiled['source_stage_verified'] and compiled['published_inputs_reverified'] and compiled['runtime_executed'] is False
    assert set(build.namelist()) == set(compiled['artifacts']) | {'compile-only-receipt.json'}
    for name, expected in compiled['artifacts'].items():
        assert identity(build.read(name)) == expected
    pe = build.read('MapServer.exe')
    assert identity(pe) == {'bytes': 7495680, 'sha256': PE_SHA}
    pe_at = struct.unpack_from('<I', pe, 0x3c)[0]
    assert pe[:2] == b'MZ' and pe[pe_at:pe_at+4] == b'PE\0\0'
    assert struct.unpack_from('<H', pe, pe_at+4)[0] == 0x14c and struct.unpack_from('<H', pe, pe_at+24)[0] == 0x10b
    overlay_files = {'coh_source_catalog_export.inc': 'scenecatalog/source_export.inc', 'coh_source_catalog_sink.inc': 'scenecatalog-server/source_sink.inc', 'coh_source_runtime_snapshot.inc': 'scenecatalog-server/source_snapshot.inc', 'coh_source_runtime_snapshot_sink.inc': 'scenecatalog-server/source_snapshot_sink.inc'}
    for name, path in overlay_files.items():
        assert build.read('source/MapServer/src/group/' + name) == blob('native-android/engine/' + path)
    capture = load(runtime, 'capture/capture-receipt.json')
    binding = load(runtime, 'capture/snapshot-binding.json')
    source_id = load(runtime, 'capture/source-identity.json')
    run_id = load(runtime, 'capture/run-identity.json')
    graph = load(runtime, 'runtime-graph-diagnostic.json')
    assert capture['passed'] and capture['runtime_executed'] and capture['runtime_snapshot_captured'] and capture['catalog_exact_equality']
    assert capture['source_snapshot_only'] and capture['orchestration_source_revision'] == capture['exporter_source_revision'] == REVISION
    for field in ('physical_thor_generation_verified', 'player_profile_opened', 'accepted_runtime_modified', 'renderer_authorized', 'matching_groups_transaction_captured', 'live_groups_transaction'):
        assert capture[field] is False
    assert capture['exporter_sha256'] == PE_SHA
    pinned(capture['source_sha256'])
    assert source_id['orchestration_source_sha256'] == capture['source_sha256']
    assert source_id['exporter_source_revision'] == REVISION and source_id['exporter'] == identity(pe)
    assert source_id['compile_receipt_sha256'] == digest(build.read('compile-only-receipt.json'))
    assert source_id['stage_receipt_sha256'] == digest(build.read('native-runtime-snapshot-server-build-input.json'))
    assert source_id['runtime_inventory'] == capture['source_runtime_inventory'] and capture['source_runtime_unchanged']
    assert source_id['map_id'] == 1 and source_id['map_name'] == 'maps/City_Zones/City_01_01/City_01_01.txt'
    assert source_id['control_fixture_sha256'] == capture['control_fixture_sha256'] == digest(runtime.read('control-fixture.json'))
    assert source_id['db_donor'] == capture['db_donor'] == {'bytes': 42048020, 'sha256': 'c2d859621476e22add673a76c4b6aae65c2143671e50c085d020108b6e19d95e'}
    for key, name in (('source_identity', 'source-identity.json'), ('run_identity', 'run-identity.json')):
        raw = runtime.read('capture/' + name)
        assert raw == (json.dumps(json.loads(raw), sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
        assert binding[key] == {'file': name, 'sha256': digest(raw)}
        assert capture[key + '_sha256'] == digest(raw)
    assert run_id['source_identity_sha256'] == binding['source_identity']['sha256'] and re.fullmatch('[0-9a-f]{64}', run_id['nonce'])
    assert run_id['orchestration_source_revision'] == REVISION and run_id['orchestration_source_tree'] == capture['orchestration_source_tree']
    assert run_id['orchestration_source_tree'] == subprocess.check_output(['git', '-C', str(a.repository), 'rev-parse', REVISION + '^{tree}'], text=True).strip()
    assert run_id['db_schema_sha256'] == digest((json.dumps(capture['db_schema'], sort_keys=True, separators=(',', ':')) + '\n').encode())
    assert run_id['private_fresh_postgresql'] and run_id['private_fresh_wine_prefix'] and not run_id['player_profile_opened']
    catalog = runtime.read('capture/catalog.cohcat')
    sidecar = runtime.read('capture/runtime.cohrts')
    assert identity(catalog) == binding['catalog'] == capture['catalog'] == {'bytes': 12179670, 'sha256': CATALOG_SHA}
    assert identity(sidecar) == binding['snapshot'] == capture['snapshot'] == {'bytes': 6585, 'sha256': SNAPSHOT_SHA}
    old_zip_raw = blob('native-android/corpus/server-catalog/capture-38948147691/evidence.zip')
    assert digest(old_zip_raw) == '6f45437efd8fe7c16b7468634f2ad1914ba446b739632e59d65dc6912624ade3'
    old = zipfile.ZipFile(io.BytesIO(old_zip_raw))
    assert old.testzip() is None and old.getinfo('capture/catalog.cohcat').CRC == 0x5c1d8631
    assert old.read('capture/catalog.cohcat') == catalog
    assert old.read('path-probe-build.json') == runtime.read('path-probe-build.json')
    assert digest(old.read('catalog-path-probe.exe')) == capture['path_probe_sha256']
    prior_fixture, current_fixture = load(old, 'control-fixture.json'), load(runtime, 'control-fixture.json')
    for key in ('all_external_payloads', 'client_asset_hashes', 'atlas_preparation'):
        assert prior_fixture[key] == current_fixture[key]
    old_inventory = load(old, 'capture/capture-receipt.json')['source_runtime_inventory']
    assert sidecar[:8] == b'COHRTS01'
    header = struct.unpack_from('<18I', sidecar, 8)
    assert header == (1, 80, len(sidecar), 20261016, len(catalog), 508, 40225, 40225, 130314, 33, 33, 7, 3173822562, 3649375123, 0, 0, 0, 0)
    assert capture['sink'] == dict(zip(('status', 'catalog_status', 'snapshot_status', 'catalog_bytes', 'snapshot_bytes', 'files', 'slots', 'definitions', 'children', 'root_slots', 'active_roots', 'external_count', 'external_children', 'defs_crc', 'refs_crc', 'partial_remaining'), (1, 0, 0, len(catalog), len(sidecar), 508, 40225, 40225, 130314, 33, 33, 7, 0, 3173822562, 3649375123, 0)))
    assert capture['cleanup_verified'] and binding['cleanup_verified'] and capture['owned_process_groups_absent']
    assert capture['wine_prefix_cleanup'] == {'kill_exit_code': 0, 'wait_exit_code': 0, 'private_fresh_prefix': True}
    assert capture['retained_failed_outputs'] == [] and capture['diagnostics_suppressed_unverified_credentials'] is False
    postgres_stopped = False
    for entry in capture['diagnostics']:
        raw = runtime.read('capture/' + entry['file'])
        assert identity(raw) == {key: entry[key] for key in ('bytes', 'sha256')} and len(raw) <= 768 * 1024
        if entry['owned_source'] == 'pg/postgres.log':
            postgres_stopped = b'database system is shut down' in raw
    assert postgres_stopped and len(capture['diagnostics']) == 19
    assert binding['asset_generation'] == source_id['asset_generation'] == capture['generation'] == 20261016
    assert binding['source_snapshot_only'] and binding['live_groups_transaction'] is False
    assert graph['passed'] and graph['actual_snapshot_qualified']
    for key in ('native_source_sha256', 'producer_source_sha256', 'original_helper_sha256'):
        pinned(graph[key])
    assert graph['capture_pins'] == {'asset_generation': 20261016, 'catalog_sha256': CATALOG_SHA, 'snapshot_sha256': SNAPSHOT_SHA, 'source_sha256': binding['source_identity']['sha256'], 'run_sha256': binding['run_identity']['sha256']}
    result = graph['captured']['release']
    assert graph['captured']['asan'] == graph['captured']['ubsan'] == result
    assert result['passed'] and result['definitions_crc_verified'] == result['references_crc_verified'] == 1 and result['root_matrices_verified'] == 33
    for key in ('graph_published', 'groups_received', 'world_authority', 'assets_admitted', 'actor_admitted', 'android_executed', 'physical_thor_accepted'):
        assert graph[key] is False
    report = {'schema': 'coh-runtime-snapshot-independent-artifact-review-v1', 'reviewer': 'worker-a', 'passed': True,
        'review_program_sha256': digest(Path(__file__).read_bytes()), 'run_id': 38977202310, 'source_revision': REVISION,
        'source_controls_archive': source_zip, 'win32_compile_archive': dict(build_zip, artifact_id=12079533226),
        'runtime_archive': dict(runtime_zip, artifact_id=12079509924), 'compiled_pe': dict(identity(pe), machine='I386', format='PE32'),
        'host_native_helper_inputs_verified': len(producer['source_sha256']), 'host_original_lf_inputs_verified': len(producer['original_sha256_lf']),
        'runtime_orchestration_inputs_verified': len(capture['source_sha256']), 'host_fixture_files_verified': len(producer['fixtures']),
        'compile_artifact_members_verified': len(compiled['artifacts']), 'catalog': identity(catalog), 'snapshot': identity(sidecar),
        'original_catalog_byte_equality_verified': True, 'retained_path_probe_reused': True,
        'original_asset_payloads_client_hashes_and_atlas_preparation_equal': True,
        'source_identity_sha256': binding['source_identity']['sha256'], 'run_identity_sha256': binding['run_identity']['sha256'],
        'receipt_sha256': {name: digest(runtime.read(name)) for name in ('capture/capture-receipt.json', 'capture/snapshot-binding.json', 'capture/source-identity.json', 'capture/run-identity.json', 'runtime-graph-diagnostic.json')},
        'same_run_runtime_inventory': capture['source_runtime_inventory'], 'prior_capture_runtime_inventory': old_inventory,
        'whole_runtime_identity_matches_prior_capture': capture['source_runtime_inventory'] == old_inventory,
        'whole_runtime_difference_localized': False, 'same_run_source_runtime_unchanged': True,
        'cleanup_receipt_verified': True, 'wine_prefix_kill_and_wait_zero': True, 'owned_process_groups_absent': True,
        'postgres_shutdown_log_observed': True, 'diagnostic_file_hashes_verified': len(capture['diagnostics']),
        'cleanup_scope': 'Original hosted receipts and ordered qualified driver control flow; no access to already-terminated hosted processes.',
        'actual_native_diagnostic_reused_without_rerun': result, 'source_snapshot_only': True, 'live_groups_transaction': False,
        'new_runtime_started_by_review': False, 'tests_rebuilt_or_rerun': False, 'android_executed': False, 'physical_thor_accepted': False,
        'limitations': ['Root/future source snapshot is not a received GROUPS transaction or a selected actor.', 'A reachable future still requires original client semantics and asset qualification.', 'Named native memory is not whole-process RSS.', 'Same-run inventory integrity does not assert identical full runtime to the older capture.'],
        'canonical_runtime_archive': 'native-android/corpus/server-catalog/runtime-snapshot-38977202310/evidence.zip',
        'canonical_compile_archive': 'native-android/corpus/server-catalog/runtime-snapshot-38977202310/win32-compile.zip'}
    with a.output.open('x') as out:
        json.dump(report, out, indent=2); out.write('\n')
    print(json.dumps({'passed': True, 'review_sha256': digest(a.output.read_bytes()), 'catalog_exact': True, 'snapshot_bytes': len(sidecar), 'cleanup_verified': True, 'runtime_started': False}))


if __name__ == '__main__':
    main()
