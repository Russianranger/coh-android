#include "../coh_auth_interop.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"auth interop test line %d\n",__LINE__);exit(1);}}while(0)
static CohStatus kp(void *c,uint8_t a[64],uint8_t b[64]){(void)c;(void)a;(void)b;abort();}
static CohStatus sh(void *c,const uint8_t a[64],const uint8_t b[64],uint8_t d[64]){(void)c;(void)a;(void)b;(void)d;abort();}
static CohStatus md(void *c,CohBytes a,uint8_t d[16]){(void)c;(void)a;(void)d;abort();}
static CohStatus sha(void *c,CohBytes a,uint8_t d[64]){(void)c;(void)a;(void)d;abort();}
static CohStatus rsa(void *c,CohBytes a,CohBytes b,CohBytes d,uint8_t *e,size_t f,size_t *g){(void)c;(void)a;(void)b;(void)d;(void)e;(void)f;(void)g;abort();}
static const CohAuthCrypto fake={NULL,kp,sh,md,sha,rsa};
static CohAuthInteropProfile profile(void){
 CohAuthInteropProfile p;memset(&p,0,sizeof(p));p.auth=(CohNetEndpoint){{127,0,0,1},2106};
 p.db=(CohNetEndpoint){{127,0,0,1},7000};p.maps[0]=(CohNetEndpoint){{127,0,0,1},7002};p.map_count=1;
 p.shard_id=1;p.db_policy.protocol_version=COH_DB_PROTOCOL_VERSION;strcpy(p.db_policy.patch_version,"authorized-fixture-version");
 p.db_policy.executable_checksum[0]=7;strcpy(p.db_policy.system_spec,"Disabled");p.timeout_ms=30000;return p;
}
static void bad(CohAuthInteropProfile p,CohAuthInteropPolicyFailure reason){
 CohAuthInteropPolicyFailure f=COH_INTEROP_POLICY_OK;CHECK(coh_auth_interop_validate(&p,&f)==COH_INVALID&&f==reason);
 CohLiveConfig out,old;memset(&out,0xa5,sizeof(out));old=out;
 CHECK(coh_auth_interop_config(&p,&fake,&out)==COH_INVALID&&!memcmp(&out,&old,sizeof(out)));
 CHECK(coh_auth_interop_approve_map(&p,p.maps[0],1)==COH_INVALID);
}
int main(void){
 CohAuthInteropProfile p=profile(),q;CohAuthInteropPolicyFailure failure;CohLiveConfig c;
 CHECK(coh_auth_interop_validate(&p,&failure)==COH_OK&&failure==COH_INTEROP_POLICY_OK);
 CHECK(coh_auth_interop_config(&p,&fake,&c)==COH_OK);
 CHECK(c.db.transport.encryption_required==1&&c.map.udp.encryption_required==1);
 CHECK(c.db.transport.link.version==5&&c.map.udp.link.version==5&&c.policy_context==&p);
 CHECK(c.db.transport.peer.port==p.db.port&&c.authorized_auth.port==p.auth.port);
 CHECK(c.approve_map(c.policy_context,p.maps[0],1)==COH_OK);
 CHECK(c.approve_map(c.policy_context,p.maps[0],0)==COH_INVALID);
 CohNetEndpoint e=p.maps[0];e.port++;CHECK(c.approve_map(c.policy_context,e,1)==COH_INVALID);
 e=p.maps[0];e.address[3]++;CHECK(c.approve_map(c.policy_context,e,1)==COH_INVALID);
 p.maps[1]=p.maps[0];p.maps[1].port++;p.map_count=2;
 CHECK(coh_auth_interop_validate(&p,NULL)==COH_OK&&coh_auth_interop_approve_map(&p,p.maps[1],1)==COH_OK);
 q=p;q.maps[1]=q.maps[0];bad(q,COH_INTEROP_POLICY_ENDPOINT);p=profile();
 q=p;q.auth.port=0;bad(q,COH_INTEROP_POLICY_ENDPOINT);
 q=p;q.db.address[0]=224;bad(q,COH_INTEROP_POLICY_ENDPOINT);
 q=p;q.maps[0].address[0]=0;bad(q,COH_INTEROP_POLICY_ENDPOINT);
 q=p;q.map_count=0;bad(q,COH_INTEROP_POLICY_ENDPOINT);
 q=p;q.map_count=3;bad(q,COH_INTEROP_POLICY_ENDPOINT);
 q=p;q.shard_id=0;bad(q,COH_INTEROP_POLICY_SELECTION);
 q=p;q.character_slot=COH_DB_SLOTS_MAX;bad(q,COH_INTEROP_POLICY_SELECTION);
 q=p;q.db_policy.protocol_version++;bad(q,COH_INTEROP_POLICY_PROTOCOL);
 q=p;q.db_policy.patch_version[0]=0;bad(q,COH_INTEROP_POLICY_VERSION);
 q=p;memset(q.db_policy.patch_version,'a',sizeof(q.db_policy.patch_version));bad(q,COH_INTEROP_POLICY_VERSION);
 q=p;memset(q.db_policy.patch_version,'a',100);q.db_policy.patch_version[100]=0;bad(q,COH_INTEROP_POLICY_VERSION);
 q=p;q.db_policy.patch_version[0]='\n';bad(q,COH_INTEROP_POLICY_VERSION);
 q=p;memset(q.db_policy.executable_checksum,0,16);bad(q,COH_INTEROP_POLICY_CHECKSUM);
 q=p;q.db_policy.account[14]='a';bad(q,COH_INTEROP_POLICY_AUTH_INJECTION);
 q=p;q.db_policy.user_id=1;bad(q,COH_INTEROP_POLICY_AUTH_INJECTION);
 q=p;q.db_policy.cookie=1;bad(q,COH_INTEROP_POLICY_AUTH_INJECTION);
 q=p;q.db_policy.auth_user_data[127]=1;bad(q,COH_INTEROP_POLICY_AUTH_INJECTION);
 q=p;q.db_policy.no_version_check=1;bad(q,COH_INTEROP_POLICY_BYPASS);
 q=p;q.db_policy.no_timeout=1;bad(q,COH_INTEROP_POLICY_BYPASS);
 q=p;q.db_policy.keyed_access_level=1;bad(q,COH_INTEROP_POLICY_BYPASS);
 q=p;q.db_policy.keyed_access_issued_to[255]='a';bad(q,COH_INTEROP_POLICY_BYPASS);
 q=p;memset(q.db_policy.patch_message,'a',sizeof(q.db_policy.patch_message));bad(q,COH_INTEROP_POLICY_VERSION);
 q=p;memset(q.db_policy.system_spec,'a',sizeof(q.db_policy.system_spec));bad(q,COH_INTEROP_POLICY_VERSION);
 q=p;q.timeout_ms=999;bad(q,COH_INTEROP_POLICY_TIMEOUT);
 q=p;q.timeout_ms=300001;bad(q,COH_INTEROP_POLICY_TIMEOUT);
 CHECK(coh_auth_interop_validate(NULL,NULL)==COH_INVALID);
 CHECK(coh_auth_interop_config(&p,NULL,&c)==COH_INVALID);
 CohAuthCrypto broken=fake;broken.rsa_oaep_sha1=NULL;CHECK(coh_auth_interop_config(&p,&broken,&c)==COH_INVALID);
 /* Valid 99-byte version fits original server's 100-byte destination. */
 q=p;memset(q.db_policy.patch_version,'a',99);q.db_policy.patch_version[99]=0;CHECK(coh_auth_interop_validate(&q,NULL)==COH_OK);
 /* Parser-free policy accepts only bounded inputs, including arbitrary bytes. */
 uint32_t rng=0x1a2b3c4d;
 for(unsigned i=0;i<2048;i++){
  unsigned char *data=(unsigned char*)&q;
  for(size_t j=0;j<sizeof(q);j++){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;data[j]=(unsigned char)rng;}
  CHECK(coh_auth_interop_validate(&q,NULL)!=COH_OK);
 }
 CohLiveDiagnostics d={0};d.phase=COH_LIVE_SCENE_INCOMPLETE;d.auth_receipts=1;d.opened_sockets=3;d.closed_sockets=3;
 char text[2048],before[2048];memset(text,0xa5,sizeof(text));memcpy(before,text,sizeof(text));size_t bytes=7;
 CHECK(coh_auth_interop_report(&d,42,0,text,8,&bytes)==COH_LIMIT&&bytes==7&&!memcmp(text,before,sizeof(text)));
 CHECK(coh_auth_interop_report(&d,42,0,text,sizeof(text),&bytes)==COH_OK&&bytes==strlen(text));
 CHECK(strstr(text,"\"real_account_login_verified\":false")&&strstr(text,"\"native_live_world\":false"));
 CHECK(strstr(text,"\"cleanup_complete\":true")&&!strstr(text,"account_name")&&!strstr(text,"password")&&!strstr(text,"cookie"));
 CHECK(!strstr(text,"127.0.0.1")&&!strstr(text,"authorized-fixture-version"));
 d.closed_sockets=2;CHECK(coh_auth_interop_report(&d,42,1,text,sizeof(text),&bytes)==COH_OK);
 CHECK(strstr(text,"\"cleanup_complete\":false")&&strstr(text,"\"interrupted\":true"));
 printf("{\"passed\":true,\"checks\":%u,\"policy_only\":true,\"network_connections\":0,\"real_account_login_verified\":false,\"native_live_world\":false}\n",checks);
 return 0;
}
