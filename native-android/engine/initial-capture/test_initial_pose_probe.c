#include "coh_initial_pose_probe.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,cuts,mutations,invalid_arguments,formatter_checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint32_t word(FILE*f){unsigned char raw[4];CHECK(fread(raw,1,4,f)==4);return(uint32_t)raw[0]|(uint32_t)raw[1]<<8|(uint32_t)raw[2]<<16|(uint32_t)raw[3]<<24;}
static CohStatus parse(const CohRepReader*r,uint32_t packet_id,CohInitialPoseProbe*out){
 CohRepReader before=*r;unsigned char*bytes=malloc(r->bytes.size?r->bytes.size:1);CHECK(bytes);memcpy(bytes,r->bytes.data,r->bytes.size);
 CohStatus status=coh_initial_pose_probe(r,packet_id,out);CHECK(status!=COH_OK);CHECK(!memcmp(r,&before,sizeof(before)));CHECK(!memcmp(bytes,r->bytes.data,r->bytes.size));free(bytes);return status;
}
static void invalid(const CohRepReader*r,uint32_t packet_id,CohInitialPoseProbe*out){
 CohInitialPoseProbe before=*out;CHECK(coh_initial_pose_probe(r,packet_id,out)==COH_INVALID);CHECK(!memcmp(out,&before,sizeof(before)));invalid_arguments++;
}
static void formatting(const CohInitialPoseProbe*report){
 char json[COH_INITIAL_POSE_REPORT_MAX],small[2];CohInitialPoseProbe empty={0};CHECK(coh_initial_pose_probe_json(&empty,json,sizeof(json))==4&&!strcmp(json,"null"));
 int length=coh_initial_pose_probe_json(report,json,sizeof(json));CHECK(length>0&&(size_t)length<sizeof(json));CHECK(strstr(json,"\"schema\":\"coh-initial-first-pose-v1\"")&&strstr(json,"\"diagnostic_only\":true"));
 CHECK(strstr(json,"\"source_generation_admitted\":false")&&strstr(json,"\"complete_initial_character\":false")&&strstr(json,"\"actor_publication\":false")&&strstr(json,"\"ack_permitted\":false")&&strstr(json,"\"world_authority\":false"));
 CHECK(!strstr(json,"\"packet_id\"")&&!strstr(json,"\"quaternion\"")&&!strstr(json,"\"position\"")&&!strstr(json,"\"state_mode\"")&&!strstr(json,"Fixture"));
 if(report->stage==COH_INITIAL_POSE_SEQUENCE)CHECK(strstr(json,"FIRST_SEQUENCE_BODY_REQUIRED"));
 CHECK(coh_initial_pose_probe_json(report,small,sizeof(small))==length&&small[0]=='{'&&!small[1]);CHECK(coh_initial_pose_probe_json(NULL,json,sizeof(json))<0&&coh_initial_pose_probe_json(report,NULL,sizeof(json))<0&&coh_initial_pose_probe_json(report,json,0)<0);
 CohInitialPoseProbe copy=*report;CHECK(coh_initial_pose_probe_json(&copy,(char*)(void*)&copy,sizeof(copy))<0&&!memcmp(&copy,report,sizeof(copy)));formatter_checks++;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*stream=fopen(argv[1],"rb");if(!stream)return 2;uint32_t count=word(stream),complete=0;
 for(uint32_t fixture=0;fixture<count;fixture++){
  uint32_t row[18];for(unsigned i=0;i<18;i++)row[i]=word(stream);size_t bytes=row[0],bits=row[1];unsigned mode=row[2],variant=row[3],scenario=row[4];
  unsigned char*wire=malloc(bytes);CHECK(wire&&fread(wire,1,bytes,stream)==bytes);CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,(CohBytes){wire,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);reader.cursor=row[8];
  CohInitialPoseProbe report;memset(&report,0x5a,sizeof(report));CohStatus status=parse(&reader,row[5],&report);
  if(status!=(CohStatus)row[6]||report.stage!=(CohInitialPoseStage)row[7]){fprintf(stderr,"fixture%u mode%u variant%u scenario%u status%u/%u stage%u/%u bit%zu\n",fixture,mode,variant,scenario,status,row[6],report.stage,row[7],report.failure_bit);return 1;}
  CHECK(report.status==status&&report.begin_bit==row[8]&&report.failure_bit<=bits);CHECK(report.flags_validated==row[13]);CHECK(report.mode_validated==row[14]);CHECK(report.position_validated==row[15]);CHECK(report.orientation_validated==row[16]);CHECK(report.pose_validated==row[17]);
  if(report.flags_validated)CHECK(report.flags_end_bit==row[9]);
  if(report.mode_validated)CHECK(report.mode_end_bit==row[10]);
  if(report.position_validated)CHECK(report.position_end_bit==row[11]);
  if(report.pose_validated){CHECK(report.pose_end_bit==row[12]);complete++;}
  formatting(&report);CohInitialPoseProbe again;memset(&again,0xa5,sizeof(again));CHECK(parse(&reader,row[5],&again)==status);CHECK(!memcmp(&again,&report,sizeof(report)));
  if(!variant){
   for(size_t end=reader.cursor;end<row[12];end++){CohRepReader shortened=reader;shortened.bits=end;CohInitialPoseProbe cut={0};CHECK(parse(&shortened,row[5],&cut)!=COH_OK);CHECK(!cut.pose_validated);cuts++;}
   for(size_t i=reader.cursor/8;i<bytes;i++){wire[i]^=0x81;CohInitialPoseProbe changed={0};CHECK(parse(&reader,row[5],&changed)!=COH_OK);wire[i]^=0x81;mutations++;}
  }
  if(!fixture){
   CohInitialPoseProbe untouched;memset(&untouched,0x5a,sizeof(untouched));invalid(NULL,row[5],&untouched);invalid(&reader,0,&untouched);CHECK(coh_initial_pose_probe(&reader,row[5],NULL)==COH_INVALID);invalid_arguments++;
   CohRepReader bad=reader;bad.cursor=bad.bits+1;invalid(&bad,row[5],&untouched);bad=reader;bad.compressed=2;invalid(&bad,row[5],&untouched);bad=reader;bad.bytes.data=NULL;invalid(&bad,row[5],&untouched);bad=reader;bad.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX+1u;invalid(&bad,row[5],&untouched);bad=reader;bad.compressed=1;bad.cursor=1;invalid(&bad,row[5],&untouched);
   CohRepReader saved=reader;CHECK(coh_initial_pose_probe(&reader,row[5],(CohInitialPoseProbe*)(void*)&reader)==COH_INVALID&&!memcmp(&saved,&reader,sizeof(reader)));invalid_arguments++;
   unsigned char*copy=malloc(bytes);CHECK(copy);memcpy(copy,wire,bytes);CHECK(coh_initial_pose_probe(&reader,row[5],(CohInitialPoseProbe*)(void*)wire)==COH_INVALID&&!memcmp(copy,wire,bytes));free(copy);invalid_arguments++;
  }
  free(wire);
 }
 CHECK(fgetc(stream)==EOF);fclose(stream);CHECK(count==91&&complete==62);
 printf("{\"checks\":%lu,\"fixtures\":%u,\"complete_pose_observations\":%u,\"truncated_extents\":%lu,\"mutations\":%lu,\"invalid_argument_checks\":%lu,\"formatter_checks\":%lu,\"sequence_body_parsed\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,count,complete,cuts,mutations,invalid_arguments,formatter_checks);return 0;
}
