#include "coh_initial_triggered_probe.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,cuts,mutations,invalid_arguments,formatter_checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint32_t word(FILE*f){unsigned char raw[4];CHECK(fread(raw,1,4,f)==4);return(uint32_t)raw[0]|(uint32_t)raw[1]<<8|(uint32_t)raw[2]<<16|(uint32_t)raw[3]<<24;}
static CohStatus parse(const CohRepReader*r,CohInitialTriggeredProbe*out){
 CohRepReader before=*r;unsigned char*bytes=malloc(r->bytes.size?r->bytes.size:1);CHECK(bytes);memcpy(bytes,r->bytes.data,r->bytes.size);CohStatus status=coh_initial_triggered_probe(r,out);CHECK(status!=COH_OK);CHECK(!memcmp(r,&before,sizeof(before)));CHECK(!memcmp(bytes,r->bytes.data,r->bytes.size));free(bytes);return status;
}
static void invalid(const CohRepReader*r,CohInitialTriggeredProbe*out){CohInitialTriggeredProbe before=*out;CHECK(coh_initial_triggered_probe(r,out)==COH_INVALID);CHECK(!memcmp(out,&before,sizeof(before)));invalid_arguments++;}
static void formatting(const CohInitialTriggeredProbe*report){
 char json[COH_INITIAL_TRIGGERED_REPORT_MAX],small[2];CohInitialTriggeredProbe empty={0};CHECK(coh_initial_triggered_probe_json(&empty,json,sizeof(json))==4&&!strcmp(json,"null"));
 int length=coh_initial_triggered_probe_json(report,json,sizeof(json));CHECK(length>0&&(size_t)length<sizeof(json));CHECK(strstr(json,"\"schema\":\"coh-initial-first-triggered-v1\"")&&strstr(json,"\"diagnostic_only\":true"));
 CHECK(strstr(json,"\"selected_owner_bound\":false")&&strstr(json,"\"source_generation_admitted\":false")&&strstr(json,"\"complete_initial_character\":false")&&strstr(json,"\"actor_publication\":false")&&strstr(json,"\"ack_permitted\":false")&&strstr(json,"\"world_authority\":false"));
 CHECK(!strstr(json,"\"move_index\"")&&!strstr(json,"\"ticks\"")&&!strstr(json,"\"fx_id\"")&&!strstr(json,"\"packet\"")&&!strstr(json,"909090")&&!strstr(json,"Fixture"));
 if(report->stage==COH_INITIAL_TRIGGERED_AI_ANIMATION)CHECK(strstr(json,"FIRST_AI_ANIMATION_REQUIRED"));
 CHECK(coh_initial_triggered_probe_json(report,small,sizeof(small))==length&&small[0]=='{'&&!small[1]);CHECK(coh_initial_triggered_probe_json(NULL,json,sizeof(json))<0&&coh_initial_triggered_probe_json(report,NULL,sizeof(json))<0&&coh_initial_triggered_probe_json(report,json,0)<0);
 CohInitialTriggeredProbe copy=*report;CHECK(coh_initial_triggered_probe_json(&copy,(char*)(void*)&copy,sizeof(copy))<0&&!memcmp(&copy,report,sizeof(copy)));formatter_checks++;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*stream=fopen(argv[1],"rb");if(!stream)return 2;uint32_t count=word(stream),complete=0;
 for(uint32_t fixture=0;fixture<count;fixture++){
  uint32_t row[16];for(unsigned i=0;i<16;i++)row[i]=word(stream);size_t bytes=row[0],bits=row[1];unsigned mode=row[2],variant=row[3],scenario=row[4];unsigned char*wire=malloc(bytes);CHECK(wire&&fread(wire,1,bytes,stream)==bytes);CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,(CohBytes){wire,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);reader.cursor=row[5];CohInitialTriggeredProbe report;memset(&report,0x5a,sizeof(report));CohStatus status=parse(&reader,&report);
  if(status!=(CohStatus)row[8]||report.stage!=(CohInitialTriggeredStage)row[9]){fprintf(stderr,"fixture%u mode%u variant%u scenario%u status%u/%u stage%u/%u bit%zu\n",fixture,mode,variant,scenario,status,row[8],report.stage,row[9],report.failure_bit);return 1;}
  CHECK(report.status==status&&report.begin_bit==row[5]&&report.failure_bit<=bits);CHECK(report.count==row[10]);CHECK(report.count_validated==row[11]);CHECK(report.entries_validated==row[12]);CHECK(report.current_entry==row[13]);CHECK(report.fx_entries==row[14]);CHECK(report.triggered_moves_validated==row[15]);
  if(report.count_validated)CHECK(report.count_end_bit==row[6]);
  if(report.triggered_moves_validated){CHECK(report.triggered_end_bit==row[7]);complete++;}
  formatting(&report);CohInitialTriggeredProbe again;memset(&again,0xa5,sizeof(again));CHECK(parse(&reader,&again)==status);CHECK(!memcmp(&again,&report,sizeof(report)));
  if(!variant){
   for(size_t end=reader.cursor;end<row[7];end++){CohRepReader shortened=reader;shortened.bits=end;CohInitialTriggeredProbe cut={0};CHECK(parse(&shortened,&cut)!=COH_OK);CHECK(!cut.triggered_moves_validated);cuts++;}
   for(size_t i=reader.cursor/8;i<bytes;i++){wire[i]^=0x81;CohInitialTriggeredProbe changed={0};CHECK(parse(&reader,&changed)!=COH_OK);wire[i]^=0x81;mutations++;}
  }
  if(!fixture){
   CohInitialTriggeredProbe untouched;memset(&untouched,0x5a,sizeof(untouched));invalid(NULL,&untouched);CHECK(coh_initial_triggered_probe(&reader,NULL)==COH_INVALID);invalid_arguments++;
   CohRepReader bad=reader;bad.cursor=bad.bits+1;invalid(&bad,&untouched);bad=reader;bad.compressed=2;invalid(&bad,&untouched);bad=reader;bad.bytes.data=NULL;invalid(&bad,&untouched);bad=reader;bad.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX+1u;invalid(&bad,&untouched);bad=reader;bad.compressed=1;bad.cursor=1;invalid(&bad,&untouched);
   CohRepReader saved=reader;CHECK(coh_initial_triggered_probe(&reader,(CohInitialTriggeredProbe*)(void*)&reader)==COH_INVALID&&!memcmp(&saved,&reader,sizeof(reader)));invalid_arguments++;
   unsigned char*copy=malloc(bytes);CHECK(copy);memcpy(copy,wire,bytes);CHECK(coh_initial_triggered_probe(&reader,(CohInitialTriggeredProbe*)(void*)wire)==COH_INVALID&&!memcmp(copy,wire,bytes));free(copy);invalid_arguments++;
  }
  free(wire);
 }
 CHECK(fgetc(stream)==EOF);fclose(stream);CHECK(count==131&&complete==117);
 printf("{\"checks\":%lu,\"fixtures\":%u,\"complete_triggered_observations\":%u,\"truncated_extents\":%lu,\"mutations\":%lu,\"invalid_argument_checks\":%lu,\"formatter_checks\":%lu,\"ai_animation_parsed\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,count,complete,cuts,mutations,invalid_arguments,formatter_checks);return 0;
}
