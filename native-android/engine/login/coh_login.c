#include "coh_login.h"
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

struct CohLogin {
    CohLoginConfig config;CohLoginDiagnostics diagnostics;int fd;
    uint64_t clock_ms, stage_ms;uint32_t subscription;uint16_t flags;
    char account[15],password[17];uint8_t chosen;
    CohAuthHello hello;CohAuthLoginOk login;CohAuthPlayOk play;CohAuthShards shards;
    CohAuthStream stream;
    uint8_t tx[COH_AUTH_BODY_MAX+2];size_t tx_size,tx_at;
};
static int endpoint_valid(CohNetEndpoint e){return e.port&&e.address[0]&&e.address[0]<224;}
static void close_fd(CohLogin *s){if(s->fd>=0){(void)close(s->fd);s->fd=-1;s->diagnostics.sockets_closed++;}}
static void wipe_session(CohLogin *s){
    coh_auth_wipe(s->account,sizeof(s->account));coh_auth_wipe(s->password,sizeof(s->password));
    coh_auth_wipe(&s->hello,sizeof(s->hello));coh_auth_wipe(&s->login,sizeof(s->login));
    coh_auth_wipe(&s->play,sizeof(s->play));coh_auth_wipe(&s->shards,sizeof(s->shards));
    coh_auth_stream_reset(&s->stream);coh_auth_wipe(s->tx,sizeof(s->tx));
    s->tx_size=s->tx_at=0;s->chosen=0;
}
static CohStatus fail(CohLogin *s,CohLoginState state,CohStatus status){
    close_fd(s);wipe_session(s);s->diagnostics.state=state;s->diagnostics.failures++;return status;
}
static CohStatus system_error(CohLogin *s){s->diagnostics.last_system_error=errno;return fail(s,COH_LOGIN_FAILED,COH_IO);}
CohLoginConfig coh_login_default_config(const CohAuthCrypto *p){CohLoginConfig c={p,10000,15000,4};return c;}
CohLogin *coh_login_create(const CohLoginConfig *c){
    if(!c||!c->crypto||!c->crypto->md5||!c->crypto->sha512||!c->crypto->rsa_oaep_sha1||
       !c->connect_timeout_ms||!c->reply_timeout_ms||!c->receive_budget||c->receive_budget>16)return NULL;
    CohLogin *s=calloc(1,sizeof(*s));if(s){s->config=*c;s->fd=-1;}return s;
}
void coh_login_destroy(CohLogin *s){if(s){close_fd(s);coh_auth_wipe(s,sizeof(*s));free(s);}}
void coh_login_close(CohLogin *s){if(s){close_fd(s);wipe_session(s);s->diagnostics.state=COH_LOGIN_CLOSED;}}
void coh_login_suspend(CohLogin *s){if(s){coh_login_close(s);s->diagnostics.state=COH_LOGIN_SUSPENDED;s->diagnostics.suspends++;}}
void coh_login_cancel(CohLogin *s){if(s){coh_login_close(s);s->diagnostics.state=COH_LOGIN_CANCELLED;s->diagnostics.cancellations++;}}
static int text_length(const char *p,size_t max,int ascii,size_t *length){
    if(!p)return 0;
    for(size_t i=0;i<=max;i++){if(!p[i]){*length=i;return 1;}if(ascii&&((unsigned char)p[i]<32||(unsigned char)p[i]>126))return 0;}return 0;
}
CohStatus coh_login_begin(CohLogin *s,CohNetEndpoint e,const char *name,const char *pass,uint32_t subscription,uint16_t flags,uint64_t now){
    size_t n,p;
    if(!s||!endpoint_valid(e)||!text_length(name,14,1,&n)||!n||!text_length(pass,16,0,&p))return COH_INVALID;
    size_t first=0;while(first<n&&name[first]==' ')first++;
    while(n>first&&name[n-1]==' ')n--;
    if(n==first)return COH_INVALID;
    CohLoginState state=s->diagnostics.state;
    if(state>=COH_LOGIN_CONNECTING&&state<=COH_LOGIN_AUTHORIZED)return COH_STATE;
    if(now<s->clock_ms)return COH_INVALID;
    close_fd(s);wipe_session(s);s->clock_ms=s->stage_ms=now;s->subscription=subscription;s->flags=flags;
    s->diagnostics.protocol=s->diagnostics.shard_count=0;s->diagnostics.last_system_error=0;
    s->diagnostics.remote_failure_command=s->diagnostics.remote_failure_reason=0;
    for(size_t i=first;i<n;i++){unsigned char c=(unsigned char)name[i];s->account[i-first]=(char)(c>='A'&&c<='Z'?c+32:c);}
    memcpy(s->password,pass,p+1);
    s->fd=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(s->fd<0)return system_error(s);s->diagnostics.sockets_opened++;
    int f=fcntl(s->fd,F_GETFL,0);if(f<0||fcntl(s->fd,F_SETFL,f|O_NONBLOCK)<0)return system_error(s);
    f=fcntl(s->fd,F_GETFD,0);if(f<0||fcntl(s->fd,F_SETFD,f|FD_CLOEXEC)<0)return system_error(s);
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons(e.port);memcpy(&a.sin_addr.s_addr,e.address,4);
    int result=connect(s->fd,(struct sockaddr *)&a,sizeof(a));
    if(result<0&&errno!=EINPROGRESS&&errno!=EINTR)return system_error(s);
    s->diagnostics.state=result==0?COH_LOGIN_WAIT_HELLO:COH_LOGIN_CONNECTING;return COH_OK;
}
static CohStatus queue_body(CohLogin *s,CohBytes body){
    if(s->tx_at!=s->tx_size)return COH_STATE;
    size_t size=0;CohStatus status=coh_auth_global_encode(body,s->tx,sizeof(s->tx),&size);
    if(status!=COH_OK)return status;
    s->tx_size=size;s->tx_at=0;return COH_OK;
}
static CohStatus dispatch(CohLogin *s,CohBytes body,uint64_t now){
    if(!body.size)return COH_INVALID;
    uint8_t command=body.data[0];CohStatus status;uint8_t request[COH_AUTH_BODY_MAX];size_t bytes=0;
    memset(request,0,sizeof(request));
    if(command==1||command==2||command==5||command==6||command==8||command==9){
        if(body.size<2)return COH_INVALID;
        s->diagnostics.remote_failure_command=command;s->diagnostics.remote_failure_reason=body.data[1];return COH_IO;
    }
    switch(command){
    case 0:
        if(s->diagnostics.state!=COH_LOGIN_WAIT_HELLO)return COH_STATE;
        status=coh_auth_parse_hello(body,&s->hello);if(status!=COH_OK)return status;
        s->diagnostics.protocol=s->hello.protocol;
        status=coh_auth_login(s->config.crypto,&s->hello,s->account,s->password,s->subscription,s->flags,request,sizeof(request),&bytes);
        coh_auth_wipe(s->password,sizeof(s->password));
        if(status==COH_OK)status=queue_body(s,(CohBytes){request,bytes});
        coh_auth_wipe(request,sizeof(request));if(status!=COH_OK)return status;
        s->diagnostics.state=COH_LOGIN_WAIT_LOGIN;s->stage_ms=now;return COH_OK;
    case 3:
        if(s->diagnostics.state!=COH_LOGIN_WAIT_LOGIN)return COH_STATE;
        status=coh_auth_parse_login_ok(body,s->hello.protocol,&s->login);if(status!=COH_OK)return status;
        status=coh_auth_server_list(s->login.session,s->hello.protocol,NULL,0,request,sizeof(request),&bytes);
        if(status==COH_OK)status=queue_body(s,(CohBytes){request,bytes});
        coh_auth_wipe(request,sizeof(request));if(status!=COH_OK)return status;
        s->diagnostics.state=COH_LOGIN_WAIT_SHARDS;s->stage_ms=now;return COH_OK;
    case 4:
        if(s->diagnostics.state!=COH_LOGIN_WAIT_SHARDS)return COH_STATE;
        status=coh_auth_parse_shards(body,s->hello.protocol,0,&s->shards);if(status!=COH_OK)return status;
        s->diagnostics.shard_count=s->shards.count;s->diagnostics.state=COH_LOGIN_SHARDS_READY;return COH_OK;
    case 7:
        if(s->diagnostics.state!=COH_LOGIN_WAIT_PLAY)return COH_STATE;
        status=coh_auth_parse_play_ok(body,&s->play);if(status!=COH_OK)return status;
        if(!s->play.game_key||!s->play.user_id||s->play.shard_id!=s->chosen)return COH_INVALID;
        s->diagnostics.state=COH_LOGIN_AUTHORIZED;return COH_OK;
    default:return COH_UNSUPPORTED;
    }
}
static CohStatus received(CohLogin *s,CohBytes bytes,uint64_t now){
    size_t at=0;
    while(at<bytes.size){
        size_t used=0;CohBytes frame;CohStatus r=coh_auth_stream_feed(&s->stream,(CohBytes){bytes.data+at,bytes.size-at},&used,&frame);
        at+=used;if(r==COH_NOT_FOUND)break;if(r!=COH_OK)return r;
        uint8_t body[COH_AUTH_BODY_MAX];size_t count=0;
        r=coh_auth_global_decode(frame,body,sizeof(body),&count);
        if(r==COH_OK)r=dispatch(s,(CohBytes){body,count},now);
        coh_auth_wipe(body,sizeof(body));coh_auth_stream_reset(&s->stream);
        if(r!=COH_OK)return r;
        s->diagnostics.received_frames++;
        if(s->diagnostics.state==COH_LOGIN_AUTHORIZED)return COH_OK;
    }
    return COH_OK;
}
static CohStatus send_pending(CohLogin *s){
    if(s->tx_at==s->tx_size)return COH_OK;
    ssize_t n=send(s->fd,s->tx+s->tx_at,s->tx_size-s->tx_at,MSG_NOSIGNAL);
    if(n<0){if(errno==EAGAIN||errno==EWOULDBLOCK||errno==EINTR)return COH_OK;return system_error(s);}
    if(!n)return COH_OK;
    coh_auth_wipe(s->tx+s->tx_at,(size_t)n);s->tx_at+=(size_t)n;s->diagnostics.sent_bytes+=(size_t)n;
    if(s->tx_at==s->tx_size)s->tx_at=s->tx_size=0;
    return COH_OK;
}
CohStatus coh_login_service(CohLogin *s,uint64_t now,CohCancel cancel){
    if(!s)return COH_INVALID;
    CohLoginState state=s->diagnostics.state;
    if(state<COH_LOGIN_CONNECTING||state>COH_LOGIN_AUTHORIZED)return state==COH_LOGIN_CANCELLED?COH_CANCELLED:COH_STATE;
    if(now<s->clock_ms)return COH_INVALID;
    s->clock_ms=now;
    if(cancel.poll&&cancel.poll(cancel.context)){coh_login_cancel(s);return COH_CANCELLED;}
    /* Match authWaitFor(AC_PLAY_OK): expose the completed receipt before any
     * later EOF/notification. Owner copies it and closes this controller; it
     * is not a persistent account-revocation monitor. */
    if(state==COH_LOGIN_AUTHORIZED)return COH_OK;
    uint64_t budget=state==COH_LOGIN_CONNECTING?s->config.connect_timeout_ms:s->config.reply_timeout_ms;
    if(state!=COH_LOGIN_SHARDS_READY&&state!=COH_LOGIN_AUTHORIZED&&now-s->stage_ms>=budget)return fail(s,COH_LOGIN_TIMED_OUT,COH_STATE);
    if(state==COH_LOGIN_CONNECTING){
        struct pollfd p={s->fd,POLLOUT,0};int n=poll(&p,1,0);
        if(n<0){if(errno==EINTR)return COH_OK;return system_error(s);}if(!n)return COH_OK;
        int error=0;socklen_t size=sizeof(error);if(getsockopt(s->fd,SOL_SOCKET,SO_ERROR,&error,&size)<0)return system_error(s);
        if(error){errno=error;return system_error(s);}s->diagnostics.state=COH_LOGIN_WAIT_HELLO;s->stage_ms=now;
    }
    CohStatus r=send_pending(s);if(r!=COH_OK)return r;
    for(unsigned i=0;i<s->config.receive_budget;i++){
        if(cancel.poll&&cancel.poll(cancel.context)){coh_login_cancel(s);return COH_CANCELLED;}
        uint8_t data[1024];ssize_t n=recv(s->fd,data,sizeof(data),MSG_DONTWAIT);
        if(n<0){if(errno==EAGAIN||errno==EWOULDBLOCK||errno==EINTR)break;return system_error(s);}
        if(!n){errno=ECONNRESET;return system_error(s);}s->diagnostics.received_bytes+=(size_t)n;
        r=received(s,(CohBytes){data,(size_t)n},now);coh_auth_wipe(data,sizeof(data));
        if(r!=COH_OK)return fail(s,r==COH_UNSUPPORTED?COH_LOGIN_UNSUPPORTED:COH_LOGIN_FAILED,r);
        r=send_pending(s);if(r!=COH_OK)return r;
        if(s->diagnostics.state==COH_LOGIN_AUTHORIZED)return COH_OK;
    }
    return COH_OK;
}
CohStatus coh_login_shards(const CohLogin *s,CohAuthShards *out){if(!s||!out)return COH_INVALID;if(s->diagnostics.state!=COH_LOGIN_SHARDS_READY)return COH_STATE;*out=s->shards;return COH_OK;}
CohStatus coh_login_choose(CohLogin *s,uint8_t id,uint64_t now){
    if(!s)return COH_INVALID;
    if(s->diagnostics.state!=COH_LOGIN_SHARDS_READY)return COH_STATE;
    if(now<s->clock_ms)return COH_INVALID;
    const CohAuthShard *chosen=NULL;for(unsigned i=0;i<s->shards.count;i++)if(s->shards.shards[i].id==id)chosen=&s->shards.shards[i];
    if(!chosen||!chosen->status||!chosen->port||!chosen->ipv4[0]||chosen->ipv4[0]>=224)return COH_INVALID;
    uint8_t body[32];size_t n=0;CohStatus r=coh_auth_about_to_play(s->login.session,id,body,sizeof(body),&n);
    if(r==COH_OK)r=queue_body(s,(CohBytes){body,n});
    coh_auth_wipe(body,sizeof(body));
    if(r==COH_OK){s->chosen=id;s->diagnostics.state=COH_LOGIN_WAIT_PLAY;s->clock_ms=s->stage_ms=now;}return r;
}
CohStatus coh_login_authorization(const CohLogin *s,CohLoginAuthorization *out){
    if(!s||!out)return COH_INVALID;
    if(s->diagnostics.state!=COH_LOGIN_AUTHORIZED)return COH_STATE;
    CohLoginAuthorization a;memset(&a,0,sizeof(a));a.protocol=s->hello.protocol;memcpy(a.account_name,s->account,sizeof(a.account_name));a.account=s->login;a.play=s->play;
    for(unsigned i=0;i<s->shards.count;i++)if(s->shards.shards[i].id==s->chosen)a.shard=s->shards.shards[i];
    *out=a;coh_auth_wipe(&a,sizeof(a));return COH_OK;
}
void coh_login_diagnostics(const CohLogin *s,CohLoginDiagnostics *out){if(s&&out){*out=s->diagnostics;out->pending_send_bytes=s->tx_size-s->tx_at;out->buffered_receive_bytes=s->stream.used;out->password_retained=s->password[0]!=0;}}
