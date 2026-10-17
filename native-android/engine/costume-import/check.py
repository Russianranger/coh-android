#!/usr/bin/env python3
"""Pinned source slot oracle + native immutable serialized import qualification."""
import argparse,hashlib,json,os,platform,subprocess,tempfile
from pathlib import Path
import oracle
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCES=[HERE/'coh_costume_import.c',HERE/'../entities/coh_costume.c',HERE/'../replication/coh_replication.c']
def run(args,**kw):
 return subprocess.run(list(map(str,args)),check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
def main():
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);args=a.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-costume-import-') as tmp:
  work=Path(tmp);proof={'schema':1,'passed':True,'source_head':run(['git','rev-parse','HEAD'],cwd=ROOT).stdout.strip(),'source_oracle':oracle.build(ROOT,work),'native':{},'source_sha256':{}}
  sourceid=json.loads((HERE/'source-pins.json').read_text())['source_id'];expected='const uint8_t coh_costume_import_source_id[32]={'+','.join(str(v)for v in bytes.fromhex(sourceid))+'};\n';assert (HERE/'source_id.h').read_text()==expected
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*SOURCES,HERE/'test_import.c','-lcrypto','-lm','-o',binary]);env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1';receipt=json.loads(run([binary],env=env).stdout);receipt['binary_sha256']=oracle.sha(binary.read_bytes());proof['native'][mode]=receipt
  stack=[];excluded=[]
  reachable={'valid','disjoint','nonzero','take','word','sizeok','slots','palette','coh_costume_import','string_table_size','coh_ent_costume_dictionary_load','coh_ent_costume_dictionary_free','coh_ent_costume_dictionary_bytes'}
  for n,source in enumerate(SOURCES):
   run(['cc','-std=c99','-O2','-fstack-usage','-c',source,'-o',work/f'frame{n}.o'])
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    name,n,kind=line.split('\t');assert kind in ('static','dynamic,bounded');(stack if name.rsplit(':',1)[-1] in reachable else excluded).append({'function':name,'bytes':int(n),'kind':kind})
  total=sum(s['bytes']for s in stack);assert total<=16384;proof['native_stack']={'conservative_sum_bytes':total,'reserve_bytes':16384,'frames':stack,'excluded_unreachable_other_costume_wire_parsers':excluded,'external_digest_stack_included':False}
  # C headers and native implementation stay consumable by a C++ coordinator.
  (work/'header.cpp').write_text('#include "'+str(HERE/'coh_costume_import.h')+'"\nint main(){return coh_costume_import_source_id[0]==255;}\n');run(['c++','-std=c++17','-Wall','-Wextra','-Werror',work/'header.cpp',*[work/f'frame{i}.o'for i in range(len(SOURCES))],'-lm','-o',work/'cpp']);run([work/'cpp']);proof['cpp_link_passed']=True;proof['leak_sanitizer']={'executed':False,'reason':'Container LeakSanitizer cannot inspect /proc/2/task and terminates with fatal ptrace/proc error; address checking uses detect_leaks=0. No leak-sanitizer qualification claimed.'}
  files=list(HERE.glob('*.c'))+list(HERE.glob('*.h'))+list(HERE.glob('*.py'))+[HERE/'source-pins.json',HERE/'CONTRACT.md',HERE/'../entities/coh_costume.h',HERE/'../entities/coh_costume.c',HERE/'../entities/coh_entities.h',HERE/'../replication/coh_replication.c',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h']
  for path in files:proof['source_sha256'][str(path.relative_to(HERE))]=oracle.sha(path.read_bytes())
  linked=run(['ldd',work/'release']).stdout;proof['external_crypto']={'linker_output':linked,'headers_version':run(['openssl','version']).stdout.strip(),'runtime_sanitizer_closure':False,'callback_scratch_test_reservation':16384,'scope':'Host test SHA256_Init/Update/Final provider only; native core requires independently qualified caller digest. No allocator interposition or external library sanitizer/stack qualification.'}
  for line in linked.splitlines():
   if 'libcrypto.so' in line and '=>' in line:
    path=Path(line.split('=>',1)[1].strip().split()[0]);proof['external_crypto']['path']=str(path);proof['external_crypto']['sha256']=oracle.sha(path.read_bytes())
  proof.update(android_arm64_built=False,android13_executed=False,physical_thor_qualified=False,real_server_accepted=False,authentic_dictionary_captured=False,actor_authority=False,scope='Bounded integrity import of synthetic source-shaped full slots into existing immutable dictionary; no original whole builder or authentic input capture, no complete entity/actor/ACK.')
  args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'native':proof['native'],'source_cases':proof['source_oracle']['cases'],'output':str(args.output)}))
if __name__=='__main__':main()
