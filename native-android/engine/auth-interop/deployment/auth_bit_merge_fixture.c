/* Exact original bit-mask/merge code; public one-hot/deterministic fixtures. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t U32;typedef unsigned char U8;
#define AUTH_BYTES 128
#define AUTH_USER_AUTHSERVER 0
#define AUTH_USER_DBSERVER 1
#define STATIC_INFUNC_ASSERT(x) _Static_assert((x),"source mask size")
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define LOG_OLD(...) ((void)0)
/* EXACT_MASK_SOURCE */
static void original_merge(U8 output[128],const U8 auth[128],const U8 game[128]){
 struct {U8 user_data[128];} record;void*unused=0;(void)unused;
 U8 game_data[128];memcpy(record.user_data,auth,128);memcpy(game_data,game,128);
 __typeof__(record)*entry=&record;int i;
/* EXACT_MERGE_BLOCK */
 memcpy(output,entry->user_data,128);
}
static unsigned checks;
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"mask failed at %u\n",__LINE__);return 1;}}while(0)
static void hex(const U8*p){for(int i=0;i<128;++i)printf("%02x",p[i]);}
int main(void){U8 am[128],gm[128],a[128],g[128],out[128];U32 endian=1;CHECK(*(U8*)&endian==1);
 memset(am,255,128);memset(gm,255,128);authUserMaskAuthBits(am,0);authUserMaskAuthBits(gm,1);authUserMaskAuthBits(NULL,0);
 unsigned overlap=0;for(int i=0;i<128;++i)for(int b=0;b<8;++b)if((am[i]&gm[i])&(1u<<b))++overlap;
 for(unsigned bit=0;bit<1024;++bit)for(unsigned mode=0;mode<3;++mode){memset(a,0,128);memset(g,0,128);if(mode!=1)a[bit/8]=(U8)(1u<<(bit%8));if(mode!=0)g[bit/8]=(U8)(1u<<(bit%8));original_merge(out,a,g);for(unsigned i=0;i<128;++i)CHECK(out[i]==(U8)((a[i]&am[i])|(g[i]&gm[i])));}
 for(unsigned seed=0;seed<32;++seed){for(unsigned i=0;i<128;++i){a[i]=(U8)((i+seed)*17);g[i]=(U8)((i^seed)*31);}original_merge(out,a,g);for(unsigned i=0;i<128;++i)CHECK(out[i]==(U8)((a[i]&am[i])|(g[i]&gm[i])));}
 printf("{\"passed\":true,\"checks\":%u,\"bits\":1024,\"overlapping_source_bits\":%u,\"auth_mask\":\"",checks,overlap);hex(am);printf("\",\"db_mask\":\"");hex(gm);printf("\"}\n");return 0;}
