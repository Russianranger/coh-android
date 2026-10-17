#include "coh_wr_texname.h"
#include <string.h>
#include <stdint.h>
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int equal(const char*a,const char*b){while(*a&&*b){if(lower((unsigned char)*a++)!=lower((unsigned char)*b++))return 0;}return *a==*b;}
static int portal(const char*s){for(;*s;s++){const char*key="portal";unsigned i=0;while(key[i]&&s[i]&&lower((unsigned char)s[i])==(unsigned)key[i])i++;if(!key[i])return 1;}return 0;}
static CohStatus length(const char*s,size_t cap,size_t*out){if(!s)return COH_INVALID;for(size_t n=0;n<=cap;n++){unsigned c=(unsigned char)s[n];if(!c){*out=n;return COH_OK;}if(c<32||c>126)return COH_UNSUPPORTED;}return COH_LIMIT;}
static int disjoint(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
CohStatus coh_wr_texname_project(const CohWrTexNameInput*q,CohWrTexNameProjection*out){
 if(!q||!out||!disjoint(q,sizeof(*q),out,sizeof(*out)))return COH_INVALID;
 if(q->texture_count>65536||q->swap_count>COH_WR_TEXNAME_SWAPS_MAX)return COH_LIMIT;
 if(q->swap_count&&(!q->scene_material_swaps||!disjoint(q->scene_material_swaps,q->swap_count*sizeof(*q->scene_material_swaps),out,sizeof(*out))))return COH_INVALID;
 CohWrTexNameProjection result;memset(&result,0,sizeof(result));result.scene_swap_index=UINT32_MAX;
 if(!q->texture_count){if(q->name)return COH_INVALID;result.branch=COH_WR_TEXNAME_EMPTY_TABLE_BRANCH;*out=result;return COH_OK;}
 size_t n=0;CohStatus status=length(q->name,COH_WR_TEXNAME_INPUT_MAX,&n);if(status!=COH_OK)return status;
 if(!n||!disjoint(q->name,n+1,out,sizeof(*out)))return COH_INVALID;
 memcpy(result.stripped,q->name,n+1);char*dot=strrchr(result.stripped,'.');if(dot)memset(dot,0,sizeof(result.stripped)-(size_t)(dot-result.stripped));
 if(portal(result.stripped)){result.branch=COH_WR_TEXNAME_PORTAL_BRANCH;*out=result;return COH_OK;}
 const char*name=result.stripped;if(*name=='!')name++;n=strlen(name);if(n>COH_WR_TEXNAME_KEY_MAX)return COH_LIMIT;
 memcpy(result.composite_key,name,n+1);
 if(n>=4){if(name[n-4]=='.')memset(result.composite_key+n-4,0,sizeof(result.composite_key)-n+4);else if(n<8)return COH_UNSUPPORTED;else if(name[n-8]=='.')memset(result.composite_key+n-8,0,sizeof(result.composite_key)-n+8);}
 for(uint32_t i=0;i<q->swap_count;i++){
  const CohWrMaterialNameSwap*s=&q->scene_material_swaps[i];size_t a,b;
  status=length(s->source,COH_WR_TEXNAME_KEY_MAX,&a);if(status!=COH_OK)return status;
  status=length(s->destination,COH_WR_TEXNAME_KEY_MAX,&b);if(status!=COH_OK)return status;
  if(!disjoint(s->source,a+1,out,sizeof(*out))||!disjoint(s->destination,b+1,out,sizeof(*out)))return COH_INVALID;
  if(result.scene_swap_index==UINT32_MAX&&equal(result.composite_key,s->source)){
   memset(result.composite_key,0,sizeof(result.composite_key));memcpy(result.composite_key,s->destination,b+1);result.scene_swap_index=i;
  }
 }
 result.branch=COH_WR_TEXNAME_COMPOSITE_LOOKUP;*out=result;return COH_OK;
}
