#include "coh_initial_aianim_probe.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,cuts,mutations,invalid_arguments,formatter_checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint32_t word(FILE*f){unsigned char raw[4];CHECK(fread(raw,1,4,f)==4);return(uint32_t)raw[0]|(uint32_t)raw[1]<<8|(uint32_t)raw[2]<<16|(uint32_t)raw[3]<<24;}
static CohStatus parse(const CohRepReader*r,CohInitialAiAnimProbe*out){CohRepReader before=*r;unsigned char*bytes=malloc(r->bytes.size?r->bytes.size:1);CHECK(bytes);memcpy(bytes,r->bytes.data,r->bytes.size);CohStatus status=coh_initial_aianim_probe(r,out);CHECK(status!=COH_OK);CHECK(!memcmp(r,&before,sizeof(before)));CHECK(!memcmp(bytes,r->bytes.data,r->bytes.size));free(bytes);return status;}
static void invalid(const CohRepReader*r,CohInitialAiAnimProbe*out){CohInitialAiAnimProbe before=*out;CHECK(coh_initial_aianim_probe(r,out)==COH_INVALID);CHECK(!memcmp(out,&before,sizeof(before)));invalid_arguments++;}
static void formatting(const CohInitialAiAnimProbe*report){
 char json[COH_INITIAL_AIANIM_REPORT_MAX],small[2];CohInitialAiAnimProbe empty={0};CHECK(coh_initial_aianim_probe_json(&empty,json,sizeof(json))==4&&!strcmp(json,"null"));int length=coh_initial_aianim_probe_json(report,json,sizeof(json));CHECK(length>0&&(size_t)length<sizeof(json));CHECK(strstr(json,"\"schema\":\"coh-initial-first-aianim-v1\"")&&strstr(json,"\"diagnostic_only\":true"));
 CHECK(strstr(json,"\"selected_owner_bound\":false")&&strstr(json,"\"source_generation_admitted\":false")&&strstr(json,"\"complete_initial_character\":false")&&strstr(json,"\"actor_publication\":false")&&strstr(json,"\"ack_permitted\":false")&&strstr(json,"\"world_authority\":false"));CHECK(!strstr(json,"FixtureAnim")&&!strstr(json,"AAAA")&&!strstr(json,"\"text\"")&&!strstr(json,"\"packet\"")&&!strstr(json,"909090"));
 if(report->stage==COH_INITIAL_AIANIM_NETFX)CHECK(strstr(json,"FIRST_NETFX_REQUIRED"));
 CHECK(coh_initial_aianim_probe_json(report,small,sizeof(small))==length&&small[0]=='{'&&!small[1]);CHECK(coh_initial_aianim_probe_json(NULL,json,sizeof(json))<0&&coh_initial_aianim_probe_json(report,NULL,sizeof(json))<0&&coh_initial_aianim_probe_json(report,json,0)<0);CohInitialAiAnimProbe copy=*report;CHECK(coh_initial_aianim_probe_json(&copy,(char*)(void*)&copy,sizeof(copy))<0&&!memcmp(&copy,report,sizeof(copy)));formatter_checks++;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*stream=fopen(argv[1],"rb");if(!stream)return 2;uint32_t count=word(stream),complete=0;
 for(uint32_t fixture=0;fixture<count;fixture++){
  uint32_t row[13];for(unsigned i=0;i<13;i++)row[i]=word(stream);size_t bytes=row[0],bits=row[1];unsigned mode=row[2],variant=row[3],scenario=row[4];unsigned char*wire=malloc(bytes);CHECK(wire&&fread(wire,1,bytes,stream)==bytes);CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,(CohBytes){wire,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);reader.cursor=row[5];CohInitialAiAnimProbe report;memset(&report,0x5a,sizeof(report));CohStatus status=parse(&reader,&report);
  if(status!=(CohStatus)row[7]||report.stage!=(CohInitialAiAnimStage)row[8]){fprintf(stderr,"fixture%u mode%u variant%u scenario%u status%u/%u stage%u/%u bit%zu bytes%u/%u\n",fixture,mode,variant,scenario,status,row[7],report.stage,row[8],report.failure_bit,report.string_bytes,row[11]);return 1;}
  CHECK(report.status==status&&report.begin_bit==row[5]&&report.failure_bit<=bits);CHECK(report.update_seen==row[9]);CHECK(report.string_present==row[10]);CHECK(report.string_bytes==row[11]);CHECK(report.ai_animation_validated==row[12]);if(report.ai_animation_validated){CHECK(report.ai_end_bit==row[6]);complete++;}
  formatting(&report);CohInitialAiAnimProbe again;memset(&again,0xa5,sizeof(again));CHECK(parse(&reader,&again)==status);CHECK(!memcmp(&again,&report,sizeof(report)));
  if(!variant){for(size_t end=reader.cursor;end<row[6];end++){CohRepReader shortened=reader;shortened.bits=end;CohInitialAiAnimProbe cut={0};CHECK(parse(&shortened,&cut)!=COH_OK);CHECK(!cut.ai_animation_validated);cuts++;}for(size_t i=reader.cursor/8;i<bytes;i++){wire[i]^=0x81;CohInitialAiAnimProbe changed={0};CHECK(parse(&reader,&changed)!=COH_OK);wire[i]^=0x81;mutations++;}}
  if(!fixture){CohInitialAiAnimProbe untouched;memset(&untouched,0x5a,sizeof(untouched));invalid(NULL,&untouched);CHECK(coh_initial_aianim_probe(&reader,NULL)==COH_INVALID);invalid_arguments++;CohRepReader bad=reader;bad.cursor=bad.bits+1;invalid(&bad,&untouched);bad=reader;bad.compressed=2;invalid(&bad,&untouched);bad=reader;bad.bytes.data=NULL;invalid(&bad,&untouched);bad=reader;bad.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX+1u;invalid(&bad,&untouched);bad=reader;bad.compressed=1;bad.cursor=1;invalid(&bad,&untouched);CohRepReader saved=reader;CHECK(coh_initial_aianim_probe(&reader,(CohInitialAiAnimProbe*)(void*)&reader)==COH_INVALID&&!memcmp(&saved,&reader,sizeof(reader)));invalid_arguments++;unsigned char*copy=malloc(bytes);CHECK(copy);memcpy(copy,wire,bytes);CHECK(coh_initial_aianim_probe(&reader,(CohInitialAiAnimProbe*)(void*)wire)==COH_INVALID&&!memcmp(copy,wire,bytes));free(copy);invalid_arguments++;}
  free(wire);
 }
 CHECK(fgetc(stream)==EOF);fclose(stream);CHECK(count==89&&complete==65);printf("{\"checks\":%lu,\"fixtures\":%u,\"complete_ai_observations\":%u,\"truncated_extents\":%lu,\"mutations\":%lu,\"invalid_argument_checks\":%lu,\"formatter_checks\":%lu,\"netfx_parsed\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,count,complete,cuts,mutations,invalid_arguments,formatter_checks);return 0;
}
