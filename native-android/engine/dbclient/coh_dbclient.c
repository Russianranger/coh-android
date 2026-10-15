#include "coh_dbclient.h"
#include "../../protocol/coh_protocol.h"
#include <math.h>
#include <string.h>
#include <zlib.h>

typedef struct { uint8_t *p; size_t bytes,bits,cursor; int aligned,writing; } Bits;
#define TRY(expr) do { CohStatus status_=(expr); if(status_!=COH_OK)return status_; } while(0)
#define R(n,v) TRY(read_bits(&b,(n),&(v)))
#define P(v) TRY(read_pack(&b,&(v)))
#define S(v) TRY(read_string(&b,(v),sizeof(v)))
/* The accepted scalar kernel caps individual storage at one datagram. Logical
 * assembled messages may be larger. Each scalar gets a bounded borrowed
 * window; its real bit cursor and the existing kernel semantics are preserved. */
static CohStatus kernel(Bits *b,unsigned n,uint32_t *value,int packed) {
    size_t byte=b->cursor/8,offset=b->cursor&7;
    if(byte>b->bytes || b->cursor>b->bits)return COH_INVALID;
    size_t cap=b->bytes-byte;if(cap>COH_PROTOCOL_FRAME_MAX)cap=COH_PROTOCOL_FRAME_MAX;
    size_t bits=b->bits-byte*8;if(bits>cap*8)bits=cap*8;
    CohProtocolBits q;
    if(coh_protocol_bits_init(&q,b->p+byte,cap,bits,b->writing))return COH_INVALID;
    q.cursor=offset;
    int failed=b->writing?(packed?coh_protocol_write_pack(&q,n,*value):coh_protocol_write(&q,n,*value)):
        (packed?coh_protocol_read_pack(&q,n,value):coh_protocol_read(&q,n,value));
    if(failed)return COH_INVALID;
    b->cursor=byte*8+q.cursor;return COH_OK;
}
static CohStatus read_bits(Bits *b,unsigned n,uint32_t *v){return kernel(b,b->aligned?(n+7)&~7u:n,v,0);}
static CohStatus read_pack(Bits *b,uint32_t *v){return kernel(b,b->aligned?32:1,v,!b->aligned);}
static CohStatus write_bits(Bits *b,unsigned n,uint32_t v){return kernel(b,b->aligned?(n+7)&~7u:n,&v,0);}
static CohStatus write_pack(Bits *b,uint32_t v){return kernel(b,b->aligned?32:1,&v,!b->aligned);}
static CohStatus auto_read(Bits *b,uint32_t *v) {
    static const unsigned widths[]={2,10,24,32};uint32_t bin;
    TRY(read_bits(b,2,&bin));if(bin>3)return COH_INVALID;
    return read_bits(b,widths[bin],v);
}
static CohStatus auto_write(Bits *b,uint32_t v) {
    static const unsigned widths[]={2,10,24,32};unsigned bin=0;
    while(bin<3 && v>=(1u<<widths[bin]))bin++;
    TRY(write_bits(b,2,bin));return write_bits(b,widths[bin],v);
}
static size_t bounded_length(const char *s,size_t cap) {
    size_t n=0;while(n<cap&&s[n])n++;return n;
}
static CohStatus read_string(Bits *b,char *out,size_t cap) {
    for(size_t i=0;i<cap;i++){uint32_t c;TRY(read_bits(b,8,&c));out[i]=(char)c;if(!c)return COH_OK;}
    return COH_LIMIT;
}
static CohStatus write_string(Bits *b,const char *s,size_t cap) {
    size_t n=bounded_length(s,cap);if(n==cap)return COH_LIMIT;
    for(size_t i=0;i<=n;i++)TRY(write_bits(b,8,(uint8_t)s[i]));
    return COH_OK;
}
static CohStatus array(Bits *b,uint8_t *v,size_t bytes) {
    size_t at=(b->cursor+7)&~(size_t)7;
    if(at>b->bits || bytes>(b->bits-at)/8)return COH_INVALID;
    if(b->writing)memcpy(b->p+at/8,v,bytes);else memcpy(v,b->p+at/8,bytes);
    b->cursor=at+bytes*8;return COH_OK;
}
static CohStatus float_read(Bits *b,float *v) {
    uint32_t u;TRY(read_bits(b,32,&u));memcpy(v,&u,4);return isfinite(*v)?COH_OK:COH_INVALID;
}
static CohStatus reader(Bits *b,CohBytes bytes,size_t bits,int aligned,int legacy) {
    if(!b||!bytes.data||!bytes.size||bytes.size>COH_DB_MESSAGE_MAX||bits>bytes.size*8||
       (aligned!=0&&aligned!=1)||(legacy!=0&&legacy!=1))return COH_INVALID;
    *b=(Bits){(uint8_t *)(uintptr_t)bytes.data,bytes.size,bits,0,aligned,0};return COH_OK;
}
static CohStatus command(Bits *b,uint32_t expected,int legacy) {
    uint32_t cmd;TRY(read_pack(b,&cmd));return cmd==expected+(legacy?5u:0u)?COH_OK:COH_UNSUPPORTED;
}
void coh_db_wipe(void *p,size_t n){volatile uint8_t *v=(volatile uint8_t *)p;if(v)while(n--)*v++=0;}
static CohStatus login(const CohDbLogin *v,Bits *b,int legacy,int local) {
    if(!v->account[0]||!v->patch_version[0]||!v->protocol_version||(!local&&!v->user_id)||
        (local&&(v->user_id||v->cookie))||
        v->no_timeout>1||v->no_version_check>1)return COH_INVALID;
    /* compress2 matches pktSendZipped exactly, including terminating NUL. */
    size_t raw=bounded_length(v->system_spec,sizeof(v->system_spec));
    if(raw==sizeof(v->system_spec))return COH_LIMIT;
    uint8_t zipped[1100];uLongf zipbytes=sizeof(zipped);
    if(compress2(zipped,&zipbytes,(const uint8_t *)v->system_spec,(uLong)raw+1,5)!=Z_OK)return COH_IO;
    TRY(write_pack(b,COH_DB_LOGIN+(legacy?5u:0u)));
    TRY(write_string(b,v->account,sizeof(v->account)));
    TRY(write_pack(b,v->user_id));TRY(write_pack(b,v->protocol_version));
    TRY(array(b,(uint8_t *)(uintptr_t)v->auth_user_data,COH_DB_AUTH_BYTES));
    TRY(write_pack(b,v->no_version_check));TRY(write_string(b,v->patch_version,sizeof(v->patch_version)));
    TRY(array(b,(uint8_t *)(uintptr_t)v->executable_checksum,16));
    TRY(write_bits(b,32,v->cookie));TRY(write_bits(b,1,v->no_timeout));
    TRY(write_string(b,v->patch_message,sizeof(v->patch_message)));TRY(write_string(b,"",1));
    TRY(write_pack(b,(uint32_t)zipbytes));TRY(write_pack(b,(uint32_t)raw+1));TRY(array(b,zipped,zipbytes));
    TRY(write_pack(b,v->keyed_access_level));
    if(v->keyed_access_level)TRY(write_string(b,v->keyed_access_issued_to,sizeof(v->keyed_access_issued_to)));
    return COH_OK;
}
static CohStatus login_encode(const CohDbLogin *v,int aligned,int legacy,uint8_t *out,size_t cap,size_t *bits,int local) {
    if(!v||!out||!bits||!cap||(aligned!=0&&aligned!=1)||(legacy!=0&&legacy!=1))return COH_INVALID;
    uint8_t tmp[COH_DB_LOGIN_MAX]={0};Bits b={tmp,sizeof(tmp),sizeof(tmp)*8,0,aligned,1};
    CohStatus s=login(v,&b,legacy,local);
    if(s==COH_OK&&(b.cursor+7)/8>cap)s=COH_LIMIT;
    if(s==COH_OK){memcpy(out,tmp,(b.cursor+7)/8);*bits=b.cursor;}
    coh_db_wipe(tmp,sizeof(tmp));return s;
}
CohStatus coh_db_login_encode(const CohDbLogin *v,int aligned,int legacy,uint8_t *out,size_t cap,size_t *bits) {
    return login_encode(v,aligned,legacy,out,cap,bits,0);
}
CohStatus coh_db_local_login_encode(const CohDbLogin *v,int aligned,int legacy,uint8_t *out,size_t cap,size_t *bits) {
    return login_encode(v,aligned,legacy,out,cap,bits,1);
}
CohStatus coh_db_choose_encode(const CohDbChoose *v,int aligned,int legacy,uint8_t *out,size_t cap,size_t *bits) {
    if(!v||!out||!bits||!cap||v->slot>=COH_DB_SLOTS_MAX||!v->name[0]||
       (aligned!=0&&aligned!=1)||(legacy!=0&&legacy!=1))return COH_INVALID;
    uint8_t tmp[160]={0};Bits b={tmp,sizeof(tmp),sizeof(tmp)*8,0,aligned,1};
    TRY(write_pack(&b,COH_DB_CHOOSE_PLAYER+(legacy?5u:0u)));TRY(write_pack(&b,v->slot));
    TRY(write_pack(&b,v->local_map_ip));TRY(write_string(&b,v->name,sizeof(v->name)));TRY(auto_write(&b,v->create_location));
    if((b.cursor+7)/8>cap)return COH_LIMIT;
    memcpy(out,tmp,(b.cursor+7)/8);*bits=b.cursor;return COH_OK;
}
static int ascii_equal(const char *a,const char *b) {
    for(;;a++,b++){unsigned x=(unsigned char)*a,y=(unsigned char)*b;if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;if(!x)return 1;}
}
CohStatus coh_db_players_parse(CohBytes bytes,size_t bits,int aligned,int legacy,CohDbPlayers *out) {
    if(!out)return COH_INVALID;
    Bits b;TRY(reader(&b,bytes,bits,aligned,legacy));TRY(command(&b,COH_DB_SEND_PLAYERS,legacy));
    CohDbPlayers v={0};TRY(auto_read(&b,&v.user_id));
    char ignored[1024];TRY(read_string(&b,ignored,sizeof(ignored)));v.ignored_remote_command=ignored[0]!=0;
    R(1,v.nag_going_rogue);R(1,v.beta_shard);R(1,v.vip_shard);
    if(v.nag_going_rogue>1||v.beta_shard>1||v.vip_shard>1)return COH_INVALID;
    P(v.base_slots);P(v.max_slots);P(v.bonus_slots);P(v.vip);P(v.premium_nag);
    if(v.max_slots>COH_DB_SLOTS_MAX)return COH_LIMIT;
    if(v.vip>1||v.premium_nag>1)return COH_INVALID;
    for(uint32_t i=0;i<v.max_slots;i++) {
        CohDbPlayer *p=&v.players[i];p->wire_slot=i;P(p->level);S(p->name);S(p->player_class);S(p->origin);
        P(p->db_flags);P(p->type);P(p->subtype);TRY(auto_read(&b,&p->type_by_location));P(p->praetorian);
        S(p->primary_power);S(p->secondary_power);P(p->body_type);TRY(float_read(&b,&p->scale));TRY(float_read(&b,&p->bone_scale));
        R(32,p->skin_color);S(p->map_name);P(p->map_seconds);R(32,p->seconds_till_offline);R(32,p->last_online);R(2,p->slot_lock);
        if(p->slot_lock>2)return COH_UNSUPPORTED;
        p->empty=ascii_equal(p->name,"empty");p->visitor=strchr(p->name,':')!=NULL;
        p->invalid=!p->empty&&(!p->name[0]||!p->player_class[0]||!p->origin[0]);
        if(!p->empty&&!p->visitor&&!p->invalid&&!p->slot_lock)v.selectable_count++;
    }
    TRY(array(&b,v.auth_user_data,COH_DB_AUTH_BYTES));TRY(array(&b,v.overridden_auth,COH_DB_AUTH_BYTES));
    if(b.cursor!=bits)return COH_UNSUPPORTED;
    *out=v;return COH_OK;
}
CohStatus coh_db_queue_parse(CohBytes bytes,size_t bits,int aligned,int legacy,CohDbQueue *out) {
    if(!out)return COH_INVALID;
    Bits b;TRY(reader(&b,bytes,bits,aligned,legacy));TRY(command(&b,COH_DB_QUEUE_POSITION,legacy));
    CohDbQueue v;TRY(auto_read(&b,&v.position));TRY(auto_read(&b,&v.count));
    if(b.cursor!=bits)return COH_UNSUPPORTED;
    if(v.position>v.count)return COH_INVALID;
    *out=v;return COH_OK;
}
CohStatus coh_db_map_handoff_parse(CohBytes bytes,size_t bits,int aligned,int legacy,CohAuthMapHandoff *out) {
    if(!out)return COH_INVALID;
    Bits b;TRY(reader(&b,bytes,bits,aligned,legacy));TRY(command(&b,COH_DB_MAP_CONNECT,legacy));
    size_t remain=bits-b.cursor;
    if(remain>7u*68u)return COH_INVALID;
    uint8_t body[64]={0};CohProtocolBits target;
    if(coh_protocol_bits_init(&target,body,sizeof(body),0,1))return COH_INVALID;
    while(b.cursor<bits) {
        unsigned width=(unsigned)(bits-b.cursor);if(width>32)width=32;
        uint32_t value;TRY(kernel(&b,width,&value,0));
        if(coh_protocol_write(&target,width,value))return COH_INVALID;
    }
    return coh_auth_map_handoff_profile((CohBytes){body,(remain+7)/8},remain,aligned,out);
}
CohStatus coh_db_server_error_parse(CohBytes bytes,size_t bits,int aligned,int legacy) {
    Bits b;TRY(reader(&b,bytes,bits,aligned,legacy));TRY(command(&b,COH_DB_MESSAGE,legacy));
    char text[1000];CohStatus s=read_string(&b,text,sizeof(text));coh_db_wipe(text,sizeof(text));
    if(s!=COH_OK)return s;
    return b.cursor==bits?COH_OK:COH_UNSUPPORTED;
}
CohStatus coh_db_player_choose(const CohDbPlayers *players,uint32_t slot,uint32_t ip,uint32_t location,CohDbChoose *out) {
    if(!players||!out||players->max_slots>COH_DB_SLOTS_MAX||slot>=players->max_slots)return COH_INVALID;
    const CohDbPlayer *p=&players->players[slot];
    if(p->wire_slot!=slot||p->empty||p->visitor||p->invalid||p->slot_lock||!p->name[0]||bounded_length(p->name,sizeof(p->name))==sizeof(p->name))return COH_STATE;
    CohDbChoose v={0};v.slot=slot;v.local_map_ip=ip;v.create_location=location;memcpy(v.name,p->name,sizeof(v.name));*out=v;return COH_OK;
}
