#!/usr/bin/env python3
import argparse,ctypes as C,hashlib,json,os,subprocess,tempfile,zipfile
from pathlib import Path
import oracle
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
 if r.returncode:raise RuntimeError(str(args)+'\n'+r.stdout+r.stderr)
 return r
def main():
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);args=a.parse_args();archive=HERE/'../entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip';assert oracle.sha(archive.read_bytes())=='350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241'
 with tempfile.TemporaryDirectory(prefix='coh-costume-inputs-')as tmp:
  work=Path(tmp);lib,proof=oracle.build(ROOT,work);lib.original_decode.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.POINTER(C.c_uint)];lines=[];rows=[];cases=[]
  with zipfile.ZipFile(archive)as z:
   for kind,name,begin,sha in [(1,'BodyParts.bin',64,'b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb'),(2,'supergroupColors.bin',92,'e5676ebbccc380f9d69322ef6750332b0b7e7a46d915bdfb591322862d22cb75')]:
    original=z.read('data/bin/'+name);assert oracle.sha(original)==sha
    for scenario in (0,1):
     source=(C.c_uint8*len(original)).from_buffer_copy(original);projection=(C.c_uint8*lib.original_result_size())();wire=(C.c_uint8*65536)();end=C.c_uint();size=lib.original_decode(kind,source,len(original),begin,scenario,projection,wire,C.byref(end));assert end.value==len(original);assert size>0;raw=bytes(wire[:size]);actual=scenario==0
     if actual:assert raw==original
     # Decode every generated original producer fixture through the whole original consumer again.
     source=(C.c_uint8*len(raw)).from_buffer_copy(raw);again=(C.c_uint8*65536)();assert lib.original_decode(kind,source,len(raw),begin,0,projection,again,C.byref(end))==len(raw);assert end.value==len(raw)and bytes(again[:len(raw)])==raw
     n=len(rows);lines.append('static const unsigned char wire_'+str(n)+'[]={'+','.join(map(str,raw))+'};');pairs=[(i,b)for i,b in enumerate(projection)if b];lines.append('static const Pair expected_'+str(n)+'[]={'+','.join('{'+str(i)+','+str(b)+'}'for i,b in pairs)+'};');rows.append('{wire_'+str(n)+',sizeof(wire_'+str(n)+'),'+str(kind)+',expected_'+str(n)+','+str(len(pairs))+','+str(len(projection))+','+str(int(actual))+'}');cases.append({'kind':kind,'input':name,'scenario':scenario,'actual_verified_donor':actual,'bytes':len(raw),'sha256':oracle.sha(raw),'whole_original_producer_consumer_roundtrip':True,'expected_projection_sha256':oracle.sha(bytes(projection))})
  fixtures='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+','.join(rows)+'};\n';(work/'fixtures.h').write_text(fixtures);proof={'schema':1,'passed':True,'source_head':run(['git','rev-parse','HEAD'],cwd=ROOT).stdout.strip(),'source_oracle':proof,'cases':cases,'fixtures_sha256':oracle.sha(fixtures.encode()),'native':{}}
  sources=[HERE/'coh_costume_inputs.c',HERE/'test_inputs.c']
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lcrypto','-lm','-o',binary]);env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1';r=json.loads(run([binary],env=env).stdout);r['binary_sha256']=oracle.sha(binary.read_bytes());proof['native'][mode]=r
  run(['cc','-std=c99','-O2','-fstack-usage','-c',sources[0],'-o',work/'input.o']);stack=[]
  for line in (work/'input.su').read_text().splitlines():
   name,n,kind=line.split('\t');assert kind in('static','dynamic,bounded');stack.append({'function':name,'bytes':int(n),'kind':kind})
  total=sum(s['bytes']for s in stack);assert total<=16384;proof['native_stack']={'conservative_sum_bytes':total,'reserve':16384,'frames':stack,'external_digest_stack_included':False}
  (work/'header.cpp').write_text('#include "'+str(HERE/'coh_costume_inputs.h')+'"\nint main(){return COH_COSTUME_INPUT_PART_MAX!=29;}\n');run(['c++','-std=c++17','-Wall','-Wextra','-Werror',work/'header.cpp',work/'input.o','-lm','-o',work/'cpp']);run([work/'cpp']);proof['cpp_link_passed']=True
  files=list(HERE.glob('*.c'))+list(HERE.glob('*.h'))+list(HERE.glob('*.py'))+[HERE/'CONTRACT.md',HERE/'source-pins.json',HERE/'../costume-import/coh_costume_import.h',HERE/'../entities/coh_costume.h',HERE/'../entities/coh_entities.h',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',archive]
  proof['source_sha256']={str(p.relative_to(HERE)):oracle.sha(p.read_bytes())for p in files};proof.update(actual_verified_donor_bins_decoded=True,original_crc_recomputed=False,original_callbacks_applied=False,whole_original_engine_or_win32_abi=False,authentic_stash_slots=False,actor_authority=False,android_built=False,real_server_executed=False,external_crypto_sanitizer_or_stack_closure=False,leak_sanitizer_executed=False)
  args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'native':proof['native'],'output':str(args.output)}))
if __name__=='__main__':main()
