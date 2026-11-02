"""Host-only controls; fixtures do not execute a game process or database."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock
from zipfile import ZipFile
import baseline_reopen as b
import modern_runtime_donor as donor
import modern_validation as v

class AssetViewTests(unittest.TestCase):
    def fixture(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-baseline-view-')))
        source=self.root/'current';source.mkdir()
        for name,raw in {'game-package.tar.gz':b'new-game',b.BINDING:b'bound',
                         'fixed.dat':b'constant','task-gate.json':b'{"original":true}'}.items():
            (source/name).write_bytes(raw)
        client={'format':1,'files':{p.name:donor.pin(p) for p in source.iterdir()}}
        (source/'client-manifest.json').write_bytes(b.encoded(client))
        runtime={'format':1,'repository_commit':'a'*40,'files':{p.name:donor.pin(p) for p in source.iterdir()},
                 'armport_server_metrics':{'fixture':True},'armport_client':{'archive':'same'}}
        (source/'runtime-manifest.json').write_bytes(b.encoded(runtime))
        apk=self.root/'donor.apk'
        with ZipFile(apk,'w') as archive:archive.writestr('assets/runtime/game-package.tar.gz',b'old-game')
        old={'files':{'MapServer.exe':copy.deepcopy(b.BASELINE_MAP)},'original':True}
        self.old={'MapServer.exe':b'old-map','game-package.json':b'old-manifest','DbServer.exe':b'same-db'}
        self.new={'MapServer.exe':b'new-map','game-package.json':b'new-manifest','DbServer.exe':b'same-db'}
        def read(path):
            if Path(path).read_bytes()==b'old-game':return copy.deepcopy(old),copy.deepcopy(self.old)
            if Path(path).read_bytes()==b'new-game':return {'current':True},copy.deepcopy(self.new)
            raise ValueError('unknown game archive')
        native=NS(read_game_archive=read,validate_predecessor=mock.Mock(),
            previous_package=lambda _:copy.deepcopy(old),THOR_PREDECESSOR_MAPSERVER=b.BASELINE_MAP)
        docs={'runtime-manifest.json':{'files':{'game-package.tar.gz':donor.raw_pin(b'old-game')}}}
        self.enterContext(mock.patch.object(donor,'inspect_donor',return_value=docs))
        self.enterContext(mock.patch.object(b.importlib,'import_module',return_value=NS(
            mapserver_progress_contract=lambda _: {'producer':{'mapserver_sha256':b.BASELINE_MAP['sha256']}})))
        return source,apk,native,runtime

    def test_actual_donor_private_metadata_and_no_payload_copies_or_source_mutation(self):
        source,apk,native,runtime=self.fixture()
        before={p.name:(p.read_bytes(),p.stat().st_ino,p.stat().st_nlink) for p in source.iterdir()}
        (source/'__pycache__').mkdir()
        target=self.root/'baseline';view=b.asset_view(source,target,apk,native)
        self.assertFalse((target/'__pycache__').exists())
        self.assertEqual((target/'game-package.tar.gz').read_bytes(),b'old-game')
        self.assertFalse((target/b.BINDING).exists())
        self.assertEqual((target/'fixed.dat').stat().st_size,0)
        self.assertEqual(dict(view['file_binds']),{str(source/'fixed.dat'):'/opt/coh/fixed.dat',
            str(source/'task-gate.json'):'/opt/coh/task-gate.json'})
        self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_ino,p.stat().st_nlink) for p in source.iterdir() if p.is_file()})
        self.assertNotIn('armport_server_metrics',view['runtime_manifest'])
        self.assertNotIn(b.BINDING,view['client_manifest']['files'])
        self.assertEqual(view['runtime_manifest']['armport_client'],runtime['armport_client'])
        native.validate_predecessor.assert_called_once_with(b'old-manifest','thor_certified_startup')
        for name in b.CHANGED_FILES:self.assertNotEqual((source/name).stat().st_ino,(target/name).stat().st_ino)

    def test_other_native_member_change_refuses(self):
        source,apk,native,_=self.fixture();self.new['DbServer.exe']=b'wrong-db'
        with self.assertRaisesRegex(ValueError,'another native member'):
            b.asset_view(source,self.root/'baseline',apk,native)

    def test_changed_source_or_unknown_member_refuses(self):
        source,apk,native,_=self.fixture();(source/'fixed.dat').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'source asset changed'):
            b.asset_view(source,self.root/'baseline',apk,native)
        (source/'unexpected').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError,'Unexpected modern asset'):
            b.asset_view(source,self.root/'baseline2',apk,native)

class AdmissionTests(unittest.TestCase):
    def test_actual_baseline_native_proof_required(self):
        producer=dict(repository_commit='a'*40,manifest_sha256='b'*64,mapserver_sha256=b.BASELINE_MAP['sha256'])
        observation=dict(actual_installed_mapserver=copy.deepcopy(b.BASELINE_MAP),
            actual_launched_mapserver=copy.deepcopy(b.BASELINE_MAP),source_package_mapserver_pin_equal=True,
            launch_path_binding_observed=True,native_ready_verified=True)
        report={'scope':'actual_character_reopen_guest','session_id':'1'*32,'character_reopen':
            dict(session_id='1'*32,mapserver_producer=producer,map_startup_observation={'1':observation})}
        admit=b.admission(producer)
        self.assertEqual(admit(report,{'files':{}})['actual_mapserver'],b.BASELINE_MAP)
        for mutate in (
            lambda r:r['character_reopen']['mapserver_producer'].update(mapserver_sha256='f'*64),
            lambda r:r['character_reopen']['map_startup_observation']['1'].update(actual_launched_mapserver={'bytes':1,'sha256':'f'*64}),
            lambda r:r['character_reopen']['map_startup_observation']['1'].update(launch_path_binding_observed=False),
            lambda r:r['character_reopen']['map_startup_observation']['1'].update(native_ready_verified=False)):
            changed=copy.deepcopy(report);mutate(changed)
            with self.assertRaises(ValueError):admit(changed,{'files':{}})
        with self.assertRaises(ValueError):admit(report,{'armport_server_metrics':{},'files':{}})

class BaselineRunTests(unittest.TestCase):
    def fixture(self):
        root=Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-baseline-run-')))
        work=root/'work';work.mkdir();evidence=root/'evidence';evidence.mkdir();assets=work/'modern-assets';assets.mkdir()
        original=lambda *args:None
        records={};projector=NS(records=records,project=lambda *args:None)
        reopen=NS(persistent_profile_identity=mock.Mock(return_value={'same_profile':True}),
            archive_completed_reports=mock.Mock(),reset_session_requests=mock.Mock(),
            reopen_command=lambda command,old,new:[new if item==old else
                '/opt/coh/character_reopen_diagnostic.py' if item=='/opt/coh/character_creation_diagnostic.py' else item for item in command],
            validate_continuity=mock.Mock())
        returned={'session_id':'3'*32,'character_reopen':{}}
        def run_session(*args,**kwargs):
            records[args[4]]={'session_id':args[4]};returned['session_id']=args[4];return returned
        driver=NS(reopen=reopen,legacy_report=original,
            character=NS(OVERALL_SECONDS=5400),run_session=mock.Mock(side_effect=run_session))
        saved={'session_id':'2'*32,'scope':'actual_character_reopen_guest','passed':True,'cleanup_complete':True,
            'cleanup':dict(postgres_graceful=True,wine_prefix_stopped=True,owned_processes_reaped=True),
            'character_reopen':{'snapshot_sha256':'saved-modern-row-hash'}}
        runtime={'armport_client':{'same':True},'armport_server_native_closure':{'same':True},'files':{},
                 'armport_server_metrics':{},'armport_server_metrics_build':{}}
        view={'runtime_manifest':{'files':{}},'client_manifest':{},'expected_producer':{},'source_pins':{},
              'file_binds':[(str(assets/'fixed.dat'),'/opt/coh/fixed.dat')],'provenance':{'fixture_only':True}}
        self.enterContext(mock.patch.object(b,'asset_view',return_value=view))
        self.enterContext(mock.patch.object(v,'contracts',return_value={}))
        self.enterContext(mock.patch.object(v,'ModernProjector',return_value=projector))
        self.enterContext(mock.patch.object(b.secrets,'token_hex',return_value='3'*32))
        self.enterContext(mock.patch.object(b.time,'monotonic',return_value=100))
        command=['proot','-b',str(assets)+':/opt/coh','-w','/state','COH_CLIENT_ARCH=arm64',
                 '/opt/coh/character_creation_diagnostic.py','--session-id','1'*32]
        args=(driver,command,work,evidence,root/'proot',runtime,{},None,
              NS(legacy=original),saved,'2'*32,assets,root/'apk',None)
        return args,driver,reopen,saved,original,evidence

    def test_one_stopped_profile_reopen_preserves_bound_input_and_saved_proof(self):
        args,driver,reopen,saved,original,evidence=self.fixture();before=copy.deepcopy(saved)
        result=b.run(*args)
        self.assertTrue(result['passed']);self.assertFalse(result['physical_device_validated'])
        self.assertFalse(result['performance_acceptance']);self.assertEqual(saved,before)
        self.assertIs(driver.legacy_report,original);driver.run_session.assert_called_once()
        command,work,_,_,session,runtime,_,deadline=driver.run_session.call_args.args
        self.assertEqual(deadline,5500);self.assertEqual(session,'3'*32)
        self.assertIn(str(work/'baseline-assets')+':/opt/coh',command)
        self.assertIn(str(work/'modern-assets/fixed.dat')+':/opt/coh/fixed.dat',command)
        self.assertEqual(command[-1],'--zoning');self.assertIn('COH_CLIENT_ARCH=arm64',command)
        self.assertNotIn('armport_server_metrics',runtime)
        prior,_,first,last=reopen.validate_continuity.call_args.args
        self.assertIs(prior['character_creation'],saved['character_reopen']);self.assertEqual(first,last)
        self.assertTrue(json.loads((evidence/'baseline-compatibility-report.json').read_text())['passed'])

    def test_incomplete_modern_cleanup_never_starts_baseline(self):
        args,driver,reopen,saved,original,evidence=self.fixture();saved['cleanup']['postgres_graceful']=False
        with self.assertRaisesRegex(ValueError,'did not stop cleanly'):b.run(*args)
        driver.run_session.assert_not_called();reopen.persistent_profile_identity.assert_not_called()
        self.assertIs(driver.legacy_report,original)
        self.assertFalse(json.loads((evidence/'baseline-compatibility-report.json').read_text())['passed'])

if __name__=='__main__':unittest.main()
