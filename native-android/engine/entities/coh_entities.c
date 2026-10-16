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
        /* Original basepower_Send sends its full-name CRC using BitsAuto.
         * Preserve the unresolved reference; never send BASEPOWER_NOT_FOUND. */
        if(flag(p))c->pet_power_crc=auto_bits(p);
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
static float float32(Parse *p){
    uint32_t bits=scalar(p,32);float value;memcpy(&value,&bits,sizeof(value));
    require(p,isfinite(value),COH_INVALID);return value;
}
static float optional_float32(Parse *p){return flag(p)?float32(p):0;}
static void netfx(Parse *p,CohEntNetFxList *list){
    uint32_t i,j;stage(p,COH_ENT_STAGE_NETFX);list->count=pack(p,1);
    require(p,list->count<=COH_ENT_NETFX_MAX,COH_LIMIT);
    for(i=0;i<list->count&&p->status==COH_OK;i++){
        CohEntNetFx *fx=&list->entries[i];
        fx->command=scalar(p,2);fx->net_id=scalar(p,32);fx->pitch_to_target=flag(p);
        require(p,fx->command>0&&fx->net_id>0,COH_INVALID);
        fx->power_type_flags=opt_bits(p,4);fx->handle=opt_pack(p,12);fx->has_color_tint=flag(p);
        if(fx->has_color_tint){fx->primary_color=scalar(p,32);fx->secondary_color=scalar(p,32);}
        fx->client_timer=opt_pack(p,4);fx->trigger_fx=opt_bits(p,32);
        fx->duration=optional_float32(p);fx->radius=optional_float32(p);
        fx->power=opt_bits(p,4);fx->debris=opt_bits(p,32);fx->origin_type=opt_bits(p,2);
        require(p,fx->client_timer<=INT32_MAX&&fx->origin_type<=1,COH_LIMIT);
        if(fx->origin_type==1)for(j=0;j<3;j++)fx->origin_position[j]=float32(p);
        else{
            fx->origin_entity=opt_pack(p,8);fx->bone_id=pack(p,2);
            require(p,fx->origin_entity<=COH_ENT_INDEX_MAX&&fx->bone_id<=255,COH_LIMIT);
        }
        fx->target_type=opt_bits(p,2);require(p,fx->target_type<=1,COH_LIMIT);
        if(fx->target_type==1)for(j=0;j<3;j++)fx->target_position[j]=float32(p);
        fx->target_entity=opt_pack(p,12);require(p,fx->target_entity<=COH_ENT_INDEX_MAX,COH_LIMIT);
    }
    list->end_bit=p->r.cursor;
}
CohStatus coh_ent_netfx(CohRepReader *r,CohEntNetFxList *out,CohEntFailure *failure){
    Parse p;CohEntNetFxList s={0};if(check_reader(r)!=COH_OK||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_NETFX,COH_OK};netfx(&p,&s);
    if(p.status!=COH_OK)return fail(&p,failure);
    *r=p.r;*out=s;clear_failure(failure);return COH_OK;
}
static void appearance(Parse *p,uint32_t id,CohEntAppearance *state) {
    CohEntAppearance a=*state;uint32_t type;stage(p,COH_ENT_STAGE_APPEARANCE);
    type=opt_pack(p,2);
    if(type){
        memset(a.sequence_name,0,sizeof(a.sequence_name));
        a.type=type;a.npc_index=a.costume_index=0;
        if(type==3){
            a.npc_index=pack(p,12);a.costume_index=pack(p,1);
            require(p,a.npc_index<=INT32_MAX&&a.costume_index<=65535,COH_LIMIT);
            if(flag(p)){char group[260]={0};string(p,group,sizeof(group));if(p->status==COH_OK&&group[0])memcpy(a.world_group,group,sizeof(group));}
            if(pack(p,1))require(p,0,COH_UNSUPPORTED); /* Custom NPC colors. */
        }else if(type==4){
            string(p,a.sequence_name,sizeof(a.sequence_name));
            if(flag(p)){char group[260]={0};string(p,group,sizeof(group));if(p->status==COH_OK&&group[0])memcpy(a.world_group,group,sizeof(group));}
        }else require(p,0,COH_UNSUPPORTED); /* Full/owned costume or unknown type. */
        if(p->status==COH_OK&&id>=state->packet_id){a.packet_id=id;*state=a;}
    }
    if(p->status==COH_OK){
        uint32_t value=opt_bits(p,8);
        /* entReceiveXlucency always applies, including absent -> opaque. */
        if(id>=state->translucency_packet){state->translucency=value;state->translucency_packet=id;}
    }
}
/* All supported source schema scalars use packed absolute values. Original
 * packed writers send signed values through U32; decode two's complement
 * explicitly without implementation-defined uint32_t-to-int32_t conversion. */
static int32_t signed_bits(uint32_t v){return v<=INT32_MAX?(int32_t)v:-1-(int32_t)(UINT32_MAX-v);}
static void stats_leaf(Parse *p,uint32_t id,uint32_t self,uint32_t group,CohEntCharacterStats *s){
    static const unsigned low_map[]={0,1,2,3,5};
    static const unsigned low_bits[]={7,7,5,6,7};
    static const float low_scale[]={1,1,5,.1f,1};
    static const unsigned high_bits[]={6,6,6,8,7,7,6,8};
    static const float high_scale[]={.1f,.1f,.1f,.01f,1,1,.1f,.01f};
    uint32_t mask=0,limit=group==2?2:(self?(group==0?8:7):5);
    require(p,flag(p)==1,COH_UNSUPPORTED); /* embedded struct must exist */
    require(p,flag(p)==1,COH_UNSUPPORTED); /* absolute nested values */
    while(p->status==COH_OK&&flag(p)){
        uint32_t field=pack(p,1),slot;int32_t raw;
        require(p,field<limit,COH_UNSUPPORTED);if(p->status!=COH_OK)return;
        require(p,!(mask&(1u<<field)),COH_INVALID);mask|=1u<<field;
        if(group==2){
            raw=signed_bits(pack(p,4));
            if(p->status==COH_OK&&id>=s->integer_packets[field]){
                s->integers[field]=raw;s->integer_packets[field]=id;s->integer_valid|=1u<<field;
            }
        }else{
            float value;float *out=group?s->maximum:s->current;uint32_t *ids=group?s->maximum_packets:s->current_packets;
            raw=signed_bits(pack(p,self?high_bits[field]:low_bits[field]));
            slot=self?field:low_map[field];value=(float)raw*(self?high_scale[field]:low_scale[field]);
            if(p->status==COH_OK&&id>=ids[slot]){
                out[slot]=value;ids[slot]=id;
                if(group)s->maximum_valid|=1u<<slot;else s->current_valid|=1u<<slot;
            }
        }
    }
}
static void character_stats(Parse *p,uint32_t id,uint32_t self,CohEntCharacterStats *s){
    uint32_t mask=0;stage(p,COH_ENT_STAGE_ATTRIBUTE_SCHEMA);
    while(p->status==COH_OK&&flag(p)){
        uint32_t field=pack(p,1);require(p,field<(self?7u:3u),COH_UNSUPPORTED);
        if(p->status!=COH_OK)return;
        require(p,!(mask&(1u<<field)),COH_INVALID);mask|=1u<<field;
        if(field<3)stats_leaf(p,id,self,field,s);
        else{
            int32_t raw=signed_bits(pack(p,16));uint32_t slot=field-1;
            if(p->status==COH_OK&&id>=s->integer_packets[slot]){
                s->integers[slot]=raw;s->integer_packets[slot]=id;s->integer_valid|=1u<<slot;
            }
        }
    }
}
CohStatus coh_ent_character_stats(CohRepReader *r,uint32_t id,uint32_t self,CohEntCharacterStats *out,CohEntFailure *failure){
    Parse p;CohEntCharacterStats s;if(check_reader(r)!=COH_OK||!id||self>1||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_ATTRIBUTE_SCHEMA,COH_OK};s=*out;character_stats(&p,id,self,&s);
    if(p.status!=COH_OK)return fail(&p,failure);
    *r=p.r;*out=s;clear_failure(failure);return COH_OK;
}
CohStatus coh_ent_appearance(CohRepReader *r,uint32_t id,CohEntAppearance *out,CohEntFailure *failure){
    Parse p;CohEntAppearance s;if(check_reader(r)!=COH_OK||!id||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_APPEARANCE,COH_OK};s=*out;appearance(&p,id,&s);
    if(p.status!=COH_OK)return fail(&p,failure);
    *r=p.r;*out=s;clear_failure(failure);return COH_OK;
}
static void target(Parse *p,uint32_t id,uint32_t self,CohEntTarget *state) {
    CohEntTarget t={0};uint32_t i;stage(p,COH_ENT_STAGE_TARGET);
    if(!flag(p))return;
    t.target=opt_pack(p,12);t.assist=opt_pack(p,12);t.taunter=opt_pack(p,12);
    t.clear_target=flag(p)&&self;t.count=pack(p,2);
    require(p,t.target<=COH_ENT_INDEX_MAX&&t.assist<=COH_ENT_INDEX_MAX&&
        t.taunter<=COH_ENT_INDEX_MAX&&t.count<=COH_ENT_PLACATE_MAX,COH_LIMIT);
    for(i=0;i<t.count&&p->status==COH_OK;i++){
        t.placates[i]=pack(p,12);require(p,t.placates[i]<=COH_ENT_INDEX_MAX,COH_LIMIT);
    }
    if(p->status==COH_OK&&id>=state->packet_id){t.packet_id=id;*state=t;}
}
static void status_effects(Parse *p,uint32_t id,CohEntStatusEffects *state) {
    CohEntStatusEffects s={0};uint32_t i;stage(p,COH_ENT_STAGE_STATUS);
    s.effects=scalar(p,10);s.vision_phases=auto_bits(p);s.exclusive_vision_phase=auto_bits(p);s.count=auto_bits(p);
    require(p,s.count<=COH_ENT_STATUS_MAX,COH_LIMIT);
    for(i=0;i<s.count&&p->status==COH_OK;i++)string(p,s.descriptions[i],sizeof(s.descriptions[i]));
    if(p->status==COH_OK&&id>=state->packet_id){s.packet_id=id;*state=s;}
}
static void inventory_sizes(Parse *p,CohEntInventorySizes *state) {
    CohEntInventorySizes s={0};uint32_t i;stage(p,COH_ENT_STAGE_INVENTORY);
    s.valid=pack(p,1);require(p,s.valid<=1,COH_INVALID);if(!s.valid)return;
    s.count=pack(p,3);require(p,s.count==COH_ENT_INVENTORY_TYPES,COH_UNSUPPORTED);
    for(i=0;i<s.count&&p->status==COH_OK;i++){
        s.total[i]=pack(p,8);s.used[i]=pack(p,8);
        require(p,s.total[i]<=INT32_MAX&&s.used[i]<=INT32_MAX,COH_LIMIT);
    }
    s.auction_total=pack(p,8);s.boost_total=pack(p,8);
    require(p,s.auction_total<=INT32_MAX&&s.boost_total<=INT32_MAX,COH_LIMIT);
    if(p->status==COH_OK)*state=s;
}
CohStatus coh_ent_target(CohRepReader *r,uint32_t id,uint32_t self,CohEntTarget *out,CohEntFailure *failure){
    Parse p;CohEntTarget t;if(check_reader(r)!=COH_OK||!id||self>1||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_TARGET,COH_OK};t=*out;target(&p,id,self,&t);
    if(p.status!=COH_OK)return fail(&p,failure);
    *r=p.r;*out=t;clear_failure(failure);return COH_OK;
}
CohStatus coh_ent_status_effects(CohRepReader *r,uint32_t id,CohEntStatusEffects *out,CohEntFailure *failure){
    Parse p;CohEntStatusEffects s;if(check_reader(r)!=COH_OK||!id||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_STATUS,COH_OK};s=*out;status_effects(&p,id,&s);
    if(p.status!=COH_OK)return fail(&p,failure);
    *r=p.r;*out=s;clear_failure(failure);return COH_OK;
}
CohStatus coh_ent_inventory_sizes(CohRepReader *r,CohEntInventorySizes *out,CohEntFailure *failure){
    Parse p;CohEntInventorySizes s;if(check_reader(r)!=COH_OK||!out)return COH_INVALID;
    p=(Parse){*r,COH_ENT_STAGE_INVENTORY,COH_OK};s=*out;inventory_sizes(&p,&s);
    if(p.status!=COH_OK)return fail(&p,failure);
    *r=p.r;*out=s;clear_failure(failure);return COH_OK;
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
    if(v&&c.pchar_things){netfx(&p,&c.netfx);if(p.status!=COH_OK)return fail(&p,failure);}
    if(c.medium_rare){
        appearance(&p,id,&s.appearance);c.appearance_type=s.appearance.type;
        if(p.status!=COH_OK)return fail(&p,failure);
    }
    if(c.very_rare){
        stage(&p,COH_ENT_STAGE_POWER_CUSTOM);require(&p,0,COH_UNSUPPORTED);return fail(&p,failure);
    }
    stage(&p,COH_ENT_STAGE_RAGDOLL);c.ragdoll_bones=opt_bits(&p,5);
    for(i=0;i<c.ragdoll_bones*3&&p.status==COH_OK;i++)(void)scalar(&p,10);
    if(c.pchar_things){
        stage(&p,COH_ENT_STAGE_CHARACTER_STATS);
        if(flag(&p)&&flag(&p))character_stats(&p,id,0,&s.stats);
        if(p.status!=COH_OK)return fail(&p,failure);
    }
    stage(&p,COH_ENT_STAGE_VISION);s.vision_phases=auto_bits(&p);s.exclusive_vision_phase=auto_bits(&p);s.con_yellow=auto_bits(&p);
    if(c.pchar_things){
        s.combat_mod_shift=auto_bits(&p);target(&p,id,s.identity.is_self,&s.target);
        if(flag(&p))status_effects(&p,id,&s.status_effects);
        if(s.identity.is_self)inventory_sizes(&p,&s.inventory);
        if(p.status!=COH_OK)return fail(&p,failure);
    }
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
