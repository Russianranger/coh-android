/* New command13 tests and one mixed sequence only. Included old main/helpers
 * are never run as their historical suite. Transport remains a fake in memory. */
#define main historical_account_controls_main_not_called
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "test_account_controls.c"
#pragma GCC diagnostic pop
#undef main
#include "../coh_db_account_inventory.h"
#include "inventory-fixtures.h"
static unsigned inventory_cases;
static CohStatus inv(const uint8_t*data,size_t bytes,size_t bits,int aligned,int legacy,CohDbAccountInventory*out){inventory_cases++;return coh_db_account_inventory_parse((CohBytes){data,bytes},bits,aligned,legacy,out);}
static void inv_refuse(const uint8_t*data,size_t bytes,size_t bits,int aligned,int legacy){CohDbAccountInventory out,before;memset(&out,0x5a,sizeof(out));before=out;CHECK(inv(data,bytes,bits,aligned,legacy,&out)!=COH_OK&&!memcmp(&out,&before,sizeof(out)));}
static unsigned find_fixture(unsigned aligned,unsigned legacy,unsigned items,unsigned authoritative){for(unsigned i=0;i<sizeof(inventory_fixtures)/sizeof(*inventory_fixtures);i++)if(inventory_fixtures[i].aligned==aligned&&inventory_fixtures[i].legacy==legacy&&inventory_fixtures[i].items==items&&inventory_fixtures[i].authoritative==authoritative&&inventory_fixtures[i].shard_bytes<1024)return i;CHECK(0);return 0;}
static CohNetMessage inventory_message(unsigned index){CohNetMessage m={0};m.compressed=(uint8_t)inventory_fixtures[index].aligned;size_t bytes=(inventory_fixtures[index].bits+7)/8;if(bytes>sizeof(m.payload))bytes=sizeof(m.payload);memcpy(m.payload,inventory_fixtures[index].data,bytes);m.payload_bits=(uint32_t)inventory_fixtures[index].bits;if(m.payload_bits>bytes*8)m.payload_bits=(uint32_t)(bytes*8);return m;}
static void inventory_direct(void){
 for(unsigned i=0;i<sizeof(inventory_fixtures)/sizeof(*inventory_fixtures);i++){
  const uint8_t*p=inventory_fixtures[i].data;size_t bits=inventory_fixtures[i].bits,bytes=(bits+7)/8;unsigned a=inventory_fixtures[i].aligned,l=inventory_fixtures[i].legacy;CohDbAccountInventory out={0};CohStatus expected=inventory_fixtures[i].items>COH_DB_ACCOUNT_ITEMS_MAX||inventory_fixtures[i].shard_bytes>COH_DB_ACCOUNT_STRING_MAX?COH_LIMIT:COH_OK;
  CHECK(inv(p,bytes,bits,a,l,&out)==expected);
  if(expected==COH_OK)CHECK(out.items==inventory_fixtures[i].items&&out.wire_authoritative==inventory_fixtures[i].authoritative);else inv_refuse(p,bytes,bits,a,l);
  if(bits<4096){for(size_t n=0;n<bits;n++)inv_refuse(p,bytes,n,a,l);}else{for(size_t n=0;n<bits;n+=997)inv_refuse(p,bytes,n,a,l);for(size_t n=1;n<=40;n++)inv_refuse(p,bytes,bits-n,a,l);}
  uint8_t tail[COH_DB_MESSAGE_MAX+1]={0};CHECK(bytes+1<=sizeof(tail));memcpy(tail,p,bytes);inv_refuse(tail,bytes+1,bits+1,a,l);inv_refuse(tail,bytes+1,bits+8,a,l);
  if(expected==COH_OK&&inventory_fixtures[i].padding_bits){for(unsigned n=0;n<inventory_fixtures[i].padding_bits;n++){size_t at=inventory_fixtures[i].padding_start+n;tail[at/8]|=(uint8_t)(1u<<(at&7));}CHECK(inv(tail,bytes,bits,a,l,&out)==COH_OK&&out.items==inventory_fixtures[i].items);}
 }
}
static void inventory_boundaries(void){
 unsigned f=find_fixture(0,0,0,0);const uint8_t*p=inventory_fixtures[f].data;size_t bits=inventory_fixtures[f].bits,bytes=(bits+7)/8;
 CHECK(coh_db_account_inventory_parse((CohBytes){p,bytes},bits,0,0,NULL)==COH_INVALID);inv_refuse(NULL,1,1,0,0);inv_refuse(p,0,bits,0,0);inv_refuse(p,bytes,bits,2,0);inv_refuse(p,bytes,bits,0,2);inv_refuse(p,COH_DB_MESSAGE_MAX+1,bits,0,0);inv_refuse((const uint8_t*)(uintptr_t)(UINTPTR_MAX-8),16,1,0,0);
 alignas(CohDbAccountInventory)uint8_t alias[256]={0};CHECK(bytes<=sizeof(alias));memcpy(alias,p,bytes);CHECK(coh_db_account_inventory_parse((CohBytes){alias,sizeof(alias)},bits,0,0,(CohDbAccountInventory*)(void*)alias)==COH_INVALID);CHECK(coh_db_account_inventory_parse((CohBytes){p,bytes},bits,0,0,(CohDbAccountInventory*)(void*)(alias+1))==COH_INVALID);
 for(unsigned a=0;a<2;a++)for(unsigned l=0;l<2;l++){
  uint8_t data[256]={0};CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,data,sizeof(data),0,1));write_command(&b,a,l,12);inv_refuse(data,(b.bit_length+7)/8,b.bit_length,a,l);
  if(l){memset(data,0,sizeof(data));CHECK(!coh_protocol_bits_init(&b,data,sizeof(data),0,1));write_command(&b,a,0,4);inv_refuse(data,(b.bit_length+7)/8,b.bit_length,a,1);}
  if(a){unsigned index=find_fixture(a,l,0,0);size_t n=(inventory_fixtures[index].bits+7)/8;CHECK(n<=sizeof(data));for(unsigned at=4;at<=6;at++){memcpy(data,inventory_fixtures[index].data,n);data[at]=at==6?4:2;inv_refuse(data,n,inventory_fixtures[index].bits,a,l);}}
 }
}
static void inventory_sessions(void){
 for(unsigned a=0;a<2;a++)for(unsigned l=0;l<2;l++){
  unsigned base=a*22+l*11,index=find_fixture(a,l,0,0);CohDbSession*s=session(l?3:5,a);enqueue(s,message(base));enqueue(s,message(base+1));enqueue(s,message(base+1));enqueue(s,inventory_message(index));CHECK(coh_db_session_service(s,102,(CohCancel){0})==COH_OK&&s->diagnostics.account_unavailable==1&&s->diagnostics.account_charcounts==2&&s->diagnostics.account_inventories==1&&!s->diagnostics.account_last_inventory_items&&!s->diagnostics.unsupported&&!s->diagnostics.player_lists&&s->diagnostics.phase==COH_DB_WAIT_PLAYERS&&s->phase_start_ms==101&&s->user_id==42&&s->udp->queues==1);
  s->udp->count=s->udp->next=0;enqueue(s,players(a,l));CHECK(coh_db_session_service(s,103,(CohCancel){0})==COH_OK&&s->diagnostics.player_lists==1&&s->diagnostics.phase==COH_DB_CHARACTERS);CohDbPlayers p;CHECK(coh_db_session_players(s,&p)==COH_OK&&p.user_id==42&&p.max_slots==1&&p.players[0].empty);end(s);
  for(unsigned mode=0;mode<9;mode++){
   s=session(l?3:5,a);CohNetMessage m=inventory_message(index);CohStatus expected=COH_INVALID;
   if(mode==0)m.payload_bits--;
   else if(mode==1){m.payload_bits++;expected=COH_UNSUPPORTED;}
   else if(mode==2){m=inventory_message(find_fixture(a,l,1025,0));expected=COH_LIMIT;}
   else if(mode==3){s->diagnostics.phase=COH_DB_QUEUED;expected=COH_STATE;}
   else if(mode==4){s->diagnostics.phase=COH_DB_CHARACTERS;expected=COH_STATE;}
   else if(mode==5){s->diagnostics.account_inventories=UINT64_MAX;s->diagnostics.account_last_inventory_items=17;expected=COH_LIMIT;}
   else if(mode==6){m.payload_bits=sizeof(m.payload)*8+1;}
   else if(mode==7){s->udp->end=COH_INVALID;}
   else {m=inventory_message(find_fixture(a,l,3,1));m.payload_bits--;}
   uint64_t before=s->diagnostics.account_inventories;uint32_t old_items=s->diagnostics.account_last_inventory_items;enqueue(s,m);CHECK(coh_db_session_service(s,102,(CohCancel){0})==expected&&s->diagnostics.phase==COH_DB_FAILED&&s->diagnostics.account_inventories==before+(mode==7)&&s->diagnostics.account_last_inventory_items==(mode==7?0:old_items)&&!s->diagnostics.player_lists&&!s->diagnostics.choices&&!s->diagnostics.handoffs&&s->udp->d.state==COH_UDP_CLOSED);end(s);
  }
  s=session(l?3:5,a);enqueue(s,inventory_message(find_fixture(a,l,3,1)));CHECK(coh_db_session_service(s,102,(CohCancel){0})==COH_OK&&s->diagnostics.account_inventories==1&&s->diagnostics.account_last_inventory_items==3&&s->phase_start_ms==101&&s->user_id==42);CHECK(coh_db_session_service(s,1101,(CohCancel){0})==COH_STATE&&s->diagnostics.phase==COH_DB_TIMED_OUT&&s->diagnostics.account_inventories==1);end(s);
  s=session(l?3:5,a);enqueue(s,inventory_message(index));unsigned polls=0;CHECK(coh_db_session_service(s,102,(CohCancel){cancel,&polls})==COH_CANCELLED&&polls==1&&s->diagnostics.phase==COH_DB_CANCELLED&&!s->diagnostics.account_inventories);end(s);
  s=session(l?3:5,a);enqueue(s,inventory_message(index));CohNetMessage unknown={0};unknown.compressed=(uint8_t)a;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,unknown.payload,COH_PROTOCOL_FRAME_MAX,0,1));write_command(&b,a,l,21);unknown.payload_bits=(uint32_t)b.bit_length;enqueue(s,unknown);CHECK(coh_db_session_service(s,102,(CohCancel){0})==COH_OK&&s->diagnostics.account_inventories==1&&s->diagnostics.unsupported==1&&!s->diagnostics.player_lists&&s->diagnostics.phase==COH_DB_WAIT_PLAYERS);end(s);
 }
}
int main(void){inventory_direct();inventory_boundaries();inventory_sessions();CHECK(!allocations);printf("{\"passed\":true,\"checks\":%u,\"inventory_parser_cases\":%u,\"session_transactions\":%u,\"inventory_output_bytes\":%zu,\"session_bytes\":%zu,\"diagnostics_bytes\":%zu,\"old8822_main_executed\":false,\"sockets_executed\":false,\"real_auth_or_db\":false,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks,inventory_cases,transactions,sizeof(CohDbAccountInventory),sizeof(CohDbSession),sizeof(CohDbSessionDiagnostics));return 0;}
