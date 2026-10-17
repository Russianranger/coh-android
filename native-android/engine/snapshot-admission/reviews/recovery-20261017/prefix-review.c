/* Independent transaction and partial-alias controls for pinned prefix parser.
 * Synthetic bit writer is deliberately separate from original-source oracle. */
#include "coh_character_prefix.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;assert(x);}while(0)
static void bits(unsigned char *p,size_t *at,unsigned n,uint32_t v){for(unsigned i=0;i<n;i++,(*at)++)if(v&(1u<<i))p[*at/8]|=(unsigned char)(1u<<(*at%8));}
int main(void){
    for(unsigned prefix=0;prefix<8;prefix++){
        union {CohCharacterPrefix alignment;unsigned char data[256];} storage;
        unsigned char *data=storage.data;memset(data,0,256);size_t at=prefix;
        /* Packed settings 0,0,0,0,0 with original widths 1,1,1,2,1. */
        for(unsigned i=0;i<5;i++)bits(data,&at,i==3?2:1,0);
        size_t pad_start=at;at=(at+7u)&~(size_t)7u;
        /* Nonzero padding is ignored by original bsReadBitsArray. */
        for(size_t i=pad_start;i<at;i++)data[i/8]|=(unsigned char)(1u<<(i%8));
        size_t auth_at=at;for(unsigned i=0;i<128;i++)bits(data,&at,8,(i*29u+prefix)&255u);
        bits(data,&at,1,1);bits(data,&at,2,3);bits(data,&at,3,7);bits(data,&at,1,1);
        CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){data,256},at,0)==COH_OK);r.cursor=prefix;
        CohRepReader initial=r;CohCharacterPrefix out;memset(&out,0xa5,sizeof(out));
        CHECK(coh_character_prefix(&r,&out)==COH_OK);CHECK(r.cursor==at&&out.begin_bit==prefix&&out.end_bit==at);
        CHECK(out.player_type==1&&out.player_subtype==3&&out.praetorian_progress==7&&out.player_type_by_location==1);
        CHECK(!memcmp(out.auth_user_data,data+auth_at/8,128));
        for(size_t cut=prefix;cut<at;cut++){
            r=initial;r.bits=cut;CohRepReader before=r;memset(&out,0xa5,sizeof(out));CohCharacterPrefix prior=out;
            CHECK(coh_character_prefix(&r,&out)==COH_INVALID);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&out,&prior,sizeof(out)));
        }
        /* Partial overlap is refused before writes, including overlap with
         * unused bytes past declared bits but inside the input owner span. */
        for(size_t offset=0;offset<sizeof(r);offset+=sizeof(size_t)){
            r=initial;CohRepReader before=r;
            CHECK(coh_character_prefix(&r,(CohCharacterPrefix *)(void *)((unsigned char *)&r+offset))==COH_INVALID);
            CHECK(!memcmp(&r,&before,sizeof(r)));
        }
        for(size_t offset=0;offset<256;offset+=sizeof(size_t)){
            unsigned char prior[256];memcpy(prior,data,256);r=initial;CohRepReader before=r;
            CHECK(coh_character_prefix(&r,(CohCharacterPrefix *)(void *)(data+offset))==COH_INVALID);
            CHECK(!memcmp(data,prior,256)&&!memcmp(&r,&before,sizeof(r)));
        }
        /* Invalid cursor and compressed alignment refuse atomically. */
        r=initial;r.cursor=at+1;CohRepReader before=r;memset(&out,0xa5,sizeof(out));CohCharacterPrefix prior=out;
        CHECK(coh_character_prefix(&r,&out)==COH_INVALID);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&out,&prior,sizeof(out)));
        r=initial;r.compressed=1;r.cursor=1;before=r;
        CHECK(coh_character_prefix(&r,&out)==COH_INVALID);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&out,&prior,sizeof(out)));
    }
    printf("{\"passed\":true,\"checks\":%u,\"independent_writer\":true,\"whole_character_complete\":false}\n",checks);return 0;
}
