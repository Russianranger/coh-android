#!/usr/bin/env python3
"""Reuse pinned CI client binaries while updating two host-qualified guest helpers.

No Java, native ELF, manifest, scene, or resource payload is rebuilt. The changed
Python orchestration is not executed by Android x86 framework qualification;
actual ARM64 guest server startup remains a separate device acceptance step.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import zipfile

from prepare import safe_zip, pin, verify
from package_check import audit

BASE = '623b51299f32cbc7d09195c039a63caaa9e06179'
RUNTIME = 'd26253eaf38e254aadda7e1c18b4dfee39296dc8'
WORKFLOW = '38788212809'
ARTIFACT = '11999855486'
ARCHIVE_SHA = '7d878cad7e73f8e7b0f36cde4b35057f773a03bc7d4d258a2687be10805f852d'
PREFIX = 'native-android/combined-client/'
HELPERS = ('server_runtime.py', 'test_runtime.py')
CHANGED_SOURCE = {PREFIX + 'runtime/' + name for name in HELPERS}
REPLACEMENTS = {'assets/combined/' + name for name in (*HELPERS, 'build-inputs.json')}
APKS = {
    'arm64-v8a': ('CoH-Native-Combined-0.1.1-arm64.apk', '17a24a072fb370cceea2ff59bf52223659f467f20e70633a170898a0fd15e758', 'arm64-package.json'),
    'x86_64': ('CoH-Native-Combined-0.1.1-emulator-x86_64.apk', '28ac93f8047b075bd1e8da15b93ca964470108ac2144c6b5e217ddcf41b1350f', 'x86_64-package.json'),
}
DOCS = {
    PREFIX + 'README.md', PREFIX + 'THOR-TEST.md', PREFIX + 'QUALIFICATION.md',
    PREFIX + 'tools/reuse_server_helper.py',
    '.github/workflows/native-combined-client.yml',
    '.github/workflows/native-combined-startup-requalify.yml',
}


def run(command):
    return subprocess.run([str(v) for v in command], check=True, capture_output=True, timeout=120).stdout


def git(root, *args):
    return run(['git', '-C', root, *args]).decode().strip()


def source_contract(args):
    git(args.source_root, 'merge-base', '--is-ancestor', BASE, RUNTIME)
    git(args.source_root, 'merge-base', '--is-ancestor', RUNTIME, 'HEAD')
    changed = set(git(args.source_root, 'diff', '--name-only', '--no-renames', BASE, RUNTIME).splitlines())
    if changed != CHANGED_SOURCE:
        raise ValueError('Pinned runtime revision changed the qualified client source closure')
    later = git(args.source_root, 'diff', '--name-only', '--no-renames', RUNTIME, 'HEAD').splitlines()
    rejected = [v for v in later if v not in DOCS and not v.startswith(PREFIX + 'evidence/')]
    if rejected:
        raise ValueError('Client/runtime source changed after pinned helper revision: ' + repr(rejected))
    dirty = git(args.source_root, 'status', '--porcelain', '--untracked-files=all')
    if args.require_clean and dirty:
        raise ValueError('Repackage source must be clean')
    # Even without --require-clean, never admit working-tree runtime changes.
    for name in HELPERS:
        source = args.source_root / PREFIX / 'runtime' / name
        pinned = run(['git', '-C', args.source_root, 'show', RUNTIME + ':' + PREFIX + 'runtime/' + name])
        if source.read_bytes() != pinned or (args.assets / 'combined' / name).read_bytes() != pinned:
            raise ValueError('Prepared helper does not match pinned runtime source: ' + name)
    return {'source_commit': git(args.source_root, 'rev-parse', 'HEAD'),
            'source_clean': not bool(dirty), 'changes_after_runtime_revision': later,
            'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def payload_proof(base, final):
    with zipfile.ZipFile(base) as old, zipfile.ZipFile(final) as new:
        safe_zip(old)
        safe_zip(new)
        if set(old.namelist()) != set(new.namelist()):
            raise ValueError('Repackage added or removed APK payload entries')
        changed = {name for name in old.namelist() if old.read(name) != new.read(name)}
        if changed != REPLACEMENTS:
            raise ValueError('Unexpected changed APK payload entries: ' + repr(sorted(changed)))
        unchanged = {name: pin(new.read(name)) for name in sorted(new.namelist()) if name not in changed}
        return {'changed_entries': {name: {'before': pin(old.read(name)), 'after': pin(new.read(name))}
                                    for name in sorted(changed)},
                'unchanged_entries': unchanged, 'unchanged_entry_count': len(unchanged),
                'client_payload_byte_identical_to_ci': True}


def repackage(args):
    verify(args.archive, ARCHIVE_SHA)
    source = source_contract(args)
    if args.output.exists():
        raise ValueError('Preserve existing outputs; choose a new output directory')
    args.output.mkdir(parents=True)
    work = args.output / '_intermediate'
    work.mkdir()
    packages = {}
    try:
        with zipfile.ZipFile(args.archive) as bundle:
            safe_zip(bundle)
            boundary_pins = {}
            for entry, limit in (('host/local-android/android-build.json', 65536),
                                 ('host/local-android/coh-local-x86_64', 1 << 20)):
                if bundle.getinfo(entry).file_size > limit:
                    raise ValueError('Pinned Android boundary input exceeds its bound')
                data = bundle.read(entry)
                target = args.output / entry
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                boundary_pins[entry] = pin(data)
            binary = args.output / 'host/local-android/coh-local-x86_64'
            boundary = json.loads((args.output / 'host/local-android/android-build.json').read_text())
            members = [v for v in boundary['artifacts'] if v['abi'] == 'x86_64']
            if (len(members) != 1 or members[0]['file'] != binary.name
                    or members[0]['sha256'] != pin(binary.read_bytes())['sha256']
                    or binary.read_bytes()[:5] != b'\x7fELF\x02'
                    or int.from_bytes(binary.read_bytes()[18:20], 'little') != 62):
                raise ValueError('Pinned Android boundary executable/receipt mismatch')
            binary.chmod(0o755)
            for abi, (name, sha, receipt_name) in APKS.items():
                base = work / ('base-' + name)
                base.write_bytes(bundle.read(name))
                verify(base, sha)
                prior = json.loads(bundle.read(receipt_name))
                if (prior['status'] != 'passed' or prior['source_commit'] != BASE
                        or prior['tracked_source_clean'] is not True or prior['abi'] != abi
                        or prior['apk'] != dict(name=name, **pin(base.read_bytes()))):
                    raise ValueError('Pinned CI package receipt does not match the admitted binary')
                # Independently repeat payload, architecture, identity and signer audits.
                audit(argparse.Namespace(apk=base, abi=abi, source_root=args.source_root,
                                         build_tools=args.build_tools, require_clean=False))
                replacement = {name: (args.assets / name.removeprefix('assets/')).read_bytes()
                               for name in REPLACEMENTS}
                with zipfile.ZipFile(base) as old:
                    old_inputs = json.loads(old.read('assets/combined/build-inputs.json'))
                    new_inputs = json.loads(replacement['assets/combined/build-inputs.json'])
                    normalized = copy.deepcopy(new_inputs)
                    for helper in HELPERS:
                        expected = pin(replacement['assets/combined/' + helper])
                        if new_inputs['combined_helpers'][helper] != expected:
                            raise ValueError('Prepared helper receipt mismatch')
                        normalized['combined_helpers'][helper] = old_inputs['combined_helpers'][helper]
                    if normalized != old_inputs:
                        raise ValueError('Prepared build inputs changed beyond two guest helper pins')
                    unsigned = work / ('unsigned-' + name)
                    with zipfile.ZipFile(unsigned, 'w') as new:
                        for info in old.infolist():
                            new.writestr(info, replacement.get(info.filename, old.read(info.filename)))
                aligned = work / ('aligned-' + name)
                run([args.build_tools / 'zipalign', '-P', '16', '-f', '4', unsigned, aligned])
                final = args.output / name
                key = args.source_root / 'native-android/session-client/app/test-signing/session-test.p12'
                run([args.build_tools / 'apksigner', 'sign', '--ks', key, '--ks-type', 'PKCS12',
                     '--ks-key-alias', 'coh-native-test', '--ks-pass', 'pass:coh-native-public-test',
                     '--key-pass', 'pass:coh-native-public-test', '--v1-signing-enabled', 'false',
                     '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'true',
                     '--v4-signing-enabled', 'false', '--out', final, aligned])
                run([args.build_tools / 'zipalign', '-P', '16', '-c', '4', final])
                receipt = audit(argparse.Namespace(apk=final, abi=abi, source_root=args.source_root,
                                                  build_tools=args.build_tools, require_clean=args.require_clean))
                if receipt['signer_certificate_sha256'] != prior['signer_certificate_sha256']:
                    raise ValueError('Repackage changed the established update signer')
                (args.output / receipt_name).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
                packages[abi] = {'base_ci_apk': prior['apk'], 'apk': receipt['apk'],
                                 'payload_identity': payload_proof(base, final),
                                 'same_signer_as_ci': True}
                final.with_suffix(final.suffix + '.idsig').unlink(missing_ok=True)
        value = {'schema': 'coh-native-combined-helper-repackage-v1', 'status': 'passed',
                 'base_client_source': BASE, 'guest_runtime_source': RUNTIME,
                 'base_workflow': WORKFLOW, 'base_artifact': ARTIFACT, 'archive_sha256': ARCHIVE_SHA,
                 **source, 'packages': packages, 'android_boundary_inputs': boundary_pins,
                 'java_native_scene_recompiled': False,
                 'apk_resigned': True, 'changed_guest_python_executed_on_android': False,
                 'actual_guest_server_boot_verified': False, 'actual_server_interoperability_verified': False,
                 'physical_thor_accepted': False,
                 'scope': 'Exact pinned CI Java/native/scene/resource payloads retained; only two host-qualified guest Python helpers and their build-input receipt change. Android framework evidence applies to the unchanged client payload. The final APK and changed guest orchestration have not been executed by this tool.'}
        (args.output / 'helper-repackage-proof.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'status': 'passed', 'packages': {abi: item['apk'] for abi, item in packages.items()},
                          'changed_guest_python_executed_on_android': False}))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument('--assets', type=Path)
    p.add_argument('--build-tools', type=Path, required=True)
    p.add_argument('--require-clean', action='store_true')
    args = p.parse_args()
    args.source_root = args.source_root.resolve()
    args.assets = args.assets or args.source_root / PREFIX / 'app/src/main/assets'
    repackage(args)


if __name__ == '__main__':
    main()
