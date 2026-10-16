#define _POSIX_C_SOURCE 200809L
#include "coh_auth_interop.h"
#include <arpa/inet.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static volatile sig_atomic_t stopped;
static void interrupted(int sig){(void)sig;stopped=1;}
static uint64_t milliseconds(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
static int number(const char *s,uint32_t maximum,uint32_t *out){
 if(!s||!*s)return 0;
 uint64_t n=0;for(size_t i=0;s[i];i++){if(s[i]<'0'||s[i]>'9')return 0;n=n*10+(unsigned)(s[i]-'0');if(n>maximum)return 0;}
 *out=(uint32_t)n;return 1;
}
static int endpoint(const char *ip,const char *port,CohNetEndpoint *out){
 uint32_t p;struct in_addr a;if(inet_pton(AF_INET,ip,&a)!=1||!number(port,65535,&p)||!p)return 0;
 memcpy(out->address,&a.s_addr,4);out->port=(uint16_t)p;return 1;
}
static int hex(char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1;}
static int secret_line(char *out,size_t capacity){
 if(!fgets(out,(int)capacity,stdin))return 0;
 size_t n=strlen(out);if(!n||out[n-1]!='\n')return 0;
 out[n-1]=0;return 1;
}
int main(int argc,char **argv){
 /* All argv values describe public deployment policy; no credentials allowed. */
 CohAuthInteropProfile p;memset(&p,0,sizeof(p));uint32_t shard,slot,timeout,id;
 if(argc!=13||!endpoint(argv[1],argv[2],&p.auth)||!endpoint(argv[3],argv[4],&p.db)||
    !endpoint(argv[5],argv[6],&p.maps[0])||!number(argv[7],255,&shard)||!number(argv[8],COH_DB_SLOTS_MAX-1,&slot)||
    strlen(argv[9])>=sizeof(p.db_policy.patch_version)||strlen(argv[10])!=32||!number(argv[11],300000,&timeout)||
    !number(argv[12],UINT32_MAX-1,&id)||!id){fputs("Invalid public deployment policy\n",stderr);return 2;}
 p.map_count=1;p.shard_id=(uint8_t)shard;p.character_slot=slot;p.timeout_ms=timeout;
 p.db_policy.protocol_version=COH_DB_PROTOCOL_VERSION;strcpy(p.db_policy.patch_version,argv[9]);strcpy(p.db_policy.system_spec,"Disabled");
 for(unsigned i=0;i<16;i++){int a=hex(argv[10][2*i]),b=hex(argv[10][2*i+1]);if(a<0||b<0)return 2;p.db_policy.executable_checksum[i]=(uint8_t)((a<<4)|b);}
 CohAuthInteropPolicyFailure failure;CohLiveConfig config;
 if(coh_auth_interop_validate(&p,&failure)!=COH_OK){fprintf(stderr,"Deployment policy rejected: %u\n",(unsigned)failure);return 2;}
 if(coh_auth_interop_config(&p,coh_auth_openssl_provider(),&config)!=COH_OK)return 2;
 if(isatty(STDIN_FILENO)){fputs("Private credential pipe required\n",stderr);return 2;}
 char account[16]={0},password[18]={0};
 /* Anonymous pipe/private stdin, never argv/env/files; exactly bounded lines. */
 if(!secret_line(account,sizeof(account))||!secret_line(password,sizeof(password))){
  coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));fputs("Invalid private credential input\n",stderr);return 2;
 }
 signal(SIGINT,interrupted);signal(SIGTERM,interrupted);
 CohLive *owner=coh_live_create(&config);
 if(!owner){coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));return 2;}
 uint64_t start=milliseconds();CohStatus status=coh_live_begin(owner,&p.db_policy,account,password,0,0,id,id+1,start);
 coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));
 CohLiveDiagnostics d={0};int boundary=0;
 for(;;){
  coh_live_diagnostics(owner,&d);
  if(status!=COH_OK||stopped||milliseconds()-start>=p.timeout_ms)break;
  status=coh_live_service(owner,milliseconds(),(CohCancel){0});coh_live_diagnostics(owner,&d);
  if(d.phase==COH_LIVE_SCENE_INCOMPLETE&&status==COH_UNSUPPORTED){boundary=1;break;}
  if(status!=COH_OK)break;
  if(d.phase==COH_LIVE_SHARDS_READY)status=coh_live_choose_shard(owner,p.shard_id,milliseconds());
  else if(d.phase==COH_LIVE_CHARACTERS_READY)status=coh_live_choose_character(owner,p.character_slot,0,0,milliseconds());
  else if(d.phase==COH_LIVE_MAP_APPROVAL){
   CohNetEndpoint candidates[2];status=coh_live_map_candidates(owner,candidates);
   if(status==COH_OK){
    status=COH_INVALID;
    for(unsigned i=0;i<2;i++)if(coh_auth_interop_approve_map(&p,candidates[i],d.authentication_generation)==COH_OK){status=coh_live_choose_map(owner,i,milliseconds());break;}
   }
  }
  if(status!=COH_OK)break;
  struct timespec pause={0,1000000};while(nanosleep(&pause,&pause)&&errno==EINTR&&!stopped){}
 }
 coh_live_diagnostics(owner,&d);uint64_t elapsed=milliseconds()-start;
 if(stopped){d.phase=COH_LIVE_CANCELLED;d.last_status=COH_CANCELLED;}
 else if(!boundary&&elapsed>=p.timeout_ms){d.phase=COH_LIVE_TIMED_OUT;d.last_status=COH_STATE;}
 else if(status!=COH_OK)d.last_status=status;
 /* Keep failure/boundary phase and status before cleanup changes the owner. */
 coh_live_close(owner);CohLiveDiagnostics closed={0};coh_live_diagnostics(owner,&closed);
 d.closed_sockets=closed.closed_sockets;d.opened_sockets=closed.opened_sockets;
 char report[2048];size_t bytes=0;
 int result=coh_auth_interop_report(&d,elapsed,stopped,report,sizeof(report),&bytes)==COH_OK&&fwrite(report,1,bytes,stdout)==bytes;
 coh_live_destroy(owner);coh_auth_wipe(&p,sizeof(p));
 return result&&boundary&&d.opened_sockets==d.closed_sockets?0:1;
}
