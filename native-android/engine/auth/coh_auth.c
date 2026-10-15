#include "coh_auth.h"
#include "../../protocol/coh_protocol.h"
#include <stdio.h>
#include <string.h>
const uint8_t coh_auth_dh_prime[64]={
 0x88,0x9c,0x71,0x97,0xe0,0xb8,0x8d,0x04,0xa2,0xcf,0x46,0xfd,0x12,0x5f,0xf2,0x9c,
 0xb8,0x0f,0x1f,0xc4,0x27,0x10,0x7b,0x88,0xf5,0x73,0x1a,0x96,0x09,0x44,0xb5,0x59,
 0x49,0xdf,0xf8,0xac,0xf6,0xb8,0x35,0xda,0x41,0x11,0x29,0xa4,0x92,0x2e,0x3f,0x5c,
 0x6c,0x4d,0x2f,0x12,0x31,0x0c,0x5a,0xff,0x3e,0xf8,0xca,0x40,0x1f,0xa8,0xf6,0x1f};
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
 }
static uint16_t u16(const uint8_t *p){return (uint16_t)((uint16_t)p[0]|(uint16_t)p[1]<<8);
 }
static void put32(uint8_t *p,uint32_t v){p[0]=(uint8_t)v;
 p[1]=(uint8_t)(v>>8);
 p[2]=(uint8_t)(v>>16);
 p[3]=(uint8_t)(v>>24);
 }
void coh_auth_wipe(void *p,size_t n){volatile uint8_t *v=(volatile uint8_t *)p;
 if(v)while(n--)*v++=0;
 }
static int valid_span(CohBytes b){return b.data||!b.size;
 }
static int range_key(const uint8_t v[64]){
 uint8_t upper[64],one[64]={0};
 one[63]=1;
 memcpy(upper,coh_auth_dh_prime,64);
 upper[63]--;
 return memcmp(v,one,64)>0&&memcmp(v,upper,64)<0;
}
CohStatus coh_auth_dh_keypair(const CohAuthCrypto *p,uint8_t private_key[64],uint8_t public_key[64]){
 uint8_t a[64]={0},b[64]={0};
 CohStatus s;
 if(!p||!p->keypair||!private_key||!public_key)return COH_INVALID;
 if((uintptr_t)private_key<=(uintptr_t)public_key?
    (uintptr_t)public_key-(uintptr_t)private_key<64:
    (uintptr_t)private_key-(uintptr_t)public_key<64)return COH_INVALID;
 s=p->keypair(p->context,a,b);
 if(s==COH_OK&&(!range_key(a)||!range_key(b)))s=COH_INVALID;
 if(s==COH_OK){memcpy(private_key,a,64);
 memcpy(public_key,b,64);
 }
 coh_auth_wipe(a,64);
 coh_auth_wipe(b,64);
 return s;
}
CohStatus coh_auth_dh_blowfish(const CohAuthCrypto *p,const uint8_t private_key[64],const uint8_t peer_key[64],CohBlowfish *out){
 uint8_t shared[64]={0},digest[16]={0};
 CohBlowfish key;
 CohStatus s;
 if(!p||!p->shared||!p->md5||!private_key||!peer_key||!out||!range_key(private_key)||!range_key(peer_key))return COH_INVALID;
 s=p->shared(p->context,private_key,peer_key,shared);
 if(s==COH_OK)s=p->md5(p->context,(CohBytes){shared,64},digest);
 if(s==COH_OK&&coh_bf_init(&key,digest,16))s=COH_INVALID;
 if(s==COH_OK)*out=key;
 coh_auth_wipe(&key,sizeof(key));
 coh_auth_wipe(shared,64);
 coh_auth_wipe(digest,16);
 return s;
}
static void global_key(CohBlowfish *key){
 static const uint8_t k[]={0xa4,0xde,0x6b,0x64,0xff,0x24,0xad,0x74,0x52,0xa0,0x6a,0x35,0xaf,0xf5,0x37,0x11,0xd3,0x5a,0xc8,0x42};
 (void)coh_bf_init(key,k,sizeof(k));
}
CohStatus coh_auth_global_encode(CohBytes body,uint8_t *out,size_t cap,size_t *bytes){
 uint8_t frame[COH_AUTH_BODY_MAX+2]={0};
 size_t pad,n,i;
 uint32_t sum=0;
 CohBlowfish key;
 if(!valid_span(body)||!body.size||!out||!bytes)return COH_INVALID;
 if(body.size>COH_AUTH_BODY_MAX-8)return COH_LIMIT;
 pad=(body.size+7u)&~(size_t)7;
 n=pad+10;
 if(n>cap)return COH_LIMIT;
 memcpy(frame+2,body.data,body.size);
 for(i=0;i<pad;i+=4)sum^=u32(frame+2+i);
 put32(frame+2+pad,sum);
 global_key(&key);
 (void)coh_bf_crypt(&key,frame+2,pad+8,0);
 frame[0]=(uint8_t)n;
 frame[1]=(uint8_t)(n>>8);
 memcpy(out,frame,n);
 *bytes=n;
 coh_auth_wipe(&key,sizeof(key));
 coh_auth_wipe(frame,sizeof(frame));
 return COH_OK;
}
CohStatus coh_auth_global_decode(CohBytes frame,uint8_t *out,size_t cap,size_t *bytes){
 uint8_t plain[COH_AUTH_BODY_MAX];
 size_t n,pad,i;
 uint32_t sum=0;
 CohBlowfish key;
 if(!valid_span(frame)||!out||!bytes||frame.size<18)return COH_INVALID;
 n=frame.size-2;
 if(n>sizeof(plain))return COH_LIMIT;
 if(u16(frame.data)!=frame.size||(n&7)||n<16)return COH_INVALID;
 pad=n-8;
 if(pad>cap)return COH_LIMIT;
 memcpy(plain,frame.data+2,n);
 global_key(&key);
 (void)coh_bf_crypt(&key,plain,n,1);
 coh_auth_wipe(&key,sizeof(key));
 for(i=0;i<pad;i+=4)sum^=u32(plain+i);
 if(sum!=u32(plain+pad)){coh_auth_wipe(plain,sizeof(plain));
 return COH_INVALID;
 }
 memcpy(out,plain,pad);
 *bytes=pad;
 coh_auth_wipe(plain,sizeof(plain));
 return COH_OK;
}
void coh_auth_stream_reset(CohAuthStream *s){if(s)coh_auth_wipe(s,sizeof(*s));
 }
CohStatus coh_auth_stream_feed(CohAuthStream *s,CohBytes input,size_t *consumed,CohBytes *frame){
 size_t take,goal;
 if(!s||!consumed||!frame||!valid_span(input))return COH_INVALID;
 *consumed=0;
 *frame=(CohBytes){0,0};
 if(s->failed)return COH_STATE;
 if(s->expected&&s->used==s->expected){s->used=0;
 s->expected=0;
 }
 while(*consumed<input.size){
  goal=s->expected?s->expected:2;
 take=goal-s->used;
 if(take>input.size-*consumed)take=input.size-*consumed;
  memcpy(s->data+s->used,input.data+*consumed,take);
 s->used+=take;
 *consumed+=take;
  if(s->used==2&&!s->expected){s->expected=u16(s->data);
 if(s->expected<3||s->expected>sizeof(s->data)){s->failed=1;
 return COH_INVALID;
 }}
  if(s->expected&&s->used==s->expected){*frame=(CohBytes){s->data,s->used};
 return COH_OK;
 }
 }
 return COH_NOT_FOUND;
}
typedef struct { CohBytes b;
 size_t at;
 int bad;
  } Reader;
static uint32_t get(Reader *r,size_t n){uint32_t v=0;
 size_t i;
 if(n>4||r->at>r->b.size||n>r->b.size-r->at){r->bad=1;
 return 0;
 }for(i=0;i<n;i++)v|=(uint32_t)r->b.data[r->at++]<<(8*i);
 return v;
 }
static void array(Reader *r,void *out,size_t n){if(r->at>r->b.size||n>r->b.size-r->at){r->bad=1;
 return;
 }memcpy(out,r->b.data+r->at,n);
 r->at+=n;
 }
static int end(Reader *r){return !r->bad&&r->b.size<=COH_AUTH_BODY_MAX&&r->at<=r->b.size&&r->b.size-r->at<=7;
 }
static int supported(uint32_t p){return p==COH_AUTH_GLOBAL||p==COH_AUTH_REACTIVATION||p==COH_AUTH_OUROBOROS1||p==COH_AUTH_OUROBOROS2;
 }
CohStatus coh_auth_parse_hello(CohBytes b,CohAuthHello *out){
 CohAuthHello v={0};
 Reader r={b,0,0};
 if(!out||!valid_span(b))return COH_INVALID;
 if(get(&r,1)!=0)return COH_INVALID;
 v.one_time_key=get(&r,4);
 v.protocol=get(&r,4);
 if(!v.protocol)v.protocol=COH_AUTH_GLOBAL;
 v.exponent_bytes=get(&r,4);
 if(!v.exponent_bytes||v.exponent_bytes>sizeof(v.exponent))return COH_INVALID;
 array(&r,v.exponent,v.exponent_bytes);
 v.modulus_bytes=get(&r,4);
 if(v.modulus_bytes<64||v.modulus_bytes>sizeof(v.modulus))return COH_INVALID;
 array(&r,v.modulus,v.modulus_bytes);
 if(!end(&r)||!(v.exponent[v.exponent_bytes-1]&1)||!(v.modulus[v.modulus_bytes-1]&1)||!v.modulus[0])return COH_INVALID;
 if(!supported(v.protocol))return COH_UNSUPPORTED;
 *out=v;
 return COH_OK;
}
CohStatus coh_auth_parse_login_ok(CohBytes b,uint32_t protocol,CohAuthLoginOk *out){
 CohAuthLoginOk v={0};
 Reader r={b,0,0};
 if(!out||!valid_span(b))return COH_INVALID;
 if(!supported(protocol))return COH_UNSUPPORTED;
 if(get(&r,1)!=3)return COH_INVALID;
 array(&r,v.session,8);
 array(&r,v.update_key,8);
 v.pay_status=get(&r,4);
 v.loyalty=get(&r,4);
 v.remaining=get(&r,4);
 v.quota=get(&r,4);
 v.warning=get(&r,4);
 v.login_flags=get(&r,4);
 if(protocol>=COH_AUTH_REACTIVATION)v.reactivation=get(&r,4);
 if(!end(&r))return COH_INVALID;
 *out=v;
 return COH_OK;
}
CohStatus coh_auth_parse_play_ok(CohBytes b,CohAuthPlayOk *out){
 CohAuthPlayOk v={0};
 Reader r={b,0,0};
 if(!out||!valid_span(b))return COH_INVALID;
 if(get(&r,1)!=7)return COH_INVALID;
 v.game_key=get(&r,4);
 v.user_id=get(&r,4);
 v.shard_id=(uint8_t)get(&r,1);
 if(!end(&r)||!v.shard_id||!v.user_id)return COH_INVALID;
 *out=v;
 return COH_OK;
}
CohStatus coh_auth_parse_shards(CohBytes b,uint32_t protocol,int extended,CohAuthShards *out){
 CohAuthShards v={0};
 Reader r={b,0,0};
 size_t i,j,n;
 uint32_t port;
 if(!out||!valid_span(b))return COH_INVALID;
 if(!supported(protocol))return COH_UNSUPPORTED;
 if(get(&r,1)!=4)return COH_INVALID;
 v.count=(uint8_t)get(&r,1);
 v.last_shard=(uint8_t)get(&r,1);
 if(v.count>COH_AUTH_SHARDS_MAX)return COH_LIMIT;
 for(i=0;i<v.count;i++){
  CohAuthShard *s=&v.shards[i];
 s->id=(uint8_t)get(&r,1);
 array(&r,s->ipv4,4);
 port=get(&r,4);
 if(!port||port>65535)return COH_INVALID;
 s->port=(uint16_t)port;
  s->age_limit=(uint8_t)get(&r,1);
 s->pk=(uint8_t)get(&r,1);
 s->current_users=(uint16_t)get(&r,2);
 s->maximum_users=(uint16_t)get(&r,2);
 s->status=(uint8_t)get(&r,1);
 s->vip=(uint8_t)get(&r,1);
  if(extended)s->type=get(&r,4);
 if(protocol>=COH_AUTH_OUROBOROS1){n=get(&r,1);
 array(&r,s->name,n);
 s->name[n]=0;
 for(j=0;j<n;j++)if((uint8_t)s->name[j]<32)return COH_INVALID;
 }
  if(!s->id||r.bad)return COH_INVALID;
 for(j=0;j<i;j++)if(v.shards[j].id==s->id)return COH_INVALID;
 }
 if(!end(&r))return COH_INVALID;
 *out=v;
 return COH_OK;
}
CohStatus coh_auth_server_list(const uint8_t session[8],uint32_t protocol,const uint32_t *groups,size_t count,uint8_t *out,size_t cap,size_t *bytes){
 uint8_t b[51];
 size_t n=10,i;
 if(!session||!out||!bytes||(!groups&&count))return COH_INVALID;
 if(!supported(protocol))return COH_UNSUPPORTED;
 if(count>10)return COH_LIMIT;
 if(count&&protocol<COH_AUTH_OUROBOROS2)return COH_UNSUPPORTED;
 b[0]=5;
 memcpy(b+1,session,8);
 b[9]=1;
 if(protocol>=COH_AUTH_OUROBOROS2){b[n++]=(uint8_t)count;
 for(i=0;i<count;i++){put32(b+n,groups[i]);
 n+=4;
 }}
 if(cap<n)return COH_LIMIT;
 memcpy(out,b,n);
 *bytes=n;
 return COH_OK;
}
CohStatus coh_auth_about_to_play(const uint8_t session[8],uint8_t shard,uint8_t *out,size_t cap,size_t *bytes){
 uint8_t b[10];
 if(!session||!shard||!out||!bytes)return COH_INVALID;
 if(cap<10)return COH_LIMIT;
 b[0]=2;
 memcpy(b+1,session,8);
 b[9]=shard;
 memcpy(out,b,10);
 *bytes=10;
 return COH_OK;
}
static uint32_t account_adler(const uint8_t *p,size_t n){uint32_t a=1,b=0;
 size_t i;
 for(i=0;i<n;i++){a=(a+p[i])%65521;
 b=(b+a)%65521;
 }/* CryptoPP Final writes BE bytes, source loads LE. */return ((b>>8)&255)|((b&255)<<8)|((a>>8)<<16)|((a&255)<<24);
 }
CohStatus coh_auth_login(const CohAuthCrypto *p,const CohAuthHello *hello,const char *account,const char *password,uint32_t subscription,uint16_t flags,uint8_t *out,size_t cap,size_t *bytes){
 uint8_t plain[94]={0},password_buf[17]={0},lineage[16],passkey[16],mdinput[28],sha_input[24],hash[64],cipher[512],body[523];
 char normalized[15]={0},salt[9],session[12];
 size_t alen=0,plen=0,start=0,stop,i,n=0;
 uint8_t pad=0;
 CohStatus s=COH_INVALID;
 static const uint32_t mul[]={213119,213247,213203,213821},add[]={2529077,2529089,2529589,2529997};
 if(!p||!p->md5||!p->sha512||!p->rsa_oaep_sha1||!hello||!account||!password||!out||!bytes)return COH_INVALID;
 if(hello->modulus_bytes<64||hello->modulus_bytes>sizeof(hello->modulus)||!hello->exponent_bytes||hello->exponent_bytes>sizeof(hello->exponent))return COH_INVALID;
 if(!supported(hello->protocol))return COH_UNSUPPORTED;
 while(alen<15&&account[alen])alen++;
 while(plen<17&&password[plen])plen++;
 if(alen>14||!alen||plen>16)return COH_LIMIT;
 while(start<alen&&account[start]==' ')start++;
 stop=alen;
 while(stop>start&&account[stop-1]==' ')stop--;
 if(stop==start)return COH_INVALID;
 for(i=start;i<stop;i++){unsigned char c=(unsigned char)account[i];
 if(c<32||c>126)return COH_INVALID;
 normalized[i-start]=(char)(c>='A'&&c<='Z'?c+32:c);
 }alen=stop-start;
 memcpy(password_buf,password,plen);
 memcpy(lineage,password_buf,16);
 for(i=0;i<4;i++)put32(passkey+4*i,u32(lineage+4*i)*mul[i]+add[i]);
 for(i=0;i<16;i++){lineage[i]^=pad^passkey[i];
 pad=lineage[i];
 if(!lineage[i])lineage[i]=0x66;
 }
 (void)snprintf(session,sizeof(session),"%d",(int32_t)hello->one_time_key);
 memcpy(mdinput,lineage,16);
 n=strlen(session);
 memcpy(mdinput+16,session,n);
 s=p->md5(p->context,(CohBytes){mdinput,16+n},plain+14);
 if(s!=COH_OK)goto done;
 (void)snprintf(salt,sizeof(salt),"%08x",account_adler((const uint8_t *)normalized,alen));
 memcpy(sha_input,password_buf,plen);
 memcpy(sha_input+plen,salt,8);
 s=p->sha512(p->context,(CohBytes){sha_input,plen+8},hash);
 if(s!=COH_OK)goto done;
 /* cryptSHA512Final swaps every U64 on LE hosts before memcpy to RSA input. */
 for(i=0;i<64;i++)plain[30+i]=hash[(i&~(size_t)7)+(7-(i&7))];
 memcpy(plain,normalized,alen);
 s=p->rsa_oaep_sha1(p->context,(CohBytes){hello->modulus,hello->modulus_bytes},(CohBytes){hello->exponent,hello->exponent_bytes},(CohBytes){plain,94},cipher,sizeof(cipher),&n);
 if(s!=COH_OK)goto done;
 if(!n||n>sizeof(cipher)){s=COH_INVALID;
 goto done;
 }if(cap<n+11){s=COH_LIMIT;
 goto done;
 }
 body[0]=4;
 put32(body+1,(uint32_t)n);
 memcpy(body+5,cipher,n);
 put32(body+5+n,subscription);
 body[9+n]=(uint8_t)flags;
 body[10+n]=(uint8_t)(flags>>8);
 memcpy(out,body,n+11);
 *bytes=n+11;
 s=COH_OK;
 done:coh_auth_wipe(plain,sizeof(plain));
 coh_auth_wipe(password_buf,sizeof(password_buf));
 coh_auth_wipe(lineage,sizeof(lineage));
 coh_auth_wipe(passkey,sizeof(passkey));
 coh_auth_wipe(mdinput,sizeof(mdinput));
 coh_auth_wipe(sha_input,sizeof(sha_input));
 coh_auth_wipe(hash,sizeof(hash));
 coh_auth_wipe(cipher,sizeof(cipher));
 coh_auth_wipe(body,sizeof(body));
 coh_auth_wipe(normalized,sizeof(normalized));
 coh_auth_wipe(salt,sizeof(salt));
 coh_auth_wipe(session,sizeof(session));
 return s;
}
CohStatus coh_auth_map_handoff_profile(CohBytes b,size_t bit_length,int byte_aligned,CohAuthMapHandoff *out){
 CohProtocolBits bits;
 CohAuthMapHandoff v={0};
 uint32_t values[7];
 size_t i;
 if(!out||!valid_span(b)||b.size>COH_PROTOCOL_FRAME_MAX||bit_length>b.size*8||bit_length>7*68||(byte_aligned!=0&&byte_aligned!=1))return COH_INVALID;
 if(coh_protocol_bits_init(&bits,(uint8_t *)b.data,b.size,bit_length,0))return COH_INVALID;
 for(i=0;i<7;i++)if(byte_aligned?coh_protocol_read(&bits,32,&values[i]):coh_protocol_read_pack(&bits,1,&values[i]))return COH_INVALID;
 if(bits.cursor!=bit_length||values[4]>65535||values[5]>65535||!values[4]||values[6]<2)return COH_INVALID;
 v.link_id=values[0];
 v.map_id=values[1];
 v.address[0]=values[2];
 v.address[1]=values[3];
 v.udp_port=(uint16_t)values[4];
 v.tcp_port=(uint16_t)values[5];
 v.cookie=values[6];
 *out=v;
 return COH_OK;
}
CohStatus coh_auth_map_handoff(CohBytes b,size_t bit_length,CohAuthMapHandoff *out){return coh_auth_map_handoff_profile(b,bit_length,0,out);}
