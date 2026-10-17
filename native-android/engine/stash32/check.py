#!/usr/bin/env python3
import argparse,ctypes as C,hashlib,importlib.util,json,os,struct,subprocess,tempfile,zipfile
from pathlib import Path
import oracle
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
 if r.returncode:raise RuntimeError(str(args)+'\n'+r.stdout+r.stderr)
 return r
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-stash32-')as tmp:
  work=Path(tmp);lib,source=oracle.build(ROOT,work);lines=[];hashes=[];ints=[];tables=[];tableproof=[]
  for n in range(260):
   raw=bytes((i*73+n*19)&255 for i in range(n+3));buf=(C.c_uint8*len(raw)).from_buffer_copy(raw);lines.append('static const struct{uint32_t align;uint8_t bytes['+str(len(raw))+'];}key_'+str(n)+'={0,{'+','.join(map(str,raw))+'}};')
   for offset in range(4):
    for seed in (0,0xfaceface,0xffffffff):
     value=lib.original_string_hash(C.byref(buf,offset),n,seed);hashes.append('{key_'+str(n)+'.bytes+'+str(offset)+','+str(n)+','+str(seed)+'u,'+str(value)+'u}')
  lines.append('static const HashFixture hashes[]={'+',\n'.join(hashes)+'};')
  for n in range(1024):
   key=(n*2654435761)&0xffffffff
   for seed in (0,0xfaceface,0xffffffff):ints.append('{'+str(key)+'u,'+str(seed)+'u,'+str(lib.original_int_hash(key,seed))+'u}')
  lines.append('static const IntFixture integer_hashes[]={'+','.join(ints)+'};')
  # Authentic super palette floats through complete original small-bin reader.
  small=module('stash32_small_input_oracle',HERE/'../costume-inputs/oracle.py');sub=work/'small';sub.mkdir();slib,sproof=small.build(ROOT,sub)
  class Dependency(C.Structure):_fields_=[('path',C.c_char*260),('timestamp',C.c_uint32)]
  class Part(C.Structure):_fields_=[('text',C.c_char*1300),('words',C.c_uint32*7)]
  class Input(C.Structure):_fields_=[('kind',C.c_uint32),('crc',C.c_uint32),('dependencies_count',C.c_uint32),('parts_count',C.c_uint32),('color_count',C.c_uint32),('deps',Dependency*16),('parts',Part*29),('name',C.c_char*260),('colors',(C.c_uint32*3)*256),('sha',C.c_uint8*32),('end',C.c_size_t),('flags',C.c_uint32*3)]
  assert C.sizeof(Input)==slib.original_result_size()
  archive=HERE/'../entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip';assert oracle.sha(archive.read_bytes())=='350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241'
  with zipfile.ZipFile(archive)as z:raw=z.read('data/bin/supergroupColors.bin')
  assert oracle.sha(raw)=='e5676ebbccc380f9d69322ef6750332b0b7e7a46d915bdfb591322862d22cb75';rb=(C.c_uint8*len(raw)).from_buffer_copy(raw);projection=Input();wire=(C.c_uint8*65536)();end=C.c_uint();slib.original_decode.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.POINTER(C.c_uint)];assert slib.original_decode(2,rb,len(raw),92,0,C.byref(projection),wire,C.byref(end))==len(raw);assert projection.color_count==160
  palette=[]
  for row in projection.colors[:projection.color_count]:
   floats=[struct.unpack('<f',struct.pack('<I',v))[0]for v in row];assert all(0<=v<=255 for v in floats);palette.append(lib.getRGBAFromVec3((C.c_float*3)(*floats)))
  scenarios=[]
  for n in (0,1,5,6,7,12,24,48,96,512,1024,2048,4096):
   keys=[((i*2654435761)^0x712e31)&0xffffffff for i in range(n)]
   if n>12:keys[3]=0;keys[7]=keys[1];keys[-1]=0xfffffffe
   scenarios.append((keys,8,False))
  scenarios.extend([(palette,128,True),(palette+palette,128,False),([0,1,0x80000000,0xffffffff,0xfffffffe,1],65536,False)])
  for n,(keys,initial,actual)in enumerate(scenarios):
   rawkeys=(C.c_uint32*max(1,len(keys)))(*keys);slots=(C.c_uint32*65536)();stats=(C.c_uint32*5)();assert lib.original_build(rawkeys,len(keys),initial,slots,stats);entries=[(i,v)for i,v in enumerate(slots[:stats[0]])if v];assert len(entries)==stats[1]
   lines.append('static const uint32_t table_keys_'+str(n)+'[]={'+(','.join(str(v)+'u'for v in keys)if keys else'0')+'};');lines.append('static const SlotPair table_slots_'+str(n)+'[]={'+(','.join('{'+str(i)+','+str(v)+'u}'for i,v in entries)if entries else'{0,0}')+'};');tables.append('{table_keys_'+str(n)+','+str(len(keys))+','+str(initial)+',table_slots_'+str(n)+','+str(len(entries))+','+','.join(str(v)for v in stats)+'}');tableproof.append({'key_count':len(keys),'initial':initial,'max_size':stats[0],'valid':stats[1],'resizes':stats[2],'duplicates':stats[3],'zeros':stats[4],'authentic_super_palette_prefix_only':actual,'keys_sha256':oracle.sha(b''.join(struct.pack('<I',v)for v in keys)),'slots_sha256':oracle.sha(bytes(slots)[:stats[0]*4])})
  lines.append('static const TableFixture tables[]={'+',\n'.join(tables)+'};');fixtures='\n'.join(lines)+'\n';(work/'fixtures.h').write_text(fixtures)
  proof={'schema':1,'passed':True,'source_head':run(['git','rev-parse','HEAD'],cwd=ROOT).stdout.strip(),'original_source':source,'authentic_palette_small_input_source':sproof,'string_hash_cases':len(hashes),'integer_hash_cases':len(ints),'table_cases':tableproof,'fixtures_sha256':oracle.sha(fixtures.encode()),'native':{}}
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),HERE/'coh_stash32.c',HERE/'test_stash.c','-o',binary]);env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1';r=json.loads(run([binary],env=env).stdout);r['binary_sha256']=oracle.sha(binary.read_bytes());proof['native'][mode]=r
  run(['cc','-std=c99','-O2','-fstack-usage','-c',HERE/'coh_stash32.c','-o',work/'stash.o']);stack=[]
  for line in (work/'stash.su').read_text().splitlines():
   name,n,kind=line.split('\t');assert kind in('static','dynamic,bounded');stack.append({'function':name,'bytes':int(n),'kind':kind})
  total=sum(s['bytes']for s in stack);assert total<=16384;proof['native_stack']={'conservative_sum_bytes':total,'reserve_bytes':16384,'frames':stack}
  (work/'header.cpp').write_text('#include "'+str(HERE/'coh_stash32.h')+'"\nint main(){return coh_stash32_int_hash(1,0)==0;}\n');run(['c++','-std=c++17','-Wall','-Wextra','-Werror',work/'header.cpp',work/'stash.o','-o',work/'cpp']);run([work/'cpp']);proof['cpp_link_passed']=True
  files=list(HERE.glob('*.c'))+list(HERE.glob('*.h'))+list(HERE.glob('*.py'))+[HERE/'source-pins.json',HERE/'CONTRACT.md',HERE/'../coh_contracts.h',HERE/'../costume-inputs/oracle.py',HERE/'../costume-inputs/source-pins.json',HERE/'../costume-inputs/coh_costume_inputs.h',HERE/'../costume-import/coh_costume_import.h',HERE/'../entities/coh_costume.h',HERE/'../entities/coh_entities.h',HERE/'../replication/coh_replication.h',archive];proof['source_sha256']={str(p.relative_to(HERE)):oracle.sha(p.read_bytes())for p in files};proof.update(whole_original_win32_abi_executed=False,original_ub4_width_modeled=32,original_constructor_executed=False,complete_costume_builder_executed=False,complete_original_palette=False,authentic_global_stash=False,actor_authority=False,android_built=False,server_capture_executed=False,leak_sanitizer_executed=False)
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'native':proof['native'],'tables':tableproof,'output':str(a.output)}))
if __name__=='__main__':main()
