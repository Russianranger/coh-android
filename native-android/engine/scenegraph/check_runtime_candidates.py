#!/usr/bin/env python3
"""Source-only lossless candidate paging and original CLIENT distance projection."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,tempfile
HELPER_PATH=Path(__file__).resolve().parent/'check_group_bounds.py'
HELPER_PREIMPORT_SHA256=hashlib.sha256(HELPER_PATH.read_bytes()).hexdigest()
from check_group_bounds import extract
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
paths=[ROOT/'upstream/ouroboros'/x for x in ['Game/src/graphics/groupdrawinline.c','Game/src/graphics/groupdraw.h','libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h']];texts=[x.read_text() for x in paths];function=extract(texts[0],'closeEnough');source_flags=re.search(r'enum\s*\{[^}]+\};',texts[1]).group();macros=[]
for text,name in [(texts[1],'calculateVisDist'),(texts[2],'SQR'),(texts[2],'lengthVec3Squared')]:macros.append(next(line for line in text.splitlines() if re.match(r'#define\s+'+name+r'\(',line)))
code='#include "coh_client_distance.h"\n#include <string.h>\ntypedef float F32;typedef float Vec3[3];\n#define INLINEDBG\n#define CALL_INC\n'+source_flags+'\n'+ '\n'.join(macros)+'''
typedef struct {int lod_fadenode;Vec3 node_mid;} DrawParams;
typedef struct {unsigned flags_cache;float vis_dist_scaled_cache,vis_def_radius_cache;} GroupEnt;
static struct {float lod_scale;} game_state;
'''+function+'''
float original_client_distance(const CohClientDistanceInput *in){DrawParams d={0};GroupEnt g={0};Vec3 mid;d.lod_fadenode=(int)in->lod_fadenode;memcpy(d.node_mid,in->parent_node_mid,sizeof(mid));memcpy(mid,in->view_mid,sizeof(mid));g.flags_cache=in->client_flags_cache;g.vis_dist_scaled_cache=in->client_vis_dist_scaled_cache;g.vis_def_radius_cache=in->client_vis_def_radius_cache;game_state.lod_scale=in->game_lod_scale;return closeEnough(&d,mid,&g);}
'''
sources=[HERE/'coh_runtime_candidates.c',HERE/'coh_runtime_instances.c',HERE/'coh_client_distance.c',HERE/'tests/test_runtime_candidates.c'];deps=sources+paths+[HERE/'check_group_bounds.py',Path(__file__)]+[ROOT/'upstream/ouroboros'/x for x in ['Game/src/graphics/groupdraw.c','Game/src/graphics/groupdrawutil.h','Game/src/graphics/gfxwindow.h','Common/group/grouptrack.c','Common/group/groupfileload.c','Common/seq/tricks.h']]
for d in [HERE.parent,ROOT/'native-android/include']:deps.extend(d.rglob('*.h'))
deps=sorted(set(deps));pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps};modes={}
assert pins[str(HELPER_PATH.relative_to(ROOT))]==HELPER_PREIMPORT_SHA256
with tempfile.TemporaryDirectory(prefix='coh-runtime-candidates-') as directory:
 d=Path(directory);(d/'original.c').write_text(code)
 for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
  binary=d/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off',*flags,'-I'+str(HERE),'-I'+str(ROOT/'native-android/include'),*sources,d/'original.c','-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lm','-o',binary]);modes[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 stack={}
 for path in d.glob('*.su'):
  for line in path.read_text().splitlines():
   fields=line.split('\t')
   if len(fields)>=2 and 'coh_runtime_candidates.c:' in fields[0]:stack[fields[0].rsplit(':',1)[-1]]=int(fields[1])
 assert stack and max(stack.values())<65536
assert pins=={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps}
result={'passed':True,'source_sha256':pins,'modes':modes,'release_stack_bytes':stack,'original_closeEnough_sha256':hashlib.sha256(function.encode()).hexdigest(),'original_flags_sha256':hashlib.sha256(source_flags.encode()).hexdigest(),'original_macros_sha256':[hashlib.sha256(x.encode()).hexdigest() for x in macros],'original_oracle_sha256':hashlib.sha256(code.encode()).hexdigest(),'scope':'source graph/join API fixtures and unchanged CLIENT arithmetic only; no actual CLIENT state or real visibility admission','world_authority':False,'android_executed':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes,'stack':stack}))
