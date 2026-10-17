#!/usr/bin/env python3
"""Bounded CLIENT texture-name projection against unchanged original lookup chain."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def extract(text,signature):
 start=text.index(signature);at=text.index('{',start);end=at+1;depth=1
 while depth:
  if text[end]=='{':depth+=1
  if text[end]=='}':depth-=1
  end+=1
 return text[start:end]+'\n'
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout

def oracle(parts):
 prefix='''#include "coh_wr_texname.h"
#include <string.h>
#include <stdlib.h>
#include <assert.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define TEX_TGA 1
#define TEX_JPEG 2
#define TEX_DDS 4
typedef int TexLoadHow;typedef int TexUsage;typedef struct{int marker;} TexBind;
typedef struct{int count;char**strings;} PackNames;typedef struct{char*src,*dst;} TexSwap;
static TexBind white={1},invisible={2},composite={3};static TexBind*white_tex_bind=&white,*invisible_tex_bind=&invisible;
static void*g_compositeTextures_ht;static TexSwap rows[256],*row_ptrs[256];static char destinations[256][128];static int row_count,missing,lookup_calls;static CohWrTexNameProjection observed;
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int stricmp(const char*a,const char*b){while(*a&&*b){int d=(int)fold((unsigned char)*a++)-(int)fold((unsigned char)*b++);if(d)return d;}return (unsigned char)*a-(unsigned char)*b;}
static char*strstri(const char*s,const char*needle){for(;*s;s++){unsigned i=0;while(needle[i]&&s[i]&&fold((unsigned char)s[i])==fold((unsigned char)needle[i]))i++;if(!needle[i])return (char*)s;}return NULL;}
static void strncpyt(char*d,const char*s,int n){assert(n>0&&strlen(s)<(unsigned)n);memcpy(d,s,strlen(s)+1);}
static TexSwap**sceneGetMaterialSwaps(int*count){*count=row_count;return row_ptrs;}
static int stashFindPointer(void*table,const char*key,TexBind**out){(void)table;lookup_calls++;assert(strlen(key)<128);strcpy(observed.composite_key,key);for(int i=0;i<row_count;i++)if(key==rows[i].dst)observed.scene_swap_index=(unsigned)i;*out=missing?NULL:&composite;return !missing;}
static void texLoadInternalComposite(TexBind*bind,TexLoadHow how,TexUsage use){(void)bind;(void)how;(void)use;}
'''
 wrapper='''
CohWrTexNameProjection original_texname(const CohWrTexNameInput*q,int miss,int*fallback){
 memset(&observed,0,sizeof(observed));observed.scene_swap_index=0xffffffffu;missing=miss;lookup_calls=0;row_count=q->swap_count;
 for(int i=0;i<row_count;i++){strcpy(destinations[i],q->scene_material_swaps[i].destination);rows[i]=(TexSwap){(char*)q->scene_material_swaps[i].source,destinations[i]};row_ptrs[i]=rows+i;}
 char name[256];if(q->name)strcpy(name,q->name);else name[0]=0;char*names[]={name};PackNames packed={q->texture_count?1:0,names};TexBind**binds=buildTexBindArrayFromTexNames(&packed,1,2);
 strcpy(observed.stripped,name);observed.branch=!q->texture_count?COH_WR_TEXNAME_EMPTY_TABLE_BRANCH:lookup_calls?COH_WR_TEXNAME_COMPOSITE_LOOKUP:COH_WR_TEXNAME_PORTAL_BRANCH;
 *fallback=lookup_calls&&binds[0]==white_tex_bind;free(binds);return observed;}
'''
 return prefix+''.join(parts)+wrapper

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 pins=json.loads((HERE/'texname-source-pins.json').read_text());sources={}
 for path,h in pins.items():
  if sha(ROOT/path)!=h:raise ValueError('Original source differs '+path)
  sources[path]=(ROOT/path).read_text()
 tex=sources['upstream/ouroboros/Game/src/render/tex.c'];model=sources['upstream/ouroboros/Game/src/render/model.c']
 signatures=[(tex,'static int texFixName('),(tex,'char *texCheckForSceneMaterialSwap('),(tex,'TexBind *texFindComposite('),(tex,'TexBind *texLoad('),(model,'static TexBind ** buildTexBindArrayFromTexNames(')]
 parts=[extract(t,s) for t,s in signatures]
 fixture=json.loads((HERE/'texname-fixtures.json').read_text());report=ROOT/fixture['report_path']
 if sha(report)!=fixture['report_sha256']:raise ValueError('Captured source-name report differs')
 j=json.loads(report.read_text());names=sorted({p[2] for f in j['files'] for m in f['models'] for o in m['source_observations'] for p in o['texture_partitions']})
 if not all(all(32<=ord(c)<=126 for c in name) for name in names):raise ValueError('Source fixture ASCII precondition differs')
 if len(names)!=fixture['captured_name_count']:raise ValueError('Captured source names differ')
 names+=fixture['qualified_manifest_examples']
 deps=[HERE/'coh_wr_texname.c',HERE/'coh_wr_texname.h',HERE/'tests/test_texname.c',HERE/'check_texname.py',HERE/'texname-source-pins.json',HERE/'texname-fixtures.json',HERE.parent/'coh_contracts.h',report,*[ROOT/x for x in pins],*[ROOT/x for x in fixture['manifest_example_proof_paths']]]
 hashes={str(x.relative_to(ROOT)):sha(x) for x in deps};results={}
 with tempfile.TemporaryDirectory(prefix='coh-texname-') as directory:
  t=Path(directory);(t/'original.c').write_text(oracle(parts));(t/'texname_fixture.h').write_text('#define TEXNAME_FIXTURE_COUNT '+str(len(names))+'u\n#define TEXNAME_CAPTURED_COUNT '+str(fixture['captured_name_count'])+'u\nstatic const char*texname_fixture[]={'+','.join(json.dumps(x) for x in names)+'};\n')
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',t]
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   run(['cc',*flags,*extra,HERE/'tests/test_texname.c',HERE/'coh_wr_texname.c',t/'original.c','-o',t/mode]);results[mode]=json.loads(run([t/mode,t/(mode+'-refused.txt')],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  refused_names=(t/'release-refused.txt').read_text().splitlines()
  if any((t/(mode+'-refused.txt')).read_text().splitlines()!=refused_names for mode in results):raise ValueError('Refusal corpus differs between modes')
  mutations=[('last_extension','strrchr(result.stripped,\'.\')','strchr(result.stripped,\'.\')'),('swap_chaining','result.scene_swap_index==UINT32_MAX&&equal','equal')]
  for name,before,after in mutations:
   src=(HERE/'coh_wr_texname.c').read_text();assert before in src;(t/(name+'.c')).write_text(src.replace(before,after));run(['cc',*flags,'-O2',HERE/'tests/test_texname.c',t/(name+'.c'),t/'original.c','-o',t/name]);r=subprocess.run([str(t/name),str(t/(name+'-refused.txt'))],capture_output=True,timeout=60)
   if not r.returncode:raise ValueError('Mutation escaped '+name)
 if hashes!={str(x.relative_to(ROOT)):sha(x) for x in deps}:raise ValueError('Source changed')
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_inputs_unchanged':True,'source_sha256':hashes,'unchanged_original_functions_sha256_lf':{s:hashlib.sha256(f.encode()).hexdigest() for (_,s),f in zip(signatures,parts)},'modes':results,'production_mutations_rejected':[x[0] for x in mutations],'captured_source_domain_refusals':refused_names,'fixture_stash_only':True,'asset_generation_permit':False,'material_authority':False,'world_authority':False,'android_execution':False},indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()
