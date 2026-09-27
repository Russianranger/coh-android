#!/usr/bin/env python3
"""Build PE32 diagnostics and assemble pinned, credential-free APK assets."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

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
    a = p.parse_args()
    out = a.output
    out.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT/'android/runtime-lock.json').read_text())
    shutil.copyfile(fetch(lock['odbc'], ROOT/'out/android/cache/psqlodbc_x86.msi'), out/'psqlodbc_x86.msi')
    cmds = [
        [a.cc, '-O2', '-Wall', '-Wextra', '-static-libgcc', str(ROOT/'android/native/runtime-probe.c'), '-o', str(out/'runtime-probe.exe')],
        [a.cc, '-O2', '-Wall', '-Wextra', '-shared', '-static-libgcc', '-Wl,--kill-at', str(ROOT/'android/native/probe.c'), '-o', str(out/'probe.dll')],
        [a.cc, '-O2', '-Wall', '-Wextra', '-static-libgcc', '-I'+str(ROOT/'database/postgresql/overlay/Common/sql'), str(ROOT/'database/postgresql/tests/odbc_probe.c'), '-lodbc32', '-o', str(out/'odbc_probe.exe')],
    ]
    for cmd in cmds:
        subprocess.run(cmd, check=True)
    for name in ['runtime-probe.exe', 'probe.dll', 'odbc_probe.exe']:
        pe32(out/name)
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
        'scope':'APK build inputs; not proof of Android execution or gameplay'}
    (out/'runtime-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(files),'repository_commit':a.repository_commit,'manifest_sha256':digest(out/'runtime-manifest.json')}))

if __name__ == '__main__':
    main()
