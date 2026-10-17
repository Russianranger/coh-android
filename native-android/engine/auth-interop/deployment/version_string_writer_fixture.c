/* Minimal host shell for exact original bsWriteString; no real version getter. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t U8;typedef uint32_t U32;
typedef struct BitStream {
 U8 *data;struct {U32 byte,bit;}cursor;U32 size,maxSize,bitLength,errorFlags;
 int byteAlignedMode;void (*memAllocator)(struct BitStream*);
} BitStream;
#define BSASSERT(x) assert(x)
#define BSE_OVERFLOW 1
static U32 bsGetCursorBitPosition(BitStream *bs){return bs->cursor.byte*8+bs->cursor.bit;}
/* EXACT_ORIGINAL_WRITER */
int main(void){
 for(unsigned shift=0;shift<8;shift++)for(unsigned length=1;length<=99;length++){
  U8 data[512]={0};char first[100];memset(first,'v',length);first[length]=0;
  BitStream bs={0};bs.data=data;bs.maxSize=sizeof(data)-1;bs.cursor.bit=shift;
  bsWriteString(&bs,first);bsWriteString(&bs,"server-version");
  unsigned count=(bs.bitLength+7)/8;
  printf("{\"offset\":%u,\"length\":%u,\"bits\":%u,\"data\":\"",shift,length,bs.bitLength-shift);
  for(unsigned i=0;i<count;i++)printf("%02x",data[i]);
  printf("\"}\n");
 }
 return 0;
}
