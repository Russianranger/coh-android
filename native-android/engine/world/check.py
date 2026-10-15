#!/usr/bin/env python3
"""Qualify new source map transforms, bounded residency and expanded collision."""
from pathlib import Path
import argparse, hashlib, json, os, struct, subprocess, tempfile
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[1]
def run(command,env=None):
 p=subprocess.run(list(map(str,command)),capture_output=True,text=True,env=env,timeout=120)
 if p.returncode:raise RuntimeError(' '.join(map(str,command))+'\n'+p.stdout+p.stderr)
 return p.stdout

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');p.add_argument('--ndk',type=Path);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);fixture=json.loads((a.prepared/'map-fixture.json').read_text());walk=json.loads((a.prepared/'walkable-fixture.json').read_text());common=['cc','-std=c11','-O2','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Werror','-pedantic','-I',str(NATIVE/'include')];sources=[HERE/'coh_world_stream.c',NATIVE/'engine/assets/coh_asset_loader.c',NATIVE/'src/coh_assets.c',NATIVE/'src/coh_dds.c'];results={}
 with tempfile.TemporaryDirectory(prefix='coh-map-check-') as temp:
  t=Path(temp);exe=t/'world';matrix=t/'world-matrices.json';run([*common,HERE/'test_world.c',*sources,'-lz','-lm','-o',exe]);results['host']=json.loads(run([exe,a.prepared/'map.bin',matrix]));native=json.loads(matrix.read_text());original=walk['source_world_matrices'];comparisons=0
  for n,g in zip(native['nodes'],original):
   assert all(struct.pack('<f',x)==struct.pack('<f',y) for x,y in zip(n['world'],g));comparisons+=12
   index=n['id'];tint=None
   while index!=0xffffffff:
    if fixture['nodes'][index]['tint'] is not None:tint=fixture['nodes'][index]['tint'];break
    index=fixture['nodes'][index]['parent']
   expected=[struct.unpack('<f',struct.pack('<f',x*struct.unpack('<f',struct.pack('<f',1./255))[0]))[0] for x in (tint or [255,255,255,0,0,0])];assert all(struct.pack('<f',x)==struct.pack('<f',y) for x,y in zip(n['tint'],expected))
  results['original_transform_parity']={'passed':True,'nodes':len(original),'components':comparisons,'maximum_absolute_error':0.,'byte_exact_including_signed_zero':True,'source_math_pins':walk['source_math_pins']}
  # Every expanded collision triangle must have exactly the same baked float
  # position bytes as the corresponding source material mesh index stream.
  b=(a.prepared/'walkable.bin').read_bytes();partcount,texcount,tricount=struct.unpack_from('<3I',b,16);tri_offset=struct.unpack_from('<I',b,52)[0];triangle_cursor=0;position_components=0
  for i in range(partcount):
   off,size=struct.unpack_from('<2I',b,128+i*96);mesh=b[off:off+size];indexcount=struct.unpack_from('<I',mesh,20)[0];io=struct.unpack_from('<I',mesh,36)[0];indices=struct.unpack_from('<'+'I'*indexcount,mesh,io)
   for tri in range(0,indexcount,3):
    expected=b''.join(mesh[64+indices[tri+j]*48:64+indices[tri+j]*48+12] for j in range(3));actual=b[tri_offset+triangle_cursor*40:tri_offset+triangle_cursor*40+36];assert expected==actual;position_components+=9;triangle_cursor+=1
  assert triangle_cursor==tricount==2304;results['render_collision_parity']={'passed':True,'triangles':tricount,'binary32_position_components':position_components,'byte_exact':True}
  centers=t/'benches.txt';centers.write_text(''.join(' '.join(str(v) for v in [x['world_center'][0],x['world_center'][2],x['world_center'][2]-2,(-1 if x['world'][8]>0 else 1)])+'\n' for x in fixture['instances'] if fixture['endpoints'][x['endpoint']]['geometry']!=1))
  walk_sources=[NATIVE/'walk'/s for s in ['coh_walk.c','source_world.c','source_ctri.c','source_tritri.c']]+[NATIVE/'motion/coh_motion.c',NATIVE/'walkable/coh_walkable_scene.c',NATIVE/'world-probe/app/src/main/cpp/coh_world_scene.c',NATIVE/'material-probe/app/src/main/cpp/coh_mesh.c',NATIVE/'world/coh_world.c',NATIVE/'src/coh_assets.c']
  wc=[*[c for c in common if c!='-pedantic'],'-Wno-unused-variable','-Wno-unused-parameter','-Wno-unused-but-set-variable','-Wno-unused-function','-Wno-misleading-indentation','-fno-strict-aliasing','-I',str(NATIVE/'world-probe/app/src/main/cpp'),'-I',str(NATIVE/'material-probe/app/src/main/cpp'),'-I',str(NATIVE/'walk'),'-I',str(NATIVE/'world')];we=t/'walk';run([*wc,HERE/'test_walkable.c',*walk_sources,'-lm','-o',we]);results['expanded_walk']=json.loads(run([we,a.prepared/'walkable.bin',centers]));results['sanitizers']={'run':False}
  if a.sanitize:
   env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'};sx=t/'world-san';run([*common,'-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',HERE/'test_world.c',*sources,'-lz','-lm','-o',sx]);san=json.loads(run([sx,a.prepared/'map.bin',matrix],env));sw=t/'walk-san';run([*wc,'-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',HERE/'test_walkable.c',*walk_sources,'-lm','-o',sw]);walksan=json.loads(run([sw,a.prepared/'walkable.bin',centers],env));results['sanitizers']={'run':True,'asan':True,'ubsan':True,'lsan':False,'lsan_reason':'Existing execution environment /proc task inspection limitation; counted module heap/teardown is independently checked.','map':san,'expanded_walk':walksan}
  if a.ndk:
   clang=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang';obj=t/'world.o';run([clang,'-std=c11','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-fPIC','-I',NATIVE/'include','-c',HERE/'coh_world_stream.c','-o',obj]);results['android_arm64_compile']={'passed':True,'object_bytes':obj.stat().st_size,'object_sha256':sha(obj),'execution':False}
 report={'schema':'coh-gate23-world-qualification-v1','passed':True,'host_qualified':True,'android_execution_qualified':False,'physical_qualified':False,'full_atlas_loaded':False,'new_source_files':{str(x.relative_to(NATIVE)):sha(x) for x in [HERE/'coh_world_stream.h',HERE/'coh_world_stream.c',HERE/'test_world.c',HERE/'test_walkable.c',Path(__file__),NATIVE/'tools/map_fixture/prepare.py',NATIVE/'tools/map_fixture/walkable.py']},'bundle':fixture['bundle'],'expanded_walkable':walk['assets'],'results':results,'scope':fixture['scope']};a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'host':results['host'],'original_transform_components':comparisons,'render_collision_components':position_components,'expanded_walk':results['expanded_walk'],'sanitizers':results['sanitizers']['run']}))
if __name__=='__main__':main()
