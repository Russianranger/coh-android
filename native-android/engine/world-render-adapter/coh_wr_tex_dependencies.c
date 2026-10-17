#include "coh_wr_tex_dependencies.h"
#include "coh_wr_texopt_types_internal.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#define ALL_MISSING 1023u
#define RESERVE 65536u
#define TEX_NOT_LOADED 0
#define GL_TEXTURE_2D 0x0de1u
#define GL_TEXTURE_CUBE_MAP_ARB 0x8513u
typedef struct{CohWrTexBasicInput view;CohWrTexOptRecord*record;}Entry;
struct CohWrTexDependencies{CohWrTexInputs*inputs;CohWrTexDependencyReport report;size_t allocation;Entry rows[];};
typedef struct{const char*name,*dirname;uint32_t flags,texopt_flags,texopt_surface,target,load_state[2];int hasBeenComposited;float gloss;TexOpt stub;}BasicTexture;
typedef struct{uint32_t flags;uint8_t alpha;}Header;
_Static_assert(sizeof(BasicTexture)+sizeof(CohWrTexBasicInput)+3*sizeof(CohWrTexOptView)+4096<16384,"own nested control/frame reservation");
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int icmp(const char*a,const char*b){for(;*a&&*b;a++,b++){int d=(int)fold((unsigned char)*a)-(int)fold((unsigned char)*b);if(d)return d;}return (unsigned char)*a-(unsigned char)*b;}
static const char*strstriConst(const char*s,const char*k){size_t n=strlen(k);for(;*s;s++){size_t i=0;while(i<n&&s[i]&&fold((unsigned char)s[i])==fold((unsigned char)k[i]))i++;if(i==n)return s;}return NULL;}
static void bounded_copy(char*out,const char*in,int n){assert(n>0&&(size_t)n>strlen(in));memcpy(out,in,strlen(in)+1);}
static TexOpt*prepared(BasicTexture*b,const char*directory,const char*name,TexOptFlags*flags){assert(!strcmp(b->dirname,directory)&&!strcmp(b->name,name));*flags=(TexOptFlags)b->texopt_flags;return b->stub.name?&b->stub:NULL;}
#define stricmp icmp
#define strncpyt bounded_copy
#define trickFromTextureDirName(dir,name,flags) prepared(bind,dir,name,flags)
static int texResetTrickBasedParametersBasic(BasicTexture*,BasicTexture**,int);
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wunused-variable"
#include "coh_wr_tex_dependencies_source.inc"
#pragma GCC diagnostic pop
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int stop(CohCancel c){return c.poll&&c.poll(c.context);}
/* Imported cached names are exactly protected parser blob+32; fixed header
 * lengths were already validated against the pinned complete body. Recover that
 * immutable span only for alias rejection, never as new asset admission. */
static uint32_t u32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int input_output(const CohWrTexInputs*inputs,const void*out,size_t n){CohWrTexInputsReport r;if(coh_wr_tex_inputs_report(inputs,&r)!=COH_OK||!apart(inputs,r.owned_bytes,out,n))return 0;for(uint32_t i=0;i<r.texture_count;i++){CohWrTexHeaderInput h;if(coh_wr_tex_inputs_header(inputs,i,&h)!=COH_OK||!h.original_name||(uintptr_t)h.original_name<32)return 0;const uint8_t*body=(const uint8_t*)h.original_name-32;size_t bytes=u32(body);if(!add(&bytes,u32(body+4))||!apart(body,bytes,out,n))return 0;}for(uint32_t i=0;i<r.raw_trick_count;i++){CohWrRawTrickInput v;if(coh_wr_tex_inputs_raw_trick(inputs,i,&v)!=COH_OK||!apart(v.raw.data,v.raw.size,out,n))return 0;}return 1;}
static int output(const CohWrTexDependencies*d,const void*out,size_t n){if(!apart(d,d->allocation,out,n)||!input_output(d->inputs,out,n))return 0;for(uint32_t i=0;i<d->report.count;i++)if(d->rows[i].record){CohWrTexOptView v;if(coh_wr_texopt_record_view(d->rows[i].record,&v)!=COH_OK||!apart(d->rows[i].record,v.owned_bytes,out,n))return 0;}return 1;}
void coh_wr_tex_dependencies_release(CohWrTexDependencies**out){if(out&&*out){CohWrTexDependencies*d=*out;for(uint32_t i=0;i<d->report.count;i++)coh_wr_texopt_record_release(&d->rows[i].record);coh_wr_tex_inputs_release(&d->inputs);free(d);*out=NULL;}}
CohStatus coh_wr_tex_dependencies_stage(CohWrTexInputs**inputs,const CohWrTexOptCache*cache,const CohWrSurfaceStates*surface,const CohWrTexDependencyLimits*limits,CohCancel cancel,CohWrTexDependencies**out){
 if(!inputs||!*inputs||!cache||!surface||!limits||!out||!apart(inputs,sizeof(*inputs),out,sizeof(*out))||!apart(limits,sizeof(*limits),out,sizeof(*out))||!apart(limits,sizeof(*limits),inputs,sizeof(*inputs)))return COH_INVALID;
 if(*out)return COH_STATE;
 CohWrTexInputsReport ir;CohWrTexOptCacheReport cr;CohWrSurfaceReport sr;CohStatus status=coh_wr_tex_inputs_report(*inputs,&ir);if(status!=COH_OK)return status;status=coh_wr_texopt_cache_report(cache,&cr);if(status!=COH_OK)return status;status=coh_wr_surface_report(surface,&sr);if(status!=COH_OK)return status;
 if(!input_output(*inputs,out,sizeof(*out))||!input_output(*inputs,inputs,sizeof(*inputs))||!apart(cache,cr.owned_bytes,out,sizeof(*out))||!apart(cache,cr.owned_bytes,inputs,sizeof(*inputs))||!apart(surface,sr.owned_bytes,out,sizeof(*out))||!apart(surface,sr.owned_bytes,inputs,sizeof(*inputs)))return COH_INVALID;
 if(!ir.texture_count||ir.texture_count>256)return COH_UNSUPPORTED;
 if(ir.input_generation!=cr.historical_input_generation||ir.input_generation!=sr.historical_input_generation)return COH_STATE;
 size_t minimum=ir.owned_bytes;if(!add(&minimum,ir.loader_reservation)||!add(&minimum,cr.owned_bytes)||!add(&minimum,cr.loader_reservation)||!add(&minimum,sr.owned_bytes)||!add(&minimum,16384)||limits->external_bytes<minimum)return COH_LIMIT;
 size_t allocation=sizeof(CohWrTexDependencies)+(size_t)ir.texture_count*sizeof(Entry),total=limits->external_bytes;if(!add(&total,allocation)||!add(&total,RESERVE)||total>limits->aggregate_limit||allocation>limits->owned_limit)return COH_LIMIT;
 if(stop(cancel))return COH_CANCELLED;
 CohWrTexDependencies*d=calloc(1,allocation);if(!d)return COH_LIMIT;d->allocation=allocation;d->report=(CohWrTexDependencyReport){ir.texture_count,ir.input_generation,ALL_MISSING,allocation,total};
 for(uint32_t i=0;i<ir.texture_count;i++){
  if(stop(cancel)){status=COH_CANCELLED;goto fail;}Entry*e=d->rows+i;status=coh_wr_tex_inputs_header(*inputs,i,&e->view.header);if(status!=COH_OK)goto fail;CohWrTexHeaderInput*h=&e->view.header;size_t n=strlen(h->original_name);if(n<4||strcmp(h->original_name+n-4,".dds")){status=COH_UNSUPPORTED;goto fail;}
  char query[260],key[128];size_t directory=strlen(h->directory),name=strlen(h->basic_key);if(directory+name+2>sizeof(query)||name+5>sizeof(key)){status=COH_LIMIT;goto fail;}memcpy(query,h->directory,directory);query[directory]='/';memcpy(query+directory+1,h->basic_key,name+1);
  size_t external=limits->external_bytes;if(!add(&external,d->report.owned_bytes)||!add(&external,16384)){status=COH_LIMIT;goto fail;}CohWrTexOptLimits l={limits->owned_limit-d->report.owned_bytes,limits->aggregate_limit,cr.loader_reservation,external};status=coh_wr_texopt_lookup(cache,surface,query,&l,cancel,&e->view.lookup,&e->record);if(status!=COH_OK)goto fail;
  BasicTexture basic;memset(&basic,0,sizeof(basic));basic.name=h->basic_key;basic.dirname=h->directory;basic.texopt_flags=e->view.lookup.name_flags;
  if(e->record){CohWrTexOptView v;status=coh_wr_texopt_record_view(e->record,&v);if(status!=COH_OK)goto fail;if(!add(&d->report.owned_bytes,v.owned_bytes)||!add(&d->report.aggregate_reserved_bytes,v.owned_bytes)){status=COH_LIMIT;goto fail;}basic.stub.name=(char*)v.name;basic.stub.flags=(TexOptFlags)v.flags;basic.stub.surface=(int)v.surface;basic.stub.gloss=v.gloss;basic.texopt_surface=v.surface;}
  memcpy(key,h->basic_key,name);memcpy(key+name,".dds",5);basic.flags=(uint32_t)texFixName(key,key,-1);if(strcmp(key,h->basic_key)){status=COH_INVALID;goto fail;}header_flags(&basic,(Header){h->cached_flags,h->cached_alpha});e->view.initial_basic_flags=basic.flags;e->view.reload_required=(uint32_t)texResetTrickBasedParametersBasic(&basic,NULL,0);target_projection(&basic);e->view.effective_basic_flags=basic.flags;e->view.effective_texopt_flags=basic.texopt_flags;e->view.texopt_surface=basic.texopt_surface;e->view.gloss=basic.gloss;e->view.target=basic.target;e->view.load_state[0]=basic.load_state[0];e->view.load_state[1]=basic.load_state[1];e->view.has_been_composited=(uint32_t)basic.hasBeenComposited;e->view.initial_composite_name=h->basic_key;e->view.initial_composite_directory=h->directory;e->view.missing_requirements=ALL_MISSING;e->view.unresolved_client_semantics=1;
 }
 if(d->report.owned_bytes>limits->owned_limit||d->report.aggregate_reserved_bytes>limits->aggregate_limit){status=COH_LIMIT;goto fail;}if(stop(cancel)){status=COH_CANCELLED;goto fail;}d->inputs=*inputs;*inputs=NULL;*out=d;return COH_OK;
fail:for(uint32_t i=0;i<d->report.count;i++)coh_wr_texopt_record_release(&d->rows[i].record);free(d);return status;
}
CohStatus coh_wr_tex_dependencies_report(const CohWrTexDependencies*d,CohWrTexDependencyReport*out){if(!d||!out||!output(d,out,sizeof(*out)))return COH_INVALID;*out=d->report;return COH_OK;}
CohStatus coh_wr_tex_dependencies_basic(const CohWrTexDependencies*d,uint32_t row,CohWrTexBasicInput*out){if(!d||!out||!output(d,out,sizeof(*out)))return COH_INVALID;if(row>=d->report.count)return COH_NOT_FOUND;*out=d->rows[row].view;return COH_OK;}
CohStatus coh_wr_tex_dependencies_texopt(const CohWrTexDependencies*d,uint32_t row,CohWrTexOptView*out){if(!d||!out||!output(d,out,sizeof(*out)))return COH_INVALID;if(row>=d->report.count||!d->rows[row].record)return COH_NOT_FOUND;return coh_wr_texopt_record_view(d->rows[row].record,out);}
CohStatus coh_wr_tex_dependencies_dependency(const CohWrTexDependencies*d,uint32_t row,uint32_t slot,CohWrTexDependency*out){
 if(!d||!out||!output(d,out,sizeof(*out)))return COH_INVALID;
 if(row>=d->report.count||slot>=16)return COH_NOT_FOUND;
 CohWrTexOptView v;memset(&v,0,sizeof(v));if(d->rows[row].record){CohStatus s=coh_wr_texopt_record_view(d->rows[row].record,&v);if(s!=COH_OK)return s;}CohWrTexDependency result;memset(&result,0,sizeof(result));result.source_slot=slot;result.local_header_ordinal=UINT32_MAX;if(slot<13)result.name=v.layers[slot].name;else if(v.fallback.use_fallback)result.name=slot==13?v.fallback.base:slot==14?v.fallback.blend:v.fallback.bumpmap;result.valid_source_request=(uint32_t)IsValidTexName(result.name);
 if(result.valid_source_request){const char*name=result.name;if(*name=='!')name++;size_t n=strlen(name);if(n>=128||(n>=4&&n<8&&name[n-4]!='.'))result.local_observation=COH_WR_TEX_DEP_UNQUALIFIED_KEY;else if(!n)result.local_observation=COH_WR_TEX_DEP_NOT_OBSERVED;else{(void)texFixName(name,result.basic_key,128);CohWrTexHeaderInput found;CohStatus s=coh_wr_tex_inputs_find_basic(d->inputs,result.basic_key,&found);if(s==COH_OK){result.local_observation=COH_WR_TEX_DEP_PRESENT_IMPORTED_HEADER;result.local_header_ordinal=found.input_ordinal;}else if(s==COH_NOT_FOUND)result.local_observation=COH_WR_TEX_DEP_NOT_OBSERVED;else return s;}}
 *out=result;return COH_OK;
}
