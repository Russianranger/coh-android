#!/usr/bin/env python3
"""Stage and receipt new Win32 performance candidates without replacing donors."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'android/guest'))
from package_reference_runtime import dependency_report, file_record
import native_responsiveness_contract as contract

INPUTS = {'character_events': ('prepare_character_events_source', 'character-events-build-input.json', 'expected_events_receipt'),
          'client_texture': ('prepare_client_texture_source', 'client-texture-build-input.json', 'expected_texture_receipt'),
          'graphics_profile': ('prepare_client_graphics_source', 'client-graphics-build-input.json', 'expected_graphics_receipt')}
# Texture-header and transient graphics overlays do not edit ParseTable layout or
# Parse6 serialization. Pin their actual schema/reader inputs independently.
SCHEMA_FILES = ('libs/UtilitiesLib/src/utils/textparser.c',
                'libs/UtilitiesLib/include/utilitieslib/utils/textparser.h',
                'Common/seq/seqload.c', 'Common/seq/seqload.h')


def require(value, message):
    if not value:
        raise ValueError(message)


def read_json(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 8*1024*1024,
            'Missing or unbounded native build receipt: ' + path.name)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def source_receipts(directory):
    records = {}
    for key, (module_name, receipt_name, expected_name) in INPUTS.items():
        module = importlib.import_module(module_name)
        actual = read_json(directory / receipt_name)
        expected = getattr(module, expected_name)()
        require(actual == expected, 'Native overlay source receipt differs: ' + key)
        records[key] = actual
    return records


def schema_pins(directory=None):
    pins = {}
    for name in SCHEMA_FILES:
        source = ROOT / 'upstream/ouroboros' / name
        require(source.is_file() and not source.is_symlink(), 'Missing serializer source: ' + name)
        digest = hashlib.sha256(source.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if directory is not None:
            path = directory / name
            require(path.is_file() and not path.is_symlink()
                    and hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest,
                    'Native performance overlay changed prepared-cache schema: ' + name)
        pins[name] = digest
    return pins


def stage(args):
    events = importlib.import_module(INPUTS['character_events'][0])
    texture = importlib.import_module(INPUTS['client_texture'][0])
    graphics = importlib.import_module(INPUTS['graphics_profile'][0])
    events.prepare(args.output)
    texture.apply_texture_overlay(args.output)
    graphics.apply_graphics_overlay(args.output)
    receipts = source_receipts(args.output)
    schema_pins(args.output)
    (args.output / 'responsiveness-source-input.json').write_text(json.dumps({
        'format': 1, 'role': contract.ROLE, 'source_commit': contract.SOURCE,
        'runtime_execution_validated': False, 'build_targets': ['Game', 'MapServer'],
        'build_inputs': receipts, 'schema_sources_sha256': schema_pins()}, indent=2) + '\n')


def package(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Exact native build commit required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh native package directory required')
    receipts = source_receipts(args.source)
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', args.cache.read_text(encoding='utf-8-sig'), re.M) == ['OFF'],
            'Native candidate must disable persistence fixtures')
    schema = schema_pins(args.source)
    files = {name: file_record(args.directory / name) for name in ('CityOfHeroes.exe', 'MapServer.exe')}
    require(all(record['pe_machine'] == 0x14c for record in files.values()), 'Native candidates must be PE32')
    # Dependency closure is checked against the exact published donor at APK
    # packaging, where the authoritative retained DLL records are available.
    document = {'format': 1, 'role': contract.ROLE, 'repository_commit': args.repository_commit,
                'source_commit': contract.SOURCE, 'data_commit': contract.DATA,
                'configuration': 'OptDebug', 'architecture': 'Win32',
                'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
                'build_targets': ['Game', 'MapServer'], 'build_inputs': receipts,
                'schema_sources_sha256': schema, 'cmake_cache_sha256': file_record(args.cache)['sha256'],
                'files': files, 'run_url': args.run_url,
                'symbols': {name: file_record(args.directory / name) for name in ('CityOfHeroes.pdb', 'MapServer.pdb')}}
    args.output.mkdir(parents=True)
    for name in files:
        shutil.copyfile(args.directory / name, args.output / name)
    (args.output / 'native-responsiveness-build.json').write_text(json.dumps(document, indent=2) + '\n')
    return document


def validate_package(directory, commit):
    document = read_json(directory / 'native-responsiveness-build.json')
    require(document.get('format') == 1 and document.get('role') == contract.ROLE
            and document.get('repository_commit') == commit
            and document.get('source_commit') == contract.SOURCE and document.get('data_commit') == contract.DATA
            and document.get('configuration') == 'OptDebug' and document.get('architecture') == 'Win32'
            and document.get('postgresql_persistence_fixture') is False
            and document.get('runtime_execution_validated') is False
            and document.get('build_targets') == ['Game', 'MapServer']
            and document.get('schema_sources_sha256') == schema_pins(), 'Native build identity differs')
    require(set(path.name for path in directory.iterdir()) == {'CityOfHeroes.exe', 'MapServer.exe', 'native-responsiveness-build.json'},
            'Unexpected native package member')
    for name, (module_name, _, expected_name) in INPUTS.items():
        require(document.get('build_inputs', {}).get(name) == getattr(importlib.import_module(module_name), expected_name)(),
                'Native build source overlay changed: ' + name)
    require(set(document.get('files', {})) == {'CityOfHeroes.exe', 'MapServer.exe'}, 'Native executable inventory differs')
    for name, record in document['files'].items():
        contract.pe_record(record)
        require(file_record(directory / name) == record, 'Native candidate bytes or imports differ: ' + name)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('stage')
    prepare.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('package')
    for name in ('directory', 'source', 'cache', 'output'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--repository-commit', required=True)
    create.add_argument('--run-url', default='')
    args = parser.parse_args()
    {'stage': stage, 'package': package}[args.command](args)


if __name__ == '__main__':
    main()
