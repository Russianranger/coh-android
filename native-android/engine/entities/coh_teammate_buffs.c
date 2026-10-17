#include "coh_teammate_buffs.h"
#include <string.h>
typedef struct { CohRepReader reader; CohStatus status; } BuffReader;
static int overlaps(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(!an||!bn)return 0;
    if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;
    return aa<bb+bn&&bb<aa+an;
}
static uint32_t scalar(BuffReader *p,unsigned width) {
    uint32_t v=0;
    if(p->status==COH_OK)p->status=coh_rep_read(&p->reader,width,&v);
    if(p->status==COH_OK&&width<32&&v>=(UINT32_C(1)<<width))p->status=COH_INVALID;
    return v;
}
static uint32_t packed(BuffReader *p,unsigned width) {
    uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->reader,width,&v);return v;
}
static uint32_t automatic(BuffReader *p) {
    static const unsigned widths[]={2,10,24,32};uint32_t bin=scalar(p,2);
    return p->status==COH_OK?scalar(p,widths[bin]):0;
}
CohStatus coh_ent_teammate_buffs(CohRepReader *reader,CohEntTeammateBuffs *out,
    CohEntTeammateBuffsWorkspace *workspace,size_t retained,size_t limit) {
    BuffReader p;uint32_t ignored;size_t needed;
    if(!reader||!out||!workspace||!limit||limit>COH_ENT_BUFF_AGGREGATE_MAX)return COH_INVALID;
    p.reader=*reader;p.status=coh_rep_read(&p.reader,0,&ignored);
    if(p.status!=COH_OK)return p.status;
    const void *objects[]={reader,out,workspace,p.reader.bytes.data};
    const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),p.reader.bytes.size};
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)
        if(overlaps(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
    needed=sizeof(*out)+sizeof(*workspace)+COH_ENT_BUFF_STACK_RESERVE;
    if(needed>limit||p.reader.bytes.size>limit-needed)return COH_LIMIT;
    needed+=p.reader.bytes.size;if(retained>limit-needed)return COH_LIMIT;
    CohEntTeammateBuffs *v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=p.reader.cursor;
    v->teammate=scalar(&p,1);
    if(v->teammate)v->buffs_present=scalar(&p,1);
    if(v->buffs_present) {
        v->not_getting_buffs=scalar(&p,1);
        if(!v->not_getting_buffs) {
            v->diffs_only=scalar(&p,1);v->count=packed(&p,4);
            if(p.status==COH_OK&&v->count>COH_ENT_BUFFS_MAX)p.status=COH_LIMIT;
            for(uint32_t i=0;i<v->count&&p.status==COH_OK;i++) {
                CohEntBuff *b=&v->buffs[i];
                if(v->diffs_only)b->delete_mark=scalar(&p,1);
                b->power_crc=automatic(&p);b->timer_present=scalar(&p,1);
                if(b->timer_present)b->blink_now=scalar(&p,1);
                b->uid=packed(&p,20);b->mods_present=scalar(&p,1);b->mods_begin=v->mods_count;
                if(b->mods_present)b->mods_count=packed(&p,5);
                if(p.status==COH_OK&&(b->mods_count>COH_ENT_BUFF_MODS_PER_BUFF_MAX||
                    b->mods_count>COH_ENT_BUFF_MODS_MAX-v->mods_count))p.status=COH_LIMIT;
                for(uint32_t j=0;j<b->mods_count&&p.status==COH_OK;j++) {
                    CohEntBuffMod *m=&v->mods[v->mods_count++];
                    m->magnitude_word=packed(&p,10);m->attribute_hash=packed(&p,10);
                }
            }
        }
    }
    if(p.status!=COH_OK)return p.status;
    v->end_bit=p.reader.cursor;*out=*v;*reader=p.reader;return COH_OK;
}
