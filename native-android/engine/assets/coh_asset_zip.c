#include "coh_asset_zip.h"
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
#define ZIP_MEMBERS 64u
#define ZIP_ASSET_MAX (1u<<20)
#define ZIP_SOURCE_MAX (4u<<20)
#define ZIP_WORK 65568u
#define ZIP_CHUNK 8192u
typedef struct {struct CohAssetZip *owner;char path[COH_ASSET_PATH_MAX+1];uint64_t data;uint32_t stored,bytes,crc;uint16_t method,flags;uint32_t matches;int found;} Member;
struct CohAssetZip {CohAssetSource source;CohAssetZipStats stats;size_t arena_used;_Alignas(max_align_t) unsigned char workspace[ZIP_WORK];unsigned char input[ZIP_CHUNK],output[ZIP_CHUNK];Member member[];};
static uint16_t u16(const unsigned char *p){return (uint16_t)(p[0]|(uint16_t)p[1]<<8);}
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static CohStatus read_zip(CohAssetZip *z,uint64_t o,void *p,size_t n){if(o>z->source.size||n>z->source.size-o)return COH_INVALID;CohStatus s=z->source.read_at(z->source.context,o,p,n);z->stats.reads++;if(s==COH_OK)z->stats.read_bytes+=n;return s;}
static int valid_path(const char *p){if(!p||(uintptr_t)p>UINTPTR_MAX-(COH_ASSET_PATH_MAX+1u)||!*p||*p=='/'||*p=='\\')return 0;size_t n=0,start=0;for(;;n++){unsigned char c=(unsigned char)p[n];if(n>COH_ASSET_PATH_MAX||c=='\\'||c==':'||c>126||(c&&c<32))return 0;if(!c||c=='/'){size_t k=n-start;if(!k||(k==1&&p[start]=='.')||(k==2&&p[start]=='.'&&p[start+1]=='.'))return 0;if(!c)return 1;start=n+1;}}}
static voidpf allocate_z(voidpf context,uInt n,uInt bytes){CohAssetZip *z=context;size_t a=_Alignof(max_align_t),o=(z->arena_used+a-1)&~(a-1);if(bytes&&n>SIZE_MAX/bytes)return NULL;size_t size=(size_t)n*bytes;if(o>ZIP_WORK||size>ZIP_WORK-o)return NULL;void *p=z->workspace+o;memset(p,0,size);z->arena_used=o+size;return p;}
static void free_z(voidpf context,voidpf p){(void)context;(void)p;}
static CohStatus member_read(void *context,uint64_t offset,void *dst,size_t count){
    Member *m=context;if(!m||(!dst&&count)||offset>m->bytes||count>m->bytes-offset)return COH_INVALID;
    CohAssetZip *z=m->owner;uint64_t input=0,output=0;uLong crc=crc32(0,NULL,0);CohStatus status=COH_OK;z_stream stream;memset(&stream,0,sizeof stream);
    if(!count)return COH_OK;
    if(m->method==8){z->arena_used=0;stream.zalloc=allocate_z;stream.zfree=free_z;stream.opaque=z;if(inflateInit2(&stream,-MAX_WBITS)!=Z_OK)return COH_LIMIT;}
    int ended=0;
    while(output<m->bytes||(!ended&&m->method==8)){
        size_t produced=0;
        if(m->method==0){produced=m->bytes-(size_t)output;if(produced>ZIP_CHUNK)produced=ZIP_CHUNK;status=read_zip(z,m->data+output,z->output,produced);if(status!=COH_OK)break;}
        else {
            if(!stream.avail_in&&input<m->stored){size_t n=m->stored-(size_t)input;if(n>ZIP_CHUNK)n=ZIP_CHUNK;status=read_zip(z,m->data+input,z->input,n);if(status!=COH_OK)break;input+=n;stream.next_in=z->input;stream.avail_in=(uInt)n;}
            stream.next_out=z->output;stream.avail_out=ZIP_CHUNK;uLong before=stream.total_in;int result=inflate(&stream,Z_NO_FLUSH);produced=ZIP_CHUNK-stream.avail_out;
            if(result==Z_STREAM_END)ended=1;
            else if(result!=Z_OK||(!produced&&stream.total_in==before)){status=COH_INVALID;break;}
            if(produced>m->bytes-output){status=COH_INVALID;break;}
        }
        crc=crc32(crc,z->output,(uInt)produced);
        uint64_t begin=output>offset?output:offset,end=output+produced<offset+count?output+produced:offset+count;
        if(end>begin)memcpy((unsigned char *)dst+(size_t)(begin-offset),z->output+(size_t)(begin-output),(size_t)(end-begin));
        output+=produced;if(ended)break;
    }
    if(status==COH_OK&&(output!=m->bytes||crc!=m->crc||(m->method==8&&(!ended||stream.total_in!=m->stored))))status=COH_INVALID;
    if(m->method==8)inflateEnd(&stream);
    if(status==COH_OK)z->stats.decoded_bytes+=output;
    return status;
}
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+32u:c;}
static int same(const char*a,const char*b){for(size_t i=0;i<=COH_ASSET_PATH_MAX;i++){if(lower((unsigned char)a[i])!=lower((unsigned char)b[i]))return 0;if(!a[i])return 1;}return 0;}
static int query_match(const char *path,const CohAssetZipQuery*q){
 if(q->kind==COH_ZIP_QUERY_PATH)return same(path,q->name);
 const char *base=strrchr(path,'/');if(!base)return 0;
 /* Imported CLIENT and reference archives retain different virtual roots.
  * Original texLoadHeaderProcessor scans texture_library in all data dirs;
  * texFind uses a case-insensitive basename, not one archive/path prefix. */
 const char *prefixes[]={"texture_library/","data/texture_library/","assets/texture_library/"};int root=0;
 for(unsigned r=0;r<3;r++){size_t i=0;for(;prefixes[r][i]&&path[i]&&lower((unsigned char)path[i])==(unsigned char)prefixes[r][i];i++);if(!prefixes[r][i])root=1;}
 if(!root)return 0;
 base++;
 size_t n=strlen(base),wanted=strlen(q->name);if(n!=wanted+8u||!same(base+wanted,".texture"))return 0;
 for(size_t i=0;i<wanted;i++)if(lower((unsigned char)base[i])!=lower((unsigned char)q->name[i]))return 0;
 return 1;
}
static CohStatus open_zip(CohAssetSource source,const CohAssetZipMember *want,const CohAssetZipQuery *query,uint32_t count,CohCancel cancel,CohAssetZip **out){
    if(!out||!source.read_at||source.size<22||source.size>UINT32_MAX||(!want&&!query)||!count||count>ZIP_MEMBERS||!source.generation)return COH_INVALID;
    uintptr_t output=(uintptr_t)out,input=(uintptr_t)(query?(const void*)query:(const void*)want);size_t input_bytes=(size_t)count*(query?sizeof *query:sizeof *want);
    if(output>UINTPTR_MAX-sizeof *out||input>UINTPTR_MAX-input_bytes||(output<input+input_bytes&&input<output+sizeof *out))return COH_INVALID;
    size_t bytes=coh_asset_zip_allocation_bytes(count);CohAssetZip *z=calloc(1,bytes);if(!z)return COH_LIMIT;z->source=source;z->stats.owned_bytes=bytes;z->stats.members=count;CohStatus status=COH_INVALID;
    uint32_t asset_max=query?ZIP_SOURCE_MAX:ZIP_ASSET_MAX;
    for(uint32_t i=0;i<count;i++){
        const char *path=query?query[i].name:want[i].path;uint32_t expected=query?query[i].bytes:want[i].bytes;
        if(!valid_path(path)||(!query&&!expected)||expected>asset_max||(query&&query[i].kind>COH_ZIP_QUERY_TEXTURE)||(query&&query[i].kind==COH_ZIP_QUERY_TEXTURE&&(strchr(path,'/')||strchr(path,'.'))))goto failed;
        uintptr_t span=(uintptr_t)path;size_t length=strlen(path)+1;if(output<span+length&&span<output+sizeof *out)goto failed;
        for(uint32_t j=0;j<i;j++)if(!strcmp(path,query?query[j].name:want[j].path)&&(!query||query[i].kind==query[j].kind))goto failed;
        z->member[i].owner=z;z->member[i].bytes=expected;memcpy(z->member[i].path,path,length);
    }
    if(cancelled(cancel)){status=COH_CANCELLED;goto failed;}
    size_t tail=source.size<65557u?(size_t)source.size:65557u;uint64_t base=source.size-tail;status=read_zip(z,base,z->workspace,tail);if(status!=COH_OK)goto failed;status=COH_INVALID;
    size_t eocd=tail;for(size_t p=tail-22;;p--){if(u32(z->workspace+p)==0x06054b50u&&p+22u+u16(z->workspace+p+20)==tail){eocd=p;break;}if(!p)break;}
    if(eocd==tail)goto failed;
    const unsigned char *end=z->workspace+eocd;uint32_t entries=u16(end+10),central_bytes=u32(end+12),central=u32(end+16);if(u16(end+4)||u16(end+6)||u16(end+8)!=entries||entries==65535u||!entries||(uint64_t)central+central_bytes!=base+eocd)goto failed;
    uint64_t cursor=central,limit=(uint64_t)central+central_bytes;unsigned char header[46];char name[COH_ASSET_PATH_MAX+1];
    for(uint32_t row=0;row<entries;row++){
        if(cancelled(cancel)){status=COH_CANCELLED;goto failed;}
        if(cursor>limit||sizeof header>limit-cursor)goto invalid;
        status=read_zip(z,cursor,header,sizeof header);if(status!=COH_OK)goto failed;
        uint16_t names=u16(header+28),extra=u16(header+30),comment=u16(header+32);uint64_t next=cursor+46u+names+extra+comment;if(u32(header)!=0x02014b50u||next>limit||u16(header+34))goto invalid;
        if(names&&names<=COH_ASSET_PATH_MAX){status=read_zip(z,cursor+46,name,names);if(status!=COH_OK)goto failed;name[names]=0;if(memchr(name,0,names))goto invalid;
            for(uint32_t i=0;i<count;i++)if(query?query_match(name,query+i):!strcmp(name,z->member[i].path)){
                Member *m=&z->member[i];uint16_t flags=u16(header+8),method=u16(header+10);uint32_t decoded=u32(header+24);
                if(query&&query[i].kind==COH_ZIP_QUERY_TEXTURE&&m->found){m->matches++;continue;}
                if(m->found||(flags&~0x0808u)||(method!=0&&method!=8)||!decoded||decoded>asset_max||(m->bytes&&decoded!=m->bytes)||!u32(header+20)||u32(header+20)>asset_max||(method==0&&u32(header+20)!=decoded))goto invalid;
                if(query){m->bytes=decoded;memcpy(m->path,name,(size_t)names+1u);}m->matches=1;
                m->flags=flags;m->method=method;m->crc=u32(header+16);m->stored=u32(header+20);uint32_t local=u32(header+42);unsigned char h[30];if((uint64_t)local+30>central)goto invalid;status=read_zip(z,local,h,sizeof h);if(status!=COH_OK)goto failed;
                if(u32(h)!=0x04034b50u||u16(h+6)!=flags||u16(h+8)!=method||u16(h+26)!=names)goto invalid;
                uint64_t data=(uint64_t)local+30+names+u16(h+28);if(data>central||m->stored>central-data)goto invalid;
                status=read_zip(z,(uint64_t)local+30,z->input,names);if(status!=COH_OK)goto failed;if(memcmp(z->input,name,names))goto invalid;
                if(!(flags&8u)&&(u32(h+14)!=m->crc||u32(h+18)!=m->stored||u32(h+22)!=m->bytes))goto invalid;
                m->data=data;m->found=1;
            }}
        cursor=next;
    }
    if(cursor!=limit)goto invalid;
    for(uint32_t i=0;i<count;i++)if(!query&&!z->member[i].found){status=COH_NOT_FOUND;goto failed;}
    *out=z;return COH_OK;
invalid:status=COH_INVALID;
failed:free(z);return status;
}
CohStatus coh_asset_zip_open(CohAssetSource source,const CohAssetZipMember *want,uint32_t count,CohCancel cancel,CohAssetZip **out){return open_zip(source,want,NULL,count,cancel,out);}
CohStatus coh_asset_zip_open_queries(CohAssetSource source,const CohAssetZipQuery *query,uint32_t count,CohCancel cancel,CohAssetZip **out){return open_zip(source,NULL,query,count,cancel,out);}
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if((an&&(!a||an>UINTPTR_MAX-x))||(bn&&(!b||bn>UINTPTR_MAX-y)))return 0;return !an||!bn||(x<y?an<=y-x:bn<=x-y);}
CohStatus coh_asset_zip_query(const CohAssetZip*z,uint32_t index,const char**path,uint32_t*bytes,uint32_t*matches){
 if(!z||index>=z->stats.members||!path||!bytes||!matches)return COH_INVALID;
 if(!disjoint(path,sizeof *path,z,z->stats.owned_bytes)||!disjoint(bytes,sizeof *bytes,z,z->stats.owned_bytes)||!disjoint(matches,sizeof *matches,z,z->stats.owned_bytes)||!disjoint(path,sizeof *path,bytes,sizeof *bytes)||!disjoint(path,sizeof *path,matches,sizeof *matches)||!disjoint(bytes,sizeof *bytes,matches,sizeof *matches))return COH_INVALID;
 const Member*m=z->member+index;if(!m->found)return COH_NOT_FOUND;
 *path=m->path;*bytes=m->bytes;*matches=m->matches;return COH_OK;
}
CohStatus coh_asset_zip_read(CohAssetZip*z,uint32_t index,void*dst,size_t bytes){
 if(!z||index>=z->stats.members||!dst)return COH_INVALID;
 Member*m=z->member+index;
 if(!m->found)return COH_NOT_FOUND;
 if(bytes!=m->bytes||!disjoint(dst,bytes,z,z->stats.owned_bytes))return COH_INVALID;
 return member_read(m,0,dst,bytes);
}
CohStatus coh_asset_zip_mount(CohAssetZip *z,CohAssetLoader *loader){if(!z||!loader)return COH_INVALID;for(uint32_t i=0;i<z->stats.members;i++){Member *m=&z->member[i];if(!m->found)continue;CohAssetSource source={member_read,m,m->bytes,z->source.generation};CohStatus s=coh_asset_mount_file(loader,m->path,source);if(s!=COH_OK)return s;}return COH_OK;}
void coh_asset_zip_free(CohAssetZip *z){free(z);}
CohAssetZipStats coh_asset_zip_stats(const CohAssetZip *z){CohAssetZipStats s={0};return z?z->stats:s;}

size_t coh_asset_zip_allocation_bytes(uint32_t count){return count&&count<=ZIP_MEMBERS?sizeof(CohAssetZip)+(size_t)count*sizeof(Member):0;}
