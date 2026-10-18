/* NEW host-only differential controls; owner_fixture.h is produced from the
 * admitted original declarations/functions and the fresh-only transform. */
#include "owner_fixture.h"
#define SLOT(type,name) union {type value;unsigned char separation[512];} name
static struct {
 SLOT(NetLink,owned);SLOT(NetLink,other);SLOT(ClientLink,client);SLOT(ClientLink,foreign);
 SLOT(Entity,entity);SLOT(Entity,elsewhere);SLOT(Character,character);SLOT(Array,array);
 void *storage[COH_SOURCE_GROUPS_OWNER_MAX_LINKS];
} fixture,fixture_before;
#define fixture_owned fixture.owned.value
#define fixture_other fixture.other.value
#define fixture_client fixture.client.value
#define fixture_foreign fixture.foreign.value
#define fixture_entity fixture.entity.value
#define fixture_elsewhere fixture.elsewhere.value
#define fixture_character fixture.character.value
#define fixture_array fixture.array.value
#define fixture_storage fixture.storage
static CohSourceGroupsOwner result,result_before;
static unsigned char globals_before[sizeof(owner_globals)];
static unsigned scenarios,first_failures,successes;

static void reset(void)
{
 memset(&fixture,0,sizeof(fixture));memset(&owner_globals,0,sizeof(owner_globals));
 memset(&result,0xa5,sizeof(result));
 fixture_entity.owner=7;fixture_entity.id=123;fixture_entity.db_id=17;fixture_entity.auth_id=12345;
 fixture_entity.map_id=1;fixture_entity.static_map_id=1;fixture_entity.pchar=&fixture_character;fixture_entity.client=&fixture_client;
 fixture_character.pclass=&fixture_class;fixture_character.entParent=&fixture_entity;
 entities[7]=&fixture_entity;entity_state[7]=ENTITY_IN_USE;entities_max=8;world_id=19;
 fixture_owned.type=NLT_UDP;fixture_owned.opType=NLOT_SYNC;fixture_owned.UID=29;fixture_owned.connection_id=31;
 fixture_owned.connect_id=37;fixture_owned.connected=1;fixture_owned.protocolVersion=5;fixture_owned.userData=&fixture_client;
 fixture_owned.last_world_id=-1;fixture_owned.last_update_time=41;fixture_owned.last_processed_id=43;
 fixture_owned.last_recv_id=47;fixture_owned.last_ordered_recv_id=53;
 fixture_client.link=&fixture_owned;fixture_client.entity=&fixture_entity;fixture_client.lastSentFullUpdateID=59;fixture_client.ackedFullUpdateID=61;
 fixture_array.size=1;fixture_array.maxSize=COH_SOURCE_GROUPS_OWNER_MAX_LINKS;fixture_array.storage=fixture_storage;
 fixture_storage[0]=&fixture_owned;net_links.links=&fixture_array;
 coh_fp_thread=31;current_thread=31;coh_fp_entered=1;coh_fp_complete=0;
 coh_fp_owner_failure=COH_FRESH_OWNER_NONE;trace_count=0;
}
static void save_inputs(void)
{
 memcpy(&fixture_before,&fixture,sizeof(fixture));memcpy(globals_before,&owner_globals,sizeof(owner_globals));
 memcpy(&result_before,&result,sizeof(result));
}
static void check_inputs(int output_unchanged)
{
 CHECK(!memcmp(&fixture_before,&fixture,sizeof(fixture)));
 CHECK(!memcmp(globals_before,&owner_globals,sizeof(owner_globals)));
 if(output_unchanged)CHECK(!memcmp(&result_before,&result,sizeof(result)));
}
static void expected_trace(unsigned failure,unsigned repeated_entry)
{
 unsigned at=0;
 for(unsigned id=1;id<=47;id++){
  CHECK(at<trace_count&&trace_ids[at]==id);
  CHECK(trace_values[at]==(failure==id&&(!repeated_entry||id!=45)));at++;
  if(repeated_entry&&id==45){
   CHECK(at<trace_count&&trace_ids[at]==44&&trace_values[at]==0);at++;
   CHECK(at<trace_count&&trace_ids[at]==45&&trace_values[at]==(failure==45));at++;
   if(failure==45)break;
  }
  if(failure==id)break;
 }
 CHECK(at==trace_count);
 CHECK(coh_fp_owner_failure==(CohFreshOwnerFailure)failure);
}
static void fail_case(unsigned id)
{
 const NetLink *input=&fixture_owned;CohSourceGroupsOwner *output=&result;unsigned repeat=0;
 reset();
 switch(id){
 case 1:input=NULL;break;case 2:output=NULL;break;case 3:net_links.links=NULL;break;
 case 4:fixture_array.size=0;break;case 5:fixture_array.size=COH_SOURCE_GROUPS_OWNER_MAX_LINKS+1;break;
 case 6:fixture_array.storage=NULL;break;case 7:fixture_array.maxSize=0;break;
 case 8:output=(CohSourceGroupsOwner*)&fixture_owned;break;
 case 9:output=(CohSourceGroupsOwner*)&net_links;break;
 case 10:output=(CohSourceGroupsOwner*)&fixture_array;break;
 case 11:output=(CohSourceGroupsOwner*)fixture_storage;break;
 case 12:output=(CohSourceGroupsOwner*)&world_id;break;
 case 13:output=(CohSourceGroupsOwner*)&entities_max;break;
 case 14:output=(CohSourceGroupsOwner*)entities;break;
 case 15:output=(CohSourceGroupsOwner*)entity_state;break;
 case 16:fixture_owned.userData=NULL;break;case 17:fixture_client.link=&fixture_other;break;
 case 18:output=(CohSourceGroupsOwner*)&fixture_client;break;case 19:fixture_client.entity=NULL;break;
 case 20:output=(CohSourceGroupsOwner*)&fixture_entity;break;case 21:fixture_entity.client=&fixture_foreign;break;
 case 22:fixture_entity.db_id=0;break;case 23:fixture_entity.id=0;break;case 24:fixture_entity.owner=0;break;
 case 25:fixture_entity.owner=MAX_ENTITIES_PRIVATE;break;case 26:entities_max=0;break;
 case 27:entities_max=MAX_ENTITIES_PRIVATE+1;break;case 28:entity_state[7]=0;break;
 case 29:entities[7]=&fixture_elsewhere;break;case 30:fixture_entity.pchar=NULL;break;
 case 31:output=(CohSourceGroupsOwner*)&fixture_character;break;case 32:fixture_character.pclass=NULL;break;
 case 33:fixture_character.entParent=&fixture_elsewhere;break;case 34:fixture_owned.type=NLT_TCP;break;
 case 35:fixture_owned.connected=0;break;case 36:fixture_owned.pending=1;break;case 37:fixture_owned.connecting=1;break;
 case 38:fixture_owned.disconnected=1;break;case 39:fixture_owned.destroyed=1;break;
 case 40:fixture_owned.removedFromMasterList=1;break;case 41:fixture_owned.protocolVersion=6;break;
 case 42:fixture_client.ready=(ClientReadyState)-1;break;
 case 43:fixture_client.ready=(ClientReadyState)(CLIENTSTATE_RE_REQALLENTS+1);break;
 case 44:fixture_storage[0]=NULL;break;
 case 45:fixture_array.size=2;fixture_storage[1]=&fixture_other;output=(CohSourceGroupsOwner*)&fixture_other;repeat=1;break;
 case 46:fixture_storage[0]=&fixture_other;break;
 case 47:fixture_array.size=2;fixture_storage[1]=&fixture_other;fixture_other.userData=&fixture_client;repeat=1;break;
 default:CHECK(0);
 }
 save_inputs();CHECK(original_prepare(input,output)==0);check_inputs(1);
 CHECK(fresh_prepare(input,output)==0);check_inputs(1);expected_trace(id,repeat);
 scenarios++;first_failures++;
}
static void success_case(unsigned version,unsigned ready)
{
 CohSourceGroupsOwner original;
 reset();fixture_owned.protocolVersion=version;fixture_client.ready=(ClientReadyState)ready;
 save_inputs();CHECK(original_prepare(&fixture_owned,&result)==1);check_inputs(0);original=result;
 memset(&result,0xa5,sizeof(result));
 CHECK(fresh_prepare(&fixture_owned,&result)==1);check_inputs(0);
 CHECK(!memcmp(&original,&result,sizeof(result)));expected_trace(0,0);
 CHECK(result.links_scanned==1&&result.link_slot==0&&result.protocol_version==version);
 scenarios++;successes++;
}
static void latch_controls(void)
{
 reset();CHECK(original_latch(0,COH_FRESH_OWNER_INPUT_LINK)==0);
 CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_NONE);
 CHECK(original_latch(-7,COH_FRESH_OWNER_ENTITY_DBID)==-7);
 CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_ENTITY_DBID);
 CHECK(original_latch(1,COH_FRESH_OWNER_INPUT_LINK)==1);
 CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_ENTITY_DBID);
 for(unsigned gate=0;gate<6;gate++){
  reset();CohFreshOwnerFailure reason=COH_FRESH_OWNER_INPUT_LINK;
  if(gate==0)coh_fp_thread=0;
  if(gate==1)current_thread++;
  if(gate==2)coh_fp_entered=0;
  if(gate==3)coh_fp_complete=1;
  if(gate==4)reason=COH_FRESH_OWNER_NONE;
  if(gate==5)reason=COH_FRESH_OWNER_COUNT;
  CHECK(original_latch(1,reason)==1);CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_NONE);
  scenarios++;
 }
 scenarios++;
}
static void short_circuit_controls(void)
{
 reset();fixture_owned.userData=NULL;fixture_entity.db_id=0;fixture_owned.pending=1;fixture_storage[0]=NULL;
 save_inputs();CHECK(!original_prepare(&fixture_owned,&result));CHECK(!fresh_prepare(&fixture_owned,&result));
 check_inputs(1);expected_trace(16,0);scenarios++;
 reset();fixture_entity.db_id=0;fixture_owned.pending=1;fixture_storage[0]=NULL;
 save_inputs();CHECK(!original_prepare(&fixture_owned,&result));CHECK(!fresh_prepare(&fixture_owned,&result));
 check_inputs(1);expected_trace(22,0);scenarios++;
 /* The pointer is deliberately unreadable: both original and transformed
  * helpers must stop at !out, before reading any member of this pointer. */
 reset();save_inputs();CHECK(!original_prepare((const NetLink*)(uintptr_t)1,NULL));
 CHECK(!fresh_prepare((const NetLink*)(uintptr_t)1,NULL));check_inputs(1);expected_trace(2,0);scenarios++;
}
static void maximum_scan(void)
{
 CohSourceGroupsOwner original;
 reset();fixture_array.size=COH_SOURCE_GROUPS_OWNER_MAX_LINKS;
 for(unsigned i=0;i<COH_SOURCE_GROUPS_OWNER_MAX_LINKS;i++)fixture_storage[i]=&fixture_other;
 fixture_storage[COH_SOURCE_GROUPS_OWNER_MAX_LINKS-1]=&fixture_owned;
 save_inputs();CHECK(original_prepare(&fixture_owned,&result));original=result;
 CHECK(fresh_prepare(&fixture_owned,&result));check_inputs(0);CHECK(!memcmp(&original,&result,sizeof(result)));
 CHECK(trace_count==43+2*COH_SOURCE_GROUPS_OWNER_MAX_LINKS+2);
 for(unsigned i=0;i<43;i++)CHECK(trace_ids[i]==i+1&&trace_values[i]==0);
 for(unsigned i=0;i<COH_SOURCE_GROUPS_OWNER_MAX_LINKS;i++){
  CHECK(trace_ids[43+2*i]==44&&trace_values[43+2*i]==0);
  CHECK(trace_ids[44+2*i]==45&&trace_values[44+2*i]==0);
 }
 CHECK(trace_ids[trace_count-2]==46&&trace_ids[trace_count-1]==47);
 CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_NONE&&result.link_slot==65535&&result.links_scanned==65536);
 scenarios++;successes++;
}
int main(void)
{
 struct rlimit no_core={0,0};CHECK(!setrlimit(RLIMIT_CORE,&no_core));
 CHECK(COH_FRESH_OWNER_COUNT==48);CHECK(sizeof(CohSourceGroupsOwner)<=512);
 for(unsigned id=1;id<COH_FRESH_OWNER_COUNT;id++)fail_case(id);
 for(unsigned version=0;version<=5;version++)
  for(unsigned ready=CLIENTSTATE_NOT_READY;ready<=CLIENTSTATE_RE_REQALLENTS;ready++)success_case(version,ready);
 latch_controls();short_circuit_controls();maximum_scan();
 printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"first_failure_atoms\":%u,\"successful_differential_cases\":%u,\"latch_controls\":7,\"short_circuit_controls\":3,\"maximum_links_scanned\":65536,\"host_member_subset_storage_only\":true,\"actual_windows_executed\":false,\"runtime_executed\":false,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks,scenarios,first_failures,successes);
 return 0;
}
