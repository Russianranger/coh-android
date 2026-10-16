#include "coh_entity_control.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"control check failed: %s at %d\n",#x,__LINE__);exit(1);}}while(0)
typedef struct {const unsigned char *data;size_t bytes,bits;int mode,prefix;CohStatus status;const unsigned char *state,*events,*ordering;}Fixture;
#include "fixtures.h"
static CohRepReader reader(const uint8_t *data,size_t bytes,size_t bits,int mode,size_t prefix){
    CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){data,bytes},bits,mode)==COH_OK);r.cursor=prefix;return r;
}
static void fail_atomic(CohRepReader r,CohStatus expected){
    unsigned char before[sizeof(r)],old[sizeof(CohControlUpdate)];CohControlUpdate out;CohControlFailure failure={0};
    memset(&out,0xa5,sizeof(out));memcpy(old,&out,sizeof(out));memcpy(before,&r,sizeof(r));
    CohStatus result=coh_control_read(&r,&out,&failure);
    CHECK(result!=COH_OK);if(expected!=COH_OK)CHECK(result==expected);
    CHECK(!memcmp(&r,before,sizeof(r)));CHECK(!memcmp(&out,old,sizeof(out)));CHECK(failure.status==result);
}
static void source_controls(void){
    CHECK(sizeof(CohControlState)==ORIGINAL_STATE_SIZE);CHECK(sizeof(CohControlUpdate)==ORIGINAL_UPDATE_SIZE);
    for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
        const Fixture *f=&fixtures[i];CohRepReader r=reader(f->data,f->bytes,f->bits,f->mode,(size_t)f->prefix);
        if(f->status!=COH_OK){fail_atomic(r,f->status);continue;}
        CohControlUpdate update,events;CohControlState state,expected;memcpy(&events,f->events,sizeof(events));memcpy(&expected,f->state,sizeof(expected));
        CHECK(coh_control_read(&r,&update,NULL)==COH_OK);CHECK(r.cursor==f->bits);CHECK(update.end_bit==f->bits);
        CHECK(update.push_count==events.push_count);
        CHECK(!memcmp(update.pushes,events.pushes,sizeof(update.pushes)));
        CHECK(coh_control_state_init(&state,1)==COH_OK);CHECK(coh_control_stage(&state,1,12,&update)==COH_OK);
        CHECK(!memcmp(&state,&expected,sizeof(state)));
        for(uint32_t prior=11;prior<=13;prior++){
            CHECK(coh_control_state_init(&state,1)==COH_OK);
            state.server_packet=state.forced_packet=state.physics_position_packet=prior;
            state.server_valid=state.forced_valid=state.physics_valid=1;
            CHECK(coh_control_stage(&state,1,12,&update)==COH_OK);
            CHECK(!memcmp(&state,f->ordering+(prior-11)*sizeof(state),sizeof(state)));
        }
        for(size_t cut=(size_t)f->prefix;cut<f->bits;cut++){
            CohRepReader truncated=reader(f->data,f->bytes,cut,f->mode,(size_t)f->prefix);fail_atomic(truncated,COH_OK);
        }
        for(size_t b=0;b<f->bytes;b++){
            uint8_t changed[2048];CHECK(f->bytes<=sizeof(changed));memcpy(changed,f->data,f->bytes);changed[b]^=0xff;
            CohRepReader mutated=reader(changed,f->bytes,f->bits,f->mode,(size_t)f->prefix);
            CohControlUpdate v;unsigned char before[sizeof(mutated)],old[sizeof(v)];
            memset(&v,0x5a,sizeof(v));memcpy(old,&v,sizeof(v));memcpy(before,&mutated,sizeof(mutated));
            CohStatus result=coh_control_read(&mutated,&v,NULL);
            if(result!=COH_OK){CHECK(!memcmp(&mutated,before,sizeof(before)));CHECK(!memcmp(&v,old,sizeof(v)));}
            else CHECK(v.push_count<=32&&v.end_bit<=f->bits);
        }
    }
}
typedef struct{uint8_t data[8192];size_t bits;int mode;}Writer;
static void put(Writer *w,unsigned n,uint32_t v){
    if(w->mode)n=(n+7)&~7u;
    for(unsigned i=0;i<n;i++){if((v>>i)&1u)w->data[w->bits/8]|=(uint8_t)(1u<<(w->bits&7));w->bits++;}
}
static void pack(Writer*w,unsigned n,uint32_t v){
    if(w->mode){put(w,32,v);return;}
    while(n<32&&v>=((1u<<n)-1u)){uint32_t all=(1u<<n)-1u;put(w,n,all);v-=all;n=n>16?32:n*2;}put(w,n,v);
}
static void minimal(Writer*w){put(w,1,0);put(w,1,0);put(w,1,0);put(w,1,0);put(w,1,0);put(w,1,0);}
static void check_writer(Writer*w,CohStatus status){fail_atomic(reader(w->data,(w->bits+7)/8,w->bits,w->mode,0),status);}
static void malformed_controls(void){
    for(int mode=0;mode<2;mode++){
        Writer w={{0},0,mode};put(&w,1,1);put(&w,16,1);pack(&w,5,65536);check_writer(&w,COH_INVALID);
        w=(Writer){{0},0,mode};put(&w,1,1);put(&w,16,1);pack(&w,5,1);put(&w,32,1);put(&w,32,0x7f800000u);check_writer(&w,COH_INVALID);
        for(unsigned member=0;member<10;member++){
            w=(Writer){{0},0,mode};put(&w,1,0);put(&w,1,0);put(&w,1,0);put(&w,1,0);put(&w,1,1);put(&w,8,37);
            for(unsigned j=0;j<4;j++)put(&w,32,0);
            while(w.bits&7)put(&w,1,0);
            for(unsigned j=0;j<10;j++)put(&w,32,j==member?0x7fc00000u:0);
            check_writer(&w,COH_INVALID);
        }
        w=(Writer){{0},0,mode};put(&w,1,0);put(&w,1,0);put(&w,1,0);put(&w,1,0);put(&w,1,0);put(&w,1,1);pack(&w,1,1);
        for(unsigned j=0;j<3;j++)put(&w,32,0);
        for(unsigned j=0;j<6;j++)put(&w,1,0);
        pack(&w,1,2);check_writer(&w,COH_INVALID);
        if(mode){w=(Writer){{0},0,mode};put(&w,1,2);check_writer(&w,COH_INVALID);}
        w=(Writer){{0},0,mode};minimal(&w);CohRepReader r=reader(w.data,(w.bits+7)/8,w.bits,mode,0);CohControlUpdate v;
        CHECK(coh_control_read(&r,&v,NULL)==COH_OK);
    }
    CohControlServer server={0};float value=123;CHECK(coh_control_surface_value(&server,2,0,&value)==COH_INVALID);CHECK(value==123);
    for(unsigned i=0;i<10;i++){CHECK(coh_control_surface_value(&server,i/5,i%5,&value)==COH_OK);CHECK(value==0);}
    CohRepReader bad={0};bad.bits=SIZE_MAX;bad.cursor=SIZE_MAX;fail_atomic(bad,COH_INVALID);
}
static void ordering_controls(void){
    const Fixture*f=&fixtures[1];CohRepReader r=reader(f->data,f->bytes,f->bits,f->mode,(size_t)f->prefix);
    CohControlUpdate v;CHECK(coh_control_read(&r,&v,NULL)==COH_OK);
    CohControlState s;unsigned char before[sizeof(s)];
    CHECK(coh_control_state_init(&s,19)==COH_OK);CHECK(coh_control_stage(&s,19,12,&v)==COH_OK);memcpy(before,&s,sizeof(s));
    CHECK(coh_control_stage(&s,20,13,&v)==COH_STATE);CHECK(!memcmp(&s,before,sizeof(s)));
    CHECK(coh_control_stage(&s,19,0,&v)==COH_INVALID);CHECK(!memcmp(&s,before,sizeof(s)));
    v.server.speed.x=999;v.forced.position.x=999;v.physics.position.x=999;
    CHECK(coh_control_stage(&s,19,12,&v)==COH_OK);CHECK(!memcmp(&s,before,sizeof(s)));
    CHECK(coh_control_stage(&s,19,11,&v)==COH_OK);CHECK(!memcmp(&s,before,sizeof(s)));
    CHECK(coh_control_stage(&s,19,13,&v)==COH_OK);CHECK(s.server.speed.x==999&&s.forced.position.x==999&&s.physics.position.x==999);
    CHECK(s.forced.pyr.x==0);CHECK(v.forced.pyr.x!=0);
    CohControlUpdate idonly={0};idonly.physics.has_id=1;idonly.physics.net_id=42;
    CHECK(coh_control_stage(&s,19,14,&idonly)==COH_OK);CHECK(s.physics.net_id==42&&s.physics.position.x==999&&s.physics_position_packet==13);
    memcpy(before,&s,sizeof(s));CHECK(coh_control_state_init(&s,0)==COH_INVALID);CHECK(!memcmp(&s,before,sizeof(s)));
    CHECK(coh_control_state_init(&s,20)==COH_OK);CHECK(coh_control_stage(&s,20,15,&idonly)==COH_OK);CHECK(!s.physics_valid);
    v.has_server=2;memcpy(before,&s,sizeof(s));CHECK(coh_control_stage(&s,20,15,&v)==COH_INVALID);CHECK(!memcmp(&s,before,sizeof(s)));
}
static uint32_t random_word(uint32_t *seed){*seed=*seed*1664525u+1013904223u;return *seed;}
static void fuzz_controls(void){
    uint32_t seed=0x9017ab42;
    for(unsigned trial=0;trial<20000;trial++){
        uint8_t data[256];for(unsigned i=0;i<sizeof(data);i++)data[i]=(uint8_t)(random_word(&seed)>>24);
        size_t bytes=random_word(&seed)%257,bits=bytes?random_word(&seed)%(bytes*8+1):0;int mode=(int)(trial&1);
        CohRepReader r=reader(data,bytes,bits,mode,0);CohControlUpdate out;
        unsigned char before[sizeof(r)],old[sizeof(out)];memset(&out,0xa5,sizeof(out));
        memcpy(old,&out,sizeof(out));memcpy(before,&r,sizeof(r));
        CohStatus result=coh_control_read(&r,&out,NULL);
        if(result!=COH_OK){CHECK(!memcmp(&r,before,sizeof(r)));CHECK(!memcmp(&out,old,sizeof(out)));}
        else CHECK(out.push_count<=32&&out.end_bit<=bits);
    }
}
int main(void){source_controls();malformed_controls();ordering_controls();fuzz_controls();
    printf("{\"passed\":true,\"checks\":%u,\"random_malformed_inputs\":20000,\"update_bytes\":%zu,\"state_bytes\":%zu,\"allocations\":0,\"acknowledgments\":0}\n",checks,sizeof(CohControlUpdate),sizeof(CohControlState));return 0;}
