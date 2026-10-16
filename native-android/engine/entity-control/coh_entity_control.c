#include "coh_entity_control.h"
#include <float.h>
#include <math.h>
#include <string.h>
typedef char control_float32_required[(sizeof(float)==4 && FLT_RADIX==2 && FLT_MANT_DIG==24 && FLT_MAX_EXP==128)?1:-1];
#define CALL(x) do { CohStatus s_=(x); if(s_!=COH_OK)return s_; } while(0)
static CohStatus scalar(CohRepReader *r, unsigned width, uint32_t *out) {
    CALL(coh_rep_read(r,width,out));
    if(width<32 && *out>=(1u<<width))return COH_INVALID;
    return COH_OK;
}
static CohStatus f32(CohRepReader *r,float *out) {
    uint32_t u; CALL(scalar(r,32,&u)); memcpy(out,&u,4);
    return isfinite(*out)?COH_OK:COH_INVALID;
}
static CohStatus vec(CohRepReader *r,CohVec3 *out) {
    CALL(f32(r,&out->x)); CALL(f32(r,&out->y)); return f32(r,&out->z);
}
static CohStatus optional_vec(CohRepReader *r,CohVec3 *out) {
    float *fields[3]={&out->x,&out->y,&out->z};
    for(unsigned i=0;i<3;i++){uint32_t set;CALL(scalar(r,1,&set));if(set)CALL(f32(r,fields[i]));}
    return COH_OK;
}
CohStatus coh_control_surface_value(const CohControlServer *s,unsigned surface,unsigned member,float *out) {
    if(!s||!out||surface>=2||member>=5)return COH_INVALID;
    const uint8_t *p=s->surface_le+4*(surface*5+member);
    uint32_t u=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
    float value;memcpy(&value,&u,4);if(!isfinite(value))return COH_INVALID;
    *out=value;return COH_OK;
}
static CohStatus read_body(CohRepReader *r,CohControlUpdate *v,CohControlStage *stage) {
    uint32_t more;
    *stage=COH_CONTROL_FUTURE_PUSHES;
    for(;;){
        CALL(scalar(r,1,&more));if(!more)break;
        if(v->push_count==COH_CONTROL_PUSH_MAX)return COH_LIMIT;
        CohControlPush *p=&v->pushes[v->push_count++];
        CALL(scalar(r,16,&p->net_id_start));
        CALL(coh_rep_pack(r,5,&p->physics_ticks));
        /* Original producer and consumer storage are U16, do not truncate. */
        if(p->physics_ticks>UINT16_MAX)return COH_INVALID;
        CALL(scalar(r,32,&p->abs_time));CALL(vec(r,&p->velocity));
        CALL(scalar(r,1,&p->knockback_animation));
    }
    *stage=COH_CONTROL_PHYSICS;CALL(coh_rep_physics(r,&v->physics));
    *stage=COH_CONTROL_SERVER;CALL(scalar(r,1,&v->has_server));
    if(v->has_server){
        CALL(scalar(r,8,&v->server.update_id));CALL(vec(r,&v->server.speed));
        CALL(f32(r,&v->server.speed_back));
        *stage=COH_CONTROL_SURFACE;
        /* bsReadBitsArray always aligns, even in ordinary bit mode. Padding
         * bits are skipped exactly as source; they carry no semantic value. */
        size_t padding=(8-(r->cursor&7))&7;
        if(padding>r->bits-r->cursor)return COH_INVALID;
        r->cursor+=padding;
        for(unsigned i=0;i<COH_CONTROL_SURFACE_BYTES;i++){
            uint32_t byte;CALL(scalar(r,8,&byte));v->server.surface_le[i]=(uint8_t)byte;
        }
        for(unsigned i=0;i<10;i++){float ignored;CALL(coh_control_surface_value(&v->server,i/5,i%5,&ignored));}
        *stage=COH_CONTROL_SERVER;CALL(f32(r,&v->server.jump_height));
        for(unsigned i=0;i<COH_CONTROL_FLAG_COUNT;i++){uint32_t flag;CALL(scalar(r,1,&flag));v->server.flags|=flag<<i;}
    }
    *stage=COH_CONTROL_FORCED;CALL(scalar(r,1,&v->has_forced));
    if(v->has_forced){
        CALL(coh_rep_pack(r,1,&v->forced.position_id));
        CALL(vec(r,&v->forced.position));CALL(optional_vec(r,&v->forced.velocity));
        CALL(optional_vec(r,&v->forced.pyr));CALL(coh_rep_pack(r,1,&v->forced.falling));
        if(v->forced.falling>1)return COH_INVALID;
    }
    v->end_bit=r->cursor;return COH_OK;
}
CohStatus coh_control_read(CohRepReader *r,CohControlUpdate *out,CohControlFailure *failure) {
    if(!r||!out)return COH_INVALID;
    CohRepReader q=*r;CohControlUpdate v={0};CohControlStage stage=COH_CONTROL_FUTURE_PUSHES;
    CohStatus result=read_body(&q,&v,&stage);
    if(failure)*failure=(CohControlFailure){result,stage,q.cursor};
    if(result!=COH_OK)return result;
    *r=q;*out=v;return COH_OK;
}
CohStatus coh_control_state_init(CohControlState *out,uint32_t generation) {
    if(!out||!generation)return COH_INVALID;
    CohControlState value={0};value.generation=generation;*out=value;return COH_OK;
}
CohStatus coh_control_stage(CohControlState *state,uint32_t generation,uint32_t packet,const CohControlUpdate *v) {
    if(!state||!v||!generation||!packet)return COH_INVALID;
    if(state->generation!=generation)return COH_STATE;
    /* This helper accepts only decoder outputs. Scalar shape checks prevent
     * accidental misuse but are not a replacement for wire validation. */
    if(v->push_count>COH_CONTROL_PUSH_MAX||v->has_server>1||v->has_forced>1||
       v->physics.has_id>1||v->physics.position_changed>1||
       (v->physics.position_changed&&!v->physics.has_id))return COH_INVALID;
    CohControlState next=*state;
    if(v->physics.has_id && packet>next.physics_position_packet &&
       (v->physics.position_changed||next.physics_position_packet)){
        if(v->physics.position_changed){next.physics=v->physics;next.physics_position_packet=packet;}
        else next.physics.net_id=v->physics.net_id;
        next.physics_valid=1;
    }
    if(v->has_server&&packet>next.server_packet){next.server=v->server;next.server_packet=packet;next.server_valid=1;}
    if(v->has_forced&&packet>next.forced_packet){
        float ignored_pitch=next.forced.pyr.x;
        next.forced=v->forced;next.forced.pyr.x=ignored_pitch;
        next.forced_packet=packet;next.forced_valid=1;
    }
    *state=next;return COH_OK;
}
