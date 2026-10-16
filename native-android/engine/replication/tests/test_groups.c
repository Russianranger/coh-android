#include "coh_groups.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "groups_fixtures.h"

static unsigned long checks,truncations,sampled_truncations,negative,fuzzed,allocations,deallocations;
void *__real_malloc(size_t);
void *__real_calloc(size_t,size_t);
void *__real_realloc(void *,size_t);
void __real_free(void *);
void *__wrap_malloc(size_t n){allocations++;return __real_malloc(n);}
void *__wrap_calloc(size_t n,size_t m){allocations++;return __real_calloc(n,m);}
void *__wrap_realloc(void *p,size_t n){allocations++;return __real_realloc(p,n);}
void __wrap_free(void *p){deallocations++;__real_free(p);}
#define CHECK(e) do { checks++;if(!(e)){fprintf(stderr,"groups check failed line %d: %s\n",__LINE__,#e);exit(1);} } while(0)
static unsigned char storage[COH_REP_BOUNDED_MESSAGE_MAX];
typedef struct { size_t bits;unsigned aligned; } Writer;
static void put(Writer *w,unsigned width,uint32_t value) {
    unsigned n=w->aligned?(width+7)&~7u:width;
    CHECK(w->bits+n<=sizeof(storage)*8u);
    for(unsigned i=0;i<n;i++) {
        size_t at=w->bits++;unsigned char mask=(unsigned char)(1u<<(at&7));
        if((value>>i)&1u)storage[at/8]|=mask;else storage[at/8]&=(unsigned char)~mask;
    }
}
static void pk(Writer *w,unsigned width,uint32_t value) {
    if(w->aligned){put(w,32,value);return;}
    while(width<32 && value>=((1u<<width)-1u)) {
        uint32_t m=(1u<<width)-1u;put(w,width,m);value-=m;width=width>16?32:width*2;
    }
    put(w,width,value);
}
static void text(Writer *w,const char *s){do {put(w,8,(unsigned char)*s);}while(*s++);}
static Writer begin(unsigned mode){Writer w={0,mode};memset(storage,0,sizeof(storage));pk(&w,1,0);pk(&w,1,0);put(&w,1,0);put(&w,1,1);return w;}
static void footer(Writer *w,uint32_t files,uint32_t refs){pk(w,1,UINT32_MAX);pk(w,1,files);pk(w,1,refs);put(w,32,0x12345678);put(w,32,0x9abcdef0);}
static void start_file(Writer *w){put(w,1,1);text(w,"maps/synthetic.txt");put(w,32,12);put(w,1,0);}
static void root(Writer *w,uint32_t id){pk(w,1,id);text(w,"forward_name");put(w,1,1);put(w,1,0);put(w,1,0);put(w,1,0);}
static CohStatus inspect(const unsigned char *data,size_t bytes,size_t bits,unsigned mode,size_t start,CohGroupsInspection *out,CohGroupsFailure *failure) {
    CohRepReader r,before;CHECK(coh_rep_reader_bounded(&r,(CohBytes){data,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=start;before=r;
    CohGroupsInspection prior=*out;unsigned long old_allocations=allocations,old_deallocations=deallocations;
    CohStatus status=coh_rep_groups(&r,out,failure);CHECK(allocations==old_allocations && deallocations==old_deallocations);
    if(status!=COH_OK){CHECK(!memcmp(&r,&before,sizeof(r)));CHECK(!memcmp(out,&prior,sizeof(prior)));CHECK(failure->status==status);CHECK(failure->bit_offset<=bits);negative++;}
    else {CHECK(r.cursor==bits);CHECK(out->consumed_bits==bits);CHECK(failure->status==COH_OK);CHECK(failure->stage==COH_GROUPS_STAGE_NONE);CHECK(out->work_units<=COH_GROUPS_WORK_MAX);}
    return status;
}
static CohStatus written(Writer *w,CohGroupsInspection *out) {
    CohGroupsFailure f;memset(out,0x5a,sizeof(*out));return inspect(storage,(w->bits+7)/8,w->bits,w->aligned,0,out,&f);
}
static void source_tests(void) {
    for(size_t i=0;i<SOURCE_GROUPS_FIXTURES;i++) {
        const SourceFixture *f=&source_fixtures[i];CohRepReader reader;uint32_t command;
        CHECK(coh_rep_reader_bounded(&reader,(CohBytes){f->data,f->bytes},f->bits,f->compressed,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
        CHECK(coh_rep_pack(&reader,1,&command)==COH_OK);CHECK(command==COH_REP_GROUPS || command==COH_REP_GROUPS+5);
        CohGroupsInspection got;CohGroupsFailure failure;memset(&got,0x3c,sizeof(got));
        CohStatus status=inspect(f->data,f->bytes,f->bits,(unsigned)f->compressed,reader.cursor,&got,&failure);
        if(status!=f->status)fprintf(stderr,"source fixture %s status %u expected %u stage %u offset %zu\n",f->name,(unsigned)status,(unsigned)f->status,(unsigned)failure.stage,failure.bit_offset);
        CHECK(status==f->status);
        if(status==COH_OK) {
            unsigned at=0;
#define EXPECT(field) do { if(f->expected_mask&(1u<<at))CHECK(got.field==f->expected.field);at++; } while(0)
            EXPECT(new_world);EXPECT(files);EXPECT(present_files);EXPECT(defs);EXPECT(removed_defs);EXPECT(children);EXPECT(roots);EXPECT(removed_roots);EXPECT(properties);EXPECT(swaps);EXPECT(raw_matrices);EXPECT(packed_matrices);EXPECT(strings);EXPECT(string_bytes);EXPECT(work_units);EXPECT(max_def_id);EXPECT(max_root_id);EXPECT(footer_file_count);EXPECT(footer_active_roots);EXPECT(footer_defs_crc);EXPECT(footer_refs_crc);
#undef EXPECT
            size_t step=f->bits>16384?(f->bits-reader.cursor)/128:1;
            if(!step)step=1;
            for(size_t end=reader.cursor;end<f->bits;end+=step) {
                CohGroupsInspection untouched;memset(&untouched,0x69,sizeof(untouched));
                CHECK(inspect(f->data,f->bytes,end,(unsigned)f->compressed,reader.cursor,&untouched,&failure)!=COH_OK);
                if(step==1)truncations++;else sampled_truncations++;
            }
            if(step>1)for(size_t end=f->bits-128;end<f->bits;end++) {
                CohGroupsInspection untouched;memset(&untouched,0x69,sizeof(untouched));
                CHECK(inspect(f->data,f->bytes,end,(unsigned)f->compressed,reader.cursor,&untouched,&failure)!=COH_OK);sampled_truncations++;
            }
        }
    }
}
static void boundaries(unsigned mode) {
    CohGroupsInspection result;Writer w=begin(mode);pk(&w,1,0);footer(&w,0,0);CHECK(written(&w,&result)==COH_OK);CHECK(result.files==0 && result.roots==0);
    put(&w,1,0);CHECK(written(&w,&result)==COH_UNSUPPORTED);
    w=begin(mode);pk(&w,1,COH_GROUPS_FILE_MAX+1);CHECK(written(&w,&result)==COH_LIMIT);
    w=begin(mode);pk(&w,1,1);start_file(&w);pk(&w,1,1);put(&w,1,0);pk(&w,1,1);CHECK(written(&w,&result)==COH_INVALID);
    w=begin(mode);pk(&w,1,1);start_file(&w);pk(&w,1,3);put(&w,1,0);pk(&w,1,2);CHECK(written(&w,&result)==COH_INVALID);
    w=begin(mode);pk(&w,1,1);start_file(&w);pk(&w,1,COH_GROUPS_DEF_ID_MAX+1);put(&w,1,0);pk(&w,1,0);footer(&w,1,0);CHECK(written(&w,&result)==COH_OK);CHECK(result.max_def_id==COH_GROUPS_DEF_ID_MAX && result.removed_defs==1);
    w=begin(mode);pk(&w,1,1);start_file(&w);pk(&w,1,COH_GROUPS_DEF_ID_MAX+2);CHECK(written(&w,&result)==COH_LIMIT);
    w=begin(mode);pk(&w,1,1);start_file(&w);pk(&w,1,UINT32_MAX);CHECK(written(&w,&result)==COH_INVALID);
    w=begin(mode);pk(&w,1,0);root(&w,3);root(&w,COH_GROUPS_ROOT_ID_MAX);footer(&w,0,65536);CHECK(written(&w,&result)==COH_OK);CHECK(result.roots==2 && result.max_root_id==COH_GROUPS_ROOT_ID_MAX && result.footer_active_roots==65536);
    w=begin(mode);pk(&w,1,0);root(&w,3);pk(&w,1,3);CHECK(written(&w,&result)==COH_INVALID);
    w=begin(mode);pk(&w,1,0);root(&w,3);pk(&w,1,2);CHECK(written(&w,&result)==COH_INVALID);
    w=begin(mode);pk(&w,1,0);pk(&w,1,COH_GROUPS_ROOT_ID_MAX+1);CHECK(written(&w,&result)==COH_LIMIT);
    w=begin(mode);pk(&w,1,0);pk(&w,1,UINT32_MAX-1);CHECK(written(&w,&result)==COH_INVALID);
    w=begin(mode);pk(&w,1,0);footer(&w,1,0);CHECK(written(&w,&result)==COH_INVALID);
    w=begin(mode);pk(&w,1,0);footer(&w,0,COH_GROUPS_ROOT_MAX+1);CHECK(written(&w,&result)==COH_LIMIT);
    w=begin(mode);pk(&w,1,1);put(&w,1,1);text(&w,"");put(&w,32,0);put(&w,1,1);CHECK(written(&w,&result)==COH_UNSUPPORTED);
    w=begin(mode);pk(&w,1,0);pk(&w,1,0);text(&w,"x");put(&w,1,0);put(&w,32,0x7fc00000);CHECK(written(&w,&result)==COH_INVALID);
    w=begin(mode);pk(&w,1,0);pk(&w,1,0);text(&w,"x");put(&w,1,1);put(&w,1,1);put(&w,1,0);put(&w,1,0);put(&w,1,0);put(&w,32,0x7f800000);CHECK(written(&w,&result)==COH_INVALID);
    if(mode){w=begin(mode);storage[8]=2;CHECK(written(&w,&result)==COH_INVALID);}
}
static void properties_and_masks(unsigned mode) {
    CohGroupsInspection result;Writer w=begin(mode);
    pk(&w,1,1);start_file(&w);pk(&w,1,1);put(&w,1,1);text(&w,"p");put(&w,32,0);pk(&w,1,0);
    for(unsigned i=0;i<4;i++)put(&w,1,0);
    put(&w,1,1);text(&w,"");for(unsigned i=0;i<9;i++)put(&w,1,0);
    pk(&w,1,4);CHECK(written(&w,&result)==COH_UNSUPPORTED);
    w=begin(mode);pk(&w,1,1);start_file(&w);pk(&w,1,1);put(&w,1,1);text(&w,"p");put(&w,32,0);pk(&w,1,0);
    for(unsigned i=0;i<4;i++)put(&w,1,0);
    put(&w,1,1);text(&w,"");for(unsigned i=0;i<9;i++)put(&w,1,0);
    pk(&w,1,0);put(&w,1,0);pk(&w,1,1);put(&w,32,COH_GROUPS_PROPERTY_MAX+1);CHECK(written(&w,&result)==COH_LIMIT);
    w=begin(mode);pk(&w,1,1);start_file(&w);pk(&w,1,1);put(&w,1,1);text(&w,"p");put(&w,32,0);pk(&w,1,COH_GROUPS_CHILD_MAX+1);CHECK(written(&w,&result)==COH_LIMIT);
    /* Source property names are a 64-byte storage field. Values are dynamic
     * in the old engine, so the new finite 4096-byte ceiling is explicit. */
    for(unsigned which=0;which<2;which++) {
        w=begin(mode);pk(&w,1,1);start_file(&w);pk(&w,1,1);put(&w,1,1);text(&w,"p");put(&w,32,0);pk(&w,1,0);
        for(unsigned i=0;i<4;i++)put(&w,1,0);
        put(&w,1,1);text(&w,"");for(unsigned i=0;i<9;i++)put(&w,1,0);
        pk(&w,1,0);put(&w,1,0);pk(&w,1,1);put(&w,32,1);
        if(which)text(&w,"valid_name");
        for(unsigned i=0;i<(which?COH_GROUPS_VALUE_MAX:64);i++)put(&w,8,'x');
        CHECK(written(&w,&result)==COH_LIMIT);
    }
    for(uint32_t team=5;team<=7;team++) {
        w=(Writer){0,mode};memset(storage,0,sizeof(storage));pk(&w,1,0);pk(&w,1,0);put(&w,1,1);put(&w,2,0);pk(&w,1,0);pk(&w,1,0);pk(&w,1,1);
        put(&w,2,0);put(&w,2,0);pk(&w,3,team);put(&w,1,0);text(&w,"");text(&w,"");put(&w,1,0);
        pk(&w,1,0);footer(&w,0,0);CHECK(written(&w,&result)==COH_OK);
    }
}
static void large(void) {
    Writer w=begin(1);CohGroupsInspection result;pk(&w,1,1);put(&w,1,0);
    for(uint32_t i=0;i<8192;i++)root(&w,i*2);
    footer(&w,1,8192);CHECK((w.bits+7)/8>COH_REP_MESSAGE_MAX);CHECK(written(&w,&result)==COH_OK);CHECK(result.roots==8192 && result.packed_matrices==8192 && result.present_files==0);
    /* An otherwise complete body never silently admits zero tail padding. */
    size_t original=w.bits;put(&w,32,0);CHECK(written(&w,&result)==COH_UNSUPPORTED);w.bits=original;
    CohRepReader ordinary;CHECK(coh_rep_reader(&ordinary,(CohBytes){storage,(w.bits+7)/8},w.bits,1)==COH_INVALID);
    /* Work budget is independent of body size and count ceilings. Many legal
     * short names force a bounded refusal even before the 4 MiB byte ceiling. */
    w=begin(1);pk(&w,1,0);char name[256];memset(name,'x',255);name[255]=0;
    for(uint32_t i=0;i<4096;i++){pk(&w,1,i);text(&w,name);put(&w,1,1);put(&w,1,0);put(&w,1,0);put(&w,1,0);}
    footer(&w,0,4096);CHECK(written(&w,&result)==COH_LIMIT);
}
static uint32_t random_word(uint32_t *seed){uint32_t x=*seed;x^=x<<13;x^=x>>17;x^=x<<5;*seed=x;return x;}
static void fuzz(void) {
    uint32_t seed=0x170027u;CohGroupsInspection result;CohGroupsFailure failure;
    for(unsigned i=0;i<30000;i++) {
        size_t bytes=random_word(&seed)%1025;for(size_t j=0;j<bytes;j++)storage[j]=(unsigned char)random_word(&seed);
        size_t bits=bytes?random_word(&seed)%(bytes*8+1):0;unsigned mode=random_word(&seed)&1;
        memset(&result,0xa5,sizeof(result));(void)inspect(storage,bytes,bits,mode,0,&result,&failure);fuzzed++;
    }
    for(unsigned i=0;i<10000;i++) {
        const SourceFixture *f=&source_fixtures[random_word(&seed)%SOURCE_GROUPS_FIXTURES];if(!f->bytes)continue;
        CHECK(f->bytes<=sizeof(storage));memcpy(storage,f->data,f->bytes);
        size_t at=random_word(&seed)%f->bits;storage[at/8]^=(unsigned char)(1u<<(at&7));
        CohRepReader r;uint32_t command;CHECK(coh_rep_reader_bounded(&r,(CohBytes){storage,f->bytes},f->bits,f->compressed,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
        if(coh_rep_pack(&r,1,&command)!=COH_OK)continue;
        memset(&result,0x5a,sizeof(result));(void)inspect(storage,f->bytes,f->bits,(unsigned)f->compressed,r.cursor,&result,&failure);fuzzed++;
    }
}
int main(void) {
    source_tests();boundaries(0);boundaries(1);properties_and_masks(0);properties_and_masks(1);large();fuzz();
    CohGroupsInspection out,before;CohGroupsFailure failure;memset(&out,0x81,sizeof(out));before=out;
    CHECK(coh_rep_groups(NULL,&out,&failure)==COH_INVALID);CHECK(!memcmp(&out,&before,sizeof(out)));
    CHECK(coh_rep_groups(NULL,NULL,NULL)==COH_INVALID);
    CHECK(allocations==0 && deallocations==0);
    printf("{\"checks\":%lu,\"negative\":%lu,\"every_bit_truncations\":%lu,\"sampled_large_truncations\":%lu,\"fuzz_cases\":%lu,\"source_fixtures\":%zu,\"allocations\":%lu,\"deallocations\":%lu}\n",checks,negative,truncations,sampled_truncations,fuzzed,(size_t)SOURCE_GROUPS_FIXTURES,allocations,deallocations);return 0;
}
