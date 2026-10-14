#!/usr/bin/env python3
"""Execute retained Map baseline/candidate in full Atlas and Kings worlds.

This is genuine Windows native world initialization and geometry/count parity.
It does not prove player movement, gameplay collision behavior, or Thor timing.
Only disposable PostgreSQL state is used. No produced cache enters an APK.
"""
from __future__ import annotations
import argparse
import ast
from contextlib import contextmanager
import ctypes
import copy
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'android/guest'),str(Path(__file__).resolve().parent)]
import qualify_minimal_db_runtime as minimal
import prepare_native_map_world_inputs_037 as inputs

# These modules' binary/package validators are portable. Actual Wine supervisors
# are imported lazily only by their POSIX execution functions.
import reuse_native_startup_profile as retained
import reuse_native_map_prefetch as candidate_reuse
import package_native_map_prefetch as candidate_package
import prepare_native_startup_reuse_fixture as generation
import qualify_native_startup_profile as profiles
import server_message_cache_format as message_format
import server_animation_package as animation_package

require=minimal.require
REPORT='native-map-world-037-qualification.json'
WORLDS={1:('City_01_01',7001,2311),5:('City_01_02',7003,2166)}
MAP_STAGES={str(i):s for i,s in enumerate((
 'INITIALIZED','STARTUP','MAP_LOAD','DB_SETUP','READY_PUBLISH','READY_PUBLISHED',
 'RUNTIME_PRIORITY','RUNTIME_PRIORITY_DONE','HEAP_VALIDATE','HEAP_VALIDATED','SG_VERIFY','SG_VERIFIED',
 'CALLBACKS_ENABLE','CALLBACKS_ENABLED','RANDOM_SEED','ITEM_POWER_REQUEST','ITEM_POWER_REQUESTED',
 'ERROR_QUEUE_DRAIN','ERROR_QUEUE_DRAINED','READY_STDOUT','LAUNCHER_CONTACT','LATE_STARTUP_DONE',
 'LOOP_PRE_TICK','TICK_BEGIN','TICK_TOP','DB_COMM','DB_COMM_DONE','FOLDER_CALLBACKS','FOLDER_CALLBACKS_DONE',
 'TICK_TOP_DONE','ENTITY_UPDATE','GAME_LOGIC','TICK_BOTTOM','TICK_DONE','LOOP_POST_TICK','SLEEP','SLEEP_DONE'),1)}
MAX_LOG=16*1024**2
CONFIG='data/server/db/servers.cfg'
MEMORY_SAMPLES=128
MAX_WORLD_CACHES=4096
NEW_WORLD_GLOBALS={'data/bin/animlists.bin','data/bin/behavioralias.bin',
                   'data/server/bin/ai_config.bin','data/server/bin/plaquemsg-en.bin'}
INHERITED_STOCK={'source':'04b7a623ef21d7ad48774a58b3122c69ae07f46b','run_id':38494199595,
    'native_job_id':115627188579,'artifact_id':11864550716,
    'artifact':{'bytes':3039985,'sha256':'962d7517ca5d91dd00b797f5b428bdf5fce1975c6c4afc392f7dc9e0a24b06fc'},
    'qualifier':{'bytes':59963,'sha256':'ed7e2cb2da75664027dcd6be1b7239e1fabe463eec1a3f951835eda7badd9877'},
    'generation_archive':{'bytes':2409058,'sha256':'b15026b0ee92354069159303ec73e6cbbe6bc07c44ad53bf2798cfcd8488d4d8'}}
ANIMATION_PIG={'bytes':97084456,'sha256':'465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'}
BUDGET=None
PHASE_COSTS=None


def budget_check(phase):
    if BUDGET is not None:BUDGET.check(phase)


@contextmanager
def measured_phase(name):
    budget_check(name);started=time.monotonic();completed=False
    try:
        yield
        completed=True
    finally:
        if PHASE_COSTS is not None:PHASE_COSTS.append({'phase':name,
            'elapsed_host_seconds':round(time.monotonic()-started,6),'completed':completed,
            'timing_scope':'host_Windows_fixture_work_not_Android_or_Thor'})


def generated_cache_name(name):
    inputs.safe_windows_name(name)
    return (name in NEW_WORLD_GLOBALS
            or (name.startswith(('data/geobin/object_library/','data/geobin/maps/')) and name.endswith('.bin'))
            or (name.startswith('data/geobin/object_library/') and name.endswith('.bounds')))


def map_command(target,map_id):
    require(map_id in WORLDS,'Reviewed selected world required')
    return [str(target),'-assertmode','8256','-db','127.0.0.1','-nosharedmemory','-nostats',
            '-udp',str(WORLDS[map_id][1]),'-tcp','0','-map_id',str(map_id),
            '-idleExitTimeout','0','-donotautogroup']


def pin(path):
    budget_check('content hashing')
    return inputs.leaf.pin(path)
def digest(value): return hashlib.sha256(inputs.leaf.canonical(value)).hexdigest()
def write(path,value):inputs.write(path,value)


def read_manifest(path):
    path=Path(path);require(path.is_file() and not path.is_symlink() and path.stat().st_size<=192*1024**2,
                            'Bounded regular prepared manifest required')
    value=json.loads(path.read_bytes())
    require(value.get('format')==1 and value.get('status')=='prepared' and value.get('public_apk')==inputs.APK
            and value.get('production_source')==inputs.SOURCE and value.get('asset_version')=='1.0.0'
            and set(value.get('providers',{}))=={'db','1','5'} and value.get('shipping_allowed') is False
            and value.get('native_processes_started')==0 and value.get('player_profile_opened') is False,
            'Current public prepared provider scope differs')
    require(value.get('public_audit')=={'run_id':inputs.PUBLIC_RUN,'public_audit_job_id':inputs.PUBLIC_AUDIT_JOB,
            'head_sha':inputs.SOURCE,'run_conclusion':'success','public_audit_conclusion':'success'},
            'Public .36 native provider admission differs')
    full=inputs.transport.worker_module('full_startup')
    require(value.get('asset_volumes')=={**inputs.leaf.VOLUMES,'Audio':full.AUDIO_VOLUME},
            'All four original Assets 1.0.0 volume identities required')
    require(value.get('fx_variants')==inputs.FX_VARIANTS and value.get('full_FX_BIN')==inputs.FX_VARIANTS['full'],
            'Exact full and SERVER-only FX variant pins required')
    for provider in value['providers'].values():
        files=provider['files'];require(0<len(files)<=inputs.MAX_FILES and provider['count']==len(files)
            and provider['bytes']==sum(x['bytes'] for x in files.values())<=inputs.MAX_TOTAL
            and digest(files)==provider['inventory_sha256'],'Provider manifest bounds/digest differ')
        aliases=set()
        for name,record in files.items():
            budget_check('provider manifest validation')
            inputs.safe_windows_name(name)
            require(name.casefold() not in aliases and set(record)=={'bytes','sha256','mtime_ns'}
                    and type(record['bytes']) is int and 0<=record['bytes']<=inputs.MAX_FILE
                    and re.fullmatch('[0-9a-f]{64}',record['sha256']) and type(record['mtime_ns']) is int
                    and 0<=record['mtime_ns']<2**63 and record['mtime_ns']%100==0,'Provider leaf metadata differs')
            aliases.add(name.casefold())
    return value


def extract_provider(archive_path,provider,destination):
    require(pin(archive_path)==provider['archive'],'Prepared provider archive differs')
    destination=Path(destination);require(not destination.exists(),'Fresh provider extraction required');destination.mkdir()
    seen=set()
    with tarfile.open(archive_path,'r:gz') as archive:
        for member in archive:
            budget_check('provider extraction')
            inputs.safe_windows_name(member.name);record=provider['files'].get(member.name)
            require(member.isfile() and not member.issym() and not member.islnk() and record is not None
                    and member.name not in seen and member.size==record['bytes'],'Provider member is unsafe or unpinned')
            seen.add(member.name);path=native_path(destination,member.name);path.parent.mkdir(parents=True,exist_ok=True)
            with archive.extractfile(member) as source,path.open('xb') as target:
                shutil.copyfileobj(source,target,1024**2)
            require(pin(path)=={k:record[k] for k in ('bytes','sha256')},'Provider leaf digest differs')
            os.utime(path,ns=(record['mtime_ns'],record['mtime_ns']))
            require(path.stat().st_mtime_ns//100==record['mtime_ns']//100,'Native provider timestamps were not preserved')
    require(seen==set(provider['files']),'Prepared provider archive omitted pinned leaves')
    return destination


def native_path(root,relative):
    """Keep legacy native Win32 consumers below MAX_PATH including the NUL."""
    inputs.safe_windows_name(relative)
    path=Path(root)/relative
    require(len(str(path.absolute()).encode('utf-16-le'))//2<260,
            'Native provider path exceeds MAX_PATH headroom')
    return path


def clone_provider(source,provider,destination,generated_cache=None):
    """Copy only pinned provider members into a fresh closed-process consumer.

    Actual BIN bodies may come from the separately qualified generator. The
    subsequent complete provider/content census authenticates immutable bytes
    before native launch. No progress mapping, native log, private configuration
    or other generated operational file becomes a warm input by directory copy.
    """
    source,destination=Path(source),Path(destination)
    require(source.is_dir() and not source.is_symlink() and not destination.exists(),
            'Fresh unlinked warm consumer destination required')
    names=provider['files'];members=dict(names)
    if generated_cache is not None:
        require(0<len(generated_cache)<=MAX_WORLD_CACHES,'Generated world cache membership exceeds bound')
        additions=set(generated_cache)-set(names)
        require(all(generated_cache_name(n) for n in additions),'Generated BIN membership escapes fixed native producer closure')
        members.update({n:generated_cache[n] for n in additions})
    require(0<len(members)<=inputs.MAX_FILES and len({n.casefold() for n in members})==len(members),
            'Warm input membership bound or case identity differs')
    destination.mkdir();copied=0
    for name in sorted(members):
        budget_check('immutable provider clone')
        if name in (CONFIG,'MapServer.exe'):continue
        original=native_path(source,name);target=native_path(destination,name)
        require(not original.is_symlink() and all(not p.is_symlink() for p in original.parents),
                'Linked original warm provider input refused')
        info=original.lstat();require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,
                                    'Private regular warm provider source required')
        expected=(generated_cache or {}).get(name,members[name])
        require(info.st_size==expected['bytes'],'Warm source size differs from authenticated membership')
        if name not in (generated_cache or {}):
            require(info.st_mtime_ns//100==names[name]['mtime_ns']//100,
                    'Immutable provider date changed before warm copy')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,target)
        later=original.lstat()
        require((later.st_dev,later.st_ino,later.st_size,later.st_mtime_ns)==
                (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)
                and target.stat().st_size==expected['bytes'] and target.stat().st_mtime_ns//100==info.st_mtime_ns//100,
                'Warm input changed during bounded regular copy')
        if name in (generated_cache or {}):require(pin(target)==generated_cache[name],'Warm generated BIN digest changed')
        copied+=1
    return {'copied_provider_files':copied,'operational_members_excluded':True,
            'private_configuration_copied':False,'generated_cache_byte_identity_checked':generated_cache is not None,
            'immutable_content_census_required_before_launch':True,
            'explicit_generated_world_cache_members':sorted(set(members)-set(names))}


def cache_snapshot(runtime):
    result={}
    for directory in ('data/bin','data/server/bin','data/geobin'):
        root=Path(runtime)/directory
        if directory=='data/geobin' and not root.exists():continue
        require(root.is_dir() and not root.is_symlink(),'Native BIN directory missing/linked')
        for path in sorted(root.rglob('*')):
            budget_check('native cache census')
            if not path.is_file() or path.suffix not in (('.bin','.bounds') if directory=='data/geobin' else ('.bin',)):continue
            name=path.relative_to(runtime).as_posix()
            require(directory!='data/geobin' or generated_cache_name(name),'Unreviewed geometry BIN layout')
            require(len(result)<MAX_WORLD_CACHES,'Native world BIN bound exceeded');result[name]=pin(path)
    require(result and 'data/bin/sequencers.bin' in result,'Current native cache closure missing')
    return result


def cache_dates(runtime,cache):
    return {n:(Path(runtime)/n).stat().st_mtime_ns//100*100 for n in cache}


def retain_generation_outputs(runtime,before,after,output):
    """Preserve actual asset cache bytes before format gates can reject them."""
    delta=cache_delta(before,after);names=sorted(set(delta['added'])|set(delta['changed']))
    require(len(names)<=MAX_WORLD_CACHES and sum(after[n]['bytes'] for n in names)<=256*1024**2,
            'Native generated cache evidence exceeds safe retention bound')
    require(all(generated_cache_name(n) or n in before for n in names),'Unreviewed generation evidence path')
    archive_path=Path(output)/'stock-native-generated-cache-outputs.tar.gz'
    require(not archive_path.exists(),'Fresh generation evidence archive required')
    members={}
    with tarfile.open(archive_path,'w:gz') as archive:
        for name in names:
            path=native_path(runtime,name);info=path.lstat()
            require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and info.st_nlink==1 and pin(path)==after[name],
                    'Actual native cache output changed before retention')
            member=tarfile.TarInfo(name);member.size=info.st_size;member.mtime=info.st_mtime_ns//10**9;member.mode=0o600
            with path.open('rb') as stream:archive.addfile(member,stream)
            require(pin(path)==after[name] and path.stat().st_mtime_ns==info.st_mtime_ns,
                    'Actual native cache output changed during retention')
            members[name]={**after[name],'mtime_ns':info.st_mtime_ns//100*100}
    result={'archive':pin(archive_path),'members':members,'exact_current_native_outputs_retained':True,
            'source_or_player_files_included':False,'cache_validation_alone_admits_native_world':False}
    write(Path(output)/'stock-native-generated-cache-outputs.json',result)
    return result


def provider_inventory(runtime,cache):
    runtime=Path(runtime);values={}
    for root in (runtime/'data',runtime/'piggs'):
        require(root.is_dir() and not root.is_symlink(),'Native provider directory missing/linked')
        def walk_error(error):raise error
        for current,dirs,files in os.walk(root,followlinks=False,onerror=walk_error):
            budget_check('complete source hashing')
            require(not any((Path(current)/n).is_symlink() for n in dirs),'Linked native provider directory refused')
            for name in files:
                budget_check('complete source hashing')
                path=Path(current)/name;relative=path.relative_to(runtime).as_posix()
                if relative in cache or relative==CONFIG:continue
                info=path.lstat();require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,
                                        'Private regular provider leaf required')
                require(len(values)<inputs.MAX_FILES,'Native provider inventory exceeded bound')
                values[relative]={**pin(path),'mtime_ns':info.st_mtime_ns//100*100}
    for path in runtime.iterdir():
        if path.suffix.casefold() in ('.exe','.dll'):values[path.name]=pin(path)
    return values


def provider_snapshot(runtime,cache,inventory=None):
    values=provider_inventory(runtime,cache) if inventory is None else inventory
    return {'files':len(values),'bytes':sum(x['bytes'] for x in values.values()),
            'inventory_sha256':digest(values),'without_MapServer_sha256':digest({n:r for n,r in values.items() if n!='MapServer.exe'}),
            'native_components':{n:r for n,r in values.items() if '/' not in n},
            'identifier_inputs':{n:r for n,r in values.items() if n.casefold().endswith(('.dbidmap','.attribute'))},
            'world_and_graph_inputs':{n:r for n,r in values.items() if n.casefold().endswith(('.bcn','.bcn.date'))
                or re.fullmatch(r'data/maps/city_zones/city_01_0[12]/city_01_0[12]\.txt',n.casefold())},
            'scope':'all_data_except_exact_BINs_and_private_DB_configuration_plus_piggs_and_native_components',
            'full_content_hashed':True}


def cache_delta(before,after):
    return {'added':{n:after[n] for n in after.keys()-before.keys()},
            'removed':{n:before[n] for n in before.keys()-after.keys()},
            'changed':{n:{'before':before[n],'after':after[n]} for n in before.keys()&after.keys() if before[n]!=after[n]}}


def map_progress(raw,pid):
    require(isinstance(raw,bytes) and len(raw)==128,'Map progress record length differs')
    magic,version,size,observed,tid,seq,stage,started,completed,flags,count=struct.unpack_from('<8s10I',raw)
    if seq==0 or seq&1:return None
    require(magic==b'COHMAP1\0' and version==1 and size==128 and observed==pid and tid>0
            and flags==0 and count==len(MAP_STAGES) and str(stage) in MAP_STAGES
            and completed<=started<=completed+1 and not any(raw[48:]),'Map progress producer/counters differ')
    return {'windows_pid':observed,'main_thread_id':tid,'sequence':seq,'stage':MAP_STAGES[str(stage)],
            'tick_started':started,'tick_completed':completed,'raw_record_hex':raw.hex(),
            'raw_record_sha256':hashlib.sha256(raw).hexdigest()}


def read_progress(path,process):
    require(process.poll() is None,'Owned Map process exited')
    try:
        info=Path(path).lstat();require(stat.S_ISREG(info.st_mode) and not Path(path).is_symlink()
                and info.st_size==4096,'Fresh Map progress mapping differs')
        with Path(path).open('rb',buffering=0) as file:
            first=file.read(128);file.seek(0);second=file.read(128)
    except FileNotFoundError:return None
    return map_progress(first,process.child.pid) if first==second else None


def ready_status(text,map_id):
    require(map_id in WORLDS and len(text.encode())<=MAX_LOG,'Bounded reviewed native status required')
    rows=[m.groups() for line in text.splitlines() if (m:=re.fullmatch(r'\s*(\d+)\s+(\S+)\s+((?:NotReady|S:).*)',line))]
    require(len(rows)==1 and int(rows[0][0])==map_id and rows[0][1].replace('\\','/').split('/')[-1].casefold()==WORLDS[map_id][0].lower()+'.txt',
            'Native Db status does not name selected world')
    fields=rows[0][2]
    if 'NotReady' in fields:return None
    match=re.match(r'S:\s*(\d+)\s*/\s*(\d+)\s+Ip:\s*([0-9.]+):(\d+)\s+Mem:',fields)
    require(match is not None,'Native destination endpoint is malformed')
    network_age,stats_age,address,port=match.groups()
    require(address=='127.0.0.1' and int(port)==WORLDS[map_id][1] and int(network_age)<=20 and int(stats_age)<=20,
            'Native status endpoint or freshness differs')
    return {'map_id':map_id,'world':WORLDS[map_id][0],'address':address,'port':int(port),
            'network_age_seconds':int(network_age),'stats_age_seconds':int(stats_age),'native_response_sha256':hashlib.sha256(text.encode()).hexdigest()}


def world_markers(text,map_id):
    require(map_id in WORLDS and len(text.encode())<=MAX_LOG,'Bounded selected world console required')
    text=text.replace('\\','/')
    world,port,objects=WORLDS[map_id]
    markers=[r'loading map:\s*maps/City_Zones/'+world+'/'+world+r'\.txt',
             r'loading beacons\.\.',r'Created '+str(objects)+r' PhysX objects',
             r'Loaded actor spore grid',r'freeing all \.geo files\.\.\.done',r'Checking memory\.\. done',
             r'Server ready\. \(took ([0-9]+\.[0-9]+) seconds\)']
    positions=[];elapsed=None
    for marker in markers:
        matches=list(re.finditer(marker,text));require(len(matches)==1,'Exact native world phase missing/duplicated: '+marker)
        positions.append(matches[0].start())
        if matches[0].lastindex:elapsed=float(matches[0][1])
    require(positions==sorted(positions),'Native world phases are out of order')
    ack='COH_GAME_LOOPBACK_ONLY=1 active: IPv4 loopback binding policy'
    endpoint=f'COH_GAME_LOOPBACK_ONLY bind verified: protocol=udp address=127.0.0.1 port={port}'
    require(text.count(ack)==1 and text.count(endpoint)==1,'Held native Map did not verify selected UDP loopback endpoint')
    return {'map_id':map_id,'world':world,'udp_port':port,'PhysX_objects':objects,'ordered_world_phases':True,
            'native_console_startup_seconds':elapsed,'UDP_loopback_endpoint_verified':True,
            'initialization_geometry_parity_only':True,'behavioral_collision_proven':False}


def native_failures(text):
    """Use exact production failure/asset patterns without Linux guest imports."""
    source='android/guest/game_evidence.py';tree=ast.parse((ROOT/source).read_text())
    selected=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name)
        and t.id in ('LOG_LIMIT','FAILURE','CRITICAL_ASSET','BENIGN_NOTICE') for t in n.targets)]
    require(len(selected)==4,'Exact guest native error pattern definitions differ')
    namespace={'re':re,'require':require}
    exec(compile(ast.Module(body=selected,type_ignores=[]),source,'exec'),namespace)
    minimal.load_functions(source,('_text','diagnostic_failures'),namespace)
    return namespace['diagnostic_failures'](text)


class Memory:
    """Sample the retained Popen process handle; never reopen a recycled PID."""
    def __init__(self,process):self.process=process;self.values=[];self.total=0;self.last=0
    def sample(self):
        require(os.name=='nt','Actual memory sampling requires Windows')
        now=time.monotonic()
        if now-self.last<1:return
        self.last=now;require(self.process.poll() is None,'Owned memory process exited')
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),
                *[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
                 'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]]
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        fn=ctypes.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo
        fn.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD];fn.restype=wintypes.BOOL
        require(fn(wintypes.HANDLE(int(self.process.child._handle)),ctypes.byref(counters),counters.cb),
                'Owned native process memory query failed')
        self.total+=1;self.values.append({'elapsed_seconds':round(now-self.process.started,3),
            'working_set_bytes':int(counters.WorkingSetSize),'private_commit_bytes':int(counters.PrivateUsage),
            'lifetime_peak_working_set_bytes':int(counters.PeakWorkingSetSize),'lifetime_peak_commit_bytes':int(counters.PeakPagefileUsage)})
        if len(self.values)>MEMORY_SAMPLES:del self.values[16]
    def report(self):
        return {'source':'GetProcessMemoryInfo on retained Popen native process handle','samples':self.values,
                'sample_count':self.total,'omitted_samples':self.total-len(self.values),'sample_bound':MEMORY_SAMPLES,
                'Linux_RSS_PSS_measured':False,'Thor_measured':False}


def native_namespace(runtime):
    """Close the actual stock file/FolderCache namespace before proving absence."""
    runtime=Path(runtime);index={};pigs=[]
    def enumeration_error(error):
        raise ValueError('Native namespace enumeration failed; absence cannot be proven')
    for current,dirs,files in os.walk(runtime,followlinks=False,onerror=enumeration_error):
        for name in dirs+files:
            path=Path(current)/name;info=path.lstat()
            require(not path.is_symlink() and not getattr(info,'st_file_attributes',0)&0x400,
                    'Native namespace contains a link/reparse point')
        for name in files:
            path=Path(current)/name;key=path.relative_to(runtime).as_posix().casefold()
            require(key not in index and len(index)<inputs.MAX_FILES+MAX_WORLD_CACHES+256,
                    'Native namespace is ambiguous/oversized')
            index[key]=path
            if path.suffix.casefold() in ('.pigg','.hogg'):pigs.append(key)
    require(not any(key=='gamedatadir.txt' for key in index),'Native external directory control refused')
    require(not (runtime/'localdata').exists() and not (runtime/'serverdata').exists(),
            'Native local/server data overlay refused')
    # The unchanged file.c fallback searches CWD piggs/data/CWD. Autodetection
    # additionally requires an ancestor with both data and tools; no such
    # unaccounted provider or drive-level gamedatadir may influence this lane.
    ancestors=[]
    for parent in (runtime,*runtime.parents):
        require(not ((parent/'data').is_dir() and (parent/'tools').is_dir()),
                'Native automatic external data provider refused')
        ancestors.append(str(parent))
    drive=Path(runtime.anchor)
    require(not os.path.lexists(drive/'gamedatadir.txt'),'Native drive-level directory control refused')
    require(pigs==['piggs/server-animations.pigg'] and pin(index[pigs[0]])==ANIMATION_PIG,
            'Native Pig namespace is not the exact animation-only provider')
    with index[pigs[0]].open('rb') as stream:
        raw=stream.read(animation_package.HEADER.size)
        require(animation_package.HEADER.unpack(raw)==(0x123,2,2,16,48,5878),
                'Exact native animation Pig header differs')
        table=stream.read(animation_package.ENTRY.size*5878)
        require(len(table)==animation_package.ENTRY.size*5878,'Animation Pig table truncated')
        names=animation_package.pool(stream,0x6789,maximum=animation_package.MAX_METADATA)
        require(len(names)==5878 and len(set(names))==5878,'Animation Pig namespace membership differs')
        decoded=[]
        for raw in names:
            require(raw.endswith(b'\0') and raw.count(b'\0')==1,'Animation Pig member terminator differs')
            name=raw[:-1].decode('ascii');require(animation_package.safe_name(name),
                'Unknown non-animation member in native Pig namespace');decoded.append(name)
    return index,{'ordinary_search_roots':['./piggs','./data','./'],
        'original_and_current_casefolded_paths_checked':True,'linked_or_reparse_providers_refused':True,
        'external_directory_controls_refused':True,'automatic_data_tools_ancestor_pairs_absent':True,
        'checked_ancestors':ancestors,'animation_Pig':ANIMATION_PIG,'complete_Pig_member_count':5878,
        'complete_Pig_member_names_sha256':digest(decoded),'Pig_members_exclusively_original_anim_paths':True,
        'animation_Pig_member_recipe_source':pin(animation_package.__file__),
        'native_recipe_source':pin(ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c')}


def bind_world_dependencies(runtime,proof,original_sources):
    """Preserve native zero-date absence sentinels in their exact producer scope."""
    runtime=Path(runtime);positive={};negative={};original={n.casefold():r for n,r in original_sources.items()}
    require(len(original)==len(original_sources),'Original provider namespace is ambiguous')
    for cache,value in proof.items():
        positive[cache]=copy.deepcopy(value);kept=[]
        for dependency in value['after']['dependencies']:
            name=dependency['path'].casefold().removeprefix('data/')
            if dependency['timestamp']!=0:kept.append(dependency);continue
            expected=cache.removeprefix('data/geobin/').removesuffix('.bin').removesuffix('.bounds').casefold()+'.txt'
            require(cache.startswith('data/geobin/object_library/') and name==expected,
                    'Native absent dependency escapes fixed same-stem geometry recipe')
            require(all(prefix+name not in original for prefix in ('data/','','piggs/')),
                    'Zero-date dependency is present in original provider')
            negative.setdefault(cache,[]).append({'path':name,'native_dependency_timestamp':0,
                'original_source_absent':True,'kind':'native_same_stem_missing_text_sentinel'})
        positive[cache]['after']['dependencies']=kept
    result=generation.bind_dependency_sources(runtime,positive);namespace_proof=None
    if negative:
        namespace,namespace_proof=native_namespace(runtime)
        for cache,rows in negative.items():
            for row in rows:
                name=row['path']
                require(all(prefix+name not in namespace and not os.path.lexists(runtime/(prefix+name))
                            for prefix in ('data/','','piggs/')),
                        'Native absent dependency appeared in current namespace')
                row['current_native_namespace_source_absent']=True
            result[cache].extend(rows)
    return result,{'rows':sum(len(v) for v in negative.values()),
        'unique_paths':len({r['path'] for rows in negative.values() for r in rows}),
        'all_same_stem_object_library_text_with_native_zero_date':True,'namespace':namespace_proof,
        'original_complete_provider_membership_count':len(original),
        'original_complete_provider_membership_sha256':digest(sorted(original)),
        'native_sentinel_recipe':{'FileListInsert':pin(ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/utils/structInternals.c'),
            'ParserIsPersistNewer':pin(ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c'),
            'groupWriteGroupAndRootnameToBin':pin(ROOT/'upstream/ouroboros/Common/group/groupfileload.c'),
            'objectLibraryWriteBoundsFile':pin(ROOT/'upstream/ouroboros/Common/group/groupfilelib.c')}}


def validate_generation_changes(runtime,before,after,raw_before,original_sources=None):
    delta=cache_delta(before,after)
    require(not delta['removed'] and all(generated_cache_name(n) for n in delta['added']),
            'Native generation altered BIN membership outside fixed world producer closure')
    require(len(delta['added'])<=MAX_WORLD_CACHES and sum(p['bytes'] for p in delta['added'].values())<=256*1024**2,
            'New native world cache output exceeds producer bound')
    proof={};messages={}
    for name in delta['changed']:
        proof[name]=generation.parse6_equivalence(raw_before[name],(Path(runtime)/name).read_bytes())
    for name in delta['added']:
        raw=(Path(runtime)/name).read_bytes()
        if name=='data/server/bin/plaquemsg-en.bin':
            messages[name]={'structure':message_format.inspect_message_store(raw),'actual_input':after[name],
                            'schema_source':'MessageStore.c:msWriteBin/msReadBin'}
            continue
        decoded=generation.inspect_native_parse6(raw)
        require(decoded['dependency_count']>0,'New world cache lacks authoritative source dependencies')
        proof[name]={'after':decoded,'new_native_world_cache':True,
                     'kind':'GroupBounds_Parse6' if name.endswith('.bounds') else 'Parse6',
                     'native_payload_sha256':hashlib.sha256(raw[-decoded['body_bytes']:]).hexdigest(),
                     'original_payload_comparison_available':False}
    if delta['added']:require(isinstance(original_sources,dict),'New world caches require original immutable source authority')
    dependencies,negative=bind_world_dependencies(runtime,proof,original_sources or {})
    source_index={n.removeprefix('data/').casefold():r for n,r in (original_sources or {}).items() if n.startswith('data/')}
    for name,rows in dependencies.items():
        for row in rows:
            if original_sources is None:continue
            if row.get('kind')=='native_same_stem_missing_text_sentinel':continue
            original=source_index.get(row['path'].casefold())
            require(original is not None and row['actual_source']=={k:original[k] for k in ('bytes','sha256')}
                    and row['actual_source_mtime_ns']//100==original['mtime_ns']//100,
                    'Generated cache dependency escapes or changes original source authority')
    for name,value in messages.items():
        sources={n:r for n,r in (original_sources or {}).items()
                 if n.casefold().startswith('data/texts/english/server/plaques/')}
        require(0<len(sources)<=4096,'Original English plaque message source closure missing/bounded')
        cache_mtime=(Path(runtime)/name).stat().st_mtime_ns
        for source,original in sources.items():
            actual=Path(runtime)/source
            require(pin(actual)=={k:original[k] for k in ('bytes','sha256')}
                    and actual.stat().st_mtime_ns//100==original['mtime_ns']//100
                    and original['mtime_ns']//10**9<=cache_mtime//10**9,
                    'Plaque message cache source/date differs from original immutable provider')
        value['original_English_source_closure']=sources
        value['source_inventory_sha256']=digest(sources)
        value['actual_native_cache_mtime_ns']=cache_mtime
    return {'delta':delta,'Parse6_dependency_envelope_changes':proof,'actual_dependency_sources':dependencies,
            'native_negative_source_dependencies':negative,
            'new_MessageStore_outputs':messages,
            'existing_decoded_payload_and_schema_unchanged':True,
            'new_payloads_require_exact_stock_native_world_producer':True,
            'new_payloads_require_identical_warm_native_consumers':True,
            'fixed_new_cache_closure':{'global_BINs':sorted(NEW_WORLD_GLOBALS),
                'geometry_BIN_roots':['data/geobin/object_library/','data/geobin/maps/'],
                'geometry_bounds_root':'data/geobin/object_library/','geometry_bounds_extension':'.bounds',
                'geometry_bounds_native_validation':'objectLibraryLoadBoundsFileInternal checks schema/name/raw GroupBounds and Adler32 against computed original geometry; warm bytes and mtimes must remain unchanged',
                'source_recipe':'Common/group/groupfileload.c:makeBinName/groupWriteGroupAndRootnameToBin and retained global/message parser callsites',
                'source_files':{n:pin(ROOT/'upstream/ouroboros'/n) for n in (
                    'Common/group/groupfileload.c','Common/group/groupfilelib.c','Common/seq/AnimBitList.c',
                    'MapServer/src/ai/entaiBehaviorAlias.c','MapServer/src/ai/entaiInstance.c',
                    'MapServer/src/plaque.c','libs/UtilitiesLib/src/language/MessageStore.c',
                    'libs/UtilitiesLib/src/language/MultiMessageStore.c')}},
            'Android_cache_authority_created':False}


def load_inherited_stock(path,output,prepared_manifest):
    """Authenticate the original failed run and retain its one real ready case."""
    require(pin(path)==INHERITED_STOCK['artifact'],'Exact executed stock evidence ZIP required')
    destination=Path(output)/'inherited-stock-04b';require(not destination.exists(),'Fresh inherited evidence output required')
    destination.mkdir();names=set()
    with zipfile.ZipFile(path) as archive:
        require(0<len(archive.infolist())<=64 and sum(m.file_size for m in archive.infolist())<=32*1024**2,
                'Inherited stock evidence archive exceeds bound')
        for member in archive.infolist():
            inputs.safe_windows_name(member.filename)
            require(not member.is_dir() and not member.flag_bits&1 and member.filename.casefold() not in names
                    and stat.S_IFMT(member.external_attr>>16) in (0,stat.S_IFREG),'Unsafe inherited evidence member')
            names.add(member.filename.casefold());target=destination/member.filename;target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(member) as source,target.open('xb') as stream:shutil.copyfileobj(source,stream,1024**2)
    old=json.loads((destination/REPORT).read_bytes());facts=old['cases'][0]
    require(old['repository_commit']==INHERITED_STOCK['source'] and old['status']=='failed' and len(old['cases'])==1
            and old['failures']==['ValueError: Native dependency source missing/linked: object_library/v_cov/destructible_objects/v_destructible_place_holders/v_destructible_place_holders.txt']
            and old['owned_cleanup_verified'] is True and old['player_profile_opened'] is False
            and old['prepared_manifest']==prepared_manifest and old['public_APK']==inputs.APK
            and old['production_source']==inputs.SOURCE and old['behavioral_collision_proven'] is False
            and old['physical_device_executed'] is False and old['shipping_allowed'] is False,
            'Inherited stock source/result boundary differs')
    require(old['source_pins']['tools/android/interactive/qualify_native_map_world_037.py']==INHERITED_STOCK['qualifier']
            and old['source_pins']['tools/android/interactive/prepare_native_map_world_inputs_037.py']==pin(inputs.__file__),
            'Inherited stock qualifier/unchanged preparation source differs')
    require(facts==json.loads((destination/'1-server_only-generation/phase.json').read_bytes())
            and (facts['map_id'],facts['fx_variant'],facts['phase'],facts['role'])==(1,'server_only','generation','stock')
            and facts['synthetic_row_unchanged'] is True and facts['owned_cleanup_verified'] is True
            and not any(facts['original_source_delta'].values()) and not facts['cache_delta']['removed'],
            'Inherited stock case/immutable original inputs differ')
    for key in ('Map_progress_before_status','Map_progress_after_status'):
        value=facts[key];decoded=map_progress(bytes.fromhex(value['raw_record_hex']),value['windows_pid'])
        require(decoded==value and value['tick_completed']>0,'Inherited held-PID progress witness differs')
    first,later=(facts[k] for k in ('Map_progress_before_status','Map_progress_after_status'))
    require(first['windows_pid']==later['windows_pid'] and later['tick_completed']>first['tick_completed']
            and later['sequence']>first['sequence'] and facts['native_Db_status']['map_id']==1
            and facts['native_Db_status']['port']==7001 and facts['native_Db_status']['address']=='127.0.0.1'
            and facts['world_markers']['PhysX_objects']==2311 and facts['world_markers']['ordered_world_phases'] is True,
            'Inherited stock independent readiness/world proof differs')
    first_db,later_db=(facts[k] for k in ('Db_progress_before_world','Db_progress_after_status'))
    require(first_db['windows_pid']==later_db['windows_pid'] and later_db['loop_count']>first_db['loop_count']
            and later_db['sequence']>first_db['sequence'] and old['retained_native_build']==retained.provenance()
            and facts['actual_native']==facts['provider_before']['native_components']['MapServer.exe'],
            'Inherited held Db/native build authority differs')
    profile=json.loads((destination/'failed-native-observations.json').read_bytes())['synthetic_profile']
    require(profile['unchanged'] is True and profile['scope']=='new_disposable_fixture_only'
            and profile['original_canonical_sha256']==profile['current_canonical_sha256'],
            'Inherited disposable SQL identity/location witness differs')
    archive=destination/'1-server_only-generation/stock-native-generated-cache-outputs.tar.gz'
    retention=json.loads(archive.with_name('stock-native-generated-cache-outputs.json').read_bytes())
    require(pin(archive)==INHERITED_STOCK['generation_archive'] and retention==facts['native_generated_output_retention']
            and retention['archive']==INHERITED_STOCK['generation_archive'], 'Inherited actual stock cache bytes differ')
    authority={**INHERITED_STOCK,'original_overall_result':'failed','original_stock_world_readiness_genuine':True,
        'stock_native_readiness_reexecuted':False,'stock_native_execution_inherited':True,
        'negative_dependency_validation_fresh_in_this_qualifier':False,'negative_dependency_validation_status':'pending',
        'original_report':pin(destination/REPORT),
        'prepared_manifest':prepared_manifest,'disposable_SQL_fixture':profile}
    return {'facts':facts,'archive':archive,'retention':retention,'authority':authority}


def recover_stock_cache(runtime,before,before_dates,provider_before,raw_before,original_sources,inherited,case_output):
    """Restore only authenticated native cache outputs, never operational files."""
    original=inherited['facts'];members=inherited['retention']['members']
    require(before==original['cache_before'] and before_dates==original['cache_dates_before']
            and provider_before==original['provider_before'],'Inherited stock provider/native input authority differs')
    expected=set(original['cache_delta']['added'])|set(original['cache_delta']['changed'])
    require(set(members)==expected and len(members)<=MAX_WORLD_CACHES,'Inherited stock cache membership differs')
    seen=set()
    with tarfile.open(inherited['archive'],'r:gz') as archive:
        for member in archive:
            require(member.name in members and member.name not in seen and member.isfile()
                    and not member.issym() and not member.islnk()
                    and (member.name in before or generated_cache_name(member.name)),
                    'Inherited stock cache archive has an unsafe/unowned member')
            record=members[member.name];require(member.size==record['bytes'],'Inherited cache size differs')
            seen.add(member.name);path=native_path(runtime,member.name);path.parent.mkdir(parents=True,exist_ok=True)
            require(not path.is_symlink() and (not path.exists() or path.is_file()),'Inherited cache destination is linked/nonregular')
            if path.exists():require(member.name in before and pin(path)==before[member.name],'Inherited cache would overwrite changed input')
            with archive.extractfile(member) as stream,path.open('wb') as target:shutil.copyfileobj(stream,target,1024**2)
            require(pin(path)=={k:record[k] for k in ('bytes','sha256')},'Inherited actual cache digest differs')
            os.utime(path,ns=(record['mtime_ns'],record['mtime_ns']))
    after=cache_snapshot(runtime);dates=cache_dates(runtime,after)
    require(seen==expected and after==original['cache_after'] and dates==original['cache_dates_after'],
            'Inherited complete stock cache bytes/dates differ')
    provider_after=provider_snapshot(runtime,set(before)|set(after))
    require(provider_after==provider_before==original['provider_after'],'Inherited cache changed original provider/native components')
    proof=validate_generation_changes(runtime,before,after,raw_before,original_sources)
    require(proof['native_negative_source_dependencies']['rows']==136
            and proof['native_negative_source_dependencies']['unique_paths']==68,
            'Inherited actual native negative dependency closure differs')
    inherited['authority'].update(negative_dependency_validation_fresh_in_this_qualifier=True,
        negative_dependency_validation_status='passed')
    facts=copy.deepcopy(original);facts['inherited_native_execution']=inherited['authority'];facts['native_generation']=proof
    proof['actual_stock_producer']={'native':facts['actual_native'],'retained_native_build':retained.provenance(),
        'held_windows_pid':facts['Map_progress_after_status']['windows_pid'],'map_id':1,
        'native_Db_status':facts['native_Db_status'],'post_query_completed_ticks':facts['Map_progress_after_status']['tick_completed'],
        'world_initialization_markers':facts['world_markers'],'original_source_delta':facts['original_source_delta'],
        'provider_native_components':provider_after['native_components'],'inherited_execution':inherited['authority']}
    write(Path(case_output)/'phase.json',facts);write(Path(case_output)/'generation.json',proof)
    return facts


def phase_plan(baseline,candidate):
    baseline,candidate=Path(baseline),Path(candidate)
    cases=[]
    for variant in ('server_only','full'):
        cases.extend((variant,phase,role,native) for phase,role,native in (
            ('generation','stock',baseline/'MapServer-control.exe'),
            ('baseline-forward','baseline',baseline/'MapServer-profile.exe'),
            ('candidate-forward','candidate',candidate/candidate_package.BINARY)))
        if variant=='server_only':
            cases.extend((variant,phase,role,native) for phase,role,native in (
                ('candidate-reverse','candidate',candidate/candidate_package.BINARY),
                ('baseline-reverse','baseline',baseline/'MapServer-profile.exe')))
    return cases


def world_native_observations(raw,map_id):
    """Frame only the stock selected-world loadstart prefix; never repair rows."""
    require(type(raw) is bytes and len(raw)<=64*1024**2 and map_id in WORLDS,
            'Bounded selected-world native observations required')
    world=WORLDS[map_id][0]
    prefix=('loading map: maps/City_Zones/'+world+'/'+world+'.txt..').encode('ascii')
    marker=b'COH_MAP_BIN_FRESHNESS_V1 ';profile=b'COH_NATIVE_STARTUP_PROFILE_V1 '
    parts=[];offset=0;framed_rows=[]
    for line in raw.splitlines(keepends=True):
        raw_line_bytes=len(line)
        if marker in line:
            require(line.count(marker)==1,'Duplicated native freshness marker in one line')
            if not line.startswith(marker):
                require(line.startswith(prefix+marker) and not framed_rows,
                        'Unknown/duplicated progress prefix on native freshness row')
                framed_rows.append({'raw_line_offset_bytes':offset,'raw_marker_offset_bytes':offset+len(prefix),
                    'removed_exact_prefix':prefix.decode('ascii'),'raw_line_sha256':hashlib.sha256(line).hexdigest()})
                line=line[len(prefix):]
        require(profile not in line or line.startswith(profile),'Unknown prefix on native profiler row')
        parts.append(line);offset+=raw_line_bytes
    view=b''.join(parts);result=profiles.parse_observations(view)
    result['native_world_console_framing']={'original_stdout':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
        'validated_framed_view':{'bytes':len(view),'sha256':hashlib.sha256(view).hexdigest()},
        'selected_map_id':map_id,'known_prefixed_rows':framed_rows,'native_rows_or_ordinals_rewritten':False,
        'legacy_native_parser_changed':False,'native_profiler_bounds_unchanged':True,
        'stock_loadstart_source':pin(ROOT/'upstream/ouroboros/MapServer/src/group/groupnetdb.c')}
    return result


def FX_consumption(observation,variant,input_pin):
    """Bind the actual native successful FX BIN path and stock freshness decision."""
    require(variant in inputs.FX_VARIANTS and input_pin==inputs.FX_VARIANTS[variant],
            'Native FX variant input differs')
    # FNV diagnostic tokens from exact retained C callsites: BIN decoder uses
    # bin/fxinfo.bin; freshness uses (bin/fxinfo.bin, fx, .fx). These tokens are
    # operation identifiers, not content hashes or independent authority.
    decoded=[r for r in observation['profile_rows'] if r['phase']=='bin_decode' and r['input_token']=='8a842dea']
    checked=[r for r in observation['freshness_rows'] if r['input_token']=='ca526c44']
    require(len(decoded)==len(checked)==1 and decoded[0]['success'] is True
            and checked[0]['outcome']=='freshness_accepted','Actual native FX BIN consumption/freshness did not pass')
    return {'variant':variant,'actual_input':input_pin,'native_decoder':decoded[0],'native_freshness':checked[0],
            'decoder_executed':True,'stock_freshness_accepted':True,'native_ID_table_observed':False}


def animation_consumption(raw,pig_pin):
    require(pig_pin=={'bytes':97084456,'sha256':'465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'},
            'Actual certified animation PIG input differs')
    names=('opened','certified','fallback','crypto_failed','raw_bytes','hash_us','stock_us',
           'skipped_rot_keys','skipped_pos_keys','scanned_rot_keys','scanned_pos_keys')
    rows=[]
    for line in raw.decode('ascii',errors='replace').replace('\r','').splitlines():
        if not line.startswith('COH_ANIM_CERT_V1 '):continue
        pairs=[p.split('=',1) for p in line.split()[1:]]
        require(all(len(p)==2 for p in pairs),'Native animation counter malformed')
        value=dict(pairs)
        require(len(value)==len(pairs) and set(value)=={'schema','pack',*names} and value['schema']=='1'
                and value['pack']==pig_pin['sha256'] and len(rows)<64,'Native animation counter producer differs')
        require(all(re.fullmatch('0|[1-9][0-9]*',value[n]) for n in names),'Native animation counters malformed')
        row={n:int(value[n]) for n in names}
        require(all(v<2**64 for v in row.values()) and row['opened']>0
                and row['certified']+row['fallback']==row['opened'] and row['crypto_failed']==0,
                'Native animation counter accounting differs')
        if rows:require(all(row[n]>=rows[-1][n] for n in names),'Native animation counters regressed')
        rows.append(row)
    require(rows and rows[-1]['certified']>0 and rows[-1]['raw_bytes']>=rows[-1]['certified']*596
            and rows[-1]['skipped_rot_keys']+rows[-1]['skipped_pos_keys']>0,
            'Actual native certified animation consumption did not execute')
    return {'counter_rows':rows,'latest_counters':rows[-1],'actual_PIG_input':pig_pin,
            'loaded_subset_only':True,'whole_inventory_loaded_claimed':False,'native_PIG_IO_trace_observed':False}


def owned_process_class(base_process):
    """Isolate each native Windows console without changing observer bounds."""
    class OwnedProcess(base_process):
        def __init__(self,command,cwd,logs,label,*,env=None,interactive=False):
            if os.name!='nt':
                super().__init__(command,cwd,logs,label,env=env,interactive=interactive)
                return
            self.label,self.started=label,time.monotonic()
            self.stdout,self.stderr=logs/(label+'-stdout.log'),logs/(label+'-stderr.log')
            self.handles=[self.stdout.open('xb'),self.stderr.open('xb')]
            try:
                # A shared runner console can have more than the observer's
                # 32 verified peers. Own a fresh console; keep both output
                # handles file-backed and retain this exact Popen handle.
                self.child=subprocess.Popen(command,cwd=cwd,env=env,
                    stdin=subprocess.PIPE if interactive else subprocess.DEVNULL,
                    stdout=self.handles[0],stderr=self.handles[1],
                    creationflags=subprocess.CREATE_NEW_CONSOLE)
            except Exception:
                self.close()
                raise
            self.forced_stop=False
        def stop(self):
            if self.child.poll() is None:self.forced_stop=True;self.child.terminate();self.child.wait(timeout=15)
            self.close()
    return OwnedProcess


def progress_snapshot(path,process):
    """Retain raw bounded bytes even when a failed startup cannot be admitted."""
    result={'held_windows_pid':process.child.pid,'held_process_exit_code':process.child.poll()}
    path=Path(path)
    if not path.exists():return dict(result,mapping_present=False)
    info=path.lstat();require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and info.st_size==4096,
                            'Failure Map progress mapping is not a bounded regular native file')
    with path.open('rb',buffering=0) as stream:
        first=stream.read(128);stream.seek(0);second=stream.read(128)
    result.update(mapping_present=True,mapping_bytes=info.st_size,raw_record_hex=first.hex(),
                  raw_record_sha256=hashlib.sha256(first).hexdigest(),stable_read=first==second)
    if first==second:
        try:result['decoded_record']=map_progress(first,process.child.pid)
        except ValueError as error:result['decoding_failure']=str(error)
    return result


def owned_process_times(process):
    require(os.name=='nt','Actual retained-handle CPU observations require Windows')
    result={'held_windows_pid':process.child.pid,'exit_code':process.child.poll(),
            'elapsed_seconds':round(time.monotonic()-process.started,3),
            'source':'GetProcessTimes on retained Popen native process handle'}
    fields=[wintypes.FILETIME() for _ in range(4)]
    fn=ctypes.WinDLL('kernel32',use_last_error=True).GetProcessTimes
    fn.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)];fn.restype=wintypes.BOOL
    require(fn(wintypes.HANDLE(int(process.child._handle)),*[ctypes.byref(x) for x in fields]),
            'Owned process CPU query failed')
    seconds=lambda x:round(((int(x.dwHighDateTime)<<32)|int(x.dwLowDateTime))/10**7,6)
    result.update(kernel_cpu_seconds=seconds(fields[2]),user_cpu_seconds=seconds(fields[3]))
    return result


def failure_snapshot(probe,start,read_dispatch):
    result={'case':probe.get('label'),'map_id':probe.get('map_id'),'admitted_world_ready':False,'errors':[]}
    result['last_readiness_observation']=probe.get('last_readiness_observation')
    result['Db_ready_baseline']=probe.get('Db_ready_baseline')
    map_process=probe.get('map_process');db_process=probe.get('db_process')
    for name,process in (('Map',map_process),('Db',db_process)):
        if process is not None:
            try:result[name+'_owned_process']=owned_process_times(process)
            except Exception as error:result['errors'].append(name+' CPU: '+type(error).__name__+': '+str(error))
    if map_process is not None:
        try:result['Map_progress_before_query']=progress_snapshot(probe['progress'],map_process)
        except Exception as error:result['errors'].append('Map progress: '+type(error).__name__+': '+str(error))
        try:
            if map_process.child.poll() is None:probe['memory'].sample()
            result['Map_memory']=probe['memory'].report()
        except Exception as error:result['errors'].append('Map memory: '+type(error).__name__+': '+str(error))
    if db_process is not None and 'db_stages' in probe:
        try:result['Db_dispatch']=read_dispatch(probe['dispatch'],db_process,probe['db_stages'])
        except Exception as error:result['errors'].append('Db dispatch: '+type(error).__name__+': '+str(error))
    # A status-only request is independent evidence, never a replacement for
    # the failed console+held-PID readiness gate. It does not mutate characters.
    if map_process is not None and db_process is not None and all(p.child.poll() is None for p in (map_process,db_process)):
        query=None
        try:
            query=start(minimal.map_query_command(probe['runtime'],probe['map_id']),probe['runtime'],
                        probe['logs'],probe['label']+'-failed-status',probe['env'])
            probe['children'].append(query)
            result['status_query_exit_code']=query.wait(15)
            text=query.text();result['status_query_stdout']=text
            result['status_query_stdout_sha256']=hashlib.sha256(text.encode()).hexdigest()
            result['native_Db_status']=ready_status(text,probe['map_id'])
        except Exception as error:result['errors'].append('failure status: '+type(error).__name__+': '+str(error))
        finally:
            if query is not None:
                try:query.stop()
                except Exception as error:result['errors'].append('failure query cleanup: '+type(error).__name__)
        try:result['Map_progress_after_query']=progress_snapshot(probe['progress'],map_process)
        except Exception as error:result['errors'].append('post-query progress: '+type(error).__name__+': '+str(error))
    return result


def selected_pool(args):
    map_id=getattr(args,'pool_map_id',None);variant=getattr(args,'pool_fx_variant',None)
    require((map_id is None)==(variant is None),'Both exact pool selectors required')
    if map_id is None:return None
    require(type(map_id) is int and map_id in WORLDS and variant in inputs.FX_VARIANTS,
            'Reviewed map and FX pool required')
    return {'map_id':map_id,'fx_variant':variant}


def namespace_summary(value):
    return {k:value[k] for k in ('format','runtime','root_identity','namespace_sha256',
        'owned_error_log','full_namespace_verified','content_schema_native_SQL_gates_supplied',
        'unknown_leaf_deletion_allowed','shipping_allowed')}|{
        'ordinary_files':len(value['files']),'ordinary_file_bytes':sum(r['bytes'] for r in value['files'].values()),
        'directories':len(value['directories']),'complete_stat_ledger_embedded':False}


def run(args):
    global BUDGET,PHASE_COSTS
    require(os.name=='nt','Genuine world gate requires Windows')
    require(re.fullmatch('[0-9a-f]{40}',args.repository_commit) and 30<=args.timeout_seconds<=1800,
            'Exact source and finite host bound required')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==args.repository_commit,
            'Native world qualifier checkout source differs')
    selection=selected_pool(args);pool=None
    if selection is not None:
        import native_map_world_pool_037 as pool
    PHASE_COSTS=[]
    if pool is not None:BUDGET=pool.Budget(getattr(args,'operation_budget_seconds',7200))
    if selection:
        require(type(getattr(args,'run_id',None)) is int and args.run_id>0
                and type(getattr(args,'job_id',None)) is int and args.job_id>0,
                'Actual native pool run and job authority required')
        require(os.environ.get('GITHUB_RUN_ID')==str(args.run_id),'Actual Actions run differs')
        if getattr(args,'inherited_stock_evidence',None) is not None:
            require(selection=={'map_id':1,'fx_variant':'server_only'},
                    'Inherited stock generation belongs only to Atlas SERVER-only pool')
    with measured_phase('authenticate original manifest and native artifacts'):
        manifest=read_manifest(args.inputs/inputs.MANIFEST)
    pin_apk=args.inputs/'COH-Atlas-Gameplay-0.13.36.apk'
    require(pin(pin_apk)==inputs.APK,'Exact public .36 APK required')
    require(pin(args.inputs/'full-fxinfo.bin')==inputs.FX_VARIANTS['full'],'Exact original full FX BIN required')
    retained.validate_package(args.baseline);candidate=candidate_package.validate(args.candidate,
        candidate_reuse.SOURCE,args.baseline)
    work=args.work.resolve();output=args.output.resolve()
    require(not work.exists() and not output.exists() and work!=output and ROOT not in work.parents
            and work not in ROOT.parents and work not in output.parents and output not in work.parents,
            'Fresh independent owned native work and evidence required')
    sys.path[:0]=[str(ROOT/'database/postgresql/tests'),str(ROOT/'database/postgresql')]
    import pg_local
    import run_network_ack as network
    from character_console import ConsoleCapture
    network.make_private_directory(work);output.mkdir(parents=True)
    report={'format':1,'status':'failed','scope':'actual_Windows_Atlas_Kings_world_initialization_and_geometry_parity',
        'repository_commit':args.repository_commit,'public_APK':inputs.APK,'production_source':inputs.SOURCE,
        'prepared_manifest':pin(args.inputs/inputs.MANIFEST),'retained_native_build':retained.provenance(),
        'candidate_native_build':candidate,'cases':[],'failures':[],'player_profile_opened':False,
        'SQL_scope':'new_disposable_fixture_only','behavioral_collision_proven':False,'physical_device_executed':False,
        'shipping_allowed':False,'freshness_bypass_enabled':False,'source_hashing_warms_host_filesystem_cache':True,
        'owned_cleanup_verified':False,'generated_cache_authorizes_Android_reuse':False}
    if selection is not None:report.update(scope='actual_Windows_one_Map_FX_pool_initialization_and_geometry_parity',
        selected_pool=selection,provider_runtime_reused=True,
        host_phase_costs=PHASE_COSTS,operation_budget_seconds=getattr(args,'operation_budget_seconds',7200),
        native_execution_authority={'source':args.repository_commit,
            'run_id':getattr(args,'run_id',None),'job_id':getattr(args,'job_id',None),
            'fresh_native_world_processes_only':True},complete_all_16_case_gate_claimed=False)
    inherited=None
    partial=None;partial_values=None
    cluster=None;children=[];observers=[];secrets=[];current=None;current_before=None;log_contexts=[];case_probe={}
    OwnedProcess=owned_process_class(network.Process)
    def start(command,runtime,logs,label,env):
        with measured_phase(label+' owned native process launch'):
            p=OwnedProcess(command,runtime,logs,label,env=env)
        children.append(p);return p
    def stop_case(case_children,case_observers):
        for p in reversed(case_children):p.stop()
        for observer in reversed(case_observers):observer.stop()
        require(all(p.child.poll() is not None for p in case_children),'Owned native case cleanup failed')
    try:
        if getattr(args,'partial_world_evidence',None) is not None:
            require(selection is not None and selection['map_id']==5,
                    'Partial world resume only executes still missing Kings pools')
            import recover_native_map_world_partial_037 as partial_recovery
            with measured_phase('authenticate cancelled original individual native cases'):
                partial,partial_values=partial_recovery.recover(args.partial_world_evidence)
            report['cancelled_original_individual_case_resume']={
                'source':partial_recovery.SOURCE,'run_id':partial_recovery.RUN,'job_id':partial_recovery.JOB,
                'artifact_id':partial_recovery.ARTIFACT,'artifact':partial_recovery.ZIP_PIN,
                'original_result':'cancelled','original_final_report_present':False,
                'original_global_cleanup_verified':False,'already_revalidated_native_cases':9}
        if getattr(args,'inherited_stock_evidence',None) is not None:
            inherited=load_inherited_stock(args.inherited_stock_evidence,output,report['prepared_manifest'])
            report['inherited_stock_generation']=inherited['authority']
        largest=max(manifest['providers'][str(m)]['bytes'] for m in WORLDS)+inputs.FX_VARIANTS['full']['bytes']
        require(shutil.disk_usage(work).free>=2*largest+3*1024**3,
                'Full world native fixture storage reserve unavailable')
        for port,kind in ((15439,socket.SOCK_STREAM),(6997,socket.SOCK_STREAM),(7000,socket.SOCK_DGRAM),
                          (7001,socket.SOCK_DGRAM),(7003,socket.SOCK_DGRAM)):
            with socket.socket(socket.AF_INET,kind) as probe:probe.bind(('127.0.0.1',port))
        with measured_phase('initialize disposable PostgreSQL'):
            cluster=pg_local.initialize(work/'pg',args.bin,15439,'coh_native_world',args.driver)
        secrets=list(cluster.secrets.values())
        schema_original=None;fixture=None
        for map_id in ((selection['map_id'],) if selection else (1,5)):
            # Original current-provider generation is measured separately; each
            # warm consumer then uses an independent copy of its resulting bytes.
            generated=None;decision_control=None
            original_provider=None;animation_reference=None
            for case_index,(variant,phase,role,native) in enumerate(phase_plan(args.baseline,args.candidate)):
                if selection and variant!=selection['fx_variant']:continue
                budget_check('admit next genuine native case')
                if role=='stock':
                    if generated is not None:shutil.rmtree(generated)
                    generated=None;decision_control=None
                    with measured_phase(str(map_id)+'-'+variant+' original provider extraction'):
                        seed=extract_provider(args.inputs/('provider-'+str(map_id)+'.tar.gz'),manifest['providers'][str(map_id)],
                            work/('s'+str(map_id)+str(case_index)))
                    require(pin(seed/'data/bin/fxinfo.bin')==inputs.FX_VARIANTS['server_only'],
                            'Actual public Map provider does not contain qualified SERVER-only FX')
                label=str(map_id)+'-'+variant+'-'+phase
                if selection:
                    current=seed if generated is None else generated
                    clone={'copied_provider_files':0,'operational_members_excluded':True,
                        'private_configuration_copied':False,'provider_runtime_reused':generated is not None,
                        'initial_private_manifest_extraction_used_directly':generated is None,
                        'full_content_source_cache_date_censuses_required_each_case':True}
                else:
                    current=work/('m'+str(map_id)+str(case_index))
                    with measured_phase(label+' immutable provider clone'):
                        clone=clone_provider(seed if generated is None else generated,manifest['providers'][str(map_id)],current,
                            cache_snapshot(generated) if generated is not None else None)
                # The full variant changes precisely this original BIN and
                # preserves its controlled source date before native generation.
                if generated is None and variant=='full':
                    shutil.copyfile(args.inputs/'full-fxinfo.bin',current/'data/bin/fxinfo.bin')
                    stamp=manifest['providers'][str(map_id)]['files']['data/bin/fxinfo.bin']['mtime_ns']
                    os.utime(current/'data/bin/fxinfo.bin',ns=(stamp,stamp))
                logs=work/(label+'-logs');logs.mkdir();case_output=output/label;case_output.mkdir()
                log_context={'runtime':current,'logs':logs,'output':case_output,'retained':False};log_contexts.append(log_context)
                with measured_phase(label+' fresh Db provider extraction'):
                    db=extract_provider(args.inputs/'provider-db.tar.gz',manifest['providers']['db'],work/('d'+str(map_id)+str(case_index)))
                config=db/CONFIG;config.write_text(minimal.guest_config(config.read_text(),cluster.meta['database'],cluster.connection_string(args.driver)))
                target=current/'MapServer.exe';shutil.copyfile(native,target)
                (current/CONFIG).write_bytes(config.read_bytes())
                with measured_phase(label+' full prelaunch source SDK and cache hashing'):
                    before=cache_snapshot(current);before_dates=cache_dates(current,before);source_before=provider_inventory(current,before)
                namespace_before=None
                if selection:
                    with measured_phase(label+' full prelaunch private namespace census'):
                        namespace_before=pool.closed_namespace(current,manifest['providers'][str(map_id)]['files'],before,BUDGET)
                    require(namespace_before['owned_error_log'] is None,'Prior operational error log was not transferred')
                provider_before=provider_snapshot(current,before,source_before)
                require(before['data/bin/fxinfo.bin']==inputs.FX_VARIANTS[variant],
                        'Current native FX consumer received wrong variant')
                if original_provider is None:original_provider=provider_before['without_MapServer_sha256']
                require(provider_before['without_MapServer_sha256']==original_provider,
                        'Full/compact world variants do not share exact non-BIN source provider')
                raw_before={n:(current/n).read_bytes() for n in before} if role=='stock' else {}
                current_before={'cache':before,'provider':provider_before,'native':pin(target)}
                current_before['regular_provider_clone']=clone
                current_before['cache_dates_before']=before_dates
                if namespace_before is not None:current_before['closed_private_namespace']=namespace_summary(namespace_before)
                write(case_output/'before-launch.json',current_before)
                if inherited is not None and (map_id,variant,phase,role)==(1,'server_only','generation','stock'):
                    original_sources={**manifest['providers'][str(map_id)]['files'],**source_before}
                    facts=recover_stock_cache(current,before,before_dates,provider_before,raw_before,original_sources,inherited,case_output)
                    if selection:
                        with measured_phase(label+' inherited stock restoration closed namespace'):
                            restored=pool.closed_namespace(current,manifest['providers'][str(map_id)]['files'],cache_snapshot(current),BUDGET)
                        facts['inherited_private_restoration_closed_namespace']=namespace_summary(restored)
                        facts['new_stock_native_process_executed']=False
                    report['cases'].append(facts);animation_identity=facts['actual_certified_animation_consumption']['latest_counters']
                    animation_reference={k:v for k,v in animation_identity.items() if k not in ('hash_us','stock_us')}
                    generated=current
                    if not selection:shutil.rmtree(seed)
                    shutil.rmtree(db)
                    current=None;current_before=None
                    continue
                if partial is not None and (map_id,variant,phase,role)==(5,'server_only','generation','stock'):
                    original_sources={**manifest['providers'][str(map_id)]['files'],**source_before}
                    with measured_phase(label+' captured current-provider stock cache-only checkout'):
                        facts=partial_recovery.restore_Kings_stock(current,before,before_dates,provider_before,
                            raw_before,original_sources,partial,partial_values,case_output)
                        restored=pool.closed_namespace(current,manifest['providers'][str(map_id)]['files'],cache_snapshot(current),BUDGET)
                    facts['fresh_private_Kings_stock_restore']['closed_namespace']=namespace_summary(restored)
                    write(case_output/'phase.json',facts);report['cases'].append(facts)
                    animation_identity=facts['actual_certified_animation_consumption']['latest_counters']
                    animation_reference={k:v for k,v in animation_identity.items() if k not in ('hash_us','stock_us')}
                    generated=current;shutil.rmtree(db);current=None;current_before=None
                    continue
                case_children=[];case_observers=[]
                case_probe={'label':label,'map_id':map_id,'runtime':current,'logs':logs,'children':case_children,
                            'source_before':source_before}
                env={k:v for k,v in os.environ.items() if not k.startswith(('COH_','PG'))}
                dispatch=db/'dispatch.bin';db_env=dict(env,COH_WINE_DB_FIXED_INPUTS='1',COH_WINE_DB_LOOPBACK_ONLY='1',
                    COH_WINE_DB_MANUAL_ATLAS='1',COH_WINE_DB_PROGRESS=str(dispatch))
                db_process=start([str(db/'DbServer.exe'),'-start','0'],db,logs,label+'-db',db_env);case_children.append(db_process)
                case_probe.update(db_process=db_process,dispatch=dispatch)
                db_console=ConsoleCapture(db_process.child.pid,logs,label+'-db');observers.append(db_console);case_observers.append(db_console);db_console.start()
                stages=manifest['db_package']['wine_build_input']['dispatch_progress']['stages']
                case_probe['db_stages']=stages
                first_dispatch=None
                def db_ready():
                    nonlocal first_dispatch
                    budget_check(label+' owned native Db readiness')
                    first_dispatch=minimal.read_dispatch(dispatch,db_process,stages)
                    text=db_console.text()+'\n'+db_process.text()
                    return first_dispatch and first_dispatch['loop_count']>0 and all(a in text for a in
                        (minimal.FIXED_ACK,minimal.LOOPBACK_ACK,minimal.MANUAL_ACK))
                with measured_phase(label+' fresh owned native Db readiness'):
                    network.wait_for(db_ready,[db_process],db,300,'owned retained minimal Db readiness')
                case_probe['Db_ready_baseline']=first_dispatch
                schema=minimal.schema_snapshot(cluster,manifest['schema'])
                if schema_original is None:
                    if inherited is not None:require(schema==inherited['facts']['schema_snapshot'],
                        'Fresh disposable Db schema differs from inherited native stock consumer')
                    schema_original=schema;fixture=minimal.seed_fixture(cluster)
                    if inherited is not None:require(fixture['canonical_sha256']==inherited['authority']['disposable_SQL_fixture']['original_canonical_sha256'],
                        'Fresh disposable fixture identity differs from inherited stock case')
                require(schema==schema_original,'Native full-world initialization changed database schema/attributes')
                progress=(work/('p'+str(map_id)+str(case_index)+'.bin')) if selection else current/'world-progress.bin'
                require(not progress.exists(),'Fresh unique current Map progress namespace required')
                map_env=dict(env,COH_GAME_LOOPBACK_ONLY='1',COH_WINE_MAP_PROGRESS=str(progress))
                if role=='candidate':map_env['COH_MAP_ANIMATION_METADATA_PREFETCH']='1'
                # Keep the exact -nogui assertion policy, but allow the already
                # owned fresh console to execute native setvbuf(_IONBF). With
                # -nogui, loadend/Server-ready stdout may remain buffered after
                # the final explicitly flushed loadstart despite live ticks.
                command=map_command(target,map_id)
                map_process=start(command,current,logs,label+'-map',map_env);case_children.append(map_process)
                map_console=ConsoleCapture(map_process.child.pid,logs,label+'-map');observers.append(map_console);case_observers.append(map_console);map_console.start()
                memory=Memory(map_process);first=None;later=None;status=None;deadline=time.monotonic()+args.timeout_seconds
                readiness_started=time.monotonic()
                case_probe.update(map_process=map_process,progress=progress,memory=memory,env=env)
                while True:
                    budget_check(label+' owned native world readiness')
                    require(time.monotonic()<deadline,'Owned native world readiness timed out')
                    require(map_process.poll() is None and db_process.poll() is None,'Owned world or Db process exited')
                    memory.sample();sample=read_progress(progress,map_process)
                    text=map_console.text()+'\n'+map_process.text()
                    case_probe['last_readiness_observation']={'observed_utc_ms':int(time.time()*1000),
                        'elapsed_Map_seconds':round(time.monotonic()-map_process.started,3),
                        'held_Map_windows_pid':map_process.child.pid,'Map_progress':sample,
                        'Server_ready_stdout_observed':'Server ready.' in text}
                    if sample and sample['tick_completed']>0 and 'Server ready.' in text:
                        first=sample;break
                    time.sleep(.1)
                PHASE_COSTS.append({'phase':label+' owned native Map readiness',
                    'elapsed_host_seconds':round(time.monotonic()-readiness_started,6),'completed':True,
                    'timing_scope':'host_Windows_native_process_not_Android_or_Thor'})
                marker_text=map_console.text()
                # Console screen and redirected stdout may duplicate the same
                # native stream. Use one whole owned stream for phase witnesses.
                if 'Server ready.' not in marker_text:marker_text=map_process.text()
                markers=world_markers(marker_text,map_id)
                query=start(minimal.map_query_command(current,map_id),current,logs,label+'-status',env);case_children.append(query)
                require(query.wait(45)==0,'Genuine native Db world status query failed')
                status=ready_status(query.text(),map_id);require(status is not None,'Native destination remains NotReady')
                for line in query.text().splitlines():require(not network.is_failure_line(line),'Native status emitted failure')
                while True:
                    budget_check(label+' post-status native tick advancement')
                    require(time.monotonic()<deadline,'Native post-status tick advancement timed out')
                    memory.sample();later=read_progress(progress,map_process)
                    if later and later['tick_completed']>first['tick_completed'] and later['sequence']>first['sequence']:break
                    time.sleep(.1)
                db_later=minimal.read_dispatch(dispatch,db_process,stages)
                require(db_later and db_later['loop_count']>first_dispatch['loop_count'],'Native Db dispatch did not advance during world queries')
                require(minimal.fixture_snapshot(cluster)['canonical_sha256']==fixture['canonical_sha256'],
                        'Synthetic character identity/location was changed')
                elapsed=time.monotonic()-map_process.started;memory.sample()
                write(case_output/'native-ready-before-observation-parsing.json',{
                    'map_id':map_id,'fx_variant':variant,'phase':phase,'role':role,'actual_native':pin(target),
                    'command':command,'world_markers':markers,'native_Db_status':status,
                    'host_ready_status_and_post_query_tick_seconds':round(elapsed,3),
                    'Map_progress_before_status':first,'Map_progress_after_status':later,
                    'Db_progress_before_world':first_dispatch,'Db_progress_after_status':db_later,
                    'memory':memory.report(),'synthetic_row_unchanged':True,
                    'whole_case_admitted_passed':False,'all_cache_parity_checks_complete':False,
                    'observation_parser_validation_pending':True})
                observation=world_native_observations(map_process.stdout.read_bytes(),map_id) if role!='stock' else None
                animation=animation_consumption(map_process.stdout.read_bytes(),pin(current/'piggs/server-animations.pigg'))
                animation_identity={k:v for k,v in animation['latest_counters'].items() if k not in ('hash_us','stock_us')}
                if animation_reference is None:animation_reference=animation_identity
                require(animation_identity==animation_reference,'Native full/compact or prefetch variants changed observed animation subset')
                if role=='candidate':observation['metadata_prefetch']=profiles.prefetch_observation(map_process.stdout.read_bytes())
                elif role!='stock':require(b'COH_MAP_ANIMATION_METADATA_PREFETCH_V1' not in map_process.stdout.read_bytes(),'Baseline unexpectedly enabled candidate')
                stop_case(case_children,case_observers)
                require(minimal.fixture_snapshot(cluster)['canonical_sha256']==fixture['canonical_sha256']
                        and minimal.schema_snapshot(cluster,manifest['schema'])==schema_original,
                        'Owned native case cleanup changed synthetic identity/location or schema')
                with measured_phase(label+' full poststop source SDK cache byte and date census'):
                    after=cache_snapshot(current);source_after=provider_inventory(current,set(before)|set(after))
                    after_dates=cache_dates(current,after)
                provider_after=provider_snapshot(current,set(before)|set(after),source_after);delta=cache_delta(before,after)
                facts={'map_id':map_id,'fx_variant':variant,'phase':phase,'role':role,'command':command,'actual_native':pin(target),
                    'host_ready_status_and_post_query_tick_seconds':round(elapsed,3),'world_markers':markers,
                    'native_Db_status':status,'Map_progress_before_status':first,'Map_progress_after_status':later,
                    'Db_progress_before_world':first_dispatch,'Db_progress_after_status':db_later,
                    'memory':memory.report(),'cache_before':before,'cache_after':after,'cache_delta':delta,
                    'cache_dates_before':before_dates,'cache_dates_after':after_dates,
                    'provider_before':provider_before,'provider_after':provider_after,
                    'original_source_delta':cache_delta(source_before,source_after),
                    'observed_native_decoder_and_freshness_prefix_only':True,
                    'native_profiler_limits_unchanged':{'maximum_profile_rows_per_translation_unit':256,'maximum_freshness_rows':256},
                    'schema_snapshot':schema,'synthetic_row_unchanged':True,'owned_cleanup_verified':True,
                    'native_observations':observation,'Map_console':map_console.report(),'Db_console':db_console.report()}
                if selection:facts.update(provider_runtime_reused=role!='stock',
                    native_execution_authority=report['native_execution_authority'],
                    closed_private_namespace_before=namespace_summary(namespace_before),
                    whole_case_admitted_passed=False)
                facts['actual_certified_animation_consumption']=animation
                if role!='stock':facts['actual_FX_BIN_consumption']=FX_consumption(observation,variant,before['data/bin/fxinfo.bin'])
                # Persist full facts and deltas before any immutability gate.
                write(case_output/'phase.json',facts);report['cases'].append(facts)
                if role=='stock':
                    facts['native_generated_output_retention']=retain_generation_outputs(current,before,after,case_output)
                    write(case_output/'phase.json',facts)
                native_text,log_records=network.collect_logs(current,logs,case_output,secrets)
                report.setdefault('redacted_logs',[]).append(log_records);log_context['retained']=True
                require(not native_failures(native_text),'Owned native world reported failure or missing critical input')
                require(provider_before==provider_after and pin(target)==current_before['native'],
                        'Native world changed exact provider/native component inputs')
                if role=='stock':
                    original_sources={**manifest['providers'][str(map_id)]['files'],**source_before}
                    proof=validate_generation_changes(current,before,after,raw_before,original_sources);facts['native_generation']=proof
                    proof['actual_stock_producer']={'native':facts['actual_native'],
                        'retained_native_build':retained.provenance(),
                        'held_windows_pid':first['windows_pid'],'map_id':map_id,
                        'native_Db_status':status,'post_query_completed_ticks':later['tick_completed'],
                        'world_initialization_markers':markers,'original_source_delta':facts['original_source_delta'],
                        'provider_native_components':provider_after['native_components']}
                    write(case_output/'generation.json',proof);generated=current
                    # The pinned compressed original archive and its complete
                    # manifest remain available; only this exact fresh expanded
                    # copy is released after owned processes stop and proofs land.
                    if not selection:shutil.rmtree(seed)
                else:
                    require(before==after==cache_snapshot(generated),'Warm native world changed generated BIN bytes')
                    require(before_dates==after_dates,'Warm native world rewrote byte-identical generated caches')
                    def decisions(o):return ([(r['phase'],r['input_token'],r['success']) for r in o['profile_rows']],
                                            [(r['input_token'],r['outcome']) for r in o['freshness_rows']])
                    if decision_control is None:decision_control=decisions(observation)
                    require(decisions(observation)==decision_control,'Warm native world changed ordered decoder/freshness decisions')
                    # Release only this fully stopped fresh owned case. Evidence
                    # and original public/provider trees are retained separately.
                    if not selection:shutil.rmtree(current)
                if selection:
                    with measured_phase(label+' closed namespace and owned operational transfer'):
                        namespace_after=pool.closed_namespace(current,manifest['providers'][str(map_id)]['files'],after,BUDGET)
                        private_archive=work/'owned-log-archive';private_archive.mkdir(exist_ok=True)
                        transfer=pool.quarantine_owned_error_log(current,private_archive,label,namespace_after,
                            stopped=all(p.child.poll() is not None for p in case_children))
                    facts.update(closed_private_namespace_after=namespace_summary(namespace_after),
                        owned_operational_log_transfer=transfer,whole_case_admitted_passed=True)
                    write(case_output/'phase.json',facts)
                shutil.rmtree(db);current=None;current_before=None;case_probe={}
            shutil.rmtree(generated)
        expected_cases=(5 if selection['fx_variant']=='server_only' else 3) if selection else 16
        require(len(report['cases'])==expected_cases,'Every selected pool/native consumer must execute and pass')
        if selection:
            stock_recovered=(inherited is not None or partial is not None and selection['fx_variant']=='server_only')
            report.update(status='passed',actual_native_worlds_executed=[selection['map_id']],
                initialization_geometry_parity_verified=True,actual_native_processes=expected_cases-int(stock_recovered),
                inherited_native_world_processes=int(stock_recovered),total_native_world_cases=expected_cases,
                selected_pool_only_verified=True,actual_full_and_SERVER_only_FX_world_consumers_verified=False,
                memory_measured=True,synthetic_fixture_proof=fixture,schema_snapshot=schema_original)
        else:
            report.update(status='passed',actual_native_worlds_executed=[1,5],initialization_geometry_parity_verified=True,
            actual_native_processes=16-int(inherited is not None),inherited_native_world_processes=int(inherited is not None),
            total_native_world_cases=16,baseline_and_candidate_pairs_per_world={'server_only':2,'full':1},
            actual_full_and_SERVER_only_FX_world_consumers_verified=True,FX_variants=inputs.FX_VARIANTS,
            memory_measured=True,synthetic_fixture_proof=fixture,schema_snapshot=schema_original)
    except Exception as error:
        report['failures'].append(type(error).__name__+': '+network.redact(str(error),secrets)[-4000:])
    finally:
        BUDGET=None # The reserved job budget remains available for owned cleanup and failure evidence.
        if report['failures'] and case_probe:
            try:
                value=failure_snapshot(case_probe,start,minimal.read_dispatch)
                if cluster is not None and fixture is not None:
                    current_fixture=minimal.fixture_snapshot(cluster)
                    value['synthetic_profile']={'scope':'new_disposable_fixture_only',
                        'original_canonical_sha256':fixture['canonical_sha256'],
                        'current_canonical_sha256':current_fixture['canonical_sha256'],
                        'unchanged':current_fixture['canonical_sha256']==fixture['canonical_sha256']}
                # The same configured redaction policy applies before public
                # retention; raw progress bytes have no SQL/profile content.
                value=json.loads(network.redact(json.dumps(value),secrets))
                write(output/'failed-native-observations.json',value)
                report['failed_native_observations']=pin(output/'failed-native-observations.json')
            except Exception as error:report['failures'].append('failure native observations: '+type(error).__name__)
        for child in reversed(children):
            try:child.stop()
            except Exception as error:report['failures'].append('owned child cleanup: '+type(error).__name__)
        for observer in reversed(observers):
            try:observer.stop()
            except Exception as error:report['failures'].append('owned console cleanup: '+type(error).__name__)
        if cluster is not None:
            try:cluster.stop()
            except Exception as error:report['failures'].append('owned PostgreSQL cleanup: '+type(error).__name__)
        if current is not None and current.exists():
            try:
                after=cache_snapshot(current);source_after=provider_inventory(current,set(current_before['cache'])|set(after))
                write(output/'failed-case-input-deltas.json',{'before':current_before,
                    'cache_after':after,'cache_delta':cache_delta(current_before['cache'],after),
                    'cache_dates_after':cache_dates(current,after),
                    'provider_after':provider_snapshot(current,set(current_before['cache'])|set(after),source_after),
                    'original_source_delta':cache_delta(case_probe['source_before'],source_after)})
            except Exception as error:report['failures'].append('failure input snapshot: '+type(error).__name__)
        for context in log_contexts:
            if context['retained']:continue
            try:
                text,records=network.collect_logs(context['runtime'],context['logs'],context['output'],secrets)
                report.setdefault('redacted_logs',[]).append(records)
                context['retained']=True
            except Exception as error:report['failures'].append('failure diagnostic retention: '+type(error).__name__)
        report['owned_cleanup_verified']=all(c.child.poll() is not None for c in children) and not any('cleanup:' in str(e) for e in report['failures'])
        if report['failures']:report['status']='failed'
        report['source_pins']={Path(__file__).relative_to(ROOT).as_posix():pin(__file__),
            Path(inputs.__file__).relative_to(ROOT).as_posix():pin(inputs.__file__),
            Path(message_format.__file__).relative_to(ROOT).as_posix():pin(message_format.__file__)}
        if pool is not None:report['source_pins'][Path(pool.__file__).relative_to(ROOT).as_posix()]=pin(pool.__file__)
        if partial is not None:report['source_pins'][Path(partial_recovery.__file__).relative_to(ROOT).as_posix()]=pin(partial_recovery.__file__)
        write(output/REPORT,report)
    require(report['status']=='passed','Actual native world gate failed; inspect '+str(output/REPORT))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('inputs','baseline','candidate','bin','work','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--driver',required=True);p.add_argument('--repository-commit',required=True)
    p.add_argument('--timeout-seconds',type=int,default=900)
    p.add_argument('--inherited-stock-evidence',type=Path)
    p.add_argument('--pool-map-id',type=int,choices=(1,5))
    p.add_argument('--pool-fx-variant',choices=('server_only','full'))
    p.add_argument('--operation-budget-seconds',type=int,default=7200)
    p.add_argument('--run-id',type=int);p.add_argument('--job-id',type=int)
    p.add_argument('--partial-world-evidence',type=Path)
    args=p.parse_args();run(args)


if __name__=='__main__':main()
