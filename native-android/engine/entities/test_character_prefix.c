#include "coh_character_prefix.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {const uint8_t *data;size_t bits,start;unsigned aligned;uint32_t words[9];uint8_t auth[128];} Fixture;
#include "prefix_fixtures.h"
static unsigned long checks;
#define CHECK(x) do { checks++;assert(x); }while(0)
int main(void) {
    for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++) {
        const Fixture *f=&fixtures[i];CohRepReader reader;CohCharacterPrefix out;
        CHECK(coh_rep_reader(&reader,(CohBytes){f->data,(f->bits+7)/8},f->bits,f->aligned)==COH_OK);
        reader.cursor=f->start;CohRepReader initial=reader;
        memset(&out,0xa5,sizeof(out));CHECK(coh_character_prefix(&reader,&out)==COH_OK);
        CHECK(reader.cursor==f->bits&&out.begin_bit==f->start&&out.end_bit==f->bits);
        CHECK(out.boost_diminishing==f->words[0]&&out.power_diminishing==f->words[1]&&out.no_base_edit==f->words[2]&&out.beta_base==f->words[3]&&out.base_raid==f->words[4]);
        CHECK(out.player_type==f->words[5]&&out.player_subtype==f->words[6]&&out.praetorian_progress==f->words[7]&&out.player_type_by_location==f->words[8]);
        CHECK(!memcmp(out.auth_user_data,f->auth,128));
        for(size_t bit=f->start;bit<f->bits;bit++) {
            reader=initial;reader.bits=bit;CohRepReader before=reader;
            memset(&out,0xa5,sizeof(out));CohCharacterPrefix previous=out;
            CHECK(coh_character_prefix(&reader,&out)==COH_INVALID);
            CHECK(!memcmp(&reader,&before,sizeof(reader))&&!memcmp(&out,&previous,sizeof(out)));
        }
        /* Original array reader ignores alignment padding; preserve that rule. */
        uint8_t data[4096];memcpy(data,f->data,(f->bits+7)/8);
        reader=initial;uint32_t ignored;
        for(unsigned word=0;word<5;word++)CHECK(coh_rep_pack(&reader,word==3?2:1,&ignored)==COH_OK);
        size_t unaligned=reader.cursor,aligned=(unaligned+7u)&~(size_t)7u;
        for(size_t bit=unaligned;bit<aligned;bit++)data[bit/8]|=(uint8_t)(1u<<(bit%8));
        reader=initial;reader.bytes.data=data;
        CHECK(coh_character_prefix(&reader,&out)==COH_OK);
        CHECK(reader.cursor==f->bits&&!memcmp(out.auth_user_data,f->auth,128));
        if(f->aligned) {
            /* Oversize rounded scalar bytes must fail closed for every width. */
            for(unsigned field=0;field<4;field++) {
                static const uint8_t invalid[]={2,4,8,2};
                memcpy(data,f->data,(f->bits+7)/8);data[f->bits/8-4+field]=invalid[field];
                reader=initial;reader.bytes.data=data;CohRepReader before=reader;
                memset(&out,0xa5,sizeof(out));CohCharacterPrefix previous=out;
                CHECK(coh_character_prefix(&reader,&out)==COH_INVALID);
                CHECK(!memcmp(&reader,&before,sizeof(reader))&&!memcmp(&out,&previous,sizeof(out)));
            }
        }
        reader=initial;CHECK(coh_character_prefix(&reader,(CohCharacterPrefix *)(void *)&reader)==COH_INVALID);
        reader=initial;CHECK(coh_character_prefix(&reader,(CohCharacterPrefix *)(void *)f->data)==COH_INVALID);
        reader=initial;reader.cursor=reader.bits+1;CHECK(coh_character_prefix(&reader,&out)==COH_INVALID);
    }
    CHECK(coh_character_prefix(NULL,NULL)==COH_INVALID);
    printf("{\"fixtures\":%zu,\"checks\":%lu,\"whole_character_complete\":false}\n",sizeof(fixtures)/sizeof(fixtures[0]),checks);
    return 0;
}
