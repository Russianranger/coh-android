"""Bind the exact completed read-only inventory and derive a compile guard lock."""
import argparse,copy,hashlib,json,re,subprocess,zipfile
from pathlib import Path,PureWindowsPath
import windows_tool_inventory as observer

HERE=Path(__file__).resolve().parent
COMMIT='d6ef33b3306c496e6d6a9ee2f8c9ab12ffdfbc05'
RUN='39005570623'
ARTIFACT=12090613318
ZIP_SHA='a9435c960839c4a4b93174d527b5d1c294ed9f964ed507ccd943cd9676e40c23'
RECEIPT_SHA='9f34ad291572a4424d17f400f05b2b9aceaabefc2d2cce23fcecbe5235a9666b'
PREFIX='native-android/engine/auth-interop/'
FALSES=('compiler_executed','cmake_executed','source_patched','dependencies_fetched','service_executed','toolchain_reviewed','compile_permit','shipping_runtime_replacement_permit')


def sha(data):return hashlib.sha256(data).hexdigest()


def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)


def path_row(row):
    if not isinstance(row,dict) or set(row)!={'path','bytes','sha256'}:raise ValueError('inventory_tool_record_shape')
    path=PureWindowsPath(row['path'])
    if not path.is_absolute() or str(path)!=row['path'] or '..' in path.parts or type(row['bytes']) is not int or not 0<row['bytes']<=256*1024*1024 or not re.fullmatch('[0-9a-f]{64}',row['sha256']):
        raise ValueError('inventory_tool_record_identity')
    return path


def verify_receipt(value,root):
    if (value.get('schema')!='coh-readonly-windows-build-tool-inventory-v1' or value.get('passed') is not True
            or value.get('repository_commit')!=COMMIT or value.get('github_run_id')!=RUN
            or value.get('image_os')!='win25-vs2026' or value.get('image_version')!='20261007.264.1'
            or value.get('source_inputs_unchanged') is not True or value.get('all_tool_inputs_stable') is not True
            or any(value.get(name) is not False for name in FALSES)):raise ValueError('inventory_receipt_scope')
    if (value.get('repository_tree')!=git(root,'rev-parse',COMMIT+'^{tree}').decode().strip()
            or value.get('original_source_tree')!=git(root,'rev-parse',COMMIT+':upstream/ouroboros').decode().strip()):raise ValueError('inventory_original_tree_identity')
    before=value.get('input_state_before')
    if not isinstance(before,dict) or before!=value.get('input_state_after') or before.get('commit')!=COMMIT or before.get('tracked_dirty')!='':raise ValueError('inventory_source_generation_stability')
    # The actual hosted checkout was CRLF. Require exactly that byte transform
    # for every immediate deployment Python file and source_oracle, not a
    # permissive choice of normalization modes on a per-file basis.
    names=git(root,'ls-tree','-r','--name-only',COMMIT+':'+PREFIX.rstrip('/')).decode().splitlines()
    expected={name for name in names if name=='source_oracle.py' or (name.startswith('deployment/') and name.count('/')==1 and name.endswith('.py'))}
    reported=before.get('helper_inputs',{});normalized={n.replace('\\','/'):h for n,h in reported.items()}
    if len(reported)!=len(normalized) or len(expected)!=61 or set(normalized)!=expected:raise ValueError('inventory_complete_helper_domain')
    source_map={}
    for name in sorted(expected):
        blob=git(root,'show',COMMIT+':'+PREFIX+name)
        if b'\r' in blob:raise ValueError('inventory_git_lf_profile_changed')
        converted=blob.replace(b'\n',b'\r\n')
        if sha(converted)!=normalized[name]:raise ValueError('inventory_explicit_crlf_source_binding')
        source_map[name]={'git_blob_sha256':sha(blob),'actual_crlf_sha256':sha(converted),'git_bytes':len(blob),'actual_bytes':len(converted)}
    observation=value.get('observation_before')
    if not isinstance(observation,dict) or observation!=value.get('observation_after'):raise ValueError('inventory_tool_observation_stability')
    vs=PureWindowsPath(value.get('vs_installation',''));toolset=value.get('vc_toolset_version')
    if vs!=PureWindowsPath('C:/Program Files/Microsoft Visual Studio/18/Enterprise') or toolset!='14.51.36231':raise ValueError('inventory_vs_toolset_identity')
    tools=observation.get('tools',{})
    if set(tools)!={'cl','link','ml','msbuild','git','patch','cmake'}:raise ValueError('inventory_seven_common_tools')
    for name,row in tools.items():
        path=path_row(row)
        if name in ('cl','link','ml') and path!=vs/('VC/Tools/MSVC/'+toolset+'/bin/Hostx64/x86/'+name+'.exe'):raise ValueError('inventory_compiler_owner')
        if name=='msbuild' and path!=vs/'MSBuild/Current/Bin/MSBuild.exe':raise ValueError('inventory_msbuild_owner')
    for name,expected_path in {'git':'C:/Program Files/Git/bin/git.exe','patch':'C:/Program Files/Git/usr/bin/patch.exe','cmake':'C:/Program Files/CMake/bin/cmake.exe'}.items():
        if PureWindowsPath(tools[name]['path'])!=PureWindowsPath(expected_path):raise ValueError('inventory_primary_tool_path')
    versions=observation.get('file_versions',{})
    if versions.get('cl')!='19.51.36260.0' or versions.get('cmake')!='4.4.4.0':raise ValueError('inventory_static_version_identity')
    marker=value.get('default_toolset_marker',{})
    if path_row(marker)!=vs/'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt' or marker['bytes']!=11 or marker['sha256']!=sha(toolset.encode()):raise ValueError('inventory_toolset_marker_identity')
    sdk='10.0.26100.0';sdks=observation.get('sdks',{})
    if set(sdks)!={sdk} or sdks[sdk].get('missing')!=[] or set(sdks[sdk].get('files',{}))!={'rc','kernel32','ucrt','windows_header'}:raise ValueError('inventory_complete_sdk_identity')
    kits=PureWindowsPath('C:/Program Files (x86)/Windows Kits/10')
    sdk_paths={'rc':kits/('bin/'+sdk+'/x64/rc.exe'),'kernel32':kits/('Lib/'+sdk+'/um/x86/kernel32.lib'),
               'ucrt':kits/('Lib/'+sdk+'/ucrt/x86/ucrt.lib'),'windows_header':kits/('Include/'+sdk+'/um/Windows.h')}
    for name,row in sdks[sdk]['files'].items():
        if path_row(row)!=sdk_paths[name]:raise ValueError('inventory_sdk_file_owner')
    candidates=observer.observed_locks(observation,str(vs),toolset,{'ImageOS':value['image_os'],'ImageVersion':value['image_version']})
    if len(candidates)!=1 or value.get('observed_lock_candidates')!=candidates:raise ValueError('inventory_exact_observed_candidate')
    lock=copy.deepcopy(candidates[0]);lock['schema']='coh-reviewed-windows-build-tool-lock-v1';del lock['requires_independent_review']
    lock['sdk_representatives']={n:copy.deepcopy(sdks[sdk]['files'][n]) for n in ('kernel32','ucrt','windows_header')}
    lock['inventory_binding']={'run_id':RUN,'artifact_id':ARTIFACT,'artifact_sha256':ZIP_SHA,'receipt_sha256':RECEIPT_SHA,
          'repository_commit':COMMIT,'source_byte_profile':'exact_git_LF_to_checkout_CRLF_all_61_helpers',
          'scope':'Eight primary executable observations; next build rehash required. No runtime or shipping permit.'}
    workflow='.github/workflows/native-reviewed-inputs.yml'
    return lock,{'source_helper_map':source_map,'workflow_path':workflow,'workflow_sha256':sha(git(root,'show',COMMIT+':'+workflow)),
                 'actual_raw_receipt_sha256':RECEIPT_SHA,'source_byte_profile':'exact_git_LF_to_checkout_CRLF_all_61_helpers',
                 'windows_tools_rehashed_locally':False,'compiler_executed':False,'service_executed':False,'shipping_runtime_replacement_permit':False}


def admit(archive,root):
    if archive.is_symlink() or archive.stat().st_size!=4986 or sha(archive.read_bytes())!=ZIP_SHA:raise ValueError('inventory_outer_archive_pin')
    with zipfile.ZipFile(archive) as zipped:
        if zipped.namelist()!=['receipt.json'] or zipped.getinfo('receipt.json').file_size!=24407:raise ValueError('inventory_archive_member_profile')
        raw=zipped.read('receipt.json')
    if sha(raw)!=RECEIPT_SHA:raise ValueError('inventory_raw_receipt_pin')
    lock,review=verify_receipt(json.loads(raw),root)
    review.update(schema='coh-actual-tool-inventory-admission-v1',passed=True,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,run_id=RUN,repository_commit=COMMIT)
    return raw,lock,review


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('inventory_new_review_directory_required')
    raw,lock,review=admit(a.archive,a.source_root);a.output.mkdir(parents=True)
    (a.output/'receipt.json').write_bytes(raw);data=(json.dumps(lock,indent=2)+'\n').encode();(a.output/'reviewed-toolchain-lock.json').write_bytes(data)
    review['reviewed_lock_sha256']=sha(data);(a.output/'admission.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps({'passed':True,'reviewed_lock_sha256':sha(data),'source_helpers':61,'compiler_executed':False}))
