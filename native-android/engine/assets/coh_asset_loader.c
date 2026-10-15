#include "coh_asset_loader.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <math.h>
#include <zlib.h>
typedef struct { size_t bytes;
 } Allocation;

struct CohAssetBlob { uint8_t *data;
 size_t size;
 uint32_t refs,index;
 uint64_t used;
 CohAssetId id;
 };

typedef struct {
    char *name,*key;
 CohAssetInfo info;
 uint32_t source,previous;

    CohAssetBlob blob;

} Entry;

struct CohAssetLoader {
    CohAssetLimits limits;
 CohAssetStats stats;
 Entry *entries;

    CohAssetSource *sources;
 uint32_t *hash,hash_count;
 uint64_t clock;

};

static uint16_t u16(const uint8_t *p){return (uint16_t)((uint16_t)p[0]|(uint16_t)p[1]<<8);
}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static float f32(const uint8_t *p){uint32_t n=u32(p);
float v;
memcpy(&v,&n,4);
return v;
}
static int range64(uint64_t n,uint64_t o,uint64_t s){return o<=n&&s<=n-o;
}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);
}
static void *take(CohAssetLoader *l,size_t n){
    if(n>SIZE_MAX-sizeof(Allocation)||n+sizeof(Allocation)>l->limits.total_bytes-l->stats.allocated_bytes)return NULL;

    Allocation *a=calloc(1,sizeof(*a)+n);
if(!a)return NULL;
a->bytes=n+sizeof(*a);

    l->stats.allocated_bytes+=a->bytes;
if(l->stats.allocated_bytes>l->stats.peak_allocated_bytes)l->stats.peak_allocated_bytes=l->stats.allocated_bytes;

    return a+1;

}
static void drop(CohAssetLoader *l,void *p){if(p){Allocation *a=(Allocation*)p-1;
l->stats.allocated_bytes-=a->bytes;
free(a);
}}
static voidpf ztake(voidpf c,uInt n,uInt size){if(size&&n>SIZE_MAX/size)return NULL;
return take(c,(size_t)n*size);
}
static void zdrop(voidpf c,voidpf p){drop(c,p);
}
static CohStatus reject(CohAssetLoader *l,CohStatus s){if(l)l->stats.rejections++;
return s;
}
static CohStatus read_source(CohAssetLoader *l,CohAssetSource *s,uint64_t off,void *dst,size_t n){
    if(!range64(s->size,off,n))return COH_INVALID;

    if(!n)return COH_OK;

    CohStatus r=s->read_at(s->context,off,dst,n);
l->stats.reads++;
if(r==COH_OK)l->stats.read_bytes+=n;
return r;

}
static CohStatus canonical(const char *path,char key[COH_ASSET_PATH_MAX+1]){
    if(!path||!path[0]||path[0]=='/'||path[0]=='\\')return COH_INVALID;

    size_t out=0,component=0;

    for(size_t i=0;i<=COH_ASSET_PATH_MAX;i++){
        unsigned char c=(unsigned char)path[i];

        if(c=='\\')c='/';

        if(!c||c=='/'){
            if(component){size_t start=out-component;
if((component==1&&key[start]=='.')||(component==2&&key[start]=='.'&&key[start+1]=='.'))return COH_INVALID;
component=0;
}
            if(!c){if(out&&key[out-1]=='/')out--;
key[out]=0;
return out?COH_OK:COH_INVALID;
}
            if(out&&key[out-1]!='/')key[out++]='/';

        } else {
            if(c<32||c==127||c==':'||out>=COH_ASSET_PATH_MAX)return COH_INVALID;

            key[out++]=(char)(c>='A'&&c<='Z'?c+32:c);
component++;

        }
    }
    return COH_LIMIT;

}
static uint32_t hashof(const char *p){uint32_t h=2166136261u;
for(;*p;p++)h=(h^(uint8_t)*p)*16777619u;
return h;
}
static uint32_t *slot_for(CohAssetLoader *l,const char *key){
    uint32_t n=hashof(key)&(l->hash_count-1);

    while(l->hash[n]&&strcmp(l->entries[l->hash[n]-1].key,key))n=(n+1)&(l->hash_count-1);

    return l->hash+n;

}
static void rebuild(CohAssetLoader *l){
    memset(l->hash,0,l->hash_count*sizeof(*l->hash));

    for(uint32_t i=0;i<l->stats.indexed_entries;i++){Entry *e=l->entries+i;
uint32_t *s=slot_for(l,e->key);
e->previous=*s;
*s=i+1;
}
}
static void undo(CohAssetLoader *l,uint32_t count){
    while(l->stats.indexed_entries>count){Entry *e=&l->entries[--l->stats.indexed_entries];
drop(l,e->name);
memset(e,0,sizeof(*e));
}rebuild(l);

}
static CohStatus append(CohAssetLoader *l,const char *name,CohAssetInfo info,uint32_t source){
    char key[COH_ASSET_PATH_MAX+1];
CohStatus r=canonical(name,key);
if(r!=COH_OK)return r;

    if(l->stats.indexed_entries==l->limits.entries)return COH_LIMIT;

    uint32_t *slot=slot_for(l,key);

    for(uint32_t i=*slot;i;i=l->entries[i-1].previous)if(l->entries[i-1].info.id.generation==info.id.generation)return COH_INVALID;

    size_t a=strlen(name)+1,b=strlen(key)+1;
char *p=take(l,a+b);
if(!p)return COH_LIMIT;

    memcpy(p,name,a);
memcpy(p+a,key,b);
uint32_t index=l->stats.indexed_entries++;

    Entry *e=l->entries+index;
e->name=p;
e->key=p+a;
e->info=info;
e->info.id.path=e->name;
e->source=source;
e->previous=*slot;
e->blob.index=index;
e->blob.id=e->info.id;
*slot=index+1;
return COH_OK;

}
CohStatus coh_asset_create(const CohAssetLimits *limits,CohAssetLoader **out){
    if(!limits||!out||!limits->entries||limits->entries>(1u<<22)||!limits->sources||limits->sources>limits->entries||!limits->cache_entries||limits->cache_entries>limits->entries||!limits->cache_bytes||!limits->max_asset_bytes||!limits->max_stored_bytes||limits->total_bytes<sizeof(CohAssetLoader))return COH_INVALID;

    CohAssetLoader *l=calloc(1,sizeof(*l));
if(!l)return COH_LIMIT;
l->limits=*limits;
l->stats.allocated_bytes=sizeof(*l);
l->stats.peak_allocated_bytes=sizeof(*l);

    uint32_t n=1;
while(n<limits->entries*2)n*=2;
l->hash_count=n;

    l->entries=take(l,(size_t)limits->entries*sizeof(Entry));
l->sources=take(l,(size_t)limits->sources*sizeof(CohAssetSource));
l->hash=take(l,(size_t)n*sizeof(uint32_t));

    if(!l->entries||!l->sources||!l->hash){drop(l,l->entries);
drop(l,l->sources);
drop(l,l->hash);
free(l);
return COH_LIMIT;
}
    *out=l;
return COH_OK;

}
CohAssetStats coh_asset_stats(const CohAssetLoader *l){CohAssetStats s={0};
return l?l->stats:s;
}
static void evict(CohAssetLoader *l,Entry *e){if(e->blob.data){l->stats.resident_bytes-=e->blob.size;
l->stats.resident_entries--;
l->stats.evictions++;
drop(l,e->blob.data);
e->blob.data=NULL;
e->blob.size=0;
}}
void coh_asset_trim(CohAssetLoader *l){if(l)for(uint32_t i=0;i<l->stats.indexed_entries;i++)if(!l->entries[i].blob.refs)evict(l,l->entries+i);
}
CohStatus coh_asset_destroy(CohAssetLoader **p){
    if(!p||!*p)return COH_OK;
CohAssetLoader *l=*p;
if(l->stats.pinned_blobs)return COH_STATE;

    for(uint32_t i=0;i<l->stats.indexed_entries;i++){drop(l,l->entries[i].name);
drop(l,l->entries[i].blob.data);
}
    drop(l,l->entries);
drop(l,l->sources);
drop(l,l->hash);
free(l);
*p=NULL;
return COH_OK;

}
CohStatus coh_asset_mount_file(CohAssetLoader *l,const char *path,CohAssetSource src){
    if(!l||!src.read_at||!src.generation||src.size>UINT32_MAX)return reject(l,COH_INVALID);

    if(l->stats.mounted_sources==l->limits.sources)return reject(l,COH_LIMIT);

    CohAssetInfo info;
memset(&info,0,sizeof(info));
info.id.generation=src.generation;
info.decoded_bytes=info.stored_bytes=(uint32_t)src.size;

    CohStatus r=append(l,path,info,l->stats.mounted_sources);
if(r!=COH_OK)return reject(l,r);

    l->sources[l->stats.mounted_sources++]=src;
return COH_OK;

}
/* DataPool byte counts are validated before allocation;
 header pool is walked
 * without retaining it. Names have independent bounded terminators. */
static CohStatus pool(CohAssetLoader *l,CohAssetSource *s,uint64_t *off,uint32_t flag,uint32_t *count,uint8_t **data,uint32_t *size){
    uint8_t h[12];
CohStatus r=read_source(l,s,*off,h,12);
if(r!=COH_OK)return r;

    uint32_t n=u32(h+4),bytes=u32(h+8);
if(u32(h)!=flag||n>l->limits.entries||n>bytes/4||!range64(s->size,*off+12,bytes))return COH_INVALID;

    *off+=12;
uint8_t *p=take(l,bytes?bytes:1);
if(!p)return COH_LIMIT;

    r=read_source(l,s,*off,p,bytes);
if(r!=COH_OK){drop(l,p);
return r;
}
    size_t pos=0;
for(uint32_t i=0;i<n;i++){if(pos>bytes||bytes-pos<4){drop(l,p);
return COH_INVALID;
}uint32_t len=u32(p+pos);
pos+=4;
if(len>bytes-pos){drop(l,p);
return COH_INVALID;
}pos+=len;
}
    if(pos!=bytes){drop(l,p);
return COH_INVALID;
}*off+=bytes;
*count=n;
*data=p;
*size=bytes;
return COH_OK;

}
CohStatus coh_asset_mount_pigg(CohAssetLoader *l,CohAssetSource src,CohCancel cancel){
    if(!l||!src.read_at||!src.generation)return reject(l,COH_INVALID);

    if(cancelled(cancel))return COH_CANCELLED;

    if(l->stats.mounted_sources==l->limits.sources)return reject(l,COH_LIMIT);

    uint8_t h[16];
CohStatus r=read_source(l,&src,0,h,16);
if(r!=COH_OK)return reject(l,r);

    if(u32(h)!=0x123)return reject(l,COH_UNSUPPORTED);

    if(u16(h+6)>2)return reject(l,COH_UNSUPPORTED);

    uint32_t count=u32(h+12);
uint16_t ah=u16(h+8),fh=u16(h+10);

    if(ah<16||fh<48||count>l->limits.entries-l->stats.indexed_entries||!range64(src.size,ah,(uint64_t)fh*count))return reject(l,COH_INVALID);

    uint64_t off=(uint64_t)ah+(uint64_t)fh*count;
uint8_t *names=NULL,*headers=NULL;
uint32_t nn,ns,hn,hs;

    r=pool(l,&src,&off,0x6789,&nn,&names,&ns);
if(r!=COH_OK)goto end;

    r=pool(l,&src,&off,0x9abc,&hn,&headers,&hs);
if(r!=COH_OK)goto end;

    if(nn!=count){r=COH_INVALID;
goto end;
}
    uint32_t start=l->stats.indexed_entries;
size_t pos=0;

    /* Original writer associates name_id with record order;
 still validate IDs
     * and support arbitrary valid name_id ordering rather than assuming it. */
    uint32_t *nameoff=take(l,(size_t)(count?count:1)*sizeof(uint32_t));
if(!nameoff){r=COH_LIMIT;
goto end;
}
    for(uint32_t i=0;i<count;i++){uint32_t len=u32(names+pos);
pos+=4;
nameoff[i]=(uint32_t)pos;

        if(!len||len>COH_ASSET_PATH_MAX+1||names[pos+len-1]||memchr(names+pos,0,len-1)){r=COH_INVALID;
goto rollback;
}pos+=len;
}
    for(uint32_t i=0;i<count;i++){
        if(cancelled(cancel)){r=COH_CANCELLED;
goto rollback;
}
        uint8_t rec[48];
r=read_source(l,&src,(uint64_t)ah+(uint64_t)i*fh,rec,48);
if(r!=COH_OK)goto rollback;

        uint32_t name=u32(rec+4),pack=u32(rec+44),size=u32(rec+8),data=u32(rec+16),header=u32(rec+24);

        if(u32(rec)!=0x3456||name>=count||u32(rec+20)|| (header!=UINT32_MAX&&header>=hn)|| (pack&&!size)||data<off||!range64(src.size,data,pack?pack:size)){r=COH_INVALID;
goto rollback;
}
        CohAssetInfo info;
memset(&info,0,sizeof(info));
info.id.generation=src.generation;
info.offset=data;
info.decoded_bytes=size;
info.stored_bytes=pack?pack:size;
info.timestamp=u32(rec+12);
info.compressed=pack!=0;
memcpy(info.md5,rec+28,16);

        r=append(l,(const char*)names+nameoff[name],info,l->stats.mounted_sources);
if(r!=COH_OK)goto rollback;

    }
    l->sources[l->stats.mounted_sources++]=src;
r=COH_OK;

rollback:
    if(r!=COH_OK)undo(l,start);
drop(l,nameoff);

end:
    drop(l,names);
drop(l,headers);
return r==COH_OK?r:reject(l,r);

}
static Entry *find(CohAssetLoader *l,CohAssetId id){
    char key[COH_ASSET_PATH_MAX+1];
if(canonical(id.path,key)!=COH_OK)return NULL;

    uint32_t i=*slot_for(l,key);
while(i){Entry *e=l->entries+i-1;
if(!id.generation||e->info.id.generation==id.generation)return e;
i=e->previous;
}return NULL;

}
CohStatus coh_asset_lookup(CohAssetLoader *l,CohAssetId id,CohAssetInfo *out){if(!l||!out)return COH_INVALID;
Entry *e=find(l,id);
if(!e)return COH_NOT_FOUND;
*out=e->info;
return COH_OK;
}
static CohStatus reserve(CohAssetLoader *l,size_t size){
    if(size>l->limits.cache_bytes)return COH_LIMIT;

    while(l->stats.resident_bytes>l->limits.cache_bytes-size||l->stats.resident_entries>=l->limits.cache_entries){
        Entry *oldest=NULL;
for(uint32_t i=0;i<l->stats.indexed_entries;i++){Entry *e=l->entries+i;
if(e->blob.data&&!e->blob.refs&&(!oldest||e->blob.used<oldest->blob.used))oldest=e;
}
        if(!oldest)return COH_LIMIT;
evict(l,oldest);

    }return COH_OK;

}
static CohStatus inflate_source(CohAssetLoader *l,CohAssetSource *src,CohAssetInfo *info,uint8_t *dst,CohCancel cancel){
    z_stream z;
memset(&z,0,sizeof(z));
z.zalloc=ztake;
z.zfree=zdrop;
z.opaque=l;

    if(inflateInit(&z)!=Z_OK)return COH_LIMIT;

    uint8_t input[4096],overflow;
uint32_t at=0;
int zr=Z_OK;
CohStatus r=COH_INVALID;

    z.next_out=dst;
z.avail_out=info->decoded_bytes;

    while(zr!=Z_STREAM_END){
        if(cancelled(cancel)){r=COH_CANCELLED;
break;
}
        if(!z.avail_in&&at<info->stored_bytes){uint32_t n=info->stored_bytes-at;
if(n>sizeof(input))n=sizeof(input);
r=read_source(l,src,info->offset+at,input,n);
if(r!=COH_OK)break;
at+=n;
z.next_in=input;
z.avail_in=n;
}
        if(!z.avail_out){z.next_out=&overflow;
z.avail_out=1;
}
        uLong beforein=z.total_in,beforeout=z.total_out;
zr=inflate(&z,Z_NO_FLUSH);

        if(z.total_out>info->decoded_bytes){r=COH_INVALID;
break;
}
        if(zr==Z_STREAM_END){r=(z.total_out==info->decoded_bytes&&z.total_in==info->stored_bytes)?COH_OK:COH_INVALID;
break;
}
        if(zr!=Z_OK||(z.total_in==beforein&&z.total_out==beforeout)){r=zr==Z_MEM_ERROR?COH_LIMIT:COH_INVALID;
break;
}
    }
    inflateEnd(&z);
return r;

}
CohStatus coh_asset_acquire(CohAssetLoader *l,CohAssetId id,CohCancel cancel,const CohAssetBlob **out){
    if(!l||!out)return COH_INVALID;
if(cancelled(cancel))return COH_CANCELLED;
Entry *e=find(l,id);
if(!e)return COH_NOT_FOUND;

    if(e->blob.data){if(e->blob.refs==UINT32_MAX)return COH_LIMIT;
l->stats.cache_hits++;
if(!e->blob.refs)l->stats.pinned_blobs++;
e->blob.refs++;
e->blob.used=++l->clock;
*out=&e->blob;
return COH_OK;
}
    l->stats.cache_misses++;
if(e->info.decoded_bytes>l->limits.max_asset_bytes||e->info.stored_bytes>l->limits.max_stored_bytes)return reject(l,COH_LIMIT);

    CohStatus r=reserve(l,e->info.decoded_bytes);
if(r!=COH_OK)return reject(l,r);

    uint8_t *data=take(l,e->info.decoded_bytes?e->info.decoded_bytes:1);
if(!data)return reject(l,COH_LIMIT);

    CohAssetSource *src=l->sources+e->source;

    if(e->info.compressed)r=inflate_source(l,src,&e->info,data,cancel);

    else {uint32_t at=0;
r=COH_OK;
while(at<e->info.decoded_bytes){if(cancelled(cancel)){r=COH_CANCELLED;
break;
}size_t n=e->info.decoded_bytes-at;
if(n>65536)n=65536;
r=read_source(l,src,e->info.offset+at,data+at,n);
if(r!=COH_OK)break;
at+=(uint32_t)n;
}}
    if(r!=COH_OK){drop(l,data);
return reject(l,r);
}
    e->blob.data=data;
e->blob.size=e->info.decoded_bytes;
e->blob.refs=1;
e->blob.used=++l->clock;
l->stats.resident_entries++;
l->stats.pinned_blobs++;
l->stats.resident_bytes+=e->blob.size;

    if(l->stats.resident_bytes>l->stats.peak_resident_bytes)l->stats.peak_resident_bytes=l->stats.resident_bytes;
*out=&e->blob;
return COH_OK;

}
void coh_asset_release(CohAssetLoader *l,const CohAssetBlob *b){
    if(!l||!b||!l->stats.indexed_entries)return;
    /* Entry storage never moves. Validate the opaque address before touching it. */
    uintptr_t first=(uintptr_t)&l->entries[0].blob, address=(uintptr_t)b;
    if(address<first)return;
    uintptr_t difference=address-first;
    if(difference%sizeof(Entry))return;
    size_t index=difference/sizeof(Entry);
    if(index>=l->stats.indexed_entries)return;
    CohAssetBlob *p=&l->entries[index].blob;
    if(p->refs&&!--p->refs)l->stats.pinned_blobs--;
}

CohBytes coh_asset_bytes(const CohAssetBlob *b){CohBytes r={NULL,0};
if(b){r.data=b->data;
r.size=b->size;
}return r;
}
CohAssetId coh_asset_identity(const CohAssetBlob *b){CohAssetId r={NULL,0};
return b?b->id:r;
}
CohStatus coh_asset_resolve(CohAssetLoader *l,CohAssetId root,CohAssetDependencies deps,void *ctx,uint32_t cap,CohCancel cancel,uint32_t *visited){
    if(!l||!deps||!visited||!cap||cap>l->limits.entries)return COH_INVALID;

    uint32_t *queue=take(l,(size_t)cap*sizeof(uint32_t));
CohAssetId *ids=take(l,(size_t)cap*sizeof(CohAssetId));
if(!queue||!ids){drop(l,queue);
drop(l,ids);
return COH_LIMIT;
}
    Entry *first=find(l,root);
CohStatus r=COH_NOT_FOUND;
uint32_t head=0,count=0;

    if(!first)goto done;
queue[count++]=(uint32_t)(first-l->entries);

    while(head<count){
        if(cancelled(cancel)){r=COH_CANCELLED;
goto done;
}Entry *e=l->entries+queue[head];
const CohAssetBlob *blob=NULL;

        r=coh_asset_acquire(l,e->info.id,cancel,&blob);
if(r!=COH_OK)goto done;

        size_t n=0;
r=deps(ctx,e->info.id,coh_asset_bytes(blob),ids,cap,&n);
coh_asset_release(l,blob);
if(r!=COH_OK)goto done;

        if(n>cap){r=COH_LIMIT;
goto done;
}
        for(size_t j=0;j<n;j++){
            Entry *d=find(l,ids[j]);
if(!d){r=COH_NOT_FOUND;
goto done;
}uint32_t k=(uint32_t)(d-l->entries);
size_t a=0;
while(a<count&&queue[a]!=k)a++;

            if(a==count){if(count==cap){r=COH_LIMIT;
goto done;
}queue[count++]=k;
}
        }head++;

    }r=COH_OK;

done:
    *visited=head;
drop(l,queue);
drop(l,ids);
return r==COH_OK?r:reject(l,r);

}
CohStatus coh_asset_texture(CohBytes b,CohAssetTexture *out){
    if(!b.data||!out)return COH_INVALID;
CohAssetTexture t;
memset(&t,0,sizeof(t));
t.dds=b;

    if(b.size>=4&&memcmp(b.data,"DDS ",4)==0){CohDdsMip m;
int r=coh_dds_mip(b.data,b.size,0,&m);
if(r)return r==2?COH_UNSUPPORTED:COH_INVALID;
t.width=m.width;
t.height=m.height;
*out=t;
return COH_OK;
}
    if(b.size<33)return COH_INVALID;
uint32_t hs=u32(b.data),size=u32(b.data+4);

    if(hs<33||hs>b.size||size!=b.size-hs||hs>COH_ASSET_PATH_MAX+32+65536)return COH_INVALID;

    if(memcmp(b.data+29,"TEX",3)&&memcmp(b.data+29,"TX2",3))return COH_UNSUPPORTED;

    if(!memchr(b.data+32,0,hs-32))return COH_INVALID;

    t.name=(const char*)b.data+32;
t.flags=u32(b.data+16);
t.fade[0]=f32(b.data+20);
t.fade[1]=f32(b.data+24);
t.alpha=b.data[28];
t.dds.data=b.data+hs;
t.dds.size=size;

    if(!isfinite(t.fade[0])||!isfinite(t.fade[1]))return COH_INVALID;

    CohDdsMip m;
int r=coh_dds_mip(t.dds.data,t.dds.size,0,&m);
if(r)return r==2?COH_UNSUPPORTED:COH_INVALID;

    t.width=m.width;
t.height=m.height;
if(t.width!=u32(b.data+8)||t.height!=u32(b.data+12))return COH_INVALID;
*out=t;
return COH_OK;

}
CohStatus coh_asset_texture_rgba(const CohAssetTexture *t,uint32_t level,uint8_t *out,size_t n){if(!t)return COH_INVALID;
int r=coh_dds_rgba(t->dds.data,t->dds.size,level,out,n);
return r==0?COH_OK:r==2?COH_UNSUPPORTED:COH_INVALID;
}
CohStatus coh_asset_animation(CohBytes b,CohAnimHeader *out){
    CohAnimHeader h;
if(!out||coh_anim_header(b.data,b.size,&h))return COH_INVALID;

    uint8_t seen[100]={0};
for(uint32_t i=0;i<h.bone_count;i++){CohBoneView v;
int r=coh_anim_bone(b.data,b.size,i,&v);
if(r)return r==2?COH_UNSUPPORTED:COH_INVALID;
if(seen[v.id])return COH_INVALID;
seen[v.id]=1;
}
    *out=h;
return COH_OK;

}
CohStatus coh_asset_sound(CohBytes b,CohAssetSound *out){
    if(!out||!b.data||b.size<27||memcmp(b.data,"OggS",4)||b.data[4]||!(b.data[5]&2)||b.data[5]&1)return COH_INVALID;

    uint8_t segments=b.data[26];
if(!segments||b.size<(size_t)27+segments)return COH_INVALID;
size_t packet=0;
unsigned i=0;

    for(;i<segments;i++){packet+=b.data[27+i];
if(b.data[27+i]<255)break;
}
    if(i==segments||packet<30||packet>b.size-27-segments)return COH_INVALID;

    const uint8_t *p=b.data+27+segments;
if(p[0]!=1||memcmp(p+1,"vorbis",6))return COH_UNSUPPORTED;

    if(u32(p+7)||!p[11]||p[11]>8||u32(p+12)<8000||u32(p+12)>192000||!(p[29]&1))return COH_INVALID;

    CohAssetSound s={u32(p+12),p[11],b};
*out=s;
return COH_OK;

}
