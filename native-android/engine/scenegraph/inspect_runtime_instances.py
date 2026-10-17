#!/usr/bin/env python3
"""Bounded source-only occurrence enumeration of retained authentic runtime graph."""
from pathlib import Path
import argparse,hashlib,importlib,json,os,re,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent;NATIVE=ROOT/'native-android'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
p=argparse.ArgumentParser();p.add_argument('--capture-directory',type=Path,required=True);p.add_argument('--binding-sha256',required=True);p.add_argument('--maximum-occurrences',type=int,default=1048576);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise ValueError('New output required')
if not re.fullmatch('[0-9a-f]{64}',a.binding_sha256) or not 0<a.maximum_occurrences<=16777216:raise ValueError('Trusted binding pin and bounded count required')
sources=[HERE/'diagnose_runtime_instances.c',HERE/'coh_runtime_instances.c',HERE/'runtime_snapshot.c',HERE/'tests/runtime_matrix_bridge.c',ENGINE/'scenecatalog/coh_scenecatalog.c',ENGINE/'replication/coh_replication.c',ENGINE/'replication/coh_groups.c']
deps=sources+[HERE/'coh_scenegraph.c',Path(__file__),ROOT/'upstream/ouroboros/Common/group/grouputil.c',ROOT/'upstream/ouroboros/Common/group/grouptrack.c',ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h']
for directory in [ENGINE,NATIVE/'include',NATIVE/'protocol',NATIVE/'src']:
 deps.extend(directory.rglob('*.h'))
for directory in [ENGINE/'scenecatalog-server',ENGINE/'scenecatalog']:
 for extension in ['*.py','*.inc','*.json']:
  deps.extend(x for x in directory.rglob(extension) if 'evidence' not in x.parts and '__pycache__' not in x.parts)
deps=sorted(set(deps));pins={str(x.relative_to(ROOT)):sha(x) for x in deps}
capture=a.capture_directory.resolve();sys.path.insert(0,str(ENGINE/'scenecatalog-server'));validator=importlib.import_module('capture_resources');d=validator.d
binding_path=d.regular(capture/'resource-binding.json')
if d.hash_file(binding_path,8*1024**2)[1]!=a.binding_sha256:raise ValueError('Binding digest differs')
binding=d.json_object(d.read(binding_path,8*1024**2));receipt=d.json_object(d.read(capture/'capture-receipt.json',8*1024**2))
if validator.build_binding(capture,receipt,binding['asset_generation'])!=binding:raise ValueError('Capture binding revalidation differs')
paths=[binding_path,capture/'capture-receipt.json',capture/'source-identity.json',capture/'run-identity.json',capture/'catalog.cohcat',capture/'runtime.cohrts',capture/'resources.cohres'];inputs={x.name:{'bytes':x.stat().st_size,'sha256':sha(x)} for x in paths}
arguments=[capture/'catalog.cohcat',capture/'runtime.cohrts',binding['asset_generation'],binding['catalog']['sha256'],binding['snapshot']['sha256'],binding['source_identity']['sha256'],binding['run_identity']['sha256'],a.maximum_occurrences]
modes={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
with tempfile.TemporaryDirectory(prefix='coh-actual-runtime-instances-') as directory:
 work=Path(directory)
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off',*flags,'-I'+str(HERE),*sources,'-lcrypto','-lm','-o',binary]);row=json.loads(run([binary,*arguments],env=env));assert row['passed'] and row['independent_dag_count_equal'];modes[mode]={'binary_sha256':sha(binary),'result':row}
assert modes['release']['result']==modes['asan']['result']==modes['ubsan']['result']
assert pins=={str(x.relative_to(ROOT)):sha(x) for x in deps}
assert inputs=={x.name:{'bytes':x.stat().st_size,'sha256':sha(x)} for x in paths}
result={'passed':True,'source_sha256':pins,'capture_inputs':inputs,'binding_sha256':a.binding_sha256,'maximum_occurrences':a.maximum_occurrences,'modes':modes,'scope':'every source graph root/child path, no flattening; independent bounded DAG multiplicity recurrence agrees; raw observed roots composed with decoded source-child matrices','source_generation_admitted':False,'assets_admitted':False,'client_materials_available':False,'client_lods_available':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,**{k:v for k,v in modes['release']['result'].items() if k!='per_root'}}))
