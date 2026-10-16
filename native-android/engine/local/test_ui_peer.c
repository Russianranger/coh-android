/* Qualification-only source-layout peer for real Android UI flows. This is
 * never packaged in the APK and never claims an authentic server session. */
#define main accepted_db_test_main
#include "../dbclient/tests/test_db_session.c"
#undef main
#include "../mapclient/coh_mapclient.h"
#include "server-command-fixtures.h"
#include "../mapclient/tests/large_scene_fixture.h"
#include <signal.h>
#include <time.h>

typedef struct {
    Peer db,map;
    CohNetEndpoint db_target,map_target;
    unsigned db_phase,map_phase,lists,choices,handoffs,connects,catalogs,scenes;
    uint32_t selected_slot;
    size_t scene_compressed_bytes,scene_decoded_bytes;
    unsigned closed,failed;
    const char *report;
} UiPeer;
/* Bounded scripted reliable-response replay. It is a test peer cache, not a
 * replacement for the accepted transport implementation used by the app. */
typedef struct {uint32_t request_id;CohNetPacket input;unsigned count;CohNetPacket replies[16];} ReplyCache;
static ReplyCache reply_cache[2][16];static unsigned reply_cursor[2];
static ReplyCache *recording;
static void ui_frame_send(Peer *p,CohNetEndpoint target,unsigned version,const CohNetPacket *packet){
    if(recording){CHECK(recording->count<16);recording->replies[recording->count++]=*packet;}
    frame_send(p,target,version,packet);
}
static void ui_message(Peer *p,CohNetEndpoint target,const uint8_t *data,size_t bits,uint32_t ack,unsigned compressed){
    size_t bytes=(bits+7)/8,count=(bytes+1199)/1200;CHECK(count<=16);
    uint32_t sibling=count>1?++p->sibling:0;
    for(size_t part=0;part<count;part++){
        CohNetPacket m={0};m.id=++p->id;m.compressed=(uint8_t)compressed;
        if(sibling){m.sibling_id=sibling;m.sibling_count=(uint32_t)count;m.sibling_part=(uint32_t)part;}
        m.payload_bits=(uint32_t)(bits-part*1200*8);if(m.payload_bits>1200*8)m.payload_bits=1200*8;
        memcpy(m.payload,data+part*1200,(m.payload_bits+7)/8);m.ack_count=1;m.acks[0]=ack;
        ui_frame_send(p,target,5,&m);
    }
}
static volatile sig_atomic_t stopped;
static void stop_peer(int signal_number){(void)signal_number;stopped=1;}
static uint64_t milliseconds(void){struct timespec t;CHECK(!clock_gettime(CLOCK_MONOTONIC,&t));return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
static void write_report(const UiPeer *u){
    char temporary[4096];int length=snprintf(temporary,sizeof(temporary),"%s.tmp",u->report);
    CHECK(length>0&&(size_t)length<sizeof(temporary));
    FILE *f=fopen(temporary,"w");CHECK(f);
    CHECK(fprintf(f,"{\"schema\":1,\"scripted_source_layout\":true,\"real_server_interoperability\":false,"
        "\"authserver_authenticated\":false,\"live_world\":false,\"failed\":%s,\"pid\":%ld,"
        "\"db_port\":%u,\"map_port\":%u,\"db_phase\":%u,\"map_phase\":%u,"
        "\"character_lists\":%u,\"character_choices\":%u,\"map_handoffs\":%u,\"map_connects\":%u,"
        "\"source_command_catalogs\":%u,\"source_command_count\":%u,\"scene_prefixes\":%u,"
        "\"large_body_fixture\":true,\"scene_tail_parsed\":false,\"scene_decoded_bytes\":%zu,"
        "\"scene_compressed_bytes\":%zu,\"scene_payload_bits\":%zu,\"scene_compressed\":%s,"
        "\"scene_ordered\":false,\"decoded_budget_bytes\":%u,"
        "\"selected_wire_slot\":%u,\"opened_sockets\":2,\"closed_sockets\":%u}\n",
        u->failed?"true":"false",(long)getpid(),u->db.endpoint.port,u->map.endpoint.port,
        u->db_phase,u->map_phase,u->lists,u->choices,u->handoffs,u->connects,u->catalogs,
        SOURCE_ACCESSIBLE_COMMAND_COUNT,u->scenes,u->scene_decoded_bytes,u->scene_compressed_bytes,
        u->scene_decoded_bytes*8,u->scenes?"true":"false",COH_NET_DECODED_MAX,u->selected_slot,u->closed)>0);
    CHECK(!fclose(f));CHECK(!rename(temporary,u->report));
}
static void response(Peer *p,unsigned cmd,CohNetPacket *out,CohProtocolBits *b){
    memset(out,0,sizeof(*out));out->id=++p->id;
    CHECK(coh_protocol_bits_init(b,out->payload,sizeof(out->payload),0,1)==COH_OK);
    CHECK(coh_protocol_write_pack(b,1,cmd)==COH_OK);
}
/* Return the bit cursor just after the modern command; transport control
 * packets have command0 and a following control ID. */
static unsigned read_command(CohNetPacket *p,CohProtocolBits *b){
    uint32_t cmd;CHECK(!p->compressed&&!p->sibling_count);
    CHECK(coh_protocol_bits_init(b,p->payload,sizeof(p->payload),p->payload_bits,0)==COH_OK);
    CHECK(coh_protocol_read_pack(b,1,&cmd)==COH_OK);return cmd;
}
static void handle(UiPeer *u,unsigned map){
    Peer *p=map?&u->map:&u->db;unsigned *phase=map?&u->map_phase:&u->db_phase;
    CohNetEndpoint *target=map?&u->map_target:&u->db_target;
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];struct sockaddr_in address;socklen_t size=sizeof(address);
    ssize_t bytes=recvfrom(p->fd,frame,sizeof(frame),0,(struct sockaddr*)&address,&size);
    CHECK(bytes>0&&size==sizeof(address)&&address.sin_family==AF_INET);
    CHECK(ntohl(address.sin_addr.s_addr)==UINT32_C(0x7f000001));
    CohNetPacket packet;CohStatus decoded=coh_net_frame_decode(5,NULL,0,*phase==0,(CohBytes){frame,(size_t)bytes},&packet);
    if(decoded!=COH_OK&&*phase)decoded=coh_net_frame_decode(5,NULL,0,1,(CohBytes){frame,(size_t)bytes},&packet);
    CHECK(decoded==COH_OK);
    if(*phase==0){memcpy(target->address,&address.sin_addr.s_addr,4);target->port=ntohs(address.sin_port);}
    CHECK(address.sin_port==htons(target->port));
    for(unsigned i=0;i<16;i++)if(reply_cache[map][i].request_id==packet.id){
        ReplyCache *saved=&reply_cache[map][i];
        if(saved->input.connect)CHECK(coh_net_frame_decode(5,NULL,0,1,(CohBytes){frame,(size_t)bytes},&packet)==COH_OK);
        CHECK(packet.payload_bits==saved->input.payload_bits&&packet.compressed==saved->input.compressed&&
            !memcmp(packet.payload,saved->input.payload,(packet.payload_bits+7)/8));
        for(unsigned n=0;n<saved->count;n++)frame_send(p,*target,5,&saved->replies[n]);
        return;
    }
    CohProtocolBits b;unsigned cmd=read_command(&packet,&b);
    if(!cmd&&b.cursor==b.bit_length)return; /* ordinary transport ACK */
    recording=&reply_cache[map][reply_cursor[map]++%16];memset(recording,0,sizeof(*recording));
    recording->request_id=packet.id;recording->input=packet;
    if(*phase==0){
        CHECK(cmd==1&&packet.connect);CohNetPacket reply=control(5,100,2,1,0);
        reply.ack_count=1;reply.acks[0]=packet.id;ui_frame_send(p,*target,5,&reply);*phase=1;
    }else if(!cmd){
        uint32_t control_id;CHECK(coh_protocol_read_pack(&b,1,&control_id)==COH_OK);
        if(control_id==3&&*phase==1){
            CohNetPacket reply=control(5,101,4,0,0);reply.ack_count=1;reply.acks[0]=packet.id;
            ui_frame_send(p,*target,5,&reply);*phase=2;
        }else if(control_id==5){
            CohNetPacket reply=control(5,++p->id,6,0,0);reply.ack_count=1;reply.acks[0]=packet.id;
            ui_frame_send(p,*target,5,&reply);*phase=9;
        }else CHECK(control_id==0);
    }else if(!map&&*phase==2){
        CHECK(cmd==COH_DB_LOGIN);ui_message(p,*target,players0,players0_bits,packet.id,0);
        *phase=3;u->lists++;
    }else if(!map&&*phase==3){
        uint32_t slot,local_ip,location;CHECK(cmd==COH_DB_CHOOSE_PLAYER);
        CHECK(coh_protocol_read_pack(&b,1,&slot)==COH_OK&&slot==0);
        CHECK(coh_protocol_read_pack(&b,1,&local_ip)==COH_OK&&local_ip==0);
        char name[64]={0};unsigned end=0;
        for(unsigned i=0;i<sizeof(name);i++) {
            uint32_t c;CHECK(coh_protocol_read(&b,8,&c)==COH_OK);name[i]=(char)c;
            if(!c){end=1;break;}
        }
        CHECK(end&&!strcmp(name,"Native Fixture"));
        uint32_t bin;CHECK(coh_protocol_read(&b,2,&bin)==COH_OK&&bin==0);
        CHECK(coh_protocol_read(&b,2,&location)==COH_OK&&location==0&&b.cursor==b.bit_length);
        u->selected_slot=slot;u->choices++;
        CohProtocolBits out_bits;CohNetPacket reply;response(p,COH_DB_MAP_CONNECT,&reply,&out_bits);
        uint32_t fields[]={17,5,0x0100007f,0,u->map.endpoint.port,7003,123456};
        for(unsigned i=0;i<7;i++)CHECK(coh_protocol_write_pack(&out_bits,1,fields[i])==COH_OK);
        reply.payload_bits=(uint32_t)out_bits.bit_length;reply.ack_count=1;reply.acks[0]=packet.id;
        ui_frame_send(p,*target,5,&reply);u->handoffs++;*phase=4;
    }else if(map&&*phase==2){
        uint32_t cookie,cod,new_character;CHECK(cmd==COH_MAP_CONNECT);
        CHECK(coh_protocol_read_pack(&b,1,&cookie)==COH_OK&&cookie==123456);
        CHECK(coh_protocol_read(&b,1,&cod)==COH_OK&&cod==0);
        CHECK(coh_protocol_read(&b,1,&new_character)==COH_OK&&new_character==0&&b.cursor==b.bit_length);
        CohProtocolBits out_bits;CohNetPacket reply;response(p,COH_REP_CONNECT_MSG,&reply,&out_bits);
        CHECK(coh_protocol_write_pack(&out_bits,1,1)==COH_OK&&coh_protocol_write(&out_bits,32,0)==COH_OK);
        reply.payload_bits=(uint32_t)out_bits.bit_length;reply.ack_count=1;reply.acks[0]=packet.id;
        ui_frame_send(p,*target,5,&reply);u->connects++;*phase=3;
    }else if(map&&*phase==3){
        CHECK(cmd==COH_MAP_REQSHORTCUTS);
        ui_message(p,*target,source_commands0,source_commands0_bits,packet.id,0);
        u->catalogs++;*phase=4;
    }else if(map&&*phase==4){
        uint32_t stealth;CHECK(cmd==COH_MAP_REQSCENE&&coh_protocol_read(&b,1,&stealth)==COH_OK&&!stealth);
        uint8_t encoded[COH_NET_MESSAGE_MAX];
        u->scene_compressed_bytes=scene_fixture_encode(SCENE_FIXTURE_DECODED_BYTES,COH_REP_GROUPS,0,encoded,sizeof(encoded));
        u->scene_decoded_bytes=SCENE_FIXTURE_DECODED_BYTES;
        ui_message(p,*target,encoded,u->scene_compressed_bytes*8,packet.id,1);u->scenes++;*phase=5;
    }else {u->failed=1;stopped=1;}
    recording=NULL;write_report(u);
}
int main(int argc,char **argv){
    if(argc!=4||strcmp(argv[1],"--serve")||strcmp(argv[2],"--report"))return 2;
    UiPeer u={0};u.report=argv[3];u.selected_slot=UINT32_MAX;u.db=peer_open();u.map=peer_open();
    signal(SIGTERM,stop_peer);signal(SIGINT,stop_peer);uint64_t deadline=milliseconds()+180000;
    write_report(&u);
    printf("{\"pid\":%ld,\"db_port\":%u,\"map_port\":%u,\"scripted_source_layout\":true,\"real_server_interoperability\":false}\n",
        (long)getpid(),u.db.endpoint.port,u.map.endpoint.port);fflush(stdout);
    while(!stopped&&milliseconds()<deadline){
        struct pollfd fds[2]={{u.db.fd,POLLIN,0},{u.map.fd,POLLIN,0}};
        int result=poll(fds,2,100);if(result<0){if(stopped)break;u.failed=1;break;}
        for(unsigned i=0;i<2;i++)if(fds[i].revents&POLLIN)handle(&u,i);
    }
    peer_close(&u.db);peer_close(&u.map);u.closed=2;write_report(&u);return u.failed?1:0;
}
