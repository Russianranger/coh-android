#!/usr/bin/env python3
"""Source getter-backed exporter and frozen native importer composition only."""
import argparse,hashlib,importlib.util,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
 if r.returncode:raise RuntimeError(str(args)+'\n'+r.stdout+r.stderr)
 return r
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 source=module('costume_source_import_oracle',HERE/'../costume-import/oracle.py');stage=module('costume_export_stage',HERE/'stage.py');meta={'generation':9,'inventory_sha256':'01'*32,'profile_sha256':'02'*32,'run_sha256':'03'*32}
 with tempfile.TemporaryDirectory(prefix='coh-costume-export-')as tmp:
  work=Path(tmp);proof={'schema':1,'passed':True,'source_head':run(['git','rev-parse','HEAD'],cwd=ROOT).stdout.strip(),'source_oracle':source.build(ROOT,work),'native':{}}
  # Whole actual source getters and body-type table/count from pinned oracle.
  code=(work/'original.c').read_text()+'''\nstatic int part_count=1;
int GetBodyPartCount(void){return part_count;}
cStashTable costume_HashTable,costume_HashTableExtraInfo,costume_PaletteTable;
#include "coh_source_costume_export.inc"
#include <unistd.h>
#include <errno.h>
static unsigned fault_flags;
static int diagnostic_write(int fd,const void*p,unsigned n){if(fault_flags&1)return 0;return (int)write(fd,p,n);}
static int diagnostic_unlink(const char*p){if(fault_flags&2){errno=EACCES;return -1;}return unlink(p);}
#define COH_COSTUME_WRITE diagnostic_write
#define COH_COSTUME_UNLINK diagnostic_unlink
#include "coh_source_costume_sink.inc"
static void fixture(unsigned scenario){
 static StashElementImp storage[3][8];static StashTableImp tables[3];static char longname[261];unsigned i;
 memset(storage,0,sizeof(storage));for(i=0;i<3;i++){tables[i].uiMaxSize=8;tables[i].uiValidValues=i?1:2;tables[i].pStorage=storage[i];tables[i].eKeyType=i==2;}
 storage[0][2].key.pKey=(void*)"";storage[0][5].key.pKey=(void*)"SM_Chest.geo";storage[1][1].key.pKey=(void*)"Chest";storage[2][6].key.pKey=(void*)(uintptr_t)0xff030201U;
 storage[0][3].key.pKey=(void*)"Deleted";storage[0][3].value.pValue=STASH_TABLE_DELETED_SLOT_VALUE;
 part_count=scenario==3?30:1;
 if(scenario==1)tables[0].uiValidValues++;
 if(scenario==2)tables[1].uiMaxSize=7;
 if(scenario==4){memset(longname,'a',260);longname[260]=0;storage[0][5].key.pKey=longname;}
 costume_HashTable=&tables[0];costume_HashTableExtraInfo=&tables[1];costume_PaletteTable=&tables[2];
}
int diagnostic_export(unsigned scenario,size_t cap,unsigned char*out,size_t*written){fixture(scenario);return coh_source_costume_export(out,cap,9,coh_costume_export_inventory,coh_costume_export_profile,coh_costume_export_run,written);}
int diagnostic_sink(const char*path){fixture(0);if(setenv("COH_NATIVE_COSTUME_OUTPUT",path,1))return 1;return coh_source_costume_snapshot_startup();}
int diagnostic_sink_fault(const char*path,unsigned flags){fault_flags=flags;int rc=diagnostic_sink(path);fault_flags=0;return rc;}
'''
  (work/'original.c').write_text('#define _POSIX_C_SOURCE 200809L\n'+code)
  for name,local in [('coh_source_costume_export.inc','source_costume_export.inc'),('coh_source_costume_sink.inc','source_costume_sink.inc'),('coh_costume_export_source_id.inc','source_id.inc')]:
   (work/name).write_bytes((HERE/local).read_bytes())
  expected=(HERE/'../costume-import/source_id.h').read_text().replace('const uint8_t coh_costume_import_source_id','static const unsigned char coh_costume_export_source_id');assert (HERE/'source_id.inc').read_text()==expected
  (work/'coh_costume_export_configuration.inc').write_bytes(stage.configuration(meta));sources=[work/'original.c',HERE/'../costume-import/coh_costume_import.c',HERE/'../entities/coh_costume.c',HERE/'../replication/coh_replication.c',HERE/'test_export.c']
  for name,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=work/name;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-lcrypto','-o',binary]);env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1';out=run([binary,work],env=env).stdout.splitlines();result=json.loads(out[-1]);result['binary_sha256']=sha(binary.read_bytes());proof['native'][name]=result
  originals={n:(ROOT/'upstream/ouroboros'/n).read_bytes()for n in stage.FILES};overlay=stage.render(originals,meta);changed={n for n in originals if n in overlay};assert changed==set(stage.FILES[:2]);assert originals=={n:(ROOT/'upstream/ouroboros'/n).read_bytes()for n in stage.FILES}
  for field in ['inventory_sha256','generation']:
   bad=dict(meta);bad[field]='00'*32 if field.endswith('sha256')else 0
   try:stage.render(originals,bad)
   except ValueError:pass
   else:raise AssertionError(field)
  bad=dict(originals);bad[stage.FILES[0]]+=b'\n'
  try:stage.render(bad,meta)
  except ValueError:pass
  else:raise AssertionError('source pin')
  proof['stage']={'passed':True,'source_unchanged':True,'overlay_sha256':{n:sha(b)for n,b in overlay.items()},'hook':'svr_init.c after loadCostumes before loadPowerCustomizations','configuration_fixture':meta}
  files=list(HERE.glob('*.py'))+list(HERE.glob('*.inc'))+[HERE/'test_export.c',HERE/'source-pins.json',HERE/'CONTRACT.md',HERE/'../costume-import/source-pins.json',HERE/'../costume-import/source_id.h',HERE/'../costume-import/coh_costume_import.c',HERE/'../costume-import/coh_costume_import.h',HERE/'../costume-import/oracle.py',HERE/'../entities/coh_costume.c',HERE/'../entities/coh_costume.h',HERE/'../replication/coh_replication.c',HERE/'../replication/coh_replication.h',HERE/'../entities/coh_entities.h',HERE/'../coh_contracts.h']
  proof['source_sha256']={str(f.relative_to(HERE)):sha(f.read_bytes())for f in files};proof.update(scope='Nonshipping original-source getter-backed serializer+host POSIX sink on synthetic storage, composed with frozen immutable importer; no full original builder/engine or actual Win32 runtime/ABI execution.',actual_bins_read_by_builder=False,win32_server_compiled=False,win32_runtime_executed=False,android_built=False,original_stash_hashing_or_insertion_executed=False,authentic_dictionary_exported=False,actor_authority=False,external_crypto_sanitizer_or_stack_closure=False,leak_sanitizer_executed=False,maximum_scratch_bytes=4*1024*1024)
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'native':proof['native'],'output':str(a.output)}))
if __name__=='__main__':main()
