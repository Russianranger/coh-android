#!/usr/bin/env python3
"""Qualify exact historical CLIENT request inventory for two retained SOURCE models."""
import argparse,gzip,hashlib,json,os,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent
P=argparse.ArgumentParser(description=__doc__)
P.add_argument('--source-root',type=Path,required=True)
P.add_argument('--work',type=Path,required=True)
P.add_argument('--output',type=Path,required=True)
P.add_argument('--prepared',type=Path,help='Reuse immutable authenticated one-GEO preparation; rehashed before use')
a=P.parse_args();work=a.work.resolve();root=a.source_root.resolve()
if work.exists() or work==ROOT or work.is_relative_to(ROOT):P.error('Fresh external work directory required')
work.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=300,**kw)
 if r.returncode:raise RuntimeError(r.stdout[-2000:]+r.stderr[-5000:])
 return r.stdout
prepared=a.prepared.resolve() if a.prepared else work/'prepared'
if not a.prepared:run(['python3',HERE/'prepare_source_placement.py','--source-root',root,'--output',prepared])
cache=prepared/'tricks.bin';assert sha(cache)=='cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1'
body=prepared/'bodies/data/object_library/city_zones/atlas_park_makeover/ap_cityhall_makeover_01.geo';assert sha(body)=='80e8e7530ab9d42ad98a6ddd065a0e40ba1cc1a999558241c3aebc17eb89db9a'
stateszip=root/'native-android/engine/world-render-adapter/qualification/client-surface-states-20261017/seqstatebits.bin.gz'
with gzip.open(stateszip,'rb') as stream:raw=stream.read(15381)
assert len(raw)==15380 and hashlib.sha256(raw).hexdigest()=='9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac'
states=work/'seqstatebits.bin';states.write_bytes(raw)
old=HERE/'tests/test_source_placement.c';assert sha(old)=='dc1971dca7248070edf7fe066c7e0d5080f40ea09997f4aa804ba2d8f071e7ce'
fixture=old.read_text();anchor='int main(int argc,char**argv){CHECK(argc==13);';assert fixture.count(anchor)==1
fixture=fixture.replace(anchor,'#include "test_source_material_plan.inc"\nint main(int argc,char**argv){CHECK(argc==14);')
anchor=' size_t owner_live=sr2.owned_bytes+sr2.shared_source_bytes;';assert fixture.count(anchor)==1
fixture=fixture.replace(anchor,' material_tests(sealed,argv[12],argv[13]);\n'+anchor)
source=work/'source-material-fixture.c';source.write_text(fixture)
EH=ENGINE/'world-render-adapter'
sources=[source,HERE/'coh_source_material_plan.c',HERE/'coh_source_placement.c',ENGINE/'scenegraph/coh_runtime_candidates.c',ENGINE/'scenegraph/coh_runtime_instances.c',HERE/'coh_source_sealed.c',HERE/'coh_source_mesh_batch.c',HERE/'coh_source_mesh.c']+[HERE/(n+'.c') for n in ('coh_source_selection','coh_resource_join','coh_resource_index','coh_resource_geo_source','coh_catalog_snapshot','coh_catalog_owner','coh_scenecatalog')]+[ENGINE/n for n in ('scenegraph/runtime_snapshot.c','scenegraph/tests/runtime_matrix_bridge.c','replication/coh_replication.c','replication/coh_groups.c','assets/coh_asset_loader.c','assets/coh_asset_geo.c')]+[ROOT/'native-android/src'/n for n in ('coh_assets.c','coh_dds.c')]+[EH/(n+'.c') for n in ('coh_wr_texopt','coh_wr_trick','coh_wr_surface_states')]
includes=[HERE,HERE/'tests',EH,ROOT/'native-android/include'];deps={Path(__file__).resolve(),old};pending=list(sources)
while pending:
 f=pending.pop().resolve()
 if f in deps:continue
 deps.add(f)
 for name in re.findall(rb'^\s*#\s*include\s*"([^"\n]+)"',f.read_bytes(),re.M):
  options=[f.parent/name.decode()]+[d/name.decode() for d in includes]
  found=next((x.resolve() for x in options if x.is_file()),None)
  if found is None:raise RuntimeError('Missing include '+name.decode())
  pending.append(found)
frozen={f:sha(f) for f in deps}
cap=prepared/'capture'
args=[cap/n for n in ('catalog.cohcat','runtime.cohrts','resources.cohres','source-identity.json','run-identity.json')]+[prepared/'control-fixture.json',cap/'resource-binding.json',cap/'capture-receipt.json',HERE/'evidence/actual-resource-bodies-source-adapter-sealed-38994607354.json',HERE/'evidence/prepared-geo-source-route-final-38994607354.json',prepared/'bodies',cache,states]
inputs={f:sha(f) for f in args if f.is_file()};inputs[body]=sha(body)
# Pins originate in the already accepted capture's independent source/run chain.
assert inputs[cap/'catalog.cohcat']=='61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763'
assert inputs[cap/'runtime.cohrts']=='c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02'
assert inputs[cap/'resources.cohres']=='8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6'
# Reverify the exact independently qualified source lookup/postprocess closure;
# do not rerun its historical policy suite or claim current CLIENT selection.
prior=EH/'qualification/client-texopt-lookup-20261017/host.json'
assert sha(prior)=='fa51e2a18556caf727a160b5fb85172e71f263b8415e77ae425397aea4023961'
qualified=json.loads(prior.read_bytes());assert qualified['passed']
reused={}
compiled_names={str(f.relative_to(ROOT)) for f in frozen if f.is_relative_to(ROOT)}
for name,pin in qualified['source_sha256'].items():
 if not name.startswith('upstream/') and name not in compiled_names:continue
 path=root/name
 if sha(path)!=pin:raise ValueError('Prior qualified source changed: '+name)
 reused[path]=pin
modes={};same=None;stack=[]
for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
 binary=work/mode
 run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-pthread',*['-I'+str(d) for d in includes],*flags,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free,--wrap=coh_source_selection_retain','-lcrypto','-lz','-lm','-o',binary])
 rss=work/(mode+'-rss-kib.txt')
 measure="import resource,subprocess,sys; r=subprocess.run(sys.argv[2:]); open(sys.argv[1],'x').write(str(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)); sys.exit(r.returncode)"
 result=run([sys.executable,'-c',measure,rss,binary,*args],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
 (work/(mode+'.stdout')).write_text(result)
 rows=[json.loads(line) for line in result.splitlines()];plans=[r for r in rows if r.get('material_plan')];summary=next(r for r in rows if r.get('material_plan_summary'));base=rows[-1]
 assert len(plans)==21 and summary['plans']==21 and base['passed'] and summary['peak_named_bytes']<=96*1024**2
 semantic={'plans':plans,'material_summary':summary,'source_fixture':base}
 if same is None:same=semantic
 else:assert same==semantic
 modes[mode]={'binary_sha256':sha(binary),'checks':base['checks'],'material_summary':summary,'host_peak_RSS_bytes':int(rss.read_text().strip())*1024};print(json.dumps({'mode':mode,'checks':base['checks'],'material_summary':summary}),flush=True)
# Conservative sum of every reached emitted native frame in the query closure.
# libc memcpy/memset, compiler/sanitizer runtime and caller frames stay external.
selected={HERE/'coh_source_material_plan.c':None,
 HERE/'coh_source_sealed.c':{'safe','separate','coh_source_sealed_report','coh_source_sealed_identity','coh_source_sealed_entry','coh_source_sealed_part'},
 EH/'coh_wr_texopt.c':{'apart','record_view','coh_wr_texopt_record_view'}}
for opt in ('-O0','-O1','-O2'):
 frames={};total=0
 for src,names in selected.items():
  obj=work/(src.stem+opt+'.o');run(['cc','-std=c11',opt,'-fstack-usage',*['-I'+str(d) for d in includes],'-c',src,'-o',obj]);lines=obj.with_suffix('.su').read_text().splitlines();chosen=[]
  for line in lines:
   fields=line.split('\t');name=fields[0].rsplit(':',1)[-1].split('.')[0]
   if names is None or name in names:chosen.append(line);total+=int(fields[1])
  assert chosen;frames[str(src)]=chosen
 assert total<32768;stack.append({'optimization':opt,'reached_frames':frames,'conservative_native_frame_sum':total})
assert frozen=={f:sha(f) for f in frozen} and inputs=={f:sha(f) for f in inputs} and reused=={f:sha(f) for f in reused}
receipt={'passed':True,'scope':'Exact-key historical CLIENT TexOpt dependency inventory tied to authentic two-model sealed SOURCE partitions; no effective material/texture/GPU/current generation admission','source_sha256':{str(f):v for f,v in frozen.items()},'input_sha256':{str(f):v for f,v in inputs.items()},'reused_source_qualification_sha256':sha(prior),'reused_qualified_source_sha256':{str(f):v for f,v in reused.items()},'prior_source_qualification_replayed':False,'modes':modes,'plans':same['plans'],'material_summary':same['material_summary'],'source_fixture':same['source_fixture'],'new_query_stack':stack,'effective_client_material':False,'texture_body_provenance':False,'live_generation_admitted':False,'world_authority':False,'android_execution':False,'device_RSS_PSS_measurement':None,'host_RSS_scope':'per-mode native host fixture child high-water RSS from a fresh Python wrapper RUSAGE_CHILDREN (one child); separate from source named reservations; not Android or GPU memory','leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
