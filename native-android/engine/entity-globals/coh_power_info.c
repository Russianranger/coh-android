#include "coh_power_info.h"
#include <float.h>
#include <math.h>
#include <string.h>
typedef char power_info_float32[(sizeof(float)==4&&FLT_RADIX==2&&FLT_MANT_DIG==24&&FLT_MAX_EXP==128)?1:-1];
#define CALL(x) do{CohStatus status_=(x);if(status_!=COH_OK)return status_;}while(0)
#define PACK(n,x) CALL(coh_rep_pack(r,(n),&(x)))
static CohStatus bit(CohRepReader*r,uint32_t*v){CALL(coh_rep_read(r,1,v));return *v<=1?COH_OK:COH_INVALID;}
static CohStatus automatic(CohRepReader*r,uint32_t*v){
    static const unsigned widths[]={2,10,24,32};uint32_t b;
    CALL(coh_rep_read(r,2,&b));if(b>3)return COH_INVALID;
    CALL(coh_rep_read(r,widths[b],v));
    return widths[b]==32||*v<(1u<<widths[b])?COH_OK:COH_INVALID;
}
static CohStatus number(CohRepReader*r,float*v){uint32_t u;CALL(coh_rep_read(r,32,&u));memcpy(v,&u,4);return isfinite(*v)?COH_OK:COH_INVALID;}
static CohStatus reference(CohRepReader*r,CohPowerRef*v){CALL(automatic(r,&v->build));PACK(2,v->set);PACK(1,v->power);return COH_OK;}
static CohStatus count(CohRepReader*r,unsigned width,uint32_t*v,uint32_t max){CALL(coh_rep_pack(r,width,v));return *v<=max?COH_OK:COH_LIMIT;}
static CohStatus boost(CohRepReader*r,CohPowerInfoUpdate*v){
    if(v->boost_count==COH_POWER_INFO_BOOSTS)return COH_LIMIT;
    CohCharacterBoost*b=&v->boosts[v->boost_count++];CALL(bit(r,&b->present));if(!b->present)return COH_OK;
    CALL(automatic(r,&b->power_crc));PACK(5,b->level);PACK(2,b->combines);
    for(unsigned i=0;i<4;i++)CALL(number(r,&b->variables[i]));
    CALL(count(r,1,&b->powerup_count,10));
    for(unsigned i=0;i<b->powerup_count;i++){PACK(1,b->powerups[i].type);PACK(5,b->powerups[i].id);PACK(1,b->powerups[i].filled);}
    return COH_OK;
}
static CohStatus ranges(CohRepReader*r,CohPowerInfoUpdate*v){
    uint32_t more;for(;;){CALL(bit(r,&more));if(!more)return COH_OK;
        if(v->range_count==COH_POWER_INFO_EVENTS)return COH_LIMIT;
        CohPowerRange*p=&v->ranges[v->range_count++];CALL(automatic(r,&p->crc));CALL(number(r,&p->range));}
}
static CohStatus statuses(CohRepReader*r,CohPowerStatus*out,uint32_t*n,unsigned kind){
    CALL(count(r,kind==3?1:4,n,COH_POWER_INFO_EVENTS));
    for(uint32_t i=0;i<*n;i++){
        CohPowerStatus*p=&out[i];CALL(bit(r,&p->present));if(!p->present)continue;
        CALL(reference(r,&p->ref));
        if(kind==0){PACK(1,p->value);}
        else if(kind==1){CALL(automatic(r,&p->value));CALL(automatic(r,&p->disabled_manually));}
        else if(kind==2){PACK(3,p->charges);CALL(number(r,&p->usage_time));CALL(number(r,&p->available_time));}
        else CALL(number(r,&p->timer));
    }return COH_OK;
}
static CohStatus body(CohRepReader*r,CohPowerInfoUpdate*v){
    v->begin_bit=r->cursor;CALL(bit(r,&v->has_updates));
    if(!v->has_updates){CALL(ranges(r,v));v->end_bit=r->cursor;return COH_OK;}
    CALL(coh_rep_read(r,4,&v->current_build));if(v->current_build>=COH_CHARACTER_BUILDS)return COH_INVALID;
    CALL(bit(r,&v->redefine));if(v->redefine){CALL(bit(r,&v->default_present));if(v->default_present)CALL(automatic(r,&v->default_crc));}
    CALL(count(r,1,&v->definition_count,COH_POWER_INFO_DEFINITIONS));
    for(uint32_t i=0;i<v->definition_count;i++){
        CohPowerDefinition*p=&v->definitions[i];CALL(reference(r,&p->ref));CALL(bit(r,&p->present));if(!p->present)continue;
        CALL(automatic(r,&p->crc));PACK(5,p->set_level);PACK(5,p->level);PACK(3,p->charges);
        CALL(number(r,&p->usage_time));CALL(number(r,&p->available_time));PACK(24,p->creation_time);
        CALL(automatic(r,&p->enabled));CALL(automatic(r,&p->disabled_manually));CALL(automatic(r,&p->unique_id));
        CALL(count(r,4,&p->boost_count,COH_POWER_INFO_BOOSTS-v->boost_count));p->boost_first=v->boost_count;
        for(uint32_t j=0;j<p->boost_count;j++)CALL(boost(r,v));
        CALL(automatic(r,&p->global_count));if(p->global_count>COH_POWER_INFO_BOOSTS-v->boost_count)return COH_LIMIT;
        p->global_first=v->boost_count;for(uint32_t j=0;j<p->global_count;j++)CALL(boost(r,v));
    }
    CALL(ranges(r,v));CALL(statuses(r,v->active,&v->active_count,0));CALL(statuses(r,v->enabled,&v->enabled_count,1));
    CALL(statuses(r,v->usage,&v->usage_count,2));CALL(statuses(r,v->recharge,&v->recharge_count,3));
    uint32_t present;CALL(bit(r,&present));if(present)CALL(count(r,4,&v->inspiration_count,COH_POWER_INFO_EVENTS));
    for(uint32_t i=0;i<v->inspiration_count;i++){
        CohPowerInspiration*p=&v->inspirations[i];PACK(3,p->column);PACK(3,p->row);
        if(p->column>=5||p->row>=4)return COH_INVALID;
        CALL(bit(r,&p->present));if(p->present)CALL(automatic(r,&p->crc));
    }
    CALL(count(r,1,&v->inventory_boost_count,COH_POWER_INFO_EVENTS));
    for(uint32_t i=0;i<v->inventory_boost_count;i++){
        CohPowerInventoryBoost*p=&v->inventory_boosts[i];PACK(3,p->slot);if(p->slot>=COH_CHARACTER_BOOST_SLOTS)return COH_INVALID;
        p->boost=v->boost_count;CALL(boost(r,v));
    }
    v->end_bit=r->cursor;return COH_OK;
}
static int overlap(const void*a,size_t an,const void*b,size_t bn){
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 0;
    if(an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
    return x<y+bn&&y<x+an;
}
CohStatus coh_global_power_info(CohRepReader*reader,CohPowerInfoUpdate*out,CohPowerInfoWorkspace*work,size_t retained,size_t limit){
    if(!reader||!out||!work||!limit||limit>COH_POWER_INFO_LIMIT)return COH_INVALID;
    const void*objects[]={reader,out,work,reader->bytes.data};
    size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*work),reader->bytes.size};
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
    CohRepReader r=*reader;uint32_t ignored;CALL(coh_rep_read(&r,0,&ignored));
    size_t fixed=sizeof(*out)+sizeof(*work)+8192u;
    if(fixed>limit||r.bytes.size>limit-fixed||retained>limit-fixed-r.bytes.size)return COH_LIMIT;
    memset(work,0,sizeof(*work));CALL(body(&r,&work->candidate));memcpy(out,&work->candidate,sizeof(*out));*reader=r;return COH_OK;
}
