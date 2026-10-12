"""Host guards for the real Windows minimal-Db gate; no simulated native pass."""
import ast
import copy
import io
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parent))
import qualify_minimal_db_runtime as m


class MinimalDbRuntimeContractTests(unittest.TestCase):
    def proof(self):
        snapshot={'table_count':1,'ordered_columns_sha256':'a'*64}
        phase=dict(fixed_inputs_ack=True,loopback_ack=True,manual_launcher_wait_ack=True,
            schema_verified=True,schema_snapshot=snapshot,dispatch_loop_advanced=True,native_process_exit_owned=True,
            map_status=[dict(map_id=i,world=w,not_started=True,native_response_sha256='b'*64)
                        for i,w in ((1,'City_01_01'),(5,'City_01_02'))])
        value=dict(format=1,status='passed',scope=m.SCOPE,repository_commit='d'*40,source_pins=m.source_pins(),
            inputs=m.expected_inputs(),failures=[],run_id=123,
            run_url='https://github.com/Russianranger/coh-android/actions/runs/123',
            phases=[dict(copy.deepcopy(phase),name=n) for n in ('fresh','restart')],
            synthetic_fixture_digest=m.digest([m.FIXTURE]))
        for name in ('actual_retained_dbserver_host_fixture_executed','actual_native_map_query_executed',
                     'postgresql_disposable_cluster_only','owned_cleanup_verified','synthetic_identity_location_restart_preserved',
                     'full_schema_and_attributes_restart_preserved','fresh_minimal_runtime_each_start'):value[name]=True
        for name in ('full_runtime_executed','native_world_started','wine_executed','physical_execution_validated',
                     'player_profile_opened','native_character_gameplay_validated'):value[name]=False
        return value

    def test_receipt_requires_two_native_restarts_exact_inputs_and_source(self):
        value=self.proof();self.assertIs(m.validate_proof(value,'d'*40),value)
        for key in ('actual_retained_dbserver_host_fixture_executed','owned_cleanup_verified',
                    'synthetic_identity_location_restart_preserved','fresh_minimal_runtime_each_start'):
            bad=copy.deepcopy(value);bad[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):m.validate_proof(bad,'d'*40)
        for key,replacement in (('schema_input_files',63),('extra_world_data_files',1),('manual_dbserver',m.MAP)):
            bad=copy.deepcopy(value);bad['inputs'][key]=replacement
            with self.subTest(key=key),self.assertRaises(ValueError):m.validate_proof(bad,'d'*40)
        bad=copy.deepcopy(value);bad['run_id']=True
        with self.assertRaises(ValueError):m.validate_proof(bad,'d'*40)
        bad=copy.deepcopy(value);bad['source_pins']={}
        with self.assertRaises(ValueError):m.validate_proof(bad,'d'*40)
        bad=copy.deepcopy(value);bad['phases'].pop()
        with self.assertRaises(ValueError):m.validate_proof(bad,'d'*40)

    def test_receipt_cannot_claim_wine_world_player_or_device_execution(self):
        value=self.proof()
        for key in ('full_runtime_executed','native_world_started','wine_executed','physical_execution_validated',
                    'player_profile_opened','native_character_gameplay_validated'):
            bad=copy.deepcopy(value);bad[key]=True
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'overclaims'):m.validate_proof(bad,'d'*40)
        bad=copy.deepcopy(value);bad['format']=True
        with self.assertRaises(ValueError):m.validate_proof(bad,'d'*40)

    def test_exact_guest_config_keeps_local_safety_and_no_external_auth(self):
        original='UseFakeAuth 1\nUseQueueServer 0\nUseLogServer 0\nSqlAllowDdl 1\nSqlLogin "old"\n'
        text=m.guest_config(original,'coh_minimal_db','Driver={PostgreSQL Unicode};Database=coh_minimal_db;Username=coh_game;Password=fixture;')
        for line in ('AdvertisedIp 127.0.0.1','DoNotLaunchBeaconClients 1','DoNotLaunchMapServerTSR 1',
                     'DisableContainerBackups 1','SqlDbProvider postgresql','SqlDbName coh_minimal_db'):
            self.assertIn(line,text)
        self.assertNotIn('"old"',text);self.assertNotIn('Database=coh_minimal_db;',text)
        with self.assertRaises(ValueError):m.guest_config(original+'AuthServer external\n','coh_minimal_db','Driver={x};')

    def dispatch(self,pid=7,seq=2,flags=0):
        return struct.pack('<8s9I',b'COHDBP1\0',1,128,pid,8,seq,1,2,flags,1)+bytes(84)

    def test_dispatch_requires_exact_live_child_and_stable_complete_native_record(self):
        self.assertEqual(m.parse_dispatch(self.dispatch(),7,{'1':'INITIALIZED'})['loop_count'],2)
        self.assertIsNone(m.parse_dispatch(self.dispatch(seq=3),7,{'1':'INITIALIZED'}))
        for raw in (self.dispatch(pid=9),self.dispatch(flags=1),self.dispatch()[:-1],self.dispatch()[:-1]+b'x'):
            with self.subTest(raw=raw[-2:]),self.assertRaises(ValueError):m.parse_dispatch(raw,7,{'1':'INITIALIZED'})
        with tempfile.TemporaryDirectory() as tmp:
            child=type('Child',(),{'poll':lambda self:None})()
            self.assertIsNone(m.read_dispatch(Path(tmp)/'not-yet-created',child,{'1':'INITIALIZED'}))

    def test_status_queries_are_readonly_exact_maps_and_do_not_start_world(self):
        for map_id,world in ((1,'City_01_01'),(5,'City_01_02')):
            command=m.map_query_command(Path('runtime'),map_id)
            self.assertEqual(command[-3:],['-getstatus','1',str(map_id)])
            self.assertIn('-dbquery',command);self.assertNotIn('-map_id',command)
            text=f'{map_id} maps/City_Zones/{world}/{world}.txt NotReady 1 (Not started) Info\n'
            self.assertTrue(m.validate_status(text,map_id)['not_started'])
            with self.assertRaises(ValueError):m.validate_status(text.replace(world,'WrongWorld'),map_id)
            with self.assertRaises(ValueError):m.validate_status(text+text,map_id)
        with self.assertRaises(ValueError):m.map_query_command(Path('runtime'),True)

    def test_archive_cannot_escape_or_add_linked_inputs(self):
        def archive(name,kind=tarfile.REGTYPE):
            out=io.BytesIO()
            with tarfile.open(fileobj=out,mode='w:gz') as tar:
                member=tarfile.TarInfo(name);member.type=kind;member.size=1 if kind==tarfile.REGTYPE else 0
                tar.addfile(member,io.BytesIO(b'x') if member.size else None)
            return out.getvalue()
        self.assertEqual(m.safe_members(archive('data/known')),{'data/known':b'x'})
        for name,kind in (('../outside',tarfile.REGTYPE),('/absolute',tarfile.REGTYPE),('data/link',tarfile.SYMTYPE)):
            with self.subTest(name=name),self.assertRaises(ValueError):m.safe_members(archive(name,kind))

    def test_sql_fixture_runs_only_in_explicit_new_cluster_and_never_uses_thorhero(self):
        calls=[]
        class Cluster:
            meta={'database':'coh_minimal_db'}
            def sql(self,text,**kwargs):
                calls.append((text,kwargs));return '[{"containerid":90001,"authid":77,"authname":"COHMINIMAL","name":"MINIMALFIXTURE","staticmapid":5,"mapid":null,"posx":12.5,"posy":-20.0,"posz":40.25,"logincount":3}]'
        self.assertEqual(m.seed_fixture(Cluster()),m.digest([m.FIXTURE]))
        self.assertTrue(calls[0][0].startswith('INSERT INTO dbo.ents'))
        self.assertEqual(calls[0][1],{'user':'coh_game','database':'coh_minimal_db'})
        self.assertNotIn('THORHERO',calls[0][0]);self.assertNotIn('UPDATE',calls[0][0])

    def test_world_constants_match_current_production_saved_map_table(self):
        tree=ast.parse((m.ROOT/'android/guest/character_zoning.py').read_text())
        maps=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='MAPS' for t in n.targets))
        for map_id in (1,5):
            world=maps[map_id]['world']
            self.assertEqual(m.validate_status(f'{map_id} maps/{world}.txt NotReady 1 (Not started) Info\n',map_id)['world'],world)


if __name__=='__main__':unittest.main()
