#include "coh_initial_send.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "initial-send-fixtures.h"
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"send check %u line %u\n",checks,__LINE__);exit(1);}}while(0)
static uint32_t scalar(CohProtocolBits*b,CohMapProfile p,unsigned width){uint32_t v=0;CHECK(!coh_protocol_read(b,p.byte_aligned?(width+7u)&~7u:width,&v));return v;}
static uint32_t packed(CohProtocolBits*b,CohMapProfile p,unsigned width){uint32_t v=0;CHECK(!(p.byte_aligned?coh_protocol_read(b,32,&v):coh_protocol_read_pack(b,width,&v)));return v;}
static CohProtocolBits reader(CohMapPacket*p){CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,p->data,sizeof p->data,p->bits,0));return b;}
int main(void){
 unsigned cases=0;
 for(size_t i=0;i<sizeof source_sends/sizeof source_sends[0];i++){
  const SendGolden*g=&source_sends[i];CohMapProfile profile={g->legacy,g->aligned};CohMapPacket ack,ready;
  memset(&ack,0xa5,sizeof ack);memset(&ready,0x5a,sizeof ready);
  CHECK(coh_initial_input_serialize(profile,g->id,g->received,&ack)==COH_OK);
  CHECK(ack.bits==g->ack_bits&&!memcmp(ack.data,g->ack,(ack.bits+7u)/8u));
  CohMapFields fields={.cookie=g->cookie,.console_open=g->console,.initial_login=g->initial,.password_md5=g->md5};
  CHECK(g->id!=g->cookie&&g->id!=0x11223344u);
  CHECK(coh_map_serialize(COH_MAP_READY,profile,&fields,&ready)==COH_OK);
  CHECK(ready.bits==g->ready_bits&&!memcmp(ready.data,g->ready,(ready.bits+7u)/8u));
  CohProtocolBits b=reader(&ack);
  CHECK(packed(&b,profile,1)==COH_MAP_INPUT); /* Source direct write: no legacy shift. */
  CHECK(scalar(&b,profile,1)==0&&scalar(&b,profile,1)==0&&packed(&b,profile,14)==0);
  CHECK(scalar(&b,profile,1)==0&&packed(&b,profile,1)==0);
  while(b.cursor&7u)CHECK(scalar(&b,(CohMapProfile){0,0},1)==0);
  CHECK(packed(&b,profile,1)==4&&packed(&b,profile,1)==g->id);
  if(g->received)CHECK(packed(&b,profile,1)==3);
  CHECK(b.cursor==b.bit_length);
  b=reader(&ready);CHECK(packed(&b,profile,1)==COH_MAP_READY+(g->legacy?5u:0u));
  CHECK(packed(&b,profile,1)==g->cookie&&packed(&b,profile,1)==g->console);
  while(b.cursor&7u)CHECK(scalar(&b,(CohMapProfile){0,0},1)==0);
  for(unsigned j=0;j<16;j++)CHECK(scalar(&b,(CohMapProfile){0,0},8)==g->md5[j]);
  CHECK(scalar(&b,profile,2)==0&&scalar(&b,profile,2)==g->initial&&b.cursor==b.bit_length);
  coh_map_packet_wipe(&ack);coh_map_packet_wipe(&ready);
  for(size_t j=0;j<sizeof ack;j++)CHECK(((unsigned char*)&ack)[j]==0&&((unsigned char*)&ready)[j]==0);
  cases++;
 }
 CohMapPacket out,saved;memset(&out,0xa5,sizeof out);saved=out;
 CHECK(coh_initial_input_serialize((CohMapProfile){2,0},7,0,&out)==COH_INVALID&&!memcmp(&out,&saved,sizeof out));
 CHECK(coh_initial_input_serialize((CohMapProfile){0,2},7,0,&out)==COH_INVALID&&!memcmp(&out,&saved,sizeof out));
 CHECK(coh_initial_input_serialize((CohMapProfile){0,0},7,2,&out)==COH_INVALID&&!memcmp(&out,&saved,sizeof out));
 CHECK(coh_initial_input_serialize((CohMapProfile){0,0},7,0,NULL)==COH_INVALID);
 unsigned char md5[16]={0xd4,0x1d,0x8c,0xd9,0x8f,0x00,0xb2,0x04,0xe9,0x80,0x09,0x98,0xec,0xf8,0x42,0x7e};
 CohMapFields fields={.cookie=0x1a2b3c4d,.password_md5=md5};
 CHECK(coh_map_serialize(COH_MAP_READY,(CohMapProfile){0,0},&fields,NULL)==COH_INVALID);
 for(unsigned bad=0;bad<5;bad++){
  CohMapFields f=fields;if(bad<2)f.cookie=bad;else if(bad==2)f.console_open=2;else if(bad==3)f.initial_login=2;else f.password_md5=NULL;
  CHECK(coh_map_serialize(COH_MAP_READY,(CohMapProfile){0,0},&f,&out)==COH_INVALID&&!memcmp(&out,&saved,sizeof out));
 }
 /* Borrowed MD5 may alias output: production stages its candidate before commit. */
 memcpy(out.data,md5,16);fields.password_md5=out.data;
 CHECK(coh_map_serialize(COH_MAP_READY,(CohMapProfile){0,0},&fields,&out)==COH_OK);
 coh_map_packet_wipe(&out);for(size_t j=0;j<sizeof out;j++)CHECK(((unsigned char*)&out)[j]==0);
 printf("{\"checks\":%u,\"source_cases\":%u,\"packet_bytes\":%zu,\"runtime_socket_or_entity_claim\":false}\n",checks,cases,sizeof(CohMapPacket));return 0;
}
