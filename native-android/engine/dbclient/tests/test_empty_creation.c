#define _POSIX_C_SOURCE 200809L
#include "../coh_db_session.h"
#include "../coh_db_handoff_private.h"
#include <arpa/inet.h>
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
static unsigned checks,scenarios,cancel_probes,close_probes,allocation_refusals,queue_refusals;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"empty creation check %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t bits;}Wire;
typedef struct{unsigned version,aligned,legacy;Wire players,wrong_uid,zero_slots,choose,map,map_wrong_map,map_zero_dbid,map_high_dbid,map_bad_cookie,unknown,error,queued;}Profile;
#include "empty-creation-fixtures.h"
static uint32_t receipt_generation=1;
typedef struct {int fd;CohNetEndpoint endpoint;uint32_t id,sibling;CohNetZip *zip;} Peer;
static struct sockaddr_in addr(CohNetEndpoint endpoint) {
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons(endpoint.port);memcpy(&a.sin_addr.s_addr,endpoint.address,4);return a;
}
static Peer peer_open(void) {
    Peer p={-1,{{127,0,0,1},0},101,50,NULL};p.fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(p.fd>=0);
    struct sockaddr_in a=addr(p.endpoint);CHECK(!bind(p.fd,(struct sockaddr*)&a,sizeof(a)));socklen_t size=sizeof(a);
    CHECK(!getsockname(p.fd,(struct sockaddr*)&a,&size));p.endpoint.port=ntohs(a.sin_port);CHECK(!fcntl(p.fd,F_SETFL,O_NONBLOCK));
    p.zip=coh_net_zip_create();CHECK(p.zip);return p;
}
static void peer_close(Peer *p){CHECK(!close(p->fd));coh_net_zip_destroy(p->zip);}
static void frame_send(Peer *p,CohNetEndpoint target,unsigned version,const CohNetPacket *packet) {
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];size_t size=0;
    CHECK(coh_net_frame_encode(version,NULL,0,packet,frame,sizeof(frame),&size)==COH_OK);
    struct sockaddr_in a=addr(target);CHECK(sendto(p->fd,frame,size,0,(struct sockaddr*)&a,sizeof(a))==(ssize_t)size);
}
static CohNetPacket frame_read(Peer *p,unsigned version,int connecting) {
    struct pollfd pollfd={p->fd,POLLIN,0};CHECK(poll(&pollfd,1,100)==1&&(pollfd.revents&POLLIN));
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];ssize_t size=recv(p->fd,frame,sizeof(frame),0);CHECK(size>0);
    CohNetPacket packet;CHECK(coh_net_frame_decode(version,NULL,0,connecting,(CohBytes){frame,(size_t)size},&packet)==COH_OK);return packet;
}
static CohNetPacket control(unsigned version,uint32_t id,uint32_t command,int has_value,uint32_t value) {
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1));
    if(version>=4&&command!=1){CHECK(!coh_protocol_write_pack(&b,1,0));if(command)CHECK(!coh_protocol_write_pack(&b,1,command));}
    else CHECK(!coh_protocol_write_pack(&b,1,command));
    if(has_value)CHECK(!coh_protocol_write_pack(&b,1,value));
    p.payload_bits=(uint32_t)b.bit_length;return p;
}
static uint32_t command(const CohNetPacket *p,unsigned version,int is_control) {
    CohProtocolBits b;uint32_t c;CHECK(!coh_protocol_bits_init(&b,(uint8_t *)(uintptr_t)p->payload,sizeof(p->payload),p->payload_bits,0));
    CHECK(!(p->compressed?coh_protocol_read(&b,32,&c):coh_protocol_read_pack(&b,1,&c)));
    if(version>=4&&is_control&&!c&&b.cursor<b.bit_length)CHECK(!coh_protocol_read_pack(&b,1,&c));
    return c;
}
static CohDbSessionConfig configuration(Peer *p,unsigned version,int compressed) {
    CohDbSessionConfig c;memset(&c,0,sizeof(c));c.transport.link=coh_net_default_config();c.transport.link.version=version;
    c.transport.peer=p->endpoint;c.transport.local.address[0]=127;c.transport.local.address[3]=1;c.transport.receive_budget=16;
    c.request_timeout_ms=2000;c.outbound_compressed=compressed;return c;
}
static void login_configuration(CohDbLogin *v,CohDbAuthReceipt *auth,uint32_t generation) {
    memset(v,0,sizeof(*v));strcpy(v->account,"fixture");strcpy(v->patch_version,"disposable-native-test");strcpy(v->system_spec,"Disabled");
    v->user_id=12345;v->protocol_version=COH_DB_PROTOCOL_VERSION;v->cookie=0x89abcdef;
    memset(auth,0,sizeof(*auth));auth->user_id=v->user_id;auth->game_cookie=v->cookie;auth->generation=generation;auth->verified=1;strcpy(auth->account,v->account);
}
static CohNetEndpoint local(CohDbSession *s){CohNetEndpoint e;CHECK(coh_db_session_local_endpoint(s,&e)==COH_OK);return e;}
static CohNetPacket handshake_uid(CohDbSession *s,Peer *peer,unsigned version,uint32_t connect_id,uint64_t now,uint32_t uid) {
    CohDbLogin login;CohDbAuthReceipt auth;login_configuration(&login,&auth,receipt_generation);
    login.user_id=auth.user_id=uid;
    if(uid)CHECK(coh_db_session_begin(s,&login,&auth,connect_id,now)==COH_OK);
    else {login.cookie=0;login.no_version_check=1;CHECK(coh_db_session_begin_local(s,&login,1,connect_id,now)==COH_OK);}
    CHECK(coh_db_session_service(s,now,(CohCancel){0})==COH_OK);
    CohNetPacket first=frame_read(peer,version,1);CHECK(command(&first,version,1)==1);
    CohNetEndpoint target=local(s);CohNetPacket reply=control(version,100,2,1,0);reply.ack_count=1;reply.acks[0]=first.id;frame_send(peer,target,version,&reply);
    CHECK(coh_db_session_service(s,now+1,(CohCancel){0})==COH_OK);CohNetPacket ack=frame_read(peer,version,0);CHECK(command(&ack,version,1)==3);
    reply=control(version,101,4,0,0);reply.ack_count=1;reply.acks[0]=ack.id;frame_send(peer,target,version,&reply);
    CHECK(coh_db_session_service(s,now+2,(CohCancel){0})==COH_OK);ack=frame_read(peer,version,0);CHECK(command(&ack,version,1)==0);
    CHECK(coh_db_session_phase(s)==COH_DB_WAIT_PLAYERS);CHECK(coh_db_session_service(s,now+3,(CohCancel){0})==COH_OK);
    CohNetPacket request=frame_read(peer,version,0);CHECK(!request.sibling_count);
    uint8_t decoded[COH_NET_MESSAGE_MAX];const uint8_t *data=request.payload;size_t bytes=(request.payload_bits+7)/8;
    if(request.compressed){CHECK(coh_net_zip_decode(peer->zip,0,(CohBytes){data,bytes},decoded,sizeof(decoded),&bytes)==COH_OK);data=decoded;}
    uint8_t expected[COH_DB_LOGIN_MAX];size_t expected_bits=0;
    CHECK((uid?coh_db_login_encode:coh_db_local_login_encode)(&login,request.compressed,version<4,expected,sizeof(expected),&expected_bits)==COH_OK);
    CHECK(expected_bits==(request.compressed?bytes*8:request.payload_bits)&&!memcmp(data,expected,(expected_bits+7)/8));
    coh_db_wipe(&login,sizeof(login));coh_db_wipe(&auth,sizeof(auth));return request;
}
static CohNetPacket handshake(CohDbSession *s,Peer *peer,unsigned version,uint32_t connect_id,uint64_t now) {
    return handshake_uid(s,peer,version,connect_id,now,12345);
}
static void peer_message(Peer *p,CohNetEndpoint target,unsigned version,const uint8_t *data,size_t bits,int compressed,uint32_t ack) {
    uint8_t zipped[COH_NET_MESSAGE_MAX];size_t bytes=(bits+7)/8;
    if(compressed){CHECK(!(bits&7));CHECK(coh_net_zip_encode(p->zip,0,(CohBytes){data,bytes},zipped,sizeof(zipped),&bytes)==COH_OK);data=zipped;bits=bytes*8;}
    size_t count=(bytes+1199)/1200;uint32_t sibling=count>1?++p->sibling:0;
    for(size_t part=0;part<count;part++) {
        CohNetPacket m;memset(&m,0,sizeof(m));m.id=++p->id;m.compressed=(uint8_t)compressed;
        if(sibling){m.sibling_id=sibling;m.sibling_count=(uint32_t)count;m.sibling_part=(uint32_t)part;}
        m.payload_bits=(uint32_t)(bits-part*1200*8);if(m.payload_bits>1200*8)m.payload_bits=1200*8;
        memcpy(m.payload,data+part*1200,(m.payload_bits+7)/8);if(ack){m.ack_count=1;m.acks[0]=ack;}
        frame_send(p,target,version,&m);
    }
}
static void drain_ack(Peer *peer,unsigned version){CohNetPacket ack=frame_read(peer,version,0);CHECK(command(&ack,version,1)==0);}
/* Link wrapping observes only real allocation boundaries, never private fields. */
typedef struct{void*p;size_t bytes;}Allocation;
static Allocation allocations[4096];static size_t live_allocs,allocation_calls,armed_calls,fail_at;
static CohDbSession*active_owner;static size_t owner_bytes;static int verify_owner_wipe;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
static void *record_allocation(void*p,size_t n){if(p){size_t i;for(i=0;i<4096;i++)if(!allocations[i].p)break;CHECK(i<4096);allocations[i]=(Allocation){p,n};live_allocs++;}return p;}
static int allocation_failure(void){allocation_calls++;if(fail_at&&++armed_calls==fail_at){allocation_refusals++;return 1;}return 0;}
void *__wrap_malloc(size_t n){return allocation_failure()?NULL:record_allocation(__real_malloc(n),n);}
void *__wrap_calloc(size_t n,size_t s){if(s&&n>SIZE_MAX/s)return NULL;return allocation_failure()?NULL:record_allocation(__real_calloc(n,s),n*s);}
void __wrap_free(void*p){if(p){for(unsigned i=0;i<4096;i++)if(allocations[i].p==p){if(p==active_owner&&verify_owner_wipe){for(size_t j=0;j<allocations[i].bytes;j++)CHECK(!((const uint8_t*)p)[j]);active_owner=NULL;}allocations[i]=(Allocation){0};live_allocs--;break;}}__real_free(p);}
static void arm_failure(size_t n){armed_calls=0;fail_at=n;}
static void remember_owner(CohDbSession*s){active_owner=s;verify_owner_wipe=1;for(unsigned i=0;i<4096;i++)if(allocations[i].p==s){if(owner_bytes)CHECK(owner_bytes==allocations[i].bytes);owner_bytes=allocations[i].bytes;return;}CHECK(0);}
static unsigned allocator_calls;
static void *forbidden_allocate(void*p,size_t n){(void)p;(void)n;allocator_calls++;return NULL;}
static void forbidden_free(void*p,void*q,size_t n){(void)p;(void)q;(void)n;CHECK(0);}
static void take_guards(CohDbSession*s){CohDbSessionDiagnostics before,after;coh_db_session_diagnostics(s,&before);CohDbSessionHandoff raw,copy;memset(&raw,0xa5,sizeof(raw));copy=raw;size_t allocated=allocation_calls;unsigned calls=allocator_calls;CHECK(coh_db_session_take_handoff(s,&raw)==COH_STATE&&!memcmp(&raw,&copy,sizeof(raw)));CohDbHandoffOwner*owner=NULL;CohDbHandoffAllocator a={NULL,forbidden_allocate,forbidden_free};CHECK(coh_db_session_take_handoff_owner_alloc(s,&a,&owner)==COH_STATE&&!owner);CHECK(coh_db_session_take_handoff_owner(s,&owner)==COH_STATE&&!owner);CHECK(allocation_calls==allocated&&allocator_calls==calls);coh_db_session_diagnostics(s,&after);CHECK(before.phase==after.phase&&before.disconnects==after.disconnects&&before.choices==after.choices&&before.handoffs==after.handoffs);}
static int close_arm;static CohDbCreatedOfferPolicy close_policy;
int __real_close(int);
int __wrap_close(int fd){if(close_arm&&active_owner){close_arm=0;take_guards(active_owner);CohDbCreatedOfferSummary out,before;memset(&out,0xa5,sizeof(out));before=out;CHECK(coh_db_session_retire_created_offer(active_owner,&close_policy,&out)==COH_STATE&&!memcmp(&out,&before,sizeof(out)));close_probes++;}return __real_close(fd);}
static int queue_capture,fill_queue;static unsigned captured_queues;static size_t captured_bits;static uint8_t captured_payload[160];
CohStatus __real_coh_net_udp_queue(CohNetUdp*,CohBytes,uint32_t,int,int,int,uint64_t);
CohStatus __wrap_coh_net_udp_queue(CohNetUdp*u,CohBytes b,uint32_t bits,int reliable,int ordered,int compressed,uint64_t now){if(queue_capture){captured_queues++;CHECK(reliable==1&&!ordered&&b.size<=sizeof(captured_payload));memcpy(captured_payload,b.data,b.size);captured_bits=bits;if(fill_queue){fill_queue=0;uint8_t filler=1;unsigned count=0;while(__real_coh_net_udp_queue(u,(CohBytes){&filler,1},1,1,0,0,now)==COH_OK){count++;CHECK(count<=COH_NET_TX_MAX);}CHECK(count==COH_NET_TX_MAX);queue_refusals++;}}return __real_coh_net_udp_queue(u,b,bits,reliable,ordered,compressed,now);}
typedef struct{Peer peer;CohDbSession*s;const Profile*p;CohNetPacket login;unsigned persistent_row;uint64_t now;}Context;
static Context context(const Profile*p,unsigned kind){Context c;memset(&c,0,sizeof(c));c.p=p;c.peer=peer_open();CohDbSessionConfig cfg=configuration(&c.peer,p->version,(int)p->aligned);c.s=coh_db_session_create(&cfg);CHECK(c.s);remember_owner(c.s);receipt_generation=1;c.login=kind==2?handshake_uid(c.s,&c.peer,p->version,1001,100,0):handshake(c.s,&c.peer,p->version,1001,100);c.now=104;if(kind!=1){Wire w=kind==3?p->wrong_uid:kind==4?p->zero_slots:p->players;peer_message(&c.peer,local(c.s),p->version,w.data,w.bits,(int)p->aligned,c.login.id);CohStatus s=coh_db_session_service(c.s,c.now,(CohCancel){0});if(kind==3)CHECK(s==COH_INVALID&&coh_db_session_phase(c.s)==COH_DB_FAILED);else CHECK(s==COH_OK&&coh_db_session_phase(c.s)==COH_DB_CHARACTERS);drain_ack(&c.peer,p->version);}return c;}
static void finish(Context*c){arm_failure(0);queue_capture=fill_queue=0;close_arm=0;coh_db_session_cancel(c->s);CohDbSessionDiagnostics d;coh_db_session_diagnostics(c->s,&d);CHECK(d.transport.sockets_opened==d.transport.sockets_closed);coh_db_session_destroy(c->s);CHECK(!active_owner);peer_close(&c->peer);CHECK(!live_allocs);scenarios++;}
static CohDbEmptyCreationRequest request(Context*c){CohDbSessionDiagnostics d;coh_db_session_diagnostics(c->s,&d);CohDbEmptyCreationRequest r={0};r.wire_slot=1;r.name=(CohBytes){(const uint8_t*)"New Fixture",11};r.location=COH_DB_CREATE_PRIMAL_HERO;r.expected_session_generation=d.generation;r.expected_receipt_generation=receipt_generation;r.expected_list_generation=d.player_lists;return r;}
static CohDbCreatedOfferPolicy policy(Context*c,unsigned second){CohDbSessionDiagnostics d;coh_db_session_diagnostics(c->s,&d);CohDbCreatedOfferPolicy p={d.generation,receipt_generation,d.selection_generation,1,{{127,0,0,(uint8_t)(second?2:1)},7002}};return p;}
static void create_ok(Context*c){CohDbEmptyCreationRequest r=request(c);queue_capture=1;captured_queues=0;CHECK(coh_db_session_create_empty(c->s,&r,++c->now)==COH_OK);queue_capture=0;CHECK(captured_queues==1&&captured_bits==c->p->choose.bits&&!memcmp(captured_payload,c->p->choose.data,(captured_bits+7)/8));CohDbSessionDiagnostics d;coh_db_session_diagnostics(c->s,&d);CHECK(d.phase==COH_DB_WAIT_MAP&&d.choices==1&&d.selection_generation==1&&!d.handoffs);CHECK(coh_db_session_create_empty(c->s,&r,c->now)==COH_STATE);CohDbPlayers out,before;memset(&out,0xa5,sizeof(out));before=out;CHECK(coh_db_session_players(c->s,&out)==COH_STATE&&!memcmp(&out,&before,sizeof(out)));}
static void pump_create(Context*c){CHECK(coh_db_session_service(c->s,c->now,(CohCancel){0})==COH_OK);CohNetPacket p=frame_read(&c->peer,c->p->version,0);CHECK(command(&p,c->p->version,0)==COH_DB_CHOOSE_PLAYER+(c->p->legacy?5:0));uint8_t raw[COH_NET_MESSAGE_MAX];const uint8_t*b=p.payload;size_t bytes=(p.payload_bits+7)/8;if(p.compressed){CHECK(coh_net_zip_decode(c->peer.zip,0,(CohBytes){b,bytes},raw,sizeof(raw),&bytes)==COH_OK);b=raw;}CHECK((p.compressed?bytes*8:p.payload_bits)==c->p->choose.bits&&!memcmp(b,c->p->choose.data,(c->p->choose.bits+7)/8));c->persistent_row=1;c->login=p;}
static CohStatus deliver(Context*c,Wire w){peer_message(&c->peer,local(c->s),c->p->version,w.data,w.bits,(int)c->p->aligned,c->login.id);CohStatus s=coh_db_session_service(c->s,++c->now,(CohCancel){0});drain_ack(&c->peer,c->p->version);return s;}
static void offer(Context*c){create_ok(c);pump_create(c);CHECK(deliver(c,c->p->map)==COH_OK&&coh_db_session_phase(c->s)==COH_DB_HANDOFF_READY);take_guards(c->s);}
static void normal(const Profile*p,unsigned mismatch){Context c=context(p,0);offer(&c);CohDbCreatedOfferPolicy q=policy(&c,mismatch==1);switch(mismatch){case 2:q.expected_session_generation++;break;case 3:q.expected_receipt_generation++;break;case 4:q.expected_selection_generation++;break;case 5:q.owned_map_id++;break;case 6:q.owned_map_endpoint.port++;break;case 7:q.owned_map_endpoint.address[3]=3;break;case 8:q.owned_map_id=0;break;case 9:memset(q.owned_map_endpoint.address,0,4);break;default:break;}CohDbCreatedOfferSummary out,before;memset(&out,0xa5,sizeof(out));before=out;if(mismatch==0){close_policy=q;close_arm=1;}CohStatus s=coh_db_session_retire_created_offer(c.s,&q,&out);CHECK(s==(mismatch<2?COH_OK:COH_STATE));CHECK(coh_db_session_phase(c.s)==COH_DB_CANCELLED);if(s==COH_OK)CHECK(out.server_allocated_offer_observed==1&&out.private_offer_retired==1&&out.container_uninitialized==1&&!out.persistent_rollback_claimed&&out.session_generation==1&&out.receipt_generation==1&&out.selection_generation==1);else CHECK(!memcmp(&out,&before,sizeof(out)));CHECK(c.persistent_row==1);CHECK(coh_db_session_retire_created_offer(c.s,&q,&out)==COH_STATE);finish(&c);CHECK(c.persistent_row==1);}
static void rejected_request(const Profile*p,unsigned which){Context c=context(p,0);CohDbEmptyCreationRequest r=request(&c),*arg=&r;static const uint8_t longname[64]={'A'};static const uint8_t nulname[3]={'A',0,'B'};static const uint8_t nonascii[1]={255};union{uint64_t align;uint8_t bytes[sizeof(r)+8];}bad;CohStatus expected=COH_INVALID;switch(which){case 0:arg=NULL;break;case 1:arg=(CohDbEmptyCreationRequest*)(void*)c.s;break;case 2:memcpy(bad.bytes+1,&r,sizeof(r));arg=(CohDbEmptyCreationRequest*)(void*)(bad.bytes+1);break;case 3:r.expected_session_generation++;expected=COH_STATE;break;case 4:r.expected_receipt_generation++;expected=COH_STATE;break;case 5:r.expected_list_generation++;expected=COH_STATE;break;case 6:r.expected_session_generation=UINT32_MAX;expected=COH_STATE;break;case 7:r.expected_list_generation=UINT64_MAX;expected=COH_STATE;break;case 8:r.wire_slot=64;break;case 9:r.wire_slot=0;expected=COH_STATE;break;case 10:r.wire_slot=2;expected=COH_STATE;break;case 11:r.wire_slot=3;expected=COH_STATE;break;case 12:r.wire_slot=4;expected=COH_STATE;break;case 13:r.location=(CohDbCreationLocation)0;break;case 14:r.name.data=NULL;break;case 15:r.name.size=0;break;case 16:r.name=(CohBytes){longname,64};break;case 17:r.name=(CohBytes){nulname,3};break;case 18:r.name=(CohBytes){nonascii,1};break;case 19:r.name=(CohBytes){(const uint8_t*)"\177",1};break;case 20:r.name=(CohBytes){(const uint8_t*)c.s,1};break;case 21:r.name=(CohBytes){(const uint8_t*)&r,1};break;case 22:r.name.size=SIZE_MAX;break;case 23:arg=(CohDbEmptyCreationRequest*)(uintptr_t)(UINTPTR_MAX-7);break;case 24:r.name=(CohBytes){(const uint8_t*)"\037",1};break;default:break;}CohDbPlayers list,before;CHECK(coh_db_session_players(c.s,&before)==COH_OK);queue_capture=1;captured_queues=0;CHECK(coh_db_session_create_empty(c.s,arg,which==25?1:c.now+1)==expected);CHECK(!captured_queues);queue_capture=0;CHECK(coh_db_session_phase(c.s)==COH_DB_CHARACTERS&&coh_db_session_players(c.s,&list)==COH_OK&&!memcmp(&list,&before,sizeof(list)));r=request(&c);CHECK(coh_db_session_create_empty(c.s,&r,c.now+1)==COH_STATE);if(which==0){coh_db_session_cancel(c.s);receipt_generation=2;c.login=handshake(c.s,&c.peer,p->version,1002,200);c.now=204;CHECK(deliver(&c,p->players)==COH_OK);r=request(&c);CHECK(coh_db_session_create_empty(c.s,&r,c.now+1)==COH_STATE);}finish(&c);}
static void alias_retirement(const Profile*p){Context c=context(p,0);offer(&c);CohDbCreatedOfferPolicy q=policy(&c,0);CohDbCreatedOfferSummary out,before;memset(&out,0xa5,sizeof(out));before=out;CHECK(coh_db_session_retire_created_offer(c.s,NULL,&out)==COH_INVALID&&!memcmp(&out,&before,sizeof(out)));CHECK(coh_db_session_retire_created_offer(c.s,(CohDbCreatedOfferPolicy*)(void*)c.s,&out)==COH_INVALID);CHECK(coh_db_session_retire_created_offer(c.s,&q,(CohDbCreatedOfferSummary*)(void*)c.s)==COH_INVALID);CHECK(coh_db_session_retire_created_offer(c.s,&q,(CohDbCreatedOfferSummary*)(void*)&q)==COH_INVALID);union{uint64_t align;uint8_t bytes[sizeof(q)+sizeof(out)+8];}bad;memcpy(bad.bytes+1,&q,sizeof(q));CHECK(coh_db_session_retire_created_offer(c.s,(CohDbCreatedOfferPolicy*)(void*)(bad.bytes+1),&out)==COH_INVALID);CHECK(coh_db_session_retire_created_offer(c.s,&q,(CohDbCreatedOfferSummary*)(void*)(bad.bytes+1))==COH_INVALID);CHECK(coh_db_session_phase(c.s)==COH_DB_HANDOFF_READY);CHECK(coh_db_session_retire_created_offer(c.s,&q,&out)==COH_OK&&out.private_offer_retired);finish(&c);}
static int cancellation_probe(void*p){Context*c=p;take_guards(c->s);cancel_probes++;return 1;}
static void cancellation(const Profile*p,unsigned stage){Context c=context(p,0);if(stage)create_ok(&c);if(stage==2){pump_create(&c);CHECK(deliver(&c,p->map)==COH_OK);}CHECK(coh_db_session_service(c.s,++c.now,(CohCancel){cancellation_probe,&c})==COH_CANCELLED);CohDbCreatedOfferSummary out;CohDbCreatedOfferPolicy q=policy(&c,0);CHECK(coh_db_session_retire_created_offer(c.s,&q,&out)==COH_STATE);CohDbEmptyCreationRequest r=request(&c);CHECK(coh_db_session_create_empty(c.s,&r,c.now)==COH_STATE);CHECK(c.persistent_row==(stage==2));finish(&c);}
static void context_rejections(const Profile*p,unsigned kind){Context c=context(p,kind==7?1:kind<5?kind:0);if(kind==5)CHECK(deliver(&c,p->players)==COH_OK);if(kind==6)CHECK(deliver(&c,p->unknown)==COH_OK);if(kind==7){CHECK(deliver(&c,p->queued)==COH_OK);CHECK(deliver(&c,p->players)==COH_OK);}CohDbEmptyCreationRequest r=request(&c);CHECK(coh_db_session_create_empty(c.s,&r,c.now+1)==COH_STATE);CHECK(coh_db_session_create_empty(c.s,NULL,c.now+1)==COH_STATE);finish(&c);}
static void map_refusals(const Profile*p,unsigned which){Context c=context(p,0);create_ok(&c);pump_create(&c);Wire w=which==0?p->map_bad_cookie:which==1?p->map_zero_dbid:which==2?p->map_high_dbid:which==3?p->map_wrong_map:p->error;CohStatus s=deliver(&c,w);CohDbCreatedOfferSummary out,before;memset(&out,0xa5,sizeof(out));before=out;CohDbCreatedOfferPolicy q=policy(&c,0);if(which==3)CHECK(s==COH_OK&&coh_db_session_retire_created_offer(c.s,&q,&out)==COH_STATE);else CHECK(s!=COH_OK&&coh_db_session_retire_created_offer(c.s,&q,&out)==COH_STATE);CHECK(!memcmp(&out,&before,sizeof(out))&&c.persistent_row==1);finish(&c);}
static void duplicate_offer(const Profile*p){Context c=context(p,0);offer(&c);CHECK(deliver(&c,p->map)==COH_STATE&&coh_db_session_phase(c.s)==COH_DB_FAILED);CohDbCreatedOfferPolicy q=policy(&c,0);CohDbCreatedOfferSummary out;CHECK(coh_db_session_retire_created_offer(c.s,&q,&out)==COH_STATE);finish(&c);}
static void queue_full(const Profile*p){Context c=context(p,0);CohDbEmptyCreationRequest r=request(&c);CohDbPlayers list,before;CHECK(coh_db_session_players(c.s,&before)==COH_OK);queue_capture=1;fill_queue=1;CHECK(coh_db_session_create_empty(c.s,&r,++c.now)==COH_LIMIT);queue_capture=0;CHECK(coh_db_session_players(c.s,&list)==COH_OK&&!memcmp(&list,&before,sizeof(list)));CHECK(coh_db_session_create_empty(c.s,&r,c.now)==COH_STATE);finish(&c);}
static void allocation_controls(void){Peer peer=peer_open();CohDbSessionConfig cfg=configuration(&peer,5,0);for(size_t n=1;n<=2;n++){size_t baseline=live_allocs;arm_failure(n);CHECK(!coh_db_session_create(&cfg));arm_failure(0);CHECK(live_allocs==baseline);scenarios++;}CohDbLogin login;CohDbAuthReceipt auth;login_configuration(&login,&auth,1);CohDbSession*s=coh_db_session_create(&cfg);CHECK(s);remember_owner(s);size_t before=allocation_calls;CHECK(coh_db_session_begin(s,&login,&auth,1001,100)==COH_OK);size_t points=allocation_calls-before;CHECK(points>0&&points<32);coh_db_session_cancel(s);coh_db_session_destroy(s);for(size_t n=1;n<=points;n++){s=coh_db_session_create(&cfg);CHECK(s);remember_owner(s);size_t baseline=live_allocs;arm_failure(n);CHECK(coh_db_session_begin(s,&login,&auth,1001,100)==COH_LIMIT);arm_failure(0);CHECK(live_allocs==baseline);coh_db_session_destroy(s);scenarios++;}peer_close(&peer);CHECK(!live_allocs);}
static void queue_allocation_controls(void){const Profile*p=&profiles[1];Context c=context(p,0);CohDbEmptyCreationRequest r=request(&c);size_t before=allocation_calls;CHECK(coh_db_session_create_empty(c.s,&r,++c.now)==COH_OK);size_t points=allocation_calls-before;CHECK(points>0&&points<32);finish(&c);for(size_t n=1;n<=points;n++){c=context(p,0);r=request(&c);CohDbPlayers list,saved;CHECK(coh_db_session_players(c.s,&saved)==COH_OK);size_t baseline=live_allocs;arm_failure(n);CHECK(coh_db_session_create_empty(c.s,&r,++c.now)==COH_LIMIT);arm_failure(0);CHECK(live_allocs==baseline);CHECK(coh_db_session_phase(c.s)==COH_DB_CHARACTERS&&coh_db_session_players(c.s,&list)==COH_OK&&!memcmp(&list,&saved,sizeof(list)));CHECK(coh_db_session_create_empty(c.s,&r,c.now)==COH_STATE);finish(&c);}}
static void ordinary_take(const Profile*p){Context c=context(p,0);CHECK(coh_db_session_choose(c.s,0,0,0,++c.now)==COH_OK);CohDbEmptyCreationRequest rejected=request(&c);CHECK(coh_db_session_create_empty(c.s,&rejected,c.now)==COH_STATE);CHECK(coh_db_session_service(c.s,c.now,(CohCancel){0})==COH_OK);c.login=frame_read(&c.peer,p->version,0);CHECK(deliver(&c,p->map)==COH_OK);CohDbSessionHandoff out;CHECK(coh_db_session_create_empty(c.s,&rejected,c.now)==COH_STATE);CHECK(coh_db_session_take_handoff(c.s,&out)==COH_OK&&out.selected_dbid==17);coh_db_wipe(&out,sizeof(out));finish(&c);}
static unsigned fd_count(void){DIR*d=opendir("/proc/self/fd");CHECK(d);unsigned n=0;while(readdir(d))n++;CHECK(!closedir(d));return n;}
int main(void){CHECK(coh_db_session_create_empty(NULL,NULL,0)==COH_INVALID);CHECK(coh_db_session_retire_created_offer(NULL,NULL,NULL)==COH_INVALID);unsigned fds=fd_count();CHECK(sizeof(profiles)/sizeof(*profiles)==4);for(unsigned p=0;p<4;p++){normal(&profiles[p],0);normal(&profiles[p],1);queue_full(&profiles[p]);ordinary_take(&profiles[p]);for(unsigned k=0;k<5;k++)map_refusals(&profiles[p],k);}const Profile*p=&profiles[0];for(unsigned k=2;k<10;k++)normal(p,k);for(unsigned k=0;k<26;k++)rejected_request(p,k);for(unsigned k=1;k<8;k++)context_rejections(p,k);alias_retirement(p);for(unsigned k=0;k<3;k++)cancellation(p,k);duplicate_offer(p);allocation_controls();queue_allocation_controls();CHECK(!live_allocs&&!active_owner&&!allocator_calls&&close_probes==4&&cancel_probes==3&&queue_refusals==4);CHECK(fd_count()==fds);printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"wire_profiles\":4,\"session_bytes\":%zu,\"allocation_refusals\":%u,\"queue_capacity_refusals\":%u,\"cancel_guard_probes\":%u,\"close_guard_probes\":%u,\"project_live_allocations\":%zu,\"synthetic_receipts\":true,\"real_UDP_queue_and_parser\":true,\"private_handoff_setters\":false,\"actual_Auth_DB_Map_SQL\":false,\"SQL_rollback_claimed\":false,\"ACK_authority\":false}\n",checks,scenarios,owner_bytes,allocation_refusals,queue_refusals,cancel_probes,close_probes,live_allocs);return 0;}
