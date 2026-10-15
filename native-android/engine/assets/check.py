#!/usr/bin/env python3
"""Standalone opt-in Gate22 host proof; --output is a JSON file.

--source-root is a full checkout containing upstream/ouroboros for independent
original-source execution. --corpus-root points to recovered authentic files.
No binary game assets are written into the repository. Test packaging synthesizes
PIGG containers around original asset bytes; this is NOT an original PIGG oracle.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,io,json,os,shlex,struct,subprocess,tempfile,time,zlib
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]
class Bytes(C.Structure):_fields_=[('data',C.c_void_p),('size',C.c_size_t)]
class Pack(C.Structure):_fields_=[('packed',C.c_uint32),('decoded',C.c_uint32),('offset',C.c_uint32)]
class Geo(C.Structure):_fields_=[('header',Bytes),('payload',Bytes),('textures',Bytes),('names',Bytes),('materials',Bytes),('version',C.c_uint32),('model_count',C.c_uint32),('texture_count',C.c_uint32),('records_offset',C.c_size_t)]
class Model(C.Structure):_fields_=[('name',C.c_char_p),('vertices',C.c_uint32),('triangles',C.c_uint32),('material_count',C.c_uint32),('material_offset',C.c_uint32),('bone_info_offset',C.c_uint32),('pack_count',C.c_uint32),('scale',C.c_float*3),('packs',Pack*10)]
class Texture(C.Structure):_fields_=[('dds',Bytes),('name',C.c_char_p),('flags',C.c_uint32),('width',C.c_uint32),('height',C.c_uint32),('fade',C.c_float*2),('alpha',C.c_uint8)]
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def corpus(root):
 if not root:return []
 paths={}
 for d in [root,*root.glob('*/native-android/tools/*/corpus'),*root.glob('native-android/tools/*/corpus'),*root.glob('*/native-android/integration-probe/app/src/main/assets')]:
  if d.is_dir():
   for p in d.iterdir():
    if p.is_file() and p.suffix in ('.geo','.anim','.texture','.ogg'):paths.setdefault(p.name,[]).append(p)
 pins=list((NATIVE/'tools').glob('*/pins.json'))
 result={}
 for pinpath in pins:
  data=json.loads(pinpath.read_text());records=data.get('records',[])+([data['record']] if 'record' in data else [])
  for r in records:
   for p in paths.get(r.get('file_name',''),[]):
    raw=p.read_bytes()
    if sha(raw)==r.get('sha256'):
     result[r['name']]={'virtual':r['name'],'disk':str(p),'sha256':sha(raw),'pin':str(pinpath.relative_to(NATIVE)),'raw':raw};break
 return list(result.values())

def make_pigg(items):
 allitems=[('test/a',bytes(range(32)),None),('test/b',bytes(range(64)),None)]+[(f'test/p{i}',bytes([i+1])*16,None) for i in range(5)]
 allitems+=[('test/corrupt',bytes(32),b'bad zlib'),('test/trailing',bytes(32),zlib.compress(bytes(32))+b'bad')]
 allitems += [(r['virtual'],r['raw'],None) for r in items]
 names=b''.join(struct.pack('<I',len(p.encode())+1)+p.encode()+b'\0' for p,_,_ in allitems)
 pools=struct.pack('<III',0x6789,len(allitems),len(names))+names+struct.pack('<III',0x9abc,0,0)
 offset=16+48*len(allitems)+len(pools);records=[];body=[]
 for i,(p,raw,override) in enumerate(allitems):
  packed=override if override is not None else zlib.compress(raw) if i%2 else None
  stored=raw if packed is None else packed
  records.append(struct.pack('<7I',0x3456,i,len(raw),0,offset,0,0xffffffff)+hashlib.md5(raw).digest()+struct.pack('<I',len(packed) if packed is not None else 0));body.append(stored);offset+=len(stored)
 return struct.pack('<I4HI',0x123,2,2,16,48,len(allitems))+b''.join(records)+pools+b''.join(body)

def reference(raw):
 """Independent bytewise source GEO envelope/table walk, no native calls."""
 u=lambda b,o:struct.unpack_from('<I',b,o)[0]
 bias,n=struct.unpack_from('<II',raw)
 if n:v,start,packed,off=0,8,bias-4,bias+8
 else:v,n=struct.unpack_from('<II',raw,8);start,packed,off=16,bias-12,bias+4
 h=zlib.decompress(raw[start:start+packed]);assert len(h)==n
 data=raw[off:];assert len(data)==u(h,0)
 fields=5 if 2<=v<=6 else 4;sizes=[u(h,i*4) for i in range(fields)];pos=fields*4;blocks=[]
 for size in sizes[1:4]:blocks.append(h[pos:pos+size]);pos+=size
 if fields==5:pos+=sizes[4]
 tn,names,mats=blocks;nt=u(tn,0);base=4+nt*4
 nameat=lambda b,o:b[o:b.index(b'\0',o)].decode()
 texnames=[nameat(tn,base+u(tn,4+i*4)) for i in range(nt)]
 count=u(h,pos+136);pos+=140;models=[]
 for i in range(count):
  size=216 if v<3 else u(h,pos);r=h[pos:pos+size];pos+=size
  if v<3:nameoff,vc,mc,mo,po,so,bc=80,28,12,36,132,92,20
  else:nameoff,vc,mc,mo,po,so,bc=(64,16,8,28,108,72,12) if v>=8 else (60,16,8,24,104,68,12)
  packs=[struct.unpack_from('<III',r,po+j*12) for j in range(7 if v<3 else 8+(v>=7)+(v>=8))]
  if v<3:packs.insert(4,(0,0,0))
  material=[(texnames[tid],tris) for tid,tris in struct.iter_unpack('<HH',mats[u(r,mo):u(r,mo)+u(r,mc)*4])]
  models.append({'name':nameat(names,u(r,nameoff)),'vertices':u(r,vc),'triangles':u(r,vc+4),'materials':material,'packs':packs,'scale':struct.unpack_from('<3f',r,so)})
 assert pos==len(h)
 return v,data,models

def source_oracle(lib,items,source_root,temp):
 source=source_root/'upstream/ouroboros/Common/seq/anim.c'
 original=module('asset_original_delta',NATIVE/'tools/material_fixture/original_delta_check.py')
 code=original.original_c(source);c=temp/'original.c';c.write_bytes(code);so=temp/'original.so'
 subprocess.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC',str(c),'-o',str(so)],check=True)
 ref=C.CDLL(str(so));ref.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
 lib.coh_asset_geo_workspace.argtypes=[Bytes,C.POINTER(C.c_size_t)];lib.coh_asset_geo_open.argtypes=[Bytes,C.c_void_p,C.c_size_t,C.c_uint32,C.POINTER(Geo)]
 lib.coh_asset_geo_model.argtypes=[C.POINTER(Geo),C.c_uint32,C.POINTER(Model)]
 lib.coh_asset_geo_stream.argtypes=[C.POINTER(Geo),C.POINTER(Model),C.c_uint32,C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
 lib.coh_asset_delta_floats.argtypes=[Bytes,C.c_uint32,C.c_uint32,C.c_void_p,C.c_size_t];lib.coh_asset_delta_indices.argtypes=[Bytes,C.c_uint32,C.c_void_p,C.c_size_t]
 lib.coh_asset_texture.argtypes=[Bytes,C.POINTER(Texture)];lib.coh_asset_texture_rgba.argtypes=[C.POINTER(Texture),C.c_uint32,C.c_void_p,C.c_size_t]
 results=[];elements=0;models_checked=0;channels=0;texture_pixels=0
 for item in items:
  raw=item['raw'];p=C.create_string_buffer(raw);b=Bytes(C.addressof(p),len(raw));r={'virtual':item['virtual'],'sha256':sha(raw),'bytes':len(raw),'pin':item['pin']}
  if item['virtual'].endswith('.geo'):
   version,data,models=reference(raw);n=C.c_size_t();assert lib.coh_asset_geo_workspace(b,C.byref(n))==0;w=C.create_string_buffer(n.value);g=Geo();assert lib.coh_asset_geo_open(b,w,len(w),4096,C.byref(g))==0;assert g.version==version and g.model_count==len(models);scratch=C.create_string_buffer(65536)
   for i,want in enumerate(models):
    m=Model();assert lib.coh_asset_geo_model(C.byref(g),i,C.byref(m))==0;assert m.name.decode()==want['name'];assert m.vertices==want['vertices'] and m.triangles==want['triangles'];assert list(m.scale)==list(want['scale']);assert m.pack_count==len(want['packs']);models_checked+=1
    for j,(packed,size,off) in enumerate(want['packs']):
     stored=data[off:off+(packed or size)];gold=zlib.decompress(stored) if packed else stored;assert len(gold)==size;assert (m.packs[j].packed,m.packs[j].decoded,m.packs[j].offset)==(packed,size,off)
     out=C.create_string_buffer(max(1,size));actual=C.c_size_t();assert lib.coh_asset_geo_stream(C.byref(g),C.byref(m),j,out,size,scratch,len(scratch),C.byref(actual))==0;assert actual.value==size and out.raw[:size]==gold
     if j<=3 and gold:
      count=m.triangles if j==0 else m.vertices;stride=2 if j==3 else 3;total=count*stride;decoded=C.create_string_buffer(total*4);encoded=C.create_string_buffer(gold+b'\0'*16)
      if j==0:assert lib.coh_asset_delta_indices(Bytes(C.addressof(encoded),len(gold)),count,decoded,total)==0
      else:assert lib.coh_asset_delta_floats(Bytes(C.addressof(encoded),len(gold)),count,stride,decoded,total)==0
      original_out=C.create_string_buffer(total*4);consumed=ref.uncompressDeltas(original_out,encoded,stride,count,int(j==0));assert consumed==len(gold);assert original_out.raw==decoded.raw;elements+=total;channels+=1
   r.update(version=version,models=len(models),original_delta_byte_exact=True)
  elif item['virtual'].endswith('.texture'):
   from PIL import Image
   t=Texture();assert lib.coh_asset_texture(b,C.byref(t))==0;decoded=C.create_string_buffer(t.width*t.height*4);assert lib.coh_asset_texture_rgba(C.byref(t),0,decoded,len(decoded))==0;dds=C.string_at(t.dds.data,t.dds.size);gold=Image.open(io.BytesIO(dds)).convert('RGBA').tobytes();assert decoded.raw==gold;texture_pixels+=t.width*t.height;r.update(width=t.width,height=t.height,pillow_rgba_exact=True)
  results.append(r)
 return {'passed':True,'original_source_sha256_lf':original.SOURCE_SHA,'original_function_sha256_lf':original.FUNCTION_SHA,'models_compared':models_checked,'delta_channels':channels,'scalar_elements':elements,'texture_pixels':texture_pixels,'assets':results,'original_game_execution':False}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--source-root',type=Path,default=NATIVE.parent);ap.add_argument('--corpus-root',type=Path);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args();items=corpus(a.corpus_root);a.output.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='coh-assets-') as temp:
  t=Path(temp);pigg=t/'corpus.pigg';pigg.write_bytes(make_pigg(items));manifest=t/'manifest';manifest.write_text(''.join(r['virtual']+'|'+r['disk']+'\n' for r in items))
  sources=[HERE/'coh_asset_loader.c',HERE/'coh_asset_geo.c',NATIVE/'src/coh_assets.c',NATIVE/'src/coh_dds.c'];base=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fno-fast-math','-ffp-contract=off','-I',str(NATIVE/'include')];exe=t/'harness'
  command=[*base,'-O2',str(HERE/'tests/harness.c'),*map(str,sources),'-lz','-lm','-o',str(exe)];subprocess.run(command,check=True);started=time.monotonic();host=json.loads(subprocess.check_output([str(exe),str(pigg),str(manifest)],text=True));host['elapsed_seconds']=time.monotonic()-started
  so=t/'assets.so';subprocess.run([*base,'-O0','-fPIC','-shared',*map(str,sources),'-lz','-lm','-o',str(so)],check=True);lib=C.CDLL(str(so))
  oracle=source_oracle(lib,items,a.source_root,t) if items else {'passed':False,'reason':'No authentic corpus supplied; run --corpus-root. Synthetic unit proof only.'}
  san={'run':False}
  if a.sanitize:
   sx=t/'harness-san';cmd=[*base,'-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(HERE/'tests/harness.c'),*map(str,sources),'-lz','-lm','-o',str(sx)];subprocess.run(cmd,check=True);env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');san={'run':True,'address':True,'undefined':True,'leak_detection':False,'leak_note':'LeakSanitizer cannot inspect /proc under this execution environment; initial detect_leaks=1 run failed during leak runtime setup. ASan/UBSan rerun with leak detection disabled.','result':json.loads(subprocess.check_output([str(sx),str(pigg),str(manifest)],text=True,env=env))}
  sourcepaths=['libs/UtilitiesLib/include/utilitieslib/utils/piglib_internal.h','libs/UtilitiesLib/src/utils/piglib.c','libs/UtilitiesLib/src/components/datapool.c','Game/src/render/tex.h','Common/seq/anim.c'];provenance={p:sha((a.source_root/'upstream/ouroboros'/p).read_bytes().replace(b'\r\n',b'\n')) for p in sourcepaths if (a.source_root/'upstream/ouroboros'/p).exists()}
  report={'schema':'coh-gate22-host-v1','implemented':True,'host_qualified':bool(items and oracle['passed']),'android_built':False,'emulator_qualified':False,'physical_qualified':False,'host':host,'oracle':oracle,'sanitizers':san,'source_provenance_lf_sha256':provenance,'pigg_corpus_container':'synthetic original-format packaging; authentic payloads, no original PIGG archive execution comparison','compile_command':command,'limits':{'heap_bytes':4<<20,'resident_bytes':512<<10,'single_asset_bytes':256<<10,'resident_entries':4},'scope':'Opt-in indexed native asset library; no Session Client or JNI changes.'};a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('host_qualified','host','sanitizers')},indent=2))
if __name__=='__main__':main()
