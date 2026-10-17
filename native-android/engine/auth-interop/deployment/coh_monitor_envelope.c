#include "coh_monitor_envelope.h"
#include <string.h>
static int disjoint(const void *a,size_t an,const void *b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!an||!bn)return 1;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;
 return x+an<=y||y+bn<=x;
}
CohStatus coh_monitor_request(unsigned legacy,uint8_t output[8],uint32_t *bits){
 if(legacy>1||!output||!bits||!disjoint(output,8,bits,sizeof(*bits)))return COH_INVALID;
 uint8_t local[8]={0};CohProtocolBits b;
 if(coh_protocol_bits_init(&b,local,sizeof(local),0,1)||coh_protocol_write_pack(&b,1,legacy?15:10))return COH_INVALID;
 memcpy(output,local,sizeof(local));*bits=(uint32_t)b.cursor;return COH_OK;
}
void coh_monitor_stream_reset(CohMonitorStream *s){if(s)memset(s,0,sizeof(*s));}
CohStatus coh_monitor_stream_feed(CohMonitorStream *s,CohBytes input,size_t *consumed,CohMonitorFrame *out){
 if(!s||!consumed||!out||(!input.data&&input.size))return COH_INVALID;
 const void *p[]={s,input.data,consumed,out};
 const size_t n[]={sizeof(*s),input.size,sizeof(*consumed),sizeof(*out)};
 for(unsigned i=0;i<4;i++)for(unsigned j=i+1;j<4;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;
 *consumed=0;if(s->failed)return COH_STATE;
 if(s->used>sizeof(s->data)||s->expected>sizeof(s->data)||(s->expected&&(s->expected<20||((s->expected-4)&7)||s->used<4))){s->failed=1;return COH_INVALID;}
 while(*consumed<input.size){
  size_t target=s->expected?s->expected:4;
  if(s->used>target){s->failed=1;return COH_INVALID;}
  size_t take=target-s->used;if(take>input.size-*consumed)take=input.size-*consumed;
  memcpy(s->data+s->used,input.data+*consumed,take);s->used+=take;*consumed+=take;
  if(!s->expected&&s->used==4){
   uint32_t bits=(uint32_t)s->data[0]|(uint32_t)s->data[1]<<8|(uint32_t)s->data[2]<<16|(uint32_t)s->data[3]<<24;
   /* Exact source blowfishPad byte-length convention, bounded before size_t
    * conversion.105 is the existing native frame decoder's minimum subset. */
   uint64_t bytes=((uint64_t)bits+7)/8;
   uint64_t padded=bytes<4?0:4+((bytes-4+7)&~UINT64_C(7));
   if(bits<105||padded>sizeof(s->data)||padded<20){s->failed=1;return COH_LIMIT;}
   s->expected=(size_t)padded;
  }
  if(s->expected&&s->used==s->expected){
   CohMonitorFrame frame;memset(&frame,0,sizeof(frame));frame.size=s->expected;
   memcpy(frame.data,s->data,frame.size);*out=frame;
   s->used=0;s->expected=0;return COH_OK;
  }
 }
 return COH_NOT_FOUND;
}
