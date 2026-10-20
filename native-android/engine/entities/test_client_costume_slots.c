/* Original sender fixtures plus exact CLIENT primary slots. */
#define main original_literal_test_main
#include "test_original_costume_receive.c"
#undef main
#include <openssl/sha.h>
static uint8_t raw_slots[COH_CLIENT_COSTUME_RAW_BYTES];
static uint32_t slot_index[COH_CLIENT_COSTUME_INDEX_COUNT],saved_index[COH_CLIENT_COSTUME_INDEX_COUNT];
static CohClientCostumeSlots slots,saved_slots;
static uint8_t list_raw[131072];
static unsigned digests;
static CohStatus digest(void *context,CohBytes bytes,uint8_t out[32]){(void)context;digests++;return SHA256(bytes.data,bytes.size,out)?COH_OK:COH_INVALID;}
static CohCostumeImportDigest provider={digest,NULL,0,4096};
static CohStatus prepare(size_t budget,size_t retained){return coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)},slot_index,COH_CLIENT_COSTUME_INDEX_COUNT,&provider,&slots,budget,retained);}
static void unchanged(void){CHECK(!memcmp(slot_index,saved_index,sizeof(slot_index)));CHECK(!memcmp(&slots,&saved_slots,sizeof(slots)));}
static void bad_inputs(void){
 CohCostumeImportDigest bad=provider;size_t charge=slots.charged_bytes;uint8_t old;unsigned calls=digests;
 memcpy(saved_index,slot_index,sizeof(slot_index));saved_slots=slots;
 CHECK(prepare(charge-1,0)==COH_LIMIT);unchanged();CHECK(digests==calls);
 CHECK(prepare(8u<<20,SIZE_MAX)==COH_LIMIT);unchanged();CHECK(digests==calls);
 CHECK(prepare((8u<<20)+1,0)==COH_LIMIT);unchanged();
 CHECK(coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)-1},slot_index,COH_CLIENT_COSTUME_INDEX_COUNT,&provider,&slots,8u<<20,0)==COH_INVALID);unchanged();
 CHECK(coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)},slot_index,SIZE_MAX,&provider,&slots,8u<<20,0)==COH_INVALID);unchanged();
 CHECK(coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)},(uint32_t*)(void*)raw_slots,COH_CLIENT_COSTUME_INDEX_COUNT,&provider,&slots,8u<<20,0)==COH_INVALID);unchanged();
 CHECK(coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)},slot_index,COH_CLIENT_COSTUME_INDEX_COUNT,&provider,(CohClientCostumeSlots*)(void*)slot_index,8u<<20,0)==COH_INVALID);unchanged();
 bad.context=raw_slots;bad.context_bytes=1;CHECK(coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)},slot_index,COH_CLIENT_COSTUME_INDEX_COUNT,&bad,&slots,8u<<20,0)==COH_INVALID);unchanged();
 bad=provider;bad.scratch_reserve=SIZE_MAX;CHECK(coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)},slot_index,COH_CLIENT_COSTUME_INDEX_COUNT,&bad,&slots,8u<<20,0)==COH_LIMIT);unchanged();
 old=raw_slots[8];raw_slots[8]=2;CHECK(prepare(8u<<20,0)==COH_INVALID);raw_slots[8]=old;unchanged();
 /* First present string begins at slot_index[first]+4; change spelling only. */
 {uint32_t i=0;while(!slot_index[i])i++;old=raw_slots[slot_index[i]+4];raw_slots[slot_index[i]+4]^=1;CHECK(prepare(8u<<20,0)==COH_STATE);raw_slots[slot_index[i]+4]=old;unchanged();}
 CHECK(prepare(charge,0)==COH_OK);CHECK(slots.charged_bytes==charge);
}
static CohStatus parse_slots(Writer *w){
 CohRepReader r={{w->bytes,(w->bit+7)/8},w->bit,0,w->mode,COH_REP_BOUNDED_MESSAGE_MAX},before=r;
 CohStatus status=coh_original_costume_receive_slots(&r,28,&slots,&workspace,&report);
 CHECK(!memcmp(&r,&before,sizeof(r)));CHECK(!memcmp(&workspace,&zero_workspace,sizeof(workspace)));return status;
}
static void index_string(Writer *w,unsigned index,unsigned extra){if(!extra)bits(w,1,0);bits(w,1,1);bits(w,1,1);pack(w,extra?8:15,index);}
static void index_color(Writer *w,unsigned index){bits(w,1,0);bits(w,1,1);pack(w,9,index);}
static unsigned found(unsigned base,unsigned capacity,unsigned present){unsigned i=0;while(i<capacity&&!!slot_index[base+i]!=!!present)i++;CHECK(i<capacity);return i;}
static void indexed_cases(unsigned mode){
 Writer w={{0},0,mode};unsigned ordinary=found(0,32768,1),extra=found(32768,256,1),palette=found(33024,512,1),hole=found(0,32768,0),palette_hole=found(33024,512,0);CohClientCostumeSlots bad;CohRepReader reader;CohOriginalCostumeReport before;
 header(&w,1,1,1,1);index_string(&w,ordinary,0);index_string(&w,hole,0);index_string(&w,32768,0);literal(&w,NULL);bits(&w,1,0);index_color(&w,palette);index_color(&w,palette_hole);index_string(&w,extra,1);index_string(&w,256,1);
 CHECK(parse_slots(&w)==COH_OK);CHECK(report.costume_complete&&report.end_bit==w.bit&&report.parts_read==1&&report.strings_read==4&&report.colors_read==2&&report.literal_strings==0);
 reader=(CohRepReader){{w.bytes,(w.bit+7)/8},w.bit,0,w.mode,COH_REP_BOUNDED_MESSAGE_MAX};before=report;
 bad=slots;bad.index=(const uint32_t*)(const void*)(raw_slots+1);CHECK(coh_original_costume_receive_slots(&reader,28,&bad,&workspace,&report)==COH_INVALID);CHECK(!memcmp(&before,&report,sizeof(report)));
 bad=slots;bad.raw.data=(const uint8_t*)(uintptr_t)(UINTPTR_MAX-4);CHECK(coh_original_costume_receive_slots(&reader,28,&bad,&workspace,&report)==COH_INVALID);
 CHECK(coh_original_costume_receive_slots(&reader,28,(const CohClientCostumeSlots*)(const void*)&workspace,&workspace,&report)==COH_INVALID);
 {uint32_t old=slot_index[ordinary];slot_index[ordinary]=COH_CLIENT_COSTUME_RAW_BYTES;CHECK(parse_slots(&w)==COH_INVALID);slot_index[ordinary]=old;}
 for(size_t n=0,end=w.bit;n<end;n++){w.bit=n;CHECK(parse_slots(&w)!=COH_OK);CHECK(!report.costume_complete);w.bit=end;}
}
int main(int argc,char **argv){
 FILE *f;unsigned scenarios,lists,complete=0;CHECK(argc==5);f=fopen(argv[1],"rb");CHECK(f!=NULL);CHECK(fread(raw_slots,1,sizeof(raw_slots),f)==sizeof(raw_slots));CHECK(fgetc(f)==EOF);CHECK(fclose(f)==0);
 CHECK(prepare(8u<<20,0)==COH_OK);bad_inputs();
 f=fopen(argv[2],"rb");CHECK(f!=NULL);scenarios=word(f);
 for(unsigned n=0;n<scenarios;n++){
  Writer w={{0},0,0};CohRepReader r;unsigned count,expected,mode,start;mode=word(f);start=word(f);count=word(f);expected=word(f);w.bit=word(f);CHECK(fread(w.bytes,1,(w.bit+7)/8,f)==(w.bit+7)/8);r=(CohRepReader){{w.bytes,(w.bit+7)/8},w.bit,start,mode,COH_REP_BOUNDED_MESSAGE_MAX};
  if(expected){CHECK(coh_original_costume_receive(&r,count,&workspace,&report)==COH_UNSUPPORTED);CHECK(report.dictionary_required==COH_ORIGINAL_COSTUME_STRINGS);}
  CHECK(coh_original_costume_receive_slots(&r,count,&slots,&workspace,&report)==COH_OK);CHECK(report.costume_complete&&report.end_bit==w.bit&&report.part_count==expected&&report.parts_read==expected&&report.bodytype_validated&&report.count_validated&&report.literal_strings==0);complete++;
 }
 CHECK(fgetc(f)==EOF);CHECK(fclose(f)==0);indexed_cases(0);indexed_cases(1);
 f=fopen(argv[3],"rb");CHECK(f!=NULL);lists=word(f);
 for(unsigned n=0;n<lists;n++){
  CohRepReader reader;unsigned mode=word(f),start=word(f),bodies=word(f),parts=word(f),ends[10],bits=word(f);CHECK(bodies>=2&&bodies<=10&&bits<=sizeof(list_raw)*8);
  for(unsigned i=0;i<bodies;i++)ends[i]=word(f);
  CHECK(fread(list_raw,1,(bits+7)/8,f)==(bits+7)/8);
  reader=(CohRepReader){{list_raw,(bits+7)/8},bits,start,mode,COH_REP_BOUNDED_MESSAGE_MAX};
  for(unsigned i=0;i<bodies;i++){
   CohRepReader before=reader;CHECK(coh_original_costume_receive_slots(&reader,28,&slots,&workspace,&report)==COH_OK);
   CHECK(!memcmp(&reader,&before,sizeof(reader)));CHECK(!memcmp(&workspace,&zero_workspace,sizeof(workspace)));
   CHECK(report.costume_complete&&report.part_count==parts&&report.parts_read==parts&&report.begin_bit==reader.cursor&&report.end_bit==ends[i]);reader.cursor=report.end_bit;
  }
  CHECK(reader.cursor==bits);
  /* Truncate each later body: earlier complete bodies remain consumed, and
   * callers must stop on the exact first incomplete body, without skipping. */
  for(unsigned truncated=0;truncated<bodies;truncated++){
   unsigned read=0;reader.cursor=start;reader.bits=ends[truncated]-1;
   for(unsigned i=0;i<bodies;i++){
    CohStatus status=coh_original_costume_receive_slots(&reader,28,&slots,&workspace,&report);
    if(status!=COH_OK){CHECK(!report.costume_complete&&report.failure_bit<=reader.bits);break;}
    CHECK(report.costume_complete&&report.end_bit==ends[i]);read++;reader.cursor=report.end_bit;
   }
   CHECK(read==truncated);
  }
 }
 CHECK(fgetc(f)==EOF);CHECK(fclose(f)==0);
 f=fopen(argv[4],"wb");CHECK(f!=NULL);for(unsigned i=0;i<COH_CLIENT_COSTUME_INDEX_COUNT;i++){uint32_t v=slot_index[i];uint8_t b[4]={(uint8_t)v,(uint8_t)(v>>8),(uint8_t)(v>>16),(uint8_t)(v>>24)};CHECK(fwrite(b,1,4,f)==4);}CHECK(fclose(f)==0);
 printf("{\"passed\":true,\"checks\":%u,\"whole_original_indexed_sender_scenarios\":%u,\"multiple_body_scenarios\":%u,\"raw_bytes\":%u,\"index_bytes\":%zu,\"charged_prepare_bytes\":%zu,\"heap_allocations\":0,\"physical_packet_replayed\":false}\n",checks,complete,lists,COH_CLIENT_COSTUME_RAW_BYTES,(size_t)COH_CLIENT_COSTUME_INDEX_BYTES,slots.charged_bytes);return 0;
}
