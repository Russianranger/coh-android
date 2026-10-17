#include "coh_catalog_seed.h"
#include <string.h>
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static CohStatus length(const char*s,size_t*n){if(!s)return COH_INVALID;for(size_t i=0;i<COH_REP_NAME_MAX;i++){if(!s[i]){*n=i;return COH_OK;}if((unsigned char)s[i]<32||(unsigned char)s[i]>126)return COH_UNSUPPORTED;}return COH_LIMIT;}
static int prefix(const char*s,size_t n,const char*p){size_t m=strlen(p);if(n<m)return 0;for(size_t i=0;i<m;i++){unsigned a=(unsigned char)s[i],b=(unsigned char)p[i];if(a>='A'&&a<='Z')a+='a'-'A';if(a!=b)return 0;}return 1;}
static uint32_t adler(uint32_t v,const uint8_t*p,size_t n){uint32_t a=v&65535,b=v>>16;for(size_t i=0;i<n;i++){a=(a+p[i])%65521u;b=(b+a)%65521u;}return b<<16|a;}
static uint32_t reverse(uint32_t n){return n<<24|(n&0xff00u)<<8|(n&0xff0000u)>>8|n>>24;}
CohStatus coh_source_bounds_checksum(uint32_t file,const char*fname,const CohSourceBoundsChecksumRow*rows,size_t count,uint32_t expected,CohSourceBoundsChecksumReport*out){
 if(!out||!fname||(count&&!rows))return COH_INVALID;
 if(!file)return COH_UNSUPPORTED;
 if(count>COH_SG_DEFS_MAX)return COH_LIMIT;
 size_t fn;TRY(length(fname,&fn));if(!disjoint(out,sizeof(*out),fname,fn+1)||!disjoint(out,sizeof(*out),rows,count*sizeof(*rows)))return COH_INVALID;
 CohSourceBoundsChecksumReport r={0};uint32_t crc=1;
 for(size_t i=0;i<count;i++){
  const CohSourceBoundsChecksumRow*d=&rows[i];size_t n=0;if(d->in_use>1)return COH_STATE;
  if(d->name){TRY(length(d->name,&n));if(!disjoint(out,sizeof(*out),d->name,n+1))return COH_INVALID;}
  if(!disjoint(out,sizeof(*out),d->raw_bounds.data,d->raw_bounds.size))return COH_INVALID;
  if(!d->in_use||!d->name)continue;
  if(prefix(d->name,n,"grp")||!prefix(fname,fn,"object_library"))continue;
  if(!n)return COH_INVALID;
  if(d->name[n-1]=='&')continue;
  if(d->raw_bounds.size!=60||!d->raw_bounds.data)return COH_STATE;
  crc=adler(crc,d->raw_bounds.data,60);crc=adler(crc,(const uint8_t*)d->name,n);r.public_records++;r.bytes_hashed+=60+n;
 }
 r.checksum=reverse(crc);if(r.checksum!=expected)return COH_STATE;*out=r;return COH_OK;
}
typedef struct {const CohRuntimeGraph*graph;uint8_t*mask;size_t rows;uint32_t count;} SeedMask;
static CohStatus mark(void*context,const CohGroupsEvent*e){SeedMask*m=context;if(e->kind!=COH_GROUPS_DEFINITION)return COH_OK;uint32_t node;TRY(coh_runtime_graph_slot(m->graph,e->file,e->slot,&node));if(node>=m->rows||m->mask[node])return COH_STATE;m->mask[node]=1;m->count++;return COH_OK;}
CohStatus coh_catalog_seed_visit(const CohRuntimeGraph*g,const CohCatalogOwner*o,const CohRuntimeGroupsWitness*w,const CohRuntimeGroupsWitnessBinding*b,const CohRepReader*r,const CohRuntimeGroupsBudget*budget,uint8_t*scratch,size_t capacity,CohCatalogSeedVisit visit,void*ctx,CohCatalogSeedReport*out){
 if(!g||!o||!w||!b||!r||!budget||!visit||!out||(capacity&&!scratch))return COH_INVALID;
 CohRuntimeGraphReport gr;CohBytes cat,snap,owned;TRY(coh_runtime_graph_report(g,&gr));TRY(coh_runtime_graph_sources(g,&cat,&snap));TRY(coh_catalog_owner_bytes(o,&owned));if(cat.data!=owned.data||cat.size!=owned.size)return COH_STATE;
 if(capacity<gr.nodes)return COH_LIMIT;
 const void*p[]={b,r,budget,scratch,out,r->bytes.data,cat.data,snap.data};size_t n[]={sizeof(*b),sizeof(*r),sizeof(*budget),capacity,sizeof(*out),r->bytes.size,cat.size,snap.size};
 for(unsigned i=0;i<8;i++)for(unsigned j=i+1;j<8;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;
 if(!gr.source.definitions_crc_verified||!gr.source.references_crc_verified)return COH_STATE;
 CohRuntimeGroupsBudget charged=*budget;if(capacity>charged.aggregate_limit||charged.retained_bytes>charged.aggregate_limit-capacity)return COH_LIMIT;charged.retained_bytes+=capacity;
 CohRuntimeGroupsReport match;TRY(coh_runtime_graph_compare_groups_witness(g,o,w,b,r,&charged,&match));
 if(gr.nodes)memset(scratch,0,gr.nodes);
 SeedMask m={g,scratch,gr.nodes,0};CohGroupsVisitor visitor={&m,mark};CohRepReader copy=*r;CohGroupsInspection groups;TRY(coh_rep_groups_visit(&copy,&visitor,&groups,NULL));if(m.count!=match.emitted_definitions_equal)return COH_STATE;
 CohCatalogSeedReport result={0};result.files=gr.source.files;result.definitions_crc_verified=gr.source.definitions_crc_verified;result.references_crc_verified=gr.source.references_crc_verified;result.aggregate_reserved_bytes=match.aggregate_reserved_bytes;result.protocol_wire_inputs_complete=1;
 for(uint32_t i=0;i<gr.nodes;i++){
  CohRuntimeGraphNode node;TRY(coh_runtime_graph_node(g,i,&node));
  if(!node.external){CohCatalogRecordIdentity ci;TRY(coh_catalog_owner_record(o,node.file,node.slot,&ci));if(!ci.allocated||ci.in_use!=node.in_use)return COH_STATE;result.allocated_definitions++;if(node.in_use)result.active_definitions++;else result.tombstones++;if(scratch[i])result.applied_equal_updates++;else result.omitted_definitions++;}
  else{if(scratch[i])return COH_STATE;result.captured_future_records++;}
  CohCatalogSeedRecord record={i,node.file,node.slot,node.external,node.in_use,scratch[i],node.wire,node.wire_bits,node.aligned};TRY(visit(ctx,&record));
 }
 *out=result;return COH_OK;
}
