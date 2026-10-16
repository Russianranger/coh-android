#define _POSIX_C_SOURCE 200809L
#include "coh_local.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "groups-fixtures.h"
static uint64_t now_ms(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))exit(2);return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
int main(int argc,char **argv){
    if(argc!=2)return 2;
    unsigned long port=strtoul(argv[1],NULL,10);if(!port||port>65535)return 2;
    CohLocalConfig config=coh_local_default_config();config.local_development_enabled=1;
    config.db.transport.peer=(CohNetEndpoint){{127,0,0,1},(uint16_t)port};
    config.db.request_timeout_ms=config.map.application_timeout_ms=5000;
    CohLocal *local=coh_local_create(&config);if(!local)return 2;
    CohDbLogin policy;CohStatus status=coh_local_login_policy(&policy);uint64_t now=now_ms(),deadline=now+5000;
    if(status==COH_OK)status=coh_local_begin(local,&policy,"Fixture",1001,1002,now);
    unsigned selected=0;CohLocalDiagnostics d={0};
    while(status==COH_OK&&now<deadline){
        status=coh_local_service(local,now,(CohCancel){0});coh_local_diagnostics(local,&d);
        if(d.phase==COH_LOCAL_CHARACTERS_READY&&!selected){
            status=coh_local_choose_character(local,0,now);selected=1;
        }
        if(d.phase==COH_LOCAL_SCENE_INCOMPLETE)break;
        struct timespec pause={0,10000000};nanosleep(&pause,NULL);now=now_ms();
    }
    int ok=status==COH_UNSUPPORTED&&d.phase==COH_LOCAL_SCENE_INCOMPLETE&&d.character_lists==1&&d.character_choices==1&&
        d.map_handoffs==1&&d.map_protocol.scene_prefixes==1&&d.map_protocol.accepted_messages==2&&
        !d.map_protocol.character_identity_verified&&d.map_protocol.last_command==COH_REP_GROUPS&&
        d.map_protocol.last_decoded_bytes==sizeof(source_groups_large_world_byte_aligned)&&d.map_protocol.scene_decoded_bytes==sizeof(source_groups_large_world_byte_aligned)&&
        d.map_protocol.last_payload_bits==source_groups_large_world_byte_aligned_bits&&d.map_protocol.last_byte_aligned==1&&
        d.map_protocol.scene_structures==1&&d.map_protocol.scene_inspection.consumed_bits==source_groups_large_world_byte_aligned_bits&&
        !d.map_protocol.scene_failure.stage&&!d.map_protocol.scene_failure.bit_offset&&!d.map_protocol.scene_failure.status&&
        d.map_protocol.scene_inspection.files==source_groups_expected_files&&d.map_protocol.scene_inspection.present_files==source_groups_expected_present_files&&
        d.map_protocol.scene_inspection.defs==source_groups_expected_defs&&d.map_protocol.scene_inspection.children==source_groups_expected_children&&
        d.map_protocol.scene_inspection.roots==source_groups_expected_roots&&d.map_protocol.scene_inspection.properties==source_groups_expected_properties&&
        d.map_protocol.scene_inspection.swaps==source_groups_expected_swaps&&d.map_protocol.scene_inspection.raw_matrices==source_groups_expected_raw_matrices&&
        d.map_protocol.scene_inspection.packed_matrices==source_groups_expected_packed_matrices&&d.map_protocol.scene_inspection.footer_file_count==source_groups_expected_footer_file_count&&
        d.map_protocol.scene_inspection.footer_active_roots==source_groups_expected_footer_active_roots&&
        d.map_protocol.scene_inspection.footer_defs_crc==source_groups_expected_footer_defs_crc&&d.map_protocol.scene_inspection.footer_refs_crc==source_groups_expected_footer_refs_crc&&
        !d.map_protocol.udp.link.owned_retained_bytes&&d.map_protocol.udp.link.owned_high_water_bytes==sizeof(source_groups_large_world_byte_aligned);
    coh_local_close(local);coh_local_diagnostics(local,&d);
    ok=ok&&d.opened_sockets==2&&d.closed_sockets==2;
    printf("{\"passed\":%s,\"status\":%u,\"stage\":%u,\"command\":%u,\"phase\":%u,\"scripted_source_layout\":true,"
        "\"source_command_count\":915,\"large_body_fixture\":true,\"scene_tail_parsed\":true,\"scene_assets_resolved\":false,\"scene_crc_verified\":false,"
        "\"scene_decoded_bytes\":%u,\"scene_compressed_bytes\":%zu,\"owned_retained_bytes\":%zu,"
        "\"opened_sockets\":%llu,\"closed_sockets\":%llu,\"real_server_interoperability\":false}\n",
        ok?"true":"false",(unsigned)status,(unsigned)d.map_protocol.stage,d.map_protocol.last_command,
        (unsigned)d.phase,d.map_protocol.scene_decoded_bytes,d.map_protocol.udp.link.decode.compressed_bytes,
        d.map_protocol.udp.link.owned_retained_bytes,(unsigned long long)d.opened_sockets,(unsigned long long)d.closed_sockets);
    coh_local_destroy(local);return ok?0:1;
}
