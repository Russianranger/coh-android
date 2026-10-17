#!/usr/bin/env python3
"""Actual v5 CPU streams and unchanged legacy LOD source consumer qualification."""
import argparse,ctypes as C,hashlib,importlib.util,inspect,json,os,struct,subprocess,tempfile,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout

def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def original_record32(directory,record,names,materials):
 legacy=load('v5_original32_harness',HERE/'check_rigid_legacy.py');text=inspect.getsource(legacy.original_record)
 assert text.count('readModel(&dst,(char*)record,0,names,materials)')==1
 text=text.replace('readModel(&dst,(char*)record,0,names,materials)','readModel(&dst,(char*)record,5,names,materials)').replace('U32 facts[52]','U32 facts[55]').replace('int wrote;__asm__','memcpy(facts+52,dst.autolod_dists,12);int wrote;__asm__').replace("struct.unpack('<52I',execution.stdout)","struct.unpack('<55I',execution.stdout)")
 start=text.index(' expected=[216,216,');end=text.index(' if facts is not None',start)
 replacement=''' expected=[216,len(record),0,struct.unpack_from('<I',record,4)[0],struct.unpack_from('<I',record,8)[0],struct.unpack_from('<I',record,16)[0],struct.unpack_from('<I',record,20)[0],struct.unpack_from('<I',record,12)[0],struct.unpack_from('<I',record,64)[0],struct.unpack_from('<I',record,28)[0],struct.unpack_from('<I',record,60)[0],struct.unpack_from('<I',record,24)[0],struct.unpack_from('<h',record,200)[0]&0xffffffff,*struct.unpack_from('<9I',record,68)]
 packs=[struct.unpack_from('<3I',record,104+i*12) for i in range(8)]+[(0,0,0)]*2
 expected+=sum((list(p) for p in packs),[])+[0xbf800000]*3
'''
 text=text[:start]+replacement+text[end:];text=text.replace("'source_model_record_bytes':216","'source_model_record_bytes':len(record),'source_version':5").replace("'metadata_and_pack_scalars_compared':52", "'metadata_and_pack_scalars_compared':55")
 namespace=dict(legacy.__dict__);exec(text,namespace);proof=namespace['original_record'](directory,record,names,materials);proof['harness_scope']='Unchanged original readModel+original32 disk declarations; v5 call and expected facts/CLIENT autolod -1 checks added. Execution refusal is not qualification.';return proof

def lod_oracle(directory,lod,count,modes):
 legacy=load('v5_lod_extract',HERE/'check_rigid_legacy.py');anim=(ROOT/'upstream/ouroboros/Common/seq/anim.c').read_text();function=legacy.brace(anim,anim.index('static ModelLODInfo *unpackLODInfo('));a=anim.index('typedef struct AutoLODOnDisk_v5');b=anim.index('} ModelLODInfoOnDisk_v5;',a)+len('} ModelLODInfoOnDisk_v5;');declarations=anim[a:b]
 prefix='''#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef float F32;
typedef struct AutoLOD {int flags;float max_error,lod_near,lod_far,lod_nearfade,lod_farfade;char*lod_modelname,*lod_filename;} AutoLOD;
typedef struct {AutoLOD**lods;} ModelLODInfo;
typedef struct {uint32_t count;AutoLOD*rows[6];} EA;
static AutoLOD*allocAutoLOD(void){AutoLOD*p=calloc(1,sizeof(*p));assert(p);return p;}
static void eaPush(AutoLOD***dst,AutoLOD*item){EA*p;if(!*dst){p=calloc(1,sizeof(*p));assert(p);*dst=p->rows;}p=(EA*)((char*)*dst - offsetof(EA,rows));assert(p->count<6);p->rows[p->count++]=item;}
static char*ParserAllocString(const char*s){size_t n=strlen(s)+1;char*p=malloc(n);assert(p);memcpy(p,s,n);return p;}
static void ParserFreeString(char*s){free(s);}
'''
 main='''
_Static_assert(sizeof(AutoLODOnDisk_v5)==24,"original scalar layout");
_Static_assert(sizeof(ModelLODInfoOnDisk_v5)==148,"original fixed row layout");
int main(int argc,char**argv){assert(argc==3);unsigned count=(unsigned)strtoul(argv[2],NULL,10);assert(count>0&&count<=65536);FILE*f=fopen(argv[1],"rb");assert(f&&!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0&&n<16*1024*1024);rewind(f);char*raw=malloc((size_t)n);assert(raw&&fread(raw,1,(size_t)n,f)==(size_t)n&&!fclose(f));ModelLODInfo*info=unpackLODInfo(raw,(int)n,(int)count,5);assert(info);
for(unsigned r=0;r<count;r++){EA*e=info[r].lods?(EA*)((char*)info[r].lods - offsetof(EA,rows)):NULL;uint32_t num=e?e->count:0;assert(fwrite(&num,4,1,stdout)==1);for(unsigned j=0;j<num;j++){AutoLOD*l=e->rows[j];float fields[]={l->max_error,l->lod_near,l->lod_far,l->lod_nearfade,l->lod_farfade};assert(fwrite(fields,4,5,stdout)==5&&fwrite(&l->flags,4,1,stdout)==1);free(l->lod_modelname);free(l->lod_filename);free(l);}free(e);}free(info);free(raw);return 0;}
'''
 source=directory/'original-lod.c';source.write_text(prefix+declarations+'\n'+function+'\n'+main);inputpath=directory/'actual-lod.bin';inputpath.write_bytes(lod);expected=bytearray()
 for row in range(count):
  n=struct.unpack_from('<I',lod,row*148)[0];assert n<=6;expected+=struct.pack('<I',n)+lod[row*148+4:row*148+4+n*24]
 results={}
 for mode,extra in modes:
  binary=directory/('original-lod-'+mode);run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*extra,source,'-o',binary]);actual=run([binary,inputpath,count],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));assert actual==expected;(directory/(mode+'-lod-output.bin')).write_bytes(actual);results[mode]={'passed':True,'binary_sha256':sha(binary),'output_sha256':hashlib.sha256(actual).hexdigest()}
 return dict(unchanged_function_sha256_lf=hashlib.sha256(function.encode()).hexdigest(),unchanged_disk_declarations_sha256_lf=hashlib.sha256(declarations.encode()).hexdigest(),generated_harness_sha256=sha(source),scope='Unchanged original unpackLODInfo v5 function+fixed disk declarations; toy runtime destination/allocation helpers only. Raw inputs validated before use.',model_rows=count,raw_bytes=len(lod),active_lod_records=sum(struct.unpack_from('<I',lod,row*148)[0] for row in range(count)),modes=results,client_lod_applied=False)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('actual-geo','v0-regression-geo','v8-regression-geo','v7-regression-geo','output','oracle-output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--require-original32',action='store_true');a=p.parse_args();assert not a.output.exists() and not a.oracle_output.exists();a.oracle_output.mkdir(parents=True)
 pin=json.loads((HERE/'rigid-v5-pins.json').read_text());assert a.actual_geo.stat().st_size==pin['bytes'] and sha(a.actual_geo)==pin['sha256'];raw=a.actual_geo.read_bytes();bias,unused,version,n=struct.unpack_from('<4I',raw);assert unused==0 and version==5;header=zlib.decompress(raw[16:bias+4]);payload=raw[bias+4:];assert len(header)==n
 _,tn,nn,mn,ln=struct.unpack_from('<5I',header);names=header[20+tn:20+tn+nn];materials=header[20+tn+nn:20+tn+nn+mn];lodstart=20+tn+nn+mn;lod=header[lodstart:lodstart+ln];at=lodstart+ln;count=struct.unpack_from('<I',header,at+136)[0];at+=140;records=[]
 for _ in range(count):size=struct.unpack_from('<I',header,at)[0];assert size>=202 and at+size<=len(header);records.append((at,header[at:at+size]));at+=size
 assert count==14 and at==len(header) and len(lod)==2072;record=records[13][1];assert names[struct.unpack_from('<I',record,60)[0]:].split(b'\0')[0].decode()==pin['model']
 sources=[HERE/'tests/test_rigid_v5.c',HERE/'coh_wr_rigid.c',HERE/'coh_wr_rigid_v5.c',HERE/'coh_wr_rigid_v7.c',HERE/'coh_wr_rigid_source.c',HERE.parent/'scenecatalog/coh_resource_geo_source.c',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_geo.c',HERE.parent/'renderer/coh_renderer.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
 deps=sources+[HERE/n for n in ('coh_wr_rigid_v5.h','coh_wr_rigid_v7.h','coh_wr_rigid_internal.h','coh_wr_rigid.h','coh_wr_rigid_source.h','coh_world_render.h','check_rigid_v5.py','check_rigid_legacy.py','rigid-v5-pins.json','rigid-source-pins.json')]+[HERE.parent/'scenecatalog/coh_resource_geo_source.h',HERE.parent/'assets/coh_asset_geo.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'renderer/coh_renderer.h',HERE.parent/'renderer/coh_renderer_shaders.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/tools/material_fixture/original_delta_check.py']
 originalpins=json.loads((HERE/'rigid-source-pins.json').read_text())['source_sha256']
 for f,h in originalpins.items():assert sha(ROOT/f)==h
 deps += [ROOT/f for f in originalpins];hashes={str(f.relative_to(ROOT)):sha(f) for f in deps};regressions={str(f):sha(f) for f in (a.v0_regression_geo,a.v8_regression_geo,a.v7_regression_geo)};results={};modes=[('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 with tempfile.TemporaryDirectory(prefix='coh-rigid-v5-') as directory:
  temp=Path(directory)
  def body(h,ver=5,payload=payload):
   compressed=zlib.compress(h);return struct.pack('<4I',len(compressed)+12,0,ver,len(h))+compressed+payload
  (temp/'wrong-policy.geo').write_bytes(body(header,6));malformed=[]
  for name,row,offset,value in [('bad-pack',13,112,0xffffffff),('bad-lod',None,lodstart,7),('duplicate-name',0,60,struct.unpack_from('<I',record,60)[0]),('short-record',0,0,4)]:
   h=bytearray(header);struct.pack_into('<I',h,(records[row][0] if row is not None else 0)+offset,value);path=temp/(name+'.geo');path.write_bytes(body(h));malformed.append(path)
  badstream=bytearray(raw);packed,unpacked,off=struct.unpack_from('<3I',record,116);assert packed==39 and unpacked==65;badstream[bias+4+off:bias+4+off+packed]=b'\xff'*packed;(temp/'bad-stream.geo').write_bytes(badstream)
  nan=bytearray(header);struct.pack_into('<I',nan,lodstart+4,0x7fc00000);(temp/'nan-lod.geo').write_bytes(body(nan));short=bytearray(header);del short[lodstart+ln-148:lodstart+ln];struct.pack_into('<I',short,16,ln-148);(temp/'short-lod.geo').write_bytes(body(short))
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',ROOT/'native-android/include']
  for mode,extra in modes:
   run(['cc',*flags,*extra,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lz','-lm','-lcrypto','-pthread','-o',temp/mode]);results[mode]=json.loads(run([temp/mode,a.actual_geo,temp/'wrong-policy.geo',*malformed,temp/(mode+'.packet'),a.v0_regression_geo,a.v8_regression_geo,a.v7_regression_geo,temp/'bad-stream.geo',temp/'nan-lod.geo',temp/'short-lod.geo'],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  assert results['release']==results['address']==results['undefined'];consumer=original_record32(a.oracle_output,record,names,materials);legacy_lod=lod_oracle(a.oracle_output,lod,count,modes)
  delta=load('v5_original_delta',ROOT/'native-android/tools/material_fixture/original_delta_check.py');(temp/'delta.c').write_bytes(delta.original_c(ROOT/'upstream/ouroboros/Common/seq/anim.c'));run(['cc','-std=c11','-O0','-fno-strict-aliasing','-shared','-fPIC',temp/'delta.c','-o',temp/'delta.so']);lib=C.CDLL(str(temp/'delta.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int];decoded=[];channels=[]
  for channel in range(4):
   packed,unpacked,off=struct.unpack_from('<3I',record,104+channel*12);data=payload[off:off+(packed or unpacked)];data=zlib.decompress(data) if packed else data;assert len(data)==unpacked;count=4 if channel==0 else 10;stride=2 if channel==3 else 3;out=C.create_string_buffer(count*stride*4);encoded=C.create_string_buffer(data+b'\0'*16);assert lib.uncompressDeltas(out,encoded,stride,count,int(channel==0))==len(data);decoded.append(struct.unpack('<'+('I' if channel==0 else 'f')*(count*stride),out.raw));channels.append(dict(channel=channel,packed_bytes=packed,decoded_delta_bytes=unpacked))
  expected=bytearray()
  for part in range(2):
   for vertex in range(10):
    uv=decoded[3][vertex*2:vertex*2+2];v=struct.unpack('<f',struct.pack('<f',1-uv[1]))[0];expected+=struct.pack('<14f',*decoded[1][vertex*3:vertex*3+3],*decoded[2][vertex*3:vertex*3+3],uv[0],v,uv[0],v,1,1,1,1)
   expected+=struct.pack('<6I',*decoded[0][part*6:part*6+6])
  for mode in results:assert (temp/(mode+'.packet')).read_bytes()==expected
  assert hashes=={str(f.relative_to(ROOT)):sha(f) for f in deps} and sha(a.actual_geo)==pin['sha256'];assert regressions=={str(f):sha(f) for f in (a.v0_regression_geo,a.v8_regression_geo,a.v7_regression_geo)}
  proof=dict(passed=not a.require_original32 or consumer['original_consumer_executed'],original32_required=a.require_original32,scope='Explicit v5 CPU opt-in with authentic compressed positions/two partitions, unchanged original delta consumer and executed unchanged legacy LOD wire consumer. Materials fixtures only.',source_sha256=hashes,regression_input_sha256=regressions,actual_body=pin,modes=results,original_readModel=consumer,original_legacy_lod=legacy_lod,channels=channels,packet_sha256=hashlib.sha256(expected).hexdigest(),packet_bytes=len(expected),original_delta_scalar_count=92,original_delta_sha256_lf=delta.FUNCTION_SHA,default_policy_unchanged=True,client_lod_applied=False,client_materials_available=False,source_generation_admitted=False,world_authority=False,android_executed=False,leak_sanitizer=False)
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':proof['passed'],'modes':results,'original32executed':consumer['original_consumer_executed'],'original_lod_records':legacy_lod['active_lod_records']}))
  if not proof['passed']:raise SystemExit(1)
if __name__=='__main__':main()
