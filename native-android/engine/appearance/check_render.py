#!/usr/bin/env python3
"""Qualify only the new GEO/CPU-render bridge; reuse prior assembly evidence.

Real model streams are compared with independently executed original source.
No Android execution, GPU rendering or complete-body acceptance is inferred.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,os,struct,subprocess,tempfile,zlib
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def sha(raw):return hashlib.sha256(raw).hexdigest()
asset=module('appearance_render_assets',NATIVE/'engine/assets/check.py')
original=module('appearance_render_original',NATIVE/'tools/material_fixture/original_delta_check.py')
class Requirements(C.Structure):_fields_=[('canonical_bytes',C.c_size_t),('workspace_bytes',C.c_size_t),('vertices',C.c_uint32),('indices',C.c_uint32),('bones',C.c_uint32),('materials',C.c_uint32),('rigid',C.c_uint32)]
class Mesh(C.Structure):_fields_=[('bytes',C.c_void_p),('byte_count',C.c_size_t),('vertices',C.c_uint32),('indices',C.c_uint32),('bones',C.c_uint32),('vo',C.c_uint32),('io',C.c_uint32),('bo',C.c_uint32)]
def configure(lib):
 lib.coh_asset_geo_workspace.argtypes=[asset.Bytes,C.POINTER(C.c_size_t)]
 lib.coh_asset_geo_open.argtypes=[asset.Bytes,C.c_void_p,C.c_size_t,C.c_uint32,C.POINTER(asset.Geo)]
 lib.coh_appearance_mesh_requirements.argtypes=[C.POINTER(asset.Geo),C.c_uint32,C.c_uint32,C.POINTER(Requirements)]
 lib.coh_appearance_mesh_build.argtypes=[C.POINTER(asset.Geo),C.c_uint32,C.c_uint32,C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.POINTER(Mesh),C.POINTER(Requirements)]
def oracle(lib,ref,corpus,pins):
 files=[];model_count=scalar_count=0
 for path in sorted(corpus.glob('*.geo')):
  if path.name in ('scalel.geo','scales.geo'):continue # morphology-only records, not render meshes
  if path.name not in pins:continue
  raw=path.read_bytes();pin=pins[path.name];assert sha(raw)==pin['sha256'] and len(raw)==pin['size']
  source=C.create_string_buffer(raw);needed=C.c_size_t();assert lib.coh_asset_geo_workspace(asset.Bytes(C.addressof(source),len(raw)),C.byref(needed))==0
  header=C.create_string_buffer(needed.value);geo=asset.Geo();assert lib.coh_asset_geo_open(asset.Bytes(C.addressof(source),len(raw)),header,len(header),4096,C.byref(geo))==0
  version,payload,models=asset.reference(raw)
  # Independently locate bone table offsets; reference() deliberately omits it.
  bias,n=struct.unpack_from('<II',raw)
  start,packed=(8,bias-4) if n else (16,bias-12)
  h=zlib.decompress(raw[start:start+packed]);fields=5 if 2<=version<=6 else 4
  sizes=struct.unpack_from('<'+'I'*fields,h);record_pos=fields*4+sum(sizes[1:])+140
  file_models=[]
  for index,model in enumerate(models):
   size=216 if version<3 else struct.unpack_from('<I',h,record_pos)[0]
   bone_offset=struct.unpack_from('<I',h,record_pos+(20 if version<3 else 12))[0];record_pos+=size
   req=Requirements();socket=0;assert lib.coh_appearance_mesh_requirements(C.byref(geo),index,socket,C.byref(req))==0
   scratch=C.create_string_buffer(req.workspace_bytes);dest=C.create_string_buffer(req.canonical_bytes);view=Mesh()
   assert lib.coh_appearance_mesh_build(C.byref(geo),index,socket,scratch,len(scratch),dest,len(dest),C.byref(view),None)==0
   canonical=dest.raw;vc,tc=model['vertices'],model['triangles'];assert (vc,tc*3)==(view.vertices,view.indices)
   def stream(channel):
    packed,decoded,offset=model['packs'][channel];s=payload[offset:offset+(packed or decoded)];s=zlib.decompress(s) if packed else s;assert len(s)==decoded;return s
   for channel,count,stride,offset in [(0,tc,3,None),(1,vc,3,0),(2,vc,3,12),(3,vc,2,24)]:
    encoded=stream(channel);source_stream=C.create_string_buffer(encoded+b'\0'*16);result=C.create_string_buffer(count*stride*4)
    assert ref.uncompressDeltas(result,source_stream,stride,count,int(channel==0))==len(encoded)
    if channel==3:
     values=(C.c_float*(vc*2)).from_buffer_copy(result.raw);upload=(C.c_float*(vc*2))();ref.original_gpu_uvs(values,vc,upload);gold=bytes(upload)
    else:gold=result.raw
    actual=canonical[view.io:view.io+tc*12] if channel==0 else b''.join(canonical[64+i*48+offset:64+i*48+offset+stride*4] for i in range(vc))
    assert actual==gold,(path.name,model['name'],channel);scalar_count+=count*stride
   if bone_offset:
    count=struct.unpack_from('<I',payload,bone_offset)[0];bones=struct.unpack_from('<'+'I'*count,payload,bone_offset+4)
    weights,slots=stream(5),stream(6);wf=(C.c_float*(vc*2))();indices=(C.c_uint32*(vc*2))();wb=C.create_string_buffer(weights);sb=C.create_string_buffer(slots)
    assert ref.original_weight_slots(wb,sb,vc,count,wf,indices)==0
    assert bytes(wf)==b''.join(canonical[64+i*48+32:64+i*48+40] for i in range(vc))
    assert bytes(indices)==b''.join(canonical[64+i*48+40:64+i*48+48] for i in range(vc));scalar_count+=vc*4
   else:
    bones=(socket,)
    assert not stream(5) and not stream(6)
    assert all(canonical[64+i*48+32:64+i*48+48]==struct.pack('<ffII',1.,0.,0,0) for i in range(vc))
   assert struct.unpack_from('<'+'I'*view.bones,canonical,view.bo)==bones
   file_models.append({'model':model['name'],'canonical_sha256':sha(canonical),'vertices':vc,'triangles':tc,'palette':list(bones),'source_channels_byte_exact':True})
  files.append({'file':path.name,'sha256':sha(raw),'version':version,'models':file_models});model_count+=len(file_models)
 return {'passed':True,'models':model_count,'compared_scalar_elements':scalar_count,'original_delta_function_sha256_lf':original.FUNCTION_SHA,'original_source_sha256_lf':original.SOURCE_SHA,'source_weight_sha256_lf':original.WEIGHT_SOURCE_SHA,'source_palette_sha256_lf':original.PALETTE_SOURCE_SHA,'files':files,'original_gpu_execution':False,'original_full_client_execution':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corpus-root',type=Path,required=True);p.add_argument('--wretch-corpus',type=Path);p.add_argument('--families-root',type=Path);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--ndk',type=Path);p.add_argument('--sanitize',action='store_true');p.add_argument('--gpu',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 base=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fno-fast-math','-I',str(NATIVE/'include')]
 sources=[HERE/n for n in ['coh_appearance.c','coh_appearance_adapters.c','coh_appearance_mesh.c','coh_appearance_render.c']]+[NATIVE/p for p in ['character/coh_character.c','engine/assets/coh_asset_geo.c','engine/assets/coh_asset_loader.c','src/coh_assets.c','src/coh_dds.c','material-probe/app/src/main/cpp/coh_mesh.c']]
 source_root=a.source_root/'upstream/ouroboros';source=source_root/'Common/seq/anim.c'
 for path,pinned in [('Game/src/render/model_cache.c',original.WEIGHT_SOURCE_SHA),('Game/src/render/thread/rt_bonedmodel.c',original.PALETTE_SOURCE_SHA)]:assert sha((source_root/path).read_bytes().replace(b'\r\n',b'\n'))==pinned
 pins={r['file_name']:r for r in json.loads((HERE/'corpus-pins.json').read_text())['records']}
 with tempfile.TemporaryDirectory(prefix='coh-appearance-render-') as td:
  arguments=[str(a.corpus_root)]+([str(a.families_root)] if a.families_root else [])
  t=Path(td);exe=t/'host';subprocess.run(['cc',*base,'-O2',*map(str,sources),str(HERE/'tests/render.c'),'-lz','-lm','-o',str(exe)],check=True);host=json.loads(subprocess.check_output([str(exe),*arguments],text=True))
  shared=t/'render.so';subprocess.run(['cc',*base,'-O0','-shared','-fPIC',*map(str,sources),str(NATIVE/'engine/renderer/coh_renderer.c'),'-lz','-lm','-o',str(shared)],check=True);lib=C.CDLL(str(shared));configure(lib)
  (t/'original.c').write_bytes(original.original_c(source));subprocess.run(['cc','-std=c11','-O0','-fno-strict-aliasing','-shared','-fPIC',str(t/'original.c'),'-o',str(t/'original.so')],check=True);ref=C.CDLL(str(t/'original.so'))
  ref.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int];ref.original_gpu_uvs.argtypes=[C.c_void_p,C.c_int,C.c_void_p];ref.original_weight_slots.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_void_p]
  source_result=oracle(lib,ref,a.corpus_root,pins);wretch={'run':False}
  if a.wretch_corpus:
   wpins={r['file_name']:r for r in json.loads((NATIVE/'tools/character_fixture/pins.json').read_text())['records']};wretch=oracle(lib,ref,a.wretch_corpus,wpins);wretch['run']=True
  gpu_result={'run':False}
  if a.gpu:
   gpu_test=module('appearance_part_gpu_proof',HERE/'tests/render_gpu.py');gpu_result=gpu_test.prove(lib,__import__(__name__),a.corpus_root,a.families_root)
  sanitized={'run':False}
  if a.sanitize:
   san=t/'san';subprocess.run(['cc',*base,'-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined',*map(str,sources),str(HERE/'tests/render.c'),'-lz','-lm','-o',str(san)],check=True);env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');sanitized={'run':True,'asan':True,'ubsan':True,'leak_detection':False,'result':json.loads(subprocess.check_output([str(san),*arguments],text=True,env=env))}
  android={'built':False}
  if a.ndk:
   compiler=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang';target=t/'libcoh_appearance_render.so';subprocess.run([str(compiler),*base,'-O2','-shared','-fPIC','-Wl,--no-undefined',*map(str,sources),'-lz','-lm','-o',str(target)],check=True);android={'built':True,'abi':'arm64-v8a','api':26,'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()),'undefined_symbols_rejected':True,'executed':False}
 family_inputs={name+'-jump_n_smash.bin':sha((a.families_root/(name+'-jump_n_smash.bin')).read_bytes()) for name in ['male','fem','huge']} if a.families_root else {}
 report={'schema':'coh-appearance-render-bridge-v1','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=HERE).strip(),'original_source_commit':json.loads((HERE/'corpus-pins.json').read_text())['source_commit'],'implemented':True,'host_qualified':True,'arm64_built':android['built'],'gpu_qualified':False,'partial_host_gpu_qualified':gpu_result.get('passed',False),'emulator_qualified':False,'physical_qualified':False,'full_gate31_accepted':False,'host':host,'source_oracle':source_result,'wretch_converter_regression':wretch,'neutral_rig_sha256':family_inputs,'neutral_rig_provenance':'sequencer showcase-build/families; sequencer source qualification owns raw animation, hierarchy and blend comparisons','partial_gpu':gpu_result,'sanitizers':sanitized,'android':android,'code_sha256':{str(s.relative_to(NATIVE)):sha(s.read_bytes()) for s in sources},'limitations':['Complete Male/Female/Huge costume texture/morph/GPU closure remains pending.','Authentic neutral source rig/mesh/socket compatibility and host GPU part transforms are partial part evidence; not a new complete actor, original material or body morphology.','The CPU render bridge has no GPU skinning or Android execution qualification.','Real-time caller allocations, frame rate and Android execution are not measured here.','No accepted Session Client, live session, JNI or shared renderer source changed.']}
 report['qualification_tool_sha256']={str(path.relative_to(NATIVE)):sha(path.read_bytes()) for path in [HERE/'check_render.py',HERE/'tests/render.c',HERE/'tests/render_gpu.py']}
 report['gpu_dependency_sha256']={str((NATIVE/path).relative_to(NATIVE)):sha((NATIVE/path).read_bytes()) for path in ['engine/renderer/coh_renderer.c','engine/renderer/coh_renderer_shaders.h','engine/renderer/tests/gpu_check.py','engine/renderer/tests/oracle.py']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({key:report[key] for key in ['implemented','host_qualified','arm64_built','gpu_qualified','partial_host_gpu_qualified','full_gate31_accepted','host']}))
if __name__=='__main__':main()
