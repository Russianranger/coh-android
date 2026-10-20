#define _POSIX_C_SOURCE 200809L
#include "../app/src/main/cpp/session_world_imports.h"
#include "../../engine/world/coh_world_live.h"
#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#v);return 1;}}while(0)
static unsigned checks;
static int descriptors(void){DIR *d=opendir("/proc/self/fd");if(!d)return -1;int count=0;struct dirent *e;while((e=readdir(d)))if(e->d_name[0]!='.')count++;closedir(d);return count;}
static int inputs(char **paths,CohSessionWorldFd out[3]){for(unsigned i=0;i<3;i++){int fd=open(paths[i],O_RDONLY);struct stat st;if(fd<0||fstat(fd,&st))return 0;out[i]=(CohSessionWorldFd){fd,i?0:37,(uint64_t)st.st_size-(i?0:74)};}return 1;}
static void close_inputs(CohSessionWorldFd in[3]){for(unsigned i=0;i<3;i++)close(in[i].fd);}
int main(int argc,char **argv){
    CHECK(argc==4);int baseline=descriptors();CHECK(baseline>0);CohSessionWorldFd in[3];CHECK(inputs(argv+1,in));int opened=descriptors();CHECK(opened==baseline+3);
    CohSessionWorldImports *owner=NULL,*sentinel=(CohSessionWorldImports *)(uintptr_t)1;
    CHECK(coh_session_world_imports_open(NULL,&sentinel)==COH_INVALID&&sentinel==(CohSessionWorldImports *)(uintptr_t)1);
    CHECK(coh_session_world_imports_open(in,(CohSessionWorldImports **)(UINTPTR_MAX-1))==COH_INVALID);
    CHECK(coh_session_world_imports_open(in,(CohSessionWorldImports **)(void *)in)==COH_INVALID);
    CohSessionWorldFd invalid[3];memcpy(invalid,in,sizeof in);invalid[2].fd=-1;
    CHECK(coh_session_world_imports_open(invalid,&sentinel)==COH_INVALID&&sentinel==(CohSessionWorldImports *)(uintptr_t)1&&descriptors()==opened);
    memcpy(invalid,in,sizeof in);invalid[1].offset=1;CHECK(coh_session_world_imports_open(invalid,&sentinel)==COH_INVALID&&descriptors()==opened);
    memcpy(invalid,in,sizeof in);invalid[0].offset=UINT64_MAX;CHECK(coh_session_world_imports_open(invalid,&sentinel)==COH_INVALID&&descriptors()==opened);
    memcpy(invalid,in,sizeof in);invalid[0].bytes=UINT64_MAX;CHECK(coh_session_world_imports_open(invalid,&sentinel)==COH_INVALID&&descriptors()==opened);
    memcpy(invalid,in,sizeof in);invalid[2].bytes--;CHECK(coh_session_world_imports_open(invalid,&sentinel)==COH_STATE&&descriptors()==opened);
    CHECK(!chmod(argv[1],0600));int rw=open(argv[1],O_RDWR);CHECK(rw>=0);CHECK(!chmod(argv[1],0444));memcpy(invalid,in,sizeof in);invalid[0].fd=rw;CHECK(coh_session_world_imports_open(invalid,&sentinel)==COH_STATE);close(rw);CHECK(descriptors()==opened);
    CHECK(coh_session_world_imports_open(in,&owner)==COH_OK&&owner&&descriptors()==opened+3);
    CHECK(coh_session_world_imports_owned_bytes(owner)==coh_session_world_imports_allocation_bytes()&&coh_session_world_imports_owned_bytes(NULL)==0);
    CohSessionWorldSources source=coh_session_world_imports_sources(owner,12345);CHECK(source.parent_retained_bytes==12345&&source.placements.size==10144&&source.placements.generation==1);
    close_inputs(in);CHECK(descriptors()==baseline+3); /* Only owned dup FDs survive. */
    unsigned char header[64],before[64];memset(header,0xa5,sizeof header);memcpy(before,header,sizeof header);
    CHECK(source.placements.read_at(source.placements.context,0,header,sizeof header)==COH_OK&&!memcmp(header,"COHLIVE1",8));
    CHECK(source.placements.read_at(source.placements.context,source.placements.size-1,header,2)==COH_INVALID);
    CHECK(source.placements.read_at(source.placements.context,UINT64_MAX,header,2)==COH_INVALID);
    CHECK(source.placements.read_at(source.placements.context,0,NULL,0)==COH_OK);
    CohWorldLive *live=NULL;CHECK(coh_world_live_open(source.placements,4,(CohCancel){0},&live)==COH_OK);
    CohWorldInstance rows[64];uint32_t count=0;const float pose[3]={131.453125f,.25f,-114.953125f};CHECK(coh_world_live_query(live,pose,24,rows,64,&count,(CohCancel){0})==COH_OK&&count==2&&rows[0].node==8&&rows[1].node==13);
    CHECK(source.atlas_zip.read_at(source.atlas_zip.context,source.atlas_zip.size-22,header,22)==COH_OK&&!memcmp(header,"PK\005\006",4));
    CHECK(!chmod(argv[3],0600));memcpy(header,before,sizeof header);CHECK(source.client_zip.read_at(source.client_zip.context,0,header,4)==COH_STATE&&!memcmp(header,before,sizeof header));CHECK(!chmod(argv[3],0444));
    CHECK(source.client_zip.read_at(source.client_zip.context,0,header,4)==COH_STATE); /* Restored mode cannot restore the old inode state. */
    coh_world_live_free(live);coh_session_world_imports_free(owner);CHECK(descriptors()==baseline);
    CHECK(inputs(argv+1,in));for(unsigned i=0;i<128;i++){owner=NULL;CHECK(coh_session_world_imports_open(in,&owner)==COH_OK);coh_session_world_imports_free(owner);}close_inputs(in);CHECK(descriptors()==baseline);
    printf("{\"passed\":true,\"controls\":%u,\"fd_owned_bytes\":%llu,\"duplicate_descriptors\":3,\"repeat_open_close\":128,\"caller_close_preserved_native_sources\":true,\"index_span_offset\":37,\"heap_archive_copies\":0}\n",checks,(unsigned long long)coh_session_world_imports_allocation_bytes());return 0;
}
