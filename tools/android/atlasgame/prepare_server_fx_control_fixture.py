#!/usr/bin/env python3
"""Retain a complete public .31 Atlas preparation for isolated native FX proof.

This fresh process imports only exact APK guest helpers before using their real
preparation methods. No native process, SQL or saved character is started. The
result is a disposable host fixture, never player data or a shipping payload.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[3]
DONOR = {'bytes':41203812,'sha256':'e56df1bcf2210aff131ba80189b1b2dee760f27066e3ee26e09c5fea1654ad80'}
MAPSERVER = {'bytes':6892032,'sha256':'53ff6ee013690670abbaed39e44d66267caf8753486fbc05c64766a56d9c0713'}
BASE_FX = {'bytes':58505496,'sha256':'3b1af6d146db65aa2a00fa9dbe4502776409cdea15f94f717e5455a3cda5fe70'}


def require(ok, message):
    if not ok: raise ValueError(message)


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(),'Regular host fixture input required')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): digest.update(block)
    return {'bytes':path.stat().st_size,'sha256':digest.hexdigest()}


def prepare(args):
    args.output = args.output.resolve(); args.payloads = args.payloads.resolve()
    require(pin(args.donor_apk) == DONOR and not args.output.exists(),'Exact public .31 APK and fresh control fixture required')
    args.output.mkdir(parents=True); runtime_assets = args.output/'apk-runtime'; runtime_assets.mkdir()
    with zipfile.ZipFile(args.donor_apk) as archive:
        names = archive.namelist(); require(len(names) == len(set(names)),'Duplicate APK member')
        selected = [n for n in names if n.startswith('assets/runtime/')]
        require(selected and all(n.count('/') == 2 for n in selected),'Flat exact APK runtime assets required')
        for name in selected:
            info = archive.getinfo(name)
            require(not info.is_dir() and not info.flag_bits&1 and 0 < info.file_size < 64*1024**2,'Invalid APK runtime leaf')
            (runtime_assets/Path(name).name).write_bytes(archive.read(name))
    sys.path.insert(0,str(runtime_assets))
    import client_startup_diagnostic as client
    import local_character_server as server
    import character_avatar_assets as avatar
    import atlas_world_assets as world
    require(all(Path(m.__file__).resolve().parent == runtime_assets for m in (client,server,avatar,world)),
            'Control preparation must import authenticated .31 packaged guests')
    sys.path.insert(1,str(ROOT/'tools/android/interactive'))
    spec = importlib.util.spec_from_file_location('fx_complete_startup_fixture',ROOT/'tools/android/interactive/qualify_full_startup_preflight.py')
    complete = importlib.util.module_from_spec(spec); spec.loader.exec_module(complete)
    payload_pins = complete.leaf.validate_assets(args.payloads); complete.extra_inputs(args.payloads)
    assets = args.output/'assets'; assets.mkdir()
    for source in sorted(runtime_assets.iterdir()):
        if source.is_file(): shutil.copyfile(source,assets/source.name)
    for name in set(payload_pins)|{Path(n).name for n in complete.IMPORT_INPUTS}:
        target = assets/name
        if target.exists(): require(pin(target) == pin(args.payloads/name),'APK/external control payload collision differs')
        elif name.endswith('.json'): shutil.copyfile(args.payloads/name,target)
        else: os.link(args.payloads/name,target)
    asset_hashes,data,import_proof = complete.verify_inputs_before_import(client,assets,args.payloads)
    context = complete.Context(); state = args.output/'state'; state.mkdir(); owned = args.output/'owned'; owned.mkdir()
    identity = client.import_identity(data)
    work,receipt = client.prepare_worktree(owned,data,assets,identity,context)
    require(receipt['reused'] is False and receipt['input_files'] == complete.COUNT
            and receipt['imported_inputs_readonly'] is True,'Complete cold client control preparation required')
    context.report['client_worktree'] = receipt
    context.report['character_avatar_supplement'] = avatar.install(work,assets,context)
    context.report['atlas_world_supplement'] = world.install(work,assets,context)
    # Preserve the strict production guard. Failure-only metadata makes a host
    # input-parent mutation inspectable instead of silently retrying/waiving it.
    resolver_type = server.server_data_cache.CheckedInputResolver
    original_verify = resolver_type.verify; original_directory = resolver_type.directory
    first_root_children = {}
    def root_children(path):
        result = {}
        for child in sorted(path.iterdir()):
            info = child.lstat()
            result[child.name] = {name:getattr(info,name) for name in
                ('st_dev','st_ino','st_uid','st_mode','st_size','st_mtime_ns','st_ctime_ns')}
        return result
    def checked_directory(resolver, path):
        result = original_directory(resolver,path)
        path = Path(path)
        if path in resolver.roots and path not in first_root_children:
            first_root_children[path] = root_children(path)
        return result
    def checked_verify(resolver):
        try:
            return original_verify(resolver)
        except Exception:
            changed = []
            for path, before in resolver.observed.items():
                current = resolver.directory_identity(path.lstat())
                if before != current:
                    changed.append({'path':str(path),'before':list(before),'after':list(current),
                        'before_children':first_root_children.get(path),
                        'after_children':root_children(path) if path in resolver.roots else None})
            (args.output/'input-parent-mutation.json').write_text(json.dumps(changed,indent=2)+'\n')
            raise
    resolver_type.verify = checked_verify; resolver_type.directory = checked_directory
    owner = SimpleNamespace(root=owned,work=work,ctx=context,
        args=SimpleNamespace(assets=assets,game_data=data,session_id='3'*32,state=state),
        cleanup_status={'wine_prefix_stopped':True,'owned_processes_reaped':True})
    instance = server.LocalCharacterServer(owner)
    try:
        instance.payloads(); instance.prepare_runtime()
    finally:
        resolver_type.verify = original_verify; resolver_type.directory = original_directory
    require(pin(instance.runtime/'MapServer.exe') == MAPSERVER and pin(instance.runtime/'data/bin/fxinfo.bin') == BASE_FX,
            'Native control must retain approved shipping MapServer/full client FX')
    proof = {'format':1,'role':'complete_prepared_public_031_native_fx_control','status':'prepared',
        'donor_apk':DONOR,'source_commit':'74fe247be85173e618f1af2c8af71b1316de4cd8',
        'original_import':import_proof,'atlas_preparation':complete.phase_result(instance),
        'runtime_host_path':str(instance.runtime.resolve()),'mapserver':MAPSERVER,'fx':BASE_FX,
        'all_external_payloads':payload_pins,'client_asset_hashes':asset_hashes,
        'packaged_guest_sources':{p.name:pin(p) for p in sorted(runtime_assets.glob('*.py'))},
        'native_processes_started':False,'live_sql_started':False,'player_database_used':False,
        'cache_cleanup_prerequisites_stubbed_no_native_processes_started':True,
        'source_script':pin(Path(__file__))}
    (args.output/'control-fixture.json').write_text(json.dumps(proof,sort_keys=True,separators=(',',':'))+'\n')
    return proof


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk','payloads','output'): p.add_argument('--'+name,type=Path,required=True)
    proof = prepare(p.parse_args())
    print(json.dumps({'status':proof['status'],'runtime':proof['runtime_host_path'],
        'control_fixture':str(Path(proof['runtime_host_path']).parents[1]/'control-fixture.json')}))
