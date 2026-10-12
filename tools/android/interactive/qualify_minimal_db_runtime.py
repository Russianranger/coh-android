#!/usr/bin/env python3
"""Boot the retained manual DbServer twice with only its 62 authenticated inputs.

Windows + a new disposable PostgreSQL cluster only. No installed profile is
opened. MapServer runs query mode only; no world, Game, Wine or device claim.
"""
from __future__ import annotations
import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import struct
import subprocess
import sys
import tarfile
import time
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[3]
DONOR = {'bytes': 42048020, 'sha256': 'c2d859621476e22add673a76c4b6aae65c2143671e50c085d020108b6e19d95e'}
MANUAL_DB = {'bytes': 1664512, 'sha256': 'ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba'}
MAP = {'bytes': 7475200, 'sha256': 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'}
SCHEMA = 'b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92'
SCOPE = 'actual_retained_manual_dbserver_minimal_schema_native_windows'
PROOF = 'minimal-db-native-proof.json'
INPUTS_FIXTURE = 'tools/android/interactive/fixtures/minimal-db-native-inputs-0.13.34.json'
INPUTS_SHA256 = 'd39162bbd4768f9d233077772a6c73604f5d2266f9a3b832f13d0b46d7505a7d'
FIXED_ACK = 'COH_WINE_DB_FIXED_INPUTS=1 active: directory monitoring disabled; initial reads and lookup mode preserved'
LOOPBACK_ACK = 'COH_WINE_DB_LOOPBACK_ONLY=1 active: IPv4 listener binds restricted to loopback; endpoint verification required'
MANUAL_ACK = 'COH_WINE_DB_MANUAL_ATLAS=1 active: unused Launcher connection wait skipped; manual Atlas launch; ordinary DbServer readiness required'
SOURCE_FILES = (
    INPUTS_FIXTURE, 'tools/android/interactive/qualify_minimal_db_runtime.py',
    'tools/android/interactive/test_minimal_db_runtime_contract.py',
    'database/postgresql/pg_local.py', 'database/postgresql/001-coh-compat.sql',
    'database/postgresql/tests/run_network_ack.py', 'database/postgresql/tests/run_generated_schema.py',
    'database/postgresql/tests/character_console.py',
    'android/guest/local_login_server.py', 'android/guest/local_character_server.py',
    'android/guest/game_diagnostic.py', 'android/guest/dbserver_diagnostic.py',
    'android/guest/game_hang_evidence.py', 'android/guest/character_zoning.py',
    'database/wine-dbserver/overlay/DBServer/src/wine_dispatch_progress.c',
    'database/wine-dbserver/overlay/DBServer/src/wine_dispatch_progress.h')
FIXTURE = dict(containerid=90001, authid=77, authname='COHMINIMAL', name='MINIMALFIXTURE',
               staticmapid=5, mapid=None, posx=12.5, posy=-20.0, posz=40.25, logincount=3)


def require(condition, message):
    if not condition: raise ValueError(message)


def utc(): return datetime.now(timezone.utc).isoformat()
def encoded(value): return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
def pin(path):
    data=Path(path).read_bytes(); return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def digest(value): return hashlib.sha256(encoded(value)).hexdigest()
def source_pins(): return {name:pin(ROOT/name) for name in SOURCE_FILES}


def expected_inputs():
    raw=(ROOT/INPUTS_FIXTURE).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==INPUTS_SHA256,'Historical native input fixture changed')
    return json.loads(raw)


def load_functions(path, names, namespace):
    """Execute exact pure guest functions without Linux-only module imports."""
    tree=ast.parse((ROOT/path).read_text()); selected=[]
    for name in names:
        values=[node for node in ast.walk(tree) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name]
        require(len(values)==1,'Pure source function is missing/ambiguous: '+name)
        selected.append(values[0])
    exec(compile(ast.Module(body=selected,type_ignores=[]),path,'exec'),namespace)
    return namespace


def guest_config(original, database, connection):
    common={'require':require,'hashlib':hashlib,'HEX64':re.compile('[0-9a-f]{64}\\Z')}
    load_functions('android/guest/dbserver_diagnostic.py',('private_config',),common)
    namespace={'require':require,'dbserver':SimpleNamespace(private_config=common['private_config'])}
    load_functions('android/guest/game_diagnostic.py',('game_config',),namespace)
    return namespace['game_config'](original,database,connection)


def schema_snapshot(cluster, schema):
    namespace={'require':require,'hashlib':hashlib,'HEX64':re.compile('[0-9a-f]{64}\\Z')}
    load_functions('android/guest/dbserver_diagnostic.py',
                   ('column_digest','attribute_digest','sql_hash','schema_snapshot'),namespace)
    methods={name:namespace[name] for name in ('sql_hash','schema_snapshot')}
    methods['sql']=lambda self,query,**kw:cluster.sql(query,user='coh_game',database=cluster.meta['database'])
    reader=type('ExactGuestSchemaReader',(),methods)(); reader.schema=schema
    return reader.schema_snapshot()


def safe_members(raw):
    require(len(raw)<=64*1024**2,'Compressed native/schema archive exceeded bound')
    result={}; total=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        for member in archive.getmembers():
            name=PurePosixPath(member.name)
            require(member.isfile() and not name.is_absolute() and name.as_posix()==member.name
                    and all(p not in ('.','..') for p in name.parts) and '\\' not in member.name
                    and member.name not in result and 0<=member.size<=200*1024**2,
                    'Unsafe/duplicate nonregular archive member')
            total+=member.size
            require(len(result)<4096 and total<=300*1024**2,'Expanded native/schema archive exceeded bound')
            result[member.name]=archive.extractfile(member).read()
    return result


def donor_inputs(path):
    require(pin(path)==DONOR,'Exact independently audited .34 donor APK required')
    with zipfile.ZipFile(path) as apk:
        names=apk.namelist(); require(len(names)==len(set(names)),'Duplicate APK member')
        manifest=json.loads(apk.read('assets/runtime/runtime-manifest.json'))
        required=('dbserver-package.tar.gz','dbserver-schema.tar.gz','game-package.tar.gz',
                  'startup-dbserver.exe','startup-dbserver-manifest.json')
        raw={name:apk.read('assets/runtime/'+name) for name in required}
    for name,data in raw.items():
        require({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}==manifest['files'][name],
                'Donor runtime payload manifest differs: '+name)
    db=safe_members(raw['dbserver-package.tar.gz']); schema=safe_members(raw['dbserver-schema.tar.gz'])
    game=safe_members(raw['game-package.tar.gz']); dbdoc=json.loads(db['package-manifest.json'])
    sdoc=json.loads(schema['schema-manifest.json']); gdoc=json.loads(game['game-package.json'])
    require(hashlib.sha256(schema['schema-manifest.json']).hexdigest()==SCHEMA and len(sdoc['files'])==62
            and set(schema)==set(sdoc['files'])|{'schema-manifest.json'},'Exact 62-file schema bundle differs')
    files={}
    for name,record in sdoc['files'].items():
        payload=schema[name]
        require(name.startswith('data/') and {'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}==record,
                'Schema input differs: '+name)
        files[name]=payload
    for name,record in gdoc['files'].items():
        require(PurePosixPath(name).name==name,'Native dependency path differs')
        payload=game[name]
        require(len(payload)==record['bytes'] and hashlib.sha256(payload).hexdigest()==record['sha256'],
                'Native dependency differs: '+name)
        files[name]=payload
    for name,record in dbdoc['variants']['normal']['files'].items():
        require(files.get(name)==db['normal/'+name], 'Game and normal Db dependencies disagree: '+name)
    require({'bytes':len(raw['startup-dbserver.exe']),'sha256':hashlib.sha256(raw['startup-dbserver.exe']).hexdigest()}==MANUAL_DB,
            'Retained manual DbServer differs')
    require(hashlib.sha256(files['MapServer.exe']).hexdigest()==MAP['sha256'],'Retained native Map query producer differs')
    files['DbServer.exe']=raw['startup-dbserver.exe']
    return files,sdoc,dbdoc,{'donor_apk':DONOR,'manual_dbserver':MANUAL_DB,
        'mapserver':{'bytes':len(files['MapServer.exe']),'sha256':MAP['sha256']},
        'schema_manifest_sha256':SCHEMA,'schema_input_files':62,
        'initial_files':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()},
        'extra_world_data_files':0,'original_dbserver_package':digest(dbdoc),
        'retained_startup_manifest':hashlib.sha256(raw['startup-dbserver-manifest.json']).hexdigest()}


def parse_dispatch(raw, pid, stages):
    require(len(raw)==128,'Dispatch record length differs')
    magic,version,size,observed,tid,sequence,stage,loops,flags,count=struct.unpack_from('<8s9I',raw)
    if sequence==0 or sequence&1: return None
    require(magic==b'COHDBP1\0' and version==1 and size==128 and observed==pid and tid>0
            and count==len(stages) and str(stage) in stages and flags==0 and not any(raw[44:]),
            'Owned native dispatch producer/record differs')
    return dict(windows_pid=observed,main_thread_id=tid,sequence=sequence,stage=stage,
                loop_count=loops,raw_record_sha256=hashlib.sha256(raw).hexdigest())


def read_dispatch(path, process, stages):
    require(process.poll() is None,'Owned native DbServer exited')
    try:
        if not path.exists(): return None
        require(path.is_file() and not path.is_symlink() and path.stat().st_size==4096,
                'Dispatch mapping is not a bounded regular owned file')
        with path.open('rb',buffering=0) as source:
            first=source.read(128); source.seek(0); second=source.read(128)
    except FileNotFoundError: return None
    return parse_dispatch(first,process.child.pid,stages) if first==second else None


def map_query_command(runtime,map_id):
    require(type(map_id) is int and map_id in (1,5),'Only Atlas/Kings native status queries reviewed')
    return [str(runtime/'MapServer.exe'),'-nogui','-db','127.0.0.1','-dbquery','-timeout','10000','-getstatus','1',str(map_id)]


def validate_status(text,map_id):
    world={1:'City_01_01',5:'City_01_02'}[map_id]
    rows=[m.groups() for line in text.splitlines() if (m:=re.fullmatch(r'\s*(\d+)\s+(\S+)\s+(NotReady.*|S:.*)',line))]
    require(len(rows)==1 and int(rows[0][0])==map_id
            and rows[0][1].replace('\\','/').split('/')[-1].casefold()==world.lower()+'.txt'
            and re.fullmatch(r'NotReady 1 \(Not started\) Info(?: .*)?',rows[0][2]) is not None,
            'Native Db query did not prove exact unstarted destination')
    return {'map_id':map_id,'world':world,'not_started':True,'native_response_sha256':hashlib.sha256(text.encode()).hexdigest()}


def fixture_snapshot(cluster):
    query='SELECT coalesce(json_agg(x ORDER BY containerid),\'[]\'::json) FROM (SELECT '+','.join(FIXTURE)+' FROM dbo.ents) x;'
    rows=json.loads(cluster.sql(query,user='coh_game',database=cluster.meta['database']))
    require(rows==[FIXTURE],'Disposable synthetic identity/location changed')
    return digest(rows)


def seed_fixture(cluster):
    # Explicitly synthetic host rows in this new cluster, never player data.
    sql="INSERT INTO dbo.ents(containerid,active,authid,authname,name,staticmapid,mapid,posx,posy,posz,logincount) VALUES (90001,0,77,'COHMINIMAL','MINIMALFIXTURE',5,NULL,12.5,-20.0,40.25,3);"
    cluster.sql(sql,user='coh_game',database=cluster.meta['database'])
    return fixture_snapshot(cluster)


def source_commit(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{40}',value),'Exact repository commit required')
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    require(actual==value,'Native gate source commit differs from checkout')
    return value


def validate_proof(value,repository_commit):
    require(type(value) is dict and type(value.get('format')) is int and value['format']==1
            and value.get('status')=='passed' and value.get('scope')==SCOPE
            and value.get('repository_commit')==repository_commit and value.get('source_pins')==source_pins()
            and value.get('failures')==[]
            and type(value.get('run_id')) is int and value['run_id']>0
            and value.get('run_url')=='https://github.com/Russianranger/coh-android/actions/runs/'+str(value['run_id']),
            'Minimal native Db proof source/scope/status differs')
    for name in ('actual_retained_dbserver_host_fixture_executed','actual_native_map_query_executed',
                 'postgresql_disposable_cluster_only','owned_cleanup_verified','synthetic_identity_location_restart_preserved',
                 'full_schema_and_attributes_restart_preserved','fresh_minimal_runtime_each_start'):
        require(value.get(name) is True,'Minimal native Db gate missing: '+name)
    for name in ('full_runtime_executed','native_world_started','wine_executed','physical_execution_validated',
                 'player_profile_opened','native_character_gameplay_validated'):
        require(value.get(name) is False,'Minimal native Db gate overclaims: '+name)
    inputs=value.get('inputs',{})
    require(inputs==expected_inputs() and inputs.get('donor_apk')==DONOR and inputs.get('manual_dbserver')==MANUAL_DB
            and inputs.get('mapserver')==MAP
            and inputs.get('schema_manifest_sha256')==SCHEMA and inputs.get('schema_input_files')==62
            and inputs.get('extra_world_data_files')==0,'Minimal native Db input authority differs')
    phases=value.get('phases',[])
    require(len(phases)==2 and [p.get('name') for p in phases]==['fresh','restart'],'Two fresh native phases required')
    for phase in phases:
        require(phase.get('fixed_inputs_ack') is True and phase.get('loopback_ack') is True
                and phase.get('manual_launcher_wait_ack') is True and phase.get('schema_verified') is True
                and phase.get('dispatch_loop_advanced') is True and phase.get('native_process_exit_owned') is True
                and [p.get('map_id') for p in phase.get('map_status',[])]==[1,5]
                and all(p.get('not_started') is True and p.get('world')=={1:'City_01_01',5:'City_01_02'}[p['map_id']]
                        and re.fullmatch('[0-9a-f]{64}',str(p.get('native_response_sha256'))) is not None
                        for p in phase['map_status']),
                'Minimal native Db phase readiness/cleanup missing')
    require(phases[0].get('schema_snapshot')==phases[1].get('schema_snapshot')
            and phases[0].get('schema_snapshot',{}).get('table_count',0)>0
            and value.get('synthetic_fixture_digest')==digest([FIXTURE]),'Minimal native restart schema/identity differs')
    return value


def run(args):
    require(os.name=='nt','Genuine native gate requires Windows; no simulated success')
    commit=source_commit(args.repository_commit); pins=source_pins()
    require(os.environ.get('GITHUB_REPOSITORY')=='Russianranger/coh-android'
            and re.fullmatch('[1-9][0-9]*',os.environ.get('GITHUB_RUN_ID','')),
            'Current owned GitHub native qualification run required')
    run_id=int(os.environ['GITHUB_RUN_ID'])
    files,schema,dbdoc,inputs=donor_inputs(args.donor_apk)
    require(inputs==expected_inputs(),'Actual donor input closure differs from independently extracted identity')
    work,output=args.work.resolve(),args.output.resolve()
    require(not work.exists() and not output.exists() and work!=output
            and work not in output.parents and output not in work.parents
            and ROOT not in work.parents and work not in ROOT.parents,
            'Fresh separate owned work/public output required outside repository')
    sys.path[:0]=[str(ROOT/'database/postgresql/tests'),str(ROOT/'database/postgresql')]
    import pg_local
    import run_network_ack as network
    from character_console import ConsoleCapture
    network.make_private_directory(work); output.mkdir(parents=True)
    report=dict(format=1,status='failed',scope=SCOPE,repository_commit=commit,source_pins=pins,
        started_utc=utc(),run_id=run_id,
        run_url='https://github.com/Russianranger/coh-android/actions/runs/'+str(run_id),
        inputs=inputs,phases=[],failures=[],actual_retained_dbserver_host_fixture_executed=False,
        actual_native_map_query_executed=False,postgresql_disposable_cluster_only=True,owned_cleanup_verified=False,
        synthetic_identity_location_restart_preserved=False,full_schema_and_attributes_restart_preserved=False,
        fresh_minimal_runtime_each_start=True,full_runtime_executed=False,native_world_started=False,
        wine_executed=False,physical_execution_validated=False,player_profile_opened=False,
        native_character_gameplay_validated=False,sql_mutation_scope='new_disposable_fixture_only',
        launch_config='exact_current_guest_game_config; disposable database and least-privilege coh_game role')
    cluster=None; children=[]; observers=[]; secrets=[]; runtimes=[]; success=False
    class OwnedProcess(network.Process):
        def stop(self):
            # Terminate this retained Popen handle only; never enumerate/kill an
            # unrelated process by image name or infer ownership from a PID file.
            if self.child.poll() is None:
                self.forced_stop=True; self.child.terminate(); self.child.wait(timeout=15)
            self.close()
    def start(command,runtime,logs,label,env):
        process=OwnedProcess(command,runtime,logs,label,env=env);children.append(process);return process
    try:
        for port,kind in ((15437,socket.SOCK_STREAM),(6997,socket.SOCK_STREAM),(7000,socket.SOCK_DGRAM)):
            with socket.socket(socket.AF_INET,kind) as probe:
                probe.bind(('127.0.0.1',port))
        cluster=pg_local.initialize(work/'pg',args.bin,15437,'coh_minimal_db',args.driver)
        secrets=list(cluster.secrets.values()); original_snapshot=None
        for label in ('fresh','restart'):
            runtime=work/label; runtime.mkdir(); logs=work/(label+'-logs'); logs.mkdir();runtimes.append((runtime,logs))
            for name,data in files.items():
                path=runtime/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            require(len(list((runtime/'data').rglob('*')))>62
                    and set(p.relative_to(runtime).as_posix() for p in (runtime/'data').rglob('*') if p.is_file())==set(schema['files']),
                    'Runtime contains unexpected world/BIN/provider data before native startup')
            config=runtime/'data/server/db/servers.cfg'
            config.write_text(guest_config(config.read_text(),cluster.meta['database'],cluster.connection_string(args.driver)))
            progress=runtime/'dispatch.bin'
            env={key:value for key,value in os.environ.items() if not key.startswith(('COH_','PG'))}
            env.update(COH_WINE_DB_FIXED_INPUTS='1',COH_WINE_DB_LOOPBACK_ONLY='1',
                       COH_WINE_DB_MANUAL_ATLAS='1',COH_WINE_DB_PROGRESS=str(progress))
            child=start([str(runtime/'DbServer.exe'),'-start','0'],runtime,logs,label+'-db',env)
            capture=ConsoleCapture(child.child.pid,logs,label+'-db');observers.append(capture);capture.start()
            stages=dbdoc['wine_build_input']['dispatch_progress']['stages'];first=None
            def ready():
                nonlocal first
                first=read_dispatch(progress,child,stages)
                text=capture.text()+'\n'+child.text()
                return first and first['loop_count']>0 and all(ack in text for ack in (FIXED_ACK,LOOPBACK_ACK,MANUAL_ACK))
            network.wait_for(ready,[child],runtime,300,'owned minimal Db native dispatch and policy acknowledgement')
            snapshot=schema_snapshot(cluster,schema)
            if original_snapshot is None: original_snapshot=snapshot
            require(snapshot==original_snapshot,'Native minimal Db restart changed schema or attributes')
            statuses=[]
            for map_id in (1,5):
                query=start(map_query_command(runtime,map_id),runtime,logs,label+'-map-'+str(map_id),
                            {k:v for k,v in env.items() if not k.startswith('COH_')})
                require(query.wait(45)==0,'Native map status query failed')
                text=query.text();require(not any(network.is_failure_line(line) for line in text.splitlines()),'Native query emitted failure')
                statuses.append(validate_status(text,map_id));query.close()
            later=None
            def advanced():
                nonlocal later
                later=read_dispatch(progress,child,stages)
                return later and later['loop_count']>first['loop_count'] and later['sequence']>=first['sequence']
            network.wait_for(advanced,[child],runtime,15,'native Db loop advancement after real queries')
            if label=='fresh': report['synthetic_fixture_digest']=seed_fixture(cluster)
            else: require(fixture_snapshot(cluster)==report['synthetic_fixture_digest'],'Synthetic saved identity/location changed')
            native_console=capture.text()+'\n'+child.text()
            require('Waiting for launchers to link up...' not in native_console,'Manual Db entered unused launcher wait')
            child.stop();capture.stop()
            require(child.child.poll() is not None,'Owned Db process did not exit')
            phase=dict(name=label,fixed_inputs_ack=True,loopback_ack=True,manual_launcher_wait_ack=True,
                schema_verified=True,schema_snapshot=snapshot,dispatch_loop_advanced=True,
                dispatch_before=first,dispatch_after=later,map_status=statuses,native_process_exit_owned=True,
                started_native_pid=child.child.pid,elapsed_seconds=round(time.monotonic()-child.started,3),
                console=capture.report())
            report['phases'].append(phase)
            (output/(label+'-console.txt')).write_text(network.redact(native_console,secrets),encoding='utf-8')
            print('Minimal native Db '+label+' dispatch, schema, Atlas/Kings queries passed',flush=True)
        report.update(actual_retained_dbserver_host_fixture_executed=True,actual_native_map_query_executed=True,
            synthetic_identity_location_restart_preserved=True,full_schema_and_attributes_restart_preserved=True)
        success=True
    except Exception as error:
        report['failures'].append(type(error).__name__+': '+network.redact(str(error),secrets)[-4000:])
    finally:
        for child in reversed(children):
            try:child.stop()
            except Exception as error:report['failures'].append('owned child cleanup: '+type(error).__name__)
        for observer in reversed(observers):
            try:observer.stop()
            except Exception as error:report['failures'].append('owned console cleanup: '+type(error).__name__)
        if cluster is not None:
            try:cluster.stop()
            except Exception as error:report['failures'].append('owned PostgreSQL cleanup: '+type(error).__name__)
        for index,(runtime,logs) in enumerate(runtimes):
            try:
                destination=output/('logs-'+str(index));destination.mkdir()
                text,records=network.collect_logs(runtime,logs,destination,secrets)
                report.setdefault('redacted_logs',[]).append(records)
                failures=[line[:2000] for line in text.splitlines() if network.is_failure_line(line)]
                if failures:report['failures'].append({'native_failure_lines':failures[:30]})
            except Exception as error:report['failures'].append('diagnostic retention: '+type(error).__name__)
        report['owned_cleanup_verified']=not report['failures'] and all(p.child.poll() is not None for p in children)
        report['finished_utc']=utc()
        if success and not report['failures'] and source_pins()==pins:
            report['status']='passed';validate_proof(report,commit)
        (output/PROOF).write_bytes(encoded(report))
    require(report['status']=='passed','Genuine minimal Db gate failed; inspect '+str(output/PROOF))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit',required=True)
    parser.add_argument('--driver',required=True)
    for name in ('donor-apk','bin','work','output'):parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())


if __name__=='__main__':main()
