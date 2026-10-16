#include "coh_badges.h"
#include <string.h>

static int overlap(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(!an||!bn)return 0;
    if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;
    return aa<bb+bn&&bb<aa+an;
}
static CohStatus boolean(CohRepReader *r,uint32_t *out) {
    CohStatus s=coh_rep_read(r,1,out);
    return s==COH_OK&&*out>1?COH_INVALID:s;
}
static CohStatus filename(CohRepReader *r,char *out,size_t capacity,size_t *length) {
    for(size_t i=0;i<capacity;i++) {
        uint32_t c;CohStatus s=coh_rep_read(r,8,&c);if(s!=COH_OK)return s;
        out[i]=(char)c;if(!c){*length=i;return COH_OK;}
    }
    return COH_LIMIT;
}
static CohStatus records(CohRepReader *r,CohBadgeUpdate *out,unsigned group) {
    uint32_t *count=group?&out->supergroup_count:&out->player_count;
    uint32_t limit=group?COH_BADGE_SUPERGROUP_MAX:COH_BADGE_PLAYER_MAX;
    uint32_t base=group?out->player_count:0,present;
    CohStatus s;
    for(;;) {
        s=boolean(r,&present);if(s!=COH_OK)return s;if(!present)return COH_OK;
        if(*count>=limit)return COH_LIMIT;
        CohBadgeRecord *item=&out->records[base+*count];
        s=coh_rep_pack(r,6,&item->index);if(s!=COH_OK)return s;
        /* Original sender excludes index zero. Negative source int values and
         * indices beyond the destination array cannot be safely applied. */
        if(!item->index||item->index>=limit)return COH_INVALID;
        s=boolean(r,&present);if(s!=COH_OK)return s;
        if(present)item->flags=COH_BADGE_OWNED;
        else {
            s=boolean(r,&present);if(s!=COH_OK)return s;
            if(present)item->flags|=COH_BADGE_VISIBLE;
            s=boolean(r,&present);if(s!=COH_OK)return s;
            if(present)item->flags|=COH_BADGE_KNOWN;
            s=boolean(r,&present);if(s!=COH_OK)return s;
            if(present){s=coh_rep_read(r,20,&item->completion);if(s!=COH_OK)return s;
                if(item->completion>0xfffffu)return COH_INVALID;}
        }
        s=boolean(r,&present);if(s!=COH_OK)return s;
        if(present) {
            size_t available=COH_BADGE_FILENAMES_MAX-out->filenames_bytes;
            size_t cap=available<COH_BADGE_FILENAME_MAX?available:COH_BADGE_FILENAME_MAX;
            if(!cap)return COH_LIMIT;
            char *name=out->filenames+out->filenames_bytes;
            size_t length;
            s=filename(r,name,cap,&length);if(s!=COH_OK)return s;
            item->flags|=COH_BADGE_FILENAME;
            item->filename_offset=out->filenames_bytes;
            item->filename_bytes=(uint32_t)length;
            out->filenames_bytes+=(uint32_t)length+1;
        }
        (*count)++;
    }
}
CohStatus coh_global_badges(CohRepReader *reader,CohBadgeUpdate *output,
    CohBadgeWorkspace *workspace,size_t retained,size_t limit) {
    CohRepReader r;CohStatus s;uint32_t ignored;
    if(!reader||!output||!workspace||!limit||limit>COH_BADGE_AGGREGATE_MAX)return COH_INVALID;
    r=*reader;s=coh_rep_read(&r,0,&ignored);if(s!=COH_OK)return s;
    const void *objects[]={reader,output,workspace,r.bytes.data};
    const size_t sizes[]={sizeof(*reader),sizeof(*output),sizeof(*workspace),r.bytes.size};
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)
        if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
    size_t needed=sizeof(*output)+sizeof(*workspace)+8192u;
    if(needed>limit||r.bytes.size>limit-needed)return COH_LIMIT;
    needed+=r.bytes.size;if(retained>limit-needed)return COH_LIMIT;
    CohBadgeUpdate *candidate=&workspace->candidate;
    memset(candidate,0,sizeof(*candidate));
    s=coh_rep_pack(&r,4,&candidate->debug_mode);if(s!=COH_OK)return s;
    s=records(&r,candidate,0);if(s!=COH_OK)return s;
    s=boolean(&r,&candidate->history_present);if(s!=COH_OK)return s;
    if(candidate->history_present) {
        s=coh_rep_read(&r,8,&candidate->history_count);if(s!=COH_OK)return s;
        if(candidate->history_count>COH_BADGE_RECENT_MAX)return COH_LIMIT;
        for(uint32_t i=0;i<candidate->history_count;i++) {
            s=coh_rep_read(&r,16,&candidate->recent[i].index);if(s!=COH_OK)return s;
            s=coh_rep_read(&r,32,&candidate->recent[i].time_awarded);if(s!=COH_OK)return s;
        }
    }
    s=boolean(&r,&candidate->supergroup_present);if(s!=COH_OK)return s;
    if(candidate->supergroup_present){s=records(&r,candidate,1);if(s!=COH_OK)return s;}
    memcpy(output,candidate,sizeof(*output));*reader=r;return COH_OK;
}
CohStatus coh_global_badge_monitor(CohRepReader *reader,CohBadgeMonitor *output) {
    CohRepReader r;CohBadgeMonitor candidate={{0}};CohStatus s;uint32_t present;
    if(!reader||!output)return COH_INVALID;
    r=*reader;s=coh_rep_read(&r,0,&present);if(s!=COH_OK)return s;
    if(overlap(reader,sizeof(*reader),output,sizeof(*output))||
       overlap(reader,sizeof(*reader),r.bytes.data,r.bytes.size)||
       overlap(output,sizeof(*output),r.bytes.data,r.bytes.size))return COH_INVALID;
    for(unsigned i=0;i<COH_BADGE_MONITOR_MAX;i++) {
        s=boolean(&r,&present);if(s!=COH_OK)return s;
        if(present){s=coh_rep_pack(&r,8,&candidate.indices[i]);if(s!=COH_OK)return s;}
    }
    *output=candidate;*reader=r;return COH_OK;
}
