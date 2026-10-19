#!/usr/bin/env python3
"""Bounded source-type/getter witness producer tests; never run a MapServer."""
import argparse,hashlib,importlib.util,json,os,re,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(args,work,stem,env=None):
 result=subprocess.run(list(map(str,args)),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
 for kind,data in [('command.json',json.dumps(list(map(str,args)))),('stdout',result.stdout),('stderr',result.stderr)]: (work/(stem+'.'+kind)).write_text(data)
 if result.returncode:raise RuntimeError(f'{stem} exit{result.returncode}\n'+result.stderr[-4000:]+result.stdout[-1000:])
 return result
class Reader:
 def __init__(self,data):self.data=data;self.at=0
 def take(self,n):
  if n>len(self.data)-self.at:raise ValueError('bounds')
  v=self.data[self.at:self.at+n];self.at+=n;return v
 def word(self):return struct.unpack('<I',self.take(4))[0]
 def string(self):
  n=struct.unpack('<H',self.take(2))[0];return None if n==65535 else self.take(n)
def decode(data,maximum,meta,source_id):
 r=Reader(data);assert r.take(8)==b'COHBW1\0\0'
 header=[r.word()for _ in range(8)]
 assert header==[1,3 if maximum else 2,2,0,2,29 if maximum else 1,0,0],header
 for key in ['source_sha256','build_sha256','profile_sha256','run_sha256']:assert r.take(32)==bytes.fromhex(source_id if key=='source_sha256'else meta[key])
 assert r.string()==b'/owned/profile/data/bin/BodyParts.bin'
 for i in range(29 if maximum else 1):
  expected=[i if i else 0xffffffff,0x80000000,i,2 if i%2 else 1,(-i-1)&0xffffffff,i+226]
  assert[r.word()for _ in range(6)]==expected
  for j in range(5):
   expected=bytes([97+(i+j)%26])*259 if maximum else None if j==0 else b''if j==1 else f'part{i}-string{j}'.encode()
   assert r.string()==expected,(i,j)
 assert r.at==len(data)
 return{'bytes':len(data),'sha256':sha(data),'rows':29 if maximum else 1,'all_fields_independently_matched':True}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();work=a.work.resolve();work.mkdir(parents=True,exist_ok=False)
 stage=module('body_witness_stage',HERE/'stage_body_witness.py');loader=module('body_witness_loader',HERE/'../body-catalog/body_part_loader_provider.py')
 meta={'build_sha256':'01'*32,'profile_sha256':'02'*32,'run_sha256':'03'*32}
 names={stage.BODY,stage.PARSER,stage.SERVER,stage.BODY_H,stage.BONES_H,*stage.load('stage').FILES}
 originals={n:(ROOT/'upstream/ouroboros'/n).read_bytes()for n in sorted(names)}
 inputs=list(HERE.glob('*body_witness*'))+[HERE/'BODY_RUNTIME_WITNESS.md',ROOT/'.github/workflows/native-body-provenance-witness.yml']+[HERE/'stage.py',HERE/'source-pins.json',HERE/'../body-catalog/struct-clear-source-pins.json',ROOT/loader.BODY_H,ROOT/loader.BONES_H]
 before={str(path.relative_to(ROOT)):sha(path.read_bytes())for path in inputs}
 output,overlay=stage.render(originals,meta)
 combined,cproof=stage.render(originals,meta,{'generation':9,'inventory_sha256':'04'*32,'profile_sha256':'05'*32,'run_sha256':'06'*32})
 assert combined[stage.SERVER].count(b'coh_source_body_witness_snapshot_startup()!=0')==1
 assert combined[stage.SERVER].count(b'coh_source_costume_snapshot_startup()!=0')==1
 assert combined[stage.SERVER].index(b'coh_source_body_witness_snapshot_startup()!=0')<combined[stage.SERVER].index(b'coh_source_costume_snapshot_startup()!=0')
 controls=0
 for field in ['build_sha256','profile_sha256','run_sha256','generation']:
  bad=dict(meta);bad[field]='00'*32
  try:stage.render(originals,bad)
  except ValueError:controls+=1
  else:raise AssertionError(field)
 for name in (stage.BODY,stage.PARSER,stage.SERVER,stage.BODY_H,stage.BONES_H):
  bad=dict(originals);bad[name]+=b'\n'
  try:stage.render(bad,meta)
  except ValueError:controls+=1
  else:raise AssertionError(name)
 for name,data in output.items():target=work/'overlay'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 # Exact original full structs/enum and unchanged original getter are reused.
 bodies=(ROOT/loader.BODY_H).read_text();bones=(ROOT/loader.BONES_H).read_text()
 declarations='\n'.join([re.search(r'typedef\s+enum\s+BoneId\s*\{.*?\}\s*BoneId\s*;',bones,re.S)[0],re.search(r'typedef struct BodyPart\s*\{.*?\}\s*BodyPart\s*;',bodies,re.S)[0],re.search(r'typedef struct\s*\{\s*const BodyPart\*\* bodyParts;\s*\}\s*BodyPartList\s*;',bodies,re.S)[0]])
 getter=loader.extract(originals[stage.BODY].decode().replace('\r\n','\n'),'GetBodyPartCount')
 entry=loader.extract(output[stage.BODY].decode(),'bpReadBodyPartFiles')
 original_entry=loader.extract(originals[stage.BODY].decode().replace('\r\n','\n'),'bpReadBodyPartFiles')
 assert entry.replace('    coh_body_witness_begin(&bodyPartList);\n','').replace('    coh_body_witness_end();\n','')==original_entry
 (work/'coh_body_witness_configuration.inc').write_bytes(output['Common/gameData/coh_body_witness_configuration.inc'])
 for local in ('source_body_witness.inc','source_body_witness_sink.inc'):(work/('coh_'+local)).write_bytes((HERE/local).read_bytes())
 code='''#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
typedef uint8_t U8;
'''+declarations+'''
static BodyPartList bodyPartList;
static int fixture_count;
#define eaSize(p) fixture_count
'''+getter+'''
static int diag_open(const char*,int,int);
static int diag_write(int,const void*,unsigned);
static int diag_close(int);
static int diag_unlink(const char*);
#define COH_BODY_OPEN diag_open
#define COH_BODY_WRITE diag_write
#define COH_BODY_CLOSE diag_close
#define COH_BODY_UNLINK diag_unlink
#include "coh_source_body_witness.inc"
#include "coh_source_body_witness_sink.inc"
static int fixture_loader(const char*,const char*,const char*,const char*,int,void*,void*,size_t,void*,void*,int(*)(void*,void*),void*,void*);
static int ParseBoneNames(void*a,void*b){(void)a;(void)b;return 1;}
#define ParseBodyPartBegin NULL
#define ParserLoadFilesShared fixture_loader
'''+entry+(HERE/'test_body_witness.c').read_text()
 (work/'producer-fixture.c').write_text(code)
 proof={'schema':'coh-body-runtime-provenance-witness-host-v1','source_head':run(['git','-C',ROOT,'rev-parse','HEAD'],work,'head').stdout.strip(),'scope':'Host new read-only producer, exact original BodyPart/BoneId declarations + getter + staged entry, fixture loader routing and POSIX sink. Prepared original Map overlay is NOT target compiled/executed.','source_overlay':overlay,'overlay_composition':{'existing_costume_export_composed':True,'body_snapshot_before_costume_export':True,'generation_in_body_metadata':False,'negative_stage_controls':controls},'original_getter_sha256_lf':sha(getter.encode()),'original_entry_sha256_lf':sha(original_entry.encode()),'native':{}}
 compiler=run(['cc','--version'],work,'compiler').stdout;proof['compiler_sha256']=sha(compiler.encode())
 for mode,flags in [('release',['-O2','-fstack-usage']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  target=work/mode;target.mkdir();binary=target/'body-witness';env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
  run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),work/'producer-fixture.c','-o',binary],target,'compile')
  result=run([binary,target],target,'native',env)
  # Exactly one intentionally retained-partial cleanup marker; test then removes it.
  assert result.stderr.count('COH_NATIVE_BODY_WITNESS_CLEANUP_FAILED')==1
  assert result.stderr.count('COH_NATIVE_BODY_WITNESS_CLOSE_FAILED')==1
  assert len(result.stderr.splitlines())==2
  native=json.loads(result.stdout.splitlines()[-1]);native['binary_sha256']=sha(binary.read_bytes());native['intentional_unlink_failure_marker_verified']=True
  native['independent_payloads']={name:decode((target/(name+'.bin')).read_bytes(),name=='max',meta,overlay['source_closure_id'])for name in ('min','max')}
  assert sorted(p.name for p in target.glob('*.bin'))==['max.bin','min.bin']
  proof['native'][mode]=native
 stacks=[]
 for path in work.rglob('*.su'):
  for line in path.read_text().splitlines():
   fields=line.split('\t');stacks.append({'function':fields[0],'bytes':int(fields[1]),'kind':fields[2]})
 # main fixture has a large saved-buffer oracle, excluded from production stack.
 producer_frames=[s for s in stacks if any(n in s['function']for n in ('coh_body_witness_','coh_source_body_witness_','GetBodyPartCount','bpReadBodyPartFiles'))]
 assert all(s['kind']=='static'for s in producer_frames)
 assert sum(s['bytes']for s in producer_frames)<=4096
 proof['memory']={'producer_owned_static_bytes':proof['native']['release']['owned_static_bytes'],'producer_heap_allocations':0,'producer_stack_reserve_bytes':4096,'all_selected_frame_sum_conservative_bytes':sum(s['bytes']for s in producer_frames),'frames':stacks,'borrowed_engine_body_owner_not_measured':True,'whole_Map_RSS_or_PSS':'unavailable','device_RSS_or_PSS':'unavailable','external_libc_sanitizer_stack_or_allocator_closure':False,'leak_sanitizer_executed':False}
 assert originals=={n:(ROOT/'upstream/ouroboros'/n).read_bytes()for n in originals}
 assert before=={str(path.relative_to(ROOT)):sha(path.read_bytes())for path in inputs}
 proof.update(passed=True,source_stable_before_after=True,input_sha256=before,current_Map_runtime_observed=False,actual_Map_target_compiled=False,actual_Map_runtime_executed=False,runtime_body_catalog_admitted=False,dictionary_generation_admitted=False,complete_character=False,actor_authority=False,application_ACK=False,android_built=False,physical_Thor_test=False)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'native':{k:{x:v[x]for x in('checks','source_load_transactions','repeated_create_destroy','owned_static_bytes')}for k,v in proof['native'].items()},'output':str(a.output)}))
if __name__=='__main__':main()
