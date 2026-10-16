#include "coh_scene_lookup.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lookup_fixtures.h"
static unsigned checks;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"lookup check failed %s:%d: %s\n",__FILE__,__LINE__,#x);abort();}}while(0)
#ifdef COH_LOOKUP_STANDALONE
static size_t live;
static int fail_next;
void*__real_calloc(size_t,size_t);
void __real_free(void*);
void*__wrap_calloc(size_t n,size_t z){if(fail_next){fail_next=0;return NULL;}void*p=__real_calloc(n,z);if(p)live++;return p;}
void __wrap_free(void*p){if(p){if(!live)abort();live--;}__real_free(p);}
static void coh_lookup_test_fail_next(void){fail_next=1;}
#else
void coh_lookup_test_fail_next(void);
#endif
static CohSgLookupBinding binding(void){CohSgLookupBinding b={0};b.generation=1;b.asset_generation=7;b.map_generation=99;b.input_kind=COH_SG_LOOKUP_FIXTURE;memset(b.source_sha256,1,32);memset(b.inventory_sha256,2,32);memset(b.manifest_sha256,3,32);return b;}
static CohSgLookupManifest manifest(void){CohSgLookupManifest m={0};m.binding=binding();m.files=lookup_files;m.file_count=2;m.libraries=lookup_libraries;m.library_count=5;m.models=lookup_models;m.model_count=5;return m;}
static CohSgLookupBudget budget={COH_SG_LOOKUP_AGGREGATE_MAX,0};
static void reject(const CohSgLookupIndex*old,CohSgLookupManifest*m,CohStatus status){
    CohSgLookupIndex*candidate=NULL;CohSgLookupMemory report;memset(&report,0xa5,sizeof(report));unsigned char before[sizeof(report)];memcpy(before,&report,sizeof(report));
    CHECK(coh_sg_lookup_build(old,m,&budget,&candidate,&report)==status);CHECK(candidate==NULL);CHECK(!memcmp(before,&report,sizeof(report)));
}
static void source_tests(void){
    CohSgLookupManifest m=manifest();CohSgLookupIndex*g=NULL;CohSgLookupMemory memory;
    CHECK(coh_sg_lookup_build(NULL,&m,&budget,&g,&memory)==COH_OK);CHECK(memory.candidate_bytes==coh_sg_lookup_owned_bytes(g));
    CHECK(memory.aggregate_bytes==memory.input_bytes+memory.candidate_bytes+COH_SG_LOOKUP_STACK_RESERVE);
    for(size_t i=0;i<sizeof(lookup_fixtures)/sizeof(*lookup_fixtures);i++){
        const LookupFixture*f=&lookup_fixtures[i];CohSgLookupMatch result;memset(&result,0x33,sizeof(result));unsigned char previous[sizeof(result)];memcpy(previous,&result,sizeof(result));
        CHECK(coh_sg_lookup_find(g,&m.binding,f->query,&result)==(f->found?COH_OK:COH_NOT_FOUND));
        if(f->found){
            CHECK(result.file_slot==f->file&&result.model_slot==f->model);CHECK(result.unresolved==COH_SG_LOOKUP_UNRESOLVED);
            CHECK(coh_sg_lookup_asset_matches(&result,result.asset_id,result.asset_generation,result.payload_sha256)==COH_OK);
            uint8_t changed[32];memcpy(changed,result.payload_sha256,32);changed[31]^=1;
            CHECK(coh_sg_lookup_asset_matches(&result,result.asset_id,result.asset_generation,changed)==COH_STATE);
            CHECK(coh_sg_lookup_asset_matches(&result,result.asset_id,result.asset_generation+1,result.payload_sha256)==COH_STATE);
        }else CHECK(!memcmp(previous,&result,sizeof(result)));
    }
    CohSgLookupBinding wrong=m.binding;wrong.manifest_sha256[0]^=1;CohSgLookupMatch result;
    CHECK(coh_sg_lookup_find(g,&wrong,"Box",&result)==COH_STATE);wrong=m.binding;wrong.asset_generation++;
    CHECK(coh_sg_lookup_find(g,&wrong,"Box",&result)==COH_STATE);
    CHECK(coh_sg_lookup_find(g,&m.binding,"folder/",&result)==COH_INVALID);
    CHECK(coh_sg_lookup_find(g,&m.binding,"__",&result)==COH_INVALID);
    CHECK(coh_sg_lookup_find(g,&m.binding,"\xc3\xa9",&result)==COH_UNSUPPORTED);
    char long_name[1000];memset(long_name,'a',999);long_name[999]=0;
    CHECK(coh_sg_lookup_find(g,&m.binding,long_name,&result)==COH_LIMIT);
    /* Caller owns the returned names/identity after retirement. */
    CHECK(coh_sg_lookup_find(g,&m.binding,"Box",&result)==COH_OK);coh_sg_lookup_free(g);
    CHECK(!strcmp(result.model_name,"Box__OriginalTrick"));CHECK(!strcmp(result.geo_path,"object_library/a.geo"));
    for(size_t i=0;i<sizeof(lookup_extensions)/sizeof(*lookup_extensions);i++){
        CohSgLookupFile file=lookup_files[0];file.library_path=lookup_extensions[i].name;file.geo_path=lookup_extensions[i].geo;
        m.files=&file;m.file_count=1;m.library_count=2;m.model_count=3;g=NULL;
        CHECK(coh_sg_lookup_build(NULL,&m,&budget,&g,NULL)==COH_OK);
        CHECK(coh_sg_lookup_find(g,&m.binding,"Box",&result)==COH_OK);CHECK(!strcmp(result.geo_path,lookup_extensions[i].geo));coh_sg_lookup_free(g);
    }
}
static void failure_tests(void){
    CohSgLookupManifest m=manifest();CohSgLookupFile files[2];CohSgLookupLibrary libraries[5];CohSgLookupModel models[5];
    memcpy(files,m.files,sizeof(files));memcpy(libraries,m.libraries,sizeof(libraries));memcpy(models,m.models,sizeof(models));m.files=files;m.libraries=libraries;m.models=models;
    models[1].name="bOX__Other";reject(NULL,&m,COH_INVALID);models[1]=lookup_models[1];
    libraries[1].name="bOX";reject(NULL,&m,COH_INVALID);libraries[1]=lookup_libraries[1];
    files[1].library_path="object_library/a.vrml";files[1].geo_path="object_library/a.geo";reject(NULL,&m,COH_INVALID);files[1]=lookup_files[1];
    files[0].geo_path="guessed.geo";reject(NULL,&m,COH_INVALID);files[0]=lookup_files[0];
    files[0].asset_generation++;reject(NULL,&m,COH_STATE);files[0]=lookup_files[0];
    memset(files[0].payload_sha256,0,32);reject(NULL,&m,COH_STATE);files[0]=lookup_files[0];
    libraries[0].file_slot=0;reject(NULL,&m,COH_STATE);libraries[0]=lookup_libraries[0];
    models[0].file_slot=0;reject(NULL,&m,COH_STATE);models[0]=lookup_models[0];
    models[1].slot=models[0].slot;reject(NULL,&m,COH_STATE);models[1]=lookup_models[1];
    m.binding.generation=2;reject(NULL,&m,COH_STATE);m.binding.generation=1;
    m.binding.input_kind=0;reject(NULL,&m,COH_STATE);m.binding.input_kind=COH_SG_LOOKUP_FIXTURE;
    m.model_count=COH_SG_LOOKUP_MODELS_MAX+1;reject(NULL,&m,COH_LIMIT);m.model_count=5;
    coh_lookup_test_fail_next();reject(NULL,&m,COH_LIMIT);
    CohSgLookupIndex*g=NULL;CohSgLookupMemory memory;
    CHECK(coh_sg_lookup_build(NULL,&m,&budget,&g,&memory)==COH_OK);
    CohSgLookupBudget limit={memory.aggregate_bytes-1,0};CohSgLookupIndex*candidate=NULL;
    CHECK(coh_sg_lookup_build(NULL,&m,&limit,&candidate,NULL)==COH_LIMIT);CHECK(candidate==NULL);
    limit.aggregate_limit++;CHECK(coh_sg_lookup_build(NULL,&m,&limit,&candidate,NULL)==COH_OK);coh_sg_lookup_free(candidate);candidate=NULL;
    limit.retained_bytes=1;CHECK(coh_sg_lookup_build(NULL,&m,&limit,&candidate,NULL)==COH_LIMIT);
    m.binding.generation=2;CHECK(coh_sg_lookup_build(g,&m,&budget,&candidate,&memory)==COH_OK);CHECK(memory.prior_bytes==coh_sg_lookup_owned_bytes(g));
    CohSgLookupIndex*retired=NULL,*old=g;
    CohSgLookupManifest unrelated=manifest();unrelated.binding.manifest_sha256[0]^=1;CohSgLookupIndex*other=NULL;
    CHECK(coh_sg_lookup_build(NULL,&unrelated,&budget,&other,NULL)==COH_OK);
    CohSgLookupIndex*other_before=other,*candidate_before=candidate;
    CHECK(coh_sg_lookup_publish(&other,&candidate,&retired)==COH_STATE);
    CHECK(other==other_before&&candidate==candidate_before&&!retired);coh_sg_lookup_free(other);
    CHECK(coh_sg_lookup_publish(&g,&candidate,&retired)==COH_OK);CHECK(!candidate&&retired==old&&g!=old);
    CohSgLookupBinding old_binding=m.binding;old_binding.generation=1;CohSgLookupMatch result;
    CHECK(coh_sg_lookup_find(retired,&old_binding,"Box",&result)==COH_OK);
    m.binding.generation=3;CHECK(coh_sg_lookup_build(g,&m,&budget,&candidate,NULL)==COH_OK);
    CHECK(coh_sg_lookup_publish(&g,&candidate,&retired)==COH_STATE);CHECK(candidate&&g&&retired==old);
    coh_sg_lookup_free(retired);retired=NULL;coh_sg_lookup_free(candidate);candidate=NULL; /* cancelled preparation */
    CHECK(coh_sg_lookup_find(g,&m.binding,"Box",&result)==COH_STATE);m.binding.generation=2;
    CHECK(coh_sg_lookup_find(g,&m.binding,"Box",&result)==COH_OK);coh_sg_lookup_free(g);
    /* Input storage may be released or reused immediately after build. */
    char mutable_name[]="Mutable__Trick";CohSgLookupLibrary one={0,3,"Mutable"};CohSgLookupModel model={3,0,mutable_name};
    m=manifest();m.libraries=&one;m.library_count=1;m.models=&model;m.model_count=1;g=NULL;
    CHECK(coh_sg_lookup_build(NULL,&m,&budget,&g,NULL)==COH_OK);memset(mutable_name,'x',sizeof(mutable_name)-1);
    CHECK(coh_sg_lookup_find(g,&m.binding,"Mutable",&result)==COH_OK);CHECK(!strcmp(result.model_name,"Mutable__Trick"));coh_sg_lookup_free(g);
}
static size_t stress_owned,stress_aggregate;
static uint32_t collision_hash(const char*s){uint32_t h=2166136261u;for(unsigned i=0;i<4;i++)h*=16777619u;for(;*s;s++){h^=(unsigned char)*s;h*=16777619u;}return h;}
static void adversarial_tests(void){
    CohSgLookupLibrary*rows=calloc(257,sizeof(*rows));char(*names)[20]=calloc(257,sizeof(*names));CHECK(rows&&names);
    unsigned found=0;
    for(unsigned i=0;found<257;i++){
        char name[20];snprintf(name,sizeof(name),"collision%u",i);
        if((collision_hash(name)&1023u)==0){strcpy(names[found],name);rows[found]=(CohSgLookupLibrary){found,3,names[found]};found++;}
    }
    CohSgLookupManifest m=manifest();m.file_count=1;m.libraries=rows;m.library_count=257;m.model_count=0;reject(NULL,&m,COH_LIMIT);free(rows);free(names);
    m=manifest();CohSgLookupIndex*g=NULL;CHECK(coh_sg_lookup_build(NULL,&m,&budget,&g,NULL)==COH_OK);
    uint32_t seed=117;
    for(unsigned i=0;i<2000;i++){
        char name[65];seed=seed*1664525u+1013904223u;unsigned n=seed%64+1;
        for(unsigned j=0;j<n;j++){seed=seed*1664525u+1013904223u;name[j]=(char)(1+(seed>>24)%255);}name[n]=0;
        CohSgLookupMatch match;memset(&match,0xa5,sizeof(match));unsigned char before[sizeof(match)];memcpy(before,&match,sizeof(match));
        CohStatus status=coh_sg_lookup_find(g,&m.binding,name,&match);
        CHECK(status!=COH_OK);CHECK(!memcmp(before,&match,sizeof(match)));
    }
    coh_sg_lookup_free(g);
}
static void stress_tests(void){
    const unsigned count=32768;CohSgLookupLibrary*libs=calloc(count,sizeof(*libs));CohSgLookupModel*models=calloc(count,sizeof(*models));
    char(*names)[10]=calloc(count,sizeof(*names));char(*full)[17]=calloc(count,sizeof(*full));CHECK(libs&&models&&names&&full);
    for(unsigned i=0;i<count;i++){
        snprintf(names[i],10,"mesh%05u",i);snprintf(full[i],17,"mesh%05u__Trick",i);
        libs[i]=(CohSgLookupLibrary){i*2,3,names[i]};models[i]=(CohSgLookupModel){3,i*3,full[i]};
    }
    CohSgLookupManifest m=manifest();m.file_count=1;m.libraries=libs;m.library_count=count;m.models=models;m.model_count=count;
    CohSgLookupIndex*g=NULL;CohSgLookupMemory memory;CHECK(coh_sg_lookup_build(NULL,&m,&budget,&g,&memory)==COH_OK);
    stress_owned=memory.candidate_bytes;stress_aggregate=memory.aggregate_bytes;
    for(unsigned i=0;i<count;i++){
        CohSgLookupMatch match;CHECK(coh_sg_lookup_find(g,&m.binding,names[i],&match)==COH_OK);
        CHECK(match.library_slot==i*2&&match.model_slot==i*3&&match.unresolved==COH_SG_LOOKUP_UNRESOLVED);
    }
    m.binding.generation=2;CohSgLookupIndex*candidate=NULL;CohSgLookupBudget small={memory.aggregate_bytes,0};
    CHECK(coh_sg_lookup_build(g,&m,&small,&candidate,NULL)==COH_LIMIT);CHECK(candidate==NULL);
    CHECK(coh_sg_lookup_build(g,&m,&budget,&candidate,&memory)==COH_OK);CHECK(memory.prior_bytes==stress_owned);
    coh_sg_lookup_free(candidate);coh_sg_lookup_free(g);free(libs);free(models);free(names);free(full);
}
unsigned coh_scene_lookup_tests(void){checks=0;source_tests();failure_tests();adversarial_tests();stress_tests();return checks;}
#ifdef COH_LOOKUP_STANDALONE
int main(void){unsigned count=coh_scene_lookup_tests();CHECK(live==0);printf("{\"passed\":true,\"checks\":%u,\"large_model_rows\":32768,\"large_library_rows\":32768,\"large_owned_bytes\":%zu,\"large_aggregate_bytes\":%zu,\"live_allocations\":%zu,\"draw_admission\":false}\n",count,stress_owned,stress_aggregate,live);return 0;}
#endif
