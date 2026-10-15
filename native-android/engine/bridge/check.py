#!/usr/bin/env python3
"""New loader→render packet ownership and source-byte adapter qualification.

Uses existing pinned raw corpus. Does not rerun disconnected module suites.
--output is a JSON file; optional --ndk performs a strict direct ARM64 build.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,io,json,os,random,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def run(args,**kw):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout+'\n'+p.stderr)
 return p.stdout
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def corpus_pins(corpus):
 pins={}
 for p in (NATIVE/'tools/world_fixture/pins.json',NATIVE/'tools/walkable_fixture/pins.json'):
  data=json.loads(p.read_text())
  for r in data.get('records',[]):
   name=r.get('file_name')
   if name and (corpus/name).is_file():
    assert sha(corpus/name)==r['sha256'],str(corpus/name)
    assert (corpus/name).stat().st_size==r['size'],str(corpus/name)
    pins[name]={'path':r['name'],'bytes':r['size'],'sha256':r['sha256'],'pin':str(p.relative_to(NATIVE))}
 assert set(pins)==set(('misc.geo','trainstation.geo','bench.texture','sign.texture','white.texture','grey.texture','mono_station_infloor.texture','mono_station_infloor_sml.texture'))
 return pins
def packet_oracle(corpus,temp,source_root):
 asset=module('bridge_asset_reference',NATIVE/'engine/assets/check.py')
 original=module('bridge_original_delta',NATIVE/'tools/material_fixture/original_delta_check.py')
 source=source_root/'upstream/ouroboros/Common/seq/anim.c'
 code=original.original_c(source);(temp/'original.c').write_bytes(code)
 run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC',temp/'original.c','-o',temp/'original.so'])
 ref=C.CDLL(str(temp/'original.so'));ref.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
 compared=0;index_count=0;rows=[]
 for name,model_name,packet in [('misc.geo','modern_bench_2wide__mbench','bench.packet'),('misc.geo','modern_bench_4wide__mbench','bench4.packet'),('trainstation.geo','_trnstation_infloor','floor.packet')]:
  raw=(corpus/name).read_bytes();version,payload,models=asset.reference(raw)
  model=next(x for x in models if x['name']==model_name);vc=model['vertices'];tc=model['triangles'];decoded=[]
  for pack,count,stride,integer in [(0,tc,3,True),(1,vc,3,False),(2,vc,3,False),(3,vc,2,False)]:
   packed,n,off=model['packs'][pack];data=payload[off:off+(packed or n)]
   if packed:
    import zlib
    data=zlib.decompress(data)
   inp=C.create_string_buffer(data+b'\0'*16);out=C.create_string_buffer(count*stride*4)
   assert ref.uncompressDeltas(out,inp,stride,count,int(integer))==len(data)
   decoded.append(list(struct.unpack('<'+('I' if integer else 'f')*(count*stride),out.raw)))
  data=(temp/packet).read_bytes();parts=struct.unpack_from('<I',data)[0];assert parts==len(model['materials']);offset=4;first=0
  for material_name,tris in model['materials']:
   got_vc,got_ic,family=struct.unpack_from('<3I',data,offset);offset+=12;assert (got_vc,got_ic)==(vc,tris*3)
   want_family=1 if material_name=='modern_bench.tga' else 0;assert family==want_family
   scale=8 if material_name=='mono_station_infloor_sml.tga' else 14 if material_name=='mono_station_infloor.tga' else 1
   expected=bytearray()
   for i in range(vc):
    u,v=decoded[3][i*2:i*2+2];v=f32(1-v)
    expected+=struct.pack('<14f',*decoded[1][i*3:i*3+3],*decoded[2][i*3:i*3+3],f32(u*scale),f32(v*scale),u,v,1,1,1,1)
   assert data[offset:offset+len(expected)]==expected,(name,material_name,'position/normal/one-V-flip/source-scale')
   offset+=len(expected);ix=decoded[0][first*3:(first+tris)*3];first+=tris
   want=struct.pack('<'+'I'*len(ix),*ix);assert data[offset:offset+len(want)]==want;offset+=len(want)
   compared+=vc*14;index_count+=len(ix)
  assert offset==len(data)
  rows.append({'source':name,'version':version,'model':model_name,'parts':parts,'packet_sha256':sha(temp/packet)})
 return {'passed':True,'reference':'hash-pinned unchanged original uncompressDeltas plus independent binary32 source V flip/scales and material partitions','original_decoder_source_sha256_lf':original.SOURCE_SHA,'scalar_components_byte_exact':compared,'index_components_byte_exact':index_count,'meshes':rows}
def texture_oracle(corpus,temp):
 from PIL import Image
 rows=[]
 for p in sorted(corpus.glob('*.texture')):
  raw=p.read_bytes();offset=struct.unpack_from('<I',raw)[0];dds=raw[offset:]
  rgba=Image.open(io.BytesIO(dds)).convert('RGBA').tobytes();got=(temp/(p.name+'.rgba')).read_bytes();assert got==rgba,p.name
  rows.append({'source':p.name,'pixels':len(rgba)//4,'rgba_sha256':hashlib.sha256(got).hexdigest(),'pillow_byte_exact':True})
 return {'passed':True,'textures':rows,'pixels':sum(x['pixels'] for x in rows)}
class Bytes(C.Structure):_fields_=[('data',C.c_void_p),('size',C.c_size_t)]
def argb_checks(library):
 lib=C.CDLL(str(library));fn=lib.coh_bridge_argb8888
 fn.argtypes=[Bytes,C.c_void_p,C.c_size_t,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
 rng=random.Random(0x2324);checks=0
 for case in range(120):
  w,h=rng.randint(1,19),rng.randint(1,17);pixels=bytes(rng.randrange(256) for _ in range(w*h*4))
  head=bytearray(128);head[:4]=b'DDS ';struct.pack_into('<I',head,4,124);struct.pack_into('<II',head,12,h,w);struct.pack_into('<I',head,28,1);struct.pack_into('<8I',head,76,32,65,0,32,0xff0000,0xff00,0xff,0xff000000)
  raw=bytes(head)+pixels;buf=C.create_string_buffer(raw);out=C.create_string_buffer(len(pixels));width=C.c_uint32();height=C.c_uint32()
  assert fn(Bytes(C.addressof(buf),len(raw)),out,len(out),C.byref(width),C.byref(height))==0
  expected=b''.join(bytes((pixels[i+2],pixels[i+1],pixels[i],pixels[i+3])) for i in range(0,len(pixels),4))
  assert out.raw==expected and (width.value,height.value)==(w,h);checks+=1
  for mutation in ('short','tail','mask','volume','mips','width','capacity','overlap'):
   bad=bytearray(raw);capacity=len(pixels);target=out
   if mutation=='short':bad=bad[:-1]
   elif mutation=='tail':bad+=b'x'
   elif mutation=='mask':struct.pack_into('<I',bad,92,0xff)
   elif mutation=='volume':struct.pack_into('<I',bad,112,0x200000)
   elif mutation=='mips':struct.pack_into('<I',bad,28,32)
   elif mutation=='width':struct.pack_into('<I',bad,16,0xffffffff)
   elif mutation=='capacity':capacity-=1
   buf2=C.create_string_buffer(bytes(bad));before=bytes([83])*len(pixels);C.memmove(out,before,len(before));width.value=999;height.value=998
   if mutation=='overlap':target=buf2
   assert fn(Bytes(C.addressof(buf2),len(bad)),target,capacity,C.byref(width),C.byref(height))!=0
   assert (width.value,height.value)==(999,998)
   if mutation!='overlap':assert out.raw==before
   checks+=1
 return {'passed':True,'cases':checks,'independent_channel_swizzle_cases':120,'malformed_capacity_overlap_cases':960,'scope':'exact ARGB8888 only, mip-zero output; no compressed decoder retest'}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--corpus',type=Path,required=True);ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--ndk',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 pins=corpus_pins(a.corpus);sources=[HERE/'coh_asset_render.c',NATIVE/'engine/assets/coh_asset_loader.c',NATIVE/'engine/assets/coh_asset_geo.c',NATIVE/'engine/renderer/coh_renderer.c',NATIVE/'src/coh_assets.c',NATIVE/'src/coh_dds.c']
 flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',NATIVE/'include']
 result={'scope':'new asset/render bridge only','raw_assets':pins,'source_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.suffix in ('.c','.h','.py')},'android_execution':False,'physical_thor_acceptance':False}
 with tempfile.TemporaryDirectory(prefix='coh-bridge-') as directory:
  temp=Path(directory);run(['cc',*flags,'-O2',HERE/'tests/test_bridge.c',*sources,'-lz','-lm','-o',temp/'test'])
  result['host']=json.loads(run([temp/'test',a.corpus,temp]));result['source_packet_oracle']=packet_oracle(a.corpus,temp,a.source_root);result['texture_upload_oracle']=texture_oracle(a.corpus,temp)
  run(['cc',*flags,'-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined',HERE/'tests/test_bridge.c',*sources,'-lz','-lm','-o',temp/'test-san'])
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
  result['sanitizers']={'passed':True,'address':True,'undefined':True,'leak_sanitizer':False,'reason':'LSan unavailable in this execution environment; no LSan pass claimed','test':json.loads(run([temp/'test-san',a.corpus,temp],env=env))}
  run(['cc',*flags,'-O2','-fPIC','-shared',*sources,'-lz','-lm','-o',temp/'bridge.so']);result['native_argb8888']=argb_checks(temp/'bridge.so')
  if a.ndk:
   cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang'
   run([cc,*flags,'-O2','-fPIC','-shared','-Wl,--no-undefined',*sources,'-lz','-lm','-o',temp/'bridge-arm64.so'])
   result['android_arm64_build']={'passed':True,'api':26,'ndk':a.ndk.name,'bytes':(temp/'bridge-arm64.so').stat().st_size,'sha256':sha(temp/'bridge-arm64.so'),'elf':run(['file',temp/'bridge-arm64.so']).strip(),'execution':False}
 result['passed']=True;a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
