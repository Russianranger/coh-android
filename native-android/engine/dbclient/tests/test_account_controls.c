/* New account-control tests only: actual session/parser/protocol, fake UDP. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdalign.h>
#include "../coh_db_account_controls.h"
#include "../../../protocol/coh_protocol.h"
#include "../coh_db_session.c"
#include "account-fixtures.h"
static unsigned checks,cases,transactions,allocations;
#define CHECK(e) do{checks++;if(!(e)){fprintf(stderr,"account-control:%u:%s\n",__LINE__,#e);exit(1);}}while(0)
struct CohNetUdp {CohNetUdpDiagnostics d;CohNetMessage messages[4];unsigned count,next,queues;CohStatus end;};
CohStatus coh_net_udp_config_validate(const CohNetUdpConfig*c){return c&&c->receive_budget?COH_OK:COH_INVALID;}
CohNetUdp*coh_net_udp_create(const CohNetUdpConfig*c){(void)c;CohNetUdp*u=calloc(1,sizeof(*u));if(u){allocations++;u->end=COH_NOT_FOUND;}return u;}
void coh_net_udp_destroy(CohNetUdp*u){if(u){allocations--;coh_db_wipe(u,sizeof(*u));free(u);}}
CohStatus coh_net_udp_begin(CohNetUdp*u,uint32_t id,uint64_t now){(void)now;if(!id)return COH_INVALID;u->d.state=COH_UDP_ACTIVE;u->d.link_state=COH_NET_CONNECTED;return COH_OK;}
CohStatus coh_net_udp_resume(CohNetUdp*u,uint32_t id,uint64_t now){return coh_net_udp_begin(u,id,now);}
CohNetUdpState coh_net_udp_state(const CohNetUdp*u){return u->d.state;}
void coh_net_udp_close(CohNetUdp*u){u->d.state=COH_UDP_CLOSED;}
void coh_net_udp_cancel(CohNetUdp*u){u->d.state=COH_UDP_CANCELLED;}
void coh_net_udp_suspend(CohNetUdp*u){u->d.state=COH_UDP_SUSPENDED;}
CohStatus coh_net_udp_disconnect(CohNetUdp*u,uint64_t now){(void)now;coh_net_udp_close(u);return COH_OK;}
CohStatus coh_net_udp_local_endpoint(const CohNetUdp*u,CohNetEndpoint*out){(void)u;*out=(CohNetEndpoint){{127,0,0,1},1};return COH_OK;}
void coh_net_udp_diagnostics(const CohNetUdp*u,CohNetUdpDiagnostics*out){*out=u->d;}
CohStatus coh_net_udp_service(CohNetUdp*u,uint64_t now,CohCancel cancel){(void)u;(void)now;return cancel.poll&&cancel.poll(cancel.context)?COH_CANCELLED:COH_OK;}
CohStatus coh_net_udp_queue(CohNetUdp*u,CohBytes b,uint32_t bits,int reliable,int ordered,int compressed,uint64_t now){(void)b;(void)bits;(void)reliable;(void)ordered;(void)compressed;(void)now;u->queues++;return COH_OK;}
CohStatus coh_net_udp_next(CohNetUdp*u,CohNetMessage*out){if(u->next==u->count)return u->end;*out=u->messages[u->next++];return COH_OK;}
static CohStatus parse(const uint8_t*data,size_t bytes,size_t bits,int aligned,int legacy,CohDbAccountControl*out){cases++;return coh_db_account_control_parse((CohBytes){data,bytes},bits,aligned,legacy,out);}
static void unchanged(const uint8_t*data,size_t bytes,size_t bits,int aligned,int legacy){CohDbAccountControl out,before;memset(&out,0x5a,sizeof(out));before=out;CHECK(parse(data,bytes,bits,aligned,legacy,&out)!=COH_OK&&!memcmp(&out,&before,sizeof(out)));}
static void fixture_tests(void){
 for(unsigned i=0;i<sizeof(account_fixtures)/sizeof(*account_fixtures);i++){
  const size_t bits=account_fixtures[i].bits,bytes=(bits+7)/8;const uint8_t*p=account_fixtures[i].data;
  unsigned a=account_fixtures[i].aligned,l=account_fixtures[i].legacy,k=account_fixtures[i].kind,n=account_fixtures[i].shards,length=account_fixtures[i].length;
  CohDbAccountControl out={0};CohStatus expected=(length>=COH_DB_ACCOUNT_STRING_MAX||n>COH_DB_ACCOUNT_SHARDS_MAX)?COH_LIMIT:COH_OK;
  CHECK(parse(p,bytes,bits,a,l,&out)==expected);
  if(expected==COH_OK){CHECK(out.command==(k?8u:14u)&&out.shards==n&&out.error_branch==(k&&!n));}
  else unchanged(p,bytes,bits,a,l);
  /* Every truncation bit on compact fixtures, plus string/window boundaries
   * and every one-bit suffix truncation of the long-string fixture. */
  if(bits<4096){for(size_t at=0;at<bits;at++)unchanged(p,bytes,at,a,l);}
  else {for(size_t at=0;at<bits;at+=997)unchanged(p,bytes,at,a,l);for(unsigned at=1;at<=40;at++)unchanged(p,bytes,bits-at,a,l);}
  uint8_t tail[COH_DB_MESSAGE_MAX+1]={0};memcpy(tail,p,bytes);unchanged(tail,bytes+1,bits+1,a,l);unchanged(tail,bytes+1,bits+8,a,l);
 }
}
static void write_scalar(CohProtocolBits*b,unsigned a,unsigned bits,uint32_t value){CHECK(!coh_protocol_write(b,a?(bits+7)&~7u:bits,value));}
static void write_auto(CohProtocolBits*b,unsigned a,uint32_t value){unsigned widths[]={2,10,24,32},bin=0;while(bin<3&&value>=(1u<<widths[bin]))bin++;write_scalar(b,a,2,bin);write_scalar(b,a,widths[bin],value);}
static void write_command(CohProtocolBits*b,unsigned a,unsigned legacy,uint32_t command){CHECK(!(a?coh_protocol_write(b,32,command+(legacy?5u:0u)):coh_protocol_write_pack(b,1,command+(legacy?5u:0u))));}
static void write_string(CohProtocolBits*b,unsigned a,const char*s){do{write_scalar(b,a,8,(uint8_t)*s);}while(*s++);}
static CohNetMessage message(unsigned index){CohNetMessage m={0};m.compressed=(uint8_t)account_fixtures[index].aligned;m.payload_bits=(uint32_t)account_fixtures[index].bits;memcpy(m.payload,account_fixtures[index].data,(m.payload_bits+7)/8);return m;}
static CohNetMessage players(unsigned a,unsigned legacy){CohNetMessage m={0};m.compressed=(uint8_t)a;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,m.payload,COH_PROTOCOL_FRAME_MAX,0,1));write_command(&b,a,legacy,2);write_auto(&b,a,42);write_string(&b,a,"");for(unsigned i=0;i<3;i++)write_scalar(&b,a,1,0);uint32_t setup[]={1,1,0,0,0};for(unsigned i=0;i<5;i++)write_command(&b,a,0,setup[i]);/* command writer is Pack1 scalar in both profiles */
 write_command(&b,a,0,0);write_string(&b,a,"empty");write_string(&b,a,"");write_string(&b,a,"");for(unsigned i=0;i<3;i++)write_command(&b,a,0,0);write_auto(&b,a,0);write_command(&b,a,0,0);write_string(&b,a,"");write_string(&b,a,"");write_command(&b,a,0,0);write_scalar(&b,a,32,0);write_scalar(&b,a,32,0);write_scalar(&b,a,32,0);write_string(&b,a,"");write_command(&b,a,0,0);write_scalar(&b,a,32,0);write_scalar(&b,a,32,0);write_scalar(&b,a,2,0);
 if(b.cursor&7){CHECK(!coh_protocol_write(&b,(unsigned)(8-(b.cursor&7)),0));}
 for(unsigned i=0;i<COH_DB_AUTH_BYTES*2;i++){CHECK(!coh_protocol_write(&b,8,0));}
 m.payload_bits=(uint32_t)b.bit_length;return m;}
static CohDbSession*session(unsigned version,unsigned aligned){CohDbSessionConfig c={0};c.transport.link=(CohNetConfig){version,100,8,3000,10000,10000};c.transport.receive_budget=4;c.request_timeout_ms=1000;c.outbound_compressed=(int)aligned;CohDbSession*s=coh_db_session_create(&c);CHECK(s);CohDbLogin l={0};strcpy(l.account,"fixture");strcpy(l.patch_version,"dev:account-control-fixture");l.user_id=42;l.cookie=77;l.protocol_version=COH_DB_PROTOCOL_VERSION;CohDbAuthReceipt r={0};r.user_id=42;r.game_cookie=77;r.generation=1;r.verified=1;strcpy(r.account,l.account);CHECK(coh_db_session_begin(s,&l,&r,51,100)==COH_OK);CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_OK&&s->diagnostics.phase==COH_DB_WAIT_PLAYERS&&s->phase_start_ms==101&&s->user_id==42);return s;}
static void enqueue(CohDbSession*s,CohNetMessage m){CHECK(s->udp->count<4);s->udp->messages[s->udp->count++]=m;}
static void end(CohDbSession*s){coh_db_session_destroy(s);CHECK(!allocations);transactions++;}
static int cancel(void*p){(*(unsigned*)p)++;return 1;}
static void session_tests(void){for(unsigned a=0;a<2;a++)for(unsigned l=0;l<2;l++){
 unsigned base=a*22+l*11;CohDbSession*s=session(l?3:5,a);enqueue(s,message(base));enqueue(s,message(base+1));enqueue(s,message(base+1));CHECK(coh_db_session_service(s,102,(CohCancel){0})==COH_OK&&s->diagnostics.account_unavailable==1&&s->diagnostics.account_charcounts==2&&s->diagnostics.account_last_error_branch==1&&!s->diagnostics.account_last_shards&&!s->diagnostics.unsupported&&!s->diagnostics.player_lists&&s->diagnostics.phase==COH_DB_WAIT_PLAYERS&&s->phase_start_ms==101&&s->user_id==42&&s->udp->queues==1);
 s->udp->count=s->udp->next=0;enqueue(s,players(a,l));CHECK(coh_db_session_service(s,103,(CohCancel){0})==COH_OK&&s->diagnostics.player_lists==1&&s->diagnostics.phase==COH_DB_CHARACTERS);CohDbPlayers p;CHECK(coh_db_session_players(s,&p)==COH_OK&&p.user_id==42&&p.max_slots==1&&p.players[0].empty);end(s);
 for(unsigned mode=0;mode<9;mode++){
  s=session(l?3:5,a);CohNetMessage m=message(base+1);CohStatus expected=COH_INVALID;
  if(mode==0)m.payload_bits--;
  else if(mode==1){m=message(base);m.payload_bits++;expected=COH_UNSUPPORTED;}
  else if(mode==2){memset(&m,0,sizeof(m));m.compressed=(uint8_t)a;m.payload_bits=sizeof(m.payload)*8;memcpy(m.payload,account_fixtures[base+4].data,sizeof(m.payload));}
  else if(mode==3){m=message(base+8);expected=COH_LIMIT;}
  else if(mode==4){s->diagnostics.phase=COH_DB_QUEUED;expected=COH_STATE;}
  else if(mode==5){s->diagnostics.account_charcounts=UINT64_MAX;expected=COH_LIMIT;}
  else if(mode==6){s->diagnostics.account_unavailable=UINT64_MAX;m=message(base);expected=COH_LIMIT;}
  else if(mode==7){m=message(base);s->udp->end=COH_INVALID;}
  else {m=message(base);m.payload_bits=sizeof(m.payload)*8+1;}
  uint64_t before_count=s->diagnostics.account_charcounts,before_unavailable=s->diagnostics.account_unavailable;enqueue(s,m);CHECK(coh_db_session_service(s,102,(CohCancel){0})==expected&&s->diagnostics.phase==COH_DB_FAILED&&s->diagnostics.account_charcounts==before_count&&s->diagnostics.account_unavailable==before_unavailable+(mode==7)&&!s->diagnostics.player_lists&&!s->diagnostics.choices&&!s->diagnostics.handoffs&&s->udp->d.state==COH_UDP_CLOSED);end(s);
 }
 s=session(l?3:5,a);CohNetMessage unknown={0};CohProtocolBits b;unknown.compressed=(uint8_t)a;CHECK(!coh_protocol_bits_init(&b,unknown.payload,COH_PROTOCOL_FRAME_MAX,0,1));write_command(&b,a,l,21);unknown.payload_bits=(uint32_t)b.bit_length;enqueue(s,message(base));enqueue(s,unknown);CHECK(coh_db_session_service(s,102,(CohCancel){0})==COH_OK&&s->diagnostics.unsupported==1&&s->diagnostics.account_unavailable==1&&!s->diagnostics.player_lists);end(s);
 s=session(l?3:5,a);enqueue(s,message(base));CHECK(coh_db_session_service(s,1101,(CohCancel){0})==COH_STATE&&s->diagnostics.phase==COH_DB_TIMED_OUT&&!s->diagnostics.account_unavailable);end(s);
 s=session(l?3:5,a);enqueue(s,message(base));unsigned polls=0;CHECK(coh_db_session_service(s,102,(CohCancel){cancel,&polls})==COH_CANCELLED&&polls==1&&s->diagnostics.phase==COH_DB_CANCELLED&&!s->diagnostics.account_unavailable);end(s);
}}
static void boundaries(void){
 const uint8_t*p=account_fixtures[0].data;size_t bits=account_fixtures[0].bits;CohDbAccountControl out,before;memset(&out,0x5a,sizeof(out));before=out;
 CHECK(coh_db_account_control_parse((CohBytes){p,(bits+7)/8},bits,0,0,NULL)==COH_INVALID);
 unchanged(p,0,bits,0,0);unchanged(p,(bits+7)/8,bits,2,0);unchanged(p,(bits+7)/8,bits,0,2);unchanged(p,COH_DB_MESSAGE_MAX+1,bits,0,0);unchanged(NULL,1,1,0,0);unchanged((const uint8_t*)(uintptr_t)(UINTPTR_MAX-8),16,1,0,0);
 alignas(CohDbAccountControl)uint8_t alias[64]={0};memcpy(alias,p,(bits+7)/8);CHECK(coh_db_account_control_parse((CohBytes){alias,sizeof(alias)},bits,0,0,(CohDbAccountControl*)(void*)alias)==COH_INVALID);CHECK(coh_db_account_control_parse((CohBytes){p,(bits+7)/8},bits,0,0,(CohDbAccountControl*)(void*)(alias+1))==COH_INVALID);
 CHECK(!memcmp(&out,&before,sizeof(out)));
 for(unsigned a=0;a<2;a++)for(unsigned l=0;l<2;l++){
 uint8_t data[64]={0};CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,data,sizeof(data),0,1));write_command(&b,a,l,8);write_auto(&b,a,UINT32_MAX);unchanged(data,(b.bit_length+7)/8,b.bit_length,a,l);
 memset(data,0,sizeof(data));CHECK(!coh_protocol_bits_init(&b,data,sizeof(data),0,1));write_command(&b,a,l,7);unchanged(data,(b.bit_length+7)/8,b.bit_length,a,l);
 if(l){memset(data,0,sizeof(data));CHECK(!coh_protocol_bits_init(&b,data,sizeof(data),0,1));write_command(&b,a,0,4);unchanged(data,(b.bit_length+7)/8,b.bit_length,a,1);}
 if(a){memset(data,0,sizeof(data));CHECK(!coh_protocol_bits_init(&b,data,sizeof(data),0,1));write_command(&b,a,l,8);write_scalar(&b,a,2,4);unchanged(data,(b.bit_length+7)/8,b.bit_length,a,l);}
 }
}
int main(void){fixture_tests();boundaries();session_tests();CHECK(!allocations);printf("{\"passed\":true,\"checks\":%u,\"parser_cases\":%u,\"session_transactions\":%u,\"control_bytes\":%zu,\"session_bytes\":%zu,\"diagnostics_bytes\":%zu,\"sockets_executed\":false,\"real_auth_or_db\":false,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks,cases,transactions,sizeof(CohDbAccountControl),sizeof(CohDbSession),sizeof(CohDbSessionDiagnostics));return 0;}
