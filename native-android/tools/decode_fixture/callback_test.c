#define OV_EXCLUDE_STATIC_CALLBACKS
#include <vorbis/vorbisfile.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct { char *mem; int curr,length; } MemFile;
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
#include "source_callbacks.inc"
#pragma GCC diagnostic pop
static unsigned checks;
static void check(int ok) { ++checks;if(!ok) { fprintf(stderr,"callback bound check %u failed\n",checks);exit(1); } }
int main(void) {
    char data[]="0123456789",out[16]={0};MemFile f={data,0,10};
    check(readbytes(out,0,SIZE_MAX,&f)==0 && f.curr==0);
    check(readbytes(out,SIZE_MAX,SIZE_MAX,&f)==0 && f.curr==0);
    check(readbytes(out,3,SIZE_MAX,&f)==3 && f.curr==9 && !memcmp(out,data,9));
    check(readbytes(out,2,1,&f)==0 && f.curr==9);
    check(readbytes(out,1,SIZE_MAX,&f)==1 && f.curr==10);
    check(readbytes(out,1,1,&f)==0 && f.curr==10);
    check(!seekbytes(&f,-1,SEEK_END) && f.curr==9);
    check(!seekbytes(&f,-4,SEEK_CUR) && f.curr==5);
    check(seekbytes(&f,-1,SEEK_SET)==-1 && f.curr==5);
    check(seekbytes(&f,1,SEEK_END)==-1 && f.curr==5);
    check(seekbytes(&f,INT64_MAX,SEEK_CUR)==-1 && f.curr==5);
    check(seekbytes(&f,INT64_MIN,SEEK_CUR)==-1 && f.curr==5);
    check(seekbytes(&f,0,12345)==-1 && f.curr==5);
    check(!seekbytes(&f,0,SEEK_END) && tellbytes(&f)==10);
    check(!seekbytes(&f,0,SEEK_SET) && tellbytes(&f)==0);
    f.curr=-1;check(readbytes(out,1,1,&f)==0 && seekbytes(&f,0,SEEK_SET)==-1);
    f.curr=11;check(readbytes(out,1,1,&f)==0 && seekbytes(&f,0,SEEK_SET)==-1);
    check(readbytes(out,1,1,NULL)==0 && seekbytes(NULL,0,SEEK_SET)==-1);
    check(closebytes(&f)==0);
    printf("{\"passed\":true,\"unchanged_callback_bound_checks\":%u}\n",checks);return 0;
}
