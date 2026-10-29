"""Additive reviewed MapServer startup consumer; original cache history stays exact."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
import native_monorail_contract as monorail

require = monorail.require
SOURCE = monorail.retained.SOURCE
DATA = monorail.retained.DATA
ROLE = 'native_map_startup_certified_animation'
PREVIOUS_SHA256 = '53ff6ee013690670abbaed39e44d66267caf8753486fbc05c64766a56d9c0713'
PREVIOUS_RECEIPT_SHA256 = 'e0ab383a91b83c258bfacbc44acf328f1a0c1435c0e4a385eb5ad643566f3178'
PACK_SHA256 = '465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'
TABLE_SHA256 = '179f8a15614dd42c9222be4d3716986bc9c0716a41d6045ef8f2ef7dc83427c4'
DEPENDENCY_SHA256 = '03236d08d8b33300cc27e614a25cbe37f6556ebe1c35132ab230a31170db33c9'
MANIFEST = 'map-startup-manifest.json'

def same(first, second):
    return json.dumps(first, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(second, sort_keys=True, separators=(',', ':'), allow_nan=False)

def compact_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def canonical_sha(value):
    return monorail.canonical_sha(value)

def file_pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Current MapServer must be a regular owned payload')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}

def pin_record(row):
    require(isinstance(row, dict) and type(row.get('bytes', row.get('size'))) is int
        and 0 < row.get('bytes', row.get('size')) <= 64*1024*1024
        and monorail.retained.HEX64.fullmatch(str(row.get('sha256'))), 'Map startup byte pin differs')
    return {'bytes': row.get('bytes', row.get('size')), 'sha256': row['sha256']}

ANIMATION_SOURCE_SHA256 = {'Common/seq/animtrack.c': 'a8f07b2a46d9a45640770707d5730ddc2f9f53cfbde3dd546f66ec9e89dfd50e'}

ANIMATION_PATCHED_SHA256 = {'Common/seq/animtrack.c': '37061a3801e6e943b2d2f34414ae0191045c0e08415761889253cd8c5a93ccd2'}

ANIMATION_OVERLAY_SHA256 = {'Common/seq/coh_animation_certificate.h': 'e099c3136045dff355ed4a334b0962badeb9ca39d89c942d410cce713c1e8c4b', 'Common/seq/coh_animation_certificate_table.h': '179f8a15614dd42c9222be4d3716986bc9c0716a41d6045ef8f2ef7dc83427c4'}

RETAINED_SOURCES_SHA256 = {'Common/fxinfo.c': '61f36247ec92e56395cc6548689c34b1e341283a25c78490627327eafd5e9a13', 'Common/seq/seqload.c': '8c2761ceeabcc564f89d943780579a4f401ffb344f9ad6e7f5e73660c2b9b60f', 'Common/seq/animtrackanimate.c': 'ad976409823db61d1610e3cece2ba323ffc7623af8be1c2c1ac8b38abdcebf21', 'libs/UtilitiesLib/src/utils/textparser.c': '22be253a9e48e2565086e051d469ff92e68c2ae5a84802d8dc3d90713c766fef', 'libs/UtilitiesLib/src/utils/file.c': '8ad08c34d2fed652578e26f0ec1fab79419b40414644c6b8e1ccbc58694733e1', 'libs/UtilitiesLib/src/utils/FolderCache.c': '93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c', 'libs/UtilitiesLib/src/utils/FolderCacheNode.c': '36faafa73afd83361fb8e4f25e340961fae5fb9d33c298b1200be9a4b2a48524', 'libs/UtilitiesLib/src/utils/piglib.c': '786ea2c5e9b8cf14fe4dfd4880b9cfe85a138afbccd56759e59b30b7663ed528', 'libs/UtilitiesLib/src/utils/PigFileWrapper.c': 'e4347a4694045a559c8db4d97d4dfc60748378d272e4365508ace3e2ef90909e'}

ANIMATION_CONTRACT = {'format': 1, 'policy': 'actual_opened_pig_raw_bytes_full_sha256_before_pointer_fixup', 'server_only': True, 'build_targets': ['MapServer'], 'certified_tracks': 5878, 'certificate_schema': 1, 'validator_version': 'original-win32-animation-loader-numeric-and-bounded-structure-v1', 'bounded_structure_and_offsets_always_checked': True, 'full_position_and_rotation_payloads_retained': True, 'base_skeleton_linking_retained': True, 'stock_key_validation_fallback': ['loose_input', 'unknown_name', 'changed_bytes', 'crypto_failure', 'header_only'], 'client_or_renderer_changes': False, 'environment_trust_switch': False, 'physical_startup_timing_validated': False}

def validate_animation_certificate(value):
    import server_animation_package as animation
    require(isinstance(value, dict) and type(value.get('format')) is int and value['format'] == 1
        and value.get('role') == 'server_raw_animation_certificate'
        and value.get('validator_version') == ANIMATION_CONTRACT['validator_version']
        and type(value.get('validated_track_count')) is int and value['validated_track_count'] == 5878
        and type(value.get('validated_raw_bytes')) is int and value['validated_raw_bytes'] == 88380730
        and value.get('rotation_key_count') == 11894088 and value.get('position_key_count') == 2083384
        and value.get('original_animation_pack') == {'animation_count': 5878, 'bytes': 97084456,
            'metadata_bytes': 8703726, 'original_animation_bytes': 88380730, 'sha256': PACK_SHA256}
        and value.get('generated_table') == {'bytes': 1363915, 'sha256': TABLE_SHA256}
        and hashlib.sha256((json.dumps(value.get('dependency_closure'), sort_keys=True,
            separators=(',', ':'), allow_nan=False) + '\n').encode()).hexdigest() == DEPENDENCY_SHA256
        and value.get('native_execution_validated') is False
        and value.get('physical_startup_timing_validated') is False,
        'Map startup original animation certification differs')
    require(same(value.get('original_animation_identity'), animation.identity()),
        'Map startup animation donor history changed')
    require(isinstance(value.get('validator_sources'), dict) and value['validator_sources'],
        'Map startup animation validator sources missing')
    return value

def previous_package(package):
    require(isinstance(package, dict) and isinstance(package.get('native_map_startup'), dict),
        'Missing additive Map startup receipt')
    previous = copy.deepcopy(package)
    wrapper = previous.pop('native_map_startup')
    previous['files']['MapServer.exe'] = copy.deepcopy(wrapper.get('receipt', {}).get('previous_mapserver'))
    return previous

def embedded_receipt(package):
    wrapper = package.get('native_map_startup', {})
    receipt = wrapper.get('receipt', {})
    require(isinstance(wrapper, dict) and set(wrapper) == {'receipt', 'receipt_sha256'}
        and isinstance(receipt, dict) and type(receipt.get('format')) is int and receipt['format'] == 1 and receipt.get('role') == ROLE
        and re.fullmatch(r'[0-9a-f]{40}', str(receipt.get('repository_commit')))
        and receipt.get('source_commit') == package.get('source_commit') == SOURCE
        and receipt.get('data_commit') == package.get('data_commit') == DATA
        and wrapper['receipt_sha256'] == canonical_sha(receipt), 'Map startup receipt identity differs')
    previous = previous_package(package)
    old = monorail.embedded_receipt(previous)
    require(previous['native_monorail']['receipt_sha256'] == PREVIOUS_RECEIPT_SHA256
        and old['mapserver']['sha256'] == PREVIOUS_SHA256 and pin_record(old['mapserver'])['bytes'] == 6892032
        and same(receipt.get('previous_mapserver'), old['mapserver']), 'Map startup changed the accepted station donor')
    build = receipt.get('build_input', {})
    certificate = validate_animation_certificate(build.get('animation_certificate'))
    budget = build.get('monorail_budget', {})
    require(type(budget.get('schema_version')) is int and budget['schema_version'] == 1 and budget.get('build_role') == 'map_startup_monorail_budget'
        and budget.get('source_sha256') == {'MapServer/src/svr/wine_monorail.c': '002957b67a841cb650c67412b7fcd3a159e02000a358c29c591d8049f23acf56'}
        and budget.get('patched_sha256') == {'MapServer/src/svr/wine_monorail.c': '3bd765cddc3975d2ca9c4f69f36b6cdd21ae0454068c33bd437a1fb3e21c57ad'}
        and budget.get('retained_sources_sha256') == {'MapServer/src/svr/wine_monorail.h': 'e4fef174151cf1595275039e5155213ce3d2f1673b377a0cd606d31b35f6fba9'}
        and same(budget.get('base_monorail_contract'), monorail.CONTRACT)
        and budget.get('base_monorail_contract_canonical_sha256') == compact_sha(monorail.CONTRACT)
        and same(budget.get('contract'), dict(monorail.CONTRACT, station_preparation_timeout_seconds=720))
        and budget.get('patch_scope') == 'one_exact_native_station_pending_timeout_literal_only'
        and budget.get('guest_absolute_cap_basis') == 'validated_native_request_utc_ms_plus_720000'
        and budget.get('expiry_comparison') == 'strictly_greater_than_720000_milliseconds'
        and budget.get('native_fixture_required') is True and budget.get('runtime_validation') == 'unverified'
        and budget.get('physical_startup_timing_validated') is False
        and build.get('monorail_budget_canonical_sha256') == compact_sha(budget),
        'Map startup native station budget source/clock differs')
    require(type(build.get('schema_version')) is int and build['schema_version'] == 1 and build.get('build_role') == 'map_startup_certified_animation'
        and build.get('source_commit') == SOURCE and build.get('build_targets') == ['MapServer']
        and build.get('runtime_validation') == 'unverified'
        and build.get('animation_certificate_canonical_sha256') == compact_sha(certificate)
        and build.get('source_sha256') == dict(ANIMATION_SOURCE_SHA256, **budget['source_sha256'])
        and build.get('patched_sha256') == dict(ANIMATION_PATCHED_SHA256, **budget['patched_sha256'])
        and build.get('overlay_sha256') == ANIMATION_OVERLAY_SHA256
        and build.get('retained_sources_sha256') == RETAINED_SOURCES_SHA256
        and same(build.get('contract'), dict(ANIMATION_CONTRACT,
            native_station_prepare_seconds=720, historical_station_prepare_seconds=600)), 'Map startup source scope or ABI differs')
    base = build.get('monorail_build_input', {})
    require(build.get('monorail_build_input_canonical_sha256') == compact_sha(base),
        'Map startup station source ancestry digest differs')
    # Preserve both LF/CRLF PG histories through the existing narrow ancestry
    # comparator; every monorail source and protocol field remains exact.
    a, b = copy.deepcopy(base), copy.deepcopy(old['build_input'])
    for item in (a, b): item.pop('events_build_input', None); item.pop('events_build_input_canonical_sha256', None)
    require(same(a, b), 'Map startup changed the retained station bridge sources')
    original = copy.deepcopy(previous); original.pop('native_monorail')
    original['files']['MapServer.exe'] = old['previous_mapserver']
    accepted = monorail.retained.embedded_receipt(original)
    comparison = copy.deepcopy(accepted['build_inputs'])
    comparison['character_events'] = base.get('events_build_input')
    monorail.retained.scene_source_inputs_equivalent(comparison, accepted['build_inputs'])
    current = monorail.retained.pe_record(receipt.get('mapserver'))
    require(package.get('files', {}).get('MapServer.exe') == current
        and current['sha256'] != PREVIOUS_SHA256
        and current.get('imports') == old['mapserver'].get('imports')
        and current.get('delay_imports') == old['mapserver'].get('delay_imports')
        and receipt.get('retained_native_files') == {n:r for n,r in package['files'].items() if n != 'MapServer.exe'}
        and len(receipt['retained_native_files']) == 24
        and receipt.get('schema_sources_sha256') == old['schema_sources_sha256'],
        'Map startup changed native dependencies or Parse6 schemas')
    require(re.fullmatch(r'[0-9a-f]{40}', str(receipt.get('native_build_repository_commit')))
        and pin_record(receipt.get('native_build_manifest'))
        and pin_record(receipt.get('native_fixture'))
        and pin_record(receipt.get('native_monorail_fixture'))
        and pin_record(receipt.get('fx_qualification'))
        and receipt.get('physical_timing_validated') is False
        and receipt.get('native_gameplay_validated') is False,
        'Map startup component provenance/scope missing')
    return receipt

def _current(path, package):
    metrics = None
    if 'armport_server_metrics' in package:
        import armport_server_metrics_contract as observer
        package, metrics = observer.verified_previous(path, package)
        require(metrics['variant'] == 'thor_certified_startup', 'Startup compatibility requires the modern metrics lineage')
    receipt = embedded_receipt(package)
    if metrics is None:
        require(file_pin(path) == pin_record(receipt['mapserver']), 'Current MapServer bytes differ from startup source receipt')
    return receipt, package, metrics

def current_receipt(path, package):
    """Authenticate the current PE before returning its retained startup recipe."""
    return _current(path, package)[0]

def verify_current_map(path, package):
    receipt, package, metrics = _current(path, package)
    result = {'format': 1, 'policy': 'qualified_startup_overlay_preserves_original_cache_and_graph_history',
        'actual_mapserver_sha256': receipt['mapserver']['sha256'],
        'previous_monorail_mapserver_sha256': PREVIOUS_SHA256,
        'original_cache_donor_mapserver_sha256': receipt['build_input']['animation_certificate']['original_animation_identity']['mapserver_sha256'],
        'cache_donor_identity_preserved': True, 'animation_identity_preserved': True,
        'native_animation_reader_changed': True, 'parser_or_definition_sources_changed': False,
        'native_build_repository_commit': receipt['native_build_repository_commit'],
        'native_build_manifest': receipt['native_build_manifest'],
        'native_map_startup_receipt_sha256': package['native_map_startup']['receipt_sha256'],
        'physical_loading_gain_validated': False}
    if metrics is not None:
        result.update(actual_mapserver_sha256=metrics['actual_mapserver_sha256'], armport_server_metrics=metrics)
    return result

def progress_contract(package):
    receipt = embedded_receipt(package)
    return {'contract': receipt['build_input']['monorail_build_input']['events_build_input']['progress_contract'],
        'producer': {'repository_commit': receipt['native_build_repository_commit'],
            'manifest_sha256': receipt['native_build_manifest']['sha256'],
            'mapserver_sha256': receipt['mapserver']['sha256']}}
