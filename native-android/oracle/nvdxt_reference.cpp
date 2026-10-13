/* Qualification adapter for the pinned original Win32 NVIDIA static SDK.
 * The decode implementation comes from nvDXTlibMT_S.lib, not this source.
 * Run each well-formed, provenance-checked input in its own process.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <malloc.h>

/* Exact C++ API from pinned dxtlib.h; no compressor/header dependency. */
unsigned char * __cdecl nvDXTdecompress(int &,int &,int &,int &,int &,int &,int);

static unsigned char *input_bytes;
static size_t input_size,input_offset;
static size_t read_offsets[256],read_counts[256],read_calls;
static const size_t limit_bytes=128u*1024u*1024u;

static void fail(const char *message){fprintf(stderr,"nvDXT oracle: %s\n",message);exit(90);}
static uint32_t read32(const unsigned char *p){
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
void __cdecl ReadDTXnFile(DWORD count,void *buffer,void *user_data){
    (void)user_data;
    if(input_offset>input_size||(size_t)count>input_size-input_offset)fail("SDK callback requested bytes outside bounded input");
    if(read_calls>=256)fail("SDK callback trace limit exceeded");
    read_offsets[read_calls]=input_offset;read_counts[read_calls]=(size_t)count;read_calls++;
    memcpy(buffer,input_bytes+input_offset,(size_t)count);input_offset+=(size_t)count;
}
void __cdecl WriteDTXnFile(DWORD count,void *buffer,void *user_data){
    (void)count;(void)buffer;(void)user_data;fail("unexpected SDK write callback");
}
static void save_bytes(const char *path,const unsigned char *bytes,size_t size){
    FILE *f=fopen(path,"wb");if(!f)fail("cannot open output");
    if(fwrite(bytes,1,size,f)!=size){fclose(f);fail("cannot write output");}
    if(fclose(f))fail("cannot close output");
}
static void validate_dds(void){
    if(input_size<128||memcmp(input_bytes,"DDS ",4)||read32(input_bytes+4)!=124||read32(input_bytes+76)!=32)fail("invalid DDS envelope");
    uint32_t width=read32(input_bytes+16),height=read32(input_bytes+12),mips=read32(input_bytes+28);
    uint32_t format=read32(input_bytes+84),unit=format==0x31545844u?8:16;
    if(!(read32(input_bytes+80)&4)||(format!=0x31545844u&&format!=0x33545844u&&format!=0x35545844u))fail("only DXT1/3/5 oracle inputs accepted");
    if(!width||!height||width>4096||height>4096||read32(input_bytes+24)>1||(read32(input_bytes+112)&0x20fe00u))fail("unsupported DDS dimensions or surface");
    uint32_t maximum=1,t=width>height?width:height;while(t>1){maximum++;t>>=1;}
    if(!mips)mips=1;if(mips>maximum)fail("invalid DDS mip count");
    size_t offset=128;
    for(uint32_t i=0;i<mips;i++){
        size_t bytes=(size_t)((width+3)/4)*((height+3)/4)*unit;
        if(offset>input_size||bytes>input_size-offset)fail("truncated DDS mip chain");
        offset+=bytes;width=width>1?width/2:1;height=height>1?height/2:1;
    }
}
int main(int argc,char **argv){
    static_assert(sizeof(void *)==4,"original nvDXT oracle must be built Win32");
    if(argc!=5){fprintf(stderr,"usage: nvdxt-reference.exe input.dds out.raw out.rgba out.json\n");return 2;}
    FILE *f=fopen(argv[1],"rb");if(!f)fail("cannot open input");
    if(fseek(f,0,SEEK_END))fail("cannot seek input");long length=ftell(f);
    if(length<0||(size_t)length>limit_bytes)fail("input size exceeds oracle limit");
    input_size=(size_t)length;input_bytes=(unsigned char *)malloc(input_size?input_size:1);
    if(!input_bytes)fail("input allocation failed");
    if(fseek(f,0,SEEK_SET)||fread(input_bytes,1,input_size,f)!=input_size)fail("cannot read input");
    if(fclose(f))fail("cannot close input");validate_dds();
    int width=0,height=0,depth=0,total_width=0,row_bytes=0,source_format=0;
    unsigned char *raw=nvDXTdecompress(width,height,depth,total_width,row_bytes,source_format,1);
    if(!raw)fail("SDK returned null");
    fprintf(stderr,"nvDXT metadata: width=%d height=%d depth=%d total_width=%d row_bytes=%d source_format=%d\n",width,height,depth,total_width,row_bytes,source_format);
    if(width<=0||height<=0||width>4096||height>4096||(depth!=3&&depth!=4)||total_width<width||row_bytes<width*depth)fail("SDK returned unsupported output metadata");
    if(row_bytes!=width*depth)fail("SDK row pitch differs from Game consumer's tightly packed pixel conversion");
    size_t allocated=_msize(raw),raw_size=(size_t)row_bytes*(size_t)height;
    size_t rgba_size=(size_t)width*(size_t)height*4;
    if(allocated==(size_t)-1||allocated>limit_bytes||raw_size>allocated||raw_size>limit_bytes||rgba_size>limit_bytes)fail("SDK output extent exceeds allocation or oracle limit");
    unsigned char *rgba=(unsigned char *)malloc(rgba_size);if(!rgba)fail("RGBA allocation failed");
    for(int y=0;y<height;y++)for(int x=0;x<width;x++){
        const unsigned char *pixel=raw+(size_t)y*(size_t)row_bytes+(size_t)x*(size_t)depth;
        unsigned char *out=rgba+((size_t)y*(size_t)width+(size_t)x)*4;
        /* Exact consumer channel conversion in uncompressRawTexInfo. */
        out[0]=pixel[2];out[1]=pixel[1];out[2]=pixel[0];out[3]=depth==4?pixel[3]:255;
    }
    save_bytes(argv[2],raw,raw_size);save_bytes(argv[3],rgba,rgba_size);
    f=fopen(argv[4],"wb");if(!f)fail("cannot open metadata");
    fprintf(f,"{\n  \"oracle\":\"original-nvDXTlibMT_S-Win32\",\n  \"specified_mip_maps\":1,\n  \"width\":%d,\"height\":%d,\"depth\":%d,\"total_width\":%d,\"row_bytes\":%d,\"source_format\":%d,\n  \"allocation_bytes\":%lu,\"raw_bytes\":%lu,\"rgba_bytes\":%lu,\n  \"input_bytes\":%lu,\"input_consumed\":%lu,\"read_calls\":%lu,\n  \"normalization\":\"BGR(A) to tightly packed RGBA; opaque alpha for depth3\",\n  \"reads\":[",
            width,height,depth,total_width,row_bytes,source_format,(unsigned long)allocated,(unsigned long)raw_size,(unsigned long)rgba_size,(unsigned long)input_size,(unsigned long)input_offset,(unsigned long)read_calls);
    for(size_t i=0;i<read_calls;i++)fprintf(f,"%s{\"offset\":%lu,\"bytes\":%lu}",i?",":"",(unsigned long)read_offsets[i],(unsigned long)read_counts[i]);
    fprintf(f,"]\n}\n");if(fclose(f))fail("cannot close metadata");
    free(rgba);free(raw);free(input_bytes);return 0;
}
