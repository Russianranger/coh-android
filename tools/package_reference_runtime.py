#!/usr/bin/env python3
"""Package a verified Win32 reference build, with hashes and PE dependency evidence.

This prepares development executables, not an Android app or a tested game world.
Only the explicit product list and MSVC redistributable DLLs are copied. Windows
system DLLs and optional driver DLLs are never copied from the host installation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ('DbServer.exe', 'MapServer.exe', 'CityOfHeroes.exe', 'TestClient.exe',
            'pig.exe', 'Launcher.exe')
DYNAMIC_DLLS = ('CrashRpt.dll', 'cg.dll', 'cgGL.dll', 'NxCharacter.dll',
                'PhysXCooking.dll', 'PhysXCore.dll', 'PhysXLoader.dll',
                'cudart32_30_9.dll', 'NxCooking.dll', 'physxcudart_20.dll', 'PhysXDevice.dll')
SYMBOLS = tuple(str(Path(name).with_suffix('.pdb')) for name in PRODUCTS) + ('CrashRpt.pdb',)
# OS APIs remain provided by Windows/Wine. Restrict to named OS components rather
# than accepting any DLL that happens to be installed on the hosted runner.
SYSTEM_DLLS = frozenset('''advapi32.dll bcrypt.dll cabinet.dll cfgmgr32.dll comctl32.dll
comdlg32.dll crypt32.dll d3d9.dll ddraw.dll dbghelp.dll dbgcore.dll dhcpcsvc.dll dinput8.dll
dnsapi.dll dsound.dll dwmapi.dll gdi32.dll glu32.dll hid.dll imagehlp.dll imm32.dll
iphlpapi.dll kernel32.dll mpr.dll msacm32.dll msvcrt.dll mswsock.dll netapi32.dll
normaliz.dll ntdll.dll odbc32.dll odbccp32.dll ole32.dll oleacc.dll oleaut32.dll
opengl32.dll pdh.dll powrprof.dll psapi.dll rasapi32.dll rpcrt4.dll secur32.dll
setupapi.dll shell32.dll shlwapi.dll ucrtbase.dll user32.dll userenv.dll usp10.dll
uxtheme.dll version.dll winhttp.dll wininet.dll winmm.dll winscard.dll winspool.drv
wintrust.dll wldap32.dll ws2_32.dll wsock32.dll wtsapi32.dll'''.split())
OPTIONAL_DRIVER_DLLS = {'nvcpl.dll', 'lightfx.dll', 'nvcuda.dll'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pe_info(data):
    """Read PE32 x86 imports and delay imports without loading/executing an image."""
    def unpack(fmt, offset):
        require(0 <= offset <= len(data) - struct.calcsize(fmt), 'Truncated PE structure')
        return struct.unpack_from(fmt, data, offset)
    require(data[:2] == b'MZ', 'Missing DOS signature')
    pe, = unpack('<I', 60)
    require(data[pe:pe + 4] == b'PE\0\0', 'Missing PE signature')
    machine, sections = unpack('<HH', pe + 4)
    optional_size, = unpack('<H', pe + 20)
    optional = pe + 24
    require(machine == 0x14c and unpack('<H', optional)[0] == 0x10b,
            'Expected Win32 x86 PE image')
    require(optional_size >= 96, 'Truncated PE optional header')
    imagebase, = unpack('<I', optional + 28)
    headers_size, = unpack('<I', optional + 60)
    directory_count, = unpack('<I', optional + 92)
    require(directory_count <= (optional_size - 96) // 8, 'Invalid PE data directory count')
    mappings = []
    for index in range(sections):
        _, rva, raw_size, raw = unpack('<4I', optional + optional_size + 40 * index + 8)
        require(raw <= len(data) and raw_size <= len(data) - raw, 'PE section outside file')
        mappings.append((rva, raw_size, raw))

    def locate(rva, size=1):
        if 0 <= rva < headers_size and size <= headers_size - rva:
            require(rva + size <= len(data), 'PE header RVA outside file')
            return rva, min(headers_size, len(data))
        for base, length, raw in mappings:
            if base <= rva and size <= length - (rva - base):
                return raw + rva - base, raw + length
        raise ValueError('PE RVA outside raw section bounds')

    def dll_name(rva):
        offset, end = locate(rva)
        end = min(end, offset + 4096)
        terminator = data.find(b'\0', offset, end)
        require(terminator != -1, 'Unterminated PE import name')
        name = data[offset:terminator].decode('ascii')
        require(re.fullmatch(r'[A-Za-z0-9_.-]+', name), 'Invalid PE import name')
        return name

    def imports(index, delay=False):
        if directory_count <= index:
            return []
        rva, length = unpack('<II', optional + 96 + index * 8)
        if not rva and not length:
            return []
        width = 32 if delay else 20
        require(rva and width <= length <= 1024 * 1024, 'Invalid PE import table size')
        names = []
        for pos in range(0, length - width + 1, width):
            offset, _ = locate(rva + pos, width)
            values = unpack('<' + 'I' * (width // 4), offset)
            if not any(values):
                return sorted(set(names), key=str.casefold)
            if delay:
                require(values[0] in (0, 1), 'Unsupported delay import attributes')
                name_rva = values[1] if values[0] else values[1] - imagebase
            else:
                name_rva = values[3]
            names.append(dll_name(name_rva))
        raise ValueError('Unterminated PE import descriptor table')

    return {'pe_machine': machine, 'imports': imports(1), 'delay_imports': imports(13, True)}


def dependency_report(records):
    available = {name.casefold(): name for name in records}
    result, unresolved = {}, []
    for name, info in records.items():
        if 'pe_machine' not in info:
            continue
        resolved = {}
        for dep in sorted(set(info['imports'] + info['delay_imports']), key=str.casefold):
            key = dep.casefold()
            if key in available:
                resolved[dep] = {'kind': 'packaged', 'file': available[key]}
            elif key in SYSTEM_DLLS or key.startswith(('api-ms-win-', 'ext-ms-win-')):
                resolved[dep] = {'kind': 'windows_system_api'}
            elif key in OPTIONAL_DRIVER_DLLS and dep not in info['imports']:
                resolved[dep] = {'kind': 'optional_driver_delay_import'}
            else:
                resolved[dep] = {'kind': 'unresolved'}
                unresolved.append(name + ' -> ' + dep)
        result[name] = resolved
    return {'files': result, 'unresolved': unresolved,
            'explicit_dynamic_dependencies': list(DYNAMIC_DLLS),
            'optional_dynamic_driver_probes': sorted(OPTIONAL_DRIVER_DLLS),
            'limitation': 'Import inventory and explicit dynamic allowlist; execution not validated'}


def file_record(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
            'Missing, empty or symlink package input: ' + str(path))
    data = path.read_bytes()
    record = {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}
    if path.suffix.lower() in ('.exe', '.dll'):
        record.update(pe_info(data))
    return record


def package(binary_directory, build_input, cmake_cache, crt_directories, output,
            repository_commit, run_url='', root=ROOT):
    require(re.fullmatch(r'[a-f0-9]{40}', repository_commit), 'Invalid repository commit')
    require(not output.exists() and not output.is_symlink(), 'Output must be a new directory')
    lock = json.loads((root / 'upstream-lock.json').read_text())
    receipt = json.loads(build_input.read_text())
    require(receipt['source_commit'] == lock['commit'], 'Build receipt source pin mismatch')
    patch = (root / 'patches/postgresql/0001-dbserver-postgresql.patch').read_bytes().replace(b'\r\n', b'\n')
    require(receipt['patch_sha256'] == hashlib.sha256(patch).hexdigest(), 'Build receipt patch mismatch')
    overlay = root / 'database/postgresql/overlay'
    expected = {p.relative_to(overlay).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in overlay.rglob('*') if p.is_file()}
    require(receipt['overlay_sha256'] == expected, 'Build receipt overlay mismatch')
    cache = cmake_cache.read_text()
    require(re.search(r'^COH_PG_PERSISTENCE_TESTS:BOOL=OFF$', cache, re.MULTILINE),
            'Reference runtime must have persistence fixture mode OFF')
    inputs = {name: binary_directory / name for name in PRODUCTS + DYNAMIC_DLLS}
    for directory in crt_directories:
        require(directory.is_dir() and not directory.is_symlink(), 'Invalid CRT directory')
        dlls = list(directory.glob('*.dll'))
        require(dlls, 'CRT directory has no redistributable DLLs')
        for path in dlls:
            key = path.name.casefold()
            require(key not in SYSTEM_DLLS, 'System DLL must not be copied from CRT directory')
            require(key not in {name.casefold() for name in inputs}, 'Duplicate package DLL: ' + path.name)
            inputs[path.name] = path
    records = {name: file_record(path) for name, path in inputs.items()}
    symbols = {name: file_record(binary_directory / name) for name in SYMBOLS}
    deps = dependency_report(records)
    require(not deps['unresolved'], 'Unresolved runtime imports: ' + '; '.join(deps['unresolved']))
    records['postgresql-build-input.json'] = file_record(build_input)
    manifest = {
        'schema_version': 1, 'status': 'reference_build_packaged_runtime_unverified',
        'source_commit': lock['commit'], 'repository_commit': repository_commit,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'run_url': run_url,
        'postgresql_persistence_fixture': False, 'postgresql_build_input': receipt,
        'files': records, 'symbols': symbols,
        'database_driver': {'name': 'psqlODBC x86 Unicode', 'version': '18.00.0004',
                            'installed_or_bundled': False,
                            'url': 'https://ftp.postgresql.org/pub/odbc/releases/REL-18_00_0004/psqlodbc_x86.msi',
                            'sha256': '1b1c85f694ecad95fd3a0125a8b071669772bef098366738de48812124896773'},
        'dependency_report': deps,
    }
    runtime, symbol_directory = output / 'runtime', output / 'symbols'
    runtime.mkdir(parents=True)
    symbol_directory.mkdir()
    for name, path in inputs.items():
        shutil.copy2(path, runtime / name)
    shutil.copy2(build_input, runtime / 'postgresql-build-input.json')
    for name in SYMBOLS:
        shutil.copy2(binary_directory / name, symbol_directory / name)
    info = ('Commit: ' + lock['commit'] + '\nRepository-Commit: ' + repository_commit +
            '\nConfiguration: OptDebug\nArchitecture: Win32 (x86)\n'
            'PostgreSQL persistence fixture: OFF\nRuntime validation: pending\n')
    for folder in (runtime, symbol_directory):
        (folder / 'build-info.txt').write_text(info, encoding='utf-8')
        (folder / 'build-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (output / 'dependency-report.json').write_text(json.dumps(deps, indent=2) + '\n', encoding='utf-8')
    (output / 'build-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    archives = []
    for folder, name in ((runtime, 'coh-reference-win32.zip'),
                         (symbol_directory, 'coh-reference-win32-symbols.zip')):
        target = output / name
        with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(folder.iterdir()):
                archive.write(path, path.name)
        archives.append(target)
    (output / 'SHA256SUMS.txt').write_text(''.join(
        hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n' for path in archives))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary-directory', type=Path, required=True)
    parser.add_argument('--build-input', type=Path, required=True)
    parser.add_argument('--cmake-cache', type=Path, required=True)
    parser.add_argument('--crt-directory', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--run-url', default='')
    args = parser.parse_args()
    manifest = package(args.binary_directory, args.build_input, args.cmake_cache,
                       args.crt_directory, args.output, args.repository_commit, args.run_url)
    print(json.dumps({'status': manifest['status'], 'files': len(manifest['files']),
                      'output': str(args.output)}))


if __name__ == '__main__':
    main()
