#!/usr/bin/env python3
"""Generate genuine map-5 beacons and prove cold/reopened native world identity.

The separately compiled host tool fails on missing world geometry or members.
No host tool enters the APK. No host elapsed time is an Android loading claim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile
import generate_atlas_beacons as shared
sys.path.insert(0, str(shared.ROOT/'tools'))
import prepare_kings_row_beacon_generator_source as producer
ROOT = shared.ROOT
require, pin, canonical = shared.require, shared.pin, shared.canonical
MAP = producer.MAP
GRAPH = 'data/server/'+MAP+'.v8.bcn'
DATE = GRAPH+'.date'
ARCHIVE = 'kings-row-beacons.zip'
MANIFEST = 'kings-row-beacon-manifest.json'
REPORT = 'kings-row-beacon-generation-report.json'
LOCK = 'kings-row-beacon-lock.json'
DONOR = {'bytes':1560390578,'sha256':'25afcd1c4d4afb55990e295a5fdcf4daab18389d461f2ffaf7d9455676edd49f'}
PROFILES = ('cold_world','reopened_world')
SOURCE_FILES = ('tools/prepare_kings_row_beacon_generator_source.py', producer.PATCH,
                'tools/android/interactive/generate_kings_row_beacons.py',
                'tools/android/interactive/generate_atlas_beacons.py',
                'tools/prepare_atlas_beacon_generator_source.py', producer.atlas.PATCH)


def extract_donor(apk, output):
    require(pin(apk)==DONOR,'Exact published .27 donor APK required')
    output.mkdir()
    with zipfile.ZipFile(apk) as archive:
        names=archive.namelist()
        require(len(names)==len(set(names)), 'Duplicate APK entries')
        for name in names:
            if not name.startswith('assets/'): continue
            shared.safe(name)
            require(name.count('/')==2,'Unexpected donor nesting')
            target=output/('atlas' if name.startswith('assets/atlas/') else 'runtime')/Path(name).name
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(name) as source,target.open('xb') as dest: shutil.copyfileobj(source,dest,1024**2)


def overlay_collision(archive_path, manifest_path, runtime):
    value=json.loads(Path(manifest_path).read_bytes())
    require(pin(archive_path)=={k:value['archive'][k] for k in ('bytes','sha256')},'Zone archive pin differs')
    selected=value.get('kings_row_collision_files')
    require(isinstance(selected,dict) and len(selected)==52,'Exact Kings Row missing collision set required')
    targets=shared.resolve_world_targets(runtime,selected)
    with zipfile.ZipFile(archive_path) as archive:
        require(len(archive.namelist())==len(set(archive.namelist())),'Zone archive duplicates')
        for name,record in selected.items():
            shared.safe(name)
            require(name.startswith('data/object_library/') and name.endswith('.geo')
                    and record=={k:value['files'][name][k] for k in ('bytes','sha256')},'Collision set outside original zone resources')
            target=targets[name]
            require(not target.exists(),'New Kings geometry overlaps retained original')
            with archive.open(name) as source: shared.copy_pinned(source,target,record)
            os.utime(target,(1767225600,1767225600))
    return {'archive':pin(archive_path),'manifest':pin(manifest_path),'files':selected}


def geometry_inputs(runtime):
    scopes=('data/object_library','data/maps/city_zones/city_01_02','data/tricks')
    targets=shared.resolve_world_targets(runtime,[scope+'/.kings-inventory' for scope in scopes])
    records={};seen=set();count=0
    for scope in scopes:
        root=targets[scope+'/.kings-inventory'].parent
        require(root.is_dir() and not root.is_symlink(),'Missing collision root')
        for path in root.rglob('*'):
            count+=1
            name=path.relative_to(runtime).as_posix()
            require(count<=200000 and not path.is_symlink() and name.casefold() not in seen,'Unsafe/ambiguous collision tree')
            seen.add(name.casefold())
            if path.is_dir(): continue
            require(path.is_file(),'Special collision input')
            suffixes=('.geo','.txt','.rootnames') if scope=='data/object_library' else ('.txt',)
            if path.suffix.casefold() in suffixes: records[shared.canonical_input_name(name)]=pin(path)
    require(100<len(records)<=12288 and ('data/'+MAP) in records,'Incomplete Kings world input inventory')
    return dict(sorted(records.items()))


def native_evidence(log,date):
    # Share the v8 reader / v9 CRC / 32-path parser, never an Atlas graph or pin.
    require(log.count(b'COH_KINGS_ROW_COLLISION_LOAD_V1 missing_groups=0 missing_root_models=0')==1,
            'Fresh collision load failed or lacks missing-input refusal witness')
    require(b'Host Kings Row collision missing' not in log,'Native world collision input missing')
    result=shared.native_evidence(log.replace(b'COH_KINGS_ROW_BEACON_',b'COH_ATLAS_BEACON_'),date)
    return dict(result,missing_groups=0,missing_root_models=0,native_collision_load_verified=True)


def role_environment(verify=False):
    env=shared.role_environment();env.pop('COH_KINGS_ROW_BEACON_VERIFY_ONLY',None)
    if verify: env['COH_KINGS_ROW_BEACON_VERIFY_ONLY']='1'
    return env


def stop_roles(processes):
    for process in processes.values():
        if process.poll() is None: process.terminate()
    for process in processes.values():
        try: process.wait(timeout=15)
        except subprocess.TimeoutExpired: process.kill();process.wait(timeout=15)


def run_generation(runtime,generator,evidence,timeout):
    common=['-nogui','-nopigs','-noencrypt','-beaconallownovodex','-beacondatatoolsrootpath',str(runtime)]
    roles=[('master',['-beaconmasterserver','-beaconrequestcachedir',str(runtime.parent/'requests')]),
           ('server',['-beaconserver','127.0.0.1','-beacononepassonly','-beaconforcerebuild']),
           ('sentry',['-beaconclient','127.0.0.1','-beaconworkduringuseractivity']),
           ('worker',['-beaconclient','127.0.0.1','-beaconworkduringuseractivity'])]
    processes,logs,commands={},{},{};started=time.monotonic();failure=None
    try:
        for role,flags in roles:
            command=[str(generator),*common,*flags];commands[role]=command
            logs[role]=(evidence/(role+'.log')).open('wb')
            processes[role]=subprocess.Popen(command,cwd=runtime,env=role_environment(),stdin=subprocess.DEVNULL,
                                            stdout=logs[role],stderr=subprocess.STDOUT)
            if role in ('master','sentry'):
                marker=b'BEACON MASTER SERVER RUNNING' if role=='master' else b"I'm the sentry!!!"
                deadline=min(started+timeout,time.monotonic()+300)
                while marker not in (evidence/(role+'.log')).read_bytes():
                    require((evidence/(role+'.log')).stat().st_size<=shared.MAX_LOG,'Native startup log limit')
                    require(processes[role].poll() is None and time.monotonic()<deadline,'Native role failed: '+role)
                    time.sleep(.5)
        heartbeat=0
        while processes['server'].poll() is None:
            require(time.monotonic()-started<timeout,'Kings generation time bound exceeded')
            for role,process in processes.items():
                require((evidence/(role+'.log')).stat().st_size<=shared.MAX_LOG,'Native role log bound')
                require(role=='server' or process.poll() is None,'Native role exited: '+role)
            if time.monotonic()>=heartbeat:
                shared.record_role_heartbeat(evidence,processes,started,'kings_row_generation')
                heartbeat=time.monotonic()+60
            time.sleep(1)
        require(processes['server'].returncode==0,'Native Kings graph producer failed')
    except BaseException as error:
        failure=error;raise
    finally:
        before={role:p.poll() for role,p in processes.items()}
        stop_roles(processes)
        for stream in logs.values(): stream.close()
        if failure: shared.record_role_failure(evidence,processes,commands,failure,before)
    return commands


def verify_profile(runtime,generator,evidence,profile,timeout):
    shared.clear_private_geometry_caches(runtime)
    command=[str(generator),'-nogui','-nopigs','-noencrypt','-beaconallownovodex',
             '-beacondatatoolsrootpath',str(runtime),'-beaconserver','127.0.0.1','-beaconnonetstart']
    path=evidence/(profile+'.log')
    with path.open('wb') as log:
        process=subprocess.Popen(command,cwd=runtime,env=role_environment(True),stdin=subprocess.DEVNULL,
                                 stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+min(timeout,600)
            while process.poll() is None:
                require(time.monotonic()<deadline and path.stat().st_size<=shared.MAX_LOG,'Fresh native proof bound')
                time.sleep(.5)
            require(process.returncode==0,'Fresh native proof failed: '+profile)
        finally: stop_roles({profile:process})
    return native_evidence(path.read_bytes(),(runtime/DATE).read_bytes()),command


def validate_package(directory,repository_commit=None):
    directory=Path(directory);value=json.loads((directory/MANIFEST).read_bytes());report=json.loads((directory/REPORT).read_bytes())
    sys.path.insert(0,str(ROOT/'android/guest'))
    import kings_row_beacon_package as guest
    locked_value,lock=guest.read_manifest(directory/MANIFEST,directory/LOCK)
    require(locked_value==value and lock['archive']==pin(directory/ARCHIVE),'APK lock or graph differs')
    require(value['format']==1 and value['role']=='authentic_native_kings_row_beacon_graph' and value['map']==MAP
            and value['map_id']==5 and value['physical_zoning_verified'] is False,'Kings graph identity differs')
    require(report['status']=='passed' and report['cleanup_complete'] is True and report['owned_roles']==0
            and report['native_worker_spawning_allowed'] is False and report['build_input']==producer.expected(),
            'Kings generator provenance or cleanup differs')
    if repository_commit is not None: require(report['repository_commit']==repository_commit,'Kings source commit differs')
    require(report['manifest']==pin(directory/MANIFEST) and report['archive']==pin(directory/ARCHIVE)
            and report['native']==value['native'] and report['profile_proofs']==value['input_profiles']
            and report['source_files']=={n:pin(ROOT/n) for n in SOURCE_FILES},'Kings package source/proof pins differ')
    require(set(value['input_profiles'])==set(PROFILES),'Both fresh native proofs required')
    for profile in PROFILES:
        require(value['input_profiles'][profile]=={'native':value['native'],'input_files_sha256':value['input_files_sha256']},
                'Native proof profiles differ')
    require(hashlib.sha256(canonical(value['input_files'])).hexdigest()==value['input_files_sha256'],'Collision source inventory differs')
    with zipfile.ZipFile(directory/ARCHIVE) as archive:
        require(set(archive.namelist())=={GRAPH,DATE,MANIFEST} and len(archive.namelist())==3,'Kings graph archive closure differs')
        require(archive.read(MANIFEST)==(directory/MANIFEST).read_bytes(),'Embedded manifest differs')
        for name in (GRAPH,DATE):
            raw=archive.read(name);require({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==value['files'][name],'Graph payload differs')
    return value


def generate(args):
    require(os.name=='nt','Genuine native generation requires Windows')
    require(60<=args.timeout_seconds<=5400 and re.fullmatch('[0-9a-f]{40}',args.repository_commit),'Bounded exact source invocation required')
    for name in ('donor_apk','asset_archive','zones_archive','zones_manifest','generator','build_input','work','output'):
        setattr(args,name,Path(getattr(args,name)).resolve())
    require(not args.work.exists() and not args.output.exists(),'Fresh native owned directories required')
    args.work.mkdir(parents=True);args.output.mkdir(parents=True);evidence=args.output/'evidence';evidence.mkdir()
    build=json.loads(args.build_input.read_bytes());require(build==producer.expected(),'Host generator source receipt differs')
    assets=args.work/'donor';extract_donor(args.donor_apk,assets)
    data=shared.import_data(assets,args.asset_archive,args.work,evidence).resolve(strict=True)
    runtime=args.work/'r';data.parent.rename(runtime)
    shared.extract_tar(assets/'runtime/game-package.tar.gz',runtime,'game-package.json')
    shared.extract_tar(assets/'runtime/dbserver-schema.tar.gz',runtime,'schema-manifest.json')
    shared.overlay_zip(assets/'runtime/atlas-world-supplement.zip',assets/'runtime/atlas-world-supplement-manifest.json',runtime)
    # Same accepted required 406 original object GEOs; expanded UI manifest is
    # checked by the immutable .27 APK pin and every extracted physical leaf.
    visual=json.loads((assets/'runtime/client-visual-manifest.json').read_bytes())
    selected={n:r for n,r in visual['files'].items() if n.startswith('data/object_library/') and n.endswith('.geo')}
    require(len(selected)==406,'Retained Atlas object geometry identity changed')
    targets=shared.resolve_world_targets(runtime,selected)
    with zipfile.ZipFile(assets/'runtime/client-visual-assets.zip') as archive:
        for name,row in selected.items():
            target=targets[name]
            if target.exists(): require(pin(target)=={k:row[k] for k in ('bytes','sha256')},'Retained original overlap differs');continue
            with archive.open(name) as source: shared.copy_pinned(source,target,row)
    zone=overlay_collision(args.zones_archive,args.zones_manifest,runtime)
    for path in (runtime/'data').rglob('*'):
        if path.is_file(): os.utime(path,(1767225600,1767225600))
    inputs=geometry_inputs(runtime);cold=args.work/'c';mirror=shared.mirror_cold_runtime(runtime,cold)
    generator=runtime/'KingsRowBeaconGenerator.exe';shutil.copyfile(args.generator,generator)
    (runtime/'tools').mkdir(exist_ok=True)
    started=time.monotonic();commands=run_generation(runtime,generator,evidence,args.timeout_seconds)
    require(all((runtime/n).is_file() for n in (GRAPH,DATE)),'Native graph/date absent')
    witness=native_evidence((evidence/'server.log').read_bytes(),(runtime/DATE).read_bytes())
    profiles={}
    for profile,tree in (('cold_world',cold),('reopened_world',runtime)):
        if tree!=runtime:
            for name in (GRAPH,DATE):
                target=tree/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(runtime/name,target)
            shutil.copyfile(generator,tree/generator.name)
        proof,command=verify_profile(tree,tree/generator.name,evidence,profile,args.timeout_seconds)
        require(proof==witness and geometry_inputs(tree)==inputs,'Fresh world graph/CRC/path/input mismatch')
        profiles[profile]={'native':proof,'input_files_sha256':hashlib.sha256(canonical(inputs)).hexdigest()};commands[profile]=command
    manifest={'format':1,'role':'authentic_native_kings_row_beacon_graph','map':MAP,'map_id':5,
              'source_commit':build['source_commit'],'data_commit':visual['data_commit'],
              'files':{n:pin(runtime/n) for n in (GRAPH,DATE)},'native':witness,
              'input_files':inputs,'input_files_sha256':hashlib.sha256(canonical(inputs)).hexdigest(),
              'input_profiles':profiles,'zone_collision':zone,'generator':pin(generator),
              'runtime_graph_readback':True,'physical_zoning_verified':False}
    raw=canonical(manifest);(args.output/MANIFEST).write_bytes(raw)
    with zipfile.ZipFile(args.output/ARCHIVE,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in (GRAPH,DATE): archive.write(runtime/name,name)
        archive.writestr(MANIFEST,raw)
    report={'format':1,'status':'passed','repository_commit':args.repository_commit,'build_input':build,
            'generator':pin(generator),'donor':DONOR,'archive':pin(args.output/ARCHIVE),'manifest':pin(args.output/MANIFEST),
            'native':witness,'profile_proofs':profiles,'commands':commands,'cleanup_complete':True,'owned_roles':0,
            'native_worker_spawning_allowed':False,'physical_zoning_verified':False,'cold_mirror':mirror,
            'source_files':{n:pin(ROOT/n) for n in SOURCE_FILES},'elapsed_seconds':round(time.monotonic()-started,3)}
    (args.output/REPORT).write_bytes(canonical(report))
    (args.output/LOCK).write_bytes(canonical({'format':1,'map_id':5,'archive':report['archive'],'manifest':report['manifest']}))
    validate_package(args.output,args.repository_commit)
    print(json.dumps({'status':'passed','native':witness,'archive':report['archive']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk','asset-archive','zones-archive','zones-manifest','generator','build-input','work','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--repository-commit',required=True)
    parser.add_argument('--timeout-seconds',type=int,default=5400)
    generate(parser.parse_args())
