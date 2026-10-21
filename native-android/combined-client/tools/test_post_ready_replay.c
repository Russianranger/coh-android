#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
static int write_mode,write_calls;
static ssize_t controlled_write(int fd,const void*data,size_t n){
 write_calls++;if(write_mode==1&&write_calls==1){errno=EINTR;return -1;}
 if(write_mode==2)return 0;if(write_mode==3){errno=ENOSPC;return -1;}
 if(write_mode==4&&n>3)n=3;return write(fd,data,n);
}
#define COH_POST_REPLAY_WRITE controlled_write
#include "../app/src/main/cpp/post_ready_replay.h"
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed:%d:%s\n",__LINE__,#x);abort();}}while(0)
static int tempfd(char*name){strcpy(name,"/tmp/coh-post-XXXXXX");int fd=mkstemp(name);CHECK(fd>=0);return fd;}
static uint32_t u32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void record(CohPostReplay*s,const uint8_t*p,size_t n,uint64_t t,size_t retained){post_replay_record(s,p,n,n*8,8,t,t,7,2,0,1,1,retained);}
int main(int argc,char**argv){
 char name[64];uint8_t payload[40];for(unsigned i=0;i<sizeof(payload);i++)payload[i]=(uint8_t)i;
 CohPostReplay s;post_replay_init(&s);CHECK(s.fd==-1);CHECK(!post_replay_start(&s,-1));int pipes[2];CHECK(pipe(pipes)==0);CHECK(!post_replay_start(&s,pipes[1]));close(pipes[0]);close(pipes[1]);
 int fd=tempfd(name);CHECK(post_replay_start(&s,fd));int owned=s.fd;CHECK(owned!=fd);CHECK(!post_replay_start(&s,fd));record(&s,payload,sizeof(payload),1,7000000);record(&s,payload,10,2,7000000);CHECK(s.records==2&&s.payload_bytes==50&&s.seen==2);post_replay_finish(&s,1);CHECK(s.finalized&&s.fd==-1&&s.reasons==0);CHECK(fcntl(owned,F_GETFD)<0&&errno==EBADF);post_replay_finish(&s,0);CHECK(!s.reasons);
 off_t bytes=lseek(fd,0,SEEK_END);CHECK(bytes==64+2*112+50+96);CHECK(lseek(fd,0,SEEK_SET)==0);uint8_t file[1024];CHECK(read(fd,file,sizeof(file))==bytes);CHECK(!memcmp(file,"COHPRP01",8));CHECK(!memcmp(file+64,"COHMSG01",8));CHECK(!memcmp(file+176,payload,40));CHECK(u32(file+bytes-96+12)==2);uint8_t hash[32];SHA256(file,(size_t)bytes-96,hash);CHECK(!memcmp(hash,file+bytes-32,32));close(fd);unlink(name);
 for(int mode=1;mode<=4;mode++){
  fd=tempfd(name);post_replay_init(&s);write_mode=mode;write_calls=0;int ok=post_replay_start(&s,fd);if(mode==2||mode==3)CHECK(!ok);else{CHECK(ok);record(&s,payload,40,3,0);post_replay_finish(&s,1);CHECK(!s.reasons&&s.records==1);}write_mode=0;close(fd);unlink(name);
 }
 for(unsigned k=0;k<8;k++){
  fd=tempfd(name);post_replay_init(&s);CHECK(post_replay_start(&s,fd));
  if(k==0)record(&s,payload,40,1,8388608);
  if(k==1)post_replay_record(&s,(uint8_t*)&s,1,8,0,1,1,1,2,0,0,0,0);
  if(k==2)post_replay_record(&s,(uint8_t*)(UINTPTR_MAX-1),8,64,0,1,1,1,2,0,0,0,0);
  if(k==3)post_replay_record(&s,payload,40,321,0,1,1,1,2,0,0,0,0);
  if(k==4)post_replay_record(&s,payload,40,320,0,1,0,1,999,0,0,0,0);
  if(k==5)post_replay_record(&s,payload,40,320,0,1,1,1,2,2,0,0,0);
  if(k==6){record(&s,payload,40,2,0);record(&s,payload,40,1,0);}
  if(k==7){write_mode=3;record(&s,payload,40,1,0);write_mode=0;}
  CHECK(s.omitted==1&&s.reasons);unsigned old=s.records;record(&s,payload,40,4,0);CHECK(s.records==old&&s.omitted==2);post_replay_finish(&s,0);CHECK(s.reasons&COH_POST_REPLAY_WINDOW_INCOMPLETE);close(fd);unlink(name);
 }
 fd=tempfd(name);post_replay_init(&s);CHECK(post_replay_start(&s,fd));for(unsigned i=0;i<128;i++)record(&s,payload,1,i+1,0);CHECK(s.records==128);record(&s,payload,1,129,0);CHECK(s.records==128&&(s.reasons&COH_POST_REPLAY_RECORD_LIMIT));post_replay_finish(&s,1);close(fd);unlink(name);
 fd=tempfd(name);post_replay_init(&s);CHECK(post_replay_start(&s,fd));uint8_t*big=calloc(1,4194304);CHECK(big);record(&s,big,4194304,1,0);record(&s,big,4194304,2,0);CHECK(s.records==1&&(s.reasons&COH_POST_REPLAY_DISK_LIMIT));CHECK(s.bytes+96<8388608);post_replay_finish(&s,1);free(big);close(fd);unlink(name);
 fd=tempfd(name);post_replay_init(&s);CHECK(post_replay_start(&s,fd));record(&s,payload,40,1,0);post_replay_reconcile(&s,3);CHECK(s.seen==3&&s.records==1&&s.omitted==2&&s.reasons==COH_POST_REPLAY_UNOBSERVED_MESSAGE);post_replay_finish(&s,1);close(fd);unlink(name);
 fd=tempfd(name);post_replay_init(&s);CHECK(post_replay_start(&s,fd));record(&s,payload,40,1,0);post_replay_reconcile(&s,0);CHECK(s.reasons&COH_POST_REPLAY_INVALID);post_replay_finish(&s,0);close(fd);unlink(name);
 fd=tempfd(name);CHECK(write(fd,payload,40)==40);post_replay_init(&s);CHECK(!post_replay_start(&s,fd));close(fd);unlink(name);
 if(argc==2){
  fd=open(argv[1],O_WRONLY|O_CREAT|O_EXCL,0600);CHECK(fd>=0);post_replay_init(&s);CHECK(post_replay_start(&s,fd));uint8_t*fixture=malloc(37963);CHECK(fixture);for(unsigned i=0;i<37963;i++)fixture[i]=(uint8_t)(i*13u);
  for(unsigned i=0;i<115;i++){size_t n=i?32u+(i%17u):37963u;post_replay_record(&s,fixture,n,n*8-(i%7),32,1000u+i*250u,i+1,i+4,i?2:3,i%2,1,i+2,7000000);}
  post_replay_finish(&s,1);CHECK(s.records==115&&s.seen==115&&!s.reasons);free(fixture);close(fd);
 }
 printf("{\"passed\":true,\"checks\":%u,\"state_bytes\":%zu,\"disk_cap\":%u,\"record_cap\":%u,\"stack_reserve\":%u,\"decoded\":false}\n",checks,sizeof(s),COH_POST_REPLAY_FILE_BYTES,COH_POST_REPLAY_RECORDS,COH_POST_REPLAY_STACK_RESERVE);return 0;
}
