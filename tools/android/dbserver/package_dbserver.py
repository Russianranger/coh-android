#!/usr/bin/env python3
"""Package separate Wine DbServer fixture and normal binaries; never a stock replacement."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from package_reference_runtime import pe_info, dependency_report, require, SYSTEM_DLLS
from prepare_wine_dbserver_source import expected_wine_receipt, REQUIRED_IMPORTS, FORBIDDEN_IMPORTS, WINE_COMMIT


def ordinal_exports():
    path = ROOT / 'database/wine-dbserver/odbc32-exports.json'
    value = json.loads(path.read_text())
    require(value['wine_commit'] == WINE_COMMIT, 'ODBC export map is not the pinned Wine revision')
    source = path.with_name('odbc32.spec').read_bytes().replace(b'\r\n', b'\n')
    source_hash = hashlib.sha256(source).hexdigest()
    require(source_hash == value['source_sha256'] == '2e9ce4715558914972e83fff0bb04f4dc3101619cf760616756e494c2fd49350',
            'Pinned Wine ODBC export specification changed')
    exports = {ordinal: {'name': name, 'kind': kind} for ordinal, kind, name in
               re.findall(r'^\s*(\d+)\s+(\w+)\s+(\w+)', source.decode(), re.M)}
    require(exports == value['exports'], 'ODBC ordinal map differs from the pinned export specification')
    return value


def imported_functions(data, library='odbc32.dll'):
    """Read a PE32 import lookup table, independently of compiler text output."""
    pe_info(data)
    pe = struct.unpack_from('<I', data, 60)[0]
    sections = struct.unpack_from('<H', data, pe + 6)[0]
    opt = pe + 24
    opt_size = struct.unpack_from('<H', data, pe + 20)[0]
    headers = struct.unpack_from('<I', data, opt + 60)[0]
    mappings = []
    for i in range(sections):
        _, rva, size, raw = struct.unpack_from('<4I', data, opt + opt_size + i * 40 + 8)
        mappings.append((rva, size, raw))

    def locate(rva, size=1):
        if 0 <= rva and rva + size <= min(headers, len(data)):
            return rva
        for base, length, raw in mappings:
            if base <= rva and rva - base + size <= length:
                return raw + rva - base
        raise ValueError('Import address outside PE raw bounds')

    def string(rva):
        chars = bytearray()
        for offset in range(4096):
            value = data[locate(rva + offset)]
            if value == 0:
                return chars.decode('ascii')
            chars.append(value)
        raise ValueError('Unterminated import string')

    rva, size = struct.unpack_from('<II', data, opt + 104)
    found = []
    for offset in range(0, size - 19, 20):
        lookup, timestamp, forward, name, iat = struct.unpack_from('<5I', data, locate(rva + offset, 20))
        if not any((lookup, timestamp, forward, name, iat)):
            break
        if string(name).lower() != library:
            continue
        require(not found, 'Duplicate ODBC import library')
        table = lookup or iat
        require(table > 0, 'Missing import lookup table')
        for index in range(16384):
            value = struct.unpack_from('<I', data, locate(table + index * 4, 4))[0]
            if not value:
                break
            if value & 0x80000000:
                require(value & 0x7fff0000 == 0, 'Malformed ODBC ordinal import')
                ordinal = value & 0xffff
                export = ordinal_exports()['exports'].get(str(ordinal))
                require(export is not None, 'Unknown pinned Wine ODBC ordinal: ' + str(ordinal))
                require(export['kind'] == 'stdcall', 'Stubbed or unsupported Wine ODBC ordinal: ' + str(ordinal))
                found.append(export['name'])
            else:
                found.append(string(value + 2))
        else:
            raise ValueError('Unterminated import lookup table')
    require(found, 'Missing ODBC function imports')
    return sorted(set(found))


def record(path):
    require(path.is_file() and not path.is_symlink(), 'Invalid package file: ' + str(path))
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), **pe_info(data)}


def package(args):
    require(re.fullmatch(r'[a-f0-9]{40}', args.repository_commit), 'Invalid repository commit')
    require(not args.output.exists(), 'Package output must be new')
    wine = json.loads(args.build_input.read_text(encoding='utf-8-sig'))
    require(wine['source_commit'] == json.loads((ROOT / 'upstream-lock.json').read_text())['commit'],
            'Wine build source pin differs')
    require(wine == expected_wine_receipt(ROOT, wine.get('postgresql_build_input')),
            'Wine source receipt differs from current isolated overlay')
    manifest = {'format': 1, 'repository_commit': args.repository_commit,
                'source_commit': wine['source_commit'], 'wine_build_input': wine,
                'configuration': 'OptDebug', 'architecture': 'Win32',
                'odbc_export_spec': {k: v for k, v in ordinal_exports().items() if k != 'exports'},
                'odbc_export_map_sha256': hashlib.sha256((ROOT / 'database/wine-dbserver/odbc32-exports.json').read_bytes()).hexdigest(),
                'variants': {}, 'android_execution_validated': False, 'gameplay_validated': False,
                'scope': 'Separate Wine-compatible real DbServer; runtime qualification required'}
    for name, fixture in (('fixture', True), ('normal', False)):
        binary = getattr(args, name + '_directory')
        cache = getattr(args, name + '_cache').read_text(encoding='utf-8-sig')
        require(re.search(r'^COH_PG_PERSISTENCE_TESTS:BOOL=' + ('ON' if fixture else 'OFF') + '$', cache, re.M),
                'Fixture build mode differs: ' + name)
        inputs = {'DbServer.exe': binary / 'DbServer.exe'}
        # The build stages game DLLs and the x86 CRT. Select only the dependency
        # closure and CrashRpt, which the engine can load dynamically.
        available = {p.name.lower(): p for p in binary.glob('*.dll')}
        for p in args.crt_directory.glob('*.dll'):
            require(p.name.lower() not in SYSTEM_DLLS, 'Refusing copied OS DLL')
            require(p.name.lower() not in available, 'Ambiguous runtime DLL')
            available[p.name.lower()] = p
        require('crashrpt.dll' in available, 'Missing dynamic CrashRpt dependency')
        pending = [inputs['DbServer.exe'], available['crashrpt.dll']]
        records = {}
        while pending:
            path = pending.pop()
            if path.name in records:
                continue
            info = record(path)
            inputs[path.name] = path
            records[path.name] = info
            for dep in info['imports'] + info['delay_imports']:
                if dep.lower() in available:
                    pending.append(available[dep.lower()])
        deps = dependency_report(records)
        deps['explicit_dynamic_dependencies'] = ['CrashRpt.dll']
        deps['optional_dynamic_driver_probes'] = []
        require(not deps['unresolved'], 'Unresolved DbServer imports: ' + str(deps['unresolved']))
        functions = imported_functions(inputs['DbServer.exe'].read_bytes())
        required, forbidden = set(REQUIRED_IMPORTS), set(FORBIDDEN_IMPORTS)
        require(required <= set(functions) and not forbidden.intersection(functions),
                'DbServer ODBC imports violate Wine compatibility contract: ' + str(functions))
        out = args.output / name
        out.mkdir(parents=True)
        for filename, path in inputs.items():
            shutil.copyfile(path, out / filename)
        manifest['variants'][name] = {'postgresql_persistence_fixture': fixture, 'files': records,
                                      'cmake_cache_sha256': hashlib.sha256(getattr(args, name + '_cache').read_bytes()).hexdigest(),
                                      'odbc_imports': functions, 'dependency_report': deps}
    require(manifest['variants']['fixture']['files']['DbServer.exe']['sha256'] !=
            manifest['variants']['normal']['files']['DbServer.exe']['sha256'], 'Fixture and normal binaries are identical')
    (args.output / 'package-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('fixture-directory', 'normal-directory', 'fixture-cache', 'normal-cache', 'crt-directory', 'build-input', 'output'):
        ap.add_argument('--' + name, required=True, type=Path)
    ap.add_argument('--repository-commit', required=True)
    args = ap.parse_args()
    value = package(args)
    print(json.dumps({'status': 'packaged', 'variants': list(value['variants']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
