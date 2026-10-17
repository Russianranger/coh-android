#!/usr/bin/env python3
"""Actual opaque source-body supplemental special-channel qualification."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent
p=argparse.ArgumentParser(description=__doc__)
for name in ('capture-directory','body-directory','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--renderer-source-root',type=Path,required=True)
p.add_argument('--root-coverage',type=Path,required=True)
a=p.parse_args();cap=a.capture_directory.resolve();ER=a.renderer_source_root.resolve();EH=ER/'native-android/engine/world-render-adapter'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
sources=[HERE/'coh_source_special.c',HERE/'coh_source_rigid.c',EH/'coh_wr_rigid.c',EH/'coh_wr_rigid_source.c',ENGINE/'renderer/coh_renderer.c',HERE/'tests/test_source_selection.c',HERE/'coh_source_selection.c',HERE/'coh_resource_join.c',HERE/'coh_resource_index.c',HERE/'coh_resource_geo_source.c',HERE/'coh_catalog_snapshot.c',HERE/'coh_catalog_owner.c',HERE/'coh_scenecatalog.c',ENGINE/'scenegraph/runtime_snapshot.c',ENGINE/'scenegraph/tests/runtime_matrix_bridge.c',ENGINE/'replication/coh_replication.c',ENGINE/'replication/coh_groups.c',ENGINE/'assets/coh_asset_loader.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
deps=sources+[HERE/'tests/test_source_special_grammar.c',HERE/'coh_source_special.h',HERE/'tests/test_source_special.inc',HERE/'tests/source_special_routes.inc',HERE/'tests/source_special_routes.json',HERE/'coh_source_rigid_internal.h',HERE/'coh_source_rigid.h',HERE/'tests/test_source_rigid.inc',EH/'coh_wr_rigid_internal.h',EH/'coh_wr_rigid.h',EH/'coh_wr_rigid_source.h',EH/'coh_world_render.h',ENGINE/'renderer/coh_renderer.h',ENGINE/'renderer/coh_renderer_shaders.h']+[HERE/n for n in ('coh_source_selection.h','coh_source_selection_profile.inc','coh_resource_join.h','coh_resource_index.h','coh_resource_geo_source.h','coh_catalog_snapshot.h','coh_catalog_owner.h','coh_scenecatalog.h')]+[ENGINE/'scenegraph'/n for n in ('runtime_snapshot.h','runtime_graph.h','coh_scenegraph.c','coh_scenegraph.h')]+[ENGINE/'replication'/n for n in ('coh_replication.h','coh_groups.h')]+[ENGINE/'assets'/n for n in ('coh_asset_loader.h','coh_asset_geo.h')]+[ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',Path(__file__)]
arguments=[cap/n for n in ('catalog.cohcat','runtime.cohrts','resources.cohres','source-identity.json','run-identity.json')]+[cap.parent/'control-fixture.json',cap/'resource-binding.json',cap/'capture-receipt.json',HERE/'evidence/actual-resource-bodies-source-adapter-sealed-38994607354.json',HERE/'evidence/prepared-geo-source-route-final-38994607354.json',a.body_directory]
inputs=[Path(x) for x in arguments[:-1]]+[a.body_directory/'data/object_library/buildings/elements/signs/neon/neon.geo',a.body_directory/'data/object_library/special_buildings/shop_interiors/shop_tailor/shop_tailor.geo']
# Independently replay unchanged original delta function over each actual planar
# reflection stream. AltPivotInfo active Mat4s are exact source payload copies.
import ctypes as C,importlib.util,struct,zlib
routes=json.loads((HERE/'tests/source_special_routes.json').read_text());assert len(routes)==9
original_path=ROOT/'native-android/tools/material_fixture/original_delta_check.py';original_source=ROOT/'upstream/ouroboros/Common/seq/anim.c'
deps += [HERE/'inspect_root_partitions.py',original_path,original_source,ROOT/'upstream/ouroboros/Common/seq/anim.h',ROOT/'upstream/ouroboros/Game/src/render/model_cache.c',ROOT/'upstream/ouroboros/Game/src/graphics/groupdrawinline.c',ROOT/'upstream/ouroboros/Game/src/render/rendertree.c',ROOT/'upstream/ouroboros/Game/src/graphics/FX/fx.c',ROOT/'upstream/ouroboros/Game/src/render/rendershadow.c']
spec=importlib.util.spec_from_file_location('special_original',original_path);original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original);oracle=[]
with tempfile.TemporaryDirectory(prefix='coh-special-oracle-') as td:
 temp=Path(td);code=original.original_c(original_source);(temp/'o.c').write_bytes(code);run(['cc','-shared','-fPIC','-O0',temp/'o.c','-o',temp/'o.so']);lib=C.CDLL(str(temp/'o.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
 for route in routes:
  path=a.body_directory/route['path'];raw=path.read_bytes();assert sha(path)==route['body_sha256'];inputs.append(path);bias,n=struct.unpack_from('<2I',raw);version=0 if n else struct.unpack_from('<I',raw,8)[0];header=zlib.decompress(raw[8 if version==0 else 16:bias+4]);payload=raw[bias+(8 if version==0 else 4):];at=16+sum(struct.unpack_from('<3I',header,4))+140;found=0
  while at<len(header):
   size=216 if version==0 else struct.unpack_from('<I',header,at)[0];nameoff=struct.unpack_from('<I',header,at+(80 if version==0 else 64))[0];names=16+struct.unpack_from('<I',header,4)[0];name=header[names+nameoff:].split(b'\0',1)[0].decode()
   if name==route['model']:
    found+=1;quads=0 if version==0 else struct.unpack_from('<I',header,at+24)[0];assert quads==route['quads'];points=b''
    if quads:
     packed,n,off=struct.unpack_from('<3I',header,at+216);stream=payload[off:off+(packed or n)];stream=zlib.decompress(stream) if packed else stream;assert len(stream)==n;dst=C.create_string_buffer(quads*48);src=C.create_string_buffer(stream+b'\0'*16);assert lib.uncompressDeltas(dst,src,3,quads*4,0)==len(stream);points=dst.raw
    assert __import__('hashlib').sha256(points).hexdigest()==route['points_sha256'];pivot=struct.unpack_from('<I',header,at+(84 if version==0 else 68))[0];active=b''
    if pivot:
     count=struct.unpack_from('<I',payload,pivot)[0];assert count==route['pivots'] and count<=15 and pivot+724<=len(payload);active=payload[pivot+4:pivot+4+count*48]
    assert __import__('hashlib').sha256(active).hexdigest()==route['pivots_sha256'];oracle.append({'ordinal':route['ordinal'],'reflection_scalars':quads*12,'pivot_scalars':route['pivots']*12,'points_sha256':route['points_sha256'],'pivots_sha256':route['pivots_sha256']})
   at+=size
  assert found==1
ledger_script=HERE/'inspect_root_partitions.py';spec=importlib.util.spec_from_file_location('partitions',ledger_script);partitions=importlib.util.module_from_spec(spec);spec.loader.exec_module(partitions)
ledger=HERE/'evidence/root-model-texture-partitions-38994607354.json';assert json.loads(json.dumps(partitions.build(cap/'resources.cohres',a.root_coverage)))==json.loads(ledger.read_text());inputs += [ledger,a.root_coverage]
with tempfile.TemporaryDirectory(prefix='coh-partition-negative-') as td:
 bad=Path(td)/'bad';bad.write_bytes(b'bad')
 for left,right in ((bad,a.root_coverage),(cap/'resources.cohres',bad)):
  try:partitions.build(left,right)
  except ValueError:pass
  else:raise AssertionError('changed immutable partition input admitted')
def label(f):
 return 'coordinator:'+str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else 'renderer:'+str(f.relative_to(ER))
pins={label(f):sha(f) for f in deps};inputpins={str(f):sha(f) for f in inputs}
env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');modes={};grammar={};stack={}
with tempfile.TemporaryDirectory(prefix='coh-source-selection-') as td:
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=Path(td)/mode
  run(['cc','-std=c99','-DCOH_SOURCE_SPECIAL_TEST','-DCOH_SOURCE_RIGID_BRIDGE_TEST','-ffp-contract=off','-fstack-usage','-pthread','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),'-I'+str(EH.parent/'scenecatalog'),*flags,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lcrypto','-lz','-lm','-o',binary])
  result=json.loads(run([binary,*arguments],env=env));assert result['bridge_completions']==2
  assert result['special_completions']==9
  functions={}
  for su in Path(td).glob(mode+'-*.su'):
   for line in su.read_text().splitlines():
    cols=line.split('\t')
    if len(cols)==3:
     function=cols[0].split(':')[-1]
     if function in ('coh_source_special_prepare','coh_source_body_lease','coh_resource_index_view','coh_resource_source_view','coh_resource_index_owner_sources','coh_source_selection_pin','coh_resource_join_node','coh_asset_geo_stream','inflate_exact','coh_asset_delta_floats','delta','coh_geo_model'):
      functions[function]={'bytes':int(cols[1]),'bound':cols[2]}
  assert 'coh_source_special_prepare' in functions and all(f['bound'] in ('static','dynamic,bounded') for f in functions.values())
  # Sum of all listed frames conservatively covers simultaneous local callchains;
  # external zlib/hash/callback/system stack remains explicitly caller charged.
  native_sum=sum(f['bytes'] for f in functions.values());assert native_sum<16384
  stack[mode]={'frames':functions,'conservative_frame_sum_bytes':native_sum,'preparation_reserve_bytes':16384,'external_stack_in_caller_reservation':True}
  modes[mode]={'result':result,'binary_sha256':sha(binary)}
with tempfile.TemporaryDirectory(prefix='coh-special-grammar-') as td:
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=Path(td)/mode
  run(['cc','-I'+str(ROOT/'native-android/include'),'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off',*flags,HERE/'tests/test_source_special_grammar.c',HERE/'coh_source_special.c',HERE/'coh_resource_geo_source.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c','-lz','-lm','-o',binary])
  grammar[mode]=[json.loads(run([binary,a.body_directory/route['path'],str(0 if route['kinds']==4 else (6 if route['kinds']==2 else 0))],env=env)) for route in (routes[0],routes[6],routes[8])]
assert pins=={label(f):sha(f) for f in deps}
assert inputpins=={str(f):sha(f) for f in inputs}
assert all(x['result']==modes['release']['result'] for x in modes.values())
result={'passed':True,'source_sha256':pins,'input_sha256':inputpins,'modes':modes,'special_original_oracle':oracle,'synthetic_grammar':grammar,'native_stack':stack,'scope':'Actual opaque SourceBody supplemental reflection/pivot/absent-UV source contract; no ordinary CPU, CLIENT or world authority','evidence_kind':'PROCEDURAL_EXACT_COLD_CAPTURE','direct_open_observed':False,'assets_admitted':False,'world_authority':False,'android_executed':False,'allocation_balance_controls':True,'leak_sanitizer':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'modes':modes}))
