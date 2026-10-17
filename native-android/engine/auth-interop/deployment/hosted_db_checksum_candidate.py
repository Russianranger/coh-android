#!/usr/bin/env python3
"""Compile/admit a standalone original MSSQL DBServer checksum candidate only.

No accepted PostgreSQL/Wine overlay, persistence fixture, reference alias,
version override, account or service is installed by this helper.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

import checksum_candidate
import hosted_auth_stage as prior
from source_audit import CHECKSUM, decoded, extract, pinned_sources

HERE=Path(__file__).resolve().parent
SCHEMA='coh-hosted-original-dbserver-checksum-build-v1'
BINARY='DbServer-checksum-candidate.exe'
RELATIVE='Common/ClientLogin/clientcommLogin.c'
POLICY={'generator':'Visual Studio 18 2026','architecture':'Win32','configuration':'OptDebug',
        'target':'DbServer','parallel':'2','source_profile':'original-MSSQL-single-checksum-change',
        'postgresql_overlay':False,'wine_overlay':False,'persistence_fixture':False,
        'mapserver':False,'beaconserver':False,'service_execution':False}
FILES={BINARY,'original-clientcommLogin.c','candidate-clientcommLogin.c','checksum-failclosed.patch',
       'candidate-manifest.json','host-policy-matrix.json','candidate-CMakeCache.txt',
       'archive-original-source.log','configure-db-candidate.log','build-db-candidate.log','source-file-map.json'}
INPUTS=('deployment/hosted_db_checksum_candidate.py','deployment/hosted_auth_stage.py',
        'deployment/checksum_candidate.py','deployment/source_audit.py','deployment/generate_odbc.py',
        'deployment/admit_schema.py','deployment/qualify_db_policy_matrix.py','deployment/source-pins.json',
        'source_oracle.py')


def input_state(root,host):
    return {'repository_commit':prior.capture(['git','-C',root,'rev-parse','HEAD']),
            'helper_inputs':{name:prior.sha(HERE.parent/name) for name in INPUTS},
            'host_qualification_sha256':prior.sha(host)}


def committed_input_hashes(root,commit):
    if not isinstance(commit,str) or not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('db_build_input_commit')
    tree=subprocess.check_output(['git','-C',str(root),'rev-parse',commit+':upstream/ouroboros'],timeout=30).decode().strip()
    if tree!=prior.ORIGINAL_TREE:raise ValueError('db_build_input_original_tree')
    prefix='native-android/engine/auth-interop/'
    return {name:hashlib.sha256(subprocess.check_output(['git','-C',str(root),'show',commit+':'+prefix+name],timeout=30)).hexdigest() for name in INPUTS}


def source_map(source,names):
    result={}
    for name in names:
        path=source/name
        if path.is_symlink() or not path.is_file():raise ValueError('db_original_source_missing_or_linked')
        result[name]=prior.sha(path)
    return result


def archive_map(tar):
    result={};prefix='upstream/ouroboros/'
    for item in tar.getmembers():
        if item.isdir():continue
        if not item.isfile() or not item.name.startswith(prefix):raise ValueError('db_original_archive_member')
        name=item.name[len(prefix):];parts=PurePosixPath(name)
        if not name or '\\' in name or parts.is_absolute() or '..' in parts.parts or name in result:raise ValueError('db_original_archive_path')
        stream=tar.extractfile(item)
        result[name]=hashlib.file_digest(stream,'sha256').hexdigest()
    if RELATIVE not in result:raise ValueError('db_original_archive_missing_checksum')
    return result


class BuildCommands(prior.Commands):
    def run(self,name,command,**kwargs):
        before=len(self.records)
        try:return super().run(name,command,**kwargs)
        finally:
            if len(self.records)>before:self.records[-1]['argv']=list(map(str,command))


def validate_commands(records,paths,commit):
    keys={'root','source','build','patch','archive'}
    if (not isinstance(paths,dict) or set(paths)!=keys
            or any(type(v) is not str or not 1<=len(v)<=4096 or '\0' in v for v in paths.values())
            or not isinstance(commit,str) or not re.fullmatch('[0-9a-f]{40}',commit)):
        raise ValueError('db_candidate_command_path_profile')
    normal={k:v.replace('\\','/') for k,v in paths.items()}
    if not normal['source'].endswith('/source/upstream/ouroboros'):raise ValueError('db_candidate_command_source_path')
    temporary=normal['source'][:-len('/source/upstream/ouroboros')]
    if normal['build']!=temporary+'/build' or normal['archive']!=temporary+'/original-source.tar' or not normal['patch'].endswith('/Git/usr/bin/patch.exe'):
        raise ValueError('db_candidate_command_path_binding')
    configure,compile_command=commands(paths['source'],paths['build'],paths['patch'])
    expected=[['git','-C',paths['root'],'archive','--format=tar','--output='+paths['archive'],commit,'upstream/ouroboros'],configure,compile_command]
    names=['archive-original-source','configure-db-candidate','build-db-candidate']
    if not isinstance(records,list) or len(records)!=3:raise ValueError('db_candidate_command_count')
    for row,name,argv in zip(records,names,expected):
        if not isinstance(row,dict) or row.get('name')!=name or row.get('argv')!=list(map(str,argv)):
            raise ValueError('db_candidate_exact_command_argv')


def source_bytes(root):
    if prior.capture(['git','-C',root,'rev-parse','HEAD:upstream/ouroboros'])!=prior.ORIGINAL_TREE:
        raise ValueError('db_candidate_original_tree')
    values,identities=pinned_sources(root)
    raw=subprocess.check_output(['git','-C',str(root),'show','HEAD:'+CHECKSUM],timeout=30)
    if raw!=values[CHECKSUM].encode():raise ValueError('db_candidate_canonical_original_required')
    return raw,identities


def replace_checksum(raw):
    text=decoded(raw)
    if text.encode()!=raw:raise ValueError('db_candidate_original_encoding')
    original=extract(text,'clientCommLoginVerifyChecksum')
    pins=json.loads((HERE/'source-pins.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=pins['sha256_utf8_lf'][CHECKSUM]:
        raise ValueError('db_candidate_original_identity')
    if text.count(original)!=1:raise ValueError('db_candidate_function_not_unique')
    return text.replace(original,checksum_candidate.CANDIDATE).encode()


def prepare(root,directory):
    if directory.exists():raise ValueError('new_candidate_directory_required')
    raw,_=source_bytes(root);candidate=replace_checksum(raw)
    directory.mkdir(parents=True)
    proof=checksum_candidate.prepare(root,directory)
    # prepare also generates two host C fixtures; do not ship them as DB sources.
    for name in ('original-policy.c','candidate-policy.c'):(directory/name).unlink()
    (directory/'original-clientcommLogin.c').write_bytes(raw)
    (directory/'candidate-clientcommLogin.c').write_bytes(candidate)
    manifest={'schema':SCHEMA+'-source','source_tree':prior.ORIGINAL_TREE,'changed_paths':[RELATIVE],
              'original_source_sha256':hashlib.sha256(raw).hexdigest(),
              'candidate_source_sha256':hashlib.sha256(candidate).hexdigest(),
              'candidate_function_sha256':proof['candidate_function_sha256'],
              'original_db_login_policy_block_sha256':proof['original_db_login_policy_block_sha256'],
              'patch_sha256':proof['patch_sha256'],'source_profile':POLICY['source_profile']}
    (directory/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def stage_source(raw,destination):
    path=destination/RELATIVE
    if path.is_symlink() or not path.is_file() or path.read_bytes()!=raw:
        raise ValueError('db_candidate_archive_identity')
    path.write_bytes(replace_checksum(raw));return prior.sha(path)


def commands(source,build,patch):
    return [
      ['cmake','-S',source,'-B',build,'-G',POLICY['generator'],'-A','Win32',
       '-DCOX_BUILD_MAPSERVER=OFF','-DCOX_BUILD_BEACONSERVER=OFF','-DPATCH_EXECUTABLE='+str(patch)],
      ['cmake','--build',build,'--config','OptDebug','--parallel','2','--target','DbServer']]


def validate_corpus(value):
    if value.get('schema')!='coh-original-db-login-dev-normal-policy-matrix-v1' or value.get('passed') is not True:
        raise ValueError('db_candidate_policy_receipt_scope')
    rows=value.get('executions')
    if not isinstance(rows,dict) or set(rows)!={name+'-'+mode for name in ('original','candidate') for mode in ('release','asan_ubsan')}:
        raise ValueError('db_candidate_policy_execution_modes')
    for name,row in rows.items():
        original=name.startswith('original-')
        expected={'passed':True,'checks':1056,'original_defect_expected':original,
                  'production_checksum_bit_refusals':0 if original else 256,
                  'provisional_checksum_bit_acceptances':768 if original else 384,'live_db_login_verified':False}
        if (json.dumps(row.get('result'),sort_keys=True)!=json.dumps(expected,sort_keys=True)
                or any(not isinstance(row.get(key),str) or not re.fullmatch('[0-9a-f]{64}',row[key])
                       for key in ('binary_sha256','generated_sha256'))):
            raise ValueError('db_candidate_policy_corpus')
    if (value.get('nondevelopment_profile_deployed') is not False
            or value.get('live_authenticated_db_login_verified') is not False
            or value.get('leak_sanitizer_enabled') is not False):raise ValueError('db_candidate_policy_scope')


def admit_host(path,expected_sha256,root):
    if path.is_symlink() or path.stat().st_size>1024*1024 or prior.sha(path)!=expected_sha256:
        raise ValueError('db_candidate_host_receipt_identity')
    value=json.loads(path.read_text());validate_corpus(value)
    raw,identities=source_bytes(root)
    base=value.get('base_checksum_source_qualification',{})
    if (value.get('qualifier_sha256')!=prior.sha(HERE/'qualify_db_policy_matrix.py')
            or base.get('candidate_function_sha256')!=hashlib.sha256(checksum_candidate.CANDIDATE.encode()).hexdigest()
            or base.get('patched_dbserver_built') is not False):raise ValueError('db_candidate_host_source_scope')
    with tempfile.TemporaryDirectory(prefix='coh-db-policy-inputs-') as temp:
        expected_base=checksum_candidate.prepare(root,Path(temp))
    for key in ('original_function_sha256','original_db_login_policy_block_sha256','patch_sha256'):
        if base.get(key)!=expected_base[key]:raise ValueError('db_candidate_host_original_policy')
    expected={name:row['sha256'] for name,row in identities.items()}
    if {name:row.get('sha256') for name,row in base.get('source_identities',{}).items()}!=expected:
        raise ValueError('db_candidate_host_original_sources')
    return value


def admit(directory,receipt_sha256,binary_sha256):
    receipt=directory/'receipt.json'
    if receipt.is_symlink() or receipt.stat().st_size>1024*1024 or prior.sha(receipt)!=receipt_sha256:
        raise ValueError('db_candidate_build_receipt_identity')
    value=json.loads(receipt.read_text())
    if (value.get('schema')!=SCHEMA or value.get('passed') is not True or value.get('build_policy')!=POLICY
            or value.get('original_source_tree')!=prior.ORIGINAL_TREE
            or value.get('source_inputs_unchanged') is not True or value.get('candidate_source_unchanged_after_build') is not True
            or value.get('all_original_source_files_unchanged_after_build') is not True
            or value.get('helper_and_head_unchanged') is not True
            or value.get('service_executed') is not False or value.get('live_authenticated_db_login_verified') is not False):
        raise ValueError('db_candidate_build_scope')
    if not isinstance(value.get('files'),dict) or set(value['files'])!=FILES:raise ValueError('db_candidate_file_set')
    for name,record in value['files'].items():
        path=directory/name;limit=256*1024*1024 if name==BINARY else prior.LOG_LIMIT
        if (path.is_symlink() or not path.is_file() or path.stat().st_size>limit
                or record!={'bytes':path.stat().st_size,'sha256':prior.sha(path)}):raise ValueError('db_candidate_file_identity')
    raw=(directory/'original-clientcommLogin.c').read_bytes();candidate=(directory/'candidate-clientcommLogin.c').read_bytes()
    manifest=json.loads((directory/'candidate-manifest.json').read_text())
    canonical_patch=(directory/'checksum-failclosed.patch').read_bytes().replace(b'\r\n',b'\n')
    expected_patch=''.join(difflib.unified_diff(raw.decode().splitlines(True),candidate.decode().splitlines(True),
                                              fromfile='a/'+CHECKSUM,tofile='b/'+CHECKSUM)).encode()
    if canonical_patch!=expected_patch:raise ValueError('db_candidate_exact_patch_diff')
    if (replace_checksum(raw)!=candidate or manifest.get('source_tree')!=prior.ORIGINAL_TREE
            or manifest.get('changed_paths')!=[RELATIVE] or manifest.get('source_profile')!=POLICY['source_profile']
            or manifest.get('original_source_sha256')!=hashlib.sha256(raw).hexdigest()
            or manifest.get('candidate_source_sha256')!=hashlib.sha256(candidate).hexdigest()
            or manifest.get('candidate_function_sha256')!=hashlib.sha256(checksum_candidate.CANDIDATE.encode()).hexdigest()
            or manifest.get('patch_sha256')!=hashlib.sha256((directory/'checksum-failclosed.patch').read_bytes().replace(b'\r\n',b'\n')).hexdigest()):
        raise ValueError('db_candidate_source_identity')
    host=json.loads((directory/'host-policy-matrix.json').read_text());validate_corpus(host)
    if (host.get('qualifier_sha256')!=prior.sha(HERE/'qualify_db_policy_matrix.py')
            or host.get('base_checksum_source_qualification',{}).get('candidate_function_sha256')!=manifest['candidate_function_sha256']
            or host.get('base_checksum_source_qualification',{}).get('original_db_login_policy_block_sha256')!=manifest.get('original_db_login_policy_block_sha256')):
        raise ValueError('db_candidate_host_source_binding')
    state=value.get('input_state_before')
    if (not isinstance(state,dict) or state!=value.get('input_state_after')
            or state.get('repository_commit')!=value.get('repository_commit')
            or state.get('helper_inputs')!=committed_input_hashes(HERE.parents[3],value.get('repository_commit'))
            or state.get('host_qualification_sha256')!=prior.sha(directory/'host-policy-matrix.json')):
        raise ValueError('db_candidate_input_stability')
    source_record=json.loads((directory/'source-file-map.json').read_text())
    files=source_record.get('files')
    if (not isinstance(files,dict) or not files or len(files)>200000
            or any(type(k) is not str or not k or PurePosixPath(k).is_absolute() or '..' in PurePosixPath(k).parts
                   or type(v) is not str or not re.fullmatch('[0-9a-f]{64}',v) for k,v in files.items())
            or files.get(RELATIVE)!=manifest['candidate_source_sha256']
            or source_record.get('source_tree')!=prior.ORIGINAL_TREE
            or source_record.get('changed_paths')!=[RELATIVE]
            or source_record.get('unchanged_after_build') is not True
            or source_record.get('changed_original_paths')!=[]
            or type(value.get('original_archived_file_count')) is not int or value['original_archived_file_count']!=len(files)
            or value.get('source_file_map_sha256')!=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()):
        raise ValueError('db_candidate_original_file_map')
    records=value.get('commands')
    validate_commands(records,value.get('command_paths'),value.get('repository_commit'))
    for row in records:
        if (type(row.get('returncode')) is not int or row['returncode']!=0 or row.get('log_truncated') is not False
                or row.get('log_sha256')!=prior.sha(directory/(row['name']+'.log'))):
            raise ValueError('db_candidate_build_command_result')
    binary=prior.pe_identity(directory/BINARY,3)
    if binary['sha256']!=binary_sha256 or value.get('candidate_binary')!=binary:raise ValueError('db_candidate_binary_identity')
    return {'admitted':True,'scope':'Caller-pinned compilation only; original MSSQL target, no accepted overlays or service execution.',
            'binary':binary,'receipt_sha256':receipt_sha256,'live_authenticated_db_login_verified':False,
            'accepted_runtime_compatibility_verified':False,'nondevelopment_version_observed':False}


def build(args):
    root,output=args.source_root.resolve(),args.output.resolve()
    identity=prior.require_hosted(root,output,args.expected_commit)
    raw,_=source_bytes(root);admit_host(args.host_qualification,args.expected_host_qualification_sha256,root)
    output.mkdir(parents=True)
    proof=dict(identity,schema=SCHEMA,passed=False,build_policy=POLICY,service_executed=False,
               live_authenticated_db_login_verified=False,accepted_runtime_compatibility_verified=False,
               nondevelopment_version_observed=False)
    initial=input_state(root,args.host_qualification)
    if initial['repository_commit']!=args.expected_commit:raise ValueError('db_candidate_head_before_build')
    proof['input_state_before']=initial
    runner=BuildCommands(output)
    try:
        patch=Path(os.environ['ProgramFiles'])/'Git/usr/bin/patch.exe'
        if not patch.is_file():raise ValueError('qualified_patch_tool_unavailable')
        with tempfile.TemporaryDirectory(prefix='coh-db-checksum-build-',dir=os.environ['RUNNER_TEMP']) as temp:
            temp=Path(temp);staged=temp/'candidate';prepare(root,staged)
            for path in staged.iterdir():shutil.copy2(path,output/path.name)
            shutil.copy2(args.host_qualification,output/'host-policy-matrix.json')
            archive=temp/'original-source.tar'
            proof['command_paths']={'root':str(root),'source':str(temp/'source/upstream/ouroboros'),
                                    'build':str(temp/'build'),'patch':str(patch),'archive':str(archive)}
            runner.run('archive-original-source',['git','-C',root,'archive','--format=tar','--output='+str(archive),args.expected_commit,'upstream/ouroboros'])
            proof['source_archive_sha256']=prior.sha(archive)
            with tarfile.open(archive) as tar:
                originals=archive_map(tar)
                tar.extractall(temp/'source',filter='data')
            source=temp/'source/upstream/ouroboros';build_dir=temp/'build'
            if source_map(source,originals)!=originals:raise ValueError('db_original_archive_extraction_changed')
            proof['candidate_source_sha256']=stage_source(raw,source)
            originals[RELATIVE]=proof['candidate_source_sha256']
            if source_map(source,originals)!=originals:raise ValueError('db_candidate_unexpected_staged_change')
            proof['original_archived_file_count']=len(originals)
            proof['source_file_map_sha256']=hashlib.sha256(json.dumps(originals,sort_keys=True).encode()).hexdigest()
            source_record={'source_tree':prior.ORIGINAL_TREE,'changed_paths':[RELATIVE],'files':originals,
                           'unchanged_after_build':False,'changed_original_paths':None}
            map_path=output/'source-file-map.json';map_path.write_text(json.dumps(source_record,indent=2)+'\n')
            configure,compile_command=commands(source,build_dir,patch)
            runner.run('configure-db-candidate',configure,timeout=900)
            runner.run('build-db-candidate',compile_command,timeout=1800)
            binary=build_dir/'bin/OptDebug/DbServer.exe'
            proof['candidate_binary']=prior.pe_identity(binary,3)
            shutil.copy2(binary,output/BINARY);shutil.copy2(build_dir/'CMakeCache.txt',output/'candidate-CMakeCache.txt')
            after=source_map(source,originals)
            changed=[name for name in originals if originals[name]!=after[name]]
            source_record.update(unchanged_after_build=not changed,changed_original_paths=changed)
            map_path.write_text(json.dumps(source_record,indent=2)+'\n')
            proof['all_original_source_files_unchanged_after_build']=not changed
            proof['candidate_source_unchanged_after_build']=prior.sha(source/RELATIVE)==proof['candidate_source_sha256']
            proof['passed']=proof['all_original_source_files_unchanged_after_build'] and proof['candidate_source_unchanged_after_build'] and prior.sha(output/BINARY)==proof['candidate_binary']['sha256']
    except Exception as error:proof['failure']=str(error) if isinstance(error,ValueError) else type(error).__name__
    finally:
        proof['commands']=runner.records
        try:
            proof['input_state_after']=input_state(root,args.host_qualification)
            proof['helper_and_head_unchanged']=proof['input_state_before']==proof['input_state_after']
        except Exception:proof['helper_and_head_unchanged']=False
        try:proof['source_inputs_unchanged']=not prior.capture(['git','-C',root,'status','--porcelain','--untracked-files=no','--','upstream/ouroboros','native-android/engine/auth-interop'])
        except Exception:proof['source_inputs_unchanged']=False
        proof['passed']=proof['passed'] and proof['source_inputs_unchanged'] and proof['helper_and_head_unchanged']
        proof['files']={p.name:{'bytes':p.stat().st_size,'sha256':prior.sha(p)} for p in output.iterdir() if p.is_file() and p.name!='receipt.json'}
        (output/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='operation',required=True)
    b=sub.add_parser('build');b.add_argument('--source-root',type=Path,required=True);b.add_argument('--expected-commit',required=True)
    b.add_argument('--output',type=Path,required=True);b.add_argument('--host-qualification',type=Path,required=True);b.add_argument('--expected-host-qualification-sha256',required=True)
    a=sub.add_parser('admit');a.add_argument('--stage',type=Path,required=True);a.add_argument('--expected-receipt-sha256',required=True);a.add_argument('--expected-binary-sha256',required=True)
    args=p.parse_args();result=build(args) if args.operation=='build' else admit(args.stage,args.expected_receipt_sha256,args.expected_binary_sha256)
    print(json.dumps(result if args.operation=='admit' else {'passed':result['passed'],'failure':result.get('failure'),'service_executed':False}))
    raise SystemExit(0 if result.get('passed',result.get('admitted',False)) else 1)
