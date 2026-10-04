#!/usr/bin/env python3
"""Validate the explicitly unaccepted 0.11.5 native derivative.

The enclosing signed APK inventories pin this receipt. It never promotes the
candidate executable to the stock reference or rewrites prepared-cache history.
"""
import hashlib
import json
import re

SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
ROLE = 'native_responsiveness_candidate'
EXECUTABLES = {'CityOfHeroes.exe', 'MapServer.exe', 'client-launcher.exe'}
HEX64 = re.compile(r'[0-9a-f]{64}')


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical_sha(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()).hexdigest()


def pe_record(record):
    size = record.get('size', record.get('bytes')) if isinstance(record, dict) else None
    require(isinstance(record, dict) and type(size) is int
            and 0 < size <= 64 * 1024 * 1024
            and HEX64.fullmatch(str(record.get('sha256', '')))
            and record.get('pe_machine') == 0x14c
            and all(isinstance(record.get(key), list)
                    and all(isinstance(item, str) and re.fullmatch(r'[A-Za-z0-9_.-]+', item)
                            for item in record[key]) for key in ('imports', 'delay_imports')),
            'Invalid candidate Win32 executable record')
    return record


def validate_receipt(receipt):
    require(isinstance(receipt, dict) and receipt.get('format') == 1 and receipt.get('role') == ROLE
            and re.fullmatch(r'[0-9a-f]{40}', str(receipt.get('repository_commit', '')))
            and receipt.get('source_commit') == SOURCE and receipt.get('data_commit') == DATA
            and receipt.get('configuration') == 'OptDebug' and receipt.get('architecture') == 'Win32'
            and receipt.get('runtime_execution_validated') is False
            and receipt.get('postgresql_persistence_fixture') is False
            and set(receipt.get('files', {})) == EXECUTABLES,
            'Native responsiveness candidate identity differs')
    for record in receipt['files'].values():
        pe_record(record)
    inputs = receipt.get('build_inputs', {})
    require(set(inputs) == {'character_events', 'client_texture', 'graphics_profile'}
            and all(isinstance(value, dict) and value.get('source_commit') == SOURCE
                    for value in inputs.values())
            and all(inputs[key].get('runtime_validation') == 'unverified'
                    for key in ('character_events', 'graphics_profile'))
            and inputs['client_texture'].get('runtime_performance_validated') is False
            and inputs['client_texture'].get('parse6_schema_changes') is False
            and inputs['client_texture'].get('role') == 'opt_in_client_texture_header_index',
            'Native responsiveness source receipts are incomplete')
    require(inputs['character_events'].get('build_role') == 'character_events'
            and inputs['character_events'].get('progress_build_input', {}).get('build_role') == 'mapserver_progress',
            'Native responsiveness must retain the original progress producer')
    cache = receipt.get('retained_cache', {})
    require(cache.get('schema_changed') is False
            and HEX64.fullmatch(str(cache.get('executable_sha256', '')))
            and cache['executable_sha256'] != receipt['files']['CityOfHeroes.exe']['sha256']
            and isinstance(cache.get('archive'), dict)
            and set(cache['archive']) == {'bytes', 'sha256'}
            and type(cache['archive']['bytes']) is int and cache['archive']['bytes'] > 0
            and HEX64.fullmatch(str(cache['archive']['sha256']))
            and isinstance(cache.get('schema_sources_sha256'), dict) and cache['schema_sources_sha256'],
            'Prepared cache donor history or schema compatibility proof differs')
    retained = receipt.get('retained_native_files', {})
    require(set(retained) == {'client', 'game'} and retained['client'] and retained['game'],
            'Retained native dependency receipts are incomplete')
    for group in retained.values():
        require(isinstance(group, dict), 'Invalid retained native dependency group')
        for name, record in group.items():
            require(re.fullmatch(r'[A-Za-z0-9_.-]+', name), 'Unsafe retained native dependency')
            pe_record(record)
    return receipt


def embedded_receipt(package):
    wrapper = package.get('native_responsiveness', {})
    receipt = validate_receipt(wrapper.get('receipt'))
    require(wrapper.get('receipt_sha256') == canonical_sha(receipt)
            and package.get('repository_commit') == receipt['repository_commit'],
            'Native candidate embedded receipt or checkout differs')
    return receipt


def client_contract(package, receipt=None):
    candidate = embedded_receipt(package)
    require(receipt is None or candidate == validate_receipt(receipt),
            'Client package and installed candidate receipts differ')
    expected = dict(candidate['retained_native_files']['client'])
    executable = candidate['files']['CityOfHeroes.exe']
    if 'startup_bundle_client' in package:
        executable = startup_bundle_client_contract(package, candidate)
    expected['CityOfHeroes.exe'] = executable
    require(package.get('files') == expected and len(expected) == 21
            and package.get('source_commit') == SOURCE and package.get('data_commit') == DATA
            and package.get('android_execution_validated') is False and package.get('gameplay_validated') is False,
            'Client candidate changed its retained DLL closure')
    return executable


def startup_bundle_client_contract(package, candidate=None):
    """A new client producer wraps the frozen receipt; MapServer stays frozen."""
    candidate = embedded_receipt(package) if candidate is None else validate_receipt(candidate)
    wrapper = package.get('startup_bundle_client')
    require(isinstance(wrapper, dict) and set(wrapper) == {'manifest', 'manifest_sha256',
            'base_responsiveness_receipt_sha256', 'base_client_executable'}
            and wrapper['base_responsiveness_receipt_sha256'] == canonical_sha(candidate)
            and wrapper['base_client_executable'] == candidate['files']['CityOfHeroes.exe'],
            'Startup client must retain the exact frozen native producer')
    manifest = wrapper['manifest']
    require(isinstance(manifest, dict) and wrapper['manifest_sha256'] == canonical_sha(manifest)
            and manifest.get('format') == 1
            and manifest.get('role') == 'verified_root_client_startup_supplement'
            and re.fullmatch(r'[0-9a-f]{40}', str(manifest.get('repository_commit', '')))
            and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
            and manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
            and manifest.get('build_targets') == ['Game']
            and manifest.get('postgresql_persistence_fixture') is False
            and manifest.get('runtime_execution_validated') is False
            and manifest.get('replacement_scope') == 'CityOfHeroes.exe_only'
            and manifest.get('retained_native_dependencies_changed') is False
            and manifest.get('retained_source_inputs') == candidate['build_inputs']
            and manifest.get('schema_sources_sha256') == candidate['retained_cache']['schema_sources_sha256']
            and set(manifest.get('files', {})) == {'CityOfHeroes.exe'},
            'Startup client source, dependency or cache provenance differs')
    build = manifest.get('build_input', {})
    require(isinstance(build, dict) and build.get('format') == 1
            and build.get('role') == manifest['role'] and build.get('source_commit') == SOURCE
            and build.get('base_texture_build_input') == candidate['build_inputs']['client_texture']
            and candidate['build_inputs']['client_texture'].get('texture_header_struct_bytes') == 32
            and build.get('build_targets') == ['Game']
            and build.get('configuration') == 'OptDebug' and build.get('architecture') == 'Win32'
            and all(build.get(key) is False for key in ('parse6_schema_changes', 'full_texture_asset_changes',
                'graphics_profile_changes', 'gameplay_validation_changes', 'runtime_execution_validated'))
            and build.get('verified_root_environment') == 'COH_TEXTURE_HEADER_ROOT'
            and build.get('missing_texture_reporting') == {'environment_variable': 'COH_STARTUP_DIAGNOSTIC_BOUND',
                'enabled_value': '1', 'disabled_by_default': True, 'sample_limit_per_stage': 1024,
                'retained_key_limit_per_stage': 8192, 'all_validation_retained': True}
            and build.get('source_sha256') == {'Game/src/render/tex.c':
                candidate['build_inputs']['client_texture'].get('patched_sha256', {}).get('Game/src/render/tex.c')}
            and set(build.get('patched_sha256', {})) == {'Game/src/render/tex.c'}
            and set(build.get('overlay_sha256', {})) == {'Game/src/render/coh_texture_header_root.h'}
            and all(HEX64.fullmatch(str(value)) for field in ('patched_sha256', 'overlay_sha256')
                    for value in build[field].values())
            and HEX64.fullmatch(str(build.get('patch_sha256', ''))),
            'Startup client layer changed validation or native source scope')
    record = pe_record(manifest['files']['CityOfHeroes.exe'])
    require(record != candidate['files']['CityOfHeroes.exe'], 'Startup client derivative is unchanged')
    return record


def events_progress_contract(package):
    receipt = embedded_receipt(package)
    expected = dict(receipt['retained_native_files']['game'])
    record = receipt['files']['MapServer.exe']
    expected['MapServer.exe'] = dict(record, bytes=record['size'])
    del expected['MapServer.exe']['size']
    require(package.get('files') == expected
            and package.get('postgresql_persistence_fixture') is False
            and package.get('runtime_execution_validated') is False,
            'Native candidate changed the retained DbServer or game dependency closure')
    donor = package.get('inputs', {}).get('mapserver_progress', {})
    manifest = donor.get('manifest', {})
    build = receipt['build_inputs']['character_events']
    require(manifest.get('build_role') == 'character_events' and manifest.get('build_input') == build
            and manifest.get('files', {}).get('MapServer.exe') == record
            and manifest.get('progress_contract') == build.get('progress_contract')
            and manifest.get('events_contract') == build.get('events_contract')
            and package.get('character_events_contract') == build.get('events_contract')
            and donor.get('repository_commit') == manifest.get('repository_commit') == receipt['repository_commit'],
            'Candidate native events producer differs from its source receipt')
    encoded = (json.dumps(manifest, indent=2) + '\n').encode()
    require(donor.get('manifest_sha256') == hashlib.sha256(encoded).hexdigest(),
            'Candidate MapServer producer manifest differs')
    return {'contract': build['progress_contract'], 'producer': {
        'repository_commit': receipt['repository_commit'], 'manifest_sha256': donor['manifest_sha256'],
        'mapserver_sha256': record['sha256']}}
