#define _POSIX_C_SOURCE 200809L
#include "coh_login.h"
#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <openssl/evp.h>
#include <openssl/bn.h>
#include <openssl/core_names.h>
#include <poll.h>
#include <netinet/tcp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
static unsigned checks,scenarios;static uint64_t clock_ms=100;
static int client_fd=-1,limited_sends,send_blocked,short_writes;
int __real_connect(int,const struct sockaddr *,socklen_t);
ssize_t __real_send(int,const void *,size_t,int);
int __wrap_connect(int fd,const struct sockaddr *a,socklen_t n){client_fd=fd;return __real_connect(fd,a,n);}
ssize_t __wrap_send(int fd,const void *data,size_t n,int flags){
    if(fd==client_fd&&limited_sends){
        if(!send_blocked){send_blocked=1;errno=EAGAIN;return -1;}
        if(n>3){n=3;short_writes++;}
    }
    return __real_send(fd,data,n,flags);
}
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"login test line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {int listener,peer;CohNetEndpoint endpoint;} Peer;
static unsigned descriptors(void){DIR *d=opendir("/proc/self/fd");CHECK(d);unsigned n=0;while(readdir(d))n++;closedir(d);return n;}
static Peer peer_open(void){
    Peer p={-1,-1,{{127,0,0,1},0}};p.listener=socket(AF_INET,SOCK_STREAM,0);CHECK(p.listener>=0);
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    CHECK(bind(p.listener,(struct sockaddr *)&a,sizeof(a))==0);CHECK(listen(p.listener,1)==0);
    socklen_t n=sizeof(a);CHECK(getsockname(p.listener,(struct sockaddr *)&a,&n)==0);p.endpoint.port=ntohs(a.sin_port);
    CHECK(fcntl(p.listener,F_SETFL,O_NONBLOCK)==0);return p;
}
static void peer_close(Peer p){if(p.peer>=0)CHECK(close(p.peer)==0);CHECK(close(p.listener)==0);}
static CohLoginDiagnostics diagnostics(CohLogin *s){CohLoginDiagnostics d;memset(&d,0,sizeof(d));coh_login_diagnostics(s,&d);return d;}
static void pump(CohLogin *s){CHECK(coh_login_service(s,++clock_ms,(CohCancel){0})==COH_OK);}
static void drain(CohLogin *s){for(unsigned i=0;i<1000&&diagnostics(s).pending_send_bytes;i++)pump(s);CHECK(!diagnostics(s).pending_send_bytes);}
static CohLogin *begin(Peer *p,const char *password){
    CohLoginConfig c=coh_login_default_config(coh_auth_openssl_provider());CohLogin *s=coh_login_create(&c);CHECK(s);
    CHECK(coh_login_begin(s,p->endpoint," THOR ",password,0,0,clock_ms)==COH_OK);
    for(unsigned i=0;i<20;i++){pump(s);p->peer=accept(p->listener,NULL,NULL);if(p->peer>=0)break;CHECK(errno==EAGAIN||errno==EWOULDBLOCK);}
    CHECK(p->peer>=0);CHECK(fcntl(p->peer,F_SETFL,O_NONBLOCK)==0);int one=1;CHECK(setsockopt(p->peer,IPPROTO_TCP,TCP_NODELAY,&one,sizeof(one))==0);pump(s);CHECK(diagnostics(s).state==COH_LOGIN_WAIT_HELLO);return s;
}
static void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static size_t encode(const uint8_t *body,size_t n,uint8_t *frame){size_t bytes=0;CHECK(coh_auth_global_encode((CohBytes){body,n},frame,1002,&bytes)==COH_OK);return bytes;}
static void send_bytes(Peer p,const uint8_t *frame,size_t n){CHECK(send(p.peer,frame,n,MSG_NOSIGNAL)==(ssize_t)n);}
static void send_body(Peer p,const uint8_t *body,size_t n){uint8_t frame[1002];size_t bytes=encode(body,n,frame);send_bytes(p,frame,bytes);}
static size_t read_body(Peer p,uint8_t body[1000]){
    uint8_t frame[1002];size_t have=0,need=2;
    while(have<need){struct pollfd fd={p.peer,POLLIN,0};CHECK(poll(&fd,1,500)==1);ssize_t n=recv(p.peer,frame+have,need-have,0);CHECK(n>0);have+=(size_t)n;if(have==2){need=(size_t)frame[0]|(size_t)frame[1]<<8;CHECK(need>=18&&need<=sizeof(frame));}}
    size_t n=0;CHECK(coh_auth_global_decode((CohBytes){frame,have},body,1000,&n)==COH_OK);return n;
}
static size_t hello(uint8_t body[1000]){
    EVP_PKEY *key=EVP_PKEY_Q_keygen(NULL,NULL,"RSA",2048);CHECK(key);BIGNUM *n=NULL,*e=NULL;
    CHECK(EVP_PKEY_get_bn_param(key,OSSL_PKEY_PARAM_RSA_N,&n));CHECK(EVP_PKEY_get_bn_param(key,OSSL_PKEY_PARAM_RSA_E,&e));
    body[0]=0;put32(body+1,0x87654321);put32(body+5,COH_AUTH_GLOBAL);size_t at=9;
    unsigned size=(unsigned)BN_num_bytes(e);put32(body+at,size);at+=4;CHECK(BN_bn2bin(e,body+at)==(int)size);at+=size;
    size=(unsigned)BN_num_bytes(n);put32(body+at,size);at+=4;CHECK(BN_bn2bin(n,body+at)==(int)size);at+=size;
    BN_free(n);BN_free(e);EVP_PKEY_free(key);return at;
}
static void login_to_shards(CohLogin *s,Peer p,int fragmented){
    uint8_t body[1000],frame[1002];size_t size=hello(body);size_t bytes=encode(body,size,frame);
    if(fragmented){send_bytes(p,frame,1);pump(s);CHECK(diagnostics(s).buffered_receive_bytes==1);CHECK(diagnostics(s).password_retained);
        send_bytes(p,frame+1,9);pump(s);CHECK(diagnostics(s).buffered_receive_bytes==10);CHECK(diagnostics(s).state==COH_LOGIN_WAIT_HELLO);
        send_bytes(p,frame+10,bytes-10);
    }else send_bytes(p,frame,bytes);
    pump(s);CHECK(diagnostics(s).state==COH_LOGIN_WAIT_LOGIN);CHECK(!diagnostics(s).password_retained);drain(s);
    size=read_body(p,body);CHECK(size>=267&&body[0]==4);CHECK(((unsigned)body[1]|(unsigned)body[2]<<8)==256);
    memset(body,0,41);body[0]=3;for(unsigned i=0;i<8;i++){body[1+i]=(uint8_t)(i+1);body[9+i]=(uint8_t)(i+17);}send_body(p,body,41);pump(s);
    CHECK(diagnostics(s).state==COH_LOGIN_WAIT_SHARDS);drain(s);CHECK(read_body(p,body)>=10&&body[0]==5&&body[9]==1);
    memset(body,0,24);body[0]=4;body[1]=1;body[2]=1;body[3]=1;body[4]=127;body[7]=1;put32(body+8,7000);body[16]=10;body[18]=1;
    send_body(p,body,20);pump(s);CHECK(diagnostics(s).state==COH_LOGIN_SHARDS_READY);
    CohAuthShards shards;CHECK(coh_login_shards(s,&shards)==COH_OK&&shards.count==1&&shards.shards[0].port==7000);
    CHECK(coh_login_choose(s,2,clock_ms)==COH_INVALID);CHECK(diagnostics(s).state==COH_LOGIN_SHARDS_READY);
    CHECK(coh_login_choose(s,1,++clock_ms)==COH_OK);pump(s);drain(s);CHECK(read_body(p,body)>=10&&body[0]==2&&body[9]==1);
}
static void success(int ending){
    limited_sends=ending==2;send_blocked=short_writes=0;
    Peer p=peer_open();const char opaque_password[]={ (char)0xe2,(char)0x82,(char)0xac,0};
    CohLogin *s=begin(&p,ending==0?"":opaque_password);login_to_shards(s,p,ending==1);
    CohLoginAuthorization out;memset(&out,0xa5,sizeof(out));CHECK(coh_login_authorization(s,&out)==COH_STATE&&out.protocol==0xa5a5a5a5u);
    uint8_t body[10]={7},frame[1002],extra[1002];put32(body+1,0x12345678);put32(body+5,42);body[9]=1;
    size_t n=encode(body,sizeof(body),frame);
    if(ending==2){uint8_t notice[2]={8,9};size_t more=encode(notice,2,extra);memcpy(frame+n,extra,more);n+=more;}
    send_bytes(p,frame,n);if(ending==1){CHECK(shutdown(p.peer,SHUT_WR)==0);}
    pump(s);CHECK(diagnostics(s).state==COH_LOGIN_AUTHORIZED);CHECK(coh_login_authorization(s,&out)==COH_OK);
    CHECK(out.play.user_id==42&&out.play.game_key==0x12345678&&out.play.shard_id==1&&!strcmp(out.account_name,"thor"));
    if(limited_sends)CHECK(send_blocked&&short_writes>0);
    pump(s);CHECK(diagnostics(s).state==COH_LOGIN_AUTHORIZED);
    coh_auth_wipe(&out,sizeof(out));coh_login_close(s);CHECK(!diagnostics(s).password_retained&&diagnostics(s).sockets_opened==diagnostics(s).sockets_closed);
    CHECK(coh_login_authorization(s,&out)==COH_STATE);coh_login_destroy(s);peer_close(p);scenarios++;
}
static int cancel(void *unused){(void)unused;return 1;}
static void failure(unsigned kind){
    Peer p=peer_open();CohLogin *s=begin(&p,"sample");CohStatus result=COH_OK;
    if(kind==0){uint8_t b[2]={1,7};send_body(p,b,2);result=coh_login_service(s,++clock_ms,(CohCancel){0});CHECK(result==COH_IO&&diagnostics(s).remote_failure_reason==7);}
    if(kind==1){uint8_t b[2]={11,0};send_body(p,b,2);result=coh_login_service(s,++clock_ms,(CohCancel){0});CHECK(result==COH_UNSUPPORTED&&diagnostics(s).state==COH_LOGIN_UNSUPPORTED);}
    if(kind==2){uint8_t b[2]={255,255};send_bytes(p,b,2);result=coh_login_service(s,++clock_ms,(CohCancel){0});CHECK(result==COH_INVALID);}
    if(kind==3){uint8_t b=18;send_bytes(p,&b,1);pump(s);CHECK(shutdown(p.peer,SHUT_WR)==0);result=coh_login_service(s,++clock_ms,(CohCancel){0});CHECK(result==COH_IO);}
    if(kind==4){clock_ms+=20000;result=coh_login_service(s,clock_ms,(CohCancel){0});CHECK(result==COH_STATE&&diagnostics(s).state==COH_LOGIN_TIMED_OUT);}
    if(kind==5){result=coh_login_service(s,++clock_ms,(CohCancel){cancel,NULL});CHECK(result==COH_CANCELLED&&diagnostics(s).state==COH_LOGIN_CANCELLED);}
    if(kind==6){coh_login_suspend(s);CHECK(diagnostics(s).state==COH_LOGIN_SUSPENDED);}
    if(kind==7){uint8_t body[41]={3};send_body(p,body,sizeof(body));result=coh_login_service(s,++clock_ms,(CohCancel){0});CHECK(result==COH_STATE);}
    CHECK(!diagnostics(s).password_retained);CHECK(diagnostics(s).pending_send_bytes==0&&diagnostics(s).buffered_receive_bytes==0);
    CHECK(diagnostics(s).sockets_opened==diagnostics(s).sockets_closed);
    CohLoginAuthorization out;memset(&out,0xa5,sizeof(out));CHECK(coh_login_authorization(s,&out)==COH_STATE&&out.protocol==0xa5a5a5a5u);
    coh_login_destroy(s);peer_close(p);limited_sends=0;scenarios++;
}
int main(void){
    unsigned before=descriptors();CohLoginConfig c=coh_login_default_config(NULL);CHECK(!coh_login_create(&c));
    for(int i=0;i<3;i++)success(i);
    for(unsigned i=0;i<8;i++)failure(i);
    CHECK(descriptors()==before);
    printf("{\"passed\":true,\"checks\":%u,\"socket_scenarios\":%u,\"actual_os_tcp\":true,\"synthetic_authserver\":true,\"real_account_login_verified\":false,\"passwords_logged\":false,\"descriptor_cleanup\":true}\n",checks,scenarios);return 0;
}
