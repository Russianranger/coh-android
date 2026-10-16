#!/usr/bin/env python3
"""Read-only review of retained CoH host/ABI and Android qualification artifacts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
p.add_argument('--repo', type=Path, required=True)
p.add_argument('--source', required=True)
p.add_argument('--kind', choices=('primary', 'catalog'), required=True)
p.add_argument('--run', type=int, required=True)
p.add_argument('--host-artifact', type=int, required=True)
p.add_argument('--android-artifact', type=int, required=True)
a = p.parse_args()
root, host = a.root.resolve(), a.root.resolve() / 'host'
digest = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
read = lambda f: json.loads(f.read_text())
git = lambda *args: subprocess.check_output(['git', '-C', str(a.repo), *args])
tree = git('rev-parse', a.source + '^{tree}').decode().strip()
q, m, e = (read(host / 'qualification.json'), read(host / 'android-execution-manifest.json'),
           read(root / 'android-execution/receipt.json'))
assert q['passed'] and not q['errors']
assert q['source_revision'] == q['source_revision_end'] == m['source_revision'] == e['source_revision'] == a.source
assert not q['source_git_status_porcelain'] and not q['source_git_status_porcelain_end']
assert not q['source_worktree_dirty'] and not m['source_worktree_dirty']
assert q['android_manifest_sha256'] == e['manifest_sha256'] == digest(host / 'android-execution-manifest.json')
assert e['passed'] and e['android_executed'] and e['emulator_qualified'] and not e['errors']
assert e['device_is_emulator'] and e['android_sdk'] == 33 and e['abi'] == 'x86_64'
assert e['temporary_files_removed'] and not e['physical_android_executed']
claims = ('accepted_apks_rebuilt', 'actual_server_interoperability_verified', 'full_live_world_verified',
          'gates25_27_complete', 'physical_thor_accepted', 'real_account_login_verified')
for key in claims:
    assert q[key] is False and m[key] is False and e[key] is False
report = {'run': a.run, 'kind': a.kind, 'source_revision': a.source, 'source_tree': tree,
          'host_artifact': a.host_artifact, 'host_archive_sha256': digest(root / 'host.zip'),
          'android_artifact': a.android_artifact, 'android_archive_sha256': digest(root / 'android-execution.zip'),
          'host_qualification_sha256': digest(host / 'qualification.json'),
          'manifest_sha256': digest(host / 'android-execution-manifest.json'),
          'android_receipt_sha256': digest(root / 'android-execution/receipt.json'),
          'suites': {}, 'android_sdk': 33, 'executed_abi': 'x86_64', 'arm64_built_only': True,
          'temporary_files_removed': True, 'authentic_catalog_captured': False,
          'renderer_activation_authorized': False, 'gates25_27_complete': False}

def source_map(values):
    for path, value in values.items():
        actual = 'native-android/' + path if path.startswith('engine/') else path
        assert hashlib.sha256(git('show', a.source + ':' + actual)).hexdigest() == value, actual

def elf(binary, abi, sha):
    data = binary.read_bytes()
    assert digest(binary) == sha and data[:6] == bytes((127, 69, 76, 70, 2, 1))
    assert struct.unpack_from('<H', data, 18)[0] == {'arm64-v8a': 183, 'x86_64': 62}[abi]

if a.kind == 'catalog':
    assert q['android_built'] and q['source_sha256'] == m['source_sha256'] == e['source_sha256']
    assert e['qualification_sha256'] == digest(host / 'qualification.json')
    source_map(m['source_sha256'])
    report['aggregate_source_file_count'] = len(m['source_sha256'])
    exact = root / 'exact-driver'
    exact.mkdir(exist_ok=True)
    for name in ('common.py', 'run_android.py'):
        (exact / name).write_bytes(git('show', a.source + ':native-android/engine/scenecatalog-qualification/' + name))
    sys.path.insert(0, str(exact))
    import run_android
    run_android.validate(host, m, 'x86_64')
    report['exact_source_driver_admission_passed'] = True

assert set(e['suites']) == set(m['suites'])
for name, suite in m['suites'].items():
    receipt = read(host / suite['host_receipt'])
    assert digest(host / suite['host_receipt']) == suite['host_receipt_sha256']
    assert receipt['passed'] and all(value == suite['expected'] for value in receipt['checks'].values())
    source_map(receipt['source_sha256'])
    if 'source_revision' in receipt:
        assert receipt['source_revision'] == a.source and receipt['source_tree'] == tree
    for clean in ('source_worktree_clean_before', 'source_worktree_clean_after'):
        if clean in receipt:
            assert receipt[clean] is True
    actual = e['suites'][name]
    assert actual['passed'] and actual['android_executed'] and actual['result'] == suite['expected']
    assert actual['binary_sha256'] == suite['abis']['x86_64']['sha256']
    assert actual['build_receipt_sha256'] == suite['abis']['x86_64']['receipt_sha256']
    record = {'checks': suite['expected']['checks'], 'declared_source_byte_maps_verified': True,
              'host_sanitizers_android_equal': True, 'builds': {}}
    for key, hkey in (('fixture', 'fixtures_sha256'), ('costume_fixture', 'costume_fixtures_sha256'), ('lookup_fixture', 'lookup_fixtures_sha256')):
        if suite.get(key):
            fixture = suite[key]
            assert digest(host / fixture['path']) == fixture['sha256'] == receipt[hkey]
            record[hkey] = fixture['sha256']
    assert set(suite['abis']) == {'arm64-v8a', 'x86_64'}
    for abi, entry in suite['abis'].items():
        built, binary = read(host / entry['receipt']), host / entry['binary']
        assert digest(host / entry['receipt']) == entry['receipt_sha256']
        assert built['passed'] and built['abi'] == abi and built['binary'] == binary.name
        assert built['binary_sha256'] == entry['sha256'] and binary.stat().st_size == entry['bytes']
        assert built.get('executed', built.get('execution_qualified')) is False
        source_map(built['source_sha256'])
        assert all(receipt['source_sha256'][path] == sha for path, sha in built['source_sha256'].items())
        elf(binary, abi, entry['sha256'])
        for key, hkey in (('fixture', 'fixtures_sha256'), ('costume_fixture', 'costume_fixtures_sha256'), ('lookup_fixture', 'lookup_fixtures_sha256')):
            if suite.get(key):
                assert built[hkey] == suite[key]['sha256']
        record['builds'][abi] = {'binary_sha256': entry['sha256'], 'receipt_sha256': entry['receipt_sha256'],
                                 'bytes': entry['bytes'], 'executed': abi == 'x86_64'}
    report['suites'][name] = record

if a.kind == 'primary':
    adapter = read(host / 'world-adapter/qualification.json')
    ar = read(root / 'android-execution/world-adapter/receipt.json')
    batch = read(root / 'android-execution/batch.json')
    assert batch['passed'] and all(s['driver_attempted'] and s['driver_exit_code'] == 0 for s in batch['suites'].values())
    assert adapter['passed'] and adapter['source_revision'] == a.source and adapter['source_tree'] == tree
    assert adapter['clean_worktree_before'] and adapter['clean_worktree_after'] and adapter['source_inputs_unchanged']
    assert not adapter['tracked_changes_before'] and not adapter['tracked_changes_after'] and not adapter['untracked_source_inputs']
    assert adapter['host'] == adapter['address'] == adapter['undefined'] == ar['result']
    source_map(adapter['source_sha256'])
    for name, sha in adapter['fixtures_sha256'].items():
        assert digest(host / 'world-adapter' / name) == sha
    assert ar['source_revision'] == a.source and ar['source_tree'] == tree and ar['source_sha256'] == adapter['source_sha256']
    assert ar['passed'] and ar['android_executed'] and ar['emulator_qualified'] and not ar['errors']
    assert ar['temporary_files_removed'] and ar['device_test_command_attempted'] and ar['device_test_command_exit_code'] == 0 and ar['native_result_validated']
    assert ar['qualification_sha256'] == digest(host / 'world-adapter/qualification.json')
    assert ar['runner_sha256'] == hashlib.sha256(git('show', a.source + ':native-android/engine/continuation/run_adapter_android.py')).hexdigest()
    for key in claims:
        assert ar[key] is False
    record = {'checks': ar['result']['checks'], 'declared_source_byte_maps_verified': True,
              'host_sanitizers_android_equal': True, 'builds': {}}
    for abi in ('arm64-v8a', 'x86_64'):
        folder = host / 'world-adapter/android' / abi
        built = read(folder / 'build.json')
        assert built == adapter['android_builds'][abi] and built['passed'] and built['executed'] is False
        assert built['source_revision'] == a.source and built['source_tree'] == tree
        assert built['source_sha256'] == adapter['source_sha256'] and built['fixtures_sha256'] == adapter['fixtures_sha256']
        assert built['expected_native_result'] == ar['result']
        elf(folder / built['binary'], abi, built['binary_sha256'])
        if abi == 'x86_64':
            assert ar['binary_sha256'] == built['binary_sha256'] and ar['build_receipt_sha256'] == digest(folder / 'build.json')
        record['builds'][abi] = {'binary_sha256': built['binary_sha256'], 'receipt_sha256': digest(folder / 'build.json'),
                                 'executed': abi == 'x86_64'}
    report['suites']['world-adapter'] = record
    report['adapter_execution_receipt_sha256'] = digest(root / 'android-execution/world-adapter/receipt.json')
    report['batch_receipt_sha256'] = digest(root / 'android-execution/batch.json')

(root / 'independent-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'passed': True, 'source': a.source, 'kind': a.kind,
                  'checks': {name: item['checks'] for name, item in report['suites'].items()}}, indent=2))
