#!/usr/bin/env python3
"""Compose/admit a new MSSQL DbServer with the retained diagnostic-name repair.

The old checksum-only PE remains historical evidence. This driver never starts
a service and does not compose PostgreSQL, Wine or saved-character overlays.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

import hosted_db_checksum_candidate as base
from manual_runtime_preflight import PE

HERE=Path(__file__).resolve().parent
PREFIX='native-android/engine/auth-interop/'
SCHEMA='coh-hosted-mssql-dbserver-threadname-build-v1'
BINARY='DbServer-threadname-candidate.exe'
THREAD='libs/UtilitiesLib/src/utils/utils.c'
THREAD_ORIGINAL='9ed817dc9dd6233fe5e06d7d0958ff9ae87aaec9c159d0c86dd8b129f55a1ecf'
THREAD_FIXED='ebcb8d4a08f752abc9f7e9e4cbf7434f977f4144e93f269ee15402bf62353cff'
PATCH='patches/levelup-ui-repair/0001-pg-empty-row-witness.patch'
PATCH_SHA='66653e01f415ba00f8e65655b8e9db1e1bbb21d76dd54b3bb4741ea13032671b'
HUNK_SHA='a1fb86bbf9e02cf048ced2d3f2f4c295fbab2f7eb3b9a227e30573bbed1aa04c'
OLD_ARCHIVE=PREFIX+'evidence/independent-db-build-39000395572/artifact.zip'
OLD_ARCHIVE_SHA='2eb66715cb8b35d82580971b60734a92b48c91e2a557cb253d39b7fdafef6ee7'
OLD_RECEIPT_SHA='51e72ef676b3db845ec4f72d1a0e856f5f34b4470050ee388087c06e843a3334'
OLD_BINARY_SHA='9dd91e456484c3fde1d9832163c2bbdad97d6a3f4db4db6a7773fddffe3319c3'
MATRIX_SHA='c17afbf163cccb5c924138efffe25e3d788c4f851cbc64b2a7988ccb42fd0503'
HISTORICAL_COMMIT='be955678b4b82f889b31c4071b3b979b0aef6771'
HISTORICAL_PINS={
 'tools/prepare_schema_source.py':'b4874d063c4f69e98120bc52a5611b213ed5d54af3926fca7fa9ab93a3e39b91',
 'tools/prepare_runtime.py':'20f97eddb239bda51ab7fee816407069daa74fd6122f6b2612e5269f5cfc7433',
 'tools/package_reference_runtime.py':'53de7076e7798b527e8d6cb823d877693668c3474b32cad810ac4fe752f3dd59',
 'tools/android/interactive/test_reopen_dbserver_thread_name.py':'54713652ed7409c4b3a948d9d6c7f55ed748df0ed77a7f557e4205682a1dce4a',
 'tools/android/interactive/package_levelup_ui_repair_dbserver.py':'48bf06d780ec0de60fdf7ffc1259d742ef908b56af587d700e5aab1ebf8b8deb',
 'docs/android-evidence/reopen-startup-repair-0.13.13-publication.json':'f44575ec47e788f28868d3c658442a3a1d5f151937b0ace8ade612ab65c48749'}
CHANGED=[base.RELATIVE,THREAD]
POLICY=dict(base.POLICY,source_profile='MSSQL-checksum-and-retained-diagnostic-threadname',
            diagnostic_threadname_repair=True,global_formatter_changed=False)
PLATFORM_DLLS={'odbc32.dll','iphlpapi.dll','ws2_32.dll','winmm.dll','advapi32.dll','user32.dll','gdi32.dll','kernel32.dll'}
INPUTS=tuple(PREFIX+name for name in base.INPUTS)+(PREFIX+'deployment/manual_runtime_preflight.py',PREFIX+'deployment/hosted_db_threadname_candidate.py',
 PREFIX+'deployment/test_db_threadname_candidate.py',PATCH,*HISTORICAL_PINS,OLD_ARCHIVE)
PREPARED={'original-clientcommLogin.c','candidate-clientcommLogin.c','checksum-failclosed.patch',
 'candidate-manifest.json','original-utils.c','candidate-utils.c','retained-threadname.patch',
 'threadname-manifest.json','retained-policy-matrix.json'}
FILES=PREPARED|{BINARY,'composition-qualification.json','candidate-CMakeCache.txt','source-file-map.json',
 'archive-original-source.log','configure-db-candidate.log','build-db-candidate.log'}


def digest(raw):return hashlib.sha256(raw).hexdigest()


def read_pinned(path,pin,limit=base.prior.LOG_LIMIT):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise ValueError('threadname_pinned_file_shape')
    raw=path.read_bytes()
    if digest(raw)!=pin:raise ValueError('threadname_pinned_file_identity')
    return raw


def repair_hunk(root):
    # Select the already-authored section verbatim. Never restate its C body.
    raw=read_pinned(root/PATCH,PATCH_SHA)
    marker=('--- a/'+THREAD+'\n').encode()
    if raw.count(marker)!=1:raise ValueError('threadname_reference_section_count')
    hunk=raw[raw.index(marker):]
    if digest(hunk)!=HUNK_SHA or hunk.count(b'+++ b/')!=1:
        raise ValueError('threadname_reference_section_identity')
    return hunk


def apply_retained_hunk(root,destination):
    helper=root/'tools/prepare_schema_source.py'
    for name in ('tools/prepare_schema_source.py','tools/prepare_runtime.py','tools/package_reference_runtime.py'):
        read_pinned(root/name,HISTORICAL_PINS[name])
    # Reuse the existing checked git-apply implementation without its PG recipe.
    before=list(sys.path)
    try:
        sys.path.insert(0,str(root/'tools'))
        spec=importlib.util.spec_from_file_location('coh_threadname_retained_patch_applier',helper)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.apply_patch(destination,repair_hunk(root))
    finally:sys.path[:]=before


def old_evidence(root):
    archive=root/OLD_ARCHIVE
    read_pinned(archive,OLD_ARCHIVE_SHA,2*1024*1024)
    with tempfile.TemporaryDirectory(prefix='coh-threadname-old-evidence-') as temp:
        directory=Path(temp)
        with zipfile.ZipFile(archive) as source:
            if set(source.namelist())!=base.FILES|{'receipt.json'} or len(source.namelist())!=len(set(source.namelist())):
                raise ValueError('threadname_old_archive_members')
            for info in source.infolist():
                if info.file_size>base.prior.LOG_LIMIT or Path(info.filename).name!=info.filename:
                    raise ValueError('threadname_old_archive_bound')
                (directory/info.filename).write_bytes(source.read(info))
        admission=base.admit(directory,OLD_RECEIPT_SHA,OLD_BINARY_SHA)
        matrix=read_pinned(directory/'host-policy-matrix.json',MATRIX_SHA)
        source_map=json.loads((directory/'source-file-map.json').read_text())['files']
        original,_=base.source_bytes(root)
        source_map[base.RELATIVE]=digest(original)
        if len(source_map)!=5995 or source_map.get(THREAD)!=THREAD_ORIGINAL:
            raise ValueError('threadname_old_source_inventory')
    return source_map,matrix,admission


def source_inputs(root):
    originals,matrix,admission=old_evidence(root)
    if base.source_map(root/'upstream/ouroboros',originals)!=originals:
        raise ValueError('threadname_original_source_map')
    repair_hunk(root)
    for name,pin in HISTORICAL_PINS.items():read_pinned(root/name,pin)
    history=json.loads((root/'docs/android-evidence/reopen-startup-repair-0.13.13-publication.json').read_bytes())
    if (history.get('repository_commit')!=HISTORICAL_COMMIT or history.get('workflow_run_id')!=37324515114
            or history.get('native_startup_contract',{}).get('scope')!='x_beginthreadex_diagnostic_name_storage_only'
            or history.get('tests_run')!=985 or history.get('skipped')!=0
            or len(history.get('startup_thread_name_fixtures',[]))!=11):
        raise ValueError('threadname_retained_fixture_scope')
    return originals,matrix,admission


def prepare(root,directory):
    root=Path(root).resolve();directory=Path(directory).resolve()
    if directory.exists() or directory.is_symlink() or directory.is_relative_to(root/'upstream'):
        raise ValueError('threadname_new_external_directory_required')
    originals,matrix,old=source_inputs(root)
    checksum=base.prepare(root,directory)
    original=read_pinned(root/'upstream/ouroboros'/THREAD,THREAD_ORIGINAL)
    with tempfile.TemporaryDirectory(prefix='coh-threadname-source-') as temp:
        source=Path(temp);path=source/THREAD;path.parent.mkdir(parents=True);path.write_bytes(original)
        apply_retained_hunk(root,source)
        fixed=read_pinned(path,THREAD_FIXED)
    (directory/'original-utils.c').write_bytes(original)
    (directory/'candidate-utils.c').write_bytes(fixed)
    (directory/'retained-threadname.patch').write_bytes(repair_hunk(root))
    (directory/'retained-policy-matrix.json').write_bytes(matrix)
    result={'schema':SCHEMA+'-source','source_tree':base.prior.ORIGINAL_TREE,'changed_paths':CHANGED,
      'source_profile':POLICY['source_profile'],'reference_patch':PATCH,'reference_patch_sha256':PATCH_SHA,
      'reference_threadname_section_sha256':HUNK_SHA,'original_utils_sha256':THREAD_ORIGINAL,
      'candidate_utils_sha256':THREAD_FIXED,'checksum_manifest':checksum,
      'old_candidate_archive_sha256':OLD_ARCHIVE_SHA,'old_candidate_receipt_sha256':OLD_RECEIPT_SHA,
      'old_candidate_binary_sha256':OLD_BINARY_SHA,'retained_policy_matrix_sha256':MATRIX_SHA,
      'retained_thread_fixture_source_sha256':HISTORICAL_PINS,
      'historical_thread_fixture_run_id':37324515114,'old_candidate_admitted':old['admitted'],
      'original_file_count':len(originals),'changed_global_formatter':False,
      'checksum_version_or_auth_policy_changed_by_threadname_repair':False,
      'service_executed':False,'accepted_runtime_replaced':False}
    (directory/'threadname-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_source_map(root):
    originals,_,_=source_inputs(root)
    candidate=dict(originals)
    raw,_=base.source_bytes(root)
    candidate[base.RELATIVE]=digest(base.replace_checksum(raw));candidate[THREAD]=THREAD_FIXED
    return originals,candidate


def stage_source(root,source,prepared):
    originals,candidate=expected_source_map(root)
    if base.source_map(source,originals)!=originals:raise ValueError('threadname_staged_original_map')
    # Reuse the exact checksum staging guard, then the existing patch applier.
    base.stage_source((prepared/'original-clientcommLogin.c').read_bytes(),source)
    apply_retained_hunk(root,source)
    if base.source_map(source,originals)!=candidate:raise ValueError('threadname_staged_composition_map')
    return candidate


def input_state(root):
    return {'repository_commit':base.prior.capture(['git','-C',root,'rev-parse','HEAD']),
            'project_inputs_sha256':{name:base.prior.sha(root/name) for name in INPUTS}}


def committed_inputs(root,commit):
    if not isinstance(commit,str) or not base.re.fullmatch('[a-f0-9]{40}',commit):
        raise ValueError('threadname_expected_commit')
    if base.prior.capture(['git','-C',root,'rev-parse',commit+':upstream/ouroboros'])!=base.prior.ORIGINAL_TREE:
        raise ValueError('threadname_original_tree')
    result={}
    for name in INPUTS:
        try:raw=subprocess.check_output(['git','-C',str(root),'show',commit+':'+name],timeout=30,stderr=subprocess.PIPE)
        except subprocess.SubprocessError:raise ValueError('threadname_input_not_owned_by_commit') from None
        if root.joinpath(name).is_symlink() or raw!=root.joinpath(name).read_bytes():
            raise ValueError('threadname_input_not_owned_by_commit')
        result[name]=digest(raw)
    return result


def require_own_checkout(root):
    if (Path(__file__).resolve()!=root/PREFIX/'deployment/hosted_db_threadname_candidate.py'
            or Path(base.__file__).resolve()!=root/PREFIX/'deployment/hosted_db_checksum_candidate.py'
            or Path(sys.modules[PE.__module__].__file__).resolve()!=root/PREFIX/'deployment/manual_runtime_preflight.py'):
        raise ValueError('threadname_executed_helper_checkout')


def admit_composition(root,path,pin,commit):
    value=json.loads(read_pinned(path,pin,1024*1024))
    if (value.get('schema')!='coh-db-threadname-composition-tests-v1' or value.get('passed') is not True
            or any(type(value.get(k)) is not int or value[k]!=n for k,n in (('failures',0),('errors',0),('skipped',0),('tests_run',7)))
            or value.get('service_executed') is not False
            or value.get('old_policy_or_formatter_suites_repeated') is not False
            or value.get('actual_win32_compile_verified') is not False or value.get('accepted_runtime_replaced') is not False
            or value.get('original_source_tree')!=base.prior.ORIGINAL_TREE or value.get('changed_source_paths')!=CHANGED
            or value.get('reference_patch_sha256')!=PATCH_SHA or value.get('reference_threadname_section_sha256')!=HUNK_SHA
            or value.get('old_candidate_archive_sha256')!=OLD_ARCHIVE_SHA or value.get('old_candidate_binary_sha256')!=OLD_BINARY_SHA
            or value.get('source_inputs_sha256')!=committed_inputs(root,commit)):
        raise ValueError('threadname_composition_qualification')
    return value


def check_artifacts(root,directory):
    # Regenerate only preparation metadata; no compiler or old suite executes.
    with tempfile.TemporaryDirectory(prefix='coh-threadname-admit-source-') as temp:
        expected=Path(temp)/'prepared';prepare(root,expected)
        for name in PREPARED:
            if directory.joinpath(name).is_symlink() or directory.joinpath(name).read_bytes()!=expected.joinpath(name).read_bytes():
                raise ValueError('threadname_prepared_artifact_identity')


def admit(root,directory,receipt_sha256,binary_sha256):
    root=Path(root).resolve();directory=Path(directory).resolve()
    require_own_checkout(root)
    value=json.loads(read_pinned(directory/'receipt.json',receipt_sha256,1024*1024))
    if (value.get('schema')!=SCHEMA or value.get('passed') is not True or value.get('build_policy')!=POLICY
            or value.get('original_source_tree')!=base.prior.ORIGINAL_TREE
            or any(value.get(k) is not True for k in ('source_inputs_unchanged','all_staged_original_files_unchanged_after_build','helper_and_head_unchanged'))
            or any(value.get(k) is not False for k in ('service_executed','accepted_runtime_replaced','live_authenticated_db_login_verified'))):
        raise ValueError('threadname_build_scope')
    if not isinstance(value.get('files'),dict) or set(value['files'])!=FILES:
        raise ValueError('threadname_build_files')
    if {p.name for p in directory.iterdir()}!=FILES|{'receipt.json'}:raise ValueError('threadname_artifact_inventory')
    for name,record in value['files'].items():
        path=directory/name;raw=read_pinned(path,record.get('sha256'),256*1024*1024 if name==BINARY else base.prior.LOG_LIMIT)
        if record!={'bytes':len(raw),'sha256':digest(raw)}:raise ValueError('threadname_artifact_record')
    check_artifacts(root,directory)
    state=value.get('input_state_before');commit=value.get('repository_commit')
    expected={'repository_commit':commit,'project_inputs_sha256':committed_inputs(root,commit)}
    if state!=expected or state!=value.get('input_state_after'):raise ValueError('threadname_build_input_stability')
    admit_composition(root,directory/'composition-qualification.json',value['composition_qualification_sha256'],commit)
    originals,candidate=expected_source_map(root)
    source=json.loads((directory/'source-file-map.json').read_text())
    expected_map={'source_tree':base.prior.ORIGINAL_TREE,'changed_paths':CHANGED,'files':candidate,
                  'unchanged_after_build':True,'changed_original_paths':[]}
    if source!=expected_map or value.get('source_file_map_sha256')!=digest(json.dumps(candidate,sort_keys=True).encode()):
        raise ValueError('threadname_build_complete_source_map')
    base.validate_commands(value.get('commands'),value.get('command_paths'),commit)
    for row in value['commands']:
        if (type(row.get('returncode')) is not int or row['returncode']!=0 or row.get('log_truncated') is not False
                or row.get('log_sha256')!=base.prior.sha(directory/(row['name']+'.log'))):
            raise ValueError('threadname_build_command_result')
    binary=base.prior.pe_identity(directory/BINARY,3)
    if binary['sha256']!=binary_sha256 or value.get('candidate_binary')!=binary or binary_sha256==OLD_BINARY_SHA:
        raise ValueError('threadname_new_binary_identity')
    if set(PE((directory/BINARY).read_bytes()).imports())!=PLATFORM_DLLS or value.get('platform_imports')!=sorted(PLATFORM_DLLS):
        raise ValueError('threadname_nonplatform_imports')
    return {'admitted':True,'schema':SCHEMA+'-admission','binary':binary,'receipt_sha256':receipt_sha256,
            'changed_source_paths':CHANGED,'old_candidate_binary_sha256':OLD_BINARY_SHA,
            'service_executed':False,'accepted_runtime_replaced':False,
            'live_authenticated_db_login_verified':False,'normal_version_or_checksum_acceptance_verified':False}


def build(args):
    root,output=args.source_root.resolve(),args.output.resolve()
    require_own_checkout(root)
    identity=base.prior.require_hosted(root,output,args.expected_commit)
    inputs=committed_inputs(root,args.expected_commit)
    admit_composition(root,args.composition_qualification,args.expected_composition_qualification_sha256,args.expected_commit)
    output.mkdir(parents=True)
    proof=dict(identity,schema=SCHEMA,passed=False,build_policy=POLICY,service_executed=False,
               accepted_runtime_replaced=False,live_authenticated_db_login_verified=False,
               composition_qualification_sha256=args.expected_composition_qualification_sha256)
    initial=input_state(root);proof['input_state_before']=initial
    if initial!={'repository_commit':args.expected_commit,'project_inputs_sha256':inputs}:
        raise ValueError('threadname_head_before_build')
    runner=base.BuildCommands(output)
    try:
        patch=Path(os.environ['ProgramFiles'])/'Git/usr/bin/patch.exe'
        if not patch.is_file():raise ValueError('qualified_patch_tool_unavailable')
        with tempfile.TemporaryDirectory(prefix='coh-db-threadname-build-',dir=os.environ['RUNNER_TEMP']) as temp:
            temp=Path(temp);prepared=temp/'candidate';prepare(root,prepared)
            for path in prepared.iterdir():shutil.copy2(path,output/path.name)
            shutil.copy2(args.composition_qualification,output/'composition-qualification.json')
            archive=temp/'original-source.tar';source=temp/'source/upstream/ouroboros';build_dir=temp/'build'
            proof['command_paths']={'root':str(root),'source':str(source),'build':str(build_dir),'patch':str(patch),'archive':str(archive)}
            runner.run('archive-original-source',['git','-C',root,'archive','--format=tar','--output='+str(archive),args.expected_commit,'upstream/ouroboros'])
            originals,_=expected_source_map(root)
            with tarfile.open(archive) as tar:
                if base.archive_map(tar)!=originals:raise ValueError('threadname_archived_original_map')
                tar.extractall(temp/'source',filter='data')
            candidate=stage_source(root,source,prepared)
            source_record={'source_tree':base.prior.ORIGINAL_TREE,'changed_paths':CHANGED,'files':candidate,
                           'unchanged_after_build':False,'changed_original_paths':None}
            map_path=output/'source-file-map.json';map_path.write_text(json.dumps(source_record,indent=2)+'\n')
            proof['source_file_map_sha256']=digest(json.dumps(candidate,sort_keys=True).encode())
            configure,compile_command=base.commands(source,build_dir,patch)
            runner.run('configure-db-candidate',configure,timeout=900)
            runner.run('build-db-candidate',compile_command,timeout=1800)
            binary=build_dir/'bin/OptDebug/DbServer.exe';proof['candidate_binary']=base.prior.pe_identity(binary,3)
            imports=set(PE(binary.read_bytes()).imports())
            if imports!=PLATFORM_DLLS:raise ValueError('threadname_nonplatform_imports')
            proof['platform_imports']=sorted(imports)
            shutil.copy2(binary,output/BINARY);shutil.copy2(build_dir/'CMakeCache.txt',output/'candidate-CMakeCache.txt')
            after=base.source_map(source,candidate);changed=[name for name in candidate if candidate[name]!=after[name]]
            source_record.update(unchanged_after_build=not changed,changed_original_paths=changed)
            map_path.write_text(json.dumps(source_record,indent=2)+'\n')
            proof['all_staged_original_files_unchanged_after_build']=not changed
            proof['passed']=not changed and proof['candidate_binary']['sha256']!=OLD_BINARY_SHA
    except Exception as error:proof['failure']=str(error) if isinstance(error,ValueError) else type(error).__name__
    finally:
        proof['commands']=runner.records
        try:
            proof['input_state_after']=input_state(root)
            proof['helper_and_head_unchanged']=initial==proof['input_state_after']
            proof['source_inputs_unchanged']=inputs==committed_inputs(root,args.expected_commit)
        except Exception:proof['helper_and_head_unchanged']=proof['source_inputs_unchanged']=False
        proof['passed']=proof['passed'] and proof['helper_and_head_unchanged'] and proof['source_inputs_unchanged']
        proof['files']={p.name:{'bytes':p.stat().st_size,'sha256':base.prior.sha(p)} for p in output.iterdir() if p.is_file() and p.name!='receipt.json'}
        (output/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='operation',required=True)
    p=sub.add_parser('prepare');p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('build');p.add_argument('--source-root',type=Path,required=True);p.add_argument('--expected-commit',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--composition-qualification',type=Path,required=True)
    p.add_argument('--expected-composition-qualification-sha256',required=True)
    p=sub.add_parser('admit');p.add_argument('--source-root',type=Path,required=True);p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--expected-receipt-sha256',required=True);p.add_argument('--expected-binary-sha256',required=True)
    args=parser.parse_args()
    if args.operation=='prepare':
        result=prepare(args.source_root,args.output);print(json.dumps({'prepared':True,'changed_source_paths':CHANGED,'service_executed':False}))
    elif args.operation=='build':
        result=build(args);print(json.dumps({'passed':result['passed'],'failure':result.get('failure'),'service_executed':False}));raise SystemExit(0 if result['passed'] else 1)
    else:print(json.dumps(admit(args.source_root,args.stage,args.expected_receipt_sha256,args.expected_binary_sha256)))
