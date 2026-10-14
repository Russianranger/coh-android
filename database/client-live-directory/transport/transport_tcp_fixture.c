/* Host TCPv4 byte-stream control, not native Game or backend authority. */
#include "coh_live_transport.h"
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"TCP fixture failure line %d\n",__LINE__);exit(3);}}while(0)
static void p32(unsigned char *p,uint32_t n){p[0]=(unsigned char)n;p[1]=(unsigned char)(n>>8);p[2]=(unsigned char)(n>>16);p[3]=(unsigned char)(n>>24);}
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void readAll(int fd,unsigned char *p,size_t bytes){while(bytes){ssize_t n=recv(fd,p,1,0);CHECK(n==1);p++;bytes--;}}
static void writeAll(int fd,const unsigned char *p,size_t bytes){while(bytes){ssize_t n=send(fd,p,1,0);CHECK(n==1);p++;bytes--;}}
static void serve(int listener){
 int fd=accept(listener,NULL,NULL);unsigned char request[96],path[1024],reply[32+392];uint32_t command;
 CHECK(fd>=0);CHECK(close(listener)==0);
 for(command=1;command<=3;command++){
  uint32_t length;readAll(fd,request,sizeof(request));CHECK(!memcmp(request,"COHLDIR1",8));
  CHECK(u32(request+8)==1&&u32(request+12)==command&&u32(request+64)==command);
  CHECK(request[16]==11&&request[31]==26&&request[32]==37&&request[63]==68);
  CHECK(request[68]==7&&u32(request+92)==0);length=u32(request+84);
  CHECK(u32(request+88)==96+length);CHECK(length<=1024);
  if(command==1){CHECK(length==20);readAll(fd,path,length);CHECK(!memcmp(path,"/game-import/data/fx",20));}
  else CHECK(length==0);
  memset(reply,0,sizeof(reply));memcpy(reply,"COHRSP1\0",8);p32(reply+8,1);p32(reply+16,command);
  if(command==1){length=32;p32(reply+32,1);p32(reply+40,2);p32(reply+48,1);p32(reply+52,1);}
  else if(command==2){
   unsigned char *frame=reply+32,*wfd=frame+64+8;length=392;
   memcpy(frame,"COHLIVE1",8);memcpy(frame+8,request+16,16);memcpy(frame+24,request+68,16);
   p32(frame+48,1);p32(frame+52,1);p32(frame+60,392);p32(wfd+32,99);memcpy(wfd+44,"test.txt",9);
  }else length=0;
  p32(reply+20,length);writeAll(fd,reply,32+length);
 }
 CHECK(close(fd)==0);exit(0);
}
typedef struct Io {int fd,closes,last_error;unsigned allocated,released;} Io;
static int32_t readPeer(void *context,unsigned char *p,uint32_t count){Io *io=(Io *)context;ssize_t n; (void)count;n=recv(io->fd,p,1,0);if(n<0)io->last_error=errno;return (int32_t)n;}
static int32_t writePeer(void *context,const unsigned char *p,uint32_t count){Io *io=(Io *)context;ssize_t n;if(count>7)count=7;n=send(io->fd,p,count,0);if(n<0)io->last_error=errno;return (int32_t)n;}
static void closePeer(void *context){Io *io=(Io *)context;io->closes++;(void)close(io->fd);}
static void *allocate(void *context,size_t bytes){Io *io=(Io *)context;void *p=malloc(bytes);if(p)io->allocated++;return p;}
static void release(void *context,void *p){Io *io=(Io *)context;io->released++;free(p);}
int main(void){
 int listener,status;pid_t child;struct sockaddr_in address;socklen_t address_bytes=sizeof(address);
 Io io={0};CohLiveTransportIo callbacks;CohLiveTransport t;unsigned char operation[16],nonce[32],token[16]={7};
 uint32_t handle=0;const unsigned char *row;unsigned i;uint64_t device,inode;
 memset(&address,0,sizeof(address));address.sin_family=AF_INET;address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 listener=socket(AF_INET,SOCK_STREAM,0);CHECK(listener>=0);CHECK(bind(listener,(struct sockaddr *)&address,sizeof(address))==0);
 CHECK(getsockname(listener,(struct sockaddr *)&address,&address_bytes)==0);CHECK(address.sin_port!=0);
 CHECK(listen(listener,1)==0);child=fork();CHECK(child>=0);if(!child)serve(listener);
 io.fd=socket(AF_INET,SOCK_STREAM,0);CHECK(io.fd>=0);CHECK(connect(io.fd,(struct sockaddr *)&address,sizeof(address))==0);
 CHECK(close(listener)==0);memset(&callbacks,0,sizeof(callbacks));callbacks.context=&io;callbacks.read=readPeer;
 callbacks.write=writePeer;callbacks.close=closePeer;callbacks.allocate=allocate;callbacks.release=release;
 for(i=0;i<16;i++)operation[i]=(unsigned char)(i+11);for(i=0;i<32;i++)nonce[i]=(unsigned char)(i+37);
 CHECK(cohLiveTransportInit(&t,&callbacks,operation,nonce)==1);
 CHECK(cohLiveTransportOpen(&t,"/game-import/data/fx",token,1,2,&handle)==1);
 CHECK(cohLiveTransportIdentity(&t,handle,&device,&inode)==1&&device==1&&inode==2);
 CHECK(cohLiveTransportNext(&t,handle,&row)==1);CHECK(!strcmp((const char *)row+44,"test.txt"));CHECK(u32(row+32)==99);
 CHECK(cohLiveTransportNext(&t,handle,&row)==0&&row==NULL);CHECK(cohLiveTransportClose(&t,&handle)==1&&handle==0);
 cohLiveTransportShutdown(&t);CHECK(io.closes==1&&io.allocated==io.released&&io.last_error==0);
 CHECK(waitpid(child,&status,0)==child);CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);
 printf("{\"group\":\"host_tcpv4_stream\",\"checks\":%u,\"passed\":true,\"native_authority\":false}\n",checks);return 0;
}
