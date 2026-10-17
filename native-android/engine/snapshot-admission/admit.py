#!/usr/bin/env python3
"""Admit one retained source snapshot for offline analysis, never live publication.

The adjacent reviewed trust manifest is part of this module, not archive input.
No extraction, subprocess, server startup or archive-supplied source execution.
"""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import stat
import zipfile
import zlib

SOURCE = '3e8b5c9f5b794b58a66c6d8c62a593b926a10873'
MAX_ARCHIVE = 4 * 1024 * 1024
MAX_TOTAL = 16 * 1024 * 1024

class AdmissionError(ValueError):
    """No admission result exists when any input fails."""

def require(condition, label):
    if not condition:
        raise AdmissionError(label)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result

def decode(data):
    try:
        return json.loads(data, object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(AdmissionError('nonfinite JSON')))
    except (ValueError, UnicodeError) as exc:
        raise AdmissionError('invalid JSON') from exc

@dataclass(frozen=True)
class OfflineAdmission:
    schema: str
    source_revision: str
    asset_generation: int
    catalog_sha256: str
    snapshot_sha256: str
    source_identity_sha256: str
    run_identity_sha256: str
    diagnostic_sha256: str
    active_roots: int
    external_objects: int
    reachable_external: tuple
    evidence_member_count: int
    offline_analysis_only: bool = True
    live_groups_transaction: bool = False
    physical_generation_verified: bool = False
    graph_publication_authorized: bool = False
    actor_publication_authorized: bool = False
    renderer_authorized: bool = False
    world_authority: bool = False


def _bindings(data):
    """Cross-check receipts independently of the exact-member digest seal."""
    def obj(name):
        result = decode(data[name])
        require(type(result) is dict, name + ': object required')
        return result
    binding = obj('capture/snapshot-binding.json')
    receipt = obj('capture/capture-receipt.json')
    source = obj('capture/source-identity.json')
    run = obj('capture/run-identity.json')
    diag = obj('runtime-graph-diagnostic.json')
    scope = obj('scope.json')
    require(binding['schema'] == 'coh-runtime-snapshot-binding-v1', 'binding schema')
    require(receipt['schema'] == 'coh-disposable-runtime-snapshot-v1', 'receipt schema')
    require(source['schema'] == 'coh-runtime-snapshot-source-v1', 'source schema')
    require(run['schema'] == 'coh-runtime-snapshot-run-v1', 'run schema')
    for flag in ('cleanup_verified', 'source_snapshot_only'):
        require(binding[flag] is True and receipt[flag] is True, flag)
    for flag in ('runtime_executed', 'runtime_snapshot_captured', 'catalog_captured',
                 'catalog_exact_equality', 'owned_process_groups_absent', 'source_runtime_unchanged', 'passed'):
        require(receipt[flag] is True, flag)
    for flag in ('live_groups_transaction', 'renderer_authorized', 'physical_thor_generation_verified',
                 'matching_groups_transaction_captured', 'player_profile_opened', 'accepted_runtime_modified'):
        require(receipt[flag] is False, flag)
    require(binding['live_groups_transaction'] is False, 'binding live scope')
    for flag in ('native_ready_or_character_ack', 'actual_groups_transaction',
                 'physical_thor_accepted', 'full_live_world_verified', 'gates25_27_complete'):
        require(scope[flag] is False, 'scope ' + flag)
    require(scope['source_revision'] == SOURCE, 'scope source')
    generation = binding['asset_generation']
    require(type(generation) is int and generation == 20261016 and
            source['asset_generation'] == generation == receipt['generation'], 'generation binding')
    for kind, filename in (('catalog', 'catalog.cohcat'), ('snapshot', 'runtime.cohrts')):
        payload = data['capture/' + filename]
        require(binding[kind] == receipt[kind] == {'bytes': len(payload), 'sha256': digest(payload)}, kind + ' binding')
    for kind in ('source', 'run'):
        name = kind + '-identity.json'
        actual = digest(data['capture/' + name])
        require(binding[kind + '_identity'] == {'file': name, 'sha256': actual}, kind + ' identity binding')
        require(receipt[kind + '_identity_sha256'] == actual, kind + ' receipt identity')
    require(run['source_identity_sha256'] == digest(data['capture/source-identity.json']), 'run source')
    require(run['orchestration_source_revision'] == receipt['orchestration_source_revision'] ==
            receipt['exporter_source_revision'] == source['exporter_source_revision'] == SOURCE, 'source pin')
    require(run['orchestration_source_tree'] == receipt['orchestration_source_tree'] ==
            'f1979e5e065cdabcbed888e22ca0870c4548cbec', 'source tree')
    require(source['orchestration_source_sha256'] == receipt['source_sha256'], 'source closure')
    require(source['runtime_inventory'] == receipt['source_runtime_inventory'], 'runtime inventory')
    require(source['exporter']['sha256'] == receipt['exporter_sha256'], 'exporter identity')
    require(source['retained_catalog_sha256'] == binding['catalog']['sha256'], 'retained catalog')
    for key in ('control_fixture_sha256', 'native_dependency_closure_sha256'):
        require(source[key] == receipt[key], key)
    require(receipt['control_fixture_sha256'] == digest(data['control-fixture.json']), 'control receipt')
    require(receipt['path_probe_build_receipt_sha256'] == digest(data['path-probe-build.json']), 'probe receipt')
    for row in receipt['diagnostics']:
        payload = data['capture/' + row['file']]
        require(row['bytes'] == len(payload) and row['sha256'] == digest(payload), 'diagnostic receipt')
    for flag in ('graph_published', 'groups_received', 'world_authority', 'assets_admitted',
                 'actor_admitted', 'android_executed', 'physical_thor_accepted'):
        require(diag[flag] is False, 'diagnostic scope ' + flag)
    require(diag['passed'] is True and diag['actual_snapshot_qualified'] is True, 'diagnostic qualification')
    pins = diag['capture_pins']
    require(pins == dict(asset_generation=generation, catalog_sha256=binding['catalog']['sha256'],
                        snapshot_sha256=binding['snapshot']['sha256'],
                        source_sha256=binding['source_identity']['sha256'],
                        run_sha256=binding['run_identity']['sha256']), 'diagnostic pins')
    captured = diag['captured']
    require(set(captured) == {'release', 'asan', 'ubsan'} and
            captured['release'] == captured['asan'] == captured['ubsan'], 'qualification mode parity')
    result = captured['release']
    for key in ('active_roots', 'root_slots', 'external_count', 'files', 'slots', 'children'):
        require(result[key] == receipt['sink'][key], 'sink ' + key)
    require(result['passed'] is True and result['definitions_crc_verified'] == 1 and
            result['references_crc_verified'] == 1, 'CRC qualification')
    require(result['source_defs_crc'] == receipt['sink']['defs_crc'] == 3173822562 and
            result['source_refs_crc'] == receipt['sink']['refs_crc'] == 3649375123, 'source CRC identity')
    require(result['root_matrices_verified'] == result['active_roots'] == 33, 'root matrix coverage')
    return OfflineAdmission('coh-offline-snapshot-admission-v1', SOURCE, generation,
                            binding['catalog']['sha256'], binding['snapshot']['sha256'],
                            binding['source_identity']['sha256'], binding['run_identity']['sha256'],
                            digest(data['runtime-graph-diagnostic.json']), result['active_roots'],
                            result['external_count'], tuple(e['name'] for e in result['external'] if e['reachable']), len(data))


def validate_archive(path):
    """Validate all exact retained members before returning a frozen summary.

    ZIP container metadata may differ; member names, sizes and bytes may not.
    Trust is the reviewed local manifest, never hashes supplied by the archive.
    """
    trust = decode(Path(__file__).with_name('capture-trust.json').read_bytes())
    try:
        with open(path, 'rb') as stream:
            require(stream.seek(0, 2) <= MAX_ARCHIVE, 'archive bound')
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive:
                infos = archive.infolist()
                require(len(infos) == len(trust['members']), 'member count')
                require(len({i.filename for i in infos}) == len(infos), 'duplicate ZIP member')
                require({i.filename for i in infos} == set(trust['members']), 'member set')
                require(sum(i.file_size for i in infos) <= MAX_TOTAL, 'aggregate uncompressed bound')
                data = {}
                for info in infos:
                    expected = trust['members'][info.filename]
                    require(info.file_size == expected['bytes'], 'member size: ' + info.filename)
                    mode = info.external_attr >> 16
                    require(stat.S_IFMT(mode) in (0, stat.S_IFREG) and not info.is_dir() and not info.flag_bits & 1, 'member type')
                    require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'compression method')
                    with archive.open(info) as member:
                        payload = member.read(expected['bytes'] + 1)
                    require(len(payload) == expected['bytes'] and digest(payload) == expected['sha256'],
                            'member digest: ' + info.filename)
                    data[info.filename] = payload
                return _bindings(data)
    except (KeyError, TypeError, OSError, EOFError, zipfile.BadZipFile, zlib.error, RuntimeError) as exc:
        raise AdmissionError('invalid capture archive: ' + str(exc)) from exc

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(asdict(validate_archive(args.archive)), indent=2))
    except AdmissionError as exc:
        parser.exit(1, 'refused: ' + str(exc) + '\n')
