#!/usr/bin/env python3
"""Independent read-only APK byte/signature audit; this grants no runtime acceptance.

No APK code executes. Android SDK tools inspect its signature and binary manifest;
all ZIP/tar payload bytes are hashed independently of the producer's build report.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import sys
import tarfile
import zipfile

APP = 'io.github.russianranger.cohclientinteractive'
SIGNER = '92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282'
DONOR = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
OLD_GAME = {'bytes': 11231995, 'sha256': '20445586ef4271b5f1ce34dd105d4131b8ec1a73fbd88f21c23b700a6913bfe6'}
OLD_MAP = {'bytes': 7475200, 'sha256': 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'}
ADDED = {'armport-client.zip', 'armport_client_package.py', 'armport_interactive.py', 'client_stdio.py', 'server_metrics.py'}
CHANGED = {'client_login_diagnostic.py', 'character_creation_diagnostic.py', 'local_login_server.py',
    'local_character_server.py', 'character_zoning.py', 'runtime-manifest.json', 'client-manifest.json',
    'game_diagnostic.py', 'atlas_beacon_package.py', 'native_map_startup_contract.py',
    'native_monorail_contract.py', 'server_cache_package.py', 'server_fx_catalog.py', 'server_animation_package.py'}
BINDING = 'armport-server-metrics-binding.json'
SERVER_ADDED = {'armport_server_metrics_contract.py', BINDING}
PREFIX = 'assets/runtime/'
STARTUP_MARKERS = ('ARMPORT_SERVER_STARTUP_V1 status=ok', 'directory_cache_begin',
    'directory_cache_done', 'args_parsed', 'sys_init_done', 'server_state_done',
    'map_metadata_done', 'sequencer_info_done', 'definitions_done',
    'encounter_scripts_done', 'player_animations_done', 'db_connect_begin',
    'db_connected', 'group_load_begin', 'group_load_done', 'db_setup_done',
    'ready_published', 'main_loop_begin')


def need(ok, message):
    if not ok: raise ValueError(message)


def pin(raw): return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def document(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, 'Duplicate JSON key')
            value[key] = item
        return value
    def bad(_): raise ValueError('Nonfinite JSON constant')
    need(len(raw) <= 16 * 1024 * 1024, 'JSON exceeds bound')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
    need(isinstance(value, dict), 'JSON object required')
    return value


def zip_bytes(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        records = archive.infolist()
        need(len(records) == len({i.filename for i in records}) and len(records) <= 4096, 'ZIP member count/duplicates')
        need(sum(i.file_size for i in records) <= 1024 * 1024 * 1024, 'ZIP bytes exceed bound')
        result = {}
        for item in records:
            path = PurePosixPath(item.filename)
            need(not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename,
                 'Unsafe ZIP path')
            need(not item.flag_bits & 1 and (item.external_attr >> 16) & 0o170000 != 0o120000, 'Encrypted/linked ZIP member')
            if not item.is_dir(): result[item.filename] = archive.read(item)
        return result


def pe_header(raw, machine, magic):
    need(len(raw) >= 64 and raw[:2] == b'MZ', 'Missing DOS header')
    offset, = struct.unpack_from('<I', raw, 60)
    need(64 <= offset <= len(raw) - 26 and raw[offset:offset + 4] == b'PE\0\0', 'Missing/truncated PE header')
    need(struct.unpack_from('<H', raw, offset + 4)[0] == machine
         and struct.unpack_from('<H', raw, offset + 24)[0] == magic, 'Wrong PE architecture')


def game_archive(raw):
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        total = 0
        for item in archive:
            need(item.isfile() and re.fullmatch('[A-Za-z0-9_.-]+', item.name)
                 and item.name.casefold() not in {n.casefold() for n in result}, 'Unsafe/linked/duplicate native member')
            total += item.size
            need(0 < item.size <= 64 * 1024 * 1024 and total <= 512 * 1024 * 1024 and len(result) < 65, 'Native archive bounds')
            result[item.name] = archive.extractfile(item).read()
    manifest = document(result['game-package.json'])
    need(set(result) == set(manifest['files']) | {'game-package.json'}, 'Native inventory members differ')
    for name, expected in manifest['files'].items():
        need(pin(result[name]) == {k: expected[k] for k in ('bytes', 'sha256')}, 'Native byte pin differs: ' + name)
        if name.lower().endswith(('.exe', '.dll')): pe_header(result[name], 0x14c, 0x10b)
    return manifest, result


def sdk(*args):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=120)
    need(result.returncode == 0, 'SDK verification failed: ' + str(args[0]) + '\n' + result.stderr[-2000:])
    return result.stdout


def signature(apk, tools):
    text = sdk(tools / 'apksigner', 'verify', '--verbose', '--print-certs', apk)
    need('Verified using v2 scheme (APK Signature Scheme v2): true' in text
         and 'Verified using v3 scheme (APK Signature Scheme v3): true' in text, 'v2/v3 signature missing')
    need(re.findall(r'Signer #[0-9]+ certificate SHA-256 digest: ([0-9a-f]{64})', text) == [SIGNER], 'Wrong or multiple signers')
    need(re.search(r'Number of signers: 1\b', text), 'Expected exactly one signer')
    return text


def manifest_tree(apk, tools):
    text = sdk(tools / 'aapt2', 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml')
    lines = text.splitlines()
    need(sum(':versionCode(' in s for s in lines) == sum(':versionName(' in s for s in lines) == 1, 'Version attributes missing/duplicated')
    return [re.sub(r' \(line=\d+\)', '', s).split('=')[0] + '=VERSION'
            if ':versionCode(' in s or ':versionName(' in s else re.sub(r' \(line=\d+\)', '', s) for s in lines]


def source_bytes(repo, source_commit, path):
    value = subprocess.run(['git', '-C', str(repo), 'show', source_commit + ':' + path], capture_output=True, timeout=30)
    need(value.returncode == 0, 'Frozen source unavailable: ' + path)
    return value.stdout


def execute(args):
    source_commit, native_build_run_id = args.source_commit, args.native_build_run_id
    independent_dex = None
    donor_raw, apk_raw = args.donor.read_bytes(), args.apk.read_bytes()
    need(pin(donor_raw) == DONOR, 'Public donor bytes differ')
    donor, apk = zip_bytes(donor_raw), zip_bytes(apk_raw)
    signed = signature(args.apk, args.tools)
    badging = sdk(args.tools / 'aapt2', 'dump', 'badging', args.apk)
    version, code = ('0.13.36', 51) if args.mode == 'donor' else ('0.13.54', 69)
    need(re.search(r"^package: name='" + re.escape(APP) + "' versionCode='" + str(code) + "' versionName='" + re.escape(version) + "'", badging, re.M), 'Application/version differs')
    need("minSdkVersion:'26'" in badging and "targetSdkVersion:'35'" in badging, 'SDK bounds changed')
    need(manifest_tree(args.apk, args.tools) == manifest_tree(args.donor, args.tools), 'Manifest changed beyond version')
    runtime = document(apk[PREFIX + 'runtime-manifest.json'])
    client = document(apk[PREFIX + 'client-manifest.json'])
    pack = document(apk[PREFIX + 'asset-pack-manifest.json'])
    missing = {name for name in runtime['files'] if PREFIX + name not in apk}
    external = {name.split('/', 1)[1]: value for name, value in pack['files'].items() if name.startswith('runtime/')}
    need(missing == set(external), 'Missing runtime leaves differ from original external pack')
    need({name[len(PREFIX):] for name in apk if name.startswith(PREFIX)} == (set(runtime['files']) - missing) | {'runtime-manifest.json'}, 'Runtime inventory/member closure differs')
    for name, expected in runtime['files'].items():
        need((external[name] if name in missing else pin(apk[PREFIX + name])) == expected, 'Runtime pin differs: ' + name)
    need(all(runtime['files'].get(n) == p for n, p in client['files'].items()), 'Client/runtime inventories disagree')
    old_manifest, old_game = game_archive(donor[PREFIX + 'game-package.tar.gz'])
    game_manifest, game = game_archive(apk[PREFIX + 'game-package.tar.gz'])
    need(pin(donor[PREFIX + 'game-package.tar.gz']) == OLD_GAME and pin(old_game['MapServer.exe']) == OLD_MAP, 'Original modern server identity differs')
    need(set(game) == set(old_game), 'Native payload member closure changed')
    changed_native = sorted(n for n in game if game[n] != old_game[n])
    metrics = args.mode == 'candidate'
    if not metrics:
        need(not changed_native and pin(apk[PREFIX + 'game-package.tar.gz']) == OLD_GAME, 'Original modern package was not retained/restored')
        need('armport_server_metrics' not in runtime and not SERVER_ADDED.intersection(n[len(PREFIX):] for n in apk if n.startswith(PREFIX)), 'Rollback unexpectedly enables metrics')
    clean = lambda names: {n for n in names if not n.startswith('META-INF/')}
    old_names, names = clean(donor), clean(apk)
    need(not old_names - names, 'Donor members removed')
    added = names - old_names
    changed = {n for n in names & old_names if apk[n] != donor[n]}
    if args.mode == 'donor':
        need(not added and not changed and apk_raw == donor_raw, 'Donor positive control differs')
    else:
        allowed_added = ADDED | (SERVER_ADDED if metrics else set())
        allowed_changed = CHANGED | ({'game-package.tar.gz'} if metrics else set())
        need(added == {PREFIX + n for n in allowed_added}, 'Unlisted APK additions')
        need(changed <= {'AndroidManifest.xml', 'classes.dex'} | {PREFIX + n for n in allowed_changed}, 'Unlisted APK replacements')
        for name in sorted(added | changed):
            if name.startswith(PREFIX) and name.endswith('.py'):
                leaf = name[len(PREFIX):]
                directory = 'armport/app/' if leaf in ADDED else 'android/guest/'
                need(apk[name] == source_bytes(args.repo, source_commit, directory + leaf), 'Guest/helper differs from frozen source: ' + leaf)
        need(runtime.get('repository_commit') == source_commit, 'Runtime source commit differs')
        old_runtime = document(donor[PREFIX + 'runtime-manifest.json'])
        strip = lambda x: {k: v for k, v in x.items() if k not in {'files', 'repository_commit', 'armport_client', 'armport_server_metrics'}}
        need(strip(runtime) == strip(old_runtime), 'Runtime feature/asset metadata changed')
        arm_raw = apk[PREFIX + 'armport-client.zip']
        if args.armport_zip: need(arm_raw == args.armport_zip.read_bytes(), 'ARM64 package differs from downloaded qualified runtime')
        arm = zip_bytes(arm_raw); doc = document(arm['client-package.json'])
        need(doc.get('role') == 'arm64_graphical_client' and doc.get('machine') == 'ARM64'
             and doc.get('client_run_id') == doc.get('data_run_id') == native_build_run_id, 'ARM64 client/data identity differs')
        need(set(arm) == set(doc['files']) | {'client-package.json'}, 'ARM64 overlay closure differs')
        for name, expected in doc['files'].items():
            need(pin(arm[name]) == {'bytes': expected['size'], 'sha256': expected['sha256']}, 'ARM64 overlay byte pin differs')
            if name.lower().endswith(('.exe', '.dll')): pe_header(arm[name], 0xaa64, 0x20b)
        need(runtime['armport_client'] == {'archive_sha256': pin(arm_raw)['sha256'],
             'executable_sha256': pin(arm['CityOfHeroes.exe'])['sha256'], 'client_run_id': native_build_run_id,
             'data_run_id': native_build_run_id, 'machine': 'ARM64', 'default_architecture': 'x86'}, 'Outer ARM64 binding differs')
        need({k: v for k, v in client.items() if k != 'files'} ==
             {k: v for k, v in document(donor[PREFIX + 'client-manifest.json']).items() if k != 'files'},
             'Client manifest metadata changed')
        report = document(args.build_report.read_bytes())
        need({k: report.get(k) for k in ('bytes', 'sha256')} == pin(apk_raw)
             and report.get('repository_commit') == source_commit and report.get('version_name') == version
             and report.get('version_code') == code and report.get('application_id') == APP
             and report.get('signer_certificate_sha256') == SIGNER, 'Producer identity/hash differs from independent audit')
        need(set(report['added_members']) == added and set(report['replaced_members']) == changed
             and report['retained_members'] == len(names & old_names) - len(changed), 'Producer member accounting differs')
        actual_changed_runtime = {n[len(PREFIX):] for n in changed if n.startswith(PREFIX)}
        need(set(report['changed_runtime_payloads']) == actual_changed_runtime, 'Producer changed-runtime list differs')
        need(report['armport_package'] == pin(arm_raw) and report['armport_client'] == runtime['armport_client'], 'Producer ARM64 package binding differs')
        need(isinstance(report.get('java_sources'), dict) and len(report['java_sources']) == 24, 'Expected full 24-source Java provenance')
        for path, expected in report['java_sources'].items():
            need(pin(source_bytes(args.repo, source_commit, path)) == expected, 'Java provenance differs from frozen source')
        if args.expected_dex:
            preflight_raw = args.dex_preflight_report.read_bytes()
            preflight = document(preflight_raw)
            expected_dex = args.expected_dex.read_bytes()
            need(preflight.get('passed') is True and preflight.get('actual_repository_java_sources') == 24
                 and preflight.get('java_sources') == report['java_sources']
                 and preflight.get('java_source_bytes_unchanged_after_compilation') is True,
                 'Independent DEX compilation did not cover these exact 24 source pins')
            need(pin(expected_dex) == preflight.get('dex') and apk['classes.dex'] == expected_dex,
                 'APK DEX differs from the separately compiled exact-source DEX')
            independent_dex = {'preflight_report': pin(preflight_raw), 'dex': pin(expected_dex),
                'all_24_source_pins_match': True, 'actual_APK_DEX_byte_identical': True}
        if metrics:
            need(args.native_server_zip is not None and args.runtime_run_id is not None, 'Candidate requires exact native ZIP and runtime ID')
            native_raw = args.native_server_zip.read_bytes(); native = zip_bytes(native_raw)
            need(set(native) == {'MapServer.exe', 'server-metrics-build.json', 'previous-game-package.json', 'server-metrics-source-checks.json'}, 'Native build ZIP closure differs')
            binding = document(apk[PREFIX + BINDING]); build = document(native['server-metrics-build.json'])
            need(binding['server_package'] == pin(native_raw) and binding['game_archive'] == pin(apk[PREFIX + 'game-package.tar.gz']), 'Embedded server archive binding differs')
            for key, leaf in [('build_manifest', 'server-metrics-build.json'), ('previous_manifest', 'previous-game-package.json'), ('source_report', 'server-metrics-source-checks.json')]:
                need(binding[key + '_utf8'].encode() == native[leaf] and binding[key] == pin(native[leaf]), 'Embedded native metadata differs: ' + key)
            need(native['MapServer.exe'] == game['MapServer.exe'] and native['previous-game-package.json'] == old_game['game-package.json'], 'Actual installed MapServer/predecessor differs from exact native artifact')
            # Inspect the actual APK's authenticated PE bytes, not its source
            # receipt. Literal presence is a static check, not proof of calls
            # executing or of startup checkpoints being emitted at runtime.
            need(all(marker.encode('ascii') in game['MapServer.exe'] for marker in STARTUP_MARKERS),
                 'Actual candidate MapServer lacks expected startup instrumentation literals')
            need(changed_native == ['MapServer.exe', 'game-package.json'], 'Candidate changed additional native files')
            need(build['repository_commit'] == source_commit and build['run_id'] == native_build_run_id and build['variant'] == 'thor_certified_startup'
                 and build['architecture'] == 'Win32' and build['postgresql_persistence_fixture'] is False, 'Native build identity differs')
            need(game_manifest['armport_server_metrics'] == {'receipt': build, 'receipt_sha256': hashlib.sha256(canonical(build)).hexdigest()}, 'Game manifest receipt differs')
            restored = dict(game_manifest); restored.pop('armport_server_metrics'); restored['files'] = dict(restored['files']); restored['files']['MapServer.exe'] = old_manifest['files']['MapServer.exe']
            need(restored == old_manifest, 'Native ancestry changed beyond MapServer')
            need({k: build['files']['MapServer.exe'][k] for k in ('bytes', 'sha256')} == pin(game['MapServer.exe'])
                 and build['files']['MapServer.exe']['imports'] == old_manifest['files']['MapServer.exe']['imports']
                 and build['files']['MapServer.exe']['delay_imports'] == old_manifest['files']['MapServer.exe']['delay_imports'], 'Native MapServer record/closure differs')
            q = report.get('server_metrics_qualification', {})
            need(q.get('native_build_run_id') == native_build_run_id and q.get('runtime_run_id') == args.runtime_run_id, 'Producer qualification run IDs differ')
            # Reuse source certificate validation as an additional check, after
            # all independent byte/header/identity comparisons above.
            sys.path[:0] = [str(args.repo / 'armport/app'), str(args.repo / 'tools'), str(args.repo / 'armport/scripts'), str(args.repo / 'android/guest')]
            import server_package
            import armport_server_metrics_contract as guest_contract
            admitted_build, _, _ = guest_contract.validate_binding(binding)
            need(admitted_build == build, 'Guest admission differs from the actual native binding')
            server_package.read_package(args.native_server_zip, variant='thor_certified_startup', repository_commit=source_commit,
                                        run_id=native_build_run_id, upstream_root=args.baseline_root)
        else:
            need('server_metrics_qualification' not in report and 'server_metrics_variant' not in report
                 and 'game-package.tar.gz' not in actual_changed_runtime, 'Rollback producer reports a server overlay')
    return {'format': 1, 'mode': args.mode, 'apk': str(args.apk), **pin(apk_raw), 'application_id': APP,
        'version_name': version, 'version_code': code, 'signer_certificate_sha256': SIGNER,
        'signature_v2_verified': True, 'signature_v3_verified': True, 'binary_manifest_version_only': True,
        'runtime_inventory_verified': True, 'native_inventory_verified': True,
        'native_mapserver': pin(game['MapServer.exe']), 'native_mapserver_machine': 'Win32_PE32',
        'added_members': sorted(added), 'changed_members': sorted(changed), 'changed_native_members': changed_native,
        'candidate_source': source_commit if args.mode != 'donor' else None,
        'audit_script': pin(Path(__file__).read_bytes()),
        'dex_independently_recompiled': independent_dex is not None,
        'independent_dex_comparison': independent_dex, 'java_source_metadata_compared_to_frozen_git': args.mode != 'donor',
        'native_startup_instrumentation_static_check': {'performed': metrics,
            'passed': True if metrics else None, 'method': 'ASCII_literal_presence_in_actual_APK_MapServer_PE',
            'required_markers': list(STARTUP_MARKERS) if metrics else [], 'execution_proven': False},
        'native_build_run_id': native_build_run_id if metrics else None,
        'arm64_client_build_run_id': native_build_run_id if args.mode != 'donor' else None,
        'qualified_runtime_run_id': args.runtime_run_id, 'source_guest_bytes_verified': args.mode != 'donor',
        'external_arm64_package_compared': args.armport_zip is not None,
        'runtime_executed_by_audit': False, 'device_validated': False, 'startup_performance_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('donor', 'candidate', 'rollback'), required=True)
    for name in ('apk', 'donor', 'repo', 'tools', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    for name in ('build-report', 'native-server-zip', 'armport-zip', 'baseline-root', 'expected-dex', 'dex-preflight-report'): parser.add_argument('--' + name, type=Path)
    parser.add_argument('--source-commit', help='Exact API-verified candidate source commit (required for candidate/rollback)')
    parser.add_argument('--native-build-run-id', type=int, help='Exact API-verified native/client build run ID (required for candidate/rollback)')
    parser.add_argument('--runtime-run-id', type=int)
    args = parser.parse_args()
    if args.source_commit is not None and not re.fullmatch('[0-9a-f]{40}', args.source_commit):
        parser.error('--source-commit must be exactly 40 lowercase hexadecimal characters')
    if args.native_build_run_id is not None and args.native_build_run_id <= 0:
        parser.error('--native-build-run-id must be a positive integer')
    if args.runtime_run_id is not None and args.runtime_run_id <= 0:
        parser.error('--runtime-run-id must be a positive integer')
    if args.mode != 'donor' and (args.source_commit is None or args.native_build_run_id is None):
        parser.error('candidate/rollback require --source-commit and --native-build-run-id')
    if bool(args.expected_dex) != bool(args.dex_preflight_report):
        parser.error('--expected-dex and --dex-preflight-report must be supplied together')
    if args.mode == 'donor' and args.expected_dex:
        parser.error('independent candidate DEX comparison does not apply to donor mode')
    need(args.mode == 'donor' or args.build_report is not None, 'Candidate/rollback producer report required')
    need(args.mode != 'candidate' or args.baseline_root is not None, 'Candidate source certificate baseline required')
    result = execute(args)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('mode', 'bytes', 'sha256', 'native_mapserver', 'startup_performance_validated')}, sort_keys=True))


if __name__ == '__main__': main()
