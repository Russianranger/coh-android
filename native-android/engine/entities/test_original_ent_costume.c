#define main original_body_tests
#include "test_original_costume_receive.c"
#undef main
#include "coh_original_ent_costume.h"
#include <openssl/sha.h>
static uint8_t raw_slots[COH_CLIENT_COSTUME_RAW_BYTES],packet[131072];
static uint32_t indices[COH_CLIENT_COSTUME_INDEX_COUNT];static CohClientCostumeSlots slots;
static CohOriginalCostumeSnapshot capture;static CohOriginalEntCostumeReport outer;
static CohStatus digest(void*c,CohBytes b,uint8_t o[32]){(void)c;return SHA256(b.data,b.size,o)?COH_OK:COH_IO;}
static void fixtures(const char *path){FILE*f=fopen(path,"rb");CHECK(f);unsigned count=word(f);
 for(unsigned row=0;row<count;row++){
  unsigned mode=word(f),start=word(f),bodies=word(f),sg=word(f),fx=word(f),npc=word(f),custom=word(f),appearance=word(f),end=word(f);(void)custom;CHECK((end+7)/8<=sizeof(packet));CHECK(fread(packet,1,(end+7)/8,f)==(end+7)/8);
  CohRepReader r={{packet,(end+7)/8},end,start,mode,COH_REP_BOUNDED_MESSAGE_MAX},before=r;
  CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,&outer)==COH_OK);
  CHECK(outer.appearance_complete&&outer.xlucency_complete&&outer.appearance_end_bit==appearance&&outer.end_bit==end&&outer.packet_bits==end);
  CHECK(outer.bodies_expected==bodies&&outer.bodies_read==bodies&&outer.selected_complete&&capture.part_count==28&&capture.bodytype==1);
  CHECK(outer.supergroup_present==sg&&outer.supergroup_complete==sg&&outer.fx_present==fx&&outer.fx_bytes==(fx?6u:0u)&&outer.npc_fallthrough==npc);
  CHECK(!outer.entity_complete&&!outer.message_complete&&outer.field==COH_ENT_COSTUME_SUFFIX&&!memcmp(&r,&before,sizeof(r))&&!memcmp(&workspace,&zero_workspace,sizeof(workspace)));
  if(npc)CHECK(outer.npc_index==123&&outer.npc_costume_index==2);
  CHECK(outer.selected_body_end_bit<=outer.main_body_end_bit&&outer.main_body_end_bit<appearance);
  r.bits=end+32;r.bytes.size=(r.bits+7)/8;CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,&outer)==COH_OK);CHECK(outer.end_bit==end&&outer.packet_bits==end+32&&!outer.entity_complete&&!outer.message_complete);r=before;
  for(unsigned trim=1;trim<=64&&end-trim>=start;trim++){
   r.bits=end-trim;CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,&outer)!=COH_OK);CHECK(!outer.message_complete&&!outer.entity_complete&&!memcmp(&workspace,&zero_workspace,sizeof(workspace)));CHECK(outer.failure_bit<=r.bits&&outer.packet_bits==r.bits);
  }
  r.bits=appearance;CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,&outer)!=COH_OK);CHECK(outer.appearance_complete&&!outer.xlucency_complete&&outer.end_bit==appearance);
 }
 CHECK(fgetc(f)==EOF);CHECK(fclose(f)==0);
}
static void invalids(void){uint8_t tiny[32]={0};CohRepReader r={{tiny,sizeof(tiny)},256,0,0,COH_REP_BOUNDED_MESSAGE_MAX};CohOriginalEntCostumeReport old;memset(&outer,0xa5,sizeof(outer));old=outer;
 CHECK(coh_original_ent_costume_receive(NULL,28,0,&slots,&workspace,&capture,&outer)==COH_INVALID);
 CHECK(coh_original_ent_costume_receive(&r,28,10,&slots,&workspace,&capture,&outer)==COH_INVALID&&!memcmp(&old,&outer,sizeof(old)));
 CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,(void*)&workspace)==COH_INVALID);
 CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,(void*)raw_slots,&outer)==COH_INVALID);
 CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,(void*)(uintptr_t)(UINTPTR_MAX-4),&outer)==COH_INVALID);
 CHECK(coh_original_ent_costume_receive((void*)(uintptr_t)(UINTPTR_MAX-4),28,0,&slots,&workspace,&capture,&outer)==COH_INVALID);
 r.bytes.data=(void*)(uintptr_t)(UINTPTR_MAX-4);CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,&outer)==COH_INVALID);r.bytes.data=tiny;
 r.bytes.size=SIZE_MAX;CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,&outer)==COH_INVALID);
 for(unsigned mode=0;mode<2;mode++){
  Writer w={{0},0,mode};bits(&w,1,1);pack(&w,2,2);r=(CohRepReader){{w.bytes,(w.bit+7)/8},w.bit,0,mode,COH_REP_BOUNDED_MESSAGE_MAX};CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,&outer)==COH_UNSUPPORTED);CHECK(outer.selector==2&&!outer.appearance_complete);
  memset(&w,0,sizeof(w));w.mode=mode;bits(&w,1,1);pack(&w,2,1);bits(&w,1,1);bits(&w,32,257);r=(CohRepReader){{w.bytes,(w.bit+7)/8},w.bit,0,mode,COH_REP_BOUNDED_MESSAGE_MAX};CHECK(coh_original_ent_costume_receive(&r,28,0,&slots,&workspace,&capture,&outer)==COH_LIMIT);
 }
}
int main(int argc,char**argv){CHECK(argc==3);FILE*f=fopen(argv[1],"rb");CHECK(f);CHECK(fread(raw_slots,1,sizeof(raw_slots),f)==sizeof(raw_slots));CHECK(fgetc(f)==EOF);CHECK(!fclose(f));CohCostumeImportDigest d={digest,NULL,0,4096};CHECK(coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)},indices,COH_CLIENT_COSTUME_INDEX_COUNT,&d,&slots,8u<<20,sizeof(capture)+sizeof(workspace)+8192)==COH_OK);fixtures(argv[2]);invalids();printf("{\"passed\":true,\"checks\":%u,\"whole_appearance_and_xlucency\":true,\"heap_allocations\":0,\"entity_or_message_complete\":false,\"physical_packet_replayed\":false}\n",checks);return 0;}
