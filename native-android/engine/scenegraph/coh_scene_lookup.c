#include "coh_scene_lookup.h"
#include <stdlib.h>
#include <string.h>
typedef struct {CohSgLookupModel row;uint32_t base_length;} Model;
struct CohSgLookupIndex {
    CohSgLookupBinding binding,base_binding;
    uint32_t file_count,library_count,model_count,file_capacity,library_capacity,model_capacity;
    size_t owned_bytes;
    CohSgLookupFile *files;CohSgLookupLibrary *libraries;Model *models;
    uint32_t *file_index,*library_index,*model_index;
};
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+('a'-'A'):c;}
static int equal(const char*a,size_t an,const char*b,size_t bn){
    if(an!=bn)return 0;
    for(size_t i=0;i<an;i++)if(lower((unsigned char)a[i])!=lower((unsigned char)b[i]))return 0;
    return 1;
}
static CohStatus length(const char*s,size_t cap,size_t*n){
    if(!s)return COH_INVALID;
    for(size_t i=0;i<cap;i++){
        unsigned c=(unsigned char)s[i];
        if(!c){if(!i)return COH_INVALID;*n=i;return COH_OK;}
        if(c<32||c>126)return COH_UNSUPPORTED;
    }
    return COH_LIMIT;
}
static uint32_t hash(const char*s,size_t n,uint32_t file){
    uint32_t h=2166136261u;
    for(unsigned i=0;i<4;i++){h^=(file>>(i*8))&255u;h*=16777619u;}
    for(size_t i=0;i<n;i++){h^=lower((unsigned char)s[i]);h*=16777619u;}
    return h;
}
static uint32_t capacity(uint32_t n){uint32_t c=1;while(c<n*2u)c*=2;return c;}
static int digest(const uint8_t*p){uint8_t n=0;for(unsigned i=0;i<32;i++)n|=p[i];return n!=0;}
static int binding_equal(const CohSgLookupBinding*a,const CohSgLookupBinding*b){
    return a->generation==b->generation&&a->asset_generation==b->asset_generation&&a->map_generation==b->map_generation&&
        a->input_kind==b->input_kind&&!memcmp(a->source_sha256,b->source_sha256,32)&&
        !memcmp(a->inventory_sha256,b->inventory_sha256,32)&&!memcmp(a->manifest_sha256,b->manifest_sha256,32);
}
static size_t base_length(const char*s){const char*p=strstr(s,"__");return p?(size_t)(p-s):strlen(s);}
static CohStatus geo_name(const char*s,char*out){
    size_t n;CohStatus status=length(s,COH_SG_LOOKUP_PATH_CAP,&n);if(status!=COH_OK)return status;
    size_t dot=n,slash=0;
    for(size_t i=0;i<n;i++){if(s[i]=='/'||s[i]=='\\')slash=i+1;if(s[i]=='.')dot=i;}
    if(dot<slash)dot=n;
    if(dot+4>=COH_SG_LOOKUP_PATH_CAP)return COH_LIMIT;
    memcpy(out,s,dot);memcpy(out+dot,".geo",5);return COH_OK;
}
static uint32_t find_file(const CohSgLookupIndex*g,uint32_t slot){
    uint32_t lo=0,hi=g->file_count;
    while(lo<hi){uint32_t m=lo+(hi-lo)/2;if(g->files[m].slot<slot)lo=m+1;else hi=m;}
    return lo<g->file_count&&g->files[lo].slot==slot?lo:UINT32_MAX;
}
static CohStatus insert(CohSgLookupIndex*g,unsigned kind,uint32_t row){
    const char*name;size_t n;uint32_t file=0,*table,cap;
    if(kind==0){name=g->files[row].geo_path;n=strlen(name);table=g->file_index;cap=g->file_capacity;}
    else if(kind==1){name=g->libraries[row].name;n=strlen(name);table=g->library_index;cap=g->library_capacity;}
    else{name=g->models[row].row.name;n=g->models[row].base_length;file=g->models[row].row.file_slot;table=g->model_index;cap=g->model_capacity;}
    uint32_t at=hash(name,n,file)&(cap-1);
    for(unsigned p=0;p<COH_SG_LOOKUP_PROBES_MAX;p++,at=(at+1)&(cap-1)){
        if(!table[at]){table[at]=row+1;return COH_OK;}
        uint32_t other=table[at]-1;const char*key;size_t size;uint32_t keyfile=0;
        if(kind==0){key=g->files[other].geo_path;size=strlen(key);}
        else if(kind==1){key=g->libraries[other].name;size=strlen(key);}
        else{key=g->models[other].row.name;size=g->models[other].base_length;keyfile=g->models[other].row.file_slot;}
        if(file==keyfile&&equal(name,n,key,size))return COH_INVALID;
    }
    return COH_LIMIT;
}
static char*copy_string(char**cursor,const char*s){size_t n=strlen(s)+1;char*out=*cursor;memcpy(out,s,n);*cursor+=n;return out;}
CohStatus coh_sg_lookup_build(const CohSgLookupIndex*old,const CohSgLookupManifest*m,
    const CohSgLookupBudget*b,CohSgLookupIndex**out,CohSgLookupMemory*report){
    if(!m||!b||!out)return COH_INVALID;
    if(*out)return COH_STATE;
    if(!m->binding.generation||!m->binding.asset_generation||!m->binding.map_generation||
        (m->binding.input_kind!=COH_SG_LOOKUP_FIXTURE&&m->binding.input_kind!=COH_SG_LOOKUP_CALLER_VERIFIED_INPUT)||
        !digest(m->binding.source_sha256)||!digest(m->binding.inventory_sha256)||!digest(m->binding.manifest_sha256))return COH_STATE;
    uint32_t previous=old?old->binding.generation:0;
    if(previous==UINT32_MAX||m->binding.generation!=previous+1)return COH_STATE;
    if(!m->file_count||m->file_count>COH_SG_LOOKUP_FILES_MAX||m->library_count>COH_SG_LOOKUP_LIBRARIES_MAX||m->model_count>COH_SG_LOOKUP_MODELS_MAX)return COH_LIMIT;
    if(!m->files||(m->library_count&&!m->libraries)||(m->model_count&&!m->models))return COH_INVALID;
    size_t strings=0;char path[COH_SG_LOOKUP_PATH_CAP];
    for(uint32_t i=0;i<m->file_count;i++){
        const CohSgLookupFile*f=&m->files[i];size_t a,z;CohStatus status;
        if((i&&f->slot<=m->files[i-1].slot)||!f->asset_id||f->asset_generation!=m->binding.asset_generation||!digest(f->payload_sha256))return COH_STATE;
        status=length(f->library_path,COH_SG_LOOKUP_PATH_CAP,&a);if(status!=COH_OK)return status;
        status=length(f->geo_path,COH_SG_LOOKUP_PATH_CAP,&z);if(status!=COH_OK)return status;
        status=geo_name(f->library_path,path);if(status!=COH_OK)return status;
        if(strcmp(path,f->geo_path))return COH_INVALID;
        strings+=a+z+2;
        if(strings>COH_SG_LOOKUP_BYTES_MAX)return COH_LIMIT;
    }
    for(uint32_t i=0;i<m->library_count;i++){
        size_t n;CohStatus status=length(m->libraries[i].name,COH_SG_LOOKUP_NAME_CAP,&n);if(status!=COH_OK)return status;
        if(i&&m->libraries[i].slot<=m->libraries[i-1].slot)return COH_STATE;
        strings+=n+1;
        if(strings>COH_SG_LOOKUP_BYTES_MAX)return COH_LIMIT;
    }
    for(uint32_t i=0;i<m->model_count;i++){
        const CohSgLookupModel*r=&m->models[i];size_t n;CohStatus status=length(r->name,COH_SG_LOOKUP_NAME_CAP,&n);if(status!=COH_OK)return status;
        if(!base_length(r->name))return COH_INVALID;
        if(i&&(r->file_slot<m->models[i-1].file_slot||(r->file_slot==m->models[i-1].file_slot&&r->slot<=m->models[i-1].slot)))return COH_STATE;
        strings+=n+1;
        if(strings>COH_SG_LOOKUP_BYTES_MAX)return COH_LIMIT;
    }
    uint32_t fc=capacity(m->file_count),lc=capacity(m->library_count),mc=capacity(m->model_count);
    /* Count/name ceilings keep every addition below SIZE_MAX on 32-bit too. */
    size_t bytes=sizeof(CohSgLookupIndex)+m->file_count*sizeof(CohSgLookupFile)+m->library_count*sizeof(CohSgLookupLibrary)+
        m->model_count*sizeof(Model)+((size_t)fc+lc+mc)*sizeof(uint32_t)+strings;
    size_t input=sizeof(*m)+m->file_count*sizeof(CohSgLookupFile)+m->library_count*sizeof(CohSgLookupLibrary)+m->model_count*sizeof(CohSgLookupModel)+strings;
    size_t prior=old?old->owned_bytes:0;
    if(bytes>COH_SG_LOOKUP_BYTES_MAX||b->aggregate_limit>COH_SG_LOOKUP_AGGREGATE_MAX||b->retained_bytes>b->aggregate_limit)return COH_LIMIT;
    size_t available=b->aggregate_limit-b->retained_bytes;
    if(input>available)return COH_LIMIT;
    available-=input;
    if(prior>available)return COH_LIMIT;
    available-=prior;
    if(COH_SG_LOOKUP_STACK_RESERVE>available)return COH_LIMIT;
    available-=COH_SG_LOOKUP_STACK_RESERVE;
    if(bytes>available)return COH_LIMIT;
    CohSgLookupIndex*g=calloc(1,bytes);if(!g)return COH_LIMIT;
    g->binding=m->binding;if(old)g->base_binding=old->binding;
    g->file_count=m->file_count;g->library_count=m->library_count;g->model_count=m->model_count;
    g->file_capacity=fc;g->library_capacity=lc;g->model_capacity=mc;g->owned_bytes=bytes;
    g->files=(CohSgLookupFile*)(g+1);g->libraries=(CohSgLookupLibrary*)(g->files+m->file_count);g->models=(Model*)(g->libraries+m->library_count);
    g->file_index=(uint32_t*)(g->models+m->model_count);g->library_index=g->file_index+fc;g->model_index=g->library_index+lc;
    char*next=(char*)(g->model_index+mc);CohStatus status=COH_OK;
    for(uint32_t i=0;i<m->file_count;i++){
        g->files[i]=m->files[i];g->files[i].library_path=copy_string(&next,m->files[i].library_path);g->files[i].geo_path=copy_string(&next,m->files[i].geo_path);
        status=insert(g,0,i);if(status!=COH_OK)goto fail;
    }
    for(uint32_t i=0;i<m->library_count;i++){
        g->libraries[i]=m->libraries[i];g->libraries[i].name=copy_string(&next,m->libraries[i].name);
        if(find_file(g,g->libraries[i].file_slot)==UINT32_MAX){status=COH_STATE;goto fail;}
        status=insert(g,1,i);if(status!=COH_OK)goto fail;
    }
    for(uint32_t i=0;i<m->model_count;i++){
        g->models[i].row=m->models[i];g->models[i].row.name=copy_string(&next,m->models[i].name);g->models[i].base_length=(uint32_t)base_length(m->models[i].name);
        if(find_file(g,g->models[i].row.file_slot)==UINT32_MAX){status=COH_STATE;goto fail;}
        status=insert(g,2,i);if(status!=COH_OK)goto fail;
    }
    if(report)*report=(CohSgLookupMemory){input,prior,bytes,COH_SG_LOOKUP_STACK_RESERVE,b->retained_bytes,input+prior+bytes+COH_SG_LOOKUP_STACK_RESERVE+b->retained_bytes};
    *out=g;return COH_OK;
fail:free(g);return status;
}
CohStatus coh_sg_lookup_publish(CohSgLookupIndex**current,CohSgLookupIndex**candidate,CohSgLookupIndex**retired){
    if(!current||!candidate||!retired||current==candidate||current==retired||candidate==retired)return COH_INVALID;
    if(!*candidate||*retired||*candidate==*current)return COH_STATE;
    if(*current){if(!binding_equal(&(*candidate)->base_binding,&(*current)->binding))return COH_STATE;}
    else if((*candidate)->base_binding.generation)return COH_STATE;
    *retired=*current;*current=*candidate;*candidate=NULL;return COH_OK;
}
void coh_sg_lookup_free(CohSgLookupIndex*g){free(g);}
size_t coh_sg_lookup_owned_bytes(const CohSgLookupIndex*g){return g?g->owned_bytes:0;}
CohStatus coh_sg_lookup_find(const CohSgLookupIndex*g,const CohSgLookupBinding*binding,const char*name,CohSgLookupMatch*out){
    if(!g||!binding||!out)return COH_INVALID;
    if(!binding_equal(&g->binding,binding))return COH_STATE;
    size_t n;CohStatus status=length(name,COH_SG_LOOKUP_NAME_CAP,&n);if(status!=COH_OK)return status;
    const char*base=strrchr(name,'/');base=base?base+1:name;if(!*base)return COH_INVALID;
    char public_name[COH_SG_LOOKUP_NAME_CAP];strcpy(public_name,base);n=strlen(public_name);
    if(public_name[n-1]=='&'){char*s=strrchr(public_name,'_');if(s)*s=0;}
    size_t keylen=base_length(public_name);if(!keylen)return COH_INVALID;
    uint32_t row=UINT32_MAX,at=hash(public_name,keylen,0)&(g->library_capacity-1);
    for(unsigned p=0;p<COH_SG_LOOKUP_PROBES_MAX;p++,at=(at+1)&(g->library_capacity-1)){
        if(!g->library_index[at])break;
        uint32_t i=g->library_index[at]-1;const char*key=g->libraries[i].name;
        if(equal(public_name,keylen,key,strlen(key))){row=i;break;}
    }
    if(row==UINT32_MAX)return COH_NOT_FOUND;
    uint32_t file=g->libraries[row].file_slot,model=UINT32_MAX;n=base_length(base);if(!n)return COH_INVALID;
    at=hash(base,n,file)&(g->model_capacity-1);
    for(unsigned p=0;p<COH_SG_LOOKUP_PROBES_MAX;p++,at=(at+1)&(g->model_capacity-1)){
        if(!g->model_index[at])break;
        uint32_t i=g->model_index[at]-1;
        if(g->models[i].row.file_slot==file&&equal(base,n,g->models[i].row.name,g->models[i].base_length)){model=i;break;}
    }
    if(model==UINT32_MAX)return COH_NOT_FOUND;
    uint32_t f=find_file(g,file);if(f==UINT32_MAX)return COH_STATE;
    CohSgLookupMatch match={0};match.binding=g->binding;match.library_slot=g->libraries[row].slot;match.file_slot=file;match.model_slot=g->models[model].row.slot;
    match.asset_id=g->files[f].asset_id;match.asset_generation=g->files[f].asset_generation;match.unresolved=COH_SG_LOOKUP_UNRESOLVED;
    memcpy(match.payload_sha256,g->files[f].payload_sha256,32);strcpy(match.geo_path,g->files[f].geo_path);strcpy(match.model_name,g->models[model].row.name);
    memcpy(out,&match,sizeof(match));return COH_OK;
}
CohStatus coh_sg_lookup_asset_matches(const CohSgLookupMatch*m,uint32_t id,uint32_t generation,const uint8_t digest_value[32]){
    if(!m||!digest_value)return COH_INVALID;
    return id==m->asset_id&&generation==m->asset_generation&&!memcmp(digest_value,m->payload_sha256,32)?COH_OK:COH_STATE;
}
