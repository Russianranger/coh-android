#include "coh_original_ent_costume.h"
#include "coh_entities.h"
#include <setjmp.h>
#include <stdint.h>
#include <limits.h>
#include <string.h>
#include <strings.h>
enum{false=0,true=1};
typedef uint32_t U32;typedef uint8_t U8;typedef float F32;typedef int bool;
#define COH_ORIGINAL_ENT_COSTUME_TYPES
#include "original_ent_costume_receive.inc"
#undef COH_ORIGINAL_ENT_COSTUME_TYPES
typedef CohOriginalCostumeObject Costume;
typedef struct{unsigned dummy;} SeqInst;
typedef CohOriginalCostumeColor Color;
typedef struct{const char *regionName;Color color[2];} CustomNPCCostumePart;
typedef struct{char *originalNPCName;CustomNPCCostumePart **parts;Color skinColor;} CustomNPCCostume;
typedef struct{const char *pchFullName;} BasePower;
typedef struct{const BasePower *power;const char *powerFullName;struct{Color primary,secondary;}customTint;const char *token;unsigned padding[5];}PowerCustomization;
typedef struct{PowerCustomization **powerCustomizations;unsigned padding[5];}PowerCustomizationList;
typedef struct{CohEntCharacterStats stats;uint32_t iCombatModShift;}Character;
typedef struct{
 int titleThe,titleColors[2],titleBadge,glowieUnlocked,attachArticle,respecTokens,lastTurnstileEventID,lastTurnstileMissionID,helperStatus;char titleTheText[10],titleCommon[32],titleOrigin[32],titleSpecial[128];
 int current_costume,num_costume_slots,pendingCostumeIgnoreTime,num_costumes_stored,
  pendingCostumeForceTime,pendingCostumeNumber,current_powerCust,supergroup_mode,hide_supergroup_emblem;
 Costume *costume[10],*pendingCostume,*superCostume;char costumeFxSpecial[260];PowerCustomizationList *powerCustomizationLists[10];
} Player;
typedef struct{
 Player *pl;SeqInst *seq;Character *pchar;uint32_t pkt_id_basicAttrDef,pkt_id_targetting,pkt_id_status_effects,bitfieldVisionPhases,exclusiveVisionPhase,shouldIConYellow;char name[128];int gender,name_gender;const Costume *costume;Costume *ownedCostume;
 CustomNPCCostume *customNPC_costume;char *costumeWorldGroup;
 int npcIndex,costumeIndex,randSeed,next_move_idx,next_move_bits;float xlucency;PowerCustomizationList *ownedPowerCustomizationList,*powerCust;
} Entity;
typedef struct{
 CohRepReader reader;CohOriginalEntCostumeReport report;jmp_buf trap;
 const CohClientCostumeSlots *slots;CohOriginalCostumeWorkspace *workspace;
 CohOriginalCostumeSnapshot *capture;uint32_t body_parts,selected_index;
 union{CohEntTarget target;CohEntStatusEffects status;CohEntInventorySizes inventory;}suffix;Entity entity;Player player;Character character;Costume dummy;unsigned initial,pchar_things;
 CustomNPCCostume custom;CustomNPCCostumePart npc_parts[63];
 CustomNPCCostumePart *npc_pointers[63];unsigned npc_count;
 int hasDebugInfo;PowerCustomizationList power_list;PowerCustomization power_entry;PowerCustomization *power_pointers[1];
 char literal[260];unsigned in_power,power_prefix;unsigned in_rewards,reward_groups,in_sg,npc_field,prefix_step,self;
} Packet;
typedef struct{unsigned kind;} Table;typedef const Table *cStashTable;
static const Table ordinary={1};
#define costume_HashTable (&ordinary)
#define TEST_CLIENT 1
#define SERVER 0
#define IS_OOP(id) ((void)(id),1)
#define UPDATE_PACKET_ID(id) ((void)(id))
#define MAX_NAME_LEN 128
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define NUM_BITS_PER_RAGDOLL_QUAT_ELEM 10
#define strncpyt(d,s,n) source_copy((d),(n),(s))
#define SendBasicCharacter 0
#define sdUnpackDiff(s,p,c,id,abs) ((void)(s),(void)(id),(void)(abs),source_stats((p),(c)))
#define character_LevelFinalize(c,b) ((void)(c),(void)(b))
#define MAX_COSTUMES 10
#define dummy_ent_powerCust (&pak->power_list)
static const int g_PowerDictionary;
#define ParsePowerCustomizationList 0
#define StructAllocString(s) (s)
#define StructInit(p,n,s) ((void)(n),(void)(s),memset((p),0,sizeof(*(p))))
#define StructCopy(s,a,b,c,d) ((void)(s),(void)(c),(void)(d),*(b)=*(a))
#define eaQSort(a,b) ((void)(a),(void)sizeof(#b))
#define powerdict_GetBasePowerByCRC(d,c) source_power_lookup(pak,(d),(c))
#define pktGetIndexedString outerGetIndexedString
#define START_BIT_COUNT(pak,label) source_field((pak),(label))
#define STOP_BIT_COUNT(...)
#define START_BIT_COUNT_TICK(...)
#define STOP_BIT_COUNT_TICK(...)
#define stricmp strcasecmp
#define ENTTYPE(e) ((void)(e),0)
#define ENTTYPE_MISSION_ITEM 9
#define ENTTYPE_PLAYER 1
#define MENU_SUPERCOSTUME 1
#define MENU_TAILOR 2
#define MENU_GENDER 3
#define MENU_BODY 4
#define CC_EMOTE_BASIC_TIMEOUT 1
#define CC_EMOTE_IGNORE_EXTRA_TIMEOUT 1
#define playerPtr() (&pak->entity)
#define menuCanSetCostumeAndPowerCust() 0
#define shell_menu() 1
#define isMenu(n) ((void)(n),0)
#define timerSecondsSince2000() 0
#define GetBodyPartCount() ((int)pak->body_parts)
#define dummy_ent_costume (&pak->dummy)
#define costume_as_const(c) ((const Costume*)(c))
#define costume_init(c) ((void)(c))
#define costume_Apply(e) ((void)(e))
#define costumeApplyNPCColorsToCostume(c,n) ((void)(c),(void)(n))
#define costume_create(n) ((void)(n),&pak->dummy)
#define entUseCopyOfCurrentCostumeAndOwn(e) ((void)(e),&pak->dummy)
#define entUseCopyOfCostume(e,c) ((void)(e),(void)(c))
#define entSetSeq(e,s) ((void)(e),(void)(s))
#define seqLoadInst(s,a,b,c,e) ((void)(s),(void)(a),(void)(b),(void)(c),(void)(e),(SeqInst*)0)
#define SEQ_LOAD_FULL 1
#define demoRecordAppearance(e) ((void)(e))
#define demoRecordMove(e,a,b) ((void)(e),(void)(a),(void)(b))
#define log_printf(...) ((void)0)
#define TODO() ((void)0)
#define tailor_exit(n) ((void)(n))
#define strdup(s) ((char*)(s))
#define Strncpyt(dst,src) ((void)source_copy((dst),sizeof(dst),(src)))
#define fxCleanFileName(d,s) ((void)(d),(void)(s))
#define StructDestroy(schema,p) ((void)(schema),(void)(p))
#define ParseCustomNPCCostume 0
#define StructAllocRaw(n) source_alloc(pak,(n))
#define StructInitFields(schema,c) ((void)(schema),source_npc_init(pak,(c)))
#define eaPush(a,p) source_push(pak,(void*)(a),(void*)(p))
#define costumereward_clear(n) ((void)(n))
#define costumereward_add(s,n) ((void)(s),(void)(n))
static const int demo_recording=0,ent_create=0;
static int g_costume_apply_hack;
static void fail(Packet *pak,CohStatus status){pak->report.status=status;longjmp(pak->trap,1);}
static void source_copy(char *d,size_t n,const char*s){size_t k=s?strlen(s):0;if(k>=n)k=n-1;if(k)memcpy(d,s,k);d[k]=0;}
static void source_field(Packet *pak,const char *name){
 if(!strcmp(name,"FullCostume")){if(pak->in_power){pak->report.field=COH_ENT_COSTUME_POWER_LIST;pak->power_prefix=1;}else{pak->report.field=COH_ENT_COSTUME_REWARDS;pak->prefix_step=1;}}
 else if(!strcmp(name,"SupergroupCostume")){pak->in_sg=1;pak->report.field=COH_ENT_COSTUME_SG_BODY;}
 else if(!strcmp(name,"entReceiveTargetUpdate"))pak->report.field=COH_ENT_COSTUME_TARGET;
 else if(!strcmp(name,"entReceiveStatusEffects"))pak->report.field=COH_ENT_COSTUME_STATUS;
 else if(!strcmp(name,"character_ReceiveInventorySizes"))pak->report.field=COH_ENT_COSTUME_INVENTORY;
 else if(!strcmp(name,"NpcCostume")){pak->report.field=COH_ENT_COSTUME_NPC_FIELDS;pak->npc_field=0;}
}
static U32 pktGetBits(Packet *pak,int n){
 U32 value=0;CohStatus s=coh_rep_read(&pak->reader,(unsigned)n,&value);if(s!=COH_OK)fail(pak,s);
 if(n<32&&value>=(1u<<(unsigned)n))fail(pak,COH_INVALID);
 if(pak->in_rewards&&n==32){if(value>256)fail(pak,COH_LIMIT);pak->reward_groups++;}
 if(!pak->in_rewards&&pak->prefix_step){switch(pak->prefix_step){
 case 1:if(n!=1)fail(pak,COH_INVALID);pak->self=value;pak->prefix_step=value?0:2;break;
 case 2:if(n!=1)fail(pak,COH_INVALID);pak->prefix_step=pak->self?3:5;break;
 case 3:if(n!=8||value>=10||value!=pak->selected_index)fail(pak,COH_INVALID);pak->prefix_step=4;break;
 case 4:if(n!=8)fail(pak,COH_INVALID);pak->prefix_step=5;break;
 case 5:if(n!=1)fail(pak,COH_INVALID);pak->prefix_step=value?6:0;break;
 case 6:if(n!=4||!value||value>10||pak->selected_index>=value)fail(pak,COH_INVALID);pak->prefix_step=0;break;
 default:fail(pak,COH_INVALID);}}

 if(n==1)switch(pak->report.field){
  case COH_ENT_COSTUME_SG_FLAG:pak->report.supergroup_present=value;pak->report.field=value?COH_ENT_COSTUME_SG_BODY:COH_ENT_COSTUME_FX_FLAG;break;
  case COH_ENT_COSTUME_SG_MODE:pak->report.supergroup_mode=value;pak->report.field=COH_ENT_COSTUME_SG_HIDE;break;
  case COH_ENT_COSTUME_SG_HIDE:pak->report.hide_emblem=value;pak->report.field=COH_ENT_COSTUME_FX_FLAG;break;
  case COH_ENT_COSTUME_FX_FLAG:pak->report.fx_present=value;pak->report.field=value?COH_ENT_COSTUME_FX_STRING:COH_ENT_COSTUME_NPC_FLAG;break;
  case COH_ENT_COSTUME_NPC_FLAG:pak->report.npc_fallthrough=value;pak->report.field=value?COH_ENT_COSTUME_NPC_FIELDS:COH_ENT_COSTUME_APPEARANCE_END;break;
  default:break;
 }
 return value;
}
static U32 pktGetBitsAuto(Packet *pak){static const unsigned bins[]={2,10,24,32};U32 bin=pktGetBits(pak,2),value=pktGetBits(pak,(int)bins[bin]);if(pak->in_power&&pak->report.field==COH_ENT_COSTUME_POWER_LIST){if(value>INT_MAX)fail(pak,COH_LIMIT);pak->report.power_entry_count=value;}return value;}
static U32 pktGetBitsPack(Packet *pak,int n){
 U32 value=0;CohStatus s=coh_rep_pack(&pak->reader,(unsigned)n,&value);if(s!=COH_OK)fail(pak,s);if(value>INT_MAX)fail(pak,COH_LIMIT);
 if(pak->report.field==COH_ENT_COSTUME_NPC_FIELDS){if(!pak->npc_field&&n==12){pak->report.npc_index=value;pak->npc_field=1;}else if(pak->npc_field==1&&n==1){pak->report.npc_costume_index=value;pak->npc_field=2;}}
 return value;
}
static U32 pktGetIfSetBitsPack(Packet *pak,int n){U32 value=pktGetBits(pak,1)?pktGetBitsPack(pak,n):0;if(pak->report.field==COH_ENT_COSTUME_SELECTOR){pak->report.selector=value;if(value!=AT_ENTIRE_COSTUME)fail(pak,COH_UNSUPPORTED);}if(pak->report.field==COH_ENT_COSTUME_POWER_SELECTOR){pak->report.power_selector=value;if(value!=AT_ENTIRE_COSTUME&&value!=AT_NO_APPEARANCE)fail(pak,COH_UNSUPPORTED);}return value;}
static U32 pktGetIfSetBits(Packet *pak,int n){return pktGetBits(pak,1)?pktGetBits(pak,n):0;}
static char *pktGetString(Packet *pak){unsigned i;for(i=0;i<260;i++){pak->literal[i]=(char)pktGetBits(pak,8);if(!pak->literal[i]){if(pak->report.field==COH_ENT_COSTUME_FX_STRING){pak->report.fx_bytes=i;pak->report.field=COH_ENT_COSTUME_NPC_FLAG;}return pak->literal;}}fail(pak,COH_LIMIT);return NULL;}
static const char *pktGetIfSetString(Packet *pak){return pktGetBits(pak,1)?pktGetString(pak):NULL;}
static const char *allocAddString(const char *s){return s;}
static uint32_t word(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int source_bits(Packet *pak,cStashTable table){(void)table;if(!pak->slots)fail(pak,COH_UNSUPPORTED);return 15;}
static int source_index(Packet *pak,cStashTable table,uint32_t index,const char **out){uint32_t at,n;(void)table;if(!pak->slots)fail(pak,COH_UNSUPPORTED);if(index>=32768||!(at=pak->slots->index[index])){*out=NULL;return 0;}if(at>pak->slots->raw.size-4)fail(pak,COH_INVALID);n=word(pak->slots->raw.data+at);if(n>=260||n>pak->slots->raw.size-at-4)fail(pak,COH_INVALID);memcpy(pak->literal,pak->slots->raw.data+at+4,n);pak->literal[n]=0;*out=pak->literal;return 1;}
#define defaultBitsPack(t) source_bits(pak,(t))
#define stashFindKeyByIndex(t,i,o) source_index(pak,(t),(uint32_t)(i),(o))
#define stashFindIndexByKey(t,s,o) ((void)(t),(void)(s),(void)(o),0)
static const int g_bAssertOnBitStreamError=0,do_not_assert_on_bad_indexed_string_read=0;
#define assert(v) do{if(!(v))fail(pak,COH_INVALID);}while(0)
static void *source_alloc(Packet *pak,size_t n){if(pak->in_power){if(n==sizeof(PowerCustomizationList)){pak->report.power_lists_read++;return &pak->power_list;}if(n==sizeof(PowerCustomization)){pak->report.field=COH_ENT_COSTUME_POWER_CRC;return &pak->power_entry;}fail(pak,COH_INVALID);}if(n==sizeof(CustomNPCCostume)){memset(&pak->custom,0,sizeof(pak->custom));return &pak->custom;}if(n==sizeof(CustomNPCCostumePart)){if(pak->npc_count>=63)fail(pak,COH_LIMIT);return &pak->npc_parts[pak->npc_count];}fail(pak,COH_UNSUPPORTED);return NULL;}
static void source_npc_init(Packet *pak,CustomNPCCostume *c){memset(c,0,sizeof(*c));memset(pak->npc_pointers,0,sizeof(pak->npc_pointers));c->parts=pak->npc_pointers;pak->npc_count=0;pak->report.field=COH_ENT_COSTUME_NPC_CUSTOM;}
static void source_push(Packet *pak,void *array,void *p){if(pak->in_power)fail(pak,COH_UNSUPPORTED);CustomNPCCostumePart ***a=array;if(pak->npc_count>=63)fail(pak,COH_LIMIT);(*a)[pak->npc_count++]=p;}
static const BasePower *source_power_lookup(Packet *pak,const int *ignored,int crc){(void)ignored;pak->report.field=COH_ENT_COSTUME_POWER_CRC;pak->report.power_crc=(uint32_t)crc;pak->report.required_table=1;fail(pak,COH_UNSUPPORTED);return NULL;}
static const Costume *npcDefsGetCostume(int npc,int index){(void)npc;(void)index;return NULL;}
static int costume_receive(Packet *pak,Costume *costume){
 CohStatus s;CohOriginalCostumeSnapshot *capture=NULL;(void)costume;
 if(!pak->in_sg){pak->report.field=COH_ENT_COSTUME_BODY;pak->report.bodies_expected=pak->player.num_costumes_stored?(uint32_t)pak->player.num_costumes_stored:1;if(pak->report.bodies_expected>10||pak->report.bodies_read>=10)fail(pak,COH_LIMIT);if(pak->report.bodies_read==pak->selected_index)capture=pak->capture;}
 s=coh_original_costume_receive_slots_capture(&pak->reader,pak->body_parts,pak->slots,pak->workspace,&pak->report.body,capture);
 if(s!=COH_OK){pak->reader.cursor=pak->report.body.failure_bit;fail(pak,s);}if(!pak->report.body.costume_complete)fail(pak,COH_INVALID);pak->reader.cursor=pak->report.body.end_bit;
 if(pak->in_sg){pak->report.supergroup_complete=1;pak->report.field=COH_ENT_COSTUME_SG_MODE;}
 else{pak->report.main_body_end_bit=pak->reader.cursor;if(pak->report.bodies_read==pak->selected_index){pak->report.selected_complete=1;pak->report.selected_body_end_bit=pak->reader.cursor;}pak->report.bodies_read++;if(pak->report.bodies_read==pak->report.bodies_expected)pak->report.field=COH_ENT_COSTUME_SG_FLAG;}
 return 1;
}
static void source_stats(Packet *pak,Character *c){CohEntFailure failure={0};CohStatus s=coh_ent_character_stats(&pak->reader,1,0,&c->stats,&failure);if(s!=COH_OK){pak->reader.cursor=failure.bit;fail(pak,s);}}
static int entReceiveTargetUpdate(Packet *pak,Entity *e,int oo,int self){CohEntFailure f={0};(void)e;(void)oo;memset(&pak->suffix,0,sizeof(pak->suffix));CohStatus s=coh_ent_target(&pak->reader,1,(uint32_t)self,&pak->suffix.target,&f);if(s!=COH_OK){pak->reader.cursor=f.bit;fail(pak,s);}return 1;}
static void character_ReceiveStatusEffects(Packet *pak,Character *c,int oo){CohEntFailure f={0};(void)c;(void)oo;memset(&pak->suffix,0,sizeof(pak->suffix));CohStatus s=coh_ent_status_effects(&pak->reader,1,&pak->suffix.status,&f);if(s!=COH_OK){pak->reader.cursor=f.bit;fail(pak,s);}}
static int entReceiveStatusEffects(Packet *,Entity *,bool);
static void character_ReceiveInventorySizes(Character *c,Packet *pak){CohEntFailure f={0};(void)c;memset(&pak->suffix,0,sizeof(pak->suffix));CohStatus s=coh_ent_inventory_sizes(&pak->reader,&pak->suffix.inventory,&f);if(s!=COH_OK){pak->reader.cursor=f.bit;fail(pak,s);}}
static void receive_vision(Packet *pak){Entity *e=&pak->entity;unsigned pchar_things=pak->pchar_things,isSelf=1;
#define COH_ORIGINAL_ENT_INITIAL_FIELDS
#include "original_ent_costume_receive.inc"
#undef COH_ORIGINAL_ENT_INITIAL_FIELDS
 pak->report.vision_complete=1;pak->report.field=COH_ENT_COSTUME_TASKFORCE;
}
static void observed_rewards(Packet *,Entity *);
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-variable"
#pragma GCC diagnostic ignored "-Wunused-but-set-variable"
#pragma GCC diagnostic ignored "-Wimplicit-fallthrough"
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wswitch"
#include "original_ent_costume_receive.inc"
#pragma GCC diagnostic pop
#undef ent_ReceiveCostumeRewards
static void observed_rewards(Packet *pak,Entity *e){pak->in_rewards=1;pak->report.field=COH_ENT_COSTUME_REWARDS;ent_ReceiveCostumeRewards(pak,e);pak->in_rewards=0;pak->prefix_step=2;pak->report.field=COH_ENT_COSTUME_BODY;}
static void run(Packet *volatile pak){if(!setjmp(pak->trap)){if(!entReceiveCostume(pak,&pak->entity,1))fail(pak,COH_UNSUPPORTED);pak->report.appearance_complete=1;pak->report.appearance_end_bit=pak->reader.cursor;pak->report.field=COH_ENT_COSTUME_XLUCENCY;(void)entReceiveXlucency(pak,&pak->entity,1);pak->report.xlucency_complete=1;pak->report.field=COH_ENT_COSTUME_POWER_SELECTOR;pak->report.power_begin_bit=pak->reader.cursor;pak->in_power=1;(void)entReceivePowerCust(pak,&pak->entity,1);pak->report.power_complete=1;pak->report.power_end_bit=pak->reader.cursor;pak->report.field=COH_ENT_COSTUME_TITLES;if(pak->initial){pak->in_power=0;(void)entReceiveTitles(pak,&pak->entity,1);pak->report.titles_complete=1;pak->report.field=COH_ENT_COSTUME_RAGDOLL;(void)entGetRagdollIgnore(pak,&pak->entity);pak->report.ragdoll_complete=1;pak->report.field=COH_ENT_COSTUME_BASIC_STATS;if(pak->pchar_things)(void)entReceiveCharacterStats(pak,&pak->entity,1);pak->report.basic_stats_complete=1;pak->report.field=COH_ENT_COSTUME_VISION;receive_vision(pak);CohStatus tf=coh_original_taskforce_receive(&pak->reader,pak->body_parts,pak->slots,pak->workspace,&pak->report.taskforce);pak->reader.cursor=tf==COH_OK?pak->report.taskforce.end_bit:pak->report.taskforce.failure_bit;if(tf!=COH_OK)fail(pak,tf);pak->report.taskforce_complete=1;pak->report.field=COH_ENT_COSTUME_RARE_PREFIX;}}}
static int span(const void*p,size_t n){return p&&(uintptr_t)p<=UINTPTR_MAX-n;}
static int apart(const void*a,size_t an,const void*b,size_t bn){return(uintptr_t)a+an<=(uintptr_t)b||(uintptr_t)b+bn<=(uintptr_t)a;}
static CohStatus receive_component(const CohRepReader *reader,uint32_t parts,uint32_t selected,uint32_t initial,uint32_t pchar_things,const CohClientCostumeSlots *slots,CohOriginalCostumeWorkspace *workspace,CohOriginalCostumeSnapshot *capture,CohOriginalEntCostumeReport *out){
 const void *p[8];size_t n[8];unsigned i,j,k=5;Packet state;
 if(!span(reader,sizeof(*reader))||!workspace||!out||!parts||parts>30||selected>=10||initial>1||pchar_things>1)return COH_INVALID;
 if((uintptr_t)reader%sizeof(void*)||(uintptr_t)workspace%sizeof(void*)||(uintptr_t)out%sizeof(void*)||(capture&&(uintptr_t)capture%sizeof(uint32_t))||(slots&&(uintptr_t)slots%sizeof(void*)))return COH_INVALID;
 p[0]=reader;n[0]=sizeof(*reader);p[1]=workspace;n[1]=sizeof(*workspace);p[2]=out;n[2]=sizeof(*out);p[3]=reader->bytes.data;n[3]=reader->bytes.size;p[4]=capture;n[4]=capture?sizeof(*capture):0;
 if(slots){if(!span(slots,sizeof(*slots)))return COH_INVALID;p[k]=slots;n[k++]=sizeof(*slots);p[k]=slots->raw.data;n[k++]=slots->raw.size;p[k]=slots->index;n[k++]=COH_CLIENT_COSTUME_INDEX_BYTES;}
 for(i=0;i<k;i++){if(!n[i])continue;if(!span(p[i],n[i]))return COH_INVALID;for(j=0;j<i;j++)if(n[j]&&!apart(p[i],n[i],p[j],n[j]))return COH_INVALID;}
 {size_t cap=reader->max_bytes?reader->max_bytes:COH_REP_MESSAGE_MAX;if(cap>COH_REP_BOUNDED_MESSAGE_MAX||reader->bytes.size>cap||reader->cursor>reader->bits||reader->bits>reader->bytes.size*8||reader->compressed>1||(reader->compressed&&(reader->cursor&7)))return COH_INVALID;}
 if(slots&&(!slots->raw.data||slots->raw.size!=COH_CLIENT_COSTUME_RAW_BYTES||!slots->index||slots->capacity[0]!=32768||slots->capacity[1]!=256||slots->capacity[2]!=512))return COH_INVALID;
 memset(&state,0,sizeof(state));state.reader=*reader;state.report.begin_bit=reader->cursor;state.report.packet_bits=reader->bits;state.report.field=COH_ENT_COSTUME_SELECTOR;state.report.selected_body=selected;state.body_parts=parts;state.selected_index=selected;state.slots=slots;state.workspace=workspace;state.capture=capture;state.initial=initial;state.pchar_things=pchar_things;state.entity.pchar=&state.character;state.entity.pl=&state.player;state.player.current_costume=(int)selected;
 run(&state);state.report.end_bit=state.reader.cursor;state.report.failure_bit=state.reader.cursor;*out=state.report;
 {volatile unsigned char *v=(volatile unsigned char*)&state;size_t bytes=sizeof(state);while(bytes--)*v++=0;}
 return out->status;
}

CohStatus coh_original_ent_costume_receive(const CohRepReader *r,uint32_t n,uint32_t selected,const CohClientCostumeSlots*s,CohOriginalCostumeWorkspace*w,CohOriginalCostumeSnapshot*c,CohOriginalEntCostumeReport*out){return receive_component(r,n,selected,0,0,s,w,c,out);}
CohStatus coh_original_ent_costume_receive_initial(const CohRepReader*r,uint32_t n,uint32_t selected,uint32_t pchar,const CohClientCostumeSlots*s,CohOriginalCostumeWorkspace*w,CohOriginalCostumeSnapshot*c,CohOriginalEntCostumeReport*out){return receive_component(r,n,selected,1,pchar,s,w,c,out);}
const char *coh_original_ent_costume_field_name(uint32_t n){static const char *const names[]={"none","appearance selector","costume rewards","main costume body","Supergroup costume presence","Supergroup costume body","Supergroup mode","Supergroup emblem","costume FX presence","costume FX string","NPC costume fallthrough","NPC costume fields","custom NPC costume","appearance end","translucency","entity suffix","NPC definitions","power customization selector","power customization list","BasePower CRC lookup","titles","ragdoll","basic character statistics","vision phases","target update","status effects","inventory sizes","taskforce parameters","later very-rare entity fields"};return n<sizeof(names)/sizeof(names[0])?names[n]:"unknown source field";}
