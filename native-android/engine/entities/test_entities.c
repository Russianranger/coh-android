#include "coh_entities.h"
#include "coh_costume.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fixtures.h"
static unsigned checks, truncations, randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"entity test failed %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
typedef struct {const unsigned char *data;size_t bits;} Fixture;
#define F(x) (Fixture){x,x##_bits}
static CohRepReader reader(Fixture f,unsigned mode){CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){f.data,(f.bits+7)/8},f.bits,(int)mode)==COH_OK);return r;}
static void same_reader(const CohRepReader *a,const CohRepReader *b){CHECK(!memcmp(a,b,sizeof(*a)));}
static void test_create(Fixture f,unsigned mode,unsigned scenario){
    CohRepReader r=reader(f,mode),before=r;CohEntCreate c={0};CohEntFailure failure={0};
    memset(&c,0xa5,sizeof(c));CohEntCreate previous=c;
    CohStatus status=coh_ent_create(&r,4242,&c,&failure);
    CHECK(status==COH_OK);CHECK(c.create==1&&!c.end);CHECK(c.entity_id==(scenario==6?70001u:91u));CHECK(r.cursor==f.bits);CHECK(c.end_bit==f.bits);
    if(scenario==0||scenario==1||scenario==6){CHECK(c.type==2);CHECK(c.is_self==(scenario<2));CHECK(c.dbid==(scenario==6?4243u:4242u));CHECK(c.class_index==3&&c.origin_index==1);CHECK(c.critter_form==(scenario==1));}
    if(scenario==4)CHECK(c.pet_power_crc==0xa1b2c3d4u);
    if(scenario==3||scenario==4){CHECK(c.owner_index==12&&c.creator_index==13);CHECK(c.commandable_pet&&c.visible_pet&&c.dismissable_pet);CHECK(c.special_power_state==4);}
    if(scenario==5){CHECK(c.name[0]==0);CHECK(c.contact_handle==1025);}
    else CHECK(!strcmp(c.name,"FixtureName"));
    if(scenario==0){r=before;c=previous;CHECK(coh_ent_create(&r,4343,&c,&failure)==COH_STATE);same_reader(&r,&before);CHECK(!memcmp(&c,&previous,sizeof(c)));CHECK(failure.stage==COH_ENT_STAGE_IDENTITY);}
    for(size_t n=0;n<f.bits;n++){
        r=before;r.bits=n;CohRepReader save=r;c=previous;truncations++;
        CHECK(coh_ent_create(&r,4242,&c,&failure)!=COH_OK);same_reader(&r,&save);CHECK(!memcmp(&c,&previous,sizeof(c)));CHECK(failure.bit<=n);
    }
}
static void bad_create(Fixture f,unsigned mode,CohStatus expected){CohRepReader r=reader(f,mode),save=r;CohEntCreate c={0},old=c;CohEntFailure d={0};CHECK(coh_ent_create(&r,4242,&c,&d)==expected);same_reader(&r,&save);CHECK(!memcmp(&c,&old,sizeof(c)));CHECK(d.bit<=f.bits);}
static void orientation_sequence(Fixture *fs,unsigned mode,const float **expected,const unsigned int **expected_ids){
    CohEntOrientation q;coh_ent_orientation_init(&q);CohEntFailure d={0};const unsigned ids[]={10,12,11,12,20};
    for(unsigned i=0;i<5;i++){
        CohRepReader r=reader(fs[i],mode),original=r;CohEntOrientation prior=q;
        CHECK(coh_ent_orientation(&r,ids[i],&q,&d)==COH_OK);CHECK(r.cursor==fs[i].bits);
        for(unsigned j=0;j<4;j++)CHECK(fabsf(q.quaternion[j]-expected[i][j])<0.000002f);
        for(unsigned j=0;j<3;j++)CHECK(q.packet_ids[j]==expected_ids[i][j]);
        for(size_t n=0;n<fs[i].bits;n++){
            r=original;r.bits=n;CohRepReader oldr=r;CohEntOrientation old=prior;truncations++;
            CHECK(coh_ent_orientation(&r,ids[i],&old,&d)!=COH_OK);same_reader(&r,&oldr);CHECK(!memcmp(&old,&prior,sizeof(old)));CHECK(d.bit<=n);
        }
    }
}
static void record_case(Fixture f,unsigned mode,unsigned medium){
    CohRepReader r=reader(f,mode),start=r;CohEntSlot slot;CohEntRecord record={0};CohEntFailure failure={0};
    coh_ent_slot_init(&slot,4);CohEntSlot empty=slot;CohEntRecord old=record;
    CHECK(coh_ent_record(&r,4242,10,2,&slot,&record,&failure)==COH_OK);CHECK(r.cursor==f.bits);CHECK(record.end_bit==f.bits);
    CHECK(slot.present&&slot.create_packet==10&&slot.identity.entity_id==91);CHECK(slot.position.valid);
    CHECK(slot.position.position.x==12.5f&&slot.position.position.y==-6.25f&&slot.position.position.z==128.f);
    CHECK(fabsf(slot.orientation.quaternion[1]-0.70710678f)<0.000002f);CHECK(slot.orientation.valid==7);
    if(medium){CHECK(slot.state_mode==1);CHECK(slot.sequence_index==33&&slot.sequence_ticks==4&&slot.sequence_bits==3);CHECK(record.trigger_count==1&&record.triggers[0].index==42&&record.triggers[0].fx_id==1000);CHECK(record.ragdoll_bones==1);}
    for(size_t n=0;n<f.bits;n++){
        r=start;r.bits=n;CohRepReader oldr=r;CohEntSlot copy=empty;record=old;truncations++;
        CHECK(coh_ent_record(&r,4242,10,2,&copy,&record,&failure)!=COH_OK);same_reader(&r,&oldr);CHECK(!memcmp(&copy,&empty,sizeof(copy)));CHECK(!memcmp(&record,&old,sizeof(old)));CHECK(failure.bit<=n);
    }
}
static void bad_record(Fixture f,unsigned mode,CohEntStage stage){
    CohRepReader r=reader(f,mode),oldr=r;CohEntSlot s;coh_ent_slot_init(&s,4);s.present=1;s.create_packet=1;s.identity.entity_id=91;s.identity.type=1;
    CohEntSlot old=s;CohEntRecord rec={0},oldrec=rec;CohEntFailure d={0};
    CHECK(coh_ent_record(&r,4242,10,2,&s,&rec,&d)==COH_UNSUPPORTED);CHECK(d.stage==stage);CHECK(d.bit<=f.bits);same_reader(&r,&oldr);CHECK(!memcmp(&s,&old,sizeof(s)));CHECK(!memcmp(&rec,&oldrec,sizeof(rec)));
}
static void update_case(Fixture f,unsigned mode){
    CohRepReader r=reader(f,mode),oldr=r;CohEntSlot s;coh_ent_slot_init(&s,4);CohEntRecord rec={0};CohEntFailure d;
    CHECK(coh_ent_record(&r,4242,20,2,&s,&rec,&d)==COH_STATE);same_reader(&r,&oldr);
    s.present=1;s.create_packet=10;s.identity.type=1;s.identity.entity_id=91;
    CHECK(coh_ent_record(&r,4242,20,2,&s,&rec,&d)==COH_OK);CHECK(r.cursor==f.bits);CHECK(s.position.position.x==12.5f);
    r=oldr;CohEntSlot prev=s;CHECK(coh_ent_record(&r,4242,9,2,&s,&rec,&d)==COH_STATE);same_reader(&r,&oldr);CHECK(!memcmp(&s,&prev,sizeof(s)));
    s.identity.is_self=1;s.identity.dbid=4243;CHECK(coh_ent_record(&r,4242,20,2,&s,&rec,&d)==COH_STATE);same_reader(&r,&oldr);
}
static void deletes_case(Fixture f,unsigned mode){
    CohRepReader r=reader(f,mode),original=r;CohEntDeletes d={0},old=d;CohEntFailure failure;
    CHECK(coh_ent_deletes(&r,&d,&failure)==COH_OK);CHECK(d.count==2&&d.entries[0].index==4&&d.entries[1].index==7);CHECK(r.cursor==f.bits);
    CohEntSlot slots[2];coh_ent_slot_init(&slots[0],4);coh_ent_slot_init(&slots[1],7);
    slots[0].present=slots[1].present=1;slots[0].create_packet=10;slots[1].create_packet=30;
    CHECK(coh_ent_stage_deletes(slots,2,&d,20)==COH_OK);CHECK(!slots[0].present&&slots[1].present);CHECK(slots[0].delete_packet==20&&slots[1].delete_packet==20);
    CHECK(coh_ent_stage_deletes(slots,2,&d,15)==COH_OK);CHECK(slots[0].delete_packet==20&&slots[1].delete_packet==20);
    CHECK(coh_ent_stage_deletes(slots,2,&d,30)==COH_OK);CHECK(slots[1].present);
    CHECK(coh_ent_stage_deletes(slots,2,&d,31)==COH_OK);CHECK(!slots[1].present);
    CohEntSlot saved[2];memcpy(saved,slots,sizeof(slots));CohEntDeletes bad=d;bad.entries[1].index=9;
    CHECK(coh_ent_stage_deletes(slots,2,&bad,100)==COH_NOT_FOUND);CHECK(!memcmp(saved,slots,sizeof(slots)));
    bad=d;bad.entries[1].index=4;CHECK(coh_ent_stage_deletes(slots,2,&bad,100)==COH_INVALID);CHECK(!memcmp(saved,slots,sizeof(slots)));
    for(size_t n=0;n<f.bits;n++){r=original;r.bits=n;CohRepReader oldr=r;CohEntDeletes copy=old;truncations++;CHECK(coh_ent_deletes(&r,&copy,&failure)!=COH_OK);same_reader(&r,&oldr);CHECK(!memcmp(&copy,&old,sizeof(old)));CHECK(failure.bit<=n);}
}
static void delete_bad(Fixture f,unsigned mode,CohStatus expected){CohRepReader r=reader(f,mode),oldr=r;CohEntDeletes d={0},old=d;CohEntFailure err;CHECK(coh_ent_deletes(&r,&d,&err)==expected);same_reader(&r,&oldr);CHECK(!memcmp(&d,&old,sizeof(d)));CHECK(err.bit<=f.bits);}
static CohEntListWorkspace list_workspace;
static unsigned list_checks,list_truncations;
static void list_slots(CohEntSlot *slots){
    const uint32_t indices[]={4,7,9,COH_ENT_INDEX_MAX};
    for(unsigned i=0;i<4;i++)coh_ent_slot_init(&slots[i],indices[i]);
}
static void list_case(Fixture f,unsigned mode,unsigned expected_count,unsigned kind){
    CohRepReader r=reader(f,mode),start=r;CohEntSlot slots[4],initial[4];CohEntList result,old;CohEntFailure d;
    unsigned self=kind==1;
    list_slots(slots);if(kind==2)slots[0].index=6;
    memcpy(initial,slots,sizeof(slots));memset(&result,0xa5,sizeof(result));old=result;
    CHECK(coh_ent_list(&r,4242,10,2,slots,4,&list_workspace,&result,&d)==COH_OK);list_checks++;
    CHECK(result.count==expected_count&&result.end_bit==f.bits&&r.cursor==f.bits);
    CHECK(result.self_index==(self?4u:0u));CHECK(result.self_dbid==(self?4242u:0u));
    CHECK(!self||result.self_entity_id==slots[0].identity.entity_id);
    unsigned present=0;for(unsigned i=0;i<4;i++){
        if(slots[i].present){present++;CHECK(slots[i].create_packet==10);CHECK(slots[i].position.valid);}
    }
    CHECK(present==expected_count);
    for(size_t n=0;n<f.bits;n++){
        r=start;r.bits=n;CohRepReader oldr=r;memcpy(slots,initial,sizeof(slots));result=old;truncations++;list_truncations++;
        CHECK(coh_ent_list(&r,4242,10,2,slots,4,&list_workspace,&result,&d)!=COH_OK);
        same_reader(&r,&oldr);CHECK(!memcmp(slots,initial,sizeof(slots)));CHECK(!memcmp(&result,&old,sizeof(old)));CHECK(d.bit<=n);
    }
    /* A list boundary must leave later control/character/global bits untouched. */
    unsigned char extended[4096];CHECK((f.bits+7)/8+1<=sizeof(extended));memset(extended,0xa5,sizeof(extended));memcpy(extended,f.data,(f.bits+7)/8);
    CHECK(coh_rep_reader(&r,(CohBytes){extended,sizeof(extended)},f.bits+8,(int)mode)==COH_OK);
    memcpy(slots,initial,sizeof(slots));CHECK(coh_ent_list(&r,4242,10,2,slots,4,&list_workspace,&result,NULL)==COH_OK);
    CHECK(r.cursor==f.bits);CohRepReader tail=r;CHECK(coh_ent_full_update_tail(&r,&d)==COH_UNSUPPORTED);same_reader(&r,&tail);
}
static void list_bad(Fixture f,unsigned mode,CohStatus expected,CohEntStage stage){
    CohRepReader r=reader(f,mode),oldr=r;CohEntSlot slots[4],oldslots[4];CohEntList result,old;CohEntFailure d;
    size_t count=expected==COH_NOT_FOUND?1u:4u;
    list_slots(slots);memcpy(oldslots,slots,sizeof(slots));memset(&result,0xa5,sizeof(result));old=result;
    CHECK(coh_ent_list(&r,4242,10,2,slots,count,&list_workspace,&result,&d)==expected);list_checks++;
    CHECK(d.stage==stage&&d.bit<=f.bits);same_reader(&r,&oldr);CHECK(!memcmp(slots,oldslots,sizeof(slots)));CHECK(!memcmp(&result,&old,sizeof(old)));
    /* The diagnostic pointer is optional; failure must still be transactional. */
    CHECK(coh_ent_list(&r,4242,10,2,slots,count,&list_workspace,&result,NULL)==expected);
    same_reader(&r,&oldr);CHECK(!memcmp(slots,oldslots,sizeof(slots)));CHECK(!memcmp(&result,&old,sizeof(old)));
}
static void seed_self(CohEntSlot *s,uint32_t entity_id){s->present=1;s->create_packet=1;s->identity.type=2;s->identity.is_self=1;s->identity.dbid=4242;s->identity.entity_id=entity_id;}
static void list_seeded_cases(Fixture update,Fixture creates,unsigned mode){
    CohRepReader r=reader(update,mode),start=r;CohEntSlot slots[4],oldslots[4];CohEntList result={0},old=result;CohEntFailure d;
    list_slots(slots);slots[0].present=1;slots[0].create_packet=10;slots[0].identity.type=1;slots[0].identity.entity_id=91;
    seed_self(&slots[2],93);CohEntSlot untouched=slots[2];
    CHECK(coh_ent_list(&r,4242,20,2,slots,4,&list_workspace,&result,&d)==COH_OK);list_checks++;
    CHECK(result.count==1&&result.self_index==9&&r.cursor==update.bits);CHECK(!memcmp(&slots[2],&untouched,sizeof(untouched)));
    r=start;slots[0].create_packet=30;memcpy(oldslots,slots,sizeof(slots));old=result;
    CHECK(coh_ent_list(&r,4242,20,2,slots,4,&list_workspace,&result,&d)==COH_STATE);list_checks++;
    CHECK(d.stage==COH_ENT_STAGE_IDENTITY);same_reader(&r,&start);CHECK(!memcmp(slots,oldslots,sizeof(slots)));CHECK(!memcmp(&result,&old,sizeof(old)));
    r=reader(creates,mode);start=r;list_slots(slots);slots[1].delete_packet=20;slots[1].deleted_entity_id=92;
    memcpy(oldslots,slots,sizeof(slots));old=result;
    CHECK(coh_ent_list(&r,4242,10,2,slots,4,&list_workspace,&result,&d)==COH_STATE);list_checks++;
    CHECK(d.stage==COH_ENT_STAGE_IDENTITY);same_reader(&r,&start);CHECK(!memcmp(slots,oldslots,sizeof(slots)));CHECK(!memcmp(&result,&old,sizeof(old)));
    /* An existing self slot need not be mentioned by this entity-list fragment. */
    r=start;list_slots(slots);seed_self(&slots[2],93);untouched=slots[2];
    CHECK(coh_ent_list(&r,4242,21,2,slots,4,&list_workspace,&result,&d)==COH_OK);list_checks++;
    CHECK(result.count==2&&result.self_index==9);CHECK(!memcmp(&slots[2],&untouched,sizeof(untouched)));
}
static void ownership_cases(Fixture empty,unsigned mode){
    CohRepReader r=reader(empty,mode),start=r;CohEntSlot slots[4],oldslots[4];CohEntList result={0},old=result;CohEntFailure d;
    list_slots(slots);seed_self(&slots[0],91);
    CHECK(coh_ent_list(&r,4242,10,2,slots,4,&list_workspace,&result,&d)==COH_OK);
    CHECK(result.count==0&&result.self_index==4&&result.self_entity_id==91&&result.self_dbid==4242);list_checks++;
    for(unsigned kind=0;kind<8;kind++){
        r=start;list_slots(slots);seed_self(&slots[0],91);
        CohStatus expected=COH_STATE;
        if(kind==0)seed_self(&slots[1],92);
        if(kind==1){seed_self(&slots[1],92);slots[1].identity.is_self=0;}
        if(kind==2)slots[0].identity.dbid=4243;
        if(kind==3)slots[0].identity.type=1;
        if(kind==4){slots[0].identity.is_self=2;expected=COH_INVALID;}
        if(kind==5){slots[1].index=4;expected=COH_INVALID;}
        if(kind==6){slots[1].orientation.quaternion[0]=NAN;expected=COH_INVALID;}
        if(kind==7){slots[0].identity.dbid=0;expected=COH_INVALID;}
        memcpy(oldslots,slots,sizeof(slots));result=old;
        CHECK(coh_ent_list(&r,4242,10,2,slots,4,&list_workspace,&result,&d)==expected);list_checks++;
        CHECK(d.stage==COH_ENT_STAGE_OWNERSHIP&&d.bit==start.cursor);same_reader(&r,&start);CHECK(!memcmp(slots,oldslots,sizeof(slots)));CHECK(!memcmp(&result,&old,sizeof(old)));
    }
    r=start;CHECK(coh_ent_list(&r,4242,10,2,NULL,0,&list_workspace,&result,&d)==COH_OK);
    CHECK(result.count==0&&result.self_index==0&&r.cursor==empty.bits);
    r=start;CHECK(coh_ent_list(&r,4242,10,2,slots,COH_ENT_LIST_MAX+1,&list_workspace,&result,&d)==COH_INVALID);same_reader(&r,&start);
    CHECK(coh_ent_list(&r,4242,10,2,NULL,1,&list_workspace,&result,&d)==COH_INVALID);
    CHECK(coh_ent_list(&r,4242,10,2,NULL,0,NULL,&result,&d)==COH_INVALID);
    CHECK(coh_ent_list(&r,0,10,2,NULL,0,&list_workspace,&result,&d)==COH_INVALID);
}
static unsigned random_state=0x172391ac;
static unsigned rand32(void){random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;return random_state;}
static void fuzz(void){
    for(unsigned i=0;i<20000;i++){
        unsigned char data[192];for(unsigned j=0;j<sizeof(data);j++)data[j]=(unsigned char)rand32();
        unsigned mode=rand32()&1;size_t bits=rand32()%(sizeof(data)*8+1);CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){data,sizeof(data)},bits,(int)mode)==COH_OK);CohRepReader oldr=r;
        CohEntCreate c={0},oldc=c;CohEntFailure d;CohStatus status=coh_ent_create(&r,4242,&c,&d);randomized++;
        if(status!=COH_OK){same_reader(&r,&oldr);CHECK(!memcmp(&c,&oldc,sizeof(c)));CHECK(d.bit<=bits);}else CHECK(r.cursor<=bits);
        r=oldr;CohEntSlot slot;coh_ent_slot_init(&slot,4);slot.present=1;slot.create_packet=1;CohEntSlot oldslot=slot;CohEntRecord record={0},oldrec=record;
        status=coh_ent_record(&r,4242,100,2,&slot,&record,&d);
        if(status!=COH_OK){same_reader(&r,&oldr);CHECK(!memcmp(&slot,&oldslot,sizeof(slot)));CHECK(!memcmp(&record,&oldrec,sizeof(record)));CHECK(d.bit<=bits);}else CHECK(r.cursor<=bits);
        r=oldr;CohEntCharacterStats stats={0},oldstats=stats;status=coh_ent_character_stats(&r,100,i%2,&stats,&d);
        if(status!=COH_OK){same_reader(&r,&oldr);CHECK(!memcmp(&stats,&oldstats,sizeof(stats)));CHECK(d.bit<=bits);}else CHECK(r.cursor<=bits);
        r=oldr;CohEntNetFxList effects={0},oldeffects=effects;status=coh_ent_netfx(&r,&effects,&d);
        if(status!=COH_OK){same_reader(&r,&oldr);CHECK(!memcmp(&effects,&oldeffects,sizeof(effects)));CHECK(d.bit<=bits);}else CHECK(r.cursor<=bits);
        r=oldr;CohRepReader title_reader;memcpy(&title_reader,&r,sizeof(r));CohEntTitles titles={0},oldtitles;memcpy(&oldtitles,&titles,sizeof(titles));status=coh_ent_titles(&r,100,&titles,&d);
        if(status!=COH_OK){same_reader(&r,&title_reader);CHECK(!memcmp(&titles,&oldtitles,sizeof(titles)));CHECK(d.bit<=bits);}else CHECK(r.cursor<=bits);
        r=oldr;CohEntDeletes deletes={0},olddeletes=deletes;status=coh_ent_deletes(&r,&deletes,&d);
        if(status!=COH_OK){same_reader(&r,&oldr);CHECK(!memcmp(&deletes,&olddeletes,sizeof(deletes)));CHECK(d.bit<=bits);}else CHECK(r.cursor<=bits);
        r=oldr;CohEntSlot slots[4],previous[4];list_slots(slots);memcpy(previous,slots,sizeof(slots));CohEntList list={0},oldlist=list;
        status=coh_ent_list(&r,4242,100,2,slots,4,&list_workspace,&list,&d);
        if(status!=COH_OK){same_reader(&r,&oldr);CHECK(!memcmp(slots,previous,sizeof(slots)));CHECK(!memcmp(&list,&oldlist,sizeof(list)));CHECK(d.bit<=bits);}else CHECK(r.cursor<=bits&&list.count<=4&&list.self_index==0);
    }
}
static void delta_cases(Fixture f,Fixture overflow,Fixture zero,Fixture descending,unsigned mode){
    CohRepReader r=reader(f,mode);uint32_t idx=999;CohEntFailure failure;
    CHECK(coh_ent_next_index(&r,-1,&idx,&failure)==COH_OK);CHECK(idx==4);
    CHECK(coh_ent_next_index(&r,(int32_t)idx,&idx,&failure)==COH_OK);CHECK(idx==7);CHECK(r.cursor==f.bits);
    r=reader(overflow,mode);CohRepReader oldr=r;idx=999;
    CHECK(coh_ent_next_index(&r,7,&idx,&failure)==COH_LIMIT);CHECK(idx==999);same_reader(&r,&oldr);
    r=reader(zero,mode);CHECK(coh_ent_next_index(&r,-1,&idx,&failure)==COH_OK);CHECK(idx==0);
    r=reader(descending,mode);CHECK(coh_ent_next_index(&r,-1,&idx,&failure)==COH_OK);CHECK(idx==7);
    CHECK(coh_ent_next_index(&r,7,&idx,&failure)==COH_OK);CHECK(idx==4);
    CHECK(coh_ent_next_index(&r,4,&idx,&failure)==COH_OK);CHECK(idx==9&&r.cursor==descending.bits);
}
static void tombstone_cases(Fixture f,unsigned mode){
    CohRepReader r=reader(f,mode),oldr=r;CohEntSlot s;CohEntRecord rec;CohEntFailure d;
    coh_ent_slot_init(&s,4);s.delete_packet=20;s.deleted_entity_id=91;CohEntSlot old=s;
    CHECK(coh_ent_record(&r,4242,19,2,&s,&rec,&d)==COH_STATE);same_reader(&r,&oldr);CHECK(!memcmp(&s,&old,sizeof(s)));
    CHECK(coh_ent_record(&r,4242,21,2,&s,&rec,&d)==COH_OK);CHECK(s.present&&s.delete_packet==20&&s.create_packet==21);
    r=oldr;old=s;CHECK(coh_ent_record(&r,4242,21,2,&s,&rec,&d)==COH_STATE);same_reader(&r,&oldr);CHECK(!memcmp(&s,&old,sizeof(s)));
}
static void netfx_case(Fixture f,unsigned mode,const unsigned int *values,const float *positions){
    CohEntNetFxList s={0},old=s;CohEntFailure d;CohRepReader r=reader(f,mode),start=r;
    CHECK(coh_ent_netfx(&r,&s,&d)==COH_OK);CHECK(r.cursor==f.bits&&s.end_bit==f.bits&&s.count==values[0]);
    for(unsigned i=0;i<s.count;i++){
        const CohEntNetFx *fx=&s.entries[i];
        unsigned int fields[]={fx->command,fx->net_id,fx->pitch_to_target,fx->power_type_flags,fx->handle,fx->has_color_tint,fx->primary_color,fx->secondary_color,fx->client_timer,fx->trigger_fx,fx->power,fx->debris,fx->origin_type,fx->origin_entity,fx->bone_id,fx->target_type,fx->target_entity};
        for(unsigned j=0;j<17;j++)CHECK(fields[j]==values[1+i*17+j]);
        CHECK(fx->duration==positions[i*8]&&fx->radius==positions[i*8+1]);
        for(unsigned j=0;j<3;j++){CHECK(fx->origin_position[j]==positions[i*8+2+j]);CHECK(fx->target_position[j]==positions[i*8+5+j]);}
    }
    for(size_t n=0;n<f.bits;n++){r=start;r.bits=n;CohRepReader before=r;s=old;truncations++;CHECK(coh_ent_netfx(&r,&s,&d)!=COH_OK);same_reader(&r,&before);CHECK(!memcmp(&s,&old,sizeof(s)));CHECK(d.bit<=n);}
}
static void netfx_bad(Fixture f,unsigned mode,CohStatus expected){
    CohEntNetFxList s={0},old=s;CohEntFailure d;CohRepReader r=reader(f,mode),before=r;
    CHECK(coh_ent_netfx(&r,&s,&d)==expected);same_reader(&r,&before);CHECK(!memcmp(&s,&old,sizeof(s)));CHECK(d.stage==COH_ENT_STAGE_NETFX&&d.bit<=f.bits);
}
static void appearance_case(Fixture f,unsigned mode,unsigned type){
    CohEntAppearance s={0},old=s;CohEntFailure d;CohRepReader r=reader(f,mode),start=r;
    CHECK(coh_ent_appearance(&r,10,&s,&d)==COH_OK);CHECK(r.cursor==f.bits&&s.type==type&&s.translucency==44);
    if(type){CHECK(s.packet_id==10&&!strcmp(s.world_group,"FixtureWorldGroup"));if(type==3)CHECK(s.npc_index==12345&&s.costume_index==3);else CHECK(!strcmp(s.sequence_name,"FixtureSequence"));}
    CohEntAppearance saved=s;r=start;CHECK(coh_ent_appearance(&r,9,&s,&d)==COH_OK);CHECK(!memcmp(&s,&saved,sizeof(s)));
    for(size_t n=0;n<f.bits;n++){r=start;r.bits=n;CohRepReader before=r;s=old;truncations++;CHECK(coh_ent_appearance(&r,10,&s,&d)!=COH_OK);same_reader(&r,&before);CHECK(!memcmp(&s,&old,sizeof(s)));CHECK(d.bit<=n);}
}
static void appearance_update_case(Fixture first,Fixture update,unsigned mode){
    CohEntAppearance s={0};CohEntFailure d;CohRepReader r=reader(first,mode);
    CHECK(coh_ent_appearance(&r,10,&s,&d)==COH_OK);CohEntAppearance before=s;
    r=reader(update,mode);CohRepReader start=r;
    CHECK(coh_ent_appearance(&r,11,&s,&d)==COH_OK);CHECK(r.cursor==update.bits&&!strcmp(s.world_group,"FixtureWorldGroup")&&s.packet_id==11);
    r=start;CohEntAppearance newer=s;CHECK(coh_ent_appearance(&r,9,&s,&d)==COH_OK);CHECK(!memcmp(&newer,&s,sizeof(s)));
    for(size_t n=0;n<update.bits;n++){r=start;r.bits=n;CohRepReader oldr=r;s=before;truncations++;CHECK(coh_ent_appearance(&r,11,&s,&d)!=COH_OK);same_reader(&r,&oldr);CHECK(!memcmp(&s,&before,sizeof(s)));}
}
static void stats_case(Fixture f,unsigned mode,unsigned self,const float *expected,const float *received,const int *integers){
    CohEntCharacterStats s={0},old=s;CohEntFailure d;CohRepReader r=reader(f,mode),start=r;
    CHECK(coh_ent_character_stats(&r,10,self,&s,&d)==COH_OK);CHECK(r.cursor==f.bits);
    for(unsigned i=0;i<8;i++){CHECK(s.current[i]==received[i]);CHECK(s.maximum[i]==received[8+i]);}
    for(unsigned i=0;i<6;i++)CHECK(s.integers[i]==integers[i]);
    CHECK(s.current_valid==(self?255u:47u)&&s.maximum_valid==(self?127u:47u)&&s.integer_valid==(self?63u:3u));
    CHECK(s.current[0]==expected[0]&&s.current[2]==expected[1]&&s.current[5]==expected[2]);CHECK(s.integers[0]==12&&s.integers[1]==14);
    if(self){CHECK(s.current[6]==expected[3]&&s.current[7]==expected[4]);CHECK(s.integers[2]==123456&&s.integers[3]==-123&&s.integers[4]==1000&&s.integers[5]==7654321);}
    CohEntCharacterStats saved=s;r=start;CHECK(coh_ent_character_stats(&r,9,self,&s,&d)==COH_OK);CHECK(!memcmp(&s,&saved,sizeof(s)));
    /* Per-field ordering: one more recent leaf survives an otherwise newer
     * packet; unmentioned channels retain their independent ages. */
    s.current[0]=999;s.current_packets[0]=20;r=start;CHECK(coh_ent_character_stats(&r,11,self,&s,&d)==COH_OK);CHECK(s.current[0]==999&&s.current_packets[0]==20&&s.current_packets[2]==11);
    for(size_t n=0;n<f.bits;n++){r=start;r.bits=n;CohRepReader before=r;s=old;truncations++;CHECK(coh_ent_character_stats(&r,10,self,&s,&d)!=COH_OK);same_reader(&r,&before);CHECK(!memcmp(&s,&old,sizeof(s)));CHECK(d.bit<=n);}
}
static void stats_bad(Fixture f,unsigned mode,CohStatus expected){
    CohEntCharacterStats s={0},old=s;CohEntFailure d;CohRepReader r=reader(f,mode),before=r;
    CHECK(coh_ent_character_stats(&r,10,1,&s,&d)==expected);same_reader(&r,&before);CHECK(!memcmp(&s,&old,sizeof(s)));CHECK(d.stage==COH_ENT_STAGE_ATTRIBUTE_SCHEMA&&d.bit<=f.bits);
}
static void character_parts(Fixture targetf,Fixture statusf,Fixture inventoryf,unsigned mode){
    CohEntFailure d;CohRepReader r=reader(targetf,mode),start=r;
    CohEntTarget t={0},oldt=t;CHECK(coh_ent_target(&r,10,1,&t,&d)==COH_OK);CHECK(r.cursor==targetf.bits);
    CHECK(t.target==4&&t.assist==7&&t.taunter==9&&t.count==2&&t.placates[0]==0&&t.placates[1]==4);
    CohEntTarget saved=t;r=start;CHECK(coh_ent_target(&r,9,1,&t,&d)==COH_OK);CHECK(!memcmp(&t,&saved,sizeof(t)));
    for(size_t n=0;n<targetf.bits;n++){r=start;r.bits=n;CohRepReader before=r;t=oldt;truncations++;CHECK(coh_ent_target(&r,10,1,&t,&d)!=COH_OK);same_reader(&r,&before);CHECK(!memcmp(&t,&oldt,sizeof(t)));}
    CohEntStatusEffects status={0},olds=status;r=reader(statusf,mode);start=r;
    CHECK(coh_ent_status_effects(&r,10,&status,&d)==COH_OK);CHECK(r.cursor==statusf.bits);
    CHECK(status.effects==0x305&&status.vision_phases==3&&status.exclusive_vision_phase==7&&status.count==2);
    CHECK(!strcmp(status.descriptions[0],"Held")&&!strcmp(status.descriptions[1],"SyntheticStatus"));
    CohEntStatusEffects savedstatus=status;r=start;CHECK(coh_ent_status_effects(&r,9,&status,&d)==COH_OK);CHECK(!memcmp(&status,&savedstatus,sizeof(status)));
    for(size_t n=0;n<statusf.bits;n++){r=start;r.bits=n;CohRepReader before=r;status=olds;truncations++;CHECK(coh_ent_status_effects(&r,10,&status,&d)!=COH_OK);same_reader(&r,&before);CHECK(!memcmp(&status,&olds,sizeof(status)));}
    CohEntInventorySizes inv={0},oldinv=inv;r=reader(inventoryf,mode);start=r;
    CHECK(coh_ent_inventory_sizes(&r,&inv,&d)==COH_OK);CHECK(r.cursor==inventoryf.bits&&inv.valid&&inv.count==5);
    for(unsigned i=0;i<5;i++)CHECK(inv.total[i]==100+i&&inv.used[i]==50+i);
    CHECK(inv.auction_total==999&&inv.boost_total==70);
    for(size_t n=0;n<inventoryf.bits;n++){r=start;r.bits=n;CohRepReader before=r;inv=oldinv;truncations++;CHECK(coh_ent_inventory_sizes(&r,&inv,&d)!=COH_OK);same_reader(&r,&before);CHECK(!memcmp(&inv,&oldinv,sizeof(inv)));}
}
static void parts_bad(Fixture f,unsigned mode,unsigned kind,CohStatus expected){
    CohRepReader r=reader(f,mode),before=r;CohEntFailure d;CohStatus status;
    CohEntTarget t={0},oldt=t;CohEntStatusEffects s={0},olds=s;CohEntInventorySizes i={0},oldi=i;
    if(kind==0)status=coh_ent_target(&r,10,1,&t,&d);
    else if(kind==1)status=coh_ent_status_effects(&r,10,&s,&d);
    else status=coh_ent_inventory_sizes(&r,&i,&d);
    CHECK(status==expected);same_reader(&r,&before);CHECK(!memcmp(&t,&oldt,sizeof(t))&&!memcmp(&s,&olds,sizeof(s))&&!memcmp(&i,&oldi,sizeof(i)));CHECK(d.bit<=f.bits);
}
static void expanded_record(Fixture f,unsigned mode,unsigned type){
    CohRepReader r=reader(f,mode),start=r;CohEntSlot s;coh_ent_slot_init(&s,4);CohEntSlot empty=s;CohEntRecord rec={0},old=rec;CohEntFailure d;
    CHECK(coh_ent_record(&r,4242,10,2,&s,&rec,&d)==COH_OK);CHECK(r.cursor==f.bits);
    if(type==5||type==6){if(type==6)CHECK(rec.netfx.count==3&&rec.netfx.entries[0].client_timer==6&&rec.netfx.entries[1].trigger_fx==123);CHECK(s.stats.current[0]==123&&s.stats.current[2]==90&&s.stats.integers[0]==12&&s.stats.integers[1]==14);CHECK(rec.pchar_things&&s.combat_mod_shift==8);}
    else if(type){CHECK(s.appearance.type==type&&s.appearance.packet_id==10&&s.appearance.translucency==44);CHECK(!strcmp(s.appearance.world_group,"FixtureWorldGroup"));
        if(type==3)CHECK(s.appearance.npc_index==12345&&s.appearance.costume_index==3);
        else CHECK(!strcmp(s.appearance.sequence_name,"FixtureSequence"));
    }else{CHECK(rec.pchar_things&&s.combat_mod_shift==8&&s.status_effects.effects==0x305&&s.status_effects.count==2);}
    for(size_t n=0;n<f.bits;n++){r=start;r.bits=n;CohRepReader before=r;s=empty;rec=old;truncations++;CHECK(coh_ent_record(&r,4242,10,2,&s,&rec,&d)!=COH_OK);same_reader(&r,&before);CHECK(!memcmp(&s,&empty,sizeof(s))&&!memcmp(&rec,&old,sizeof(rec)));CHECK(d.bit<=n);}
}
#define RUN_MODE(m) do { \
    netfx_case(F(netfx_0_##m),m,netfx_0_##m##_values,netfx_0_##m##_positions);netfx_case(F(netfx_1_##m),m,netfx_1_##m##_values,netfx_1_##m##_positions);netfx_case(F(netfx_2_##m),m,netfx_2_##m##_values,netfx_2_##m##_positions); \
    netfx_bad(F(netfx_limit##m),m,COH_LIMIT);netfx_bad(F(netfx_zero_command##m),m,COH_INVALID);netfx_bad(F(netfx_zero_id##m),m,COH_INVALID);netfx_bad(F(netfx_nan##m),m,COH_INVALID); \
    netfx_bad(F(netfx_origin_type##m),m,COH_LIMIT);netfx_bad(F(netfx_bone_limit##m),m,COH_LIMIT);netfx_bad(F(netfx_target_limit##m),m,COH_LIMIT);netfx_bad(F(netfx_infinite_position##m),m,COH_INVALID); \
    expanded_record(F(source_record_3_##m),m,6); \
    stats_case(F(stats_0_##m),m,0,stats_0_##m##_expected,stats_0_##m##_received,stats_0_##m##_integers);stats_case(F(stats_1_##m),m,1,stats_1_##m##_expected,stats_1_##m##_received,stats_1_##m##_integers); \
    stats_bad(F(stats_unknown##m),m,COH_UNSUPPORTED);stats_bad(F(stats_duplicate##m),m,COH_INVALID);stats_bad(F(stats_relative##m),m,COH_UNSUPPORTED);stats_bad(F(stats_nested_unknown##m),m,COH_UNSUPPORTED); \
    appearance_update_case(F(appearance_0_##m),F(appearance_absent_group##m),m);appearance_update_case(F(appearance_0_##m),F(appearance_empty_group##m),m); \
    appearance_case(F(appearance_0_##m),m,3);appearance_case(F(appearance_1_##m),m,4);appearance_case(F(appearance_2_##m),m,0); \
    character_parts(F(target_0_##m),F(status##m),F(inventory_1_##m),m); \
    parts_bad(F(target_overflow##m),m,0,COH_LIMIT);parts_bad(F(target_limit##m),m,0,COH_LIMIT); \
    parts_bad(F(status_limit##m),m,1,COH_LIMIT);parts_bad(F(status_long##m),m,1,COH_LIMIT); \
    parts_bad(F(inventory_unknown##m),m,2,COH_UNSUPPORTED);parts_bad(F(inventory_invalid##m),m,2,COH_INVALID); \
    expanded_record(F(source_record_2_##m),m,5); \
    expanded_record(F(record_appearance_3_##m),m,3);expanded_record(F(record_appearance_4_##m),m,4);expanded_record(F(record_pchar##m),m,0); \
    delta_cases(F(delta_indices##m),F(delta_overflow##m),F(delta_zero##m),F(delta_descending##m),m);tombstone_cases(F(record_simple##m),m); \
    Fixture creates[]={F(create_0_##m),F(create_1_##m),F(create_2_##m),F(create_3_##m),F(create_4_##m),F(create_5_##m),F(create_6_##m)}; \
    for(unsigned i=0;i<7;i++)test_create(creates[i],m,i); \
    bad_create(F(create_7_##m),m,COH_STATE); \
    bad_create(F(bad_type##m),m,COH_UNSUPPORTED);bad_create(F(bad_id##m),m,COH_LIMIT);bad_create(F(long_name##m),m,COH_LIMIT); \
    Fixture orientations[]={F(orientation_0_##m),F(orientation_1_##m),F(orientation_2_##m),F(orientation_3_##m),F(orientation_4_##m)}; \
    const float *expected[]={orientation_0_##m##_expected,orientation_1_##m##_expected,orientation_2_##m##_expected,orientation_3_##m##_expected,orientation_4_##m##_expected}; \
    const unsigned int *ids[]={orientation_0_##m##_ids,orientation_1_##m##_ids,orientation_2_##m##_ids,orientation_3_##m##_ids,orientation_4_##m##_ids}; \
    orientation_sequence(orientations,m,expected,ids); \
    record_case(F(source_record_0_##m),m,0);record_case(F(source_record_1_##m),m,1);deletes_case(F(source_deletes##m),m); \
    record_case(F(record_simple##m),m,0);record_case(F(record_medium##m),m,1);update_case(F(record_update##m),m); \
    bad_record(F(unsupported_interp##m),m,COH_ENT_STAGE_INTERPOLATION);bad_record(F(unsupported_appearance##m),m,COH_ENT_STAGE_APPEARANCE);bad_record(F(unsupported_pchar##m),m,COH_ENT_STAGE_ATTRIBUTE_SCHEMA); \
    deletes_case(F(deletes##m),m);delete_bad(F(delete_zero##m),m,COH_LIMIT);delete_bad(F(delete_duplicate##m),m,COH_INVALID);delete_bad(F(delete_limit##m),m,COH_LIMIT); \
    CohRepReader dr=reader(F(delete_large_generation##m),m);CohEntDeletes dd;CHECK(coh_ent_deletes(&dr,&dd,NULL)==COH_OK);CHECK(dd.entries[0].entity_id==70001); \
    CohRepReader endr=reader(F(end##m),m);CohEntCreate endc;CHECK(coh_ent_create(&endr,4242,&endc,NULL)==COH_OK);CHECK(endc.end); \
    CohRepReader ur=reader(F(update_flag##m),m);CHECK(coh_ent_create(&ur,4242,&endc,NULL)==COH_OK);CHECK(!endc.create); \
    list_case(F(source_list_0_##m),m,2,0);list_case(F(source_list_1_##m),m,3,0);list_case(F(source_list_2_##m),m,1,0); \
    list_case(F(source_list_self_##m),m,2,1);ownership_cases(F(list_empty##m),m); \
    list_case(F(list_sentinel_collision##m),m,2,2); \
    list_seeded_cases(F(list_unknown_update##m),F(source_list_0_##m),m); \
    list_bad(F(source_list_duplicate_self_##m),m,COH_STATE,COH_ENT_STAGE_OWNERSHIP); \
    list_bad(F(list_end_nonzero_delta##m),m,COH_INVALID,COH_ENT_STAGE_LIST); \
    list_bad(F(list_duplicate_index##m),m,COH_INVALID,COH_ENT_STAGE_LIST); \
    list_bad(F(list_zero_normal##m),m,COH_LIMIT,COH_ENT_STAGE_LIST); \
    list_bad(F(list_unknown_update##m),m,COH_STATE,COH_ENT_STAGE_IDENTITY); \
    list_bad(F(list_capacity_missing##m),m,COH_NOT_FOUND,COH_ENT_STAGE_LIST); \
    list_bad(F(list_late_unsupported##m),m,COH_UNSUPPORTED,COH_ENT_STAGE_APPEARANCE); \
}while(0)
#include "test_titles.c.inc"
#include "test_rare.c.inc"
void costume_run_tests(unsigned *,unsigned *,unsigned *);
int main(void){
    costume_run_tests(&checks,&truncations,&randomized);
    RUN_MODE(0);RUN_MODE(1);titles_run_tests();rare_run_tests();fuzz();
    CohRepReader r=reader(F(end0),0),oldr=r;CohEntFailure d;
    CHECK(coh_ent_full_update_tail(&r,&d)==COH_UNSUPPORTED);CHECK(d.stage==COH_ENT_STAGE_FULL_UPDATE_TAIL&&d.bit==0);same_reader(&r,&oldr);
    CohEntSlot invalid;CohEntRecord rec;coh_ent_slot_init(&invalid,4);invalid.position.packed[0]=0x80000000u;
    CHECK(coh_ent_record(&r,4242,5,2,&invalid,&rec,&d)==COH_INVALID);same_reader(&r,&oldr);
    coh_ent_slot_init(&invalid,0);CHECK(coh_ent_record(&r,4242,5,2,&invalid,&rec,&d)==COH_OK);CHECK(rec.identity.end);
    CHECK(coh_ent_create(NULL,4242,NULL,NULL)==COH_INVALID);CHECK(coh_ent_deletes(NULL,NULL,NULL)==COH_INVALID);
    printf("{\"passed\":true,\"slot_bytes\":%zu,\"workspace_bytes\":%zu,\"record_bytes\":%zu,\"costume_bytes\":%zu,\"costume_workspace_bytes\":%zu,\"custom_costume_bytes\":%zu,\"costume_envelope_bytes\":%zu,\"costume_envelope_workspace_bytes\":%zu,\"power_custom_envelope_bytes\":%zu,\"power_custom_workspace_bytes\":%zu,\"checks\":%u,\"every_bit_truncations\":%u,\"randomized_cases\":%u,\"list_cases\":%u,\"list_every_bit_truncations\":%u,\"full_update_accepted\":false,\"render_spawn\":false}\n",sizeof(CohEntSlot),sizeof(CohEntListWorkspace),sizeof(CohEntRecord),sizeof(CohEntCostume),sizeof(CohEntCostumeWorkspace),sizeof(CohEntCustomCostume),sizeof(CohEntCostumeEnvelope),sizeof(CohEntCostumeEnvelopeWorkspace),sizeof(CohEntPowerCustomEnvelope),sizeof(CohEntPowerCustomWorkspace),checks,truncations,randomized,list_checks,list_truncations);
    return 0;
}
