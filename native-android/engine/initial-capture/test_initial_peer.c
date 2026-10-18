/* Test-only extension of the unchanged source-layout UI peer. The generated
 * server-command-fixtures.h must, only under this macro, define main as
 * accepted_ui_peer_main after the included DB suite undefines its own main. */
#define COH_INITIAL_PEER_RENAME_MAIN 1
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "../local/test_ui_peer.c"
#pragma GCC diagnostic pop
#undef main
#ifdef COH_INITIAL_EDITMSG_PEER
#include "editmsg-fixtures.h"
#endif
static const char *initial_mode;
static unsigned initial_requests,initial_responses,initial_replays,forbidden_commands;
static uint8_t initial_bytes[65536];
#ifdef COH_INITIAL_EDITMSG_PEER
static void initial_editmsg(Peer*p,CohNetEndpoint target,uint32_t ack,unsigned malformed,unsigned overlong){
 /* Fixture 17: packed type3,257 bytes, from whole original sendEditMessage. */
 unsigned index=overlong?39:17;
 if(editmsg_fixtures[index].aligned){
  uint8_t encoded[COH_NET_MESSAGE_MAX];size_t raw=(editmsg_fixtures[index].bits+7)/8;uint32_t tail=(uint32_t)raw-4;memcpy(encoded,editmsg_fixtures[index].data,4);for(unsigned i=0;i<4;i++)encoded[4+i]=(uint8_t)(tail>>(8*i));uLongf count=sizeof(encoded)-8;CHECK(compress2(encoded+8,&count,editmsg_fixtures[index].data+4,tail,9)==Z_OK);ui_message(p,target,encoded,(count+8)*8,ack,1);
 }else ui_message(p,target,editmsg_fixtures[index].data,editmsg_fixtures[index].bits-malformed,ack,0);
 initial_responses++;
}
#endif
static void initial_packet(Peer*p,CohNetEndpoint target,uint32_t ack){
 memset(initial_bytes,0,sizeof(initial_bytes));
 /* Explicit synthetic byte-aligned ALLENTS header plus opaque raw tail.
  * This does not execute or claim a whole original ALLENTS producer. */
 scene_fixture_u32(initial_bytes,COH_REP_ALLENTS);scene_fixture_u32(initial_bytes+4,7);
 initial_bytes[8]=strcmp(initial_mode,"badheader")?1:0;
 scene_fixture_u32(initial_bytes+9,0);scene_fixture_u32(initial_bytes+13,123);
 scene_fixture_u32(initial_bytes+17,456);initial_bytes[21]=1;
 uint8_t encoded[COH_NET_MESSAGE_MAX];memcpy(encoded,initial_bytes,4);
 uint32_t tail=sizeof(initial_bytes)-4;for(unsigned i=0;i<4;i++)encoded[4+i]=(uint8_t)(tail>>(8*i));
 uLongf bytes=sizeof(encoded)-8;CHECK(compress2(encoded+8,&bytes,initial_bytes+4,tail,9)==Z_OK);bytes+=8;
 CHECK(bytes<=sizeof(encoded));ui_message(p,target,encoded,(size_t)bytes*8,ack,1);initial_responses++;
}
static void initial_report(const UiPeer*u){
 char temporary[4096];int n=snprintf(temporary,sizeof(temporary),"%s.tmp",u->report);CHECK(n>0&&(size_t)n<sizeof(temporary));FILE*f=fopen(temporary,"w");CHECK(f);
 CHECK(fprintf(f,"{\"schema\":1,\"scripted_source_layout\":true,\"real_server_interoperability\":false,\"authserver_authenticated\":false,\"live_world\":false,\"failed\":%s,\"pid\":%ld,\"db_port\":%u,\"map_port\":%u,\"db_phase\":%u,\"map_phase\":%u,\"character_lists\":%u,\"character_choices\":%u,\"map_handoffs\":%u,\"map_connects\":%u,\"source_command_catalogs\":%u,\"source_command_count\":%u,\"scene_prefixes\":%u,\"large_body_fixture\":true,\"scene_tail_parsed\":true,\"scene_assets_resolved\":false,\"scene_crc_verified\":false,\"scene_decoded_bytes\":%zu,\"scene_compressed_bytes\":%zu,\"scene_payload_bits\":%zu,\"scene_compressed\":%s,\"scene_ordered\":false,\"decoded_budget_bytes\":%u,\"scene_expected_counts\":%s,\"selected_wire_slot\":%u,\"opened_sockets\":2,\"closed_sockets\":%u,\"initial_mode\":\"%s\",\"reqallents_unique\":%u,\"initial_responses\":%u,\"initial_replays\":%u,\"forbidden_application_commands\":%u,\"ready_commands\":0,\"received_character_commands\":0,\"full_update_ack_commands\":0,\"whole_original_allents_producer_executed\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false}\n",u->failed?"true":"false",(long)getpid(),u->db.endpoint.port,u->map.endpoint.port,u->db_phase,u->map_phase,u->lists,u->choices,u->handoffs,u->connects,u->catalogs,SOURCE_ACCESSIBLE_COMMAND_COUNT,u->scenes,u->scene_decoded_bytes,u->scene_compressed_bytes,u->scene_decoded_bytes*8,u->scenes?"true":"false",COH_NET_DECODED_MAX,SOURCE_GROUPS_EXPECTED_JSON,u->selected_slot,u->closed,initial_mode,initial_requests,initial_responses,initial_replays,forbidden_commands)>0);CHECK(!fclose(f));CHECK(!rename(temporary,u->report));
}
static void initial_handle(UiPeer*u,unsigned map){
 if(!map||u->map_phase<5){handle(u,map);initial_report(u);return;}
 Peer*p=&u->map;uint8_t frame[COH_PROTOCOL_FRAME_MAX];struct sockaddr_in from;socklen_t length=sizeof(from);ssize_t bytes=recvfrom(p->fd,frame,sizeof(frame),MSG_PEEK,(struct sockaddr*)&from,&length);CHECK(bytes>0&&length==sizeof(from));CohNetPacket packet;CHECK(coh_net_frame_decode(5,NULL,0,0,(CohBytes){frame,(size_t)bytes},&packet)==COH_OK);CohProtocolBits bits;unsigned cmd=read_command(&packet,&bits);
 if(!cmd){handle(u,map);initial_report(u);return;}
 CHECK(ntohl(from.sin_addr.s_addr)==UINT32_C(0x7f000001)&&from.sin_port==htons(u->map_target.port));
 ssize_t consumed=recvfrom(p->fd,frame,sizeof(frame),0,NULL,NULL);CHECK(consumed==bytes);
 if(cmd!=COH_MAP_REQALLENTS||bits.cursor!=bits.bit_length){u->failed=1;forbidden_commands++;stopped=1;initial_report(u);return;}
 for(unsigned i=0;i<16;i++)if(reply_cache[1][i].request_id==packet.id){ReplyCache*saved=&reply_cache[1][i];CHECK(packet.payload_bits==saved->input.payload_bits&&!memcmp(packet.payload,saved->input.payload,(packet.payload_bits+7)/8));for(unsigned j=0;j<saved->count;j++)frame_send(p,u->map_target,5,&saved->replies[j]);initial_replays++;initial_report(u);return;}
 if(u->map_phase!=5||initial_requests){u->failed=1;forbidden_commands++;stopped=1;initial_report(u);return;}
 initial_requests++;u->map_phase=6;recording=&reply_cache[1][reply_cursor[1]++%16];memset(recording,0,sizeof(*recording));recording->request_id=packet.id;recording->input=packet;
 #ifdef COH_INITIAL_EDITMSG_PEER
 if(!strncmp(initial_mode,"editmsg-",8)){
  initial_editmsg(p,u->map_target,packet.id,!strcmp(initial_mode,"editmsg-malformed"),!strcmp(initial_mode,"editmsg-limit"));
  if(!strcmp(initial_mode,"editmsg-captured"))initial_packet(p,u->map_target,packet.id);
  else if(!strcmp(initial_mode,"editmsg-unknown")){CohNetPacket reply;CohProtocolBits out;response(p,15,&reply,&out);reply.payload_bits=(uint32_t)out.bit_length;reply.ack_count=1;reply.acks[0]=packet.id;ui_frame_send(p,u->map_target,5,&reply);initial_responses++;}
 }else
 #endif
 if(!strcmp(initial_mode,"none")){CohNetPacket ack=control(5,++p->id,0,0,0);ack.ack_count=1;ack.acks[0]=packet.id;ui_frame_send(p,u->map_target,5,&ack);}
 else if(!strcmp(initial_mode,"unknown")){CohNetPacket reply;CohProtocolBits out;response(p,15,&reply,&out);reply.payload_bits=(uint32_t)out.bit_length;reply.ack_count=1;reply.acks[0]=packet.id;ui_frame_send(p,u->map_target,5,&reply);initial_responses++;}
 else initial_packet(p,u->map_target,packet.id);
 recording=NULL;initial_report(u);
}
int main(int argc,char**argv){
 if(argc!=6||strcmp(argv[1],"--serve")||strcmp(argv[2],"--report")||strcmp(argv[4],"--mode"))return 2;
 initial_mode=argv[5];if(strcmp(initial_mode,"captured")&&strcmp(initial_mode,"unknown")&&strcmp(initial_mode,"badheader")&&strcmp(initial_mode,"none")
 #ifdef COH_INITIAL_EDITMSG_PEER
 &&strcmp(initial_mode,"editmsg-captured")&&strcmp(initial_mode,"editmsg-unknown")&&strcmp(initial_mode,"editmsg-malformed")&&strcmp(initial_mode,"editmsg-limit")&&strcmp(initial_mode,"editmsg-none")
 #endif
 )return 2;
 UiPeer u={0};u.report=argv[3];u.selected_slot=UINT32_MAX;u.db=peer_open();u.map=peer_open();signal(SIGTERM,stop_peer);signal(SIGINT,stop_peer);uint64_t deadline=milliseconds()+180000;initial_report(&u);
 printf("{\"pid\":%ld,\"db_port\":%u,\"map_port\":%u,\"scripted_source_layout\":true,\"real_server_interoperability\":false}\n",(long)getpid(),u.db.endpoint.port,u.map.endpoint.port);fflush(stdout);
 while(!stopped&&milliseconds()<deadline){struct pollfd fds[2]={{u.db.fd,POLLIN,0},{u.map.fd,POLLIN,0}};int status=poll(fds,2,100);if(status<0){if(stopped)break;u.failed=1;break;}for(unsigned i=0;i<2;i++)if(fds[i].revents&POLLIN)initial_handle(&u,i);}
 peer_close(&u.db);peer_close(&u.map);u.closed=2;initial_report(&u);return u.failed?1:0;
}
