#include "coh_monitor_envelope.h"
#include <stdio.h>
#include <string.h>
/* EXACT_ORIGINAL_BLOWFISH_PAD */
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"monitor-envelope:%d\n",__LINE__);return 1;}}while(0)
int main(void){
 uint8_t request[8];uint32_t bits;
 for(unsigned legacy=0;legacy<2;legacy++){
  CHECK(coh_monitor_request(legacy,request,&bits)==COH_OK);
  CohProtocolBits reader;uint32_t cmd=0;
  CHECK(!coh_protocol_bits_init(&reader,request,8,bits,0));CHECK(!coh_protocol_read_pack(&reader,1,&cmd));CHECK(cmd==(legacy?15:10));CHECK(reader.cursor==bits);
 }
 CHECK(coh_monitor_request(2,request,&bits)==COH_INVALID);
 CHECK(coh_monitor_request(0,request,&bits)==COH_OK);
 CohNetPacket packet={0};packet.id=1;packet.payload_bits=bits;memcpy(packet.payload,request,8);
 uint8_t wire[COH_PROTOCOL_FRAME_MAX];size_t bytes=0;
 CHECK(coh_net_frame_encode(5,NULL,0,&packet,wire,sizeof(wire),&bytes)==COH_OK);
 for(size_t cap=1;cap<=bytes;cap++){
  CohMonitorStream stream={0};CohMonitorFrame frame,previous;memset(&frame,0xA5,sizeof(frame));previous=frame;
  size_t at=0;
  while(at<bytes){size_t count=bytes-at;if(count>cap)count=cap;size_t consumed=0;
   CohStatus result=coh_monitor_stream_feed(&stream,(CohBytes){wire+at,count},&consumed,&frame);at+=consumed;
   CHECK(consumed==count);CHECK(result==(at==bytes?COH_OK:COH_NOT_FOUND));
   if(at<bytes)CHECK(!memcmp(&frame,&previous,sizeof(frame)));
  }
  CHECK(frame.size==bytes);CHECK(!memcmp(frame.data,wire,bytes));
  CohNetPacket decoded;CHECK(coh_net_frame_decode(5,NULL,0,0,(CohBytes){frame.data,frame.size},&decoded)==COH_OK);CHECK(decoded.payload_bits==bits);
 }
 uint8_t joined[3*COH_PROTOCOL_FRAME_MAX];for(int i=0;i<3;i++)memcpy(joined+i*bytes,wire,bytes);
 CohMonitorStream stream={0};CohMonitorFrame frame;size_t at=0;
 for(int i=0;i<3;i++){size_t consumed=0;CHECK(coh_monitor_stream_feed(&stream,(CohBytes){joined+at,3*bytes-at},&consumed,&frame)==COH_OK);CHECK(consumed==bytes);at+=consumed;}
 const uint32_t bad[]={0,104,0xFFFFFFFFu,12000};
 for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++){
  coh_monitor_stream_reset(&stream);uint8_t header[4];for(unsigned b=0;b<4;b++)header[b]=(uint8_t)(bad[i]>>(8*b));
  memset(&frame,0xA5,sizeof(frame));CohMonitorFrame previous=frame;size_t consumed;
  CHECK(coh_monitor_stream_feed(&stream,(CohBytes){header,4},&consumed,&frame)==COH_LIMIT);CHECK(consumed==4);CHECK(!memcmp(&frame,&previous,sizeof(frame)));
  CHECK(coh_monitor_stream_feed(&stream,(CohBytes){wire,bytes},&consumed,&frame)==COH_STATE);
 }
 for(uint32_t logical=105;logical<=COH_PROTOCOL_FRAME_MAX*8;logical++){
  coh_monitor_stream_reset(&stream);uint8_t header[4];for(unsigned b=0;b<4;b++)header[b]=(uint8_t)(logical>>(8*b));
  size_t used;CohStatus result=coh_monitor_stream_feed(&stream,(CohBytes){header,4},&used,&frame);
  int expected=blowfishPad((int)((logical+7)/8));CHECK(used==4);
  CHECK(result==(expected<=COH_PROTOCOL_FRAME_MAX?COH_NOT_FOUND:COH_LIMIT));
  if(expected<=COH_PROTOCOL_FRAME_MAX)CHECK(stream.expected==(size_t)expected);
 }
 coh_monitor_stream_reset(&stream);stream.expected=1;size_t bad_used;
 CHECK(coh_monitor_stream_feed(&stream,(CohBytes){wire,bytes},&bad_used,&frame)==COH_INVALID);
 coh_monitor_stream_reset(&stream);size_t consumed;CHECK(coh_monitor_stream_feed(&stream,(CohBytes){NULL,0},&consumed,&frame)==COH_NOT_FOUND);
 /* Every declared control/input span overlap refuses before any write. */
 uint8_t old_request[8];memcpy(old_request,request,8);
 CHECK(coh_monitor_request(0,request,(uint32_t*)(void*)request)==COH_INVALID);CHECK(!memcmp(request,old_request,8));
 CHECK(coh_monitor_request(0,(uint8_t*)(uintptr_t)(UINTPTR_MAX-3),&bits)==COH_INVALID);
 coh_monitor_stream_reset(&stream);CohMonitorStream old_stream=stream;
 memset(&frame,0xA5,sizeof(frame));CohMonitorFrame old_frame=frame;consumed=99;
 CHECK(coh_monitor_stream_feed(&stream,(CohBytes){stream.data,4},&consumed,&frame)==COH_INVALID);CHECK(consumed==99&&!memcmp(&stream,&old_stream,sizeof(stream))&&!memcmp(&frame,&old_frame,sizeof(frame)));
 CHECK(coh_monitor_stream_feed(&stream,(CohBytes){wire,bytes},&stream.used,&frame)==COH_INVALID);CHECK(!memcmp(&stream,&old_stream,sizeof(stream)));
 CHECK(coh_monitor_stream_feed(&stream,(CohBytes){wire,bytes},&consumed,(CohMonitorFrame*)(void*)&stream)==COH_INVALID);CHECK(consumed==99&&!memcmp(&stream,&old_stream,sizeof(stream)));
 CHECK(coh_monitor_stream_feed(&stream,(CohBytes){frame.data,4},&consumed,&frame)==COH_INVALID);CHECK(consumed==99&&!memcmp(&frame,&old_frame,sizeof(frame)));
 CHECK(coh_monitor_stream_feed(&stream,(CohBytes){(const uint8_t*)&consumed,sizeof(consumed)},&consumed,&frame)==COH_INVALID);CHECK(consumed==99);
 CHECK(coh_monitor_stream_feed(&stream,(CohBytes){wire,bytes},(size_t*)(void*)&frame,&frame)==COH_INVALID);CHECK(!memcmp(&frame,&old_frame,sizeof(frame)));
 CHECK(coh_monitor_stream_feed(&stream,(CohBytes){(const uint8_t*)(uintptr_t)(UINTPTR_MAX-3),8},&consumed,&frame)==COH_INVALID);CHECK(consumed==99);
 printf("{\"passed\":true,\"checks\":%u,\"send_caps\":%zu,\"coalesced_frames\":3,\"sockets_opened\":0}\n",checks,bytes);return 0;
}
