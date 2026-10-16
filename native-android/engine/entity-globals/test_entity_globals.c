#include "coh_entity_globals.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const unsigned char *data;size_t bytes,bits;
    unsigned aligned,prefix,present,count;
    CohStatus status;const unsigned char *expected;
} Fixture;
#include "fixtures.h"
static unsigned checks,truncations,random_cases;
unsigned coh_badges_run_tests(void);
void coh_badges_print_report(void);
#define CHECK(expr) do {checks++;if(!(expr)){fprintf(stderr,"globals check failed line %d: %s\n",__LINE__,#expr);exit(1);}} while(0)
static void init(CohRepReader *r,const unsigned char *data,size_t bytes,size_t bits,unsigned aligned,unsigned prefix) {
    CHECK(coh_rep_reader(r,(CohBytes){data,bytes},bits,(int)aligned)==COH_OK);
    r->cursor=prefix;
}
static CohStatus attempt(CohRepReader *r,CohPowerModes *state,CohPowerModeEvent *event) {
    CohRepReader before;CohPowerModes saved;CohPowerModeEvent old;
    memcpy(&before,r,sizeof(before));memcpy(&saved,state,sizeof(saved));memcpy(&old,event,sizeof(old));
    CohStatus status=coh_global_power_modes(r,state,event);
    if(status!=COH_OK) {
        CHECK(memcmp(r,&before,sizeof(before))==0);
        CHECK(memcmp(state,&saved,sizeof(saved))==0);
        CHECK(memcmp(event,&old,sizeof(old))==0);
    } else {
        CHECK(r->cursor>=before.cursor && r->cursor<=r->bits);
        CHECK(event->replacement_present<=1 && state->count<=COH_GLOBAL_POWER_MODE_MAX);
        if(!event->replacement_present) CHECK(memcmp(state,&saved,sizeof(saved))==0);
        else for(uint32_t i=state->count;i<COH_GLOBAL_POWER_MODE_MAX;i++) CHECK(state->modes[i]==0);
    }
    return status;
}
static void source_fixtures(void) {
    for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++) {
        const Fixture *f=&fixtures[i];CohRepReader reader;CohPowerModes state;CohPowerModeEvent event={99};
        memcpy(&state,prior_state,sizeof(state));init(&reader,f->data,f->bytes,f->bits,f->aligned,f->prefix);
        CHECK(attempt(&reader,&state,&event)==f->status);
        if(f->status==COH_OK) {
            CHECK(reader.cursor==f->bits);CHECK(event.replacement_present==f->present);
            CHECK(memcmp(&state,f->expected,sizeof(state))==0);
            /* Exhaust all small-field bit cuts; large cap fixtures additionally
             * cover every 97th bit and final 96 bits, without quadratic fuzz. */
            for(size_t cut=f->prefix;cut<f->bits;cut++) {
                if(f->count>=1024 && cut>f->prefix+96 && cut+96<f->bits && cut%97) continue;
                memcpy(&state,prior_state,sizeof(state));event.replacement_present=99;
                init(&reader,f->data,f->bytes,cut,f->aligned,f->prefix);
                CHECK(attempt(&reader,&state,&event)!=COH_OK);truncations++;
            }
        }
    }
}
typedef struct {unsigned char data[128];size_t bits;} Writer;
static void bits(Writer *w,unsigned width,uint32_t value) {
    CHECK(w->bits+width<=sizeof(w->data)*8);
    for(unsigned i=0;i<width;i++,w->bits++) if((value>>i)&1u)w->data[w->bits/8]|=(unsigned char)(1u<<(w->bits&7));
}
static void pack(Writer *w,unsigned width,uint32_t value) {
    while(width<32 && value>=((1u<<width)-1u)) {
        uint32_t limit=(1u<<width)-1u;bits(w,width,limit);value-=limit;width=width>16?32:width*2;
    }
    bits(w,width,value);
}
static void malformed(void) {
    CohPowerModes state={0},saved;CohPowerModeEvent event={99};CohRepReader reader;
    Writer w={{0},0};bits(&w,1,1);pack(&w,3,1025);
    init(&reader,w.data,(w.bits+7)/8,w.bits,0,0);CHECK(attempt(&reader,&state,&event)==COH_LIMIT);
    memset(&w,0,sizeof(w));bits(&w,1,1);pack(&w,3,UINT32_MAX);
    init(&reader,w.data,(w.bits+7)/8,w.bits,0,0);CHECK(attempt(&reader,&state,&event)==COH_LIMIT);
    /* Overflow an individual mode's expanded pack3 accumulator. */
    memset(&w,0,sizeof(w));bits(&w,1,1);pack(&w,3,1);
    bits(&w,3,7);bits(&w,6,63);bits(&w,12,4095);bits(&w,24,16777215);bits(&w,32,UINT32_MAX);
    init(&reader,w.data,(w.bits+7)/8,w.bits,0,0);CHECK(attempt(&reader,&state,&event)==COH_INVALID);
    unsigned char aligned[]={2,0,0,0,0};
    init(&reader,aligned,sizeof(aligned),40,1,0);CHECK(attempt(&reader,&state,&event)==COH_INVALID);
    unsigned char absent[]={0};
    memset(&state,0xa5,sizeof(state));state.count=2;memcpy(&saved,&state,sizeof(state));
    init(&reader,absent,1,1,0,0);CHECK(attempt(&reader,&state,&event)==COH_OK);CHECK(memcmp(&saved,&state,sizeof(state))==0);
    state.count=1025;init(&reader,absent,1,1,0,0);CHECK(attempt(&reader,&state,&event)==COH_LIMIT);state.count=0;
    reader.cursor=reader.bits+1;CHECK(attempt(&reader,&state,&event)==COH_INVALID);
    init(&reader,absent,1,1,0,0);reader.compressed=2;CHECK(attempt(&reader,&state,&event)==COH_INVALID);
    CHECK(coh_global_power_modes(NULL,&state,&event)==COH_INVALID);
    CHECK(coh_global_power_modes(&reader,NULL,&event)==COH_INVALID);
    CHECK(coh_global_power_modes(&reader,&state,NULL)==COH_INVALID);
}
static void alias_refusals(void) {
    union Storage {CohPowerModes state;CohRepReader reader;CohPowerModeEvent event;unsigned char bytes[8192];} a,before;
    CohPowerModes state={0},saved;CohRepReader reader,old;CohPowerModeEvent event={0},prior;
    unsigned char absent[]={0};
    memset(&a,0,sizeof(a));init(&a.reader,absent,1,1,0,0);memcpy(&before,&a,sizeof(a));
    CHECK(coh_global_power_modes(&a.reader,&a.state,&event)==COH_INVALID);CHECK(memcmp(&a,&before,sizeof(a))==0);
    CHECK(coh_global_power_modes(&a.reader,&state,&a.event)==COH_INVALID);CHECK(memcmp(&a,&before,sizeof(a))==0);
    memset(&a,0,sizeof(a));init(&reader,absent,1,1,0,0);memcpy(&before,&a,sizeof(a));memcpy(&old,&reader,sizeof(old));
    CHECK(coh_global_power_modes(&reader,&a.state,&a.event)==COH_INVALID);CHECK(memcmp(&a,&before,sizeof(a))==0);CHECK(memcmp(&reader,&old,sizeof(old))==0);
    init(&reader,(unsigned char *)&state,sizeof(state),1,0,0);memcpy(&saved,&state,sizeof(state));memcpy(&old,&reader,sizeof(old));
    CHECK(coh_global_power_modes(&reader,&state,&event)==COH_INVALID);CHECK(memcmp(&saved,&state,sizeof(state))==0);CHECK(memcmp(&reader,&old,sizeof(old))==0);
    init(&reader,(unsigned char *)&event,sizeof(event),1,0,0);memcpy(&prior,&event,sizeof(event));memcpy(&old,&reader,sizeof(old));
    CHECK(coh_global_power_modes(&reader,&state,&event)==COH_INVALID);CHECK(memcmp(&prior,&event,sizeof(event))==0);CHECK(memcmp(&reader,&old,sizeof(old))==0);
    init(&reader,(unsigned char *)&reader,sizeof(reader),1,0,0);memcpy(&old,&reader,sizeof(old));
    CHECK(coh_global_power_modes(&reader,&state,&event)==COH_INVALID);CHECK(memcmp(&reader,&old,sizeof(old))==0);
}
static uint32_t rng=0x391705u;
static uint32_t random32(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static void fuzz(void) {
    unsigned char data[128];
    for(unsigned i=0;i<25000;i++) {
        for(size_t j=0;j<sizeof(data);j++)data[j]=(unsigned char)random32();
        unsigned aligned=i&1u;size_t length=random32()%(sizeof(data)+1);size_t nbits=length?random32()%(length*8+1):0;
        unsigned prefix=aligned?0:(unsigned)(random32()%8);if(prefix>nbits)prefix=0;
        CohRepReader reader;CohPowerModes state;CohPowerModeEvent event={99};
        memcpy(&state,prior_state,sizeof(state));init(&reader,data,length,nbits,aligned,prefix);
        (void)attempt(&reader,&state,&event);random_cases++;
    }
}
int main(void) {
    CHECK(sizeof(CohPowerModes)==4100);CHECK(sizeof(CohPowerModeEvent)==4);
    source_fixtures();malformed();alias_refusals();fuzz();
    checks+=coh_badges_run_tests();
    printf("{\"passed\":true,\"checks\":%u,\"source_fixtures\":%u,\"truncation_cases\":%u,\"random_cases\":%u,\"mode_limit\":%u,\"state_bytes\":%u,\"full_update_complete\":false,\"acknowledgments_enabled\":false,\"badges\":",checks,(unsigned)(sizeof(fixtures)/sizeof(fixtures[0])),truncations,random_cases,COH_GLOBAL_POWER_MODE_MAX,(unsigned)sizeof(CohPowerModes));
    coh_badges_print_report();puts("}");
    return 0;
}
