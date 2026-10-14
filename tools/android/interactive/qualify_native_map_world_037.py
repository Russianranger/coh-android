#!/usr/bin/env python3
"""Execute retained Map baseline/candidate in full Atlas and Kings worlds.

This is genuine Windows native world initialization and geometry/count parity.
It does not prove player movement, gameplay collision behavior, or Thor timing.
Only disposable PostgreSQL state is used. No produced cache enters an APK.
"""
from __future__ import annotations
import argparse
import ast
import ctypes
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


def generated_cache_name(name):
    inputs.safe_windows_name(name)
    return name in NEW_WORLD_GLOBALS or (name.startswith(('data/geobin/object_library/','data/geobin/maps/'))
                                        and name.endswith('.bin'))


def map_command(target,map_id):
    require(map_id in WORLDS,'Reviewed selected world required')
    return [str(target),'-assertmode','8256','-db','127.0.0.1','-nosharedmemory','-nostats',
            '-udp',str(WORLDS[map_id][1]),'-tcp','0','-map_id',str(map_id),
            '-idleExitTimeout','0','-donotautogroup']


def pin(path): return inputs.leaf.pin(path)
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
        for path in sorted(root.rglob('*.bin')):
            name=path.relative_to(runtime).as_posix()
            require(directory!='data/geobin' or generated_cache_name(name),'Unreviewed geometry BIN layout')
            require(len(result)<MAX_WORLD_CACHES,'Native world BIN bound exceeded');result[name]=pin(path)
    require(result and 'data/bin/sequencers.bin' in result,'Current native cache closure missing')
    return result


def provider_inventory(runtime,cache):
    runtime=Path(runtime);values={}
    for root in (runtime/'data',runtime/'piggs'):
        require(root.is_dir() and not root.is_symlink(),'Native provider directory missing/linked')
        for current,dirs,files in os.walk(root,followlinks=False):
            require(not any((Path(current)/n).is_symlink() for n in dirs),'Linked native provider directory refused')
            for name in files:
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
                     'native_payload_sha256':hashlib.sha256(raw[-decoded['body_bytes']:]).hexdigest(),
                     'original_payload_comparison_available':False}
    dependencies=generation.bind_dependency_sources(runtime,proof)
    if delta['added']:require(isinstance(original_sources,dict),'New world caches require original immutable source authority')
    source_index={n.removeprefix('data/').casefold():r for n,r in (original_sources or {}).items() if n.startswith('data/')}
    for name,rows in dependencies.items():
        for row in rows:
            if original_sources is None:continue
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
            'new_MessageStore_outputs':messages,
            'existing_decoded_payload_and_schema_unchanged':True,
            'new_payloads_require_exact_stock_native_world_producer':True,
            'new_payloads_require_identical_warm_native_consumers':True,
            'fixed_new_cache_closure':{'global_BINs':sorted(NEW_WORLD_GLOBALS),
                'geometry_BIN_roots':['data/geobin/object_library/','data/geobin/maps/'],
                'source_recipe':'Common/group/groupfileload.c:makeBinName/groupWriteGroupAndRootnameToBin and retained global/message parser callsites',
                'source_files':{n:pin(ROOT/'upstream/ouroboros'/n) for n in (
                    'Common/group/groupfileload.c','Common/seq/AnimBitList.c',
                    'MapServer/src/ai/entaiBehaviorAlias.c','MapServer/src/ai/entaiInstance.c',
                    'MapServer/src/plaque.c','libs/UtilitiesLib/src/language/MessageStore.c',
                    'libs/UtilitiesLib/src/language/MultiMessageStore.c')}},
            'Android_cache_authority_created':False}


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


def run(args):
    require(os.name=='nt','Genuine world gate requires Windows')
    require(re.fullmatch('[0-9a-f]{40}',args.repository_commit) and 30<=args.timeout_seconds<=1800,
            'Exact source and finite host bound required')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==args.repository_commit,
            'Native world qualifier checkout source differs')
    manifest=read_manifest(args.inputs/inputs.MANIFEST);pin_apk=args.inputs/'COH-Atlas-Gameplay-0.13.36.apk'
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
    cluster=None;children=[];observers=[];secrets=[];current=None;current_before=None;log_contexts=[];case_probe={}
    OwnedProcess=owned_process_class(network.Process)
    def start(command,runtime,logs,label,env):
        p=OwnedProcess(command,runtime,logs,label,env=env);children.append(p);return p
    def stop_case(case_children,case_observers):
        for p in reversed(case_children):p.stop()
        for observer in reversed(case_observers):observer.stop()
        require(all(p.child.poll() is not None for p in case_children),'Owned native case cleanup failed')
    try:
        largest=max(manifest['providers'][str(m)]['bytes'] for m in WORLDS)+inputs.FX_VARIANTS['full']['bytes']
        require(shutil.disk_usage(work).free>=2*largest+3*1024**3,
                'Full world native fixture storage reserve unavailable')
        for port,kind in ((15439,socket.SOCK_STREAM),(6997,socket.SOCK_STREAM),(7000,socket.SOCK_DGRAM),
                          (7001,socket.SOCK_DGRAM),(7003,socket.SOCK_DGRAM)):
            with socket.socket(socket.AF_INET,kind) as probe:probe.bind(('127.0.0.1',port))
        cluster=pg_local.initialize(work/'pg',args.bin,15439,'coh_native_world',args.driver);secrets=list(cluster.secrets.values())
        schema_original=None;fixture=None
        for map_id in (1,5):
            # Original current-provider generation is measured separately; each
            # warm consumer then uses an independent copy of its resulting bytes.
            generated=None;decision_control=None
            original_provider=None;animation_reference=None
            for case_index,(variant,phase,role,native) in enumerate(phase_plan(args.baseline,args.candidate)):
                if role=='stock':
                    if generated is not None:shutil.rmtree(generated)
                    generated=None;decision_control=None
                    seed=extract_provider(args.inputs/('provider-'+str(map_id)+'.tar.gz'),manifest['providers'][str(map_id)],
                        work/('s'+str(map_id)+str(case_index)))
                    require(pin(seed/'data/bin/fxinfo.bin')==inputs.FX_VARIANTS['server_only'],
                            'Actual public Map provider does not contain qualified SERVER-only FX')
                label=str(map_id)+'-'+variant+'-'+phase;current=work/('m'+str(map_id)+str(case_index))
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
                db=extract_provider(args.inputs/'provider-db.tar.gz',manifest['providers']['db'],work/('d'+str(map_id)+str(case_index)))
                config=db/CONFIG;config.write_text(minimal.guest_config(config.read_text(),cluster.meta['database'],cluster.connection_string(args.driver)))
                target=current/'MapServer.exe';shutil.copyfile(native,target)
                (current/CONFIG).write_bytes(config.read_bytes())
                before=cache_snapshot(current);source_before=provider_inventory(current,before)
                provider_before=provider_snapshot(current,before,source_before)
                require(before['data/bin/fxinfo.bin']==inputs.FX_VARIANTS[variant],
                        'Current native FX consumer received wrong variant')
                if original_provider is None:original_provider=provider_before['without_MapServer_sha256']
                require(provider_before['without_MapServer_sha256']==original_provider,
                        'Full/compact world variants do not share exact non-BIN source provider')
                raw_before={n:(current/n).read_bytes() for n in before} if role=='stock' else {}
                current_before={'cache':before,'provider':provider_before,'native':pin(target)}
                current_before['regular_provider_clone']=clone
                write(case_output/'before-launch.json',current_before)
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
                    first_dispatch=minimal.read_dispatch(dispatch,db_process,stages)
                    text=db_console.text()+'\n'+db_process.text()
                    return first_dispatch and first_dispatch['loop_count']>0 and all(a in text for a in
                        (minimal.FIXED_ACK,minimal.LOOPBACK_ACK,minimal.MANUAL_ACK))
                network.wait_for(db_ready,[db_process],db,300,'owned retained minimal Db readiness')
                case_probe['Db_ready_baseline']=first_dispatch
                schema=minimal.schema_snapshot(cluster,manifest['schema'])
                if schema_original is None:schema_original=schema;fixture=minimal.seed_fixture(cluster)
                require(schema==schema_original,'Native full-world initialization changed database schema/attributes')
                progress=current/'world-progress.bin'
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
                case_probe.update(map_process=map_process,progress=progress,memory=memory,env=env)
                while True:
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
                    require(time.monotonic()<deadline,'Native post-status tick advancement timed out')
                    memory.sample();later=read_progress(progress,map_process)
                    if later and later['tick_completed']>first['tick_completed'] and later['sequence']>first['sequence']:break
                    time.sleep(.1)
                db_later=minimal.read_dispatch(dispatch,db_process,stages)
                require(db_later and db_later['loop_count']>first_dispatch['loop_count'],'Native Db dispatch did not advance during world queries')
                require(minimal.fixture_snapshot(cluster)['canonical_sha256']==fixture['canonical_sha256'],
                        'Synthetic character identity/location was changed')
                elapsed=time.monotonic()-map_process.started;memory.sample()
                observation=profiles.parse_observations(map_process.stdout.read_bytes()) if role!='stock' else None
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
                after=cache_snapshot(current);source_after=provider_inventory(current,set(before)|set(after))
                provider_after=provider_snapshot(current,set(before)|set(after),source_after);delta=cache_delta(before,after)
                facts={'map_id':map_id,'fx_variant':variant,'phase':phase,'role':role,'command':command,'actual_native':pin(target),
                    'host_ready_status_and_post_query_tick_seconds':round(elapsed,3),'world_markers':markers,
                    'native_Db_status':status,'Map_progress_before_status':first,'Map_progress_after_status':later,
                    'Db_progress_before_world':first_dispatch,'Db_progress_after_status':db_later,
                    'memory':memory.report(),'cache_before':before,'cache_after':after,'cache_delta':delta,
                    'provider_before':provider_before,'provider_after':provider_after,
                    'original_source_delta':cache_delta(source_before,source_after),
                    'observed_native_decoder_and_freshness_prefix_only':True,
                    'native_profiler_limits_unchanged':{'maximum_profile_rows_per_translation_unit':256,'maximum_freshness_rows':256},
                    'schema_snapshot':schema,'synthetic_row_unchanged':True,'owned_cleanup_verified':True,
                    'native_observations':observation,'Map_console':map_console.report(),'Db_console':db_console.report()}
                facts['actual_certified_animation_consumption']=animation
                if role!='stock':facts['actual_FX_BIN_consumption']=FX_consumption(observation,variant,before['data/bin/fxinfo.bin'])
                # Persist full facts and deltas before any immutability gate.
                write(case_output/'phase.json',facts);report['cases'].append(facts)
                native_text,log_records=network.collect_logs(current,logs,case_output,secrets)
                report.setdefault('redacted_logs',[]).append(log_records);log_context['retained']=True
                require(not native_failures(native_text),'Owned native world reported failure or missing critical input')
                require(provider_before==provider_after and pin(target)==current_before['native'],
                        'Native world changed exact provider/native component inputs')
                if role=='stock':
                    proof=validate_generation_changes(current,before,after,raw_before,source_before);facts['native_generation']=proof
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
                    shutil.rmtree(seed)
                else:
                    require(before==after==cache_snapshot(generated),'Warm native world changed generated BIN bytes')
                    def decisions(o):return ([(r['phase'],r['input_token'],r['success']) for r in o['profile_rows']],
                                            [(r['input_token'],r['outcome']) for r in o['freshness_rows']])
                    if decision_control is None:decision_control=decisions(observation)
                    require(decisions(observation)==decision_control,'Warm native world changed ordered decoder/freshness decisions')
                    # Release only this fully stopped fresh owned case. Evidence
                    # and original public/provider trees are retained separately.
                    shutil.rmtree(current)
                shutil.rmtree(db);current=None;current_before=None;case_probe={}
            shutil.rmtree(generated)
        require(len(report['cases'])==16,'Both worlds require separately generated full and SERVER-only FX native consumers')
        report.update(status='passed',actual_native_worlds_executed=[1,5],initialization_geometry_parity_verified=True,
            actual_native_processes=16,baseline_and_candidate_pairs_per_world={'server_only':2,'full':1},
            actual_full_and_SERVER_only_FX_world_consumers_verified=True,FX_variants=inputs.FX_VARIANTS,
            memory_measured=True,synthetic_fixture_proof=fixture,schema_snapshot=schema_original)
    except Exception as error:
        report['failures'].append(type(error).__name__+': '+network.redact(str(error),secrets)[-4000:])
    finally:
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
        write(output/REPORT,report)
    require(report['status']=='passed','Actual native world gate failed; inspect '+str(output/REPORT))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('inputs','baseline','candidate','bin','work','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--driver',required=True);p.add_argument('--repository-commit',required=True)
    p.add_argument('--timeout-seconds',type=int,default=900)
    args=p.parse_args();run(args)


if __name__=='__main__':main()
