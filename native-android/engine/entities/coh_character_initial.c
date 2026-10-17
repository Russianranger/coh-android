#include "coh_character_initial.h"
#include <string.h>
static int overlap(const void *a,size_t an,const void *b,size_t bn){
    uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(!an||!bn)return 0;
    if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;
    return aa<bb+bn&&bb<aa+an;
}
static CohStatus scalar(CohRepReader *r,unsigned width,uint32_t *v){
    CohStatus s=coh_rep_read(r,width,v);
    if(s==COH_OK&&width<32&&*v>=(UINT32_C(1)<<width))return COH_INVALID;
    return s;
}
CohStatus coh_character_initial_read(CohRepReader *reader,
    const CohCharacterWireProfile *profile,uint32_t packet_id,
    CohCharacterInitialWorkspace *workspace,CohCharacterInitialPrefix *out,
    size_t budget,size_t retained,CohCharacterInitialFailure *failure){
    CohRepReader r;CohStatus status;uint32_t ignored;
    CohCharacterInitialFailure f;size_t fixed,child_retained;
    if(!reader||!profile||!workspace||!out||!packet_id||
       !budget||budget>COH_CHARACTER_INITIAL_RAM_MAX)return COH_INVALID;
    r=*reader;status=coh_rep_read(&r,0,&ignored);if(status!=COH_OK)return status;
    const void *objects[]={reader,profile,workspace,out,failure,r.bytes.data};
    const size_t sizes[]={sizeof(*reader),sizeof(*profile),sizeof(*workspace),
        sizeof(*out),failure?sizeof(*failure):0,r.bytes.size};
    for(unsigned i=0;i<6;i++)for(unsigned j=0;j<i;j++)
        if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
    fixed=sizeof(*out)+sizeof(*workspace)+COH_CHARACTER_INITIAL_STACK_RESERVE;
    if(fixed>budget||r.bytes.size>budget-fixed||retained>budget-fixed-r.bytes.size)
        return COH_LIMIT;
    /* Child already charges its output+workspace+input. Its extra retained
     * reservation names every other enclosing owned byte exactly once. */
    child_retained=fixed-2*sizeof(CohCharacterData)+retained;
    CohCharacterInitialPrefix *v=&workspace->candidate;
    memset(v,0,sizeof(*v));memset(&f,0,sizeof(f));v->begin_bit=r.cursor;v->packet_id=packet_id;
    f.stage=COH_CHARACTER_INITIAL_ACCOUNT;
    status=coh_character_prefix(&r,&v->account);if(status!=COH_OK)goto failed;
    v->prefix_end_bit=r.cursor;f.stage=COH_CHARACTER_INITIAL_DATA;
    status=coh_character_data_read(&r,profile,&workspace->character,&v->character,
        budget,child_retained,&f.character);if(status!=COH_OK)goto failed;
    v->character_end_bit=r.cursor;f.stage=COH_CHARACTER_INITIAL_SETS;
    status=coh_rep_string(&r,v->primary_set,sizeof(v->primary_set));if(status!=COH_OK)goto failed;
    status=coh_rep_string(&r,v->secondary_set,sizeof(v->secondary_set));if(status!=COH_OK)goto failed;
    v->names_end_bit=r.cursor;f.stage=COH_CHARACTER_INITIAL_ALLY_PVP;
    status=coh_rep_pack(&r,2,&v->ally_id);if(status!=COH_OK)goto failed;
    status=coh_rep_pack(&r,4,&v->gang_id);if(status!=COH_OK)goto failed;
    status=scalar(&r,1,&v->pvp_switch);if(status!=COH_OK)goto failed;
    status=scalar(&r,1,&v->pvp_active);if(status!=COH_OK)goto failed;
    status=coh_rep_pack(&r,5,&v->pvp_timer);if(status!=COH_OK)goto failed;
    status=scalar(&r,1,&v->is_ganker);if(status!=COH_OK)goto failed;
    f.stage=COH_CHARACTER_INITIAL_SELF_STATS;
    status=coh_ent_character_stats(&r,packet_id,1,&v->self_stats,&f.entity);
    if(status!=COH_OK)goto failed;
    v->end_bit=r.cursor;*out=*v;*reader=r;
    if(failure)memset(failure,0,sizeof(*failure));
    return COH_OK;
failed:
    f.status=status;f.bit=r.cursor;if(failure)*failure=f;return status;
}
