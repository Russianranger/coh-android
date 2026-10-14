import ast
import copy
import struct
from pathlib import Path
import sys
import os
import subprocess
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT/'probe'),str(ROOT/'native'),str(ROOT/'transport'),str(ROOT/'pipeline')]
import package_live_native as package
import qualify_live_bridge_probe_windows as qualifier
from test_live_bridge_probe_parser import packet,row
WORKFLOW=ROOT/'pipeline/native-client-live-directory-sdk.yml'
if not WORKFLOW.is_file():
    WORKFLOW=ROOT.parents[1]/'.github/workflows/android-native-client-live-directory-sdk.yml'


class PipelineSource(unittest.TestCase):
    def test_probe_has_finite_observation_and_exact_native_api_contract(self):
        text=(ROOT/'probe/coh_live_bridge_probe.c').read_text()
        self.assertIn('#define NT_PROBE_MAX_ROWS 256u',text)
        self.assertIn('#define NT_PROBE_MAX_BATCHES 32u',text)
        self.assertIn('#define NT_PROBE_BUFFER_BYTES 8192u',text)
        self.assertIn('0x100001,&attributes,&io,probe.mode==2?0:3,0x4021',text)
        self.assertIn('sizeof(buffer),3,0,&mask',text)
        self.assertIn('probe.open_status!=0',text)
        self.assertIn('probe.info_status!=0',text)
        self.assertIn("if(getchar()!='N')",text)
        self.assertIn("if(getchar()!='C')",text)
        self.assertNotIn('Sleep(',text)
        self.assertNotIn('CreateProcess',text)

    def test_workflow_builds_only_one_game_and_probe_and_preserves_failed_stage_bytes(self):
        text=WORKFLOW.read_text()
        value=yaml.safe_load(text)
        self.assertEqual(set(value['jobs']),{'portable-controls','native-game-and-observer'})
        steps=value['jobs']['native-game-and-observer']['steps']
        scripts=[s.get('run','') for s in steps]
        compiler='\n'.join(scripts)
        self.assertEqual(compiler.count('cl /nologo'),1)
        self.assertEqual(compiler.count('--parallel --target Game'),1)
        self.assertNotIn('--target MapServer',compiler)
        observer=next(i for i,s in enumerate(steps) if s.get('name','').startswith('Compile one tiny'))
        game=next(i for i,s in enumerate(steps) if s.get('name','').startswith('Compile one complete'))
        self.assertLess(observer,game)
        checkout=next(i for i,s in enumerate(steps) if s.get('uses','').startswith('actions/checkout'))
        self.assertIn('core.autocrlf false',scripts[checkout-1])
        recovery=next(s for s in steps if s.get('name','').startswith('Preserve any compiled'))
        self.assertEqual(recovery['if'],'always()')
        self.assertIn('CityOfHeroes.exe',recovery['run'])
        self.assertIn('coh-live-bridge-probe.exe',recovery['run'])
        self.assertNotIn('release',value['permissions'])
        controls='\n'.join(s.get('run','') for s in value['jobs']['portable-controls']['steps'])
        self.assertIn('PyYAML==6.0.2',controls)
        self.assertIn('--commit "$env:GITHUB_SHA"',compiler)

    def test_pipeline_and_embedded_python_syntax(self):
        for p in (ROOT/'pipeline').glob('*.py'):
            ast.parse(p.read_text())
        text=WORKFLOW.read_text()
        program=text.split("$source = @'",1)[1].split("'@",1)[0]
        import textwrap
        ast.parse(textwrap.dedent(program))

    def test_sdk_package_retains_source_renderer_and_closed_runtime_gates(self):
        text=(ROOT/'pipeline/package_live_native.py').read_text()
        self.assertIn('live.validate_staged_source',text)
        self.assertIn('retained.validate_cmake_cache',text)
        self.assertIn("game_record['imports']==inherited['native_game']['imports']",text)
        self.assertIn("'native_Game_executed':False",text)
        self.assertIn("'Android_runtime_executed':False",text)
        self.assertIn("'native_registration_allowed':False",text)
        self.assertNotIn('native_Game_executed\':True',text)
        self.assertIn("pin(OVERLAY/'native/coh_live_directory.cmake')",text)
        self.assertIn("'test_live_sdk_pipeline'",text)

    def test_clean_retained_repository_imports_without_research_capture_helper(self):
        repository=Path(os.environ['COH_LIVE_REPOSITORY']).resolve()
        tools=repository/'tools'
        # Admit only the committed reference/retained helper roots, deliberately
        # refusing every research-only package in a fresh process import graph.
        program='''import importlib.abc,sys,pathlib
class NoResearch(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.startswith(('package_native_client_metadata_capture','prepare_native_client_metadata_census','native_client_census')):
            raise ImportError('Research-only helper refused: '+fullname)
sys.meta_path.insert(0,NoResearch())
sys.path.insert(0,sys.argv[1])
import package_live_native as p
retained,file_record,dependency=p.imports(sys.argv[2])
assert retained.ROOT==pathlib.Path(sys.argv[2]).resolve()
assert callable(file_record) and callable(dependency)
assert not any(n.startswith('package_native_client_metadata_capture') for n in sys.modules)
print('Clean retained import closure passed')
'''
        result=subprocess.run([sys.executable,'-W','error::ResourceWarning','-c',program,str(ROOT/'pipeline'),str(repository)],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('Clean retained import closure passed',result.stdout)

    def test_typed_sdk_receipt_binds_actual_probe_source_console_pid_cleanup_and_membership(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            binary=root/'probe.exe';binary.write_bytes(b'controlled binary only')
            original=packet()
            raw=bytearray(original[:-40])
            names=[f'fixture_{n:03d}_'+('x'*70)+'.fx' for n in range(200)]
            for batch in range(10):
                rows=bytearray()
                for offset,name in enumerate(names[batch*20:(batch+1)*20]):
                    item=row(name);span=(len(item)+7)&~7
                    rows+=row(name,span if offset<19 else 0)+b'\0'*(span-len(item))
                raw+=b'NTBATCH1'+struct.pack('<IIII',batch,0,len(rows),20)+rows
            raw+=b'NTEND1\0\0'+struct.pack('<IIIIIIII',1,1,10,200,0x80000006,0,len(raw)+40,0)
            packets={'stock.bin':bytes(raw),'share-block.bin':packet(mode=2),
                     'sharing-refusal.bin':packet(complete=0,opened=0xc0000043,info=0xc0000001,inode=0)}
            records={}
            for name,data in packets.items():
                path=root/name;path.write_bytes(data)
                parsed=package.probe_parser.parse(data)
                complete=parsed['packet_complete'];mode=parsed['mode'];code=0 if complete else 1
                stdout=('COH_NT_SHARE_READY pid=12 inode=99\n' if mode==2 else '')+\
                    f'COH_NT_PROBE_RESULT pid=12 mode={mode} complete={int(complete)} rows={len(parsed["rows"])} batches={len(parsed["batches"])} input_cleanup_failed=0 bytes={len(data)}\n'
                records[name]={'held_native_pid':12,'returncode':code,'execution_error':None,'stdout':stdout,
                    'stderr':'','packet':package.pin(path),'parsed':parsed,'readiness_observer_stopped':True,
                    'process_cleanup':{'held_pid':12,'returncode':code,'closed_exact_owned_child':True,'forced_termination':False}}
            refused=lambda code,pin: {'held_native_pid':21,'returncode':code,'execution_error':None,'packet':pin,
                'process_cleanup':{'held_pid':21,'returncode':code,'closed_exact_owned_child':True,'forced_termination':False}}
            control={'format':1,'role':'fresh_native_Win32_NT_bridge_observer_controls','status':'passed',
                     'binary':package.pin(binary),'fresh_native_control_groups':4,'repository_commit':'a'*40,
                     'probe_source':qualifier.source_pins(),'Wine_executed':False,'Android_runtime_executed':False,
                     'Game_executed':False,'provider_authority':False,'publication_allowed':False,
                     'cases':{'actual_stock_multibuffer':records['stock.bin'],
                              'existing_output_preserved':refused(65,records['stock.bin']['packet']),
                              'native_share_refusal_and_owned_release':{'held':records['share-block.bin'],'blocked':records['sharing-refusal.bin']},
                              'input_namespace_output_refused':refused(64,None)}}
            package.validate_probe_controls(control,binary,root,'a'*40)
            for change in ('source','commit','console','pid','cleanup','mode'):
                value=copy.deepcopy(control)
                case=value['cases']['actual_stock_multibuffer']
                if change=='source':value['probe_source']['coh_live_bridge_probe.c']['sha256']='0'*64
                elif change=='commit':value['repository_commit']='b'*40
                elif change=='console':case['stdout']=case['stdout'].replace('rows=200','rows=201')
                elif change=='pid':case['held_native_pid']=13
                elif change=='cleanup':case['process_cleanup']['closed_exact_owned_child']=False
                else:case['stdout']=case['stdout'].replace('mode=1','mode=2')
                with self.assertRaises(ValueError):
                    package.validate_probe_controls(value,binary,root,'a'*40)


if __name__=='__main__':
    unittest.main()
