#include "coh_original_taskforce_receive.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/sha.h>
static unsigned checks;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"line%d %s\n",__LINE__,#v);exit(1);}}while(0)
static uint8_t raw[COH_CLIENT_COSTUME_RAW_BYTES],packet[131072];static uint32_t index_slots[COH_CLIENT_COSTUME_INDEX_COUNT];
static CohClientCostumeSlots slots;static CohOriginalCostumeWorkspace workspace,zero_workspace;static CohOriginalTaskforceReport report;
static uint32_t word(FILE*f){uint8_t b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static CohStatus digest(void*c,CohBytes b,uint8_t o[32]){(void)c;return SHA256(b.data,b.size,o)?COH_OK:COH_IO;}
static void scenarios(const char*path){FILE*f=fopen(path,"rb");CHECK(f);unsigned count=word(f);
 for(unsigned row=0;row<count;row++){
  unsigned mode=word(f),start=word(f),scenario=word(f),end=word(f),bodyend=word(f);CHECK((end+7)/8<=sizeof(packet));CHECK(fread(packet,1,(end+7)/8,f)==(end+7)/8);
  CohRepReader r={{packet,(end+7)/8},end,start,mode,COH_REP_BOUNDED_MESSAGE_MAX},before=r;CohStatus wanted=scenario==8||scenario==9?COH_LIMIT:scenario==10?COH_UNSUPPORTED:COH_OK;
  CHECK(coh_original_taskforce_receive(&r,28,scenario==10?NULL:&slots,&workspace,&report)==wanted);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&workspace,&zero_workspace,sizeof(workspace)));
  if(wanted!=COH_OK){CHECK(!report.complete&&report.end_bit<=end);if(scenario==10)CHECK(report.field==COH_ORIGINAL_TASKFORCE_BODY&&report.body.dictionary_required==COH_ORIGINAL_COSTUME_STRINGS);continue;}
  CHECK(report.complete&&report.end_bit==end&&report.packet_bits==end&&report.on_architect==(scenario>=2)&&report.on_flashback==scenario%2&&report.field==COH_ORIGINAL_TASKFORCE_COMPLETE);
  CHECK(report.body_count==(scenario==2||scenario==5));if(report.body_count)CHECK(report.body.costume_complete&&report.body.end_bit==bodyend&&report.body.parts_read==28);
  CHECK(report.custom_parts==(scenario==3?63u:0u));CHECK(report.review_present==(scenario==4||scenario==7));
  if(scenario==4)CHECK(report.review_bytes[0]==255&&report.review_bytes[1]==127&&report.review_bytes[2]==4095);
  uint32_t mask=scenario==0?0:scenario==7?UINT32_MAX:(1u<<1)|(1u<<23)|(1u<<31);CHECK(report.parameter_mask==mask);for(unsigned i=0;i<32;i++)CHECK(report.parameters[i]==((mask&(1u<<i))?(i*1023u-(i==1||i==23?10u:0u)):0));
  r.bits=end+32;r.bytes.size=(r.bits+7)/8;CHECK(coh_original_taskforce_receive(&r,28,&slots,&workspace,&report)==COH_OK);CHECK(report.end_bit==end&&report.packet_bits==end+32);r=before;
  for(unsigned trim=1;trim<=32&&end-trim>=start;trim++){r.bits=end-trim;CHECK(coh_original_taskforce_receive(&r,28,&slots,&workspace,&report)!=COH_OK);CHECK(!report.complete&&report.failure_bit<=r.bits&&!memcmp(&workspace,&zero_workspace,sizeof(workspace)));}
 }
 CHECK(fgetc(f)==EOF);CHECK(!fclose(f));
}
static void invalids(void){uint8_t tiny[32]={0};CohRepReader r={{tiny,sizeof(tiny)},256,0,0,COH_REP_BOUNDED_MESSAGE_MAX};CohOriginalTaskforceReport saved;memset(&report,0xa5,sizeof(report));saved=report;
 CHECK(coh_original_taskforce_receive(NULL,28,&slots,&workspace,&report)==COH_INVALID);CHECK(coh_original_taskforce_receive(&r,0,&slots,&workspace,&report)==COH_INVALID);CHECK(coh_original_taskforce_receive(&r,31,&slots,&workspace,&report)==COH_INVALID);
 CHECK(coh_original_taskforce_receive(&r,28,&slots,&workspace,(void*)&workspace)==COH_INVALID);CHECK(coh_original_taskforce_receive(&r,28,&slots,(void*)raw,&report)==COH_INVALID);CHECK(coh_original_taskforce_receive((void*)(uintptr_t)(UINTPTR_MAX-4),28,&slots,&workspace,&report)==COH_INVALID);
 CHECK(coh_original_taskforce_receive(&r,28,&slots,&workspace,(void*)(uintptr_t)(UINTPTR_MAX-4))==COH_INVALID);CHECK(coh_original_taskforce_receive((void*)(tiny+1),28,&slots,&workspace,&report)==COH_INVALID);CHECK(!memcmp(&report,&saved,sizeof(report)));
 r.bytes.size=SIZE_MAX;CHECK(coh_original_taskforce_receive(&r,28,&slots,&workspace,&report)==COH_INVALID);r.bytes.size=sizeof(tiny);r.compressed=1;r.cursor=1;CHECK(coh_original_taskforce_receive(&r,28,&slots,&workspace,&report)==COH_INVALID);
}
int main(int argc,char**argv){CHECK(argc==3);FILE*f=fopen(argv[1],"rb");CHECK(f);CHECK(fread(raw,1,sizeof(raw),f)==sizeof(raw));CHECK(fgetc(f)==EOF);CHECK(!fclose(f));CohCostumeImportDigest d={digest,NULL,0,4096};CHECK(coh_client_costume_slots_prepare((CohBytes){raw,sizeof(raw)},index_slots,COH_CLIENT_COSTUME_INDEX_COUNT,&d,&slots,8u<<20,sizeof(workspace)+sizeof(report)+16384)==COH_OK);scenarios(argv[2]);invalids();printf("{\"passed\":true,\"checks\":%u,\"body_workspace\":%zu,\"report_bytes\":%zu,\"source_parameter_bit31\":true,\"heap_allocations\":0,\"physical_packet_replayed\":false,\"entity_or_ACK\":false}\n",checks,sizeof(workspace),sizeof(report));return 0;}
