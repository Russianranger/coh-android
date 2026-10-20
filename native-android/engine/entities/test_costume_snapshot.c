/* Existing whole-original sender fixtures plus pointer-free decoded capture. */
#define main retained_original_receiver_tests
#include "test_original_costume_receive.c"
#undef main
#include <openssl/sha.h>
static uint8_t raw_slots[COH_CLIENT_COSTUME_RAW_BYTES];
static uint32_t offsets[COH_CLIENT_COSTUME_INDEX_COUNT];
static CohClientCostumeSlots slots;
static CohOriginalCostumeSnapshot snapshot,previous;
static CohStatus digest(void *context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
static uint32_t raw_word(const uint8_t *p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static const uint8_t *ordinal(unsigned table,unsigned nth){unsigned begin=table==0?0:table==1?32768:33024,end=table==0?32768:table==1?33024:33536;for(unsigned i=begin;i<end;i++)if(offsets[i]&&nth--==0)return raw_slots+offsets[i];CHECK(0);return NULL;}
static void string_value(const CohOriginalCostumeSnapshotPart *p,unsigned field,const char *literal_value,unsigned table,unsigned index,int indexed){
 const char *value=p->strings[field];CHECK(p->present_mask&(1u<<field));
 if(indexed){const uint8_t *r=ordinal(table,index);CHECK(strlen(value)==raw_word(r)&&!memcmp(value,r+4,raw_word(r)));}
 else {if(strcmp(value,literal_value))fprintf(stderr,"field%u value=[%s] expected=[%s] indexed=%d\n",field,value,literal_value,indexed);CHECK(!strcmp(value,literal_value));}
}
static void fixtures(const char *name,unsigned indexed){
 FILE *f=fopen(name,"rb");CHECK(f);unsigned count=word(f);
 for(unsigned row=0;row<count;row++){
  uint8_t bytes[16384];unsigned mode=word(f),begin=word(f),parts=word(f),expected=word(f),end=word(f);CHECK((end+7)/8<=sizeof(bytes));CHECK(fread(bytes,1,(end+7)/8,f)==(end+7)/8);
  CohRepReader reader={{bytes,(end+7)/8},end,begin,mode,COH_REP_BOUNDED_MESSAGE_MAX},before=reader;
  memset(&snapshot,0xa5,sizeof(snapshot));
  CHECK(coh_original_costume_receive_slots_capture(&reader,parts,&slots,&workspace,&report,&snapshot)==COH_OK);
  CHECK(report.costume_complete&&snapshot.bodytype==1&&snapshot.part_count==expected&&report.end_bit==end);
  CHECK(!memcmp(&reader,&before,sizeof(reader))&&!memcmp(&workspace,&zero_workspace,sizeof(workspace)));
  CHECK(snapshot.header_present==0||snapshot.header_present==3);
  if(snapshot.header_present){
   if(indexed){const uint8_t *a=ordinal(0,0),*b=ordinal(0,1);CHECK(strlen(snapshot.ent_type)==raw_word(a)&&!memcmp(snapshot.ent_type,a+4,raw_word(a)));CHECK(strlen(snapshot.geometry_prefix)==raw_word(b)&&!memcmp(snapshot.geometry_prefix,b+4,raw_word(b)));}
   else CHECK(!strcmp(snapshot.ent_type,"FixtureEntity")&&!strcmp(snapshot.geometry_prefix,"Male"));
  }else CHECK(!snapshot.ent_type[0]&&!snapshot.geometry_prefix[0]);
  for(unsigned i=0;i<expected;i++){
   const CohOriginalCostumeSnapshotPart *p=&snapshot.parts[i];
   string_value(p,0,"FixtureGeometry",0,2+i*4,indexed);string_value(p,1,"InlineTexture",0,3+i*4,indexed);string_value(p,2,"InlineTexture",0,4+i*4,indexed);
   if(i%2)string_value(p,3,"GlowFX",0,5+i*4,indexed);else string_value(p,3,indexed?"none":"None",0,0,0);
   if(p->present_mask&16){string_value(p,4,"Upper",1,i%4,indexed);string_value(p,5,"BodySet",1,4+i%4,indexed);}else CHECK(!(p->present_mask&32)&&!p->strings[4][0]&&!p->strings[5][0]);
   for(unsigned j=0;j<4;j++)CHECK(p->colors[j]==((i%2||j<2)?(indexed?raw_word(ordinal(2,j)):0x12340000u+j):0));
  }
  previous=snapshot;
  for(unsigned trim=1;trim<=32&&trim<=end-begin;trim++){
   reader.bits=end-trim;CHECK(coh_original_costume_receive_slots_capture(&reader,parts,&slots,&workspace,&report,&snapshot)!=COH_OK);
   CHECK(!memcmp(&snapshot,&previous,sizeof(snapshot))&&!memcmp(&workspace,&zero_workspace,sizeof(workspace)));
  }
 }
 CHECK(fgetc(f)==EOF);CHECK(fclose(f)==0);
}
static void bodytypes_and_aliases(void){
 for(unsigned mode=0;mode<2;mode++)for(unsigned body=0;body<9;body++){
  Writer w={{0},0,mode};header(&w,1,1,1,body);nullpart(&w);bits(&w,1,0);bits(&w,1,0);
  CohRepReader r={{w.bytes,(w.bit+7)/8},w.bit,0,mode,COH_REP_BOUNDED_MESSAGE_MAX};
  CHECK(coh_original_costume_receive_slots_capture(&r,28,NULL,&workspace,&report,&snapshot)==COH_OK);
  CHECK(snapshot.bodytype==body&&snapshot.part_count==1&&!snapshot.header_present&&!snapshot.parts[0].present_mask);
  for(unsigned family=0;family<6;family++)for(unsigned i=0;i<6;i++){CHECK(snapshot.super_colors[family][i].SGBitSetLow==i*12+family*2);CHECK(snapshot.super_colors[family][i].SGBitSetHigh==i*12+family*2+1);}
  previous=snapshot;CohOriginalCostumeReport saved=report;
  CHECK(coh_original_costume_receive_slots_capture(&r,28,NULL,&workspace,&report,(CohOriginalCostumeSnapshot*)(void*)&workspace)==COH_INVALID);
  CHECK(!memcmp(&saved,&report,sizeof(report))&&!memcmp(&workspace,&zero_workspace,sizeof(workspace)));
  CHECK(coh_original_costume_receive_slots_capture(&r,28,&slots,&workspace,&report,(CohOriginalCostumeSnapshot*)(void*)raw_slots)==COH_INVALID);
  CHECK(coh_original_costume_receive_slots_capture(&r,28,&slots,&workspace,(CohOriginalCostumeReport*)(void*)&snapshot,&snapshot)==COH_INVALID);
  CHECK(coh_original_costume_receive_slots_capture(&r,28,&slots,&workspace,&report,(CohOriginalCostumeSnapshot*)(uintptr_t)(UINTPTR_MAX-3))==COH_INVALID);
  CHECK(!memcmp(&snapshot,&previous,sizeof(snapshot)));
 }
}
int main(int argc,char **argv){
 CHECK(argc==4);FILE *f=fopen(argv[1],"rb");CHECK(f);CHECK(fread(raw_slots,1,sizeof(raw_slots),f)==sizeof(raw_slots));CHECK(fgetc(f)==EOF);CHECK(fclose(f)==0);
 CohCostumeImportDigest provider={digest,NULL,0,4096};CHECK(coh_client_costume_slots_prepare((CohBytes){raw_slots,sizeof(raw_slots)},offsets,COH_CLIENT_COSTUME_INDEX_COUNT,&provider,&slots,8u<<20,sizeof(snapshot)+sizeof(workspace))==COH_OK);
 fixtures(argv[2],0);fixtures(argv[3],1);bodytypes_and_aliases();
 printf("{\"passed\":true,\"checks\":%u,\"body_types\":9,\"snapshot_bytes\":%zu,\"workspace_bytes\":%zu,\"snapshot_heap_allocations\":0,\"physical_packet_replayed\":false}\n",checks,sizeof(snapshot),sizeof(workspace));return 0;
}
