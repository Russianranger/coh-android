/* Exact original consumer plus bounded cache/quiet logging fixtures. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
typedef uint32_t U32;typedef unsigned char U8;
#define AUTH_BYTES 128
#define AUTH_CACHE_SIZE 4096
#define AUTH_CACHE_MASK (AUTH_CACHE_SIZE-1)
#define stricmp strcasecmp
#define LOG_OLD(...) ((void)0)
#define LOG_OLD_ERR(...) ((void)0)
/* EXACT_AUTH_ENTRY */
static AuthEntry auth_cache[AUTH_CACHE_SIZE];
/* EXACT_FUNCTIONS */
static unsigned checks;
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"failed at %u\n",__LINE__);return 1;}}while(0)
static void seed(U32 cookie){AuthEntry*e=&auth_cache[cookie&AUTH_CACHE_MASK];memset(e,0,sizeof(*e));e->id=900001;e->cookie=cookie;e->created=0;strcpy(e->name,"sourcefixture");e->pay_stat=1;e->loyalty=123;e->loyaltyLegacy=456;for(unsigned i=0;i<AUTH_BYTES;++i)e->user_data[i]=(U8)(i*31+7);}
int main(void){U8 data[AUTH_BYTES];U32 l=0,g=0,p=0;char name[32];
 for(U32 slot=0;slot<AUTH_CACHE_SIZE;++slot){U32 cookie=0x76543000u|slot;seed(cookie);strcpy(name,"SOURCEFIXTURE   ");
  CHECK(authValidLogin(900001,cookie,name,data,&l,&g,&p)==1);CHECK(!strcmp(name,"sourcefixture"));CHECK(l==123&&g==456&&p==1);
  for(unsigned i=0;i<AUTH_BYTES;++i)CHECK(data[i]==(U8)(i*31+7));
  CHECK(auth_cache[slot].id==0&&auth_cache[slot].cookie==0);CHECK(authValidLogin(900001,cookie,name,data,&l,&g,&p)==0);
 }
 for(unsigned bit=0;bit<32;++bit){U32 cookie=0x76543210;seed(cookie);strcpy(name,"sourcefixture");CHECK(authValidLogin(900001,cookie^(1u<<bit),name,data,&l,&g,&p)==0);CHECK(auth_cache[cookie&AUTH_CACHE_MASK].id==900001);}
 seed(0);strcpy(name,"sourcefixture");CHECK(authValidLogin(900001,0,name,data,&l,&g,&p)==1);
 seed(123);strcpy(name,"sourcefixture");CHECK(authValidLogin(0,123,name,data,&l,&g,&p)==0);CHECK(authValidLogin(900002,123,name,data,&l,&g,&p)==0);
 strcpy(name,"wrongname");CHECK(authValidLogin(900001,123,name,data,&l,&g,&p)==0);CHECK(auth_cache[123].id==900001);
 strcpy(name,"sourcefixture\t");CHECK(authValidLogin(900001,123,name,data,&l,&g,&p)==0);
 strcpy(name,"sourcefixture");CHECK(authValidLogin(900001,123,name,data,&l,&g,&p)==1);
 printf("{\"passed\":true,\"checks\":%u,\"cache_slots\":4096,\"one_shot_consumer\":true,\"zero_cookie_source_semantics\":true,\"cookie_generator_executed\":false,\"live_service_executed\":false}\n",checks);return 0;
}
