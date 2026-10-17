#include "coh_resource_index.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define HEADER 192u
#define UNRESOLVED_CLIENT 1u
typedef struct {const CohAssetBlob *blob;uint8_t *workspace;size_t workspace_bytes;CohAssetGeo geo;const char *path;} Geo;
typedef struct {uint8_t *record;size_t bytes;uint32_t geo;CohResourceView view;} Row;
struct CohResourceIndex {CohResourceBinding binding;CohResourceReport report;CohAssetLoader *loader;Row *rows;Geo *geos;uint32_t count,geo_count,work;size_t owned_bytes;};
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int nz(const uint8_t *p){uint8_t n=0;for(unsigned i=0;i<32;i++)n|=p[i];return n!=0;}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int ascii(const char *s,size_t cap,size_t *len){if(!s)return 0;size_t n=0;while(n<cap&&s[n]){unsigned c=(unsigned char)s[n];if(c<32||c>126)return 0;n++;}if(!n||n==cap)return 0;*len=n;return 1;}
static CohStatus key(const char *s,char out[256],unsigned kind){char b[256];size_t n;if(!out||!ascii(s,256,&n))return COH_INVALID;memcpy(b,s,n+1);
    if(kind==0&&b[n-1]=='&'){char *p=strrchr(b,'_');if(p)*p=0;}
    char *begin=b;if(kind==0||kind==1){char *p=strrchr(b,'/');if(p)begin=p+1;}
    char *suffix=strstr(begin,"__");if(kind==2){if(suffix)begin=suffix+2;}else if(suffix)*suffix=0;
    if(!*begin)return COH_INVALID;
    size_t m=strlen(begin);char result[256];for(size_t i=0;i<=m;i++)result[i]=(char)fold((unsigned char)begin[i]);memcpy(out,result,m+1);return COH_OK;
}
CohStatus coh_resource_library_key(const char *s,char out[256]){return key(s,out,0);}
CohStatus coh_resource_model_key(const char *s,char out[256]){return key(s,out,1);}
CohStatus coh_resource_trick_key(const char *s,char out[256]){return key(s,out,2);}
static int rowcmp(const void *a,const void *b){const CohResourceView *x=&((const Row *)a)->view,*y=&((const Row *)b)->view;uint32_t xa[]={x->owner_kind,x->file,x->slot},ya[]={y->owner_kind,y->file,y->slot};for(unsigned i=0;i<3;i++)if(xa[i]!=ya[i])return xa[i]<ya[i]?-1:1;return 0;}
static const Row *find(const CohResourceIndex *i,uint32_t k,uint32_t f,uint32_t s){Row needle;memset(&needle,0,sizeof(needle));needle.view.owner_kind=k;needle.view.file=f;needle.view.slot=s;return bsearch(&needle,i->rows,i->count,sizeof(Row),rowcmp);}
void coh_resource_index_free(CohResourceIndex *i){if(!i)return;for(uint32_t n=0;n<i->geo_count;n++){coh_asset_release(i->loader,i->geos[n].blob);free(i->geos[n].workspace);}for(uint32_t n=0;n<i->count;n++)free(i->rows[n].record);free(i->geos);free(i->rows);free(i);}
static CohStatus charge(CohResourceIndex *i,size_t bytes,const CohResourceBudget *b,size_t fixed){if(bytes>b->owned_limit-i->owned_bytes||bytes>b->aggregate_limit-fixed-i->owned_bytes)return COH_LIMIT;i->owned_bytes+=bytes;return COH_OK;}
static CohStatus strings(Row *r){const uint8_t *p=r->record;size_t at=HEADER;const char **out[]={&r->view.definition_name,&r->view.model_name,&r->view.geo_name,&r->view.trick_name,&r->view.trick_file,&r->view.library_name};unsigned off[]={48,52,56,60,64,124};
    for(unsigned j=0;j<6;j++){size_t n=u32(p+off[j]);if(n>(j==2?COH_ASSET_PATH_MAX:256u)||n>r->bytes-at)return COH_INVALID;*out[j]=NULL;if(n){const char *s=(const char *)p+at;size_t actual;if(!ascii(s,n,&actual)||actual+1!=n)return COH_INVALID;*out[j]=s;}at+=n;}
    if(!r->view.definition_name)return COH_INVALID;
    uint32_t parts=u32(p+96);if(parts>COH_RESOURCE_TEXTURES_MAX)return COH_LIMIT;for(uint32_t j=0;j<parts;j++){if(r->bytes-at<12)return COH_INVALID;size_t n=u32(p+at+8);at+=12;if(n>256||n>r->bytes-at)return COH_INVALID;size_t actual;if(!ascii((const char *)p+at,n,&actual)||actual+1!=n)return COH_INVALID;at+=n;}
    if(at!=r->bytes)return COH_INVALID;
    return COH_OK;
}
static CohStatus decode(Row *r,uint32_t generation){
    const uint8_t *p=r->record;if(r->bytes<HEADER||r->bytes>COH_RESOURCE_RECORD_MAX||memcmp(p,"COHRES01",8)||u32(p+8)!=1||u32(p+12)!=HEADER||u32(p+16)!=r->bytes||u32(p+20)!=generation||u32(p+44)!=1)return COH_INVALID;
    r->view.owner_kind=u32(p+24);r->view.file=u32(p+28);r->view.slot=u32(p+32);r->view.original_id=u32(p+36);r->view.model_present=u32(p+40);r->view.model_row=u32(p+68);r->view.geo_version=u32(p+72);r->view.geo_disk_row=UINT32_MAX;r->view.unresolved_client_semantics=UNRESOLVED_CLIENT;
    r->view.gld_loadstate=u32(p+76);r->view.model_loadstate=u32(p+80);r->view.model_flags=u32(p+84);
    r->view.trick_present=u32(p+100);r->view.trick_info_present=u32(p+104);r->view.trick_flags[0]=u32(p+108);r->view.trick_flags[1]=u32(p+112);r->view.info_model_flags=u32(p+116);r->view.info_group_flags=u32(p+120);
    for(unsigned n=0;n<3;n++){uint32_t bits=u32(p+128+4*n);memcpy(&r->view.source_min[n],&bits,4);bits=u32(p+140+4*n);memcpy(&r->view.source_max[n],&bits,4);bits=u32(p+152+4*n);memcpy(&r->view.source_scale[n],&bits,4);}uint32_t radius=u32(p+164);memcpy(&r->view.source_radius,&radius,4);
    for(unsigned n=0;n<6;n++){uint32_t bits=u32(p+168+4*n);memcpy(&r->view.source_lod[n],&bits,4);}
    if((r->view.owner_kind!=1&&r->view.owner_kind!=2)||(r->view.owner_kind==2&&r->view.file!=UINT32_MAX)||(r->view.owner_kind==1&&r->view.file==UINT32_MAX)||r->view.model_present>1||u32(p+100)>1||u32(p+104)>1)return COH_INVALID;
    CohStatus st=strings(r);if(st!=COH_OK)return st;
    if(!r->view.model_present){if(r->view.model_name||r->view.geo_name||r->view.trick_name||r->view.trick_file||r->view.model_row!=UINT32_MAX||u32(p+96))return COH_INVALID;for(unsigned off=72;off<124;off+=4)if(u32(p+off))return COH_INVALID;for(unsigned off=128;off<192;off+=4)if(u32(p+off))return COH_INVALID;return COH_OK;}
    if(!r->view.model_name||!r->view.geo_name||r->view.model_row==UINT32_MAX||r->view.gld_loadstate==2||r->view.model_loadstate==2)return COH_INVALID;
    if(!u32(p+100)&&(u32(p+104)||u32(p+108)||u32(p+112)))return COH_INVALID;
    if(u32(p+104)&&(!r->view.trick_name||!r->view.trick_file))return COH_INVALID;
    if(!u32(p+104)){if(r->view.trick_name||r->view.trick_file||u32(p+116)||u32(p+120))return COH_INVALID;for(unsigned off=168;off<192;off+=4)if(u32(p+off))return COH_INVALID;}
    for(unsigned off=128;off<192;off+=4){uint32_t bits=u32(p+off);float value;memcpy(&value,&bits,4);if(!isfinite(value))return COH_INVALID;}
    return COH_OK;
}
CohStatus coh_resource_source_view(CohBytes bytes,uint32_t generation,CohResourceView *out){if(!out||!bytes.data||!generation)return COH_INVALID;Row r;memset(&r,0,sizeof(r));r.record=(uint8_t *)bytes.data;r.bytes=bytes.size;CohStatus st=decode(&r,generation);if(st==COH_OK)*out=r.view;return st;}
static CohStatus work(CohResourceIndex *i,CohCancel cancel){if(i->work==16777216u)return COH_LIMIT;i->work++;if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;return COH_OK;}
typedef struct {char selected[256];uint32_t runtime,disk,matches;} Rank;
static CohStatus rank_add(Rank *rank,const char *query,const char *name,uint32_t row){char other[256];CohStatus st=key(name,other,3);if(st!=COH_OK)return st;int cmp=strcmp(other,rank->selected);if(cmp<0)rank->runtime++;if(!cmp){rank->matches++;if(!strcmp(name,query))rank->disk=row;}return COH_OK;}
CohStatus coh_resource_model_order(const char *query,const char *const *names,uint32_t count,CohCancel cancel,uint32_t *runtime,uint32_t *disk){if(!names||!count||count>COH_RESOURCE_ROWS_MAX||!runtime||!disk||runtime==disk)return COH_INVALID;Rank rank={{0},0,UINT32_MAX,0};CohStatus st=key(query,rank.selected,3);if(st!=COH_OK)return st;for(uint32_t n=0;n<count;n++){if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;if((st=rank_add(&rank,query,names[n],n))!=COH_OK)return st;}if(rank.matches!=1||rank.disk==UINT32_MAX)return COH_STATE;*runtime=rank.runtime;*disk=rank.disk;return COH_OK;}
static CohStatus verify_model(Row *r,const Geo *g,CohResourceIndex *i,CohCancel cancel){const uint8_t *p=r->record;CohAssetGeoModel model={0};CohStatus st;Rank rank={{0},0,UINT32_MAX,0};if((st=key(r->view.model_name,rank.selected,3))!=COH_OK)return st;
    /* Runtime gld->modelheader.models has been geoSortModels-sorted. The public
     * GEO reader exposes raw disk rows. Unique base-key rank reproduces that
     * original permutation without allocating or trusting a caller index. */
    for(uint32_t n=0;n<g->geo.model_count;n++){if((st=work(i,cancel))!=COH_OK)return st;CohAssetGeoModel m;if((st=coh_asset_geo_model(&g->geo,n,&m))!=COH_OK)return st;if((st=rank_add(&rank,r->view.model_name,m.name,n))!=COH_OK)return st;if(!strcmp(m.name,r->view.model_name))model=m;}
    if(rank.matches!=1||rank.disk==UINT32_MAX||rank.runtime!=r->view.model_row)return COH_STATE;
    if(g->geo.version!=r->view.geo_version||model.vertex_count!=u32(p+88)||model.triangle_count!=u32(p+92)||model.material_count!=u32(p+96))return COH_STATE;
    r->view.geo_disk_row=rank.disk;
    size_t at=HEADER;unsigned offs[]={48,52,56,60,64,124};for(unsigned n=0;n<6;n++)at+=u32(p+offs[n]);
    for(uint32_t n=0;n<model.material_count;n++){CohAssetGeoMaterial part;st=coh_asset_geo_material(&g->geo,&model,n,&part);if(st!=COH_OK)return st;uint32_t id=u32(p+at),tris=u32(p+at+4),bytes=u32(p+at+8);at+=12;if(id!=part.texture_id||tris!=part.triangle_count||strcmp((const char *)p+at,part.texture_name))return COH_STATE;at+=bytes;}
    r->view.model=model;return COH_OK;
}
CohStatus coh_resource_index_build(const CohResourceIndex *old,CohAssetLoader *loader,const CohResourceSource *sources,size_t count,const CohResourceGeoPin *pins,size_t pin_count,const CohResourceBinding *binding,const CohResourceBudget *budget,CohResourceDigest digest,void *context,CohCancel cancel,CohResourceIndex **out,CohResourceReport *report){
    if(!loader||!sources||!count||count>COH_RESOURCE_ROWS_MAX||!pins||!pin_count||pin_count>COH_RESOURCE_ROWS_MAX||!binding||!budget||!digest||!out||!report)return COH_INVALID;
    if(*out||!binding->generation||!binding->asset_generation||!nz(binding->source_sha256)||!nz(binding->run_sha256)||!nz(binding->manifest_sha256))return COH_STATE;
    if(old&&(old->binding.generation==UINT32_MAX||binding->generation!=old->binding.generation+1||binding->asset_generation<old->binding.asset_generation||old->loader!=loader))return COH_STATE;
    if(!old&&binding->generation!=1)return COH_STATE;
    if(old&&binding->asset_generation==old->binding.asset_generation&&(memcmp(binding->source_sha256,old->binding.source_sha256,32)||memcmp(binding->run_sha256,old->binding.run_sha256,32)||memcmp(binding->manifest_sha256,old->binding.manifest_sha256,32)))return COH_STATE;
    if(!budget->owned_limit||budget->owned_limit>COH_RESOURCE_INPUT_MAX||!budget->aggregate_limit||budget->aggregate_limit>96u*1024u*1024u||!budget->loader_reservation||coh_asset_stats(loader).allocated_bytes>budget->loader_reservation)return COH_LIMIT;
    size_t fixed=budget->retained_bytes,charges[]={32768u,budget->loader_reservation,old?old->owned_bytes:0,count*sizeof(*sources),pin_count*sizeof(*pins)};
    for(unsigned n=0;n<5;n++){if(fixed>budget->aggregate_limit||charges[n]>budget->aggregate_limit-fixed)return COH_LIMIT;fixed+=charges[n];}
    for(size_t n=0;n<count;n++){if(!sources[n].record.data||!nz(sources[n].sha256)||sources[n].record.size<HEADER||sources[n].record.size>COH_RESOURCE_RECORD_MAX||sources[n].record.size>budget->aggregate_limit-fixed)return COH_LIMIT;fixed+=sources[n].record.size;}
    size_t base=sizeof(CohResourceIndex)+count*sizeof(Row)+count*sizeof(Geo);if(base>budget->owned_limit||base>budget->aggregate_limit-fixed)return COH_LIMIT;
    CohResourceIndex *i=calloc(1,sizeof(*i));if(!i)return COH_LIMIT;i->binding=*binding;i->loader=loader;i->owned_bytes=base;
    i->rows=calloc(count,sizeof(Row));i->geos=calloc(count,sizeof(Geo));CohStatus st=COH_LIMIT;if(!i->rows||!i->geos)goto fail;
    for(size_t n=0;n<count;n++){
        if(cancel.poll&&cancel.poll(cancel.context)){st=COH_CANCELLED;goto fail;}
        Row *r=&i->rows[n];r->geo=UINT32_MAX;r->bytes=sources[n].record.size;if((st=charge(i,r->bytes,budget,fixed))!=COH_OK)goto fail;r->record=malloc(r->bytes);if(!r->record){st=COH_LIMIT;goto fail;}i->count++;memcpy(r->record,sources[n].record.data,r->bytes);
        uint8_t hash[32];st=digest(context,(CohBytes){r->record,r->bytes},hash);if(st!=COH_OK)goto fail;if(memcmp(hash,sources[n].sha256,32)){st=COH_STATE;goto fail;}
        if((st=decode(r,binding->asset_generation))!=COH_OK)goto fail;
        if(!r->view.model_present)continue;
        size_t selected=pin_count;for(size_t k=0;k<pin_count;k++){if((st=work(i,cancel))!=COH_OK)goto fail;size_t pin_length;if(!ascii(pins[k].source_geo_name,COH_ASSET_PATH_MAX,&pin_length)||!ascii(pins[k].id.path,COH_ASSET_PATH_MAX,&pin_length)){st=COH_INVALID;goto fail;}if(!pins[k].id.path||!nz(pins[k].sha256)||pins[k].id.generation!=binding->asset_generation){st=COH_STATE;goto fail;}if(!strcmp(pins[k].source_geo_name,r->view.geo_name)){if(selected!=pin_count){st=COH_STATE;goto fail;}selected=k;}}
        if(selected==pin_count){st=COH_NOT_FOUND;goto fail;}
        uint32_t g;for(g=0;g<i->geo_count;g++){if((st=work(i,cancel))!=COH_OK)goto fail;if(!strcmp(i->geos[g].path,r->view.geo_name))break;}
        if(g==i->geo_count){Geo *geo=&i->geos[g];CohAssetId id=pins[selected].id;st=coh_asset_acquire(loader,id,cancel,&geo->blob);if(st!=COH_OK)goto fail;i->geo_count++;
            if(coh_asset_stats(loader).allocated_bytes>budget->loader_reservation){st=COH_LIMIT;goto fail;}
            CohAssetId actual=coh_asset_identity(geo->blob);if(actual.generation!=id.generation||strcmp(actual.path,id.path)){st=COH_STATE;goto fail;}
            CohBytes data=coh_asset_bytes(geo->blob);st=digest(context,data,hash);if(st!=COH_OK)goto fail;if(memcmp(hash,pins[selected].sha256,32)){st=COH_STATE;goto fail;}
            st=coh_asset_geo_workspace(data,&geo->workspace_bytes);if(st!=COH_OK)goto fail;if((st=charge(i,geo->workspace_bytes,budget,fixed))!=COH_OK)goto fail;
            geo->workspace=malloc(geo->workspace_bytes);if(!geo->workspace){st=COH_LIMIT;goto fail;}st=coh_asset_geo_open(data,geo->workspace,geo->workspace_bytes,COH_RESOURCE_ROWS_MAX,&geo->geo);if(st!=COH_OK)goto fail;geo->path=r->view.geo_name;
        }
        r->geo=g;if((st=verify_model(r,&i->geos[g],i,cancel))!=COH_OK)goto fail;
    }
    qsort(i->rows,i->count,sizeof(Row),rowcmp);for(uint32_t n=1;n<i->count;n++)if(!rowcmp(&i->rows[n-1],&i->rows[n])){st=COH_STATE;goto fail;}
    if(old&&binding->asset_generation==old->binding.asset_generation){if(old->count!=i->count){st=COH_STATE;goto fail;}for(uint32_t n=0;n<i->count;n++)if(old->rows[n].bytes!=i->rows[n].bytes||memcmp(old->rows[n].record,i->rows[n].record,i->rows[n].bytes)){st=COH_STATE;goto fail;}else if(i->rows[n].view.model_present){CohAssetId before=coh_asset_identity(old->geos[old->rows[n].geo].blob),after=coh_asset_identity(i->geos[i->rows[n].geo].blob);if(before.generation!=after.generation||strcmp(before.path,after.path)){st=COH_STATE;goto fail;}}}
    i->report=(CohResourceReport){i->count,i->geo_count,i->work,i->owned_bytes,fixed+i->owned_bytes};*report=i->report;*out=i;return COH_OK;
fail:coh_resource_index_free(i);return st;
}
CohStatus coh_resource_index_view(const CohResourceIndex *i,uint32_t k,uint32_t f,uint32_t s,CohResourceView *out){if(!i||!out)return COH_INVALID;const Row *r=find(i,k,f,s);if(!r)return COH_NOT_FOUND;*out=r->view;return COH_OK;}
CohStatus coh_resource_index_material(const CohResourceIndex *i,uint32_t k,uint32_t f,uint32_t s,uint32_t part,CohAssetGeoMaterial *out){if(!i||!out)return COH_INVALID;const Row *r=find(i,k,f,s);if(!r)return COH_NOT_FOUND;if(!r->view.model_present)return COH_NOT_FOUND;return coh_asset_geo_material(&i->geos[r->geo].geo,&r->view.model,part,out);}

CohStatus coh_resource_index_metadata(const CohResourceIndex *i,CohResourceBinding *binding,CohResourceReport *report){if(!i||!binding||!report)return COH_INVALID;*binding=i->binding;*report=i->report;return COH_OK;}
CohStatus coh_resource_index_record(const CohResourceIndex *i,uint32_t ordinal,CohBytes *bytes,CohResourceView *view){if(!i||!bytes||!view)return COH_INVALID;if(ordinal>=i->count)return COH_NOT_FOUND;*bytes=(CohBytes){i->rows[ordinal].record,i->rows[ordinal].bytes};*view=i->rows[ordinal].view;return COH_OK;}
CohStatus coh_resource_index_header(const CohResourceIndex *i,uint32_t k,uint32_t f,uint32_t s,CohBytes *out){if(!i||!out)return COH_INVALID;const Row *r=find(i,k,f,s);if(!r||!r->view.model_present)return COH_NOT_FOUND;*out=i->geos[r->geo].geo.header;return COH_OK;}
