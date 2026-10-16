#!/usr/bin/env python3
"""Reverify the pinned support artifact without rebuilding qualified source.

This validates retained Android evidence and exact APK identities; it does not
perform a new emulator run or confer physical acceptance. Runtime source drift
fails closed, including quoted local headers omitted from the old build receipt.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import posixpath
import re
import struct
import subprocess
import zipfile

from emulator_check import verify_report_identity


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(command, cwd=None, binary=False):
    result = subprocess.run([str(x) for x in command], cwd=cwd,
                            capture_output=True, text=not binary, check=False)
    require(result.returncode == 0, 'Command failed: ' + str(command[0]))
    return result.stdout


def read_json(path):
    return json.loads(path.read_text())


def check_identity(raw, record, label):
    require(len(raw) == record['bytes'] and sha(raw) == record['sha256'],
            label + ' size/SHA256 differs')


def safe_name(name):
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,
            'Unsafe archive path')


def source_audit(root, receipt, pins):
    base = pins['qualified_source_commit']
    tracked = set(run(['git', 'ls-tree', '-r', '--name-only', base], root).splitlines())
    checked, external, drift = {}, [], []

    def original(path):
        return run(['git', 'show', base + ':' + path], root, binary=True)

    def inspect(path, expected=None):
        raw = original(path)
        if expected:
            check_identity(raw, expected, 'Qualified source ' + path)
        if path in checked:
            return raw
        current = root / path
        matches = current.is_file() and current.read_bytes() == raw
        checked[path] = {'sha256': sha(raw), 'bytes': len(raw), 'matches': matches}
        if not matches:
            drift.append(path)
        return raw

    config_path = receipt['source_manifest']['file']
    inspect(config_path, receipt['source_manifest'])
    config = json.loads(original(config_path))
    include_dirs = [p for p in config['include_dirs'] if '{' not in p]
    pending = []
    for item in receipt['sources'] + receipt['java_sources']:
        path = item['file']
        if path not in tracked:
            external.append(path)
            continue
        raw = inspect(path, item)
        if path.endswith(('.c', '.h')):
            pending.append((path, raw if raw is not None else original(path)))
    # Modern receipts record compiler -MMD closure, including angle-bracket
    # headers and macro includes that recursive quoted-include scans cannot see.
    compiled_inputs = set()
    for artifact in receipt['artifacts']:
        for item in artifact['native'].get('compiled_inputs', []):
            path = item['file']
            if path in tracked:
                inspect(path, item)
                compiled_inputs.add(path)
            else:
                external.append(path)
    headers, unresolved = set(), set()
    scanned = set()
    while pending:
        path, raw = pending.pop()
        if path in scanned:
            continue
        scanned.add(path)
        for name in re.findall(rb'^\s*#\s*include\s*"([^"]+)"', raw, re.M):
            name = name.decode()
            candidates = [posixpath.normpath(posixpath.join(posixpath.dirname(path), name))]
            candidates += [posixpath.normpath(posixpath.join(d, name)) for d in include_dirs]
            target = next((p for p in candidates if p in tracked), None)
            if target:
                if target not in headers:
                    headers.add(target)
                    data = inspect(target)
                    pending.append((target, data if data is not None else original(target)))
            else:
                unresolved.add(name)
    # Shader source is embedded by the build driver, not a normal C include.
    additional = ['native-android/support-client/AndroidManifest.xml',
                  'native-android/support-client/emulator-scenario.json']
    additional += sorted(p for p in tracked if p.startswith('native-android/world-probe/shaders/'))
    for path in additional:
        inspect(path)
    require(not drift, 'Qualified runtime source/header/shader drift: ' + ', '.join(drift))
    return {'qualified_source_commit': base,
            'current_head': run(['git', 'rev-parse', 'HEAD'], root).strip(),
            'tracked_inputs_compared': len(checked), 'local_headers_compared': len(headers),
            'compiler_recorded_tracked_inputs_compared': len(compiled_inputs),
            'runtime_drift': drift, 'external_codec_sources_not_locally_reverified': sorted(set(external)),
            'generated_or_external_includes': sorted(unresolved),
            'inputs': checked,
            'scope': 'Tracked build sources, Java, recursively quoted local headers, manifest, scenario and embedded shader inputs; external codec/generated content is bound by original artifact/native-library hashes.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-dir', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--accepted-apk', type=Path,
                        help='Optional retained 0.3.0 APK for independent seven-asset byte comparison')
    parser.add_argument('--source-root', type=Path, default=Path('.'))
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--pins', type=Path, default=Path(__file__).resolve().parents[1] /
                        'qualification-next/baseline-artifact-pins.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pins, artifact = read_json(args.pins), args.artifact_dir
    require(sha(args.archive.read_bytes()) == pins['archive_sha256'], 'Artifact archive SHA256 differs')
    with zipfile.ZipFile(args.archive) as archive:
        require(len(set(archive.namelist())) == len(archive.namelist()), 'Duplicate artifact member')
        require(archive.testzip() is None, 'Artifact ZIP CRC differs')
        for name in archive.namelist():
            safe_name(name)
            if not name.endswith('/'):
                require((artifact / name).is_file() and
                        (artifact / name).read_bytes() == archive.read(name),
                        'Extracted artifact differs: ' + name)
    receipt = read_json(artifact / 'build-receipt.json')
    summary = read_json(artifact / 'emulator-support-summary.json')
    preparation = read_json(artifact / 'preparation.json')
    require(receipt['passed'] and receipt['source_tree_clean'] and
            receipt['source_commit'] == pins['qualified_source_commit'], 'Build source binding differs')
    require(preparation['passed'] and preparation['accepted_apk_sha256'] ==
            pins['accepted_session_apk_sha256'], 'Accepted asset-source binding differs')
    source = source_audit(args.source_root.resolve(), receipt, pins)
    tools = args.sdk / 'build-tools/35.0.0'
    accepted_assets = None
    if args.accepted_apk:
        require(sha(args.accepted_apk.read_bytes()) == pins['accepted_session_apk_sha256'],
                'Retained accepted APK identity differs')
        with zipfile.ZipFile(args.accepted_apk) as z:
            manifest = json.loads(z.read('assets/asset-manifest.json'))
            accepted_assets = {name: z.read('assets/' + name) for name in manifest['assets']}
            for name, record in manifest['assets'].items():
                check_identity(accepted_assets[name], record, 'Retained accepted asset ' + name)
    apks = []
    for abi, expected in pins['apks'].items():
        apk = artifact / expected['file']
        check_identity(apk.read_bytes(), expected, 'Pinned ' + abi + ' APK')
        record = next(x for x in receipt['artifacts'] if x['native']['abi'] == abi)
        check_identity(apk.read_bytes(), record, 'Build-receipt ' + abi + ' APK')
        signature = run([tools / 'apksigner', 'verify', '--verbose', '--print-certs', apk])
        match = re.findall(r'Signer #\d+ certificate SHA-256 digest: ([0-9a-f]+)', signature)
        require(match == [pins['signer_certificate_sha256']], 'Signing identity differs')
        require('Verified using v2 scheme (APK Signature Scheme v2): true' in signature and
                'Verified using v3 scheme (APK Signature Scheme v3): true' in signature,
                'Expected APK v2/v3 signature absent')
        badging = run([tools / 'aapt2', 'dump', 'badging', apk])
        for value in ("name='" + pins['package'] + "'", "versionCode='" + str(pins['version_code']) + "'",
                      "versionName='" + pins['version_name'] + "'", "native-code: '" + abi + "'"):
            require(value in badging, 'APK manifest identity differs: ' + value)
        with zipfile.ZipFile(apk) as z:
            require(z.testzip() is None and len(z.namelist()) == len(set(z.namelist())),
                    'APK CRC/duplicate member failure')
            actual_assets = {n for n in z.namelist() if n.startswith('assets/') and not n.endswith('/')}
            require(actual_assets == {'assets/' + x['file'] for x in receipt['assets']},
                    'Packaged asset closure differs')
            for asset in receipt['assets']:
                check_identity(z.read('assets/' + asset['file']), asset, asset['file'])
            if accepted_assets is not None:
                for name, raw in accepted_assets.items():
                    require(z.read('assets/' + name) == raw, 'Accepted support asset differs: ' + name)
            libraries = [n for n in z.namelist() if n.startswith('lib/') and n.endswith('.so')]
            require(libraries == ['lib/' + abi + '/libcoh_support_client.so'], 'Native library closure differs')
            native = z.read(libraries[0])
            check_identity(native, record['native'], 'Native library')
            require(native[:6] == b'\x7fELF\x02\x01' and
                    struct.unpack_from('<H', native, 18)[0] == {'arm64-v8a': 183, 'x86_64': 62}[abi],
                    'Native ELF architecture differs')
        apks.append({'abi': abi, **expected, 'signature_verified_now': True,
                     'signer_certificate_sha256': match[0], 'packaged_assets_verified_now': len(receipt['assets'])})
    scenario_count = pins.get('emulator_scenarios', 13)
    require(summary['passed'] and summary['source_commit'] == pins['qualified_source_commit'] and
            len(summary['steps']) == scenario_count and all(s['passed'] for s in summary['steps']),
            'Retained emulator qualification differs')
    check_identity((artifact / pins['apks']['x86_64']['file']).read_bytes(), summary['installed_apk'],
                   'Installed emulator APK')
    final = read_json(artifact / 'emulator-final-report.json')
    require(final['device']['emulator_detected'] is True and
            not summary['thor_device_execution_verified'], 'Emulator/device acceptance boundary differs')
    report_count = 0
    if pins.get('require_report_identity'):
        require(summary.get('package') == pins['package'] and
                summary.get('version_name') == pins['version_name'] and
                summary.get('version_code') == pins['version_code'],
                'Emulator summary package identity differs')
        require(final['device'].get('sdk') == pins['emulator_api'],
                'Retained emulator Android API differs')
        scenario = args.source_root / 'native-android/support-client/emulator-scenario.json'
        require(sha(scenario.read_bytes()) == summary['scenario_sha256'],
                'Emulator scenario identity differs')
        reports = [artifact / 'emulator-initial-report.json',
                   artifact / 'emulator-final-report.json']
        reports += [artifact / ('emulator-step-%02d-report.json' % i)
                    for i in range(scenario_count)]
        for path in reports:
            verify_report_identity(read_json(path), receipt, pins['apks']['x86_64'])
            report_count += 1
    result = {'schema': 'coh-support-artifact-recovery-v1', 'passed': True,
              'artifact_id': pins['artifact_id'], 'artifact_url': pins['artifact_url'],
              'archive_sha256': pins['archive_sha256'], 'source': source, 'apks': apks,
              'retained_android_emulator_scenarios_passed': scenario_count,
              'retained_report_package_identities_verified': report_count,
              'new_emulator_run_performed': False,
              'new_android_build_performed': False, 'physical_thor_accepted': False,
              'retained_accepted_apk_assets_independently_compared': len(accepted_assets) if accepted_assets else 0,
              'full_gates_accepted': False,
              'known_diagnostic_limitations': pins.get('known_diagnostic_limitations', [
                  'Baseline app report version_code=1 disagrees with verified manifest versionCode=100.',
                  'Authentic font glyphs are rendered; original icon/skin resource closure remains incomplete.',
                  '10-minute sustained session, audible quality, real controller/touch/IME and route changes require Thor evidence.'])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'tracked_inputs_compared': source['tracked_inputs_compared'],
                      'local_headers_compared': source['local_headers_compared'],
                      'retained_emulator_scenarios': scenario_count,
                      'retained_report_package_identities_verified': report_count,
                      'physical_thor_accepted': False}))


if __name__ == '__main__':
    main()
