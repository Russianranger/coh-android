#!/usr/bin/env python3
"""Explicit v7 actual streams/unchanged source delta consumer; fixture materials."""
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
 # Reuse the frozen original32 harness declarations/function extraction. Only
 # the invoked version and expected facts differ; readModel itself is untouched.
 legacy=load('v7_original32_harness',HERE/'check_rigid_legacy.py')
 text=inspect.getsource(legacy.original_record)
 assert text.count('readModel(&dst,(char*)record,0,names,materials)')==1
 text=text.replace('readModel(&dst,(char*)record,0,names,materials)','readModel(&dst,(char*)record,7,names,materials)')
 start=text.index(' expected=[216,216,');end=text.index(' if facts is not None',start)
 replacement=''' expected=[216,len(record),0,struct.unpack_from('<I',record,4)[0],struct.unpack_from('<I',record,8)[0],struct.unpack_from('<I',record,16)[0],struct.unpack_from('<I',record,20)[0],struct.unpack_from('<I',record,12)[0],struct.unpack_from('<I',record,64)[0],struct.unpack_from('<I',record,28)[0],struct.unpack_from('<I',record,60)[0],struct.unpack_from('<I',record,24)[0],struct.unpack_from('<h',record,224)[0]&0xffffffff,*struct.unpack_from('<9I',record,68)]
 packs=[struct.unpack_from('<3I',record,104+i*12) for i in range(9)]+[(0,0,0)]
 expected+=sum((list(p) for p in packs),[])
'''
 text=text[:start]+replacement+text[end:]
 text=text.replace("'source_model_record_bytes':216","'source_model_record_bytes':len(record),'source_version':7")
 namespace=dict(legacy.__dict__);exec(text,namespace)
 proof=namespace['original_record'](directory,record,names,materials)
 proof['harness_scope']='Unchanged original readModel and original32 disk declarations; invoked v7, expected facts changed only. Execution refusal is retained, never promoted to execution.'
 return proof

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('actual-geo','v0-regression-geo','v8-regression-geo','output','oracle-output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--require-original32',action='store_true')
 a=p.parse_args();assert not a.output.exists() and not a.oracle_output.exists();a.oracle_output.mkdir(parents=True)
 pin=json.loads((HERE/'rigid-v7-pins.json').read_text());assert a.actual_geo.stat().st_size==pin['bytes'] and sha(a.actual_geo)==pin['sha256']
 raw=a.actual_geo.read_bytes();bias,unused,version,n=struct.unpack_from('<4I',raw);assert unused==0 and version==7
 header=zlib.decompress(raw[16:bias+4]);payload=raw[bias+4:];assert len(header)==n
 _,tn,nn,mn=struct.unpack_from('<4I',header);names=header[16+tn:16+tn+nn];materials=header[16+tn+nn:16+tn+nn+mn];at=16+tn+nn+mn;count=struct.unpack_from('<I',header,at+136)[0];at+=140;records=[]
 for _ in range(count):
  size=struct.unpack_from('<I',header,at)[0];assert size>=226 and at+size<=len(header);records.append((at,header[at:at+size]));at+=size
 assert count==5 and at==len(header)
 sources=[HERE/'tests/test_rigid_v7.c',HERE/'coh_wr_rigid.c',HERE/'coh_wr_rigid_v7.c',HERE/'coh_wr_rigid_source.c',HERE.parent/'scenecatalog/coh_resource_geo_source.c',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_geo.c',HERE.parent/'renderer/coh_renderer.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
 deps=sources+[HERE/n for n in ('coh_wr_rigid_v7.h','coh_wr_rigid_internal.h','coh_wr_rigid.h','coh_wr_rigid_source.h','coh_world_render.h','check_rigid_v7.py','check_rigid_legacy.py','rigid-v7-pins.json','rigid-source-pins.json')]+[HERE.parent/'scenecatalog/coh_resource_geo_source.h',HERE.parent/'assets/coh_asset_geo.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'renderer/coh_renderer.h',HERE.parent/'renderer/coh_renderer_shaders.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/tools/material_fixture/original_delta_check.py']
 originalpins=json.loads((HERE/'rigid-source-pins.json').read_text())['source_sha256']
 for f,h in originalpins.items():assert sha(ROOT/f)==h
 deps += [ROOT/f for f in originalpins];hashes={str(f.relative_to(ROOT)):sha(f) for f in deps};results={}
 regression_inputs={str(f):sha(f) for f in (a.v0_regression_geo,a.v8_regression_geo)}
 with tempfile.TemporaryDirectory(prefix='coh-rigid-v7-') as directory:
  temp=Path(directory)
  def body(h,ver=7):
   c=zlib.compress(h);return struct.pack('<4I',len(c)+12,0,ver,len(h))+c+payload
  (temp/'wrong-policy.geo').write_bytes(body(header[:16]+b'\0'*4+header[16:],6))
  malformed=[]
  for name,row,offset,value in [('bad-pack',1,112,0xffffffff),('bad-sibling',0,16,0xffffffff),('duplicate-name',0,60,struct.unpack_from('<I',records[1][1],60)[0]),('short-record',0,0,4)]:
   h=bytearray(header);struct.pack_into('<I',h,records[row][0]+offset,value);path=temp/(name+'.geo');path.write_bytes(body(h));malformed.append(path)
  bad_stream=bytearray(raw);packed,unpacked,offset=struct.unpack_from('<3I',records[1][1],104);assert packed==0 and unpacked==8;bad_stream[bias+4+offset:bias+4+offset+unpacked]=b'\xff'*unpacked;(temp/'bad-stream.geo').write_bytes(bad_stream)
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',ROOT/'native-android/include']
  for mode,extra in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   run(['cc',*flags,*extra,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lz','-lm','-lcrypto','-pthread','-o',temp/mode])
   results[mode]=json.loads(run([temp/mode,a.actual_geo,temp/'wrong-policy.geo',*malformed,temp/(mode+'.packet'),a.v0_regression_geo,a.v8_regression_geo,temp/'bad-stream.geo'],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  assert results['release']==results['address']==results['undefined']
  consumer=original_record32(a.oracle_output,records[1][1],names,materials)
  delta=load('v7_original_delta',ROOT/'native-android/tools/material_fixture/original_delta_check.py');source=ROOT/'upstream/ouroboros/Common/seq/anim.c'
  (temp/'delta.c').write_bytes(delta.original_c(source));run(['cc','-std=c11','-O0','-fno-strict-aliasing','-shared','-fPIC',temp/'delta.c','-o',temp/'delta.so']);lib=C.CDLL(str(temp/'delta.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
  expected=bytearray();metadata=[]
  for row,(_,record) in enumerate(records):
   vertices,triangles=struct.unpack_from('<2I',record,16);decoded=[]
   for channel in range(4):
    packed,unpacked,off=struct.unpack_from('<3I',record,104+channel*12);data=payload[off:off+(packed or unpacked)];data=zlib.decompress(data) if packed else data;assert len(data)==unpacked
    count=triangles if channel==0 else vertices;stride=2 if channel==3 else 3;out=C.create_string_buffer(count*stride*4);encoded=C.create_string_buffer(data+b'\0'*16);assert lib.uncompressDeltas(out,encoded,stride,count,int(channel==0))==len(data)
    decoded.append(struct.unpack('<'+('I' if channel==0 else 'f')*(count*stride),out.raw))
   assert all(index<vertices for index in decoded[0])
   for vertex in range(vertices):
    uv=decoded[3][vertex*2:vertex*2+2];v=struct.unpack('<f',struct.pack('<f',1-uv[1]))[0];expected+=struct.pack('<14f',*decoded[1][vertex*3:vertex*3+3],*decoded[2][vertex*3:vertex*3+3],uv[0],v,uv[0],v,1,1,1,1)
   expected+=struct.pack('<'+'I'*len(decoded[0]),*decoded[0]);nameoff=struct.unpack_from('<I',record,60)[0];metadata.append(dict(row=row,name=names[nameoff:].split(b'\0')[0].decode(),vertices=vertices,triangles=triangles,grid_unpack_bytes=struct.unpack_from('<I',record,104+7*12+4)[0],reduction_unpack_bytes=struct.unpack_from('<I',record,104+8*12+4)[0],autolod_f32=struct.unpack_from('<3f',record,212)))
  for mode in results:assert (temp/(mode+'.packet')).read_bytes()==expected
  assert hashes=={str(f.relative_to(ROOT)):sha(f) for f in deps} and sha(a.actual_geo)==pin['sha256']
  assert regression_inputs=={str(f):sha(f) for f in (a.v0_regression_geo,a.v8_regression_geo)}
  proof=dict(passed=not a.require_original32 or consumer['original_consumer_executed'],original32_required=a.require_original32,scope='Explicit v7 CPU opt-in with actual five-model body streams and fixture materials; original32 readModel compile/layout and execution status recorded separately',source_sha256=hashes,regression_input_sha256=regression_inputs,actual_body=pin,models=metadata,modes=results,original_readModel=consumer,original_delta_sha256_lf=delta.FUNCTION_SHA,packet_sha256=hashlib.sha256(expected).hexdigest(),packet_bytes=len(expected),original_delta_scalar_count=sum(m['vertices']*8+m['triangles']*3 for m in metadata),default_policy_unchanged=True,client_reductions_applied=False,client_materials_available=False,source_generation_admitted=False,world_authority=False,android_executed=False,leak_sanitizer=False)
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':proof['passed'],'modes':results,'original32executed':consumer['original_consumer_executed']}))
  if not proof['passed']:raise SystemExit(1)
if __name__=='__main__':main()
