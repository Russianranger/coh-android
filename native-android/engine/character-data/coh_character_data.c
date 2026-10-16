#include "coh_character_data.h"
#include <float.h>
#include <math.h>
#include <string.h>
typedef char character_float32[(sizeof(float)==4&&FLT_RADIX==2&&FLT_MANT_DIG==24&&FLT_MAX_EXP==128)?1:-1];
#define CALL(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
#define PACK(n,v) CALL(coh_rep_pack(r,(n),&(v)))
static CohStatus scalar(CohRepReader*r,unsigned bits,uint32_t*v){CALL(coh_rep_read(r,bits,v));if(bits<32&&*v>=(1u<<bits))return COH_INVALID;return COH_OK;}
static CohStatus automatic(CohRepReader*r,uint32_t*v){static const unsigned widths[]={2,10,24,32};uint32_t bin;CALL(scalar(r,2,&bin));return scalar(r,widths[bin],v);}
static CohStatus number(CohRepReader*r,float*v){uint32_t u;CALL(scalar(r,32,&u));memcpy(v,&u,4);return isfinite(*v)?COH_OK:COH_INVALID;}
static CohStatus power_ref(CohRepReader*r,uint32_t*v){CALL(automatic(r,v));return *v?COH_OK:COH_INVALID;}
static CohStatus boost(CohRepReader*r,CohCharacterData*v,uint32_t*index,CohCharacterStage*stage){
    *stage=COH_CHARACTER_BOOST;
    if(v->boost_count==COH_CHARACTER_BOOSTS_MAX)return COH_LIMIT;
    *index=v->boost_count++;CohCharacterBoost*b=&v->boosts[*index];
    CALL(scalar(r,1,&b->present));if(!b->present)return COH_OK;
    CALL(power_ref(r,&b->power_crc));PACK(5,b->level);PACK(2,b->combines);
    for(unsigned i=0;i<4;i++)CALL(number(r,&b->variables[i]));
    PACK(1,b->powerup_count);if(b->powerup_count>10)return COH_LIMIT;
    for(unsigned i=0;i<b->powerup_count;i++){
        PACK(1,b->powerups[i].type);PACK(5,b->powerups[i].id);PACK(1,b->powerups[i].filled);
        if(b->powerups[i].type>=11||b->powerups[i].filled>1)return COH_INVALID;
    }
    return COH_OK;
}
static CohStatus powers(CohRepReader*r,CohCharacterData*v,CohCharacterStage*stage){
    uint32_t wire_build;*stage=COH_CHARACTER_POWERS;CALL(scalar(r,1,&v->multiple_builds));
    if(v->multiple_builds!=v->profile.player)return COH_STATE;
    v->build_count=v->multiple_builds?8:1;
    if(v->multiple_builds){
        CALL(scalar(r,4,&v->active_build));if(v->active_build>=8)return COH_INVALID;
        for(unsigned i=0;i<8;i++)CALL(scalar(r,6,&v->builds[i].level));
    }
    for(unsigned i=0;i<v->build_count;i++){
        *stage=COH_CHARACTER_POWERS;
        if(v->multiple_builds){CALL(scalar(r,4,&wire_build));if(wire_build!=i)return COH_INVALID;}
        CohCharacterBuild*b=&v->builds[i];PACK(4,b->total_sets);
        uint32_t first=i?v->profile.shared_set_count:0;
        if(b->total_sets<first)return COH_INVALID;
        if(b->total_sets>COH_CHARACTER_SETS_MAX||b->total_sets-first>COH_CHARACTER_SETS_MAX-v->set_count)return COH_LIMIT;
        if(i&&v->builds[0].total_sets<first)return COH_INVALID;
        b->set_first=v->set_count;b->set_count=b->total_sets-first;
        for(uint32_t j=first;j<b->total_sets;j++){
            *stage=COH_CHARACTER_POWERS;CohCharacterSet*s=&v->sets[v->set_count++];s->build=i;s->index=j;
            PACK(5,s->level);PACK(4,s->power_count);s->power_first=v->power_count;
            if(s->power_count>COH_CHARACTER_POWERS_MAX-v->power_count)return COH_LIMIT;
            if(!s->power_count){CALL(power_ref(r,&s->empty_root_crc));continue;}
            for(unsigned k=0;k<s->power_count;k++){
                *stage=COH_CHARACTER_POWERS;CohCharacterPower*p=&v->powers[v->power_count++];
                CALL(power_ref(r,&p->power_crc));PACK(5,p->level);CALL(number(r,&p->range));PACK(3,p->charges);
                CALL(number(r,&p->usage_time));CALL(number(r,&p->available_time));PACK(24,p->creation_time);
                CALL(automatic(r,&p->enabled));CALL(automatic(r,&p->disabled_manually));CALL(automatic(r,&p->unique_id));
                if(p->enabled>1||p->disabled_manually>1)return COH_INVALID;
                PACK(4,p->boost_count);if(p->boost_count>COH_CHARACTER_BOOSTS_MAX-v->boost_count)return COH_LIMIT;
                p->boost_first=v->boost_count;
                for(unsigned z=0;z<p->boost_count;z++){uint32_t index;CALL(boost(r,v,&index,stage));}
                *stage=COH_CHARACTER_POWERS;CALL(automatic(r,&p->global_count));
                if(p->global_count>COH_CHARACTER_BOOSTS_MAX-v->boost_count)return COH_LIMIT;
                p->global_first=v->boost_count;
                for(unsigned z=0;z<p->global_count;z++){uint32_t index;CALL(boost(r,v,&index,stage));}
            }
        }
    }
    *stage=COH_CHARACTER_POWERS;
    if(v->multiple_builds){CALL(scalar(r,4,&wire_build));if(wire_build!=v->active_build)return COH_INVALID;}
    return COH_OK;
}
static CohStatus body(CohRepReader*r,CohCharacterData*v,CohCharacterStage*stage){
    *stage=COH_CHARACTER_IDENTITY;
    CALL(coh_rep_string(r,v->class_name,sizeof(v->class_name)));CALL(coh_rep_string(r,v->origin_name,sizeof(v->origin_name)));
    if(!v->class_name[0]||!v->origin_name[0])return COH_INVALID;
    PACK(5,v->level);CALL(automatic(r,&v->combat_mod_shift));PACK(4,v->current_build);CALL(automatic(r,&v->location));
    if(v->current_build>=8||v->location>1)return COH_INVALID;
    CALL(powers(r,v,stage));
    *stage=COH_CHARACTER_INSPIRATIONS;PACK(3,v->inspiration_columns);PACK(3,v->inspiration_rows);
    if(v->inspiration_columns>5||v->inspiration_rows>4)return COH_LIMIT;
    for(unsigned x=0;x<v->inspiration_columns;x++)for(unsigned y=0;y<v->inspiration_rows;y++){
        uint32_t present;CALL(scalar(r,1,&present));if(present)CALL(power_ref(r,&v->inspirations[x][y]));
    }
    *stage=COH_CHARACTER_BOOST_INVENTORY;uint32_t count,index;PACK(5,count);
    if(count!=COH_CHARACTER_BOOST_SLOTS)return COH_UNSUPPORTED;
    for(unsigned i=0;i<count;i++){
        *stage=COH_CHARACTER_BOOST_INVENTORY;PACK(3,index);if(index!=i)return COH_INVALID;
        CALL(boost(r,v,&v->boost_inventory[i],stage));
    }
    *stage=COH_CHARACTER_INVENTORIES;PACK(3,count);if(count!=5)return COH_UNSUPPORTED;
    for(unsigned i=0;i<5;i++){
        CohCharacterInventory*inventory=&v->inventories[i];PACK(8,inventory->total);PACK(8,inventory->count);
        if(inventory->count>COH_CHARACTER_INVENTORY_MAX-v->inventory_count)return COH_LIMIT;
        inventory->first=v->inventory_count;
        for(unsigned j=0;j<inventory->count;j++){
            CohCharacterInventoryItem*item=&v->items[v->inventory_count++];
            PACK(5,item->type);PACK(5,item->index);PACK(5,item->amount);PACK(5,item->id);
            if(item->type!=i||item->index!=j)return COH_INVALID;
            if(i==1)for(unsigned k=0;k<4;k++)CALL(number(r,&item->variables[k]));
        }
    }
    PACK(8,v->auction_slots);v->end_bit=r->cursor;return COH_OK;
}
static int overlaps(const void*a,size_t as,const void*b,size_t bs){
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    if(x>UINTPTR_MAX-as||y>UINTPTR_MAX-bs)return 1;
    return x<y+bs&&y<x+as;
}
CohStatus coh_character_data_read(CohRepReader*r,const CohCharacterWireProfile*profile,
    CohCharacterWorkspace*workspace,CohCharacterData*out,size_t budget,size_t retained,CohCharacterFailure*failure){
    CohCharacterStage stage=COH_CHARACTER_PROFILE;CohStatus result=COH_INVALID;
    if(!r||!profile||!workspace||!out)return COH_INVALID;
    /* Reject mutable-control aliases before reading input metadata, touching
     * scratch or writing a diagnostic. An aliased failure cannot be updated. */
    if(overlaps(workspace,sizeof(*workspace),out,sizeof(*out))||
       overlaps(r,sizeof(*r),workspace,sizeof(*workspace))||
       overlaps(r,sizeof(*r),out,sizeof(*out))||
       overlaps(r,sizeof(*r),profile,sizeof(*profile))||
       (failure&&(overlaps(failure,sizeof(*failure),r,sizeof(*r))||
                  overlaps(failure,sizeof(*failure),workspace,sizeof(*workspace))||
                  overlaps(failure,sizeof(*failure),out,sizeof(*out))||
                  overlaps(failure,sizeof(*failure),profile,sizeof(*profile)))))return COH_INVALID;
    if(overlaps(workspace,sizeof(*workspace),r->bytes.data,r->bytes.size)||
       overlaps(out,sizeof(*out),r->bytes.data,r->bytes.size)||
       overlaps(r,sizeof(*r),r->bytes.data,r->bytes.size)||
       (failure&&overlaps(failure,sizeof(*failure),r->bytes.data,r->bytes.size)))return COH_INVALID;
    uint8_t hash=0;for(unsigned i=0;i<32;i++)hash|=profile->source_profile_sha256[i];
    if(!profile->generation||profile->shared_set_count_bound!=1||!hash||profile->player>1||profile->shared_set_count>COH_CHARACTER_SETS_MAX){result=COH_STATE;goto fail;}
    if(budget>COH_CHARACTER_RAM_MAX||retained>budget||2*sizeof(*out)>budget-retained||r->bytes.size>budget-retained-2*sizeof(*out)){result=COH_LIMIT;goto fail;}
    CohRepReader copy=*r;CohCharacterWireProfile profile_copy=*profile;
    memset(workspace,0,sizeof(*workspace));workspace->candidate.profile=profile_copy;
    result=body(&copy,&workspace->candidate,&stage);
    if(failure)*failure=(CohCharacterFailure){result,stage,copy.cursor};
    if(result!=COH_OK)return result;
    memcpy(out,&workspace->candidate,sizeof(*out));*r=copy;return COH_OK;
fail:
    if(failure)*failure=(CohCharacterFailure){result,stage,r->cursor};
    return result;
}
