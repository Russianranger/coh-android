#!/usr/bin/env python3
"""Convert a hash-pinned real CoH mesh and material into bounded probe assets.

This Python reader is an independent source-contract implementation. It does not
execute the original client, reconstruct its scene graph or claim animation playback.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,math,struct,subprocess,sys,zlib
ROOT=Path(__file__).resolve().parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def require(v,s):
 if not v:raise ValueError(s)
def span(b,o,n):
 require(0<=o<=len(b) and 0<=n<=len(b)-o,'byte span exceeds file');return b[o:o+n]
def u32(b,o):return struct.unpack('<I',span(b,o,4))[0]
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def name_at(b,o):
 require(0<=o<len(b),'name outside table');end=b.find(b'\0',o);require(o<end<=o+1024,'name lacks bounded terminator');return b[o:end].decode('ascii')
def inflate(b,n):
 require(0<n<=4<<20,'decoded stream exceeds bound');d=zlib.decompressobj();raw=d.decompress(b,n+1);require(d.eof and not d.unused_data and not d.unconsumed_tail and len(raw)==n,'zlib decoded size or stream differs');return raw

def decode_delta(b,count,stride,is_float):
 require(0<count<=100000 and stride in (2,3),'delta cardinality exceeds bound');n=count*stride;nb=(n*2+7)//8;codes=span(b,0,nb);exp=span(b,nb,1)[0];require(exp<=30,'delta exponent exceeds safe source range');inverse=f32(1/f32(1<<exp));cursor=nb+1;last=[0.0 if is_float else 0]*stride;out=[]
 for i in range(n):
  code=(codes[i//4]>>(2*(i%4)))&3
  if code==0:v=0
  elif code==1:v=span(b,cursor,1)[0]-127;cursor+=1
  elif code==2:v=struct.unpack('<H',span(b,cursor,2))[0]-32767;cursor+=2
  else:v=struct.unpack('<f' if is_float else'<i',span(b,cursor,4))[0];cursor+=4
  j=i%stride
  if is_float:
   delta=v if code==3 else f32(f32(v)*inverse);value=f32(last[j]+delta);require(math.isfinite(value),'nonfinite decoded float')
  else:value=last[j]+v+1;require(0<=value<=0xffffffff,'index accumulation exceeds U32')
  last[j]=value;out.append(value)
 require(cursor==len(b),'delta bytes have an unconsumed suffix');return out

def mesh_from_geo(raw,pins):
 require(sha(raw)==next(x for x in pins['records'] if x['id']=='mesh')['sha256'],'real geometry SHA256 differs')
 biased,zero,version,n=struct.unpack('<4I',span(raw,0,16));require(zero==0 and version==3,'this fixture reader admits version3 only');require(12<biased<len(raw)-4,'geometry envelope outside file');header=inflate(span(raw,16,biased-12),n);data=span(raw,biased+4,u32(header,0));require(biased+4+len(data)==len(raw),'geometry trailing bytes differ')
 sizes=[u32(header,i*4) for i in range(5)];pos=20;texnames=span(header,pos,sizes[1]);pos+=sizes[1];objnames=span(header,pos,sizes[2]);pos+=sizes[2];texids=span(header,pos,sizes[3]);pos+=sizes[3];span(header,pos,sizes[4]);pos+=sizes[4];models=u32(header,pos+136);require(1<=models<=32,'model count exceeds fixture bound');pos+=140
 tcount=u32(texnames,0);require(0<tcount<=100,'texture count exceeds fixture bound');tbase=4+4*tcount;texture_names=[name_at(texnames,tbase+u32(texnames,4+4*i)) for i in range(tcount)]
 chosen=None
 for i in range(models):
  size=u32(header,pos);require(204<=size<=4096,'model record size differs');rec=span(header,pos,size);modelname=name_at(objnames,u32(rec,60))
  if i==pins['model_index']:
   require(modelname==pins['model_name'],'real model name differs');chosen=rec
  pos+=size
 require(chosen is not None,'selected model absent');r=chosen;vc=u32(r,16);tc=u32(r,20);require(0<vc<=10000 and 0<tc<=10000,'mesh exceeds probe count bound');require(u32(r,8)==1,'probe requires one material/submesh');texid,textri=struct.unpack('<HH',span(texids,u32(r,24),4));require(texid<tcount and textri==tc,'material triangle count differs');require(texture_names[texid]==pins['material_binding']['primary_geometry_texname'],'material primary name differs')
 packs=[struct.unpack('<III',span(r,104+i*12,12)) for i in range(8)]
 for packed,unpacked,off in packs:
  require(unpacked<=4<<20,'model stream decoded size exceeds bound');span(data,off,packed or unpacked)
 def stream(i):
  packed,unpacked,off=packs[i];b=span(data,off,packed or unpacked);return inflate(b,unpacked) if packed else b
 indices=decode_delta(stream(0),tc,3,False);positions=decode_delta(stream(1),vc,3,True);normals=decode_delta(stream(2),vc,3,True);uvs=decode_delta(stream(3),vc,2,True)
 # modelFixup applies this before the original GPU upload.
 for i in range(vc):uvs[i*2+1]=f32(1-uvs[i*2+1])
 require(all(i<vc for i in indices),'triangle index exceeds vertices');weights=stream(5);matidx=stream(6);require(len(weights)==vc and len(matidx)==vc*2,'skin channels differ from vertex count');bi=span(data,u32(r,12),72);bc=u32(bi,0);require(2<=bc<=15,'fixture requires a real multibone palette');bones=[u32(bi,4+4*i) for i in range(bc)];require(len(set(bones))==bc and all(i<99 for i in bones),'palette global IDs invalid');require(u32(bi,64)==u32(bi,68)==0,'legacy pointer slots must be zero')
 vertices=[];used=set();blended=0
 for i in range(vc):
  encoded=matidx[2*i:2*i+2];require(all(x%3==0 and x//3<bc for x in encoded),'encoded palette rows invalid');slots=[x//3 for x in encoded];w0=f32(f32(weights[i])/255.0);w1=f32(1-w0);used.update(slots)
  if 0<weights[i]<255 and slots[0]!=slots[1]:blended+=1
  n3=normals[i*3:i*3+3];require(sum(x*x for x in n3)>1e-12,'zero mesh normal');vertices.append(positions[i*3:i*3+3]+n3+uvs[i*2:i*2+2]+[w0,w1]+slots)
 require(blended>0 and len(used)>=2,'fixture has no genuine nontrivial skin blend');vo=64;io=vo+vc*48;bo=io+len(indices)*4;total=bo+bc*4;head=struct.pack('<8s14I',b'COHMESH1',1,64,vc,len(indices),bc,48,vo,io,bo,total,0,0,0,0);body=b''.join(struct.pack('<10f2I',*v) for v in vertices)+struct.pack('<'+'I'*len(indices),*indices)+struct.pack('<'+'I'*bc,*bones)
 require(len(head+body)==total,'canonical mesh size mismatch');bounds={'minimum':[min(positions[c::3]) for c in range(3)],'maximum':[max(positions[c::3]) for c in range(3)]}
 meta={'version':version,'model':pins['model_name'],'vertex_count':vc,'triangle_count':tc,'index_count':len(indices),'bone_count':bc,'bone_global_ids':bones,'bone_global_names':['BONEID_LARMR','BONEID_COL_R','BONEID_UARMR'],'weight_source_expression':'float(byte) * 1.f / 255.f (float32 division)','weight_byte_values':sorted(set(weights)),'source_encoded_matrix_indices':sorted(set(matidx)),'genuinely_blended_vertices':blended,'bounds':bounds,'texture_names':[texture_names[texid]],'gpu_uv_transform':'V=float32(1-V), modelFixup before GPU upload','fixture_material_bind_scales':{'base':[1.0,1.0],'generic':[1.0,1.0],'scope':'unit binds for this controlled fixture'},'canonical_format':'COHMESH1','canonical_header_bytes':64,'canonical_vertex_stride':48}
 return head+body,vertices,bones,meta

def dot3(row,p,position):
 acc=f32(f32(row[0]*p[0])+f32(row[1]*p[1]));acc=f32(acc+f32(row[2]*p[2]));return f32(acc+row[3]) if position else acc

def pose_gold(vertices,palette):
 out=[]
 for v in vertices:
  s0,s1=v[10:12];w1=v[9];p0=palette[s0];p1=palette[s1];result=[]
  for part in (0,3):
   inp=v[part:part+3];a=[dot3(p0[c*4:c*4+4],inp,part==0) for c in range(3)];b=[dot3(p1[c*4:c*4+4],inp,part==0) for c in range(3)];blend=[f32(a[c]+f32(f32(b[c]-a[c])*w1)) for c in range(3)]
   if part==3:
    norm2=f32(f32(blend[0]*blend[0])+f32(blend[1]*blend[1]));norm2=f32(norm2+f32(blend[2]*blend[2]));require(norm2>1e-12,'controlled pose normal collapsed');inverse=f32(1/f32(math.sqrt(norm2)));blend=[f32(c*inverse) for c in blend]
   result+=blend
  out.append(result)
 return b''.join(struct.pack('<6f',*v) for v in out)

def make_poses(vertices,bones):
 bc=len(bones);vc=len(vertices);identity=[1,0,0,0,0,1,0,0,0,0,1,0];a=math.radians(18);b=math.radians(-14);controlled=[list(identity) for _ in bones];controlled[1]=[math.cos(a),-math.sin(a),0,.13,math.sin(a),math.cos(a),0,-.05,0,0,1,.02];controlled[2]=[math.cos(b),0,math.sin(b),-.09,0,1,0,.07,-math.sin(b),0,math.cos(b),0];sets=[[list(identity) for _ in bones],controlled];body=[];metas=[]
 for i,p in enumerate(sets):
  serialized=struct.pack('<'+'f'*(bc*12),*(f for row in p for f in row));roundtrip=struct.unpack('<'+'f'*(bc*12),serialized);p=[list(roundtrip[j*12:j*12+12]) for j in range(bc)];gold=pose_gold(vertices,p);body.append(serialized+gold);metas.append({'index':i,'name':'identity palette' if i==0 else'controlled palette','palette_sha256':sha(serialized),'golden_sha256':sha(gold),'role':'controlled validation transforms; not original animation playback'})
 stride=bc*48+vc*24;total=64+len(sets)*stride;h=struct.pack('<8s14I',b'COHPOSE1',1,64,len(sets),vc,bc,48,stride,64,total,0,0,0,0,0);raw=h+b''.join(body);require(len(raw)==total,'pose container size mismatch');return raw,metas

def decode_texture(raw,fn):
 require(len(raw)>=32,'texture wrapper truncated');head,size,w,h,flags,fade0,fade1,alpha,ver=struct.unpack_from('<iiiiIffB3s',raw);require(32<head<=1024+32 and head+size==len(raw) and ver in (b'TEX',b'TX2'),'texture wrapper envelope differs');dds=span(raw,head,size);require(len(dds)>=128 and dds[:4]==b'DDS ','texture DDS absent');height,width=struct.unpack_from('<II',dds,12);require(0<width<=1024 and 0<height<=1024,'texture footprint exceeds probe bound');
 fmt=dds[84:88];role='coh_dds_rgba (generic BC with alpha; original GPU upload role)'
 if fmt==b'\0'*4:
  require(u32(dds,4)==124 and u32(dds,76)==32 and u32(dds,80)==65 and struct.unpack_from('<5I',dds,88)==(32,0xff0000,0xff00,0xff,0xff000000),'uncompressed texture layout unsupported');require(u32(dds,24) in (0,1) and u32(dds,112)==0,'DDS volume/cubemap unsupported');levels=max(1,u32(dds,28));require(levels<=max(width,height).bit_length(),'uncompressed mip count exceeds bound');footprint=0;mw,mh=width,height
  for _ in range(levels):footprint+=mw*mh*4;mw=max(1,mw//2);mh=max(1,mh//2)
  require(len(dds)==128+footprint,'uncompressed mip envelope differs');pixels=span(dds,128,width*height*4);output=bytearray(len(pixels))
  for i in range(0,len(pixels),4):output[i:i+4]=bytes((pixels[i+2],pixels[i+1],pixels[i],pixels[i+3]))
  decoded=bytes(output);role='bounded offline ARGB8888 BGRA-to-RGBA converter; native core uncompressed DDS support remains pending';fmtname='ARGB8888'
 else:
  buf=C.create_string_buffer(dds);rgba=C.create_string_buffer(width*height*4);require(fn(buf,len(dds),0,rgba,len(rgba))==0,'GPU-compatible generic DDS decode failed');decoded=rgba.raw;fmtname=fmt.decode('ascii')
 return decoded,width,height,{'wrapper_sha256':sha(raw),'dds_sha256':sha(dds),'dds_format':fmtname,'width':width,'height':height,'mip':0,'decoder':role}

def main():
 p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--library',type=Path);a=p.parse_args();pins=json.loads(Path(__file__).with_name('pins.json').read_text());require(pins['material_binding']['secondary_resolution']!='pending','material secondary contract still pending');a.output.mkdir(parents=True,exist_ok=True)
 for pin in pins['records']:require(sha((a.corpus/pin['file_name']).read_bytes())==pin['sha256'],'acquired fixture SHA256 differs')
 mesh,vertices,bones,mm=mesh_from_geo((a.corpus/'mesh.geo').read_bytes(),pins);poses,pm=make_poses(vertices,bones)
 library=a.library
 if library is None:
  build=ROOT/'results/material-fixture-core';subprocess.run([sys.executable,str(ROOT/'tools/build.py'),'--output',str(build)],check=True,stdout=subprocess.DEVNULL);library=build/'libcoh_native_core.so'
 lib=C.CDLL(str(library.resolve()));fn=lib.coh_dds_rgba;fn.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_void_p,C.c_size_t]
 t0,w0,h0,tm0=decode_texture((a.corpus/'texture0.texture').read_bytes(),fn)
 secondary=pins['material_binding'].get('secondary_default')
 if secondary:
  require(secondary['rgba']==[255,255,255,255],'unsupported source texture fallback');t1=bytes(secondary['rgba']);w1=h1=1;tm1={'width':1,'height':1,'role':secondary['role'],'source':secondary['source'],'synthetic_game_fixture':False,'stock_engine_generated_default':True}
 else:t1,w1,h1,tm1=decode_texture((a.corpus/'texture1.texture').read_bytes(),fn)
 sys.path.insert(0,str(ROOT/'material-probe/contract'))
 from build_material_reference import prepare as material_prepare,self_check
 self_check()
 material,cases=material_prepare(t0,w0,h0,t1,w1,h1)
 mmeta={'oracle_kind':'source-semantic-scalar','original_cg_execution':False,'original_gpu_driver_texture_capture':False,'format':'COHMAT6','reference_width':64,'reference_height':64,'case_count':len(cases),'real_pair_case_count':sum(not (c['flags']&2) for c in cases),'controlled_swatch_case_count':sum(bool(c['flags']&2) for c in cases),'controlled_swatch':{'rgba':[51,153,230,128],'dimensions':[1,1],'role':'explicit diagnostic shader input; not a game asset'},'cases':cases}
 assets={'mesh.bin':mesh,'poses.bin':poses,'texture0.rgba':t0,'texture1.rgba':t1,'material-reference.bin':material}
 for name,data in assets.items():(a.output/name).write_bytes(data)
 meta={'format':1,'oracle_kind':'source-semantic-scalar','original_cg_execution':False,'original_gpu_driver_texture_capture':False,'name':'GEO_Sleeves_Wretch default material probe','source_release':pins['release_tag'],'model':mm,'poses':pm,'textures':[tm0,tm1],'material':mmeta,'material_binding':pins['material_binding'],'assets':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in assets.items()},'real_geometry_sha256':sha((a.corpus/'mesh.geo').read_bytes()),'native_generator_library_sha256':sha(library.read_bytes()),'native_gameplay_validated':False,'original_animation_playback_validated':False}
 (a.output/'material-fixture.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({'prepared':True,'model':mm['model'],'vertices':mm['vertex_count'],'triangles':mm['triangle_count'],'bones':mm['bone_count'],'blended_vertices':mm['genuinely_blended_vertices'],'texture_dimensions':[[w0,h0],[w1,h1]],'material_cases':len(cases),'assets':meta['assets']},indent=2))
if __name__=='__main__':main()
