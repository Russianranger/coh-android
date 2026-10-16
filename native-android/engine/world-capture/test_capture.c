#include "coh_world_capture.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "capture_fixtures.h"
static unsigned long checks,truncations,mutations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"capture:%d: %s\n",__LINE__,#x);exit(1);}}while(0)
static CohWorldCaptureBinding binding(const CaptureFixture*f){
    CohWorldCaptureBinding b={0};b.generation=17;b.catalog_generation=19;b.expected_slot=3;b.expected_dbid=721;b.expected_map_id=1;
    b.footer_files=f->files;b.footer_roots=f->roots;b.footer_defs_crc=f->defs_crc;b.footer_refs_crc=f->refs_crc;
    memset(b.source_sha256,1,32);memset(b.profile_sha256,2,32);memset(b.server_run_sha256,3,32);memset(b.catalog_sha256,4,32);memset(b.character_row_sha256,5,32);return b;
}
static CohNetOwnedMessage message(const CaptureFixture*f){
    CohNetOwnedMessage m={0};m.id=12;m.ordered_id=4;m.generation=29;m.compressed=f->aligned;m.payload=f->data;m.payload_bytes=f->bytes;m.payload_bits=f->bits;return m;
}
static CohLocalDiagnostics confirmed(const CohWorldCaptureReceipt*r){
    CohLocalDiagnostics d={0};d.phase=COH_LOCAL_SCENE_INCOMPLETE;d.last_status=COH_UNSUPPORTED;d.local_development_auth=1;d.server_identity_bound=1;d.generation=1;d.selection_generation=1;d.character_choices=1;d.map_handoffs=1;
    CohMapDiagnostics*m=&d.map_protocol;m->phase=COH_MAP_SCENE_INCOMPLETE;m->stage=COH_MAP_STAGE_SCENE_STRUCTURE;m->last_status=COH_UNSUPPORTED;m->local_development_authorized=1;
    m->selected_slot=r->binding.expected_slot;m->map_id=r->binding.expected_map_id;m->selection_generation=1;m->generation=1;m->scene_structures=1;m->last_command_valid=1;m->last_command=COH_REP_GROUPS;
    m->last_payload_bits=r->payload_bits;m->last_decoded_bytes=r->payload_bytes;m->scene_decoded_bytes=r->payload_bytes;m->last_byte_aligned=r->byte_aligned;m->scene_inspection=r->structure;return d;
}
static void reject(const CohWorldCaptureBinding*b,unsigned legacy,const CohNetOwnedMessage*m,size_t retained,size_t limit){
    CohWorldCapture*c=NULL;CohGroupsFailure f={0};CohWorldCaptureBinding oldb;CohNetOwnedMessage oldm;memcpy(&oldb,b,sizeof(oldb));memcpy(&oldm,m,sizeof(oldm));
    CHECK(coh_world_capture_stage(b,legacy,m,retained,limit,&c,&f)!=COH_OK);CHECK(!c);CHECK(!memcmp(b,&oldb,sizeof(oldb)));CHECK(!memcmp(m,&oldm,sizeof(oldm)));
}
static void aliases(const CaptureFixture*f){
    CohWorldCaptureBinding b=binding(f),oldb;CohNetOwnedMessage m=message(f),oldm;
    CohWorldCapture*c=NULL;CohGroupsFailure failure={0};
    memcpy(&oldb,&b,sizeof(b));memcpy(&oldm,&m,sizeof(m));
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,(CohWorldCapture**)&b,&failure)==COH_INVALID);
    CHECK(!memcmp(&b,&oldb,sizeof(b))&&!memcmp(&m,&oldm,sizeof(m)));
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,(CohWorldCapture**)&m,&failure)==COH_INVALID);
    CHECK(!memcmp(&m,&oldm,sizeof(m)));
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,(CohGroupsFailure*)&b)==COH_INVALID);
    CHECK(!memcmp(&b,&oldb,sizeof(b))&&!c);
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,(CohGroupsFailure*)&m)==COH_INVALID);
    CHECK(!memcmp(&m,&oldm,sizeof(m))&&!c);
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,(CohGroupsFailure*)&c)==COH_INVALID&&!c);
    m.payload=(const uint8_t*)&b;
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&failure)==COH_INVALID&&!c);
    m.payload=(const uint8_t*)&m;
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&failure)==COH_INVALID&&!c);
    m.payload=(const uint8_t*)&c;
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&failure)==COH_INVALID&&!c);
    m.payload=(const uint8_t*)&failure;
    CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&failure)==COH_INVALID&&!c);
    m=oldm;CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&failure)==COH_OK&&c);
    CohWorldCaptureReceipt receipt,before;CohBytes view={0};
    CHECK(coh_world_capture_view(c,&receipt,&view)==COH_OK);memcpy(&before,&receipt,sizeof(before));
    CHECK(coh_world_capture_view(c,&receipt,(CohBytes*)&receipt)==COH_INVALID);CHECK(!memcmp(&before,&receipt,sizeof(before)));
    CHECK(coh_world_capture_view(c,(CohWorldCaptureReceipt*)c,&view)==COH_INVALID);
    CHECK(coh_world_capture_view(c,&receipt,(CohBytes*)c)==COH_INVALID);
    CHECK(coh_world_capture_view(c,&receipt,&view)==COH_OK);CHECK(!memcmp(&before,&receipt,sizeof(before)));
    CHECK(view.size==f->bytes&&!memcmp(view.data,f->data,f->bytes));coh_world_capture_free(c);
}
int main(void){
    unsigned accepted=0;size_t peak=0;
    for(size_t i=0;i<sizeof(capture_fixtures)/sizeof(*capture_fixtures);i++){
        const CaptureFixture*f=&capture_fixtures[i];CohWorldCaptureBinding b=binding(f);CohNetOwnedMessage m=message(f);CohWorldCapture*c=NULL;CohGroupsFailure failure={0};
        CohStatus s=coh_world_capture_stage(&b,f->legacy,&m,12345,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&failure);
        if(!f->admit){CHECK(s!=COH_OK&&!c);continue;}
        CHECK(s==COH_OK&&c);accepted++;aliases(f);CohWorldCaptureReceipt r;CohBytes view;CHECK(coh_world_capture_view(c,&r,&view)==COH_OK);
        CHECK(view.size==f->bytes&&!memcmp(view.data,f->data,f->bytes));CHECK(r.payload_bits==f->bits&&r.byte_aligned==f->aligned&&r.transport_lease_generation==29);
        CHECK(r.structure.consumed_bits==f->bits&&r.structure.new_world==1);CHECK(r.aggregate_bytes==12345+f->bytes+r.owned_bytes+COH_WORLD_CAPTURE_STACK_RESERVE);
        if(r.aggregate_bytes>peak)peak=r.aggregate_bytes;
        CohLocalDiagnostics d=confirmed(&r);CHECK(coh_world_capture_confirm(c,&d)==COH_OK);
#define BAD(field,value) do{CohLocalDiagnostics v;memcpy(&v,&d,sizeof(v));v.field=(value);CHECK(coh_world_capture_confirm(c,&v)==COH_STATE);}while(0)
        BAD(phase,COH_LOCAL_IDLE);BAD(last_status,COH_OK);BAD(local_development_auth,0);BAD(server_identity_bound,0);BAD(terminal_failure,1);BAD(generation,2);BAD(selection_generation,2);BAD(character_choices,2);BAD(map_handoffs,2);
        BAD(map_protocol.selected_dbid,721);BAD(map_protocol.character_identity_verified,1);BAD(map_protocol.selected_slot,4);BAD(map_protocol.map_id,2);BAD(map_protocol.generation,2);BAD(map_protocol.selection_generation,2);BAD(map_protocol.scene_structures,2);BAD(map_protocol.last_command,COH_REP_ALLENTS);BAD(map_protocol.last_payload_bits,0);BAD(map_protocol.last_decoded_bytes,0);BAD(map_protocol.scene_decoded_bytes,0);BAD(map_protocol.last_byte_aligned,!r.byte_aligned);BAD(map_protocol.scene_failure.stage,1);BAD(map_protocol.scene_failure.status,COH_INVALID);BAD(map_protocol.scene_failure.bit_offset,1);BAD(map_protocol.udp.link.owned_retained_bytes,1);BAD(map_protocol.scene_inspection.footer_defs_crc,r.structure.footer_defs_crc^1);
#undef BAD
        CohWorldCapture*same=c;CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&failure)==COH_STATE&&c==same);
        coh_world_capture_free(c);c=NULL;
        size_t exact=r.owned_bytes+f->bytes+COH_WORLD_CAPTURE_STACK_RESERVE;
        CHECK(coh_world_capture_stage(&b,f->legacy,&m,0,exact,&c,&failure)==COH_OK);coh_world_capture_free(c);c=NULL;
        reject(&b,f->legacy,&m,0,exact-1);reject(&b,f->legacy,&m,COH_WORLD_CAPTURE_AGGREGATE_MAX,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        CohWorldCaptureBinding bad=b;bad.footer_defs_crc^=1;reject(&bad,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        bad=b;bad.footer_refs_crc^=1;reject(&bad,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        bad=b;bad.expected_dbid=0;reject(&bad,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        bad=b;memset(bad.character_row_sha256,0,32);reject(&bad,f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        CohNetOwnedMessage wrong=m;wrong.generation=0;reject(&b,f->legacy,&wrong,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        wrong=m;wrong.payload_bytes++;reject(&b,f->legacy,&wrong,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        wrong=m;wrong.compressed=2;reject(&b,f->legacy,&wrong,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        reject(&b,!f->legacy,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);
        /* Every truncated logical length for <=16Kbit fixtures; larger fixtures
         * cover both endpoints and one length per4096bits, explicitly sampled. */
        for(uint32_t bit=0;bit<f->bits;bit++){
            if(f->bits>16384&&bit>128&&bit+128<f->bits&&bit%4096)continue;
            wrong=m;wrong.payload_bits=bit;wrong.payload_bytes=((size_t)bit+7)/8;reject(&b,f->legacy,&wrong,0,COH_WORLD_CAPTURE_AGGREGATE_MAX);truncations++;
        }
        uint8_t*copy=malloc(f->bytes);CHECK(copy);memcpy(copy,f->data,f->bytes);wrong=m;wrong.payload=copy;
        CHECK(coh_world_capture_stage(&b,f->legacy,&wrong,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&failure)==COH_OK);
        memset(copy,0xa5,f->bytes);free(copy);CHECK(coh_world_capture_view(c,&r,&view)==COH_OK&&!memcmp(view.data,f->data,f->bytes));coh_world_capture_free(c);
    }
    uint32_t random=0x72541;uint8_t bytes[256];
    const CaptureFixture*f=&capture_fixtures[0];CohWorldCaptureBinding b=binding(f);
    for(unsigned i=0;i<10000;i++){
        for(unsigned j=0;j<sizeof(bytes);j++){random=random*1664525u+1013904223u;bytes[j]=(uint8_t)(random>>24);}
        CohNetOwnedMessage m=message(f);m.payload=bytes;m.payload_bits=1+(random%2048);m.payload_bytes=(m.payload_bits+7)/8;m.compressed=i&1;
        CohWorldCapture*c=NULL;CohGroupsFailure error={0};CohStatus s=coh_world_capture_stage(&b,(i>>1)&1,&m,0,COH_WORLD_CAPTURE_AGGREGATE_MAX,&c,&error);
        CHECK(s!=COH_OK&&!c);mutations++;
    }
    printf("{\"passed\":true,\"checks\":%lu,\"truncation_samples\":%lu,\"randomized_inputs\":%lu,\"source_fixtures\":%zu,\"accepted_new_world_fixtures\":%u,\"peak_fixture_aggregate_bytes\":%zu,\"authentic_capture\":false,\"actor_identity\":false,\"world_ready\":false}\n",checks,truncations,mutations,sizeof(capture_fixtures)/sizeof(*capture_fixtures),accepted,peak);
    return 0;
}
