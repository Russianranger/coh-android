#!/usr/bin/env python3
"""Dormant additive Game/Map metadata contract with exact retained ancestry.

Unknown consumers fail before runtime activation. Inspection and cache bridge
results cannot authorize starting a new executable. Frozen artifact authorities
are populated only after independent producer and qualification recovery.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
import stat
from pathlib import Path
import re

FORMAT = 1
WRAPPER = 'native_startup_metadata'
ROLE = 'nonshipping_additive_native_metadata_component'
ACTIVATION_IMPLEMENTED = False
COMPONENT_AUTHORITIES = {'game': None, 'mapserver': None}
# Separate review of fresh native qualification is required for execution.
# These are intentionally absent while actual Game/Map lanes are unfinished.
REVIEWED_EXECUTION_AUTHORITIES = {'game': None, 'mapserver': None}
ATTEMPT_ENVIRONMENTS = {'game': 'COH_CLIENT_FOLDER_METADATA_SORT',
    'mapserver': 'COH_MAP_ANIMATION_METADATA_PREFETCH'}
# Process-local byte verification only. A new process must hash again; any
# inode/ctime/mtime/mode/link/owner change invalidates this bounded memo.
_CURRENT_EXECUTABLE_VERIFICATIONS = {}
COMPONENTS = {
    'game': {'executable': 'CityOfHeroes.exe', 'manifest': 'client-package.json',
        'base_manifest': {'bytes': 551823,
            'sha256': 'd01e74d53ff5e25a8efdc6d81e96bb0ec8d57ab48f7c8be585f313659b948062'}},
    'mapserver': {'executable': 'MapServer.exe', 'manifest': 'game-package.json',
        'base_manifest': {'bytes': 314572,
            'sha256': '188be5d84cd44a6ae0fda6c954c4f4a0b7e0f1e1ddf5633a45ffb5416b92930a'}},
}
MATERIAL_ROLES = ('producer', 'recovery', 'qualification')
TEXTURE_SOURCE_PATHS = frozenset({
    'Game/src/render/tex.c', 'Game/src/render/tex.h',
    'Common/gameComm/NPC.c', 'Common/gameData/costume_data.c', 'Common/seq/tricks.c',
    'Game/src/render/coh_texture_header_index.h', 'Game/src/render/coh_texture_header_root.h'})


def require(value, message):
    if not value: raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()).hexdigest()


def same(first, second):
    return canonical_sha(first) == canonical_sha(second)


def pin(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 8*1024**2, 'Bounded component receipt bytes required')
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pin_record(value, maximum=256*1024**2):
    require(type(value) is dict and set(value) == {'bytes', 'sha256'}
        and type(value['bytes']) is int and 0 < value['bytes'] <= maximum
        and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
        'Exact bounded content identity required')
    return value


def material_member_name(name):
    return (type(name) is str and 0 < len(name) <= 512 and '\\' not in name
        and not name.startswith('/') and 1 <= len(name.split('/')) <= 8
        and all(re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', part) and part not in ('.', '..')
            for part in name.split('/')))


def native_record_pin(row):
    require(type(row) is dict and set(row) in (
        {'bytes', 'sha256', 'pe_machine', 'imports', 'delay_imports'},
        {'size', 'sha256', 'pe_machine', 'imports', 'delay_imports'})
        and type(row.get('pe_machine')) is int and row['pe_machine'] == 332
        and all(type(row.get(key)) is list and all(type(name) is str for name in row[key])
            for key in ('imports', 'delay_imports')), 'Exact inherited native PE record required')
    return pin_record({'bytes': row.get('bytes', row.get('size')), 'sha256': row['sha256']}, 64*1024**2)


def unique_json(raw):
    pin(raw)
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'Duplicate native component JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))


def authority(kind):
    require(kind in COMPONENTS, 'Unsupported native metadata component')
    value = COMPONENT_AUTHORITIES.get(kind)
    require(type(value) is dict, 'Exact native producer/recovery/qualification authority is not frozen: '+kind)
    require(value.get('format') == FORMAT and type(value.get('format')) is int
        and value.get('kind') == kind and value.get('shipping_allowed') is False
        and value.get('runtime_activation_allowed') is False
        and set(value.get('materials', {})) == set(MATERIAL_ROLES),
        'Dormant native authority identity/scope differs')
    return copy.deepcopy(value)


def previous_package(package, kind):
    require(kind in COMPONENTS and type(package) is dict, 'Typed Game/Map package required')
    result = copy.deepcopy(package)
    wrapper = result.pop(WRAPPER, None)
    require(type(wrapper) is dict and set(wrapper) == {'receipt', 'receipt_sha256'},
        'Exact additive metadata wrapper required')
    receipt = wrapper['receipt']
    require(type(receipt) is dict and wrapper['receipt_sha256'] == canonical_sha(receipt)
        and receipt.get('kind') == kind and receipt.get('role') == ROLE
        and receipt.get('format') == FORMAT and type(receipt.get('format')) is int,
        'Native metadata wrapper identity differs')
    executable = COMPONENTS[kind]['executable']
    require(type(result.get('files')) is dict and executable in result['files'],
        'Native metadata executable is absent')
    result['files'][executable] = copy.deepcopy(receipt.get('previous_native_record'))
    require(pin(encoded(result)) == COMPONENTS[kind]['base_manifest']
        == receipt.get('previous_manifest'),
        'Old native manifest bytes/order/producer/schema ancestry changed')
    return result, receipt


def validate_package(package, kind):
    expected = authority(kind)
    previous, receipt = previous_package(package, kind)
    require(set(receipt) == {'format', 'role', 'kind', 'previous_manifest',
        'previous_native_record', 'native_record', 'authority_sha256', 'materials',
        'compatibility', 'scope'}, 'Unexpected additive component receipt field')
    require(receipt['authority_sha256'] == canonical_sha(expected)
        and same(receipt['materials'], expected['materials'])
        and same(receipt['compatibility'], expected['compatibility'])
        and same(receipt['native_record'], expected['native_record'])
        and same(package['files'][COMPONENTS[kind]['executable']], expected['native_record']),
        'Native component differs from frozen actual artifact authorities')
    require(same(receipt['scope'], {'shipping_allowed': False, 'runtime_activation_allowed': False,
        'behavioral_collision_validated': False, 'physical_timing_validated': False,
        'old_native_producer_relabelled': False}), 'Native initialization/research scope was promoted')
    old = previous['files'][COMPONENTS[kind]['executable']]
    current = expected['native_record']
    native_record_pin(current); native_record_pin(old)
    require(current != old and current.get('pe_machine') == old.get('pe_machine') == 332
        and current.get('imports') == old.get('imports')
        and current.get('delay_imports') == old.get('delay_imports'),
        'Native machine/import ABI changed')
    return {'format': FORMAT, 'kind': kind, 'previous_package': previous,
        'receipt': receipt, 'authority_sha256': canonical_sha(expected),
        'runtime_activation_allowed': False, 'shipping_allowed': False}


def verify_current_executable(path, package, kind):
    result = validate_package(package, kind)
    path = Path(path)
    require(path.is_absolute() and not any(part.is_symlink() for part in (path, *path.parents)),
        'Absolute nonlinked current native executable required')
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= 64*1024**2
        and before.st_uid == os.getuid(), 'Bounded owned current native executable required')
    fingerprint = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns,
        row.st_ctime_ns, row.st_mode, row.st_nlink, row.st_uid, row.st_gid)
    wanted = native_record_pin(result['receipt']['native_record'])
    key = (kind, str(path))
    if _CURRENT_EXECUTABLE_VERIFICATIONS.get(key) == (wanted, fingerprint(before)):
        require(fingerprint(path.lstat()) == fingerprint(before), 'Native consumer changed while rechecking its state')
        return dict(result, executable_validation='same_process_exact_unchanged_owned_inode')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
        require(identity(os.fstat(stream.fileno())) == identity(before), 'Native consumer changed before opening')
        raw = stream.read(64*1024**2+1)
        require(len(raw) == before.st_size and identity(os.fstat(stream.fileno())) == identity(before)
            and identity(path.lstat()) == identity(before), 'Native consumer changed while reading')
    row = result['receipt']['native_record']
    require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        == wanted and fingerprint(path.lstat()) == fingerprint(before), 'Actual native consumer bytes differ')
    if len(_CURRENT_EXECUTABLE_VERIFICATIONS) >= 16:
        _CURRENT_EXECUTABLE_VERIFICATIONS.clear()
    _CURRENT_EXECUTABLE_VERIFICATIONS[key] = (wanted, fingerprint(before))
    return dict(result, executable_validation='full_current_owned_native_byte_hash')


def runtime_admission(package, kind, path=None):
    """Require a source-frozen review bound to authenticated qualification bytes.

    The dormant component receipt remains an inspection record. Neither its
    initialization counters nor an old native producer can open this gate.
    Tests replace both closed tables with explicitly unexecuted fixtures.
    """
    require(ACTIVATION_IMPLEMENTED is True, 'Native metadata runtime integration is disabled')
    inspected = (verify_current_executable(path, package, kind) if path is not None
                 else validate_package(package, kind))
    review = REVIEWED_EXECUTION_AUTHORITIES.get(kind)
    require(type(review) is dict and set(review) == {'format', 'kind',
        'component_authority_sha256', 'qualification_artifact_zip',
        'qualification_receipts', 'qualified_maps', 'attempt_environment', 'scope'},
        'Fresh native execution review is not frozen: '+kind)
    expected = authority(kind)
    material = expected['materials']['qualification']
    require(type(review['format']) is int and review['format'] == FORMAT
        and review['kind'] == kind
        and review['component_authority_sha256'] == inspected['authority_sha256']
        and review['attempt_environment'] == ATTEMPT_ENVIRONMENTS[kind]
        and type(material) is dict and type(material.get('members')) is dict
        and type(material.get('required_receipt_values')) is dict
        and same(review['qualification_artifact_zip'], material.get('artifact_zip')),
        'Execution review differs from authenticated qualification artifact')
    pin_record(review['qualification_artifact_zip'])
    rows = review['qualification_receipts']
    require(type(rows) is dict and 0 < len(rows) <= 16,
        'Exact bounded native qualification receipt pins required')
    for name, row in rows.items():
        require(material_member_name(name)
            and type(row) is dict and set(row) == {'pin', 'required_values'}
            and same(row['pin'], material['members'].get(name))
            and same(row['required_values'], material['required_receipt_values'].get(name))
            and type(row['required_values']) is dict and row['required_values'],
            'Review must bind actual qualified receipt bytes and exact claims')
        pin_record(row['pin'], (64 if kind == 'mapserver' and name == 'native-map-world-037-qualification.json' else 8)*1024**2)
    require(same(review['scope'], {'old_native_producer_relabelled': False,
        'behavioral_collision_validated': False, 'physical_timing_validated': False}),
        'Execution review must retain historical and physical qualification limits')
    maps = review['qualified_maps']
    require((kind == 'game' and maps == []) or (kind == 'mapserver'
        and type(maps) is list and maps and all(type(item) is int and item in (1, 5) for item in maps)
        and len(maps) == len(set(maps))), 'Exact supported native world qualification required')
    return {**inspected, 'runtime_activation_allowed': True,
        'execution_review_sha256': canonical_sha(review),
        'current_consumer_sha256': inspected['receipt']['native_record']['sha256'],
        'previous_consumer_sha256': inspected['receipt']['previous_native_record']['sha256'],
        'qualified_maps': copy.deepcopy(maps),
        'native_producer': copy.deepcopy(expected['materials']['producer']), 'physical_timing_validated': False,
        'behavioral_collision_validated': False}


def legacy_package(package, kind):
    """Inspect historical protocols with the exact restored manifest only."""
    return (runtime_admission(package, kind)['previous_package']
            if type(package) is dict and WRAPPER in package else package)


def apply_attempt_environment(package, kind, path, environment, *, map_id=None):
    """Remove inherited opt-ins and enable one verified owned native attempt."""
    require(kind in COMPONENTS and type(environment) is dict, 'Native attempt environment required')
    for name in ATTEMPT_ENVIRONMENTS.values(): environment.pop(name, None)
    if type(package) is not dict or WRAPPER not in package:
        return None
    result = runtime_admission(package, kind, path)
    if kind == 'mapserver':
        require(type(map_id) is int and map_id in result['qualified_maps'],
            'Selected map lacks fresh native metadata world qualification')
    else:
        require(map_id is None, 'Game metadata attempt cannot claim a map qualification')
    environment[ATTEMPT_ENVIRONMENTS[kind]] = '1'
    return {key: result[key] for key in ('authority_sha256', 'execution_review_sha256',
        'current_consumer_sha256', 'previous_consumer_sha256', 'runtime_activation_allowed',
        'physical_timing_validated', 'behavioral_collision_validated')}


def scrub_attempt_environment(environment):
    """Copy prerequisites/query inputs without any live native opt-in."""
    require(type(environment) is dict, 'Explicit prerequisite/query environment required')
    result = dict(environment)
    for name in ATTEMPT_ENVIRONMENTS.values(): result.pop(name, None)
    return result


def cache_compatibility(package, kind, *, previous_consumer_sha256,
        provider_identity_sha256, bin_recipe_identity_sha256, original_proof_sha256):
    """Authorize only an exact immutable provider/recipe proof named by artifacts.

    An old consumer hash alone grants no compatibility. Unknown or unmatched
    cache inputs fail and must use fresh full validation under current ownership.
    """
    value = validate_package(package, kind)
    bridge = value['receipt']['compatibility'].get('cache')
    require(type(bridge) is dict and bridge.get('policy') == 'exact_provider_recipe_and_native_consumer_parity',
        'No authenticated old-cache compatibility is available')
    actual = {'previous_consumer_sha256': previous_consumer_sha256,
        'current_consumer_sha256': value['receipt']['native_record']['sha256'],
        'provider_identity_sha256': provider_identity_sha256,
        'bin_recipe_identity_sha256': bin_recipe_identity_sha256,
        'original_proof_sha256': original_proof_sha256}
    require(all(type(item) is str and re.fullmatch('[0-9a-f]{64}', item) for item in actual.values())
        and previous_consumer_sha256 == value['receipt']['previous_native_record']['sha256']
        and bridge.get('previous_consumer_sha256') == value['receipt']['previous_native_record']['sha256']
        and all(bridge.get(key) == item for key, item in actual.items())
        and type(bridge.get('qualified_per_bin')) is dict and bridge['qualified_per_bin'],
        'Old cache proof/provider/recipe/current consumer mismatch')
    rows = bridge['qualified_per_bin']
    require(len(rows) <= 512 and all(type(name) is str for name in rows)
        and len({name.casefold() for name in rows}) == len(rows),
        'Bounded unaliased per-BIN compatibility inventory required')
    eligible = bridge.get('eligible_bin_paths')
    require(type(eligible) is list and eligible == sorted(rows)
        and all(type(name) is str for name in eligible),
        'Exact authenticated eligible BIN path inventory required')
    logical = [('data/'+name if name.startswith('bin/') else name).casefold() for name in eligible]
    require(len(set(logical)) == len(logical), 'Aliased logical BIN directory paths refused')
    for name, proof in rows.items():
        require(type(name) is str and re.fullmatch(r'(?:bin|data/bin|data/server/bin)/[A-Za-z0-9_-]+\.bin', name)
            and type(proof) is dict and set(proof) == {'schema_identity_sha256', 'output_sha256',
                'identifier_inputs_sha256', 'loader_decisions_sha256'}
            and all(type(item) is str and re.fullmatch('[0-9a-f]{64}', item) for item in proof.values()),
            'Exact safe per-BIN schema/content/identifier-input/decision proof required')
    return {'status': 'exact_authenticated_cache_compatibility_inspected', **actual,
        'qualified_per_bin': copy.deepcopy(bridge['qualified_per_bin']),
        'runtime_activation_allowed': False}


def map_texture_projection(package):
    value = validate_package(package, 'mapserver')
    proof = value['receipt']['compatibility'].get('server_texture_projection')
    require(type(proof) is dict and set(proof) == {'policy', 'native_consumer_sha256',
        'native_source_path', 'native_source_sha256', 'retained_texture_exclusion_source_sha256',
        'excluded_top_level_directories', 'client_inputs_modified'}
        and proof.get('policy') == 'exact_source_bound_native_excluded_texture_directory_v2'
        and proof.get('native_consumer_sha256') == value['receipt']['native_record']['sha256']
        and proof.get('native_source_path') == 'MapServer/src/svr/svr_init.c'
        and proof.get('native_source_sha256') == '398081161ebe9e9253b326e8a5f94f502a7bc0a9974a442f1ce83a46ee0f9ae3'
        and proof.get('retained_texture_exclusion_source_sha256') == '2048c22f8380931514cefb429790552295e52dd72e03617973820936e116639d'
        and proof.get('excluded_top_level_directories') == ['texture_library']
        and proof.get('client_inputs_modified') is False,
        'New Map consumer has no explicit authenticated texture exclusion proof')
    return copy.deepcopy(proof)


def game_texture_index_migration(package, previous_client_identity, content_identity_sha256):
    require(type(previous_client_identity) is dict
        and set(previous_client_identity) == {'content_identity_sha256', 'data_contract'}
        and type(content_identity_sha256) is str and re.fullmatch('[0-9a-f]{64}', content_identity_sha256),
        'Exact previous/current client input identities required')
    value = validate_package(package, 'game')
    expected = authority('game')
    source = expected.get('source_compatibility', {})
    require(type(source) is dict and set(source) == {
        'previous_texture_source_pins', 'current_texture_source_pins'},
        'Independently frozen old/new texture source closures required')
    old_sources, current_sources = source['previous_texture_source_pins'], source['current_texture_source_pins']
    require(type(old_sources) is dict and type(current_sources) is dict
        and set(old_sources) == TEXTURE_SOURCE_PATHS and set(current_sources) == TEXTURE_SOURCE_PATHS
        and same(old_sources, current_sources),
        'Exact unchanged texture reader/header/schema/root source closure required')
    for source_pin in (*old_sources.values(), *current_sources.values()):
        pin_record(source_pin, 2*1024**2)
    bridge = value['receipt']['compatibility'].get('texture_header_index')
    bridge_sources = bridge.get('unchanged_texture_source_pins') if type(bridge) is dict else None
    require(type(bridge_sources) is dict and set(bridge_sources) == TEXTURE_SOURCE_PATHS,
        'Exact typed bridge texture source closure required')
    for source_pin in bridge_sources.values(): pin_record(source_pin, 2*1024**2)
    same_inputs = False
    if bridge.get('policy') == 'exact_verified_input_recipe_and_unchanged_texture_schema':
        # Generation IDs and private paths vary by installed application. Bind
        # the immutable recipe, then derive BOTH identities from this exact
        # already-verified data contract and the restored/current native files.
        # No prior marker's claimed consumer or content SHA supplies authority.
        data = previous_client_identity['data_contract']
        require(type(data) is dict and set(data) == {'format', 'source_data', 'import',
            'cache_archive_sha256', 'prerequisites_archive_sha256',
            'prerequisites_manifest_sha256', 'normalized_mtime_epoch'}
            and type(data['format']) is int and data['format'] == 1
            and type(data['source_data']) is str and 0 < len(data['source_data']) <= 4096
            and Path(data['source_data']).is_absolute() and '..' not in Path(data['source_data']).parts,
            'Exact verified private client data contract required')
        imported = data['import']
        require(type(imported) is dict and set(imported) == {'generation', 'receipt_sha256',
            'contract_sha256', 'file_count', 'total_bytes'}
            and type(imported['generation']) is str and re.fullmatch('generation-[0-9a-f]{32}', imported['generation'])
            and all(type(imported[key]) is str and re.fullmatch('[0-9a-f]{64}', imported[key])
                for key in ('receipt_sha256', 'contract_sha256'))
            and type(imported['file_count']) is int and imported['file_count'] == 173011
            and type(imported['total_bytes']) is int and imported['total_bytes'] == 2977730517
            and type(data['normalized_mtime_epoch']) is int,
            'Exact retained Assets 1.0.0 import identity required')
        recipe = {key: data[key] for key in ('cache_archive_sha256',
            'prerequisites_archive_sha256', 'prerequisites_manifest_sha256', 'normalized_mtime_epoch')}
        recipe.update(import_contract_sha256=imported['contract_sha256'],
            imported_file_count=imported['file_count'], imported_total_bytes=imported['total_bytes'])
        require(all(type(recipe[key]) is str and re.fullmatch('[0-9a-f]{64}', recipe[key])
            for key in ('cache_archive_sha256', 'prerequisites_archive_sha256',
                'prerequisites_manifest_sha256', 'import_contract_sha256'))
            and same(bridge.get('immutable_input_recipe'), recipe),
            'Current immutable texture input recipe differs from native compatibility qualification')
        def identity(native_package):
            closure = {key: native_package[key] for key in ('source_commit', 'data_commit', 'files')}
            return canonical_sha({'data': data, 'native': closure})
        same_inputs = (previous_client_identity['content_identity_sha256'] == identity(value['previous_package'])
            and content_identity_sha256 == identity(package))
    elif bridge.get('policy') == 'exact_unchanged_texture_schema_and_inputs':
        same_inputs = (bridge.get('content_identity_sha256') == content_identity_sha256
            and bridge.get('previous_content_identity_sha256') == previous_client_identity.get('content_identity_sha256')
            and same(bridge.get('data_contract'), previous_client_identity['data_contract']))
    require(type(bridge) is dict and same_inputs
        and type(bridge.get('texture_header_struct_bytes')) is int
        and bridge.get('texture_header_struct_bytes') == 32
        and bridge.get('previous_executable_sha256') == value['receipt']['previous_native_record']['sha256']
        and bridge.get('client_executable_sha256') == value['receipt']['native_record']['sha256']
        and type(previous_client_identity) is dict
        and set(previous_client_identity) == {'content_identity_sha256', 'data_contract'}
        and same(bridge_sources, old_sources),
        'No exact authenticated Game texture-header migration is available')
    return {'format': FORMAT, 'policy': 'verified_native_metadata_texture_layer_v1',
        'previous_client_identity': copy.deepcopy(previous_client_identity),
        'previous_executable_sha256': bridge['previous_executable_sha256'],
        'client_executable_sha256': bridge['client_executable_sha256'],
        'content_identity_sha256': content_identity_sha256,
        'layer_manifest_sha256': canonical_sha(value['receipt']),
        'texture_header_struct_bytes': 32, 'native_source_closure_verified': True,
        'runtime_activation_allowed': False}
