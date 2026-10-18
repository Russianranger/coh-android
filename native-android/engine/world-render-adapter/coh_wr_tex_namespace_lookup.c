#include "coh_wr_tex_namespace_lookup.h"
#include <stdint.h>
#include <string.h>
#define LOOKUP_CONTROL 16384u
static int separate(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return n<=UINTPTR_MAX-x&&m<=UINTPTR_MAX-y&&(x+n<=y||y+m<=x);}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static int metadata_output(const CohWrTexNamespaceBasic*b,const void*out,size_t n){
 return separate(b->asset.path,strlen(b->asset.path)+1,out,n)&&separate(b->original_name,strlen(b->original_name)+1,out,n)&&separate(b->directory,strlen(b->directory)+1,out,n)&&separate(b->basic_key,strlen(b->basic_key)+1,out,n)&&separate(b->cached_mips.data,b->cached_mips.size,out,n);
}
_Static_assert(sizeof(CohWrTexNamespaceLookup)+sizeof(CohWrTexNamespaceReport)+sizeof(CohWrTexNamespaceBasic)+4096<LOOKUP_CONTROL,"bounded lookup control");
CohStatus coh_wr_tex_namespace_lookup(const CohWrTexNamespace*source,const char*query,const CohWrTexNamespaceLookupLimits*limits,CohWrTexNamespaceLookup*out){
 if(!source||!limits||!out||(uintptr_t)limits%_Alignof(CohWrTexNamespaceLookupLimits)||(uintptr_t)out%_Alignof(CohWrTexNamespaceLookup)||!separate(limits,sizeof(*limits),out,sizeof(*out)))return COH_INVALID;
 if(limits->guarded_short_keys>1)return COH_UNSUPPORTED;
 CohWrTexNamespaceReport report;CohStatus status=coh_wr_tex_namespace_report(source,&report);if(status!=COH_OK)return status;
 size_t n=0;if(query){for(;n<129;n++){unsigned c=(unsigned char)query[n];if(!c)break;if(c<32||c>126)return COH_UNSUPPORTED;}if(n==129)return COH_LIMIT;if(!separate(query,n+1,out,sizeof(*out)))return COH_INVALID;}
 size_t total=limits->external_bytes;
 if(total<report.aggregate_reserved_bytes||!add(&total,LOOKUP_CONTROL)||!add(&total,sizeof(*limits)+sizeof(*out)+(query?n+1:0))||total>limits->aggregate_limit)return COH_LIMIT;
 /* No private-layout assumptions. Opaque provider/source output disjointness
  * remains a caller precondition; reject every exposed metadata span as well. */
 for(uint32_t row=0;row<report.basic_rows;row++){CohWrTexNamespaceBasic basic;status=coh_wr_tex_namespace_basic(source,row,&basic);if(status!=COH_OK)return status;if(!metadata_output(&basic,out,sizeof(*out)))return COH_INVALID;}
 CohWrTexNamespaceLookup value;memset(&value,0,sizeof(value));value.row=value.first_owner_row=UINT32_MAX;value.source_input_generation=report.source_input_generation;value.guarded_short_keys=limits->guarded_short_keys;value.current_CLIENT_unqualified=1;value.aggregate_reserved_bytes=total;
 if(!query){value.branch=COH_WR_TEX_NS_LOOKUP_NULL;*out=value;return COH_OK;}
 if(query[0]=='!'){query++;n--;}if(n>127)return COH_LIMIT;memcpy(value.key,query,n+1);
 if(n<4)value.format_flags=1u<<5;
 else if(value.key[n-4]=='.'){const char*extension=value.key+n-3;if(!strcmp(extension,"tga"))value.format_flags=1u<<5;else if(!strcmp(extension,"jpg"))value.format_flags=1u<<13;else if(!strcmp(extension,"dds"))value.format_flags=1u<<6;value.key[n-4]=0;}
 else if(n<8){if(!limits->guarded_short_keys)return COH_UNSUPPORTED;}
 else if(value.key[n-8]=='.'){if(!strcmp(value.key+n-7,"texture"))value.format_flags=1u<<6;value.key[n-8]=0;}
 CohWrTexNamespaceBasic basic;status=coh_wr_tex_namespace_find(source,value.key,&basic);
 if(status==COH_NOT_FOUND)value.branch=COH_WR_TEX_NS_LOOKUP_ABSENT;
 else if(status!=COH_OK)return status;
 else {size_t path_bytes=strlen(basic.asset.path);if(path_bytes>=sizeof(value.asset_path))return COH_LIMIT;value.branch=COH_WR_TEX_NS_LOOKUP_FOUND;value.row=basic.row;value.first_owner_row=basic.first_owner_row;value.asset_generation=basic.asset.generation;memcpy(value.asset_path,basic.asset.path,path_bytes+1);memcpy(value.sha256,basic.sha256,32);}
 *out=value;return COH_OK;
}
