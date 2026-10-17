"""Complete first-party source composition; static build plan, no build/runtime action."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import shutil
import subprocess
import tarfile

import pg_wine_checksum_recipe as base
from hosted_db_checksum_candidate import replace_checksum

HERE=Path(__file__).resolve().parent
MANIFEST=HERE.parent/'evidence/manual-atlas-full-recipe-20261017/accepted-startup-dbserver-manifest.json'
MANIFEST_SHA='949a15e5a796c5c63cf94d3b16072762f9f310545ca28184f5a714d897c9f087'
SOURCE_COUNT=5995
SOURCE_BYTES=173081714
BUILD_PROFILE={'generator':'Visual Studio 18 2026','architecture':'Win32','configuration':'OptDebug','target':'DbServer',
               'parallel':2,'COH_PG_PERSISTENCE_TESTS':False,'COX_BUILD_MAPSERVER':False,'COX_BUILD_BEACONSERVER':False,
               'build_executed':False,'service_executed':False}


def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)


def load_manifest():
    data=MANIFEST.read_bytes()
    if base.sha(data)!=MANIFEST_SHA:raise ValueError('manual_atlas_manifest_identity')
    value=json.loads(data)
    if (value['files']['DbServer.exe']['sha256']!='ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba'
            or value['base_normal_executable']['sha256']!='535bfd6df77ce09bc3d1048accd95d7910552f8861c3a9c4e356d522786d585c'
            or value['postgresql_persistence_fixture'] is not False or value['configuration']!='OptDebug' or value['architecture']!='Win32'
            or value['dependency_report']['unresolved']):raise ValueError('manual_atlas_product_profile')
    return value


def archive_original(root,output):
    command=['git','-C',str(root),'archive','--format=tar','HEAD','upstream/ouroboros']
    original={};total=0
    with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as process:
        try:
            with tarfile.open(fileobj=process.stdout,mode='r|') as archive:
                for member in archive:
                    if member.isdir():continue
                    prefix='upstream/ouroboros/'
                    if not member.isfile() or not member.name.startswith(prefix):raise ValueError('manual_original_archive_kind')
                    name=member.name[len(prefix):];parts=PurePosixPath(name)
                    if not name or '\\' in name or parts.is_absolute() or '..' in parts.parts or name in original:raise ValueError('manual_original_archive_path')
                    total+=member.size
                    if len(original)>=SOURCE_COUNT or total>SOURCE_BYTES:raise ValueError('manual_original_archive_budget')
                    path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
                    stream=archive.extractfile(member);digest=hashlib.sha256()
                    with path.open('xb') as target:
                        while True:
                            chunk=stream.read(1024*1024)
                            if not chunk:break
                            digest.update(chunk);target.write(chunk)
                    original[name]=digest.hexdigest()
            while process.stdout.read(1024*1024):pass
            if process.wait(timeout=30)!=0:raise ValueError('manual_original_archive_failed')
        except Exception:
            process.kill();process.wait(timeout=30);raise
    if len(original)!=SOURCE_COUNT or total!=SOURCE_BYTES:raise ValueError('manual_original_archive_identity')
    return original


def source_map(output):
    result={}
    for path in output.rglob('*'):
        if path.is_symlink():raise ValueError('manual_source_linked')
        if path.is_file():result[path.relative_to(output).as_posix()]=base.sha(path.read_bytes())
    return result


def add_overlays(output,items):
    for name,data in items.items():
        path=output/name
        if path.exists() or path.is_symlink():raise ValueError('manual_overlay_overwrites_source')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)


def prepare(root,output):
    root=root.resolve()
    if output.is_symlink():raise ValueError('manual_output_link')
    output=output.resolve()
    if output.exists() or output==root or output.is_relative_to(root):raise ValueError('new_external_full_source_required')
    revision=git(root,'rev-parse','HEAD').decode().strip()
    manifest=load_manifest();package,patches,originals,overlays=base.inputs(root)
    wine=package['wine_build_input'];pg=wine['postgresql_build_input']
    if manifest['build_input']['base_wine_build_input']!=wine:raise ValueError('manual_base_pg_wine_receipt_mismatch')
    output.mkdir(parents=True);original=archive_original(root,output)
    # Recheck every extracted original byte against its Git blob-derived archive
    # map before any overlay. No checkout/source worktree is ever edited.
    if source_map(output)!=original:raise ValueError('manual_archive_extraction_changed')
    expected=dict(original);layers=[]
    for name,receipt,overlay in [(base.PGPATCH,pg,{n:overlays[n] for n in pg['overlay_sha256']}),
                                  (base.WINEPATCH,wine,{n:overlays[n] for n in wine['wine_overlay_sha256']})]:
        if name==base.WINEPATCH:base.verify(output,wine['source_sha256'])
        base.apply_patch(output,patches[name]);base.verify(output,receipt['patched_sha256']);expected.update(receipt['patched_sha256'])
        add_overlays(output,overlay);expected.update({n:base.sha(v) for n,v in overlay.items()});layers.append({'patch':name,'sha256':base.sha(patches[name])})
    for key in ('build_input','startup_bundle_build_input','levelup_ui_repair_build_input'):
        receipt=manifest[key];patch_name=receipt['patch'];data=git(root,'show','HEAD:'+patch_name).replace(b'\r\n',b'\n')
        if base.sha(data)!=receipt['patch_sha256']:raise ValueError('manual_layer_patch_identity')
        if set(re.findall(r'^\+\+\+ b/(.+)$',data.decode(),re.M))!=set(receipt['patched_sha256']):raise ValueError('manual_layer_patch_paths')
        base.verify(output,receipt['source_sha256']);base.apply_patch(output,data);base.verify(output,receipt['patched_sha256']);expected.update(receipt['patched_sha256'])
        additions={}
        for name,digest in receipt.get('overlay_sha256',{}).items():
            raw=git(root,'show','HEAD:database/startup-dbserver/overlay/'+name).replace(b'\r\n',b'\n')
            if base.sha(raw)!=digest:raise ValueError('manual_layer_overlay_identity')
            additions[name]=raw
        add_overlays(output,additions);expected.update({n:base.sha(v) for n,v in additions.items()});layers.append({'patch':patch_name,'sha256':base.sha(data)})
    level=manifest['levelup_ui_repair_build_input'];base.verify(output,level['unchanged_thread_support_sha256'])
    base.verify(output,{'DBServer/src/container_merge.c':level['unchanged_merger_sha256'],'DBServer/src/sql_fifo.c':level['unchanged_fifo_sha256']})
    if source_map(output)!=expected:raise ValueError('manual_full_lineage_source_mismatch')
    checksum=output/base.CHECKSUM;raw=checksum.read_bytes()
    if raw!=git(root,'show','HEAD:upstream/ouroboros/'+base.CHECKSUM):raise ValueError('manual_lineage_checksum_source_changed')
    baseline=dict(expected);checksum.write_bytes(replace_checksum(raw));expected[base.CHECKSUM]=base.sha(checksum.read_bytes())
    if source_map(output)!=expected:raise ValueError('manual_unexpected_additional_source_change')
    # Both exact accepted manual guard and actual version/auth source remain
    # unchanged; this composition does not enable its fake-auth-only mode.
    guard=(output/'DBServer/src/wine_manual_atlas.c').read_text()
    if '|| !fake_auth' not in guard or '|| auth_server_present' not in guard:raise ValueError('manual_fake_only_guard_missing')
    if git(root,'rev-parse','HEAD').decode().strip()!=revision:raise ValueError('manual_repository_revision_changed')
    result={'schema':'coh-full-manual-atlas-checksum-source-recipe-v1','passed':True,'source_tree':base.ORIGINAL_TREE,
            'source_repository_commit':revision,'accepted_manifest_sha256':MANIFEST_SHA,
            'accepted_manual_binary':manifest['files']['DbServer.exe'],'accepted_base_normal_binary':manifest['base_normal_executable'],
            'retained_runtime_dependency_records':manifest['retained_normal_files'],'accepted_cmake_cache':manifest['cmake_cache'],
            'layers':layers,'original_files':len(original),'original_bytes':SOURCE_BYTES,'complete_source_files':len(expected),
            'sole_additional_changed_path':base.CHECKSUM,'build_profile':BUILD_PROFILE,'full_first_party_build_source_materialized':True,
            'external_CPM_dependencies_materialized':False,'new_binary_built':False,'build_executed':False,'runtime_profile_admitted':False,
            'shipping_runtime_replacement_permit':False,'manual_wait_skip_permitted_for_real_auth':False,'native_reference_alias_created':False,
            'nondevelopment_version_observed':False,'actual_persistence_or_authenticated_db_execution':False,
            'maps':{'original':original,'accepted_manual_lineage':baseline,'checksum_candidate':expected}}
    return result


def verify_complete_source(output,expected):
    if not isinstance(expected,dict) or len(expected)!=6007:raise ValueError('manual_complete_file_domain')
    for name,digest in expected.items():
        if type(name) is not str or not name:raise ValueError('manual_complete_file_identity')
        parts=PurePosixPath(name)
        if (not name or parts.is_absolute() or '..' in parts.parts or '\\' in name
                or type(digest) is not str or not re.fullmatch('[a-f0-9]{64}',digest)):
            raise ValueError('manual_complete_file_identity')
    if source_map(output)!=expected:raise ValueError('manual_complete_staged_source_changed')
    return {'full_first_party_source_verified':True,'runtime_profile_admitted':False,'build_executed':False}


DEPENDENCIES={
 'Zlib':('chromium_zlib','https://chromium.googlesource.com/chromium/src/third_party/zlib','cf333892c34ab6dbaed37c38a1d5aa6da7b2f99d','cmake/patches/chromium-zlib-cmake.patch'),
 'CryptoPP':('cryptopp','https://github.com/weidai11/cryptopp','b5242667a24e3db8e4600e77b2e502ef204e5280','cmake/patches/cryptopp-cmake.patch'),
 'SparseHash':('sparsehash','sparsehash/sparsehash','f93c0c69e959c1c77611d0ba8d107aa971338811',None)}
DECLARED_LISTS={
 'DBServer/CMakeLists.txt':{'DbServer_SOURCES':64,'DbServer_HEADERS':66},
 'libs/UtilitiesLib/CMakeLists.txt':{'UtilitiesLib_SOURCE_FILES':165,'UtilitiesLib_HEADER_FILES':194},
 'Utilities/StructParser/CMakeLists.txt':{'STRUCTPARSER_SOURCES':15}}


def build_plan(source,build,patch,expected):
    # This is a deliberately bounded audit of this pinned CMake profile, not a
    # general CMake interpreter. The full byte map must pass before parsing.
    source=Path(source);verify_complete_source(source,expected)
    declarations={}
    for name,variables in DECLARED_LISTS.items():
        text=(source/name).read_text();counts={}
        for variable,count in variables.items():
            match=re.search(r'set\('+variable+r'\s+(.*?)\n\)',text,re.S)
            if match is None:raise ValueError('manual_cmake_declaration_missing')
            tokens=' '.join(line.split('#')[0] for line in match[1].splitlines()).split()
            if len(tokens)!=count or len(set(tokens))!=count:raise ValueError('manual_cmake_declaration_domain')
            for token in tokens:
                path=(source/name).parent/token
                if not path.resolve().is_relative_to(source.resolve()) or not path.is_file():raise ValueError('manual_declared_first_party_input_missing')
            counts[variable]=count
        declarations[name]=counts
    dependencies={}
    for module,(package,repository,commit,patch_name) in DEPENDENCIES.items():
        name='cmake/dependencies/'+module+'.cmake';text=(source/name).read_text()
        if not all(word in text for word in (package,repository,'GIT_TAG '+commit)):
            raise ValueError('manual_dependency_source_pin')
        dependencies[package]={'repository':repository,'git_commit':commit,'definition_sha256':expected[name],
                               'materialized':False,'compiled':False}
        if patch_name:dependencies[package]['patch']={'path':patch_name,'sha256':expected[patch_name]}
    root=(source/'CMakeLists.txt').read_text()
    projects=re.findall(r'^cox_add_project\((\w+)\s+[^)]+\)$',root,re.M)
    if len(projects)!=43 or len(set(projects))!=43 or not {'Common','DbServer'}.issubset(projects):
        raise ValueError('manual_project_option_domain')
    flags=['-DCOX_BUILD_'+name.upper()+'='+('ON' if name in ('Common','DbServer') else 'OFF') for name in projects]
    configure=['cmake','-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','Win32',
               '-DCOH_PG_PERSISTENCE_TESTS=OFF','-DCOX_BUILD_MAPSERVER=OFF','-DCOX_BUILD_BEACONSERVER=OFF',
               '-DCOX_BUILD_DEV_TOOLS=OFF','-DCOX_BUILD_ART_TOOLS=OFF',
               '-DCOX_BUILD_UTILITIES_TESTS=OFF','-DCOX_BUILD_PIG_TESTS=OFF','-DCOX_BUILD_CODEC_TESTS=OFF',
               '-DPATCH_EXECUTABLE='+str(patch)]+flags
    # Include all configure modules and in-tree build tools/resources in the
    # sealed map. StructParser creates AutoGen sidecars in the disposable copy.
    tool_inputs={n:h for n,h in expected.items() if n.startswith(('cmake/','Utilities/StructParser/','libs/crashrpt/'))
                 or n in ('CMakeLists.txt','DBServer/CMakeLists.txt','libs/UtilitiesLib/CMakeLists.txt','Common/CMakeLists.txt')}
    return {'schema':'coh-manual-atlas-static-build-plan-v1','passed':True,'declared_input_lists':declarations,
            'external_dependencies':dependencies,'sealed_first_party_build_tool_inputs':tool_inputs,
            'enabled_registered_projects':['Common','DbServer'],'disabled_registered_projects':[n for n in projects if n not in ('Common','DbServer')],
            'commands':[configure,['cmake','--build',str(build),'--config','OptDebug','--parallel','2','--target','DbServer']],
            'required_host_tools':['CMake >=4.2 with Visual Studio 18 2026 generator','Visual Studio 2026 MSVC x86 C/C++ compiler and linker',
                                   'Windows SDK x86 headers/libraries and resource compiler','Git and patch.exe','network or exact-pinned CPM cache'],
            'generated_inputs':['StructParser target-owned AutoGen sidecars','SparseHash build-local sparseconfig.h'],
            'mandatory_build_execution':['verify_precise_floating_point','StructParser::Host','DbServer_LogServer alias staging'],
            'runtime_dependency_admission_required':True,'static_plan_only':True,'cmake_configure_executed':False,
            'compiler_executed':False,'runtime_profile_admitted':False,'shipping_runtime_replacement_permit':False}


if __name__=='__main__':
    import argparse,gzip
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    if a.receipt.exists() or a.receipt.with_suffix('.source-maps.json.gz').exists():raise ValueError('new_receipt_and_map_paths_required')
    result=prepare(a.source_root,a.output)
    maps=result.pop('maps');maps_path=a.receipt.with_suffix('.source-maps.json.gz');data=gzip.compress(json.dumps(maps,sort_keys=True).encode(),mtime=0);maps_path.write_bytes(data)
    result['source_maps_sha256']=base.sha(data);result['source_maps_file']=maps_path.name;a.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'source_files':result['complete_source_files'],'build_executed':False}))
