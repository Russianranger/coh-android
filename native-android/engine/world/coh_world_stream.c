#include "coh_world_live.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define STRINGS_MAX 32768u
#define DEPS_MAX 256u
typedef struct {uint32_t parent,endpoint,name;float world[12],tint[6];} Node;
typedef struct {uint32_t geo,model,first,count;float center[3],radius;uint32_t part_mask;} Endpoint;
struct CohWorldMap {
    uint32_t nodes,endpoints,assets,deps,live; uint64_t selections,cancellations,rejections;
    Node node[COH_WORLD_MAX_NODES]; Endpoint endpoint[COH_WORLD_MAX_ENDPOINTS];
    struct {uint32_t path,generation;} asset[COH_WORLD_MAX_ASSETS];
    uint32_t dep[DEPS_MAX]; uint32_t strings_size; char strings[STRINGS_MAX];
};
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float f32(const uint8_t *p){uint32_t u=u32(p);float f;memcpy(&f,&u,4);return f;}
static int same_name(const char *a,const char *b){while(*a&&*b){unsigned char x=(unsigned char)*a++,y=(unsigned char)*b++;if(x=='\\')x='/';if(y=='\\')y='/';if(x>='A'&&x<='Z')x=(unsigned char)(x+32);if(y>='A'&&y<='Z')y=(unsigned char)(y+32);if(x!=y)return 0;}return *a==*b;}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static int name_ok(const CohWorldMap *w,uint32_t offset){return offset<w->strings_size&&memchr(w->strings+offset,0,w->strings_size-offset)!=NULL&&w->strings[offset]!=0;}
static int path_ok(const char *p){size_t n=strlen(p);if(!n||n>=COH_ASSET_PATH_MAX||p[0]=='/'||p[0]=='\\')return 0;while(*p){const char *s=p;while(*p&&*p!='/'&&*p!='\\'){if((unsigned char)*p<32||*p==':')return 0;p++;}size_t k=(size_t)(p-s);if(!k||(k==1&&s[0]=='.')||(k==2&&s[0]=='.'&&s[1]=='.'))return 0;if(*p)p++;}return p[-1]!='/'&&p[-1]!='\\';}
static void local(const float p[3],const float d[3],float m[12]){
    /* Original RAD uses a double PI and binary32 reciprocal; order retained. */
    float a[3];for(int i=0;i<3;i++)a[i]=(float)(((double)d[i]*3.14159265358979323846)*(1.0f/180.0f));
    float sp=sinf(a[0]),cp=cosf(a[0]),sy=sinf(a[1]),cy=cosf(a[1]),sr=sinf(a[2]),cr=cosf(a[2]);
    float t=sy*sp,u=-cy*sp;
    m[0]=cy*cr+t*sr; m[1]=-cp*sr; m[2]=-sy*cr-u*sr;
    m[3]=cy*sr-t*cr; m[4]=cp*cr; m[5]=-sy*sr+u*cr;
    m[6]=sy*cp; m[7]=sp; m[8]=cy*cp;
    memcpy(m+9,p,12);
}
static void multiply(const float a[12],const float b[12],float o[12]){
    for(int c=0;c<4;c++)for(int r=0;r<3;r++){
        float f=a[r]*b[c*3];f+=a[3+r]*b[c*3+1];f+=a[6+r]*b[c*3+2];if(c==3)f+=a[9+r];o[c*3+r]=f;
    }
}
CohStatus coh_world_map_create(CohBytes raw,CohWorldMap **out){
    if(!out||!raw.data||raw.size<64||raw.size>1048576||memcmp(raw.data,"COHMAP01",8))return COH_INVALID;
    const uint8_t *p=raw.data;uint32_t n=u32(p+20),e=u32(p+24),a=u32(p+28),d=u32(p+32),ss=u32(p+36);
    uint32_t no=u32(p+40),eo=u32(p+44),ao=u32(p+48),dd=u32(p+52),so=u32(p+56);
    uint32_t version=u32(p+8);
    if((version!=1&&version!=2)||u32(p+12)!=64||u32(p+16)!=raw.size||u32(p+60)||!n||n>COH_WORLD_MAX_NODES||!e||e>COH_WORLD_MAX_ENDPOINTS||!a||a>COH_WORLD_MAX_ASSETS||!d||d>DEPS_MAX||!ss||ss>STRINGS_MAX||no!=64||eo!=no+n*64||ao!=eo+e*40||dd!=ao+a*8||so!=dd+d*4||(uint64_t)so+ss!=raw.size)return COH_INVALID;
    CohWorldMap *w=(CohWorldMap*)calloc(1,sizeof *w);if(!w)return COH_LIMIT;
    w->nodes=n;w->endpoints=e;w->assets=a;w->deps=d;w->strings_size=ss;memcpy(w->strings,p+so,ss);
    for(uint32_t i=0;i<a;i++){const uint8_t *r=p+ao+i*8;w->asset[i].path=u32(r);w->asset[i].generation=u32(r+4);if(!name_ok(w,w->asset[i].path)||!path_ok(w->strings+w->asset[i].path))goto bad;for(uint32_t j=0;j<i;j++)if(w->asset[i].generation==w->asset[j].generation&&same_name(w->strings+w->asset[i].path,w->strings+w->asset[j].path))goto bad;}
    for(uint32_t i=0;i<d;i++){w->dep[i]=u32(p+dd+i*4);if(w->dep[i]>=a)goto bad;}
    for(uint32_t i=0;i<e;i++){
        const uint8_t *r=p+eo+i*40;Endpoint *x=&w->endpoint[i];x->geo=u32(r);x->model=u32(r+4);x->first=u32(r+8);x->count=u32(r+12);for(int j=0;j<3;j++)x->center[j]=f32(r+16+j*4);x->radius=f32(r+28);
        if(x->geo>=a||!name_ok(w,x->model)||!x->count||x->first>d||x->count>d-x->first||!isfinite(x->radius)||x->radius<0||x->radius>1000000||(version==1&&u32(r+32))||u32(r+36))goto bad;
        x->part_mask=u32(r+32)?u32(r+32):UINT32_MAX;
        int has_geo=0;for(uint32_t j=0;j<x->count;j++){if(w->dep[x->first+j]==x->geo)has_geo=1;for(uint32_t k=0;k<j;k++)if(w->dep[x->first+k]==w->dep[x->first+j])goto bad;}if(!has_geo)goto bad;
        for(int j=0;j<3;j++)if(!isfinite(x->center[j])||fabsf(x->center[j])>1000000)goto bad;
    }
    for(uint32_t i=0;i<n;i++){
        const uint8_t *r=p+no+i*64;Node *x=&w->node[i];x->parent=u32(r);x->endpoint=u32(r+4);x->name=u32(r+8);
        if((x->parent!=COH_WORLD_NO_PARENT&&x->parent>=i)||(x->endpoint!=COH_WORLD_NO_PARENT&&x->endpoint>=e)||!name_ok(w,x->name)||u32(r+12)>1)goto bad;
        float pos[3],pyr[3],m[12];for(int j=0;j<3;j++){pos[j]=f32(r+16+j*4);pyr[j]=f32(r+28+j*4);if(!isfinite(pos[j])||fabsf(pos[j])>1000000||!isfinite(pyr[j])||fabsf(pyr[j])>1000000)goto bad;}
        local(pos,pyr,m);if(x->parent==COH_WORLD_NO_PARENT)memcpy(x->world,m,48);else multiply(w->node[x->parent].world,m,x->world);
        for(int j=0;j<12;j++)if(!isfinite(x->world[j])||fabsf(x->world[j])>10000000)goto bad;
        for(int j=0;j<6;j++){uint32_t color=u32(r+40+j*4);if(color>255)goto bad;x->tint[j]=u32(r+12)?(float)color*(1.0f/255.0f):(x->parent==COH_WORLD_NO_PARENT?(j<3?1.0f:0.0f):w->node[x->parent].tint[j]);}
    }
    *out=w;return COH_OK;
bad:free(w);return COH_INVALID;
}
CohStatus coh_world_map_destroy(CohWorldMap **p){if(!p||!*p)return COH_OK;if((*p)->live)return COH_STATE;free(*p);*p=NULL;return COH_OK;}
CohWorldStats coh_world_map_stats(const CohWorldMap *w){CohWorldStats s={0};if(w){s.nodes=w->nodes;s.endpoints=w->endpoints;s.assets=w->assets;s.live_selections=w->live;s.allocated_bytes=sizeof *w;s.selections=w->selections;s.cancellations=w->cancellations;s.rejections=w->rejections;}return s;}
CohStatus coh_world_node(const CohWorldMap *w,uint32_t i,CohWorldNode *out){if(!w||!out||i>=w->nodes)return COH_INVALID;const Node *n=&w->node[i];CohWorldNode x={n->parent,n->endpoint,w->strings+n->name,{0},{0}};memcpy(x.world,n->world,48);memcpy(x.tint,n->tint,24);*out=x;return COH_OK;}
CohStatus coh_world_endpoint(const CohWorldMap *w,uint32_t i,CohWorldEndpoint *out){if(!w||!out||i>=w->endpoints)return COH_INVALID;const Endpoint *e=&w->endpoint[i];CohWorldEndpoint x={{w->strings+w->asset[e->geo].path,w->asset[e->geo].generation},w->strings+e->model,{0},e->radius,e->count};memcpy(x.center,e->center,12);*out=x;return COH_OK;}
CohStatus coh_world_endpoint_part_mask(const CohWorldMap *w,uint32_t i,uint32_t *out){
    if(!w||!out)return COH_INVALID;
    uintptr_t source=(uintptr_t)w,destination=(uintptr_t)out;
    if(source>UINTPTR_MAX-sizeof *w||destination>UINTPTR_MAX-sizeof *out||
       (destination<source+sizeof *w&&source<destination+sizeof *out)||i>=w->endpoints)return COH_INVALID;
    *out=w->endpoint[i].part_mask;return COH_OK;
}
CohStatus coh_world_dependency(const CohWorldMap *w,uint32_t e,uint32_t i,CohAssetId *out){if(!w||!out||e>=w->endpoints||i>=w->endpoint[e].count)return COH_INVALID;uint32_t a=w->dep[w->endpoint[e].first+i];*out=(CohAssetId){w->strings+w->asset[a].path,w->asset[a].generation};return COH_OK;}
void coh_world_release(CohWorldSelection *s){if(!s)return;if(s->owner){for(uint32_t i=0;i<s->pin_count;i++)coh_asset_release(s->loader,s->pins[i]);s->owner->live--;}memset(s,0,sizeof *s);}
CohStatus coh_world_select(CohWorldMap *w,CohAssetLoader *loader,const uint32_t *nodes,uint32_t count,size_t budget,CohCancel cancel,CohWorldSelection *out){
    if(!w||!loader||!out||(!nodes&&count)||count>COH_WORLD_MAX_INSTANCES||!budget)return COH_INVALID;
    if(out->owner&&(out->owner!=w||out->loader!=loader))return COH_STATE;
    CohWorldSelection next={0};uint8_t used[COH_WORLD_MAX_ASSETS]={0};CohStatus status=COH_OK;
    for(uint32_t i=0;i<count;i++){
        if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}if(nodes[i]>=w->nodes||w->node[nodes[i]].endpoint==COH_WORLD_NO_PARENT){status=COH_INVALID;goto fail;}
        for(uint32_t j=0;j<i;j++)if(nodes[j]==nodes[i]){status=COH_INVALID;goto fail;}
        Node *n=&w->node[nodes[i]];Endpoint *e=&w->endpoint[n->endpoint];CohWorldInstance *instance=&next.instances[next.count++];instance->node=nodes[i];instance->endpoint=n->endpoint;memcpy(instance->world,n->world,48);memcpy(instance->tint,n->tint,24);
        for(uint32_t j=0;j<e->count;j++)used[w->dep[e->first+j]]=1;
    }
    /* Complete byte admission before changing cache residency. */
    for(uint32_t a=0;a<w->assets;a++)if(used[a]){CohAssetInfo info;CohAssetId id={w->strings+w->asset[a].path,w->asset[a].generation};if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}status=coh_asset_lookup(loader,id,&info);if(status!=COH_OK)goto fail;if(info.decoded_bytes>budget-next.resident_bytes){status=COH_LIMIT;goto fail;}next.resident_bytes+=info.decoded_bytes;}
    for(uint32_t a=0;a<w->assets;a++)if(used[a]){const CohAssetBlob *blob=NULL;CohAssetId id={w->strings+w->asset[a].path,w->asset[a].generation};status=coh_asset_acquire(loader,id,cancel,&blob);if(status!=COH_OK)goto fail;next.pins[next.pin_count++]=blob;}
    if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}
    coh_world_release(out);next.owner=w;next.loader=loader;w->live++;w->selections++;*out=next;return COH_OK;
fail:for(uint32_t i=0;i<next.pin_count;i++)coh_asset_release(loader,next.pins[i]);if(status==COH_CANCELLED)w->cancellations++;else w->rejections++;return status;
}
CohStatus coh_world_query(const CohWorldMap *w,const float center[3],float radius,uint32_t *nodes,uint32_t capacity,uint32_t *count){
    if(!w||!center||!count||(!nodes&&capacity)||!isfinite(radius)||radius<0||radius>1000000)return COH_INVALID;
    for(int j=0;j<3;j++)if(!isfinite(center[j]))return COH_INVALID;
    uint32_t found=0;for(uint32_t i=0;i<w->nodes;i++){const Node *n=&w->node[i];if(n->endpoint==COH_WORLD_NO_PARENT)continue;const Endpoint *e=&w->endpoint[n->endpoint];float d2=0;for(int r=0;r<3;r++){float v=n->world[r]*e->center[0]+n->world[3+r]*e->center[1]+n->world[6+r]*e->center[2]+n->world[9+r]-center[r];d2+=v*v;}float rr=radius+e->radius;if(d2<=rr*rr)found++;}
    if(found>capacity)return COH_LIMIT;
    found=0;for(uint32_t i=0;i<w->nodes;i++){const Node *n=&w->node[i];if(n->endpoint==COH_WORLD_NO_PARENT)continue;const Endpoint *e=&w->endpoint[n->endpoint];float d2=0;for(int r=0;r<3;r++){float v=n->world[r]*e->center[0]+n->world[3+r]*e->center[1]+n->world[6+r]*e->center[2]+n->world[9+r]-center[r];d2+=v*v;}float rr=radius+e->radius;if(d2<=rr*rr)nodes[found++]=i;}
    *count=found;return COH_OK;
}
static CohStatus bundle_read(void *context,uint64_t offset,void *dst,size_t count){const CohWorldBundleEntry *e=(const CohWorldBundleEntry*)context;if(!e||(!dst&&count)||offset>e->bytes.size||count>e->bytes.size-offset)return COH_IO;if(count)memcpy(dst,e->bytes.data+(size_t)offset,count);return COH_OK;}
CohStatus coh_world_bundle_open(CohBytes b,CohWorldBundle *out){
    if(!out||!b.data||b.size<64||b.size>16u*1024u*1024u||memcmp(b.data,"COHWB001",8))return COH_INVALID;
    const uint8_t *p=b.data;uint32_t ix=u32(p+20),is=u32(p+24),n=u32(p+28),ro=u32(p+32),so=u32(p+36),ss=u32(p+40),po=u32(p+44),mc=u32(p+48),mo=u32(p+52),ms=u32(p+56);
    if(u32(p+8)!=1||u32(p+12)!=64||u32(p+16)!=b.size||!n||n>COH_WORLD_MAX_ASSETS||ro!=64||so!=ro+n*24||!ss||ss>STRINGS_MAX||(uint64_t)so+ss!=ix||!is||(uint64_t)ix+is!=mo||mc>COH_WORLD_MAX_MATERIALS||ms!=mc*128||(uint64_t)mo+ms!=po||po>b.size)return COH_INVALID;
    if(u32(p+60))return COH_INVALID;
    CohWorldBundle next={0};next.count=n;next.material_count=mc;next.index=(CohBytes){p+ix,is};uint32_t expected=po;
    for(uint32_t i=0;i<n;i++){
        const uint8_t *r=p+ro+i*24;uint32_t name=u32(r),off=u32(r+8),len=u32(r+12);
        if(name>=ss||!memchr(p+so+name,0,ss-name)||!path_ok((const char*)p+so+name)||!len||off!=expected||(uint64_t)off+len>b.size||u32(r+16)||u32(r+20))return COH_INVALID;
        next.entries[i]=(CohWorldBundleEntry){{(const char*)p+so+name,u32(r+4)},{p+off,len}};
        for(uint32_t j=0;j<i;j++)if(next.entries[j].id.generation==next.entries[i].id.generation&&same_name(next.entries[j].id.path,next.entries[i].id.path))return COH_INVALID;
        expected+=len;
    }
    if(expected!=b.size)return COH_INVALID;
    for(uint32_t i=0;i<mc;i++){
        const uint8_t *r=p+mo+i*128;CohWorldMaterial *m=&next.materials[i];uint32_t offsets[3]={u32(r),u32(r+4),u32(r+8)};
        for(int j=0;j<3;j++)if(offsets[j]>=ss||!memchr(p+so+offsets[j],0,ss-offsets[j])||!p[so+offsets[j]])return COH_INVALID;
        m->name=(const char*)p+so+offsets[0];for(uint32_t j=0;j<i;j++)if(same_name(m->name,next.materials[j].name))return COH_INVALID;
        for(int j=0;j<2;j++){m->textures[j]=(CohAssetId){(const char*)p+so+offsets[j+1],u32(r+12)};if(!path_ok(m->textures[j].path))return COH_INVALID;int found=0;for(uint32_t k=0;k<n;k++)if(next.entries[k].id.generation==m->textures[j].generation&&same_name(next.entries[k].id.path,m->textures[j].path))found=1;if(!found)return COH_NOT_FOUND;}
        m->family=u32(r+16);m->wrap[0]=u32(r+20);m->wrap[1]=u32(r+24);m->cull_back=u32(r+28);if(m->family>1||m->wrap[0]>2||m->wrap[1]>2||m->cull_back>1)return COH_UNSUPPORTED;
        for(int j=0;j<4;j++){m->uv_scale[j/2][j%2]=f32(r+32+j*4);m->const0[j]=f32(r+48+j*4);m->const1[j]=f32(r+64+j*4);m->diffuse[j]=f32(r+84+j*4);m->ambient[j]=f32(r+100+j*4);if(!isfinite(m->uv_scale[j/2][j%2])||fabsf(m->uv_scale[j/2][j%2])>1024||!isfinite(m->const0[j])||m->const0[j]<0||m->const0[j]>1||!isfinite(m->const1[j])||m->const1[j]<0||m->const1[j]>1||!isfinite(m->diffuse[j])||fabsf(m->diffuse[j])>8||!isfinite(m->ambient[j])||fabsf(m->ambient[j])>8)return COH_INVALID;}
        m->alpha_ref=f32(r+80);if(!isfinite(m->alpha_ref)||m->alpha_ref<0||m->alpha_ref>1)return COH_INVALID;
        for(int j=116;j<128;j++)if(r[j])return COH_INVALID;
    }
    /* Validate semantic index independently before publishing borrowed spans. */
    CohWorldMap *map=NULL;CohStatus status=coh_world_map_create(next.index,&map);if(status!=COH_OK)return status;
    for(uint32_t i=0;i<map->assets;i++){int found=0;for(uint32_t j=0;j<n;j++)if(map->asset[i].generation==next.entries[j].id.generation&&same_name(map->strings+map->asset[i].path,next.entries[j].id.path)){found=1;break;}if(!found){coh_world_map_destroy(&map);return COH_NOT_FOUND;}}
    coh_world_map_destroy(&map);*out=next;return COH_OK;
}
CohStatus coh_world_bundle_mount(CohWorldBundle *bundle,CohAssetLoader *loader,CohCancel cancel){if(!bundle||!loader||!bundle->count||bundle->count>COH_WORLD_MAX_ASSETS)return COH_INVALID;for(uint32_t i=0;i<bundle->count;i++){if(cancelled(cancel))return COH_CANCELLED;CohWorldBundleEntry *e=&bundle->entries[i];CohAssetSource source={bundle_read,e,e->bytes.size,e->id.generation};CohStatus s=coh_asset_mount_file(loader,e->id.path,source);if(s!=COH_OK)return s;}return COH_OK;}

CohStatus coh_world_material(const CohWorldBundle *b,const char *name,CohWorldMaterial *out){if(!b||!name||!out)return COH_INVALID;for(uint32_t i=0;i<b->material_count;i++)if(same_name(name,b->materials[i].name)){*out=b->materials[i];return COH_OK;}return COH_NOT_FOUND;}

static int live_separate(const void *a,size_t an,const void *b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-an&&y<=UINTPTR_MAX-bn&&(x>=y+bn||y>=x+an);}
CohStatus coh_world_select_instances(CohWorldMap *map,CohAssetLoader *loader,const CohWorldInstance *instances,uint32_t count,size_t budget,CohCancel cancel,CohWorldSelection *out){
    if(!map||!loader||!out||(!instances&&count)||count>COH_WORLD_MAX_INSTANCES||!budget)return COH_INVALID;
    if(out->owner&&(out->owner!=map||out->loader!=loader))return COH_STATE;
    if(!live_separate(out,sizeof *out,instances,(size_t)count*sizeof *instances)||!live_separate(map,sizeof *map,out,sizeof *out)||!live_separate(map,sizeof *map,instances,(size_t)count*sizeof *instances))return COH_INVALID;
    CohWorldStats stats=coh_world_map_stats(map);CohAssetId assets[COH_WORLD_MAX_ASSETS];uint32_t used=0;CohWorldSelection next={0};CohStatus status=COH_OK;
    for(uint32_t i=0;i<count;i++){
        if(cancelled(cancel)){status=COH_CANCELLED;goto failed;}
        const CohWorldInstance *instance=&instances[i];if(instance->endpoint>=stats.endpoints){status=COH_INVALID;goto failed;}
        for(uint32_t j=0;j<i;j++)if(instances[j].node==instance->node){status=COH_INVALID;goto failed;}
        for(unsigned j=0;j<12;j++)if(!isfinite(instance->world[j])||fabsf(instance->world[j])>10000000){status=COH_INVALID;goto failed;}
        for(unsigned j=0;j<6;j++)if(!isfinite(instance->tint[j])||instance->tint[j]<0||instance->tint[j]>1){status=COH_INVALID;goto failed;}
        next.instances[next.count++]=*instance;CohWorldEndpoint endpoint;status=coh_world_endpoint(map,instance->endpoint,&endpoint);if(status!=COH_OK)goto failed;
        for(uint32_t j=0;j<endpoint.dependency_count;j++){
            CohAssetId id;status=coh_world_dependency(map,instance->endpoint,j,&id);if(status!=COH_OK)goto failed;
            uint32_t k=0;for(;k<used;k++)if(assets[k].generation==id.generation&&!strcmp(assets[k].path,id.path))break;
            if(k==used){if(used==COH_WORLD_MAX_ASSETS){status=COH_LIMIT;goto failed;}assets[used++]=id;}
        }
    }
    for(uint32_t i=0;i<used;i++){CohAssetInfo info;status=coh_asset_lookup(loader,assets[i],&info);if(status!=COH_OK)goto failed;if(info.decoded_bytes>budget-next.resident_bytes){status=COH_LIMIT;goto failed;}next.resident_bytes+=info.decoded_bytes;}
    for(uint32_t i=0;i<used;i++){const CohAssetBlob *pin=NULL;status=coh_asset_acquire(loader,assets[i],cancel,&pin);if(status!=COH_OK)goto failed;next.pins[next.pin_count++]=pin;}
    if(cancelled(cancel)){status=COH_CANCELLED;goto failed;}
    /* Reuse the existing map's selection owner accounting rather than creating
     * a second lifetime protocol for runtime source rows. */
    coh_world_release(out);next.owner=map;next.loader=loader;map->live++;map->selections++;*out=next;return COH_OK;
failed:for(uint32_t i=0;i<next.pin_count;i++)coh_asset_release(loader,next.pins[i]);return status;
}

size_t coh_world_map_allocation_bytes(void){return sizeof(CohWorldMap);}
