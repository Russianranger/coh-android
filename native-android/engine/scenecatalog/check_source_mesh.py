#!/usr/bin/env python3
"""Exact CityHall SOURCE base geometry plus actual historical dictionaries, <=96MiB."""
import argparse,hashlib,json,os,re,subprocess,tempfile,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent
p=argparse.ArgumentParser(description=__doc__)
for n in ('capture-directory','body-directory','dictionary-source-root','dictionary-cache','output'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();D=a.dictionary_source_root.resolve();EH=D/'native-android/engine/world-render-adapter';cap=a.capture_directory.resolve()
sources=[HERE/'tests/test_source_mesh.c',HERE/'coh_source_mesh.c']+[HERE/(n+'.c') for n in ('coh_source_selection','coh_resource_join','coh_resource_index','coh_resource_geo_source','coh_catalog_snapshot','coh_catalog_owner','coh_scenecatalog')]+[ENGINE/n for n in ('scenegraph/runtime_snapshot.c','scenegraph/tests/runtime_matrix_bridge.c','replication/coh_replication.c','replication/coh_groups.c','assets/coh_asset_loader.c','assets/coh_asset_geo.c')]+[ROOT/'native-android/src'/n for n in ('coh_assets.c','coh_dds.c')]+[EH/(n+'.c') for n in ('coh_wr_texopt','coh_wr_trick','coh_wr_surface_states')]
includes=[HERE,EH,ROOT/'native-android/include'];deps={Path(__file__).resolve()};pending=list(sources)
# Freeze a transitive quoted-include closure before any compilation. No project
# Python imports/module caches are used by this entry script.
while pending:
 f=pending.pop().resolve()
 if f in deps:continue
 deps.add(f)
 for name in re.findall(rb'^\s*#\s*include\s*"([^"\n]+)"',f.read_bytes(),re.M):
  candidates=[f.parent/name.decode()]+[d/name.decode() for d in includes]
  found=next((n.resolve() for n in candidates if n.is_file()),None)
  if found is None:raise RuntimeError('missing include '+name.decode())
  pending.append(found)
frozen={f:f.read_bytes() for f in deps}
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def verify():
 for f,b in frozen.items():
  if f.read_bytes()!=b:raise RuntimeError('source changed '+str(f))
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if r.returncode:raise RuntimeError(r.stdout[-3000:]+r.stderr[-5000:])
 return r.stdout
arguments=[cap/n for n in ('catalog.cohcat','runtime.cohrts','resources.cohres','source-identity.json','run-identity.json')]+[cap.parent/'control-fixture.json',cap/'resource-binding.json',cap/'capture-receipt.json',HERE/'evidence/actual-resource-bodies-source-adapter-sealed-38994607354.json',HERE/'evidence/prepared-geo-source-route-final-38994607354.json',a.body_directory,a.dictionary_cache]
ledger=HERE/'evidence/source-cpu-sweep-final-ledger.zlib'
assert sha(ledger)=='6e6d39e3b8bd9fae9bd7f9b7213cdce4569ee7856ae6c7d9f199d5c26ca89fd1'
old=json.loads(zlib.decompress(ledger.read_bytes()));row=next(r for r in old['pairs'] if r['ordinal']==26509)
assert row['packet_sha256']=='e026c08ea55313eab0ac01276cc9a0231fdfe07d111817393b9ce1e4e477cc3d' and row['packet_bytes']==21771948
body=a.body_directory/'data/object_library/city_zones/atlas_park_makeover/ap_cityhall_makeover_01.geo'
inputs=[f for f in arguments if f.is_file()]+[body,ledger,HERE/'evidence/source-cpu-sweep-final-host.json',HERE/'evidence/source-cpu-checked-source-host.json'];pins={str(f):sha(f) for f in inputs}
assert sha(a.dictionary_cache)=='cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1'
modes={};semantic=None
with tempfile.TemporaryDirectory(prefix='coh-source-mesh-') as td:
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=Path(td)/mode;verify()
  run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-pthread',*['-I'+str(d) for d in includes],*flags,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lcrypto','-lz','-lm','-o',binary])
  verify();result=json.loads(run([binary,*arguments],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  assert result['passed'] and result['mesh_peak']<96*1024*1024 and result['packet_bytes']==row['packet_bytes']
  if semantic is None:semantic=result
  else:assert semantic==result
  modes[mode]={'binary_sha256':sha(binary),'result':result};print(json.dumps({'mode':mode,**result}),flush=True)
 stack=[]
 for opt in ('-O0','-O1','-O2'):
  frames={};total=0
  for src in [HERE/'coh_source_mesh.c',HERE/'coh_source_selection.c',HERE/'coh_resource_index.c',HERE/'coh_resource_geo_source.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c']:
   obj=Path(td)/(src.stem+opt+'.o');run(['cc','-std=c11',opt,'-fstack-usage',*['-I'+str(d) for d in includes],'-c',src,'-o',obj]);text=obj.with_suffix('.su').read_text();maximum=max(int(r.split('\t')[1]) for r in text.splitlines());total+=maximum;frames[str(src)]={'file_maximum':maximum,'frames':text}
  assert total<16384
  stack.append({'optimization':opt,'conservative_sum_of_file_maxima':total,'frames':frames})
verify();assert pins=={str(f):sha(f) for f in inputs}
result={'passed':True,'scope':'Exact registered CityHall SOURCE canonical unscaled geometry; actual historical TexOpt+Trick inputs retained. No material, actor, GPU or world authority.','source_sha256':{str(f):hashlib.sha256(b).hexdigest() for f,b in frozen.items()},'input_sha256':pins,'modes':modes,'stack_usage':stack,'preparation_reserve':16384,'old_cpu_peak':row['cpu_peak'],'old_full_fixture_packet_sha256':row['packet_sha256'],'old_packet_comparison':'Complete packet SHA equality with frozen469 packet independently qualified by unchanged original delta consumer; native sweep not rerun.','actor_owner_qualified':False,'future_actor_or_resource_allowance_only':semantic['external_headroom'],'source_materials_available':False,'render_ready':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False,'process_rss_claimed':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
