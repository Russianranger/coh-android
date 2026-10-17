#!/usr/bin/env python3
"""Actual opaque source-body fixed v2/v3/v4 routes and existing bridge regressions."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,struct,subprocess,tempfile,zlib
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
sources=[HERE/'coh_source_rigid_legacy_formats.c',EH/'coh_wr_rigid_legacy_formats.c',HERE/'coh_source_rigid.c',HERE/'coh_source_rigid_versions.c',EH/'coh_wr_rigid_v7.c',EH/'coh_wr_rigid_v5.c',EH/'coh_wr_rigid.c',EH/'coh_wr_rigid_source.c',ENGINE/'renderer/coh_renderer.c',HERE/'tests/test_source_selection.c',HERE/'coh_source_selection.c',HERE/'coh_resource_join.c',HERE/'coh_resource_index.c',HERE/'coh_resource_geo_source.c',HERE/'coh_catalog_snapshot.c',HERE/'coh_catalog_owner.c',HERE/'coh_scenecatalog.c',ENGINE/'scenegraph/runtime_snapshot.c',ENGINE/'scenegraph/tests/runtime_matrix_bridge.c',ENGINE/'replication/coh_replication.c',ENGINE/'replication/coh_groups.c',ENGINE/'assets/coh_asset_loader.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
deps=sources+[HERE/'coh_source_rigid_legacy_formats.h',HERE/'tests/test_source_rigid_legacy.inc',HERE/'tests/source_rigid_legacy_routes.inc',HERE/'tests/source_rigid_legacy_routes.json',EH/'coh_wr_rigid_legacy_formats.h',HERE/'coh_source_rigid_versions.h',HERE/'tests/test_source_rigid_versions.inc',EH/'coh_wr_rigid_v7.h',EH/'coh_wr_rigid_v5.h',HERE/'coh_source_rigid_internal.h',HERE/'coh_source_rigid.h',HERE/'tests/test_source_rigid.inc',EH/'coh_wr_rigid_internal.h',EH/'coh_wr_rigid.h',EH/'coh_wr_rigid_source.h',EH/'coh_world_render.h',ENGINE/'renderer/coh_renderer.h',ENGINE/'renderer/coh_renderer_shaders.h']+[HERE/n for n in ('coh_source_selection.h','coh_source_selection_profile.inc','coh_resource_join.h','coh_resource_index.h','coh_resource_geo_source.h','coh_catalog_snapshot.h','coh_catalog_owner.h','coh_scenecatalog.h')]+[ENGINE/'scenegraph'/n for n in ('runtime_snapshot.h','runtime_graph.h','coh_scenegraph.c','coh_scenegraph.h')]+[ENGINE/'replication'/n for n in ('coh_replication.h','coh_groups.h')]+[ENGINE/'assets'/n for n in ('coh_asset_loader.h','coh_asset_geo.h')]+[ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',Path(__file__)]
arguments=[cap/n for n in ('catalog.cohcat','runtime.cohrts','resources.cohres','source-identity.json','run-identity.json')]+[cap.parent/'control-fixture.json',cap/'resource-binding.json',cap/'capture-receipt.json',HERE/'evidence/actual-resource-bodies-source-adapter-sealed-38994607354.json',HERE/'evidence/prepared-geo-source-route-final-38994607354.json',a.body_directory]
inputs=[Path(x) for x in arguments[:-1]]+[a.body_directory/'data/object_library/buildings/elements/signs/neon/neon.geo',a.body_directory/'data/object_library/special_buildings/shop_interiors/shop_tailor/shop_tailor.geo']
inputs += [a.body_directory/'data/object_library/buildings/elements/signs/special_signs/chaser_sign_4to1/chaser_sign_4to1.geo',a.body_directory/'data/object_library/villain_lairs/tech/structure/platforms/platforms.geo']
lowlevel=[EH/'qualification/rigid-v234-20261017/regressions'/name for name in ('host.json','v7-regression.json','source08-regression.json','default0-regression.json','default8-regression.json')]
for receipt in lowlevel:
 d=json.loads(receipt.read_text());assert d['passed']
 for name,expected in d['source_sha256'].items():assert sha(ER/name)==expected,(receipt,name)
inputs += lowlevel
proof=EH/'qualification/rigid-v234-20261017/all35-host.json'
proof_data=json.loads(proof.read_text());assert proof_data['passed'] and len(proof_data['cases'])==35
for name,expected in proof_data['source_sha256'].items():assert sha(ER/name)==expected,(name,expected)
routes=json.loads((HERE/'tests/source_rigid_legacy_routes.json').read_text());assert len(routes)==36 and len({r['path'] for r in routes})==10
for route in routes:
 matches=[c for c in proof_data['cases'] if c['fixture']['asset_path']==route['path'] and c['fixture']['model']==route['model']]
 assert len(matches)==1
 case=matches[0];fixture=case['fixture'];assert route['version']==fixture['version'] and route['packet_sha']==case['packet_sha256'] and route['packet_bytes']==case['packet_bytes']
 observations=[o for o in fixture['source_observations'] if o['resource_ordinal']==route['ordinal']];assert len(observations)==1 and observations[0]['record_sha256']==route['record_sha'] and observations[0]['texture_partitions']==route['materials']
 assert sha(a.body_directory/route['path'])==fixture['sha256']
inputs += [proof]+[a.body_directory/path for path in sorted({r['path'] for r in routes})]
# Independent unchanged producer-consumer delta oracle for the two exact bodies.
# Native views are compared to these fixed expectations in the integrated test.
original_path=ROOT/'native-android/tools/material_fixture/original_delta_check.py'
original_source=ROOT/'upstream/ouroboros/Common/seq/anim.c'
deps += [original_path,original_source]
spec=importlib.util.spec_from_file_location('version_original_delta',original_path);original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
packets={}
with tempfile.TemporaryDirectory(prefix='coh-version-delta-') as tempdir:
 temp=Path(tempdir);code=original.original_c(original_source);(temp/'delta.c').write_bytes(code)
 run(['cc','-std=c11','-O0','-fno-strict-aliasing','-shared','-fPIC',temp/'delta.c','-o',temp/'delta.so'])
 lib=C.CDLL(str(temp/'delta.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
 fixtures=[('data/object_library/buildings/elements/signs/special_signs/chaser_sign_4to1/chaser_sign_4to1.geo','66742a3b485b7772e6ab20a4edc750a7e46d99891e35473bfc587a3b0e9fd374',7,1,4,2,'3fb965f9418df30204ce540efbe70d2263bba4e22cfd8faec14b9eaf728fd1f5'),('data/object_library/villain_lairs/tech/structure/platforms/platforms.geo','e1462116a522be747e72ddaccf353c25c17d8d510246704563affa54695ec6c5',5,13,10,4,'93d7d45c4519de22024d1c36f140a444446c5df47096e076c399e8b77e0dee08')]
 for path,expected_body,version,row,vertices,triangles,expected_packet in fixtures:
  raw=(a.body_directory/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected_body;bias,unused,v,n=struct.unpack_from('<4I',raw);assert unused==0 and v==version;header=zlib.decompress(raw[16:bias+4]);assert len(header)==n;payload=raw[bias+4:];t,nn,mn=struct.unpack_from('<3I',header,4);fields=20 if version==5 else 16;lod=struct.unpack_from('<I',header,16)[0] if version==5 else 0;materials=header[fields+t+nn:fields+t+nn+mn];at=fields+t+nn+mn+lod+140
  for unusedrow in range(row):at+=struct.unpack_from('<I',header,at)[0]
  size=struct.unpack_from('<I',header,at)[0];record=header[at:at+size];assert struct.unpack_from('<2I',record,16)==(vertices,triangles);decoded=[]
  for channel in range(4):
   packed,unpacked,off=struct.unpack_from('<3I',record,104+channel*12);encoded=payload[off:off+(packed or unpacked)];encoded=zlib.decompress(encoded) if packed else encoded;assert len(encoded)==unpacked;count=triangles if channel==0 else vertices;stride=2 if channel==3 else 3;output=C.create_string_buffer(count*stride*4);inputdata=C.create_string_buffer(encoded+b'\0'*16);assert lib.uncompressDeltas(output,inputdata,stride,count,int(channel==0))==len(encoded);decoded.append(struct.unpack('<'+('I' if channel==0 else 'f')*(count*stride),output.raw))
  packet=bytearray();parts=struct.unpack_from('<I',record,8)[0];offset=struct.unpack_from('<I',record,24)[0];first=0
  for part in range(parts):
   texid,count=struct.unpack_from('<2H',materials,offset+part*4)
   for vertex in range(vertices):
    u,v=decoded[3][vertex*2:vertex*2+2];v=struct.unpack('<f',struct.pack('<f',1-v))[0];packet+=struct.pack('<14f',*decoded[1][vertex*3:vertex*3+3],*decoded[2][vertex*3:vertex*3+3],u,v,u,v,1,1,1,1)
   indices=decoded[0][first*3:(first+count)*3];assert all(i<vertices for i in indices);packet+=struct.pack('<'+'I'*len(indices),*indices);first+=count
  assert first==triangles and hashlib.sha256(packet).hexdigest()==expected_packet;packets[str(version)]={'body_sha256':expected_body,'packet_sha256':expected_packet,'packet_bytes':len(packet),'original_delta_scalars':vertices*8+triangles*3}
 original_proof={'unchanged_function_sha256_lf':original.FUNCTION_SHA,'generated_oracle_sha256':hashlib.sha256(code).hexdigest(),'packets':packets,'fixture_materials_only':True}
def label(f):
 return 'coordinator:'+str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else 'renderer:'+str(f.relative_to(ER))
pins={label(f):sha(f) for f in deps};inputpins={str(f):sha(f) for f in inputs}
env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');modes={}
with tempfile.TemporaryDirectory(prefix='coh-source-selection-') as td:
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=Path(td)/mode
  run(['cc','-std=c99','-DCOH_SOURCE_RIGID_LEGACY_TEST','-DCOH_SOURCE_RIGID_BRIDGE_TEST','-DCOH_SOURCE_RIGID_VERSIONS_TEST','-ffp-contract=off','-pthread','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),'-I'+str(EH.parent/'scenecatalog'),*flags,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lcrypto','-lz','-lm','-o',binary])
  result=json.loads(run([binary,*arguments],env=env));assert result['bridge_completions']==2 and result['version_completions']==2 and result['legacy_completions']==36 and result['legacy_files']==10 and result['procedural_file_bodies_checked']==14
  modes[mode]={'result':result,'binary_sha256':sha(binary)}
assert pins=={label(f):sha(f) for f in deps}
assert inputpins=={str(f):sha(f) for f in inputs}
assert all(x['result']==modes['release']['result'] for x in modes.values())
result={'passed':True,'source_sha256':pins,'input_sha256':inputpins,'modes':modes,'scope':'Actual opaque sourceBody to separate fixed v2/v3/v4 factories for all35 root pairs and36 owner routes, plus exactv7/v5 and default0/8 regressions, fixture materials only; no CLIENT/live/world authority','evidence_kind':'PROCEDURAL_EXACT_COLD_CAPTURE','direct_open_observed':False,'assets_admitted':False,'world_authority':False,'android_executed':False,'original_delta':original_proof,'source_body_legacy_entries_added':True,'legacy_unique_pairs':35,'legacy_owner_routes':36,'legacy_unique_files':10,'low_level_packet_dependency_sha256':sha(proof),'inherited_body_peak_is_not_bridge_peak':True,'allocation_balance_controls':True,'leak_sanitizer':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'modes':modes}))
