#include "coh_taskforce.h"
#include <string.h>
typedef struct {CohRepReader r;CohEntStage stage;CohStatus status;} TaskParse;
static uint32_t scalar(TaskParse *p,unsigned n){
    uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,n,&v);
    if(p->status==COH_OK&&n<32&&v>=(1u<<n))p->status=COH_INVALID;
    return v;
}
static uint32_t packed(TaskParse *p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,n,&v);return v;}
static uint32_t automatic(TaskParse *p){static const unsigned widths[]={2,10,24,32};uint32_t bin=scalar(p,2);return p->status==COH_OK?scalar(p,widths[bin]):0;}
static void text(TaskParse *p,char *out,size_t capacity){
    for(size_t i=0;i<capacity&&p->status==COH_OK;i++){out[i]=(char)scalar(p,8);if(!out[i])return;}
    if(p->status==COH_OK)p->status=COH_LIMIT;
}
CohStatus coh_ent_taskforce(CohRepReader *reader,const CohEntCostumeDictionary *dictionary,
    uint32_t generation,CohEntTaskforceWorkspace *workspace,CohEntTaskforce *out,CohEntFailure *failure){
    uint32_t ignored;TaskParse p;CohEntTaskforce *v;CohEntFailure nested={0};
    if(!reader||!workspace||!out||!generation||out==&workspace->candidate)return COH_INVALID;
    p=(TaskParse){*reader,COH_ENT_STAGE_TASKFORCE_ARCHITECT,COH_OK};
    if(coh_rep_read(&p.r,0,&ignored)!=COH_OK)return COH_INVALID;
    v=&workspace->candidate;memset(v,0,sizeof(*v));v->generation=generation;
    v->architect_update=scalar(&p,1);
    if(v->architect_update){
        v->on_architect=scalar(&p,1);
        if(v->on_architect){
            v->architect_flags=automatic(&p);v->architect_id=automatic(&p);v->contact_override=automatic(&p);
            text(&p,v->contact_name,sizeof(v->contact_name));
            v->costume_exists=scalar(&p,1);
            if(v->costume_exists){
                v->costume_body=scalar(&p,1);
                if(v->costume_body&&p.status==COH_OK){
                    p.status=coh_ent_costume(&p.r,dictionary,generation,&workspace->body,&v->costume,&nested);
                    if(p.status!=COH_OK){
                        if(nested.status!=p.status)nested=(CohEntFailure){p.status,COH_ENT_STAGE_COSTUME_DICTIONARY,p.r.cursor};
                        if(failure)*failure=nested;
                        return p.status;
                    }
                }
            }
            v->custom_exists=scalar(&p,1);
            if(v->custom_exists){
                v->custom_body=scalar(&p,1);
                if(v->custom_body&&p.status==COH_OK){
                    p.status=coh_ent_custom_costume(&p.r,&v->custom,&nested);
                    if(p.status!=COH_OK){if(failure)*failure=nested;return p.status;}
                }
            }
            v->review_present=scalar(&p,1);
            if(v->review_present){
                text(&p,v->review_name,sizeof(v->review_name));text(&p,v->review_author,sizeof(v->review_author));
                text(&p,v->review_description,sizeof(v->review_description));
                v->rating=automatic(&p);v->european=automatic(&p);v->invincible=automatic(&p);v->untargetable=automatic(&p);
            }
        }
    }
    if(p.status==COH_OK)p.stage=COH_ENT_STAGE_TASKFORCE_PARAMETERS;
    v->on_flashback=packed(&p,1);if(p.status==COH_OK&&v->on_flashback>1)p.status=COH_INVALID;
    v->parameter_update=scalar(&p,1);
    if(v->parameter_update){
        v->parameter_mask=automatic(&p);
        for(unsigned i=0;i<COH_TASKFORCE_PARAMETERS;i++)if(v->parameter_mask&(UINT32_C(1)<<i))v->parameters[i]=automatic(&p);
    }
    if(p.status!=COH_OK){if(failure)*failure=(CohEntFailure){p.status,p.stage,p.r.cursor};return p.status;}
    v->end_bit=p.r.cursor;*out=*v;*reader=p.r;if(failure)memset(failure,0,sizeof(*failure));return COH_OK;
}
