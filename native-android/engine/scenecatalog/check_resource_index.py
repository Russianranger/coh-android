#!/usr/bin/env python3
"""Native source-resource identity index: original lookup oracles and bounded ownership."""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,random,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ENGINE=HERE.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def function(text,name):
    match=re.search(r'[^\n]*\b'+name+r'\([^;]*?\)\s*\{',text)
    if not match:raise ValueError('Original function absent '+name)
    start=match.start();at=text.index('{',match.start());depth=1;end=at+1
    while depth:
        if text[end]=='{':depth+=1
        elif text[end]=='}':depth-=1
        end+=1
    return text[start:end]
def run(cmd,**kw):
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=180,**kw)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--geo',type=Path);p.add_argument('--geo-sha256');p.add_argument('--geo-path');p.add_argument('--model-row',type=int)
    a=p.parse_args()
    if a.output.exists():raise ValueError('New output required')
    actual=[a.geo,a.geo_sha256,a.geo_path,a.model_row]
    if any(x is not None for x in actual) and not all(x is not None for x in actual):raise ValueError('All authentic GEO inputs required')
    if a.geo and sha(a.geo)!=a.geo_sha256:raise ValueError('Actual GEO SHA mismatch')
    paths=[ROOT/'upstream/ouroboros/Common/group/groupfilelib.c',ROOT/'upstream/ouroboros/Common/seq/anim.c',ROOT/'upstream/ouroboros/Common/seq/tricks.c',ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/StashTable.h']
    sources=[HERE/'coh_resource_index.c',ENGINE/'assets/coh_asset_loader.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
    dependencies=paths+sources+[HERE/'coh_resource_index.h',HERE/'tests/test_resource_index.c',HERE/'tests/resource-fixtures/observed.cohres',Path(__file__),ENGINE/'assets/coh_asset_loader.h',ENGINE/'assets/coh_asset_geo.h',ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h']
    pins={str(f.relative_to(ROOT)):sha(f) for f in dependencies}
    group,anim,trick=[f.read_text() for f in paths[:3]]
    funcs=[function(group,'groupGetPublicName'),function(group,'groupNameIdx'),function(anim,'compareModelNamesAndLengths'),function(trick,'trickFromObjectName')]
    shim='''#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <strings.h>
#include <stdio.h>
#define MAX_PATH 1024
#define min(a,b) ((a)<(b)?(a):(b))
#define strnicmp strncasecmp
static char captured[1024];
static void strncpyt(char *d,const char *s,int n){snprintf(d,(size_t)n,"%s",s);}
static const char *strstriConst(const char *s,const char *x){return strstr(s,x);}
static int group_name_hashes=1;
static bool stashFindInt(int t,const char *key,int *idx){(void)t;snprintf(captured,sizeof(captured),"%s",key);*idx=0;return true;}
typedef struct {int ignored;} TrickInfo;
static struct {int trick_name_hashes;} trick_list={1};
static int trick_report_exist_errors=0;
static TrickInfo trick;
static void stashFindPointer(int t,const char *key,TrickInfo **out){(void)t;snprintf(captured,sizeof(captured),"%s",key);*out=&trick;}
#define ErrorFilenamef(...) ((void)0)
#define Errorf(...) ((void)0)
static void getDirectoryName(char *s){char *p=strrchr(s,'/');if(p)*p=0;}
'''+ '\n'.join(funcs)+'''
const char *original_library(const char *s){char public_name[1000];int index;groupNameIdx(groupGetPublicName(s,public_name,999),&index);return captured;}
const char *original_trick(const char *s){trickFromObjectName(s,"object_library/source.geo");return captured;}
int original_model_compare(const char *a,const char *b){const char *x=strstr(a,"__"),*y=strstr(b,"__");return compareModelNamesAndLengths(a,(int)(x?x-a:strlen(a)),(char*)b,(int)(y?y-b:strlen(b)));}
'''
    outcomes={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    base=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE)]
    with tempfile.TemporaryDirectory(prefix='coh-resource-index-') as temporary:
        tmp=Path(temporary);oracle=tmp/'oracle.c';oracle.write_text(shim)
        run(['cc','-std=c99','-O0','-shared','-fPIC',oracle,'-o',tmp/'oracle.so'])
        run([*base,'-O2','-shared','-fPIC',*sources,'-lz','-lm','-o',tmp/'native.so'])
        original=ctypes.CDLL(str(tmp/'oracle.so'));native=ctypes.CDLL(str(tmp/'native.so'))
        for name in ('original_library','original_trick'):getattr(original,name).argtypes=[ctypes.c_char_p];getattr(original,name).restype=ctypes.c_char_p
        original.original_model_compare.argtypes=[ctypes.c_char_p,ctypes.c_char_p]
        functions=[native.coh_resource_library_key,native.coh_resource_model_key,native.coh_resource_trick_key]
        for fn in functions:fn.argtypes=[ctypes.c_char_p,ctypes.c_void_p];fn.restype=ctypes.c_int
        cases=['piece','PIECE__Stone','dir/piece__TRICK','part_1&','dir/part_1&','under_score','name&','part_12&__suffix','part__Trick_1&','path/name__stone','piece_long']
        rng=random.Random(20261017)
        for _ in range(1500):
            s=''.join(rng.choice('abcXYZ_123') for _ in range(rng.randrange(1,60)))
            if rng.randrange(2):s+='__'+rng.choice(['stone','STONE','glass'])
            if rng.randrange(2):s+='_1&'
            if rng.randrange(2):s='object_library/'+s
            cases.append(s)
        comparisons=0
        for text in cases:
            raw=text.encode();result=ctypes.create_string_buffer(256)
            for fn,reference in [(functions[0],original.original_library),(functions[2],original.original_trick)]:
                want=reference(raw).decode().lower()
                status=fn(raw,result)
                if want:
                    assert status==0 and result.value.decode()==want,(text,want,status,result.value)
                else:assert status!=0
                comparisons+=1
        for _ in range(4000):
            x=rng.choice(cases).rsplit('/',1)[-1];y=rng.choice(cases).rsplit('/',1)[-1]
            aout=ctypes.create_string_buffer(256);bout=ctypes.create_string_buffer(256)
            sa=functions[1](x.encode(),aout);sb=functions[1](y.encode(),bout)
            if sa or sb:continue
            native_cmp=(aout.value>bout.value)-(aout.value<bout.value);original_cmp=original.original_model_compare(x.encode(),y.encode());assert native_cmp==((original_cmp>0)-(original_cmp<0));comparisons+=1
        for text in [b'',b'/',b'__',b'a'*256,b'x\xff']:
            for fn in functions:
                if text==b'/' and fn==functions[2]:continue
                out=ctypes.create_string_buffer(b'UNCHANGED'+bytes(247));before=out.raw;assert fn(text,out)!=0 and out.raw==before;comparisons+=1
        for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary=tmp/mode
            run([*base,*flags,HERE/'tests/test_resource_index.c',*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lcrypto','-lz','-lm','-o',binary])
            observed=json.loads(run([binary,'--observed',HERE/'tests/resource-fixtures/observed.cohres'],env=env))
            actual_result=json.loads(run([binary,a.geo,a.geo_path,a.model_row],env=env)) if a.geo else None
            outcomes[mode]={'observed_source_controls':observed,'authentic_geo_controls':actual_result,'binary_sha256':sha(binary)}
    if pins!={str(f.relative_to(ROOT)):sha(f) for f in dependencies}:raise ValueError('Source changed during qualification')
    if a.geo and sha(a.geo)!=a.geo_sha256:raise ValueError('GEO changed during qualification')
    result={'schema':1,'passed':True,'source_sha256':pins,'original_functions':[re.search(r'\b(\w+)\(',f).group(1) for f in funcs],'original_lookup_comparisons':comparisons,'modes':outcomes,'actual_geo_sha256':a.geo_sha256,'actual_geo_path':a.geo_path,'actual_geo_model_row':a.model_row,'actual_runtime_resource_capture':False,'source_fixture_only':True,'client_materials_admitted':False,'live_groups_admitted':False,'graph_published':False,'world_authority':False,'android_executed':False,'protected_asset_source_modified':False,'leak_sanitizer':False,'allocation_balance_controls':True}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'passed':True,'original_lookup_comparisons':comparisons,'modes':outcomes}))
if __name__=='__main__':main()
