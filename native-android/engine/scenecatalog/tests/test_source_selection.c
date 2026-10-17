#include "coh_source_selection.h"
#ifdef COH_SOURCE_RIGID_BRIDGE_TEST
#include "coh_source_rigid.h"
#endif
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,bridge_completions;static size_t calls,fail_at,live;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"selection line%d check%u: %s\n",__LINE__,checks,#x);abort();}}while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){calls++;if(calls==fail_at)return NULL;void *p=__real_malloc(n);if(p)live++;return p;}
void *__wrap_calloc(size_t n,size_t z){calls++;if(calls==fail_at)return NULL;void *p=__real_calloc(n,z);if(p)live++;return p;}
void __wrap_free(void*p){if(p){CHECK(live);live--;}__real_free(p);}
static CohStatus digest(void*ctx,CohBytes b,uint8_t out[32]){(void)ctx;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
static void hex(const char*s,uint8_t out[32]){for(unsigned n=0;n<32;n++){unsigned v;CHECK(sscanf(s+2*n,"%2x",&v)==1);out[n]=(uint8_t)v;}}
static CohBytes file(const char*path,size_t max){FILE*f=fopen(path,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&(size_t)n<=max);rewind(f);uint8_t*p=malloc((size_t)n);CHECK(p);CHECK(fread(p,1,(size_t)n,f)==(size_t)n);CHECK(!fclose(f));return(CohBytes){p,(size_t)n};}
static unsigned polls,stop;static int cancelled(void*ctx){(void)ctx;return ++polls==stop;}
static CohStatus broken(void*ctx,CohBytes b,uint8_t out[32]){(void)ctx;(void)b;(void)out;return COH_IO;}
static void refuses(CohSourceSelection *old,CohResourceJoin*j,CohSourceSelectionEvidence*e,CohSourceSelectionBudget*b,CohResourceDigest d,CohCancel c){CohSourceSelection*out=NULL;CohSourceSelectionReport report,before;memset(&report,0xa5,sizeof(report));before=report;size_t initial=live;CHECK(coh_source_selection_create(old,j,e,b,d,NULL,c,&out,&report)!=COH_OK);CHECK(!out&&!memcmp(&report,&before,sizeof(report))&&live==initial);}
static void body_refuses(CohSourceBody*old,CohSourceSelection*s,uint32_t k,CohAssetLoader*l,CohSourceBodyBudget*b,CohResourceDigest d,CohCancel c){CohSourceBody*out=NULL;CohSourceBodyReport report,before;memset(&report,0xa5,sizeof(report));before=report;size_t initial=live;CHECK(coh_source_body_create(old,s,k,l,b,d,NULL,c,&out,&report)!=COH_OK);CHECK(!out&&!memcmp(&report,&before,sizeof(report))&&live==initial);}
static CohStatus read_at(void*ctx,uint64_t off,void*dst,size_t n){FILE*f=ctx;if(off>0x7fffffffu||fseek(f,(long)off,SEEK_SET)||fread(dst,1,n,f)!=n)return COH_IO;return COH_OK;}
static CohStatus read_bad(void*ctx,uint64_t off,void*dst,size_t n){CohStatus st=read_at(ctx,off,dst,n);if(st==COH_OK&&!off&&n)((uint8_t*)dst)[0]^=1;return st;}
#ifdef COH_SOURCE_RIGID_BRIDGE_TEST
#include "test_source_rigid.inc"
#endif
int main(int argc,char**argv){CHECK(argc==12);CohCancel never={NULL,NULL};CohCatalogDigest dig={NULL,digest};CohBytes input=file(argv[1],32u<<20),side=file(argv[2],1u<<20),resources=file(argv[3],32u<<20);CohSourceSelectionEvidence evidence;
 for(unsigned n=0;n<7;n++)evidence.bytes[n]=file(argv[4+n],8u<<20);
 CohCatalogBinding cb={0};cb.owner_generation=1;cb.catalog_generation=cb.asset_generation=20261016;hex("61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763",cb.catalog_sha256);hex("9b74823a341fe565a978f81516b3b13ea8741ec8ecc57bb2b8bfb40130943eaa",cb.source_sha256);hex("f2bd6c0bac0ea8dafbf76cdff40b33089c48318a968d3db6fbb20899e172f99f",cb.inventory_sha256);
 CohCatalogOwner*catalog=NULL;CohCatalogOwnerReport cr;CohCatalogOwnerBudget cbudget={32u<<20,32u<<20,96u<<20,262144};CHECK(coh_catalog_owner_create(NULL,input,&cb,&cbudget,&dig,&catalog,&cr)==COH_OK);free((void*)input.data);
 CohCatalogSnapshotBinding sb={0};sb.generation=1;sb.catalog=cb;hex("c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02",sb.snapshot_sha256);hex("e6a25d7e6429fbb856fad617c5f8eeab75325c0fb7c0083be7f91348e5765ced",sb.run_sha256);CohCatalogSnapshot*snapshot=NULL;CohRuntimeSnapshotBudget sbudget={96u<<20,262144};CHECK(coh_catalog_snapshot_create(NULL,catalog,side,&sb,&sbudget,&dig,NULL,&snapshot)==COH_OK);free((void*)side.data);
 CohBytes cat,snap;CohRuntimeSnapshotReport sr;CHECK(coh_catalog_owner_bytes(catalog,&cat)==COH_OK);CHECK(coh_catalog_snapshot_view(snapshot,&snap,&sb,&sr)==COH_OK);CohRuntimeGraphBinding gb={0};gb.generation=1;gb.catalog_generation=20261016;gb.pins.asset_generation=20261016;gb.pins.digest=digest;memcpy(gb.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(gb.pins.snapshot_sha256,sb.snapshot_sha256,32);memcpy(gb.pins.source_sha256,cb.source_sha256,32);memcpy(gb.pins.run_sha256,sb.run_sha256,32);
 CohRuntimeGraph*graph=NULL;CohRuntimeGraphReport gr;CohRuntimeSnapshotBudget gbudget={96u<<20,coh_catalog_owner_owned_bytes(catalog)-cat.size+coh_catalog_snapshot_owned_bytes(snapshot)-snap.size+262144};CHECK(coh_runtime_graph_build(NULL,cat,snap,&gb,&gbudget,NULL,&graph,&gr)==COH_OK);
 CohResourceJoinPins jp={0};jp.resource.generation=1;jp.resource.asset_generation=20261016;memcpy(jp.resource.source_sha256,cb.source_sha256,32);memcpy(jp.resource.run_sha256,sb.run_sha256,32);hex("7c42a9612e4e08ee6463c3a8f87d2cf0749ff2baa8183d6b3c58281ec004c39c",jp.resource.manifest_sha256);hex("8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6",jp.resources_sha256);CohResourceJoin*join=NULL;CohResourceJoinReport jr;CohResourceJoinBudget jbudget={32u<<20,96u<<20,262144};CHECK(coh_resource_join_build(NULL,catalog,snapshot,graph,resources,&jp,&jbudget,digest,NULL,never,&join,&jr)==COH_OK);free((void*)resources.data);
 CohResourceJoinIdentity identity;CHECK(coh_resource_join_identity(join,&identity)==COH_OK);CHECK(!memcmp(&identity.pins,&jp,sizeof(jp))&&identity.resource_bytes.size==12596422);CHECK(coh_resource_join_identity(join,(CohResourceJoinIdentity*)identity.resource_bytes.data)==COH_INVALID);CHECK(coh_resource_join_retain(join)==COH_OK);coh_resource_join_free(join);
 /* White-box overflow control touches only the first private refs member. */
 uint32_t saved,maximum=UINT32_MAX;memcpy(&saved,join,4);memcpy(join,&maximum,4);CHECK(coh_resource_join_retain(join)==COH_LIMIT);memcpy(join,&saved,4);
 size_t evidencebytes=0;for(unsigned n=0;n<7;n++)evidencebytes+=evidence.bytes[n].size;
 CohSourceSelectionBudget budget={2u<<20,96u<<20,262144};CohSourceSelection*selection=NULL;CohSourceSelectionReport report;CHECK(coh_source_selection_create(NULL,join,&evidence,&budget,digest,NULL,never,&selection,&report)==COH_OK);CHECK(report.profile_association_verified&&report.covered_model_rows==8250&&report.root_model_references==3083&&!report.direct_open_observed&&!report.assets_admitted&&!report.world_authority);size_t selectionpeak=report.aggregate_reserved_bytes;
 /* Independently valid equal-byte owners remain distinct budget identities. */
 CohCatalogOwner *shadowcat=NULL;CohCatalogSnapshot *shadowsnap=NULL;CohRuntimeGraph *shadowgraph=NULL;CohResourceJoin *shadowjoin=NULL;CohSourceSelection *shadowselection=NULL;
 size_t base_retained=identity.report.owned_bytes+identity.catalog_owned_bytes+identity.snapshot_owned_bytes+identity.graph_owned_bytes+report.owned_bytes+evidencebytes+262144;
 CohCatalogOwnerBudget shob=cbudget;shob.retained_bytes=base_retained;CHECK(coh_catalog_owner_create(NULL,cat,&cb,&shob,&dig,&shadowcat,&cr)==COH_OK);
 CohRuntimeSnapshotBudget shsb={96u<<20,base_retained};CHECK(coh_catalog_snapshot_create(NULL,shadowcat,snap,&sb,&shsb,&dig,NULL,&shadowsnap)==COH_OK);CohBytes shcat,shside;CHECK(coh_catalog_owner_bytes(shadowcat,&shcat)==COH_OK);CHECK(coh_catalog_snapshot_view(shadowsnap,&shside,&sb,&sr)==COH_OK);
 CohRuntimeSnapshotBudget shgb={96u<<20,base_retained+coh_catalog_owner_owned_bytes(shadowcat)-shcat.size+coh_catalog_snapshot_owned_bytes(shadowsnap)-shside.size};CohRuntimeGraphReport shgr;CHECK(coh_runtime_graph_build(NULL,shcat,shside,&gb,&shgb,NULL,&shadowgraph,&shgr)==COH_OK);
 CohResourceJoinBudget shjb={32u<<20,96u<<20,base_retained};CHECK(coh_resource_join_build(NULL,shadowcat,shadowsnap,shadowgraph,identity.resource_bytes,&jp,&shjb,digest,NULL,never,&shadowjoin,&jr)==COH_OK);
 CohSourceSelectionReport shadowreport;CHECK(coh_source_selection_create(selection,shadowjoin,&evidence,&budget,digest,NULL,never,&shadowselection,&shadowreport)==COH_OK);CHECK(shadowreport.aggregate_reserved_bytes>report.aggregate_reserved_bytes+30000000u);
 CohSourceSelectionBudget shadowtight=budget;shadowtight.aggregate_limit=shadowreport.aggregate_reserved_bytes-1;refuses(selection,shadowjoin,&evidence,&shadowtight,digest,never);
 coh_source_selection_free(shadowselection);coh_resource_join_free(shadowjoin);coh_runtime_graph_free(shadowgraph);coh_catalog_snapshot_release(shadowsnap);coh_catalog_owner_release(shadowcat);
 for(unsigned n=0;n<7;n++){uint8_t*p=(uint8_t*)evidence.bytes[n].data;p[0]^=1;refuses(selection,join,&evidence,&budget,digest,never);p[0]^=1;}
 refuses(selection,join,&evidence,&budget,broken,never);
 memcpy(&saved,join,4);memcpy(join,&maximum,4);refuses(selection,join,&evidence,&budget,digest,never);memcpy(join,&saved,4);
 for(unsigned n=1;n<=2;n++){fail_at=calls+n;refuses(selection,join,&evidence,&budget,digest,never);fail_at=0;}
 for(unsigned n=0;n<3;n++){unsigned stops[]={1,100,42000};polls=0;stop=stops[n];refuses(selection,join,&evidence,&budget,digest,(CohCancel){cancelled,NULL});}
 CohSourceSelectionBudget tight=budget;tight.aggregate_limit=selectionpeak-1;refuses(NULL,join,&evidence,&tight,digest,never);CohSourceSelection*next=NULL;tight.aggregate_limit++;CHECK(coh_source_selection_create(NULL,join,&evidence,&tight,digest,NULL,never,&next,&report)==COH_OK);coh_source_selection_free(next);
 CHECK(coh_source_selection_create(NULL,join,&evidence,&budget,digest,NULL,never,(CohSourceSelection**)&report,&report)==COH_INVALID);
 CHECK(coh_source_selection_create(NULL,join,&evidence,&budget,digest,NULL,never,(CohSourceSelection**)identity.resource_bytes.data,&report)==COH_INVALID);
 const CohResourceSource *sources;size_t count;CohResourceBinding rb;CHECK(coh_resource_join_sources(join,&sources,&count,&rb)==COH_OK);
 uint32_t neon=UINT32_MAX,shop=UINT32_MAX,covered=0;CohResourceGeoPin np={0},sp={0};
 for(uint32_t n=0;n<count;n++){uint32_t k;CohResourceGeoPin pin;CohStatus st=coh_source_selection_pin(selection,n,&k,&pin);if(st==COH_NOT_FOUND)continue;CHECK(st==COH_OK);covered++;if(!strcmp(pin.source_geo_name,"object_library/Buildings/Elements/signs/Neon/neon.geo")){neon=k;np=pin;}if(!strcmp(pin.source_geo_name,"object_library/Special_Buildings/Shop_interiors/Shop_tailor/shop_tailor.geo")){shop=k;sp=pin;}}
 CHECK(covered==8250&&neon!=UINT32_MAX&&shop!=UINT32_MAX);uint32_t sentinel=123;CohResourceGeoPin untouched,before;memset(&untouched,0xa5,sizeof(untouched));before=untouched;CHECK(coh_source_selection_pin(selection,UINT32_MAX,&sentinel,&untouched)==COH_NOT_FOUND);CHECK(sentinel==123&&!memcmp(&untouched,&before,sizeof(before)));
 for(unsigned n=0;n<7;n++)free((void*)evidence.bytes[n].data);
 CHECK(coh_source_selection_retain(selection)==COH_OK);coh_source_selection_free(selection);coh_resource_join_free(join);join=NULL; /* selection retains the actualjoin */
 CohAssetLoader*loader=NULL;CohAssetLimits limits={32u<<20,16u<<20,16u<<20,16u<<20,16,4,4};CHECK(coh_asset_create(&limits,&loader)==COH_OK);char path[8192];snprintf(path,sizeof(path),"%s/%s",argv[11],np.id.path);FILE*nf=fopen(path,"rb");CHECK(nf);CHECK(!fseek(nf,0,SEEK_END));long nb=ftell(nf);rewind(nf);CHECK(coh_asset_mount_file(loader,np.id.path,(CohAssetSource){read_at,nf,(uint64_t)nb,20261016})==COH_OK);
 snprintf(path,sizeof(path),"%s/%s",argv[11],sp.id.path);FILE*sf=fopen(path,"rb");CHECK(sf);CHECK(!fseek(sf,0,SEEK_END));long ns=ftell(sf);rewind(sf);CHECK(coh_asset_mount_file(loader,sp.id.path,(CohAssetSource){read_at,sf,(uint64_t)ns,20261016})==COH_OK);
 CohSourceBodyBudget bb={32u<<20,96u<<20,262144,32u<<20};CohSourceBody*body=NULL;CohSourceBodyReport br;CHECK(coh_source_body_create(NULL,selection,neon,loader,&bb,digest,NULL,never,&body,&br)==COH_OK);CHECK(br.derived_origin_verified&&br.evidence_kind==COH_SOURCE_PROCEDURAL_EXACT_COLD_CAPTURE&&!br.direct_open_observed&&!br.assets_admitted&&!br.world_authority);size_t bodypeak=br.aggregate_reserved_bytes;
 CohSourceBodyBudget too_small=bb;too_small.aggregate_limit=40u<<20;size_t noalloc=calls;body_refuses(body,selection,neon,loader,&too_small,digest,never);CHECK(calls==noalloc);
 for(unsigned bad=0;bad<2;bad++){
  size_t startlive=live;CohAssetLoader*badloader=NULL;CohAssetLimits badlimits={4u<<20,2u<<20,2u<<20,2u<<20,4,2,2};CHECK(coh_asset_create(&badlimits,&badloader)==COH_OK);CHECK(coh_asset_mount_file(badloader,np.id.path,(CohAssetSource){bad?read_at:read_bad,nf,(uint64_t)nb,20261016+bad})==COH_OK);
  CohSourceBodyBudget badbudget=bb;badbudget.loader_reservation=4u<<20;CohSourceBody*badout=NULL;CohSourceBodyReport badreport,prior;memset(&badreport,0xa5,sizeof(badreport));prior=badreport;
  CHECK(coh_source_body_create(body,selection,neon,badloader,&badbudget,digest,NULL,never,&badout,&badreport)!=COH_OK);CHECK(!badout&&!memcmp(&badreport,&prior,sizeof(prior)));coh_asset_trim(badloader);CHECK(coh_asset_destroy(&badloader)==COH_OK);CHECK(live==startlive);
 }
 size_t initialcalls=calls;CohSourceBody*replacement=NULL;CHECK(coh_source_body_create(body,selection,neon,loader,&bb,digest,NULL,never,&replacement,&br)==COH_OK);size_t allocs=calls-initialcalls;coh_source_body_free(replacement);
 for(size_t n=1;n<=allocs;n++){fail_at=calls+n;body_refuses(body,selection,neon,loader,&bb,digest,never);fail_at=0;}
 memcpy(&saved,selection,4);memcpy(selection,&maximum,4);body_refuses(body,selection,neon,loader,&bb,digest,never);memcpy(selection,&saved,4);
 body_refuses(body,selection,neon,loader,&bb,broken,never);body_refuses(body,selection,COH_SOURCE_SELECTION_FILES,loader,&bb,digest,never);
 for(unsigned n=0;n<3;n++){unsigned stops[]={1,42000,80470};polls=0;stop=stops[n];body_refuses(body,selection,neon,loader,&bb,digest,(CohCancel){cancelled,NULL});}
 CohSourceBody*shopbody=NULL;CHECK(coh_source_body_create(body,selection,shop,loader,&bb,digest,NULL,never,&shopbody,&br)==COH_OK);const CohResourceIndex*index;CHECK(coh_source_body_view(shopbody,&index,&br)==COH_OK);CohResourceBinding binding;CohResourceReport ir;CHECK(coh_resource_index_metadata(index,&binding,&ir)==COH_OK);uint32_t zero=0;for(uint32_t n=0;n<ir.rows;n++){CohBytes raw;CohResourceView v;CHECK(coh_resource_index_record(index,n,&raw,&v)==COH_OK);zero+=v.zero_draw_model;}CHECK(zero==4);
#ifdef COH_SOURCE_RIGID_BRIDGE_TEST
 bridge_checks(selection,body,shopbody,neon,shop,loader,bb);
#endif
 coh_source_selection_free(selection);selection=NULL; /* both FILE owners retain it */
 CHECK(coh_source_body_view(body,&index,&br)==COH_OK&&br.derived_origin_verified);coh_source_body_free(shopbody);coh_source_body_free(body);coh_asset_trim(loader);CHECK(coh_asset_destroy(&loader)==COH_OK);CHECK(!fclose(nf)&&!fclose(sf));
 coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);CHECK(!live);
 printf("{\"bridge_completions\":%u,\"passed\":true,\"checks\":%u,\"profile_files\":391,\"covered_model_rows\":8250,\"source_root_references\":3083,\"body_alloc_failure_cases\":%zu,\"selection_peak_bytes\":%zu,\"body_peak_bytes\":%zu,\"input_evidence_bytes\":%zu,\"procedural_file_bodies_checked\":2,\"shop_zero_model_owners\":4,\"direct_open_observed\":false,\"assets_admitted\":false,\"world_authority\":false}\n",bridge_completions,checks,allocs,selectionpeak,bodypeak,evidencebytes);return 0;
}
