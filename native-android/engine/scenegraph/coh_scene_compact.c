#include "coh_scene_compact.h"
#include "../scenecatalog/coh_scenecatalog.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define COMPACT_STACK_RESERVE (32u*1024u)
#define COMPACT_PROBES 256u
/* Structural growth guard, complemented by emitted-frame qualification. The
 * 128-byte per-level allowance covers the measured 80-byte host visit frame;
 * 1024 bytes cover measured build/audit overhead outside the copied report.
 * The walker has its separate 64KiB reserve. External callback stack is caller
 * owned and cannot be bounded by this module. */
typedef char CompactStackReserveFits[
    sizeof(CohSgCompactAudit)+1024u+(COH_SG_DEPTH_MAX+1u)*128u<=COMPACT_STACK_RESERVE?1:-1];
typedef struct {uint32_t name_offset,checksum,slots,slot_first;} File;
typedef struct {uint32_t file,slot,in_use,mod_time,name_offset,child_first,child_count,wire_offset,wire_bytes,wire_bits,aligned;} Definition;
struct CohSgCompact {
    CohSgCompactBinding binding,prior_binding;CohBytes input;CohSgCompactReport report;
    uint32_t name_capacity;File *files;Definition *definitions;CohSgCompactChild *children;
    uint32_t *slots,*names;uint16_t *heights;uint8_t *colors;
};
typedef struct {CohSgCompact*g;const CohCancel*cancel;uint32_t phase,file,slot,definition,child;CohSgCompactAudit*audit;} Build;
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int same(const char*a,const char*b){while(*a&&*b)if(lower((unsigned char)*a++)!=lower((unsigned char)*b++))return 0;return *a==*b;}
static uint32_t hash(const char*s){uint32_t h=2166136261u;for(;*s;s++){h^=lower((unsigned char)*s);h*=16777619u;}return h;}
static int digest(const uint8_t*p){uint8_t x=0;for(unsigned i=0;i<32;i++)x|=p[i];return x!=0;}
static int binding_same(const CohSgCompactBinding*a,const CohSgCompactBinding*b){return a->generation==b->generation&&a->catalog_generation==b->catalog_generation&&a->asset_generation==b->asset_generation&&!memcmp(a->source_sha256,b->source_sha256,32)&&!memcmp(a->catalog_sha256,b->catalog_sha256,32);}
static const char*name(const CohSgCompact*g,uint32_t i){return (const char*)g->input.data+g->definitions[i].name_offset;}
static CohStatus poll(Build*b){return b->cancel&&b->cancel->poll&&b->cancel->poll(b->cancel->context)?COH_CANCELLED:COH_OK;}
static int valid_name(const char*s){if(!s||!*s)return 0;for(size_t i=0;i<COH_REP_NAME_MAX;i++){unsigned c=(unsigned char)s[i];if(!c)return 1;if(c<32||c>126)return 0;}return 0;}
CohStatus coh_sg_compact_name(const CohSgCompact*g,const char*s,uint32_t*out){
    if(!g||!out||!valid_name(s))return COH_INVALID;
    const char*base=strrchr(s,'/');s=base?base+1:s;if(!*s||strchr(s,'\\'))return COH_UNSUPPORTED;
    uint32_t at=hash(s)&(g->name_capacity-1);
    for(unsigned p=0;p<COMPACT_PROBES;p++,at=(at+1)&(g->name_capacity-1)){
        if(!g->names[at])return COH_NOT_FOUND;
        uint32_t i=g->names[at]-1;if(same(name(g,i),s)){*out=i;return COH_OK;}
    }
    return COH_NOT_FOUND;
}
static CohStatus add_name(CohSgCompact*g,uint32_t i){
    const char*s=name(g,i);if(!valid_name(s)||strchr(s,'/')||strchr(s,'\\'))return COH_UNSUPPORTED;
    uint32_t at=hash(s)&(g->name_capacity-1);
    for(unsigned p=0;p<COMPACT_PROBES;p++,at=(at+1)&(g->name_capacity-1)){
        if(!g->names[at]){g->names[at]=i+1;return COH_OK;}
        if(same(name(g,g->names[at]-1),s))return COH_INVALID;
    }
    return COH_LIMIT;
}
static CohStatus file_view(void*context,const CohCatalogFileView*v){
    Build*b=context;CohSgCompact*g=b->g;CohStatus status=poll(b);if(status!=COH_OK)return status;
    if(v->index!=b->file||v->index>=g->report.files||v->generation!=g->binding.catalog_generation||v->slots>g->report.slots-b->slot)return COH_STATE;
    File*f=&g->files[b->file++];
    if(b->phase==1){f->name_offset=(uint32_t)((const uint8_t*)v->name-g->input.data);f->checksum=v->bounds_checksum;f->slots=v->slots;f->slot_first=b->slot;}
    else if(f->checksum!=v->bounds_checksum||f->slots!=v->slots||strcmp((const char*)g->input.data+f->name_offset,v->name))return COH_STATE;
    b->slot+=v->slots;return COH_OK;
}
static CohStatus slot_view(void*context,const CohCatalogSlotView*v){
    Build*b=context;CohSgCompact*g=b->g;CohStatus status=poll(b);if(status!=COH_OK)return status;
    if(v->file->index>=g->report.files||v->catalog.data!=g->input.data||v->catalog.size!=g->input.size)return COH_STATE;
    File*f=&g->files[v->file->index];if(v->slot>=f->slots)return COH_STATE;
    if(!v->allocated)return g->slots[f->slot_first+v->slot]?COH_STATE:COH_OK;
    if(!v->definition||b->definition>=g->report.definitions||v->definition->id!=v->slot)return COH_STATE;
    const CohSgDefinition*d=v->definition;Definition*out=&g->definitions[b->definition];
    if(b->phase==1){
        if(d->child_count>g->report.children-b->child)return COH_STATE;
        *out=(Definition){v->file->index,v->slot,d->in_use,d->mod_time,0,b->child,d->child_count,(uint32_t)v->wire_offset,(uint32_t)v->wire_bytes,(uint32_t)v->wire_bits,v->aligned};
        g->slots[f->slot_first+v->slot]=b->definition+1;
        if(d->in_use){
            /* Capture the name span from the original aligned scalar prefix,
             * rather than retaining the callback's temporary decoded string. */
            CohRepReader r;uint32_t id,in_use;
            status=coh_rep_reader_bounded(&r,(CohBytes){g->input.data+v->wire_offset,v->wire_bytes},v->wire_bits,(int)v->aligned,COH_REP_BOUNDED_MESSAGE_MAX);
            if(status!=COH_OK)return status;
            status=coh_rep_pack(&r,1,&id);if(status!=COH_OK)return status;
            status=coh_rep_read(&r,1,&in_use);if(status!=COH_OK)return status;
            if(!v->aligned||(r.cursor&7)||id!=v->slot+1||in_use!=1)return COH_STATE;
            out->name_offset=(uint32_t)(v->wire_offset+r.cursor/8);
            if(strcmp(name(g,b->definition),d->name))return COH_STATE;
            status=add_name(g,b->definition);if(status!=COH_OK)return status;
        }
    }else{
        if(out->file!=v->file->index||out->slot!=v->slot||out->in_use!=d->in_use||out->mod_time!=d->mod_time||out->child_count!=d->child_count||out->child_first!=b->child||out->wire_offset!=v->wire_offset||out->wire_bytes!=v->wire_bytes||out->wire_bits!=v->wire_bits)return COH_STATE;
        for(uint32_t i=0;i<d->child_count;i++){
            CohSgCompactChild*c=&g->children[b->child+i];status=coh_sg_compact_name(g,d->children[i].name,&c->resolved);
            if(b->audit){
                b->audit->references_checked++;
                if(status==COH_NOT_FOUND){
                    b->audit->missing_references++;c->resolved=UINT32_MAX;
                    if(b->audit->missing_stored<COH_SG_COMPACT_DIAGNOSTICS_MAX){
                        CohSgCompactMissing*m=&b->audit->missing[b->audit->missing_stored++];
                        m->file=v->file->index;m->slot=v->slot;m->child=i;
                        strcpy(m->file_name,v->file->name);strcpy(m->definition_name,d->name);strcpy(m->name,d->children[i].name);
                    }else b->audit->diagnostics_truncated=1;
                }else if(status!=COH_OK)return status;
            }else if(status!=COH_OK)return status;
            for(unsigned col=0;col<4;col++)for(unsigned row=0;row<3;row++)if(!isfinite(d->children[i].matrix[col][row]))return COH_INVALID;
            memcpy(c->matrix,d->children[i].matrix,sizeof(c->matrix));
        }
    }
    b->child+=d->child_count;b->definition++;return COH_OK;
}
static CohStatus visit(CohSgCompact*g,uint32_t i,uint32_t depth,const CohCancel*cancel){
    if(cancel&&cancel->poll&&cancel->poll(cancel->context))return COH_CANCELLED;
    if(depth>COH_SG_DEPTH_MAX)return COH_LIMIT;
    if(g->colors[i]==1)return COH_INVALID;
    if(g->colors[i]==2)return depth+g->heights[i]>COH_SG_DEPTH_MAX?COH_LIMIT:COH_OK;
    g->colors[i]=1;const Definition*d=&g->definitions[i];
    for(uint32_t j=0;j<d->child_count;j++){
        uint32_t child=g->children[d->child_first+j].resolved;CohStatus status=visit(g,child,depth+1,cancel);if(status!=COH_OK)return status;
        if(g->heights[child]+1>g->heights[i])g->heights[i]=(uint16_t)(g->heights[child]+1);
    }
    g->colors[i]=2;return COH_OK;
}
static CohStatus build(const CohSgCompact*old,CohBytes input,const CohSgCompactBinding*binding,
    const CohSgCompactBudget*budget,const CohCancel*cancel,CohSgCompact**candidate,CohSgCompactReport*report,CohSgCompactAudit*audit){
    if(!candidate||!binding||!budget)return COH_INVALID;
    if(*candidate)return COH_STATE;
    uint32_t previous=old?old->binding.generation:0;
    if(previous==UINT32_MAX||binding->generation!=previous+1||!binding->catalog_generation||!binding->asset_generation||!digest(binding->source_sha256)||!digest(binding->catalog_sha256))return COH_STATE;
    if(old&&(binding->catalog_generation<old->binding.catalog_generation||binding->asset_generation<old->binding.asset_generation))return COH_STATE;
    if(old&&binding->catalog_generation==old->binding.catalog_generation&&
       (memcmp(binding->catalog_sha256,old->binding.catalog_sha256,32)||memcmp(binding->source_sha256,old->binding.source_sha256,32)))return COH_STATE;
    if(!budget->aggregate_limit||budget->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_INVALID;
    size_t prior=old?old->report.owned_bytes:0,prior_input=old?old->input.size:0;
    if(budget->retained_bytes>budget->aggregate_limit)return COH_LIMIT;
    size_t available=budget->aggregate_limit-budget->retained_bytes;
    if(prior>available)return COH_LIMIT;
    available-=prior;
    if(prior_input>available)return COH_LIMIT;
    available-=prior_input;
    if(COMPACT_STACK_RESERVE+COH_CATALOG_WALK_STACK_RESERVE>available)return COH_LIMIT;
    if(input.size>available-COMPACT_STACK_RESERVE-COH_CATALOG_WALK_STACK_RESERVE)return COH_LIMIT;
    CohCatalogReport scan;CohStatus status=coh_scenecatalog_preflight(input,binding->catalog_generation,&scan);if(status!=COH_OK)return status;
    uint32_t capacity=1;while(capacity<scan.definitions*2u)capacity*=2;
    size_t owned=sizeof(CohSgCompact)+(size_t)scan.files*sizeof(File)+(size_t)scan.definitions*sizeof(Definition)+(size_t)scan.children*sizeof(CohSgCompactChild)+((size_t)scan.slots+capacity)*sizeof(uint32_t)+(size_t)scan.definitions*(sizeof(uint16_t)+sizeof(uint8_t));
    if(owned>COH_SG_MEMORY_MAX)return COH_LIMIT;
    if(owned>available)return COH_LIMIT;
    available-=owned;
    if(COMPACT_STACK_RESERVE>available)return COH_LIMIT;
    available-=COMPACT_STACK_RESERVE;
    if(input.size>available||COH_CATALOG_WALK_STACK_RESERVE>available-input.size)return COH_LIMIT;
    CohSgCompact*g=calloc(1,owned);if(!g)return COH_LIMIT;
    g->binding=*binding;if(old)g->prior_binding=old->binding;g->input=input;g->name_capacity=capacity;
    g->report=(CohSgCompactReport){scan.files,scan.slots,scan.definitions,scan.children,scan.source_defs_crc,scan.source_refs_crc,scan.source_active_roots,owned,input.size,prior,prior_input,budget->retained_bytes,0,COMPACT_STACK_RESERVE+COH_CATALOG_WALK_STACK_RESERVE,0,0,0};
    g->files=(File*)(g+1);g->definitions=(Definition*)(g->files+scan.files);g->children=(CohSgCompactChild*)(g->definitions+scan.definitions);
    g->slots=(uint32_t*)(g->children+scan.children);g->names=g->slots+scan.slots;g->heights=(uint16_t*)(g->names+capacity);g->colors=(uint8_t*)(g->heights+scan.definitions);
    size_t retained=budget->retained_bytes+prior+prior_input+owned+COMPACT_STACK_RESERVE;
    CohCatalogWalkBudget walk_budget={COH_CATALOG_MEMORY_MAX,budget->aggregate_limit,retained};
    for(unsigned phase=1;phase<=2;phase++){
        Build b={g,cancel,phase,0,0,0,0,audit};CohCatalogVisitor visitor={&b,file_view,slot_view};CohCatalogWalkReport walked;
        status=coh_scenecatalog_walk(input,binding->catalog_generation,&walk_budget,&visitor,&walked);if(status!=COH_OK)goto fail;
        if(b.file!=scan.files||b.slot!=scan.slots||b.definition!=scan.definitions||b.child!=scan.children){status=COH_STATE;goto fail;}
        if(walked.peak_record_owned_bytes>g->report.peak_record_bytes)g->report.peak_record_bytes=walked.peak_record_owned_bytes;
        if(walked.peak_aggregate_bytes>g->report.aggregate_peak_bytes)g->report.aggregate_peak_bytes=walked.peak_aggregate_bytes;
    }
    if(audit){
        audit->topology=g->report;audit->definitions_crc_verified=1;
        if(audit->missing_references){status=COH_NOT_FOUND;goto fail;}
    }
    for(uint32_t i=0;i<scan.definitions;i++)if(g->definitions[i].in_use){
        if(cancel&&cancel->poll&&cancel->poll(cancel->context)){status=COH_CANCELLED;goto fail;}
        status=visit(g,i,0,cancel);if(status!=COH_OK)goto fail;
    }
    if(report)*report=g->report;
    *candidate=g;return COH_OK;
fail:free(g);return status;
}
CohStatus coh_sg_compact_build(const CohSgCompact*old,CohBytes input,const CohSgCompactBinding*binding,
    const CohSgCompactBudget*budget,const CohCancel*cancel,CohSgCompact**candidate,CohSgCompactReport*report){
    return build(old,input,binding,budget,cancel,candidate,report,NULL);
}
CohStatus coh_sg_compact_audit(CohBytes input,const CohSgCompactBinding*binding,
    const CohSgCompactBudget*budget,const CohCancel*cancel,CohSgCompactAudit*out){
    if(!budget||!out)return COH_INVALID;
    if(budget->retained_bytes>budget->aggregate_limit||sizeof(*out)>budget->aggregate_limit-budget->retained_bytes)return COH_LIMIT;
    CohSgCompactBudget bounded=*budget;bounded.retained_bytes+=sizeof(*out);
    CohSgCompactAudit audit;memset(&audit,0,sizeof(audit));CohSgCompact*g=NULL;
    CohStatus status=build(NULL,input,binding,&bounded,cancel,&g,NULL,&audit);
    if(status==COH_OK){audit.complete_name_closure=1;coh_sg_compact_free(g);}
    if(status==COH_OK||(status==COH_NOT_FOUND&&audit.definitions_crc_verified))memcpy(out,&audit,sizeof(audit));
    return status;
}
CohStatus coh_sg_compact_publish(CohSgCompact**current,CohSgCompact**candidate,CohSgCompact**retired){
    if(!current||!candidate||!retired||current==candidate||current==retired||candidate==retired)return COH_INVALID;
    if(!*candidate||*retired||*candidate==*current)return COH_STATE;
    if(*current){if(!binding_same(&(*candidate)->prior_binding,&(*current)->binding))return COH_STATE;}
    else if((*candidate)->prior_binding.generation)return COH_STATE;
    *retired=*current;*current=*candidate;*candidate=NULL;return COH_OK;
}
void coh_sg_compact_free(CohSgCompact*g){free(g);}
CohStatus coh_sg_compact_report(const CohSgCompact*g,CohSgCompactReport*out){if(!g||!out)return COH_INVALID;*out=g->report;return COH_OK;}
CohStatus coh_sg_compact_file(const CohSgCompact*g,uint32_t i,CohSgCompactFile*out){
    if(!g||!out)return COH_INVALID;
    if(i>=g->report.files)return COH_NOT_FOUND;
    const File*f=&g->files[i];*out=(CohSgCompactFile){(const char*)g->input.data+f->name_offset,f->checksum,f->slots,g->binding.catalog_generation};return COH_OK;
}
CohStatus coh_sg_compact_slot(const CohSgCompact*g,uint32_t file,uint32_t slot,uint32_t*out){
    if(!g||!out)return COH_INVALID;
    if(file>=g->report.files||slot>=g->files[file].slots)return COH_NOT_FOUND;
    uint32_t i=g->slots[g->files[file].slot_first+slot];if(!i)return COH_NOT_FOUND;*out=i-1;return COH_OK;
}
CohStatus coh_sg_compact_definition(const CohSgCompact*g,uint32_t i,CohSgCompactDefinition*out){
    if(!g||!out)return COH_INVALID;
    if(i>=g->report.definitions)return COH_NOT_FOUND;
    const Definition*d=&g->definitions[i];*out=(CohSgCompactDefinition){d->file,d->slot,d->in_use,d->mod_time,d->child_first,d->child_count,d->in_use?name(g,i):NULL,{g->input.data+d->wire_offset,d->wire_bytes},d->wire_bits,d->aligned};return COH_OK;
}
CohStatus coh_sg_compact_child(const CohSgCompact*g,uint32_t i,CohSgCompactChild*out){if(!g||!out)return COH_INVALID;if(i>=g->report.children)return COH_NOT_FOUND;*out=g->children[i];return COH_OK;}
