#define _POSIX_C_SOURCE 200809L
#define OPENSSL_SUPPRESS_DEPRECATED
#include "coh_source_ws_probe.h"
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
static unsigned retain_fail;CohStatus __real_coh_source_selection_retain(CohSourceSelection*);CohStatus __wrap_coh_source_selection_retain(CohSourceSelection*s){if(retain_fail){retain_fail=0;return COH_LIMIT;}return __real_coh_source_selection_retain(s);}
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

 CohSourceSealed*sealed=NULL;CohSourceSealedReport sr2,untouched;memset(&sr2,0x39,sizeof(sr2));untouched=sr2;CohSourceSealedBudget sealbudget={32u<<20,96u<<20,external};CohSourceMeshBatch*originalbatch=batch;
 CohSourceSealedBudget stight=sealbudget;stight.retained_bytes=96*MB;Poll nopoll={0,1};CHECK(coh_source_sealed_create(&batch,&stight,(CohCancel){stop_late,&nopoll},&sealed,&sr2)==COH_LIMIT&&!nopoll.calls&&batch==originalbatch&&!sealed&&!memcmp(&sr2,&untouched,sizeof(sr2)));
 CHECK(coh_source_sealed_create(&batch,&sealbudget,never,&sealed,(CohSourceSealedReport*)mr.source.actual_sources.blob.data)==COH_INVALID&&batch==originalbatch&&!sealed);
 CHECK(coh_source_sealed_create(&batch,&sealbudget,never,(CohSourceSealed**)&sr2,&sr2)==COH_INVALID&&batch==originalbatch&&!sealed);
 CHECK(coh_source_sealed_create(&batch,&sealbudget,never,&sealed,(CohSourceSealedReport*)batch)==COH_INVALID&&batch==originalbatch&&!sealed);
 CHECK(coh_source_sealed_create(&batch,&sealbudget,never,&sealed,(CohSourceSealedReport*)(uintptr_t)(UINTPTR_MAX-4))==COH_INVALID&&batch==originalbatch&&!sealed);
 stight=sealbudget;stight.owned_limit=1;CHECK(coh_source_sealed_create(&batch,&stight,never,&sealed,&sr2)==COH_LIMIT&&batch==originalbatch&&!sealed&&!memcmp(&sr2,&untouched,sizeof(sr2)));
 sealed=(CohSourceSealed*)(uintptr_t)1;CHECK(coh_source_sealed_create(&batch,&sealbudget,never,&sealed,&sr2)==COH_STATE&&batch==originalbatch&&sealed==(CohSourceSealed*)(uintptr_t)1);sealed=NULL;
 for(unsigned n=1;n<=25;n++){Poll poll={0,n};CHECK(coh_source_sealed_create(&batch,&sealbudget,(CohCancel){stop_late,&poll},&sealed,&sr2)==COH_CANCELLED&&poll.calls==n&&batch==originalbatch&&!sealed&&!memcmp(&sr2,&untouched,sizeof(sr2)));}
 fail_at=1;alloc_count=0;CHECK(coh_source_sealed_create(&batch,&sealbudget,never,&sealed,&sr2)==COH_LIMIT&&batch==originalbatch&&!sealed&&!memcmp(&sr2,&untouched,sizeof(sr2)));fail_at=0;CHECK(!live[0]&&!live[1]&&!live[2]);
 retain_fail=1;CHECK(coh_source_sealed_create(&batch,&sealbudget,never,&sealed,&sr2)==COH_LIMIT&&batch==originalbatch&&!sealed&&!memcmp(&sr2,&untouched,sizeof(sr2)));CHECK(!retain_fail);
 uint8_t rh[2][32],hh[2][32];for(unsigned n=0;n<2;n++){CohSourceMeshReport entry;uint32_t fp;CHECK(coh_source_mesh_batch_entry(batch,n,&entry,&fp)==COH_OK&&digest(NULL,entry.source.actual_sources.record,rh[n])==COH_OK&&digest(NULL,entry.source.actual_sources.header,hh[n])==COH_OK);}

 CohSourceSealedPlan measured,planold;memset(&measured,0x17,sizeof(measured));planold=measured;
 CHECK(coh_source_sealed_measure(batch,&sealbudget,(CohSourceSealedPlan*)batch)==COH_INVALID);
 CHECK(coh_source_sealed_measure(batch,&sealbudget,(CohSourceSealedPlan*)mr.source.actual_sources.header.data)==COH_INVALID);
 CHECK(coh_source_sealed_measure(batch,&sealbudget,(CohSourceSealedPlan*)(uintptr_t)(UINTPTR_MAX-4))==COH_INVALID);
 stight=sealbudget;stight.owned_limit=1;CHECK(coh_source_sealed_measure(batch,&stight,&measured)==COH_LIMIT&&!memcmp(&measured,&planold,sizeof(measured)));
 fail_at=1;alloc_count=0;CHECK(coh_source_sealed_measure(batch,&sealbudget,&measured)==COH_OK&&!alloc_count);fail_at=0;CHECK(measured.source.selection_identity==bd.selection_identity&&measured.source.join_identity==bd.join_identity&&measured.input.loader_reservations==32*MB);
 CohWorkingSet*parent=NULL;CHECK(coh_ws_create(96*MB,&parent)==COH_OK);CohWsReport parentbefore,parentafter;CHECK(coh_ws_report(parent,&parentbefore)==COH_OK);
 CohSourceWsProbe probe,probeold;memset(&probe,0x35,sizeof(probe));probeold=probe;
 CHECK(coh_source_ws_probe(parent,batch,&sealbudget,&probe)==COH_OK&&!probe.admission_permitted&&!probe.input_ticket_verified&&!probe.external_lifetimes_verified&&!probe.parent_mutated&&!probe.world_authority);
 CHECK(probe.parent_booked_added_to_retained==parentbefore.booked&&probe.source.prepared.retirement_peak_bytes==measured.prepared.retirement_peak_bytes+parentbefore.booked&&probe.candidate_copy_only.persistent_bytes==measured.prepared.owned_bytes&&probe.candidate_copy_only.call_reserve==measured.prepared.preparation_reserve);
 CHECK(coh_ws_report(parent,&parentafter)==COH_OK&&!memcmp(&parentbefore,&parentafter,sizeof(parentbefore)));
 CHECK(coh_source_ws_probe(parent,batch,&sealbudget,(CohSourceWsProbe*)mr.source.actual_sources.blob.data)==COH_INVALID);
 CHECK(coh_source_ws_probe(parent,batch,&sealbudget,(CohSourceWsProbe*)(uintptr_t)(UINTPTR_MAX-4))==COH_INVALID);
 CohWsTicket reserved={0};CohWsPlan reservation={8*MB,0,0,96*MB};CHECK(coh_ws_prepare(parent,&reservation,&reserved)==COH_OK);CHECK(coh_ws_report(parent,&parentbefore)==COH_OK);probe=probeold;CHECK(coh_source_ws_probe(parent,batch,&sealbudget,&probe)==COH_LIMIT&&!memcmp(&probe,&probeold,sizeof(probe)));CHECK(coh_ws_report(parent,&parentafter)==COH_OK&&!memcmp(&parentbefore,&parentafter,sizeof(parentbefore)));CHECK(coh_ws_abort(parent,&reserved)==COH_OK&&coh_ws_destroy(&parent)==COH_OK);
 CHECK(coh_source_sealed_create(&batch,&sealbudget,never,&sealed,&sr2)==COH_OK&&!batch&&sealed&&sr2.meshes==2&&sr2.parts==21&&!sr2.body_dependencies&&!sr2.index_dependencies&&!sr2.loader_dependencies&&!sr2.payload_streams_retained&&!sr2.renderer_ready&&!sr2.client_materials_available&&!sr2.actor_available&&!sr2.world_authority&&sr2.inherited_loader_reservations==32*MB);
 CHECK(sr2.owned_bytes==measured.prepared.owned_bytes&&sr2.retirement_peak_bytes==measured.prepared.retirement_peak_bytes);
 CHECK(sr2.shared_source_bytes==source_shared&&sr2.retirement_peak_bytes==external+batchreport.owned_bytes+batchreport.mesh_owned_bytes+batchreport.source_owner_bytes+batchreport.loader_reservations+sr2.owned_bytes+sr2.preparation_reserve&&sr2.retirement_peak_bytes<=96*MB);
 /* Explicitly prove provider/loader retirement; new views are used only AFTER
  * freeing every old pin/cache and closing the external FILE providers. */
 coh_asset_trim(l);CHECK(!coh_asset_stats(l).pinned_blobs&&!coh_asset_stats(l).resident_bytes);CohAssetStats geo=coh_asset_stats(l);CHECK(coh_asset_destroy(&l)==COH_OK&&!l&&!fclose(f));
 coh_source_selection_free(selection);selection=NULL;coh_wr_trick_release(&tk);coh_wr_texopt_cache_release(&tx);coh_asset_trim(tl);CHECK(!coh_asset_stats(tl).pinned_blobs&&coh_asset_destroy(&tl)==COH_OK&&!fclose(tf));
 CohSourceSealedIdentity sid;CHECK(coh_source_sealed_identity(sealed,&sid)==COH_OK&&sid.selection_identity==bd.selection_identity&&sid.join_identity==bd.join_identity&&sid.join.graph_identity==graph);uint32_t slot2=99;CHECK(coh_source_sealed_find(sealed,26509,&slot2)==COH_OK&&slot2==0);CHECK(coh_source_sealed_find(sealed,26510,&slot2)==COH_OK&&slot2==1);slot2=99;CHECK(coh_source_sealed_find(sealed,0,&slot2)==COH_NOT_FOUND&&slot2==99);
 for(unsigned n=0;n<2;n++){CohSourceSealedEntry entry;CHECK(coh_source_sealed_entry(sealed,n,&entry)==COH_OK&&entry.source_ordinal==26509+n&&entry.unscaled_base_uv&&entry.material_binding_required&&entry.binding.asset_generation==20261016);CHECK(digest(NULL,entry.resource_record,h)==COH_OK&&!memcmp(h,rh[n],32)&&digest(NULL,entry.original_header,h)==COH_OK&&!memcmp(h,hh[n],32));CHECK(!strcmp(entry.model.model_name,entry.model.model.name)&&entry.geo.id.generation==entry.binding.asset_generation&&!strcmp(entry.geo.source_geo_name,entry.model.geo_name));
  const char*names[]={entry.model.definition_name,entry.model.model_name,entry.model.geo_name,entry.model.trick_name,entry.model.trick_file,entry.model.library_name};for(unsigned k=0;k<6;k++)if(names[k])CHECK((uintptr_t)names[k]>=(uintptr_t)entry.resource_record.data&&(uintptr_t)names[k]-(uintptr_t)entry.resource_record.data<entry.resource_record.size);
  CHECK((uintptr_t)entry.model.model.name>=(uintptr_t)entry.original_header.data&&(uintptr_t)entry.model.model.name-(uintptr_t)entry.original_header.data<entry.original_header.size);
  SHA256_CTX copysha;CHECK(SHA256_Init(&copysha));for(uint32_t k=0;k<entry.parts;k++){CohSourceMeshPart part;CHECK(coh_source_sealed_part(sealed,n,k,&part)==COH_OK&&part.vertex_count==entry.vertices);CHECK((uintptr_t)part.source_material.texture_name>=(uintptr_t)entry.original_header.data&&(uintptr_t)part.source_material.texture_name-(uintptr_t)entry.original_header.data<entry.original_header.size);CHECK(strlen(part.source_material.texture_name)>0);CHECK(SHA256_Update(&copysha,part.vertices,(size_t)part.vertex_count*sizeof(*part.vertices))&&SHA256_Update(&copysha,part.indices,(size_t)part.index_count*sizeof(*part.indices)));}CHECK(SHA256_Final(h,&copysha));if(!n)CHECK(!memcmp(h,expected,32));else{uint8_t plaza[32];hex("b62a102362e46e0ef162c811ccb132cdbad6a6ca33087e7523ad06eba9240885",plaza);CHECK(!memcmp(h,plaza,32));}
  CHECK(coh_source_sealed_part(sealed,n,entry.parts,(CohSourceMeshPart*)&sr2)==COH_NOT_FOUND);CHECK(coh_source_sealed_entry(sealed,n,(CohSourceSealedEntry*)entry.resource_record.data)==COH_INVALID);CHECK(coh_source_sealed_report(sealed,(CohSourceSealedReport*)entry.original_header.data)==COH_INVALID);
 }
 size_t owner_live=sr2.owned_bytes+sr2.shared_source_bytes;
 printf("{\"passed\":true,\"checks\":%u,\"meshes\":%u,\"parts\":%u,\"sealed_owned\":%zu,\"shared_source\":%zu,\"retirement_peak\":%zu,\"owner_live_after_actual_geo_destroy\":%zu,\"dictionary_reservation_kept_for_conservative_comparison\":%zu,\"aggregate_with_prior_dictionary_allowance\":%zu,\"retired_geo_reservation\":%zu,\"geo_loader_actual_peak\":%zu,\"packet_bytes\":%zu,\"mesh_peak\":%zu,\"external_headroom\":%zu,\"source_loader_destroyed\":true,\"actor_available\":false,\"material_binding_available\":false,\"world_authority\":false}\n",checks,sr2.meshes,sr2.parts,sr2.owned_bytes,sr2.shared_source_bytes,sr2.retirement_peak_bytes,owner_live,external,owner_live+external,sr2.inherited_loader_reservations,geo.peak_allocated_bytes,packet,sr2.retirement_peak_bytes,96*MB-owner_live-external);
 coh_source_sealed_free(sealed);coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);return 0;}
