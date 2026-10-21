#include "coh_original_command_tail.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
typedef uint32_t U32;
static unsigned checks,fixtures;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"line%d %s\n",__LINE__,#v);exit(1);}}while(0)
static unsigned char raw[131072];
static CohOriginalCommandTailWorkspace work;
static const CohOriginalCommandTailWorkspace zero_work;
static CohOriginalCommandTailReport report,actual;
#define COH_ORIGINAL_COMMAND_TYPES
#include "original_command_tail.inc"
#undef COH_ORIGINAL_COMMAND_TYPES
typedef struct{size_t bits;unsigned mode;}Packet;
typedef struct{const char*name,*filename,*displayname,*detailtext,*iconfile;}StoryClue;
typedef struct{int unused;}ScriptVarsTable;
typedef struct{struct{int inZoneEvent;}karmaContainer;}Character;
typedef struct{struct{U32 iKey,iOrder;}combatMonitorStats[MAX_COMBAT_STATS];}Player;
typedef struct{char**perPlayerVars;}FixtureUIData;
typedef struct{char*varName;}FixtureUIVar;
typedef struct{FixtureUIVar**varCache;int uniqueID,type,hidden;}ScriptUIWidget;
typedef struct{Character*pchar;Player*pl;void*client;FixtureUIData**scriptUIData;}Entity;
static struct{int clickToSource;}server_state;
static void pktSendBits(Packet*p,int width,uint32_t value){unsigned n=p->mode?((unsigned)width+7)&~7u:(unsigned)width;CHECK(p->bits+n<=sizeof(raw)*8);for(unsigned i=0;i<n;i++){if((value>>i)&1u)raw[p->bits/8]|=(unsigned char)(1u<<(p->bits%8));p->bits++;}}
static void pktSendBitsPack(Packet*p,int width,uint32_t value){if(p->mode){pktSendBits(p,32,value);return;}for(;;){if(width==32||value<((1u<<(unsigned)width)-1)){pktSendBits(p,width,value);return;}uint32_t top=(1u<<(unsigned)width)-1;pktSendBits(p,width,top);value-=top;width=width>16?32:width*2;}}
static void pktSendBitsAuto(Packet*p,uint32_t value){unsigned widths[]={2,10,24,32};unsigned b=0;while(b<3&&value>=(1u<<widths[b]))b++;pktSendBits(p,2,b);pktSendBits(p,(int)widths[b],value);}
static void pktSendString(Packet*p,const char*s){do{pktSendBits(p,8,(unsigned char)*s);}while(*s++);}
#define saUtilDirtyFileName(s) (s)
#define saUtilTableAndEntityLocalize(s,vars,e) ((void)(vars),(void)(e),(s))
#define ClueIconFile(c) ((c)->iconfile)
static void pktSendF32(Packet*p,float f){uint32_t v;memcpy(&v,&f,4);pktSendBits(p,32,v);}
static void pktSendIfSetBitsPack(Packet*p,int n,uint32_t v){pktSendBits(p,1,v!=0);if(v)pktSendBitsPack(p,n,v);}
static void pktSendIfSetBits(Packet*p,int n,uint32_t v){pktSendBits(p,1,v!=0);if(v)pktSendBits(p,n,v);}
#define ENTTYPE(e) ((void)(e),2)
#define ENTTYPE_PLAYER 2
#define character_InterruptMissionTeleport(c) ((void)(c))
static Packet*sending;
static void cmd(Packet*,unsigned);
static unsigned karma_active;
static uint32_t karma_value(unsigned i){static const uint32_t values[]={0,3,1023,1024,0xffffff,0x1000000,0x7fffffff,0x80000000,UINT32_MAX};CHECK(i<9);return values[i];}
static int g_zoneEventScriptStageAwardsKarma;
#define eaiFind(list,event) ((void)(list),(void)(event),karma_active?0:-1)
#define CharacterCalculateKarmaBucket(c,i,t) ((void)(c),(void)(t),karma_value(i))
#define CharacterCalculateKarma(c,t) ((void)(c),(void)(t),karma_value(4))
#define ScriptKarmaGetMedian(e,z,kind) ((void)(e),(void)(z),(void)(kind),karma_value(5))
#define ScriptKarmaGetAverage(e,z,kind) ((void)(e),(void)(z),(void)(kind),karma_value(6))
#define ScriptKarmaGetActivePlayers(z) ((void)(z),karma_value(7))
#define s_GetBubbleCount(c,t) ((void)(c),(void)(t),karma_value(8))
#define SKT_SORTED_STAT 0
static const void*producer_var_array,*producer_player_array;static unsigned producer_var_count,producer_global;
static int source_ea_size(const void*p){if(p==producer_var_array)return (int)producer_var_count;CHECK(p==producer_player_array);return 1;}
#define eaSize(pp) source_ea_size(pp)
#define eaPush(pp,value) ((void)(pp),(void)(value))
#define ISGLOBAL(s) ((void)(s),producer_global)
#define VTOS(v) ((v)->varName)
#define saUtilScriptLocalize(s) (s)
#define ScriptUIGetPlayerVar(script,name,player) ((void)(script),(void)(name),(void)(player),(const char*)NULL)
#define g_currentScript 0
#define strdup(s) (s)
#define START_PACKET(pak,e,id) {Packet*pak=sending;(void)(e);cmd(pak,id);
#define END_PACKET }
#define COH_ORIGINAL_COMMAND_SENDERS
#include "original_command_tail.inc"
#undef COH_ORIGINAL_COMMAND_SENDERS
static void start(Packet*p,unsigned mode,unsigned begin){memset(raw,0,sizeof(raw));p->bits=begin;p->mode=mode;}
static void cmd(Packet*p,unsigned n){pktSendBitsPack(p,1,n);}
static void entry_batch(Packet*p,unsigned active,unsigned event_variant){Character c={{1}};Entity e={&c,NULL,NULL,NULL};sending=p;karma_active=active;CharacterKarmaStatsSend(&e,17);sendIncarnateTrialStatus(&e,trialStatus_Success);original_window_colors_send(&e,0,0xffffffffu);original_event_start_send(&e);if(event_variant){cmd(p,SERVER_EVENT_START_STATUS);pktSendBits(p,1,0);pktSendBits(p,1,event_variant&1);}}
static void misc_entry_batch(Packet*p,unsigned variant){Character c={{0}};Player pl={0};Entity e={&c,&pl,&pl,NULL};sending=p;SendSelectContact(&e,0);SendSelectTask(&e,1);serveDesaturateInformation(&e,-1.0f,0.0f,0.5f,1.0f);cmd(p,SERVER_POPHELP_EVENT_HAPPENED_BY_TAG);pktSendString(p,"source.pophelp.tag");cmd(p,SERVER_SEND_REWARD_CHOICE);pktSendString(p,"source reward");pktSendBits(p,1,variant&1);pktSendBitsPack(p,3,variant?3:0);if(variant)for(unsigned i=0;i<3;i++){pktSendBits(p,1,i!=0);if(i){pktSendBits(p,1,i&1);pktSendString(p,"choice");}}cmd(p,SERVER_SEND_MORAL_CHOICE);for(unsigned i=0;i<4;i++)pktSendString(p,"source moral");pktSendBitsAuto(p,UINT32_MAX);cmd(p,SERVER_DOOREXIT);pktSendBits(p,1,variant&1);cmd(p,SERVER_SEND_COMBAT_STATS);for(unsigned i=0;i<MAX_COMBAT_STATS;i++){pl.combatMonitorStats[i].iKey=i?0x80000000u+i:0;pl.combatMonitorStats[i].iOrder=i%16;}sendCombatMonitorStats(&e,p);}
static void script_entry_batch(Packet*p,unsigned variant){FixtureUIVar a={"source script"},b={"7200"};FixtureUIVar*vars[]={&a,&b};ScriptUIWidget widget={vars,42,variant?TimerWidget:ListWidget,0};FixtureUIData info={0};FixtureUIData*infos[]={&info};Entity e={NULL,NULL,NULL,infos};sending=p;producer_var_array=&widget.varCache;producer_player_array=&e.scriptUIData;producer_var_count=2;producer_global=variant&1;ScriptUISend(&widget,&e);cmd(p,SERVER_SCRIPT_UI_UPDATE);for(unsigned unknown=0;unknown<2;unknown++){pktSendBits(p,1,1);pktSendBitsPack(p,1,unknown?43:42);pktSendBits(p,1,unknown);pktSendBits(p,1,1);pktSendBitsPack(p,1,0);pktSendString(p,"new variable");pktSendBits(p,1,0);}pktSendBits(p,1,0);widget.uniqueID=43;widget.type=ListWidget;ScriptUISend(&widget,&e);ScriptUISendKillSignal(&e,42);ScriptUISendKillSignal(&e,43);}
static void visited_map_batch(Packet*p,unsigned variant){cmd(p,SERVER_VISITED_MAP_CELLS);if(variant){pktSendBitsPack(p,1,17);pktSendBits(p,1,variant&1);pktSendBits(p,1,1);}else{pktSendBitsPack(p,1,0);pktSendBitsPack(p,1,33);pktSendBits(p,32,0xffffffffu);pktSendBits(p,32,1);}}
static void atlas_entry_batch(Packet*p,unsigned variant){cmd(p,SERVER_RECEIVE_DIALOG);pktSendString(p,"source dialog");cmd(p,SERVER_RECEIVE_INFO_BOX);pktSendBitsPack(p,2,2);pktSendString(p,"source info");cmd(p,SERVER_SEND_CHAT_MSG);pktSendBitsPack(p,10,42);pktSendBitsPack(p,3,2);pktSendF32(p,1);pktSendString(p,"source chat");pktSendF32(p,0);pktSendF32(p,0);cmd(p,SERVER_SET_WAYPOINT);pktSendBits(p,1,variant!=0);pktSendBitsPack(p,1,variant?42:0);if(variant){pktSendBits(p,1,1);pktSendBits(p,1,0);for(unsigned i=0;i<4;i++){pktSendBits(p,1,1);pktSendString(p,"source waypoint");}pktSendBits(p,1,1);pktSendF32(p,0);for(unsigned i=0;i<3;i++)pktSendF32(p,(float)i);}cmd(p,SERVER_MISSION_EXIT);pktSendString(p,"source mission exit");cmd(p,SERVER_TEAMCOMPLETE_PROMPT);cmd(p,SERVER_BROKER_CONTACT);pktSendString(p,"source broker");cmd(p,SERVER_SEND_FLOATING_INFO);pktSendBitsPack(p,1,42);pktSendString(p,"source floater");pktSendBitsPack(p,2,2);pktSendF32(p,0);pktSendBitsPack(p,32,0xffffffffu);cmd(p,SERVER_SEND_PLAY_SOUND);pktSendString(p,"source sound");pktSendBitsAuto(p,0);pktSendF32(p,1);cmd(p,SERVER_SEND_FADE_SOUND);pktSendBitsAuto(p,0);pktSendF32(p,1);}
static void friends_entry_batch(Packet*p,unsigned variant){cmd(p,SERVER_SEND_FRIENDS);pktSendBitsPack(p,1,variant&1);pktSendBitsPack(p,1,3);pktSendBits(p,1,0);for(unsigned i=0;i<2;i++){pktSendBits(p,1,1);pktSendBitsPack(p,1,100+i);pktSendBits(p,1,i);pktSendString(p,"source friend");pktSendBitsPack(p,1,i?INT32_MAX:UINT32_MAX);pktSendBitsPack(p,1,9);if(i){pktSendBitsPack(p,1,17);pktSendString(p,"source map");}}}
static void task_body(Packet*p,unsigned branch){pktSendBits(p,1,1);pktSendString(p,"source.task");pktSendString(p,"task");pktSendString(p,"owner");for(unsigned i=0;i<4;i++)pktSendBitsPack(p,1,i+1);pktSendBitsAuto(p,0);pktSendBitsAuto(p,1);pktSendBits(p,1,0);pktSendBits(p,1,0);pktSendBitsPack(p,2,0);pktSendString(p,"state");pktSendBitsPack(p,1,7);for(unsigned i=0;i<3;i++)pktSendBitsAuto(p,i);for(unsigned i=0;i<9;i++)pktSendBits(p,1,i==8&&branch==2);pktSendBits(p,1,branch==1);if(branch==1){for(unsigned i=0;i<3;i++)pktSendBits(p,32,0x3f800000);pktSendBitsAuto(p,0);pktSendString(p,"maps/City_00_01.txt");pktSendString(p,"mission");}else pktSendBits(p,1,0);if(branch==2){pktSendBitsPack(p,1,1);pktSendBits(p,32,2);pktSendBitsPack(p,1,3);pktSendString(p,"ztype");pktSendString(p,"zname");pktSendString(p,"1 2 3");}}
static void task(Packet*p,unsigned variant,uint32_t size,uint32_t index){cmd(p,SERVER_TASK_STATUS);pktSendBitsPack(p,1,1);pktSendBitsPack(p,1,17);pktSendBits(p,1,1);pktSendBits(p,1,1);pktSendBitsAuto(p,0);pktSendBitsAuto(p,1);pktSendBits(p,1,0);pktSendBits(p,1,0);pktSendBitsPack(p,1,size);pktSendBitsPack(p,1,1);pktSendBitsPack(p,1,index);task_body(p,variant);}
static void contact(Packet*p,uint32_t size,uint32_t index){cmd(p,SERVER_CONTACT_STATUS);for(unsigned i=0;i<14;i++)pktSendBitsAuto(p,0);pktSendBitsAuto(p,size);pktSendBitsAuto(p,0);pktSendBitsAuto(p,1);pktSendBitsAuto(p,index);ContactStatusSendEmpty(p);}
static CohStatus receive(Packet*p,size_t begin){CohRepReader r={{raw,(p->bits+7)/8},p->bits,begin,p->mode,COH_REP_BOUNDED_MESSAGE_MAX},before=r;CohStatus s=coh_original_command_tail_receive(&r,&work,&report,8u<<20,0);CHECK(!memcmp(&r,&before,sizeof(r)));CHECK(!memcmp(&work,&zero_work,sizeof(work)));CHECK(report.end_bit<=r.bits&&report.status==s);return s;}
static void positive(unsigned mode,unsigned begin,unsigned variant){Packet p;start(&p,mode,begin);cmd(&p,SERVER_BEGIN_BYTE_ALIGNED_DATA);p.bits=(p.bits+7)&~(size_t)7;cmd(&p,SERVER_GAME_CMDS);cmd(&p,SERVER_ALL_STATIC_MAP_CELLS);pktSendBitsAuto(&p,42);pktSendBitsAuto(&p,2);pktSendBitsAuto(&p,0);pktSendBitsAuto(&p,17);pktSendBits(&p,1,1);for(unsigned i=0;i<256;i++)pktSendBits(&p,32,i);contact(&p,0,0);cmd(&p,SERVER_ACCESSIBLE_CONTACT_STATUS);pktSendBitsAuto(&p,1);ContactStatusSendEmpty(&p);cmd(&p,SERVER_TASK_VISITLOCATION_UPDATE);pktSendBitsPack(&p,1,2);pktSendString(&p,"one");pktSendString(&p,"two");task(&p,variant,0,0);StoryClue c={"clue","source.clue","display","details","icon"};server_state.clickToSource=1;cmd(&p,SERVER_CLUE_UPDATE);pktSendBitsPack(&p,1,1);ClueSend(&c,NULL,&p,NULL);cmd(&p,SERVER_KEYCLUE_UPDATE);pktSendBitsPack(&p,1,1);ClueSend(&c,NULL,&p,NULL);cmd(&p,SERVER_SOUVENIRCLUE_UPDATE);pktSendBitsPack(&p,1,1);pktSendBitsPack(&p,1,3);pktSendBits(&p,1,1);pktSendString(&p,"source.clue");pktSendString(&p,"display");pktSendString(&p,"icon");entry_batch(&p,variant&1,0);misc_entry_batch(&p,variant);script_entry_batch(&p,variant);visited_map_batch(&p,variant);atlas_entry_batch(&p,variant);friends_entry_batch(&p,variant);cmd(&p,0);CHECK(receive(&p,begin)==COH_OK);CHECK(report.karma_messages==1&&report.karma_values==((variant&1)?9u:0u)&&report.event_start_messages==1&&report.trial_status_messages==1&&report.window_color_messages==1);CHECK(report.tail_complete&&report.terminator&&report.end_bit==p.bits&&report.commands_read==39&&report.static_map_rows==1&&report.static_map_words==256&&report.contact_updates==1);fixtures++;
 for(size_t n=1;n<=16;n++){size_t bits=p.bits;p.bits-=n;CHECK(receive(&p,begin)!=COH_OK);CHECK(!report.tail_complete);p.bits=bits;}
 CohRepReader r={{raw,(p.bits+7)/8},p.bits,begin,mode,COH_REP_BOUNDED_MESSAGE_MAX};size_t need=sizeof(r)+sizeof(work)+sizeof(report)+r.bytes.size+COH_ORIGINAL_COMMAND_STACK_RESERVE+sizeof(void*);CohOriginalCommandTailReport old=report;CHECK(coh_original_command_tail_receive(&r,&work,&report,need-1,0)==COH_LIMIT);CHECK(!memcmp(&old,&report,sizeof(report)));CHECK(coh_original_command_tail_receive(&r,&work,&report,need,0)==COH_OK);CHECK(coh_original_command_tail_receive(&r,&work,&report,8u<<20,SIZE_MAX)==COH_LIMIT);
}
static void negative(unsigned mode){Packet p;start(&p,mode,0);contact(&p,0,UINT32_MAX);cmd(&p,0);CHECK(receive(&p,0)==COH_INVALID);start(&p,mode,0);contact(&p,INT32_MAX,0);CHECK(receive(&p,0)==COH_INVALID);start(&p,mode,0);contact(&p,40,0);CHECK(receive(&p,0)==COH_LIMIT);start(&p,mode,0);task(&p,0,0,UINT32_MAX);CHECK(receive(&p,0)==COH_INVALID);start(&p,mode,0);task(&p,0,INT32_MAX,0);CHECK(receive(&p,0)==COH_INVALID);start(&p,mode,0);task(&p,0,10,0);CHECK(receive(&p,0)==COH_LIMIT);start(&p,mode,0);cmd(&p,999);pktSendBits(&p,32,0xdeadbeef);CHECK(receive(&p,0)==COH_UNSUPPORTED);CHECK(report.end_bit==report.command_begin_bit+(mode?32:0)||!mode);start(&p,mode,0);cmd(&p,0);pktSendBits(&p,8,3);CHECK(receive(&p,0)==COH_UNSUPPORTED&&report.terminator&&!report.tail_complete);start(&p,mode,0);for(unsigned i=0;i<24;i++)cmd(&p,SERVER_GAME_CMDS);cmd(&p,0);CHECK(receive(&p,0)==COH_OK&&report.trace_count==16&&report.trace_omitted==8);}
typedef struct{unsigned id,covered;const char*handler;}DispatchRow;
static const DispatchRow dispatch_rows[]={
#define COH_ORIGINAL_COMMAND_DISPATCH
#define COH_COMMAND_DISPATCH(cmd,handler,covered) {cmd,covered,#handler},
#define COH_COMMAND_DISABLED(cmd,handler,covered)
#include "original_command_tail.inc"
#undef COH_COMMAND_DISABLED
#undef COH_COMMAND_DISPATCH
#undef COH_ORIGINAL_COMMAND_DISPATCH
};
static void dispatch_coverage(void){unsigned covered=0;CHECK(sizeof(dispatch_rows)/sizeof(dispatch_rows[0])==212);for(unsigned i=0;i<212;i++){covered+=dispatch_rows[i].covered;CHECK(dispatch_rows[i].handler&&*dispatch_rows[i].handler);for(unsigned j=0;j<i;j++)CHECK(dispatch_rows[i].id!=dispatch_rows[j].id);if(!dispatch_rows[i].covered){for(unsigned mode=0;mode<2;mode++){Packet p;start(&p,mode,0);cmd(&p,dispatch_rows[i].id);size_t end=p.bits;pktSendBits(&p,32,0xdeadbeef);CHECK(receive(&p,0)==COH_UNSUPPORTED&&report.unimplemented_handler&&!report.unknown_command&&!report.terminator&&!report.tail_complete&&report.active_command==dispatch_rows[i].id&&report.end_bit==end);}}}CHECK(covered==34);}
static void entry_controls(unsigned mode){Packet p;for(unsigned first=0;first<2;first++)for(unsigned second=0;second<2;second++){start(&p,mode,0);cmd(&p,SERVER_EVENT_START_STATUS);pktSendBits(&p,1,first);pktSendBits(&p,1,second);cmd(&p,0);CHECK(receive(&p,0)==COH_OK&&report.event_start_messages==1&&report.tail_complete&&!report.unimplemented_handler&&!report.unknown_command);}
 for(unsigned count=10;count<13;count++){start(&p,mode,0);cmd(&p,SERVER_SEND_KARMA_STATS);pktSendBits(&p,1,1);pktSendBitsAuto(&p,count==12?UINT32_MAX:count);CHECK(receive(&p,0)==COH_INVALID&&!report.unimplemented_handler&&!report.unknown_command&&!report.tail_complete);}
 start(&p,mode,0);cmd(&p,SERVER_SEND_KARMA_STATS);pktSendBits(&p,1,1);pktSendBitsAuto(&p,9);pktSendBitsAuto(&p,1);CHECK(receive(&p,0)==COH_INVALID&&!report.unimplemented_handler&&!report.unknown_command);
 for(unsigned timer=0;timer<2;timer++){start(&p,mode,0);cmd(&p,SERVER_SCRIPT_UI);pktSendBitsPack(&p,1,42);pktSendBits(&p,1,1);pktSendBitsPack(&p,1,timer?TimerWidget:ListWidget);pktSendBits(&p,1,0);pktSendBitsPack(&p,1,timer?0:65);CHECK(receive(&p,0)==(timer?COH_INVALID:COH_LIMIT)&&!report.unimplemented_handler&&!report.unknown_command);}
 start(&p,mode,0);for(unsigned i=0;i<9;i++){cmd(&p,SERVER_SCRIPT_UI);pktSendBitsPack(&p,1,i);pktSendBits(&p,1,1);pktSendBitsPack(&p,1,ListWidget);pktSendBits(&p,1,0);pktSendBitsPack(&p,1,0);}CHECK(receive(&p,0)==COH_LIMIT&&!report.unimplemented_handler&&!report.unknown_command);
 start(&p,mode,0);cmd(&p,SERVER_SCRIPT_UI_UPDATE);for(unsigned i=0;i<65;i++){pktSendBits(&p,1,1);pktSendBitsPack(&p,1,i);pktSendBits(&p,1,0);pktSendBits(&p,1,0);}pktSendBits(&p,1,0);CHECK(receive(&p,0)==COH_LIMIT&&!report.unimplemented_handler&&!report.unknown_command);
 for(unsigned bad=0;bad<2;bad++){start(&p,mode,0);cmd(&p,SERVER_VISITED_MAP_CELLS);pktSendBitsPack(&p,1,0);pktSendBitsPack(&p,1,bad?UINT32_MAX:262145);CHECK(receive(&p,0)==(bad?COH_INVALID:COH_LIMIT)&&!report.unimplemented_handler&&!report.unknown_command);}
 start(&p,mode,0);cmd(&p,SERVER_SEND_FRIENDS);pktSendBitsPack(&p,1,1);pktSendBitsPack(&p,1,1);pktSendBits(&p,1,1);CHECK(receive(&p,0)==COH_INVALID&&!report.unimplemented_handler&&!report.unknown_command);
 start(&p,mode,0);cmd(&p,999);size_t end=p.bits;pktSendBits(&p,32,0xdeadbeef);CHECK(receive(&p,0)==COH_UNSUPPORTED&&!report.unimplemented_handler&&report.unknown_command&&report.end_bit==end);
 start(&p,mode,0);cmd(&p,0);pktSendBits(&p,1,1);CHECK(receive(&p,0)==COH_UNSUPPORTED&&report.terminator&&!report.tail_complete&&!report.unimplemented_handler&&!report.unknown_command);
}
static void invalid(void){CohRepReader r={{raw,32},256,0,0,COH_REP_BOUNDED_MESSAGE_MAX};memset(&report,0xa5,sizeof(report));CohOriginalCommandTailReport old=report;
 CHECK(coh_original_command_tail_receive(NULL,&work,&report,8u<<20,0)==COH_INVALID);CHECK(coh_original_command_tail_receive(&r,NULL,&report,8u<<20,0)==COH_INVALID);CHECK(coh_original_command_tail_receive(&r,&work,NULL,8u<<20,0)==COH_INVALID);CHECK(coh_original_command_tail_receive(&r,&work,&report,0,0)==COH_INVALID);CHECK(coh_original_command_tail_receive(&r,&work,&report,(8u<<20)+1,0)==COH_INVALID);CHECK(coh_original_command_tail_receive(&r,&work,(void*)&work,8u<<20,0)==COH_INVALID);CHECK(coh_original_command_tail_receive(&r,(void*)raw,&report,8u<<20,0)==COH_INVALID);CHECK(coh_original_command_tail_receive((void*)(uintptr_t)(UINTPTR_MAX-4),&work,&report,8u<<20,0)==COH_INVALID);r.bytes.data=(void*)&work;r.bytes.size=sizeof(work);CHECK(coh_original_command_tail_receive(&r,&work,&report,8u<<20,0)==COH_INVALID);r.bytes.data=raw;r.bytes.size=SIZE_MAX;CHECK(coh_original_command_tail_receive(&r,&work,&report,8u<<20,0)==COH_INVALID);r.bytes.size=32;r.compressed=1;r.cursor=1;CHECK(coh_original_command_tail_receive(&r,&work,&report,8u<<20,0)==COH_INVALID);CHECK(!memcmp(&old,&report,sizeof(report)));}
static uint64_t le64(const unsigned char*p){uint64_t v=0;for(unsigned i=0;i<8;i++)v|=(uint64_t)p[i]<<(8*i);return v;}
static void replay(const char*path,const char*begin){FILE*f=fopen(path,"rb");CHECK(f);unsigned char h[88];CHECK(fread(h,1,88,f)==88&&!memcmp(h,"COHIRP01",8));size_t n=fread(raw,1,sizeof(raw),f);CHECK(fgetc(f)==EOF&&!fclose(f));CohRepReader r={{raw,n},(size_t)le64(h+16),strtoull(begin,NULL,10),h[40],COH_REP_BOUNDED_MESSAGE_MAX};CHECK(coh_original_command_tail_receive(&r,&work,&actual,8u<<20,0)==COH_OK);CHECK(actual.tail_complete&&actual.terminator&&actual.end_bit==r.bits&&actual.commands_read==(r.bits==303112?12u:11u)&&actual.contact_rows==2&&actual.contact_updates==1);CHECK(!memcmp(&work,&zero_work,sizeof(work)));}
int main(int argc,char**argv){CHECK(argc==1||argc==3);for(unsigned mode=0;mode<2;mode++){for(unsigned startbit=0;startbit<8;startbit+=3){if(mode&&startbit)continue;for(unsigned variant=0;variant<3;variant++)positive(mode,startbit,variant);}negative(mode);entry_controls(mode);}dispatch_coverage();invalid();if(argc==3)replay(argv[1],argv[2]);printf("{\"passed\":true,\"checks\":%u,\"fixtures\":%u,\"workspace_bytes\":%zu,\"report_bytes\":%zu,\"heap_allocations\":0,\"context_bytes\":%zu,\"dispatch_active\":212,\"dispatch_qualified\":34,\"qualified_inline_handlers\":1,\"actual_replay\":{\"supplied\":%s,\"begin\":%zu,\"end\":%zu,\"packet_bits\":%zu,\"tail_complete\":%u,\"commands\":%u}}\n",checks,fixtures,sizeof(work),sizeof(report),sizeof(void*),argc==3?"true":"false",actual.begin_bit,actual.end_bit,actual.packet_bits,actual.tail_complete,actual.commands_read);return 0;}
