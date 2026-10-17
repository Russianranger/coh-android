#define _POSIX_C_SOURCE 200809L
#define OPENSSL_SUPPRESS_DEPRECATED
#include "coh_source_mesh_batch.h"
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

 /* Second real mesh uses a distinct Body/index and the same actual loader/blob. */
 CohSourceBodyDependencies bd;CHECK(coh_source_body_dependencies((const CohSourceBody*)original,&bd)==COH_OK); /* original now retained inside m */
 CHECK(bd.loader==l&&bd.join_identity&&bd.selection_identity&&bd.body_owned_bytes==br.owned_bytes);
 CohSourceMeshDependencies md;CHECK(coh_source_mesh_dependencies(m,&md)==COH_OK&&md.body.body_identity==original&&md.body.index_identity==bd.index_identity&&md.mesh_storage.size==mr.owned_bytes);
 CHECK(coh_source_mesh_dependencies(m,(CohSourceMeshDependencies*)md.mesh_storage.data)==COH_INVALID);
 CHECK(coh_source_mesh_dependencies(m,(CohSourceMeshDependencies*)mr.source.actual_sources.blob.data)==COH_INVALID);
 CHECK(coh_source_body_dependencies((const CohSourceBody*)original,(CohSourceBodyDependencies*)bd.join.resource_bytes.data)==COH_INVALID);
 CHECK(coh_source_body_dependencies((const CohSourceBody*)original,(CohSourceBodyDependencies*)(uintptr_t)(UINTPTR_MAX-4))==COH_INVALID);
 bb.retained_bytes=external+mr.owned_bytes+bd.body_owned_bytes;CohSourceBody*b2=NULL;CohSourceBodyReport br2;CHECK(coh_source_body_create(NULL,selection,fi,l,&bb,digest,NULL,never,&b2,&br2)==COH_OK);
 CohSourceMesh*m2=NULL;CohSourceMeshReport mr2;CohSourceMeshRequest q2={26510,digest,NULL};CohSourceMeshBudget mb2={96u<<20,bb.retained_bytes,2u<<20};CHECK(coh_source_mesh_v8_create(&b2,&q2,&mb2,never,&m2,&mr2)==COH_OK&&!b2&&m2);CHECK(mr2.source.source_ordinal==26510&&mr2.source.loader==mr.source.loader);
 CohSourceMeshDependencies md2;CHECK(coh_source_mesh_dependencies(m2,&md2)==COH_OK&&md2.body.body_identity!=md.body.body_identity&&md2.body.index_identity!=md.body.index_identity&&md2.body.selection_identity==md.body.selection_identity&&md2.body.join_identity==md.body.join_identity);
 CohSourceMesh*slots[]={m,m2};CohSourceMeshBatch*batch=NULL;CohSourceMeshBatchBudget budget2={96u<<20,external};CohSourceMeshBatchReport batchreport,oldreport;memset(&batchreport,0x23,sizeof(batchreport));oldreport=batchreport;
 CHECK(coh_source_mesh_batch_create(slots,0,&budget2,never,&batch,&batchreport)==COH_LIMIT&&slots[0]==m&&slots[1]==m2&&!batch&&!memcmp(&batchreport,&oldreport,sizeof(oldreport)));
 slots[0]=m2;slots[1]=m;CHECK(coh_source_mesh_batch_create(slots,2,&budget2,never,&batch,&batchreport)==COH_STATE&&slots[0]==m2&&slots[1]==m&&!batch);slots[0]=m;slots[1]=m;CHECK(coh_source_mesh_batch_create(slots,2,&budget2,never,&batch,&batchreport)==COH_STATE&&slots[0]==m&&slots[1]==m&&!batch);slots[1]=m2;
 CHECK(coh_source_mesh_batch_create(slots,2,&budget2,(CohCancel){stop,NULL},&batch,&batchreport)==COH_CANCELLED&&slots[0]==m&&slots[1]==m2&&!batch);
 for(unsigned at=2;at<=4;at++){Poll poll={0,at};CHECK(coh_source_mesh_batch_create(slots,2,&budget2,(CohCancel){stop_late,&poll},&batch,&batchreport)==COH_CANCELLED&&poll.calls==at&&slots[0]==m&&slots[1]==m2&&!batch&&!memcmp(&batchreport,&oldreport,sizeof(oldreport)));}
 fail_at=1;alloc_count=0;CHECK(coh_source_mesh_batch_create(slots,2,&budget2,never,&batch,&batchreport)==COH_LIMIT&&slots[0]==m&&slots[1]==m2&&!batch&&!memcmp(&batchreport,&oldreport,sizeof(oldreport)));fail_at=0;CHECK(!live[0]&&!live[1]&&!live[2]);
 CHECK(coh_source_mesh_batch_create(slots,2,&budget2,never,&batch,(CohSourceMeshBatchReport*)mr.source.actual_sources.blob.data)==COH_INVALID&&slots[0]==m&&slots[1]==m2&&!batch);
 CHECK(coh_source_mesh_batch_create(slots,2,&budget2,never,(CohSourceMeshBatch**)&batchreport,&batchreport)==COH_INVALID&&slots[0]==m&&slots[1]==m2&&!batch);

 /* Independent source selection with equal fixed hashes must still refuse the
  * cross-object batch: labels are not actual retained-owner identity. */
 for(unsigned n=0;n<7;n++)evidence.bytes[n]=file(argv[4+n],8u<<20);
 CohSourceSelection*selection2=NULL;CohSourceSelectionReport report2;CohSourceSelectionBudget sb2={2u<<20,96u<<20,external+32*MB+mr.owned_bytes+mr2.owned_bytes+bd.body_owned_bytes+md2.body.body_owned_bytes};
 CHECK(coh_source_selection_create(selection,(CohResourceJoin*)bd.join_identity,&evidence,&sb2,digest,NULL,never,&selection2,&report2)==COH_OK);
 for(unsigned n=0;n<7;n++)free((void*)evidence.bytes[n].data);
 CohSourceBody*b3=NULL;CohSourceBodyReport br3;CohSourceBodyBudget bb3={32u<<20,96u<<20,external+mr.owned_bytes+mr2.owned_bytes+bd.body_owned_bytes+md2.body.body_owned_bytes+bd.selection_owned_bytes,32u<<20};CHECK(coh_source_body_create(NULL,selection2,fi,l,&bb3,digest,NULL,never,&b3,&br3)==COH_OK);
 CohSourceMesh*m3=NULL;CohSourceMeshReport mr3;CohSourceMeshBudget mb3={96u<<20,bb3.retained_bytes,2u<<20};CHECK(coh_source_mesh_v8_create(&b3,&q2,&mb3,never,&m3,&mr3)==COH_OK&&!b3);slots[1]=m3;CHECK(coh_source_mesh_batch_create(slots,2,&budget2,never,&batch,&batchreport)==COH_STATE&&slots[0]==m&&slots[1]==m3&&!batch&&!memcmp(&batchreport,&oldreport,sizeof(oldreport)));slots[1]=m2;coh_source_mesh_free(m3);coh_source_selection_free(selection2);
 CohSourceMeshBatchBudget tight=budget2;tight.aggregate_limit=1;CHECK(coh_source_mesh_batch_create(slots,2,&tight,never,&batch,&batchreport)==COH_LIMIT&&slots[0]==m&&slots[1]==m2&&!batch&&!memcmp(&batchreport,&oldreport,sizeof(oldreport)));
 Poll overbudget={0,1};tight=budget2;tight.retained_bytes=96*MB;CHECK(coh_source_mesh_batch_create(slots,2,&tight,(CohCancel){stop_late,&overbudget},&batch,&batchreport)==COH_LIMIT&&!overbudget.calls&&slots[0]==m&&slots[1]==m2&&!batch);
 batch=(CohSourceMeshBatch*)(uintptr_t)1;CHECK(coh_source_mesh_batch_create(slots,2,&budget2,never,&batch,&batchreport)==COH_STATE&&batch==(CohSourceMeshBatch*)(uintptr_t)1&&slots[0]==m&&slots[1]==m2);batch=NULL;
 size_t source_shared=bd.selection_owned_bytes+bd.profile_bytes+bd.join.report.owned_bytes+bd.join.catalog_owned_bytes+bd.join.snapshot_owned_bytes+bd.join.graph_owned_bytes;
 CHECK(coh_source_mesh_batch_create(slots,2,&budget2,never,&batch,&batchreport)==COH_OK&&!slots[0]&&!slots[1]&&batch);
 CHECK(batchreport.source_owner_bytes==source_shared+bd.body_owned_bytes+md2.body.body_owned_bytes&&batchreport.mesh_owned_bytes==mr.owned_bytes+mr2.owned_bytes&&batchreport.loader_reservations==32*MB&&batchreport.meshes==2&&batchreport.parts==mr.parts+mr2.parts&&!batchreport.renderer_ready&&!batchreport.client_materials_available&&!batchreport.actor_available&&!batchreport.world_authority);
 CHECK(batchreport.aggregate_reserved_bytes==external+batchreport.owned_bytes+batchreport.mesh_owned_bytes+batchreport.source_owner_bytes+batchreport.loader_reservations+batchreport.preparation_reserve&&batchreport.aggregate_reserved_bytes<=96*MB);
 uint32_t slot=99;CHECK(coh_source_mesh_batch_find(batch,26509,&slot)==COH_OK&&slot==0);CHECK(coh_source_mesh_batch_find(batch,26510,&slot)==COH_OK&&slot==1);slot=99;CHECK(coh_source_mesh_batch_find(batch,0,&slot)==COH_NOT_FOUND&&slot==99);CHECK(coh_source_mesh_batch_find(batch,26509,(uint32_t*)md.mesh_storage.data)==COH_INVALID);
 uint32_t first;CohSourceMeshReport er;CHECK(coh_source_mesh_batch_entry(batch,0,&er,&first)==COH_OK&&!first&&er.source.source_ordinal==26509&&!memcmp(er.source.resource_record_sha256,mr.source.resource_record_sha256,32));CHECK(coh_source_mesh_batch_entry(batch,1,&er,&first)==COH_OK&&first==mr.parts&&er.source.source_ordinal==26510);CHECK(coh_source_mesh_batch_entry(batch,0,&er,(uint32_t*)&er)==COH_INVALID);
 SHA256_CTX sha;CHECK(SHA256_Init(&sha));size_t packet=0;for(uint32_t n=0;n<mr.parts;n++){CohSourceMeshPart part;CHECK(coh_source_mesh_batch_part(batch,0,n,&part)==COH_OK);size_t vb=part.vertex_count*sizeof(*part.vertices),ib=part.index_count*sizeof(*part.indices);CHECK(SHA256_Update(&sha,part.vertices,vb)&&SHA256_Update(&sha,part.indices,ib));packet+=vb+ib;}uint8_t h[32],expected[32];CHECK(SHA256_Final(h,&sha));hex("e026c08ea55313eab0ac01276cc9a0231fdfe07d111817393b9ce1e4e477cc3d",expected);CHECK(!memcmp(h,expected,32)&&packet==21771948);
 coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);coh_source_mesh_batch_free(batch);batch=NULL;coh_asset_trim(l);CHECK(!coh_asset_stats(l).pinned_blobs);CohAssetStats geo=coh_asset_stats(l);CHECK(coh_asset_destroy(&l)==COH_OK&&!fclose(f));coh_wr_trick_release(&tk);coh_wr_texopt_cache_release(&tx);coh_asset_trim(tl);CHECK(!coh_asset_stats(tl).pinned_blobs&&coh_asset_destroy(&tl)==COH_OK&&!fclose(tf));
 size_t negative_peak=report2.aggregate_reserved_bytes;if(br3.aggregate_reserved_bytes>negative_peak)negative_peak=br3.aggregate_reserved_bytes;if(mr3.aggregate_reserved_bytes>negative_peak)negative_peak=mr3.aggregate_reserved_bytes;CHECK(negative_peak<=96*MB);
 size_t preparation_peak=mr.aggregate_reserved_bytes;if(mr2.aggregate_reserved_bytes>preparation_peak)preparation_peak=mr2.aggregate_reserved_bytes;if(br2.aggregate_reserved_bytes>preparation_peak)preparation_peak=br2.aggregate_reserved_bytes;if(batchreport.aggregate_reserved_bytes>preparation_peak)preparation_peak=batchreport.aggregate_reserved_bytes;
 printf("{\"passed\":true,\"checks\":%u,\"meshes\":%u,\"parts\":%u,\"source_shared\":%zu,\"source_owner_bytes\":%zu,\"batch_owned\":%zu,\"mesh_owned\":%zu,\"loader_reservations\":%zu,\"mesh_peak\":%zu,\"batch_peak\":%zu,\"additional_negative_owner_peak\":%zu,\"external_headroom\":%zu,\"geo_loader_actual_peak\":%zu,\"packet_bytes\":%zu,\"actor_available\":false,\"material_binding_available\":false,\"world_authority\":false}\n",checks,batchreport.meshes,batchreport.parts,source_shared,batchreport.source_owner_bytes,batchreport.owned_bytes,batchreport.mesh_owned_bytes,batchreport.loader_reservations,preparation_peak,batchreport.aggregate_reserved_bytes,negative_peak,96*MB-preparation_peak,geo.peak_allocated_bytes,packet);
 coh_source_selection_free(selection);coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);return 0;}
