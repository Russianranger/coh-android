/* New received-header wrapper controls only. Real DB session/parser/protocol;
 * fake UDP callbacks, no socket/crypto/server/old test suite. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdalign.h>
#include "../../../../protocol/coh_protocol.h"
static unsigned checks,scenarios,live_allocations,allocation_calls,fail_allocation;
#define CHECK(e) do{checks++;if(!(e)){fprintf(stderr,"prefix-control:%u:%s\n",__LINE__,#e);exit(1);}}while(0)
typedef struct {void *p;size_t bytes;} Allocation;
static Allocation allocations[16];
/* Explicit fixture allocator reuse, including under ASan quarantine. This
 * models a retired session address being reused, not an OS allocation claim. */
static void*retired_storage;static size_t reuse_bytes;static unsigned reuse_storage;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
static void *track(void*p,size_t bytes){if(p){for(unsigned i=0;i<16;i++)if(!allocations[i].p){allocations[i]=(Allocation){p,bytes};live_allocations++;return p;}CHECK(0);}return p;}
void *__wrap_malloc(size_t bytes){if(++allocation_calls==fail_allocation)return NULL;return track(__real_malloc(bytes),bytes);}
void *__wrap_calloc(size_t n,size_t bytes){if(++allocation_calls==fail_allocation)return NULL;if(reuse_storage&&retired_storage&&n==1&&bytes==reuse_bytes){void*p=retired_storage;retired_storage=NULL;memset(p,0,bytes);return track(p,bytes);}return track(__real_calloc(n,bytes),n*bytes);}
void __wrap_free(void*p){if(p){unsigned i=0;for(;i<16;i++)if(allocations[i].p==p)break;CHECK(i<16);size_t bytes=allocations[i].bytes;allocations[i]=(Allocation){0};live_allocations--;if(reuse_storage&&bytes==reuse_bytes){CHECK(!retired_storage);retired_storage=p;return;}}__real_free(p);}

/* The only source inclusion; none of its function bodies are edited. */
#include "wrapped_db_received_prefix.c"
struct CohNetUdp {
 CohNetUdpConfig config;CohNetUdpDiagnostics d;
 CohNetMessage messages[32];unsigned count,next,fetches,queues;
 CohStatus end_status;unsigned active_aliases,reenter,reentered;
 CohDbSession*session;
 uint8_t login[COH_DB_LOGIN_MAX];size_t login_bytes;uint32_t login_bits;
};
static unsigned callbacks;
CohStatus coh_net_udp_config_validate(const CohNetUdpConfig*c){return c&&c->receive_budget?COH_OK:COH_INVALID;}
CohNetUdp*coh_net_udp_create(const CohNetUdpConfig*c){CohNetUdp*u=calloc(1,sizeof(*u));if(u){u->config=*c;u->end_status=COH_NOT_FOUND;}return u;}
void coh_net_udp_destroy(CohNetUdp*u){if(u){coh_db_wipe(u,sizeof(*u));free(u);}}
CohStatus coh_net_udp_begin(CohNetUdp*u,uint32_t id,uint64_t now){(void)now;if(!u||!id)return COH_INVALID;u->d.state=COH_UDP_ACTIVE;u->d.link_state=COH_NET_CONNECTED;return COH_OK;}
CohStatus coh_net_udp_resume(CohNetUdp*u,uint32_t id,uint64_t now){return coh_net_udp_begin(u,id,now);}
CohNetUdpState coh_net_udp_state(const CohNetUdp*u){return u?u->d.state:COH_UDP_FAILED;}
void coh_net_udp_close(CohNetUdp*u){if(u)u->d.state=COH_UDP_CLOSED;}
void coh_net_udp_cancel(CohNetUdp*u){if(u)u->d.state=COH_UDP_CANCELLED;}
void coh_net_udp_suspend(CohNetUdp*u){if(u)u->d.state=COH_UDP_SUSPENDED;}
CohStatus coh_net_udp_disconnect(CohNetUdp*u,uint64_t now){(void)now;if(!u)return COH_INVALID;u->d.state=COH_UDP_CLOSED;return COH_OK;}
CohStatus coh_net_udp_local_endpoint(const CohNetUdp*u,CohNetEndpoint*out){if(!u||!out)return COH_INVALID;*out=u->config.local;return COH_OK;}
void coh_net_udp_diagnostics(const CohNetUdp*u,CohNetUdpDiagnostics*out){CHECK(u&&out);*out=u->d;}
CohStatus coh_net_udp_service(CohNetUdp*u,uint64_t now,CohCancel cancel){
 if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;
 if(u->reenter&&!u->reentered){u->reentered=1;callbacks++;CHECK(coh_db_session_service(u->session,now,(CohCancel){0})==COH_OK);}
 return COH_OK;
}
CohStatus coh_net_udp_queue(CohNetUdp*u,CohBytes bytes,uint32_t bits,int reliable,int ordered,int compressed,uint64_t now){
 (void)now;CHECK(u&&reliable==1&&!ordered&&compressed==u->session->config.outbound_compressed&&bytes.size<=sizeof(u->login));u->queues++;u->login_bytes=bytes.size;u->login_bits=bits;memcpy(u->login,bytes.data,bytes.size);return COH_OK;
}
CohStatus coh_net_udp_next(CohNetUdp*u,CohNetMessage*out){
 CHECK(u&&out);u->fetches++;
 if(u->active_aliases){
  callbacks++;CohDevDbReceivedPrefix report,before;memset(&report,0x5a,sizeof(report));before=report;
  CHECK(coh_dev_db_received_prefix(&report)==COH_STATE&&!memcmp(&report,&before,sizeof(report)));
  memset(out,0x5a,sizeof(*out));CHECK(coh_dev_db_received_prefix((CohDevDbReceivedPrefix*)(void*)out)==COH_INVALID);
  CHECK(((uint8_t*)out)[0]==0x5a&&((uint8_t*)out)[sizeof(*out)-1]==0x5a);
 }
 if(u->next==u->count)return u->end_status;
 *out=u->messages[u->next++];return COH_OK;
}
static CohDevDbReceivedPrefix report(void){CohDevDbReceivedPrefix out={0};CHECK(coh_dev_db_received_prefix(&out)==COH_OK);return out;}
static void reset(void){CHECK(!live_allocations&&!retired_storage);memset(&received,0,sizeof(received));callbacks=0;fail_allocation=0;reuse_storage=0;reuse_bytes=0;}
static CohDbSessionConfig configuration(unsigned version,unsigned compressed){CohDbSessionConfig c={0};c.transport.link=(CohNetConfig){version,100,8,3000,10000,10000};c.transport.local=(CohNetEndpoint){{127,0,0,1},0};c.transport.peer=(CohNetEndpoint){{127,0,0,1},7000};c.transport.receive_budget=4;c.request_timeout_ms=10000;c.outbound_compressed=(int)compressed;return c;}
static void begin(CohDbSession*s,unsigned generation,uint64_t now){CohDbLogin l={0};strcpy(l.account,"fixture");strcpy(l.patch_version,"dev:prefix-fixture");l.user_id=42;l.protocol_version=COH_DB_PROTOCOL_VERSION;l.cookie=77;CohDbAuthReceipt r={0};r.user_id=42;r.game_cookie=77;r.generation=generation;r.verified=1;strcpy(r.account,l.account);CHECK(coh_db_session_begin(s,&l,&r,100+generation,now)==COH_OK);coh_db_wipe(&l,sizeof(l));coh_db_wipe(&r,sizeof(r));}
static CohDbSession*create(unsigned version,unsigned compressed,unsigned observed){CohDbSessionConfig c=configuration(version,compressed);CohDbSession*s=observed?coh_db_session_create(&c):received_original_create(&c);CHECK(s);s->udp->session=s;begin(s,1,100);return s;}
static CohNetMessage header(uint32_t command,unsigned compressed,unsigned legacy){CohNetMessage m={0};m.compressed=(uint8_t)compressed;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,m.payload,128,0,1));CHECK(!(compressed?coh_protocol_write(&b,32,command+(legacy?5u:0u)):coh_protocol_write_pack(&b,1,command+(legacy?5u:0u))));m.payload_bits=(uint32_t)b.bit_length;return m;}
static void enqueue(CohDbSession*s,CohNetMessage m){CohNetUdp*u=s->udp;CHECK(u->count<32);m.id=u->count+1;u->messages[u->count++]=m;}
static void destroy(CohDbSession*s,unsigned observed){if(observed)coh_db_session_destroy(s);else received_original_destroy(s);}
static void end(CohDbSession*s){destroy(s,1);CHECK(!live_allocations);scenarios++;}
static void names(void){reset();CHECK(!strcmp(coh_dev_db_command_name(0),"NONE"));CHECK(!strcmp(coh_dev_db_command_name(1),"UNKNOWN"));CHECK(!strcmp(coh_dev_db_command_name(UINT32_MAX),"UNKNOWN"));
#define CHECK_NAME(value,name) CHECK(!strcmp(coh_dev_db_command_name(value),"DBGAMESERVER_"#name));CHECK(known_kind(value)==value);
 COH_DEV_DB_COMMANDS(CHECK_NAME)
#undef CHECK_NAME
 CHECK(known_kind(22)==COH_DEV_DB_UNKNOWN&&known_kind(0)==COH_DEV_DB_UNKNOWN);CohDevDbReceivedPrefix d=report();CHECK(!d.count&&!d.context_verified&&!d.instances);scenarios++;
}
static void batch_and_parity(unsigned version,unsigned compressed){
 reset();CohDbSession*s=create(version,compressed,1),*plain=create(version,compressed,0);uint32_t ids[]={14,8,8};for(unsigned i=0;i<3;i++){CohNetMessage m=header(ids[i],compressed,version<4);enqueue(s,m);enqueue(plain,m);}
 CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_OK);CohDevDbReceivedPrefix d=report();CHECK(d.context_verified&&!d.retired&&!d.truncated&&d.instances==1&&d.service_calls==1&&d.count==3&&d.total_seen==3);
 for(unsigned i=0;i<3;i++)CHECK(d.entries[i].kind==ids[i]&&d.entries[i].header_decoded&&d.entries[i].phase==COH_DB_WAIT_PLAYERS&&d.entries[i].legacy==(version<4)&&d.entries[i].compressed==compressed);
 CHECK(received_original_service(plain,101,(CohCancel){0})==COH_OK);CohDbSessionDiagnostics a={0},b={0};coh_db_session_diagnostics(s,&a);coh_db_session_diagnostics(plain,&b);CHECK(!memcmp(&a,&b,sizeof(a))&&a.unsupported==3&&!a.player_lists&&a.login_requests==1);CHECK(s->udp->next==plain->udp->next&&s->udp->fetches==plain->udp->fetches&&s->udp->queues==plain->udp->queues&&s->udp->login_bits==plain->udp->login_bits&&s->udp->login_bytes==plain->udp->login_bytes&&!memcmp(s->udp->login,plain->udp->login,s->udp->login_bytes));
 CohDevDbReceivedPrefix before=d;destroy(plain,0);destroy(s,1);d=report();CHECK(d.context_verified&&d.retired&&d.count==3&&!memcmp(d.entries,before.entries,sizeof(d.entries)));CHECK(!live_allocations);scenarios++;
}
static void malformed_and_unknown(unsigned mode){
 reset();CohDbSession*s=create(mode==3?3:5,mode==4,1);CohNetMessage m;
 if(mode==0)m=header(UINT32_MAX,0,0);
 else if(mode==1){m=(CohNetMessage){0};m.payload_bits=0;}
 else if(mode==2){m=(CohNetMessage){0};m.payload[0]=1;m.payload_bits=1;}
 else if(mode==3){m=header(4,0,0);}
 else if(mode==4){m=header(8,1,0);m.payload_bits=31;}
 else m=header(COH_DB_SEND_PLAYERS,0,0);
 enqueue(s,m);CohStatus status=coh_db_session_service(s,101,(CohCancel){0});CohDevDbReceivedPrefix d=report();CHECK(d.context_verified&&d.count==1&&d.total_seen==1);
 if(mode==0)CHECK(status==COH_OK&&d.entries[0].header_decoded&&d.entries[0].kind==COH_DEV_DB_UNKNOWN&&s->diagnostics.unsupported==1);
 else if(mode==5)CHECK(status==COH_INVALID&&d.entries[0].header_decoded&&d.entries[0].kind==COH_DB_SEND_PLAYERS&&s->diagnostics.malformed==1&&!s->diagnostics.unsupported);
 else CHECK(status==COH_INVALID&&!d.entries[0].header_decoded&&d.entries[0].kind==COH_DEV_DB_NO_HEADER&&!s->diagnostics.unsupported);
 end(s);
}
static void stale_decode_failure(void){
 reset();CohDbSession*s=create(5,0,1);enqueue(s,header(14,0,0));s->udp->end_status=COH_INVALID;CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_INVALID);CohDevDbReceivedPrefix d=report();CHECK(d.context_verified&&d.count==1&&d.total_seen==1&&d.entries[0].kind==14&&d.entries[0].header_decoded&&!d.entries[1].kind&&!d.entries[1].header_decoded&&s->diagnostics.unsupported==1&&s->diagnostics.phase==COH_DB_FAILED);end(s);
}
static void cap(unsigned total){reset();CohDbSession*s=create(5,0,1);for(unsigned i=0;i<total;i++)enqueue(s,header(8,0,0));CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_OK);if(total>COH_NET_RX_MAX)CHECK(coh_db_session_service(s,102,(CohCancel){0})==COH_OK);CohDevDbReceivedPrefix d=report();CHECK(d.context_verified&&d.count==(total>16?16:total)&&d.total_seen==total&&d.truncated==(total>16)&&s->diagnostics.unsupported==total);for(unsigned i=0;i<d.count;i++)CHECK(d.entries[i].kind==8&&d.entries[i].header_decoded);end(s);}
static void mutation(unsigned mode){
 reset();CohDbSession*s=create(5,0,1);enqueue(s,header(14,0,0));CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_OK);CohDevDbReceivedPrefix before=report();
 if(mode==0)s->config.transport.link.version=3;
 else if(mode==1)s->diagnostics.generation=2;
 else if(mode==2){coh_db_session_cancel(s);begin(s,2,102);}
 else if(mode==3){s->udp->reenter=1;}
 else {received.d.service_calls=65535;}
 CHECK(coh_db_session_service(s,103,(CohCancel){0})==COH_OK);CohDevDbReceivedPrefix d=report();CHECK(!d.context_verified&&d.count==before.count&&d.total_seen==before.total_seen&&!memcmp(d.entries,before.entries,sizeof(d.entries)));if(mode==3)CHECK(callbacks==1&&s->udp->reentered);end(s);
}
static void second_lifetime(unsigned concurrent){
 reset();if(!concurrent){reuse_storage=1;reuse_bytes=sizeof(CohDbSession);}CohDbSession*s=create(5,0,1);enqueue(s,header(8,0,0));CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_OK);CohDevDbReceivedPrefix before=report();
 if(!concurrent){destroy(s,1);CHECK(retired_storage==s);}CohDbSession*other=create(5,0,1);if(!concurrent)CHECK(other==s&&!retired_storage);enqueue(other,header(14,0,0));CHECK(coh_db_session_service(other,101,(CohCancel){0})==COH_OK);CohDevDbReceivedPrefix d=report();CHECK(!d.context_verified&&d.instances==2&&d.count==before.count&&!memcmp(d.entries,before.entries,sizeof(d.entries)));reuse_storage=0;destroy(other,1);if(concurrent)destroy(s,1);CHECK(!live_allocations);scenarios++;
}
static void mutation_without_service(unsigned mode){
 reset();CohDbSession*s=create(5,0,1);enqueue(s,header(14,0,0));CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_OK);CohDevDbReceivedPrefix before=report();
 if(mode<2)s->config.transport.link.version=3;
 else {coh_db_session_cancel(s);begin(s,2,102);}
 if(!(mode&1)){CohDevDbReceivedPrefix d=report();CHECK(!d.context_verified&&d.count==before.count&&!memcmp(d.entries,before.entries,sizeof(d.entries)));if(mode==0){s->config.transport.link.version=5;CHECK(!report().context_verified);}}
 destroy(s,1);CohDevDbReceivedPrefix d=report();CHECK(!d.context_verified&&d.retired&&d.count==before.count&&!memcmp(d.entries,before.entries,sizeof(d.entries))&&!live_allocations);scenarios++;
}
static void aliases(void){
 reset();CohDbSession*s=create(5,0,1);CHECK(coh_dev_db_received_prefix(NULL)==COH_INVALID);alignas(CohDevDbReceivedPrefix)uint8_t buffer[sizeof(CohDevDbReceivedPrefix)+1];memset(buffer,0x5a,sizeof(buffer));CHECK(coh_dev_db_received_prefix((CohDevDbReceivedPrefix*)(void*)(buffer+1))==COH_INVALID&&buffer[0]==0x5a&&buffer[sizeof(buffer)-1]==0x5a);
 uint8_t before[sizeof(received)];memcpy(before,&received,sizeof(before));CHECK(coh_dev_db_received_prefix((CohDevDbReceivedPrefix*)(void*)&received)==COH_INVALID&&!memcmp(before,&received,sizeof(before)));uint8_t session_before[sizeof(CohDevDbReceivedPrefix)];memcpy(session_before,s,sizeof(session_before));CHECK(coh_dev_db_received_prefix((CohDevDbReceivedPrefix*)(void*)s)==COH_INVALID&&!memcmp(session_before,s,sizeof(session_before)));
 enqueue(s,header(14,0,0));s->udp->active_aliases=1;CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_OK);CHECK(callbacks==2);CohDevDbReceivedPrefix d=report();CHECK(d.context_verified&&d.count==1);end(s);
}
static void saturation(void){reset();CohDbSession*s=create(5,0,1);received.d.total_seen=65534;enqueue(s,header(14,0,0));enqueue(s,header(8,0,0));CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_OK);CohDevDbReceivedPrefix d=report();CHECK(d.context_verified&&d.total_seen==65535&&d.truncated&&d.count==2);end(s);}
static void allocation_refusals(void){for(unsigned i=1;i<=2;i++){reset();fail_allocation=allocation_calls+i;CohDbSessionConfig c=configuration(5,0);CHECK(!coh_db_session_create(&c));CHECK(!live_allocations&&report().instances==0&&!report().context_verified);scenarios++;}reset();CohDbSessionConfig c=configuration(5,0);c.transport.receive_budget=0;CHECK(!coh_db_session_create(&c)&&!report().instances&&!live_allocations);scenarios++;}
int main(void){names();for(unsigned version=3;version<=5;version+=2)for(unsigned compressed=0;compressed<2;compressed++)batch_and_parity(version,compressed);for(unsigned i=0;i<6;i++)malformed_and_unknown(i);stale_decode_failure();cap(16);cap(17);for(unsigned i=0;i<5;i++)mutation(i);second_lifetime(0);second_lifetime(1);for(unsigned i=0;i<4;i++)mutation_without_service(i);aliases();saturation();allocation_refusals();CHECK(!live_allocations&&!retired_storage);printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"prefix_bytes\":%zu,\"wrapper_static_storage_bytes\":%zu,\"entry_bytes\":%zu,\"ordinary_session_bytes\":%zu,\"same_batch_14_8_8\":true,\"ordinary_status_and_counters_parity\":true,\"synthetic_session_address_reuse\":true,\"transport_crypto_mocked\":true,\"real_protocol_and_db_parser\":true,\"native_allocations_balanced\":true,\"sockets_executed\":false,\"real_auth_or_db\":false,\"first_unsupported_attributed\":false,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks,scenarios,sizeof(CohDevDbReceivedPrefix),sizeof(received),sizeof(CohDevDbPrefixEntry),sizeof(CohDbSession));return 0;}
