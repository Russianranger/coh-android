"""Unchanged original breakable callback/traversal on reconstructed captured topology.
Tracker allocation/opening and property-derived input flags are explicit shells;
this does not execute the original lazy-loading engine or admit live status.
"""
import ctypes as C,hashlib,json,re,struct,subprocess,tempfile
from pathlib import Path
import dynamic_observation as obs
q=obs.q;HERE=Path(__file__).resolve().parent
PATHS=['Common/group/groupdyn.c','Common/group/grouputil.c','Common/group/group.c','Common/group/groupfileload.c','Common/group/grouptrack.c','Common/group/groupdyn.h','Common/group/groupProperties.c','libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h']
def qualify(catalog,snapshot):
 state={};projection=obs.inspect(catalog,snapshot,state);texts={p:q.source(p) for p in PATHS};pins={p:q.sha(s.encode()) for p,s in texts.items()}
 if json.loads((HERE/'dynamic-source-pins.json').read_text())!=pins:raise ValueError('dynamic source pins changed')
 names=list(state['names']);indexes={n:i for i,n in enumerate(names)};edges=[];nodes=[]
 for name in names:
  d=state['names'][name];own,child=state['flags'].get(name,(False,False));nodes.append((len(edges),len(d['children']),int(own),int(child),int(bool(d.get('external')))));edges += [indexes[n] for n in d['children']]
 roots=[indexes[n] for _,n in state['roots']]
 code='''#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef unsigned char U8;
typedef struct GroupDef GroupDef;
typedef struct DefTracker{GroupDef*def;int dyn_group,count;struct DefTracker*entries;}DefTracker;
struct GroupDef{int breakable,child_breakable;unsigned first,count,index,preload;};
typedef struct{DefTracker*tracker;}DynGroup;
typedef struct{DefTracker**refs;int ref_count;}GroupInfo;
typedef int(*GroupDefTrackerProcessor)(DefTracker*);
static GroupInfo group_info;static DynGroup*dyn_groups;static int dyn_group_count,dyn_group_max;
'''
 header=texts[PATHS[5]]
 for n in ['GRPDYN_HP_BITS','GRPDYN_REPAIR_BITS']:code+=re.search(r'^#define '+n+r'[^\n]+',header,re.M).group(0)+'\n'
 code+=re.search(r'typedef struct\s*\{\s*U8\s+hp\s*:.*?\}\s*DynGroupStatus;',header,re.S).group(0)+'\nstatic DynGroupStatus*dyn_group_status;\n'
 code+='static const unsigned source_nodes[][5]={'+','.join('{'+','.join(map(str,row))+'}' for row in nodes)+'};\nstatic const unsigned source_edges[]={'+','.join(map(str,edges))+'};\nstatic const unsigned source_roots[]={'+','.join(map(str,roots))+'};\n'
 code+='''
static GroupDef definitions[sizeof(source_nodes)/sizeof(source_nodes[0])];
static unsigned preload_calls,opens;
static void groupLoadIfPreload(GroupDef*d){assert(d&&!d->preload);preload_calls++;}
static void trackerOpen(DefTracker*t){if(t->entries)return;assert(t->def&&t->def->child_breakable);t->count=t->def->count;t->entries=calloc(t->count?t->count:1,sizeof(DefTracker));assert(t->entries);opens++;for(int i=0;i<t->count;i++)t->entries[i].def=&definitions[source_edges[t->def->first+i]];}
static void*dynArrayAddStruct(DynGroup**p,int*count,int*max){if(*count==*max){*max=*max?*max*2:16;*p=realloc(*p,*max*sizeof(**p));assert(*p);}return &(*p)[(*count)++];}
'''
 funcs={}
 for path,ns in [(PATHS[0],['findBreakable']),(PATHS[1],['groupProcessDefTrackerHelper','groupProcessDefTracker']),(PATHS[0],['groupDynBuildBreakableList'])]:
  for n in ns:
   body=q.extract(texts[path],n);code+=body;funcs[n]={'path':path,'sha256_lf':q.sha(body.encode())}
 code+='''
static void dispose(DefTracker*t){for(int i=0;i<t->count;i++)dispose(t->entries+i);free(t->entries);}
unsigned tracker_fixture(unsigned*out,unsigned*counts){
 for(unsigned i=0;i<sizeof(definitions)/sizeof(definitions[0]);i++){definitions[i]=(GroupDef){source_nodes[i][2],source_nodes[i][3],source_nodes[i][0],source_nodes[i][1],i,source_nodes[i][4]};}
 group_info.ref_count=sizeof(source_roots)/sizeof(source_roots[0]);group_info.refs=calloc(group_info.ref_count,sizeof(*group_info.refs));for(int i=0;i<group_info.ref_count;i++){group_info.refs[i]=calloc(1,sizeof(DefTracker));group_info.refs[i]->def=&definitions[source_roots[i]];}
 groupDynBuildBreakableList();for(int i=0;i<dyn_group_count;i++){out[i]=dyn_groups[i].tracker->def->index;assert(dyn_groups[i].tracker->dyn_group==i+1&&dyn_group_status[i].hp==100&&dyn_group_status[i].repair==0);}counts[0]=preload_calls;counts[1]=opens;unsigned result=dyn_group_count;
 for(int i=0;i<group_info.ref_count;i++){dispose(group_info.refs[i]);free(group_info.refs[i]);}free(group_info.refs);free(dyn_groups);dyn_groups=NULL;free(dyn_group_status);dyn_group_status=NULL;return result;
}
'''
 with tempfile.TemporaryDirectory(prefix='coh-dynamic-tracker-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w',td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'));output=(C.c_uint32*65536)();counts=(C.c_uint32*2)();count=lib.tracker_fixture(output,counts);expected=[indexes[row['names'][-1]] for row in projection['occurrences']];assert list(output[:count])==expected
  # Header-only object probe needs no32bitlibc/runtime and inspects all256states.
  decl=re.search(r'typedef struct\s*\{\s*U8\s+hp\s*:.*?\}\s*DynGroupStatus;',header,re.S).group(0)
  probe='typedef unsigned char U8;\n'+''.join(re.search(r'^#define '+n+r'[^\n]+',header,re.M).group(0)+'\n' for n in ['GRPDYN_HP_BITS','GRPDYN_REPAIR_BITS'])+decl+'\n_Static_assert(sizeof(DynGroupStatus)==1,"layout");\nconst DynGroupStatus proof[256]={'+','.join('{'+str(i&127)+','+str(i>>7)+'}' for i in range(256))+'};\n'
  (td/'abi.c').write_text(probe);abis={}
  for mode,flags in [('i386_gcc',['-m32']),('i386_gcc_microsoft_bitfields',['-m32','-mms-bitfields'])]:
   obj=td/(mode+'.o');raw=td/(mode+'.bin');q.run(['cc','-std=c11',*flags,'-c',td/'abi.c','-o',obj]);q.run(['objcopy','-O','binary','--only-section=.rodata',obj,raw]);data=raw.read_bytes();assert data==bytes(range(256));head=obj.read_bytes();assert head[:5]==b'\x7fELF\x01' and struct.unpack_from('<H',head,18)[0]==3;abis[mode]={'object_sha256':q.sha(head),'layout_bytes_sha256':q.sha(data),'size':1,'all256states_verified':True,'runtime_executed':False,'msvc_or_windows_compiler_executed':False}
 return {'schema':'coh-dynamic-original-traversal-qualification-v1','passed':True,'source_pin':q.PIN,'original_source_sha256_lf':pins,'original_functions':funcs,'generated_original_source_sha256':q.sha(code.encode()),'projection':projection,'original_traversal_occurrences':count,'original_tracker_definition_indexes':list(output[:count]),'preload_callback_calls_on_saved_nonpreload':counts[0],'synthetic_tracker_opens':counts[1],'status_abi_probes':abis,'scope':'whole original callback and pre-order traversal/build; synthetic trackerOpen/arrayallocation and property-derived input flags; not original trackerOpen/lazy-load execution','original_oracle_sanitized':False,'dynamic_status_admitted':False,'world_authority':False,'actor_publication':False}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'dynamic-source-pins.json').write_text(json.dumps({p:q.sha(q.source(p).encode()) for p in PATHS},indent=2)+'\n')
 r=qualify(a.catalog,a.snapshot);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'original_occurrences':r['original_traversal_occurrences'],'abi_modes':list(r['status_abi_probes'])}))
