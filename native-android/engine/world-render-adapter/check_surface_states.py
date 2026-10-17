#!/usr/bin/env python3
"""Qualify historical native surface state importer against original CLIENT seqLoadStateBits."""
import argparse,json,hashlib,re,struct,tempfile,os,importlib.util,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
DEPS=[HERE/x for x in ['CLIENT_SURFACE_STATES.md','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','check_surface_states.py','tests/test_surface_states.c','texopt_cache_contract.py','check_texname.py']]+[ROOT/'upstream/ouroboros/Common/seq'/x for x in ['seqstate.c','seqstate.h','TriggeredMove.h']]+[HERE.parent/'coh_contracts.h']
START_SHA={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}

def states(body):
 m=load('surface_wire_prefix',HERE/'texopt_cache_contract.py');c=m.Cursor(body,20)
 if c.pascal()!=b'Files1':raise ValueError('state filelist role')
 n=c.u32();c.take(n);n=c.u32()
 if n!=c.end-c.pos:raise ValueError('whole state bound')
 count=c.u32();rows=[]
 if count!=764:raise ValueError('actual historical state count')
 for _ in range(count):
  n=c.u32();end=c.pos+n;name=c.pascal(100);flags=c.u32()
  if c.pos!=end or any(x<32 or x>126 for x in name):raise ValueError('exact state row bounds/domain')
  rows.append((name,flags))
 if c.pos!=c.end:raise ValueError('state trailing bytes')
 return rows

def oracle(rows,extract):
 header=(ROOT/'upstream/ouroboros/Common/seq/seqstate.h').read_text();source=(ROOT/'upstream/ouroboros/Common/seq/seqstate.c').read_text();defines='\n'.join(x for x in header.splitlines() if re.match(r'#define\s+(STATE_|CODE_DEFINED_STATE_COUNT)',x));a=source.index('StateBit stateBits[');b=source.index('\n};',a)+3
 code=r'''#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include <assert.h>
#include <stdarg.h>
#include "coh_wr_surface_states.h"
#define MAXSTATES 876
#define SORTED_STATEBIT_LIST 1
#define devassert(x) assert(x)
typedef uint32_t U32;typedef int bool;
#define false 0
#define true 1
#define PARSER_SERVERONLY 1
#define STATEBIT_CONTINUING 1
#define STATEBIT_FLASH 2
#define STATEBIT_PREDICTABLE 4
#define STATEBIT_CODESET 8
'''+defines+'\n'+header[header.index('typedef struct StateBit {'):header.index('} StateBit;')+11]+'\n'+source[a:b]+r'''
typedef struct{StateBit**stateBits;}StateBitList;static StateBitList fromDataStateBitList;
static int stateBitsMightBeRenumbered;static StateBit*s_SortedStateBitList_Name[MAXSTATES];static int g_MaxUsedStates=CODE_DEFINED_STATE_COUNT;
typedef struct{int updated;}ParserLoadInfo;static void*ParseStateBitList;
static int ParserLoadFiles(const char*d,const char*m,const char*p,int f,void*t,StateBitList*l,void*g,ParserLoadInfo*i,void*pre){(void)d;(void)m;(void)p;(void)f;(void)t;(void)l;(void)g;(void)pre;i->updated=0;return 1;}
static void FatalErrorf(const char*fmt,...){va_list a;va_start(a,fmt);vfprintf(stderr,fmt,a);va_end(a);abort();}
static int eaSize(StateBit***p){(void)p;return 764;}
'''+extract(source,'int CompareFunc_StateBit_Name(')+extract(source,'void seqLoadStateBits(')+extract(source,'int seqGetStateNumberFromName(')+'\nstatic StateBit fixture[]={\n'
 for name,flags in rows:code+='{(char*)"'+''.join('\\x%02x'%v for v in name)+'",0,'+str(flags)+'},\n'
 code+='};\n'
 # Original mutates cached names; make private mutable copies before invoking it.
 code+=r'''static StateBit*fixture_ptrs[764];
unsigned original_state_count(void){return(unsigned)g_MaxUsedStates;}
const StateBit*original_state(unsigned row){assert(row<(unsigned)g_MaxUsedStates);return stateBits+row;}
void original_state_initialize(void){for(unsigned i=0;i<764;i++){size_t n=strlen(fixture[i].name);char*s=malloc(n+1);assert(s);memcpy(s,fixture[i].name,n+1);fixture[i].name=s;fixture_ptrs[i]=fixture+i;}fromDataStateBitList.stateBits=fixture_ptrs;seqLoadStateBits();}
void original_state_destroy(void){for(unsigned i=0;i<764;i++)free(fixture[i].name);}
'''
 return code

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 b=a.actual_cache.read_bytes()
 if len(b)!=15380 or sha(b)!='9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac':raise ValueError('exact historical cache required')
 before=dict(START_SHA)
 if before!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source changed before import')
 old=load('surface_original_extract',HERE/'check_texname.py');rows=states(b);results={}
 with tempfile.TemporaryDirectory(prefix='coh-surface-states-') as directory:
  d=Path(directory);(d/'oracle.c').write_text(oracle(rows,old.extract))
  for name,flags in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   
   common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,*flags]
   old.run([*common,'-c',HERE/'coh_wr_surface_states.c','-o',d/'native.o']);old.run([*common,'-c',HERE/'tests/test_surface_states.c','-o',d/'test.o']);old.run([*common,'-Wno-error=discarded-qualifiers','-Wno-error=sign-compare','-c',d/'oracle.c','-o',d/'oracle.o']);old.run(['cc',*flags,d/'native.o',d/'test.o',d/'oracle.o','-lcrypto','-Wl,--wrap=calloc','-o',d/name]);results[name]=json.loads(old.run([d/name,a.actual_cache],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 if before!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS} or sha(a.actual_cache.read_bytes())!=sha(b):raise ValueError('source or cache changed')
 proof={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':before,'actual_cache_bytes':15380,'actual_cache_sha256':sha(b),'original_CLIENT_seqLoadStateBits_executed':True,'original_state_lookup_executed':True,'original_parser_input_observer':True,'actual_client_runtime_executed':False,'modes':results,'active_generation':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()
