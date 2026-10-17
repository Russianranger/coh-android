#include "coh_teammate_buffs.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations,randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
typedef struct {const unsigned char *data;size_t bytes,bits,start;unsigned mode,scenario;CohStatus status;const uint32_t *normal;size_t normal_count;const uint32_t *stale;size_t stale_count;} BuffFixture;
#include "buffs_fixtures.h"
static CohEntTeammateBuffs *value,*prior;
static CohEntTeammateBuffsWorkspace *workspace;
static uint32_t observation[32768];static size_t used;
static void emit(uint32_t n){CHECK(used<32768);observation[used++]=n;}
static int known_power(uint32_t n){return n==1||n==1023||n==0x10203040||n==0x80000000||n==0xffffffff;}
/* Explicit fixture-only projection of raw events into the original observer's
 * dictionary/UI shells. It does not apply original stale or prior game state. */
static void project(const CohEntTeammateBuffs *v,unsigned stale){
    used=0;if(!v->teammate||!v->buffs_present)return;
    if(v->not_getting_buffs){if(!stale){emit(1);emit(2);}return;}
    if(!v->diffs_only)emit(1);
    for(uint32_t i=0;i<v->count;i++){
        const CohEntBuff *b=&v->buffs[i];
        if(!stale&&b->delete_mark){emit(4);emit(b->uid);}
        else if(!stale&&known_power(b->power_crc)){
            uint32_t count=0;for(uint32_t j=0;j<b->mods_count;j++)if(v->mods[b->mods_begin+j].attribute_hash!=UINT32_MAX)count++;
            emit(3);emit(b->power_crc);emit(b->timer_present?(2u|b->blink_now):0);emit(b->uid);emit(count);
            for(uint32_t j=0;j<b->mods_count;j++){
                const CohEntBuffMod *m=&v->mods[b->mods_begin+j];
                if(m->attribute_hash!=UINT32_MAX){int32_t signed_word;float magnitude;uint32_t bits;memcpy(&signed_word,&m->magnitude_word,4);magnitude=signed_word/100.f;memcpy(&bits,&magnitude,4);emit(m->attribute_hash);emit(bits);}
            }
        }
    }
    if(!stale)emit(2);
}
static void refuse(CohRepReader r,CohStatus expected){CohRepReader old=r;memset(value,0xa5,sizeof(*value));*prior=*value;CohStatus s=coh_ent_teammate_buffs(&r,value,workspace,0,COH_ENT_BUFF_AGGREGATE_MAX);CHECK(expected==COH_OK?s!=COH_OK:s==expected);CHECK(!memcmp(&r,&old,sizeof(r)));CHECK(!memcmp(value,prior,sizeof(*value)));}
static uint32_t random_state=0x35d174abu;
static uint32_t rand32(void){random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;return random_state;}
int main(void){
 value=malloc(sizeof(*value));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));CHECK(value&&prior&&workspace);
 for(unsigned i=0;i<sizeof(buffs_fixtures)/sizeof(buffs_fixtures[0]);i++){
    const BuffFixture *f=&buffs_fixtures[i];CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->data,f->bytes},f->bits,(int)f->mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=f->start;
    if(f->status!=COH_OK){refuse(r,f->status);continue;}
    CHECK(coh_ent_teammate_buffs(&r,value,workspace,0,COH_ENT_BUFF_AGGREGATE_MAX)==COH_OK);CHECK(r.cursor==f->bits);CHECK(value->begin_bit==f->start&&value->end_bit==f->bits);
    if(f->scenario==11){CHECK(value->count==3);CHECK(value->buffs[1].power_crc==0xdeadbeef);}
    if(f->scenario==20){CHECK(value->count==1);CHECK(value->buffs[0].uid==UINT32_MAX);CHECK(value->mods[0].magnitude_word==UINT32_MAX-124u);}
    if(f->scenario==22){CHECK(value->count==3);CHECK(value->buffs[0].uid==2&&value->buffs[1].uid==1&&value->buffs[2].uid==3);}
    project(value,0);CHECK(used==f->normal_count);CHECK(!memcmp(observation,f->normal,4*used));project(value,1);CHECK(used==f->stale_count);CHECK(!memcmp(observation,f->stale,4*used));
    for(uint32_t j=0;j<value->count;j++){const CohEntBuff *b=&value->buffs[j];CHECK(b->mods_begin<=value->mods_count&&b->mods_count<=value->mods_count-b->mods_begin);}
    /* Exhaust every cut for one rich complete body per alignment. */
    if(f->scenario==20&&f->start==0)for(size_t bit=0;bit<f->bits;bit++){CohRepReader cut=r;cut.bits=bit;cut.cursor=0;refuse(cut,COH_OK);truncations++;}
    if(f->scenario==20&&f->start==0){
       size_t min=sizeof(*value)+sizeof(*workspace)+COH_ENT_BUFF_STACK_RESERVE+f->bytes;r.cursor=f->start;
       CHECK(coh_ent_teammate_buffs(&r,value,workspace,0,min)==COH_OK);r.cursor=f->start;CohRepReader old=r;
       CHECK(coh_ent_teammate_buffs(&r,value,workspace,1,min)==COH_LIMIT);CHECK(!memcmp(&old,&r,sizeof(r)));
       CHECK(coh_ent_teammate_buffs(&r,value,(CohEntTeammateBuffsWorkspace*)value,0,COH_ENT_BUFF_AGGREGATE_MAX)==COH_INVALID);
       CHECK(coh_ent_teammate_buffs(&r,(CohEntTeammateBuffs*)f->data,workspace,0,COH_ENT_BUFF_AGGREGATE_MAX)==COH_INVALID);
    }
    /* Mutate every byte of every supported source fixture independently. */
    unsigned char *mut=malloc(f->bytes);CHECK(mut);
    for(size_t byte=0;byte<f->bytes;byte++){
       memcpy(mut,f->data,f->bytes);mut[byte]^=0xff;CohRepReader changed;
       CHECK(coh_rep_reader_bounded(&changed,(CohBytes){mut,f->bytes},f->bits,(int)f->mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);changed.cursor=f->start;CohRepReader old=changed;
       memset(value,0xa5,sizeof(*value));*prior=*value;CohStatus status=coh_ent_teammate_buffs(&changed,value,workspace,0,COH_ENT_BUFF_AGGREGATE_MAX);
       if(status!=COH_OK){CHECK(!memcmp(&old,&changed,sizeof(old)));CHECK(!memcmp(value,prior,sizeof(*value)));}
       else{CHECK(changed.cursor<=changed.bits);CHECK(value->count<=COH_ENT_BUFFS_MAX);CHECK(value->mods_count<=COH_ENT_BUFF_MODS_MAX);}
       mutations++;
    }
    free(mut);
    /* Later enclosing-message bytes remain unread. */
    unsigned char *bytes=malloc(f->bytes+8);CHECK(bytes);memcpy(bytes,f->data,f->bytes);memset(bytes+f->bytes,0x7f,8);CHECK(coh_rep_reader_bounded(&r,(CohBytes){bytes,f->bytes+8},(f->bytes+8)*8,(int)f->mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=f->start;CHECK(coh_ent_teammate_buffs(&r,value,workspace,0,COH_ENT_BUFF_AGGREGATE_MAX)==COH_OK);CHECK(r.cursor==f->bits);free(bytes);
 }
 for(unsigned i=0;i<10000;i++){
    unsigned char bytes[512];size_t size=rand32()%sizeof(bytes)+1;for(size_t j=0;j<size;j++)bytes[j]=(uint8_t)rand32();CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){bytes,size},size*8,i%2)==COH_OK);r.cursor=i%2?0:rand32()%8;CohRepReader old=r;memset(value,0xa5,sizeof(*value));*prior=*value;CohStatus s=coh_ent_teammate_buffs(&r,value,workspace,0,COH_ENT_BUFF_AGGREGATE_MAX);if(s!=COH_OK){CHECK(!memcmp(&r,&old,sizeof(r)));CHECK(!memcmp(value,prior,sizeof(*value)));}else{CHECK(r.cursor<=r.bits);CHECK(value->count<=COH_ENT_BUFFS_MAX);CHECK(value->mods_count<=COH_ENT_BUFF_MODS_MAX);}randomized++;
 }
 printf("{\"passed\":true,\"checks\":%llu,\"fixtures\":%zu,\"truncations\":%llu,\"mutations\":%llu,\"randomized\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"aggregate_limit\":%u,\"full_update_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,sizeof(buffs_fixtures)/sizeof(buffs_fixtures[0]),(unsigned long long)truncations,(unsigned long long)mutations,(unsigned long long)randomized,sizeof(*value),sizeof(*workspace),COH_ENT_BUFF_AGGREGATE_MAX);
 free(value);free(prior);free(workspace);return 0;
}
