#include "coh_local_bodypart_default.h"
#include <errno.h>
#include <fcntl.h>
#include <openssl/sha.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
CohStatus coh_local_bodypart_default_file(const char*path,uint32_t*out){
 if(!path||!out)return COH_INVALID;
 size_t n=0;while(n<1024&&path[n])n++;
 if(!n||n==1024||path[0]!='/'||overlap(path,n+1,out,sizeof(*out)))return COH_INVALID;
 uint8_t data[COH_LOCAL_BODYPART_CACHE_BYTES],hash[32];struct stat info;
 static const uint8_t expected[32]={0xb0,0x95,0x5c,0x46,0x73,0x1e,0xd0,0xcb,0x54,0xad,0x01,0xd9,0x60,0x15,0xb3,0x01,0xe5,0x83,0xbd,0x02,0x24,0xf8,0xd8,0x72,0xf5,0x0c,0xfe,0xfe,0xb0,0x8f,0x6b,0xeb};
 CohStatus status=COH_IO;int fd=open(path,O_RDONLY);size_t read_bytes=0;
 if(fd<0)return errno==ENOENT||errno==ENOTDIR?COH_NOT_FOUND:COH_IO;
 if(fstat(fd,&info)!=0)goto done;
 if(!S_ISREG(info.st_mode)||info.st_size!=(off_t)sizeof(data)){status=COH_STATE;goto done;}
 while(read_bytes<sizeof(data)){
  ssize_t got=read(fd,data+read_bytes,sizeof(data)-read_bytes);
  if(got<0&&errno==EINTR)continue;
  if(got<=0)goto done;
  read_bytes+=(size_t)got;
 }
 for(;;){uint8_t extra;ssize_t got=read(fd,&extra,1);if(got<0&&errno==EINTR)continue;if(got<0)goto done;if(got){status=COH_STATE;goto done;}break;}
 if(!SHA256(data,sizeof(data),hash))goto done;
 status=memcmp(hash,expected,sizeof(hash))?COH_STATE:COH_OK;
 if(status!=COH_OK){
  /* Exact existing Parse6 projection identifies ONLY this Files1 mtime word.
   * Keep every path/header/schema/count/ordered-row byte in the comparison. */
  static const uint8_t canonical[32]={0x96,0x59,0x64,0xf4,0xe5,0x8e,0xb2,0x4d,0xbb,0x8b,0x85,0x67,0x2f,0xb0,0xbd,0xb9,0x63,0x1b,0xfc,0x98,0xd9,0x38,0xd3,0xd4,0x44,0x4a,0xa0,0x9a,0x44,0xc6,0x7c,0x83};
  memset(data+60,0,4);
  if(!SHA256(data,sizeof(data),hash))status=COH_IO;
  else status=memcmp(hash,canonical,sizeof(hash))?COH_STATE:COH_OK;
 }
done:
 if(close(fd)!=0)status=COH_IO;
 wipe(data,sizeof(data));wipe(hash,sizeof(hash));
 if(status==COH_OK)*out=COH_LOCAL_BODYPART_COUNT;
 return status;
}
