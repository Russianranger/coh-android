#include "coh_character_data.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"character check failed: %s at %d\n",#x,__LINE__);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t bytes,bits;int mode,prefix,scenario;const uint8_t*expected;}Fixture;
typedef struct{uint32_t columns,rows,inspirations[5][4];CohCharacterBoost boosts[70];CohCharacterInventory inventories[5];CohCharacterInventoryItem items[10];uint32_t inventory_count,auction_slots;}SubExpected;
#include "fixtures.h"
static CohCharacterData output;
static CohCharacterWorkspace workspace;
static unsigned char prior_output[sizeof(output)];
static CohRepReader reader(const uint8_t*p,size_t bytes,size_t bits,int mode,size_t prefix){
    CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){p,bytes},bits,mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=prefix;return r;
}
static CohCharacterWireProfile profile(int scenario){
    CohCharacterWireProfile p={0};p.generation=7;p.shared_set_count_bound=1;p.player=scenario?1:0;p.shared_set_count=scenario==5?3:(scenario==2?0:(scenario==3?2:1));memset(p.source_profile_sha256,0x11,32);return p;
}
static CohStatus parse(CohRepReader*r,const CohCharacterWireProfile*p){return coh_character_data_read(r,p,&workspace,&output,COH_CHARACTER_RAM_MAX,0,NULL);}
static void rejected(CohRepReader r,const CohCharacterWireProfile*p,CohStatus expected){
    unsigned char before[sizeof(r)];memcpy(before,&r,sizeof(r));memcpy(prior_output,&output,sizeof(output));CohCharacterFailure fail={0};
    CohStatus result=coh_character_data_read(&r,p,&workspace,&output,COH_CHARACTER_RAM_MAX,0,&fail);
    CHECK(result!=COH_OK);if(expected!=COH_OK)CHECK(result==expected);
    CHECK(fail.status==result);CHECK(!memcmp(before,&r,sizeof(r)));CHECK(!memcmp(prior_output,&output,sizeof(output)));
}
static void source_controls(void){
    CHECK(sizeof(CohCharacterData)==ORIGINAL_DATA_SIZE);CHECK(sizeof(SubExpected)==ORIGINAL_SUB_SIZE);
    for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
        const Fixture*f=&fixtures[i];CohCharacterWireProfile p=profile(f->scenario);SubExpected expected;memcpy(&expected,f->expected,sizeof(expected));
        CohRepReader r=reader(f->data,f->bytes,f->bits,f->mode,(size_t)f->prefix);
        if(f->scenario==5){rejected(r,&p,COH_INVALID);continue;} /* Original sender allows this; supported profile does not. */
        CHECK(parse(&r,&p)==COH_OK);CHECK(r.cursor==f->bits&&output.end_bit==f->bits);
        CHECK(!strcmp(output.class_name,"Fixture_Class")&&!strcmp(output.origin_name,"Fixture_Origin"));CHECK(!output.dictionary_bindings_verified);
        CHECK(output.level==17&&output.combat_mod_shift==UINT32_MAX&&output.location==1);CHECK(output.current_build==(f->scenario?3u:0u));
        CHECK(output.active_build==(f->scenario?2u:0u));CHECK(output.build_count==(f->scenario?8u:1u));
        uint32_t sets=f->scenario==0||f->scenario==3?2:(f->scenario==2?16:9);
        CHECK(output.set_count==sets);CHECK(output.power_count==(f->scenario==3?0:sets));CHECK(output.boost_count==70+3*output.power_count);
        for(unsigned b=0;b<output.build_count;b++){
            CHECK(output.builds[b].total_sets==2);CHECK(output.builds[b].level==(f->scenario?b+10:0));
            CHECK(output.builds[b].set_count==(b?2-p.shared_set_count:2));
        }
        for(unsigned k=0;k<output.set_count;k++){
            CohCharacterSet*s=&output.sets[k];CHECK(s->index<2&&s->level==5+s->index);CHECK(s->power_count==(f->scenario==3?0u:1u));
            if(!s->power_count)CHECK(s->empty_root_crc==0x12340001u);
        }
        for(unsigned k=0;k<output.power_count;k++){
            CohCharacterPower*v=&output.powers[k];CHECK(v->power_crc==0x12340003u&&v->level==7&&v->unique_id==70001);
            CHECK(v->range==13.5f&&v->charges==31&&v->usage_time==0.5f&&v->available_time==2.5f&&v->creation_time==0xfedcba98u);
            CHECK(v->enabled==1&&!v->disabled_manually&&v->boost_count==2&&v->global_count==1);
            CHECK(output.boosts[v->boost_first].present&&!output.boosts[v->boost_first+1].present&&output.boosts[v->global_first].present);
        }
        CHECK(output.inspiration_columns==expected.columns&&output.inspiration_rows==expected.rows);CHECK(!memcmp(output.inspirations,expected.inspirations,sizeof(output.inspirations)));
        for(unsigned k=0;k<70;k++)CHECK(!memcmp(&output.boosts[output.boost_inventory[k]],&expected.boosts[k],sizeof(CohCharacterBoost)));
        CHECK(output.inventory_count==expected.inventory_count&&output.auction_slots==expected.auction_slots);
        CHECK(!memcmp(output.inventories,expected.inventories,sizeof(output.inventories)));CHECK(!memcmp(output.items,expected.items,sizeof(expected.items)));
        for(size_t cut=(size_t)f->prefix;cut<f->bits;cut+=8)rejected(reader(f->data,f->bytes,cut,f->mode,(size_t)f->prefix),&p,COH_OK);
        for(size_t cut=f->bits-7;cut<f->bits;cut++)rejected(reader(f->data,f->bytes,cut,f->mode,(size_t)f->prefix),&p,COH_OK);
        for(size_t byte=0;byte<f->bytes;byte+=17){
            uint8_t mutation[65536];CHECK(f->bytes<=sizeof(mutation));memcpy(mutation,f->data,f->bytes);mutation[byte]^=0xff;
            CohRepReader m=reader(mutation,f->bytes,f->bits,f->mode,(size_t)f->prefix);unsigned char before[sizeof(m)];memcpy(before,&m,sizeof(m));memcpy(prior_output,&output,sizeof(output));
            CohStatus result=parse(&m,&p);if(result!=COH_OK){CHECK(!memcmp(before,&m,sizeof(m)));CHECK(!memcmp(prior_output,&output,sizeof(output)));}
            else CHECK(!output.dictionary_bindings_verified&&output.end_bit<=f->bits&&output.boost_count<=COH_CHARACTER_BOOSTS_MAX);
        }
    }
}
typedef struct{uint8_t bytes[65536];size_t bits;int mode;}Writer;
static void put(Writer*w,unsigned width,uint32_t v){if(w->mode)width=(width+7)&~7u;for(unsigned i=0;i<width;i++){if((v>>i)&1u)w->bytes[w->bits/8]|=(uint8_t)(1u<<(w->bits&7));w->bits++;}}
static void pack(Writer*w,unsigned width,uint32_t v){if(w->mode){put(w,32,v);return;}while(width<32&&v>=(1u<<width)-1u){uint32_t all=(1u<<width)-1u;put(w,width,all);v-=all;width=width>16?32:width*2;}put(w,width,v);}
static void automatic(Writer*w,uint32_t v){const unsigned widths[]={2,10,24,32};unsigned bin=0;while(bin<3&&v>=(1u<<widths[bin]))bin++;put(w,2,bin);put(w,widths[bin],v);}
static void prefix(Writer*w){put(w,8,'X');put(w,8,0);put(w,8,'Y');put(w,8,0);pack(w,5,0);automatic(w,0);pack(w,4,0);automatic(w,0);put(w,1,0);}
static void inventories_prefix(Writer*w){
    prefix(w);pack(w,4,0);pack(w,3,0);pack(w,3,0);pack(w,5,70);
    for(unsigned i=0;i<70;i++){pack(w,3,i);put(w,1,0);}pack(w,3,5);
}
static void power_prefix(Writer*w){
    automatic(w,1);pack(w,5,0);
    put(w,32,0);pack(w,3,0);put(w,32,0);put(w,32,0);pack(w,24,0);automatic(w,1);automatic(w,0);automatic(w,37);
}
static void one_power(Writer*w){prefix(w);pack(w,4,1);pack(w,5,0);pack(w,4,1);power_prefix(w);}
static void reject_writer(Writer*w,CohStatus expected){CohCharacterWireProfile p=profile(0);rejected(reader(w->bytes,(w->bits+7)/8,w->bits,w->mode,0),&p,expected);}
static void malformed_controls(void){
    for(int mode=0;mode<2;mode++){
        Writer w={{0},0,mode};prefix(&w);pack(&w,4,257);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};prefix(&w);pack(&w,4,1);pack(&w,5,0);pack(&w,4,1025);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};prefix(&w);pack(&w,4,1);pack(&w,5,0);pack(&w,4,1);automatic(&w,1);pack(&w,5,0);put(&w,32,0x7fc00000u);reject_writer(&w,COH_INVALID);
        w=(Writer){{0},0,mode};one_power(&w);pack(&w,4,2049);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};one_power(&w);pack(&w,4,0);automatic(&w,2049);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};prefix(&w);pack(&w,4,1);pack(&w,5,0);pack(&w,4,2);power_prefix(&w);pack(&w,4,1024);
        for(unsigned j=0;j<1024;j++)put(&w,1,0);
        automatic(&w,0);power_prefix(&w);pack(&w,4,1025);reject_writer(&w,COH_LIMIT); /* Aggregate across powers. */
        w=(Writer){{0},0,mode};one_power(&w);pack(&w,4,1);put(&w,1,1);automatic(&w,1);pack(&w,5,0);pack(&w,2,0);
        for(unsigned j=0;j<4;j++)put(&w,32,0);
        pack(&w,1,11);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};inventories_prefix(&w);pack(&w,8,0);pack(&w,8,2049);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};inventories_prefix(&w);pack(&w,8,0);pack(&w,8,1);pack(&w,5,1);pack(&w,5,0);pack(&w,5,1);pack(&w,5,1);reject_writer(&w,COH_INVALID);
        w=(Writer){{0},0,mode};prefix(&w);pack(&w,4,0);pack(&w,3,6);pack(&w,3,4);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};prefix(&w);pack(&w,4,0);pack(&w,3,0);pack(&w,3,0);pack(&w,5,71);reject_writer(&w,COH_UNSUPPORTED);
        w=(Writer){{0},0,mode};inventories_prefix(&w);for(unsigned i=0;i<5;i++){pack(&w,8,0);pack(&w,8,0);}pack(&w,8,0);
        CohCharacterWireProfile p=profile(0);CohRepReader r=reader(w.bytes,(w.bits+7)/8,w.bits,mode,0);CHECK(parse(&r,&p)==COH_OK);
        p.shared_set_count_bound=0;rejected(reader(w.bytes,(w.bits+7)/8,w.bits,mode,0),&p,COH_STATE);
        p=profile(0);memset(p.source_profile_sha256,0,32);rejected(reader(w.bytes,(w.bits+7)/8,w.bits,mode,0),&p,COH_STATE);
        p=profile(0);p.player=1;rejected(reader(w.bytes,(w.bits+7)/8,w.bits,mode,0),&p,COH_STATE);
        p=profile(0);r=reader(w.bytes,(w.bits+7)/8,w.bits,mode,0);size_t minimum=2*sizeof(output)+r.bytes.size;
        memcpy(prior_output,&output,sizeof(output));CHECK(coh_character_data_read(&r,&p,&workspace,&output,minimum-1,0,NULL)==COH_LIMIT);CHECK(!memcmp(prior_output,&output,sizeof(output)));
        CHECK(coh_character_data_read(&r,&p,&workspace,&output,minimum,1,NULL)==COH_LIMIT);CHECK(!memcmp(prior_output,&output,sizeof(output)));
        CHECK(coh_character_data_read(&r,&p,&workspace,&output,minimum,0,NULL)==COH_OK);
        workspace.candidate.profile=p;r=reader(w.bytes,(w.bits+7)/8,w.bits,mode,0);
        CHECK(coh_character_data_read(&r,&workspace.candidate.profile,&workspace,&output,minimum,0,NULL)==COH_OK);CHECK(output.profile.generation==7);
        r=reader(w.bytes,(w.bits+7)/8,w.bits,mode,0);CHECK(coh_character_data_read(&r,&p,(CohCharacterWorkspace*)&output,&output,COH_CHARACTER_RAM_MAX,0,NULL)==COH_INVALID);
        r=reader((const uint8_t*)&workspace,16,128,mode,0);CHECK(parse(&r,&p)==COH_INVALID);
        r=reader(w.bytes,(w.bits+7)/8,w.bits,mode,0);unsigned char before[sizeof(r)];memcpy(before,&r,sizeof(r));memcpy(prior_output,&output,sizeof(output));
        CHECK(coh_character_data_read(&r,&p,&workspace,&output,minimum,0,(CohCharacterFailure*)&output)==COH_INVALID);
        CHECK(!memcmp(before,&r,sizeof(r))&&!memcmp(prior_output,&output,sizeof(output)));
        CHECK(coh_character_data_read(&r,&p,&workspace,&output,minimum,0,(CohCharacterFailure*)&workspace)==COH_INVALID);
        CHECK(!memcmp(before,&r,sizeof(r))&&!memcmp(prior_output,&output,sizeof(output)));
        CHECK(coh_character_data_read(&r,&p,&workspace,&output,minimum,0,(CohCharacterFailure*)&r)==COH_INVALID);
        CHECK(!memcmp(before,&r,sizeof(r))&&!memcmp(prior_output,&output,sizeof(output)));
        memcpy(&workspace,&r,sizeof(r));
        CHECK(coh_character_data_read((CohRepReader*)&workspace,&p,&workspace,&output,minimum,0,NULL)==COH_INVALID);
        CHECK(!memcmp(before,&workspace,sizeof(r))&&!memcmp(prior_output,&output,sizeof(output)));
        memcpy(&output,&r,sizeof(r));memcpy(prior_output,&output,sizeof(output));
        CHECK(coh_character_data_read((CohRepReader*)&output,&p,&workspace,&output,minimum,0,NULL)==COH_INVALID);
        CHECK(!memcmp(prior_output,&output,sizeof(output)));
    }
    /* Declared per-build counts fit, but their aggregate exceeds ownership. */
    Writer w={{0},0,0};prefix(&w);w.bytes[(w.bits-1)/8]|=(uint8_t)(1u<<((w.bits-1)&7));put(&w,4,0);
    for(unsigned i=0;i<8;i++)put(&w,6,0);
    put(&w,4,0);pack(&w,4,256);for(unsigned i=0;i<256;i++){pack(&w,5,0);pack(&w,4,0);automatic(&w,1);}
    put(&w,4,1);pack(&w,4,1);CohCharacterWireProfile p=profile(2);
    rejected(reader(w.bytes,(w.bits+7)/8,w.bits,0,0),&p,COH_LIMIT);
}
static uint32_t random_word(uint32_t*seed){*seed=*seed*1664525u+1013904223u;return *seed;}
static void fuzz_controls(void){
    uint32_t seed=0x12870fa1;CohCharacterWireProfile p=profile(0);
    for(unsigned trial=0;trial<2000;trial++){
        uint8_t bytes[256];for(unsigned i=0;i<256;i++)bytes[i]=(uint8_t)(random_word(&seed)>>24);
        size_t n=random_word(&seed)%257,bits=n?random_word(&seed)%(n*8+1):0;CohRepReader r=reader(bytes,n,bits,(int)(trial&1),0);
        unsigned char before[sizeof(r)];memcpy(before,&r,sizeof(r));memcpy(prior_output,&output,sizeof(output));
        CohStatus result=parse(&r,&p);if(result!=COH_OK){CHECK(!memcmp(before,&r,sizeof(r)));CHECK(!memcmp(prior_output,&output,sizeof(output)));}
        else CHECK(!output.dictionary_bindings_verified&&output.end_bit<=bits);
    }
}
int main(void){source_controls();malformed_controls();fuzz_controls();printf("{\"passed\":true,\"checks\":%u,\"random_malformed_inputs\":2000,\"data_bytes\":%zu,\"scratch_bytes\":%zu,\"ram_limit\":%u,\"allocations\":0,\"acknowledgments\":0}\n",checks,sizeof(output),sizeof(workspace),COH_CHARACTER_RAM_MAX);return 0;}
