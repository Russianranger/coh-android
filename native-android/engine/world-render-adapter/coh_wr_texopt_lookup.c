#include "coh_wr_texopt_lookup.h"
#include "coh_wr_texopt_types_internal.h"
#include <stdint.h>
#include <string.h>
#define MAX_PATH 260
#define LOOKUP_RESERVE 16384u
typedef struct{const CohWrTexOptCache*cache;const CohWrSurfaceStates*surface;CohWrTexOptLimits limits;CohCancel cancel;CohStatus status;CohWrTexOptRecord*record;TexOpt stub;CohWrTexOptLookup result;}Lookup;
_Static_assert(sizeof(Lookup)+4096<LOOKUP_RESERVE,"lookup control and source frame reservation");
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int icmp(const char*a,const char*b){for(;*a&&*b;a++,b++){int d=(int)fold((unsigned char)*a)-(int)fold((unsigned char)*b);if(d)return d;}return (unsigned char)*a-(unsigned char)*b;}
static int nicmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){int d=(int)fold((unsigned char)a[i])-(int)fold((unsigned char)b[i]);if(d||!a[i]||!b[i])return d;}return 0;}
static const char*strstriConst(const char*s,const char*k){for(;*s;s++)if(!nicmp(s,k,strlen(k)))return s;return NULL;}
static char*findi(char*s,const char*k){return (char*)strstriConst(s,k);}
static void slashes(char*s){for(;*s;s++)if(*s=='\\')*s='/';}
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static void lookup(Lookup*c,const char*key,TexOpt**out){
 *out=NULL;if(c->status!=COH_OK)return;c->result.attempts++;
 if(c->cancel.poll&&c->cancel.poll(c->cancel.context)){c->status=COH_CANCELLED;return;}
 if(!*key)return;
 uint32_t ordinal;CohStatus s=coh_wr_texopt_cache_find(c->cache,key,&ordinal);if(s==COH_NOT_FOUND)return;if(s!=COH_OK){c->status=s;return;}
 s=coh_wr_texopt_record_create(c->cache,ordinal,c->surface,&c->limits,c->cancel,&c->record);if(s!=COH_OK){c->status=s;return;}
 CohWrTexOptView v;s=coh_wr_texopt_record_view(c->record,&v);if(s!=COH_OK){c->status=s;return;}
 c->stub.flags=(TexOptFlags)v.flags;c->result.matched=1;c->result.source_ordinal=ordinal;c->result.direct=c->result.attempts==1;strcpy(c->result.matched_key,key);*out=&c->stub;
}
#define stricmp icmp
#define strnicmp nicmp
#define strstri findi
#define forwardSlashes slashes
#define stashFindPointer(table,key,out) lookup(ctx,key,out)
#define strEndsWith private_ends
#define texOptFlagsFromName private_flags
static int private_ends(const char*,const char*);
static TexOptFlags private_flags(const char*,TexOptFlags);
static TexOpt*source_lookup(Lookup*,const char*,TexOptFlags*);
#include "coh_wr_texopt_lookup_source.inc"
CohStatus coh_wr_texopt_lookup(const CohWrTexOptCache*c,const CohWrSurfaceStates*s,const char*path,const CohWrTexOptLimits*l,CohCancel cancel,CohWrTexOptLookup*out,CohWrTexOptRecord**record){
 if(!c||!s||!path||!l||!out||!record)return COH_INVALID;
 CohWrTexOptCacheReport cr;CohWrSurfaceReport sr;CohStatus status=coh_wr_texopt_cache_report(c,&cr);if(status!=COH_OK)return status;status=coh_wr_surface_report(s,&sr);if(status!=COH_OK)return status;
 if(!apart(out,sizeof(*out),record,sizeof(*record))||!apart(c,cr.owned_bytes,out,sizeof(*out))||!apart(c,cr.owned_bytes,record,sizeof(*record))||!apart(s,sr.owned_bytes,out,sizeof(*out))||!apart(s,sr.owned_bytes,record,sizeof(*record))||!apart(l,sizeof(*l),out,sizeof(*out))||!apart(l,sizeof(*l),record,sizeof(*record)))return COH_INVALID;
 if(*record)return COH_STATE;
 size_t n=0;int slash=0;for(;n<260;n++){unsigned x=(unsigned char)path[n];if(!x)break;if(x<32||x>126)return COH_UNSUPPORTED;if(x=='/'||x=='\\')slash=1;}if(n==260)return COH_LIMIT;if(!n||!slash||path[n-1]=='/'||path[n-1]=='\\')return COH_UNSUPPORTED;
 char domain[260];memcpy(domain,path,n+1);slashes(domain);char*root=findi(domain,"texture_library");if(root){root+=15;if(*root=='/')root++;if(!*root)return COH_UNSUPPORTED;}
 if(!apart(path,n+1,out,sizeof(*out))||!apart(path,n+1,record,sizeof(*record)))return COH_INVALID;
 if(sr.historical_input_generation!=cr.historical_input_generation)return COH_STATE;
 size_t minimum=cr.owned_bytes;if(cr.loader_reservation>SIZE_MAX-minimum)return COH_LIMIT;minimum+=cr.loader_reservation;if(sr.owned_bytes>SIZE_MAX-minimum)return COH_LIMIT;minimum+=sr.owned_bytes;if(16384>SIZE_MAX-minimum)return COH_LIMIT;minimum+=16384;
 if(l->external_bytes<minimum||l->external_bytes>SIZE_MAX-LOOKUP_RESERVE||l->external_bytes+LOOKUP_RESERVE>l->aggregate_limit)return COH_LIMIT;
 Lookup ctx;memset(&ctx,0,sizeof(ctx));ctx.cache=c;ctx.surface=s;ctx.limits=*l;ctx.limits.external_bytes+=LOOKUP_RESERVE;ctx.cancel=cancel;ctx.result.unresolved_client_semantics=1;ctx.result.source_ordinal=UINT32_MAX;ctx.result.historical_input_generation=cr.historical_input_generation;memcpy(ctx.result.cache_sha256,cr.cache_sha256,32);
 if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;
 TexOptFlags flags=0;(void)source_lookup(&ctx,path,&flags);if(ctx.status!=COH_OK){coh_wr_texopt_record_release(&ctx.record);return ctx.status;}
 if(cancel.poll&&cancel.poll(cancel.context)){coh_wr_texopt_record_release(&ctx.record);return COH_CANCELLED;}ctx.result.name_flags=(uint32_t)flags;*out=ctx.result;*record=ctx.record;return COH_OK;
}
