/* NEW focused alternate-eligibility controls only. Original declarations and
 * helper functions are extracted into an explicit HOST member-subset fixture.
 * No original client, FolderCache, server, network or process is executed. */
#include "initial_owner_fixture.h"
#define SLOT(type,name) union {type value;unsigned char separation[512];} name
static struct {
 SLOT(NetLink,link);SLOT(NetLink,other);SLOT(ClientLink,client);
 SLOT(Entity,entity);SLOT(Entity,other_entity);SLOT(Character,character);SLOT(Array,array);
 void *storage[2];Player player;
} fixture,before_fixture;
static unsigned char before_globals[sizeof(owner_globals)];
static CohSourceGroupsOwner result,before_result;
static unsigned scenarios,failures,active_successes,sleeping_successes;
#define F(member) fixture.member.value
static void reset(void)
{
 memset(&fixture,0,sizeof(fixture));memset(&owner_globals,0,sizeof(owner_globals));
 memset(&result,0xa5,sizeof(result));
 F(entity).owner=7;F(entity).id=31;F(entity).db_id=19;F(entity).auth_id=23;
 F(entity).map_id=F(entity).static_map_id=1;F(entity).client=&F(client);F(entity).pchar=&F(character);
 F(entity).owned=1;F(entity).pl=&fixture.player;
 F(character).pclass=&fixture_class;F(character).entParent=&F(entity);
 F(client).link=&F(link);F(client).entity=&F(entity);F(client).ready=CLIENTSTATE_NOT_READY;
 F(link).type=NLT_UDP;F(link).opType=NLOT_SYNC;F(link).connected=1;F(link).protocolVersion=5;F(link).userData=&F(client);
 F(array).size=1;F(array).maxSize=2;F(array).storage=fixture.storage;fixture.storage[0]=&F(link);net_links.links=&F(array);
 entities[7]=&F(entity);entities_max=8;entity_state[7]=ENTITY_SLEEPING;entinfo[7].type=ENTTYPE_PLAYER;world_id=11;
 coh_fp_thread=current_thread=1;coh_fp_entered=1;coh_fp_complete=0;coh_fp_owner_failure=COH_FRESH_OWNER_NONE;
 trace_count=type_reads=0;
}
static void save(void)
{memcpy(&before_fixture,&fixture,sizeof(fixture));memcpy(before_globals,&owner_globals,sizeof(owner_globals));before_result=result;}
static void unchanged(int output)
{CHECK(!memcmp(&before_fixture,&fixture,sizeof(fixture)));CHECK(!memcmp(before_globals,&owner_globals,sizeof(owner_globals)));if(output)CHECK(!memcmp(&before_result,&result,sizeof(result)));}
static void sleeping_success(void)
{
 CohSourceGroupsOwner original;
 reset();entity_state[7]=ENTITY_IN_USE;save();CHECK(original_prepare(&F(link),&result));unchanged(0);original=result;
 entity_state[7]=ENTITY_SLEEPING;memset(&result,0xa5,sizeof(result));save();
 CHECK(!original_prepare(&F(link),&result));unchanged(1);
 CHECK(fresh_prepare(&F(link),&result));unchanged(0);
 CHECK(!memcmp(&original,&result,sizeof(result)));CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_NONE);CHECK(type_reads==1);
 scenarios++;sleeping_successes++;
}
static void unchanged_active(void)
{
 for(unsigned version=0;version<=5;version++)for(unsigned ready=0;ready<=CLIENTSTATE_RE_REQALLENTS;ready++){
  CohSourceGroupsOwner original;reset();entity_state[7]=ENTITY_IN_USE;
  /* The original active path did not require a Player/type/ownership subset.
   * Its old positive semantics must not silently acquire fallback restrictions. */
  F(entity).owned=0;F(entity).pl=NULL;entinfo[7].type=ENTTYPE_CRITTER;
  F(entity).demand_loaded=F(entity).is_map_xfer=1;F(entity).dbcomm_state.in_map_xfer=1;
  F(link).protocolVersion=version;F(client).ready=(ClientReadyState)ready;
  save();CHECK(original_prepare(&F(link),&result));unchanged(0);original=result;
  memset(&result,0xa5,sizeof(result));CHECK(fresh_prepare(&F(link),&result));unchanged(0);
  CHECK(!memcmp(&original,&result,sizeof(result)));CHECK(!type_reads&&coh_fp_owner_failure==COH_FRESH_OWNER_NONE);
  scenarios++;active_successes++;
 }
}
static void refusal(unsigned n)
{
 CohSourceGroupsOwner *output=&result;CohFreshOwnerFailure reason=COH_FRESH_OWNER_NONE;
 reset();
 switch(n){
 case 0:entities_max=7;reason=COH_FRESH_OWNER_INITIAL_SLOT_OUTSIDE_TABLE;break;
 case 1:entity_state[7]=0;reason=COH_FRESH_OWNER_INITIAL_STATE;break;
 case 2:output=(CohSourceGroupsOwner*)&entinfo[7];reason=COH_FRESH_OWNER_INITIAL_OUTPUT_ENTINFO_ALIAS;break;
 case 3:entinfo[7].type=ENTTYPE_CRITTER;reason=COH_FRESH_OWNER_INITIAL_NOT_PLAYER;break;
 case 4:F(entity).owned=0;reason=COH_FRESH_OWNER_INITIAL_NOT_OWNED;break;
 case 5:F(entity).pl=NULL;reason=COH_FRESH_OWNER_INITIAL_PLAYER_ABSENT;break;
 case 6:F(client).ready=CLIENTSTATE_REQALLENTS;reason=COH_FRESH_OWNER_INITIAL_CLIENT_STATE;break;
 case 7:F(entity).ready=1;reason=COH_FRESH_OWNER_INITIAL_ENTITY_READY;break;
 case 8:F(entity).demand_loaded=1;reason=COH_FRESH_OWNER_INITIAL_RELAY;break;
 case 9:F(entity).is_map_xfer=1;reason=COH_FRESH_OWNER_INITIAL_TRANSFER_LOGIN;break;
 case 10:F(entity).dbcomm_state.in_map_xfer=1;reason=COH_FRESH_OWNER_INITIAL_TRANSFER_ACTIVE;break;
 case 11:F(entity).dbcomm_state.waiting_map_xfer=1;reason=COH_FRESH_OWNER_INITIAL_TRANSFER_WAITING;break;
 case 12:F(entity).dbcomm_state.map_xfer_step=MAPXFER_WAIT_CLIENT_IDLE;reason=COH_FRESH_OWNER_INITIAL_TRANSFER_STEP;break;
 default:CHECK(0);
 }
 save();CHECK(!original_prepare(&F(link),output));unchanged(1);CHECK(!fresh_prepare(&F(link),output));unchanged(1);
 CHECK(coh_fp_owner_failure==reason);CHECK(trace_count&&trace_ids[trace_count-1]==COH_FRESH_OWNER_ENTITY_NOT_IN_USE);
 if(n<=2)CHECK(!type_reads);
 scenarios++;failures++;
}
static void state_and_phase(void)
{
 for(unsigned state=0;state<256;state++)if(!(state&ENTITY_IN_USE)&&state!=ENTITY_SLEEPING){
  reset();entity_state[7]=(U8)state;save();CHECK(!fresh_prepare(&F(link),&result));unchanged(1);
  CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_INITIAL_STATE&&type_reads==0);scenarios++;failures++;
 }
 for(int phase=-1;phase<=CLIENTSTATE_RE_REQALLENTS+1;phase++)if(phase!=CLIENTSTATE_NOT_READY){
  reset();F(client).ready=(ClientReadyState)phase;save();CHECK(!fresh_prepare(&F(link),&result));unchanged(1);
  CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_INITIAL_CLIENT_STATE);scenarios++;failures++;
 }
 for(int step=-1;step<=MAPXFER_DONE+1;step++)if(step!=MAPXFER_NO_XFER){
  reset();F(entity).dbcomm_state.map_xfer_step=(MapXferStep)step;save();CHECK(!fresh_prepare(&F(link),&result));unchanged(1);
  CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_INITIAL_TRANSFER_STEP);scenarios++;failures++;
 }
 for(int type=-1;type<=ENTTYPE_COUNT;type++)if(type!=ENTTYPE_PLAYER){
  reset();entinfo[7].type=(EntType)type;save();CHECK(!fresh_prepare(&F(link),&result));unchanged(1);
  CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_INITIAL_NOT_PLAYER&&type_reads==1);scenarios++;failures++;
 }
 /* Bounds stop before any state/type access, including a private-table-valid
  * slot outside the current live range. Existing lower/private bounds remain. */
 const int slots[]={-1,0,7,MAX_ENTITIES_PRIVATE-1,MAX_ENTITIES_PRIVATE};
 for(unsigned n=0;n<sizeof(slots)/sizeof(slots[0]);n++){
  reset();F(entity).owner=slots[n];entities_max=7;save();CHECK(!fresh_prepare(&F(link),&result));unchanged(1);
  CHECK(!type_reads);scenarios++;failures++;
 }
}
static void later_original_guards(void)
{
 const CohFreshOwnerFailure reasons[]={COH_FRESH_OWNER_ENTITY_TABLE_MISMATCH,COH_FRESH_OWNER_CHARACTER_ABSENT,
 COH_FRESH_OWNER_CHARACTER_UNINITIALIZED,COH_FRESH_OWNER_CHARACTER_PARENT,COH_FRESH_OWNER_LINK_TYPE,
 COH_FRESH_OWNER_LINK_NOT_CONNECTED,COH_FRESH_OWNER_LINK_PENDING,COH_FRESH_OWNER_CLIENT_INCIDENCE};
 for(unsigned n=0;n<sizeof(reasons)/sizeof(reasons[0]);n++){
  reset();switch(n){
  case 0:entities[7]=&F(other_entity);break;case 1:F(entity).pchar=NULL;break;
  case 2:F(character).pclass=NULL;break;case 3:F(character).entParent=&F(other_entity);break;
  case 4:F(link).type=NLT_TCP;break;case 5:F(link).connected=0;break;case 6:F(link).pending=1;break;
  case 7:F(array).size=2;fixture.storage[1]=&F(other);F(other).userData=&F(client);break;
  }
  save();CHECK(!fresh_prepare(&F(link),&result));unchanged(1);CHECK(coh_fp_owner_failure==reasons[n]);scenarios++;failures++;
 }
 /* A late original failure never commits the provisional candidate; the first
  * new fallback reason also survives later failed calls and cleanup state. */
 reset();F(entity).owned=0;CHECK(!fresh_prepare(&F(link),&result));
 F(entity).owned=1;F(link).pending=1;CHECK(!fresh_prepare(&F(link),&result));
 CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_INITIAL_NOT_OWNED);
 coh_fp_complete=1;CHECK(coh_fresh_source_owner_failed(1,COH_FRESH_OWNER_INITIAL_STATE));
 CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_INITIAL_NOT_OWNED);scenarios++;
}
int main(void)
{
 sleeping_success();unchanged_active();for(unsigned n=0;n<13;n++)refusal(n);
 state_and_phase();later_original_guards();
 printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"fallback_guard_refusals\":13,\"refusals\":%u,\"unchanged_active_successes\":%u,\"sleeping_successes\":%u,\"runtime_executed\":false,\"world_authority\":false,\"reason_names\":[",checks,scenarios,failures,active_successes,sleeping_successes);
 for(unsigned n=COH_FRESH_OWNER_INITIAL_SLOT_OUTSIDE_TABLE;n<COH_FRESH_OWNER_COUNT;n++)printf("%s\"%s\"",n==COH_FRESH_OWNER_INITIAL_SLOT_OUTSIDE_TABLE?"":",",coh_fp_owner_failures[n]);
 printf("]}\n");return 0;
}
