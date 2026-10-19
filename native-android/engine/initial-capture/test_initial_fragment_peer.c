/* Nonshipping focused 0.1.9 peer. Original-compatible sibling envelopes wrap
 * explicit synthetic compressed ALLENTS; this is not an original server. */
#define COH_INITIAL_FRAGMENT_PEER 1
#include "test_initial_inventory_peer.c"
static void initial_fragment_packet(Peer *p,CohNetEndpoint target,uint32_t ack){
 const int single=!strcmp(initial_mode,"fragment-single");
 CHECK(single||!strcmp(initial_mode,"fragment-multi"));
 const uint8_t *data=single?fragment_initial_single:fragment_initial_multi;
 const size_t bytes=single?sizeof(fragment_initial_single):sizeof(fragment_initial_multi);
 const unsigned count=(unsigned)((bytes+1199)/1200);
 CHECK(bytes>=1200&&bytes<=COH_NET_MESSAGE_MAX&&count<=COH_NET_FRAGMENT_MAX);
 CHECK(single?(bytes==1200&&count==1):count>1);
 CohNetPacket parts[COH_NET_FRAGMENT_MAX]={0};
 const uint32_t sibling=++p->sibling;
 for(unsigned part=0;part<count;part++){
  CohNetPacket *m=&parts[part];m->id=++p->id;m->compressed=m->ordered=1;
  m->ordered_id=part?0:1;m->sibling_id=sibling;m->sibling_count=count;m->sibling_part=part;
  size_t length=bytes-part*1200;if(length>1200)length=1200;
  m->payload_bits=(uint32_t)length*8;memcpy(m->payload,data+part*1200,length);
  m->ack_count=1;m->acks[0]=ack;
 }
 /* Part zero is last in the multiple-part case. Its complete logical order
  * identity must survive; later fragments deliberately carry order ID zero. */
 for(unsigned at=0;at<count;at++)ui_frame_send(p,target,5,&parts[count-at-1]);
 initial_fragment_parts=count;initial_fragment_zero_order_ids=count-1;
 initial_fragment_part_zero_sent_last=count>1;initial_fragment_single_sibling=single;
 initial_fragment_wire_bytes=bytes;initial_responses++;
}
