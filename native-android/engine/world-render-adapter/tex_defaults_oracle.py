"""Whole original cold default operation, with the explicit existing name repair."""
from pathlib import Path
import hashlib

PINS={
 'upstream/ouroboros/Game/src/render/tex.c':'4507ee6fa752ed9452e78c4c989a9de0bdf93d81dd3597f1b1db063d73f1ca5c',
 'upstream/ouroboros/Game/src/render/tex.h':'56e56aea12a4126250f5f6f4d2211f62814b7eae4ad2598271f5423b60680552',
}
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text,signature):
 start=text.index(signature);at=text.index('{',start);end=at+1;depth=1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]+'\n'
def create(root):
 root=Path(root);raw={p:(root/p).read_bytes() for p in PINS}
 if {p:sha(b) for p,b in raw.items()}!=PINS:raise ValueError('exact original source differs')
 tex=raw[next(iter(PINS))].decode().replace('\r\n','\n');header=raw[list(PINS)[1]].decode().replace('\r\n','\n')
 blocks={n:extract(tex,s) for n,s in [
  ('texFindNeededBinds','static void texFindNeededBinds()'),
  ('texFind','BasicTexture *texFind(const char *name)'),
  ('texFixName','static int texFixName(const char *s,char *res, int size)'),
  ('texSetBindsSubBasic','static void texSetBindsSubBasic('),
  ('texScanForTexHeaders','void texScanForTexHeaders(')]}
 fix=blocks['texFixName']
 if sha(fix.encode())!='940ef057ef069227a30687807b77623708162f3dc441f6a1b7f66235a363beed':raise ValueError('original name function differs')
 before='{\nint        type = 0;';after='{\nchar *const res_start = res;\nint        type = 0;'
 guard="else if(res[-8] == '.')";corrected="else if(res - res_start >= 8 && res[-8] == '.')"
 if fix.count(before)!=1 or fix.count(guard)!=1:raise ValueError('two-location guard preimage differs')
 repaired=fix.replace(before,after,1).replace(guard,corrected,1)
 a=header.index('typedef enum TexFlags');enum=header[a:header.index('} TexFlags;',a)+len('} TexFlags;')]
 code=r'''#include "tests/tex_defaults_fixture.h"
#include <stdlib.h>
#include <string.h>
#define REQUIRE(x) do{if(!(x))abort();}while(0)
#define assert(x) ((void)0) /* original release debug/sentinel checks disabled */
#define devassert(x) (required_present=!!(x)) /* observe original assertion */
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
'''+enum+r'''
typedef struct {const char*name;TexFlags flags;uint32_t row;} BasicTexture;
static BasicTexture entries[DEFAULTS_ORACLE_ROWS];
static uint32_t count,required_present,lookups;static void*g_basicTextures_ht;
static BasicTexture *white_tex,*grey_tex,*invisible_tex,*black_tex;
static BasicTexture *dummy_bump_tex,*dummy_dynamic_cubemap_tex,*building_lights_tex;
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static int same(const char*a,const char*b){while(*a&&*b){if(fold((unsigned char)*a++)!=fold((unsigned char)*b++))return 0;}return!*a&&!*b;}
static void strncpyt(char*d,const char*s,int n){REQUIRE(n>0&&strlen(s)<(unsigned)n);memcpy(d,s,strlen(s)+1);}
static int stashFindPointer(void*t,const char*key,BasicTexture**out){
 (void)t;lookups++;for(uint32_t i=0;i<count;i++)if(same(key,entries[i].name)){*out=entries+i;return 1;}return 0;
}
'''+repaired+blocks['texFind']+blocks['texFindNeededBinds']+r'''
void original_defaults(const char*const*names,const uint32_t*flags,uint32_t n,DefaultsOracle*out){
 REQUIRE(n<=DEFAULTS_ORACLE_ROWS);count=n;lookups=required_present=0;
 memset(entries,0,sizeof(entries));memset(out,0,sizeof(*out));
 for(uint32_t i=0;i<n;i++){REQUIRE(names[i]&&strlen(names[i])<128);entries[i]=(BasicTexture){names[i],(TexFlags)flags[i],i};}
 white_tex=grey_tex=invisible_tex=black_tex=dummy_bump_tex=dummy_dynamic_cubemap_tex=building_lights_tex=NULL;
 texFindNeededBinds();
 BasicTexture*selected[]={white_tex,grey_tex,invisible_tex,black_tex,dummy_bump_tex,dummy_dynamic_cubemap_tex,building_lights_tex};
 out->required_present=required_present;out->lookup_count=lookups;
 for(uint32_t i=0;i<7;i++){out->rows[i]=selected[i]?selected[i]->row:UINT32_MAX;if(selected[i])out->selected_mask|=1u<<i;}
 for(uint32_t i=0;i<n;i++)out->flags[i]=(uint32_t)entries[i].flags;
}
'''
 return code,{
  'original_raw_sha256':PINS,
  'whole_function_sha256_lf':{k:sha(v.encode()) for k,v in blocks.items()},
  'TexFlags_sha256_lf':sha(enum.encode()),
  'guarded_texFixName_sha256_lf':sha(repaired.encode()),
  'whole_texFindNeededBinds_and_texFind_unchanged':True,
  'explicit_existing_two_location_short_key_repair':True,
  'unchanged_legacy_semantics_for_repaired_short_names':False,
  'original_debug_sentinel_assertions_disabled':True,
  'original_required_default_assertion_observed':True,
  'bounded_cold_first_basename_stash_adapter':True,
  'actual_original_current_CLIENT_table':False,
 }
