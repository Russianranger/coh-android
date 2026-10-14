/* Four memory callbacks are included unchanged from the pinned client source.
 * Only the standalone libvorbis wrapper executes, not the Win32 sound engine. */
#define OV_EXCLUDE_STATIC_CALLBACKS
#include <vorbis/vorbisfile.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef struct { char *mem; int curr,length; } MemFile;
#include "source_callbacks.inc"
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    FILE *in=fopen(argv[1],"rb");if(!in)return 3;
    if(fseek(in,0,SEEK_END))return 4;
    long size=ftell(in);if(size<=0 || size>1048576)return 5;
    rewind(in);char *data=malloc((size_t)size);if(!data)return 6;
    if(fread(data,1,(size_t)size,in)!=(size_t)size)return 7;
    fclose(in);MemFile memory={data,0,(int)size};OggVorbis_File state;
    ov_callbacks callbacks={readbytes,seekbytes,closebytes,tellbytes};
    if(ov_open_callbacks(&memory,&state,0,0,callbacks)<0)return 8;
    vorbis_info *info=ov_info(&state,-1);
    ogg_int64_t frames=ov_pcm_total(&state,-1);
    if(ov_streams(&state)!=1 || !info || info->rate!=44100 || info->channels!=2 || frames!=18168)return 9;
    FILE *out=fopen(argv[2],"wb");if(!out)return 10;
    char buffer[32768];long total=0;int section=0,calls=0;
    for(;;) {
        /* Exact signed16 little-endian parameter triple used in oggDecode. */
        long n=ov_read(&state,buffer,sizeof buffer,0,2,1,&section);calls++;
        if(n<0 || section!=0 || total+n>1048576)return 11;
        if(!n)break;
        if(fwrite(buffer,1,(size_t)n,out)!=(size_t)n)return 12;
        total+=n;
    }
    if(total!=frames*info->channels*2)return 13;
    fclose(out);ov_clear(&state);free(data);
    printf("{\"passed\":true,\"sample_rate\":44100,\"channels\":2,\"frames\":%lld,\"pcm_bytes\":%ld,\"ov_read_calls\":%d,\"vorbis_version\":\"%s\",\"ov_read_parameters\":[0,2,1],\"memory_callbacks_unchanged\":true}\n",(long long)frames,total,calls,vorbis_version_string());
    return 0;
}
