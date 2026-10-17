#define _POSIX_C_SOURCE 200809L
#define OPENSSL_SUPPRESS_DEPRECATED
#include "coh_source_mesh.h"
#include "coh_wr_trick.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"mesh line%d: %s\n",__LINE__,#x);abort();}checks++;}while(0)
static unsigned checks;
static void hex(const char*s,uint8_t out[32]){for(unsigned n=0;n<32;n++){unsigned v;CHECK(sscanf(s+n*2,"%2x",&v)==1);out[n]=(uint8_t)v;}}
static CohStatus digest(void*ctx,CohBytes b,uint8_t out[32]){(void)ctx;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
static CohStatus wrong(void*ctx,CohBytes b,uint8_t out[32]){CohStatus s=digest(ctx,b,out);out[0]^=1;return s;}
static CohBytes file(const char*path,size_t max){FILE*f=fopen(path,"rb");CHECK(f&&!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&(size_t)n<=max);rewind(f);uint8_t*p=malloc((size_t)n);CHECK(p&&fread(p,1,(size_t)n,f)==(size_t)n&&!fclose(f));return(CohBytes){p,(size_t)n};}
static CohStatus read_at(void*ctx,uint64_t off,void*dst,size_t n){FILE*f=ctx;if(off>0x7fffffffu||fseek(f,(long)off,SEEK_SET)||fread(dst,1,n,f)!=n)return COH_IO;return COH_OK;}
static int stop(void*x){(void)x;return 1;}
typedef struct{unsigned calls,at;}Poll;static int stop_late(void*x){Poll*p=x;return ++p->calls==p->at;}
static unsigned fail_at,alloc_count;static void*live[3];
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);void __real_free(void*);
void*__wrap_malloc(size_t n){if(fail_at&&++alloc_count==fail_at)return NULL;void*p=__real_malloc(n);if(fail_at&&p)for(unsigned k=0;k<3;k++)if(!live[k]){live[k]=p;break;}return p;}
void*__wrap_calloc(size_t a,size_t b){if(fail_at&&++alloc_count==fail_at)return NULL;void*p=__real_calloc(a,b);if(fail_at&&p)for(unsigned k=0;k<3;k++)if(!live[k]){live[k]=p;break;}return p;}
void __wrap_free(void*p){for(unsigned k=0;k<3;k++)if(live[k]==p)live[k]=NULL;__real_free(p);}
int main(int argc,char**argv){CHECK(argc==13);CohCancel never={NULL,NULL};CohCatalogDigest dig={NULL,digest};CohBytes input=file(argv[1],32u<<20),side={0},resources={0};CohSourceSelectionEvidence evidence;
 CohCatalogBinding cb={0};cb.owner_generation=1;cb.catalog_generation=cb.asset_generation=20261016;hex("61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763",cb.catalog_sha256);hex("9b74823a341fe565a978f81516b3b13ea8741ec8ecc57bb2b8bfb40130943eaa",cb.source_sha256);hex("f2bd6c0bac0ea8dafbf76cdff40b33089c48318a968d3db6fbb20899e172f99f",cb.inventory_sha256);
 CohCatalogOwner*catalog=NULL;CohCatalogOwnerReport cr;CohCatalogOwnerBudget cbudget={32u<<20,32u<<20,96u<<20,262144};CHECK(coh_catalog_owner_create(NULL,input,&cb,&cbudget,&dig,&catalog,&cr)==COH_OK);free((void*)input.data);
 side=file(argv[2],1u<<20);
 CohCatalogSnapshotBinding sb={0};sb.generation=1;sb.catalog=cb;hex("c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02",sb.snapshot_sha256);hex("e6a25d7e6429fbb856fad617c5f8eeab75325c0fb7c0083be7f91348e5765ced",sb.run_sha256);CohCatalogSnapshot*snapshot=NULL;CohRuntimeSnapshotBudget sbudget={96u<<20,262144};CHECK(coh_catalog_snapshot_create(NULL,catalog,side,&sb,&sbudget,&dig,NULL,&snapshot)==COH_OK);free((void*)side.data);
 CohBytes cat,snap;CohRuntimeSnapshotReport sr;CHECK(coh_catalog_owner_bytes(catalog,&cat)==COH_OK);CHECK(coh_catalog_snapshot_view(snapshot,&snap,&sb,&sr)==COH_OK);CohRuntimeGraphBinding gb={0};gb.generation=1;gb.catalog_generation=20261016;gb.pins.asset_generation=20261016;gb.pins.digest=digest;memcpy(gb.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(gb.pins.snapshot_sha256,sb.snapshot_sha256,32);memcpy(gb.pins.source_sha256,cb.source_sha256,32);memcpy(gb.pins.run_sha256,sb.run_sha256,32);
 CohRuntimeGraph*graph=NULL;CohRuntimeGraphReport gr;CohRuntimeSnapshotBudget gbudget={96u<<20,coh_catalog_owner_owned_bytes(catalog)-cat.size+coh_catalog_snapshot_owned_bytes(snapshot)-snap.size+262144};CHECK(coh_runtime_graph_build(NULL,cat,snap,&gb,&gbudget,NULL,&graph,&gr)==COH_OK);
 resources=file(argv[3],32u<<20);
 CohResourceJoinPins jp={0};jp.resource.generation=1;jp.resource.asset_generation=20261016;memcpy(jp.resource.source_sha256,cb.source_sha256,32);memcpy(jp.resource.run_sha256,sb.run_sha256,32);hex("7c42a9612e4e08ee6463c3a8f87d2cf0749ff2baa8183d6b3c58281ec004c39c",jp.resource.manifest_sha256);hex("8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6",jp.resources_sha256);CohResourceJoin*join=NULL;CohResourceJoinReport jr;CohResourceJoinBudget jbudget={32u<<20,96u<<20,262144};CHECK(coh_resource_join_build(NULL,catalog,snapshot,graph,resources,&jp,&jbudget,digest,NULL,never,&join,&jr)==COH_OK);free((void*)resources.data);
 for(unsigned n=0;n<7;n++){evidence.bytes[n]=file(argv[4+n],8u<<20);}
 size_t evidencebytes=0;for(unsigned n=0;n<7;n++)evidencebytes+=evidence.bytes[n].size;
 CohSourceSelectionBudget budget={2u<<20,96u<<20,262144};CohSourceSelection*selection=NULL;CohSourceSelectionReport report;CHECK(coh_source_selection_create(NULL,join,&evidence,&budget,digest,NULL,never,&selection,&report)==COH_OK);CHECK(report.profile_association_verified&&report.covered_model_rows==8250&&report.root_model_references==3083&&!report.direct_open_observed&&!report.assets_admitted&&!report.world_authority);(void)evidencebytes;
 for(unsigned n=0;n<7;n++){free((void*)evidence.bytes[n].data);}
 coh_resource_join_free(join);

 const size_t MB=1024u*1024u,provider=256u*1024u;
 size_t source_base=coh_catalog_owner_owned_bytes(catalog)+coh_catalog_snapshot_owned_bytes(snapshot)+gr.owned_bytes+jr.owned_bytes+report.owned_bytes+provider;
 FILE*tf=fopen(argv[12],"rb");CHECK(tf&&!fseek(tf,0,SEEK_END));long tn=ftell(tf);CHECK(tn==13537052);rewind(tf);
 CohAssetLoader*tl=NULL;CohAssetLimits tlim={16u<<20,16u<<20,16u<<20,16u<<20,4,4,4};CHECK(coh_asset_create(&tlim,&tl)==COH_OK);CHECK(coh_asset_mount_file(tl,"data/bin/tricks.bin",(CohAssetSource){read_at,tf,(uint64_t)tn,17})==COH_OK);
 CohWrTexOptCache*tx=NULL;CohWrTexOptLimits txb={1u<<20,96u<<20,16u<<20,source_base};CHECK(coh_wr_texopt_cache_open(tl,(CohAssetId){"data/bin/tricks.bin",17},digest,NULL,&txb,never,&tx)==COH_OK);CohWrTexOptCacheReport tr;CHECK(coh_wr_texopt_cache_report(tx,&tr)==COH_OK);
 CohAssetStats before=coh_asset_stats(tl);CohWrTrickCache*tk=NULL;CohWrTrickLimits tkb={1u<<20,96u<<20,16u<<20,source_base+tr.owned_bytes+16*MB+16384};CHECK(coh_wr_trick_open(tl,tx,digest,NULL,&tkb,never,&tk)==COH_OK);CohWrTrickReport kr;CHECK(coh_wr_trick_report(tk,&kr)==COH_OK);CohAssetStats after=coh_asset_stats(tl);CHECK(before.allocated_bytes==after.allocated_bytes&&before.reads==after.reads&&after.peak_allocated_bytes<=16*MB);CHECK(tr.count==14715&&kr.count==3644&&kr.stanim_children==106&&kr.autolod_children==273);
 size_t external=16*MB+tr.owned_bytes+kr.owned_bytes+65536+provider;
 CohResourceGeoPin pin;uint32_t fi;CHECK(coh_source_selection_pin(selection,26509,&fi,&pin)==COH_OK&&fi==344);char path[8192];CHECK(snprintf(path,sizeof(path),"%s/%s",argv[11],pin.id.path)>0);FILE*f=fopen(path,"rb");CHECK(f&&!fseek(f,0,SEEK_END));long nb=ftell(f);CHECK(nb>0);rewind(f);CohAssetLoader*l=NULL;CohAssetLimits lim={32u<<20,16u<<20,16u<<20,16u<<20,16,4,4};CHECK(coh_asset_create(&lim,&l)==COH_OK);CHECK(coh_asset_mount_file(l,pin.id.path,(CohAssetSource){read_at,f,(uint64_t)nb,pin.id.generation})==COH_OK);
 CohSourceBody*b=NULL;CohSourceBodyReport br;CohSourceBodyBudget bb={32u<<20,96u<<20,external,32u<<20};CHECK(coh_source_body_create(NULL,selection,fi,l,&bb,digest,NULL,never,&b,&br)==COH_OK);CohSourceBody*original=b;
 CohSourceMesh*m=NULL;CohSourceMeshReport mr,unchanged;memset(&mr,0x5a,sizeof(mr));unchanged=mr;CohSourceMeshRequest q={26509,digest,NULL};CohSourceMeshBudget mb={96u<<20,external,2u<<20};
 CHECK(coh_source_mesh_v8_create(&b,&q,&mb,(CohCancel){stop,NULL},&m,&mr)==COH_CANCELLED&&b==original&&!m&&!memcmp(&mr,&unchanged,sizeof(mr)));
 q.digest=wrong;CHECK(coh_source_mesh_v8_create(&b,&q,&mb,never,&m,&mr)==COH_STATE&&b==original&&!m&&!memcmp(&mr,&unchanged,sizeof(mr)));q.digest=digest;
 CHECK(coh_source_mesh_v8_create(&b,&q,&mb,never,(CohSourceMesh**)&mr,&mr)==COH_INVALID&&b==original&&!m);
 for(unsigned k=3;k<=6;k++){Poll poll={0,k};CHECK(coh_source_mesh_v8_create(&b,&q,&mb,(CohCancel){stop_late,&poll},&m,&mr)==COH_CANCELLED&&poll.calls==k&&b==original&&!m&&!memcmp(&mr,&unchanged,sizeof(mr)));}
 for(unsigned k=1;k<=3;k++){fail_at=k;alloc_count=0;CHECK(coh_source_mesh_v8_create(&b,&q,&mb,never,&m,&mr)==COH_LIMIT&&b==original&&!m&&!memcmp(&mr,&unchanged,sizeof(mr)));fail_at=0;CHECK(!live[0]&&!live[1]&&!live[2]);}
 CHECK(coh_source_mesh_v8_create(&b,&q,&mb,never,&m,&mr)==COH_OK&&!b&&m);CHECK(mr.vertices==32056&&mr.triangles==19193&&mr.parts==12&&mr.unscaled_base_uv&&mr.material_binding_required&&!mr.render_ready&&!mr.client_materials_available&&!mr.world_authority);
 CohSourceBody*empty=NULL;CHECK(coh_source_mesh_v8_create(&empty,&q,&mb,never,&m,&unchanged)==COH_INVALID);
 SHA256_CTX sha;CHECK(SHA256_Init(&sha));const CohRenderVertex*shared=NULL;const uint32_t*next=NULL;size_t packet=0;for(uint32_t n=0;n<mr.parts;n++){CohSourceMeshPart part;CHECK(coh_source_mesh_part(m,n,&part)==COH_OK);if(!shared)shared=part.vertices;CHECK(part.vertices==shared&&part.vertex_count==32056);if(next)CHECK(next==part.indices);next=part.indices+part.index_count;size_t vb=part.vertex_count*sizeof(*part.vertices),ib=part.index_count*sizeof(*part.indices);CHECK(SHA256_Update(&sha,part.vertices,vb)&&SHA256_Update(&sha,part.indices,ib));packet+=vb+ib;}uint8_t h[32],expected[32];CHECK(SHA256_Final(h,&sha));hex("e026c08ea55313eab0ac01276cc9a0231fdfe07d111817393b9ce1e4e477cc3d",expected);CHECK(!memcmp(h,expected,32)&&packet==21771948);
 CohSourceMeshPart pv,saved;memset(&pv,0x33,sizeof(pv));saved=pv;CHECK(coh_source_mesh_part(m,12,&pv)==COH_NOT_FOUND&&!memcmp(&pv,&saved,sizeof(pv)));CHECK(coh_source_mesh_part(m,0,(CohSourceMeshPart*)shared)==COH_INVALID);CHECK(coh_source_mesh_report(m,(CohSourceMeshReport*)shared)==COH_INVALID);
 size_t mesh_owned=mr.owned_bytes,mesh_temporary=mr.temporary_bytes,source_retained=mr.source.retained_owner_bytes;size_t headroom=96*MB-mr.aggregate_reserved_bytes;CHECK(mr.aggregate_reserved_bytes<=96*MB&&mr.preparation_reserve==16384);coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);coh_source_mesh_free(m);m=NULL;coh_asset_trim(l);CHECK(!coh_asset_stats(l).pinned_blobs);
 /* Exact-minus-one refusal is checked on a fresh retained Body, before factory allocations. */
 CHECK(coh_source_body_create(NULL,selection,fi,l,&bb,digest,NULL,never,&b,&br)==COH_OK);original=b;mb.aggregate_limit=mr.aggregate_reserved_bytes-1;memset(&unchanged,0x11,sizeof(unchanged));mr=unchanged;CHECK(coh_source_mesh_v8_create(&b,&q,&mb,never,&m,&mr)==COH_LIMIT&&b==original&&!m&&!memcmp(&mr,&unchanged,sizeof(mr)));mb.aggregate_limit=96*MB;mb.retained_bytes+=headroom+1;CHECK(coh_source_mesh_v8_create(&b,&q,&mb,never,&m,&mr)==COH_LIMIT&&b==original&&!m);mb.retained_bytes=external+headroom;CHECK(coh_source_mesh_v8_create(&b,&q,&mb,never,&m,&mr)==COH_OK&&!b&&mr.aggregate_reserved_bytes==96*MB);coh_source_mesh_free(m);m=NULL;
 CohAssetStats geo=coh_asset_stats(l);coh_asset_trim(l);CHECK(!coh_asset_stats(l).pinned_blobs&&coh_asset_destroy(&l)==COH_OK&&!fclose(f));coh_wr_trick_release(&tk);coh_wr_texopt_cache_release(&tx);coh_asset_trim(tl);CHECK(!coh_asset_stats(tl).pinned_blobs&&coh_asset_destroy(&tl)==COH_OK&&!fclose(tf));
 printf("{\"passed\":true,\"checks\":%u,\"source_base\":%zu,\"dictionary_metadata\":%zu,\"dictionary_loader_reservation\":%zu,\"dictionary_actual_loader_peak\":%zu,\"dictionary_admission_peak\":%zu,\"source_body_phase_peak\":%zu,\"mesh_owned\":%zu,\"mesh_temporary\":%zu,\"source_retained_owners\":%zu,\"mesh_peak\":%zu,\"external_headroom\":%zu,\"geo_loader_actual_peak\":%zu,\"packet_bytes\":%zu,\"authoritative_actor_available\":false,\"material_binding_available\":false,\"world_authority\":false}\n",checks,source_base,tr.owned_bytes+kr.owned_bytes,16*MB,after.peak_allocated_bytes,kr.aggregate_reserved_bytes,br.aggregate_reserved_bytes,mesh_owned,mesh_temporary,source_retained,96*MB-headroom,headroom,geo.peak_allocated_bytes,packet);
 coh_source_selection_free(selection);coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);return 0;}
