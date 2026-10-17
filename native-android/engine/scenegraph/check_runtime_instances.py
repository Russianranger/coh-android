#!/usr/bin/env python3
"""Bounded per-path instance state + unchanged original Mat4 oracle; no world."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile
from check_group_bounds import extract
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
original=ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h';function=extract(original.read_text(),'mulMat4Inline');group=ROOT/'upstream/ouroboros/Common/group/grouputil.c';traversals=[extract(group.read_text(),n) for n in ['groupProcessDefHelper','groupProcessDef']];code='typedef float Mat4[4][3];\n#define INLINEDBG\n'+function+'\nvoid original_instance_compose(const float (*p)[3],const float (*c)[3],float (*out)[3]){mulMat4Inline(p,c,out);}\n'
code+='\n#include <stdlib.h>\n#include <string.h>\ntypedef struct GroupDef GroupDef;\ntypedef struct {GroupDef *def;Mat4 mat;} GroupEnt;\nstruct GroupDef {unsigned id;int count;GroupEnt *entries;};\ntypedef struct {GroupDef *def;Mat4 mat;} DefTracker;\ntypedef struct {int ref_count;DefTracker **refs;} GroupInfo;\ntypedef int(*GroupDefProcessor)(GroupDef*,Mat4);\nstatic void mulMat4(Mat4 a,Mat4 b,Mat4 c){mulMat4Inline((const float(*)[3])a,(const float(*)[3])b,c); }\n'+''.join(traversals)+r'''
static unsigned oracle_count;static unsigned *oracle_nodes;static Mat4 *oracle_matrices;
static int record_original(GroupDef *def,Mat4 matrix){if(oracle_count>=10)abort();oracle_nodes[oracle_count]=def->id;memcpy(oracle_matrices[oracle_count++],matrix,sizeof(Mat4));return 1;}
unsigned original_fixture_walk(unsigned *ids,Mat4 *matrices){
 GroupDef defs[4]={{0}};GroupEnt entries[4]={0};DefTracker roots[3]={0};DefTracker *ptrs[3]={&roots[0],&roots[1],&roots[2]};GroupInfo info={3,ptrs};unsigned targets[4]={1,2,3,3};
 for(unsigned i=0;i<4;i++){defs[i].id=i;entries[i].def=&defs[targets[i]];for(unsigned j=0;j<3;j++)entries[i].mat[j][j]=1;entries[i].mat[3][0]=(float)i+1;}
 defs[0].count=2;defs[0].entries=&entries[0];defs[1].count=1;defs[1].entries=&entries[2];defs[2].count=1;defs[2].entries=&entries[3];
 for(unsigned i=0;i<2;i++){roots[i].def=&defs[0];for(unsigned j=0;j<3;j++)roots[i].mat[j][j]=1;roots[i].mat[3][0]=10+(float)i*10;}
 oracle_count=0;oracle_nodes=ids;oracle_matrices=matrices;groupProcessDef(&info,record_original);oracle_nodes=NULL;oracle_matrices=NULL;return oracle_count;
}
'''

sources=[HERE/'coh_runtime_instances.c',HERE/'tests/test_runtime_instances.c'];deps=sources+[HERE/'coh_runtime_instances.h',HERE/'runtime_graph.h',HERE/'runtime_snapshot.h',HERE/'coh_scenegraph.h',HERE/'coh_runtime_bounds.h',HERE/'coh_group_bounds.h',HERE.parent/'replication/coh_groups.h',HERE.parent/'replication/coh_replication.h',HERE.parent/'coh_contracts.h',HERE/'check_group_bounds.py',original,group,ROOT/'upstream/ouroboros/Common/group/grouptrack.c',Path(__file__)];pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps};modes={}
with tempfile.TemporaryDirectory(prefix='coh-runtime-instances-') as directory:
 d=Path(directory);(d/'original.c').write_text(code)
 for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
  binary=d/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off',*flags,'-I'+str(HERE),*sources,d/'original.c','-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free','-lm','-o',binary]);modes[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 stack={}
 for path in d.glob('*.su'):
  for line in path.read_text().splitlines():
   fields=line.split('\t')
   if len(fields)>=2 and 'coh_runtime_instances.c:' in fields[0]:stack[fields[0].rsplit(':',1)[-1]]=int(fields[1])
 assert stack and max(stack.values())<65536
result={'passed':True,'modes':modes,'source_sha256':pins,'original_matrix_function_sha256':hashlib.sha256(function.encode()).hexdigest(),'original_traversal_function_sha256':[hashlib.sha256(x.encode()).hexdigest() for x in traversals],'original_oracle_sha256':hashlib.sha256(code.encode()).hexdigest(),'release_stack_bytes':stack,'fixture_graph_api_only':True,'actual_Atlas_occurrences_counted':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False}
assert pins=={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
