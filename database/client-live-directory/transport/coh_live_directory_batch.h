/* Source-only bounded current-directory batch decoder. No runtime registration. */
#ifndef COH_LIVE_DIRECTORY_BATCH_H
#define COH_LIVE_DIRECTORY_BATCH_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define COH_LIVE_NT_BYTES 8192u
#define COH_LIVE_ROW_BYTES 328u
#define COH_LIVE_HEADER_BYTES 64u
#define COH_LIVE_MAX_ROWS 85u
#define COH_LIVE_MAX_DIRECTORY_ROWS 8192u
#define COH_LIVE_MAX_BYTES (COH_LIVE_HEADER_BYTES+COH_LIVE_MAX_ROWS*COH_LIVE_ROW_BYTES)
typedef struct CohLiveBatch {const unsigned char *rows;uint32_t count,first,final;} CohLiveBatch;
static uint32_t cohLiveU32(const unsigned char *p) {
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static int cohLiveBatchDecode(const unsigned char *data,size_t bytes,
 const unsigned char operation[16],const unsigned char directory[16],
 uint32_t expected_sequence,uint32_t expected_first,CohLiveBatch *output) {
 uint32_t count,i,used=0;
 if(!output)return 0;memset(output,0,sizeof(*output));
 if(!data||!operation||!directory||bytes<64||bytes>COH_LIVE_MAX_BYTES||
    memcmp(data,"COHLIVE1",8)||memcmp(data+8,operation,16)||memcmp(data+24,directory,16)||
    cohLiveU32(data+40)!=expected_sequence||cohLiveU32(data+44)!=expected_first||
    cohLiveU32(data+52)>1||cohLiveU32(data+56)!=0||cohLiveU32(data+60)!=bytes)return 0;
 count=cohLiveU32(data+48);
 if(count>COH_LIVE_MAX_ROWS||expected_first>COH_LIVE_MAX_DIRECTORY_ROWS||
    count>COH_LIVE_MAX_DIRECTORY_ROWS-expected_first||
    bytes!=64u+(size_t)count*328u||(!count&&!cohLiveU32(data+52))||
    (count&&expected_first>UINT32_MAX-(count-1u)))return 0;
 for(i=0;i<count;i++) {
  const unsigned char *row=data+64u+i*328u,*wfd=row+8;uint32_t name_length=0,j,nt;
  if(cohLiveU32(row)!=expected_first+i||cohLiveU32(row+4)!=0)return 0;
  while(name_length<260&&wfd[44+name_length]) {
   unsigned char c=wfd[44+name_length];
   if(c<32||c>=127||strchr("/\\:*?\"<>|",c))return 0;
   name_length++;
  }
  if(!name_length||name_length==260)return 0;
  for(j=44+name_length;j<304;j++)if(wfd[j])return 0;
  /* Defined WFD fields remain byte-for-byte. Reserved/padding are canonical. */
  for(j=36;j<44;j++)if(wfd[j])return 0;
  {uint32_t alternate=0;while(alternate<14&&wfd[304+alternate]) {
    unsigned char c=wfd[304+alternate];if(c<32||c>=127||strchr("/\\:*?\"<>|",c))return 0;alternate++;
   }if(alternate==14)return 0;
   for(j=304+alternate;j<320;j++)if(wfd[j])return 0;
  }
  nt=((used+7u)&~7u)+94u+name_length*2u;
  if(nt>8192u)return 0;used=nt;
 }
 output->rows=data+64;output->count=count;output->first=expected_first;output->final=cohLiveU32(data+52);
 return 1;
}
/* Context custody is controlled research only. Caller must separately bind the
 * actual consumer/session/thread/provider before production can use it. */
typedef struct CohLiveCursor {
 unsigned char bytes[COH_LIVE_MAX_BYTES],operation[16],directory[16];
 CohLiveBatch batch;uint32_t sequence,first,taken;uint64_t rows_returned;
 int terminal_failure,fallback_allowed,finished;
} CohLiveCursor;
static void cohLiveInit(CohLiveCursor *c,const unsigned char operation[16],const unsigned char directory[16]) {
 memset(c,0,sizeof(*c));memcpy(c->operation,operation,16);memcpy(c->directory,directory,16);
}
static int cohLiveFail(CohLiveCursor *c) {
 c->terminal_failure=1;c->fallback_allowed=c->rows_returned==0;
 memset(&c->batch,0,sizeof(c->batch));return 0;
}
static int cohLiveSubmit(CohLiveCursor *c,const unsigned char *data,size_t bytes) {
 if(c->terminal_failure||c->finished||c->taken<c->batch.count)return cohLiveFail(c);
 if(!data||bytes>sizeof(c->bytes))return cohLiveFail(c);
 /* Decode our own complete private copy; transport storage may be recycled. */
 memcpy(c->bytes,data,bytes);
 if(!cohLiveBatchDecode(c->bytes,bytes,c->operation,c->directory,c->sequence,c->first,&c->batch))return cohLiveFail(c);
 c->taken=0;c->sequence++;if(!c->batch.count&&c->batch.final)c->finished=1;return 1;
}
static const unsigned char *cohLiveTake(CohLiveCursor *c) {
 const unsigned char *out;
 if(c->terminal_failure||c->finished)return NULL;
 if(c->taken==c->batch.count) {if(c->batch.final)c->finished=1;return NULL;}
 out=c->batch.rows+c->taken*328u+8;c->taken++;c->rows_returned++;c->first++;
 if(c->taken==c->batch.count&&c->batch.final)c->finished=1;
 return out;
}
#endif
