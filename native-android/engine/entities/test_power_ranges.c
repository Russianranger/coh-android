#include "coh_power_ranges.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {const uint8_t*data;size_t bits,start;unsigned aligned,outer,count;const CohPowerRange*expected;} Fixture;
#include "range_fixtures.h"
static unsigned long checks;
#define CHECK(x) do {checks++;assert(x);}while(0)
static CohPowerRanges*out,*previous;static CohPowerRangesWorkspace*workspace;
static CohStatus parse(CohRepReader*r,unsigned outer,size_t retained,size_t limit) {
    return outer?coh_power_info_no_changes(r,out,workspace,retained,limit):coh_power_ranges(r,out,workspace,retained,limit);
}
static void refusal(CohRepReader*r,unsigned outer,CohStatus expected,size_t retained,size_t limit) {
    CohRepReader before=*r;memset(out,0xa5,sizeof(*out));*previous=*out;
    CohStatus status=parse(r,outer,retained,limit);
    CHECK(expected==COH_OK?status!=COH_OK:status==expected);
    CHECK(!memcmp(r,&before,sizeof(*r))&&!memcmp(out,previous,sizeof(*out)));
}
typedef struct {uint8_t data[65536];size_t bits;unsigned aligned;} Writer;
static void put(Writer*w,unsigned n,uint32_t value) {
    if(w->aligned)n=(n+7u)&~7u;
    for(unsigned i=0;i<n;i++){size_t bit=w->bits++;if((value>>i)&1u)w->data[bit/8]|=(uint8_t)(1u<<(bit%8));}
}
static CohRepReader input(Writer*w) {
    CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){w->data,(w->bits+7)/8},w->bits,w->aligned)==COH_OK);return r;
}
int main(void) {
    out=malloc(sizeof(*out));previous=malloc(sizeof(*previous));workspace=malloc(sizeof(*workspace));Writer*w=calloc(1,sizeof(*w));
    CHECK(out&&previous&&workspace&&w);
    for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++) {
        const Fixture*f=&fixtures[i];CohRepReader r;
        CHECK(coh_rep_reader(&r,(CohBytes){f->data,(f->bits+7)/8},f->bits,f->aligned)==COH_OK);r.cursor=f->start;
        CohRepReader initial=r;
        if(f->count>COH_POWER_RANGES_MAX)refusal(&r,f->outer,COH_LIMIT,0,COH_POWER_RANGES_AGGREGATE_MAX);
        else {
            CHECK(parse(&r,f->outer,0,COH_POWER_RANGES_AGGREGATE_MAX)==COH_OK);
            CHECK(r.cursor==f->bits&&out->begin_bit==f->start&&out->end_bit==f->bits&&out->count==f->count);
            CHECK(!memcmp(out->ranges,f->expected,f->count*sizeof(CohPowerRange)));
            size_t exact=sizeof(*out)+sizeof(*workspace)+COH_POWER_RANGES_STACK_RESERVE+initial.bytes.size;
            r=initial;CHECK(parse(&r,f->outer,0,exact)==COH_OK);
            r=initial;refusal(&r,f->outer,COH_LIMIT,0,exact-1);
            r=initial;refusal(&r,f->outer,COH_LIMIT,1,exact);
            r=initial;CHECK(parse(&r,f->outer,1,exact+1)==COH_OK);
        }
        /* Every short-message truncation; bounded samples for 1024+ records. */
        size_t step=f->count<20?1:127;
        for(size_t bit=f->start;bit<f->bits;bit+=step) {
            r=initial;r.bits=bit;refusal(&r,f->outer,COH_OK,0,COH_POWER_RANGES_AGGREGATE_MAX);
        }
        r=initial;r.bits=f->bits-1;refusal(&r,f->outer,COH_OK,0,COH_POWER_RANGES_AGGREGATE_MAX);
        r=initial;CHECK(coh_power_ranges(&r,out,(CohPowerRangesWorkspace*)(void*)out,0,COH_POWER_RANGES_AGGREGATE_MAX)==COH_INVALID);
        r=initial;CHECK(coh_power_ranges(&r,(CohPowerRanges*)(void*)((uint8_t*)workspace+4),workspace,0,COH_POWER_RANGES_AGGREGATE_MAX)==COH_INVALID);
        r=initial;CHECK(coh_power_ranges(&r,(CohPowerRanges*)(void*)f->data,workspace,0,COH_POWER_RANGES_AGGREGATE_MAX)==COH_INVALID);
        r=initial;refusal(&r,f->outer,COH_INVALID,0,0);
        r=initial;refusal(&r,f->outer,COH_INVALID,0,COH_POWER_RANGES_AGGREGATE_MAX+1);
        r=initial;r.cursor=r.bits+1;refusal(&r,f->outer,COH_INVALID,0,COH_POWER_RANGES_AGGREGATE_MAX);
    }
    for(unsigned mode=0;mode<2;mode++) {
        memset(w,0,sizeof(*w));w->aligned=mode;put(w,1,1);CohRepReader r=input(w);
        refusal(&r,1,COH_UNSUPPORTED,0,COH_POWER_RANGES_AGGREGATE_MAX);
        if(mode) {
            memset(w,0,sizeof(*w));w->aligned=1;put(w,1,2);r=input(w);refusal(&r,1,COH_INVALID,0,COH_POWER_RANGES_AGGREGATE_MAX);
            r=input(w);refusal(&r,0,COH_INVALID,0,COH_POWER_RANGES_AGGREGATE_MAX);
            memset(w,0,sizeof(*w));w->aligned=1;put(w,1,1);put(w,2,4);r=input(w);refusal(&r,0,COH_INVALID,0,COH_POWER_RANGES_AGGREGATE_MAX);
            memset(w,0,sizeof(*w));w->aligned=1;put(w,1,1);put(w,2,0);put(w,2,4);put(w,32,0);put(w,1,0);r=input(w);refusal(&r,0,COH_INVALID,0,COH_POWER_RANGES_AGGREGATE_MAX);
        }
        /* Correct terminator consumes exactly its body; no suffix guessing. */
        memset(w,0,sizeof(*w));w->aligned=mode;put(w,1,0);size_t end=w->bits;put(w,32,0xffffffff);r=input(w);
        CHECK(parse(&r,0,0,COH_POWER_RANGES_AGGREGATE_MAX)==COH_OK&&r.cursor==end&&out->count==0);
    }
    CHECK(coh_power_ranges(NULL,out,workspace,0,COH_POWER_RANGES_AGGREGATE_MAX)==COH_INVALID);
    free(w);free(workspace);free(previous);free(out);
    printf("{\"fixtures\":%zu,\"checks\":%lu,\"full_power_info_update\":false}\n",sizeof(fixtures)/sizeof(fixtures[0]),checks);return 0;
}
