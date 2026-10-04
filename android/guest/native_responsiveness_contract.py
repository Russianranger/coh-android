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
    expected['CityOfHeroes.exe'] = candidate['files']['CityOfHeroes.exe']
    require(package.get('files') == expected and len(expected) == 21
            and package.get('source_commit') == SOURCE and package.get('data_commit') == DATA
            and package.get('android_execution_validated') is False and package.get('gameplay_validated') is False,
            'Client candidate changed its retained DLL closure')
    return candidate['files']['CityOfHeroes.exe']


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
