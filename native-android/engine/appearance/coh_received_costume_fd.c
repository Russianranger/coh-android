#define _POSIX_C_SOURCE 200809L
#include "coh_received_costume_fd.h"
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>
typedef struct {int fd;uint64_t bytes;struct stat identity;} Input;
struct CohReceivedCostumeFds {Input inputs[2];};
static int apart(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x<y?an<=y-x:bn<=x-y);}
static int same(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_size==b->st_size&&a->st_uid==b->st_uid&&a->st_mode==b->st_mode&&a->st_nlink==b->st_nlink&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
static int immutable(Input*i,struct stat*out){int flags=fcntl(i->fd,F_GETFL);return flags>=0&&(flags&O_ACCMODE)==O_RDONLY&&!fstat(i->fd,out)&&S_ISREG(out->st_mode)&&out->st_size>=22&&out->st_uid==geteuid()&&!(out->st_mode&0222);}
static CohStatus read_at(void*context,uint64_t offset,void*out,size_t bytes){
 Input*i=context;struct stat before,after;if(!i||(!out&&bytes)||offset>i->bytes||bytes>i->bytes-offset)return COH_INVALID;
 if(!immutable(i,&before)||!same(&i->identity,&before))return COH_STATE;
 size_t done=0;while(done<bytes){size_t n=bytes-done;if(n>65536)n=65536;ssize_t got=pread(i->fd,(unsigned char*)out+done,n,(off_t)(offset+done));if(got<0&&errno==EINTR)continue;if(got<=0)return COH_IO;done+=(size_t)got;}
 return immutable(i,&after)&&same(&before,&after)?COH_OK:COH_STATE;
}
size_t coh_received_costume_fds_allocation_bytes(void){return sizeof(CohReceivedCostumeFds);}
void coh_received_costume_fds_destroy(CohReceivedCostumeFds**out){if(!out||(uintptr_t)out%_Alignof(CohReceivedCostumeFds*)||!*out||!apart(out,sizeof*out,*out,sizeof**out))return;for(unsigned i=0;i<2;i++)if((*out)->inputs[i].fd>=0)close((*out)->inputs[i].fd);free(*out);*out=NULL;}
CohStatus coh_received_costume_fds_open(const CohReceivedArchiveFd in[2],CohReceivedCostumeFds**out){
 if(!in||!out||(uintptr_t)in%_Alignof(CohReceivedArchiveFd)||(uintptr_t)out%_Alignof(CohReceivedCostumeFds*)||!apart(in,2*sizeof*in,out,sizeof*out))return COH_INVALID;
 if(*out)return COH_STATE;
 for(unsigned i=0;i<2;i++)if(in[i].fd<0||in[i].offset||in[i].bytes<22||in[i].bytes>UINT32_MAX)return COH_INVALID;
 CohReceivedCostumeFds*owner=calloc(1,sizeof*owner);if(!owner)return COH_LIMIT;owner->inputs[0].fd=owner->inputs[1].fd=-1;CohStatus status=COH_STATE;
 for(unsigned i=0;i<2;i++){Input*p=owner->inputs+i;p->fd=fcntl(in[i].fd,F_DUPFD_CLOEXEC,0);if(p->fd<0){status=COH_IO;goto fail;}p->bytes=in[i].bytes;if(!immutable(p,&p->identity)||(uint64_t)p->identity.st_size!=p->bytes)goto fail;}
 *out=owner;return COH_OK;
fail:coh_received_costume_fds_destroy(&owner);return status;
}
CohStatus coh_received_costume_fds_sources(CohReceivedCostumeFds*in,CohAssetSource out[2]){
 if(!in||!out||(uintptr_t)out%_Alignof(CohAssetSource)||!apart(in,sizeof*in,out,2*sizeof*out))return COH_INVALID;
 for(unsigned i=0;i<2;i++)out[i]=(CohAssetSource){read_at,in->inputs+i,in->inputs[i].bytes,1};
 return COH_OK;
}
