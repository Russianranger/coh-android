#!/usr/bin/env python3
"""Export actual .36 guest-prepared Atlas/Kings providers for native Windows.

Preparation alone proves no native readiness. SQL/readiness boundaries used
here are explicitly synthetic; Windows execution is the independent next job.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_runtime_asset_preflight as leaf
import map_startup_proof_transport as transport
import qualify_saved_map_preparation as saved

SOURCE = '3570430cefdb15d9b239563e85cccf4d8fe6f32e'
APK = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
APK_URL = 'https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.36/COH-Atlas-Gameplay-0.13.36.apk'
PUBLIC_RUN = 38346809297
PUBLIC_AUDIT_JOB = 115141593507
MAX_FILES, MAX_TOTAL, MAX_FILE = 400000, 16*1024**3, 512*1024**2
MANIFEST = 'native-map-world-inputs-037.json'
FX_VARIANTS = {'server_only':leaf.SERVER_PROJECTED_FX,'full':leaf.CLIENT_FULL_FX}


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def safe_windows_name(name):
    require = leaf.require
    require(leaf.safe(name) and name == PurePosixPath(name).as_posix() and len(name) <= 225,
            'Unsafe Windows provider relative name')
    reserved = {'con','prn','aux','nul',*(f'com{i}' for i in range(1,10)),*(f'lpt{i}' for i in range(1,10))}
    for part in name.split('/'):
        require(part[-1] not in ' .' and not any(c in part for c in '<>"|?*')
                and not any(ord(c)<32 for c in part) and part.split('.')[0].casefold() not in reserved,
                'Windows provider path has alias/device/invalid character')
    return name


def public_audit():
    headers = {'Accept':'application/vnd.github+json'}
    if os.environ.get('GH_TOKEN'): headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    base='https://api.github.com/repos/Russianranger/coh-android/actions/runs/'+str(PUBLIC_RUN)
    def fetch(url):
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=45) as r:
            return json.load(r)
    run=fetch(base); jobs=fetch(base+'/jobs?per_page=100')['jobs']
    leaf.require(run['status']=='completed' and run['conclusion']=='success' and run['head_sha']==SOURCE
                 and run['path']=='.github/workflows/android-client-startup-latency.yml',
                 'Exact public .36 production run did not pass')
    audit=[j for j in jobs if j['id']==PUBLIC_AUDIT_JOB and j['name']=='public-audit']
    leaf.require(len(audit)==1 and audit[0]['status']=='completed' and audit[0]['conclusion']=='success',
                 'Independent public .36 artifact audit did not pass')
    return {'run_id':PUBLIC_RUN,'public_audit_job_id':PUBLIC_AUDIT_JOB,'head_sha':SOURCE,
            'run_conclusion':'success','public_audit_conclusion':'success'}


def download_apk(path):
    path=Path(path)
    if path.exists(): leaf.checked(path,APK); return
    pending=path.with_suffix('.partial'); pending.parent.mkdir(parents=True,exist_ok=True)
    try:
        with urllib.request.urlopen(APK_URL,timeout=120) as source,pending.open('xb') as out:
            while block:=source.read(1024**2):
                out.write(block); leaf.require(out.tell()<=APK['bytes'],'Public APK exceeds exact bound')
        leaf.checked(pending,APK); pending.replace(path)
    finally: pending.unlink(missing_ok=True)


def extract_apk(apk, destination):
    leaf.checked(apk,APK); destination=Path(destination); destination.mkdir()
    with zipfile.ZipFile(apk) as archive:
        names=archive.namelist(); leaf.require(len(names)==len(set(names)),'Duplicate APK members')
        manifest=json.loads(archive.read('assets/runtime/runtime-manifest.json'))
        packaged=[n[len('assets/runtime/'):] for n in names if n.startswith('assets/runtime/')
                  and n!='assets/runtime/runtime-manifest.json']
        for name in packaged:
            leaf.require(PurePosixPath(name).name==name and leaf.safe(name),'Unsafe runtime asset')
            record=manifest['files'].get(name);leaf.require(record is not None,'Unpinned APK runtime member')
            raw=archive.read('assets/runtime/'+name)
            leaf.require({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==record,
                         'Runtime asset manifest pin differs: '+name)
            (destination/name).write_bytes(raw)
        (destination/'runtime-manifest.json').write_bytes(archive.read('assets/runtime/runtime-manifest.json'))
    guest={}
    for path in destination.glob('*.py'):
        source=ROOT/'android/guest'/path.name
        leaf.require(source.is_file() and path.read_bytes()==source.read_bytes(),
                     'Public .36 guest source differs from retained source checkout: '+path.name)
        guest[path.name]=leaf.pin(path)
    return guest


def export_runtime(runtime, archive_path, allowed_roots):
    """Resolve authenticated preparation links and export regular bytes only."""
    runtime=Path(runtime); allowed=[Path(x).resolve() for x in allowed_roots]
    records={}; seen=set(); total=0
    with tarfile.open(archive_path,'w:gz',compresslevel=1,format=tarfile.PAX_FORMAT) as archive:
        for directory, dirs, files in os.walk(runtime,followlinks=False):
            leaf.require(not any((Path(directory)/n).is_symlink() for n in dirs),
                         'Linked prepared provider directory refused')
            for name in sorted(files):
                path=Path(directory)/name; relative=path.relative_to(runtime).as_posix()
                safe_windows_name(relative)
                leaf.require(relative.casefold() not in seen,'Case-aliased provider file')
                seen.add(relative.casefold()); source=path.resolve(strict=True)
                leaf.require(any(source==root or root in source.parents for root in allowed),
                             'Provider leaf escapes authenticated preparation')
                info=source.stat(); leaf.require(stat.S_ISREG(info.st_mode) and info.st_size<=MAX_FILE,
                                                'Nonregular/oversized provider leaf')
                total+=info.st_size; leaf.require(len(records)<MAX_FILES and total<=MAX_TOTAL,'Provider export exceeds bounds')
                record={**leaf.pin(source),'mtime_ns':info.st_mtime_ns//100*100}
                records[relative]=record
                member=tarfile.TarInfo(relative); member.size=record['bytes']; member.mode=0o600
                member.mtime=record['mtime_ns']/1e9
                with source.open('rb') as stream: archive.addfile(member,stream)
                leaf.require(source.stat().st_mtime_ns==info.st_mtime_ns and leaf.pin(source)=={k:record[k] for k in ('bytes','sha256')},
                             'Provider input changed during export')
    return {'archive':leaf.pin(archive_path),'files':records,'count':len(records),'bytes':total,
            'inventory_sha256':hashlib.sha256(leaf.canonical(records)).hexdigest()}


def worker(apk,payloads,output):
    output=Path(output); leaf.require(not output.exists(),'Fresh prepared world output required'); output.mkdir()
    full=transport.worker_module('full_startup'); full.extra_inputs(payloads)
    with tempfile.TemporaryDirectory(prefix='coh-native-world-prep-') as temporary:
        root=Path(temporary); runtime_assets=root/'runtime-assets'; guest=extract_apk(apk,runtime_assets)
        sys.path.insert(0,str(runtime_assets))
        import client_startup_diagnostic as client
        import character_creation_diagnostic as creation
        import character_zoning as zoning
        import local_character_server as server
        import character_avatar_assets as avatar
        import atlas_world_assets as world
        leaf.require(all(Path(m.__file__).resolve().parent==runtime_assets for m in (client,creation,zoning,server,avatar,world)),
                     'Public APK guest preparation import was shadowed')
        assets=saved.setup_assets(full,runtime_assets,payloads,root)
        # One additional exact BIN supplies the full variant; source provider
        # trees and all immutable asset archives stay shared across variants.
        with zipfile.ZipFile(assets/'client-caches.zip') as archive:
            raw_full_fx=archive.read('data/bin/fxinfo.bin')
        leaf.require({'bytes':len(raw_full_fx),'sha256':hashlib.sha256(raw_full_fx).hexdigest()}==FX_VARIANTS['full'],
                     'Original full FX source differs')
        (output/'full-fxinfo.bin').write_bytes(raw_full_fx)
        hashes,data,imported=full.verify_inputs_before_import(client,assets,payloads)
        owned=root/'owned'; owned.mkdir(); state=root/'state';state.mkdir();ctx=full.Context();ctx.secrets=[]
        work,work_receipt=client.prepare_worktree(owned,data,assets,client.import_identity(data),ctx)
        ctx.report.update(client_worktree=work_receipt,asset_sha256=hashes)
        ctx.report['character_avatar_supplement']=avatar.install(work,assets,ctx)
        ctx.report['atlas_world_supplement']=world.install(work,assets,ctx)
        owner=SimpleNamespace(root=owned,work=work,ctx=ctx,args=SimpleNamespace(assets=assets,game_data=data,
            session_id='a'*32,state=state),cleanup_status={'wine_prefix_stopped':True,'owned_processes_reaped':True})
        instance=zoning.LocalCharacterZoningServer(owner);instance.payloads();verify_sql=saved.sql_fixture(instance,5)
        instance.prepare_runtime(); config=instance.runtime/'data/server/db/servers.cfg';instance.config=config
        instance.report['server_ready']=True;instance.creation_report['map_ready']=True
        visual=creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
        visual.work,visual.ctx,visual.local_server,visual.args=work,ctx,instance,owner.args
        visual.prepare_client_visual_inputs();instance.creation_report['map_ready']=False
        kings=instance.prepare_kings_row_runtime(); atlas=instance.prepare_atlas_runtime()
        leaf.require(kings['graph']['verified'] and kings['graph']['map_id']==5,
                     'Kings graph failed actual packaged validation')
        exports={}
        for key,runtime in [('db',instance.runtime),('1',atlas),('5',kings['runtime'])]:
            exports[key]=export_runtime(runtime,output/('provider-'+key+'.tar.gz'),[root,data])
        sql=verify_sql(); binding=leaf.native_binding(atlas,instance.map_package)
        value={'format':1,'status':'prepared','role':'public_036_actual_guest_Map1_Map5_preparation',
            'public_apk':APK,'production_source':SOURCE,'public_audit':public_audit(),'guest_sources':guest,
            'asset_version':'1.0.0','original_import':imported,'providers':exports,
            'fx_variants':FX_VARIANTS,'full_FX_BIN':leaf.pin(output/'full-fxinfo.bin'),
            'native_binding':binding,'map_package':instance.map_package,'db_package':instance.package,'schema':instance.schema,
            'map_preparation':{'1':leaf.stable(instance.creation_report),'5':leaf.stable(kings['preparation'])},
            'SQL_boundary':sql,'native_readiness_boundary':'controlled_preparation_only_no_native_process',
            'native_processes_started':0,'player_profile_opened':False,'behavioral_collision_proven':False,
            'physical_device_executed':False,'shipping_allowed':False}
        instance.cleanup_config(); write(output/MANIFEST,value)
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache','output','apk','payloads'):p.add_argument('--'+n,type=Path)
    p.add_argument('--worker',action='store_true');args=p.parse_args()
    if args.worker:worker(args.apk,args.payloads,args.output);return
    leaf.require(args.cache is not None and args.output is not None,'Cache and output required')
    public_audit(); args.cache.mkdir(parents=True,exist_ok=True);apk=args.cache/'COH-Atlas-Gameplay-0.13.36.apk';download_apk(apk)
    assets=leaf.ensure_assets(args.cache);full=transport.worker_module('full_startup');full.extra_inputs(assets)
    for label,pin in {**leaf.VOLUMES,'Audio':full.AUDIO_VOLUME}.items():
        leaf.checked(args.cache/('COH-Assets-1.0.0-'+label+'.zip'),pin)
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker','--apk',str(apk.resolve()),
        '--payloads',str(assets.resolve()),'--output',str(args.output.resolve())],check=True,timeout=5400)
    shutil.copyfile(apk,args.output/apk.name)
    report=json.loads((args.output/MANIFEST).read_text());report['asset_volumes']={label:pin for label,pin in {**leaf.VOLUMES,'Audio':full.AUDIO_VOLUME}.items()}
    write(args.output/MANIFEST,report)


if __name__=='__main__':main()
