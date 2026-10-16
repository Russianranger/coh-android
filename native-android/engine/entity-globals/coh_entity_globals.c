#include "coh_entity_globals.h"
#include <string.h>

static int overlaps(const void *a, size_t an, const void *b, size_t bn) {
    uintptr_t aa=(uintptr_t)a, bb=(uintptr_t)b;
    if(!an || !bn) return 0;
    if(an>UINTPTR_MAX-aa || bn>UINTPTR_MAX-bb) return 1;
    return aa<bb+bn && bb<aa+an;
}
CohStatus coh_global_power_modes(CohRepReader *reader, CohPowerModes *state,
    CohPowerModeEvent *event) {
    CohRepReader q;
    CohPowerModes candidate;
    uint32_t present;
    CohStatus status;
    if(!reader || !state || !event) return COH_INVALID;
    /* Validate reader bounds without changing any caller memory. */
    q=*reader;
    status=coh_rep_read(&q,0,&present);
    if(status!=COH_OK) return status;
    if(overlaps(reader,sizeof(*reader),state,sizeof(*state)) ||
       overlaps(reader,sizeof(*reader),event,sizeof(*event)) ||
       overlaps(state,sizeof(*state),event,sizeof(*event)) ||
       overlaps(reader,sizeof(*reader),q.bytes.data,q.bytes.size) ||
       overlaps(state,sizeof(*state),q.bytes.data,q.bytes.size) ||
       overlaps(event,sizeof(*event),q.bytes.data,q.bytes.size)) return COH_INVALID;
    if(state->count>COH_GLOBAL_POWER_MODE_MAX) return COH_LIMIT;
    status=coh_rep_read(&q,1,&present);
    if(status!=COH_OK) return status;
    if(present>1) return COH_INVALID;
    if(present) {
        memset(&candidate,0,sizeof(candidate));
        status=coh_rep_pack(&q,3,&candidate.count);
        if(status!=COH_OK) return status;
        if(candidate.count>COH_GLOBAL_POWER_MODE_MAX) return COH_LIMIT;
        for(uint32_t i=0;i<candidate.count;i++) {
            status=coh_rep_pack(&q,3,&candidate.modes[i]);
            if(status!=COH_OK) return status;
        }
        *state=candidate;
    }
    event->replacement_present=present;
    *reader=q;
    return COH_OK;
}
