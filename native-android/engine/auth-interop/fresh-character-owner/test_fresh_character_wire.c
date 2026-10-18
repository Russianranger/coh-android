/* NEW controlled peer composition only. No old test entrypoint or real server. */
#define _POSIX_C_SOURCE 200809L
#include "fresh_character_owner.h"
#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <openssl/bn.h>
#include <openssl/core_names.h>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/tcp.h>
#include <unistd.h>
static unsigned checks,auth_frames,db_frames,db_encrypted_frames;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"fresh wire line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t bits;}Wire;
#include "fresh-character-wire-fixtures.h"
static uint64_t now_ms=100;
static CohFreshCharacterOwner*owner;
static const CohAuthCrypto*provider;
static unsigned descriptors(void){DIR*d=opendir("/proc/self/fd");CHECK(d);unsigned n=0;while(readdir(d))++n;CHECK(!closedir(d));return n;}
static void nonblocking(int fd){CHECK(fcntl(fd,F_SETFL,O_NONBLOCK)==0);}
static struct sockaddr_in address(CohNetEndpoint e){struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons(e.port);memcpy(&a.sin_addr.s_addr,e.address,4);return a;}
static void put32(uint8_t*p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static uint32_t get32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static CohFreshCharacterDiagnostics observation(void){CohFreshCharacterDiagnostics d;memset(&d,0,sizeof(d));CHECK(coh_fresh_character_diagnostics(owner,&d)==COH_OK);return d;}
static void pump(void){CHECK(coh_fresh_character_service(owner,++now_ms,(CohCancel){0})==COH_OK);}
static int readable(int fd){struct pollfd p={fd,POLLIN,0};int r=poll(&p,1,500);CHECK(r==1&&(p.revents&POLLIN));return r;}
static int auth_listener(CohNetEndpoint*out){
    for(unsigned attempt=0;attempt<64;attempt++){
        int fd=socket(AF_INET,SOCK_STREAM,0);CHECK(fd>=0);
        CohNetEndpoint e={{127,0,0,1},0};struct sockaddr_in a=address(e);
        CHECK(!bind(fd,(struct sockaddr*)&a,sizeof(a)));socklen_t n=sizeof(a);
        CHECK(!getsockname(fd,(struct sockaddr*)&a,&n));e.port=ntohs(a.sin_port);
        if(e.port>=20000&&e.port<=59999){CHECK(!listen(fd,1));nonblocking(fd);*out=e;return fd;}
        CHECK(!close(fd));
    }
    CHECK(0);return -1;
}
static int database_peer(void){int fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(fd>=0);struct sockaddr_in a=address((CohNetEndpoint){{127,0,0,1},7000});CHECK(!bind(fd,(struct sockaddr*)&a,sizeof(a)));nonblocking(fd);return fd;}
static void auth_send(int fd,const uint8_t*body,size_t bytes){uint8_t frame[1002];size_t n=0;CHECK(coh_auth_global_encode((CohBytes){body,bytes},frame,sizeof(frame),&n)==COH_OK);CHECK(send(fd,frame,n,MSG_NOSIGNAL)==(ssize_t)n);++auth_frames;coh_auth_wipe(frame,sizeof(frame));}
static size_t auth_read(int fd,uint8_t body[1000]){
    uint8_t frame[1002];size_t have=0,need=2;
    while(have<need){readable(fd);ssize_t n=recv(fd,frame+have,need-have,0);CHECK(n>0);have+=(size_t)n;if(have==2){need=(size_t)frame[0]|(size_t)frame[1]<<8;CHECK(need>=18&&need<=sizeof(frame));}}
    size_t bytes=0;CHECK(coh_auth_global_decode((CohBytes){frame,have},body,1000,&bytes)==COH_OK);coh_auth_wipe(frame,sizeof(frame));return bytes;
}
static EVP_PKEY*auth_hello(int fd){
    EVP_PKEY*key=EVP_PKEY_Q_keygen(NULL,NULL,"RSA",2048);BIGNUM*n=NULL,*e=NULL;CHECK(key);
    CHECK(EVP_PKEY_get_bn_param(key,OSSL_PKEY_PARAM_RSA_N,&n)>0&&EVP_PKEY_get_bn_param(key,OSSL_PKEY_PARAM_RSA_E,&e)>0);
    uint8_t body[1000]={0};body[0]=0;put32(body+1,0x87654321);put32(body+5,COH_AUTH_OUROBOROS2);size_t at=9;
    unsigned size=(unsigned)BN_num_bytes(e);put32(body+at,size);at+=4;CHECK(BN_bn2bin(e,body+at)==(int)size);at+=size;
    size=(unsigned)BN_num_bytes(n);put32(body+at,size);at+=4;CHECK(BN_bn2bin(n,body+at)==(int)size);at+=size;
    auth_send(fd,body,at);coh_auth_wipe(body,sizeof(body));BN_free(n);BN_free(e);return key;
}
static void check_login_request(int fd,EVP_PKEY*key){
    uint8_t body[1000],plain[512];size_t n=auth_read(fd,body);CHECK(n>=267&&body[0]==4&&get32(body+1)==256);
    CHECK(get32(body+261)==0&&body[265]==0&&body[266]==0);
    EVP_PKEY_CTX*c=EVP_PKEY_CTX_new(key,NULL);CHECK(c&&EVP_PKEY_decrypt_init(c)>0&&EVP_PKEY_CTX_set_rsa_padding(c,RSA_PKCS1_OAEP_PADDING)>0&&EVP_PKEY_CTX_set_rsa_oaep_md(c,EVP_sha1())>0&&EVP_PKEY_CTX_set_rsa_mgf1_md(c,EVP_sha1())>0);
    size_t bytes=sizeof(plain);CHECK(EVP_PKEY_decrypt(c,plain,&bytes,body+5,256)>0&&bytes==94&&!memcmp(plain,"fixture",7));
    for(unsigned i=7;i<14;i++)CHECK(!plain[i]);
    EVP_PKEY_CTX_free(c);EVP_PKEY_free(key);coh_auth_wipe(body,sizeof(body));coh_auth_wipe(plain,sizeof(plain));
}
typedef struct{int fd;struct sockaddr_in target;int target_bound;uint32_t id;CohBlowfish key;}Database;
static CohNetPacket db_read(Database*d,int encrypted,int connecting){
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];struct sockaddr_in from;socklen_t n=sizeof(from);readable(d->fd);
    ssize_t bytes=recvfrom(d->fd,frame,sizeof(frame),0,(struct sockaddr*)&from,&n);CHECK(bytes>0&&n==sizeof(from)&&from.sin_family==AF_INET&&from.sin_addr.s_addr==htonl(INADDR_LOOPBACK)&&from.sin_port);
    if(d->target_bound)CHECK(from.sin_port==d->target.sin_port&&from.sin_addr.s_addr==d->target.sin_addr.s_addr);else{d->target=from;d->target_bound=1;}
    CohNetPacket packet;CHECK(coh_net_frame_decode(5,encrypted?&d->key:NULL,encrypted,connecting,(CohBytes){frame,(size_t)bytes},&packet)==COH_OK);++db_frames;db_encrypted_frames+=(unsigned)encrypted;return packet;
}
static CohNetPacket db_control(uint32_t id,uint32_t command,int encrypt,const uint8_t*public_key){
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1));CHECK(!coh_protocol_write_pack(&b,1,0));CHECK(!coh_protocol_write_pack(&b,1,command));
    if(command==2)CHECK(!coh_protocol_write_pack(&b,1,(uint32_t)encrypt));
    p.payload_bits=(uint32_t)b.bit_length;
    if(public_key){size_t at=(b.cursor+7)&~(size_t)7;CHECK(at+512<=sizeof(p.payload)*8);memcpy(p.payload+at/8,public_key,64);p.payload_bits=(uint32_t)(at+512);}return p;
}
static uint32_t db_command(const CohNetPacket*p,int control){CohProtocolBits b;uint32_t command;CHECK(!p->compressed);CHECK(!coh_protocol_bits_init(&b,(uint8_t*)(uintptr_t)p->payload,sizeof(p->payload),p->payload_bits,0));CHECK(!coh_protocol_read_pack(&b,1,&command));if(control&&!command&&b.cursor<b.bit_length)CHECK(!coh_protocol_read_pack(&b,1,&command));return command;}
static void db_send(Database*d,CohNetPacket p,int encrypted){uint8_t frame[COH_PROTOCOL_FRAME_MAX];size_t bytes=0;CHECK(coh_net_frame_encode(5,encrypted?&d->key:NULL,encrypted,&p,frame,sizeof(frame),&bytes)==COH_OK);CHECK(sendto(d->fd,frame,bytes,0,(struct sockaddr*)&d->target,sizeof(d->target))==(ssize_t)bytes);coh_auth_wipe(frame,sizeof(frame));}
static void db_wire(Database*d,Wire wire,uint32_t ack){CohNetPacket p;memset(&p,0,sizeof(p));CHECK(wire.bits>0&&wire.bits<=sizeof(p.payload)*8);p.id=++d->id;p.payload_bits=(uint32_t)wire.bits;memcpy(p.payload,wire.data,(wire.bits+7)/8);p.ack_count=1;p.acks[0]=ack;db_send(d,p,1);}
static void db_handshake(Database*d){
    pump();CohNetPacket first=db_read(d,0,1);CHECK(db_command(&first,0)==1);
    uint8_t secret[64],public_key[64];CHECK(coh_auth_dh_keypair(provider,secret,public_key)==COH_OK);
    CohNetPacket reply=db_control(100,2,1,public_key);reply.ack_count=1;reply.acks[0]=first.id;db_send(d,reply,0);pump();
    CohNetPacket acknowledgment=db_read(d,0,0);CHECK(db_command(&acknowledgment,1)==3);
    CohProtocolBits b;uint32_t c;CHECK(!coh_protocol_bits_init(&b,acknowledgment.payload,sizeof(acknowledgment.payload),acknowledgment.payload_bits,0));
    CHECK(!coh_protocol_read_pack(&b,1,&c)&&c==0);CHECK(!coh_protocol_read_pack(&b,1,&c)&&c==3);CHECK(!coh_protocol_read_pack(&b,1,&c)&&c==1);
    size_t at=(b.cursor+7)&~(size_t)7;CHECK(at+512==b.bit_length);CHECK(coh_auth_dh_blowfish(provider,secret,acknowledgment.payload+at/8,&d->key)==COH_OK);coh_auth_wipe(secret,sizeof(secret));coh_auth_wipe(public_key,sizeof(public_key));
    reply=db_control(101,4,0,NULL);reply.ack_count=1;reply.acks[0]=acknowledgment.id;db_send(d,reply,1);pump();CohNetPacket ack=db_read(d,1,0);CHECK(db_command(&ack,1)==0);d->id=101;
}
static uint32_t db_login_request(Database*d){
    pump();CohNetPacket request=db_read(d,1,0);CHECK(!request.sibling_count&&!request.compressed&&db_command(&request,0)==COH_DB_LOGIN);
    CohDbLogin expected;memset(&expected,0,sizeof(expected));strcpy(expected.account,"fixture");strcpy(expected.patch_version,"dev:owned-fresh-character");expected.user_id=900001;expected.cookie=0x12345678;expected.protocol_version=COH_DB_PROTOCOL_VERSION;expected.no_version_check=1;expected.executable_checksum[0]=7;
    uint8_t body[COH_DB_LOGIN_MAX];size_t bits=0;CHECK(coh_db_login_encode(&expected,0,0,body,sizeof(body),&bits)==COH_OK);CHECK(bits==request.payload_bits&&!memcmp(body,request.payload,(bits+7)/8));coh_db_wipe(&expected,sizeof(expected));coh_db_wipe(body,sizeof(body));return request.id;
}
int main(void){
    unsigned before=descriptors();provider=coh_auth_openssl_provider();CHECK(provider);
    CohNetEndpoint auth;int listener=auth_listener(&auth);Database db;memset(&db,0,sizeof(db));db.fd=database_peer();
    CohFreshCharacterConfig config;memset(&config,0,sizeof(config));config.auth_endpoint=auth;config.crypto=provider;config.connect_id=1001;config.executable_checksum[0]=7;config.owned_map_id=1;config.owned_map_endpoint=(CohNetEndpoint){{127,0,0,1},7001};
    owner=coh_fresh_character_create(&config);CHECK(owner);CHECK(coh_fresh_character_begin(owner,"fixture","sample",(CohBytes){(const uint8_t*)"New Fixture",11},now_ms)==COH_OK);
    int peer=-1;for(unsigned i=0;i<20&&peer<0;i++){pump();peer=accept(listener,NULL,NULL);if(peer<0)CHECK(errno==EAGAIN||errno==EWOULDBLOCK);}CHECK(peer>=0);nonblocking(peer);int one=1;CHECK(!setsockopt(peer,IPPROTO_TCP,TCP_NODELAY,&one,sizeof(one)));pump();CHECK(observation().observed_auth_phase==COH_LOGIN_WAIT_HELLO);
    EVP_PKEY*key=auth_hello(peer);pump();check_login_request(peer,key);
    auth_send(peer,fresh_auth_login_ok,sizeof(fresh_auth_login_ok));pump();uint8_t body[1000];CHECK(auth_read(peer,body)>=11&&body[0]==5&&body[9]==1&&body[10]==0);coh_auth_wipe(body,sizeof(body));
    auth_send(peer,fresh_auth_shards,sizeof(fresh_auth_shards));pump();pump();CHECK(auth_read(peer,body)>=10&&body[0]==2&&body[9]==1);coh_auth_wipe(body,sizeof(body));
    auth_send(peer,fresh_auth_play_ok,sizeof(fresh_auth_play_ok));pump();CohFreshCharacterDiagnostics d=observation();CHECK(d.phase==COH_FRESH_CHARACTER_WAIT_LIST&&d.actual_grant_verified&&d.observed_auth_phase==COH_LOGIN_AUTHORIZED&&d.session_generation==1&&d.receipt_generation==1);
    db_handshake(&db);uint32_t login_id=db_login_request(&db);db_wire(&db,fresh_players,login_id);pump();CohNetPacket ack=db_read(&db,1,0);CHECK(db_command(&ack,1)==0);d=observation();CHECK(d.phase==COH_FRESH_CHARACTER_WAIT_OFFER&&d.matching_empty_list_verified&&d.creation_request_queued&&d.creation_attempted&&d.selection_generation==1&&d.persistent_allocation_possible&&d.private_name_wiped);
    pump();CohNetPacket choose=db_read(&db,1,0);CHECK(!choose.sibling_count&&!choose.compressed&&choose.payload_bits==fresh_choose.bits&&!memcmp(choose.payload,fresh_choose.data,(fresh_choose.bits+7)/8));
    db_wire(&db,fresh_map,choose.id);pump();ack=db_read(&db,1,0);CHECK(db_command(&ack,1)==0);d=observation();
    CHECK(d.phase==COH_FRESH_CHARACTER_COMPLETE&&d.failure==COH_FRESH_CHARACTER_FAILURE_NONE&&d.status==COH_OK&&d.allocated_offer_observed&&d.private_offer_retired&&d.container_uninitialized&&d.persistent_allocation_possible&&d.retirement_attempted&&d.controllers_destroyed&&d.bridge_temporaries_wiped&&d.private_name_wiped&&d.cleanup_cancel_close_used);
    CHECK(d.observed_db_phase==COH_DB_HANDOFF_READY&&d.final_db_phase==COH_DB_CANCELLED&&d.final_auth_phase==COH_LOGIN_CLOSED&&d.begin_attempted==1&&d.shard_attempted==1&&d.bridge_attempted==1&&d.creation_attempted==1);
    CHECK(!d.actual_server_development_skip_observed&&!d.normal_version_admitted&&!d.checksum_reference_admitted&&!d.initialized_character&&!d.persistent_rollback_claimed&&!d.map_socket_opened&&!d.map_character_body_sent&&!d.sends_ready&&!d.sends_received_character&&!d.sends_full_update_ack&&!d.current_world_verified&&!d.actor_publication&&!d.world_authority);
    CHECK(auth_frames==4&&db_frames==7&&db_encrypted_frames==5);
    CHECK(coh_fresh_character_service(owner,++now_ms,(CohCancel){0})==COH_STATE&&coh_fresh_character_cancel(owner)==COH_STATE&&coh_fresh_character_timeout(owner)==COH_STATE);CHECK(coh_fresh_character_close(owner)==COH_OK&&observation().phase==COH_FRESH_CHARACTER_COMPLETE);CHECK(coh_fresh_character_begin(owner,"fixture","sample",(CohBytes){(const uint8_t*)"New Fixture",11},now_ms)==COH_STATE);CHECK(coh_fresh_character_destroy(&owner)==COH_OK&&!owner);
    coh_auth_wipe(&db.key,sizeof(db.key));CHECK(!close(db.fd)&&!close(peer)&&!close(listener));CHECK(descriptors()==before);
    printf("{\"passed\":true,\"checks\":%u,\"transactions\":1,\"real_public_Login_DBSession_owner\":true,\"actual_OS_TCP_UDP\":true,\"OpenSSL_RSA_DH_and_Blowfish\":true,\"auth_reply_frames\":%u,\"DB_frames_observed\":%u,\"encrypted_DB_frames_observed\":%u,\"source_choose_wire_compared\":true,\"parsed_offer_retired\":true,\"descriptors_balanced\":true,\"synthetic_peers_only\":true,\"actual_server_or_SQL\":false,\"persistent_rollback_claimed\":false,\"Map_socket_or_character_ACK\":false,\"world_authority\":false}\n",checks,auth_frames,db_frames,db_encrypted_frames);return 0;
}
