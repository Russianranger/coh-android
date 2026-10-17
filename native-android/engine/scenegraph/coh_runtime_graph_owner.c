#include "coh_runtime_graph_owner.h"
#include <stdlib.h>
#include <string.h>
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
#define LOCAL_RESERVE (64u*1024u)
struct CohRuntimeGraphOwner {
 CohRuntimeGraph *graph;CohCatalogOwner *catalog;CohCatalogSnapshot *snapshot;
 CohBytes cat,snap;CohRuntimeGraphOwnerReport report;uint32_t references;
};
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static int safe(const CohRuntimeGraphOwner*t,const void*p,size_t n){return !t||(disjoint(t,sizeof(*t),p,n)&&disjoint(t->cat.data,t->cat.size,p,n)&&disjoint(t->snap.data,t->snap.size,p,n));}
static int same(const CohCatalogBinding*a,const CohCatalogBinding*b){return a->owner_generation==b->owner_generation&&a->catalog_generation==b->catalog_generation&&a->asset_generation==b->asset_generation&&a->map_generation==b->map_generation&&!memcmp(a->catalog_sha256,b->catalog_sha256,32)&&!memcmp(a->source_sha256,b->source_sha256,32)&&!memcmp(a->inventory_sha256,b->inventory_sha256,32)&&!memcmp(a->map_sha256,b->map_sha256,32);}
void coh_runtime_graph_owner_release(CohRuntimeGraphOwner*t){if(!t||--t->references)return;coh_runtime_graph_free(t->graph);coh_catalog_snapshot_release(t->snapshot);coh_catalog_owner_release(t->catalog);free(t);}
CohStatus coh_runtime_graph_owner_retain(CohRuntimeGraphOwner*t){if(!t)return COH_INVALID;if(t->references==UINT32_MAX)return COH_LIMIT;t->references++;return COH_OK;}
CohStatus coh_runtime_graph_owner_view(const CohRuntimeGraphOwner*t,const CohRuntimeGraph**g,CohCatalogOwner**c,CohCatalogSnapshot**s,CohRuntimeGraphOwnerReport*r){
 if(!t||!g||!c||!s||!r)return COH_INVALID;
 const void*p[]={g,c,s,r};size_t n[]={sizeof(*g),sizeof(*c),sizeof(*s),sizeof(*r)};
 for(unsigned i=0;i<4;i++){if(!safe(t,p[i],n[i]))return COH_INVALID;for(unsigned j=i+1;j<4;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;}
 *g=t->graph;*c=t->catalog;*s=t->snapshot;*r=t->report;return COH_OK;
}
CohStatus coh_runtime_graph_owner_create(const CohRuntimeGraphOwner*old,CohCatalogOwner*catalog,CohCatalogSnapshot*snapshot,uint32_t generation,const CohRuntimeGraphOwnerBudget*budget,const CohCatalogDigest*digest,const CohCancel*cancel,CohRuntimeGraphOwner**out,CohRuntimeGraphOwnerReport*report){
 if(!catalog||!snapshot||!budget||!digest||!digest->sha256||!out||!report)return COH_INVALID;
 CohBytes cat,snap,scat;CohCatalogBinding cb;CohCatalogSnapshotBinding sb;
 union {CohRuntimeSnapshotReport snapshot;CohRuntimeGraphReport graph;} m;
 TRY(coh_catalog_owner_bytes(catalog,&cat));TRY(coh_catalog_owner_binding(catalog,&cb));TRY(coh_catalog_snapshot_catalog(snapshot,&scat));TRY(coh_catalog_snapshot_view(snapshot,&snap,&sb,&m.snapshot));
 const void*p[]={budget,digest,cancel,out,report,cat.data,snap.data};size_t n[]={sizeof(*budget),sizeof(*digest),cancel?sizeof(*cancel):0,sizeof(*out),sizeof(*report),cat.size,snap.size};
 for(unsigned i=0;i<7;i++){if(i<5&&!safe(old,p[i],n[i]))return COH_INVALID;for(unsigned j=i+1;j<7;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;}
 if(*out)return COH_STATE;
 if(scat.data!=cat.data||scat.size!=cat.size||!same(&cb,&sb.catalog)||!m.snapshot.definitions_crc_verified||!m.snapshot.references_crc_verified||!m.snapshot.root_matrices_verified||!m.snapshot.complete_source_name_closure)return COH_STATE;
 if(old){CohCatalogBinding previous;CohCatalogSnapshotBinding ps;CohBytes ignored;TRY(coh_catalog_owner_binding(old->catalog,&previous));TRY(coh_catalog_snapshot_view(old->snapshot,&ignored,&ps,&m.snapshot));if(sb.generation<ps.generation||cb.owner_generation<previous.owner_generation||cb.asset_generation<previous.asset_generation||(cb.asset_generation==previous.asset_generation&&memcmp(cb.inventory_sha256,previous.inventory_sha256,32)))return COH_STATE;}
 size_t own=sizeof(CohRuntimeGraphOwner),limit=budget->aggregate_limit,cat_owned=coh_catalog_owner_owned_bytes(catalog),snap_owned=coh_catalog_snapshot_owned_bytes(snapshot);
 if(!limit||limit>COH_SG_TRANSACTION_MAX||budget->owned_limit<=own||budget->owned_limit>COH_SG_MEMORY_MAX||cat_owned<cat.size||snap_owned<snap.size||budget->retained_bytes>limit)return COH_LIMIT;
 size_t retained=budget->retained_bytes;size_t charges[]={own,cat_owned-cat.size,snap_owned-snap.size,old?old->report.owner_bytes:0,old?old->report.dependencies_bytes-old->cat.size-old->snap.size:0,LOCAL_RESERVE};
 for(unsigned i=0;i<sizeof(charges)/sizeof(*charges);i++){if(charges[i]>limit-retained)return COH_LIMIT;retained+=charges[i];}
 CohRuntimeGraphBinding gb;memset(&gb,0,sizeof(gb));gb.generation=generation;gb.catalog_generation=cb.catalog_generation;gb.pins.asset_generation=cb.asset_generation;gb.pins.digest=digest->sha256;gb.pins.context=digest->context;memcpy(gb.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(gb.pins.source_sha256,cb.source_sha256,32);memcpy(gb.pins.snapshot_sha256,sb.snapshot_sha256,32);memcpy(gb.pins.run_sha256,sb.run_sha256,32);
 if(cancel&&cancel->poll&&cancel->poll(cancel->context))return COH_CANCELLED;
 CohRuntimeGraph*graph=NULL;
 CohStatus status=coh_catalog_owner_retain(catalog);if(status!=COH_OK)return status;
 status=coh_catalog_snapshot_retain(snapshot);if(status!=COH_OK){coh_catalog_owner_release(catalog);return status;}
 CohRuntimeSnapshotBudget inner={limit,retained};
 status=coh_runtime_graph_build_limited(old?old->graph:NULL,cat,snap,&gb,&inner,cancel,budget->owned_limit-own,&graph,&m.graph);
 if(status!=COH_OK){coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);return status;}
 CohRuntimeGraphOwner*t=calloc(1,own);if(!t){coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);return COH_LIMIT;}
 t->references=1;t->cat=cat;t->snap=snap;t->graph=graph;t->catalog=catalog;t->snapshot=snapshot;
 t->report=(CohRuntimeGraphOwnerReport){generation,m.graph.nodes,m.graph.edges,own,m.graph.owned_bytes,cat_owned+snap_owned,m.graph.aggregate_peak_bytes};*report=t->report;*out=t;return COH_OK;
}
