#!/usr/bin/env python3
"""Actual opaque source body→source-header CPU-rigid bridge qualification."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent
p=argparse.ArgumentParser(description=__doc__)
for name in ('capture-directory','body-directory','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--renderer-source-root',type=Path,required=True)
a=p.parse_args();cap=a.capture_directory.resolve();ER=a.renderer_source_root.resolve();EH=ER/'native-android/engine/world-render-adapter'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
sources=[HERE/'coh_source_rigid.c',EH/'coh_wr_rigid.c',EH/'coh_wr_rigid_source.c',ENGINE/'renderer/coh_renderer.c',HERE/'tests/test_source_selection.c',HERE/'coh_source_selection.c',HERE/'coh_resource_join.c',HERE/'coh_resource_index.c',HERE/'coh_resource_geo_source.c',HERE/'coh_catalog_snapshot.c',HERE/'coh_catalog_owner.c',HERE/'coh_scenecatalog.c',ENGINE/'scenegraph/runtime_snapshot.c',ENGINE/'scenegraph/tests/runtime_matrix_bridge.c',ENGINE/'replication/coh_replication.c',ENGINE/'replication/coh_groups.c',ENGINE/'assets/coh_asset_loader.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
deps=sources+[HERE/'coh_source_rigid_internal.h',HERE/'coh_source_rigid.h',HERE/'tests/test_source_rigid.inc',EH/'coh_wr_rigid_internal.h',EH/'coh_wr_rigid.h',EH/'coh_wr_rigid_source.h',EH/'coh_world_render.h',ENGINE/'renderer/coh_renderer.h',ENGINE/'renderer/coh_renderer_shaders.h']+[HERE/n for n in ('coh_source_selection.h','coh_source_selection_profile.inc','coh_resource_join.h','coh_resource_index.h','coh_resource_geo_source.h','coh_catalog_snapshot.h','coh_catalog_owner.h','coh_scenecatalog.h')]+[ENGINE/'scenegraph'/n for n in ('runtime_snapshot.h','runtime_graph.h','coh_scenegraph.c','coh_scenegraph.h')]+[ENGINE/'replication'/n for n in ('coh_replication.h','coh_groups.h')]+[ENGINE/'assets'/n for n in ('coh_asset_loader.h','coh_asset_geo.h')]+[ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',Path(__file__)]
arguments=[cap/n for n in ('catalog.cohcat','runtime.cohrts','resources.cohres','source-identity.json','run-identity.json')]+[cap.parent/'control-fixture.json',cap/'resource-binding.json',cap/'capture-receipt.json',HERE/'evidence/actual-resource-bodies-source-adapter-sealed-38994607354.json',HERE/'evidence/prepared-geo-source-route-final-38994607354.json',a.body_directory]
inputs=[Path(x) for x in arguments[:-1]]+[a.body_directory/'data/object_library/buildings/elements/signs/neon/neon.geo',a.body_directory/'data/object_library/special_buildings/shop_interiors/shop_tailor/shop_tailor.geo']
def label(f):
 return 'coordinator:'+str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else 'renderer:'+str(f.relative_to(ER))
pins={label(f):sha(f) for f in deps};inputpins={str(f):sha(f) for f in inputs}
env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');modes={}
with tempfile.TemporaryDirectory(prefix='coh-source-selection-') as td:
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=Path(td)/mode
  run(['cc','-std=c99','-DCOH_SOURCE_RIGID_BRIDGE_TEST','-ffp-contract=off','-pthread','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),'-I'+str(EH.parent/'scenecatalog'),*flags,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lcrypto','-lz','-lm','-o',binary])
  result=json.loads(run([binary,*arguments],env=env));assert result['bridge_completions']==2
  modes[mode]={'result':result,'binary_sha256':sha(binary)}
assert pins=={label(f):sha(f) for f in deps}
assert inputpins=={str(f):sha(f) for f in inputs}
assert all(x['result']==modes['release']['result'] for x in modes.values())
result={'passed':True,'source_sha256':pins,'input_sha256':inputpins,'modes':modes,'scope':'Actual opaque source-body owner to source-header rigid CPU preparation with explicit fixture material callbacks; no CLIENT/live/world authority','evidence_kind':'PROCEDURAL_EXACT_COLD_CAPTURE','direct_open_observed':False,'assets_admitted':False,'world_authority':False,'android_executed':False,'allocation_balance_controls':True,'leak_sanitizer':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'modes':modes}))
