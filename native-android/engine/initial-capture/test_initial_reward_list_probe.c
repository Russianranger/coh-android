#include "coh_initial_reward_list_probe.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,cuts,mutations,index_opaque_checks,invalid_arguments,formatter_checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint32_t word(FILE*f){unsigned char b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static CohStatus parse(const CohRepReader*r,CohInitialRewardListProbe*out){CohRepReader before=*r;unsigned char*copy=malloc(r->bytes.size?r->bytes.size:1);CHECK(copy);memcpy(copy,r->bytes.data,r->bytes.size);CohStatus status=coh_initial_reward_list_probe(r,out);CHECK(status!=COH_OK);CHECK(!memcmp(r,&before,sizeof(before)));CHECK(!memcmp(copy,r->bytes.data,r->bytes.size));free(copy);return status;}
static void invalid(const CohRepReader*r,CohInitialRewardListProbe*out){CohInitialRewardListProbe before=*out;CHECK(coh_initial_reward_list_probe(r,out)==COH_INVALID);CHECK(!memcmp(out,&before,sizeof(before)));invalid_arguments++;}
static void formatting(const CohInitialRewardListProbe*d){
 char json[COH_INITIAL_REWARD_LIST_REPORT_MAX],expected[COH_INITIAL_REWARD_LIST_REPORT_MAX],small[2];CohInitialRewardListProbe empty={0};CHECK(coh_initial_reward_list_probe_json(&empty,json,sizeof(json))==4&&!strcmp(json,"null"));int n=coh_initial_reward_list_probe_json(d,json,sizeof(json));CHECK(n>0&&(size_t)n<sizeof(json));int wanted=snprintf(expected,sizeof(expected),"[%u,%u,%u,%u,%u,%u,%llu,%u,%u]",(unsigned)d->status,(unsigned)d->stage,d->group,d->index,d->entries[0],d->entries[1],(unsigned long long)d->failure_bit,d->list_validated,(unsigned)d->leaf_stage);CHECK(n==wanted&&!strcmp(json,expected));CHECK(!strstr(json,"Reward")&&!strstr(json,"AAAA")&&!strstr(json,"\"text\"")&&!strstr(json,"\"index\"")&&!strstr(json,"generation")&&!strstr(json,"packet"));
 CHECK(coh_initial_reward_list_probe_json(d,small,sizeof(small))==n&&small[0]=='['&&!small[1]);CHECK(coh_initial_reward_list_probe_json(NULL,json,sizeof(json))<0&&coh_initial_reward_list_probe_json(d,NULL,sizeof(json))<0&&coh_initial_reward_list_probe_json(d,json,0)<0);CohInitialRewardListProbe copy=*d;CHECK(coh_initial_reward_list_probe_json(&copy,(char*)(void*)&copy,sizeof(copy))<0&&!memcmp(&copy,d,sizeof(copy)));formatter_checks++;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 2;unsigned count=word(f),complete=0,max_entries=0;
 for(unsigned fi=0;fi<count;fi++){
  uint32_t row[20];for(unsigned j=0;j<20;j++)row[j]=word(f);size_t bytes=row[0],length=row[1];unsigned mode=row[2],variant=row[3];unsigned char*wire=malloc(bytes);CHECK(wire&&fread(wire,1,bytes,f)==bytes);CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){wire,bytes},length,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=row[5];CohInitialRewardListProbe d;memset(&d,0x5a,sizeof(d));CohStatus status=parse(&r,&d);
  if(status!=(CohStatus)row[7]||d.stage!=(CohInitialRewardListStage)row[8]||d.failure_bit!=row[6]){fprintf(stderr,"fixture%u mode%u variant%u scenario%u status%u/%u stage%u/%u bit%zu/%u\n",fi,mode,variant,row[4],status,row[7],d.stage,row[8],d.failure_bit,row[6]);return 1;}
  CHECK(d.status==status&&d.begin_bit==row[5]&&d.failure_bit<=length);uint32_t observed[]={d.group,d.index,d.counts[0],d.counts[1],d.entries[0],d.entries[1],d.literals,d.literal_bytes,d.list_validated,(unsigned)d.leaf_stage};for(unsigned j=0;j<10;j++){if(observed[j]!=row[9+j]){fprintf(stderr,"fixture%u mode%u variant%u field%u observed%u expected%u\n",fi,mode,variant,j,observed[j],row[9+j]);return 1;}checks++;}CHECK(d.end_bit==row[19]);formatting(&d);complete+=d.list_validated;if(d.entries[0]+d.entries[1]>max_entries)max_entries=d.entries[0]+d.entries[1];
  CohInitialRewardListProbe again;memset(&again,0xa5,sizeof(again));CHECK(parse(&r,&again)==status&&!memcmp(&again,&d,sizeof(d)));
  if(!variant){
   for(size_t end=r.cursor;end<row[6];end++){CohRepReader shorter=r;shorter.bits=end;CohInitialRewardListProbe cut={0};CHECK(parse(&shorter,&cut)!=COH_OK);CHECK(!cut.list_validated&&!cut.end_bit);cuts++;}
   for(size_t i=r.cursor/8;i<bytes;i++){wire[i]^=0x81;CohInitialRewardListProbe changed={0};CHECK(parse(&r,&changed)!=COH_OK);wire[i]^=0x81;mutations++;}
   if(d.stage==COH_INITIAL_REWARD_LIST_DICTIONARY){for(size_t bit=d.failure_bit;bit<length;bit++){wire[bit/8]^=(unsigned char)(1u<<(bit&7));CohInitialRewardListProbe changed={0};CHECK(parse(&r,&changed)==status&&!memcmp(&changed,&d,sizeof(d)));wire[bit/8]^=(unsigned char)(1u<<(bit&7));index_opaque_checks++;}}
  }
  if(!fi){
   CohInitialRewardListProbe untouched;memset(&untouched,0x5a,sizeof(untouched));invalid(NULL,&untouched);CHECK(coh_initial_reward_list_probe(&r,NULL)==COH_INVALID);invalid_arguments++;CohRepReader bad=r;bad.cursor=bad.bits+1;invalid(&bad,&untouched);bad=r;bad.compressed=2;invalid(&bad,&untouched);bad=r;bad.bytes.data=NULL;invalid(&bad,&untouched);bad=r;bad.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX+1u;invalid(&bad,&untouched);bad=r;bad.compressed=1;bad.cursor=1;invalid(&bad,&untouched);
   CohRepReader saved=r;CHECK(coh_initial_reward_list_probe(&r,(CohInitialRewardListProbe*)(void*)&r)==COH_INVALID&&!memcmp(&saved,&r,sizeof(r)));invalid_arguments++;unsigned char*copy=malloc(bytes);CHECK(copy);memcpy(copy,wire,bytes);CHECK(coh_initial_reward_list_probe(&r,(CohInitialRewardListProbe*)(void*)wire)==COH_INVALID&&!memcmp(copy,wire,bytes));free(copy);invalid_arguments++;
   bad=r;bad.bytes.data=(const unsigned char*)(const void*)&bad;bad.bytes.size=sizeof(bad);bad.bits=sizeof(bad)*8;bad.cursor=0;invalid(&bad,&untouched);
  }
  free(wire);
 }
 CHECK(fgetc(f)==EOF);fclose(f);CHECK(count>=140&&complete>=40&&max_entries==512);printf("{\"checks\":%lu,\"fixtures\":%u,\"complete_list_observations\":%u,\"max_completed_entries\":%u,\"truncated_extents\":%lu,\"mutations\":%lu,\"unread_index_controls\":%lu,\"invalid_argument_checks\":%lu,\"formatter_checks\":%lu,\"dictionary_admitted\":false,\"slot_framing_parsed\":false,\"source_generation_admitted\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,count,complete,max_entries,cuts,mutations,index_opaque_checks,invalid_arguments,formatter_checks);return 0;
}
