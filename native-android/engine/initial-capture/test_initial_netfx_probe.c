#include "coh_initial_netfx_probe.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,cuts,mutations,invalid_arguments,formatter_checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint32_t word(FILE*f){unsigned char raw[4];CHECK(fread(raw,1,4,f)==4);return(uint32_t)raw[0]|(uint32_t)raw[1]<<8|(uint32_t)raw[2]<<16|(uint32_t)raw[3]<<24;}
static CohStatus parse(const CohRepReader*r,CohInitialNetFxProbe*out){
 CohRepReader before=*r;unsigned char*bytes=malloc(r->bytes.size?r->bytes.size:1);CHECK(bytes);memcpy(bytes,r->bytes.data,r->bytes.size);
 CohStatus status=coh_initial_netfx_probe(r,out);CHECK(status!=COH_OK);CHECK(!memcmp(r,&before,sizeof(before)));CHECK(!memcmp(bytes,r->bytes.data,r->bytes.size));free(bytes);return status;
}
static void invalid(const CohRepReader*r,CohInitialNetFxProbe*out){CohInitialNetFxProbe before=*out;CHECK(coh_initial_netfx_probe(r,out)==COH_INVALID);CHECK(!memcmp(out,&before,sizeof(before)));invalid_arguments++;}
static void formatting(const CohInitialNetFxProbe*report){
 char json[COH_INITIAL_NETFX_REPORT_MAX],small[2];CohInitialNetFxProbe empty={0};CHECK(coh_initial_netfx_probe_json(&empty,json,sizeof(json))==4&&!strcmp(json,"null"));
 int length=coh_initial_netfx_probe_json(report,json,sizeof(json));CHECK(length>0&&(size_t)length<sizeof(json));
 CHECK(strstr(json,"\"schema\":\"coh-initial-first-netfx-v1\"")&&strstr(json,"\"diagnostic_only\":true"));
 CHECK(strstr(json,"\"cross_prefix_in_phase_verified\":false")&&strstr(json,"\"selected_owner_bound\":false")&&strstr(json,"\"source_generation_admitted\":false")&&strstr(json,"\"complete_initial_character\":false")&&strstr(json,"\"actor_publication\":false")&&strstr(json,"\"ack_permitted\":false")&&strstr(json,"\"world_authority\":false"));
 CHECK(!strstr(json,"\"handle\"")&&!strstr(json,"\"net_id\"")&&!strstr(json,"\"trigger_fx\"")&&!strstr(json,"\"origin\"")&&!strstr(json,"\"target\"")&&!strstr(json,"\"packet\"")&&!strstr(json,"12345")&&!strstr(json,"Fixture"));
 if(report->stage==COH_INITIAL_NETFX_COSTUME)CHECK(strstr(json,"FIRST_COSTUME_BODY_REQUIRED"));
 CHECK(coh_initial_netfx_probe_json(report,small,sizeof(small))==length&&small[0]=='{'&&!small[1]);
 CHECK(coh_initial_netfx_probe_json(NULL,json,sizeof(json))<0&&coh_initial_netfx_probe_json(report,NULL,sizeof(json))<0&&coh_initial_netfx_probe_json(report,json,0)<0);
 CohInitialNetFxProbe copy=*report;CHECK(coh_initial_netfx_probe_json(&copy,(char*)(void*)&copy,sizeof(copy))<0&&!memcmp(&copy,report,sizeof(copy)));formatter_checks++;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*stream=fopen(argv[1],"rb");if(!stream)return 2;uint32_t count=word(stream),complete=0;
 for(uint32_t fixture=0;fixture<count;fixture++){
  uint32_t row[17];for(unsigned i=0;i<17;i++)row[i]=word(stream);size_t bytes=row[0],bits=row[1];unsigned mode=row[2],variant=row[3];
  unsigned char*wire=malloc(bytes);CHECK(wire&&fread(wire,1,bytes,stream)==bytes);CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,(CohBytes){wire,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);reader.cursor=row[5];
  CohInitialNetFxProbe report;memset(&report,0x5a,sizeof(report));CohStatus status=parse(&reader,&report);
  if(status!=(CohStatus)row[8]||report.stage!=(CohInitialNetFxStage)row[9]){fprintf(stderr,"fixture%u mode%u variant%u status%u/%u stage%u/%u bit%zu\n",fixture,mode,variant,status,row[8],report.stage,row[9],report.failure_bit);return 1;}
  CHECK(report.status==status&&report.begin_bit==row[5]&&report.failure_bit<=bits);CHECK(report.pchar_things==row[10]&&report.in_phase==row[11]&&report.body_present==row[12]);
  CHECK(report.effect_count==row[13]&&report.netfx_validated==row[14]);CHECK(report.entity_failure.status==(CohStatus)row[15]);
  if(report.entity_failure.status!=COH_OK)CHECK(report.entity_failure.stage==COH_ENT_STAGE_NETFX&&report.entity_failure.bit==report.failure_bit);
  else CHECK(!report.entity_failure.stage&&!report.entity_failure.bit);
  if(report.stage!=COH_INITIAL_NETFX_FLAGS)CHECK(report.flags_end_bit==row[6]);
  else CHECK(!report.flags_end_bit);
  if(report.netfx_validated){CHECK(report.netfx_end_bit==row[7]);complete++;}
  else CHECK(!report.netfx_end_bit&&!report.effect_count);
  formatting(&report);CohInitialNetFxProbe again;memset(&again,0xa5,sizeof(again));CHECK(parse(&reader,&again)==status&&!memcmp(&again,&report,sizeof(report)));
  if(!variant){
   for(size_t end=reader.cursor;end<row[7];end++){CohRepReader shortened=reader;shortened.bits=end;CohInitialNetFxProbe cut={0};CHECK(parse(&shortened,&cut)!=COH_OK);CHECK(!cut.netfx_validated);cuts++;}
   for(size_t i=reader.cursor/8;i<bytes;i++){wire[i]^=0x81;CohInitialNetFxProbe changed={0};CHECK(parse(&reader,&changed)!=COH_OK);wire[i]^=0x81;mutations++;}
   if(report.body_present){CohRepReader child=reader;child.cursor=report.flags_end_bit;CohEntNetFxList effects={0};CohEntFailure failure={0};CHECK(coh_ent_netfx(&child,&effects,&failure)==COH_OK);CHECK(child.cursor==report.netfx_end_bit&&effects.count==report.effect_count);memset(&effects,0,sizeof(effects));}
  }
  if(!fixture){
   CohInitialNetFxProbe untouched;memset(&untouched,0x5a,sizeof(untouched));invalid(NULL,&untouched);CHECK(coh_initial_netfx_probe(&reader,NULL)==COH_INVALID);invalid_arguments++;
   CohRepReader bad=reader;bad.cursor=bad.bits+1;invalid(&bad,&untouched);bad=reader;bad.compressed=2;invalid(&bad,&untouched);bad=reader;bad.bytes.data=NULL;invalid(&bad,&untouched);bad=reader;bad.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX+1u;invalid(&bad,&untouched);bad=reader;bad.compressed=1;bad.cursor=1;invalid(&bad,&untouched);
   CohRepReader saved=reader;CHECK(coh_initial_netfx_probe(&reader,(CohInitialNetFxProbe*)(void*)&reader)==COH_INVALID&&!memcmp(&saved,&reader,sizeof(reader)));invalid_arguments++;
   unsigned char*copy=malloc(bytes);CHECK(copy);memcpy(copy,wire,bytes);CHECK(coh_initial_netfx_probe(&reader,(CohInitialNetFxProbe*)(void*)wire)==COH_INVALID&&!memcmp(copy,wire,bytes));free(copy);invalid_arguments++;
   bad=reader;bad.bytes.data=(const unsigned char*)(const void*)&bad;bad.bytes.size=sizeof(bad);bad.bits=sizeof(bad)*8;bad.cursor=0;invalid(&bad,&untouched);
  }
  free(wire);
 }
 CHECK(fgetc(stream)==EOF);fclose(stream);CHECK(count>=70&&complete>=50);
 printf("{\"checks\":%lu,\"fixtures\":%u,\"complete_netfx_observations\":%u,\"truncated_extents\":%lu,\"mutations\":%lu,\"invalid_argument_checks\":%lu,\"formatter_checks\":%lu,\"costume_parsed\":false,\"cross_prefix_in_phase_verified\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,count,complete,cuts,mutations,invalid_arguments,formatter_checks);return 0;
}
