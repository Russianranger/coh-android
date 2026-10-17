/* Host diagnostic only: fixture materials; no CLIENT/world publication. */
#define _POSIX_C_SOURCE 200809L
#define OPENSSL_SUPPRESS_DEPRECATED
#include "coh_source_special.h"
#include "../world-render-adapter/coh_wr_rigid_source.h"
#include "../world-render-adapter/coh_wr_rigid_v5.h"
#include "../world-render-adapter/coh_wr_rigid_v7.h"
#include "../world-render-adapter/coh_wr_rigid_legacy_formats.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define ROOT_PAIRS 2916u
#define ROOT_OWNERS 3083u
#define DIAG_RESERVE (256u*1024u)
#define CPU_TIME_LIMIT_MS 180000u
#define PACKET_WORK_LIMIT (1024u*1024u*1024u)
#define CHECK(x) do{if(!(x)){fprintf(stderr,"sweep line%d: %s\n",__LINE__,#x);abort();}}while(0)
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void hex(const char*s,uint8_t out[32]){for(unsigned n=0;n<32;n++){unsigned v;CHECK(sscanf(s+n*2,"%2x",&v)==1);out[n]=(uint8_t)v;}}
static void hashtext(const uint8_t h[32]){for(unsigned k=0;k<32;k++)printf("%02x",h[k]);}
static void string(const char*s){putchar('"');for(;*s;s++){unsigned c=(unsigned char)*s;if(c=='"'||c=='\\')putchar('\\');CHECK(c>=32&&c<127);putchar((int)c);}putchar('"');}
static CohStatus digest(void*ctx,CohBytes b,uint8_t out[32]){(void)ctx;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
static CohBytes file(const char*path,size_t max){FILE*f=fopen(path,"rb");CHECK(f&&!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&(size_t)n<=max);rewind(f);uint8_t*p=malloc((size_t)n);CHECK(p&&fread(p,1,(size_t)n,f)==(size_t)n&&!fclose(f));return(CohBytes){p,(size_t)n};}
static CohStatus read_at(void*ctx,uint64_t off,void*dst,size_t n){FILE*f=ctx;if(off>0x7fffffffu||fseek(f,(long)off,SEEK_SET)||fread(dst,1,n,f)!=n)return COH_IO;return COH_OK;}
static uint64_t millis(void){struct timespec t;CHECK(!clock_gettime(CLOCK_MONOTONIC,&t));return(uint64_t)t.tv_sec*1000u+(uint64_t)t.tv_nsec/1000000u;}
typedef struct{uint64_t start;uint32_t stopped;} Deadline;
static int deadline(void*v){Deadline*d=v;if(millis()-d->start>CPU_TIME_LIMIT_MS)d->stopped=1;return(int)d->stopped;}
typedef struct{uint32_t ordinal,owner_count,file,index;const uint8_t*owners;} Pair;
static int order(const void*a,const void*b){const Pair*x=a,*y=b;if(x->file!=y->file)return x->file<y->file?-1:1;return x->index<y->index?-1:x->index!=y->index;}
typedef struct{CohSourceBody*body;CohSourceBodyLease lease;const CohResourceIndex*index;uint32_t acquired,released;} Materials;
static CohStatus material(void*ctx,CohAssetId id,const char*model,uint32_t part,const CohAssetGeoMaterial*source,CohWrRigidMaterial*out){
 Materials*m=ctx;CHECK(id.generation==m->lease.binding.asset_generation&&!strcmp(id.path,m->lease.geo.id.path)&&!strcmp(model,m->lease.model.model_name));CohAssetGeoMaterial actual;CHECK(coh_resource_index_material(m->index,m->lease.model.owner_kind,m->lease.model.file,m->lease.model.slot,part,&actual)==COH_OK);CHECK(actual.texture_id==source->texture_id&&actual.first_triangle==source->first_triangle&&actual.triangle_count==source->triangle_count&&!strcmp(actual.texture_name,source->texture_name));
 memset(out,0,sizeof(*out));out->material=coh_renderer_default_material(COH_MAT_DUAL);for(unsigned k=0;k<2;k++)for(unsigned n=0;n<2;n++)out->uv_scale[k][n]=1;out->texture_id[0]=11;out->texture_id[1]=12;out->geometry_id=100+part;out->generation=19;memset(out->source_sha256,1,32);out->pin=m;m->acquired++;return COH_OK;
}
static void release(void*ctx,void*pin){Materials*m=ctx;CHECK(pin==m);CohSourceBodyLease lease;CHECK(coh_source_body_lease(m->body,m->lease.source_ordinal,&lease)==COH_OK);m->released++;}
static CohStatus acquire(uint32_t version,CohAssetLoader*l,const CohWrRigidRequest*q,const CohWrRigidLimits*b,CohCancel cancel,CohWrRigidResource**out){switch(version){case 0:case 8:return coh_wr_rigid_source_acquire(l,q,b,cancel,out);case 2:return coh_wr_rigid_v2_acquire(l,q,b,cancel,out);case 3:return coh_wr_rigid_v3_acquire(l,q,b,cancel,out);case 4:return coh_wr_rigid_v4_acquire(l,q,b,cancel,out);case 5:return coh_wr_rigid_v5_acquire(l,q,b,cancel,out);case 7:return coh_wr_rigid_v7_acquire(l,q,b,cancel,out);default:return COH_UNSUPPORTED;}}
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
 CohBytes plan=file(argv[12],1u<<20);CHECK(plan.size>=20&&!memcmp(plan.data,"COHSWP01",8)&&u32(plan.data+8)==1&&u32(plan.data+12)==ROOT_PAIRS&&u32(plan.data+16)==ROOT_OWNERS);Pair*pairs=calloc(ROOT_PAIRS,sizeof(*pairs));CHECK(pairs);size_t pos=20;uint32_t owners=0;uint8_t seen[40232]={0};
 for(uint32_t n=0;n<ROOT_PAIRS;n++){CHECK(pos<=plan.size&&plan.size-pos>=8);Pair*p=pairs+n;p->ordinal=u32(plan.data+pos);p->owner_count=u32(plan.data+pos+4);p->index=n;pos+=8;CHECK(p->owner_count&&p->owner_count<=ROOT_OWNERS&&p->owner_count*4u<=plan.size-pos);p->owners=plan.data+pos;pos+=(size_t)p->owner_count*4;CHECK(u32(p->owners)==p->ordinal);CohResourceGeoPin pin;CHECK(coh_source_selection_pin(selection,p->ordinal,&p->file,&pin)==COH_OK);for(uint32_t k=0;k<p->owner_count;k++){uint32_t ordinal=u32(p->owners+k*4);CHECK(ordinal<40232&&!seen[ordinal]);seen[ordinal]=1;}owners+=p->owner_count;}
 CHECK(pos==plan.size&&owners==ROOT_OWNERS);qsort(pairs,ROOT_PAIRS,sizeof(*pairs),order);
 const size_t retained=DIAG_RESERVE+plan.size+ROOT_PAIRS*sizeof(*pairs);Deadline clock={millis(),0};CohCancel cancel={deadline,&clock};uint32_t completed=0,files=0,successes=0,specials=0;uint64_t packet_work=0;
 printf("{\"event\":\"scope\",\"fixture_materials_only\":true,\"assets_admitted\":false,\"world_authority\":false,\"lowlevel_requests_derived_from_actual_body\":true,\"not_transfer_bridge_test\":true,\"cpu_time_limit_ms\":%u,\"packet_work_limit\":%u,\"plan_sha256\":\"",CPU_TIME_LIMIT_MS,PACKET_WORK_LIMIT);uint8_t plan_sha[32];CHECK(digest(NULL,plan,plan_sha)==COH_OK);hashtext(plan_sha);printf("\"}\n");
 for(uint32_t first=0;first<ROOT_PAIRS;){
  uint32_t end=first+1;while(end<ROOT_PAIRS&&pairs[end].file==pairs[first].file)end++;
  if(deadline(&clock)||packet_work>PACKET_WORK_LIMIT)break;
  uint32_t file_index=pairs[first].file;CohResourceGeoPin pin;uint32_t checkfile;CHECK(coh_source_selection_pin(selection,pairs[first].ordinal,&checkfile,&pin)==COH_OK&&checkfile==file_index);char path[8192];CHECK(snprintf(path,sizeof(path),"%s/%s",argv[11],pin.id.path)>0);FILE*f=fopen(path,"rb");CHECK(f&&!fseek(f,0,SEEK_END));long nb=ftell(f);CHECK(nb>0);rewind(f);CohAssetLoader*loader=NULL;CohAssetLimits limits={32u<<20,16u<<20,16u<<20,16u<<20,16,4,4};CHECK(coh_asset_create(&limits,&loader)==COH_OK);CHECK(coh_asset_mount_file(loader,pin.id.path,(CohAssetSource){read_at,f,(uint64_t)nb,pin.id.generation})==COH_OK);
  CohSourceBody*body=NULL;CohSourceBodyReport br;CohSourceBodyBudget bb={32u<<20,96u<<20,retained,32u<<20};CohStatus body_status=coh_source_body_create(NULL,selection,file_index,loader,&bb,digest,NULL,cancel,&body,&br);
  printf("{\"event\":\"file\",\"file\":%u,\"path\":",file_index);string(pin.id.path);printf(",\"status\":%u,\"body_peak\":%zu,\"body_owned\":%zu}\n",body_status,body_status==COH_OK?br.aggregate_reserved_bytes:0,body_status==COH_OK?br.owned_bytes:0);files++;
  for(uint32_t n=first;n<end;n++){
   if(deadline(&clock)||packet_work>PACKET_WORK_LIMIT)break;
   Pair*p=pairs+n;CohStatus status=body_status;CohSourceBodyLease lease;memset(&lease,0,sizeof(lease));CohWrRigidReport rr;memset(&rr,0,sizeof(rr));CohStatus aux_status=COH_NOT_FOUND;uint32_t aux_kinds=0,quad_count=0,pivots=0;size_t aux_peak=0,packet_bytes=0;uint8_t packet_sha[32]={0},record_sha[32]={0},quad_sha[32]={0},pivot_sha[32]={0};Materials m;memset(&m,0,sizeof(m));
   if(status==COH_OK){
    CHECK(coh_source_body_lease(body,p->ordinal,&lease)==COH_OK);memcpy(record_sha,lease.resource_record_sha256,32);
    for(uint32_t k=0;k<p->owner_count;k++){CohSourceBodyLease other;CHECK(coh_source_body_lease(body,u32(p->owners+k*4),&other)==COH_OK);CHECK(!strcmp(other.geo.id.path,lease.geo.id.path)&&!strcmp(other.model.model_name,lease.model.model_name)&&other.model.geo_disk_row==lease.model.geo_disk_row&&!memcmp(other.geo.sha256,lease.geo.sha256,32));}
    m.body=body;m.lease=lease;CohSourceBodyReport ir;CHECK(coh_source_body_view(body,&m.index,&ir)==COH_OK);CohWrRigidRequest q={0};q.geo=lease.geo.id;q.model=lease.model.model_name;memcpy(q.geo_sha256,lease.geo.sha256,32);q.material_generation=19;q.digest=digest;q.acquire=material;q.release=release;q.material_context=&m;
    CohWrRigidLimits cpu={96u<<20,retained+lease.retained_owner_bytes,lease.loader_reservation,2u<<20,2u<<20,65536,65536,65536,512};CohWrRigidResource*resource=NULL;status=acquire(lease.model.geo_version,loader,&q,&cpu,cancel,&resource);
    if(status==COH_OK){
     CHECK(coh_wr_rigid_report(resource,&rr)==COH_OK);CohAssetId id;const char*name;CHECK(coh_wr_rigid_identity(resource,&id,&name)==COH_OK&&!strcmp(id.path,lease.geo.id.path)&&id.generation==lease.binding.asset_generation&&!strcmp(name,lease.model.model_name)&&!memcmp(rr.geo_sha256,lease.geo.sha256,32));CHECK(rr.vertices==lease.model.model.vertex_count&&rr.triangles==lease.model.model.triangle_count&&rr.parts==lease.model.model.material_count&&rr.geo_version==lease.model.geo_version&&rr.material_generation==19&&rr.aggregate_peak_bytes<=cpu.aggregate_limit);
     SHA256_CTX sha;CHECK(SHA256_Init(&sha));for(uint32_t part=0;part<rr.parts;part++){CohRenderGeometry g;CohWrRigidMaterial mat;CHECK(coh_wr_rigid_part(resource,part,&g,&mat)==COH_OK&&g.vertex_count==rr.vertices&&g.generation==lease.binding.asset_generation&&mat.generation==19);size_t vertices=(size_t)g.vertex_count*sizeof(*g.vertices),indices=(size_t)g.index_count*sizeof(*g.indices);CHECK(SHA256_Update(&sha,g.vertices,vertices)&&SHA256_Update(&sha,g.indices,indices));CHECK(vertices<=SIZE_MAX-packet_bytes&&indices<=SIZE_MAX-packet_bytes-vertices);packet_bytes+=vertices+indices;}CHECK(SHA256_Final(packet_sha,&sha));packet_work+=packet_bytes;successes++;
    }
    coh_wr_rigid_release(&resource);CHECK(m.acquired==m.released);
    if(lease.model.geo_version==0||lease.model.geo_version==8){const size_t cap=512u<<10;void*w=malloc(cap);CHECK(w);CohSourceSpecialBudget sb={96u<<20,retained};CohSourceSpecial extra;aux_status=coh_source_special_prepare(body,p->ordinal,w,cap,&sb,cancel,&extra);if(aux_status==COH_OK){aux_kinds=extra.kinds;quad_count=extra.reflection_quads;pivots=extra.alternate_pivots;aux_peak=extra.aggregate_reserved_bytes;CHECK(!extra.ordinary_cpu_ready&&!extra.client_semantics_admitted&&!extra.world_authority);CHECK(digest(NULL,(CohBytes){(const uint8_t*)extra.reflection_vertices,(size_t)quad_count*48},quad_sha)==COH_OK&&digest(NULL,(CohBytes){(const uint8_t*)extra.alternate_pivot,(size_t)pivots*48},pivot_sha)==COH_OK);specials++;}else CHECK(aux_status==COH_NOT_FOUND||aux_status==COH_CANCELLED);free(w);}
   }
   printf("{\"event\":\"pair\",\"i\":%u,\"ordinal\":%u,\"owners\":[",p->index,p->ordinal);for(uint32_t k=0;k<p->owner_count;k++)printf("%s%u",k?",":"",u32(p->owners+k*4));printf("],\"file\":%u,\"phase\":\"%s\",\"status\":%u,\"version\":%u,\"model\":",file_index,body_status==COH_OK?"cpu":"body",status,lease.model.geo_version);string(lease.model.model_name?lease.model.model_name:"");printf(",\"record_sha256\":\"");hashtext(record_sha);printf("\",\"packet_sha256\":\"");hashtext(packet_sha);printf("\",\"packet_bytes\":%zu,\"vertices\":%u,\"triangles\":%u,\"parts\":%u,\"cpu_peak\":%zu,\"aux_status\":%u,\"aux_kinds\":%u,\"quad_count\":%u,\"pivot_count\":%u,\"aux_peak\":%zu,\"quad_sha256\":\"",packet_bytes,rr.vertices,rr.triangles,rr.parts,rr.aggregate_peak_bytes,aux_status,aux_kinds,quad_count,pivots,aux_peak);hashtext(quad_sha);printf("\",\"pivot_sha256\":\"");hashtext(pivot_sha);printf("\"}\n");completed++;
  }
  coh_source_body_free(body);coh_asset_trim(loader);CohAssetStats stats=coh_asset_stats(loader);CHECK(!stats.pinned_blobs);CHECK(coh_asset_destroy(&loader)==COH_OK&&!fclose(f));printf("{\"event\":\"cleanup\",\"file\":%u,\"loader_peak\":%zu,\"pinned_blobs\":0}\n",file_index,stats.peak_allocated_bytes);fflush(stdout);first=end;
 }
 printf("{\"event\":\"summary\",\"complete\":%s,\"completed_pairs\":%u,\"files\":%u,\"successes\":%u,\"specials\":%u,\"packet_bytes\":%llu,\"elapsed_ms\":%llu,\"deadline_stopped\":%s,\"fixture_materials_only\":true,\"world_authority\":false}\n",completed==ROOT_PAIRS?"true":"false",completed,files,successes,specials,(unsigned long long)packet_work,(unsigned long long)(millis()-clock.start),clock.stopped?"true":"false");
 free(pairs);free((void*)plan.data);coh_source_selection_free(selection);coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);return 0;
}
