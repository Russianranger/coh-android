#include "../coh_asset_loader.h"
#include "../coh_asset_geo.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <inttypes.h>
#include <math.h>
static unsigned checks,files,geo_models,streams,textures,animations,sounds,fuzz_cases;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
typedef struct { uint8_t *data;size_t size; } Mem;
static CohStatus readmem(void *ctx,uint64_t o,void *dst,size_t n){Mem *m=ctx;if(o>m->size||n>m->size-o)return COH_IO;memcpy(dst,m->data+(size_t)o,n);return COH_OK;}
static Mem load(const char *p){Mem m={0};FILE *f=fopen(p,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>=0);m.size=(size_t)n;rewind(f);m.data=malloc(m.size?m.size:1);CHECK(m.data);CHECK(fread(m.data,1,m.size,f)==m.size);CHECK(!fclose(f));return m;}
static CohAssetLimits limits(void){CohAssetLimits c={4u<<20,512u<<10,256u<<10,256u<<10,256,128,4};return c;}
static int yes(void *p){(void)p;return 1;}
static CohStatus dependencies(void *ctx,CohAssetId id,CohBytes b,CohAssetId *out,size_t cap,size_t *count){(void)b;if(!cap)return COH_LIMIT;out[0]=(CohAssetId){ctx?(const char*)ctx:(!strcmp(id.path,"test/a")?"test/b":"test/a"),0};*count=1;return COH_OK;}
static void typed(CohBytes b,const char *virtual_path){
    size_t len=strlen(virtual_path);
    if(len>=4&&!strcmp(virtual_path+len-4,".geo")){
        size_t need=0;CHECK(coh_asset_geo_workspace(b,&need)==COH_OK);CHECK(need<4u<<20);uint8_t *w=malloc(need);CHECK(w);CohAssetGeo g;memset(&g,0,sizeof(g));CHECK(coh_asset_geo_open(b,w,need,4096,&g)==COH_OK);
        CHECK(coh_asset_geo_open(b,w,need-1,4096,&g)==COH_LIMIT);
        for(uint32_t i=0;i<g.model_count;i++){
            CohAssetGeoModel m;CHECK(coh_asset_geo_model(&g,i,&m)==COH_OK);CHECK(m.name&&m.vertex_count&&m.triangle_count);geo_models++;
            for(uint32_t j=0;j<m.material_count;j++){CohAssetGeoMaterial p;CHECK(coh_asset_geo_material(&g,&m,j,&p)==COH_OK);CHECK(p.texture_name);}
            for(uint32_t j=0;j<m.pack_count;j++){
                size_t bytes=m.packs[j].unpacked_bytes;CHECK(bytes<=8u<<20);uint8_t *stream=malloc(bytes?bytes:1);CHECK(stream);uint8_t scratch[65536];size_t actual=SIZE_MAX;
                CHECK(coh_asset_geo_stream(&g,&m,j,stream,bytes,scratch,sizeof(scratch),&actual)==COH_OK);CHECK(bytes==actual);streams++;
                if(j<=3&&bytes){size_t count=j?m.vertex_count:m.triangle_count,stride=j==3?2:3;CHECK(count<1u<<20);void *decoded=malloc(count*stride*4);CHECK(decoded);CohBytes input={stream,bytes};CohStatus s=j?coh_asset_delta_floats(input,(uint32_t)count,(uint32_t)stride,decoded,count*stride):coh_asset_delta_indices(input,(uint32_t)count,decoded,count*stride);CHECK(s==COH_OK);if(!j)for(size_t k=0;k<count*stride;k++)CHECK(((uint32_t*)decoded)[k]<m.vertex_count);free(decoded);}
                free(stream);
            }
        }free(w);
    }else if(len>=8&&!strcmp(virtual_path+len-8,".texture")){
        CohAssetTexture t;CHECK(coh_asset_texture(b,&t)==COH_OK);CHECK(t.width&&t.height);size_t n=(size_t)t.width*t.height*4;uint8_t *rgba=malloc(n);CHECK(rgba);CHECK(coh_asset_texture_rgba(&t,0,rgba,n)==COH_OK);free(rgba);textures++;
    }else if(len>=5&&!strcmp(virtual_path+len-5,".anim")){
        CohAnimHeader h;CHECK(coh_asset_animation(b,&h)==COH_OK);CHECK(h.bone_count);animations++;
    }else if(len>=4&&!strcmp(virtual_path+len-4,".ogg")){
        CohAssetSound s;CHECK(coh_asset_sound(b,&s)==COH_OK);CHECK(s.channels&&s.sample_rate);sounds++;
    }
}
static void malformed_typed(CohBytes b,const char *path){
    size_t len=strlen(path);
    for(size_t n=0;n<b.size;n+=b.size/64+1){
        CohBytes shorted={b.data,n};
        if(len>=4&&!strcmp(path+len-4,".geo")){
            size_t need=0;
            if(coh_asset_geo_workspace(shorted,&need)==COH_OK&&need<(4u<<20)){
                uint8_t *w=malloc(need);CHECK(w);CohAssetGeo g;
                (void)coh_asset_geo_open(shorted,w,need,4096,&g);free(w);
            }
        }else if(len>=8&&!strcmp(path+len-8,".texture")){
            CohAssetTexture t;(void)coh_asset_texture(shorted,&t);
        }else if(len>=5&&!strcmp(path+len-5,".anim")){
            CohAnimHeader a;(void)coh_asset_animation(shorted,&a);
        }else if(len>=4&&!strcmp(path+len-4,".ogg")){
            CohAssetSound a;(void)coh_asset_sound(shorted,&a);
        }
        fuzz_cases++;
    }
}

int main(int argc,char **argv){
    CHECK(argc==3);Mem archive=load(argv[1]);CohAssetSource source={readmem,&archive,archive.size,1};CohAssetLimits c=limits();CohAssetLoader *l=NULL;CHECK(coh_asset_create(&c,&l)==COH_OK);size_t base=coh_asset_stats(l).allocated_bytes;
    CHECK(coh_asset_mount_pigg(l,source,(CohCancel){yes,NULL})==COH_CANCELLED);CHECK(!coh_asset_stats(l).indexed_entries);
    CHECK(coh_asset_mount_pigg(l,source,(CohCancel){0})==COH_OK);CHECK(coh_asset_stats(l).resident_entries==0);uint32_t indexed=coh_asset_stats(l).indexed_entries;size_t indexed_bytes=coh_asset_stats(l).allocated_bytes;
    CHECK(coh_asset_mount_pigg(l,source,(CohCancel){0})==COH_INVALID);CHECK(coh_asset_stats(l).indexed_entries==indexed);CHECK(coh_asset_stats(l).allocated_bytes==indexed_bytes);
    const CohAssetBlob *a=NULL,*b=NULL;CHECK(coh_asset_acquire(l,(CohAssetId){"TEST\\\\A",0},(CohCancel){0},&a)==COH_OK);CHECK(coh_asset_identity(a).generation==1);CHECK(!strcmp(coh_asset_identity(a).path,"test/a"));CHECK(coh_asset_destroy(&l)==COH_STATE);
    CHECK(coh_asset_acquire(l,(CohAssetId){"test/a",1},(CohCancel){0},&b)==COH_OK);CHECK(a==b);coh_asset_release(l,a);CHECK(coh_asset_stats(l).pinned_blobs==1);coh_asset_release(l,b);CHECK(!coh_asset_stats(l).pinned_blobs);
    uint32_t visited=0;CHECK(coh_asset_resolve(l,(CohAssetId){"test/a",0},dependencies,NULL,4,(CohCancel){0},&visited)==COH_OK);CHECK(visited==2);CHECK(coh_asset_resolve(l,(CohAssetId){"test/a",0},dependencies,NULL,1,(CohCancel){0},&visited)==COH_LIMIT);CHECK(coh_asset_resolve(l,(CohAssetId){"test/a",0},dependencies,"missing",4,(CohCancel){0},&visited)==COH_NOT_FOUND);CHECK(!coh_asset_stats(l).pinned_blobs);
    CHECK(coh_asset_acquire(l,(CohAssetId){"test/corrupt",0},(CohCancel){0},&a)==COH_INVALID);
    CHECK(coh_asset_acquire(l,(CohAssetId){"test/trailing",0},(CohCancel){0},&a)==COH_INVALID);
    const CohAssetBlob *pins[5]={0};
    for(unsigned i=0;i<4;i++){char key[32];snprintf(key,sizeof(key),"test/p%u",i);CHECK(coh_asset_acquire(l,(CohAssetId){key,0},(CohCancel){0},&pins[i])==COH_OK);}
    CHECK(coh_asset_acquire(l,(CohAssetId){"test/p4",0},(CohCancel){0},&pins[4])==COH_LIMIT);
    for(unsigned i=0;i<4;i++)coh_asset_release(l,pins[i]);
    coh_asset_trim(l);CHECK(coh_asset_stats(l).allocated_bytes==indexed_bytes);
    for(unsigned i=0;i<1000;i++){
        CHECK(coh_asset_acquire(l,(CohAssetId){i%2?"test/a":"test/b",0},(CohCancel){0},&a)==COH_OK);
        coh_asset_release(l,a);coh_asset_trim(l);
        CHECK(coh_asset_stats(l).allocated_bytes==indexed_bytes);
    }
    uint8_t overlay[]={9,8,7};Mem ov={overlay,sizeof(overlay)};CohAssetSource newer={readmem,&ov,sizeof(overlay),2};CHECK(coh_asset_mount_file(l,"test/a",newer)==COH_OK);CHECK(coh_asset_acquire(l,(CohAssetId){"test/a",0},(CohCancel){0},&a)==COH_OK);CHECK(coh_asset_bytes(a).size==sizeof(overlay));CHECK(!memcmp(coh_asset_bytes(a).data,overlay,sizeof(overlay)));coh_asset_release(l,a);CHECK(coh_asset_acquire(l,(CohAssetId){"test/a",1},(CohCancel){0},&a)==COH_OK);CHECK(coh_asset_identity(a).generation==1);coh_asset_release(l,a);
    const char *invalid[]={"../a","a/../b","/absolute","C:\\disk",".","a/./b","a/\001/b",""};for(size_t i=0;i<sizeof(invalid)/sizeof(*invalid);i++)CHECK(coh_asset_mount_file(l,invalid[i],newer)==COH_INVALID);
    Mem originals[128];memset(originals,0,sizeof(originals));
    FILE *manifest=fopen(argv[2],"rb");CHECK(manifest);char line[4096];
    while(fgets(line,sizeof(line),manifest)){
        line[strcspn(line,"\r\n")]=0;char *disk=strchr(line,'|');CHECK(disk);*disk++=0;CHECK(files<128);originals[files]=load(disk);Mem original=originals[files];CohAssetSource loose={readmem,&originals[files],original.size,3};
        CHECK(coh_asset_acquire(l,(CohAssetId){line,1},(CohCancel){0},&a)==COH_OK);CohBytes data=coh_asset_bytes(a);CHECK(data.size==original.size);CHECK(!memcmp(data.data,original.data,data.size));typed(data,line);malformed_typed(data,line);coh_asset_release(l,a);
        CHECK(coh_asset_mount_file(l,line,loose)==COH_OK);CHECK(coh_asset_acquire(l,(CohAssetId){line,3},(CohCancel){0},&a)==COH_OK);CHECK(coh_asset_bytes(a).size==original.size);CHECK(!memcmp(coh_asset_bytes(a).data,original.data,original.size));coh_asset_release(l,a);coh_asset_trim(l);files++;

    }CHECK(!fclose(manifest));coh_asset_trim(l);CHECK(!coh_asset_stats(l).resident_entries);CHECK(!coh_asset_stats(l).resident_bytes);
    CohAssetStats stats=coh_asset_stats(l);CHECK(stats.allocated_bytes<=c.total_bytes);CHECK(stats.peak_allocated_bytes<=c.total_bytes);CHECK(stats.peak_resident_bytes<=c.cache_bytes);CHECK(stats.evictions>0);CHECK(stats.cache_hits>0);CHECK(coh_asset_destroy(&l)==COH_OK);CHECK(!l);CHECK(coh_asset_destroy(&l)==COH_OK);
    /* Hostile short headers and record mutations use the actual general parser. */
    uint8_t *bad=malloc(archive.size);CHECK(bad);uint32_t random=0x12345678;
    for(unsigned i=0;i<1000;i++){
        memcpy(bad,archive.data,archive.size);Mem m={bad,archive.size};if(i<64)m.size=i;else{random=random*1664525u+1013904223u;size_t at=random%(archive.size<4096?archive.size:4096);bad[at]^=(uint8_t)(1u<<(random%8));}
        CohAssetSource s={readmem,&m,m.size,5};CHECK(coh_asset_create(&c,&l)==COH_OK);CohStatus r=coh_asset_mount_pigg(l,s,(CohCancel){0});if(r!=COH_OK){CHECK(!coh_asset_stats(l).indexed_entries);CHECK(coh_asset_stats(l).allocated_bytes==base);}CHECK(coh_asset_destroy(&l)==COH_OK);fuzz_cases++;
    }free(bad);
    float fo[3]={99,99,99};uint32_t io[3]={99,99,99};uint8_t badstream[]={0,31};CHECK(coh_asset_delta_floats((CohBytes){badstream,sizeof(badstream)},1,3,fo,3)==COH_INVALID);CHECK(fo[0]==99&&fo[1]==99&&fo[2]==99);CHECK(coh_asset_delta_indices((CohBytes){badstream,sizeof(badstream)},1,io,3)==COH_INVALID);CHECK(io[0]==99);
    c.cache_bytes=16;c.max_asset_bytes=8;c.max_stored_bytes=256u<<10;CHECK(coh_asset_create(&c,&l)==COH_OK);CHECK(coh_asset_mount_pigg(l,source,(CohCancel){0})==COH_OK);CHECK(coh_asset_acquire(l,(CohAssetId){"test/a",0},(CohCancel){0},&a)==COH_LIMIT);CHECK(!coh_asset_stats(l).resident_entries);CHECK(coh_asset_destroy(&l)==COH_OK);
    for(unsigned i=0;i<files;i++)free(originals[i].data);
    free(archive.data);
    printf("{\"passed\":true,\"checks\":%u,\"authentic_files\":%u,\"geo_models\":%u,\"streams\":%u,\"textures\":%u,\"animations\":%u,\"sounds\":%u,\"malformed_mutations\":%u,\"peak_heap_bytes\":%zu,\"peak_resident_bytes\":%zu,\"evictions\":%" PRIu64 "}\n",checks,files,geo_models,streams,textures,animations,sounds,fuzz_cases,stats.peak_allocated_bytes,stats.peak_resident_bytes,stats.evictions);
    return 0;
}
