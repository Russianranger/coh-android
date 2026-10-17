#!/usr/bin/env python3
"""Offline controls only: no Wine, PostgreSQL or graphical run is qualified."""
import copy, importlib.util, json, os, struct, subprocess, sys, tempfile, time, types, unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module
driver=load('fixture_driver',HERE/'capture_graphical_fixture.py')
guest=load('fixture_backup',HERE/'graphical_fixture_backup_guest.py')
sys.modules['capture_graphical_fixture']=driver
admission=load('fixture_admission',HERE/'admit_graphical_fixture.py')

def request():
    return {'schema':'coh-graphical-fixture-backup-request-v1','session_id':'a'*32,'client_pid':321,
            'character_id':1,'account':'COHLOCAL','character_name':'THORHERO'}
def receipt():
    tables=[{'schema':'dbo','table':name,'rows':1} for name in ('costumeparts','ents','ents2','powers')]
    return {'schema':'coh-graphical-fixture-full-backup-v1','passed':True,'request':request(),
        'database':'coh_local_android','fixture_account':'COHLOCAL','fixture_character':'THORHERO',
        'full_database_custom_archive':True,'selected_projection_only':False,
        'counts_share_exported_dump_snapshot':True,'dump':{'bytes':8,'sha256':'b'*64},
        'all_inventoried_tables_have_archive_data_entries':True,
        'server_version_num':180006,'roles_or_role_passwords_dumped':False,'source_or_game_data_modified':False,
        'fixture_identity':{'accounts':1,'characters':1,'character_id':1,'auth_id':7,'character_auth_id':7,
            'map_id':1,'account':'COHLOCAL','character_account':'COHLOCAL','character_name':'THORHERO'},
        'pg_dump_version':'pg_dump (PostgreSQL) 18.6','pg_restore_version':'pg_restore (PostgreSQL) 18.6',
        'archive_entries':4,'archive_list_sha256':'c'*64,'table_counts':tables,'table_count':4,'rows':4}

class Controls(unittest.TestCase):
    def test_receipt_strict_shapes(self):
        baseline=receipt();driver.validate_backup(baseline,request(),baseline['dump'])
        for key in list(baseline):
            value=copy.deepcopy(baseline);value.pop(key)
            with self.subTest(omitted=key),self.assertRaises((driver.Refused,KeyError)):
                driver.validate_backup(value,request(),baseline['dump'])
        for key in ('passed','full_database_custom_archive','counts_share_exported_dump_snapshot'):
            value=copy.deepcopy(baseline);value[key]=1
            with self.subTest(flag=key),self.assertRaises(driver.Refused):driver.validate_backup(value,request(),baseline['dump'])
        for key in ('accounts','characters','character_id','auth_id','character_auth_id','map_id'):
            value=copy.deepcopy(baseline);value['fixture_identity'][key]=True
            with self.subTest(integer=key),self.assertRaises(driver.Refused):driver.validate_backup(value,request(),baseline['dump'])
        for key in ('client_pid','character_id'):
            value=copy.deepcopy(baseline);value['request'][key]=True
            with self.subTest(request=key),self.assertRaises(driver.Refused):driver.validate_backup(value,request(),baseline['dump'])
        for change in ('boolean_count','duplicate_table','missing_table','wrong_rows','wrong_version','projection','other_character'):
            value=copy.deepcopy(baseline)
            if change=='boolean_count':value['table_counts'][0]['rows']=True
            if change=='duplicate_table':value['table_counts'][1]=value['table_counts'][0]
            if change=='missing_table':value['table_counts'][1]['table']='invented'
            if change=='wrong_rows':value['rows']=5
            if change=='wrong_version':value['pg_dump_version']='pg_dump (PostgreSQL) 16.13'
            if change=='projection':value['selected_projection_only']=True
            if change=='other_character':value['fixture_identity']['character_name']='OTHER'
            with self.subTest(change=change),self.assertRaises(driver.Refused):driver.validate_backup(value,request(),baseline['dump'])

    def test_request_refusals(self):
        self.assertEqual(guest.request_identity(request()),request())
        for key in request():
            value=request();value.pop(key)
            with self.subTest(omitted=key),self.assertRaises(guest.Refused):guest.request_identity(value)
        for key,value in [('schema','other'),('client_pid',True),('character_id',0),('account','USER'),
                          ('character_name','OTHER'),('session_id','not-a-session')]:
            data=request();data[key]=value
            with self.subTest(key=key),self.assertRaises(guest.Refused):guest.request_identity(data)

    def test_same_guest_paths_and_environment_command(self):
        command=['/tmp/proot','-r','/tmp/root','-b','/tmp/state:/state','/usr/bin/env','-i','HOME=/state',
                 '/usr/bin/python3','/opt/coh/character_creation_diagnostic.py','--session-id','a'*32]
        result=driver.backup_command(command,b'print(1)')
        self.assertEqual(result[:8],command[:8]);self.assertEqual(result[8:],['/usr/bin/python3','-c','print(1)'])
        self.assertEqual(command[-2:],["--session-id",'a'*32])
        command[9]='/opt/coh/other.py'
        with self.assertRaises(driver.Refused):driver.backup_command(command,b'pass')

    def test_actual_inherited_finish_hook_order(self):
        character=driver.load_character(driver.ROOT,driver.ROOT/'tools/android/interactive/character_host_smoke.py')
        with tempfile.TemporaryDirectory() as raw:
            directory=Path(raw);finish=directory/'finish.json';calls=[]
            def backup(events):
                self.assertFalse(finish.exists());calls.append('backup');return {'offline_stub':True}
            instance=driver.interaction_type(character,backup)('a'*32,directory,finish)
            instance.action=len(instance.ACTIONS);instance.ready_at=100;instance.frame_generation=1
            instance.result['post_save_captures']=[{}, {}, {}]
            events=types.SimpleNamespace(session='a'*32,active=True,saved_generation=1,connected_generation=1,
                                         login_generation=1,client_pid=321,character_id=1)
            frame=types.SimpleNamespace(width=800,height=600,generation=1)
            instance.on_frame(None,frame,events,1,[1,2,3],103)
            self.assertEqual(calls,['backup']);self.assertTrue(finish.exists())
            instance.on_frame(None,frame,events,2,[1,2,3],106);self.assertEqual(calls,['backup'])

    def test_save_gate_or_backup_failure_never_finishes(self):
        character=driver.load_character(driver.ROOT,driver.ROOT/'tools/android/interactive/character_host_smoke.py')
        for changed in ('saved_generation','connected_generation','login_generation','session','active','backup_failure'):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as raw:
                directory=Path(raw);finish=directory/'finish.json'
                def backup(events):raise driver.Refused('MOCKED_BACKUP_FAILURE')
                instance=driver.interaction_type(character,backup)('a'*32,directory,finish)
                instance.action=len(instance.ACTIONS);instance.result['post_save_captures']=[{}, {}, {}]
                values=dict(session='a'*32,active=True,saved_generation=1,connected_generation=1,
                            login_generation=1,client_pid=321,character_id=1)
                if changed in values:values[changed]='b'*32 if changed=='session' else 0
                with self.assertRaises(driver.Refused):instance.on_frame(None,None,types.SimpleNamespace(**values),0,[],0)
                self.assertFalse(finish.exists())

    def test_private_source_and_fresh_destination(self):
        with tempfile.TemporaryDirectory() as raw:
            directory=Path(raw);path=directory/'source';path.write_bytes(b'abc');path.chmod(0o600)
            self.assertEqual(guest.file_pin(path)['bytes'],3)
            path.chmod(0o644)
            with self.assertRaises(guest.Refused):guest.file_pin(path)
            link=directory/'link';link.symlink_to(path)
            with self.assertRaises(driver.Refused):driver.pin(link)
            self.assertEqual(driver.fresh(directory/'new'),directory/'new')
            with self.assertRaises(driver.Refused):driver.fresh(directory)
            parent_link=directory/'parent';parent_link.symlink_to(directory,target_is_directory=True)
            with self.assertRaises(driver.Refused):driver.fresh(parent_link/'new')

    def test_committed_source_rejects_untracked_and_changed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory=Path(raw)
            subprocess.run(['git','init','-q',str(directory)],check=True)
            subprocess.run(['git','-C',str(directory),'config','user.name','Offline Test'],check=True)
            subprocess.run(['git','-C',str(directory),'config','user.email','offline@example.invalid'],check=True)
            (directory/'source.py').write_text('a=1\n')
            subprocess.run(['git','-C',str(directory),'add','source.py'],check=True)
            subprocess.run(['git','-C',str(directory),'commit','-qm','fixture'],check=True)
            revision=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
            self.assertIn('source.py',driver.committed_source(directory,revision,['source.py']))
            (directory/'source.py').write_text('a=2\n')
            with self.assertRaises(driver.Refused):driver.committed_source(directory,revision,['source.py'])
            (directory/'untracked.py').write_text('pass\n')
            with self.assertRaises(subprocess.CalledProcessError):driver.committed_source(directory,revision,['untracked.py'])

    def test_owned_real_child_group_cleanup(self):
        process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
        self.assertFalse(driver.group_absent(process));self.assertTrue(driver.stop_group(process))
        self.assertIsNotNone(process.returncode)

    def test_proot_actual_binary_receipt_and_source_binding(self):
        with tempfile.TemporaryDirectory() as raw:
            directory=Path(raw);donor=directory/'donor';proot=directory/'proot';proot.mkdir()
            recipe=donor/'tools/android/build_proot.py';recipe.parent.mkdir(parents=True);recipe.write_text('offline recipe\n')
            patches=donor/'android/native/proot';patches.mkdir(parents=True)
            names=('0001-sysvipc-memfd.patch','0002-android-string-header.patch','0003-portable-loader-offset.patch')
            for name in names:(patches/name).write_text(name+'\n')
            header=bytearray(64);header[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',header,18,183)
            for name in ('proot','proot-loader'):(proot/name).write_bytes(header)
            value={'schema_version':1,'target':'linux-arm64','status':'native_built_runtime_unverified',
                'source_commit':'7266fb3e8516535682f5a9c8f3a7e70f6506eddb',
                'source_tree':'8fcee3911b8e0848a1fc75c2e9827316ba658a5a',
                'optional_acceleration_patch':False,'sysvipc_memfd_patch':True,
                'recipe_sha256':driver.pin(recipe)['sha256'],
                'patches':{name:driver.pin(patches/name) for name in names},
                'files':{name:driver.pin(proot/name) for name in ('proot','proot-loader')}}
            path=proot/'proot-build-receipt.json'
            def check(data):
                path.write_text(json.dumps(data));return driver.proot_input(proot,driver.pin(path)['sha256'],donor)
            self.assertIn('proot',check(value))
            for key,bad in [('target','android-arm64'),('schema_version',True),('source_commit','0'*40),
                            ('recipe_sha256','f'*64),('sysvipc_memfd_patch',1)]:
                data=copy.deepcopy(value);data[key]=bad
                with self.subTest(key=key),self.assertRaises(driver.Refused):check(data)
            for name in ('proot','proot-loader'):
                (proot/name).write_bytes(header+b'changed')
                with self.subTest(binary=name),self.assertRaises(driver.Refused):check(value)
                (proot/name).write_bytes(header)
            data=copy.deepcopy(value);wrong=bytearray(header);struct.pack_into('<H',wrong,18,62)
            (proot/'proot').write_bytes(wrong);data['files']['proot']=driver.pin(proot/'proot')
            with self.assertRaises(driver.Refused):check(data)

    def test_exact_retention_refuses_secret_and_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            directory=Path(raw);source=directory/'source';source.write_bytes(b'fixture data')
            self.assertEqual(driver.retain_exact(source,directory/'copy',1024),driver.pin(source))
            source.write_bytes(b'x'*(1024**2-20)+b'role-secret-which-crosses-the-chunk-boundary')
            with self.assertRaises(driver.Refused):driver.retain_exact(source,directory/'refused',2*1024**2,(b'role-secret-which-crosses-the-chunk-boundary',))

    def test_ineligible_host_refuses_before_any_child(self):
        with patch.object(driver.platform,'machine',return_value='x86_64'),patch.object(driver.subprocess,'Popen') as process:
            with self.assertRaises(driver.Refused):driver.preflight(types.SimpleNamespace())
            process.assert_not_called()

    def test_real_readonly_transaction_pipe_cleanup(self):
        child="import sys,json\nfor line in sys.stdin:\n if line.startswith('ROLLBACK'): break\n print(json.dumps({'received':line.strip()}),flush=True)\n"
        snapshot=guest.Snapshot([sys.executable,'-u','-c',child],os.environ.copy(),time.monotonic()+10)
        self.assertEqual(snapshot.query('SELECT offline_control;'),{'received':'SELECT offline_control;'})
        snapshot.close();self.assertEqual(snapshot.process.returncode,0)

    def test_mocked_full_dump_is_same_exported_snapshot(self):
        with tempfile.TemporaryDirectory() as raw:
            state=Path(raw);directory=state/'graphical-fixture-backup';directory.mkdir(mode=0o700)
            driver.write_json(directory/'request.json',request())
            profile=state/'diagnostic/android-local-login';pgdata=profile/'pgdata';pgdata.mkdir(parents=True)
            (pgdata/'PG_VERSION').write_text('18\n');socket=profile/'socket';socket.mkdir()
            driver.write_json(profile/'credentials.json',{'cohdiag_admin':'d'*64,'cohtest':'e'*64})
            (pgdata/'postmaster.pid').write_text('123\n'+str(pgdata)+'\n0\n45678\n'+str(socket)+'\n127.0.0.1\n0\nready\n')
            (pgdata/'postmaster.pid').chmod(0o600)
            commands=[];closed=[]
            class MockSnapshot:
                def __init__(self,command,environment,deadline):
                    self.count=0;commands.append(command)
                    self.environment=environment
                def query(self,query):
                    self.count+=1
                    if self.count==1:return {'database':'coh_local_android','user':'cohdiag_admin','server_version_num':180006,
                        'data_directory':str(pgdata),'listen':'127.0.0.1','port':45678,'socket':str(socket),
                        'fsync':'on','synchronous_commit':'on','full_page_writes':'on','snapshot':'00000003-00000001-1'}
                    if self.count==2:return receipt()['fixture_identity']
                    if self.count==3:return [['dbo',name] for name in ('costumeparts','ents','ents2','powers')]
                    return 1
                def close(self):closed.append(True)
            def mocked_tool(command,environment,deadline,limit=0):
                commands.append(command)
                if command[-1]=='--version':return (Path(command[0]).name+' (PostgreSQL) 18.6\n').encode()
                if Path(command[0]).name=='pg_dump':
                    self.assertIn('--snapshot=00000003-00000001-1',command)
                    self.assertIn('d'*64,environment.values())
                    self.assertTrue(not closed)
                    Path(next(word[7:] for word in command if word.startswith('--file='))).write_bytes(b'PGDMPfake')
                    return b''
                self.assertFalse(closed)
                return b'; Dumped from database version: 18.6\n; Dumped by pg_dump version: 18.6\n'+b''.join(
                    ('1; 0 1 TABLE DATA dbo '+name+' cohtest\n').encode() for name in ('costumeparts','ents','ents2','powers'))
            local=types.SimpleNamespace(profile_record=lambda path:{'initialized':True},DATABASE='coh_local_android')
            with patch.dict(sys.modules,{'local_login_server':local}),patch.object(guest,'Snapshot',MockSnapshot),patch.object(guest,'tool',mocked_tool):
                value=guest.capture(state,Path('/mock/pg'))
            self.assertEqual(closed,[True]);self.assertTrue((directory/'fixture.pgdump').is_file())
            self.assertFalse((directory/'fixture.pgdump.partial').exists())
            driver.validate_backup(value,request(),guest.file_pin(directory/'fixture.pgdump'))
            self.assertNotIn('d'*64,json.dumps(value))
            self.assertFalse(any('INSERT' in str(command) or 'UPDATE' in str(command) for command in commands))
            # Regression: cleanup must still remove owned partials when both
            # the dump operation and snapshot connection closure fail.
            (directory/'fixture.pgdump').unlink();(directory/'backup.json').unlink()
            class FailedClose(MockSnapshot):
                def close(self):raise guest.Refused('MOCKED_CLOSE_FAILURE')
            def failed_dump(command,environment,deadline,limit=0):
                if Path(command[0]).name=='pg_dump' and command[-1]!='--version':
                    raise guest.Refused('MOCKED_DUMP_FAILURE')
                return mocked_tool(command,environment,deadline,limit)
            with patch.dict(sys.modules,{'local_login_server':local}),patch.object(guest,'Snapshot',FailedClose),patch.object(guest,'tool',failed_dump):
                with self.assertRaisesRegex(guest.Refused,'MOCKED_DUMP_FAILURE'):guest.capture(state,Path('/mock/pg'))
            self.assertFalse((directory/'fixture.pgdump.partial').exists());self.assertFalse((directory/'fixture.pgdump').exists())

    def test_fixture_admission_retained_byte_closure(self):
        with tempfile.TemporaryDirectory() as raw:
            directory=Path(raw);(directory/'fixture.pgdump').write_bytes(b'PGDMPoffline-control')
            (directory/'account.txt').write_text('COHLOCAL\n');backup=receipt();backup['dump']=driver.pin(directory/'fixture.pgdump')
            observer={'session_id':'a'*32,'failure':None,'terminal_event_observed':True,'client_pid':321,
                      'interaction_script':{'full_backup':backup}}
            report={'passed':True,'status':'passed','failures':[],'session_id':'a'*32,
                    'scope':'actual_character_creation_guest','cleanup_complete':True,
                    'local_login':{'profile_reused':False,'profile_initialized':True,'character_count':0,'account':'COHLOCAL'},
                    'character_creation':{'verified':True,'committed_sql_verified':True,'requested_logout_observed':True,
                        'logout_timer_observed':True,'disconnected_before_sql':True,'forced_stop_before_save':False,
                        'name':'THORHERO','account':'COHLOCAL','character_id':1,'auth_id':7}}
            objects={'original-guest-report.json':report,'external-observer.json':observer,
                     'backup-request.json':request(),'backup-receipt.json':backup}
            for name,value in objects.items():driver.write_json(directory/name,value)
            evidence={name:driver.pin(directory/name) for name in objects}
            value={'schema':'coh-fresh-graphical-fixture-capture-v1','input_scope':'new_disposable_original_graphical_COHLOCAL_THORHERO',
                   'failure':None,'repository':'Russianranger/coh-android','runner_environment':'github-hosted',
                   'workflow_run_id':1,'workflow_run_attempt':1,'apk':driver.APK,'build_report':driver.BUILD,
                   'game_archive':driver.ARCHIVE,'donor':{'revision':driver.DONOR},'ocr_overlay_sha256':driver.OCR_SHA,
                   'fixture_wire_slot':0,'session_id':'a'*32,'retained_creation_evidence':evidence,'full_backup':backup,
                   'original_guest_report':evidence['original-guest-report.json']}
            trues=('passed','fixture_only','inputs_unchanged','owned_process_group_absent','original_guest_cleanup_verified',
                   'committed_original_logout_verified','fresh_profile_source_creation_verified',
                   'public_fixture_dump_retention_permitted','fresh_role_secret_export_scan_passed')
            falses=('private_user_input_accepted','apk_rebuilt','client_or_server_recompiled','synthetic_character_rows',
                    'source_generation_admitted','world_authority','android_execution_validated')
            value.update({name:True for name in trues});value.update({name:False for name in falses})
            def admit(data):
                path=directory/'fixture-capture.json';path.write_text(json.dumps(data));return admission.inspect(directory,driver.pin(path)['sha256'])
            result=admit(value);self.assertTrue(result['passed']);self.assertFalse(result['world_authority'])
            for name in (*trues,*falses,'fixture_wire_slot','workflow_run_id'):
                altered=copy.deepcopy(value);altered[name]=int(altered[name]) if type(altered[name]) is bool else False
                with self.subTest(key=name),self.assertRaises(driver.Refused):admit(altered)
            for name in objects:
                path=directory/name;original=path.read_bytes();path.write_bytes(original+b' ')
                with self.subTest(file=name),self.assertRaises(driver.Refused):admit(value)
                path.write_bytes(original)
            (directory/'fixture.pgdump').write_bytes(b'PGDMPchanged')
            with self.assertRaises(driver.Refused):admit(value)

if __name__=='__main__':unittest.main(verbosity=2)
