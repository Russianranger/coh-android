#!/usr/bin/env python3
"""Derive one changed-Map compile and one original initial-response transaction.

Generation only: no qualifier, compiler, native role or server is invoked.
Run after all newly reviewed suppliers and retained native evidence are frozen.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
REL = HERE.relative_to(ROOT).as_posix()
WORKFLOW = '.github/workflows/native-server-initial-observer.yml'
RECIPE = 'native-android/tools/server-initial-observer-20261018/recipe.py'
RUNTIME = 'native-android/tools/server-initial-runtime-20261018/runtime.py'
RX = 'native-android/combined-client/diagnostics/gates25-27-thor-20261018/server-initial-investigation-worker-c'
GENERATED_REVIEWS = {HERE / 'workflow-review.json', HERE / 'workflow-independent-worker-f-review.json',
                     ROOT / RX / 'android-receive-integration-review.json'}


def script_assignment(step, name):
    tree = ast.parse('\n'.join(step['run'].splitlines()[1:-1]))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets) and isinstance(node.value, ast.Dict):
            return ast.literal_eval(node.value)
    raise ValueError('MISSING_BASELINE_LITERAL:' + name)


def source_gate(manifest_hash, legacy_build_alias=False):
    return r"""python - <<'PYSOURCE'
import hashlib,json,os,pathlib,subprocess
if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):raise ValueError('OPTIMIZED_SOURCE_GATE')
assert os.environ['GITHUB_REPOSITORY']=='Russianranger/coh-android' and os.environ['GITHUB_REF']=='refs/heads/native-android'
root=pathlib.Path.cwd().resolve();head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head==os.environ['GITHUB_SHA']
manifest=root/'MANIFEST_PATH'
raw=manifest.read_bytes();assert hashlib.sha256(raw).hexdigest()=='MANIFEST_HASH'
value=json.loads(raw);assert value['schema']=='coh-server-initial-workflow-source-pins-v1'
pins=dict(value['source_sha256'])
for name in ['MANIFEST_PATH','WORKFLOW_PATH']:
 pins[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
entries=subprocess.check_output(['git','ls-tree','-r','-z','HEAD'])
assert len(entries)<=64*1024**2
blobs={}
for row in entries.split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1)
  if name.decode() not in pins:continue
  mode,kind,blob=meta.split();assert mode in (b'100644',b'100755') and kind==b'blob';blobs[name.decode()]=blob.decode()
assert set(blobs)==set(pins)
for name,digest in pins.items():
 path=root/name;assert path.resolve()==path and path.is_file() and not path.is_symlink()
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blobs[name]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
receipt={'schema':'coh-server-initial-current-source-gate-v1','passed':True,'source_revision':head,'source_sha256':pins,'runtime_executed':False,'world_authority':False}
for name in OUTPUT_NAMES:
 path=pathlib.Path(os.environ['RUNNER_TEMP'])/name
 with path.open('x') as stream:json.dump(receipt,stream,sort_keys=True,indent=2);stream.write('\n')
print(json.dumps({'raw_and_Git_sources_admitted':len(pins),'old_qualifiers_replayed':False,'runtime_executed':False}))
PYSOURCE
""".replace('MANIFEST_PATH', REL + '/source-pins.json').replace('MANIFEST_HASH', manifest_hash).replace('WORKFLOW_PATH', WORKFLOW).replace('OUTPUT_NAMES', repr(('server-initial-source-admission.json', 'fresh-groups-source-admission.json') if legacy_build_alias else ('server-initial-source-admission.json',)))


def main():
    win = yaml.safe_load((ROOT / '.github/workflows/native-fresh-groups-build.yml').read_text())
    lin = yaml.safe_load((ROOT / '.github/workflows/native-initial-progress-observation.yml').read_text())
    build = copy.deepcopy(next(iter(win['jobs'].values())))
    execute = copy.deepcopy(next(iter(lin['jobs'].values())))
    android = copy.deepcopy(yaml.safe_load((ROOT / '.github/workflows/native-gates25-27-thor.yml').read_text())['jobs']['package'])
    pins = script_assignment(build['steps'][3], 'source')
    superseded = {}
    for name, digest in script_assignment(execute['steps'][2], 'pins').items():
        if name in pins and pins[name] != digest:
            if name != 'native-android/engine/scenecatalog-server/capture_groups_transaction.py':
                raise ValueError('BASELINE_PIN_CONFLICT:' + name)
            superseded[name] = {'prior_map_build_hash': pins[name], 'qualified_current_progress_hash': digest}
        pins[name] = digest
    apk_proof_path = 'native-android/combined-client/diagnostics/gates25-27-thor-20261018/actual-39165446220/package/arm64-interop-dso.json'
    apk_pins = json.loads((ROOT / apk_proof_path).read_text())['reviewed_source_subset_sha256']
    for name, digest in apk_pins.items():
        if name == 'native-android/combined-client/app/src/main/cpp/interop_network.c':
            superseded[name] = {'accepted_apk_source_hash': digest, 'new_receive_projection_hash': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
            continue
        if name in pins and pins[name] != digest:
            raise ValueError('ANDROID_PIN_CONFLICT:' + name)
        pins[name] = digest
    pins[apk_proof_path] = hashlib.sha256((ROOT / apk_proof_path).read_bytes()).hexdigest()
    extra_folders = [HERE, ROOT / 'native-android/engine/initial-capture/server-initial-observer',
                     ROOT / 'native-android/tools/server-initial-observer-20261018',
                     ROOT / 'native-android/tools/server-initial-runtime-20261018', ROOT / RX,
                     ROOT / 'native-android/combined-client/diagnostics/gates25-27-thor-20261018/server-initial-review-worker-e',
                     ROOT / 'native-android/combined-client/diagnostics/gates25-27-thor-20261018/server-initial-review-worker-f']
    for folder in extra_folders:
        if not folder.is_dir():
            raise ValueError('UNFROZEN_SUPPLIER:' + str(folder.relative_to(ROOT)))
        for path in folder.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path != HERE / 'source-pins.json' and path not in GENERATED_REVIEWS:
                if path.suffix not in ('.py', '.json', '.c', '.h', '.inc', '.gz', '.md', '.stdout', '.stderr', '.txt', '.log'):
                    continue
                pins[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('.github/workflows/native-fresh-groups-build.yml', '.github/workflows/native-initial-progress-observation.yml',
                 '.github/workflows/native-gates25-27-thor.yml',
                 'native-android/combined-client/app/src/main/cpp/interop_network.c'):
        pins[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    for name, digest in pins.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('CHANGED_BASELINE:' + name)
    manifest = {'schema': 'coh-server-initial-workflow-source-pins-v1', 'source_sha256': dict(sorted(pins.items())),
                'explicit_reviewed_source_supersessions': superseded,
                'generated_output_reviews_excluded_from_inputs': sorted(p.relative_to(ROOT).as_posix() for p in GENERATED_REVIEWS),
                'new_native_and_server_observer_only': True, 'old_qualifiers_replayed': False,
                'runtime_executed': False, 'world_authority': False}
    raw = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    (HERE / 'source-pins.json').write_bytes(raw)
    gate = source_gate(hashlib.sha256(raw).hexdigest())
    build_gate = source_gate(hashlib.sha256(raw).hexdigest(), legacy_build_alias=True)
    condition = "github.repository == 'Russianranger/coh-android' && github.ref == 'refs/heads/native-android' && (github.event_name == 'workflow_dispatch' || contains(github.event.head_commit.message, '[server-initial-observer]'))"
    original_build = copy.deepcopy(build['steps'])
    build.update({'if': condition, 'outputs': {'artifact_id': '${{ steps.compile_artifact.outputs.artifact-id }}',
                    'artifact_digest': '${{ steps.compile_artifact.outputs.artifact-digest }}',
                    'receipt_sha256': '${{ steps.record.outputs.receipt_sha256 }}'}})
    build['steps'] = original_build[:3]
    build['steps'].append({'name': 'Admit reviewed raw and committed source closure before project imports', 'id': 'source_admission', 'shell': 'bash', 'run': build_gate})
    for i in (4, 5, 6, 7):
        step = original_build[i]
        for key in ('run', 'working-directory'):
            if key in step:
                step[key] = step[key].replace('C:/fgsrc', 'C:/isrc')
        if i == 4:
            step['run'] += '\npython ' + RECIPE + ' stage --source-root . --already-staged C:/isrc\nif ($LASTEXITCODE -ne 0) { throw \'Initial observer staging refused\' }\npython ' + RECIPE + ' verify-stage --source-root . --already-staged C:/isrc\nif ($LASTEXITCODE -ne 0) { throw \'Initial observer staged byte verification refused\' }\n'
        build['steps'].append(step)
    build['steps'].append({'name': 'Record and strictly admit the changed Map PE and exact source role', 'id': 'record', 'shell': 'bash', 'run':
        'python ' + RECIPE + ' record --source-root . --already-staged C:/isrc --binary C:/isrc/out/build/vs2026/bin/OptDebug/MapServer.exe --cmake-cache C:/isrc/out/build/vs2026/CMakeCache.txt --output "$RUNNER_TEMP/server-initial-compile"\n'
        + "python - <<'PYRECEIPT'\nimport hashlib,os,pathlib\np=pathlib.Path(os.environ['RUNNER_TEMP'])/'server-initial-compile/compile-only-receipt.json'\nwith pathlib.Path(os.environ['GITHUB_OUTPUT']).open('a') as out:out.write('receipt_sha256='+hashlib.sha256(p.read_bytes()).hexdigest()+'\\n')\nPYRECEIPT\n"})
    build['steps'].append({'uses': 'actions/upload-artifact@v4', 'id': 'compile_artifact', 'with':
        {'name': 'server-initial-compile-${{ github.sha }}-attempt-${{ github.run_attempt }}', 'path': '${{ runner.temp }}/server-initial-compile/', 'if-no-files-found': 'error', 'retention-days': 90}})
    build['steps'].append({'uses': 'actions/upload-artifact@v4', 'if': 'always()', 'with':
        {'name': 'server-initial-build-diagnostics-${{ github.sha }}-attempt-${{ github.run_attempt }}',
         'path': '${{ runner.temp }}/fresh-groups-build-logs/\n${{ runner.temp }}/fresh-groups-source-admission.json\n${{ runner.temp }}/fresh-groups-inputs-before.json\n${{ runner.temp }}/fresh-groups-inputs-after.json\n', 'if-no-files-found': 'warn', 'retention-days': 90}})
    steps = copy.deepcopy(execute['steps'])
    execute.update({'needs': 'compile', 'if': condition, 'timeout-minutes': 60})
    steps[2] = {'name': 'Admit reviewed current raw and committed source closure', 'id': 'current_source_admission', 'working-directory': 'current', 'run': gate}
    steps[6]['name'] = 'Recover only the unchanged admitted DbServer donor'
    steps[6]['run'] = re.sub(r'specs=\[.*?\]\ndef api', "specs=[(11772107531,38302653186,'46904ced3d7efb6218ecf92d9e44ad597d3146d0',None,50269915,'9c4ba6faafb1a62cbdd0cda45b435de1ee8358b25dc65ef4842bfa2189b70d3b','donor',64*1024**2)]\ndef api", steps[6]['run'], count=1, flags=re.S)
    steps[7] = {'name': 'Admit this run and attempt successful changed-Map artifact', 'working-directory': 'current',
        'env': {'GH_TOKEN': '${{ github.token }}', 'NEW_COMPILE_ID': '${{ needs.compile.outputs.artifact_id }}',
                'NEW_COMPILE_DIGEST': '${{ needs.compile.outputs.artifact_digest }}', 'NEW_COMPILE_RECEIPT': '${{ needs.compile.outputs.receipt_sha256 }}'}, 'run':
        'python3 ' + REL + '/admit_workflow_artifact.py --artifact-id "$NEW_COMPILE_ID" --digest "$NEW_COMPILE_DIGEST" --receipt-sha256 "$NEW_COMPILE_RECEIPT" --output "$RUNNER_TEMP/groups-inputs/server-initial-observer"\n'
        + 'python3 ' + RECIPE + ' verify-artifact --source-root . --compile-directory "$RUNNER_TEMP/groups-inputs/server-initial-observer" --expected-source-revision "$GITHUB_SHA" --receipt-sha256 "$NEW_COMPILE_RECEIPT"\n'
        + 'echo "INITIAL_SERVER_BUILD_SHA256=$NEW_COMPILE_RECEIPT" >> "$GITHUB_ENV"\n'}
    steps[10] = {'name': 'Admit retained new receive-counter ELF without rebuilding accepted roles', 'id': 'receive_input_admission', 'working-directory': 'current', 'run':
        "python3 - <<'PYNATIVE'\nimport gzip,hashlib,importlib.util,os,pathlib,sys\nroot=pathlib.Path.cwd().resolve();folder=root/'" + RX + "'\noutput=pathlib.Path(os.environ['RUNNER_TEMP'])/'groups-inputs/initial-receive';output.mkdir(mode=0o700)\nwith gzip.open(folder/'qualified02/coh-capture-initial-receive.gz','rb') as source:\n raw=source.read(1024**2+1);assert 0<len(raw)<=1024**2 and source.read(1)==b''\nbinary=output/'coh-capture-initial-receive';binary.write_bytes(raw);binary.chmod(0o700)\nreceipt=output/'build.json';receipt.write_bytes((folder/'qualified02/qualification.json').read_bytes());receipt.chmod(0o600)\nsys.path.insert(0,str(root/'native-android/engine/scenecatalog-server'));spec=importlib.util.spec_from_file_location('new_receive_admission',folder/'receive_admission.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\npin=hashlib.sha256(receipt.read_bytes()).hexdigest();module.native_input(binary,receipt,pin,root)\nwith pathlib.Path(os.environ['GITHUB_ENV']).open('a') as out:out.write('INITIAL_RECEIVE_BUILD_SHA256='+pin+'\\n')\nprint('{\"new_receive_role_admitted\":true,\"runtime_executed\":false,\"accepted_roles_rebuilt\":false}')\nPYNATIVE\n"}
    steps[12]['name'] = 'Observe one original server dispatch/send path and native receive result'
    steps[12]['run'] = steps[12]['run'].replace('native-android/engine/scenecatalog-server/capture_groups_transaction.py', RUNTIME + ' capture')
    steps[12]['run'] = steps[12]['run'].replace('groups-inputs/observer/fresh-groups-compile', 'groups-inputs/server-initial-observer').replace('--compile-receipt-sha256 28d61fc30718391fc5dd1a269f468b0f2aa83c33abe5d60413104dafd0b28f91', '--compile-receipt-sha256 "$INITIAL_SERVER_BUILD_SHA256"')
    steps[12]['run'] = steps[12]['run'].replace('groups-inputs/initial-progress/coh-capture-initial-progress', 'groups-inputs/initial-receive/coh-capture-initial-receive').replace('groups-inputs/initial-progress/build.json', 'groups-inputs/initial-receive/build.json').replace('$INITIAL_PROGRESS_BUILD_SHA256', '$INITIAL_RECEIVE_BUILD_SHA256')
    steps[12]['run'] += '  --source-revision "$GITHUB_SHA"\n' if steps[12]['run'].rstrip().endswith('\\') else ''
    steps[12]['run'] = steps[12]['run'].replace('--timeout-seconds 1200\n', '--timeout-seconds 1200 --source-revision "$GITHUB_SHA"\n')
    steps[13]['if'] = "always() && steps.receive_input_admission.outcome == 'success'"
    steps[14] = {'name': 'Project only bounded numeric server and receive observations after owned cleanup', 'if': "always() && steps.original_transaction.outcome == 'success'", 'working-directory': 'current',
        'run': 'python3 ' + RUNTIME + ' project --private-output "$RUNNER_TEMP/groups-private-result" --output out/groups-public/observer.json\n'}
    steps[15]['with']['name'] = 'server-initial-public-${{ github.sha }}-attempt-${{ github.run_attempt }}'
    steps[15]['with']['path'] = 'current/out/groups-public/summary.json\ncurrent/out/groups-public/tooling.json\ncurrent/out/groups-public/observer.json\n'
    execute['steps'] = steps
    android['if'] = condition
    android['steps'] = android['steps'][:6]
    android['steps'].insert(1, {'name': 'Admit the changed receive-report source before Android compilation', 'shell': 'bash', 'run': gate})
    android['steps'][-1]['name'] = 'Compile, lint and audit the additive ARM64 receive report without publishing a release'
    android['steps'].append({'uses': 'actions/upload-artifact@v4', 'if': 'always()', 'with':
        {'name': 'server-initial-android-compile-${{ github.sha }}-attempt-${{ github.run_attempt }}',
         'path': 'native-android/results/gates25-27-thor/arm64-package.json\nnative-android/results/gates25-27-thor/arm64-interop-dso.json\nnative-android/results/gates25-27-thor/crypto-reuse.json\nnative-android/results/gates25-27-thor/build-inputs.json\n',
         'if-no-files-found': 'warn', 'retention-days': 90}})
    workflow = {'name': 'Focused original server initial-response observation', 'on': {'push': {'branches': ['native-android'], 'paths': [WORKFLOW]}, 'workflow_dispatch': {}},
                'permissions': {'contents': 'read', 'actions': 'read'}, 'concurrency': {'group': 'native-server-initial-observer-${{ github.ref }}', 'cancel-in-progress': False},
                'jobs': {'compile': build, 'original_transaction': execute, 'android_receive': android}}
    (ROOT / WORKFLOW).write_text(yaml.safe_dump(workflow, sort_keys=False, width=110))
    print(json.dumps({'generated': WORKFLOW, 'source_pins': len(pins), 'original_transactions_requested': 1,
                      'old_qualifiers_executed': False, 'compiler_or_runtime_executed_by_generator': False}))


if __name__ == '__main__':
    main()
