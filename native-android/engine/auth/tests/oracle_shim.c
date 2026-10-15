/* Test-only hooks: synthetic fixture inputs; no connection or login success. */
#include "../coh_auth.h"
#include <string.h>
typedef struct { uint8_t plain[94];const CohAuthCrypto *base; } Capture;
static CohStatus md5(void *v,CohBytes b,uint8_t out[16]){Capture *c=v;return c->base->md5(c->base->context,b,out);}
static CohStatus sha512(void *v,CohBytes b,uint8_t out[64]){Capture *c=v;return c->base->sha512(c->base->context,b,out);}
static CohStatus capture(void *v,CohBytes mod,CohBytes exp,CohBytes b,uint8_t *out,size_t cap,size_t *bytes){
 Capture *c=v;(void)mod;(void)exp;if(b.size!=94||cap<64)return COH_INVALID;memcpy(c->plain,b.data,94);memset(out,0x42,64);*bytes=64;return COH_OK;
}
int auth_test_plain(const char *account,const char *password,uint32_t key,uint8_t out[94]){
 Capture c={{0},coh_auth_openssl_provider()};CohAuthCrypto provider={&c,0,0,md5,sha512,capture};CohAuthHello h={0};uint8_t wire[128];size_t bytes=0;CohStatus s;
 h.protocol=COH_AUTH_OUROBOROS2;h.one_time_key=key;h.modulus_bytes=144;h.exponent_bytes=3;
 s=coh_auth_login(&provider,&h,account,password,0,0,wire,sizeof(wire),&bytes);if(s==COH_OK)memcpy(out,c.plain,94);coh_auth_wipe(&c,sizeof(c));coh_auth_wipe(wire,sizeof(wire));return s;
}
int auth_test_shared(const uint8_t x[64],const uint8_t peer[64],uint8_t out[64]){const CohAuthCrypto *p=coh_auth_openssl_provider();return p->shared(p->context,x,peer,out);}
