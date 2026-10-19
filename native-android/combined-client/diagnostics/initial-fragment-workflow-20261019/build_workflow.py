#!/usr/bin/env python3
"""Generate changed-receiver observation and focused Android qualification.

Generation executes no compiler, qualifier, server, download or release.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REL = HERE.relative_to(ROOT).as_posix()
WORKFLOW = '.github/workflows/native-initial-fragment-observation.yml'
RX = 'native-android/combined-client/diagnostics/gates25-27-thor-20261018/server-initial-investigation-worker-c'
NEW_RX = RX + '/qualified03-fragment-20261019'
REUSE = 'native-android/tools/server-initial-reuse-20261019'
PREVIOUS = ROOT / 'native-android/combined-client/diagnostics/server-initial-workflow-20261018'


def main():
    origin = json.loads((HERE / 'map-origin.json').read_bytes())
    assert origin['revision'] == 'cf1ab9f7e872467473bc50da822ee6cfc041d639'
    base = yaml.safe_load((ROOT / '.github/workflows/native-server-initial-observer.yml').read_text())
    android = yaml.safe_load((ROOT / '.github/workflows/native-gates25-27-thor.yml').read_text())
    condition = "github.repository == 'Russianranger/coh-android' && github.ref == 'refs/heads/native-android' && (github.event_name == 'workflow_dispatch' || contains(github.event.head_commit.message, '[initial-fragment]'))"
    job = copy.deepcopy(base['jobs']['original_transaction'])
    job.pop('needs')
    job['if'] = condition
    steps = job['steps']
    steps.insert(1, {'uses': 'actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
        'with': {'persist-credentials': False, 'fetch-depth': 1, 'ref': origin['revision'], 'path': 'compile-source'}})
    # Use original step identities, rather than relying on inserted positions.
    step = next(s for s in steps if s.get('name') == 'Admit this run and attempt successful changed-Map artifact')
    step['name'] = 'Recover historical successful Map compile and verify unchanged current compiler suppliers'
    step['env'] = {'GH_TOKEN': '${{ github.token }}'}
    step['run'] = ('python3 ' + REL + '/admit_reused_map.py --origin ' + REL + '/map-origin.json --output "$RUNNER_TEMP/groups-inputs/server-initial-observer"\n'
        + 'echo "INITIAL_SERVER_BUILD_SHA256=' + origin['receipt_sha256'] + '" >> "$GITHUB_ENV"\n'
        + 'python3 - <<\'PYREUSE\'\nimport hashlib,os,pathlib\np=pathlib.Path(os.environ["RUNNER_TEMP"])/"groups-inputs/server-initial-observer-recovery.json"\nwith pathlib.Path(os.environ["GITHUB_ENV"]).open("a") as out:out.write("MAP_REUSE_ARTIFACT_ADMISSION_SHA256="+hashlib.sha256(p.read_bytes()).hexdigest()+"\\n")\nPYREUSE\n')
    steps.insert(steps.index(step) + 1, {'name': 'Verify byte-exact historical and current Map compiler suppliers', 'working-directory': 'current',
        'run': 'python3 ' + REUSE + '/reuse.py --source-root . --source-revision "$GITHUB_SHA" --historical-source-root "$GITHUB_WORKSPACE/compile-source" --historical-source-revision ' + origin['revision']
        + ' --compile-directory "$RUNNER_TEMP/groups-inputs/server-initial-observer" --receipt-sha256 "$INITIAL_SERVER_BUILD_SHA256" --artifact-admission-sha256 "$MAP_REUSE_ARTIFACT_ADMISSION_SHA256"\n'})
    step = next(s for s in steps if s.get('id') == 'receive_input_admission')
    step['name'] = 'Admit newly compiled fragment-compatible receive ELF and exact current dependencies'
    step['run'] = step['run'].replace("folder/'qualified02/", "folder/'qualified03-fragment-20261019/")
    step['run'] = step['run'].replace('"accepted_roles_rebuilt":false', '"unchanged_roles_rebuilt":false')
    step = next(s for s in steps if s.get('id') == 'original_transaction')
    step['run'] = step['run'].replace('native-android/tools/server-initial-runtime-20261018/runtime.py capture', REUSE + '/runtime.py capture')
    step['run'] += '  --historical-source-root "$GITHUB_WORKSPACE/compile-source" --historical-source-revision ' + origin['revision'] + ' --artifact-admission-sha256 "$MAP_REUSE_ARTIFACT_ADMISSION_SHA256"\n'
    step['run'] = step['run'].replace('--source-revision "$GITHUB_SHA"\n', '--source-revision "$GITHUB_SHA" \\\n')
    step = next(s for s in steps if s.get('name') == 'Project only bounded numeric server and receive observations after owned cleanup')
    step['run'] = step['run'].replace('native-android/tools/server-initial-runtime-20261018/runtime.py project', REUSE + '/runtime.py project')
    for s in steps:
        if s.get('uses', '').startswith('actions/upload-artifact'):
            s['with']['name'] = s['with']['name'].replace('server-initial-public-', 'initial-fragment-public-')
    jobs = {'original_transaction': job}
    for name in ('package', 'android13', 'publish-test'):
        j = copy.deepcopy(android['jobs'][name])
        if name == 'package':
            j['if'] = condition
        for s in j['steps']:
            if 'run' in s:
                s['run'] = s['run'].replace('0.1.8', '0.1.9').replace("['version_code']=='9'", "['version_code']=='10'")
                s['run'] = s['run'].replace('gates25-27-thor-20261018/RELEASE-NOTES.md', 'gates25-27-thor-20261019-fragments/RELEASE-NOTES.md')
                if 'build_interop_peer.py' in s['run']:
                    s['run'] = s['run'].replace('build_interop_peer.py --ndk', 'build_interop_peer.py --fragment-compat --ndk')
            if s.get('uses', '').startswith('reactivecircus/android-emulator-runner'):
                s['with']['script'] = s['with']['script'].replace('interop_emulator_check.py', 'fragment_interop_emulator_check.py').replace('0.1.8', '0.1.9')
            if s.get('uses', '').startswith(('actions/upload-artifact', 'actions/download-artifact')):
                s['with']['name'] = s['with']['name'].replace('gates25-27-thor-', 'gates25-27-fragment-')
        jobs[name] = j
    # Bind inherited reviewed inputs plus every new executed supplier. The
    # explicit diff records supersessions; previous proofs are never rewritten.
    oldpins = json.loads((PREVIOUS / 'source-pins.json').read_bytes())['source_sha256']
    names = set(oldpins)
    for folder in (HERE, ROOT / REUSE, ROOT / NEW_RX,
                   ROOT / 'native-android/engine/network/diagnostics/worker-c-fragment-20261019',
                   ROOT / 'native-android/combined-client/diagnostics/gates25-27-thor-20261019-fragments'):
        names.update(p.relative_to(ROOT).as_posix() for p in folder.rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.o', '.su'))
    names.update(('native-android/engine/network/check_fragment_compat.py',
        'native-android/engine/network/tests/test_fragment_compat.c',
        'native-android/combined-client/tools/fragment_interop_emulator_check.py',
        'native-android/engine/initial-capture/test_initial_fragment_peer.c'))
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'native-android/combined-client/tools').glob('*fragment*') if p.is_file())
    names.discard(REL + '/source-pins.json')
    names.discard(REL + '/workflow-review.json')
    pins = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sorted(names)}
    changes = {n: {'before': h, 'after': pins[n]} for n, h in oldpins.items() if pins[n] != h}
    manifest = {'schema': 'coh-server-initial-workflow-source-pins-v1', 'source_sha256': pins,
        'explicit_source_supersessions': changes, 'historical_map_origin': origin,
        'changed_native_receiver_rebuilt': True, 'unchanged_map_rebuilt': False,
        'runtime_executed': False, 'world_authority': False}
    raw = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    (HERE / 'source-pins.json').write_bytes(raw)
    spec = importlib.util.spec_from_file_location('coh_initial_source_gate_generator', PREVIOUS / 'build_workflow.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    gate = old.source_gate(hashlib.sha256(raw).hexdigest()).replace(str(PREVIOUS.relative_to(ROOT)), REL).replace(old.WORKFLOW, WORKFLOW)
    next(s for s in job['steps'] if s.get('id') == 'current_source_admission')['run'] = gate
    for name in ('package', 'android13', 'publish-test'):
        jobs[name]['steps'].insert(1, {'name': 'Admit exact current raw and committed qualification inputs', 'run': gate})
    workflow = {'name': 'Native original fragment observation and Thor test',
        'on': {'push': {'branches': ['native-android'], 'paths': [WORKFLOW]}, 'workflow_dispatch': {}},
        'permissions': {'contents': 'read', 'actions': 'read'},
        'concurrency': {'group': 'native-initial-fragment-${{ github.ref }}', 'cancel-in-progress': False},
        'jobs': jobs}
    (ROOT / WORKFLOW).write_text(yaml.safe_dump(workflow, sort_keys=False, width=110))
    print(json.dumps({'workflow': WORKFLOW, 'current_source_pins': len(pins),
        'supersessions': list(changes), 'map_compile_requested': False,
        'original_transactions_requested': 1, 'generator_executed_runtime': False}))


if __name__ == '__main__':
    main()
