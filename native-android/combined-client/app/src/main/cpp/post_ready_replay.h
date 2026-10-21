#ifndef COH_POST_READY_REPLAY_H
#define COH_POST_READY_REPLAY_H
/* Diagnostic-only logical message archive. Bytes are exactly the decoded
 * application payload loan, as in INITIAL replay, not UDP/encrypted wire data.
 * Stream to one regular private FD; never retain another packet or decode body.
 * File:64B header, repeated112B header+payload,96B terminal summary. All integers
 * LE. SHA256 covers each payload and all bytes preceding the terminal summary.
 * The disk cap includes every header/trailer; RAM is only this fixed state and
 * charged4096B stack reserve. Kernel/file-cache memory is not process payload. */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#ifndef OPENSSL_SUPPRESS_DEPRECATED
#define OPENSSL_SUPPRESS_DEPRECATED
#endif
#include <openssl/sha.h>
#define COH_POST_REPLAY_FILE_BYTES (8u*1024u*1024u)
#define COH_POST_REPLAY_MESSAGE_BYTES (4u*1024u*1024u)
#define COH_POST_REPLAY_RECORDS 128u
#define COH_POST_REPLAY_HEADER 64u
#define COH_POST_REPLAY_RECORD_HEADER 112u
#define COH_POST_REPLAY_TRAILER 96u
#define COH_POST_REPLAY_STACK_RESERVE 4096u
enum {COH_POST_REPLAY_IO=1u,COH_POST_REPLAY_DISK_LIMIT=2u,
 COH_POST_REPLAY_MEMORY=4u,COH_POST_REPLAY_INVALID=8u,
 COH_POST_REPLAY_RECORD_LIMIT=16u,COH_POST_REPLAY_WINDOW_INCOMPLETE=32u,
 COH_POST_REPLAY_UNOBSERVED_MESSAGE=64u};
typedef struct {
 int fd;uint32_t configured,finalized,records,seen,omitted,reasons;
 uint64_t bytes,payload_bytes,bits,first_ms,last_ms;
 SHA256_CTX prefix;
}CohPostReplay;
#ifndef COH_POST_REPLAY_WRITE
#define COH_POST_REPLAY_WRITE write
#endif
static void post_replay_u32(uint8_t*p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static void post_replay_u64(uint8_t*p,uint64_t v){for(unsigned i=0;i<8;i++)p[i]=(uint8_t)(v>>(8*i));}
static int post_replay_write(int fd,const uint8_t*p,size_t n){
 while(n){ssize_t k=COH_POST_REPLAY_WRITE(fd,p,n);if(k<0&&errno==EINTR)continue;if(k<=0||(size_t)k>n)return 0;p+=(size_t)k;n-=(size_t)k;}return 1;
}
static void post_replay_init(CohPostReplay*s){memset(s,0,sizeof(*s));s->fd=-1;}
static int post_replay_start(CohPostReplay*s,int source_fd){
 struct stat st;uint8_t header[COH_POST_REPLAY_HEADER]={0};
 if(!s||s->configured||source_fd<0||fstat(source_fd,&st)||!S_ISREG(st.st_mode)||st.st_size||st.st_nlink!=1||lseek(source_fd,0,SEEK_CUR)!=0)return 0;
 int fd=dup(source_fd);if(fd<0)return 0;
 if(fcntl(fd,F_SETFD,FD_CLOEXEC)<0){close(fd);return 0;}
 memcpy(header,"COHPRP01",8);post_replay_u32(header+8,COH_POST_REPLAY_HEADER);post_replay_u32(header+12,COH_POST_REPLAY_RECORD_HEADER);
 post_replay_u32(header+16,COH_POST_REPLAY_TRAILER);post_replay_u32(header+20,COH_POST_REPLAY_RECORDS);post_replay_u64(header+24,COH_POST_REPLAY_FILE_BYTES);
 post_replay_u64(header+32,30000);post_replay_u32(header+40,COH_POST_REPLAY_MESSAGE_BYTES);post_replay_u32(header+44,COH_POST_REPLAY_STACK_RESERVE);
 if(!SHA256_Init(&s->prefix)||!post_replay_write(fd,header,sizeof(header))||!SHA256_Update(&s->prefix,header,sizeof(header))){close(fd);memset(&s->prefix,0,sizeof(s->prefix));return 0;}
 s->fd=fd;s->configured=1;s->bytes=sizeof(header);return 1;
}
/* Caller proves READY was accepted before this callback. The existing concrete
 * receiver charge plus borrowed source plus this stack must fit8MiB BEFORE IO.
 * On an optional artifact failure the transport/ACK observer still proceeds. */
static void post_replay_record(CohPostReplay*s,const uint8_t*data,size_t n,
 uint64_t bits,uint64_t cursor,uint64_t now,uint64_t generation,uint64_t id,
 uint32_t command,uint32_t aligned,uint32_t ordered,uint32_t ordered_id,size_t retained){
 if(!s||!s->configured||s->finalized)return;
 if(s->seen==UINT32_MAX){s->reasons|=COH_POST_REPLAY_INVALID;return;}s->seen++;
 uint32_t reason=0;uintptr_t p=(uintptr_t)data,a=(uintptr_t)s;
 if(!data||!n||n>COH_POST_REPLAY_MESSAGE_BYTES||p>UINTPTR_MAX-n||a>UINTPTR_MAX-sizeof(*s)||
  !(p+n<=a||a+sizeof(*s)<=p)||!bits||bits>(uint64_t)n*8||cursor>bits||!generation||
  aligned>1||ordered>1||(s->records&&now<s->last_ms))reason|=COH_POST_REPLAY_INVALID;
 if(s->records>=COH_POST_REPLAY_RECORDS)reason|=COH_POST_REPLAY_RECORD_LIMIT;
 if(retained>8u*1024u*1024u||COH_POST_REPLAY_STACK_RESERVE>8u*1024u*1024u-retained||
  n>8u*1024u*1024u-retained-COH_POST_REPLAY_STACK_RESERVE)reason|=COH_POST_REPLAY_MEMORY;
 if(s->bytes>COH_POST_REPLAY_FILE_BYTES-COH_POST_REPLAY_TRAILER-COH_POST_REPLAY_RECORD_HEADER||
  n>COH_POST_REPLAY_FILE_BYTES-s->bytes-COH_POST_REPLAY_TRAILER-COH_POST_REPLAY_RECORD_HEADER)reason|=COH_POST_REPLAY_DISK_LIMIT;
 if(reason||s->reasons){s->reasons|=reason;s->omitted++;return;}
 uint8_t header[COH_POST_REPLAY_RECORD_HEADER]={0};SHA256_CTX digest;
 memcpy(header,"COHMSG01",8);post_replay_u32(header+8,sizeof(header));post_replay_u32(header+12,(uint32_t)n);
 post_replay_u64(header+16,bits);post_replay_u64(header+24,cursor);post_replay_u64(header+32,now);post_replay_u64(header+40,generation);post_replay_u64(header+48,id);
 post_replay_u32(header+56,command);post_replay_u32(header+60,aligned);post_replay_u32(header+64,ordered);post_replay_u32(header+68,ordered_id);
 post_replay_u32(header+104,command==UINT32_MAX?1u:0u); /* unavailable command header */
 int ok=SHA256_Init(&digest)&&SHA256_Update(&digest,data,n)&&SHA256_Final(header+72,&digest);
 memset(&digest,0,sizeof(digest));
 if(!ok||!post_replay_write(s->fd,header,sizeof(header))||!post_replay_write(s->fd,data,n)||
  !SHA256_Update(&s->prefix,header,sizeof(header))||!SHA256_Update(&s->prefix,data,n)){
  s->reasons|=COH_POST_REPLAY_IO;s->omitted++;return;
 }
 s->records++;s->bytes+=sizeof(header)+n;s->payload_bytes+=n;s->bits+=bits;if(s->records==1)s->first_ms=now;s->last_ms=now;
}
/* Compare with the current Map count AFTER service returns. A source loan that
 * could not be observed must make the artifact partial, never an empty success. */
static inline void post_replay_reconcile(CohPostReplay*s,uint32_t expected){
 if(!s||!s->configured||s->finalized)return;
 if(expected<s->seen){s->reasons|=COH_POST_REPLAY_INVALID;return;}
 if(expected>s->seen){s->omitted+=expected-s->seen;s->seen=expected;s->reasons|=COH_POST_REPLAY_UNOBSERVED_MESSAGE;}
}
static void post_replay_finish(CohPostReplay*s,unsigned window_complete){
 if(!s||!s->configured||s->finalized)return;
 if(!window_complete)s->reasons|=COH_POST_REPLAY_WINDOW_INCOMPLETE;
 uint8_t trailer[COH_POST_REPLAY_TRAILER]={0};memcpy(trailer,"COHPEND1",8);post_replay_u32(trailer+8,sizeof(trailer));
 post_replay_u32(trailer+12,s->records);post_replay_u32(trailer+16,s->seen);post_replay_u32(trailer+20,s->omitted);post_replay_u32(trailer+24,s->reasons);post_replay_u32(trailer+28,window_complete?1:0);
 post_replay_u64(trailer+32,s->payload_bytes);post_replay_u64(trailer+40,s->bits);post_replay_u64(trailer+48,s->first_ms);post_replay_u64(trailer+56,s->last_ms);
 if(!SHA256_Final(trailer+64,&s->prefix)||!post_replay_write(s->fd,trailer,sizeof(trailer))||fsync(s->fd))s->reasons|=COH_POST_REPLAY_IO;
 else s->bytes+=sizeof(trailer);
 memset(&s->prefix,0,sizeof(s->prefix));close(s->fd);s->fd=-1;s->finalized=1;
}
#endif
