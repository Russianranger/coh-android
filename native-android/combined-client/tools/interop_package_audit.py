#!/usr/bin/env python3
"""Audit the new diagnostic DSO in the actual APK; no execution/Thor claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

JNI = 'Java_org_coh_nativecombined_InteropNative_'
METHODS = {'begin', 'service', 'choose', 'characters', 'report', 'controlState', 'suspend', 'disconnect', 'close'}


def required_methods(entity_diagnostic=False, neighborhood_diagnostic=False):
    methods = set(METHODS)
    if entity_diagnostic or neighborhood_diagnostic:
        methods.update(('configureBodyPartsCache', 'observedSelfPose'))
    if neighborhood_diagnostic:
        methods.add('configureClientSlots')
    return methods


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(args):
    root = args.source_root.resolve()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if os.environ.get('GITHUB_SHA'):
        assert head == os.environ['GITHUB_SHA']
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root).strip()
    member = 'lib/' + args.abi + '/libcoh_combined_interop.so'
    with zipfile.ZipFile(args.apk) as archive:
        assert archive.namelist().count(member) == 1 and archive.testzip() is None
        raw = archive.read(member)
    assert raw[:6] == b'\x7fELF\x02\x01'
    assert int.from_bytes(raw[18:20], 'little') == {'arm64-v8a': 183, 'x86_64': 62}[args.abi]
    with tempfile.TemporaryDirectory(prefix='interop-dso-') as tmp:
        library = Path(tmp) / 'libcoh_combined_interop.so'
        library.write_bytes(raw)
        symbols = subprocess.check_output([str(args.readelf), '--dyn-syms', '--wide', str(library)], text=True)
        exported = set()
        for line in symbols.splitlines():
            fields = line.split()
            if len(fields) >= 8 and fields[0].rstrip(':').isdigit() and fields[6] != 'UND' and fields[4] in ('GLOBAL', 'WEAK') and fields[5] in ('DEFAULT', 'PROTECTED'):
                exported.add(fields[7].split('@', 1)[0])
    methods = required_methods(args.entity_diagnostic, args.neighborhood_diagnostic)
    expected = {JNI + name for name in methods}
    assert expected <= exported, 'Missing JNI entrypoint'
    assert not {name for name in exported if name.startswith('coh_')}, 'Core symbols could interpose the default client'
    assert exported <= expected | {'_init', '_fini'}, 'Unintended interop exports: ' + repr(sorted(exported - expected))
    # This reviewed subset records new integration and reused protocol inputs.
    # It is not claimed as the complete compiler/header/tool dependency closure.
    scopes = ['native-android/combined-client', 'native-android/engine/initial-capture',
              'native-android/engine/entities', 'native-android/engine/character-dictionary',
              'native-android/engine/network', 'native-android/engine/dbclient',
              'native-android/engine/mapclient', 'native-android/engine/local',
              'native-android/engine/auth', 'native-android/engine/session',
              'native-android/engine/replication', 'native-android/protocol',
              'native-android/src/coh_blowfish.c', 'native-android/include']
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--', *scopes], cwd=root).decode().split('\0')
    pins = {}
    for name in paths:
        if not name or any(part in ('diagnostics', 'qualification', 'evidence') for part in Path(name).parts):
            continue
        if Path(name).suffix not in ('.c', '.h', '.inc', '.java', '.gradle', '.xml', '.py', '.txt'):
            continue
        content = (root / name).read_bytes()
        assert subprocess.check_output(['git', 'show', head + ':' + name], cwd=root) == content
        pins[name] = sha(content)
    return {'schema': 'coh-gates25-27-apk-dso-audit-v1', 'passed': True,
            'source_revision': head, 'abi': args.abi,
            'apk': {'bytes': args.apk.stat().st_size, 'sha256': sha(args.apk.read_bytes())},
            'interop_library': {'bytes': len(raw), 'sha256': sha(raw)},
            'exact_exported_symbols': sorted(exported), 'internal_core_and_static_archive_exports_hidden': True,
            'reviewed_source_subset_sha256': pins, 'complete_compiler_dependency_closure_claimed': False,
            'APK_or_native_code_executed_by_audit': False, 'Thor_compatibility_qualified': False,
            'original_server_interoperability_qualified': False, 'world_authority': False}


def main():
    if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):
        raise ValueError('OPTIMIZED_PACKAGE_AUDIT_REFUSED')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--abi', choices=('arm64-v8a', 'x86_64'), required=True)
    parser.add_argument('--entity-diagnostic', action='store_true', help='Include the two local-catalog/pose JNI methods; preserve historical nine-method audits')
    parser.add_argument('--neighborhood-diagnostic', action='store_true', help='Require the client-slot JNI entrypoint in addition to the eleven entity methods')
    parser.add_argument('--readelf', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'passed': True, 'abi': args.abi, 'interop_library': value['interop_library']}))


if __name__ == '__main__':
    main()
