#include "coh_runtime_groups.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"runtimegroups line%d %s\n",__LINE__,#x);abort();}}while(0)
static CohBytes load(const char *name){FILE *f=fopen(name,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0);rewind(f);unsigned char *p=malloc((size_t)n);CHECK(p);CHECK(fread(p,1,(size_t)n,f)==(size_t)n);fclose(f);return(CohBytes){p,(size_t)n};}
static CohStatus digest(void *context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_INVALID;}
typedef struct {size_t positions[128],remove_at,remove_bytes;unsigned count;} Positions;
static CohStatus positions(void *context,const CohGroupsEvent *e){Positions *p=context;size_t at=e->span.cursor/8;
 if(e->kind==COH_GROUPS_DEFINITION&&!e->file&&!p->remove_bytes){p->remove_at=at;p->remove_bytes=(e->span.bits-e->span.cursor)/8;}
 if(p->count<128){if(e->kind==COH_GROUPS_FILE_HEADER)at+=1;else if(e->kind==COH_GROUPS_DEFINITION)at+=5;else at+=4;
  if(at<e->span.bits/8&&e->span.bytes.data[at])p->positions[p->count++]=at;}
 return COH_OK;}
int main(int argc,char **argv){
 CHECK(argc==4);CohBytes catalog=load(argv[1]),snapshot=load(argv[2]),wire=load(argv[3]);
 uint32_t generation=(uint32_t)catalog.data[20]|(uint32_t)catalog.data[21]<<8|(uint32_t)catalog.data[22]<<16|(uint32_t)catalog.data[23]<<24;
 CohCatalogBinding cb={0};cb.owner_generation=1;cb.catalog_generation=1;cb.asset_generation=generation;memset(cb.source_sha256,0x11,32);memset(cb.inventory_sha256,0x33,32);CHECK(digest(NULL,catalog,cb.catalog_sha256)==COH_OK);
 CohCatalogOwner *owner=NULL;CohCatalogOwnerBudget ob={COH_SG_MEMORY_MAX,COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohCatalogDigest d={NULL,digest};CohCatalogOwnerReport or;
 /* Catalog owner catalog_generation is original wire cataloggeneration. */
 cb.catalog_generation=generation;CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&d,&owner,&or)==COH_OK);CohBytes owned;CHECK(coh_catalog_owner_bytes(owner,&owned)==COH_OK);
 CohRuntimeGraphBinding binding={0};binding.generation=1;binding.catalog_generation=generation;binding.pins.asset_generation=generation;memcpy(binding.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(binding.pins.source_sha256,cb.source_sha256,32);memset(binding.pins.run_sha256,0x22,32);binding.pins.digest=digest;CHECK(digest(NULL,snapshot,binding.pins.snapshot_sha256)==COH_OK);
 CohRuntimeSnapshotBudget budget={COH_SG_TRANSACTION_MAX,262144+coh_catalog_owner_owned_bytes(owner)};CohRuntimeGraph *graph=NULL;CohRuntimeGraphReport gr;CHECK(coh_runtime_graph_build(NULL,owned,snapshot,&binding,&budget,NULL,&graph,&gr)==COH_OK);
 CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,wire,wire.size*8,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);uint32_t command;CHECK(coh_rep_pack(&reader,1,&command)==COH_OK&&command==COH_REP_GROUPS);CohRepReader before=reader;
 CohRuntimeGroupsReport report,prior;memset(&report,0x41,sizeof(report));prior=report;CohRuntimeGroupsBudget gb={COH_SG_TRANSACTION_MAX,262144};
 CHECK(coh_runtime_graph_compare_groups(graph,owner,&reader,&gb,&report)==COH_OK);CHECK(!memcmp(&reader,&before,sizeof(reader)));CHECK(report.files_equal==gr.source.files&&report.root_wires_equal==gr.source.active_roots);CHECK(!report.world_authority&&!report.assets_admitted&&!report.source_generation_admitted);
 gb.aggregate_limit=report.aggregate_reserved_bytes-1;report=prior;CHECK(coh_runtime_graph_compare_groups(graph,owner,&reader,&gb,&report)==COH_LIMIT);CHECK(!memcmp(&report,&prior,sizeof(report)));gb.aggregate_limit=COH_SG_TRANSACTION_MAX;
 CHECK(coh_runtime_graph_compare_groups(graph,owner,&reader,&gb,(CohRuntimeGroupsReport*)&reader)==COH_INVALID);CHECK(!memcmp(&reader,&before,sizeof(reader)));
 reader.compressed=0;CHECK(coh_runtime_graph_compare_groups(graph,owner,&reader,&gb,&report)==COH_UNSUPPORTED);reader=before;
 for(size_t end=0;end<wire.size*8;end++){reader=before;reader.bits=end;report=prior;CHECK(coh_runtime_graph_compare_groups(graph,owner,&reader,&gb,&report)!=COH_OK);CHECK(!memcmp(&report,&prior,sizeof(report)));}
 Positions points={0};CohGroupsVisitor visitor={&points,positions};CohGroupsInspection inspection;CohRepReader scanned=before;CHECK(coh_rep_groups_visit(&scanned,&visitor,&inspection,NULL)==COH_OK);
 for(unsigned i=0;i<points.count;i++){unsigned char *p=(unsigned char*)wire.data+points.positions[i];*p^=1;reader=before;report=prior;CHECK(coh_runtime_graph_compare_groups(graph,owner,&reader,&gb,&report)!=COH_OK);CHECK(!memcmp(&report,&prior,sizeof(report)));*p^=1;}
 if(points.remove_bytes){unsigned char *removed=malloc(wire.size);CHECK(removed);memcpy(removed,wire.data,wire.size);memmove(removed+points.remove_at,removed+points.remove_at+points.remove_bytes,wire.size-points.remove_at-points.remove_bytes);CohRepReader missing;size_t size=wire.size-points.remove_bytes;CHECK(coh_rep_reader_bounded(&missing,(CohBytes){removed,size},size*8,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);missing.cursor=before.cursor;CohRepReader full=missing;CHECK(coh_rep_groups(&full,&inspection,NULL)==COH_OK);report=prior;CHECK(coh_runtime_graph_compare_groups(graph,owner,&missing,&gb,&report)==COH_STATE);CHECK(!memcmp(&report,&prior,sizeof(report)));free(removed);}
 CohCatalogOwner *other=NULL;CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&d,&other,&or)==COH_OK);reader=before;report=prior;CHECK(coh_runtime_graph_compare_groups(graph,other,&reader,&gb,&report)==COH_STATE);CHECK(!memcmp(&report,&prior,sizeof(report)));coh_catalog_owner_release(other);
 /* Every footer scalar is sourcebound; a changed one cannot commit. */
 for(unsigned n=1;n<=16;n++){unsigned char *p=(unsigned char*)wire.data+wire.size-n;*p^=1;reader=before;report=prior;CHECK(coh_runtime_graph_compare_groups(graph,owner,&reader,&gb,&report)!=COH_OK);CHECK(!memcmp(&report,&prior,sizeof(report)));*p^=1;}
 coh_runtime_graph_free(graph);coh_catalog_owner_release(owner);free((void*)catalog.data);free((void*)snapshot.data);free((void*)wire.data);
 printf("{\"passed\":true,\"checks\":%u,\"live_groups_received\":false,\"world_authority\":false}\n",checks);return 0;
}
