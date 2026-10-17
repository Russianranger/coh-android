#include "coh_very_rare_tail.h"
#include <math.h>
#include <string.h>

typedef struct { CohRepReader reader; CohStatus status; CohEntVeryRareTail *out; } TailReader;
static int overlaps(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(!an||!bn)return 0;
    if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;
    return aa<bb+bn&&bb<aa+an;
}
static uint32_t scalar(TailReader *p,unsigned width) {
    uint32_t value=0;
    if(p->status==COH_OK)p->status=coh_rep_read(&p->reader,width,&value);
    if(p->status==COH_OK&&width<32&&value>=(UINT32_C(1)<<width))p->status=COH_INVALID;
    return value;
}
static uint32_t packed(TailReader *p,unsigned width) {
    uint32_t value=0;
    if(p->status==COH_OK)p->status=coh_rep_pack(&p->reader,width,&value);
    return value;
}
static uint32_t automatic(TailReader *p) {
    static const unsigned widths[]={2,10,24,32};
    uint32_t bin=scalar(p,2);
    return p->status==COH_OK?scalar(p,widths[bin]):0;
}
static uint32_t count(TailReader *p,uint32_t limit) {
    uint32_t value=automatic(p);
    if(p->status==COH_OK&&value>limit)p->status=COH_LIMIT;
    return p->status==COH_OK?value:0;
}
static void text(TailReader *p,CohEntTailString *out,size_t limit) {
    size_t start=p->out->strings_bytes;
    if(p->status!=COH_OK)return;
    if(limit>COH_ENT_TAIL_STRINGS_MAX-start)limit=COH_ENT_TAIL_STRINGS_MAX-start;
    for(size_t i=0;i<limit;i++) {
        uint32_t c=scalar(p,8);
        if(p->status!=COH_OK)return;
        p->out->strings[start+i]=(char)c;
        if(!c){out->offset=(uint32_t)start;out->bytes=(uint32_t)i;
            p->out->strings_bytes=(uint32_t)(start+i+1);return;}
    }
    p->status=COH_LIMIT;
}
static void mission(TailReader *p) {
    CohEntTailMission *m=&p->out->mission;
    m->filename_present=scalar(p,1);
    if(m->filename_present)text(p,&m->filename,COH_ENT_TAIL_STRING_MAX);
    text(p,&m->description,COH_ENT_TAIL_STRING_MAX);text(p,&m->owner,COH_ENT_TAIL_STRING_MAX);
    m->owner_dbid=packed(p,1);m->context=packed(p,1);m->subhandle=packed(p,1);m->level=packed(p,1);
    m->difficulty_level_adjust=automatic(p);m->difficulty_team_size=automatic(p);
    m->dont_reduce_boss=scalar(p,1);m->always_av=scalar(p,1);m->alliance=packed(p,2);
    text(p,&m->state,COH_ENT_TAIL_STRING_MAX);
    m->timeout=packed(p,1);m->timezero=automatic(p);m->timer_type=automatic(p);m->fail_on_timeout=automatic(p);
    m->complete=scalar(p,1);m->mission=scalar(p,1);m->running_mission=scalar(p,1);m->sg_mission=scalar(p,1);
    m->zone_transfer=scalar(p,1);m->teleport_on_complete=scalar(p,1);m->enforce_time_limit=scalar(p,1);
    m->abandonable=scalar(p,1);m->zowie=scalar(p,1);m->location_present=scalar(p,1);
    if(m->location_present) {
        for(unsigned i=0;i<3;i++) {
            uint32_t bits=scalar(p,32);memcpy(&m->position[i],&bits,sizeof(bits));
            if(p->status==COH_OK&&!isfinite(m->position[i]))p->status=COH_INVALID;
        }
        m->location_type=automatic(p);text(p,&m->location_map,COH_ENT_TAIL_STRING_MAX);
        text(p,&m->location_name,COH_ENT_TAIL_STRING_MAX);
    } else {
        m->explicit_map_present=scalar(p,1);
        if(m->explicit_map_present){m->location_type=automatic(p);text(p,&m->location_map,COH_ENT_TAIL_STRING_MAX);}
    }
    if(m->zowie) {
        m->zinfo=packed(p,1);m->zseed=scalar(p,32);m->zmap_id=packed(p,1);
        text(p,&m->ztype,COH_ENT_TAIL_STRING_MAX);text(p,&m->zname,COH_ENT_TAIL_STRING_MAX);
        text(p,&m->zpool_sizes,COH_ENT_TAIL_STRING_MAX);
    }
}
CohStatus coh_ent_very_rare_tail(CohRepReader *reader,CohEntVeryRareTail *out,
    CohEntVeryRareTailWorkspace *workspace,size_t retained,size_t limit) {
    uint32_t ignored;TailReader p;size_t needed;
    if(!reader||!out||!workspace||!limit||limit>COH_ENT_TAIL_AGGREGATE_MAX)return COH_INVALID;
    p.reader=*reader;p.status=coh_rep_read(&p.reader,0,&ignored);p.out=&workspace->candidate;
    if(p.status!=COH_OK)return p.status;
    const void *objects[]={reader,out,workspace,p.reader.bytes.data};
    const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),p.reader.bytes.size};
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)
        if(overlaps(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
    needed=sizeof(*out)+sizeof(*workspace)+COH_ENT_TAIL_STACK_RESERVE;
    if(needed>limit||p.reader.bytes.size>limit-needed)return COH_LIMIT;
    needed+=p.reader.bytes.size;if(retained>limit-needed)return COH_LIMIT;
    CohEntVeryRareTail *v=p.out;memset(v,0,sizeof(*v));v->begin_bit=p.reader.cursor;
    v->supergroup_update=scalar(&p,1);
    if(v->supergroup_update) {
        v->supergroup_id=packed(&p,2);
        if(v->supergroup_id) {
            text(&p,&v->supergroup_name,COH_ENT_TAIL_STRING_MAX);
            text(&p,&v->supergroup_emblem,COH_ENT_TAIL_STRING_MAX);
            v->colors[0]=scalar(&p,32);v->colors[1]=scalar(&p,32);v->spaces_for_items=packed(&p,2);
            v->mission_present=scalar(&p,1);if(v->mission_present)mission(&p);
            v->token_count=count(&p,COH_ENT_TAIL_TOKENS_MAX);
            for(uint32_t i=0;i<v->token_count&&p.status==COH_OK;i++) {
                text(&p,&v->tokens[i].name,COH_ENT_TAIL_STRING_MAX);
                v->tokens[i].value=packed(&p,1);v->tokens[i].time=packed(&p,1);
            }
            v->recipe_count=count(&p,COH_ENT_TAIL_RECIPES_MAX);
            for(uint32_t i=0;i<v->recipe_count&&p.status==COH_OK;i++) {
                v->recipes[i].unlimited=packed(&p,1);
                if(p.status==COH_OK&&v->recipes[i].unlimited>1)p.status=COH_INVALID;
                if(!v->recipes[i].unlimited)v->recipes[i].count=packed(&p,3);
                text(&p,&v->recipes[i].name,COH_ENT_TAIL_STRING_MAX);
            }
            v->detail_count=count(&p,COH_ENT_TAIL_DETAILS_MAX);
            for(uint32_t i=0;i<v->detail_count&&p.status==COH_OK;i++) {
                text(&p,&v->details[i].name,COH_ENT_TAIL_STRING_MAX);
                v->details[i].creation_time=automatic(&p);v->details[i].expiration_time=automatic(&p);
                v->details[i].flags=automatic(&p);
            }
        }
    }
    v->pact_update=scalar(&p,1);
    if(v->pact_update) {
        v->pact_id=automatic(&p);
        if(v->pact_id) {
            v->pact_count=count(&p,COH_ENT_TAIL_PACT_MAX);
            for(uint32_t i=0;i<v->pact_count&&p.status==COH_OK;i++) {
                v->pact[i].dbid=automatic(&p);v->pact[i].name_present=scalar(&p,1);
                if(v->pact[i].name_present)text(&p,&v->pact[i].name,COH_ENT_TAIL_PACT_NAME_MAX);
            }
        }
    }
    v->logout_update=scalar(&p,1);
    if(v->logout_update) {
        v->logout_bad_connection=scalar(&p,1);v->logout_timer_present=scalar(&p,1);
        if(v->logout_timer_present)v->logout_quanta=packed(&p,5);
    }
    if(p.status!=COH_OK)return p.status;
    v->end_bit=p.reader.cursor;memcpy(out,v,sizeof(*out));*reader=p.reader;return COH_OK;
}
