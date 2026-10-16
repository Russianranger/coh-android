#include "coh_scenecatalog.h"
#include <stdlib.h>
#include <string.h>
typedef struct { CohSgFile identity; uint32_t slots,first,count; } CatalogFile;
struct CohSceneCatalog { CohCatalogReport report; CatalogFile *files; CohSgDefinition *definitions; };
typedef struct {
    CohBytes input; size_t at; CohCatalogReport r; size_t names[COH_GROUPS_FILE_MAX];
    const CohCatalogVisitor *visitor; CohCatalogWalkReport *walk;
    size_t record_budget, working_base, retained;
} Scan;
typedef char walk_stack_descriptors_fit[(2*sizeof(Scan)+2*sizeof(CohSgDefinition)+
    sizeof(CohSceneGraph)+sizeof(CohCatalogWalkReport)<COH_CATALOG_WALK_STACK_RESERVE/2)?1:-1];
#define TRY(x) do {CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static uint32_t le32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static CohStatus read32(Scan *s,uint32_t *v){if(s->at>s->input.size||s->input.size-s->at<4)return COH_INVALID;*v=le32(s->input.data+s->at);s->at+=4;return COH_OK;}
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int same(const char *a,const char *b){while(*a&&*b)if(lower((unsigned char)*a++)!=lower((unsigned char)*b++))return 0;return *a==*b;}
static int name(const char *p,size_t n){if(!n||n>COH_REP_NAME_MAX||p[n-1])return 0;for(size_t i=0;i+1<n;i++)if((unsigned char)p[i]<32||(unsigned char)p[i]>126)return 0;return n>1;}
static uint32_t adler(uint32_t crc,const char *p){uint32_t a=crc&65535u,b=crc>>16;for(;*p;p++){a=(a+(unsigned char)*p)%65521u;b=(b+a)%65521u;}return b<<16|a;}
static uint32_t digest(uint32_t n){return n>>24|(n>>8&0xff00u)|(n<<8&0xff0000u)|n<<24;}
static CohStatus total(uint32_t *n,uint32_t add,uint32_t limit){if(add>limit-*n)return COH_LIMIT;*n+=add;return COH_OK;}
static CohStatus callback_status(CohStatus status){return status>=COH_OK&&status<=COH_STATE?status:COH_INVALID;}
static CohStatus visit_slot(Scan *s,const CohCatalogFileView *file,uint32_t slot,
    const CohSgDefinition *definition,size_t bytes,size_t bits,uint32_t aligned){
    CohCatalogSlotView view={s->input,file,slot,definition!=NULL,aligned,
        definition?s->at-16:0,definition?s->at:0,bytes,bits,definition};
    s->r.slot=slot;
    s->walk->slots_visited++;
    return s->visitor&&s->visitor->slot?callback_status(s->visitor->slot(s->visitor->context,&view)):COH_OK;
}
static CohStatus scan(Scan *s,uint32_t generation,CohSceneCatalog *catalog){
    uint32_t version,header,size,expected_defs,reserved,dc=1,seen=0;
    s->r.stage=COH_CATALOG_HEADER;s->r.input_bytes=s->input.size;
    if(!s->input.data||s->input.size<48||!generation)return COH_INVALID;
    if(s->input.size>COH_CATALOG_INPUT_MAX)return COH_LIMIT;
    if(memcmp(s->input.data,"COHCAT01",8))return COH_UNSUPPORTED;
    s->at=8;
    TRY(read32(s,&version));TRY(read32(s,&header));TRY(read32(s,&size));TRY(read32(s,&s->r.generation));
    TRY(read32(s,&s->r.files));TRY(read32(s,&expected_defs));TRY(read32(s,&s->r.source_defs_crc));
    TRY(read32(s,&s->r.source_refs_crc));TRY(read32(s,&s->r.source_active_roots));TRY(read32(s,&reserved));
    if(version!=1||header!=48||reserved)return COH_UNSUPPORTED;
    if(size!=s->input.size)return COH_INVALID;
    if(s->r.generation!=generation)return COH_STATE;
    if(s->r.files>COH_GROUPS_FILE_MAX||expected_defs>COH_CATALOG_DEFS_MAX||s->r.source_active_roots>COH_GROUPS_ROOT_MAX)return COH_LIMIT;
    s->r.minimum_owned_bytes=sizeof(CohSceneCatalog)+s->r.files*sizeof(CatalogFile)+(size_t)expected_defs*sizeof(CohSgDefinition);
    for(uint32_t f=0;f<s->r.files;f++){
        uint32_t index,checksum,slots,records,n,last=0,next_slot=0;const char *fname;s->r.stage=COH_CATALOG_FILE;s->r.file=f;s->r.slot=UINT32_MAX;
        TRY(read32(s,&index));TRY(read32(s,&checksum));TRY(read32(s,&slots));TRY(read32(s,&records));TRY(read32(s,&n));
        if(index!=f||records>slots)return COH_INVALID;
        if(slots>COH_GROUPS_DEF_ID_MAX+1u||n>COH_REP_NAME_MAX)return COH_LIMIT;
        TRY(total(&s->r.slots,slots,COH_CATALOG_SLOTS_MAX));TRY(total(&s->r.definitions,records,COH_CATALOG_DEFS_MAX));
        if(s->at>s->input.size||n>s->input.size-s->at)return COH_INVALID;
        fname=(const char *)s->input.data+s->at;if(!name(fname,n))return COH_INVALID;
        for(uint32_t j=0;j<f;j++)if(same(fname,(const char *)s->input.data+s->names[j]))return COH_INVALID;
        s->names[f]=s->at;s->at+=n;
        if(catalog){CatalogFile *out=&catalog->files[f];memcpy(out->identity.name,fname,n);out->identity.bounds_checksum=checksum;out->identity.loaded=1;out->slots=slots;out->first=seen;out->count=records;}
        CohCatalogFileView file={fname,index,checksum,slots,records,generation};
        if(s->walk){s->walk->files_visited++;if(s->visitor&&s->visitor->file)TRY(callback_status(s->visitor->file(s->visitor->context,&file)));}
        for(uint32_t d=0;d<records;d++){
            uint32_t id,bits,bytes,aligned,wireid,in_use,count;CohRepReader r;char defname[COH_REP_NAME_MAX];
            s->r.stage=COH_CATALOG_RECORD;s->r.slot=d;
            TRY(read32(s,&id));TRY(read32(s,&bits));TRY(read32(s,&bytes));TRY(read32(s,&aligned));
            if(id>=slots||(d&&id<=last)||aligned!=1||!bytes||bits!=(uint64_t)bytes*8)return COH_INVALID;
            if(bytes>COH_REP_BOUNDED_MESSAGE_MAX)return COH_LIMIT;
            if(s->at>s->input.size||bytes>s->input.size-s->at)return COH_INVALID;
            last=id;s->r.slot=id;
            TRY(coh_rep_reader_bounded(&r,(CohBytes){s->input.data+s->at,bytes},bits,1,COH_REP_BOUNDED_MESSAGE_MAX));
            TRY(coh_rep_pack(&r,1,&wireid));if(wireid!=id+1)return COH_INVALID;
            TRY(coh_rep_read(&r,1,&in_use));if(in_use>1)return COH_INVALID;
            if(in_use){TRY(coh_rep_string(&r,defname,sizeof(defname)));if(!name(defname,strlen(defname)+1))return COH_INVALID;dc=adler(dc,defname);
                TRY(coh_rep_read(&r,32,&count));TRY(coh_rep_pack(&r,1,&count));TRY(total(&s->r.children,count,COH_CATALOG_CHILDREN_MAX));
            }else dc=adler(dc,"NAMELESS");
            s->r.wire_bytes+=bytes;
            if(s->walk){
                CohSgDefinition decoded={0};size_t owned=0;CohStatus status;
                while(next_slot<id){TRY(visit_slot(s,&file,next_slot,NULL,0,0,0));next_slot++;}
                s->r.slot=id;
                s->r.stage=COH_CATALOG_DECODE;
                TRY(coh_rep_reader_bounded(&r,(CohBytes){s->input.data+s->at,bytes},bits,1,COH_REP_BOUNDED_MESSAGE_MAX));
                status=coh_scenegraph_definition_read(&decoded,&r,f,s->record_budget,&owned);
                if(status!=COH_OK)s->walk->failed_record_peak_unknown=1;
                else{
                    if(owned>s->walk->peak_record_owned_bytes)s->walk->peak_record_owned_bytes=owned;
                    s->walk->peak_working_bytes=s->working_base+s->walk->peak_record_owned_bytes;
                    s->walk->peak_aggregate_bytes=s->retained+s->walk->peak_working_bytes;
                }
                if(status==COH_OK&&r.cursor!=bits)status=COH_UNSUPPORTED;
                if(status==COH_OK){
                    s->walk->records_validated++;
                    status=visit_slot(s,&file,id,&decoded,bytes,bits,aligned);
                }
                coh_scenegraph_definition_dispose(&decoded);
                if(status!=COH_OK)return status;
                next_slot=id+1;
            }
            if(catalog){size_t owned;CohSgDefinition *out=&catalog->definitions[seen];s->r.stage=COH_CATALOG_DECODE;
                TRY(coh_rep_reader_bounded(&r,(CohBytes){s->input.data+s->at,bytes},bits,1,COH_REP_BOUNDED_MESSAGE_MAX));
                if(catalog->report.owned_bytes>COH_CATALOG_MEMORY_MAX)return COH_LIMIT;
                TRY(coh_scenegraph_definition_read(out,&r,f,COH_CATALOG_MEMORY_MAX-catalog->report.owned_bytes,&owned));
                catalog->report.owned_bytes+=owned;
                if(r.cursor!=bits)return COH_UNSUPPORTED;
            }
            seen++;s->at+=bytes;
        }
        if(s->walk)while(next_slot<slots){s->r.slot=next_slot;TRY(visit_slot(s,&file,next_slot,NULL,0,0,0));next_slot++;}
    }
    s->r.exceeds_graph_definitions=s->r.definitions>COH_SG_DEFS_MAX;s->r.exceeds_graph_children=s->r.children>COH_SG_CHILDREN_MAX;
    s->r.stage=COH_CATALOG_CHECKSUM;
    if(s->at!=s->input.size||s->r.definitions!=expected_defs||digest(dc)!=s->r.source_defs_crc)return COH_INVALID;
    s->r.stage=COH_CATALOG_PUBLISH;return COH_OK;
}
static CohStatus scanned(CohBytes input,uint32_t generation,CohSceneCatalog *catalog,CohCatalogReport *out){Scan s={0};s.input=input;s.r.file=s.r.slot=UINT32_MAX;CohStatus status=scan(&s,generation,catalog);s.r.status=status;s.r.offset=s.at;if(catalog)s.r.owned_bytes=catalog->report.owned_bytes;if(out)*out=s.r;return status;}
CohStatus coh_scenecatalog_preflight(CohBytes input,uint32_t generation,CohCatalogReport *out){return scanned(input,generation,NULL,out);}
CohStatus coh_scenecatalog_walk(CohBytes input,uint32_t generation,const CohCatalogWalkBudget *budget,
    const CohCatalogVisitor *visitor,CohCatalogWalkReport *out){
    CohCatalogWalkReport result={0};Scan s={0};CohStatus status;
    result.catalog.input_bytes=input.size;result.catalog.stage=COH_CATALOG_HEADER;
    result.catalog.file=result.catalog.slot=UINT32_MAX;
    if(!budget||budget->working_limit>COH_CATALOG_MEMORY_MAX||
       budget->aggregate_limit>COH_SG_TRANSACTION_MAX){status=COH_INVALID;goto done;}
    if(input.size>budget->working_limit||COH_CATALOG_WALK_STACK_RESERVE>budget->working_limit-input.size){status=COH_LIMIT;goto done;}
    s.working_base=input.size+COH_CATALOG_WALK_STACK_RESERVE;
    if(budget->retained_bytes>budget->aggregate_limit||
       s.working_base>budget->aggregate_limit-budget->retained_bytes){status=COH_LIMIT;goto done;}
    s.record_budget=budget->working_limit-s.working_base;
    if(s.record_budget>budget->aggregate_limit-budget->retained_bytes-s.working_base)
        s.record_budget=budget->aggregate_limit-budget->retained_bytes-s.working_base;
    s.input=input;s.visitor=visitor;s.walk=&result;s.retained=budget->retained_bytes;
    result.peak_working_bytes=s.working_base;result.peak_aggregate_bytes=s.retained+s.working_base;
    result.working_upper_bound=s.working_base+s.record_budget;
    result.aggregate_upper_bound=s.retained+result.working_upper_bound;
    status=coh_scenecatalog_preflight(input,generation,&result.catalog);
    if(status!=COH_OK)goto done;
    s.r.file=s.r.slot=UINT32_MAX;
    status=scan(&s,generation,NULL);s.r.offset=s.at;result.catalog=s.r;
done:
    result.catalog.status=status;if(out)*out=result;return status;
}
void coh_scenecatalog_free(CohSceneCatalog *c){if(!c)return;for(uint32_t i=0;i<c->report.definitions;i++)coh_scenegraph_definition_dispose(&c->definitions[i]);free(c->definitions);free(c->files);free(c);}
CohStatus coh_scenecatalog_load(CohSceneCatalog **published,CohBytes input,uint32_t generation,CohCatalogReport *out){
    CohCatalogReport r;CohSceneCatalog *c;CohStatus s;
    if(!published)return COH_INVALID;
    s=coh_scenecatalog_preflight(input,generation,&r);if(s!=COH_OK){if(out)*out=r;return s;}
    if(r.minimum_owned_bytes>COH_CATALOG_MEMORY_MAX){r.status=COH_LIMIT;r.stage=COH_CATALOG_DECODE;if(out)*out=r;return COH_LIMIT;}
    c=calloc(1,sizeof(*c));if(!c){r.status=COH_LIMIT;if(out)*out=r;return COH_LIMIT;}c->report=r;c->report.owned_bytes=r.minimum_owned_bytes;
    if(r.files)c->files=calloc(r.files,sizeof(*c->files));
    if(r.definitions)c->definitions=calloc(r.definitions,sizeof(*c->definitions));
    if((r.files&&!c->files)||(r.definitions&&!c->definitions)){c->report.definitions=0;coh_scenecatalog_free(c);r.status=COH_LIMIT;if(out)*out=r;return COH_LIMIT;}
    s=scanned(input,generation,c,&r);
    if(s!=COH_OK){coh_scenecatalog_free(c);if(out)*out=r;return s;}
    c->report=r;CohSceneCatalog *old=*published;*published=c;coh_scenecatalog_free(old);if(out)*out=r;return COH_OK;
}
CohStatus coh_scenecatalog_file(void *context,const char *name_,uint32_t checksum,uint32_t generation,CohSgImportedFile *out){
    const CohSceneCatalog *c=context;if(!c||!name_||!out)return COH_INVALID;
    size_t length=0;while(length<COH_REP_NAME_MAX&&name_[length])length++;if(length==COH_REP_NAME_MAX)return COH_INVALID;
    if(generation!=c->report.generation)return COH_STATE;
    for(uint32_t i=0;i<c->report.files;i++){const CatalogFile *f=&c->files[i];if(!same(name_,f->identity.name))continue;
        if(checksum!=f->identity.bounds_checksum)return COH_STATE;
        *out=(CohSgImportedFile){f->identity.name,checksum,generation,f->count?c->definitions+f->first:NULL,f->count};return COH_OK;
    }return COH_NOT_FOUND;
}
CohStatus coh_scenecatalog_match(const CohSceneCatalog *c,const CohGroupsInspection *g){if(!c||!g)return COH_INVALID;return g->new_world&&g->files==c->report.files&&g->footer_defs_crc==c->report.source_defs_crc&&g->footer_refs_crc==c->report.source_refs_crc&&g->footer_active_roots==c->report.source_active_roots?COH_OK:COH_STATE;}
void coh_scenecatalog_report(const CohSceneCatalog *c,CohCatalogReport *out){if(c&&out)*out=c->report;}
