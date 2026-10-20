#include "coh_original_rare_receive.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,fixtures;
#define CHECK(v)do{checks++;if(!(v)){fprintf(stderr,"line%d %s\n",__LINE__,#v);exit(1);}}while(0)
static CohOriginalRareWorkspace workspace;static const CohOriginalRareWorkspace zero_workspace;static CohOriginalRareReport report,actual;
static unsigned char packet[524288];
static uint32_t word(FILE*f){uint8_t b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static uint64_t le64(const uint8_t*p){uint64_t v=0;for(unsigned i=0;i<8;i++)v|=(uint64_t)p[i]<<(8*i);return v;}
static int wiped(void){return!memcmp(&workspace,&zero_workspace,sizeof(workspace));}
static void tailbits(size_t start){for(unsigned i=0;i<32;i++){size_t at=start+i;uint8_t mask=(uint8_t)(1u<<(at%8));packet[at/8]=(uint8_t)((packet[at/8]&~mask)|(((0xdeadbeefu>>i)&1)?mask:0));}}
static void source_fixtures(const char*path){FILE*f=fopen(path,"rb");CHECK(f);fixtures=word(f);CHECK(word(f)==sizeof(CohEntRarePrefix));
 for(unsigned row=0;row<fixtures;row++){
  unsigned mode=word(f),begin=word(f),scenario=word(f),wanted=word(f),stage=word(f),prefixend=word(f),tailend=word(f),end=word(f);(void)scenario;CohEntRarePrefix expected;CHECK(fread(&expected,1,sizeof(expected),f)==sizeof(expected));CHECK((end+7)/8+4<=sizeof(packet));CHECK(fread(packet,1,(end+7)/8,f)==(end+7)/8);
  CohRepReader r={{packet,(end+7)/8},end,begin,mode,COH_REP_BOUNDED_MESSAGE_MAX},before=r;CohStatus status=coh_original_rare_receive(&r,&workspace,&report,8u<<20,0);
  if(status!=(CohStatus)wanted)fprintf(stderr,"scenario%u mode%u status%u wanted%u stage%u end%zu\n",scenario,mode,status,wanted,report.stage,report.end_bit);
  CHECK(status==(CohStatus)wanted);CHECK(report.status==status&&report.stage==stage&&!memcmp(&r,&before,sizeof(r))&&wiped());CHECK(report.prefix_complete&&report.prefix_end_bit==prefixend&&report.power_crc_present==expected.power_present&&report.power_crc==expected.power_crc);
  if(status!=COH_OK){CHECK(!report.entity_suffix_complete&&report.failure_bit==(stage==2?prefixend:tailend)&&!report.failure_cursor_exact);continue;}
  CHECK(report.rare_complete&&report.buffs_complete&&report.entity_suffix_complete&&report.rare_end_bit==tailend&&report.end_bit==end&&report.packet_bits==end&&report.failure_cursor_exact);
  tailbits(end);r.bits=end+32;r.bytes.size=(r.bits+7)/8;CHECK(coh_original_rare_receive(&r,&workspace,&report,8u<<20,0)==COH_OK);CHECK(report.end_bit==end&&report.packet_bits==end+32&&wiped());r=before;
  size_t boundaries[]={prefixend-1,prefixend,tailend-1,tailend};for(unsigned i=0;i<4;i++){r.bits=boundaries[i];CHECK(coh_original_rare_receive(&r,&workspace,&report,8u<<20,0)!=COH_OK);CHECK(!report.entity_suffix_complete&&report.failure_bit<=r.bits&&wiped());}
  for(unsigned trim=1;trim<=8&&end-trim>=begin;trim++){r.bits=end-trim;CHECK(coh_original_rare_receive(&r,&workspace,&report,8u<<20,0)!=COH_OK);CHECK(!report.entity_suffix_complete&&report.failure_bit<=r.bits&&wiped());}
  r=before;size_t needed=sizeof(r)+sizeof(workspace)+sizeof(report)+r.bytes.size+COH_ORIGINAL_RARE_STACK_RESERVE;CohOriginalRareReport old=report;CHECK(coh_original_rare_receive(&r,&workspace,&report,needed-1,0)==COH_LIMIT);CHECK(!memcmp(&old,&report,sizeof(old))&&wiped());CHECK(coh_original_rare_receive(&r,&workspace,&report,needed,0)==COH_OK);CHECK(coh_original_rare_receive(&r,&workspace,&report,8u<<20,SIZE_MAX)==COH_LIMIT);
 }
 CHECK(fgetc(f)==EOF);CHECK(!fclose(f));
}
static void invalid(void){uint8_t raw[32]={0};CohRepReader r={{raw,sizeof(raw)},256,0,0,COH_REP_BOUNDED_MESSAGE_MAX};memset(&report,0xa5,sizeof(report));CohOriginalRareReport before=report;
 CHECK(coh_original_rare_receive(NULL,&workspace,&report,8u<<20,0)==COH_INVALID);CHECK(coh_original_rare_receive(&r,NULL,&report,8u<<20,0)==COH_INVALID);CHECK(coh_original_rare_receive(&r,&workspace,NULL,8u<<20,0)==COH_INVALID);CHECK(coh_original_rare_receive(&r,&workspace,&report,0,0)==COH_INVALID);CHECK(coh_original_rare_receive(&r,&workspace,&report,(8u<<20)+1,0)==COH_INVALID);
 CHECK(coh_original_rare_receive(&r,&workspace,(void*)&workspace,8u<<20,0)==COH_INVALID);CHECK(coh_original_rare_receive(&r,(void*)raw,&report,8u<<20,0)==COH_INVALID);CHECK(coh_original_rare_receive((void*)(uintptr_t)(UINTPTR_MAX-4),&workspace,&report,8u<<20,0)==COH_INVALID);CHECK(coh_original_rare_receive(&r,&workspace,(void*)(uintptr_t)(UINTPTR_MAX-4),8u<<20,0)==COH_INVALID);
 r.bytes.data=(void*)&workspace;r.bytes.size=sizeof(workspace);CHECK(coh_original_rare_receive(&r,&workspace,&report,8u<<20,0)==COH_INVALID);r.bytes.data=raw;r.bytes.size=SIZE_MAX;CHECK(coh_original_rare_receive(&r,&workspace,&report,8u<<20,0)==COH_INVALID);r.bytes.size=sizeof(raw);r.compressed=1;r.cursor=1;CHECK(coh_original_rare_receive(&r,&workspace,&report,8u<<20,0)==COH_INVALID);CHECK(!memcmp(&before,&report,sizeof(report))&&wiped());
}
static void replay(const char*path,const char*begin){FILE*f=fopen(path,"rb");CHECK(f);uint8_t h[88];CHECK(fread(h,1,88,f)==88&&!memcmp(h,"COHIRP01",8));size_t bytes=fread(packet,1,sizeof(packet),f);CHECK(fgetc(f)==EOF);CHECK(!fclose(f));size_t bits=(size_t)le64(h+16),at=(size_t)strtoull(begin,NULL,10);CHECK(bytes<=65536&&bits<=bytes*8&&at<bits&&h[40]<=1);CohRepReader r={{packet,bytes},bits,at,h[40],COH_REP_BOUNDED_MESSAGE_MAX};CHECK(coh_original_rare_receive(&r,&workspace,&actual,8u<<20,0)==COH_OK);CHECK(actual.entity_suffix_complete&&actual.prefix_complete&&actual.rare_complete&&actual.buffs_complete&&actual.end_bit<=bits&&wiped());}
int main(int argc,char**argv){CHECK(argc==2||argc==4);source_fixtures(argv[1]);invalid();if(argc==4)replay(argv[2],argv[3]);printf("{\"passed\":true,\"checks\":%u,\"fixtures\":%u,\"workspace_bytes\":%zu,\"report_bytes\":%zu,\"heap_allocations\":0,\"message_or_ACK\":false,\"actual_replay\":{\"supplied\":%s,\"status\":%u,\"stage\":%u,\"begin\":%zu,\"prefix_end\":%zu,\"rare_end\":%zu,\"end\":%zu,\"packet_bits\":%zu,\"suffix_complete\":%u,\"buffs\":%u,\"mods\":%u}}\n",checks,fixtures,sizeof(workspace),sizeof(report),argc==4?"true":"false",actual.status,actual.stage,actual.begin_bit,actual.prefix_end_bit,actual.rare_end_bit,actual.end_bit,actual.packet_bits,actual.entity_suffix_complete,actual.buff_count,actual.buff_mod_count);return 0;}
