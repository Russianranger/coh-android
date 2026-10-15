/* Controlled callback peer; does not impersonate native or Android authority. */
#include "coh_live_transport.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#define FRAME_MAX 27944u
#define DEVICE UINT64_C(0x1234567887654321)
#define INODE UINT64_C(0xabcdef0123456789)
enum Fault {
 CLEAN=0, MAGIC, VERSION, STATUS, REPLY_SEQUENCE, RESERVED, OVERSIZE,
 SUCCESS_ERROR, FAILURE_PAYLOAD, SHORT_NEXT, OLD_OPEN, OPEN_RECIPE,
 OPEN_FLAGS, OPEN_RESERVED, OPEN_DEVICE, OPEN_INODE, BATCH_MAGIC,
 BATCH_OPERATION, BATCH_TOKEN, BATCH_SEQUENCE, BATCH_FIRST, BATCH_COUNT,
 ROW_ORDINAL, ROW_FLAGS, ROW_NAME, ROW_NAME_PADDING, ROW_RESERVED,
 ROW_ALT_PADDING, NONFINAL_EMPTY, EMPTY_FINAL, FULL_BATCH, DECLINE,
 TERMINAL, READ_EOF, READ_ERROR, READ_OVERRETURN, WRITE_ZERO,
 WRITE_ERROR, WRITE_OVERRETURN, CROSS_CURSOR, CLOSE_PAYLOAD,
 TRUNCATE_HEADER, TRUNCATE_PAYLOAD, WRITE_PARTIAL_ZERO, WRITE_PARTIAL_ERROR,
 SECOND_ROW_BAD, FULL_OVER_NT, DIRECTORY_ROW_LIMIT
};
typedef struct PeerCursor {unsigned char token[16];uint32_t sequence,first;int active;} PeerCursor;
typedef struct Peer {
 unsigned char operation[16],nonce[32],request[1200],response[32+FRAME_MAX];
 uint32_t request_used,response_used,response_read,requests,reads,writes,closes;
 uint32_t command_counts[4],commands[256],short_read,short_write;
 enum Fault fault;uint32_t fault_command,fault_occurrence;
 uint32_t allocation_calls,fail_allocation,allocations,frees;size_t live_bytes,peak_bytes;
 int protocol_valid;
 PeerCursor cursors[16];
} Peer;
static unsigned checks=0;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(3);}} while(0)
static uint32_t u32(const unsigned char *p) {return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void p32(unsigned char *p,uint32_t n) {p[0]=(unsigned char)n;p[1]=(unsigned char)(n>>8);p[2]=(unsigned char)(n>>16);p[3]=(unsigned char)(n>>24);}
static void p64(unsigned char *p,uint64_t n) {p32(p,(uint32_t)n);p32(p+4,(uint32_t)(n>>32));}
static int injecting(Peer *p,uint32_t command) {
 return p->fault!=CLEAN&&command==p->fault_command&&p->command_counts[command]==p->fault_occurrence;
}
static PeerCursor *cursor(Peer *p,const unsigned char *token,int open) {
 unsigned i;
 for(i=0;i<16;i++)if(p->cursors[i].active&&!memcmp(p->cursors[i].token,token,16))return &p->cursors[i];
 if(open)for(i=0;i<16;i++)if(!p->cursors[i].active) {
  memset(&p->cursors[i],0,sizeof(p->cursors[i]));p->cursors[i].active=1;
  memcpy(p->cursors[i].token,token,16);return &p->cursors[i];
 }
 return NULL;
}
static void respond(Peer *p) {
 uint32_t command=u32(p->request+12),length=0,sequence=u32(p->request+64),i;
 unsigned char *reply=p->response,*batch=reply+32;PeerCursor *c;int inject;
 CHECK(p->response_read==p->response_used);
 CHECK(!memcmp(p->request,"COHLDIR1",8));CHECK(u32(p->request+8)==1);
 CHECK(command>=1&&command<=3);CHECK(!memcmp(p->request+16,p->operation,16));
 CHECK(!memcmp(p->request+32,p->nonce,32));CHECK(sequence==p->requests+1);
 CHECK(u32(p->request+92)==0);CHECK(u32(p->request+88)==p->request_used);
 CHECK((command==1&&u32(p->request+84)>0)||(command!=1&&u32(p->request+84)==0));
 p->command_counts[command]++;inject=injecting(p,command);p->requests++;
 CHECK(p->requests<=256);p->commands[p->requests-1]=command;
 c=cursor(p,p->request+68,command==1);CHECK(c!=NULL);
 memset(reply,0,sizeof(p->response));memcpy(reply,"COHRSP1\0",8);
 p32(reply+8,1);p32(reply+16,sequence);
 if(command==1) {
  length=32;p64(batch,DEVICE);p64(batch+8,INODE);p32(batch+16,1);p32(batch+20,1);
 } else if(command==2) {
  uint32_t count=c->sequence?1:2,final=c->sequence?1:0;
  if(inject&&p->fault==EMPTY_FINAL){count=0;final=1;}
  if(inject&&p->fault==NONFINAL_EMPTY){count=0;final=0;}
  if(inject&&p->fault==SECOND_ROW_BAD)count=2;
  if(inject&&(p->fault==FULL_BATCH||p->fault==FULL_OVER_NT)){count=85;final=1;}
  length=64+count*328;memcpy(batch,"COHLIVE1",8);memcpy(batch+8,p->operation,16);
  memcpy(batch+24,c->token,16);p32(batch+40,c->sequence);p32(batch+44,c->first);
  p32(batch+48,count);p32(batch+52,final);p32(batch+60,length);
  for(i=0;i<count;i++) {
   unsigned char *row=batch+64+i*328,*wfd=row+8;p32(row,c->first+i);
   p32(wfd,0x20);p32(wfd+20,0x12345678);p32(wfd+24,0x01234567);p32(wfd+32,123+i);
   /* One ASCII char allows the native NT 8KiB budget to hold all 85 rows. */
   if(count==85)memcpy(wfd+44,p->fault==FULL_OVER_NT?"aa":"a",p->fault==FULL_OVER_NT?3:2);
   else (void)sprintf((char *)wfd+44,"entry_%u_%u_%u",(unsigned)c->token[0],(unsigned)c->sequence,(unsigned)i);
  }
  c->sequence++;c->first+=count;
 } else c->active=0;
 if(inject)switch(p->fault) {
  case MAGIC:reply[0]^=1;break;case VERSION:p32(reply+8,2);break;
  case STATUS:p32(reply+12,3);break;case REPLY_SEQUENCE:p32(reply+16,sequence+1);break;
  case RESERVED:p32(reply+28,1);break;case OVERSIZE:length=FRAME_MAX+1;break;
  case SUCCESS_ERROR:p32(reply+24,77);break;
  case FAILURE_PAYLOAD:p32(reply+12,1);p32(reply+24,88);length=1;break;
  case SHORT_NEXT:length=63;break;case OLD_OPEN:length=0;break;
  case OPEN_RECIPE:p32(batch+16,2);break;case OPEN_FLAGS:p32(batch+20,2);break;
  case OPEN_RESERVED:batch[24]=1;break;case OPEN_DEVICE:batch[0]^=1;break;
  case OPEN_INODE:batch[8]^=1;break;case BATCH_MAGIC:batch[0]^=1;break;
  case BATCH_OPERATION:batch[8]^=1;break;case BATCH_TOKEN:batch[24]^=1;break;
  case BATCH_SEQUENCE:p32(batch+40,u32(batch+40)+1);break;
  case BATCH_FIRST:p32(batch+44,u32(batch+44)+1);break;
  case BATCH_COUNT:p32(batch+48,86);break;case ROW_ORDINAL:batch[64]^=1;break;
  case ROW_FLAGS:batch[68]=1;break;case ROW_NAME:batch[64+8+44]='\\';break;
  case ROW_NAME_PADDING:batch[64+8+303]=1;break;
  case ROW_RESERVED:batch[64+8+36]=1;break;case ROW_ALT_PADDING:batch[64+8+319]=1;break;
  case DECLINE:p32(reply+12,1);p32(reply+24,93);length=0;break;
  case TERMINAL:p32(reply+12,2);p32(reply+24,94);length=0;break;
  case CROSS_CURSOR:memcpy(batch+24,p->cursors[1].token,16);break;
  case CLOSE_PAYLOAD:length=1;break;
  case SECOND_ROW_BAD:batch[64+328+8+44]='\\';break;
  case DIRECTORY_ROW_LIMIT:p32(batch+44,8193);break;
  default:break;
 }
 p32(reply+20,length);p->response_read=0;
 p->response_used=32+(length<=FRAME_MAX?length:0);p->request_used=0;
 if(inject&&p->fault==TRUNCATE_HEADER)p->response_used=13;
 if(inject&&p->fault==TRUNCATE_PAYLOAD)p->response_used=32+63;
}
static int32_t peerWrite(void *context,const unsigned char *bytes,uint32_t count) {
 Peer *p=(Peer *)context;uint32_t take=count;p->writes++;
 if(p->fault==WRITE_ZERO)return 0;if(p->fault==WRITE_ERROR)return -1;
 if(p->fault==WRITE_OVERRETURN)return (int32_t)(count+1);
 if(p->fault==WRITE_PARTIAL_ZERO||p->fault==WRITE_PARTIAL_ERROR) {
  if(p->request_used>=48)return p->fault==WRITE_PARTIAL_ZERO?0:-1;
  if(take>48-p->request_used)take=48-p->request_used;
 }
 if(p->short_write&&take>p->short_write)take=p->short_write;
 CHECK(take<=sizeof(p->request)-p->request_used);memcpy(p->request+p->request_used,bytes,take);
 p->request_used+=take;
 if(p->request_used>=96&&p->request_used==u32(p->request+88))respond(p);
 return (int32_t)take;
}
static int32_t peerRead(void *context,unsigned char *bytes,uint32_t count) {
 Peer *p=(Peer *)context;uint32_t take=count;p->reads++;
 if(injecting(p,p->commands[p->requests-1])) {
  if(p->fault==READ_EOF)return 0;if(p->fault==READ_ERROR)return -1;
  if(p->fault==READ_OVERRETURN)return (int32_t)(count+1);
 }
 if(take>p->response_used-p->response_read)take=p->response_used-p->response_read;
 if(p->short_read&&take>p->short_read)take=p->short_read;
 if(!take)return 0;memcpy(bytes,p->response+p->response_read,take);p->response_read+=take;
 return (int32_t)take;
}
static void peerClose(void *context) {Peer *p=(Peer *)context;p->closes++;}
static void *peerAlloc(void *context,size_t bytes) {
 Peer *p=(Peer *)context;size_t *allocation;p->allocation_calls++;
 if(p->allocation_calls==p->fail_allocation)return NULL;
 allocation=(size_t *)malloc(sizeof(size_t)+bytes);CHECK(allocation!=NULL);*allocation=bytes;
 p->allocations++;p->live_bytes+=bytes;if(p->live_bytes>p->peak_bytes)p->peak_bytes=p->live_bytes;
 return allocation+1;
}
static void peerFree(void *context,void *memory) {
 Peer *p=(Peer *)context;size_t *allocation=(size_t *)memory-1;
 CHECK(memory!=NULL);CHECK(p->live_bytes>=*allocation);p->live_bytes-=*allocation;p->frees++;free(allocation);
}
static void setup(Peer *p,CohLiveTransport *t) {
 CohLiveTransportIo io;unsigned i;memset(p,0,sizeof(*p));
 for(i=0;i<16;i++)p->operation[i]=(unsigned char)(i+11);
 for(i=0;i<32;i++)p->nonce[i]=(unsigned char)(i+37);
 memset(&io,0,sizeof(io));io.context=p;io.read=peerRead;io.write=peerWrite;
 io.close=peerClose;io.allocate=peerAlloc;io.release=peerFree;
 CHECK(cohLiveTransportInit(t,&io,p->operation,p->nonce)==COH_TRANSPORT_OK);
 p->fault_command=2;p->fault_occurrence=1;
}
static int openDirectory(Peer *p,CohLiveTransport *t,unsigned token,uint32_t *handle) {
 unsigned char directory[16]={0};(void)p;directory[0]=(unsigned char)token;
 return cohLiveTransportOpen(t,"/game-import/data/fx",directory,DEVICE,INODE,handle);
}
static void finish(Peer *p,CohLiveTransport *t) {
 unsigned writes=p->writes;int result=t->result;CohLiveTransportReason reason=t->reason;
 uint32_t handle=0;const unsigned char *row=(const unsigned char *)1;
 cohLiveTransportShutdown(t);cohLiveTransportShutdown(t);
 CHECK(p->closes==1);CHECK(p->live_bytes==0);CHECK(p->allocations==p->frees);
 CHECK(t->result==result);CHECK(t->reason==reason);CHECK(t->active_cursors==0);
 CHECK(cohLiveTransportNext(t,1,&row)<0);CHECK(row==NULL);
 CHECK(openDirectory(p,t,3,&handle)<0);CHECK(handle==0);CHECK(p->writes==writes);
}
static void basic(void) {
 Peer p;CohLiveTransport t;uint32_t handle=0,other=0,requests;const unsigned char *row,*held;
 unsigned char copy[320];uint64_t dev=0,ino=0;setup(&p,&t);p.short_read=1;p.short_write=1;
 CHECK(openDirectory(&p,&t,1,&handle)==1);CHECK(handle!=0);
 CHECK(cohLiveTransportIdentity(&t,handle,&dev,&ino)==1);CHECK(dev==DEVICE&&ino==INODE);
 CHECK(cohLiveTransportNext(&t,handle,&row)==1);held=row;memcpy(copy,row,320);
 CHECK(!strcmp((const char *)row+44,"entry_1_0_0"));requests=p.requests;
 CHECK(openDirectory(&p,&t,2,&other)==1);CHECK(cohLiveTransportNext(&t,other,&row)==1);
 CHECK(!memcmp(copy,held,320));CHECK(cohLiveTransportNext(&t,handle,&row)==1);
 CHECK(!strcmp((const char *)row+44,"entry_1_0_1"));CHECK(p.requests==requests+2);
 CHECK(cohLiveTransportNext(&t,handle,&row)==1);CHECK(!strcmp((const char *)row+44,"entry_1_1_0"));
 CHECK(cohLiveTransportNext(&t,handle,&row)==0&&row==NULL);CHECK(t.rows_returned==4);
 CHECK(cohLiveTransportClose(&t,&handle)==1&&handle==0);
 CHECK(cohLiveTransportClose(&t,&other)==1&&other==0);CHECK(t.active_cursors==0);
 CHECK(p.short_read==1&&p.reads>1000&&p.writes>300);finish(&p,&t);
}
static void faultCase(enum Fault fault,uint32_t command,int late,CohLiveTransportReason expected) {
 Peer p;CohLiveTransport t;uint32_t handle=0,other=0;const unsigned char *row;int result;
 uint32_t reads,writes,backend_error;setup(&p,&t);
 if(late) {
  CHECK(openDirectory(&p,&t,1,&handle)==1);CHECK(cohLiveTransportNext(&t,handle,&row)==1);
  CHECK(cohLiveTransportNext(&t,handle,&row)==1);CHECK(t.rows_returned==2);
 }
 p.fault=fault;p.fault_command=command;p.fault_occurrence=p.command_counts[command]+1;
 if(command==1)result=openDirectory(&p,&t,late?2:1,&other);
 else {
  if(!late)CHECK(openDirectory(&p,&t,1,&handle)==1);
  if(command==2)result=cohLiveTransportNext(&t,handle,&row);
  else result=cohLiveTransportClose(&t,&handle);
 }
 CHECK(result==(late||fault==TERMINAL?COH_TRANSPORT_TERMINAL:COH_TRANSPORT_INITIAL_DECLINE));
 CHECK(t.dead&&t.reason==expected&&p.closes==1);CHECK(t.rows_returned==(late?2u:0u));
 CHECK(t.failure_cursor_rows==(late&&command!=1?2u:0u));
 reads=p.reads;writes=p.writes;backend_error=t.backend_error;
 CHECK(cohLiveTransportNext(&t,handle,&row)==result&&row==NULL);
 CHECK(openDirectory(&p,&t,3,&other)==result&&other==0);
 CHECK(p.reads==reads&&p.writes==writes);CHECK(t.backend_error==backend_error);
 finish(&p,&t);
}
static void malformed(void) {
 const enum Fault faults[]={MAGIC,VERSION,STATUS,REPLY_SEQUENCE,RESERVED,OVERSIZE,SUCCESS_ERROR,
  FAILURE_PAYLOAD,SHORT_NEXT,BATCH_MAGIC,BATCH_OPERATION,BATCH_TOKEN,BATCH_SEQUENCE,BATCH_FIRST,
  BATCH_COUNT,ROW_ORDINAL,ROW_FLAGS,ROW_NAME,ROW_NAME_PADDING,ROW_RESERVED,ROW_ALT_PADDING,NONFINAL_EMPTY,
  SECOND_ROW_BAD,FULL_OVER_NT,DIRECTORY_ROW_LIMIT};
 const CohLiveTransportReason reasons[]={COH_TRANSPORT_REASON_REPLY_MAGIC,COH_TRANSPORT_REASON_REPLY_VERSION,
  COH_TRANSPORT_REASON_REPLY_STATUS,COH_TRANSPORT_REASON_REPLY_SEQUENCE,COH_TRANSPORT_REASON_REPLY_RESERVED,
  COH_TRANSPORT_REASON_REPLY_PAYLOAD,COH_TRANSPORT_REASON_REPLY_ERROR,COH_TRANSPORT_REASON_REPLY_PAYLOAD,
  COH_TRANSPORT_REASON_REPLY_PAYLOAD,COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,
  COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,
  COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,
  COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,
  COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH,
  COH_TRANSPORT_REASON_BATCH,COH_TRANSPORT_REASON_BATCH};
 unsigned i;CHECK(sizeof(faults)/sizeof(faults[0])==sizeof(reasons)/sizeof(reasons[0]));
 for(i=0;i<sizeof(faults)/sizeof(faults[0]);i++) {faultCase(faults[i],2,0,reasons[i]);faultCase(faults[i],2,1,reasons[i]);}
}
static void acknowledgements(void) {
 const enum Fault faults[]={OLD_OPEN,OPEN_RECIPE,OPEN_FLAGS,OPEN_RESERVED,OPEN_DEVICE,OPEN_INODE};
 const CohLiveTransportReason reasons[]={COH_TRANSPORT_REASON_REPLY_PAYLOAD,COH_TRANSPORT_REASON_ACK_RECIPE,
  COH_TRANSPORT_REASON_ACK_RECIPE,COH_TRANSPORT_REASON_ACK_RESERVED,COH_TRANSPORT_REASON_ACK_IDENTITY,
  COH_TRANSPORT_REASON_ACK_IDENTITY};unsigned i;
 for(i=0;i<sizeof(faults)/sizeof(faults[0]);i++) {
  faultCase(faults[i],1,0,reasons[i]);faultCase(faults[i],1,1,reasons[i]);
 }
 faultCase(SUCCESS_ERROR,1,0,COH_TRANSPORT_REASON_REPLY_ERROR);
 faultCase(SUCCESS_ERROR,3,1,COH_TRANSPORT_REASON_REPLY_ERROR);
 faultCase(CLOSE_PAYLOAD,3,1,COH_TRANSPORT_REASON_REPLY_PAYLOAD);
}
static void ioFailures(void) {
 faultCase(READ_EOF,2,0,COH_TRANSPORT_REASON_READ);faultCase(READ_EOF,2,1,COH_TRANSPORT_REASON_READ);
 faultCase(READ_ERROR,2,0,COH_TRANSPORT_REASON_READ);faultCase(READ_ERROR,2,1,COH_TRANSPORT_REASON_READ);
 faultCase(READ_OVERRETURN,2,0,COH_TRANSPORT_REASON_READ);faultCase(READ_OVERRETURN,2,1,COH_TRANSPORT_REASON_READ);
 faultCase(TRUNCATE_HEADER,2,0,COH_TRANSPORT_REASON_READ);faultCase(TRUNCATE_HEADER,2,1,COH_TRANSPORT_REASON_READ);
 faultCase(TRUNCATE_PAYLOAD,2,0,COH_TRANSPORT_REASON_READ);faultCase(TRUNCATE_PAYLOAD,2,1,COH_TRANSPORT_REASON_READ);
 /* Write failures occur before any request is completed, so choose OPEN. */
 faultCase(WRITE_ZERO,1,0,COH_TRANSPORT_REASON_WRITE);faultCase(WRITE_ZERO,1,1,COH_TRANSPORT_REASON_WRITE);
 faultCase(WRITE_ERROR,1,0,COH_TRANSPORT_REASON_WRITE);faultCase(WRITE_ERROR,1,1,COH_TRANSPORT_REASON_WRITE);
 faultCase(WRITE_OVERRETURN,1,0,COH_TRANSPORT_REASON_WRITE);faultCase(WRITE_OVERRETURN,1,1,COH_TRANSPORT_REASON_WRITE);
 faultCase(WRITE_PARTIAL_ZERO,1,0,COH_TRANSPORT_REASON_WRITE);faultCase(WRITE_PARTIAL_ZERO,1,1,COH_TRANSPORT_REASON_WRITE);
 faultCase(WRITE_PARTIAL_ERROR,1,0,COH_TRANSPORT_REASON_WRITE);faultCase(WRITE_PARTIAL_ERROR,1,1,COH_TRANSPORT_REASON_WRITE);
}
static void declines(void) {
 faultCase(DECLINE,1,0,COH_TRANSPORT_REASON_PEER_DECLINE);faultCase(DECLINE,1,1,COH_TRANSPORT_REASON_PEER_DECLINE);
 faultCase(DECLINE,2,0,COH_TRANSPORT_REASON_PEER_DECLINE);faultCase(DECLINE,2,1,COH_TRANSPORT_REASON_PEER_DECLINE);
 faultCase(TERMINAL,1,0,COH_TRANSPORT_REASON_PEER_TERMINAL);faultCase(TERMINAL,2,1,COH_TRANSPORT_REASON_PEER_TERMINAL);
}
static void bounds(void) {
 Peer p;CohLiveTransport t;uint32_t handles[17]={0},i;const unsigned char *row;
 setup(&p,&t);for(i=0;i<16;i++)CHECK(openDirectory(&p,&t,i+1,&handles[i])==1);
 CHECK(t.active_cursors==16);CHECK(p.peak_bytes<480000);
 CHECK(openDirectory(&p,&t,17,&handles[16])==-1);CHECK(t.reason==COH_TRANSPORT_REASON_LIMIT);finish(&p,&t);
 setup(&p,&t);CHECK(openDirectory(&p,&t,1,&handles[0])==1);
 CHECK(openDirectory(&p,&t,1,&handles[1])==-1);CHECK(t.reason==COH_TRANSPORT_REASON_DUPLICATE_TOKEN);finish(&p,&t);
 setup(&p,&t);CHECK(openDirectory(&p,&t,1,&handles[0])==1);CHECK(openDirectory(&p,&t,2,&handles[1])==1);
 p.fault=CROSS_CURSOR;CHECK(cohLiveTransportNext(&t,handles[0],&row)==-1);
 CHECK(t.reason==COH_TRANSPORT_REASON_BATCH);finish(&p,&t);
 setup(&p,&t);CHECK(openDirectory(&p,&t,1,&handles[0])==1);i=handles[0];CHECK(cohLiveTransportClose(&t,&handles[0])==1);
 CHECK(openDirectory(&p,&t,2,&handles[0])==1);CHECK(handles[0]!=i);
 CHECK(cohLiveTransportNext(&t,i,&row)==-1);CHECK(t.reason==COH_TRANSPORT_REASON_HANDLE);finish(&p,&t);
 setup(&p,&t);t.request_sequence=UINT32_MAX;CHECK(openDirectory(&p,&t,1,&handles[0])==-1);
 CHECK(t.reason==COH_TRANSPORT_REASON_SEQUENCE&&p.requests==0);finish(&p,&t);
 setup(&p,&t);t.handle_sequence=UINT32_MAX;CHECK(openDirectory(&p,&t,1,&handles[0])==-1);
 CHECK(t.reason==COH_TRANSPORT_REASON_SEQUENCE&&p.allocation_calls==0);finish(&p,&t);
}
static void allocationFailures(void) {
 Peer p;CohLiveTransport t;uint32_t handle,other;const unsigned char *row;unsigned i;
 for(i=1;i<=2;i++) {
  setup(&p,&t);p.fail_allocation=i;CHECK(openDirectory(&p,&t,1,&handle)==-1);
  CHECK(t.reason==COH_TRANSPORT_REASON_ALLOCATION&&p.requests==0);finish(&p,&t);
 }
 setup(&p,&t);CHECK(openDirectory(&p,&t,1,&handle)==1);CHECK(cohLiveTransportNext(&t,handle,&row)==1);
 p.fail_allocation=p.allocation_calls+1;CHECK(openDirectory(&p,&t,2,&other)==-2);
 CHECK(t.reason==COH_TRANSPORT_REASON_ALLOCATION&&t.rows_returned==1);finish(&p,&t);
}
static void paths(void) {
 const char *bad[]={NULL,"","fx","Z:/data/fx","/a//b","/a/./b","/a/../b","/a/","/a\\b","/a:b","/a\n","/\177","/\200"};
 Peer p;CohLiveTransport t;unsigned i;unsigned char token[16]={1};uint32_t handle;
 char path[1026];
 for(i=0;i<sizeof(bad)/sizeof(bad[0]);i++) {
  setup(&p,&t);CHECK(cohLiveTransportOpen(&t,bad[i],token,DEVICE,INODE,&handle)==-1);
  CHECK(t.reason==COH_TRANSPORT_REASON_PATH&&p.requests==0&&p.allocation_calls==0);finish(&p,&t);
 }
 setup(&p,&t);memset(path,'a',sizeof(path));path[0]='/';path[1024]=0;
 CHECK(cohLiveTransportOpen(&t,path,token,DEVICE,INODE,&handle)==1);CHECK(p.requests==1);finish(&p,&t);
 setup(&p,&t);path[1024]='a';path[1025]=0;
 CHECK(cohLiveTransportOpen(&t,path,token,DEVICE,INODE,&handle)==-1);CHECK(p.requests==0);finish(&p,&t);
 setup(&p,&t);CHECK(cohLiveTransportOpen(&t,"/",token,DEVICE,INODE,&handle)==1);finish(&p,&t);
}
static void emptyAndFull(void) {
 Peer p;CohLiveTransport t;uint32_t handle,requests;const unsigned char *row;unsigned i;
 setup(&p,&t);CHECK(openDirectory(&p,&t,1,&handle)==1);p.fault=EMPTY_FINAL;
 CHECK(cohLiveTransportNext(&t,handle,&row)==0&&row==NULL);requests=p.requests;
 CHECK(cohLiveTransportNext(&t,handle,&row)==0&&p.requests==requests);CHECK(t.rows_returned==0);finish(&p,&t);
 setup(&p,&t);CHECK(openDirectory(&p,&t,1,&handle)==1);p.fault=FULL_BATCH;
 for(i=0;i<85;i++)CHECK(cohLiveTransportNext(&t,handle,&row)==1);
 CHECK(cohLiveTransportNext(&t,handle,&row)==0&&t.rows_returned==85);CHECK(p.requests==2);finish(&p,&t);
}
int main(int argc,char **argv) {
 CHECK(argc==2);
 if(!strcmp(argv[1],"basic"))basic();else if(!strcmp(argv[1],"malformed"))malformed();
 else if(!strcmp(argv[1],"acknowledgements"))acknowledgements();else if(!strcmp(argv[1],"io"))ioFailures();
 else if(!strcmp(argv[1],"declines"))declines();else if(!strcmp(argv[1],"bounds"))bounds();
 else if(!strcmp(argv[1],"allocation"))allocationFailures();else if(!strcmp(argv[1],"paths"))paths();
 else if(!strcmp(argv[1],"empty-full"))emptyAndFull();else return 2;
 printf("{\"group\":\"%s\",\"checks\":%u,\"passed\":true}\n",argv[1],checks);return 0;
}
