#!/usr/bin/env python3
"""Derive a bounded cache compatibility summary from immutable native evidence.

This does not run native programs, admit a consumer or authorize publication.
Raw artifacts retain their original producers. The separately derived output
is source-bound and must receive its own review before runtime authority exists.
"""
from __future__ import annotations
import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import re
import struct
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(ROOT/'tools')]
import native_startup_metadata_contract as metadata
import native_map_startup_contract as startup
import native_startup_component_migration as migration

INPUTS = ('preload', 'native_world', 'client_cache_manifest', 'server_cache_manifest')
DERIVATION_SCOPE = {'derived_by_source_reviewed_normalizer': True,
    'original_artifact_membership_claimed': False, 'native_ID_tables_observed': False,
    'shipping_bytes_executed_claimed': False, 'behavioral_collision_validated': False,
    'physical_timing_validated': False}
SCRIPT = 'tools/android/interactive/derive_native_metadata_cache_proof.py'
OUTPUT_NAME = 'native-metadata-cache-derived-proof.json'
MAX_JSON = 8*1024**2
HEX64 = re.compile('[0-9a-f]{64}')
BIN = re.compile(r'data/(?:bin|server/bin)/[A-Za-z0-9_-]+\.bin')
WORLDS = {1: ('City_01_01', 7001, 2311), 5: ('City_01_02', 7003, 2166)}
PLAN = [('server_only', 'generation', 'stock'),
    ('server_only', 'baseline-forward', 'baseline'),
    ('server_only', 'candidate-forward', 'candidate'),
    ('server_only', 'candidate-reverse', 'candidate'),
    ('server_only', 'baseline-reverse', 'baseline'),
    ('full', 'generation', 'stock'), ('full', 'baseline-forward', 'baseline'),
    ('full', 'candidate-forward', 'candidate')]


def require(value, message):
    if not value: raise ValueError(message)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def json_document(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_JSON, 'Bounded native evidence JSON required')
    return metadata.unique_json(raw)


def input_descriptor(value, role):
    require(type(value) is dict and metadata.material_member_name(value.get('member')),
        'Exact safe raw evidence member required')
    metadata.pin_record(value.get('member_pin'), MAX_JSON)
    if role in ('preload', 'native_world'):
        require(set(value) == {'repository_commit', 'run_id', 'artifact_id', 'artifact_zip', 'member', 'member_pin'}
            and type(value['repository_commit']) is str and re.fullmatch('[0-9a-f]{40}', value['repository_commit'])
            and all(type(value[key]) is int and value[key] > 0 for key in ('run_id', 'artifact_id')),
            'Original native report producer identity required')
        metadata.pin_record(value['artifact_zip'], migration.MAXIMUM_ARCHIVE)
    else:
        require(set(value) == {'component_zip', 'member', 'member_pin', 'origin'}
            and value['origin'] == 'exact_public_Assets_1_0_0_component'
            and value['member'] == ('client-cache-manifest.json' if role == 'client_cache_manifest'
                else 'server-cache-manifest.json'), 'Exact original donor component origin required')
        metadata.pin_record(value['component_zip'], migration.MAXIMUM_ARCHIVE)
    return copy.deepcopy(value)


class _AuthenticatedInputs(dict):
    """Invocation-local witness; original compact/pretty JSON bytes stay exact."""
    def __init__(self, documents, descriptors):
        super().__init__(documents)
        self.original_descriptors = copy.deepcopy(descriptors)
        self.document_hashes = {role: metadata.canonical_sha(document)
            for role, document in documents.items()}


def authenticate_inputs(paths, descriptors):
    """Read each original ZIP once; no member is rewritten or inserted."""
    require(type(paths) is dict and type(descriptors) is dict
        and set(paths) == set(descriptors) == set(INPUTS), 'Four explicit raw evidence inputs required')
    result = {}
    for role in INPUTS:
        value = input_descriptor(descriptors[role], role)
        raw = migration.read_regular(Path(paths[role]).absolute())
        require(pin(raw) == value.get('artifact_zip', value.get('component_zip')),
            'Actual original '+role+' whole ZIP differs')
        # Component archives may contain >64MiB cache bodies. They are already
        # pinned whole; only their small original manifest is decompressed here.
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            rows = archive.infolist(); names = [row.filename for row in rows]
            require(0 < len(rows) <= 512 and len(set(names)) == len(names)
                and len({name.casefold() for name in names}) == len(names)
                and all(metadata.material_member_name(name) for name in names), 'Unsafe raw evidence archive inventory')
            info = archive.getinfo(value['member'])
            require(not info.is_dir() and not info.flag_bits & 1
                and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                and info.file_size == value['member_pin']['bytes'],
                'Original native evidence member extent differs')
            body = archive.read(info)
        require(pin(body) == value['member_pin'], 'Actual original '+role+' member differs')
        result[role] = json_document(body)
        if role in ('preload', 'native_world'):
            require(result[role].get('repository_commit') == value['repository_commit'], 'Raw report source differs')
    return _AuthenticatedInputs(result, descriptors)


def cache_rows(value):
    require(type(value) is dict and 0 < len(value) <= 4096
        and all(type(name) is str and (BIN.fullmatch(name)
            or (name.startswith(('data/geobin/object_library/', 'data/geobin/maps/'))
                and name.endswith('.bin'))
            or (name.startswith('data/geobin/object_library/') and name.endswith('.bounds')))
            and name.isascii() and not re.search(r'[\x00-\x1f\\:*?<>|]', name)
            and all(part not in ('', '.', '..') and not part.endswith((' ', '.')) for part in name.split('/'))
            for name in value), 'Bounded exact native BIN/GroupBounds inventory required')
    require(len({name.casefold() for name in value}) == len(value), 'Aliased native BIN names refused')
    for row in value.values(): metadata.pin_record(row, 256*1024**2)
    return value


def identifier_inputs(value):
    require(type(value) is dict and 0 < len(value) <= 64, 'Bounded identifier input-file inventory required')
    result = {}
    for name, row in value.items():
        require(type(name) is str and (re.fullmatch(r'data/defs/[A-Za-z0-9_./-]+\.dbidmap', name)
            or re.fullmatch(r'data/server/db/templates/[A-Za-z0-9_-]+\.attribute', name))
            and '..' not in name.split('/') and type(row) is dict, 'Exact identifier input path required')
        result[name] = metadata.pin_record({key: row[key] for key in ('bytes', 'sha256')}, MAX_JSON)
    return result


def observations(value):
    require(type(value) is dict and value.get('native_decoder_executed') is True
        and value.get('freshness_bypass_enabled') is False, 'Actual ordinary native decoder observations required')
    profile, freshness = value.get('profile_rows'), value.get('freshness_rows')
    require(type(profile) is list and 0 < len(profile) <= 512
        and type(freshness) is list and 0 < len(freshness) <= 256, 'Bounded ordered native observation prefix required')
    decoded = []
    for row in profile:
        require(type(row) is dict and row.get('phase') in ('bin_decode', 'sequencer_postprocess', 'sequencer_finalize', 'sequencer_total')
            and type(row.get('input_token')) is str and re.fullmatch('[0-9a-f]{8}', row['input_token'])
            and type(row.get('success')) is bool, 'Exact native profile token/status required')
        decoded.append([row['phase'], row['input_token'], row['success']])
    checked = []
    for index, row in enumerate(freshness, 1):
        require(type(row) is dict and type(row.get('ordinal')) is int and row['ordinal'] == index
            and type(row.get('input_token')) is str and re.fullmatch('[0-9a-f]{8}', row['input_token'])
            and row.get('clock_valid') == '1'
            and row.get('outcome') in ('open_rejected', 'freshness_rejected', 'freshness_accepted'),
            'Exact ordered native freshness prefix required')
        checked.append([row['input_token'], row['outcome']])
    return {'profile': decoded, 'freshness': checked}


def diagnostic_token(name):
    require(type(name) is str and name.isascii(), 'ASCII native diagnostic input name required')
    value = 2166136261
    for byte in name.encode()[:512]: value = ((value ^ byte)*16777619) & 0xffffffff
    return f'{value:08x}'


def observed_names(decisions, inventory):
    """Unique diagnostic mapping only; the 32-bit token is no integrity proof."""
    lookup = {}
    for name in inventory:
        if not BIN.fullmatch(name): continue
        for spelling in {name[5:], name[5:].lower()}:
            lookup.setdefault(diagnostic_token(spelling), set()).add(name)
    result, excluded = set(), []
    for phase, token, success in decisions['profile']:
        if phase != 'bin_decode' or success is not True: continue
        matches = lookup.get(token, set())
        if len(matches) == 1: result.update(matches)
        else: excluded.append({'token': token, 'reason': 'unmapped_or_ambiguous_diagnostic_name'})
    return result, excluded


def donor_rows(manifests):
    result = {}
    for role, archive in (('client_cache_manifest', 'client-caches.zip'), ('server_cache_manifest', 'server-caches.zip')):
        document = manifests[role]; files = document.get('files')
        require(type(document.get('format')) is int and document['format'] == 1 and type(files) is dict
            and 0 < len(files) <= 512, 'Original bounded donor manifest required')
        for name, row in files.items():
            if not BIN.fullmatch(name): continue
            require(type(row) is dict, 'Exact original donor record required')
            # The client donor also contains two server-side leaves. The
            # authoritative server manifest owns those exact directory names;
            # never create two logical origins for the same private BIN.
            if not name.startswith('data/bin/' if role == 'client_cache_manifest' else 'data/server/bin/'):
                continue
            # This narrow native observation lane records Parse6 decoders.
            # MessageStore caches retain their own ordinary consumer rules.
            if row.get('kind', 'Parse6') != 'Parse6': continue
            require(name not in result and type(row) is dict, 'Aliased donor BIN origin refused')
            metadata.pin_record({key: row[key] for key in ('bytes', 'sha256')}, 256*1024**2)
            schema = row.get('schema_crc') if archive == 'client-caches.zip' else row.get('structure', {}).get('schema_crc')
            require(type(schema) is str and re.fullmatch('[0-9a-f]{8}', schema), 'Exact original Parse6 schema CRC required')
            result[name] = {'archive': archive, 'member': name, 'record': row,
                'schema_identity_sha256': metadata.canonical_sha({'kind': row.get('kind', 'Parse6'), 'original_manifest_record': row})}
    require(len({name.casefold() for name in result}) == len(result), 'Aliased original donor names refused')
    return result


def inspect_preload(preload, manifests):
    require(type(preload) is dict and type(preload.get('format')) is int and preload['format'] == 1
        and preload.get('role') == 'nonshipping_map_metadata_prefetch_Wine_preload_parity'
        and preload.get('status') == 'passed' and preload.get('actual_Wine_native_preload_executed') is True
        and preload.get('physical_device_executed') is False and preload.get('player_database_used') is False
        and preload.get('publication_allowed') is False, 'Successful actual nonshipping preload report required')
    records = preload.get('records'); require(type(records) is dict and set(records) == {'control', 'profile'}, 'Exact paired preload records required')
    inventories, natives, ids = {}, {}, {}
    for lane, record in records.items():
        natives[lane] = metadata.pin_record(record['actual_native'], 64*1024**2)
        before, after = cache_rows(record['cache_before']), cache_rows(record['cache_after'])
        require(metadata.same(before, after) and metadata.same(record.get('cache_delta'), {'added': {}, 'changed': {}, 'removed': {}})
            and record.get('phase', {}).get('completed_preload') is True
            and record['phase'].get('timed_out') is False
            and metadata.same(record.get('full_provider_before'), record.get('full_provider_after')),
            'Preload native cache/provider or completed phase changed')
        ids[lane] = identifier_inputs(record['identifiers_before'])
        require(metadata.same(ids[lane], identifier_inputs(record['identifiers_after'])), 'Preload identifier inputs changed')
        inventories[lane] = after
    require(metadata.same(inventories['control'], inventories['profile']) and metadata.same(ids['control'], ids['profile']), 'Paired native cache/identifier input parity differs')
    decisions = observations(preload['observations'])
    require(metadata.same(decisions, observations(preload['control_observations'])), 'Ordered native decode/freshness decisions differ')
    consumed, unknown = observed_names(decisions, inventories['profile']); originals = donor_rows(manifests)
    eligible, excluded = {}, []
    for name in sorted(consumed):
        origin = originals.get(name)
        if origin is None: excluded.append({'name': name, 'reason': 'not_an_original_donor_BIN'}); continue
        wanted = {key: origin['record'][key] for key in ('bytes', 'sha256')}
        if not metadata.same(inventories['profile'][name], wanted):
            excluded.append({'name': name, 'reason': 'original_donor_output_changed'}); continue
        eligible[name] = origin
    require(eligible, 'No successfully decoded unchanged original donor BINs')
    return {'eligible': eligible, 'actual_tested_control': natives['control'], 'actual_tested_candidate': natives['profile'],
        'identifier_inputs': ids['profile'], 'decisions': decisions, 'excluded': excluded+unknown,
        'inventory_only_count': len(inventories['profile']), 'successfully_observed_unique_names': len(consumed)}


def world_progress(row):
    require(type(row) is dict and type(row.get('raw_record_hex')) is str and re.fullmatch('[0-9a-f]{256}', row['raw_record_hex']), 'Actual bounded Map progress bytes required')
    raw = bytes.fromhex(row['raw_record_hex'])
    require(hashlib.sha256(raw).hexdigest() == row.get('raw_record_sha256') and raw[:8] == b'COHMAP1\0', 'Map progress byte identity differs')
    values = struct.unpack_from('<6I', raw, 16)
    for field, value in zip(('windows_pid', 'main_thread_id', 'sequence', '_stage', 'tick_started', 'tick_completed'), values):
        if field == '_stage': continue
        require(type(row.get(field)) is int and row[field] == value, 'Decoded actual Map progress differs')
    return row


def inspect_world(world, narrow, expected_sdk=None):
    require(type(world) is dict and type(world.get('format')) is int and world['format'] == 1 and world.get('status') == 'passed'
        and world.get('actual_native_worlds_executed') == [1, 5] and type(world.get('actual_native_processes')) is int
        and world['actual_native_processes'] == 16 and world.get('failures') == []
        and world.get('actual_full_and_SERVER_only_FX_world_consumers_verified') is True
        and world.get('owned_cleanup_verified') is True and world.get('memory_measured') is True
        and world.get('player_profile_opened') is False and world.get('physical_device_executed') is False
        and world.get('behavioral_collision_proven') is False and world.get('shipping_allowed') is False
        and world.get('freshness_bypass_enabled') is False, 'Complete genuine16-case native world gate required')
    cases = world.get('cases'); require(type(cases) is list and len(cases) == 16, 'Exact native world case matrix required')
    expected = {(map_id, *phase) for map_id, phase in itertools.product(WORLDS, PLAN)}
    seen, observed, excluded, warm_groups, generated, all_pins = set(), set(), [], {}, {}, []
    stock = None
    for case in cases:
        key = (case.get('map_id'), case.get('fx_variant'), case.get('phase'), case.get('role'))
        require(type(key[0]) is int and key in expected and key not in seen, 'Missing/duplicate/unknown native world case')
        seen.add(key); name, port, objects = WORLDS[key[0]]
        native = metadata.pin_record(case['actual_native'], 64*1024**2)
        if expected_sdk is not None:
            require(type(expected_sdk) is dict and len(expected_sdk) == 7,
                'Exact source-reviewed SDK/cooking closure required')
            for provider in (case['provider_before'], case['provider_after']):
                components = provider.get('native_components')
                require(type(components) is dict and provider.get('full_content_hashed') is True,
                    'Actual hashed native world component inventory required')
                for filename, wanted in expected_sdk.items():
                    actual = components.get(filename)
                    require(type(actual) is dict and metadata.same(
                        {field: actual.get(field) for field in ('bytes', 'sha256')}, wanted),
                        'Actual native world SDK/cooking DLL differs: '+filename)
        if key[3] == 'stock':
            if stock is None: stock = native
            require(metadata.same(native, stock), 'Actual stock generation native differs')
        else:
            require(metadata.same(native, narrow['actual_tested_candidate'] if key[3] == 'candidate' else narrow['actual_tested_control']), 'World case actual native identity differs')
        markers, status = case.get('world_markers', {}), case.get('native_Db_status', {})
        require(type(markers.get('map_id')) is int and markers['map_id'] == key[0]
            and markers.get('world') == name and type(markers.get('udp_port')) is int and markers['udp_port'] == port
            and type(markers.get('PhysX_objects')) is int and markers['PhysX_objects'] == objects
            and markers.get('ordered_world_phases') is True and markers.get('UDP_loopback_endpoint_verified') is True
            and markers.get('behavioral_collision_proven') is False and type(status.get('map_id')) is int
            and status['map_id'] == key[0] and status.get('world') == name and status.get('address') == '127.0.0.1'
            and type(status.get('port')) is int and status['port'] == port,
            'Selected native world/port/physics/status observations differ')
        before, after = world_progress(case['Map_progress_before_status']), world_progress(case['Map_progress_after_status'])
        require(before['windows_pid'] > 0 and before['windows_pid'] == after['windows_pid']
            and before['main_thread_id'] == after['main_thread_id'] and after['sequence'] > before['sequence']
            and after['tick_completed'] > before['tick_completed'] and after['tick_started'] >= after['tick_completed'],
            'Held native Map did not independently advance after Db status')
        memory = case.get('memory', {}); samples = memory.get('samples')
        require(type(samples) is list and 0 < len(samples) <= 128 and type(memory.get('sample_count')) is int
            and memory['sample_count'] >= len(samples) and memory.get('Thor_measured') is False
            and case.get('owned_cleanup_verified') is True and case.get('synthetic_row_unchanged') is True,
            'Actual bounded memory or owned fixture cleanup missing')
        for row in samples:
            require(type(row) is dict and all(type(row.get(field)) is int and 0 <= row[field] < 2**64
                for field in ('working_set_bytes', 'private_commit_bytes', 'lifetime_peak_working_set_bytes', 'lifetime_peak_commit_bytes')), 'Bounded actual native memory values required')
        if key[3] == 'stock':
            # Geometry BINs and stock GroupBounds belong to the whole world
            # producer/consumer parity closure, never the original seed list.
            generated[key[:2]] = cache_rows(case['cache_after'])
            continue
        caches_before, caches_after = cache_rows(case['cache_before']), cache_rows(case['cache_after'])
        require(metadata.same(caches_before, caches_after) and metadata.same(case.get('cache_delta'), {'added': {}, 'changed': {}, 'removed': {}}), 'Warm native world changed generated BINs')
        require(key[:2] in generated and metadata.same(caches_after, generated[key[:2]]),
            'Warm native world lost or changed stock BIN/GroupBounds closure')
        providers = case['provider_before'], case['provider_after']
        require(metadata.same(providers[0], providers[1]), 'Warm world provider changed')
        for provider in providers:
            require(metadata.same(identifier_inputs(provider['identifier_inputs']), narrow['identifier_inputs']), 'World identifier input parity differs')
        decision = observations(case['native_observations']); group = key[:2]
        if group not in warm_groups: warm_groups[group] = decision
        require(metadata.same(decision, warm_groups[group]), 'Ordered warm world decoder/freshness prefix differs')
        names, omitted = observed_names(decision, caches_after); observed.update(names); excluded.extend(omitted)
        all_pins.append(caches_after)
    require(seen == expected, 'Incomplete native world matrix')
    eligible = {name: origin for name, origin in narrow['eligible'].items() if name in observed
        and all(metadata.same(rows.get(name), {key: origin['record'][key] for key in ('bytes', 'sha256')}) for rows in all_pins)}
    require(eligible, 'No original donor BINs retain actual native preload/world parity')
    return {'eligible': eligible, 'stock': stock, 'observed_world_names': sorted(observed),
        'ordered_world_prefixes': warm_groups, 'excluded_world_tokens': excluded}


def derive_proof(documents, *, raw_inputs, derivation_source, source_review):
    """Inputs must already match whole-artifact/member pins via authenticate_inputs."""
    require(isinstance(documents, _AuthenticatedInputs) and set(documents) == set(INPUTS),
        'Actual authenticated invocation-local input witness required')
    require(type(raw_inputs) is dict and set(raw_inputs) == set(INPUTS), 'Exact original raw input descriptor closure required')
    for role in INPUTS:
        input_descriptor(raw_inputs[role], role)
        require(metadata.same(raw_inputs[role], documents.original_descriptors[role])
            and metadata.canonical_sha(documents[role]) == documents.document_hashes[role],
            'Native evidence document was mutated after authenticated reading')
    require(type(derivation_source) is dict and set(derivation_source) == {'repository_commit', 'path', 'git_blob', 'pin'}
        and derivation_source['path'] == SCRIPT
        and type(derivation_source['repository_commit']) is str and re.fullmatch('[0-9a-f]{40}', derivation_source['repository_commit'])
        and type(derivation_source['git_blob']) is str and re.fullmatch('[0-9a-f]{40}', derivation_source['git_blob']), 'Exact committed derivation source identity required')
    metadata.pin_record(derivation_source['pin'], MAX_JSON)
    narrow = inspect_preload(documents['preload'], documents)
    require(type(startup.SOURCE_ONLY_COMPATIBILITY_REVIEW) is dict,
        'Independent committed source compatibility review remains closed')
    world_document = documents['native_world']; cases = world_document.get('cases')
    require(type(cases) is list and cases and all(type(case) is dict for case in cases),
        'Native world cases required before source equivalence review')
    stock = [metadata.pin_record(case['actual_native'], 64*1024**2) for case in cases if case.get('role') == 'stock']
    require(stock and all(metadata.same(value, stock[0]) for value in stock),
        'Exact actual stock generation identity required')
    controls = [stock[0], narrow['actual_tested_control']]
    shipping = startup.SOURCE_ONLY_COMPATIBILITY_REVIEW['document']['shipping_036']['MapServer']['sha256']
    review = startup.inspect_committed_source_review(source_review,
        previous_shipping_consumer_sha256=shipping, actual_tested_control_consumers=controls,
        actual_tested_candidate=narrow['actual_tested_candidate'])
    expected_sdk = startup.SOURCE_ONLY_COMPATIBILITY_REVIEW['document']['historical_cooking_and_SDK_runtime_DLLs_to_require_in_fresh_world_inputs']
    world = inspect_world(world_document, narrow, expected_sdk)
    ids_sha = metadata.canonical_sha(narrow['identifier_inputs'])
    decisions_sha = metadata.canonical_sha({'preload': narrow['decisions'],
        'native_world': [{'map_id': key[0], 'fx_variant': key[1], 'decisions': value}
            for key, value in sorted(world['ordered_world_prefixes'].items())]})
    qualified = {name: {'schema_identity_sha256': origin['schema_identity_sha256'],
        'output_sha256': origin['record']['sha256'], 'identifier_inputs_sha256': ids_sha,
        'loader_decisions_sha256': decisions_sha} for name, origin in sorted(world['eligible'].items())}
    statement = {'derivation_source': copy.deepcopy(derivation_source), 'raw_inputs': copy.deepcopy(raw_inputs), 'scope': copy.deepcopy(DERIVATION_SCOPE)}
    proof = {'format': 1, 'role': 'native_metadata_cache_consumer_parity', 'derivation': statement,
        'previous_shipping_consumer_sha256': shipping, 'current_consumer_sha256': narrow['actual_tested_candidate']['sha256'],
        'actual_tested_control_consumers': controls, 'actual_tested_candidate': narrow['actual_tested_candidate'],
        'source_compatibility_review': review['committed_source_review'],
        'native_ID_tables_observed': False, 'observed_native_bin_paths': sorted(qualified), 'qualified_per_bin': qualified,
        'eligible_bins': {name: {key: origin[key] for key in ('archive', 'member')} for name, origin in sorted(world['eligible'].items())},
        'observations_scope': {'preload_inventory_only_count': narrow['inventory_only_count'],
            'preload_successfully_observed_unique_names': narrow['successfully_observed_unique_names'],
            'eligible_original_donor_BIN_count': len(qualified), 'identifier_input_file_count': len(narrow['identifier_inputs']),
            'native_decoded_ID_tables_dumped': False, 'ordered_prefix_only': True,
            'whole_generated_BIN_and_GroupBounds_parity_verified': True,
            'source_bound_seven_native_SDK_cooking_DLL_pins_verified': True,
            'diagnostic_token_is_integrity_proof': False, 'ordinary_native_schema_freshness_retained': True},
        'omissions': narrow['excluded']+world['excluded_world_tokens'],
        'shipping_allowed': False, 'runtime_authority_created': False, 'physical_timing_validated': False,
        'behavioral_collision_validated': False}
    raw = metadata.encoded(proof)
    descriptor = {**statement, 'output': {'filename': OUTPUT_NAME, 'pin': pin(raw)}}
    return proof, descriptor


def verify_derivation_source(value, repository=ROOT):
    """Read-only Git verification of the source that produced the new summary."""
    require(type(value) is dict and set(value) == {'repository_commit', 'path', 'git_blob', 'pin'}
        and value['path'] == SCRIPT and type(value['repository_commit']) is str
        and re.fullmatch('[0-9a-f]{40}', value['repository_commit']), 'Exact derivation source commit/path required')
    metadata.pin_record(value['pin'], MAX_JSON)
    raw = migration.read_regular(ROOT/SCRIPT, MAX_JSON)
    committed = subprocess.run(['git', 'show', value['repository_commit']+':'+SCRIPT], cwd=repository,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
    require(committed.returncode == 0 and committed.stdout == raw and pin(raw) == value['pin']
        and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == value['git_blob'],
        'Actual committed derivation source bytes/blob differ')
    return copy.deepcopy(value)


def derive_from_artifacts(paths, *, raw_inputs, derivation_source, source_review, source_repository=ROOT):
    """The production entry point authenticates original bytes before deriving."""
    documents = authenticate_inputs(paths, raw_inputs)
    verify_derivation_source(derivation_source, source_repository)
    return derive_proof(documents, raw_inputs=raw_inputs,
        derivation_source=derivation_source, source_review=source_review)
