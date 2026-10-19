#include "coh_initial_create_probe.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,cuts,mutations,invalid_arguments,formatter_checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint32_t word(FILE*f){unsigned char raw[4];CHECK(fread(raw,1,4,f)==4);return(uint32_t)raw[0]|(uint32_t)raw[1]<<8|(uint32_t)raw[2]<<16|(uint32_t)raw[3]<<24;}
static CohStatus parse(const CohRepReader*r,const CohRepSchema*s,uint32_t selected,CohInitialCreateProbe*out){
 CohRepReader before=*r;CohRepSchema schema=*s;unsigned char*bytes=malloc(r->bytes.size?r->bytes.size:1);CHECK(bytes);memcpy(bytes,r->bytes.data,r->bytes.size);
 CohStatus status=coh_initial_create_probe(r,s,selected,out);CHECK(status!=COH_OK);CHECK(!memcmp(r,&before,sizeof(before)));CHECK(!memcmp(s,&schema,sizeof(schema)));CHECK(!memcmp(bytes,r->bytes.data,r->bytes.size));free(bytes);return status;
}
static void invalid(const CohRepReader*r,const CohRepSchema*s,uint32_t selected,CohInitialCreateProbe*out){
 CohInitialCreateProbe before=*out;CHECK(coh_initial_create_probe(r,s,selected,out)==COH_INVALID);if(memcmp(out,&before,sizeof(before))){fprintf(stderr,"invalid argument case %lu modified output\n",invalid_arguments);exit(1);}checks++;invalid_arguments++;
}
static void formatting(const CohInitialCreateProbe*report){
 char json[COH_INITIAL_PROBE_REPORT_MAX],short_buffer[2];CohInitialCreateProbe empty={0};
 CHECK(coh_initial_create_probe_json(&empty,json,sizeof(json))==4&&!strcmp(json,"null"));
 int length=coh_initial_create_probe_json(report,json,sizeof(json));CHECK(length>0&&(size_t)length<sizeof(json));
 CHECK(strstr(json,"\"schema\":\"coh-initial-first-create-v1\"")&&strstr(json,"\"diagnostic_only\":true"));
 CHECK(strstr(json,"\"selected_owner_bound\":false")&&strstr(json,"\"source_generation_admitted\":false")&&strstr(json,"\"complete_initial_character\":false"));
 CHECK(strstr(json,"\"actor_publication\":false")&&strstr(json,"\"ack_permitted\":false")&&strstr(json,"\"world_authority\":false"));
 CHECK(!strstr(json,"Fixture")&&!strstr(json,"4242")&&!strstr(json,"4243")&&!strstr(json,"\"packet\"")&&!strstr(json,"\"name\"")&&!strstr(json,"\"dbid\":"));
 if(report->stage==COH_INITIAL_PROBE_RECORD_BODY)CHECK(strstr(json,"FIRST_RECORD_BODY_REQUIRED"));
 CHECK(coh_initial_create_probe_json(report,short_buffer,sizeof(short_buffer))==length&&short_buffer[0]=='{'&&!short_buffer[1]);
 CHECK(coh_initial_create_probe_json(NULL,json,sizeof(json))<0&&coh_initial_create_probe_json(report,NULL,sizeof(json))<0&&coh_initial_create_probe_json(report,json,0)<0);
 CohInitialCreateProbe copy=*report;CHECK(coh_initial_create_probe_json(&copy,(char*)(void*)&copy,sizeof(copy))<0&&!memcmp(&copy,report,sizeof(copy)));formatter_checks++;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*stream=fopen(argv[1],"rb");if(!stream)return 2;uint32_t count=word(stream),complete=0;
 for(uint32_t fixture=0;fixture<count;fixture++){
  uint32_t row[15];for(unsigned i=0;i<15;i++)row[i]=word(stream);
  size_t bytes=row[0],bits=row[1],post=row[2],header_end=row[3],create_end=row[4];unsigned mode=row[5],variant=row[6],scenario=row[7];
  unsigned char*wire=malloc(bytes);CHECK(wire&&fread(wire,1,bytes,stream)==bytes);
  CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,(CohBytes){wire,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);reader.cursor=post;
  CohRepSchema schema={{{11,1},{12,4},{13,10}},3,0};CohInitialCreateProbe report;memset(&report,0x5a,sizeof(report));
  CohStatus status=parse(&reader,&schema,row[9],&report);
  if(status!=(CohStatus)row[10]||report.stage!=(CohInitialCreateProbeStage)row[11]){fprintf(stderr,"fixture%u mode%u variant%u scenario%u status%u/%u stage%u/%u bit%zu header%zu child%u/%u/%zu indexbyte%u\n",fixture,mode,variant,scenario,status,row[10],report.stage,row[11],report.failure_bit,header_end,report.entity_failure.status,report.entity_failure.stage,report.entity_failure.bit,wire[header_end/8]);return 1;}
  CHECK(report.status==status);CHECK(report.create_validated==row[12]);CHECK(report.header_validated==row[13]);CHECK(report.is_self==row[14]);CHECK(report.self_dbid_matches_handoff==row[14]);CHECK(report.failure_bit<=bits);
  formatting(&report);
  if(report.header_validated)CHECK(report.header_end_bit==header_end);
  if(report.create_validated){CHECK(report.create_end_bit==create_end);CHECK(report.entity_index==row[8]);CHECK(report.entity_type==(scenario<=1||scenario==6?2u:scenario<=4?4u:1u));complete++;}
  CohInitialCreateProbe again;memset(&again,0xa5,sizeof(again));CHECK(parse(&reader,&schema,row[9],&again)==status);CHECK(!memcmp(&again,&report,sizeof(report)));
  if(!variant){
   /* Every shorter logical extent must refuse before claiming complete create. */
   for(size_t end=post;end<create_end;end++){
    CohRepReader shorter=reader;shorter.bits=end;CohInitialCreateProbe cut={0};CHECK(parse(&shorter,&schema,row[9],&cut)!=COH_OK);CHECK(!cut.create_validated);cuts++;
   }
   /* Mutation can alter a candidate but can never turn this observer into acceptance. */
   for(size_t i=post/8;i<bytes;i+=bytes/13+1){wire[i]^=0x81;CohInitialCreateProbe changed={0};CHECK(parse(&reader,&schema,row[9],&changed)!=COH_OK);wire[i]^=0x81;mutations++;}
  }
  if(fixture==0){
   CohInitialCreateProbe untouched;memset(&untouched,0x5a,sizeof(untouched));invalid(NULL,&schema,4242,&untouched);invalid(&reader,NULL,4242,&untouched);invalid(&reader,&schema,0,&untouched);invalid(&reader,&schema,UINT32_MAX,&untouched);CHECK(coh_initial_create_probe(&reader,&schema,4242,NULL)==COH_INVALID);invalid_arguments++;
   CohRepReader bad=reader;bad.cursor=bad.bits+1;invalid(&bad,&schema,4242,&untouched);bad=reader;bad.compressed=2;invalid(&bad,&schema,4242,&untouched);bad=reader;bad.bytes.data=NULL;invalid(&bad,&schema,4242,&untouched);bad=reader;bad.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX+1u;invalid(&bad,&schema,4242,&untouched);
   CohRepSchema bad_schema=schema;bad_schema.count=COH_REP_SHORTCUT_MAX+1;invalid(&reader,&bad_schema,4242,&untouched);
   /* Output aliases must be rejected before writing any enclosing input. */
   CohRepReader saved_reader=reader;CHECK(coh_initial_create_probe(&reader,&schema,4242,(CohInitialCreateProbe*)(void*)&reader)==COH_INVALID);CHECK(!memcmp(&reader,&saved_reader,sizeof(reader)));
   CohRepSchema saved_schema=schema;CHECK(coh_initial_create_probe(&reader,&schema,4242,(CohInitialCreateProbe*)(void*)&schema)==COH_INVALID);CHECK(!memcmp(&schema,&saved_schema,sizeof(schema)));
   unsigned char*saved=malloc(bytes);CHECK(saved);memcpy(saved,wire,bytes);CHECK(coh_initial_create_probe(&reader,&schema,4242,(CohInitialCreateProbe*)(void*)wire)==COH_INVALID);CHECK(!memcmp(saved,wire,bytes));free(saved);invalid_arguments+=3;
  }
  free(wire);
 }
 CHECK(fgetc(stream)==EOF);fclose(stream);CHECK(count==96&&complete==74);
 printf("{\"checks\":%lu,\"fixtures\":%u,\"complete_create_observations\":%u,\"truncated_extents\":%lu,\"mutations\":%lu,\"invalid_argument_checks\":%lu,\"formatter_checks\":%lu,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,count,complete,cuts,mutations,invalid_arguments,formatter_checks);return 0;
}
