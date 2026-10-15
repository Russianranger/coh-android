#include "../coh_auth.h"
#include "../../../protocol/coh_protocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#ifdef COH_AUTH_TEST_OPENSSL
#include <openssl/bn.h>
#include <openssl/core_names.h>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#endif
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)){fprintf(stderr,"auth assertion line %d\n",__LINE__);return 1;} } while(0)
static void put32(uint8_t *p,uint32_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);}
static int portable(void){
 uint8_t body[1000]={0},wire[1002],plain[1000],both[2004],expected[1000];size_t n=0,m=0,i,j,used;CohBytes frame;CohAuthStream stream={0};
 CohAuthHello hello,oldhello;CohAuthLoginOk login;CohAuthPlayOk play;CohAuthShards shards;CohAuthMapHandoff handoff;CohProtocolBits bits;
 for(i=1;i<=985;i+=7){
  for(j=0;j<i;j++)body[j]=(uint8_t)(j*17+i);
  CHECK(coh_auth_global_encode((CohBytes){body,i},wire,sizeof(wire),&n)==COH_OK);
  CHECK(coh_auth_global_decode((CohBytes){wire,n},plain,sizeof(plain),&m)==COH_OK);
  CHECK(m==((i+7)&~(size_t)7)&&!memcmp(body,plain,i));for(j=i;j<m;j++)CHECK(!plain[j]);
  memcpy(expected,plain,m);wire[n/2]^=1;CHECK(coh_auth_global_decode((CohBytes){wire,n},plain,sizeof(plain),&m)==COH_INVALID);CHECK(!memcmp(expected,plain,m));wire[n/2]^=1;
 }
 body[0]=7;CHECK(coh_auth_global_encode((CohBytes){body,10},wire,sizeof(wire),&n)==COH_OK);
 memcpy(both,wire,n);memcpy(both+n,wire,n);
 for(i=0;i<n;i++){CHECK(coh_auth_stream_feed(&stream,(CohBytes){both+i,1},&used,&frame)==(i+1==n?COH_OK:COH_NOT_FOUND));CHECK(used==1);}
 CHECK(frame.size==n&&!memcmp(frame.data,wire,n));CHECK(coh_auth_stream_feed(&stream,(CohBytes){both+n,n},&used,&frame)==COH_OK&&used==n);
 coh_auth_stream_reset(&stream);both[0]=1;both[1]=0;CHECK(coh_auth_stream_feed(&stream,(CohBytes){both,2},&used,&frame)==COH_INVALID);CHECK(coh_auth_stream_feed(&stream,(CohBytes){wire,n},&used,&frame)==COH_STATE);coh_auth_stream_reset(&stream);
 memset(body,0,sizeof(body));body[0]=0;put32(body+1,0x81234567);put32(body+5,COH_AUTH_OUROBOROS2);put32(body+9,3);body[13]=1;body[14]=0;body[15]=1;put32(body+16,144);body[20]=0x80;body[163]=1;
 CHECK(coh_auth_parse_hello((CohBytes){body,164},&hello)==COH_OK);CHECK(hello.one_time_key==0x81234567&&hello.modulus_bytes==144&&hello.exponent_bytes==3);
 oldhello=hello;for(i=0;i<164;i++){CHECK(coh_auth_parse_hello((CohBytes){body,i},&hello)!=COH_OK);CHECK(!memcmp(&hello,&oldhello,sizeof(hello)));}
 put32(body+5,12345);CHECK(coh_auth_parse_hello((CohBytes){body,164},&hello)==COH_UNSUPPORTED);
 memset(body,0,sizeof(body));body[0]=3;body[1]=42;body[9]=17;put32(body+17,5);put32(body+41,1);
 CHECK(coh_auth_parse_login_ok((CohBytes){body,45},COH_AUTH_OUROBOROS2,&login)==COH_OK&&login.session[0]==42&&login.update_key[0]==17&&login.pay_status==5&&login.reactivation==1);
 for(i=0;i<45;i++)CHECK(coh_auth_parse_login_ok((CohBytes){body,i},COH_AUTH_OUROBOROS2,&login)!=COH_OK);
 body[0]=7;put32(body+1,777);put32(body+5,99);body[9]=3;CHECK(coh_auth_parse_play_ok((CohBytes){body,10},&play)==COH_OK&&play.game_key==777&&play.user_id==99&&play.shard_id==3);
 for(i=0;i<10;i++)CHECK(coh_auth_parse_play_ok((CohBytes){body,i},&play)!=COH_OK);
 memset(body,0,sizeof(body));body[0]=4;body[1]=1;body[2]=5;body[3]=5;body[4]=127;body[7]=1;put32(body+8,7000);body[18]=1;body[20]=4;memcpy(body+21,"Test",4);
 CHECK(coh_auth_parse_shards((CohBytes){body,25},COH_AUTH_OUROBOROS2,0,&shards)==COH_OK&&shards.count==1&&shards.shards[0].port==7000&&!strcmp(shards.shards[0].name,"Test"));
 for(i=0;i<25;i++)CHECK(coh_auth_parse_shards((CohBytes){body,i},COH_AUTH_OUROBOROS2,0,&shards)!=COH_OK);
 body[1]=33;CHECK(coh_auth_parse_shards((CohBytes){body,25},COH_AUTH_OUROBOROS2,0,&shards)==COH_LIMIT);
 {uint8_t session[8]={1,2,3,4,5,6,7,8};uint32_t groups[2]={1,0x12345678};
 CHECK(coh_auth_server_list(session,COH_AUTH_OUROBOROS2,groups,2,body,sizeof(body),&n)==COH_OK&&n==19&&body[0]==5&&body[9]==1&&body[10]==2&&body[15]==0x78);
 CHECK(coh_auth_server_list(session,COH_AUTH_GLOBAL,groups,2,body,sizeof(body),&n)==COH_UNSUPPORTED);
 CHECK(coh_auth_about_to_play(session,3,body,sizeof(body),&n)==COH_OK&&n==10&&body[0]==2&&body[9]==3);
 }
 memset(body,0,sizeof(body));CHECK(!coh_protocol_bits_init(&bits,body,sizeof(body),0,1));
 {uint32_t values[7]={1,24,0x0100007f,0,7001,7002,1234};for(i=0;i<7;i++)CHECK(!coh_protocol_write_pack(&bits,1,values[i]));}
 CHECK(coh_auth_map_handoff((CohBytes){body,(bits.bit_length+7)/8},bits.bit_length,&handoff)==COH_OK&&handoff.map_id==24&&handoff.udp_port==7001&&handoff.cookie==1234);
 for(i=0;i<bits.bit_length;i++)CHECK(coh_auth_map_handoff((CohBytes){body,(bits.bit_length+7)/8},i,&handoff)!=COH_OK);
 {uint32_t values[7]={1,24,0x0100007f,0,7001,7002,1234};for(i=0;i<7;i++)put32(body+i*4,values[i]);CHECK(coh_auth_map_handoff_profile((CohBytes){body,28},224,1,&handoff)==COH_OK&&handoff.map_id==24&&handoff.udp_port==7001&&handoff.cookie==1234);CHECK(coh_auth_map_handoff_profile((CohBytes){body,28},224,2,&handoff)==COH_INVALID);}
 {uint32_t rng=2647123;for(i=0;i<10000;i++){size_t length=i%sizeof(body);for(j=0;j<length;j++){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;body[j]=(uint8_t)rng;} (void)coh_auth_parse_hello((CohBytes){body,length},&hello);(void)coh_auth_parse_login_ok((CohBytes){body,length},COH_AUTH_OUROBOROS2,&login);(void)coh_auth_parse_play_ok((CohBytes){body,length},&play);(void)coh_auth_parse_shards((CohBytes){body,length},COH_AUTH_OUROBOROS2,0,&shards);(void)coh_auth_global_decode((CohBytes){body,length},plain,sizeof(plain),&m);coh_auth_stream_reset(&stream);(void)coh_auth_stream_feed(&stream,(CohBytes){body,length},&used,&frame);}}
 return 0;
}
#ifdef COH_AUTH_TEST_OPENSSL
static int crypto(void){
 const CohAuthCrypto *p=coh_auth_openssl_provider();uint8_t a[64],A[64],b[64],B[64],invalid[64]={0},encoded[8]={1,2,3,4,5,6,7,8},x[64]={0},peer[64]={0};CohBlowfish c,d,reference;size_t i;
 static const uint8_t expected_md5[16]={0x56,0x85,0x9b,0x2f,0x54,0xf4,0x96,0xe8,0xbb,0x0a,0x09,0x23,0x19,0x75,0x84,0x2e};uint8_t secret[64]={0},digest[16];
 for(i=0;i<12;i++){CHECK(coh_auth_dh_keypair(p,a,A)==COH_OK&&coh_auth_dh_keypair(p,b,B)==COH_OK);CHECK(coh_auth_dh_blowfish(p,a,B,&c)==COH_OK&&coh_auth_dh_blowfish(p,b,A,&d)==COH_OK);CHECK(!memcmp(&c,&d,sizeof(c)));CHECK(!coh_bf_crypt(&c,encoded,8,0)&&!coh_bf_crypt(&d,encoded,8,1)&&encoded[0]==1&&encoded[7]==8);}
 x[63]=3;peer[63]=8;secret[62]=2;CHECK(p->shared(NULL,x,peer,a)==COH_OK&&!memcmp(a,secret,64));CHECK(p->md5(NULL,(CohBytes){secret,64},digest)==COH_OK&&!memcmp(digest,expected_md5,16));CHECK(!coh_bf_init(&reference,digest,16));CHECK(coh_auth_dh_blowfish(p,x,peer,&c)==COH_OK&&!memcmp(&c,&reference,sizeof(c)));
 memset(&c,0x42,sizeof(c));reference=c;CHECK(coh_auth_dh_blowfish(p,x,invalid,&c)==COH_INVALID&&!memcmp(&c,&reference,sizeof(c)));
 invalid[63]=1;CHECK(coh_auth_dh_blowfish(p,x,invalid,&c)==COH_INVALID);memcpy(invalid,coh_auth_dh_prime,64);invalid[63]--;CHECK(coh_auth_dh_blowfish(p,x,invalid,&c)==COH_INVALID);
 memset(invalid,0,64);invalid[63]=17;CHECK(coh_auth_dh_blowfish(p,x,invalid,&c)==COH_INVALID);/* valid range, wrong subgroup */
 /* Genuine RSA-OAEP roundtrip with an ephemeral disposable 1152-bit key. */
 {EVP_PKEY_CTX *gen=EVP_PKEY_CTX_new_from_name(NULL,"RSA",NULL),*dec;EVP_PKEY *key=NULL;BIGNUM *mod=NULL,*exp=NULL;CohAuthHello h={0};uint8_t wire[600],plain[256],repeat[600];size_t n=0,m=sizeof(plain),other=0;
 CHECK(gen&&EVP_PKEY_keygen_init(gen)>0&&EVP_PKEY_CTX_set_rsa_keygen_bits(gen,1152)>0&&EVP_PKEY_generate(gen,&key)>0);CHECK(EVP_PKEY_get_bn_param(key,OSSL_PKEY_PARAM_RSA_N,&mod)>0&&EVP_PKEY_get_bn_param(key,OSSL_PKEY_PARAM_RSA_E,&exp)>0);
 h.protocol=COH_AUTH_OUROBOROS2;h.one_time_key=0x81234567;h.modulus_bytes=(size_t)BN_num_bytes(mod);h.exponent_bytes=(size_t)BN_num_bytes(exp);CHECK(BN_bn2bin(mod,h.modulus)>0&&BN_bn2bin(exp,h.exponent)>0);
 CHECK(coh_auth_login(p,&h," Fixture ","fixtureonly",0,0,wire,sizeof(wire),&n)==COH_OK&&n==155&&wire[0]==4);
 CHECK(coh_auth_login(p,&h," Fixture ","fixtureonly",0,0,repeat,sizeof(repeat),&other)==COH_OK&&other==n&&memcmp(wire+5,repeat+5,144));
 dec=EVP_PKEY_CTX_new(key,NULL);CHECK(dec&&EVP_PKEY_decrypt_init(dec)>0&&EVP_PKEY_CTX_set_rsa_padding(dec,RSA_PKCS1_OAEP_PADDING)>0&&EVP_PKEY_CTX_set_rsa_oaep_md(dec,EVP_sha1())>0&&EVP_PKEY_CTX_set_rsa_mgf1_md(dec,EVP_sha1())>0);CHECK(EVP_PKEY_decrypt(dec,plain,&m,wire+5,144)>0&&m==94&&!memcmp(plain,"fixture",7));
 CHECK(coh_auth_login(p,&h,"accounttoolonghere","fixtureonly",0,0,wire,sizeof(wire),&n)==COH_LIMIT);h.protocol=COH_AUTH_ASIA;CHECK(coh_auth_login(p,&h,"fixture","fixtureonly",0,0,wire,sizeof(wire),&n)==COH_UNSUPPORTED);
 EVP_PKEY_CTX_free(dec);EVP_PKEY_CTX_free(gen);EVP_PKEY_free(key);BN_free(mod);BN_free(exp);coh_auth_wipe(plain,sizeof(plain));coh_auth_wipe(wire,sizeof(wire));coh_auth_wipe(repeat,sizeof(repeat));
 }
 coh_auth_wipe(a,64);coh_auth_wipe(b,64);coh_auth_wipe(x,64);coh_auth_wipe(secret,64);coh_auth_wipe(digest,16);coh_auth_wipe(&c,sizeof(c));coh_auth_wipe(&d,sizeof(d));coh_auth_wipe(&reference,sizeof(reference));return 0;
}
#endif
int main(void){if(portable())return 1;
#ifdef COH_AUTH_TEST_OPENSSL
 if(crypto())return 1;
#endif
 printf("{\"checks\":%u,\"malformed_inputs\":10000,\"authenticated_server_session\":false}\n",checks);return 0;
}
