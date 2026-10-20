#include "coh_original_ent_costume.h"
#include "coh_original_rare_receive.h"
#include "coh_original_initial_tail.h"
#include "coh_original_command_tail.h"
#include "../initial-capture/coh_initial_pose_probe.h"
#include "../initial-capture/coh_initial_sequence_probe.h"
#include "../initial-capture/coh_initial_triggered_probe.h"
#include "../initial-capture/coh_initial_aianim_probe.h"
#include "../initial-capture/coh_initial_netfx_probe.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/sha.h>
static uint8_t raw[COH_CLIENT_COSTUME_RAW_BYTES],packet[65536];
static uint32_t indices[COH_CLIENT_COSTUME_INDEX_COUNT];
static CohClientCostumeSlots slots;static CohOriginalCostumeWorkspace w;
static CohOriginalCostumeSnapshot snapshot;static CohOriginalEntCostumeReport report;
static CohOriginalRareWorkspace rare_work;static CohOriginalRareReport rare;
static CohOriginalInitialTailReport tail;
static CohInitialPoseProbe pose;static CohInitialSequenceProbe sequence;
static CohInitialTriggeredProbe triggered;static CohInitialAiAnimProbe ai;
static CohInitialNetFxProbe fx;
static CohOriginalCommandTailWorkspace commands_work;static CohOriginalCommandTailReport commands;
static CohStatus digest(void*c,CohBytes b,uint8_t out[32]){(void)c;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
static uint32_t le32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t le64(const uint8_t*p){return(uint64_t)le32(p)|(uint64_t)le32(p+4)<<32;}
int main(int argc,char**argv){
 if(argc!=5)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f||fread(raw,1,sizeof(raw),f)!=sizeof(raw)||fgetc(f)!=EOF)return 3;fclose(f);
 f=fopen(argv[2],"rb");uint8_t header[88],hash[32];if(!f||fread(header,1,88,f)!=88||memcmp(header,"COHIRP01",8)||le32(header+8)!=88||le32(header+12)>sizeof(packet))return 4;
 size_t bytes=le32(header+12);if(fread(packet,1,bytes,f)!=bytes||fgetc(f)!=EOF)return 5;fclose(f);SHA256(packet,bytes,hash);if(memcmp(hash,header+56,32))return 6;
 const size_t owners=sizeof(raw)+sizeof(indices)+sizeof(slots)+sizeof(w)+sizeof(snapshot)+sizeof(report)+sizeof(packet)+sizeof(rare_work)+sizeof(rare)+sizeof(tail)+sizeof(commands_work)+sizeof(commands)+sizeof(pose)+sizeof(sequence)+sizeof(triggered)+sizeof(ai)+sizeof(fx);
 const size_t budget=8u<<20;
 if(owners>budget-COH_ORIGINAL_INITIAL_STACK_RESERVE)return 7;
 CohCostumeImportDigest d={digest,NULL,0,4096};
 if(coh_client_costume_slots_prepare((CohBytes){raw,sizeof(raw)},indices,COH_CLIENT_COSTUME_INDEX_COUNT,&d,&slots,budget,owners-sizeof(raw)-sizeof(indices)-sizeof(slots)+COH_ORIGINAL_INITIAL_STACK_RESERVE)!=COH_OK)return 7;
 if(le32(header+52)!=COH_REP_ALLENTS||le64(header+24)>le64(header+32))return 10;
 char*endarg=NULL;unsigned long long create_end=strtoull(argv[3],&endarg,10);if(!*argv[3]||*endarg||create_end>SIZE_MAX)return 10;
 unsigned long previous=strtoul(argv[4],&endarg,10);if(!*argv[4]||*endarg||previous>COH_ENT_INDEX_MAX)return 10;
 CohRepReader r={{packet,bytes},le64(header+16),(size_t)create_end,le32(header+40),COH_REP_BOUNDED_MESSAGE_MAX};
 /* The earlier header/self-create prefix is independently accepted physical
  * context from the same hashed report/payload. Reuse all qualified source
  * leaves after it and derive each next cursor/flag; never scan for a value.
  * Packet ordinal1 is fresh host ordering scratch, not a live message ID. */
 (void)coh_initial_pose_probe(&r,1,&pose);if(!pose.pose_validated)return 10;r.cursor=pose.pose_end_bit;
 (void)coh_initial_sequence_probe(&r,&sequence);if(!sequence.sequence_validated)return 10;r.cursor=sequence.sequence_end_bit;
 (void)coh_initial_triggered_probe(&r,&triggered);if(!triggered.triggered_moves_validated)return 10;r.cursor=triggered.triggered_end_bit;
 (void)coh_initial_aianim_probe(&r,&ai);if(!ai.ai_animation_validated)return 10;r.cursor=ai.ai_end_bit;
 (void)coh_initial_netfx_probe(&r,&fx);if(!fx.netfx_validated||fx.netfx_end_bit!=le64(header+32))return 10;r.cursor=fx.netfx_end_bit;
 CohStatus s=coh_original_ent_costume_receive_initial(&r,le32(header+48),le32(header+44),fx.pchar_things,&slots,&w,&snapshot,&report);
 size_t end=report.end_bit;
 if(s==COH_OK&&report.taskforce_complete){
  r.cursor=end;s=coh_original_rare_receive(&r,&rare_work,&rare,budget,owners-sizeof(rare_work)-sizeof(rare)-bytes);
  end=rare.end_bit;
  if(s==COH_OK&&rare.entity_suffix_complete){
   r.cursor=end;s=coh_original_initial_tail(&r,(uint32_t)previous,1,&tail,budget,owners-sizeof(tail)-bytes);end=tail.end_bit;
   if(s==COH_OK&&tail.source_tail_complete){
    r.cursor=end;s=coh_original_command_tail_receive(&r,&commands_work,&commands,budget,owners-sizeof(commands_work)-sizeof(commands)-bytes);end=commands.end_bit;
   }
  }
 }
 printf("{\"status\":%u,\"end_bit\":%zu,\"packet_bits\":%zu,\"body_end\":%zu,\"appearance_end\":%zu,\"power_begin\":%zu,\"power_end\":%zu,\"power_entry_count\":%u,\"power_entries_read\":%u,\"power_unresolved_count\":%u,\"first_crc\":%u,\"last_crc\":%u,\"required_table\":%u,\"power_complete\":%u,\"taskforce_complete\":%u,\"outer_end_bit\":%zu,\"entity_end_bit\":%zu,\"source_tail_end_bit\":%zu,\"character_complete\":%u,\"commands_read\":%u,\"command_tail_complete\":%u,\"source_command_terminator\":%u,\"exact_saved_end\":%u,\"retained_static_owners\":%zu,\"peak_aggregate_bytes\":%zu,\"accepted_prefix_end_bit\":%zu,\"derived_appearance_begin_bit\":%zu,\"actual_pchar_things\":%u}\n",s,end,report.packet_bits,report.selected_body_end_bit,report.appearance_end_bit,report.power_begin_bit,report.power_end_bit,report.power_entry_count,report.power_entries_read,report.power_unresolved_count,report.power_first_unresolved_crc,report.power_last_unresolved_crc,report.required_table,report.power_complete,report.taskforce_complete,report.end_bit,rare.end_bit,tail.end_bit,tail.character_complete,commands.commands_read,commands.tail_complete,commands.terminator,(unsigned)(s==COH_OK&&commands.tail_complete&&commands.terminator&&end==r.bits),owners,tail.peak_aggregate_bytes,(size_t)create_end,fx.netfx_end_bit,fx.pchar_things);
 f=fopen("/tmp/coh-thor-016-costume-snapshot.bin","wb");if(!f||fwrite(&snapshot,1,sizeof(snapshot),f)!=sizeof(snapshot))return 8;fclose(f);return s==COH_OK?0:9;
}
