#include "coh_entities.h"
#include <math.h>
#include <string.h>

typedef struct { CohRepReader r; CohEntStage stage; CohStatus status; } Parse;
static void stage(Parse *p,CohEntStage s){if(p->status==COH_OK)p->stage=s;}
static uint32_t read_n(Parse *p,unsigned n) {
    uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,n,&v);return v;
}
static uint32_t pack(Parse *p,unsigned n) {
    uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,n,&v);return v;
}
/* In byteAlignedMode every scalar rounds up to bytes. Bits outside the source
 * logical width must still be zero; unlike legacy pktGetBits we fail closed. */
static uint32_t flag(Parse *p) { uint32_t v=read_n(p,1);if(v>1)p->status=COH_INVALID;return v; }
static uint32_t scalar(Parse *p,unsigned n) {
    uint32_t v=read_n(p,n);if(n<32 && v>=(1u<<n))p->status=COH_INVALID;return v;
}
static uint32_t opt_pack(Parse *p,unsigned n){return flag(p)?pack(p,n):0;}
static uint32_t opt_bits(Parse *p,unsigned n){return flag(p)?scalar(p,n):0;}
static uint32_t auto_bits(Parse *p){static const unsigned w[]={2,10,24,32};uint32_t v=scalar(p,2);return p->status==COH_OK?scalar(p,w[v]):0;}
static void string(Parse *p,char *out,size_t n) {
    size_t i;
    if(!n||n>1024){if(p->status==COH_OK)p->status=COH_INVALID;return;}
    for(i=0;i<n&&p->status==COH_OK;i++){out[i]=(char)read_n(p,8);if(!out[i])return;}
    if(p->status==COH_OK)p->status=COH_LIMIT;
}
static void discard_string(Parse *p,size_t limit) {char scratch[1024];string(p,scratch,limit);}
static void optional_string(Parse *p,size_t limit){if(flag(p))discard_string(p,limit);}
static void require(Parse *p,int ok,CohStatus bad){if(p->status==COH_OK&&!ok)p->status=bad;}
static CohStatus fail(Parse *p,CohEntFailure *out) {
    if(out){out->status=p->status;out->stage=p->stage;out->bit=p->r.cursor;}return p->status;
}
static void clear_failure(CohEntFailure *out){if(out)memset(out,0,sizeof(*out));}
static CohStatus check_reader(CohRepReader *r) {
    uint32_t unused;CohRepReader copy;if(!r)return COH_INVALID;copy=*r;
    /* Width-zero read validates all reader invariants without consuming data. */
    return coh_rep_read(&copy,0,&unused);
}

CohStatus coh_ent_next_index(CohRepReader *r,int32_t previous,uint32_t *out,CohEntFailure *failure){
    Parse p;uint32_t delta,index;
    if(check_reader(r)!=COH_OK||!out||previous < -1||previous>(int32_t)COH_ENT_INDEX_MAX)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_LIST,COH_OK};delta=pack(&p,1);
    /* sendEntity's signed negative deltas pass through the U32 writer. The
     * original x86 consumer converts them back to int; unsigned addition gives
     * the intended source result without implementation-defined conversion. */
    index=(uint32_t)previous+delta+UINT32_C(1);
    require(&p,index<=COH_ENT_INDEX_MAX,COH_LIMIT);
    if(p.status!=COH_OK)return fail(&p,failure);
    *r=p.r;*out=(uint32_t)index;clear_failure(failure);return COH_OK;
}

static void creation(Parse *p,uint32_t selected,CohEntCreate *c) {
    stage(p,COH_ENT_STAGE_CREATE);c->create=flag(p);if(!c->create)return;
    c->end=flag(p);if(c->end)return;
    c->entity_id=pack(p,12);c->type=pack(p,2);
    require(p,c->entity_id>0&&c->entity_id<=COH_ENT_GENERATION_MAX,COH_LIMIT);
    require(p,c->type>0&&c->type<9,COH_UNSUPPORTED);
    stage(p,COH_ENT_STAGE_IDENTITY);
    if(c->type==2){
        c->is_self=flag(p);if(c->is_self)c->access_level=pack(p,1);
        c->dbid=pack(p,22);require(p,c->dbid>0&&c->dbid<=INT32_MAX,COH_INVALID);
        require(p,!c->is_self||(selected&&selected==c->dbid),COH_STATE);
        require(p,!selected||c->is_self||selected!=c->dbid,COH_STATE);
    }else if(flag(p)){
        c->owner_index=pack(p,12);c->creator_index=pack(p,12);
        require(p,c->owner_index>0&&c->owner_index<=COH_ENT_INDEX_MAX&&c->creator_index<=COH_ENT_INDEX_MAX,COH_LIMIT);
        stage(p,COH_ENT_STAGE_PET_POWER);
        /* basepower_Receive references a separately negotiated dictionary. */
        if(flag(p)){require(p,0,COH_UNSUPPORTED);return;}
        c->commandable_pet=flag(p);c->visible_pet=flag(p);c->dismissable_pet=flag(p);
        optional_string(p,1000);c->special_power_state=pack(p,1);optional_string(p,128);
    }
    stage(p,COH_ENT_STAGE_CREATE_STRINGS);
    if(c->type==2||c->type==4){
        c->critter_form=pack(p,1);require(p,c->critter_form<=1,COH_INVALID);
        c->class_index=pack(p,1);c->origin_index=pack(p,1);
        require(p,c->class_index<=65535&&c->origin_index<=65535,COH_LIMIT);
        if(flag(p)){
            c->player_type=flag(p);c->player_subtype=scalar(p,2);c->praetorian_progress=scalar(p,3);
            (void)pack(p,5);optional_string(p,10);optional_string(p,128);optional_string(p,128);
            (void)auto_bits(p);(void)auto_bits(p);(void)scalar(p,32);
            optional_string(p,1000);optional_string(p,32);
        }
        if(flag(p))c->player_type_location=flag(p);
    }
    if(flag(p))string(p,c->name,sizeof(c->name));
    c->fade_in=flag(p);c->in_phase=flag(p);c->random_seed=scalar(p,32);
    if(flag(p)){
        c->rank=pack(p,2);discard_string(p,1000);
        if(flag(p)){discard_string(p,260);discard_string(p,1000);}
        c->detail_id=opt_pack(p,5);
    }
    optional_string(p,1000);optional_string(p,1000);optional_string(p,128);
    c->contact_handle=auto_bits(p);c->end_bit=p->r.cursor;
}
CohStatus coh_ent_create(CohRepReader *r,uint32_t selected,CohEntCreate *out,CohEntFailure *failure){
    Parse p;CohEntCreate c={0};CohStatus s=check_reader(r);
    if(s!=COH_OK||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_CREATE,COH_OK};creation(&p,selected,&c);
    c.end_bit=p.r.cursor;if(p.status!=COH_OK)return fail(&p,failure);
    *out=c;*r=p.r;clear_failure(failure);return COH_OK;
}
void coh_ent_orientation_init(CohEntOrientation *q){if(q){memset(q,0,sizeof(*q));q->quaternion[3]=1.f;}}
static void orientation(Parse *p,uint32_t id,CohEntOrientation *q){
    uint32_t mask,j;stage(p,COH_ENT_STAGE_ORIENTATION);mask=opt_bits(p,3);
    for(j=0;j<3;j++)if(mask&(1u<<j)){
        uint32_t packed=scalar(p,9);
        if(id>q->packet_ids[j]){
            /* Exact unpackQuatElem(...,9), with original float operation order. */
            float elem=(float)(((packed * 3.14159265358979323846) / 512) - 1.57079632679489661923);
            if(elem < -1.57079632679489661923)elem=(float)-1.57079632679489661923;
            if(elem > (1.57079632679489661923-0.00001f))elem=(float)1.57079632679489661923;
            if(fabsf(elem)<0.00001f)elem=0.f;
            q->quaternion[j]=sinf(elem);
            q->packet_ids[j]=id;q->valid|=1u<<j;
        }
    }
    if(mask&&p->status==COH_OK){
        float *v=q->quaternion,w=1.f-(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);
        float mag,scale;v[3]=w<=0?0:sqrtf(w);
        mag=sqrtf(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]+v[3]*v[3]);
        require(p,isfinite(mag)&&mag>0,COH_INVALID);
        if(p->status==COH_OK){scale=1.f/mag;for(j=0;j<4;j++)v[j]*=scale;}
    }
}
CohStatus coh_ent_orientation(CohRepReader *r,uint32_t id,CohEntOrientation *out,CohEntFailure *failure){
    Parse p;CohEntOrientation q;unsigned j;
    if(check_reader(r)!=COH_OK||!id||!out||out->valid>7)return COH_INVALID;
    for(j=0;j<4;j++)if(!isfinite(out->quaternion[j]))return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_ORIENTATION,COH_OK};q=*out;orientation(&p,id,&q);
    if(p.status!=COH_OK)return fail(&p,failure);
    *r=p.r;*out=q;clear_failure(failure);return COH_OK;
}
void coh_ent_slot_init(CohEntSlot *s,uint32_t idx){
    if(!s)return;
    memset(s,0,sizeof(*s));s->index=idx;
    coh_rep_position_init(&s->position);coh_ent_orientation_init(&s->orientation);
}
static void pose(Parse *p,uint32_t id,uint32_t create,uint32_t interp,CohEntSlot *slot){
    CohRepReader look=p->r;uint32_t changed=0;
    stage(p,COH_ENT_STAGE_POSITION);
    if(p->status!=COH_OK)return;
    p->status=coh_rep_read(&look,3,&changed);if(p->status!=COH_OK)return;
    require(p,changed<=7,COH_INVALID);if(p->status!=COH_OK)return;
    p->status=coh_rep_position(&p->r,id,&slot->position);if(p->status!=COH_OK)return;
    if(changed&&!create&&flag(p)){
        uint32_t instant=flag(p);if(!instant&&interp){
            stage(p,COH_ENT_STAGE_INTERPOLATION);require(p,0,COH_UNSUPPORTED);return;
        }
    }
    orientation(p,id,&slot->orientation);
}
CohStatus coh_ent_record(CohRepReader *r,uint32_t selected,uint32_t id,uint32_t interp,
    CohEntSlot *out,CohEntRecord *record,CohEntFailure *failure){
    Parse p;CohEntRecord c={0};CohEntSlot s;uint32_t v,i;
    if(check_reader(r)!=COH_OK||!id||!selected||!out||!record||interp>3||
       out->index>COH_ENT_INDEX_MAX||out->present>1||out->position.valid>1||
       out->orientation.valid>7)return COH_INVALID;
    for(i=0;i<3;i++)if(out->position.packed[i]>0xffffffu)return COH_INVALID;
    for(i=0;i<4;i++)if(!isfinite(out->orientation.quaternion[i]))return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_CREATE,COH_OK};s=*out;creation(&p,selected,&c.identity);
    if(p.status!=COH_OK)return fail(&p,failure);
    if(c.identity.end){c.end_bit=p.r.cursor;*r=p.r;*record=c;clear_failure(failure);return COH_OK;}
    stage(&p,COH_ENT_STAGE_IDENTITY);
    require(&p,s.index>0,COH_LIMIT);
    if(p.status!=COH_OK)return fail(&p,failure);
    if(c.identity.create){
        require(&p,!(s.present&&id<=s.create_packet)&&id>=s.delete_packet,COH_STATE);
        if(p.status!=COH_OK)return fail(&p,failure);
        coh_ent_slot_init(&s,out->index);s.identity=c.identity;s.present=1;s.create_packet=id;
        s.delete_packet=out->delete_packet;s.deleted_entity_id=out->deleted_entity_id;
    }else{
        require(&p,s.present&&id>=s.create_packet,COH_STATE);
        require(&p,!s.identity.is_self||s.identity.dbid==selected,COH_STATE);
        if(p.status!=COH_OK)return fail(&p,failure);
    }
    c.rare=flag(&p);if(c.rare){c.medium_rare=flag(&p);c.very_rare=flag(&p);}
    stage(&p,COH_ENT_STAGE_STATE);
    if(c.medium_rare&&flag(&p)){v=opt_pack(&p,3);if(id>=s.state_packet){s.state_mode=v;s.state_packet=id;}}
    pose(&p,id,c.identity.create,interp,&s);if(p.status!=COH_OK)return fail(&p,failure);
    stage(&p,COH_ENT_STAGE_SEQUENCE);
    if(c.rare&&flag(&p)){
        uint32_t idx=opt_pack(&p,8),ticks=opt_pack(&p,4),bits=opt_bits(&p,11);
        require(&p,idx<=INT32_MAX&&ticks<=65535,COH_LIMIT);
        if(id>=s.sequence_packet){s.sequence_index=idx;s.sequence_ticks=ticks;s.sequence_bits=bits;s.sequence_packet=id;}
    }
    if(c.medium_rare){
        c.trigger_count=pack(&p,1);require(&p,c.trigger_count<=COH_ENT_TRIGGER_MAX,COH_LIMIT);
        if(p.status!=COH_OK)return fail(&p,failure);
        for(i=0;i<c.trigger_count;i++){
            c.triggers[i].index=pack(&p,10);c.triggers[i].ticks=pack(&p,6);c.triggers[i].fx_id=opt_pack(&p,16);
            require(&p,c.triggers[i].index<=INT32_MAX&&c.triggers[i].ticks<=INT32_MAX,COH_LIMIT);
        }
        if(flag(&p))optional_string(&p,1000);
    }
    c.pchar_things=flag(&p);v=flag(&p);stage(&p,COH_ENT_STAGE_NETFX);
    if(v&&c.pchar_things){require(&p,0,COH_UNSUPPORTED);return fail(&p,failure);}
    if(c.medium_rare){
        stage(&p,COH_ENT_STAGE_APPEARANCE);c.appearance_type=opt_pack(&p,2);
        if(c.appearance_type){require(&p,0,COH_UNSUPPORTED);return fail(&p,failure);}
        (void)opt_bits(&p,8); /* Translucency; inspection does not publish rendering. */
    }
    if(c.very_rare){
        stage(&p,COH_ENT_STAGE_POWER_CUSTOM);require(&p,0,COH_UNSUPPORTED);return fail(&p,failure);
    }
    stage(&p,COH_ENT_STAGE_RAGDOLL);c.ragdoll_bones=opt_bits(&p,5);
    for(i=0;i<c.ragdoll_bones*3&&p.status==COH_OK;i++)(void)scalar(&p,10);
    if(c.pchar_things){stage(&p,COH_ENT_STAGE_CHARACTER_STATS);require(&p,0,COH_UNSUPPORTED);return fail(&p,failure);}
    stage(&p,COH_ENT_STAGE_VISION);s.vision_phases=auto_bits(&p);s.exclusive_vision_phase=auto_bits(&p);s.con_yellow=auto_bits(&p);
    stage(&p,COH_ENT_STAGE_BUFFS);
    if(flag(&p)){require(&p,0,COH_UNSUPPORTED);return fail(&p,failure);}
    if(p.status!=COH_OK)return fail(&p,failure);
    c.end_bit=p.r.cursor;*r=p.r;*out=s;*record=c;clear_failure(failure);return COH_OK;
}
static void list_table(Parse *p,uint32_t selected,const CohEntSlot *slots,size_t count,CohEntList *result){
    size_t i,j;stage(p,COH_ENT_STAGE_OWNERSHIP);
    for(i=0;i<count&&p->status==COH_OK;i++){
        const CohEntSlot *s=&slots[i];const CohEntCreate *c=&s->identity;
        require(p,s->index>0&&s->index<=COH_ENT_INDEX_MAX&&s->present<=1&&
            s->position.valid<=1&&s->orientation.valid<=7,COH_INVALID);
        for(j=0;j<3;j++)require(p,s->position.packed[j]<=0xffffffu,COH_INVALID);
        for(j=0;j<4;j++)require(p,isfinite(s->orientation.quaternion[j]),COH_INVALID);
        for(j=0;j<i;j++)require(p,s->index!=slots[j].index,COH_INVALID);
        if(!s->present)continue;
        require(p,c->entity_id>0&&c->entity_id<=COH_ENT_GENERATION_MAX&&
            c->type>0&&c->type<9&&c->is_self<=1,COH_INVALID);
        if(c->type==2){
            require(p,c->dbid>0&&c->dbid<=INT32_MAX,COH_INVALID);
            require(p,c->is_self?c->dbid==selected:c->dbid!=selected,COH_STATE);
        }else require(p,!c->is_self&&!c->dbid,COH_STATE);
        if(c->is_self){
            require(p,!result->self_index,COH_STATE);
            result->self_index=s->index;result->self_entity_id=c->entity_id;result->self_dbid=c->dbid;
        }
    }
}
CohStatus coh_ent_list(CohRepReader *r,uint32_t selected,uint32_t id,uint32_t interp,
    CohEntSlot *slots,size_t count,CohEntListWorkspace *workspace,CohEntList *out,CohEntFailure *failure){
    Parse p;CohEntList result={0},baseline={0};int32_t previous=-1;
    if(check_reader(r)!=COH_OK||!selected||selected>INT32_MAX||!id||interp>3||
       (!slots&&count)||count>COH_ENT_LIST_MAX||!workspace||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_OWNERSHIP,COH_OK};list_table(&p,selected,slots,count,&baseline);
    if(p.status!=COH_OK)return fail(&p,failure);
    if(count)memcpy(workspace->slots,slots,count*sizeof(*slots));
    for(;;){
        uint32_t delta,index,create,end=0;size_t i,j;Parse probe;CohEntRecord record;CohStatus status;
        stage(&p,COH_ENT_STAGE_LIST);delta=pack(&p,1);
        index=(uint32_t)previous+delta+UINT32_C(1);
        if(p.status!=COH_OK)return fail(&p,failure);
        /* The source tests end before dereferencing ent_xlat[idx]. In
         * particular a terminator after slot MAX has synthetic index MAX+1. */
        probe=p;create=flag(&probe);if(create)end=flag(&probe);
        if(probe.status!=COH_OK)return fail(&probe,failure);
        if(end){
            p=probe;require(&p,delta==0,COH_INVALID);
            if(p.status!=COH_OK)return fail(&p,failure);
            list_table(&p,selected,workspace->slots,count,&result);
            if(p.status!=COH_OK)return fail(&p,failure);
            result.end_bit=p.r.cursor;
            if(count)memcpy(slots,workspace->slots,count*sizeof(*slots));
            *r=p.r;*out=result;clear_failure(failure);return COH_OK;
        }
        require(&p,index>0&&index<=COH_ENT_INDEX_MAX,COH_LIMIT);
        require(&p,result.count<COH_ENT_LIST_MAX,COH_LIMIT);
        if(p.status!=COH_OK)return fail(&p,failure);
        for(i=0;i<result.count;i++)require(&p,index!=workspace->visited[i],COH_INVALID);
        if(p.status!=COH_OK)return fail(&p,failure);
        for(j=0;j<count;j++)if(workspace->slots[j].index==index)break;
        require(&p,j<count,COH_NOT_FOUND);if(p.status!=COH_OK)return fail(&p,failure);
        status=coh_ent_record(&p.r,selected,id,interp,&workspace->slots[j],&record,failure);
        if(status!=COH_OK)return status;
        workspace->visited[result.count++]=index;previous=(int32_t)index;
    }
}
CohStatus coh_ent_deletes(CohRepReader *r,CohEntDeletes *out,CohEntFailure *failure){
    Parse p;CohEntDeletes d={0};uint32_t i,j;
    if(check_reader(r)!=COH_OK||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_DELETES,COH_OK};d.count=pack(&p,1);
    require(&p,d.count<=COH_ENT_DELETE_MAX,COH_LIMIT);if(p.status!=COH_OK)return fail(&p,failure);
    for(i=0;i<d.count;i++){
        d.entries[i].index=pack(&p,12);d.entries[i].entity_id=pack(&p,12);
        require(&p,d.entries[i].index>0&&d.entries[i].index<=COH_ENT_INDEX_MAX&&
            d.entries[i].entity_id>0&&d.entries[i].entity_id<=COH_ENT_GENERATION_MAX,COH_LIMIT);
        for(j=0;j<i;j++)require(&p,d.entries[i].index!=d.entries[j].index,COH_INVALID);
        if(p.status!=COH_OK)return fail(&p,failure);
    }
    d.end_bit=p.r.cursor;*out=d;*r=p.r;clear_failure(failure);return COH_OK;
}
CohStatus coh_ent_stage_deletes(CohEntSlot *slots,size_t count,const CohEntDeletes *d,uint32_t id){
    size_t i,j;if(!slots||!d||!id||count>COH_ENT_DELETE_MAX||d->count>COH_ENT_DELETE_MAX)return COH_INVALID;
    for(i=0;i<count;i++){
        if(!slots[i].index||slots[i].index>COH_ENT_INDEX_MAX||slots[i].present>1)return COH_INVALID;
        for(j=0;j<i;j++)if(slots[i].index==slots[j].index)return COH_INVALID;
    }
    for(i=0;i<d->count;i++){
        if(!d->entries[i].index||d->entries[i].index>COH_ENT_INDEX_MAX||
           !d->entries[i].entity_id||d->entries[i].entity_id>COH_ENT_GENERATION_MAX)return COH_INVALID;
        for(j=0;j<i;j++)if(d->entries[i].index==d->entries[j].index)return COH_INVALID;
        for(j=0;j<count;j++)if(slots[j].index==d->entries[i].index)break;
        /* Caller must retain a tombstone for every referenced index. */
        if(j==count)return COH_NOT_FOUND;
    }
    for(i=0;i<d->count;i++)for(j=0;j<count;j++)if(slots[j].index==d->entries[i].index){
        if(id>slots[j].delete_packet){slots[j].delete_packet=id;slots[j].deleted_entity_id=d->entries[i].entity_id;}
        if(slots[j].present&&slots[j].create_packet<id)slots[j].present=0;
    }
    return COH_OK;
}
CohStatus coh_ent_full_update_tail(CohRepReader *r,CohEntFailure *failure){
    if(check_reader(r)!=COH_OK)return COH_INVALID;
    if(failure){failure->status=COH_UNSUPPORTED;failure->stage=COH_ENT_STAGE_FULL_UPDATE_TAIL;failure->bit=r->cursor;}
    return COH_UNSUPPORTED;
}
