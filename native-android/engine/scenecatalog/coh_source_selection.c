#include "coh_source_selection.h"
#include <stdlib.h>
#include <string.h>
#define PROFILE_ROWS 40232u
#define PROFILE_COVERED 8250u
#define PROFILE_ROOTS 3083u
#define NONE UINT16_MAX
#define SCRATCH_RESERVE (128u*1024u)
#include "coh_source_selection_profile.inc"
struct CohSourceSelection {
 uint32_t refs;CohResourceJoin *join;CohResourceJoinIdentity identity;
 const CohResourceSource *sources;size_t count;
 uint32_t offsets[COH_SOURCE_SELECTION_FILES];uint16_t *row_file;
 CohSourceSelectionReport report;
};
struct CohSourceBody {CohSourceSelection *selection;CohResourceIndex *index;CohAssetLoader *loader;size_t reservation;CohSourceBodyReport report;};
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static CohStatus tick(CohCancel c){return c.poll&&c.poll(c.context)?COH_CANCELLED:COH_OK;}
static int disjoint(const void *a,size_t an,const void *b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static CohStatus add(size_t *n,size_t x,size_t cap){if(*n>cap||x>cap-*n)return COH_LIMIT;
 *n+=x;return COH_OK;
 }
#define TRY(x) do{CohStatus z_=(x);if(z_!=COH_OK)return z_;}while(0)
static void unhex(const char *s,uint8_t out[32]){for(unsigned k=0;k<32;k++){unsigned a=(unsigned char)s[k*2],b=(unsigned char)s[k*2+1];out[k]=(uint8_t)(((a<='9'?a-'0':a-'a'+10)<<4)|(b<='9'?b-'0':b-'a'+10));}}
static CohStatus hash(CohResourceDigest d,void *ctx,CohBytes b,const uint8_t expected[32],CohCancel c){uint8_t got[32];TRY(tick(c));TRY(d(ctx,b,got));TRY(tick(c));return memcmp(got,expected,32)?COH_STATE:COH_OK;}
static CohStatus hashhex(CohResourceDigest d,void *ctx,CohBytes b,const char *expected,CohCancel c){uint8_t e[32];unhex(expected,e);return hash(d,ctx,b,e,c);}
static CohStatus dependencies(size_t *total,const CohSourceSelection *s,const CohSourceSelection *old,size_t cap){
 TRY(add(total,s->identity.report.owned_bytes,cap));TRY(add(total,s->identity.catalog_owned_bytes,cap));TRY(add(total,s->identity.snapshot_owned_bytes,cap));TRY(add(total,s->identity.graph_owned_bytes,cap));
 if(old&&old!=s){if(old->join!=s->join)TRY(add(total,old->identity.report.owned_bytes,cap));if(old->identity.catalog_identity!=s->identity.catalog_identity)TRY(add(total,old->identity.catalog_owned_bytes,cap));if(old->identity.snapshot_identity!=s->identity.snapshot_identity)TRY(add(total,old->identity.snapshot_owned_bytes,cap));if(old->identity.graph_identity!=s->identity.graph_identity)TRY(add(total,old->identity.graph_owned_bytes,cap));}return COH_OK;
}
static CohStatus controls(const CohSourceSelection *s,const void *out,size_t n){
 const void *p[]={s,s->row_file,s->sources,s->identity.catalog_bytes.data,s->identity.snapshot_bytes.data,s->identity.resource_bytes.data,profile_wire};
 size_t sizes[]={sizeof(*s),s->row_file?s->count*sizeof(*s->row_file):0,s->count*sizeof(*s->sources),s->identity.catalog_bytes.size,s->identity.snapshot_bytes.size,s->identity.resource_bytes.size,sizeof(profile_wire)};
 for(unsigned k=0;k<7;k++)if(!disjoint(out,n,p[k],sizes[k]))return COH_INVALID;
 return COH_OK;
}
static const char *entry_name(const CohSourceSelection *s,uint32_t file){return (const char*)profile_wire+s->offsets[file]+52;}
static const char *entry_path(const CohSourceSelection *s,uint32_t file){const uint8_t *p=profile_wire+s->offsets[file];return (const char*)p+52+u32(p+4);}
static uint32_t find(const CohSourceSelection *s,const char *name){uint32_t lo=0,hi=COH_SOURCE_SELECTION_FILES;while(lo<hi){uint32_t at=lo+(hi-lo)/2;int c=strcmp(name,entry_name(s,at));if(!c)return at;if(c<0)hi=at;else lo=at+1;}return UINT32_MAX;}
static int string_ok(const uint8_t *p,uint32_t n){if(n<2||n>256||p[n-1])return 0;for(uint32_t k=0;k+1<n;k++)if(p[k]<32||p[k]>126)return 0;return 1;}
static CohStatus profile(CohSourceSelection *s,CohResourceDigest d,void *ctx,CohCancel cancel){
 TRY(hash(d,ctx,(CohBytes){profile_wire,sizeof(profile_wire)},profile_wire_sha,cancel));
 if(memcmp(profile_wire,"COHSEL01",8)||u32(profile_wire+8)!=1||u32(profile_wire+12)!=COH_SOURCE_SELECTION_FILES||u32(profile_wire+16)!=PROFILE_ROWS||u32(profile_wire+20)!=PROFILE_ROOTS)return COH_STATE;
 size_t at=32;uint32_t roots=0;
 for(uint32_t k=0;k<COH_SOURCE_SELECTION_FILES;k++){
  TRY(tick(cancel));if(at>sizeof(profile_wire)||sizeof(profile_wire)-at<52)return COH_STATE;
 const uint8_t *p=profile_wire+at;uint32_t bytes=u32(p),a=u32(p+4),b=u32(p+8),n=u32(p+12);
  if(bytes>sizeof(profile_wire)-at||bytes<52||a>bytes-52||b>bytes-52-a||n>(bytes-52-a-b)/4||bytes!=52+a+b+n*4||!n||!string_ok(p+52,a)||!string_ok(p+52+a,b))return COH_STATE;
  s->offsets[k]=(uint32_t)at;if(k&&strcmp(entry_name(s,k-1),entry_name(s,k))>=0)return COH_STATE;
  const uint8_t *ord=p+52+a+b;uint32_t previous=0;
  for(uint32_t m=0;m<n;m++){TRY(tick(cancel));uint32_t value=u32(ord+4*m);if(value>=s->count||(m&&value<=previous))return COH_STATE;
 previous=value;CohResourceView v;TRY(coh_resource_source_view(s->sources[value].record,20261016,&v));if(!v.model_present||strcmp(v.geo_name,entry_name(s,k)))return COH_STATE;
 roots++;}
  at+=bytes;
 }
 if(at!=sizeof(profile_wire)||roots!=PROFILE_ROOTS)return COH_STATE;
 uint32_t covered=0;
 for(uint32_t n=0;n<s->count;n++){TRY(tick(cancel));CohResourceView v;TRY(coh_resource_source_view(s->sources[n].record,20261016,&v));s->row_file[n]=NONE;if(v.model_present){uint32_t k=find(s,v.geo_name);if(k!=UINT32_MAX){s->row_file[n]=(uint16_t)k;covered++;}}}
 return covered==PROFILE_COVERED?COH_OK:COH_STATE;
}
CohStatus coh_source_selection_retain(CohSourceSelection *s){if(!s)return COH_INVALID;
 if(!s->refs||s->refs==UINT32_MAX)return COH_LIMIT;
 s->refs++;return COH_OK;
 }
void coh_source_selection_free(CohSourceSelection *s){if(!s)return;if(s->refs>1){s->refs--;return;}coh_resource_join_free(s->join);free(s->row_file);free(s);}
CohStatus coh_source_selection_create(const CohSourceSelection *old,CohResourceJoin *join,const CohSourceSelectionEvidence *e,const CohSourceSelectionBudget *b,CohResourceDigest d,void *ctx,CohCancel cancel,CohSourceSelection **out,CohSourceSelectionReport *report){
 if(!join||!e||!b||!d||!out||!report)return COH_INVALID;
 const void *cp[]={e,b,out,report};size_t cs[]={sizeof(*e),sizeof(*b),sizeof(*out),sizeof(*report)};
 for(unsigned n=0;n<4;n++)for(unsigned k=n+1;k<4;k++)if(!disjoint(cp[n],cs[n],cp[k],cs[k]))return COH_INVALID;
if(!b->owned_limit||b->owned_limit>COH_RESOURCE_INPUT_MAX||!b->aggregate_limit||b->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_LIMIT;
 CohSourceSelection candidate={0};candidate.count=PROFILE_ROWS;TRY(coh_resource_join_identity(join,&candidate.identity));
 CohResourceBinding binding;size_t count;TRY(coh_resource_join_sources(join,&candidate.sources,&count,&binding));if(count!=PROFILE_ROWS)return COH_STATE;
 candidate.join=join;
 for(unsigned k=2;k<4;k++){TRY(controls(&candidate,cp[k],cs[k]));if(old)TRY(controls(old,cp[k],cs[k]));}
 if(*out)return COH_STATE;
 if(binding.asset_generation!=20261016||!binding.generation||candidate.identity.report.catalog_generation!=20261016||memcmp(binding.source_sha256,evidence_sha[0],32)||memcmp(binding.run_sha256,evidence_sha[1],32)||memcmp(binding.manifest_sha256,evidence_sha[3],32))return COH_STATE;
 uint8_t resources[32];unhex("8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6",resources);if(memcmp(candidate.identity.pins.resources_sha256,resources,32))return COH_STATE;
 if(old&&binding.generation<old->identity.pins.resource.generation)return COH_STATE;
 size_t owned=sizeof(candidate)+count*sizeof(uint16_t),aggregate=b->retained_bytes;
 if(owned>b->owned_limit)return COH_LIMIT;
 TRY(add(&aggregate,owned,b->aggregate_limit));if(old)TRY(add(&aggregate,old->report.owned_bytes,b->aggregate_limit));TRY(dependencies(&aggregate,&candidate,old,b->aggregate_limit));TRY(add(&aggregate,sizeof(profile_wire)+SCRATCH_RESERVE,b->aggregate_limit));
 for(unsigned n=0;n<COH_SOURCE_SELECTION_EVIDENCE;n++){
  if(!e->bytes[n].data||e->bytes[n].size!=evidence_sizes[n])return COH_STATE;
  for(unsigned k=0;k<4;k++)if(!disjoint(cp[k],cs[k],e->bytes[n].data,e->bytes[n].size))return COH_INVALID;
  TRY(add(&aggregate,e->bytes[n].size,b->aggregate_limit));
 }
 for(unsigned n=0;n<COH_SOURCE_SELECTION_EVIDENCE;n++)TRY(hash(d,ctx,e->bytes[n],evidence_sha[n],cancel));
 TRY(hashhex(d,ctx,candidate.identity.catalog_bytes,"61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763",cancel));TRY(hashhex(d,ctx,candidate.identity.snapshot_bytes,"c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02",cancel));TRY(hash(d,ctx,candidate.identity.resource_bytes,resources,cancel));
 CohSourceSelection *s=malloc(sizeof(*s));if(!s)return COH_LIMIT;
 *s=candidate;s->join=NULL;s->refs=1;s->row_file=malloc(count*sizeof(*s->row_file));CohStatus st=COH_LIMIT;if(!s->row_file)goto fail;
 st=profile(s,d,ctx,cancel);if(st!=COH_OK)goto fail;st=tick(cancel);if(st!=COH_OK)goto fail;st=coh_resource_join_retain(join);if(st!=COH_OK)goto fail;s->join=join;
 s->report=(CohSourceSelectionReport){COH_SOURCE_PROCEDURAL_EXACT_COLD_CAPTURE,1,1,0,COH_SOURCE_SELECTION_FILES,PROFILE_COVERED,PROFILE_ROOTS,owned,aggregate,0,0,0,0};*report=s->report;*out=s;return COH_OK;
 fail:coh_source_selection_free(s);return st;
}
CohStatus coh_source_selection_report(const CohSourceSelection *s,CohSourceSelectionReport *out){if(!s||!out)return COH_INVALID;
 TRY(controls(s,out,sizeof(*out)));*out=s->report;return COH_OK;
 }
CohStatus coh_source_selection_pin(const CohSourceSelection *s,uint32_t ordinal,uint32_t *file,CohResourceGeoPin *out){
 if(!s||!file||!out)return COH_INVALID;
 TRY(controls(s,file,sizeof(*file)));TRY(controls(s,out,sizeof(*out)));if(!disjoint(file,sizeof(*file),out,sizeof(*out)))return COH_INVALID;
 if(ordinal>=s->count||s->row_file[ordinal]==NONE)return COH_NOT_FOUND;
 uint32_t k=s->row_file[ordinal];const uint8_t *p=profile_wire+s->offsets[k];CohResourceGeoPin pin={entry_name(s,k),{entry_path(s,k),20261016},{0}};memcpy(pin.sha256,p+20,32);*file=k;*out=pin;return COH_OK;
}
void coh_source_body_free(CohSourceBody *b){if(!b)return;coh_resource_index_free(b->index);coh_source_selection_free(b->selection);free(b);}
CohStatus coh_source_body_view(const CohSourceBody *b,const CohResourceIndex **index,CohSourceBodyReport *report){if(!b||!index||!report)return COH_INVALID;
 if(!disjoint(index,sizeof(*index),report,sizeof(*report))||!disjoint(index,sizeof(*index),b,sizeof(*b))||!disjoint(report,sizeof(*report),b,sizeof(*b)))return COH_INVALID;
 TRY(controls(b->selection,index,sizeof(*index)));TRY(controls(b->selection,report,sizeof(*report)));*index=b->index;*report=b->report;return COH_OK;
 }
CohStatus coh_source_body_create(const CohSourceBody *old,CohSourceSelection *s,uint32_t file,CohAssetLoader *loader,const CohSourceBodyBudget *b,CohResourceDigest digest,void *ctx,CohCancel cancel,CohSourceBody **out,CohSourceBodyReport *report){
 if(!s||!loader||!b||!digest||!out||!report)return COH_INVALID;
 if(!disjoint(b,sizeof(*b),out,sizeof(*out))||!disjoint(b,sizeof(*b),report,sizeof(*report))||!disjoint(out,sizeof(*out),report,sizeof(*report)))return COH_INVALID;
 TRY(controls(s,out,sizeof(*out)));TRY(controls(s,report,sizeof(*report)));
 if(old&&(!disjoint(old,sizeof(*old),out,sizeof(*out))||!disjoint(old,sizeof(*old),report,sizeof(*report))))return COH_INVALID;
 if(old){TRY(controls(old->selection,out,sizeof(*out)));TRY(controls(old->selection,report,sizeof(*report)));}
 if(*out)return COH_STATE;
 if(file>=COH_SOURCE_SELECTION_FILES)return COH_NOT_FOUND;
 if(!b->owned_limit||b->owned_limit>COH_RESOURCE_INPUT_MAX||!b->aggregate_limit||b->aggregate_limit>COH_SG_TRANSACTION_MAX||!b->loader_reservation)return COH_LIMIT;
 TRY(tick(cancel));uint32_t count=0;for(uint32_t k=0;k<s->count;k++){TRY(tick(cancel));if(s->row_file[k]==file)count++;}if(!count)return COH_STATE;
 size_t fixed=b->retained_bytes;TRY(add(&fixed,s->report.owned_bytes,b->aggregate_limit));if(old&&old->selection!=s)TRY(add(&fixed,old->selection->report.owned_bytes,b->aggregate_limit));TRY(dependencies(&fixed,s,old?old->selection:NULL,b->aggregate_limit));if(old){TRY(add(&fixed,old->report.owned_bytes,b->aggregate_limit));if(old->loader!=loader)TRY(add(&fixed,old->reservation,b->aggregate_limit));else if(old->reservation>b->loader_reservation)return COH_LIMIT;
 }
 TRY(add(&fixed,sizeof(profile_wire)+4096u+sizeof(CohSourceBody)+(size_t)count*sizeof(CohResourceSource),b->aggregate_limit));if(sizeof(CohSourceBody)>b->owned_limit)return COH_LIMIT;
 size_t preflight=fixed;TRY(add(&preflight,b->loader_reservation,b->aggregate_limit));
 if(coh_asset_stats(loader).peak_allocated_bytes>b->loader_reservation||(old&&coh_asset_stats(old->loader).peak_allocated_bytes>old->reservation))return COH_LIMIT;
 CohResourceSource *selected=malloc((size_t)count*sizeof(*selected));if(!selected)return COH_LIMIT;
 uint32_t at=0;CohStatus status=COH_OK;
 for(uint32_t n=0;n<s->count;n++){status=tick(cancel);if(status!=COH_OK)goto fail;if(s->row_file[n]==file)selected[at++]=s->sources[n];}
 CohSourceBody *body=calloc(1,sizeof(*body));if(!body){status=COH_LIMIT;goto fail;}
 const uint8_t *p=profile_wire+s->offsets[file];CohResourceGeoPin pin={entry_name(s,file),{entry_path(s,file),20261016},{0}};memcpy(pin.sha256,p+20,32);CohResourceReport ir;CohResourceBudget ib={b->owned_limit-sizeof(*body),b->aggregate_limit,fixed,b->loader_reservation};
 status=coh_resource_index_build(NULL,loader,selected,count,&pin,1,&s->identity.pins.resource,&ib,digest,ctx,cancel,&body->index,&ir);if(status!=COH_OK){free(body);goto fail;}
 status=tick(cancel);if(status!=COH_OK){coh_source_body_free(body);goto fail;}status=coh_source_selection_retain(s);if(status!=COH_OK){coh_source_body_free(body);goto fail;}body->selection=s;body->loader=loader;body->reservation=b->loader_reservation;
 body->report=(CohSourceBodyReport){COH_SOURCE_PROCEDURAL_EXACT_COLD_CAPTURE,1,file,count,1,0,sizeof(*body)+ir.owned_bytes,ir.aggregate_reserved_bytes,0,0,0,0};free(selected);*report=body->report;*out=body;return COH_OK;
 fail:free(selected);return status;
}

CohStatus coh_source_body_lease(const CohSourceBody *b,uint32_t ordinal,CohSourceBodyLease *out){
 if(!b||!out)return COH_INVALID;
 if(!disjoint(b,sizeof(*b),out,sizeof(*out)))return COH_INVALID;
 CohSourceSelection *s=b->selection;TRY(controls(s,out,sizeof(*out)));
 if(ordinal>=s->count||s->row_file[ordinal]!=b->report.file_index)return COH_NOT_FOUND;
 CohSourceBodyLease v={0};CohResourceView observed;TRY(coh_resource_source_view(s->sources[ordinal].record,s->identity.pins.resource.asset_generation,&observed));
 TRY(coh_resource_index_view(b->index,observed.owner_kind,observed.file,observed.slot,&v.model));
 TRY(coh_resource_index_owner_sources(b->index,observed.owner_kind,observed.file,observed.slot,&v.actual_sources));
 if(v.actual_sources.record.size!=s->sources[ordinal].record.size||memcmp(v.actual_sources.record.data,s->sources[ordinal].record.data,v.actual_sources.record.size))return COH_STATE;
 CohBytes spans[]={v.actual_sources.record,v.actual_sources.header,v.actual_sources.blob};
 for(unsigned n=0;n<3;n++)if(!disjoint(out,sizeof(*out),spans[n].data,spans[n].size))return COH_INVALID;
 if(!observed.model_present||v.model.original_id!=observed.original_id||strcmp(v.model.definition_name,observed.definition_name)||strcmp(v.model.model_name,observed.model_name)||strcmp(v.model.geo_name,observed.geo_name))return COH_STATE;
 uint32_t file;TRY(coh_source_selection_pin(s,ordinal,&file,&v.geo));if(file!=b->report.file_index)return COH_STATE;
 TRY(coh_resource_join_node(s->join,ordinal,&v.graph_node));v.source_ordinal=ordinal;v.graph_generation=s->identity.report.graph_generation;v.catalog_generation=s->identity.report.catalog_generation;v.binding=s->identity.pins.resource;
 memcpy(v.resource_record_sha256,s->sources[ordinal].sha256,32);memcpy(v.resources_sha256,s->identity.pins.resources_sha256,32);
 size_t total=b->report.owned_bytes;TRY(add(&total,s->report.owned_bytes,COH_SG_TRANSACTION_MAX));TRY(dependencies(&total,s,NULL,COH_SG_TRANSACTION_MAX));
 TRY(add(&total,sizeof(profile_wire)+sizeof(profile_wire_sha)+sizeof(evidence_sha)+sizeof(evidence_sizes),COH_SG_TRANSACTION_MAX));
 v.loader=b->loader;v.loader_reservation=b->reservation;v.retained_owner_bytes=total;*out=v;return COH_OK;
}

CohStatus coh_source_body_dependencies(const CohSourceBody *b,CohSourceBodyDependencies *out){
 if(!b||!out||!disjoint(b,sizeof(*b),out,sizeof(*out)))return COH_INVALID;
 const CohSourceSelection*s=b->selection;TRY(controls(s,out,sizeof(*out)));
 CohBytes record;CohResourceView model;TRY(coh_resource_index_record(b->index,0,&record,&model));
 CohResourceOwnerSources source;TRY(coh_resource_index_owner_sources(b->index,model.owner_kind,model.file,model.slot,&source));
 CohBytes spans[]={record,source.header,source.blob};for(unsigned n=0;n<3;n++)if(!disjoint(out,sizeof(*out),spans[n].data,spans[n].size))return COH_INVALID;
 CohSourceBodyDependencies value={0};value.body_identity=b;value.index_identity=b->index;value.selection_identity=s;value.profile_identity=profile_wire;value.join_identity=s->join;
 value.body_owned_bytes=b->report.owned_bytes;value.selection_owned_bytes=s->report.owned_bytes;value.profile_bytes=sizeof(profile_wire)+sizeof(profile_wire_sha)+sizeof(evidence_sha)+sizeof(evidence_sizes);value.join=s->identity;value.loader=b->loader;value.loader_reservation=b->reservation;*out=value;return COH_OK;
}
