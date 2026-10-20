#define _POSIX_C_SOURCE 200809L
#include "session_world_imports.h"
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
typedef struct {int fd,archive;uint64_t offset,bytes;struct stat identity;uint64_t reads,read_bytes;} Input;
struct CohSessionWorldImports {Input inputs[3];};
static int same(const struct stat *a,const struct stat *b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_size==b->st_size&&a->st_uid==b->st_uid&&a->st_mode==b->st_mode&&a->st_nlink==b->st_nlink&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
static int readable(const Input *in,struct stat *out){int flags=fcntl(in->fd,F_GETFL);return flags>=0&&(flags&O_ACCMODE)==O_RDONLY&&!fstat(in->fd,out)&&S_ISREG(out->st_mode)&&out->st_size>=0&&(!in->archive||((out->st_mode&0222)==0&&out->st_uid==geteuid()));}
static CohStatus read_at(void *context,uint64_t offset,void *out,size_t bytes){
    Input *in=context;struct stat before,after;
    if(!in||(!out&&bytes)||offset>in->bytes||bytes>in->bytes-offset||in->offset>INT64_MAX-offset)return COH_INVALID;
    in->reads++;
    if(!readable(in,&before)||!same(&in->identity,&before))return COH_STATE;
    size_t done=0;while(done<bytes){size_t chunk=bytes-done;if(chunk>65536u)chunk=65536u;uint64_t position=in->offset+offset+done;if(position>INT64_MAX)return COH_INVALID;ssize_t n=pread(in->fd,(unsigned char *)out+done,chunk,(off_t)position);if(n<0&&errno==EINTR)continue;if(n<=0)return COH_IO;done+=(size_t)n;in->read_bytes+=(uint64_t)n;}
    if(!readable(in,&after)||!same(&before,&after))return COH_STATE;
    return COH_OK;
}
CohStatus coh_session_world_imports_open(const CohSessionWorldFd inputs[3],CohSessionWorldImports **out){
    if(!inputs||!out)return COH_INVALID;
    uintptr_t a=(uintptr_t)inputs,b=(uintptr_t)out;size_t size=3u*sizeof *inputs;
    if(a>UINTPTR_MAX-size||b>UINTPTR_MAX-sizeof *out||(a<b+sizeof *out&&b<a+size))return COH_INVALID;
    CohSessionWorldImports *owner=calloc(1,sizeof *owner);if(!owner)return COH_LIMIT;
    for(unsigned i=0;i<3;i++)owner->inputs[i].fd=-1;
    CohStatus status=COH_INVALID;
    for(unsigned i=0;i<3;i++){
        const CohSessionWorldFd *source=&inputs[i];Input *in=&owner->inputs[i];
        if(source->fd<0||!source->bytes||source->offset>INT64_MAX||source->bytes>INT64_MAX-source->offset||(i&&source->offset))goto failed;
        /* Index maximum comes from the existing65536x96-byte source row cap;
         * ZIP32 source lengths retain the original reader's UINT32_MAX cap. */
        if((!i&&(source->bytes<64||source->bytes>64u+65536u*96u))||(i&&(source->bytes<22||source->bytes>UINT32_MAX)))goto failed;
        in->fd=fcntl(source->fd,F_DUPFD_CLOEXEC,0);if(in->fd<0){status=COH_IO;goto failed;}
        in->archive=i!=0;in->offset=source->offset;in->bytes=source->bytes;
        if(!readable(in,&in->identity)||(uint64_t)in->identity.st_size<in->offset||in->bytes>(uint64_t)in->identity.st_size-in->offset||(i&&in->bytes!=(uint64_t)in->identity.st_size)){status=COH_STATE;goto failed;}
    }
    *out=owner;return COH_OK;
failed:coh_session_world_imports_free(owner);return status;
}
CohSessionWorldSources coh_session_world_imports_sources(CohSessionWorldImports *owner,uint64_t parent){
    CohSessionWorldSources result={0};result.parent_retained_bytes=parent;if(owner){CohAssetSource *sources[3]={&result.placements,&result.atlas_zip,&result.client_zip};for(unsigned i=0;i<3;i++){Input *in=&owner->inputs[i];*sources[i]=(CohAssetSource){read_at,in,in->bytes,1};}}return result;
}
uint64_t coh_session_world_imports_owned_bytes(const CohSessionWorldImports *owner){return owner?sizeof *owner:0;}
uint64_t coh_session_world_imports_allocation_bytes(void){return sizeof(CohSessionWorldImports);}
void coh_session_world_imports_free(CohSessionWorldImports *owner){if(owner){for(unsigned i=0;i<3;i++)if(owner->inputs[i].fd>=0)close(owner->inputs[i].fd);free(owner);}}

void coh_session_world_imports_io(const CohSessionWorldImports *owner,uint64_t *reads,uint64_t *bytes){uint64_t r=0,b=0;if(owner)for(unsigned i=0;i<3;i++){r+=owner->inputs[i].reads;b+=owner->inputs[i].read_bytes;}*reads=r;*bytes=b;}
