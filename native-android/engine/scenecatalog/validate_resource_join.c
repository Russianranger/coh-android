/* Host diagnostic only: exact externally pinned capture bytes, no GEO/assets. */
#include "coh_resource_join.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static CohStatus digest(void *context,CohBytes bytes,uint8_t out[32]){(void)context;return SHA256(bytes.data,bytes.size,out)?COH_OK:COH_IO;}
static int hex(const char *s,uint8_t out[32]){if(strlen(s)!=64)return 0;for(unsigned n=0;n<32;n++){unsigned a=(unsigned char)s[2*n],b=(unsigned char)s[2*n+1];a=a>='0'&&a<='9'?a-'0':a>='a'&&a<='f'?a-'a'+10:16;b=b>='0'&&b<='9'?b-'0':b>='a'&&b<='f'?b-'a'+10:16;if(a>15||b>15)return 0;out[n]=(uint8_t)(16*a+b);}return 1;}
static CohStatus read_file(const char *path,size_t cap,CohBytes *out){FILE *f=fopen(path,"rb");if(!f)return COH_IO;if(fseek(f,0,SEEK_END)){fclose(f);return COH_IO;}long n=ftell(f);if(n<=0||(size_t)n>cap){fclose(f);return COH_LIMIT;}rewind(f);uint8_t *data=malloc((size_t)n);if(!data){fclose(f);return COH_LIMIT;}size_t got=fread(data,1,(size_t)n,f);int closed=fclose(f);if(got!=(size_t)n||closed){free(data);return COH_IO;}*out=(CohBytes){data,(size_t)n};return COH_OK;}
int main(int argc,char **argv){
    CohStatus status=COH_INVALID;CohBytes input={0},side={0},resources={0},cat={0},snapshot_bytes={0};CohCatalogOwner *catalog=NULL;CohCatalogSnapshot *snapshot=NULL;CohRuntimeGraph *graph=NULL;CohResourceJoin *join=NULL;
    CohCatalogBinding cb={0};CohCatalogSnapshotBinding sb={0};CohResourceJoinPins pins={0};CohCatalogDigest dig={NULL,digest};CohCatalogOwnerReport cr={0};CohRuntimeSnapshotReport sr={0};CohRuntimeGraphReport gr={0};CohResourceJoinReport jr={0};
    if(argc!=10)goto done;
    cb.owner_generation=1;cb.catalog_generation=20261016;cb.asset_generation=20261016;
    if(!hex("61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763",cb.catalog_sha256)||!hex(argv[4],cb.source_sha256)||!hex(argv[6],cb.inventory_sha256)||!hex(argv[5],sb.run_sha256)||!hex(argv[7],sb.snapshot_sha256)||!hex(argv[8],pins.resources_sha256)||!hex(argv[9],pins.resource.manifest_sha256))goto done;
    status=read_file(argv[1],COH_CATALOG_INPUT_MAX,&input);if(status!=COH_OK)goto done;
    CohCatalogOwnerBudget cbudget={32u<<20,32u<<20,96u<<20,262144};status=coh_catalog_owner_create(NULL,input,&cb,&cbudget,&dig,&catalog,&cr);if(status!=COH_OK)goto done;free((void *)input.data);input=(CohBytes){0};
    status=read_file(argv[2],COH_RUNTIME_SNAPSHOT_INPUT_MAX,&side);if(status!=COH_OK)goto done;sb.generation=1;sb.catalog=cb;CohRuntimeSnapshotBudget sbudget={96u<<20,262144};status=coh_catalog_snapshot_create(NULL,catalog,side,&sb,&sbudget,&dig,NULL,&snapshot);if(status!=COH_OK)goto done;free((void *)side.data);side=(CohBytes){0};
    status=coh_catalog_owner_bytes(catalog,&cat);if(status!=COH_OK)goto done;status=coh_catalog_snapshot_view(snapshot,&snapshot_bytes,&sb,&sr);if(status!=COH_OK)goto done;
    CohRuntimeGraphBinding gb={0};gb.generation=1;gb.catalog_generation=cb.catalog_generation;gb.pins.asset_generation=cb.asset_generation;gb.pins.digest=digest;memcpy(gb.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(gb.pins.snapshot_sha256,sb.snapshot_sha256,32);memcpy(gb.pins.source_sha256,cb.source_sha256,32);memcpy(gb.pins.run_sha256,sb.run_sha256,32);
    CohRuntimeSnapshotBudget gbudget={96u<<20,coh_catalog_owner_owned_bytes(catalog)-cat.size+coh_catalog_snapshot_owned_bytes(snapshot)-snapshot_bytes.size+262144};status=coh_runtime_graph_build(NULL,cat,snapshot_bytes,&gb,&gbudget,NULL,&graph,&gr);if(status!=COH_OK)goto done;
    status=read_file(argv[3],COH_RESOURCE_INPUT_MAX,&resources);if(status!=COH_OK)goto done;pins.resource.generation=1;pins.resource.asset_generation=cb.asset_generation;memcpy(pins.resource.source_sha256,cb.source_sha256,32);memcpy(pins.resource.run_sha256,sb.run_sha256,32);
    CohResourceJoinBudget budget={32u<<20,96u<<20,262144};CohCancel never={NULL,NULL};status=coh_resource_join_build(NULL,catalog,snapshot,graph,resources,&pins,&budget,digest,NULL,never,&join,&jr);
 done:
    if(status==COH_OK)printf("{\"passed\":true,\"rows\":%u,\"regular\":%u,\"external\":%u,\"model_references\":%u,\"source_association_verified\":true,\"join_owned_bytes\":%zu,\"join_aggregate_peak_bytes\":%zu,\"catalog_import_peak_bytes\":%zu,\"graph_import_peak_bytes\":%zu,\"catalog_bytes\":%zu,\"snapshot_bytes\":%zu,\"resource_input_bytes\":%zu,\"fixture_slab_allocated\":false,\"resource_indices_built\":false,\"assets_admitted\":false,\"client_materials_available\":false,\"live_groups_transaction\":false,\"world_authority\":false}\n",jr.rows,jr.regular,jr.external,jr.models,jr.owned_bytes,jr.aggregate_peak_bytes,cr.peak_aggregate_bytes,gr.aggregate_peak_bytes,cat.size,snapshot_bytes.size,resources.size);
    else printf("{\"passed\":false,\"status\":%d,\"assets_admitted\":false,\"world_authority\":false}\n",status);
    coh_resource_join_free(join);coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);free((void *)resources.data);free((void *)side.data);free((void *)input.data);return status==COH_OK?0:2;
}
