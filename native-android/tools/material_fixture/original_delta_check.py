#!/usr/bin/env python3
"""Execute the hash-pinned original scalar delta function on a real CoH mesh.

This is the original uncompressDeltas function executed on a Linux host through
local type/macro shims. It is not the Win32 Game executable, a full .geo loader,
Android execution, or a safe decoder for arbitrary inputs. Only the hash-pinned
real corpus, after bounded Python decoding, reaches this legacy function.
"""
from __future__ import annotations
import argparse,ctypes as C,hashlib,importlib.util,json,os
from pathlib import Path
import shlex,struct,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
SOURCE_SHA='adcdfa2ae1a822c4aed10b0f41baeca5e94b8683e10ed78e3bb45d6bac7936bc'
FUNCTION_SHA='6e111b02fecb0eb94f82887c5429ba9c3da58ecdee6a0d063261cae41e60f8c3'
WEIGHT_SOURCE_SHA='23297301f34737585d65e39fc8b01445e5b4a8f665ac9cb49e9101f6f2cf299b'
PALETTE_SOURCE_SHA='e64ec178a7fc90b260da7c9be8aadbd5014c2dd0e909ae221630b5ea4ae74325'
def sha(b):return hashlib.sha256(b).hexdigest()
def require(v,message):
 if not v:raise ValueError(message)
def preparer():
 path=Path(__file__).with_name('prepare.py');spec=importlib.util.spec_from_file_location('coh_material_prepare',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def original_c(source):
 text=source.read_bytes().replace(b'\r\n',b'\n');require(sha(text)==SOURCE_SHA,'Original animation source hash differs')
 start=text.index(b'int uncompressDeltas(');end=text.index(b'#define IDX2PTR',start);function=text[start:end].strip()+b'\n';require(sha(function)==FUNCTION_SHA,'Original scalar decoder function hash differs')
 before=b'''#include <stdint.h>
#include <stddef.h>
typedef unsigned char U8;typedef uint16_t U16;typedef uint32_t U32;typedef float F32;typedef float Vec3[3];
typedef enum {PACK_F32,PACK_U32,PACK_U16} PackType;
#define xcase break;case
'''
 after=b'''
int original_weight_slots(const U8 *weights,const U8 *matidxs,int count,int bone_count,F32 *out,U32 *slots) {
    if(count<0||bone_count<1||bone_count>15)return 1;
    for(int i=0;i<count;i++) {
        if(matidxs[i*2]%3||matidxs[i*2+1]%3||matidxs[i*2]/3>=bone_count||matidxs[i*2+1]/3>=bone_count)return 1;
        out[i*2]=weights[i] * 1.f / 255.f;
        out[i*2+1]=1.f-out[i*2];
        slots[i*2]=matidxs[i*2]/3;slots[i*2+1]=matidxs[i*2+1]/3;
    }
    return 0;
}
void original_gpu_uvs(const F32 *raw,int count,F32 *out) {
    for(int i=0;i<count;i++) {out[i*2]=raw[i*2];out[i*2+1]=1.f-raw[i*2+1];}
}
'''
 return before+function+after

def inspect_streams(raw,pins,prepare):
 # Independent fixed v3 envelope/record span acquisition; legacy function receives only validated stream bytes.
 require(sha(raw)==next(r['sha256'] for r in pins['records'] if r['id']=='mesh'),'Real .geo hash differs')
 biased,zero,version,n=struct.unpack_from('<4I',raw);require(zero==0 and version==3,'Oracle corpus is version3 only')
 header=prepare.inflate(prepare.span(raw,16,biased-12),n);data=prepare.span(raw,biased+4,prepare.u32(header,0))
 sizes=[prepare.u32(header,i*4) for i in range(5)];record_pos=20+sum(sizes[1:])+140
 for i in range(pins['model_index']):record_pos+=prepare.u32(header,record_pos)
 record=prepare.span(header,record_pos,prepare.u32(header,record_pos));vertices=prepare.u32(record,16);triangles=prepare.u32(record,20)
 packs=[struct.unpack_from('<III',record,104+i*12) for i in range(8)];streams=[]
 for packed,unpacked,offset in packs:
  stored=prepare.span(data,offset,packed or unpacked);streams.append(prepare.inflate(stored,unpacked) if packed else stored)
 bi=prepare.span(data,prepare.u32(record,12),72);bone_count=prepare.u32(bi,0)
 return vertices,triangles,bone_count,streams

def main():
 p=argparse.ArgumentParser(description=__doc__);choice=p.add_mutually_exclusive_group(required=True)
 choice.add_argument('--corpus',type=Path,help='Acquired pinned corpus directory containing mesh.geo')
 choice.add_argument('--geometry',type=Path,help='Explicit original pinned geometry path')
 p.add_argument('--source',type=Path,default=ROOT.parent/'upstream/ouroboros/Common/seq/anim.c')
 p.add_argument('--compiler',default=os.environ.get('CC','cc'));p.add_argument('--output',type=Path);a=p.parse_args()
 prepare=preparer();pins=json.loads(Path(__file__).with_name('pins.json').read_text());geometry=a.geometry or a.corpus/'mesh.geo';raw=geometry.read_bytes()
 canonical,_,_,metadata=prepare.mesh_from_geo(raw,pins);vc,tc,bc,streams=inspect_streams(raw,pins,prepare);code=original_c(a.source)
 weight_source=(ROOT.parent/'upstream/ouroboros/Game/src/render/model_cache.c').read_bytes().replace(b'\r\n',b'\n')
 palette_source=(ROOT.parent/'upstream/ouroboros/Game/src/render/thread/rt_bonedmodel.c').read_bytes().replace(b'\r\n',b'\n')
 require(sha(weight_source)==WEIGHT_SOURCE_SHA,'Original weight conversion source hash differs')
 require(sha(palette_source)==PALETTE_SOURCE_SHA,'Original palette consumer source hash differs')
 require(b'vbo->weights[i][0] = weights[i] * 1.f / 255.f;' in weight_source and b'vbo->weights[i][1] = 1.f - vbo->weights[i][0];' in weight_source,'Original weight expressions differ')
 require(b'vbo->sts[j][1] = 1.f - vbo->sts[j][1];' in weight_source,'Original GPU UV flip expression differs')
 require(b'matidx0 = vbo->matidxs[vertidx][0]/3;' in palette_source and b'matidx1 = vbo->matidxs[vertidx][1]/3;' in palette_source,'Original palette consumer expressions differ')
 report={'format':1,'status':'passed','scope':'exact original scalar uncompressDeltas on Linux host, plus source weight conversion and encoded palette slot conversion','win32_game_execution':False,'android_device_execution':False,'complete_geo_loader':False,'source_commit':pins['source_commit'],'source_sha256_lf':SOURCE_SHA,'original_function_sha256_lf':FUNCTION_SHA,'source_weight_conversion_sha256_lf':WEIGHT_SOURCE_SHA,'source_palette_consumer_sha256_lf':PALETTE_SOURCE_SHA,'generated_shimmed_source_sha256':sha(code),'real_geometry_sha256':sha(raw),'canonical_mesh_sha256':sha(canonical),'vertex_count':vc,'triangle_count':tc,'bone_count':bc,'channels':[]}
 with tempfile.TemporaryDirectory(prefix='coh-original-delta-') as temp:
  t=Path(temp);source=t/'original_delta.c';source.write_bytes(code);library=t/'original_delta.so'
  command=[*shlex.split(a.compiler),'-std=c11','-O0','-fno-strict-aliasing','-fPIC','-shared','-o',str(library),str(source)];subprocess.run(command,check=True)
  lib=C.CDLL(str(library));lib.uncompressDeltas.argtypes=[C.c_void_p,C.POINTER(C.c_uint8),C.c_int,C.c_int,C.c_int];lib.uncompressDeltas.restype=C.c_int
  definitions=[('indices',0,tc,3,1),('positions',1,vc,3,0),('normals',2,vc,3,0),('uvs',3,vc,2,0)]
  for name,index,count,stride,kind in definitions:
   stream=streams[index];python=prepare.decode_delta(stream,count,stride,kind==0);golden=struct.pack('<'+('f' if kind==0 else'I')*len(python),*python)
   # Buffer has alignment and a small tail because the original code fetches U32 control words.
   mem=(C.c_uint8*(len(stream)+16))();C.memmove(mem,stream,len(stream));out=(C.c_uint8*len(golden))()
   consumed=lib.uncompressDeltas(out,mem,stride,count,kind);actual=bytes(out)
   require(consumed==len(stream),f'Original {name} byte consumption differs');require(actual==golden,f'Original {name} differs byte-for-byte from bounded Python decoder')
   if name not in ('indices','uvs'):
    offset={'positions':0,'normals':12,'uvs':24}[name];canonical_bytes=b''.join(canonical[64+i*48+offset:64+i*48+offset+stride*4] for i in range(vc));require(canonical_bytes==actual,f'Canonical {name} bytes differ')
   elif name=='indices':
    off=struct.unpack_from('<I',canonical,36)[0];require(canonical[off:off+len(actual)]==actual,'Canonical triangle bytes differ')
   if name=='uvs':
    lib.original_gpu_uvs.argtypes=[C.POINTER(C.c_float),C.c_int,C.POINTER(C.c_float)];lib.original_gpu_uvs.restype=None
    src=(C.c_float*(vc*2)).from_buffer_copy(actual);gpu=(C.c_float*(vc*2))();lib.original_gpu_uvs(src,vc,gpu)
    uploaded=bytes(gpu);target=b''.join(canonical[64+i*48+24:64+i*48+32] for i in range(vc))
    require(target==uploaded,'Canonical UVs differ from source GPU V-flip under unit material scales')
    report['channels'].append({'name':'uvs_gpu_upload','elements':vc*2,'decoded_bytes':len(uploaded),'sha256':sha(uploaded),'byte_exact':True,'source_expression':'u unchanged; v=1.f-v; selected fixture has unit bind scales and zero UV scrolling','full_runtime_material_transform_resolver':False})
   report['channels'].append({'name':name,'elements':count*stride,'source_stream_bytes':len(stream),'scale_exponent':stream[(count*stride*2+7)//8],'decoded_bytes':len(actual),'sha256':sha(actual),'byte_exact':True})
  weights,mats=streams[5],streams[6];require(len(weights)==vc and len(mats)==vc*2,'Raw skin channel dimensions differ')
  lib.original_weight_slots.argtypes=[C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),C.c_int,C.c_int,C.POINTER(C.c_float),C.POINTER(C.c_uint32)];lib.original_weight_slots.restype=C.c_int
  w=(C.c_uint8*len(weights)).from_buffer_copy(weights);m=(C.c_uint8*len(mats)).from_buffer_copy(mats);wf=(C.c_float*(vc*2))();slots=(C.c_uint32*(vc*2))()
  require(lib.original_weight_slots(w,m,vc,bc,wf,slots)==0,'Original palette indices invalid')
  expected_weights=b''.join(canonical[64+i*48+32:64+i*48+40] for i in range(vc));expected_slots=b''.join(canonical[64+i*48+40:64+i*48+48] for i in range(vc))
  require(bytes(wf)==expected_weights,'Canonical weight conversion differs from exact source float division/complement')
  require(bytes(slots)==expected_slots,'Canonical palette slot division differs')
  report['channels'] += [{'name':'weights','elements':vc*2,'source_stream_bytes':len(weights),'decoded_bytes':len(expected_weights),'sha256':sha(expected_weights),'byte_exact':True,'source_expression':'weight_byte * 1.f / 255.f; weight1=1.f-weight0'}, {'name':'local_palette_slots','elements':vc*2,'source_stream_bytes':len(mats),'decoded_bytes':len(expected_slots),'sha256':sha(expected_slots),'byte_exact':True,'source_expression':'encoded_byte / 3; divisible-by-three and actual-bone-count validation'}]
 rendered=json.dumps(report,indent=2)+'\n'
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered)
 print(rendered,end='')
if __name__=='__main__':main()
