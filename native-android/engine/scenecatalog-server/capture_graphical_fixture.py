#!/usr/bin/env python3
"""Create one fresh original graphical fixture and retain its complete PG18 dump.

Uses a retained signed APK, exact donor checkout and a separately pinned host
OCR overlay. No client/server compilation, SQL seed, or supplied database.
This is an input-producing development witness; it grants no world authority.
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, re, secrets, shutil, signal, socket, struct
import stat, subprocess, sys, tempfile, time, types
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DONOR='204615c6c4a809d6b814c7174b81448cffea3f7a'
OCR_SHA='c9216504faf04bb4989f6affee11020a17d421cc8cda05490bb672500d6b7e6d'
APK={'bytes':590725465,'sha256':'ee9c09a3bda8a7f68af1e481e8c85e96c14ee0ea6ab414dbcda2ca730dd73688'}
BUILD={'bytes':38185,'sha256':'587088a83e4d70e8dab88f8362367bc532b94e86412bf372750ac060728a689f'}
ARCHIVE={'bytes':615541018,'sha256':'28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07'}
MAX_DUMP=512*1024**2
MIN_FREE=16*1024**3
BACKUP_SECONDS=300
class Refused(ValueError):pass
def require(value,code):
    if not value:raise Refused(code)
def regular(path, maximum=1024**3):
    path=Path(path);info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and 0<info.st_size<=maximum,'REGULAR_INPUT')
    return path.resolve()
def pin(path,maximum=1024**3):
    path=regular(path,maximum)
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'bytes':path.stat().st_size,'sha256':digest}
def fresh(path):
    path=Path(path);require(path.parent.is_dir() and not path.exists() and not path.is_symlink(),'FRESH_DIRECTORY')
    require(path.parent.resolve()==path.parent.absolute(),'LINKED_PARENT');return path.absolute()
def write_json(path,value):
    with path.open('x') as output:
        os.chmod(path,0o600);json.dump(value,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
def committed_source(root,revision,names):
    require(re.fullmatch('[0-9a-f]{40}',revision or '') is not None,'SOURCE_REVISION')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==revision,'SOURCE_HEAD')
    result={}
    for name in names:
        expected=subprocess.check_output(['git','show',revision+':'+name],cwd=root,stderr=subprocess.DEVNULL)
        path=regular(root/name,8*1024**2)
        require(path.read_bytes()==expected,'COMMITTED_SOURCE_BYTES');result[name]=pin(path,8*1024**2)
    return result
def donor_file_pin(root,name):
    # The exact donor's original leaf inventory is44,476,275 bytes. Source
    # bodies keep their8MiB limit; this known metadata file needs its own cap.
    return pin(root/name,64*1024**2 if name=='docs/data-manifest.json' else 8*1024**2)
def donor_source(root):
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==DONOR,'DONOR_HEAD')
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().rstrip('\0').split('\0')
    selected=[name for name in tracked if name.startswith(('tools/android/','android/')) or name in
              ('docs/source-manifest.json','docs/data-manifest.json') or name.startswith('assets/')]
    require(selected and subprocess.run(['git','diff','--quiet',DONOR,'--',*selected],cwd=root).returncode==0,'DONOR_MODIFIED')
    # Reject untracked Python shadow modules before importing the donor harness.
    expected=set(selected)
    for prefix in ('tools/android','android'):
        require(all(path.relative_to(root).as_posix() in expected for path in (root/prefix).rglob('*.py')),
                'DONOR_UNTRACKED_PYTHON')
    hashes={name:donor_file_pin(root,name) for name in selected if name.endswith(('.py','.json','.java','.c','.h','.xml'))}
    canonical=json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()
    return {'revision':DONOR,'tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip(),
            'source_files':len(hashes),'source_inventory_sha256':hashlib.sha256(canonical).hexdigest()}
def proot_input(proot,receipt_pin,donor):
    for name in ('proot','proot-loader'):regular(proot/name,16*1024**2)
    launcher=regular(proot/'proot-build-receipt.json',1024**2);receipt=json.loads(launcher.read_bytes())
    require(re.fullmatch('[0-9a-f]{64}',receipt_pin or '') is not None
            and pin(launcher)['sha256']==receipt_pin,'PROOT_RECEIPT_PIN')
    require(type(receipt) is dict and receipt.get('schema_version')==1 and type(receipt['schema_version']) is int
            and receipt.get('target')=='linux-arm64' and receipt.get('status')=='native_built_runtime_unverified'
            and receipt.get('source_commit')=='7266fb3e8516535682f5a9c8f3a7e70f6506eddb'
            and receipt.get('source_tree')=='8fcee3911b8e0848a1fc75c2e9827316ba658a5a'
            and receipt.get('optional_acceleration_patch') is False and receipt.get('sysvipc_memfd_patch') is True,
            'PROOT_RECEIPT')
    require(receipt.get('recipe_sha256')==pin(donor/'tools/android/build_proot.py',128*1024)['sha256'],
            'PROOT_RECIPE')
    for name in ('0001-sysvipc-memfd.patch','0002-android-string-header.patch','0003-portable-loader-offset.patch'):
        require(receipt.get('patches',{}).get(name)==pin(donor/'android/native/proot'/name,128*1024),'PROOT_PATCH')
    for name in ('proot','proot-loader'):
        expected=receipt.get('files',{}).get(name,{})
        require(all(expected.get(key)==value for key,value in pin(proot/name,16*1024**2).items()),'PROOT_BINARY_PIN')
        with (proot/name).open('rb') as stream:header=stream.read(20)
        require(len(header)==20 and header[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',header,18)[0]==183,'PROOT_ARM64_ELF')
    return {name:pin(proot/name,16*1024**2) for name in ('proot','proot-loader','proot-build-receipt.json')}
def preflight(args):
    # All pins/freshness/host restrictions precede any package extraction or game process.
    require(sys.platform=='linux' and platform.machine().lower() in ('aarch64','arm64') and os.geteuid()!=0
            and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
            and os.environ.get('GITHUB_REPOSITORY')=='Russianranger/coh-android','OWNED_ARM64_HOST')
    require(all(re.fullmatch('[1-9][0-9]*',os.environ.get(name,'')) for name in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')),
            'HOST_RUN_IDENTITY')
    require(shutil.which('tesseract') and shutil.which('java'),'HOST_DEPENDENCIES')
    for path,expected in ((args.apk,APK),(args.build_report,BUILD),(args.archive,ARCHIVE)):
        require(pin(path)==expected,'RETAINED_INPUT_PIN')
    overlay=regular(args.ocr_overlay,128*1024);require(pin(overlay)['sha256']==OCR_SHA,'OCR_OVERLAY_PIN')
    donor=args.donor.resolve();source=donor_source(donor)
    orchestration=committed_source(ROOT,os.environ.get('GITHUB_SHA'),[
        str(HERE.relative_to(ROOT)/'capture_graphical_fixture.py'),
        str(HERE.relative_to(ROOT)/'graphical_fixture_backup_guest.py')])
    proot=args.proot.resolve()
    # The original builder owns the precise toolchain/commit closure. Its
    # receipt is pinned independently by this invocation, then rechecked later.
    proot_pins=proot_input(proot,args.proot_receipt_sha256,donor)
    work,evidence,output=map(fresh,(args.work,args.evidence,args.output))
    paths=(work,evidence,output)
    require(all(a!=b and a not in b.parents and b not in a.parents for i,a in enumerate(paths) for b in paths[i+1:]),'PATH_OVERLAP')
    for target in paths:
        require(all(target!=source and target not in source.parents and source not in target.parents
                    for source in (donor,proot,overlay,args.apk.resolve(),args.archive.resolve(),args.build_report.resolve())),'INPUT_OUTPUT_OVERLAP')
    require(shutil.disk_usage(work.parent).free>=MIN_FREE,'DISK_HEADROOM_16GIB')
    return donor,overlay,work,evidence,output,source,orchestration,proot_pins
def load_character(donor,overlay):
    # Compile the reviewed host-only OCR overlay with the exact donor filename.
    # Its existing explicit sibling imports therefore resolve to donor sources;
    # no file in either checkout or extracted APK is patched.
    require(pin(overlay,128*1024)['sha256']==OCR_SHA,'OCR_OVERLAY_EXECUTION_PIN')
    filename=donor/'tools/android/interactive/character_host_smoke.py'
    module=types.ModuleType('coh_fresh_graphical_character');module.__file__=str(filename)
    exec(compile(overlay.read_bytes(),str(filename),'exec'),module.__dict__)
    require(module.host.ROOT==donor,'DONOR_IMPORT_ROOT');return module
def backup_command(command,helper):
    index=command.index('/usr/bin/python3')
    require(command.count('/usr/bin/python3')==1 and command[index+1]=='/opt/coh/character_creation_diagnostic.py',
            'CHARACTER_COMMAND_SCOPE')
    # A separate PRoot client reuses filesystem binds/user/environment. It has
    # its own tracing/SysV session; psql/pg_dump need only the owned Unix socket.
    return command[:index]+['/usr/bin/python3','-c',helper.decode('utf-8')]
def group_absent(process):
    if process is None:return True
    try:os.killpg(process.pid,0);return False
    except ProcessLookupError:return True
def stop_group(process):
    if process is None:return True
    if not group_absent(process):
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait(timeout=5)
    # The launcher can already have exited while an owned descendant remains.
    if not group_absent(process):
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    end=time.monotonic()+5
    while not group_absent(process) and time.monotonic()<end:time.sleep(.05)
    return group_absent(process)
def run_backup(command,environment,guest,work,session,events,deadline,helper_pin):
    require(guest.poll() is None and not (work/'state/interaction-finish.json').exists(),'GUEST_NOT_LIVE_BEFORE_BACKUP')
    request={'schema':'coh-graphical-fixture-backup-request-v1','session_id':session,'client_pid':events.client_pid,
             'character_id':events.character_id,'account':'COHLOCAL','character_name':'THORHERO'}
    directory=work/'state/graphical-fixture-backup';directory.mkdir(mode=0o700)
    write_json(directory/'request.json',request)
    path=HERE/'graphical_fixture_backup_guest.py';helper=path.read_bytes()
    require({'bytes':len(helper),'sha256':hashlib.sha256(helper).hexdigest()}==helper_pin,'BACKUP_HELPER_EXECUTION_PIN')
    process=None;code=None;clean=False
    try:
        process=subprocess.Popen(backup_command(command,helper),env=environment,stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        end=min(deadline,time.monotonic()+BACKUP_SECONDS)
        while process.poll() is None:
            require(guest.poll() is None,'GUEST_EXITED_DURING_BACKUP')
            require(time.monotonic()<end,'BACKUP_TIMEOUT')
            require(not (work/'state/interaction-finish.json').exists(),'PREMATURE_FINISH_REQUEST')
            require(not (directory/'fixture.pgdump.partial').exists() or
                    (directory/'fixture.pgdump.partial').stat().st_size<=MAX_DUMP,'BACKUP_SIZE')
            time.sleep(.1)
        code=process.returncode
    finally:clean=stop_group(process)
    require(clean and code==0 and guest.poll() is None,'BACKUP_HELPER_OR_CLEANUP_FAILED')
    receipt=json.loads(regular(directory/'backup.json',4*1024**2).read_bytes())
    validate_backup(receipt,request,pin(directory/'fixture.pgdump',MAX_DUMP))
    return receipt
def validate_backup(value,request,dump):
    shape=lambda row: type(row) is dict and set(row)=={'schema','session_id','client_pid','character_id','account','character_name'} and row.get('schema')=='coh-graphical-fixture-backup-request-v1' and type(row.get('session_id')) is str and re.fullmatch('[0-9a-f]{32}',row['session_id']) is not None and all(type(row.get(key)) is int and 0<row[key]<=2147483647 for key in ('client_pid','character_id')) and row.get('account')=='COHLOCAL' and row.get('character_name')=='THORHERO'
    require(type(value) is dict and value.get('schema')=='coh-graphical-fixture-full-backup-v1'
            and value.get('passed') is True and shape(request) and shape(value.get('request')) and value['request']==request
            and value.get('full_database_custom_archive') is True and value.get('selected_projection_only') is False
            and value.get('counts_share_exported_dump_snapshot') is True and value.get('dump')==dump
            and value.get('all_inventoried_tables_have_archive_data_entries') is True
            and type(value.get('server_version_num')) is int and value['server_version_num']==180006
            and value.get('roles_or_role_passwords_dumped') is False
            and value.get('source_or_game_data_modified') is False,'BACKUP_RECEIPT')
    who=value.get('fixture_identity')
    require(type(who) is dict and all(type(who.get(key)) is int and who[key]>0 for key in
                ('accounts','auth_id','characters','character_id','character_auth_id','map_id'))
            and who['accounts']==who['characters']==who['map_id']==1 and who['character_id']==request['character_id']
            and who['account']==who['character_account']=='COHLOCAL' and who['character_name']=='THORHERO'
            and who['auth_id']==who['character_auth_id'],'FIXTURE_IDENTITY')
    require(value.get('database')=='coh_local_android' and value.get('fixture_account')=='COHLOCAL'
            and value.get('fixture_character')=='THORHERO' and value.get('pg_dump_version')=='pg_dump (PostgreSQL) 18.6'
            and value.get('pg_restore_version')=='pg_restore (PostgreSQL) 18.6'
            and type(value.get('archive_entries')) is int and 0<value['archive_entries']<=100000
            and type(value.get('archive_list_sha256')) is str and re.fullmatch('[0-9a-f]{64}',value['archive_list_sha256']),
            'ARCHIVE_SCOPE')
    counts=value.get('table_counts');require(type(counts) is list and 4<=len(counts)<=4096,'TABLE_COUNTS')
    require(all(type(row) is dict and set(row)=={'schema','table','rows'} and type(row['schema']) is str
            and type(row['table']) is str and type(row['rows']) is int and 0<=row['rows']<=10000000 for row in counts),'TABLE_COUNTS')
    names=[(row['schema'],row['table']) for row in counts]
    require(names==sorted(set(names)) and type(value.get('table_count')) is int and value['table_count']==len(counts)
            and type(value.get('rows')) is int and value['rows']==sum(row['rows'] for row in counts)
            and all(('dbo',name) in names for name in ('ents','ents2','powers','costumeparts')),'TABLE_COUNTS')
def interaction_type(character,backup):
    class BackedCharacter(character.CharacterInteraction):
        def on_frame(self,connection,frame,events,sequence,captures,now):
            if self.action==len(self.ACTIONS) and 'full_backup' not in self.result:
                require(events.session==self.session and events.active and events.saved_generation==1
                        and events.connected_generation==1 and events.login_generation==1
                        and type(events.client_pid) is int and events.client_pid>0
                        and type(events.character_id) is int and events.character_id>0
                        and 'finish_request' not in self.result and not self.finish_path.exists()
                        and len(self.result.get('post_save_captures',[]))==3,'COMMITTED_SAVE_GATE')
                self.result['full_backup']=backup(events)
            super().on_frame(connection,frame,events,sequence,captures,now)
    return BackedCharacter
def retain_exact(source,target,maximum,forbidden=()):
    expected=pin(source,maximum);tail=b''
    with source.open('rb') as source_stream,target.open('xb') as dest:
        os.chmod(target,0o600)
        while chunk:=source_stream.read(1024**2):
            data=tail+chunk;require(all(secret not in data for secret in forbidden),'ROLE_SECRET_EXPORT')
            dest.write(chunk);tail=data[-128:]
        dest.flush();os.fsync(dest.fileno())
    require(pin(target,maximum)==expected and pin(source,maximum)==expected,'RETAINED_INPUT_CHANGED')
    return expected
def capture(args):
    donor,overlay,work,evidence,output,source,orchestration,proot_pins=preflight(args)
    for path in (work,evidence,output):path.mkdir(mode=0o700)
    character=load_character(donor,overlay);host=character.host;session=secrets.token_hex(16)
    result={'schema':'coh-fresh-graphical-fixture-capture-v1','passed':False,'fixture_only':True,
            'input_scope':'new_disposable_original_graphical_COHLOCAL_THORHERO','private_user_input_accepted':False,
            'apk':APK,'build_report':BUILD,'game_archive':ARCHIVE,'donor':source,'ocr_overlay_sha256':OCR_SHA,
            'orchestration_revision':os.environ['GITHUB_SHA'],'orchestration_source':orchestration,
            'repository':os.environ['GITHUB_REPOSITORY'],'workflow_run_id':int(os.environ['GITHUB_RUN_ID']),
            'workflow_run_attempt':int(os.environ['GITHUB_RUN_ATTEMPT']),'runner_environment':'github-hosted',
            'proot_files':proot_pins,'session_id':session,'apk_rebuilt':False,'client_or_server_recompiled':False,
            'synthetic_character_rows':False,'source_generation_admitted':False,'world_authority':False,
            'android_execution_validated':False,'public_fixture_dump_retention_permitted':False}
    process=observer=backup=None;failure=None;guest_report=None;start=time.monotonic()
    try:
        manifest,assets,imports=host.extract_apk_assets(args.apk,work/'apk-assets',args.build_report,DONOR)
        data=host.import_game_data(imports,args.archive.resolve(),work,evidence)
        command,environment=character.make_command(work,assets,args.proot.resolve(),session,data,900)
        require(not (work/'state/diagnostic/android-local-login').exists(),'PROFILE_NOT_FRESH')
        deadline=time.monotonic()+character.OVERALL_SECONDS+60
        def saved_backup(events):
            nonlocal backup
            require(backup is None,'REPEATED_BACKUP')
            require(all(pin(args.proot/name,16*1024**2)==value for name,value in proot_pins.items()),'PROOT_EXECUTION_PIN')
            backup=run_backup(command,environment,process,work,session,events,deadline,
                orchestration[str(HERE.relative_to(ROOT)/'graphical_fixture_backup_guest.py')]);return backup
        with (evidence/'host-client.log').open('x') as log:
            require(all(pin(args.proot/name,16*1024**2)==value for name,value in proot_pins.items()),'PROOT_EXECUTION_PIN')
            process=subprocess.Popen(command,env=environment,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            socket_path=work/'socket/view.sock'
            while not socket_path.exists():
                require(process.poll() is None and time.monotonic()<deadline,'GUEST_BEFORE_DISPLAY');time.sleep(.1)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                connection.settimeout(90);connection.connect(str(socket_path))
                observer=character.observe_rfb(connection,session,process,deadline,evidence,evidence/'host-client.log',
                    work/'state/interaction-finish.json',interaction_factory=interaction_type(character,saved_backup))
            require(observer.get('failure') is None,'CHARACTER_OBSERVER_FAILED')
            require(process.wait(timeout=max(1,deadline-time.monotonic()))==0,'GUEST_EXIT_FAILED')
            guest_report=json.loads(regular(work/'state/latest-report.json',2*1024**2).read_bytes())
            character.validate_report(guest_report,session,manifest);character.validate_observer(observer,guest_report)
            require(not socket_path.exists() and backup is not None,'BACKUP_OR_SOCKET_CLOSURE')
            local=guest_report['local_login'];saved=guest_report['character_creation']
            require(local.get('profile_reused') is False and local.get('profile_initialized') is True
                    and local.get('character_count')==0 and type(local.get('character_count')) is int
                    and saved['character_id']==backup['request']['character_id']
                    and saved['auth_id']==backup['fixture_identity']['auth_id'],'FRESH_SOURCE_CREATION')
            result['passed']=True
    except Exception as error:
        failure={'type':type(error).__name__,'code':str(error) if isinstance(error,Refused) else 'GRAPHICAL_DEPENDENCY_OR_VALIDATION_FAILED'}
    finally:
        cleanup=character.stop_guest(process,work/'state');groups=stop_group(process)
        result.update(failure=failure,host_cleanup=cleanup,owned_process_group_absent=groups,
                      elapsed_seconds=round(time.monotonic()-start,3))
        try:
            unchanged=donor_source(donor)==source and pin(overlay)['sha256']==OCR_SHA
            unchanged=unchanged and orchestration==committed_source(ROOT,os.environ['GITHUB_SHA'],list(orchestration))
            unchanged=unchanged and all(pin(args.proot/name,16*1024**2)==value for name,value in proot_pins.items())
            unchanged=unchanged and all(pin(path)==expected for path,expected in ((args.apk,APK),(args.build_report,BUILD),(args.archive,ARCHIVE)))
            result['inputs_unchanged']=unchanged
            require(unchanged and groups and cleanup.get('process_reaped') is True and not cleanup.get('errors')
                    and cleanup.get('forced_quit') is False and cleanup.get('forced_kill') is False,'OWNED_CLEANUP_OR_INPUTS')
            require(result['passed'] and guest_report is not None,'GRAPHICAL_FIXTURE_FAILED')
            original=work/'state/graphical-fixture-backup/fixture.pgdump'
            require(pin(original,MAX_DUMP)==backup['dump'],'DUMP_CHANGED_AFTER_CLEANUP')
            credentials=json.loads(regular(work/'state/diagnostic/android-local-login/credentials.json',4096).read_bytes())
            require(set(credentials)=={'cohdiag_admin','cohtest'} and all(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) for value in credentials.values()),'ROLE_SECRET_SHAPE')
            forbidden=tuple(value.encode() for value in credentials.values())
            require(retain_exact(original,output/'fixture.pgdump',MAX_DUMP,forbidden)==backup['dump'],'RETAINED_DUMP_BYTES')
            source_evidence={}
            for path,name,maximum in ((work/'state/latest-report.json','original-guest-report.json',2*1024**2),
                    (work/'state/graphical-fixture-backup/request.json','backup-request.json',16384),
                    (work/'state/graphical-fixture-backup/backup.json','backup-receipt.json',4*1024**2)):
                source_evidence[name]=retain_exact(path,output/name,maximum,forbidden)
            observer_bytes=(json.dumps(observer,indent=2)+'\n').encode()
            require(all(secret not in observer_bytes for secret in forbidden),'ROLE_SECRET_EXPORT')
            write_json(output/'external-observer.json',observer)
            source_evidence['external-observer.json']=pin(output/'external-observer.json',16*1024**2)
            with (output/'account.txt').open('x') as account:os.chmod(output/'account.txt',0o600);account.write('COHLOCAL\n')
            result.update(full_backup=backup,fixture_wire_slot=0,original_guest_cleanup_verified=True,
                committed_original_logout_verified=True,fresh_profile_source_creation_verified=True,
                public_fixture_dump_retention_permitted=True,fresh_role_secret_export_scan_passed=True,
                retained_creation_evidence=source_evidence,
                original_guest_report=pin(work/'state/latest-report.json',2*1024**2),
                source_created_identity={'account':'COHLOCAL','character':'THORHERO',
                    'character_id':guest_report['character_creation']['character_id'],
                    'auth_id':guest_report['character_creation']['auth_id'],
                    'map_id':guest_report['character_creation']['map_id'],
                    'client_pid':guest_report['client_launch']['pid']})
        except Exception as error:
            result['passed']=False
            if failure is None:result['failure']={'type':type(error).__name__,'code':str(error) if isinstance(error,Refused) else 'FINAL_FIXTURE_VALIDATION_FAILED'}
            result['public_fixture_dump_retention_permitted']=False
            for name in ('fixture.pgdump','account.txt','original-guest-report.json','backup-request.json','backup-receipt.json','external-observer.json'):
                try:(output/name).unlink(missing_ok=True)
                except OSError:result['failed_output_cleanup_complete']=False
        # Commit-last: a backup without this successful receipt is inadmissible.
        write_json(output/'fixture-capture.json',result)
        character.export_guest_evidence(work/'state',evidence,session)
    return result
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('donor','ocr-overlay','apk','build-report','archive','proot','work','evidence','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--proot-receipt-sha256',required=True);args=parser.parse_args();os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix='coh-graphical-imports-') as cache:
        sys.pycache_prefix=cache;sys.dont_write_bytecode=True
        try:
            result=capture(args);print(json.dumps({key:result[key] for key in ('passed','fixture_only','public_fixture_dump_retention_permitted','source_generation_admitted','world_authority')}));return 0 if result['passed'] else 2
        except Exception as error:
            print(json.dumps({'passed':False,'failure_code':str(error) if isinstance(error,Refused) else 'PREFLIGHT_FAILED','world_authority':False}));return 2
if __name__=='__main__':raise SystemExit(main())
