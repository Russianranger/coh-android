#!/usr/bin/env python3
"""Closed successor native promotion boundary; historical consumers remain exact.

This scaffold can inspect additive research evidence, but cannot promote a new
Game or Map executable. Actual admission is a separately reviewed integration.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

PROMOTIONS_IMPLEMENTED = False
RETAINED_MAP = {'bytes': 7475200,
    'sha256': 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'}
MAP_CANDIDATE = {'bytes': 7480832,
    'sha256': '5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6'}
MAP_SOURCE = '47e40d4d586d29e273e31ed4d0d51d160832b89d'
MAP_BUILD_RUN = 38350813669
MAP_BUILD_ARTIFACT = {'id': 11790609618, 'bytes': 3307410,
    'sha256': '69bfc9f44e5304eae786d0668ba30f183f5b99a58586f8db7861f697d8e23aab'}


def require(value, message):
    if not value: raise ValueError(message)


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False, ensure_ascii=False).encode()).hexdigest()


def pin(value):
    require(type(value) is dict and set(value) == {'bytes', 'sha256'}
        and type(value['bytes']) is int and 0 < value['bytes'] <= 256*1024**2
        and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
        'Exact bounded native evidence pin required')
    return value


def validate_disabled_promotions(value):
    require(type(value) is dict and set(value) == {'game', 'mapserver'}
        and all(type(value[name]) is dict and set(value[name]) == {'enabled'}
            and value[name]['enabled'] is False for name in value),
        'Native Game/Map promotions are closed until exact reviewed component gates are integrated')
    require(PROMOTIONS_IMPLEMENTED is False, 'This scaffold has no implemented native promotion path')
    return copy.deepcopy(value)


def retain_native_component(donor, actual_server_archives, actual_component):
    require(actual_server_archives == donor['package_preflight']['server_archives']
        and actual_component == donor['map_startup_component'],
        'Closed native promotion must preserve exact .36 Game/Db/Map/schema/component bytes and producers')
    require(actual_component.get('files', {}).get('MapServer.exe') == RETAINED_MAP,
        'Unknown consumer cannot use the retained cache/texture projection compatibility')
    return {'format': 1, 'policy': 'retain_exact_audited_036_native_consumers',
        'native_promotions_implemented': False, 'new_native_consumer_admitted': False,
        'unknown_consumer_allowed': False, 'old_producer_facts_relabelled': False,
        'mapserver': RETAINED_MAP, 'original_component': copy.deepcopy(actual_component),
        'server_archives': copy.deepcopy(actual_server_archives)}


def prepare_reviewed_native_archives(donor_apk, material_paths):
    """Dormant bounded preparation from exact original artifact ZIP bytes.

    This has no signing, build dispatch, installation or publication action.
    Production keeps both this gate and the guest execution reviews closed.
    Opening it requires separately authenticated current Game/Map proofs;
    historical initialization/animation receipts stay unchanged inside each
    archive. A caller cannot substitute a candidate SHA or a passing boolean.
    """
    require(PROMOTIONS_IMPLEMENTED is True, 'Native archive promotion preparation is disabled')
    require(type(material_paths) is dict and material_paths
        and set(material_paths) <= {'game', 'mapserver'}, 'Explicit finite Game/Map material paths required')
    import native_startup_component_migration as migration
    contract = migration.contract
    originals = migration.authenticated_donor(donor_apk)
    archives, proofs = {}, {}
    for kind in sorted(material_paths):
        expected, executable = migration.authenticate_materials(kind, material_paths[kind])
        raw, proof = migration.migrate_archive(originals[kind], kind, executable, expected)
        reader = migration.zip_members if kind == 'game' else migration.game_members
        members, _ = reader(raw)
        package = contract.unique_json(members[contract.COMPONENTS[kind]['manifest']])
        reviewed = contract.runtime_admission(package, kind)
        require(proof['native']['sha256'] == reviewed['current_consumer_sha256'],
            'Archive native bytes differ from separately reviewed current consumer')
        archives[migration.ARCHIVES[kind]] = raw
        proofs[kind] = {**proof, 'execution_review_sha256': reviewed['execution_review_sha256'],
            'qualified_maps': reviewed['qualified_maps'],
            'actual_artifact_bytes_authenticated': True, 'apk_publication_authorized': False,
            'native_process_executed_by_preparer': False, 'original_producer_relabelled': False}
    return archives, proofs


def verify_committed_source_compatibility_review(repository=None):
    """Verify the actual committed source review without admitting native code."""
    import native_startup_component_migration as migration
    import native_map_startup_contract as startup
    repository = Path(repository) if repository is not None else migration.ROOT
    value = startup.SOURCE_ONLY_COMPATIBILITY_REVIEW
    require(type(value) is dict and set(value) == {'descriptor', 'document'},
        'Separately reviewed committed source audit is absent')
    descriptor, document = value['descriptor'], value['document']
    require(type(descriptor) is dict and type(descriptor.get('commit')) is str
        and re.fullmatch('[0-9a-f]{40}', descriptor['commit'])
        and descriptor.get('path') == 'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json',
        'Exact source-only audit commit/path required')
    result = subprocess.run(['git', 'show', descriptor['commit']+':'+descriptor['path']],
        cwd=repository, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
    raw = result.stdout
    require(result.returncode == 0 and raw == migration.contract.encoded(document)
        and migration.content_pin(raw) == descriptor['content']
        and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == descriptor['git_blob'],
        'Actual committed source audit content/blob differs')
    controls = [migration.contract.native_record_pin(document['observed_control'][name])
        for name in ('unobserved_control', 'observed_Map')]
    inspected = startup.inspect_committed_source_review(descriptor,
        previous_shipping_consumer_sha256=document['shipping_036']['MapServer']['sha256'],
        actual_tested_control_consumers=controls,
        actual_tested_candidate=migration.contract.native_record_pin(document['metadata_candidate']['native']))
    require(inspected['scope']['runtime_activation_allowed'] is False
        and inspected['native_execution_or_physical_results_added_by_source_review'] is False,
        'A source-only audit cannot admit execution or physical evidence')
    return inspected


def inspect_map_research_wrapper(wrapper, previous_component):
    """Check additive evidence structure without granting runtime authority.

    Caller must authenticate the source/build/qualification artifact bytes
    independently. This function does not convert receipt assertions to tests.
    """
    require(type(wrapper) is dict and set(wrapper) == {'receipt', 'receipt_sha256'},
        'Exact additive native research wrapper required')
    receipt = wrapper['receipt']
    require(type(receipt) is dict and wrapper['receipt_sha256'] == canonical_sha(receipt),
        'Native research wrapper digest differs')
    require(receipt.get('format') == 1 and type(receipt.get('format')) is int
        and receipt.get('role') == 'nonshipping_map_metadata_research'
        and receipt.get('previous_component') == previous_component
        and receipt.get('previous_component_sha256') == canonical_sha(previous_component)
        and receipt.get('native_producer_relabelled') is False
        and receipt.get('shipping_allowed') is False
        and receipt.get('behavioral_collision_validated') is False
        and receipt.get('physical_timing_validated') is False,
        'Research evidence must preserve the original component and truthful nonshipping scope')
    require(receipt.get('mapserver') == MAP_CANDIDATE
        and receipt.get('build_repository_commit') == MAP_SOURCE
        and receipt.get('build_run_id') == MAP_BUILD_RUN
        and receipt.get('build_artifact') == MAP_BUILD_ARTIFACT,
        'Exact completed native candidate producer required')
    for name in ('build_manifest', 'native_fixture', 'paired_preload', 'native_world'):
        pin(receipt.get(name))
    return {'status': 'research_structure_checked_only', 'shipping_allowed': False,
        'runtime_admission_granted': False, 'mapserver': MAP_CANDIDATE,
        'receipt_sha256': wrapper['receipt_sha256'],
        'behavioral_collision_validated': False, 'physical_timing_validated': False}
