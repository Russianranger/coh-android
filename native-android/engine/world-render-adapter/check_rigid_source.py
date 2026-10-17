#!/usr/bin/env python3
"""Qualify explicit zero-row-preserving rigid source entry, not material authority."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,struct,subprocess,tempfile,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-geo',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 pin=json.loads((HERE/'rigid-source-zero-pins.json').read_text())
 if a.actual_geo.stat().st_size!=pin['bytes'] or sha(a.actual_geo)!=pin['sha256']:raise ValueError('Exact Shop body pin differs')
 raw=a.actual_geo.read_bytes();bias,unused,version,n=struct.unpack_from('<4I',raw);header=zlib.decompress(raw[16:bias+4]);payload=raw[bias+4:]
 if unused or version!=8 or len(header)!=n:raise ValueError('Actual envelope differs')
 _,t,ns,ms=struct.unpack_from('<4I',header);names=header[16+t:16+t+ns];at=16+t+ns+ms;count=struct.unpack_from('<I',header,at+136)[0];at+=140;records=[]
 for row in range(count):
  size=struct.unpack_from('<I',header,at)[0];records.append(at);at+=size
 if count!=72 or at!=len(header):raise ValueError('Original row envelope differs')
 record=header[records[59]:records[59]+244];off=struct.unpack_from('<I',record,64)[0]
 if names[off:].split(b'\0')[0].decode()!=pin['model']:raise ValueError('Selected exact model/disk row differs')
 duplicate=bytearray(header);struct.pack_into('<I',duplicate,records[34]+64,off);duplicate_packed=zlib.compress(duplicate);duplicate_raw=struct.pack('<4I',len(duplicate_packed)+12,0,8,len(duplicate))+duplicate_packed+payload
 malformed=bytearray(header);struct.pack_into('<I',malformed,records[34]+16,1);packed=zlib.compress(malformed);bad=struct.pack('<4I',len(packed)+12,0,8,len(malformed))+packed+payload
 sources=[HERE/'tests/test_rigid_source.c',HERE/'coh_wr_rigid.c',HERE/'coh_wr_rigid_source.c',HERE.parent/'scenecatalog/coh_resource_geo_source.c',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_geo.c',HERE.parent/'renderer/coh_renderer.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
 deps=[*sources,HERE/'coh_wr_rigid_internal.h',HERE/'coh_wr_rigid.h',HERE/'coh_wr_rigid_source.h',HERE/'check_rigid_source.py',HERE/'rigid-source-zero-pins.json',HERE/'rigid-source-pins.json',HERE.parent/'scenecatalog/coh_resource_geo_source.h',HERE.parent/'assets/coh_asset_geo.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'renderer/coh_renderer.h',HERE.parent/'renderer/coh_renderer_shaders.h',HERE/'coh_world_render.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/tools/material_fixture/original_delta_check.py']
 source_pins=json.loads((HERE/'rigid-source-pins.json').read_text())['source_sha256']
 for path,h in source_pins.items():
  if sha(ROOT/path)!=h:raise ValueError('Original source differs')
 deps += [ROOT/path for path in source_pins];hashes={str(x.relative_to(ROOT)):sha(x) for x in deps};results={}
 with tempfile.TemporaryDirectory(prefix='coh-rigid-source-') as directory:
  temp=Path(directory);(temp/'bad.geo').write_bytes(bad);(temp/'duplicate.geo').write_bytes(duplicate_raw)
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',ROOT/'native-android/include']
  for mode,extra in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   run(['cc',*flags,*extra,*sources,'-lz','-lm','-lcrypto','-pthread','-o',temp/mode]);results[mode]=json.loads(run([temp/mode,a.actual_geo,temp/'bad.geo',temp/'duplicate.geo',temp/(mode+'.packet')],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  spec=importlib.util.spec_from_file_location('source_original_delta',ROOT/'native-android/tools/material_fixture/original_delta_check.py');original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
  (temp/'delta.c').write_bytes(original.original_c(ROOT/'upstream/ouroboros/Common/seq/anim.c'));run(['cc','-std=c11','-O0','-fno-strict-aliasing','-shared','-fPIC',temp/'delta.c','-o',temp/'delta.so']);lib=C.CDLL(str(temp/'delta.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int];decoded=[]
  for channel in range(4):
   packed,unpacked,off=struct.unpack_from('<3I',record,108+channel*12);data=payload[off:off+(packed or unpacked)];data=zlib.decompress(data) if packed else data
   if len(data)!=unpacked:raise ValueError('Source delta channel size')
   count=2 if channel==0 else 4;stride=2 if channel==3 else 3;out=C.create_string_buffer(count*stride*4);encoded=C.create_string_buffer(data+b'\0'*16)
   if lib.uncompressDeltas(out,encoded,stride,count,int(channel==0))!=len(data):raise ValueError('Original delta consumed size differs')
   decoded.append(struct.unpack('<'+('I' if channel==0 else 'f')*(count*stride),out.raw))
  expected=bytearray()
  for vertex in range(4):
   uv=decoded[3][vertex*2:vertex*2+2];v=struct.unpack('<f',struct.pack('<f',1-uv[1]))[0];expected+=struct.pack('<14f',*decoded[1][vertex*3:vertex*3+3],*decoded[2][vertex*3:vertex*3+3],uv[0],v,uv[0],v,1,1,1,1)
  expected+=struct.pack('<6I',*decoded[0])
  for mode in results:
   if (temp/(mode+'.packet')).read_bytes()!=expected:raise ValueError('Original packet differs')
 if hashes!={str(x.relative_to(ROOT)):sha(x) for x in deps} or sha(a.actual_geo)!=pin['sha256']:raise ValueError('Inputs changed')
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':hashes,'source_inputs_unchanged':True,'actual_body':pin,'modes':results,'packet_sha256':hashlib.sha256(expected).hexdigest(),'original_delta_sha256_lf':original.FUNCTION_SHA,'material_fixture_only':True,'source_generation_established':False,'world_authority':False,'android_execution':False},indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()
