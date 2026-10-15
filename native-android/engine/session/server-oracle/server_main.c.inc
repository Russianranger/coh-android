#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
int main(int argc,char **argv){
 assert(argc==3);int encrypted=atoi(argv[1]),drop=atoi(argv[2]);assert((encrypted==0||encrypted==1)&&(drop==0||drop==1));oracle_reset(encrypted);
 int fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);assert(fd>=0);struct sockaddr_in local={0};local.sin_family=AF_INET;local.sin_addr.s_addr=htonl(INADDR_LOOPBACK);assert(bind(fd,(struct sockaddr*)&local,sizeof(local))==0);socklen_t len=sizeof(local);assert(getsockname(fd,(struct sockaddr*)&local,&len)==0);printf("{\"port\":%u}\n",ntohs(local.sin_port));fflush(stdout);
 unsigned rx=0,tx=0,dropped=0,noise=0;unsigned rx_bytes[32]={0},tx_bytes[32]={0};
 while(!discarded){
  struct pollfd poller={fd,POLLIN,0};assert(poll(&poller,1,4000)==1);U8 wire[16384]={0};struct sockaddr_in peer={0};len=sizeof(peer);ssize_t n=recvfrom(fd,wire,1473,0,(struct sockaddr*)&peer,&len);assert(n>=0&&n<=1472&&len==sizeof(peer)&&peer.sin_family==AF_INET&&peer.sin_addr.s_addr==htonl(INADDR_LOOPBACK));
  if(drop&&!dropped){dropped=1;continue;}
  if(!noise){U8 bad[12]={0};assert(sendto(fd,bad,1,0,(struct sockaddr*)&peer,sizeof(peer))==1);assert(sendto(fd,bad,0,0,(struct sockaddr*)&peer,sizeof(peer))==0);assert(sendto(fd,bad,12,0,(struct sockaddr*)&peer,sizeof(peer))==12);noise=3;}
  assert(rx<32);rx_bytes[rx++]=(unsigned)n;assert(oracle_receive(wire,(unsigned)n)>=0);
  unsigned bytes;while((bytes=oracle_output(wire,sizeof(wire)))){assert(tx<32);tx_bytes[tx++]=bytes;assert(sendto(fd,wire,bytes,0,(struct sockaddr*)&peer,sizeof(peer))==(ssize_t)bytes);}
 }
 assert(close(fd)==0);printf("{\"connected\":%u,\"encrypt_on\":%u,\"decrypt_on\":%u,\"test_payload_received\":%u,\"original_ack_calls\":%u,\"discarded\":%u,\"connect_controls\":%u,\"client_ack_controls\":%u,\"disconnect_controls\":%u,\"duplicates\":%u,\"dropped\":%u,\"negative_datagrams\":%u,\"sockets_opened\":1,\"sockets_closed\":1,\"native_to_source_bytes\":[",oracle_stat(0),oracle_stat(1),oracle_stat(2),oracle_stat(3),oracle_stat(4),oracle_stat(5),oracle_stat(6),oracle_stat(7),oracle_stat(8),oracle_stat(9),dropped,noise);
 for(unsigned i=0;i<rx;i++)printf("%s%u",i?",":"",rx_bytes[i]);printf("],\"source_to_native_bytes\":[");for(unsigned i=0;i<tx;i++)printf("%s%u",i?",":"",tx_bytes[i]);printf("]}\n");oracle_reset(0);return 0;
}
