"""Reconstruct accepted PG/Wine source closure plus sole checksum correction.

This reduced closure is NOT a buildable/runtime tree. No executable, persistence
profile, native checksum reference or nondevelopment version is installed.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from hosted_auth_stage import ORIGINAL_TREE
from hosted_db_checksum_candidate import replace_checksum
from source_audit import decoded,extract

PACKAGE='docs/android-evidence/dbserver-package-36460867428.json'
PACKAGE_SHA='95f62cc81b0743c13652e55aee01aed6871fc96d70a84b8dfd62fb8a0d9fe0d6'
CHECKSUM='Common/ClientLogin/clientcommLogin.c'
PGPATCH='patches/postgresql/0001-dbserver-postgresql.patch'
WINEPATCH='patches/wine-dbserver/0001-wine-odbc.patch'
EXTRA=['DBServer/src/authcomm.c','DBServer/src/container_merge.c','Common/dbserver/servercfg.c',
       'libs/UtilitiesLib/src/version/AppVersion.c',CHECKSUM]


def sha(data):return hashlib.sha256(data).hexdigest()


def inputs(root):
    blob=lambda name:subprocess.check_output(['git','-C',str(root),'show','HEAD:'+name],timeout=30)
    tree=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD:upstream/ouroboros'],timeout=30).decode().strip()
    if tree!=ORIGINAL_TREE:raise ValueError('pg_wine_original_tree')
    raw=blob(PACKAGE)
    if sha(raw)!=PACKAGE_SHA:raise ValueError('pg_wine_accepted_package_identity')
    package=json.loads(raw);wine=package['wine_build_input'];pg=wine['postgresql_build_input']
    if (package['source_commit']!='0b75ade0c801735e10c5798f641948a45cc50488'
            or package['variants']['normal']['files']['DbServer.exe']['sha256']!='535bfd6df77ce09bc3d1048accd95d7910552f8861c3a9c4e356d522786d585c'):
        raise ValueError('pg_wine_base_variant_identity')
    patches={PGPATCH:blob(PGPATCH).replace(b'\r\n',b'\n'),WINEPATCH:blob(WINEPATCH).replace(b'\r\n',b'\n')}
    if sha(patches[PGPATCH])!=pg['patch_sha256'] or sha(patches[WINEPATCH])!=wine['wine_patch_sha256']:
        raise ValueError('pg_wine_accepted_patch_identity')
    names=set(EXTRA);patch_names=set()
    for patch in patches.values():
        paths=re.findall(r'^\+\+\+ b/(.+)$',patch.decode(),re.M)
        if not paths or len(paths)!=len(set(paths)):raise ValueError('pg_wine_patch_paths')
        names.update(paths);patch_names.update(paths)
    if CHECKSUM in patch_names:raise ValueError('pg_wine_patch_changes_checksum_source')
    originals={name:blob('upstream/ouroboros/'+name) for name in names}
    overlays={}
    for parent,records in [('database/postgresql/overlay/',pg['overlay_sha256']),('database/wine-dbserver/overlay/',wine['wine_overlay_sha256'])]:
        for name,expected in records.items():
            if name in originals or name in overlays:raise ValueError('pg_wine_overlay_overwrites_source')
            raw=blob(parent+name);canonical=raw.replace(b'\r\n',b'\n')
            variants=(raw,canonical,canonical.replace(b'\n',b'\r\n'))
            match=next((v for v in variants if sha(v)==expected),None)
            if match is None:raise ValueError('pg_wine_accepted_overlay_byte_profile')
            overlays[name]=match
    return package,patches,originals,overlays


def apply_patch(directory,data):
    env=os.environ.copy()
    for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE'):env.pop(key,None)
    env['GIT_CEILING_DIRECTORIES']=str(directory.parent)
    for extra in (['--check'],[]):
        result=subprocess.run(['git','-c','core.autocrlf=false','apply',*extra,'-'],input=data,cwd=directory,env=env,capture_output=True,timeout=30)
        if result.returncode:raise ValueError('pg_wine_patch_context_refusal')


def verify(directory,expected):
    for name,digest in expected.items():
        p=directory/name
        if p.is_symlink() or not p.is_file() or any(parent.is_symlink() for parent in p.parents if parent!=directory and directory in parent.parents) or sha(p.read_bytes())!=digest:
            raise ValueError('pg_wine_closure_identity:'+name)


def prepare(root,output):
    root=root.resolve();output=output.resolve()
    if output.exists() or output==root or output.is_relative_to(root):raise ValueError('new_external_recipe_directory_required')
    package,patches,originals,overlays=inputs(root);wine=package['wine_build_input'];pg=wine['postgresql_build_input']
    output.mkdir(parents=True)
    for name,data in originals.items():p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    apply_patch(output,patches[PGPATCH]);verify(output,pg['patched_sha256'])
    verify(output,wine['source_sha256']);apply_patch(output,patches[WINEPATCH]);verify(output,wine['patched_sha256'])
    for name,data in overlays.items():p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    baseline={name:sha((output/name).read_bytes()) for name in set(originals)|set(overlays)}
    expected=dict(pg['patched_sha256']);expected.update(pg['overlay_sha256']);expected.update(wine['patched_sha256']);expected.update(wine['wine_overlay_sha256']);verify(output,expected)
    before=(output/CHECKSUM).read_bytes()
    if before!=originals[CHECKSUM]:raise ValueError('pg_wine_checksum_baseline_changed')
    (output/CHECKSUM).write_bytes(replace_checksum(before))
    for name,digest in baseline.items():
        if name!=CHECKSUM:verify(output,{name:digest})
    original_login=extract(decoded(originals['DBServer/src/clientcomm.c']),'handleLogin')
    pg_login=extract(decoded((output/'DBServer/src/clientcomm.c').read_bytes()),'handleLogin')
    def first_block(text):return text[text.index('    {\n        int            dont_check_version'):text.index('\n\n    // DGNOTE')]
    if first_block(original_login)!=first_block(pg_login):raise ValueError('pg_wine_version_checksum_caller_changed')
    result={'schema':'coh-pg-wine-checksum-source-recipe-v1','passed':True,'original_source_tree':ORIGINAL_TREE,
            'accepted_package_sha256':PACKAGE_SHA,'accepted_base_repository_commit':package['repository_commit'],
            'accepted_normal_binary':package['variants']['normal']['files']['DbServer.exe'],
            'accepted_fixture_binary':package['variants']['fixture']['files']['DbServer.exe'],
            'patch_sha256':{n:sha(v) for n,v in patches.items()},'baseline_closure_sha256':baseline,
            'candidate_closure_sha256':{n:sha((output/n).read_bytes()) for n in baseline},'sole_additional_changed_path':CHECKSUM,
            'version_checksum_caller_unchanged':True,'auth_cookie_consumer_unchanged':True,
            'persistence_fifo_and_merger_unchanged':True,'source_profile':'accepted-base-postgresql-wine-plus-checksum',
            'reduced_closure_only':True,'buildable_tree':False,'new_binary_built':False,'shipping_runtime_replacement_permit':False,
            'manual_atlas_layers_composed':False,'runtime_profile_admitted':False,'native_reference_alias_created':False,
            'nondevelopment_version_observed':False,'live_authenticated_db_login_verified':False}
    (output/'recipe.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();value=prepare(args.source_root,args.output)
    print(json.dumps({'passed':value['passed'],'closure_files':len(value['candidate_closure_sha256']),
                      'buildable_tree':False,'runtime_profile_admitted':False}))
