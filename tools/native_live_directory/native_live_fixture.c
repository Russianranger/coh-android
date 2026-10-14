/* Same finite kernel fixture executes against host libc and static Bionic ARM64.
 * Every mutation is confined to a freshly owned temporary fixture directory. */
#define _GNU_SOURCE
#include "coh_live_directory_core.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <time.h>
#include <unistd.h>

static unsigned controls;
static unsigned char operation[16],directory[16];
static char root[1024],items[1024];
#define REQUIRE(condition) do { if (!(condition)) {fprintf(stderr,"fixture failure line=%d errno=%d\n",__LINE__,errno);exit(1);} } while(0)
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint64_t u64(const unsigned char *p){return (uint64_t)u32(p)|((uint64_t)u32(p+4)<<32);}
static void path(char *out,const char *base,const char *name){REQUIRE(snprintf(out,1024,"%s/%s",base,name)<1024);}
static void put(const char *name,const char *data){char p[1024];int fd;path(p,items,name);fd=open(p,O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC,0600);REQUIRE(fd>=0);REQUIRE(write(fd,data,strlen(data))==(ssize_t)strlen(data));REQUIRE(!close(fd));}
static unsigned fds(void){DIR *d=opendir("/proc/self/fd");struct dirent *e;unsigned n=0;REQUIRE(d!=NULL);while((e=readdir(d)))if(strcmp(e->d_name,".")&&strcmp(e->d_name,".."))n++;REQUIRE(!closedir(d));return n;}
static CohLiveNamespace *space_open(void){
    struct stat st;CohLiveRootSpec spec;CohLiveNamespace *space=NULL;CohLiveError error;
    REQUIRE(!stat(root,&st));spec=(CohLiveRootSpec){"/data",root,(uint64_t)st.st_dev,(uint64_t)st.st_ino,(uint32_t)st.st_uid};
    REQUIRE(coh_live_namespace_open(&space,&spec,1,(uint32_t)getuid(),1000,0,0,&error));return space;
}
static CohLiveDirectory *cursor_open(CohLiveNamespace *space){CohLiveDirectory *cursor=NULL;CohLiveError error;REQUIRE(coh_live_directory_open(space,&cursor,"/data/items",operation,directory,&error));return cursor;}
static const unsigned char *next(CohLiveDirectory *cursor,uint32_t sequence,uint32_t first,size_t *bytes){
    const unsigned char *wire=NULL;CohLiveError error;uint32_t count,i,used=0;
    REQUIRE(coh_live_directory_next(cursor,&wire,bytes,&error));REQUIRE(wire!=NULL&&*bytes<=27944&&*bytes>=64);
    REQUIRE(!memcmp(wire,"COHLIVE1",8)&&!memcmp(wire+8,operation,16)&&!memcmp(wire+24,directory,16));
    REQUIRE(u32(wire+40)==sequence&&u32(wire+44)==first&&u32(wire+56)==0&&u32(wire+60)==*bytes);
    count=u32(wire+48);REQUIRE(count<=85&&*bytes==64+(size_t)count*328&&u32(wire+52)<=1);
    for(i=0;i<count;i++){const unsigned char *row=wire+64+(size_t)i*328,*wfd=row+8;size_t n=strlen((const char *)wfd+44);
        REQUIRE(u32(row)==first+i&&u32(row+4)==0&&n>0&&n<260);used=((used+7)&~7u)+94+(uint32_t)n*2;REQUIRE(used<=8192);}
    return wire;
}
static const unsigned char *find(const unsigned char *wire,const char *name){uint32_t i;for(i=0;i<u32(wire+48);i++){const unsigned char *wfd=wire+64+(size_t)i*328+8;if(!strcmp((const char *)wfd+44,name))return wfd;}return NULL;}
static int walk_find(CohLiveDirectory *cursor,uint32_t sequence,uint32_t first,const char *name,uint32_t expected_size,uint64_t expected_time){
    size_t bytes;const unsigned char *wire,*row;int found=0;
    do{wire=next(cursor,sequence++,first,&bytes);first+=u32(wire+48);row=find(wire,name);if(row){REQUIRE(u32(row+32)==expected_size);if(expected_time)REQUIRE(u64(row+20)==expected_time);found=1;}}while(!u32(wire+52));
    return found;
}
static void remove_owned(const char *path_name){DIR *d=opendir(path_name);struct dirent *e;char p[1024];struct stat st;
    REQUIRE(d!=NULL);while((e=readdir(d))){if(!strcmp(e->d_name,".")||!strcmp(e->d_name,".."))continue;path(p,path_name,e->d_name);REQUIRE(!lstat(p,&st));if(S_ISDIR(st.st_mode))remove_owned(p);else REQUIRE(!unlink(p));}REQUIRE(!closedir(d));REQUIRE(!rmdir(path_name));}

int main(void){
    CohLiveNamespace *space;CohLiveDirectory *cursor,*other[16];CohLiveError error;CohLiveStats stats;
    struct stat st;struct timespec start,stop,times[2];char p[1024],name[40],moved[1024];size_t bytes;
    const unsigned char *wire,*row;unsigned i,before;uint32_t first;int good;
    REQUIRE(!clock_gettime(CLOCK_MONOTONIC,&start));
    for(i=0;i<16;i++){operation[i]=(unsigned char)i;directory[i]=(unsigned char)(16+i);}
    strcpy(root,"/tmp/coh-live-bionic-XXXXXX");REQUIRE(mkdtemp(root)!=NULL);path(items,root,"items");REQUIRE(!mkdir(items,0700));
    put("A","1");put("a","22");put("Z","333");put("z","4444");put("_under","5");put("[bracket]","6");put(".hidden","7");
    space=space_open();cursor=cursor_open(space);coh_live_namespace_stats(space,&stats);REQUIRE(stats.metadata_requests==0);controls++;
    wire=next(cursor,0,0,&bytes);REQUIRE(u32(wire+52)==1&&u32(wire+48)==9);controls++;
    REQUIRE(!strcmp((const char *)wire+64+8+44,".")&&!strcmp((const char *)wire+64+328+8+44,".."));controls++;
    REQUIRE(!strcmp((const char *)wire+64+2*328+8+44,".hidden")&&!strcmp((const char *)wire+64+3*328+8+44,"A")&&!strcmp((const char *)wire+64+4*328+8+44,"a"));controls++;
    REQUIRE(!strcmp((const char *)wire+64+7*328+8+44,"[bracket]")&&!strcmp((const char *)wire+64+8*328+8+44,"_under"));controls++;
    row=find(wire,".");REQUIRE(row&&u32(row+28)==0&&u32(row+32)==0);controls++;
    row=find(wire,".hidden");REQUIRE(row&&(u32(row)&2));controls++;
    good=coh_live_directory_next(cursor,&wire,&bytes,&error);REQUIRE(!good&&error.error_number==EPIPE&&error.rows_emitted==9&&!error.fallback_allowed);controls++;
    coh_live_directory_close(cursor);
    for(i=0;i<180;i++){snprintf(name,sizeof(name),"f%05u",i);put(name,"old");}
    cursor=cursor_open(space);wire=next(cursor,0,0,&bytes);first=u32(wire+48);REQUIRE(!u32(wire+52));
    coh_live_namespace_stats(space,&stats);REQUIRE(stats.metadata_requests>first);controls++;
    put("f00170","new current payload");path(p,items,"f00170");times[0]=(struct timespec){1700000000,123456789};times[1]=(struct timespec){1700000000,567890123};REQUIRE(!utimensat(AT_FDCWD,p,times,0));
    put("created_after_open","not in names");
    REQUIRE(walk_find(cursor,1,first,"f00170",19,UINT64_C(133444736005678901)));controls++;
    coh_live_directory_close(cursor);
    /* A registered PRoot path is not a held-FD bind. Changed pathname custody
     * is a terminal refusal, even though the kernel still owns the old inode. */
    cursor=cursor_open(space);wire=next(cursor,0,0,&bytes);first=u32(wire+48);path(moved,root,"olditems");REQUIRE(!rename(items,moved));REQUIRE(!mkdir(items,0700));put("f00170","unrelated");
    good=coh_live_directory_next(cursor,&wire,&bytes,&error);REQUIRE(!good&&error.error_number==ESTALE&&error.rows_emitted==first&&!error.fallback_allowed);controls++;
    coh_live_directory_close(cursor);remove_owned(items);REQUIRE(!rename(moved,items));
    path(p,items,"current_link");REQUIRE(!symlink("f00170",p));cursor=cursor_open(space);REQUIRE(walk_find(cursor,0,0,"current_link",19,UINT64_C(133444736005678901)));controls++;coh_live_directory_close(cursor);REQUIRE(!unlink(p));
    path(p,items,"guest_link");REQUIRE(!symlink("/data/items/f00170",p));cursor=cursor_open(space);REQUIRE(walk_find(cursor,0,0,"guest_link",19,UINT64_C(133444736005678901)));controls++;coh_live_directory_close(cursor);REQUIRE(!unlink(p));
    path(p,items,".unknown");REQUIRE(!symlink("/not-bound/missing",p));cursor=cursor_open(space);good=coh_live_directory_next(cursor,&wire,&bytes,&error);REQUIRE(!good&&error.error_number==EXDEV&&error.rows_emitted==0&&error.fallback_allowed);controls++;coh_live_directory_close(cursor);REQUIRE(!unlink(p));
    path(p,items,"zunknown");REQUIRE(!symlink("/not-bound/missing",p));cursor=cursor_open(space);wire=next(cursor,0,0,&bytes);do{good=coh_live_directory_next(cursor,&wire,&bytes,&error);}while(good);REQUIRE(error.error_number==EXDEV&&error.rows_emitted>0&&!error.fallback_allowed);controls++;
    REQUIRE(!unlink(p));good=coh_live_directory_next(cursor,&wire,&bytes,&error);REQUIRE(!good&&error.error_number==EPIPE&&!error.fallback_allowed);controls++;coh_live_directory_close(cursor);
    path(p,items,"attr_file");put("attr_file","x");REQUIRE(!setxattr(p,"user.DOSATTRIB","0x6",3,0));cursor=cursor_open(space);wire=next(cursor,0,0,&bytes);row=find(wire,"attr_file");REQUIRE(row&&(u32(row)&6)==6);controls++;coh_live_directory_close(cursor);
    REQUIRE(!setxattr(p,"user.DOSATTRIB","0x8000000000000000",18,0));cursor=cursor_open(space);wire=next(cursor,0,0,&bytes);row=find(wire,"attr_file");REQUIRE(row&&(u32(row)&6)==6);controls++;coh_live_directory_close(cursor);
    REQUIRE(!chmod(p,0444));cursor=cursor_open(space);wire=next(cursor,0,0,&bytes);row=find(wire,"attr_file");REQUIRE(row&&(u32(row)&1));controls++;coh_live_directory_close(cursor);
    /* A maximum85-row frame still observes the nonfitting86th candidate. */
    {
        char shortdir[1024],leaf[1024],letter[2];uint64_t metadata_before;int fd;
        path(shortdir,root,"short");REQUIRE(!mkdir(shortdir,0700));
        for(i=32;i<127;i++)if(!strchr("/\\:*?\"<>|.",(int)i)){
            letter[0]=(char)i;letter[1]=0;path(leaf,shortdir,letter);
            fd=open(leaf,O_WRONLY|O_CREAT|O_CLOEXEC,0600);REQUIRE(fd>=0&&write(fd,"old",3)==3);REQUIRE(!close(fd));
        }
        cursor=NULL;REQUIRE(coh_live_directory_open(space,&cursor,"/data/short",operation,directory,&error));
        coh_live_namespace_stats(space,&stats);metadata_before=stats.metadata_requests;
        wire=next(cursor,0,0,&bytes);coh_live_namespace_stats(space,&stats);
        REQUIRE(u32(wire+48)==85&&bytes==27944&&stats.metadata_requests-metadata_before==86);controls++;
        path(leaf,shortdir,"}");fd=open(leaf,O_WRONLY|O_TRUNC|O_CLOEXEC);REQUIRE(fd>=0&&write(fd,"fresh",5)==5);REQUIRE(!close(fd));
        wire=next(cursor,1,85,&bytes);row=find(wire,"}");REQUIRE(row&&u32(row+32)==5&&u32(wire+52)==1);controls++;
        coh_live_directory_close(cursor);
    }
    /* Read-only helper preserves a synthetic profile and releases all cursors. */
    before=fds();for(i=0;i<16;i++)other[i]=cursor_open(space);cursor=NULL;good=coh_live_directory_open(space,&cursor,"/data/items",operation,directory,&error);REQUIRE(!good&&error.error_number==EMFILE);controls++;
    for(i=0;i<16;i++)coh_live_directory_close(other[i]);
    REQUIRE(fds()==before);controls++;
    coh_live_namespace_stats(space,&stats);REQUIRE(stats.owned_heap_bytes<100000&&stats.peak_heap_bytes<=32u*1024u*1024u);controls++;
    REQUIRE(!stat(p,&st)&&st.st_size==1);controls++;
    before=fds();coh_live_namespace_close(space);REQUIRE(fds()+1==before);controls++;
    remove_owned(root);REQUIRE(!clock_gettime(CLOCK_MONOTONIC,&stop));
    printf("{\"schema\":\"coh-live-native-kernel-fixture-v1\",\"controls_passed\":%u,\"failures\":0,\"libc\":\"%s\",\"pointer_bytes\":%zu,\"stat_bytes\":%zu,\"uid\":%u,\"elapsed_seconds\":%.9f,\"peak_owned_heap_bytes\":%zu,\"metadata_requests\":%llu,\"android_os_or_wine_or_game_qualified\":false,\"shipping_admission\":false}\n",
        controls,
#ifdef __BIONIC__
        "Bionic",
#else
        "host",
#endif
        sizeof(void *),sizeof(struct stat),(unsigned)getuid(),
        (double)(stop.tv_sec-start.tv_sec)+(double)(stop.tv_nsec-start.tv_nsec)/1e9,
        stats.peak_heap_bytes,(unsigned long long)stats.metadata_requests);
    return 0;
}
