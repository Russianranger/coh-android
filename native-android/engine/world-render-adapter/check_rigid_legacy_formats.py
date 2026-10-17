#!/usr/bin/env python3
"""Actual v2/v3/v4 records/streams with original readModel/delta/LOD consumers."""
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

def expected_facts(version,r):
 if version==2:
  facts=[216,216,struct.unpack_from('<I',r,0)[0],struct.unpack_from('<I',r,4)[0],struct.unpack_from('<I',r,12)[0],*struct.unpack_from('<2I',r,28),struct.unpack_from('<I',r,20)[0],struct.unpack_from('<I',r,84)[0],struct.unpack_from('<I',r,40)[0],struct.unpack_from('<I',r,80)[0],struct.unpack_from('<I',r,36)[0],struct.unpack_from('<h',r,16)[0]&0xffffffff,*struct.unpack_from('<9I',r,92)];packs=[(0,0,0)]*10
  for source,target in enumerate((0,1,2,3,5,6,7)):packs[target]=struct.unpack_from('<3I',r,132+source*12)
  autolod=[0]*3
 else:
  facts=[216,len(r),0,struct.unpack_from('<I',r,4)[0],struct.unpack_from('<I',r,8)[0],*struct.unpack_from('<2I',r,16),struct.unpack_from('<I',r,12)[0],struct.unpack_from('<I',r,64)[0],struct.unpack_from('<I',r,28)[0],struct.unpack_from('<I',r,60)[0],struct.unpack_from('<I',r,24)[0],struct.unpack_from('<h',r,224 if version==4 else 200)[0]&0xffffffff,*struct.unpack_from('<9I',r,68)];packs=[struct.unpack_from('<3I',r,104+i*12) for i in range(8)]+[(0,0,0)]*2;autolod=[0xbf800000]*3
 facts+=sum((list(p) for p in packs),[])+autolod;assert len(facts)==55;return facts

def record32(directory,version,record,names,materials):
 legacy=load('legacy_readmodel_extract',HERE/'check_rigid_legacy.py');text=inspect.getsource(legacy.original_record);text=text.replace('readModel(&dst,(char*)record,0,names,materials)',f'readModel(&dst,(char*)record,{version},names,materials)').replace('U32 facts[52]','U32 facts[55]').replace('int wrote;__asm__','memcpy(facts+52,dst.autolod_dists,12);int wrote;__asm__').replace("struct.unpack('<52I',execution.stdout)","struct.unpack('<55I',execution.stdout)")
 start=text.index(' expected=[216,216,');end=text.index(' if facts is not None',start);text=text[:start]+' expected=expected_facts('+str(version)+',record)\n'+text[end:];text=text.replace("'source_model_record_bytes':216","'source_model_record_bytes':len(record),'source_version':"+str(version)).replace("'metadata_and_pack_scalars_compared':52","'metadata_and_pack_scalars_compared':55");namespace=dict(legacy.__dict__,expected_facts=expected_facts);exec(text,namespace);proof=namespace['original_record'](directory,record,names,materials)
 expected=struct.pack('<55I',*expected_facts(version,record));(directory/'expected-facts.bin').write_bytes(expected);proof['expected_facts_sha256']=hashlib.sha256(expected).hexdigest();proof['expected_bytes']=len(expected);proof['scope']='Original readModel+original32 disk declarations unchanged; exact version and55expected source facts incl autolod values. Refused ELF32 execution remains false.';return proof

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('body-directory','output','oracle-output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--require-original32',action='store_true');a=p.parse_args();assert not a.output.exists() and not a.oracle_output.exists();a.oracle_output.mkdir(parents=True)
 pins=json.loads((HERE/'rigid-legacy-formats-pins.json').read_text());cases=pins['fixtures'];assert len(cases)==35
 sources=[HERE/'tests/test_rigid_legacy_formats.c',HERE/'coh_wr_rigid.c',HERE/'coh_wr_rigid_legacy_formats.c',HERE/'coh_wr_rigid_v7.c',HERE/'coh_wr_rigid_v5.c',HERE/'coh_wr_rigid_source.c',HERE.parent/'scenecatalog/coh_resource_geo_source.c',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_geo.c',HERE.parent/'renderer/coh_renderer.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
 deps=sources+[HERE/n for n in ('coh_wr_rigid_legacy_formats.h','coh_wr_rigid_v7.h','coh_wr_rigid_v5.h','coh_wr_rigid_internal.h','coh_wr_rigid.h','coh_wr_rigid_source.h','coh_world_render.h','check_rigid_legacy_formats.py','check_rigid_legacy.py','check_rigid_v5.py','rigid-legacy-formats-pins.json','rigid-source-pins.json','tests/rigid_legacy_formats_pins.inc')]+[HERE.parent/'scenecatalog/coh_resource_geo_source.h',HERE.parent/'assets/coh_asset_geo.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'renderer/coh_renderer.h',HERE.parent/'renderer/coh_renderer_shaders.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/tools/material_fixture/original_delta_check.py']
 originalpins=json.loads((HERE/'rigid-source-pins.json').read_text())['source_sha256']
 for f,h in originalpins.items():assert sha(ROOT/f)==h
 deps+=[ROOT/f for f in originalpins];hashes={str(f.relative_to(ROOT)):sha(f) for f in deps};inputhashes={str(a.body_directory/f['asset_path']):sha(a.body_directory/f['asset_path']) for f in cases};modes=[('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])];results={};actual=[]
 with tempfile.TemporaryDirectory(prefix='coh-rigid-legacy-formats-') as td:
  temp=Path(td);mut=temp/'mutations';mut.mkdir();parsed=[]
  for k,f in enumerate(cases):
   raw=(a.body_directory/f['asset_path']).read_bytes();assert len(raw)==f['bytes'] and hashlib.sha256(raw).hexdigest()==f['sha256'];bias,unused,version,n=struct.unpack_from('<4I',raw);assert unused==0 and version==f['version'];h=zlib.decompress(raw[16:bias+4]);assert len(h)==n;payload=raw[bias+4:];t,nn,mn,ln=struct.unpack_from('<4I',h,4);names=h[20+t:20+t+nn];materials=h[20+t+nn:20+t+nn+mn];lodstart=20+t+nn+mn;lod=h[lodstart:lodstart+ln];mh=lodstart+ln;count=struct.unpack_from('<I',h,mh+136)[0];at=mh+140;records=[]
   for row in range(count):size=216 if version==2 else struct.unpack_from('<I',h,at)[0];records.append((at,h[at:at+size]));at+=size
   assert at==len(h) and len(lod)>=count*148;record=records[f['disk_row']][1];nameoff=struct.unpack_from('<I',record,80 if version==2 else 60)[0];assert names[nameoff:].split(b'\0')[0].decode()==f['model'];packoff=132 if version==2 else 104;parsed.append((raw,bias,h,payload,names,materials,lod,count,records,record,packoff))
   def body(header,ver=version):
    compressed=zlib.compress(header);return struct.pack('<4I',len(compressed)+12,0,ver,len(header))+compressed+payload
   channel=bytearray(raw);packed,decoded,off=struct.unpack_from('<3I',record,packoff);channel[bias+4+off:bias+4+off+(packed or decoded)]=b'\xff'*(packed or decoded);(mut/f'{k}-bad-channel.geo').write_bytes(channel)
   for name,offset,value in [('bad-pack',records[f['disk_row']][0]+packoff+8,0xffffffff),('bad-lod',lodstart,7),('nan-lod',lodstart+4,0x7fc00000),('unsupported-pivot',records[f['disk_row']][0]+(84 if version==2 else 64),4)]:
    altered=bytearray(h);struct.pack_into('<I',altered,offset,value);(mut/f'{k}-{name}.geo').write_bytes(body(altered))
   short=bytearray(h);del short[lodstart+ln-148:lodstart+ln];struct.pack_into('<I',short,16,ln-148);(mut/f'{k}-short-lod.geo').write_bytes(body(short))
   duplicate=bytearray(h);duplicate[lodstart+ln:lodstart+ln]=lod[:148];struct.pack_into('<I',duplicate,16,ln+148);struct.pack_into('<I',duplicate,mh+148+136,count+1);duplicate+=record;(mut/f'{k}-duplicate-model.geo').write_bytes(body(duplicate));(mut/f'{k}-wrong-layout.geo').write_bytes(body(h,3 if version in (2,4) else 4))
   if version==2:
    flagged=bytearray(h);struct.pack_into('<I',flagged,records[f['disk_row']][0],1);(mut/f'{k}-legacy-flags.geo').write_bytes(body(flagged))
   if version==4:
    skipped=bytearray(h);skipped[records[f['disk_row']][0]+200:records[f['disk_row']][0]+224]=b'\xff'*24;(mut/f'{k}-obsolete-slots.geo').write_bytes(body(skipped))
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',ROOT/'native-android/include']
  for mode,extra in modes:
   binary=temp/mode;out=temp/(mode+'-packets');out.mkdir();run(['cc',*flags,*extra,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lz','-lm','-lcrypto','-pthread','-o',binary]);results[mode]=json.loads(run([binary,a.body_directory,out,mut],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  assert results['release']==results['address']==results['undefined'];delta=load('legacy_formats_delta',ROOT/'native-android/tools/material_fixture/original_delta_check.py');(temp/'delta.c').write_bytes(delta.original_c(ROOT/'upstream/ouroboros/Common/seq/anim.c'));run(['cc','-std=c11','-O0','-fno-strict-aliasing','-shared','-fPIC',temp/'delta.c','-o',temp/'delta.so']);lib=C.CDLL(str(temp/'delta.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int];v5=load('legacy_lod_harness',HERE/'check_rigid_v5.py');lod_proofs={}
  for k,(f,data) in enumerate(zip(cases,parsed)):
   raw,bias,h,payload,names,materials,lod,count,records,record,packoff=data;version=f['version'];oracle=a.oracle_output/str(k);oracle.mkdir();consumer=record32(oracle,version,record,names,materials)
   if f['asset_path'] not in lod_proofs:
    directory=a.oracle_output/('lod-case'+str(k));directory.mkdir();text=inspect.getsource(v5.lod_oracle).replace('unpackLODInfo(raw,(int)n,(int)count,5)',f'unpackLODInfo(raw,(int)n,(int)count,{version})');namespace=dict(v5.__dict__);exec(text,namespace);lod_proofs[f['asset_path']]=namespace['lod_oracle'](directory,lod,count,modes);lod_proofs[f['asset_path']]['invoked_source_version']=version
   decoded=[];channels=[]
   for channel in range(4):
    packed,n,off=struct.unpack_from('<3I',record,packoff+12*channel);encoded=payload[off:off+(packed or n)];encoded=zlib.decompress(encoded) if packed else encoded;assert len(encoded)==n;items=f['triangles'] if channel==0 else f['vertices'];stride=2 if channel==3 else 3;out=C.create_string_buffer(items*stride*4);source=C.create_string_buffer(encoded+b'\0'*16);assert lib.uncompressDeltas(out,source,stride,items,int(channel==0))==len(encoded);decoded.append(struct.unpack('<'+('I' if channel==0 else 'f')*(items*stride),out.raw));channels.append(dict(channel=channel,packed_bytes=packed,delta_bytes=n))
   expected=bytearray();first=0
   for texid,tris,name in f['source_observations'][0]['texture_partitions']:
    for vertex in range(f['vertices']):
     u,v=decoded[3][vertex*2:vertex*2+2];v=struct.unpack('<f',struct.pack('<f',1-v))[0];expected+=struct.pack('<14f',*decoded[1][vertex*3:vertex*3+3],*decoded[2][vertex*3:vertex*3+3],u,v,u,v,1,1,1,1)
    indices=decoded[0][first*3:(first+tris)*3];assert len(indices)==tris*3 and all(i<f['vertices'] for i in indices);expected+=struct.pack('<'+'I'*len(indices),*indices);first+=tris
   assert first==f['triangles']
   for mode,_ in modes:
    assert (temp/(mode+'-packets')/(str(k)+'.packet')).read_bytes()==expected
    if version==4:assert (temp/(mode+'-packets')/(str(k)+'-skipped.packet')).read_bytes()==expected
   actual.append(dict(fixture=f,original_readModel=consumer,channels=channels,packet_bytes=len(expected),packet_sha256=hashlib.sha256(expected).hexdigest(),original_delta_scalars=f['vertices']*8+f['triangles']*3,v4_obsolete_slots=struct.unpack_from('<6I',record,200) if version==4 else None))
  assert hashes=={str(f.relative_to(ROOT)):sha(f) for f in deps} and inputhashes=={str(a.body_directory/f['asset_path']):sha(a.body_directory/f['asset_path']) for f in cases};passed=not a.require_original32 or all(f['original_readModel']['original_consumer_executed'] for f in actual)
  proof=dict(passed=passed,original32_required=a.require_original32,scope='Separate exactv2/v3/v4 CPU entries, actual compressed streams/fixedlegacy+variable+obsolete slots and original wire consumers; fixture materials only. Portal parts preserved; no portal/material/world authority.',source_sha256=hashes,input_sha256=inputhashes,modes=results,cases=actual,original_legacy_lod=lod_proofs,original_delta_sha256_lf=delta.FUNCTION_SHA,source_body_bridge_extended=False,client_lod_applied=False,client_materials_available=False,source_generation_admitted=False,world_authority=False,android_executed=False,leak_sanitizer=False);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':passed,'modes':results,'original32executed':[c['original_readModel']['original_consumer_executed'] for c in actual]}));
  if not passed:raise SystemExit(1)
if __name__=='__main__':main()
