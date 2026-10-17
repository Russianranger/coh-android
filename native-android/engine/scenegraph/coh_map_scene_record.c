#include "coh_map_scene_record.h"
#include <stdlib.h>
#include <string.h>
#define LOCAL_RESERVE (64u*1024u)
struct CohMapSceneRecord {CohMapSceneRecordReport report;uint8_t*bytes;uint32_t references;};
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static CohStatus poll(const CohCancel*c){return c&&c->poll&&c->poll(c->context)?COH_CANCELLED:COH_OK;}
void coh_map_scene_record_release(CohMapSceneRecord*r){if(!r||--r->references)return;free(r->bytes);free(r);}
CohStatus coh_map_scene_record_retain(CohMapSceneRecord*r){if(!r)return COH_INVALID;if(r->references==UINT32_MAX)return COH_LIMIT;r->references++;return COH_OK;}
CohStatus coh_map_scene_record_view(const CohMapSceneRecord*r,CohMapSceneRecordReport*out){if(!r||!out)return COH_INVALID;if(!disjoint(out,sizeof(*out),r,sizeof(*r))||!disjoint(out,sizeof(*out),r->bytes,r->report.receive.reader.bytes.size))return COH_INVALID;*out=r->report;return COH_OK;}
CohStatus coh_map_scene_record_create(const CohMapClient*client,const CohMapSceneObservation*event,const CohMapSceneRecordBudget*budget,const CohCatalogDigest*digest,const CohCancel*cancel,CohMapSceneRecord**out,CohMapSceneRecordReport*report){
 if(!client||!event||!budget||!digest||!digest->sha256||!out||!report)return COH_INVALID;
 CohMapSceneLease lease;CohStatus status=coh_map_client_scene_lease(client,event,&lease);if(status!=COH_OK)return status;
 const void*p[]={event,budget,digest,cancel,out,report,lease.reader.bytes.data};size_t n[]={sizeof(*event),sizeof(*budget),sizeof(*digest),cancel?sizeof(*cancel):0,sizeof(*out),sizeof(*report),lease.reader.bytes.size};
 for(unsigned i=0;i<7;i++)for(unsigned j=i+1;j<7;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;
 if(*out)return COH_STATE;
 size_t own=sizeof(CohMapSceneRecord)+lease.reader.bytes.size,limit=budget->aggregate_limit,total=budget->retained_bytes;
 if(!budget->owned_limit||budget->owned_limit>COH_SG_MEMORY_MAX||own>budget->owned_limit||!limit||limit>COH_SG_TRANSACTION_MAX||total>limit)return COH_LIMIT;
 size_t add[]={own,lease.reader.bytes.size,LOCAL_RESERVE};for(unsigned i=0;i<3;i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];}
 status=poll(cancel);if(status!=COH_OK)return status;
 CohMapSceneRecord*r=calloc(1,sizeof(*r));if(!r)return COH_LIMIT;r->references=1;r->bytes=malloc(lease.reader.bytes.size);if(!r->bytes){coh_map_scene_record_release(r);return COH_LIMIT;}
 memcpy(r->bytes,lease.reader.bytes.data,lease.reader.bytes.size);r->report.receive=lease;r->report.receive.reader.bytes.data=r->bytes;r->report.owned_bytes=own;r->report.aggregate_reserved_bytes=total;r->report.actual_client_loan_verified=1;
 status=digest->sha256(digest->context,r->report.receive.reader.bytes,r->report.packet_sha256);if(status==COH_OK)status=poll(cancel);
 if(status!=COH_OK){coh_map_scene_record_release(r);return status;}
 *report=r->report;*out=r;return COH_OK;
}
