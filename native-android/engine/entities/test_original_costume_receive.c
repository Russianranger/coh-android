#include "coh_original_costume_receive.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;static CohOriginalCostumeWorkspace workspace;
static CohOriginalCostumeReport report;static const CohOriginalCostumeWorkspace zero_workspace;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"line%d %s\n",__LINE__,#v);exit(1);}}while(0)
typedef struct{uint8_t bytes[16384];size_t bit;unsigned mode;} Writer;
static void bits(Writer *w,unsigned n,uint32_t v){unsigned i;if(w->mode)n=(n+7)&~7u;for(i=0;i<n;i++){w->bytes[w->bit/8]|=((v>>i)&1)<<(w->bit%8);w->bit++;}}
static void pack(Writer *w,unsigned n,uint32_t v){if(w->mode){bits(w,32,v);return;}while(n<32&&v>=(1u<<n)-1){bits(w,n,(1u<<n)-1);v-=(1u<<n)-1;n=n*2>32?32:n*2;}bits(w,n,v);}
static void literal(Writer *w,const char *s){size_t i;bits(w,1,0);bits(w,1,s!=NULL);if(s){bits(w,1,0);for(i=0;;i++){bits(w,8,(unsigned char)s[i]);if(!s[i])break;}}}
static void header(Writer *w,unsigned extra,unsigned count,unsigned explicit_count,unsigned bodytype){unsigned i;bits(w,1,0);bits(w,1,0);pack(w,6,bodytype);bits(w,32,0);bits(w,1,0);bits(w,3,0);bits(w,1,extra);for(i=0;i<72;i++)bits(w,32,i);for(i=0;i<30;i++)bits(w,i==0||extra?32:6,0);bits(w,1,explicit_count);if(explicit_count)pack(w,4,count);}
static void nullpart(Writer *w){unsigned i;for(i=0;i<4;i++)literal(w,NULL);bits(w,1,0);for(i=0;i<2;i++){bits(w,1,0);bits(w,1,0);bits(w,32,0);}}
static CohStatus parse(Writer *w,unsigned parts){CohRepReader r={{w->bytes,(w->bit+7)/8},w->bit,0,w->mode,COH_REP_BOUNDED_MESSAGE_MAX},before=r;CohStatus s=coh_original_costume_receive(&r,parts,&workspace,&report);CHECK(!memcmp(&r,&before,sizeof(r)));CHECK(!memcmp(&workspace,&zero_workspace,sizeof(workspace)));return s;}
static void unknowns(unsigned mode){
 Writer w={{0},0,mode};size_t expected;header(&w,1,28,0,1);bits(&w,1,0);bits(&w,1,1);bits(&w,1,1);expected=w.bit;pack(&w,15,32767);CHECK(parse(&w,28)==COH_UNSUPPORTED);CHECK(report.failure_bit==expected&&report.field==COH_ORIGINAL_COSTUME_GEOM&&report.part_count==28&&report.dictionary_required==COH_ORIGINAL_COSTUME_STRINGS&&report.count_validated&&report.bodytype_validated&&!report.costume_complete);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,1,1,1);literal(&w,"geo");bits(&w,1,0);bits(&w,1,1);bits(&w,1,1);expected=w.bit;pack(&w,15,5);CHECK(parse(&w,28)==COH_UNSUPPORTED);CHECK(report.failure_bit==expected&&report.field==COH_ORIGINAL_COSTUME_TEX1&&report.strings_read==1&&report.string_cache_entries==1);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,1,1,1);for(unsigned i=0;i<4;i++)literal(&w,NULL);bits(&w,1,0);bits(&w,1,0);bits(&w,1,1);expected=w.bit;pack(&w,9,3);CHECK(parse(&w,28)==COH_UNSUPPORTED);CHECK(report.failure_bit==expected&&report.field==COH_ORIGINAL_COSTUME_COLOR&&report.dictionary_required==COH_ORIGINAL_COSTUME_PALETTE);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,1,1,1,1);nullpart(&w);bits(&w,1,1);bits(&w,1,1);expected=w.bit;pack(&w,8,3);CHECK(parse(&w,28)==COH_UNSUPPORTED);CHECK(report.failure_bit==expected&&report.field==COH_ORIGINAL_COSTUME_REGION&&report.dictionary_required==COH_ORIGINAL_COSTUME_EXTRA_STRINGS);
}
static void cases(unsigned mode){
 Writer w={{0},0,mode};size_t n,end;
 for(unsigned type=0;type<10;type++){memset(&w,0,sizeof(w));w.mode=mode;header(&w,1,0,1,type);CHECK(parse(&w,28)==(type<9?COH_OK:COH_INVALID));}
 memset(&w,0,sizeof(w));w.mode=mode;
 header(&w,1,0,1,1);end=w.bit;CHECK(parse(&w,28)==COH_OK);CHECK(report.costume_complete&&report.end_bit==end&&report.part_count==0&&report.count_validated);
 for(n=0;n<end;n++){w.bit=n;CHECK(parse(&w,28)!=COH_OK);CHECK(!report.costume_complete);}w.bit=end;
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,1,1,9);CHECK(parse(&w,28)==COH_INVALID);CHECK(!report.costume_complete&&!report.bodytype_validated);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,29,1,1);CHECK(parse(&w,28)==COH_INVALID);CHECK(report.part_count==29&&!report.count_validated);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,1,1,1);bits(&w,1,1);CHECK(parse(&w,28)==COH_INVALID);CHECK(!report.costume_complete);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,1,1,1);literal(&w,"g");literal(&w,"t");literal(&w,"u");bits(&w,1,1);bits(&w,2,3);CHECK(parse(&w,28)==COH_INVALID);CHECK(report.string_cache_entries==3);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,30,0,1);for(unsigned i=0;i<30;i++)nullpart(&w);CHECK(parse(&w,30)==COH_LIMIT);CHECK(report.string_cache_entries==119);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,1,1,1);{char s[261];memset(s,'x',259);s[259]=0;literal(&w,s);for(unsigned i=0;i<3;i++)literal(&w,NULL);bits(&w,1,0);for(unsigned i=0;i<2;i++){bits(&w,1,0);bits(&w,1,0);bits(&w,32,0);}CHECK(parse(&w,28)==COH_OK);CHECK(report.literal_strings==1);}
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,0,1,1,1);{char s[261];memset(s,'x',260);s[260]=0;literal(&w,s);CHECK(parse(&w,28)==COH_LIMIT);}
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,1,0,1,0xffffffffu);CHECK(parse(&w,28)==COH_LIMIT);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,1,0xffffffffu,1,1);CHECK(parse(&w,28)==COH_LIMIT);
 memset(&w,0,sizeof(w));w.mode=mode;header(&w,1,0,1,1);
 {size_t at=mode?2408:2349;uint32_t nan=0x7fc00000;for(unsigned i=0;i<32;i++){uint8_t mask=(uint8_t)(1u<<((at+i)%8));w.bytes[(at+i)/8]=(uint8_t)((w.bytes[(at+i)/8]&~mask)|(((nan>>i)&1)?mask:0));}CHECK(parse(&w,28)==COH_INVALID);}
 if(mode){memset(&w,0,sizeof(w));w.mode=1;header(&w,1,0,1,1);w.bytes[0]=2;CHECK(parse(&w,28)==COH_INVALID);}
}
static void api(void){
 uint8_t raw[16]={0};CohRepReader r={{raw,sizeof(raw)},128,0,0,0};CohOriginalCostumeReport old;
 memset(&report,0xa5,sizeof(report));old=report;CHECK(coh_original_costume_receive(&r,0,&workspace,&report)==COH_INVALID&&!memcmp(&report,&old,sizeof(old)));
 CHECK(coh_original_costume_receive(&r,31,&workspace,&report)==COH_INVALID&&!memcmp(&report,&old,sizeof(old)));
 CHECK(coh_original_costume_receive(&r,28,&workspace,(CohOriginalCostumeReport*)(void*)raw)==COH_INVALID);
 CHECK(coh_original_costume_receive(&r,28,&workspace,(CohOriginalCostumeReport*)(void*)&workspace)==COH_INVALID);
 r.bytes.data=(const uint8_t*)(uintptr_t)(UINTPTR_MAX-4);CHECK(coh_original_costume_receive(&r,28,&workspace,&report)==COH_INVALID);r.bytes.data=raw;
 CHECK(coh_original_costume_receive(&r,28,&workspace,(CohOriginalCostumeReport*)(uintptr_t)(UINTPTR_MAX-4))==COH_INVALID);
 r.compressed=1;r.cursor=1;CHECK(coh_original_costume_receive(&r,28,&workspace,&report)==COH_INVALID&&!memcmp(&report,&old,sizeof(old)));
}
static uint32_t word(FILE *f){uint8_t b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
int main(int argc,char **argv){
 FILE *f;unsigned scenarios;CHECK(argc==2);f=fopen(argv[1],"rb");CHECK(f!=NULL);scenarios=word(f);
 for(unsigned n=0;n<scenarios;n++){
  Writer w={{0},0,0};CohRepReader r;unsigned count,expected,mode,start;mode=word(f);start=word(f);count=word(f);expected=word(f);w.bit=word(f);CHECK(fread(w.bytes,1,(w.bit+7)/8,f)==(w.bit+7)/8);r=(CohRepReader){{w.bytes,(w.bit+7)/8},w.bit,start,mode,COH_REP_BOUNDED_MESSAGE_MAX};
  CHECK(coh_original_costume_receive(&r,count,&workspace,&report)==COH_OK);CHECK(report.costume_complete&&report.end_bit==w.bit&&report.part_count==expected&&report.parts_read==expected&&report.bodytype_validated&&report.count_validated);
 }
 CHECK(fgetc(f)==EOF);CHECK(fclose(f)==0);unknowns(0);unknowns(1);cases(0);cases(1);api();
 printf("{\"passed\":true,\"checks\":%u,\"original_sender_scenarios\":%u,\"workspace_bytes\":%zu,\"heap_allocations\":0,\"unknown_index_pack_read\":false,\"whole_entity_or_ack\":false}\n",checks,scenarios,sizeof(workspace));return 0;
}
