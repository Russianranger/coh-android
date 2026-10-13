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
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
        require(identity(os.fstat(stream.fileno())) == identity(before), 'Native consumer changed before opening')
        raw = stream.read(64*1024**2+1)
        require(len(raw) == before.st_size and identity(os.fstat(stream.fileno())) == identity(before)
            and identity(path.lstat()) == identity(before), 'Native consumer changed while reading')
    row = result['receipt']['native_record']
    require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        == native_record_pin(row), 'Actual native consumer bytes differ')
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
    require(len(rows) <= 128 and all(type(name) is str for name in rows)
        and len({name.casefold() for name in rows}) == len(rows),
        'Bounded unaliased per-BIN compatibility inventory required')
    for name, proof in rows.items():
        require(type(name) is str and re.fullmatch(r'bin/[A-Za-z0-9_-]+\.bin', name)
            and type(proof) is dict and set(proof) == {'schema_identity_sha256', 'output_sha256',
                'native_ids_sha256', 'loader_decisions_sha256'}
            and all(type(item) is str and re.fullmatch('[0-9a-f]{64}', item) for item in proof.values()),
            'Exact safe per-BIN schema/content/native-ID/decision proof required')
    return {'status': 'exact_authenticated_cache_compatibility_inspected', **actual,
        'qualified_per_bin': copy.deepcopy(bridge['qualified_per_bin']),
        'runtime_activation_allowed': False}


def map_texture_projection(package):
    value = validate_package(package, 'mapserver')
    proof = value['receipt']['compatibility'].get('server_texture_projection')
    require(type(proof) is dict and proof.get('policy') == 'exact_native_excluded_texture_directory_v1'
        and proof.get('native_consumer_sha256') == value['receipt']['native_record']['sha256']
        and proof.get('native_source_path') == 'MapServer/src/svr/svr_init.c'
        and proof.get('native_source_sha256') == '2048c22f8380931514cefb429790552295e52dd72e03617973820936e116639d'
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
    require(type(bridge) is dict and bridge.get('policy') == 'exact_unchanged_texture_schema_and_inputs'
        and type(bridge.get('texture_header_struct_bytes')) is int
        and bridge.get('texture_header_struct_bytes') == 32
        and bridge.get('previous_executable_sha256') == value['receipt']['previous_native_record']['sha256']
        and bridge.get('client_executable_sha256') == value['receipt']['native_record']['sha256']
        and bridge.get('content_identity_sha256') == content_identity_sha256
        and bridge.get('previous_content_identity_sha256') == previous_client_identity.get('content_identity_sha256')
        and type(previous_client_identity) is dict
        and set(previous_client_identity) == {'content_identity_sha256', 'data_contract'}
        and same(bridge.get('data_contract'), previous_client_identity['data_contract'])
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
