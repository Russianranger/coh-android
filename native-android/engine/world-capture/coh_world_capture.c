#include "coh_world_capture.h"
#include <stdlib.h>
#include <string.h>
struct CohWorldCapture {CohWorldCaptureReceipt receipt;uint8_t bytes[];};
static int digest(const uint8_t *v){unsigned n=0;for(unsigned i=0;i<32;i++)n|=v[i];return n!=0;}
static int overlap(const void*a,size_t an,const void*b,size_t bn){
    uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(!an||!bn)return 0;
    if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;
    return aa<bb+bn&&bb<aa+an;
}
CohStatus coh_world_capture_stage(const CohWorldCaptureBinding*b,unsigned legacy,const CohNetOwnedMessage*m,
    size_t retained,size_t limit,CohWorldCapture**out,CohGroupsFailure*failure){
    if(!b||!m||!out||legacy>1)return COH_INVALID;
    const void*objects[]={b,m,out,failure,m->payload};
    const size_t sizes[]={sizeof(*b),sizeof(*m),sizeof(*out),failure?sizeof(*failure):0,m->payload_bytes};
    for(unsigned i=0;i<5;i++)for(unsigned j=0;j<i;j++)
        if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
    if(*out)return COH_STATE;
    if(!b->generation||!b->catalog_generation||b->expected_slot>=COH_DB_SLOTS_MAX||!b->expected_dbid||!b->expected_map_id||
       !digest(b->source_sha256)||!digest(b->profile_sha256)||!digest(b->server_run_sha256)||!digest(b->catalog_sha256)||!digest(b->character_row_sha256))return COH_STATE;
    if(!m->generation||!m->id||m->compressed>1||m->ordered>1||!m->payload||!m->payload_bits||
       m->payload_bytes!=((size_t)m->payload_bits+7u)/8u)return COH_INVALID;
    if(m->payload_bytes>COH_WORLD_CAPTURE_BYTES_MAX||limit>COH_WORLD_CAPTURE_AGGREGATE_MAX||retained>limit)return COH_LIMIT;
    size_t bytes=sizeof(CohWorldCapture)+m->payload_bytes,available=limit-retained;
    if(m->payload_bytes>available)return COH_LIMIT;
    available-=m->payload_bytes;
    if(COH_WORLD_CAPTURE_STACK_RESERVE>available)return COH_LIMIT;
    available-=COH_WORLD_CAPTURE_STACK_RESERVE;if(bytes>available)return COH_LIMIT;
    CohRepReader reader;CohStatus status=coh_rep_reader_bounded(&reader,(CohBytes){m->payload,m->payload_bytes},m->payload_bits,m->compressed,COH_WORLD_CAPTURE_BYTES_MAX);
    uint32_t command=0;if(status==COH_OK)status=coh_rep_pack(&reader,1,&command);
    if(status!=COH_OK)return status;
    if(command!=COH_REP_GROUPS+(legacy?5u:0u))return COH_UNSUPPORTED;
    size_t start=reader.cursor;CohGroupsInspection structure;status=coh_rep_groups(&reader,&structure,failure);
    if(status!=COH_OK)return status;
    if(!structure.new_world||structure.footer_file_count!=b->footer_files||structure.footer_active_roots!=b->footer_roots||
       structure.footer_defs_crc!=b->footer_defs_crc||structure.footer_refs_crc!=b->footer_refs_crc)return COH_STATE;
    CohWorldCapture*c=malloc(bytes);if(!c)return COH_LIMIT;
    memset(c,0,sizeof(*c));c->receipt.binding=*b;c->receipt.structure=structure;
    c->receipt.packet_id=m->id;c->receipt.ordered_id=m->ordered_id;c->receipt.payload_bits=m->payload_bits;
    c->receipt.byte_aligned=m->compressed;c->receipt.ordered=m->ordered;c->receipt.transport_lease_generation=m->generation;
    c->receipt.body_start_bit=start;c->receipt.payload_bytes=m->payload_bytes;c->receipt.owned_bytes=bytes;
    c->receipt.aggregate_bytes=retained+m->payload_bytes+bytes+COH_WORLD_CAPTURE_STACK_RESERVE;
    memcpy(c->bytes,m->payload,m->payload_bytes);*out=c;return COH_OK;
}
static int same_structure(const CohGroupsInspection*a,const CohGroupsInspection*b){
#define EQ(x) if(a->x!=b->x)return 0
    EQ(new_world);EQ(files);EQ(present_files);EQ(defs);EQ(removed_defs);EQ(children);EQ(roots);EQ(removed_roots);
    EQ(properties);EQ(swaps);EQ(raw_matrices);EQ(packed_matrices);EQ(strings);EQ(string_bytes);EQ(work_units);
    EQ(max_def_id);EQ(max_root_id);EQ(footer_file_count);EQ(footer_active_roots);EQ(footer_defs_crc);EQ(footer_refs_crc);
    EQ(prefix_bits);EQ(consumed_bits);
#undef EQ
    return 1;
}
CohStatus coh_world_capture_confirm(const CohWorldCapture*c,const CohLocalDiagnostics*d){
    if(!c||!d)return COH_INVALID;
    const CohWorldCaptureReceipt*r=&c->receipt;const CohMapDiagnostics*m=&d->map_protocol;
    if(d->phase!=COH_LOCAL_SCENE_INCOMPLETE||d->last_status!=COH_UNSUPPORTED||!d->local_development_auth||!d->server_identity_bound||
       d->terminal_failure||d->generation!=1||d->selection_generation!=1||d->character_choices!=1||d->map_handoffs!=1||
       m->phase!=COH_MAP_SCENE_INCOMPLETE||m->stage!=COH_MAP_STAGE_SCENE_STRUCTURE||m->last_status!=COH_UNSUPPORTED||
       !m->local_development_authorized||m->selected_dbid||m->character_identity_verified||m->selected_slot!=r->binding.expected_slot||
       m->map_id!=r->binding.expected_map_id||m->selection_generation!=1||m->generation!=1||m->scene_structures!=1||
       !m->last_command_valid||m->last_command!=COH_REP_GROUPS||m->last_payload_bits!=r->payload_bits||
       m->last_decoded_bytes!=r->payload_bytes||m->scene_decoded_bytes!=r->payload_bytes||m->last_byte_aligned!=r->byte_aligned||
       m->scene_failure.stage||m->scene_failure.status||m->scene_failure.bit_offset||m->udp.link.owned_retained_bytes||
       !same_structure(&m->scene_inspection,&r->structure))return COH_STATE;
    return COH_OK;
}
CohStatus coh_world_capture_view(const CohWorldCapture*c,CohWorldCaptureReceipt*r,CohBytes*out){
    if(!c||!r||!out)return COH_INVALID;
    if(overlap(r,sizeof(*r),out,sizeof(*out))||overlap(c,c->receipt.owned_bytes,r,sizeof(*r))||
       overlap(c,c->receipt.owned_bytes,out,sizeof(*out)))return COH_INVALID;
    *r=c->receipt;*out=(CohBytes){c->bytes,c->receipt.payload_bytes};return COH_OK;
}
void coh_world_capture_free(CohWorldCapture*c){if(c){volatile uint8_t*p=(volatile uint8_t*)c;size_t n=c->receipt.owned_bytes;while(n--)*p++=0;free(c);}}
