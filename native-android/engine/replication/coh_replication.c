#include "coh_replication.h"
#include <math.h>
#include <string.h>

#define GET(r,n,v) do { CohStatus s_=coh_rep_read((r),(n),&(v)); if(s_!=COH_OK)return s_; } while(0)
#define PACK(r,n,v) do { CohStatus s_=coh_rep_pack((r),(n),&(v)); if(s_!=COH_OK)return s_; } while(0)
#define CALL(expr) do { CohStatus s_=(expr); if(s_!=COH_OK)return s_; } while(0)
static int valid(const CohRepReader *r) {
    return r && r->bytes.size<=COH_REP_MESSAGE_MAX &&
        (r->bytes.data || !r->bytes.size) && r->bits<=r->bytes.size*8 &&
        r->cursor<=r->bits && r->compressed<=1 &&
        (!r->compressed || !(r->cursor&7));
}
CohStatus coh_rep_reader(CohRepReader *r,CohBytes b,size_t bits,int compressed) {
    if(!r || b.size>COH_REP_MESSAGE_MAX || (!b.data && b.size) ||
        bits>b.size*8 || (compressed!=0 && compressed!=1))return COH_INVALID;
    CohRepReader q={b,bits,0,(unsigned)compressed};*r=q;return COH_OK;
}
CohStatus coh_rep_read(CohRepReader *r,unsigned width,uint32_t *out) {
    if(!valid(r)||!out||width>32)return COH_INVALID;
    unsigned n=r->compressed?(width+7)&~7u:width;
    if(n>r->bits-r->cursor)return COH_INVALID;
    uint32_t v=0;for(unsigned i=0;i<n;i++) {
        size_t at=r->cursor+i;v|=(uint32_t)((r->bytes.data[at/8]>>(at&7))&1u)<<i;
    }
    r->cursor+=n;*out=v;return COH_OK;
}
CohStatus coh_rep_pack(CohRepReader *r,unsigned width,uint32_t *out) {
    if(!valid(r)||!out||!width||width>32)return COH_INVALID;
    CohRepReader q=*r;uint64_t base=0;uint32_t v;
    if(q.compressed) {CALL(coh_rep_read(&q,32,&v));*r=q;*out=v;return COH_OK;}
    for(;;) {
        GET(&q,width,v);
        if(width==32 || v<((1u<<width)-1u)) {
            if(base+v>UINT32_MAX)return COH_INVALID;
            *out=(uint32_t)(base+v);*r=q;return COH_OK;
        }
        base+=v;width=width>16?32:width*2;
    }
}
CohStatus coh_rep_string(CohRepReader *r,char *out,size_t cap) {
    if(!valid(r)||!out||!cap||cap>COH_REP_NAME_MAX)return COH_INVALID;
    CohRepReader q=*r;char buf[COH_REP_NAME_MAX];
    for(size_t i=0;i<cap;i++) {
        uint32_t c;GET(&q,8,c);buf[i]=(char)c;
        if(!c){memcpy(out,buf,i+1);*r=q;return COH_OK;}
    }
    return COH_LIMIT;
}
static CohStatus f32(CohRepReader *r,float *out) {
    CohRepReader q=*r;uint32_t u;GET(&q,32,u);float f;memcpy(&f,&u,4);
    if(!isfinite(f))return COH_INVALID;
    *out=f;*r=q;return COH_OK;
}
static CohStatus boolean(CohRepReader *r,uint32_t *out) {
    CohRepReader q=*r;uint32_t u;GET(&q,1,u);if(u>1)return COH_INVALID;*r=q;*out=u;return COH_OK;
}
static CohStatus auto_bits(CohRepReader *r,uint32_t *out) {
    static const unsigned widths[]={2,10,24,32};
    CohRepReader q=*r;uint32_t bin;GET(&q,2,bin);if(bin>3)return COH_INVALID;
    uint32_t u;GET(&q,widths[bin],u);*r=q;*out=u;return COH_OK;
}
CohStatus coh_rep_connect(CohRepReader *r,CohRepConnect *out) {
    if(!valid(r)||!out)return COH_INVALID;
    CohRepReader q=*r;CohRepConnect v={0};PACK(&q,1,v.accepted);
    if(v.accepted>1)return COH_INVALID;
    if(v.accepted)CALL(f32(&q,&v.timezone_delta));
    else {char error[COH_REP_NAME_MAX];CALL(coh_rep_string(&q,error,sizeof(error)));}
    /* The remote error text is intentionally discarded, never diagnosed. */
    *r=q;*out=v;return COH_OK;
}
static uint8_t shortcut_kind(const char *s) {
    static const char *names[]={"time","timescale","timestepscale","pause",
        "disablegurneys","nodynamiccollisions","noentcollisions","pvpmap",
        "svr_fog_dist","svr_fog_color"};
    for(unsigned i=0;i<10;i++)if(!strcmp(s,names[i]))return (uint8_t)(i+1);
    return 0;
}
CohStatus coh_rep_shortcuts(CohRepReader *r,CohRepSchema *out) {
    if(!valid(r)||!out)return COH_INVALID;
    CohRepReader q=*r;CohRepSchema v={0};char name[COH_REP_NAME_MAX];
    for(;;) {
        uint32_t id;PACK(&q,1,id);if(id==UINT32_MAX)break;
        if(!id||id>UINT16_MAX)return COH_INVALID;
        if(v.count==COH_REP_SHORTCUT_MAX)return COH_LIMIT;
        for(size_t i=0;i<v.count;i++)if(v.entries[i].id==id)return COH_INVALID;
        CALL(coh_rep_string(&q,name,sizeof(name)));
        v.entries[v.count++]=(CohRepShortcut){(uint16_t)id,shortcut_kind(name)};
    }
    /* The access-filtered server_cmds list is independent of the shortcut
     * schema. Discard names one at a time; never allocate n strings or let
     * their names authorize native command execution. */
    uint32_t n;PACK(&q,1,n);if(n>COH_REP_ACCESSIBLE_COMMAND_MAX)return COH_LIMIT;
    for(uint32_t i=0;i<n;i++)CALL(coh_rep_string(&q,name,sizeof(name)));
    v.accessible_commands=n;*r=q;*out=v;return COH_OK;
}
CohStatus coh_rep_scene_prefix(CohRepReader *r,CohRepScenePrefix *out) {
    if(!valid(r)||!out)return COH_INVALID;
    CohRepReader q=*r;CohRepScenePrefix v={0};
    PACK(&q,1,v.undo_count);PACK(&q,1,v.redo_count);CALL(boolean(&q,&v.new_world));
    if(v.new_world) {
        GET(&q,2,v.mission_map);if(v.mission_map>2)return COH_INVALID;
        PACK(&q,1,v.instance_id);PACK(&q,1,v.no_auto_group);PACK(&q,1,v.base_map_id);
        CALL(auto_bits(&q,&v.intro_zone));PACK(&q,3,v.team_area);
        uint32_t pages;CALL(boolean(&q,&pages));if(pages) {
            CALL(auto_bits(&q,&v.page_count));if(v.page_count>32)return COH_LIMIT;
            char name[COH_REP_NAME_MAX];for(uint32_t i=0;i<v.page_count;i++)CALL(coh_rep_string(&q,name,sizeof(name)));
        }
        CALL(coh_rep_string(&q,v.loadscreen,sizeof(v.loadscreen)));
        CALL(coh_rep_string(&q,v.map_path,sizeof(v.map_path)));
    }
    CALL(boolean(&q,&v.beacons_loaded));v.group_tail_bit=q.cursor;
    *r=q;*out=v;return COH_OK;
}
CohStatus coh_rep_update_prefix(CohRepReader *r,const CohRepSchema *schema,uint32_t cmd,CohRepUpdatePrefix *out) {
    if(!valid(r)||!schema||schema->count>COH_REP_SHORTCUT_MAX||!out ||
        (cmd!=COH_REP_UPDATE&&cmd!=COH_REP_ALLENTS))return COH_INVALID;
    CohRepReader q=*r;CohRepUpdatePrefix v={0};v.command=cmd;
    if(cmd==COH_REP_ALLENTS)PACK(&q,1,v.full_update_id);
    CALL(boolean(&q,&v.odd_send));
    for(;;) {
        uint32_t id;PACK(&q,1,id);if(!id)break;
        if(v.command_count++>=COH_REP_SHORTCUT_MAX)return COH_LIMIT;
        uint8_t kind=0;for(size_t i=0;i<schema->count;i++)if(schema->entries[i].id==id)kind=schema->entries[i].kind;
        if(!kind||kind>10)return COH_UNSUPPORTED;
        if(kind>=4&&kind<=8){uint32_t u;PACK(&q,1,u);}
        else {float f;CALL(f32(&q,&f));if(kind==10){CALL(f32(&q,&f));CALL(f32(&q,&f));}}
    }
    GET(&q,32,v.abs_time);GET(&q,32,v.db_seconds);
    uint32_t normal;CALL(boolean(&q,&normal));
    if(normal){v.interp_level=2;v.interp_precision=1;}
    else {
        CALL(boolean(&q,&v.has_debug_info));uint32_t interp;CALL(boolean(&q,&interp));
        if(interp){GET(&q,2,v.interp_level);GET(&q,2,v.interp_precision);if(v.interp_level>3||v.interp_precision>3)return COH_INVALID;}
    }
    v.entity_tail_bit=q.cursor;*r=q;*out=v;return COH_OK;
}
void coh_rep_position_init(CohRepPosition *p) {
    if(!p)return;
    memset(p,0,sizeof(*p));for(unsigned i=0;i<3;i++)p->packed[i]=1u<<23;
}
CohStatus coh_rep_position(CohRepReader *r,uint32_t id,CohRepPosition *out) {
    if(!valid(r)||!out||!id)return COH_INVALID;
    CohRepReader q=*r;CohRepPosition p=*out;uint32_t update;GET(&q,3,update);
    if(update>7)return COH_INVALID;
    if(update) {
        unsigned shift=update-1,lo=update==7?0:shift,hi=update==7?24:shift+8;
        if(update!=7&&!p.valid)return COH_STATE;
        uint32_t values[3];for(unsigned j=0;j<3;j++)GET(&q,update==7?24:8,values[j]);
        for(unsigned bit=lo;bit<hi;bit++)if(id>=p.packet_ids[bit]) {
            uint32_t mask=1u<<bit;for(unsigned j=0;j<3;j++) {
                uint32_t u=update==7?values[j]:values[j]<<shift;
                p.packed[j]=(p.packed[j]&~mask)|(u&mask);
            }
            p.packet_ids[bit]=id;
        }
        p.position.x=((int32_t)p.packed[0]-(1<<23))/64.0f;
        p.position.y=((int32_t)p.packed[1]-(1<<23))/64.0f;
        p.position.z=((int32_t)p.packed[2]-(1<<23))/64.0f;p.valid=1;
    }
    *r=q;*out=p;return COH_OK;
}
CohStatus coh_rep_physics(CohRepReader *r,CohRepPhysics *out) {
    if(!valid(r)||!out)return COH_INVALID;
    CohRepReader q=*r;CohRepPhysics p={0};CALL(boolean(&q,&p.position_changed));
    p.has_id=p.position_changed;if(!p.has_id)CALL(boolean(&q,&p.has_id));
    if(p.has_id)GET(&q,16,p.net_id);
    if(p.position_changed) {
        CALL(f32(&q,&p.position.x));CALL(f32(&q,&p.position.y));CALL(f32(&q,&p.position.z));
        float *v[3]={&p.velocity.x,&p.velocity.y,&p.velocity.z};
        for(unsigned i=0;i<3;i++){uint32_t set;CALL(boolean(&q,&set));if(set)CALL(f32(&q,v[i]));}
    }
    uint32_t recording;CALL(boolean(&q,&recording));if(recording)return COH_UNSUPPORTED;
    *r=q;*out=p;return COH_OK;
}
void coh_rep_session_init(CohRepSession *s){if(s)memset(s,0,sizeof(*s));}
CohStatus coh_rep_session_begin(CohRepSession *s,uint32_t dbid) {
    if(!s||!dbid)return COH_INVALID;
    if(s->phase!=COH_REP_DISCONNECTED)return COH_STATE;
    if(s->generation==UINT32_MAX)return COH_LIMIT;
    s->generation++;s->schema_generation=0;s->selected_dbid=dbid;s->phase=COH_REP_WAIT_MAP;return COH_OK;
}
void coh_rep_session_disconnect(CohRepSession *s) {
    if(!s)return;
    s->disconnects++;s->phase=COH_REP_DISCONNECTED;s->selected_dbid=0;s->schema_generation=0;
    memset(&s->scene,0,sizeof(s->scene));memset(&s->update,0,sizeof(s->update));
}
CohStatus coh_rep_session_message(CohRepSession *s,CohRepSchema *schema,CohBytes b,size_t bits,int compressed,int legacy,int authorized) {
    if(!s||!schema||(legacy!=0&&legacy!=1)||(authorized!=0&&authorized!=1))return COH_INVALID;
    if(!authorized||s->phase==COH_REP_DISCONNECTED)return COH_STATE;
    CohRepReader r;CohStatus result=coh_rep_reader(&r,b,bits,compressed);
    if(result!=COH_OK){s->malformed++;return result;}
    uint32_t cmd;result=coh_rep_pack(&r,1,&cmd);
    if(result==COH_OK&&legacy){if(cmd<7)result=COH_UNSUPPORTED;else cmd-=5;}
    if(result==COH_OK)switch(cmd) {
        case COH_REP_CONNECT_MSG: {
            CohRepConnect v;result=coh_rep_connect(&r,&v);
            if(result==COH_OK&&r.cursor!=r.bits)result=COH_UNSUPPORTED;
            if(result==COH_OK&&v.accepted&&s->phase!=COH_REP_WAIT_MAP)result=COH_STATE;
            if(result==COH_OK){if(v.accepted)s->phase=COH_REP_MAP_CONNECTED;else coh_rep_session_disconnect(s);}
            break;
        }
        case COH_REP_SHORTCUTS: {
            CohRepSchema v;result=coh_rep_shortcuts(&r,&v);
            if(result==COH_OK&&r.cursor!=r.bits)result=COH_UNSUPPORTED;
            if(result==COH_OK){*schema=v;s->schema_generation=s->generation;}
            break;
        }
        case COH_REP_GROUPS: {
            if(s->phase<COH_REP_MAP_CONNECTED){result=COH_STATE;break;}
            CohRepScenePrefix v;result=coh_rep_scene_prefix(&r,&v);
            if(result==COH_OK){s->scene=v;s->phase=COH_REP_SCENE_PREFIX_SEEN;}break;
        }
        case COH_REP_UPDATE:case COH_REP_ALLENTS: {
            if(s->phase<COH_REP_SCENE_PREFIX_SEEN||s->schema_generation!=s->generation){result=COH_STATE;break;}
            CohRepUpdatePrefix v;result=coh_rep_update_prefix(&r,schema,cmd,&v);
            if(result==COH_OK){s->update=v;s->phase=COH_REP_ENTITY_PREFIX_SEEN;}break;
        }
        default:result=COH_UNSUPPORTED;break;
    }
    if(result==COH_OK)s->messages++;
    else if(result==COH_UNSUPPORTED)s->unsupported++;
    else if(result==COH_INVALID||result==COH_LIMIT)s->malformed++;
    return result;
}
