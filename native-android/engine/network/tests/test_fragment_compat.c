#include "coh_net.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
static unsigned checks,source_frames,source_deliveries,negative,stream_deliveries;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
typedef struct {unsigned bytes,ordered,count;const uint8_t *parts[16];size_t sizes[16];}OriginalFragmentCase;
#include "fragment_goldens.h"
static CohNetPacket control(uint32_t id,uint32_t cmd,int value){
 CohNetPacket p={0};p.id=id;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1));CHECK(!coh_protocol_write_pack(&b,1,0));CHECK(!coh_protocol_write_pack(&b,1,cmd));if(value)CHECK(!coh_protocol_write_pack(&b,1,0));p.payload_bits=(uint32_t)b.bit_length;return p;
}
static CohStatus sink(void*ctx,CohBytes data){(void)ctx;CHECK(data.data&&data.size);return COH_OK;}
static CohBytes frame(CohNetPacket *p,uint8_t out[COH_PROTOCOL_FRAME_MAX]){size_t bytes=0;CHECK(coh_net_frame_encode(5,NULL,0,p,out,COH_PROTOCOL_FRAME_MAX,&bytes)==COH_OK);return(CohBytes){out,bytes};}
static CohNet *connected(void){
 CohNet*n=coh_net_create(NULL);CHECK(n);CHECK(coh_net_begin(n,1,100)==COH_OK);CHECK(coh_net_pump(n,100,sink,NULL,(CohCancel){0})==COH_OK);
 uint8_t raw[COH_PROTOCOL_FRAME_MAX];CohNetPacket p=control(100,2,1);p.ack_count=1;p.acks[0]=1;CHECK(coh_net_receive(n,frame(&p,raw),101)==COH_OK);CHECK(coh_net_pump(n,101,sink,NULL,(CohCancel){0})==COH_OK);
 p=control(101,4,0);p.ack_count=1;p.acks[0]=2;CHECK(coh_net_receive(n,frame(&p,raw),102)==COH_OK);CHECK(coh_net_state(n)==COH_NET_CONNECTED);return n;
}
static void assert_empty(CohNet*n){CohNetMessage m,b;memset(&m,0xa5,sizeof(m));b=m;CHECK(coh_net_next(n,&m)==COH_NOT_FOUND);CHECK(!memcmp(&b,&m,sizeof(m)));}
static void original_cases(void){
 for(size_t c=0;c<sizeof(fragment_cases)/sizeof(fragment_cases[0]);c++){
  const OriginalFragmentCase*g=&fragment_cases[c];
  for(unsigned i=0;i<g->count;i++){
   CohNetPacket p;CHECK(coh_net_frame_decode(5,NULL,0,0,(CohBytes){g->parts[i],g->sizes[i]},&p)==COH_OK);
   CHECK(p.id==102+i&&p.ordered==g->ordered&&p.ordered_id==(g->ordered&&!i?1u:0u));
   CHECK(p.sibling_count==(g->bytes>=1200?g->count:0)&&p.sibling_part==i);
   uint8_t out[COH_PROTOCOL_FRAME_MAX];CohBytes f=frame(&p,out);CHECK(f.size==g->sizes[i]&&!memcmp(f.data,g->parts[i],f.size));source_frames++;
  }
  for(unsigned order=0;order<4;order++){
   CohNet*n=connected();
   for(unsigned at=0;at<g->count;at++){
    unsigned i=order==0?at:order==1?g->count-at-1:order==2?(at+1)%g->count:(at+g->count/2)%g->count;
    CHECK(coh_net_receive(n,(CohBytes){g->parts[i],g->sizes[i]},103+at)==COH_OK);if(at+1<g->count)assert_empty(n);
   }
   CohNetOwnedMessage m;CHECK(coh_net_next_owned(n,&m)==COH_OK);CHECK(m.id==102&&m.ordered_id==g->ordered&&m.ordered==g->ordered&&m.payload_bytes==g->bytes&&m.payload_bits==g->bytes*8);
   CHECK(m.payload[0]==0x57);for(unsigned i=1;i<g->bytes;i++)CHECK(m.payload[i]==(uint8_t)(i*17));
   CHECK(coh_net_owned_release(n,&m)==COH_OK&&!m.payload&&!m.generation);assert_empty(n);
   CHECK(coh_net_receive(n,(CohBytes){g->parts[g->count-1],g->sizes[g->count-1]},120)==COH_OK);assert_empty(n);
   CohNetDiagnostics d;coh_net_diagnostics(n,&d);CHECK(!d.fragment_groups&&!d.rx_pending&&!d.malformed&&d.duplicates==1);coh_net_destroy(n);source_deliveries++;
  }
 }
}
/* Independent policy-free envelope writer enables malformed-header negatives;
 * Adler32 and packet-tail checks still run in production decode. */
static CohBytes raw_frame(CohNetPacket*p,uint8_t out[COH_PROTOCOL_FRAME_MAX]){
 memset(out,0,COH_PROTOCOL_FRAME_MAX);CohProtocolBits b;CHECK(coh_protocol_bits_init(&b,out,COH_PROTOCOL_FRAME_MAX,0,1)==COH_OK);
 CHECK(!coh_protocol_write(&b,32,0));CHECK(!coh_protocol_write(&b,32,0));CHECK(!coh_protocol_write(&b,1,0));CHECK(!coh_protocol_write(&b,32,p->id));CHECK(!coh_protocol_write_pack(&b,1,p->sibling_count));
 if(p->sibling_count){CHECK(!coh_protocol_write_pack(&b,1,p->sibling_part));CHECK(!coh_protocol_write(&b,32,p->sibling_id));}
 CHECK(!coh_protocol_write_pack(&b,1,0));CHECK(!coh_protocol_write(&b,1,p->compressed));CHECK(!coh_protocol_write(&b,1,p->ordered));
 if(p->ordered){unsigned bin=0;const unsigned bins[4]={2,10,24,32};while(bin<3&&p->ordered_id>=(UINT32_C(1)<<bins[bin]))bin++;CHECK(!coh_protocol_write(&b,2,bin));CHECK(!coh_protocol_write(&b,bins[bin],p->ordered_id));}
 size_t at=(b.cursor+7)/8;memcpy(out+at,p->payload,(p->payload_bits+7)/8);size_t bits=at*8+p->payload_bits,bytes=4+((((bits+7)/8)-4+7)&~(size_t)7);
 for(unsigned i=0;i<4;i++){out[i]=(uint8_t)(bits>>(8*i));}uLong adler=adler32(1,out+8,(uInt)bytes-8);for(unsigned i=0;i<4;i++)out[4+i]=(uint8_t)(adler>>(24-8*i));return(CohBytes){out,bytes};
}
static CohNetPacket piece(unsigned part,unsigned count,unsigned order){CohNetPacket p={0};p.id=102+part;p.sibling_id=20;p.sibling_count=count;p.sibling_part=part;p.ordered=1;p.ordered_id=order;p.payload_bits=16;p.payload[0]=0x57;p.payload[1]=(uint8_t)part;return p;}
static void bad_frame(CohNetPacket p){uint8_t raw[COH_PROTOCOL_FRAME_MAX],out[COH_PROTOCOL_FRAME_MAX];memset(out,0xa5,sizeof(out));size_t bytes=333;CHECK(coh_net_frame_encode(5,NULL,0,&p,out,sizeof(out),&bytes)==COH_INVALID&&out[0]==0xa5&&bytes==333);CohNetPacket before,after;memset(&before,0xa5,sizeof(before));after=before;CHECK(coh_net_frame_decode(5,NULL,0,0,raw_frame(&p,raw),&after)==COH_INVALID);CHECK(!memcmp(&before,&after,sizeof(before)));negative++;}
static void negatives(void){
 CohNetPacket p=piece(0,1,0);bad_frame(p);p=piece(1,2,0);p.sibling_count=0;p.sibling_part=0;p.sibling_id=0;bad_frame(p);
 p=piece(0,17,1);bad_frame(p);p=piece(1,1,0);bad_frame(p);p=piece(0,1,1);p.sibling_id=0;bad_frame(p);
 for(unsigned which=0;which<3;which++){
  CohNet*n=connected();uint8_t raw[COH_PROTOCOL_FRAME_MAX];p=piece(1,2,which==0?2:0);CHECK(coh_net_receive(n,frame(&p,raw),103)==COH_OK);assert_empty(n);
  p=piece(0,2,1);if(which==1)p.compressed=1;if(which==2)p.ordered=0;
  CHECK(coh_net_receive(n,frame(&p,raw),104)==COH_INVALID);assert_empty(n);CohNetDiagnostics d;coh_net_diagnostics(n,&d);CHECK(d.received==3&&d.malformed==1&&d.fragment_groups==1);
  /* The refused first fragment was not marked/ACKed: corrected retry works. */
  p=piece(0,2,which==0?2:1);CHECK(coh_net_receive(n,frame(&p,raw),105)==COH_OK);CohNetMessage m;CHECK(coh_net_next(n,&m)==(which==0?COH_NOT_FOUND:COH_OK));if(which)CHECK(m.ordered_id==1&&m.id==102);coh_net_destroy(n);negative++;
 }
 /* A source-form continuation can be retained while part zero is missing;
  * no ordered application message is published and existing timeout retires it. */
 CohNet*n=connected();uint8_t raw[COH_PROTOCOL_FRAME_MAX];p=piece(1,2,0);CHECK(coh_net_receive(n,frame(&p,raw),103)==COH_OK);assert_empty(n);CHECK(coh_net_pump(n,10103,sink,NULL,(CohCancel){0})==COH_STATE);CHECK(coh_net_state(n)==COH_NET_TIMED_OUT);CohNetDiagnostics d;coh_net_diagnostics(n,&d);CHECK(!d.fragment_groups&&!d.rx_pending&&d.fragment_expirations==1);coh_net_destroy(n);negative++;
 /* Previously admitted native repeated nonzero sibling IDs remain accepted. */
 n=connected();for(unsigned i=0;i<2;i++){p=piece(i,2,1);CHECK(coh_net_receive(n,frame(&p,raw),103+i)==COH_OK);}CohNetMessage m;CHECK(coh_net_next(n,&m)==COH_OK&&m.ordered_id==1);coh_net_destroy(n);
 /* 16 siblings remain the ceiling and aggregate 16KiB fail-close is unchanged. */
 n=connected();for(unsigned i=0;i<12;i++){p=piece(i,16,i?0:1);p.payload_bits=COH_NET_PAYLOAD_MAX*8;CHECK(coh_net_receive(n,frame(&p,raw),103+i)==(i==11?COH_LIMIT:COH_OK));}CHECK(coh_net_state(n)==COH_NET_FAILED);coh_net_diagnostics(n,&d);CHECK(!d.fragment_groups&&!d.rx_pending&&!d.tx_pending);coh_net_destroy(n);negative++;
 /* A completed source group rejected for RX capacity is safely retried. */
 n=connected();for(unsigned i=0;i<COH_NET_RX_MAX;i++){p=piece(0,1,1);p.id=200+i;p.ordered=0;p.sibling_count=p.sibling_id=0;CHECK(coh_net_receive(n,frame(&p,raw),103)==COH_OK);}
 p=piece(0,2,1);p.id=300;CHECK(coh_net_receive(n,frame(&p,raw),104)==COH_OK);p=piece(1,2,0);p.id=301;CohBytes f=frame(&p,raw);CHECK(coh_net_receive(n,f,105)==COH_LIMIT);CHECK(coh_net_next(n,&m)==COH_OK);CHECK(coh_net_receive(n,f,106)==COH_OK);CHECK(coh_net_next(n,&m)==COH_OK&&m.id==201);while(coh_net_next(n,&m)==COH_OK){if(m.ordered)CHECK(m.ordered_id==1&&m.id==300);}coh_net_destroy(n);negative++;
}
static void streaming(void){
 /* Independent zlib standard streaming producer: original compressed command,
  * raw-tail size and Z_SYNC_FLUSH convention, after source-form fragmentation. */
 z_stream z={0};CHECK(deflateInit(&z,Z_DEFAULT_COMPRESSION)==Z_OK);CohNet*n=connected();uint8_t input[10000],packed[COH_NET_MESSAGE_MAX];uint32_t random=25027,id=102;
 for(unsigned i=0;i<sizeof(input);i++){random^=random<<13;random^=random>>17;random^=random<<5;input[i]=(uint8_t)random;}input[0]=6;input[1]=input[2]=input[3]=0;
 for(unsigned msg=0;msg<2;msg++){
  input[50]=(uint8_t)msg;memcpy(packed,input,4);uint32_t tail=sizeof(input)-4;for(unsigned j=0;j<4;j++)packed[4+j]=(uint8_t)(tail>>(j*8));z.next_in=input+4;z.avail_in=tail;z.next_out=packed+8;z.avail_out=sizeof(packed)-8;CHECK(deflate(&z,Z_SYNC_FLUSH)==Z_OK&&!z.avail_in);size_t bytes=sizeof(packed)-z.avail_out;unsigned count=(unsigned)((bytes+1199)/1200);CHECK(count&&count<=16);if(msg==0)CHECK(count>1);
  for(unsigned at=0;at<count;at++){unsigned part=count-at-1;CohNetPacket p=piece(part,count,part?0:msg+1);p.id=id+part;p.sibling_id=40+msg;p.compressed=1;size_t off=part*1200,chunk=bytes-off;if(chunk>1200)chunk=1200;p.payload_bits=(uint32_t)chunk*8;memcpy(p.payload,packed+off,chunk);uint8_t raw[COH_PROTOCOL_FRAME_MAX];CHECK(coh_net_receive(n,frame(&p,raw),200+msg)==COH_OK);if(at+1<count)assert_empty(n);}id+=count;
  CohNetOwnedMessage m;CHECK(coh_net_next_owned(n,&m)==COH_OK);CHECK(m.ordered_id==msg+1&&m.payload_bytes==sizeof(input)&&!memcmp(m.payload,input,sizeof(input)));CHECK(coh_net_owned_release(n,&m)==COH_OK);assert_empty(n);stream_deliveries++;
 }
 CHECK(deflateEnd(&z)==Z_DATA_ERROR);coh_net_destroy(n);
}
int main(void){original_cases();negatives();streaming();printf("{\"passed\":true,\"checks\":%u,\"original_frames\":%u,\"original_reassembled_deliveries\":%u,\"negative_cases\":%u,\"independent_streaming_deliveries\":%u,\"original_server_executed\":false,\"world_authority\":false}\n",checks,source_frames,source_deliveries,negative,stream_deliveries);return 0;}
