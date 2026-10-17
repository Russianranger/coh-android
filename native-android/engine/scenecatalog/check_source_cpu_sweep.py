#!/usr/bin/env python3
"""Bounded sequential authentic root CPU preparation; fixture materials only."""
import argparse,collections,ctypes as C,hashlib,json,math,os,struct,subprocess,tempfile,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent
p=argparse.ArgumentParser(description=__doc__)
for key in ('capture-directory','body-directory','renderer-source-root','root-coverage','output','ledger-output'):p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args();cap=a.capture_directory.resolve();ER=a.renderer_source_root.resolve();EH=ER/'native-android/engine/world-render-adapter'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,**kwargs):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=300,**kwargs)
 if r.returncode:raise RuntimeError(r.stdout[-3000:]+r.stderr)
 return r.stdout
sources=[HERE/'diagnose_source_cpu_sweep.c',HERE/'coh_source_special.c',EH/'coh_wr_rigid_legacy_formats.c',EH/'coh_wr_rigid_v7.c',EH/'coh_wr_rigid_v5.c',EH/'coh_wr_rigid.c',EH/'coh_wr_rigid_source.c',ENGINE/'renderer/coh_renderer.c',HERE/'coh_source_selection.c',HERE/'coh_resource_join.c',HERE/'coh_resource_index.c',HERE/'coh_resource_geo_source.c',HERE/'coh_catalog_snapshot.c',HERE/'coh_catalog_owner.c',HERE/'coh_scenecatalog.c',ENGINE/'scenegraph/runtime_snapshot.c',ENGINE/'scenegraph/tests/runtime_matrix_bridge.c',ENGINE/'replication/coh_replication.c',ENGINE/'replication/coh_groups.c',ENGINE/'assets/coh_asset_loader.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
deps=sources+[HERE/'coh_checked_sources.py',HERE/'coh_source_cpu_oracle.py',HERE/'inspect_source_cpu_sweep.py',HERE/'tests/source_special_routes.json',HERE/'coh_source_special.h',ROOT/'native-android/src/byte_reader.h',HERE/'inspect_root_partitions.py',ROOT/'native-android/tools/material_fixture/original_delta_check.py',ROOT/'upstream/ouroboros/Common/seq/anim.c',EH/'coh_wr_rigid_legacy_formats.h',EH/'coh_wr_rigid_v7.h',EH/'coh_wr_rigid_v5.h',EH/'coh_wr_rigid_internal.h',EH/'coh_wr_rigid.h',EH/'coh_wr_rigid_source.h',EH/'coh_world_render.h',ENGINE/'renderer/coh_renderer.h',ENGINE/'renderer/coh_renderer_shaders.h']+[HERE/n for n in ('coh_source_selection.h','coh_source_selection_profile.inc','coh_resource_join.h','coh_resource_index.h','coh_resource_geo_source.h','coh_catalog_snapshot.h','coh_catalog_owner.h','coh_scenecatalog.h')]+[ENGINE/'scenegraph'/n for n in ('runtime_snapshot.h','runtime_graph.h','coh_scenegraph.c','coh_scenegraph.h')]+[ENGINE/'replication'/n for n in ('coh_replication.h','coh_groups.h')]+[ENGINE/'assets'/n for n in ('coh_asset_loader.h','coh_asset_geo.h')]+[ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',Path(__file__)]
arguments=[cap/n for n in ('catalog.cohcat','runtime.cohrts','resources.cohres','source-identity.json','run-identity.json')]+[cap.parent/'control-fixture.json',cap/'resource-binding.json',cap/'capture-receipt.json',HERE/'evidence/actual-resource-bodies-source-adapter-sealed-38994607354.json',HERE/'evidence/prepared-geo-source-route-final-38994607354.json',a.body_directory]
# Freeze every executed/read project dependency BEFORE the first project import.
# This entry script is run directly as source; bootstrap the loader itself without
# importlib, sys.modules, source-cache lookup or an external unseen bootstrap.
def label(path):return ('coordinator:'+str(path.relative_to(ROOT))) if path.is_relative_to(ROOT) else ('renderer:'+str(path.relative_to(ER)))
frozen={f.resolve():f.read_bytes() for f in deps}
for f,raw in frozen.items():
 if f.read_bytes()!=raw:raise RuntimeError('source changed during pre-import freeze: '+str(f))
guard_path=(HERE/'coh_checked_sources.py').resolve();namespace={'__name__':'checked_source_bootstrap','__file__':str(guard_path)}
exec(compile(frozen[guard_path],str(guard_path),'exec',dont_inherit=True),namespace)
checked=namespace['CheckedSources'](frozen);checked.verify()
pins={label(f):hashlib.sha256(raw).hexdigest() for f,raw in frozen.items()}
parts=checked.load('partitions',HERE/'inspect_root_partitions.py');root_partitions=parts.build(cap/'resources.cohres',a.root_coverage);coverage=json.loads(a.root_coverage.read_text());models=coverage['models'];assert len(models)==2916
inputs=list(arguments[:-1])+[a.root_coverage,HERE/'evidence/source-special-stack-host.json'];bodies={m['asset_path']:m['body_sha256'] for m in models};assert len(bodies)==391
for path,digest in bodies.items():assert sha(a.body_directory/path)==digest
# Whole original consumer captures were not rerun. This new qualification executes
# the unchanged generic delta consumer over every CPU-successful actual stream.
inputpins={str(f):sha(f) for f in inputs};modes={};semantic=None;ledger=None
with tempfile.TemporaryDirectory(prefix='coh-root-cpu-') as td:
 temp=Path(td);plan=bytearray(b'COHSWP01'+struct.pack('<III',1,2916,3083))
 for m in models:
  ordinals=m['source_ordinals'];plan+=struct.pack('<II',ordinals[0],len(ordinals))+struct.pack('<'+'I'*len(ordinals),*ordinals)
 plan_path=temp/'plan.bin';plan_path.write_bytes(plan);plan_sha=hashlib.sha256(plan).hexdigest()
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=temp/mode
  run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-pthread','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),'-I'+str(EH.parent/'scenecatalog'),*flags,*sources,'-lcrypto','-lz','-lm','-o',binary])
  text=run([binary,*arguments,plan_path],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));rows=[json.loads(line) for line in text.splitlines()];summary=rows[-1];assert rows[0]['event']=='scope' and rows[0]['plan_sha256']==plan_sha
  # Preserve even a stopped sweep. It must never be described as complete.
  pairs=sorted([r for r in rows if r['event']=='pair'],key=lambda r:r['i']);files=[r for r in rows if r['event']=='file'];cleanup=[r for r in rows if r['event']=='cleanup'];assert len(files)==len(cleanup) and all(r['pinned_blobs']==0 for r in cleanup)
  for r in pairs:
   m=models[r['i']];assert r['owners']==m['source_ordinals'] and r['ordinal']==m['source_ordinals'][0]
   if r['phase']=='cpu':assert r['version']==m['metadata']['version'] and r['model']==m['metadata']['name']
  core={'scope':rows[0],'pairs':pairs,'files':files,'cleanup':cleanup,'summary':{k:v for k,v in summary.items() if k!='elapsed_ms'}}
  if semantic is None:semantic=core;ledger=rows
  else:assert core==semantic,'mode-dependent semantic result'
  modes[mode]={'binary_sha256':sha(binary),'summary':summary,'raw_ledger_sha256':hashlib.sha256(text.encode()).hexdigest()}
  print(json.dumps({'mode':mode,'summary':summary}),flush=True)
  if not summary['complete']:break
 # Execute every project helper from the pre-admitted immutable source bytes.
 original=checked.load('original',ROOT/'native-android/tools/material_fixture/original_delta_check.py')
 oracle=checked.load('source_cpu_oracle',HERE/'coh_source_cpu_oracle.py')
 original_proof=oracle.compare(models,semantic['pairs'],bodies,a.body_directory,original,ROOT/'upstream/ouroboros/Common/seq/anim.c',temp,run)
 checked.verify()
assert pins=={label(f):sha(f) for f in deps} and inputpins=={str(f):sha(f) for f in inputs}
for path,digest in bodies.items():assert sha(a.body_directory/path)==digest
# A compact aggregate ledger keeps all exact source ordinals, full names/hashes,
# per-file cleanup, per-pair CPU and auxiliary result without duplicate modes.
ledger_raw=(json.dumps(semantic,separators=(',',':'))+'\n').encode();compressed=zlib.compress(ledger_raw,9)
with a.ledger_output.open('xb') as f:f.write(compressed)
versions={}
for row in semantic['pairs']:
 version=str(models[row['i']]['metadata']['version']);v=versions.setdefault(version,{'pairs':0,'owners':0,'successes':0,'statuses':{},'cpu_peak':0,'packet_bytes':0});v['pairs']+=1;v['owners']+=len(row['owners']);v['successes']+=row['status']==0;key=str(row['status']);v['statuses'][key]=v['statuses'].get(key,0)+1;v['cpu_peak']=max(v['cpu_peak'],row['cpu_peak']);v['packet_bytes']+=row['packet_bytes']
result={'passed':True,'complete':semantic['summary']['complete'],'scope':'Sequential exact registered Body→fixed low-level CPU geometry diagnostic, fixture materials. Not ownership-transfer bridge, CLIENT/material/portal/GPU/world admission.','source_sha256':pins,'input_sha256':inputpins,'body_sha256':bodies,'modes':modes,'versions':versions,'plan_sha256':plan_sha,'ledger_sha256':hashlib.sha256(compressed).hexdigest(),'ledger_decoded_sha256':hashlib.sha256(ledger_raw).hexdigest(),'ledger_bytes':len(compressed),'ledger_decoded_bytes':len(ledger_raw),'original_delta':original_proof,'checked_source_execution':checked.loads,'world_authority':False,'client_materials_available':False,'direct_open_observed':False,'android_executed':False,'original32_readModel_executed':False,'leak_sanitizer':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'complete':result['complete'],'versions':versions,'original_delta':result['original_delta'],'ledger_bytes':len(compressed)}))
