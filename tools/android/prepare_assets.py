#!/usr/bin/env python3
"""Build PE32 diagnostics and assemble pinned, credential-free APK assets."""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Wine 10 implements the original ANSI ODBC names but stubs these A aliases.
# Only this diagnostic compilation changes imports; fixture SQL and markers are intact.
ODBC_ANSI_ALIASES = {name+'A': name for name in
                     ('SQLDriverConnect', 'SQLExecDirect')}
ODBC_REQUIRED_IMPORTS = {*ODBC_ANSI_ALIASES.values(), 'SQLGetDiagRecA', 'SQLGetInfoW', 'SQLColumnsW'}
ODBC_FORBIDDEN_IMPORTS = {*ODBC_ANSI_ALIASES, 'SQLGetInfoA', 'SQLGetInfo', 'SQLColumnsA', 'SQLColumns'}
WINE_ODBC_INFO_SOURCE = 'https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/odbc32/proxyodbc.c#L2975'
WINE_ODBC_COLUMNS_SOURCE = 'https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/odbc32/proxyodbc.c#L1113'
WINE_ODBC_SPEC = 'https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/odbc32/odbc32.spec'

def verify_odbc_imports(dump):
    sections = [part for part in dump.split('DLL Name:')[1:]
                if part.splitlines()[0].strip().lower() == 'odbc32.dll']
    if len(sections) != 1:
        raise ValueError('Expected exactly one Windows ODBC manager import table')
    imports = set(re.findall(r'^\s*[0-9a-fA-F]+\s+\d+\s+(SQL[A-Za-z0-9_]+)\s*$', sections[0], re.M))
    if imports.intersection(ODBC_FORBIDDEN_IMPORTS):
        raise ValueError('Diagnostic imports a stubbed or broken Wine ODBC entry point')
    if not ODBC_REQUIRED_IMPORTS.issubset(imports):
        raise ValueError('Diagnostic lacks required real ODBC operations')
    return sorted(imports)

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def fetch(item, dest):
    dest = Path(dest)
    if dest.is_file() and digest(dest) == item['sha256']:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + '.part')
    try:
        with urllib.request.urlopen(item['url'], timeout=60) as src, part.open('wb') as out:
            if not src.url.startswith('https://'):
                raise ValueError('Runtime download redirected outside HTTPS')
            total = 0
            while block := src.read(1024 * 1024):
                total += len(block)
                if total > item.get('bytes', 64 * 1024 * 1024):
                    raise ValueError('Download exceeds pinned size limit')
                out.write(block)
        if ('bytes' in item and total != item['bytes']) or digest(part) != item['sha256']:
            raise ValueError('Runtime input size/hash mismatch')
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)
    return dest

def pe32(path):
    data = path.read_bytes()
    assert data[:2] == b'MZ'
    offset = struct.unpack_from('<I', data, 0x3c)[0]
    assert data[offset:offset+4] == b'PE\0\0'
    assert struct.unpack_from('<H', data, offset+4)[0] == 0x14c
    assert struct.unpack_from('<H', data, offset+24)[0] == 0x10b

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'out/android/assets/runtime')
    p.add_argument('--pg-archive', type=Path, required=True)
    p.add_argument('--pg-receipt', type=Path, required=True)
    p.add_argument('--proot-receipt', type=Path, required=True)
    p.add_argument('--repository-commit', required=True)
    p.add_argument('--cc', default='i686-w64-mingw32-gcc')
    p.add_argument('--objdump', default='i686-w64-mingw32-objdump')
    a = p.parse_args()
    out = a.output
    out.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT/'android/runtime-lock.json').read_text())
    shutil.copyfile(fetch(lock['odbc'], ROOT/'out/android/cache/psqlodbc_x86.msi'), out/'psqlodbc_x86.msi')
    cmds = [
        [a.cc, '-O2', '-Wall', '-Wextra', '-static-libgcc', str(ROOT/'android/native/runtime-probe.c'), '-ladvapi32', '-o', str(out/'runtime-probe.exe')],
        [a.cc, '-O2', '-Wall', '-Wextra', '-shared', '-static-libgcc', '-Wl,--kill-at', str(ROOT/'android/native/probe.c'), '-o', str(out/'probe.dll')],
        [a.cc, '-O2', '-Wall', '-Wextra', '-static-libgcc', '-DCOH_ODBC_TRACE=1', '-DCOH_ODBC_WIDE_INFO=1', '-DCOH_ODBC_WIDE_COLUMNS=1',
         *['-D'+alias+'='+name for alias,name in ODBC_ANSI_ALIASES.items()],
         '-I'+str(ROOT/'database/postgresql/overlay/Common/sql'), str(ROOT/'database/postgresql/tests/odbc_probe.c'), '-lodbc32', '-o', str(out/'odbc_probe.exe')],
    ]
    for cmd in cmds:
        subprocess.run(cmd, check=True)
    for name in ['runtime-probe.exe', 'probe.dll', 'odbc_probe.exe']:
        pe32(out/name)
    odbc_imports = verify_odbc_imports(subprocess.check_output([a.objdump, '-p', str(out/'odbc_probe.exe')], text=True))
    inputs = {
        'diagnostic.py': ROOT/'android/guest/diagnostic.py',
        '001-coh-compat.sql': ROOT/'database/postgresql/001-coh-compat.sql',
        'runtime-lock.json': ROOT/'android/runtime-lock.json',
        'postgresql-runtime.tar.gz': a.pg_archive,
        'postgresql-build.json': a.pg_receipt,
        'proot-build.json': a.proot_receipt,
        'THIRD_PARTY_NOTICES.md': ROOT/'android/THIRD_PARTY_NOTICES.md',
    }
    for name, src in inputs.items():
        shutil.copyfile(src, out/name)
    files = {f.name: {'bytes':f.stat().st_size, 'sha256':digest(f)} for f in sorted(out.iterdir()) if f.is_file() and f.name != 'runtime-manifest.json'}
    manifest = {'format':1, 'repository_commit':a.repository_commit, 'candidate':lock['candidate'], 'files':files,
        'runtime_probe':{'executable':'runtime-probe.exe','marker':'COH_RUNTIME_PROBE_V1 PASS bits=32 dll=verified','dll':'probe.dll'},
        'compiler':subprocess.check_output([a.cc,'--version'], text=True).splitlines()[0],
        'odbc_ansi_compatibility':{'wine_export_source':WINE_ODBC_SPEC, 'compile_aliases':ODBC_ANSI_ALIASES,
                                  'verified_windows_manager_imports':odbc_imports, 'fixture_sql_and_acceptance_markers_changed':False,
                                  'wide_driver_version_workaround': {
                                      'compile_define':'COH_ODBC_WIDE_INFO=1', 'api':'SQLGetInfoW',
                                      'result_encoding':'UTF-16 with strict ASCII conversion',
                                      'wine_source':WINE_ODBC_INFO_SOURCE,
                                      'reason':'Avoid ANSI-to-wide SQLGetInfo forwarding with a private driver handle'},
                                  'wide_columns_workaround': {
                                      'compile_define':'COH_ODBC_WIDE_COLUMNS=1', 'api':'SQLColumnsW',
                                      'filter_encoding':'UTF-16 schema/table; unchanged NULL catalog/column filters',
                                      'wine_source':WINE_ODBC_COLUMNS_SOURCE,
                                      'reason':'Avoid ANSI SQLColumns rejecting optional NULL filters during conversion'},
                                  'diagnostic_progress':'unbuffered output and credential-free ODBC call line numbers'},
        'scope':'APK build inputs; not proof of Android execution or gameplay'}
    (out/'runtime-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(files),'repository_commit':a.repository_commit,'manifest_sha256':digest(out/'runtime-manifest.json')}))

if __name__ == '__main__':
    main()
