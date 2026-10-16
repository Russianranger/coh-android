#include "coh_costume.h"
#include "coh_taskforce.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "costume_fixtures.h"
#include "fixtures.h"
static unsigned checks,truncations,randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"costume test failed %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
typedef struct {const unsigned char *data;size_t bits;} Fixture;
#define F(x) (Fixture){x,x##_bits}
static CohRepReader reader(Fixture f,unsigned mode){CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){f.data,(f.bits+7)/8},f.bits,(int)mode)==COH_OK);return r;}
static CohEntCostumeWorkspace workspace;
static CohEntCostume output,prior,expected;
static CohEntCostumeDictionary *dictionary(void){
    CohEntCostumeDictionaryInput in={0};CohBytes strings[16]={{0}},extra[8]={{0}};uint32_t palette[8]={0};uint8_t present[8]={0},sha[32];CohEntCostumeDictionary *d=NULL;
    char none[]="None",male[]="Male";
    strings[1]=(CohBytes){(uint8_t*)none,4};strings[3]=(CohBytes){(uint8_t*)male,4};strings[4]=(CohBytes){(const uint8_t*)"FixtureEntity",13};strings[5]=(CohBytes){(const uint8_t*)"FixtureGeometry",15};
    extra[2]=(CohBytes){(const uint8_t*)"Upper",5};extra[4]=(CohBytes){(const uint8_t*)"BodySet",7};
    palette[2]=0x11223344;palette[5]=0x55667788;present[2]=present[5]=1;memset(sha,0x42,32);
    in.generation=9;in.body_parts=4;in.body_types=6;memcpy(in.manifest_sha256,sha,32);in.strings=(CohEntCostumeStringTable){16,strings};in.extra_strings=(CohEntCostumeStringTable){8,extra};in.palette_max_size=8;in.palette=palette;in.palette_present=present;
    CHECK(coh_ent_costume_dictionary_load(&d,&in,8,sha)==COH_STATE&&!d);sha[0]=0x43;CHECK(coh_ent_costume_dictionary_load(&d,&in,9,sha)==COH_STATE&&!d);sha[0]=0x42;
    strings[2]=(CohBytes){NULL,1};CHECK(coh_ent_costume_dictionary_load(&d,&in,9,sha)==COH_INVALID&&!d);strings[2]=(CohBytes){0};
    present[3]=2;CHECK(coh_ent_costume_dictionary_load(&d,&in,9,sha)==COH_INVALID&&!d);present[3]=0;
    in.body_parts=31;CHECK(coh_ent_costume_dictionary_load(&d,&in,9,sha)==COH_LIMIT&&!d);in.body_parts=4;
    in.strings.max_size=65537;CHECK(coh_ent_costume_dictionary_load(&d,&in,9,sha)==COH_LIMIT&&!d);in.strings.max_size=16;
    {
        CohBytes *large=(CohBytes*)calloc(32768,sizeof(CohBytes));char longname[259];CHECK(large!=NULL);memset(longname,'q',sizeof(longname));
        for(unsigned i=0;i<32768;i++)large[i]=(CohBytes){(const uint8_t*)longname,sizeof(longname)};
        in.strings=(CohEntCostumeStringTable){32768,large};CHECK(coh_ent_costume_dictionary_load(&d,&in,9,sha)==COH_LIMIT&&!d);free(large);in.strings=(CohEntCostumeStringTable){16,strings};
    }
    CHECK(coh_ent_costume_dictionary_load(&d,&in,9,sha)==COH_OK&&d);CHECK(coh_ent_costume_dictionary_bytes(d)<4096);
    /* Poison all input storage after successful copying. */
    memset(none,'X',sizeof(none));memset(male,'X',sizeof(male));memset(strings,0,sizeof(strings));memset(extra,0,sizeof(extra));memset(palette,0,sizeof(palette));
    return d;
}
static void full(Fixture f,unsigned mode,const CostumeExpectedByte *pairs,size_t count,size_t expected_size,CohEntCostumeDictionary *d){
    CohRepReader r=reader(f,mode),start=r;CohEntFailure failure;
    CHECK(expected_size==sizeof(expected));memset(&expected,0,sizeof(expected));for(size_t i=0;i<count;i++){CHECK(pairs[i].offset<sizeof(expected));((unsigned char*)&expected)[pairs[i].offset]=pairs[i].value;}
    memset(&output,0xa5,sizeof(output));prior=output;
    CHECK(coh_ent_costume(&r,d,8,&workspace,&output,&failure)==COH_STATE);CHECK(!memcmp(&r,&start,sizeof(r))&&!memcmp(&output,&prior,sizeof(output)));
    CHECK(coh_ent_costume(&r,d,9,&workspace,&output,&failure)==COH_OK);CHECK(r.cursor==f.bits);CHECK(!memcmp(&output,&expected,sizeof(output)));
    for(size_t n=0;n<f.bits;n++){
        r=start;r.bits=n;CohRepReader oldr=r;output=prior;truncations++;
        CHECK(coh_ent_costume(&r,d,9,&workspace,&output,&failure)!=COH_OK);CHECK(!memcmp(&r,&oldr,sizeof(r))&&!memcmp(&output,&prior,sizeof(output)));CHECK(failure.bit<=n);
    }
}
static void custom(Fixture f,unsigned mode,const CostumeExpectedByte *pairs,size_t count,size_t expected_size){
    CohEntCustomCostume result={0},old=result,want={0};CohEntFailure failure;CohRepReader r=reader(f,mode),start=r;
    CHECK(expected_size==sizeof(want));for(size_t i=0;i<count;i++){CHECK(pairs[i].offset<sizeof(want));((unsigned char*)&want)[pairs[i].offset]=pairs[i].value;}
    CHECK(coh_ent_custom_costume(&r,&result,&failure)==COH_OK);CHECK(!memcmp(&result,&want,sizeof(result))&&r.cursor==f.bits);
    for(size_t n=0;n<f.bits;n++){r=start;r.bits=n;CohRepReader before=r;result=old;truncations++;CHECK(coh_ent_custom_costume(&r,&result,&failure)!=COH_OK);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&result,&old,sizeof(result)));CHECK(failure.bit<=n);}
}
static void bad(Fixture f,unsigned mode,CohStatus status,CohEntCostumeDictionary *d){
    CohRepReader r=reader(f,mode),before=r;CohEntFailure failure;memset(&output,0xa5,sizeof(output));prior=output;
    CHECK(coh_ent_costume(&r,d,9,&workspace,&output,&failure)==status);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&output,&prior,sizeof(output)));CHECK(failure.bit<=f.bits);
}
static CohEntCostumeEnvelopeWorkspace envelope_workspace;
static CohEntCostumeEnvelope envelope_output,envelope_prior,envelope_expected;
static void envelope(Fixture f,unsigned mode,int self,const CostumeExpectedByte *pairs,size_t count,size_t expected_size,CohEntCostumeDictionary *d){
    CohRepReader r=reader(f,mode),start=r;CohEntFailure failure;
    CHECK(expected_size==sizeof(envelope_expected));memset(&envelope_expected,0,sizeof(envelope_expected));for(size_t i=0;i<count;i++){CHECK(pairs[i].offset<sizeof(envelope_expected));((unsigned char*)&envelope_expected)[pairs[i].offset]=pairs[i].value;}
    memset(&envelope_output,0xa5,sizeof(envelope_output));envelope_prior=envelope_output;
    CHECK(coh_ent_costume_envelope(&r,d,8,self,&envelope_workspace,&envelope_output,&failure)==COH_STATE);CHECK(!memcmp(&r,&start,sizeof(r))&&!memcmp(&envelope_output,&envelope_prior,sizeof(envelope_output)));
    if(envelope_expected.type==1){CHECK(coh_ent_costume_envelope(&r,d,9,!self,&envelope_workspace,&envelope_output,&failure)==COH_STATE);CHECK(!memcmp(&r,&start,sizeof(r))&&!memcmp(&envelope_output,&envelope_prior,sizeof(envelope_output)));}
    CHECK(coh_ent_costume_envelope(&r,d,9,self,&envelope_workspace,&envelope_output,&failure)==COH_OK);CHECK(r.cursor==f.bits);
    if(memcmp(&envelope_output,&envelope_expected,sizeof(envelope_output))){for(size_t i=0;i<sizeof(envelope_output);i++)if(((unsigned char*)&envelope_output)[i]!=((unsigned char*)&envelope_expected)[i]){fprintf(stderr,"envelope mismatch offset %zu got %u want %u mode %u self %d\n",i,((unsigned char*)&envelope_output)[i],((unsigned char*)&envelope_expected)[i],mode,self);break;}}
    CHECK(!memcmp(&envelope_output,&envelope_expected,sizeof(envelope_output)));
    for(size_t n=0;n<f.bits;n++){
        r=start;r.bits=n;CohRepReader oldr=r;envelope_output=envelope_prior;truncations++;
        CHECK(coh_ent_costume_envelope(&r,d,9,self,&envelope_workspace,&envelope_output,&failure)!=COH_OK);CHECK(!memcmp(&r,&oldr,sizeof(r))&&!memcmp(&envelope_output,&envelope_prior,sizeof(envelope_output)));CHECK(failure.bit<=n);
    }
}
static void envelope_bad(Fixture f,unsigned mode,int self,CohStatus status,CohEntCostumeDictionary *d){
    CohRepReader r=reader(f,mode),before=r;CohEntFailure failure;memset(&envelope_output,0xa5,sizeof(envelope_output));envelope_prior=envelope_output;
    CHECK(coh_ent_costume_envelope(&r,d,9,self,&envelope_workspace,&envelope_output,&failure)==status);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&envelope_output,&envelope_prior,sizeof(envelope_output)));CHECK(failure.bit<=f.bits);
}
static void envelope_max_rewards(Fixture f,unsigned mode,CohEntCostumeDictionary *d){
    CohRepReader r=reader(f,mode);CohEntFailure failure;
    CHECK(coh_ent_costume_envelope(&r,d,9,1,&envelope_workspace,&envelope_output,&failure)==COH_OK);CHECK(r.cursor==f.bits);
    CHECK(envelope_output.reward_count[0]==256&&envelope_output.reward_count[1]==256&&envelope_output.current_slot==0&&envelope_output.additional_slots==255);
    for(unsigned i=0;i<256;i++)CHECK(!envelope_output.rewards[0][i].present&&!envelope_output.rewards[1][i].present);
}
static CohEntPowerCustomWorkspace power_workspace;
static CohEntPowerCustomEnvelope power_output,power_prior,power_expected;
static void power_custom(Fixture f,unsigned mode,int self,const CostumeExpectedByte *pairs,size_t count,size_t expected_size){
    CohRepReader r=reader(f,mode),start=r;CohEntFailure failure;
    CHECK(expected_size==sizeof(power_expected));memset(&power_expected,0,sizeof(power_expected));for(size_t i=0;i<count;i++){CHECK(pairs[i].offset<sizeof(power_expected));((unsigned char*)&power_expected)[pairs[i].offset]=pairs[i].value;}
    memset(&power_output,0xa5,sizeof(power_output));power_prior=power_output;
    if(power_expected.type==1){CHECK(coh_ent_power_custom(&r,!self,&power_workspace,&power_output,&failure)==COH_STATE);CHECK(!memcmp(&r,&start,sizeof(r))&&!memcmp(&power_output,&power_prior,sizeof(power_output)));}
    CHECK(coh_ent_power_custom(&r,self,&power_workspace,&power_output,&failure)==COH_OK);CHECK(r.cursor==f.bits);CHECK(!memcmp(&power_output,&power_expected,sizeof(power_output)));
    for(size_t n=0;n<f.bits;n++){
        r=start;r.bits=n;CohRepReader oldr=r;power_output=power_prior;truncations++;
        CHECK(coh_ent_power_custom(&r,self,&power_workspace,&power_output,&failure)!=COH_OK);CHECK(!memcmp(&r,&oldr,sizeof(r))&&!memcmp(&power_output,&power_prior,sizeof(power_output)));CHECK(failure.bit<=n);
    }
}
static void power_bad(Fixture f,unsigned mode,int self,CohStatus status){
    CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f.data,(f.bits+7)/8},f.bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);CohRepReader before=r;CohEntFailure failure;
    memset(&power_output,0xa5,sizeof(power_output));power_prior=power_output;
    CHECK(coh_ent_power_custom(&r,self,&power_workspace,&power_output,&failure)==status);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&power_output,&power_prior,sizeof(power_output)));CHECK(failure.bit<=f.bits);
}
static void power_max(Fixture f,unsigned mode){
    CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f.data,(f.bits+7)/8},f.bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);CohEntFailure failure;
    CHECK(coh_ent_power_custom(&r,1,&power_workspace,&power_output,&failure)==COH_OK);CHECK(r.cursor==f.bits&&power_output.item_count==4096&&power_output.list_count==8);
    for(unsigned i=0;i<4096;i++)CHECK(power_output.items[i].power_crc==1&&!power_output.items[i].colors[0]&&!power_output.items[i].colors[1]&&!power_output.items[i].token[0]);
}
static void fuzz(CohEntCostumeDictionary *d){
    uint32_t seed=0xabc12345;unsigned char bytes[1024];
    for(unsigned k=0;k<5000;k++){
        for(unsigned j=0;j<sizeof(bytes);j++){seed=seed*1664525u+1013904223u;bytes[j]=(unsigned char)(seed>>24);}
        size_t n=seed%(sizeof(bytes)*8+1);CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},n,k%2)==COH_OK);CohRepReader before=r;CohEntFailure failure;memset(&output,0xa5,sizeof(output));prior=output;
        CohStatus status=coh_ent_costume(&r,d,9,&workspace,&output,&failure);randomized++;
        if(status!=COH_OK){CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&output,&prior,sizeof(output)));CHECK(failure.bit<=n);}else CHECK(r.cursor<=n);
        CohEntCustomCostume c={0},old=c;r=before;status=coh_ent_custom_costume(&r,&c,&failure);
        if(status!=COH_OK){CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&c,&old,sizeof(c)));CHECK(failure.bit<=n);}else CHECK(r.cursor<=n);
        if(k<1000){
            r=before;memset(&envelope_output,0xa5,sizeof(envelope_output));envelope_prior=envelope_output;status=coh_ent_costume_envelope(&r,d,9,(k/2)%2,&envelope_workspace,&envelope_output,&failure);
            if(status!=COH_OK){CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&envelope_output,&envelope_prior,sizeof(envelope_output)));CHECK(failure.bit<=n);}else CHECK(r.cursor<=n);
            r=before;memset(&power_output,0xa5,sizeof(power_output));power_prior=power_output;status=coh_ent_power_custom(&r,(k/2)%2,&power_workspace,&power_output,&failure);
            if(status!=COH_OK){CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&power_output,&power_prior,sizeof(power_output)));CHECK(failure.bit<=n);}else CHECK(r.cursor<=n);
        }
    }
}
#define ENVELOPE(s,m,self,d) envelope(F(costume_##s##_##m),m,self,costume_##s##_##m##_expected,sizeof(costume_##s##_##m##_expected)/sizeof(CostumeExpectedByte),costume_##s##_##m##_size,d)
#define POWER(s,m,self) power_custom(F(costume_##s##_##m),m,self,costume_##s##_##m##_expected,sizeof(costume_##s##_##m##_expected)/sizeof(CostumeExpectedByte),costume_##s##_##m##_size)
#define FULL(s,m,d) full(F(costume_##s##_##m),m,costume_##s##_##m##_expected,sizeof(costume_##s##_##m##_expected)/sizeof(CostumeExpectedByte),costume_##s##_##m##_size,d)
#define MODE(m,d) do { \
 FULL(0,m,d);FULL(1,m,d);FULL(2,m,d); \
 POWER(14,m,1);POWER(15,m,0);POWER(16,m,1);POWER(17,m,0);POWER(18,m,1);POWER(19,m,0);POWER(20,m,1);POWER(21,m,1); \
 power_bad(F(power_unknown##m),m,0,COH_UNSUPPORTED);power_bad(F(power_current##m),m,1,COH_LIMIT);power_bad(F(power_slots_zero##m),m,1,COH_LIMIT);power_bad(F(power_slots_limit##m),m,1,COH_LIMIT);power_bad(F(power_current_unstored##m),m,1,COH_LIMIT); \
 power_bad(F(power_count_limit##m),m,0,COH_LIMIT);power_bad(F(power_long_token##m),m,0,COH_LIMIT);power_bad(F(power_aggregate_limit##m),m,1,COH_LIMIT);power_max(F(power_aggregate_max##m),m); \
 envelope_max_rewards(F(envelope_rewards_max##m),m,d); \
 ENVELOPE(4,m,1,d);ENVELOPE(5,m,1,d);ENVELOPE(6,m,0,d);ENVELOPE(7,m,0,d);ENVELOPE(8,m,0,d);ENVELOPE(9,m,0,d);ENVELOPE(10,m,0,d);ENVELOPE(11,m,1,d);ENVELOPE(12,m,1,d);ENVELOPE(13,m,1,d); \
 envelope_bad(F(envelope_unknown##m),m,0,COH_UNSUPPORTED,d);envelope_bad(F(envelope_reward_limit##m),m,1,COH_LIMIT,d);envelope_bad(F(envelope_reward_hole##m),m,1,COH_NOT_FOUND,d);envelope_bad(F(envelope_reward_null##m),m,1,COH_INVALID,d); \
 envelope_bad(F(envelope_slots##m),m,1,COH_LIMIT,d);envelope_bad(F(envelope_current##m),m,1,COH_LIMIT,d);envelope_bad(F(envelope_count_zero##m),m,1,COH_LIMIT,d);envelope_bad(F(envelope_count_limit##m),m,1,COH_LIMIT,d); \
 envelope_bad(F(envelope_other_multiple##m),m,0,COH_INVALID,d);envelope_bad(F(envelope_custom_flag##m),m,0,COH_INVALID,d);envelope_bad(F(envelope_sequence_long##m),m,0,COH_LIMIT,d);envelope_bad(F(envelope_fx_long##m),m,0,COH_LIMIT,d); \
 custom(F(costume_3_##m),m,costume_3_##m##_expected,sizeof(costume_3_##m##_expected)/sizeof(CostumeExpectedByte),costume_3_##m##_size); \
 bad(F(costume_bad_empty_cache##m),m,COH_INVALID,d);bad(F(costume_bad_hole##m),m,COH_NOT_FOUND,d);bad(F(costume_bad_index##m),m,COH_LIMIT,d);bad(F(costume_bad_long##m),m,COH_LIMIT,d); \
 bad(F(costume_bad_body##m),m,COH_LIMIT,d);bad(F(costume_bad_nan##m),m,COH_INVALID,d);bad(F(costume_bad_parts##m),m,COH_LIMIT,d);bad(F(costume_bad_color_cache##m),m,COH_INVALID,d);bad(F(costume_bad_color_hole##m),m,COH_NOT_FOUND,d); \
}while(0)
#include "test_taskforce.c.inc"
void costume_run_tests(unsigned *allchecks,unsigned *alltruncations,unsigned *allrandomized){
    CohEntCostumeDictionary *d=dictionary();MODE(0,d);MODE(1,d);fuzz(d);taskforce_run_tests(d);coh_ent_costume_dictionary_free(d);
    *allchecks+=checks;*alltruncations+=truncations;*allrandomized+=randomized;
}
