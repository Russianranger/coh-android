#include "coh_scenegraph.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define TRY(x) do { CohStatus s_=(x); if(s_!=COH_OK)return s_; } while(0)
typedef struct { CohSceneGraph *g; CohRepReader r; CohSgFailure f; const CohSgImports *imports; } Build;
static void *owned(CohSceneGraph *g,size_t n,size_t size) {
    size_t bytes;
    if(!n)return NULL;
    if(size>COH_SG_MEMORY_MAX/n)return NULL;
    bytes=n*size;if(bytes>COH_SG_MEMORY_MAX-g->owned_bytes)return NULL;
    void *p=calloc(n,size);if(p)g->owned_bytes+=bytes;return p;
}
static void release(CohSceneGraph *g,void *p,size_t n){if(p){free(p);g->owned_bytes-=n;}}
static void clear_def(CohSceneGraph *g,CohSgDefinition *d) {
    release(g,d->children,d->child_count*sizeof(*d->children));
    release(g,d->swaps,d->swap_count*sizeof(*d->swaps));release(g,d->wire,d->wire_bytes);
    memset(d,0,sizeof(*d));
}
void coh_scenegraph_free(CohSceneGraph *g) {
    if(!g)return;
    for(uint32_t i=0;i<g->definition_count;i++)clear_def(g,&g->definitions[i]);
    free(g->definitions);free(g->roots);free(g->files);free(g);
}
static CohSceneGraph *create(void) {
    CohSceneGraph *g=calloc(1,sizeof(*g));if(!g)return NULL;g->owned_bytes=sizeof(*g);
    g->files=owned(g,COH_GROUPS_FILE_MAX,sizeof(*g->files));
    g->definitions=owned(g,COH_SG_DEFS_MAX,sizeof(*g->definitions));
    g->roots=owned(g,COH_SG_ROOTS_MAX,sizeof(*g->roots));
    if(!g->files||!g->definitions||!g->roots){coh_scenegraph_free(g);return NULL;}return g;
}
static int valid_name(const char *s,int empty) {
    for(size_t i=0;i<COH_REP_NAME_MAX;i++) {
        unsigned char c=(unsigned char)s[i];if(!c)return empty||i>0;
        if(c<32||c>126)return 0;
    }return 0;
}
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int same_name(const char *a,const char *b) {
    while(*a&&*b){if(lower((unsigned char)*a++)!=lower((unsigned char)*b++))return 0;}return *a==*b;
}
static const char *basename_(const char *s){const char *p=strrchr(s,'/');return p?p+1:s;}
static CohStatus clone_def(CohSceneGraph *g,CohSgDefinition *d,const CohSgDefinition *s) {
    if(!valid_name(s->name,!s->in_use)||!valid_name(s->geometry,1)||!valid_name(s->textures[0],1)||!valid_name(s->textures[1],1)||s->id>COH_GROUPS_DEF_ID_MAX||s->in_use>1)return COH_INVALID;
    if(s->child_count>COH_SG_CHILDREN_MAX||s->swap_count>COH_GROUPS_SWAP_MAX||s->wire_bytes>COH_REP_BOUNDED_MESSAGE_MAX)return COH_LIMIT;
    if((s->child_count&&!s->children)||(s->swap_count&&!s->swaps)||(s->wire_bytes&&!s->wire))return COH_INVALID;
    if(s->wire_start_bit>7||s->wire_bits>s->wire_bytes*8||s->wire_start_bit>s->wire_bytes*8-s->wire_bits)return COH_INVALID;
    *d=*s;d->children=NULL;d->swaps=NULL;d->wire=NULL;
    if(s->child_count){d->children=owned(g,s->child_count,sizeof(*s->children));if(!d->children)return COH_LIMIT;memcpy(d->children,s->children,s->child_count*sizeof(*s->children));}
    if(s->swap_count){d->swaps=owned(g,s->swap_count,sizeof(*s->swaps));if(!d->swaps)return COH_LIMIT;memcpy(d->swaps,s->swaps,s->swap_count*sizeof(*s->swaps));}
    if(s->wire_bytes){d->wire=owned(g,s->wire_bytes,1);if(!d->wire)return COH_LIMIT;memcpy(d->wire,s->wire,s->wire_bytes);}
    return COH_OK;
}
static CohStatus clone_graph(CohSceneGraph *g,const CohSceneGraph *s) {
    g->file_count=s->file_count;g->root_count=s->root_count;
    memcpy(g->files,s->files,s->file_count*sizeof(*s->files));memcpy(g->roots,s->roots,s->root_count*sizeof(*s->roots));
    for(uint32_t i=0;i<s->definition_count;i++){g->definition_count++;TRY(clone_def(g,&g->definitions[i],&s->definitions[i]));}return COH_OK;
}
static CohSgDefinition *slot(CohSceneGraph *g,uint32_t file,uint32_t id) {
    for(uint32_t i=0;i<g->definition_count;i++)if(g->definitions[i].file==file&&g->definitions[i].id==id)return &g->definitions[i];
    if(g->definition_count==COH_SG_DEFS_MAX)return NULL;
    CohSgDefinition *d=&g->definitions[g->definition_count++];d->file=file;d->id=id;return d;
}
static CohSgRoot *root_slot(CohSceneGraph *g,uint32_t id) {
    for(uint32_t i=0;i<g->root_count;i++)if(g->roots[i].id==id)return &g->roots[i];
    if(g->root_count==COH_SG_ROOTS_MAX)return NULL;
    CohSgRoot *r=&g->roots[g->root_count++];r->id=id;return r;
}
static CohStatus bit(Build *b,unsigned w,uint32_t *v){TRY(coh_rep_read(&b->r,w,v));return w<32&&(*v>>w)?COH_INVALID:COH_OK;}
static CohStatus pack(Build *b,unsigned w,uint32_t *v){return coh_rep_pack(&b->r,w,v);}
static CohStatus flag(Build *b,uint32_t *v){return bit(b,1,v);}
static CohStatus string(Build *b,char *out){char tmp[COH_REP_NAME_MAX];TRY(coh_rep_string(&b->r,out?out:tmp,COH_REP_NAME_MAX));return COH_OK;}
static CohStatus f32(Build *b,float *f){uint32_t u;TRY(bit(b,32,&u));memcpy(f,&u,4);return isfinite(*f)?COH_OK:COH_INVALID;}
static CohStatus floats(Build *b,unsigned n){float f;for(unsigned i=0;i<n;i++)TRY(f32(b,&f));return COH_OK;}
static CohStatus optional(Build *b){uint32_t u;TRY(flag(b,&u));if(u)TRY(floats(b,1));return COH_OK;}
static CohStatus colors(Build *b,unsigned n){uint32_t u;for(unsigned i=0;i<n;i++)TRY(bit(b,8,&u));return COH_OK;}
static CohStatus compressed_float(Build *b,float *f) {
    uint32_t half,neg,u;TRY(flag(b,&half));if(!half)return f32(b,f);
    TRY(flag(b,&neg));TRY(pack(b,5,&u));*f=(float)u*0.5f;if(neg)*f=-*f;return COH_OK;
}
static void ypr(CohSgMatrix m,const float p[3]) {
    float sp=sinf(p[0]),cp=cosf(p[0]),sy=sinf(p[1]),cy=cosf(p[1]),sr=sinf(p[2]),cr=cosf(p[2]),t=sy*sp;
    m[0][0]=cy*cr+t*sr;m[1][0]=cy*sr-t*cr;m[2][0]=sy*cp;
    m[0][1]=-cp*sr;m[1][1]=cp*cr;m[2][1]=sp;
    t=-cy*sp;m[0][2]=-sy*cr-t*sr;m[1][2]=-sy*sr+t*cr;m[2][2]=cy*cp;
}
static CohStatus matrix(Build *b,CohSgMatrix m) {
    uint32_t packed,pos,angles,scale;TRY(flag(b,&packed));memset(m,0,sizeof(CohSgMatrix));
    if(!packed){for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++)TRY(f32(b,&m[i][j]));return COH_OK;}
    m[0][0]=m[1][1]=m[2][2]=1;TRY(flag(b,&pos));TRY(flag(b,&angles));TRY(flag(b,&scale));
    if(pos)for(unsigned j=0;j<3;j++)TRY(compressed_float(b,&m[3][j]));
    if(angles){float p[3];for(unsigned j=0;j<3;j++)TRY(compressed_float(b,&p[j]));ypr(m,p);}
    if(scale){float v[3];for(unsigned j=0;j<3;j++)TRY(f32(b,&v[j]));for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)m[i][j]*=v[j];}
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++)if(!isfinite(m[i][j]))return COH_INVALID;
    return COH_OK;
}
static CohStatus tricks(Build *b,CohSgDefinition *d) {
    uint32_t u,light,ambient;TRY(string(b,NULL));TRY(flag(b,&u));TRY(flag(b,&light));TRY(flag(b,&ambient));
    if(light||ambient){if(light)TRY(optional(b));TRY(colors(b,8));}
    TRY(flag(b,&u));if(u){TRY(bit(b,16,&u));TRY(bit(b,16,&u));TRY(floats(b,2));}
    TRY(flag(b,&u));if(u){TRY(string(b,NULL));TRY(string(b,NULL));TRY(bit(b,8,&u));TRY(floats(b,1));TRY(flag(b,&u));}
    TRY(flag(b,&u));if(u){TRY(floats(b,4));TRY(colors(b,8));}
    TRY(flag(b,&u));if(u)TRY(floats(b,3));
    TRY(flag(b,&u));if(u){TRY(string(b,NULL));TRY(floats(b,1));}
    TRY(flag(b,&u));if(u)TRY(colors(b,6));
    TRY(pack(b,1,&u));if(u&~3u)return COH_UNSUPPORTED;if(u&1)TRY(string(b,d->textures[0]));if(u&2)TRY(string(b,d->textures[1]));
    TRY(flag(b,&u));if(u)TRY(floats(b,1));TRY(pack(b,1,&u));
    if(u>1)return COH_INVALID;
    if(u){uint32_t n;char key[64];TRY(bit(b,32,&n));if(n>COH_GROUPS_PROPERTY_MAX)return COH_LIMIT;for(uint32_t i=0;i<n;i++){TRY(coh_rep_string(&b->r,key,sizeof(key)));for(uint32_t j=0;j<COH_GROUPS_VALUE_MAX;j++){uint32_t c;TRY(bit(b,8,&c));if(!c)break;if(j+1==COH_GROUPS_VALUE_MAX)return COH_LIMIT;}TRY(flag(b,&u));}}
    return COH_OK;
}
static CohStatus decode_def(Build *b,uint32_t file,uint32_t id) {
    CohSgDefinition *d=slot(b->g,file,id);if(!d)return COH_LIMIT;
    clear_def(b->g,d);d->file=file;d->id=id;b->f.definition=id;
    size_t start=b->r.cursor;uint32_t u;TRY(flag(b,&d->in_use));
    if(d->in_use) {
        TRY(string(b,d->name));if(!valid_name(d->name,0)||strchr(d->name,'/')||strchr(d->name,'\\'))return COH_UNSUPPORTED;
        TRY(bit(b,32,&d->mod_time));TRY(pack(b,1,&d->child_count));if(d->child_count>COH_SG_CHILDREN_MAX)return COH_LIMIT;
        if(d->child_count){d->children=owned(b->g,d->child_count,sizeof(*d->children));if(!d->children)return COH_LIMIT;}
        for(uint32_t i=0;i<d->child_count;i++){TRY(string(b,d->children[i].name));TRY(matrix(b,d->children[i].matrix));}
        TRY(flag(b,&u));if(u){for(unsigned i=0;i<5;i++)TRY(optional(b));TRY(bit(b,2,&u));for(unsigned i=0;i<4;i++)TRY(flag(b,&u));}
        TRY(flag(b,&u));if(u)for(unsigned i=0;i<6;i++)TRY(flag(b,&u));
        TRY(optional(b));TRY(optional(b));TRY(flag(b,&u));if(u)TRY(tricks(b,d));
        TRY(pack(b,1,&d->swap_count));if(d->swap_count>COH_GROUPS_SWAP_MAX)return COH_LIMIT;
        if(d->swap_count){d->swaps=owned(b->g,d->swap_count,sizeof(*d->swaps));if(!d->swaps)return COH_LIMIT;}
        for(uint32_t i=0;i<d->swap_count;i++){TRY(string(b,d->swaps[i].original));TRY(string(b,d->swaps[i].replacement));TRY(flag(b,&d->swaps[i].composite));}
        TRY(flag(b,&u));if(u)TRY(string(b,d->geometry));TRY(flag(b,&u));
    }
    d->wire_start_bit=(unsigned)(start%8);d->wire_bits=b->r.cursor-start;d->wire_bytes=(d->wire_bits+d->wire_start_bit+7)/8;d->aligned=b->r.compressed;
    d->wire=owned(b->g,d->wire_bytes,1);if(!d->wire)return COH_LIMIT;
    memcpy(d->wire,b->r.bytes.data+start/8,d->wire_bytes);return COH_OK;
}
void coh_scenegraph_definition_dispose(CohSgDefinition *d) {
    if(!d)return;
    free(d->children);free(d->swaps);free(d->wire);memset(d,0,sizeof(*d));
}
CohStatus coh_scenegraph_definition_read(CohSgDefinition *out,CohRepReader *reader,uint32_t file,size_t available,size_t *bytes) {
    CohSgDefinition candidate={0};CohSceneGraph graph={0};Build b={0};uint32_t id;CohStatus s;
    if(!out||!reader||!bytes||file>=COH_GROUPS_FILE_MAX||available>COH_SG_MEMORY_MAX)return COH_INVALID;
    b.r=*reader;b.g=&graph;graph.definitions=&candidate;graph.definition_count=1;
    graph.owned_bytes=COH_SG_MEMORY_MAX-available;
    s=pack(&b,1,&id);if(s!=COH_OK)return s;
    if(!id||id>COH_GROUPS_DEF_ID_MAX+1u)return COH_INVALID;
    candidate.file=file;candidate.id=id-1;
    s=decode_def(&b,file,id-1);
    if(s!=COH_OK){coh_scenegraph_definition_dispose(&candidate);return s;}
    *out=candidate;*reader=b.r;*bytes=graph.owned_bytes-(COH_SG_MEMORY_MAX-available);return COH_OK;
}
static CohStatus imported(Build *b,uint32_t index,const char *name,uint32_t checksum) {
    CohSgFile *f=&b->g->files[index];b->f.stage=COH_SG_IMPORT;b->f.file=index;
    if(!valid_name(name,0))return COH_UNSUPPORTED;
    if(f->loaded){if(!same_name(f->name,name)||f->bounds_checksum!=checksum)return COH_STATE;return COH_OK;}
    if(!b->imports->file)return COH_NOT_FOUND;
    CohSgImportedFile source={0};TRY(b->imports->file(b->imports->context,name,checksum,b->imports->generation,&source));
    if(!source.name||!valid_name(source.name,0)||!same_name(source.name,name)||source.bounds_checksum!=checksum||source.asset_generation!=b->imports->generation)return COH_STATE;
    if(source.definition_count>COH_SG_DEFS_MAX-b->g->definition_count)return COH_LIMIT;
    if(source.definition_count&&!source.definitions)return COH_INVALID;
    for(uint32_t i=0;i<source.definition_count;i++) {
        const CohSgDefinition *s=&source.definitions[i];
        for(uint32_t j=0;j<i;j++)if(source.definitions[j].id==s->id)return COH_INVALID;
        CohSgDefinition *d=slot(b->g,index,s->id);if(!d)return COH_LIMIT;
        TRY(clone_def(b->g,d,s));d->file=index;
    }
    memcpy(f->name,name,strlen(name)+1);f->bounds_checksum=checksum;f->loaded=1;return COH_OK;
}
static CohStatus decode(Build *b) {
    CohRepScenePrefix prefix;TRY(coh_rep_scene_prefix(&b->r,&prefix));uint32_t count;
    TRY(pack(b,1,&count));
    if(b->g->file_count>count)return COH_UNSUPPORTED; /* No inferred index remapping. */
    b->g->file_count=count;
    for(uint32_t n=0;n<count;n++) {
        uint32_t index=n+1==count?0:n+1,present,checksum,u;char name[COH_REP_NAME_MAX];b->f.file=index;
        TRY(flag(b,&present));if(!present){if(!b->g->files[index].loaded)return COH_NOT_FOUND;continue;}
        TRY(string(b,name));TRY(bit(b,32,&checksum));TRY(flag(b,&u));if(u)return COH_UNSUPPORTED;
        TRY(imported(b,index,name,checksum));b->f.stage=COH_SG_DECODE;
        for(;;){TRY(pack(b,1,&u));if(!u)break;TRY(decode_def(b,index,u-1));}
    }
    if(prefix.new_world&&count&&!same_name(prefix.map_path,b->g->files[0].name))return COH_INVALID;
    for(;;) {
        uint32_t index;TRY(pack(b,1,&index));if(index==UINT32_MAX)break;b->f.reference=index;
        CohSgRoot *r=root_slot(b->g,index);if(!r)return COH_LIMIT;
        TRY(string(b,r->name));r->active=r->name[0]!=0;if(r->active)TRY(matrix(b,r->matrix));else memset(r->matrix,0,sizeof(r->matrix));
    }
    /* Footer has already been independently validated by structural inspector. */
    return COH_OK;
}
static CohStatus asset(Build *b,CohSgAssetKind kind,const char *name) {
    if(!valid_name(name,1))return COH_UNSUPPORTED;
    if(!*name)return COH_OK;
    if(!b->imports->asset)return COH_NOT_FOUND;
    return b->imports->asset(b->imports->context,kind,name,b->imports->generation);
}
static CohStatus lookup(const CohSceneGraph *g,const char *name,uint32_t *out) {
    if(!valid_name(name,0))return COH_UNSUPPORTED;
    name=basename_(name);if(!*name||strchr(name,'\\'))return COH_UNSUPPORTED;
    for(uint32_t i=0;i<g->definition_count;i++)if(g->definitions[i].in_use&&same_name(g->definitions[i].name,name)){*out=i;return COH_OK;}
    return COH_NOT_FOUND;
}
static int by_slot(const void *aa,const void *bb) {
    const CohSgDefinition *a=aa,*b=bb;
    if(a->file!=b->file)return a->file<b->file?-1:1;
    return a->id<b->id?-1:a->id>b->id;
}
static int by_root(const void *aa,const void *bb) {const CohSgRoot *a=aa,*b=bb;return a->id<b->id?-1:a->id>b->id;}
static CohStatus visit(CohSceneGraph *g,uint32_t index,uint8_t *colors_,uint16_t *height,uint32_t depth) {
    if(depth>COH_SG_DEPTH_MAX)return COH_LIMIT;
    if(colors_[index]==1)return COH_INVALID;
    if(colors_[index]==2){if(depth+height[index]>COH_SG_DEPTH_MAX)return COH_LIMIT;return COH_OK;}
    colors_[index]=1;CohSgDefinition *d=&g->definitions[index];
    for(uint32_t j=0;j<d->child_count;j++){uint32_t c=d->children[j].resolved;TRY(visit(g,c,colors_,height,depth+1));if(height[c]+1>height[index])height[index]=(uint16_t)(height[c]+1);}
    colors_[index]=2;return COH_OK;
}
static uint32_t adler_string(uint32_t crc,const char *s) {
    uint32_t a=crc&65535u,b=crc>>16;for(;*s;s++){a=(a+(unsigned char)*s)%65521u;b=(b+a)%65521u;}return b<<16|a;
}
static uint32_t digest_order(uint32_t x){return (x>>24)|((x>>8)&0xff00u)|((x<<8)&0xff0000u)|(x<<24);}
static CohStatus resolve(Build *b,const CohGroupsInspection *expected) {
    CohSceneGraph *g=b->g;uint32_t children=0,dc=1,rc=1;uint8_t colors_[COH_SG_DEFS_MAX]={0};uint16_t height[COH_SG_DEFS_MAX]={0};
    b->f.stage=COH_SG_RESOLVE;
    qsort(g->definitions,g->definition_count,sizeof(*g->definitions),by_slot);qsort(g->roots,g->root_count,sizeof(*g->roots),by_root);
    for(uint32_t i=0;i<g->definition_count;i++) {
        CohSgDefinition *d=&g->definitions[i];b->f.file=d->file;b->f.definition=d->id;
        if(!d->in_use){dc=adler_string(dc,"NAMELESS");continue;}
        if(!valid_name(d->name,0)||strchr(d->name,'/')||strchr(d->name,'\\'))return COH_UNSUPPORTED;
        for(uint32_t j=0;j<i;j++)if(g->definitions[j].in_use&&same_name(d->name,g->definitions[j].name))return COH_INVALID;
        dc=adler_string(dc,d->name);
        if(d->child_count>COH_SG_CHILDREN_MAX-children)return COH_LIMIT;
        children+=d->child_count;
        for(uint32_t j=0;j<d->child_count;j++) {
            for(unsigned k=0;k<4;k++)for(unsigned l=0;l<3;l++)if(!isfinite(d->children[j].matrix[k][l]))return COH_INVALID;
            TRY(lookup(g,d->children[j].name,&d->children[j].resolved));
        }
        TRY(asset(b,COH_SG_GEOMETRY,d->geometry));
        for(unsigned j=0;j<2;j++)TRY(asset(b,COH_SG_TEXTURE,d->textures[j]));
        for(uint32_t j=0;j<d->swap_count;j++){
            if(d->swaps[j].composite>1||!d->swaps[j].original[0]||!d->swaps[j].replacement[0])return COH_INVALID;
            CohSgAssetKind kind=d->swaps[j].composite?COH_SG_COMPOSITE_TEXTURE:COH_SG_TEXTURE;
            TRY(asset(b,kind,d->swaps[j].original));TRY(asset(b,kind,d->swaps[j].replacement));
        }
    }
    for(uint32_t i=0;i<g->definition_count;i++)if(g->definitions[i].in_use)TRY(visit(g,i,colors_,height,0));
    for(uint32_t i=0;i<g->root_count;i++)if(g->roots[i].active) {
        CohSgRoot *r=&g->roots[i];b->f.reference=r->id;TRY(lookup(g,r->name,&r->resolved));
        CohSgDefinition *d=&g->definitions[r->resolved];rc=adler_string(rc,d->name);
        if(d->child_count)rc=adler_string(rc,g->definitions[d->children[0].resolved].name);
        g->active_roots++;
    }
    g->definitions_crc=digest_order(dc);g->references_crc=digest_order(rc);b->f.stage=COH_SG_CHECKSUM;
    if(g->active_roots!=expected->footer_active_roots||g->definitions_crc!=expected->footer_defs_crc||g->references_crc!=expected->footer_refs_crc)return COH_INVALID;
    return COH_OK;
}
CohStatus coh_scenegraph_apply(CohSceneGraph **published,CohRepReader *reader,const CohSgImports *imports,uint32_t generation,CohSgFailure *failure) {
    Build b={0};CohGroupsInspection inspection;CohGroupsFailure inspect_failure;CohStatus status=COH_INVALID;b.f.stage=COH_SG_INSPECT;
    if(!published||!reader||!imports||!imports->generation||!generation)goto done;
    if((*published&&((*published)->generation==UINT32_MAX||generation!=(*published)->generation+1))||(!*published&&generation!=1)){status=COH_STATE;goto done;}
    b.r=*reader;status=coh_rep_groups(&b.r,&inspection,&inspect_failure);
    if(status!=COH_OK){b.f.bit=inspect_failure.bit_offset;goto done;}
    if(!inspection.new_world&&!*published){status=COH_STATE;goto done;}
    if(!inspection.new_world&&(*published)->asset_generation!=imports->generation){status=COH_STATE;goto done;}
    b.r=*reader;b.imports=imports;b.g=create();if(!b.g){status=COH_LIMIT;goto done;}
    b.g->generation=generation;b.g->asset_generation=imports->generation;
    if(!inspection.new_world){status=clone_graph(b.g,*published);if(status!=COH_OK)goto done;}
    status=decode(&b);if(status!=COH_OK)goto done;
    status=resolve(&b,&inspection);if(status!=COH_OK)goto done;
    {CohSceneGraph *old=*published;*published=b.g;b.g=NULL;reader->cursor=inspection.consumed_bits;coh_scenegraph_free(old);}
done:
    if(status!=COH_OK){b.f.status=status;if(!b.f.bit)b.f.bit=b.r.cursor;if(failure)*failure=b.f;}
    else if(failure)memset(failure,0,sizeof(*failure));
    coh_scenegraph_free(b.g);return status;
}
CohStatus coh_scenegraph_compose(const CohSgMatrix p,const CohSgMatrix c,CohSgMatrix out) {
    if(!p||!c||!out)return COH_INVALID;
    CohSgMatrix t;
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++){if(!isfinite(p[i][j])||!isfinite(c[i][j]))return COH_INVALID;}
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++){t[i][j]=p[0][j]*c[i][0]+p[1][j]*c[i][1]+p[2][j]*c[i][2]+(i==3?p[3][j]:0);if(!isfinite(t[i][j]))return COH_INVALID;}
    memcpy(out,t,sizeof(t));return COH_OK;
}
