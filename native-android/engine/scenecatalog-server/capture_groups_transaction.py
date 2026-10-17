#!/usr/bin/env python3
"""Private isolated original-source/native GROUPS pairing from an existing dump.

Requires an authorized exact existing character PostgreSQL backup and private
account/wire-slot input. Never seeds SQL identities or creates a character. All
outputs contain private character state and MUST NOT be publicly uploaded.
"""
from __future__ import annotations
import argparse,ast,hashlib,importlib,json,os,platform,re,shlex,shutil,socket,stat,struct,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
_fresh_bytecode=tempfile.TemporaryDirectory(prefix='coh-groups-capture-imports-')
sys.pycache_prefix=_fresh_bytecode.name;sys.dont_write_bytecode=True
import delivery as d
import capture_disposable as base
import capture_resources as retained
import admit_groups_capture as admit
import inspect_groups_capture as envelope
import stage_groups_capture as stage
from groups_capture_stages import advance
ROOT=d.ROOT;HERE=Path(__file__).resolve().parent
PRIVATE_DUMP_MAX=512*1024**2
def private_file(path,maximum):
 path=d.regular(path);info=path.stat();d.require(info.st_uid==os.geteuid() and not info.st_mode&0o077 and 0<info.st_size<=maximum,'PRIVATE_INPUT');return path
def account_input(path):
 raw=d.read(private_file(path,15),15);value=raw[:-1] if raw.endswith(b'\n') else raw
 d.require(1<=len(value)<=14 and all(33<=n<=126 for n in value),'PRIVATE_ACCOUNT');return value.decode('ascii')
def identity(path,maximum):
 size,digest=d.hash_file(path,maximum);return {'bytes':size,'sha256':digest}
def native_input(binary,receipt_path,receipt_pin,root=ROOT):
 binary=d.regular(binary);d.sha(receipt_pin);d.require(d.hash_file(receipt_path,16*1024**2)[1]==receipt_pin,'NATIVE_RECEIPT_PIN')
 receipt=d.json_object(d.read(receipt_path,16*1024**2));d.require(receipt.get('schema')=='coh-local-scene-capture-build-v1' and receipt.get('passed') is True and receipt.get('source_hashes_authoritative_for_build_bytes') is True,'NATIVE_SCOPE')
 mode=receipt.get('modes',{}).get('release',{});d.require(mode.get('built') is True and mode.get('binary')==binary.name and mode.get('sha256')==d.hash_file(binary,4*1024**2)[1],'NATIVE_BINARY')
 with binary.open('rb') as stream:header=stream.read(20)
 d.require(len(header)==20 and header[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',header,18)[0]==62,'NATIVE_ELF')
 driver=root/'native-android/combined-client/tools/check_local_scene_capture.py';tree=ast.parse(driver.read_bytes());assignments=[node.value for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='RELATIVE' for target in node.targets)]
 d.require(len(assignments)==1,'NATIVE_SOURCE_LIST');relative=ast.literal_eval(assignments[0]);d.require(type(relative) is list and all(type(value) is str for value in relative),'NATIVE_SOURCE_LIST')
 sources=[root/'native-android'/value for value in relative]+[driver.with_name('capture_local_scene.c')]
 dependencies={driver,*sources}
 for source in sources:
  result=subprocess.run(['cc','-std=c11','-MM','-I'+str(root/'native-android/include'),str(source)],capture_output=True,text=True,timeout=20)
  d.require(result.returncode==0 and len(result.stdout)<=1024**2,'NATIVE_DEPENDENCIES')
  words=shlex.split(result.stdout.replace('\\\n',' '));d.require(words and words[0].endswith(':'),'NATIVE_DEPENDENCIES')
  for name in words[1:]:
   path=Path(name).resolve();d.require(root in path.parents,'NATIVE_DEPENDENCY_ROOT');dependencies.add(path)
 hashes=receipt.get('source_sha256',{})
 for path in dependencies:
  name=path.relative_to(root).as_posix();d.require(hashes.get(name)==d.hash_file(path,8*1024**2)[1],'NATIVE_SOURCE_BYTES')
 return {'binary':identity(binary,4*1024**2),'build_receipt_sha256':receipt_pin,'source_revision':receipt.get('source_revision'),'project_dependencies':len(dependencies),'dependencies_sha256':{path.relative_to(root).as_posix():hashes[path.relative_to(root).as_posix()] for path in sorted(dependencies)}}
def preflight(args):
 # Missing/invalid private inputs fail before compiler, Wine, PG or server work.
 dump=private_file(args.database_dump,PRIVATE_DUMP_MAX);dump_identity=identity(dump,PRIVATE_DUMP_MAX);d.require(dump_identity['sha256']==d.sha(args.database_dump_sha256),'DATABASE_DUMP_PIN')
 with dump.open('rb') as source:d.require(source.read(5)==b'PGDMP','DATABASE_CUSTOM_FORMAT')
 account=account_input(args.account_file);d.require(type(args.wire_slot) is int and 0<=args.wire_slot<64,'WIRE_SLOT')
 d.require(sys.platform=='linux' and os.geteuid()!=0 and platform.machine()=='x86_64' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted' and os.environ.get('GITHUB_REPOSITORY')=='Russianranger/coh-android','ISOLATED_HOST_REQUIRED')
 d.require(600<=args.timeout_seconds<=3600,'TIMEOUT')
 compiled,_=admit.inspect(args.compile_directory,ROOT,args.compile_receipt_sha256)
 native=native_input(args.native_capture,args.native_build_receipt,args.native_build_receipt_sha256)
 fx,db,pg,pe=base.fixture_modules();fixture=fx.validate_control_fixture(d.json_object(d.read(args.control_fixture,8*1024**2)))
 runtime=d.path(args.runtime);d.require(str(runtime)==fixture['runtime_host_path'] and runtime.is_dir(),'CONTROL_PATH')
 files,schema,dbdoc,donor=db.donor_inputs(args.db_donor_apk);d.require(donor==db.expected_inputs(),'DB_DONOR')
 work,output=d.absent_directory(args.work),d.absent_directory(args.output)
 for a,b in ((work,output),(runtime,work),(runtime,output)):
  d.require(a!=b and a not in b.parents and b not in a.parents,'ISOLATION')
 for source in (dump,d.path(args.account_file),d.path(args.compile_directory),d.path(args.native_capture),d.path(args.native_build_receipt)):
  d.require(work not in source.parents and output not in source.parents,'PRIVATE_INPUT_OUTPUT_OVERLAP')
 d.require(shutil.disk_usage(work.parent).free>=16*1024**3,'DISK_HEADROOM')
 return account,identity(args.account_file,15),dump_identity,compiled,native,(fx,db,pg,pe),files,schema,dbdoc,donor,runtime,work,output
def character_membership(cluster,account):
 quoted=account.replace("'","''")
 query="SELECT coalesce(json_agg(x ORDER BY containerid),'[]'::json) FROM (SELECT containerid,staticmapid,mapid FROM dbo.ents WHERE lower(authname)=lower('"+quoted+"') ORDER BY containerid LIMIT 65) x;"
 rows=json.loads(cluster.sql(query,user='coh_game',database=cluster.meta['database']))
 d.require(type(rows) is list and 1<=len(rows)<=64,'EXISTING_CHARACTER_REQUIRED')
 for row in rows:d.require(type(row) is dict and set(row)=={'containerid','staticmapid','mapid'} and type(row['containerid']) is int and 0<row['containerid']<=0x7fffffff,'EXISTING_CHARACTER_IDENTITY')
 d.require(any(row['staticmapid']==1 for row in rows),'EXISTING_ATLAS_CHARACTER_REQUIRED');return rows
def compiled_inputs_unchanged(args,native,compiled):
 return identity(args.native_capture,4*1024**2)==native['binary'] and d.hash_file(args.native_build_receipt,16*1024**2)[1]==args.native_build_receipt_sha256 and d.hash_file(args.compile_directory/'compile-only-receipt.json',8*1024**2)[1]==args.compile_receipt_sha256 and identity(args.compile_directory/'MapServer.exe',16*1024**2)==compiled['artifacts']['MapServer.exe'] and all(d.hash_file(ROOT/name,8*1024**2)[1]==digest for name,digest in native['dependencies_sha256'].items())
def verify_orchestration(root,pins,expected_revision):
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();d.require(revision==expected_revision,'ORCHESTRATION_REVISION')
 # git diff alone ignores untracked replacement helpers. Every executed source
 # must also be present in the recorded commit with these exact source bytes.
 for name,digest in pins.items():
  result=subprocess.run(['git','show',revision+':'+name],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
  d.require(result.returncode==0 and len(result.stdout)<=8*1024**2 and d.digest(result.stdout)==digest,'ORCHESTRATION_COMMITTED_SOURCE')
 d.require(subprocess.run(['git','diff','--quiet','HEAD','--',*pins],cwd=root).returncode==0,'ORCHESTRATION_DIRTY');return revision
def start_owned(children,handles,logs,work,label,command,cwd,env):
 out,err=work/(label+'-stdout.log'),work/(label+'-stderr.log');stdout=out.open('xb');handles.append(stdout);logs.append(out);stderr=err.open('xb');handles.append(stderr);logs.append(err)
 child=subprocess.Popen(list(map(str,command)),cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True);children.append(child);return child,out,err
def pair(source,received,membership,wire_slot):
 native=d.json_object(d.read(received/'capture.json',64*1024));inspection=envelope.inspect(source)
 d.require(native.get('schema')=='coh-local-scene-capture-v1' and type(wire_slot) is int and 0<=wire_slot<64,'NATIVE_CAPTURE_SCHEMA')
 numeric={'selected_slot':(0,63),'selected_dbid':(1,0x7fffffff),'map_id':(1,0x7fffffff),'bytes':(1,16*1024**2),'payload_bits':(1,16*1024**2*8),'byte_aligned':(0,1),'transport_version':(0,5),'footer_file_count':(0,4096),'footer_defs_crc':(0,0xffffffff),'footer_refs_crc':(0,0xffffffff),'footer_active_roots':(0,65536),'groups_consumed_bits':(1,16*1024**2*8),'opened_sockets':(0,2),'closed_sockets':(0,2)}
 for key,(minimum,maximum) in numeric.items():d.require(type(native.get(key)) is int and minimum<=native[key]<=maximum,'NATIVE_CAPTURE_NUMERIC')
 d.sha(native.get('packet_sha256'))
 for key in ('passed','local_development_auth','actual_client_loan_verified','selected_dbid_owner_bound','cleanup_verified','packet_written_synchronously'):d.require(native.get(key) is True,'NATIVE_CAPTURE_SCOPE')
 for key in ('authserver_authenticated','source_generation_admitted','actor_identity_verified','world_authority','packet_copy_retained'):d.require(native.get(key) is False,'NATIVE_CAPTURE_SCOPE')
 d.require(native.get('selected_slot')==wire_slot and native.get('selected_dbid') in {row['containerid'] for row in membership},'EXISTING_SELECTED_IDENTITY')
 owner=inspection['source_owner'];packet=inspection['packet'];catalog=inspection['source_catalog'];snapshot=inspection['source_snapshot']
 with d.regular(source).open('rb') as stream:stream.seek(80);owner_wire=stream.read(192)
 d.require(len(owner_wire)==192 and struct.unpack_from('<I',owner_wire,48)[0]==native.get('transport_version'),'SOURCE_NATIVE_PROFILE')
 d.require(owner['selected_dbid']==native['selected_dbid'] and owner['map_id']==native['map_id']==1 and owner['static_map_id']==1,'SOURCE_NATIVE_OWNER')
 actual=identity(received/'groups.bin',16*1024**2);d.require(actual=={'bytes':native['bytes'],'sha256':native['packet_sha256']} and actual['sha256']==inspection['files']['packet.bin']['sha256'] and actual['bytes']==inspection['files']['packet.bin']['bytes'],'EXACT_LOGICAL_PACKET')
 d.require(native['payload_bits']==packet['bits'] and native['byte_aligned']==packet['byte_aligned'] and native['transport_version'] in (4,5) and packet['compress']==1,'PACKET_PROFILE')
 d.require(native['footer_file_count']==catalog['files'] and native['footer_defs_crc']==snapshot['definitions_crc'] and native['footer_refs_crc']==snapshot['references_crc'] and native['footer_active_roots']==snapshot['active_roots'] and native['groups_consumed_bits']==native['payload_bits'],'COMPLETE_GROUPS_ASSOCIATION')
 d.require(native['opened_sockets']==native['closed_sockets']==2,'NATIVE_CLEANUP')
 return {'schema':'coh-original-native-groups-pair-v1','passed':True,'exact_logical_packet_verified':True,'same_source_selected_dbid_verified':True,'actual_native_owned_receive_verified':True,'source_envelope':inspection['envelope'],'native_packet':actual,'source_catalog':catalog,'source_snapshot':snapshot,'source_run_provenance_verified':False,'cache_equivalence_verified':False,'source_generation_admitted':False,'actor_identity_verified':False,'world_authority':False}
def capture(args):
 account,account_identity,dump_identity,compiled,native,modules,files,schema,dbdoc,donor,source,work,output=preflight(args);fx,db,pg,pe=modules
 source_paths=set((*base.SOURCE_PATHS,*retained.SOURCE_PATHS,*('native-android/engine/scenecatalog-server/'+name for name in ('capture_groups_transaction.py','groups_capture_stages.py','admit_groups_capture.py','inspect_groups_capture.py','stage_groups_capture.py','source_groups_capture_sink.inc'))))
 pins={name:d.hash_file(ROOT/name,8*1024**2)[1] for name in sorted(source_paths)}
 revision=verify_orchestration(ROOT,pins,os.environ.get('GITHUB_SHA'))
 for port,kind in ((15437,socket.SOCK_STREAM),(6997,socket.SOCK_STREAM),(7000,socket.SOCK_DGRAM),(7001,socket.SOCK_DGRAM)):
  with socket.socket(socket.AF_INET,kind) as probe:probe.bind(('127.0.0.1',port))
 work.mkdir(mode=0o700);output.mkdir(mode=0o700);children=[];handles=[];logs=[];cluster=environment=None;deadline=time.monotonic()+args.timeout_seconds;source_inventory=None;source_capture=None;native_directory=work/'native-received';private_dump=work/'existing-database.dump'
 report={'schema':'coh-private-original-native-groups-run-v1','passed':False,'private_character_state':True,'public_upload_permitted':False,'existing_database_dump':dump_identity,'existing_character_rows_seeded':False,'new_character_created':False,'native_tool':native,'original_map_binary':compiled['artifacts']['MapServer.exe'],'compile_receipt_sha256':args.compile_receipt_sha256,'source_sha256':pins,'local_development_auth':True,'authserver_authenticated':False,'runtime_executed':False,'matching_groups_transaction_captured':False,'cleanup_verified':False,'source_generation_admitted':False,'world_authority':False,
         'capture_stage':'INPUT_COPY','failure_stage':'NONE',
         'timeout_policy':{'supervised_child_deadline_seconds':args.timeout_seconds,'strict_whole_run_deadline':False,'reused_pg_helper_timeout_seconds':180,'reused_pg_dump_restore_timeout_seconds':900,'health_polling_pauses_during_pg_helpers':True},'log_limits_polled_not_kernel_enforced':True,'hard_process_memory_cap_established':False}
 def health():d.require(time.monotonic()<deadline,'CAPTURE_TIMEOUT');base.bounded_logs(logs)
 def start(label,command,cwd,env):
  return start_owned(children,handles,logs,work,label,command,cwd,env)
 def run(label,command,cwd,env,seconds):
  child,out,err=start(label,command,cwd,env);end=min(deadline,time.monotonic()+seconds)
  while child.poll() is None:health();d.require(time.monotonic()<end,'CHILD_TIMEOUT');time.sleep(.2)
  d.require(child.returncode==0,'CHILD_FAILED');return out,err
 try:
  advance(report,'INPUT_COPY')
  d.copy_verified(args.database_dump,private_dump,dump_identity['sha256'],PRIVATE_DUMP_MAX);private_dump.chmod(0o600);d.require(identity(private_dump,PRIVATE_DUMP_MAX)==dump_identity,'PRIVATE_DUMP_COPY')
  advance(report,'WINE_VERSION')
  out,_=run('wine-version',[args.wine,'--version'],work,os.environ.copy(),15);report['wine_version']=base.wine_version(d.read(out,1024))
  environment={key:value for key,value in os.environ.items() if not key.startswith(('PG','COH_'))};environment.update(WINEARCH='win32',WINEPREFIX=str(work/'wine-prefix'),WINEDEBUG='-all',WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d',TZ='UTC',LANG='C.UTF-8')
  advance(report,'WINE_BOOT');run('wineboot',[args.wine,'wineboot','--init'],work,environment,180);catalog,_=base.capture_destination(work);source_capture=catalog.parent/'live.cohgtx';source_capture_windows=r'C:\coh-native-catalog\live.cohgtx'
  advance(report,'RUNTIME_STAGE')
  runtime=work/'map-runtime';source_inventory=base.inventory(source,runtime);report['runtime_inventory']=source_inventory
  db_runtime=work/'db-runtime';db_runtime.mkdir(mode=0o700)
  for name,raw in files.items():target=db_runtime/name;target.parent.mkdir(parents=True,mode=0o700,exist_ok=True);target.write_bytes(raw)
  advance(report,'PE_ADMISSION');previous=pe.file_record(db_runtime/'MapServer.exe');replacement=pe.file_record(args.compile_directory/'MapServer.exe');d.require(previous['imports']==replacement['imports'] and previous['delay_imports']==replacement['delay_imports'],'PE_DEPENDENCIES')
  retained.copy_candidate(args.compile_directory/'MapServer.exe',runtime/'MapServer.exe',compiled['artifacts']['MapServer.exe']);records={p.name:pe.file_record(p) for p in runtime.iterdir() if p.suffix.lower() in ('.dll','.exe')};d.require(not pe.dependency_report(records)['unresolved'],'PE_CLOSURE')
  with zipfile.ZipFile(args.db_donor_apk) as archive:
   manifest=d.json_object(archive.read('assets/runtime/runtime-manifest.json'));installer=archive.read('assets/runtime/psqlodbc_x86.msi');probe_bytes=archive.read('assets/runtime/runtime-probe.exe');d.require({'bytes':len(probe_bytes),'sha256':d.digest(probe_bytes)}==manifest['files']['runtime-probe.exe'] and d.digest(installer)==base.ODBC_SHA256,'ODBC_INPUTS')
  installer_path=work/'psqlodbc_x86.msi';installer_path.write_bytes(installer);probe=work/'runtime-probe.exe';probe.write_bytes(probe_bytes)
  advance(report,'ODBC_INSTALL');run('odbc',[args.wine,'msiexec','/i',base.windows_path(installer_path),'/qn','/norestart'],work,environment,180)
  advance(report,'ODBC_PROBE');out,err=run('odbc-driver',[args.wine,base.windows_path(probe),'--odbc-driver'],work,environment,60)
  validation={'require':d.require,'re':re};db.load_functions('android/guest/diagnostic.py',('validate_odbc_driver',),validation);driver=validation['validate_odbc_driver']((d.read(out,base.MAX_LOG)+d.read(err,base.MAX_LOG)).decode(errors='replace'))['driver_name']
  advance(report,'POSTGRES_INITIALIZE');cluster=pg.initialize(work/'pg',args.pg_bin,15437,'coh_groups_bootstrap',driver)
  # Restore into a NEW database; neither an accepted profile nor an existing DB
  # is opened for mutation. No synthetic character/account/container SQL exists.
  advance(report,'DATABASE_RESTORE');health();d.require(identity(private_dump,PRIVATE_DUMP_MAX)==dump_identity,'RESTORE_INPUT_CHANGED');cluster.restore(private_dump,'coh_groups_existing');d.require(identity(private_dump,PRIVATE_DUMP_MAX)==dump_identity,'RESTORE_INPUT_CHANGED');cluster.meta['database']='coh_groups_existing';membership=character_membership(cluster,account);report['existing_character_count']=len(membership)
  config=db_runtime/'data/server/db/servers.cfg';config.write_text(db.guest_config(config.read_text(),cluster.meta['database'],cluster.connection_string(driver)));progress=db_runtime/'dispatch.bin'
  db_env=dict(environment,COH_WINE_DB_FIXED_INPUTS='1',COH_WINE_DB_LOOPBACK_ONLY='1',COH_WINE_DB_MANUAL_ATLAS='1',COH_WINE_DB_PROGRESS=base.windows_path(progress))
  advance(report,'DBSERVER_START');process,db_out,db_err=start('db',[args.wine,base.windows_path(db_runtime/'DbServer.exe'),'-start','0'],db_runtime,db_env);report['runtime_executed']=True
  advance(report,'DBSERVER_READY')
  while True:
   health();d.require(process.poll() is None,'DB_EXITED');text=(d.read(db_out,base.MAX_LOG)+d.read(db_err,base.MAX_LOG)).decode(errors='replace')
   if all(ack in text for ack in (db.FIXED_ACK,db.LOOPBACK_ACK,db.MANUAL_ACK)) and base.dispatch_ready(progress,dbdoc['wine_build_input']['dispatch_progress']['stages']):break
   time.sleep(.2)
  report['db_schema']=db.schema_snapshot(cluster,schema)
  run_identity={'schema':'coh-private-original-native-groups-identity-v1','nonce':os.urandom(32).hex(),'runtime_inventory':source_inventory,'database_dump':dump_identity,'compile_receipt_sha256':args.compile_receipt_sha256,'native_build_receipt_sha256':args.native_build_receipt_sha256,'source_sha256':pins,'private_fresh_wine_prefix':True,'private_fresh_pg_cluster':True,'restored_existing_database_only':True,'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()};report['run_identity_sha256']=retained.emit_identity(output/'run-identity.json',run_identity)
  d.require(compiled_inputs_unchanged(args,native,compiled) and identity(runtime/'MapServer.exe',16*1024**2)==compiled['artifacts']['MapServer.exe'],'COMPILED_INPUTS_CHANGED');health()
  map_env=dict(environment,COH_GAME_LOOPBACK_ONLY='1',COH_NATIVE_GROUPS_TRANSACTION_OUTPUT=source_capture_windows)
  advance(report,'MAPSERVER_START');map_process,map_out,map_err=start('map',[args.wine,base.windows_path(runtime/'MapServer.exe'),'-nogui','-db','127.0.0.1','-nosharedmemory','-nostats','-udp','7001','-tcp','0','-map_id','1','-donotautogroup'],runtime,map_env)
  policy=importlib.import_module('game_evidence')
  advance(report,'MAPSERVER_READY')
  while True:
   health();d.require(process.poll() is None and map_process.poll() is None,'SERVER_EXITED');text=(d.read(map_out,base.MAX_LOG)+d.read(map_err,base.MAX_LOG)).decode(errors='replace')
   bindings=policy.game_listener_bindings(text,'atlas',pending=True)
   if bindings:report['map_loopback_bindings']=bindings;break
   time.sleep(.2)
  native_env={key:value for key,value in os.environ.items() if not key.startswith(('PG','COH_'))}
  d.require(compiled_inputs_unchanged(args,native,compiled) and identity(runtime/'MapServer.exe',16*1024**2)==compiled['artifacts']['MapServer.exe'],'COMPILED_INPUTS_CHANGED');health()
  advance(report,'NATIVE_CAPTURE');left=max(1,min(600000,int((deadline-time.monotonic())*1000)));native_process,native_out,native_err=start('native',[args.native_capture,'7000',str(args.wire_slot),args.account_file,native_directory,str(left),'5','1','0'],work,native_env)
  while native_process.poll() is None:health();d.require(process.poll() is None and map_process.poll() is None,'SERVER_EXITED');time.sleep(.05)
  d.require(native_process.returncode==0 and source_capture.is_file(),'ACTUAL_PAIR_NOT_CAPTURED')
  d.require(not source_capture.with_name(source_capture.name+'.partial').exists(),'PARTIAL_SOURCE_CAPTURE')
  advance(report,'PAIR_VERIFY');report['pair']=pair(source_capture,native_directory,membership,args.wire_slot);report['matching_groups_transaction_captured']=True
  advance(report,'RETAIN_PRIVATE_PAIR')
  source_pin=identity(source_capture,envelope.MAXIMUM);d.copy_verified(source_capture,output/'source.cohgtx',source_pin['sha256'],envelope.MAXIMUM)
  target=output/'native';target.mkdir(mode=0o700)
  for name in ('groups.bin','capture.json'):
   actual=identity(native_directory/name,16*1024**2);d.copy_verified(native_directory/name,target/name,actual['sha256'],16*1024**2)
  report['passed']=True
 except Exception as error:
  report['failure_stage']=report['capture_stage']
  report['failure_type']=type(error).__name__;report['failure_code']=str(error) if isinstance(error,d.Refused) else 'DEPENDENCY_OR_RUNTIME_FAILURE'
 finally:
  advance(report,'CLEANUP')
  cleanup=[]
  for child in reversed(children):
   try:cleanup.append(base.stop_owned(child))
   except Exception:cleanup.append(False)
  for handle in handles:
   try:handle.close()
   except OSError:cleanup.append(False)
  if environment:
   for option in ('-k','-w'):
    try:result=subprocess.run([args.wineserver,option],env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30);cleanup.append(result.returncode==0)
    except Exception:cleanup.append(False)
  try:cleanup.append(base.cleanup_postgresql(cluster,work/'pg',pg))
  except Exception:cleanup.append(False)
  end=time.monotonic()+5
  while any(not base.process_group_absent(child) for child in children) and time.monotonic()<end:time.sleep(.1)
  report['owned_process_groups_absent']=all(base.process_group_absent(child) for child in children);cleanup.append(report['owned_process_groups_absent'])
  try:
   report['private_input_bytes_unchanged']=identity(args.database_dump,PRIVATE_DUMP_MAX)==dump_identity and identity(args.account_file,15)==account_identity and account_input(args.account_file)==account
   report['restored_private_copy_unchanged']=identity(private_dump,PRIVATE_DUMP_MAX)==dump_identity
   report['source_runtime_unchanged']=source_inventory is None or base.inventory(source)==source_inventory
   report['compiled_inputs_unchanged']=compiled_inputs_unchanged(args,native,compiled)
   if (work/'map-runtime/MapServer.exe').exists():report['compiled_inputs_unchanged']=report['compiled_inputs_unchanged'] and identity(work/'map-runtime/MapServer.exe',16*1024**2)==compiled['artifacts']['MapServer.exe']
   cleanup.extend((report['private_input_bytes_unchanged'],report['restored_private_copy_unchanged'],report['source_runtime_unchanged'],report['compiled_inputs_unchanged'],pins=={name:d.hash_file(ROOT/name,8*1024**2)[1] for name in pins}))
  except Exception:cleanup.append(False)
  report['cleanup_verified']=bool(cleanup) and all(cleanup);report['passed']=report['passed'] and report['cleanup_verified'];report['raw_logs_exported']=False
  if report['passed']:advance(report,'COMPLETE')
  elif report['failure_stage']=='NONE':report['failure_stage']='CLEANUP'
  # Raw original logs can contain account/character state or SQL. They stay in
  # the private invocation; no public diagnostic log tail is produced here.
  d.emit_json(output/'capture-receipt.json',report)
 return report
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('runtime','control-fixture','db-donor-apk','compile-directory','database-dump','account-file','native-capture','native-build-receipt','pg-bin','work','output'):parser.add_argument('--'+name,type=Path,required=True)
 for name in ('compile-receipt-sha256','database-dump-sha256','native-build-receipt-sha256'):parser.add_argument('--'+name,required=True)
 parser.add_argument('--wire-slot',type=int,required=True);parser.add_argument('--timeout-seconds',type=int,default=1200);parser.add_argument('--wine',default='wine');parser.add_argument('--wineserver',default='wineserver');args=parser.parse_args();os.umask(0o077)
 try:result=capture(args);print(json.dumps({key:result[key] for key in ('passed','runtime_executed','matching_groups_transaction_captured','cleanup_verified','public_upload_permitted','source_generation_admitted','world_authority')}));return 0 if result['passed'] else 2
 except Exception as error:print(json.dumps({'passed':False,'failure_type':type(error).__name__,'failure_code':str(error) if isinstance(error,d.Refused) else 'PREFLIGHT_FAILED','source_generation_admitted':False,'world_authority':False}));return 2
if __name__=='__main__':raise SystemExit(main())
