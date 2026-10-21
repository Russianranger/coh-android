#include "coh_original_command_tail.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <setjmp.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
typedef uint32_t U32;
#define COH_ORIGINAL_COMMAND_TYPES
#include "original_command_tail.inc"
#undef COH_ORIGINAL_COMMAND_TYPES
typedef struct{unsigned unused;}VisitedStaticMap;
typedef struct{int type,uniqueID;char**varList;}ScriptUIClientWidget;
typedef struct{struct{U32 color;}loc;}CommandWindow;
typedef struct Entity{int id;}Entity;
typedef struct {int type,handle,id,dbid,context,subhandle,iconBInCompass,contactType;void*iconB;float angle;void *icon,*destPNPC;Entity *destEntity;float world_location[4][3];char mapName[512],name[256];} Destination;
typedef struct {char *name,*locationDescription,*filename,*callOverride,*askAboutOverride,*leaveOverride,*imageOverride;int npcNum,handle,taskcontext,tasksubhandle,notifyPlayer,hasTask,canUseCell,isNewspaper,onStoryArc,onMiniArc,wontInteract,metaContact,currentCP,friendCP,confidantCP,completeCP,heistCP,alliance,hasLocation;unsigned tipType,currentOverheadIconState;Destination location;}ContactStatus;
typedef struct {int levelAdjust,teamSize,dontReduceBoss,alwaysAV;}StoryDifficulty;
typedef struct {int ownerDbid,context,subhandle,level,alliance;StoryDifficulty difficulty;char description[256],owner[129],state[256],detail[20001],intro[256],filename[256];int isComplete,isMission,hasRunningMission,isSGMission,hasLocation,detailInvalid,zoneTransfer,teleportOnComplete,enforceTimeLimit,isAbandonable,isZowie;Destination location;U32 timeout,timezero,timerType,failOnTimeout,zinfo,zseed;int zmap_id;char ztype[128],zname[128];int zpoolSize[8];}TaskStatus;
typedef struct {char *name,*filename,*displayname,*detailtext,*iconfile;}StoryClue;
typedef struct {U32 uid;char*filename,*displayName,*icon;}SouvenirClue;
typedef struct{CohRepReader reader;CohOriginalCommandTailReport report;jmp_buf trap;VisitedStaticMap map;ContactStatus row[32],*rows[32],**list;ContactStatus*accessible_rows[32],**accessible;unsigned allocated,count,accessible_count;char strings[65536];size_t string_used;char text[4096];U32 times[5],earned[5],hero,vigilante,villain,rogue;int dirty;TaskStatus task[4],*task_rows[4],**tasks;unsigned task_alloc,task_count;void**visits,**clues,**keys;StoryClue clue;SouvenirClue souvenir;unsigned tokens;char*token_cursor;ScriptUIClientWidget karma_widget;char*karma_vars[2];ScriptUIClientWidget**karma_list;unsigned karma_var_count;CommandWindow windows[MAX_WINDOW_COUNT];struct{int pendingTSMapXfer;}game;TrialStatus trial_status;}Packet;
typedef char StateFitsWorkspace[(sizeof(Packet)<=sizeof(CohOriginalCommandTailWorkspace))?1:-1];
static void fail(Packet*p,CohStatus s){p->report.status=s;longjmp(p->trap,1);}
static U32 pktGetBits(Packet*p,int n){U32 v=0;CohStatus s=coh_rep_read(&p->reader,(unsigned)n,&v);if(s!=COH_OK)fail(p,s);if(n<32&&v>=(1u<<(unsigned)n))fail(p,COH_INVALID);return v;}
static U32 raw_pack(Packet*p,int n){U32 v=0;CohStatus s=coh_rep_pack(&p->reader,(unsigned)n,&v);if(s!=COH_OK)fail(p,s);return v;}
static U32 pktGetBitsAuto(Packet*p){static const unsigned bins[]={2,10,24,32};U32 bin=pktGetBits(p,2);return pktGetBits(p,(int)bins[bin]);}
/* Original unchecked array subscripts and signed size+1 are guarded at their
 * generated source call lines before either source operation executes. */
static U32 command_auto_line(Packet*p,int line){U32 v=pktGetBitsAuto(p);if(line==COMMAND_CONTACT_INDEX_LINE){if(v>=p->count)fail(p,COH_INVALID);p->report.contact_updates++;}if(line==COMMAND_CONTACT_SIZE_LINE&&v==0x7fffffffu)fail(p,COH_INVALID);if(line==COMMAND_KARMA_COUNT_LINE){if(v>CKR_COUNT+5)fail(p,COH_INVALID);p->report.karma_values+=v;}return v;}
static U32 command_pack_line(Packet*p,int n,int line){U32 v=raw_pack(p,n);if(line==COMMAND_TASK_INDEX_LINE&&v>=p->task_count)fail(p,COH_INVALID);if(line==COMMAND_TASK_SIZE_LINE&&v==0x7fffffffu)fail(p,COH_INVALID);return v;}
static float pktGetF32(Packet*p){U32 v=pktGetBits(p,32);float f;memcpy(&f,&v,4);return f;}
static char *pktGetString(Packet*p){for(size_t i=0;i<sizeof(p->text);i++){p->text[i]=(char)pktGetBits(p,8);if(!p->text[i])return p->text;}fail(p,COH_LIMIT);return NULL;}
static char *duplicate(Packet*p,const char*s){size_t n=strlen(s)+1;if(n>sizeof(p->strings)-p->string_used)fail(p,COH_LIMIT);char*d=p->strings+p->string_used;memcpy(d,s,n);p->string_used+=n;return d;}
static char *copy_text(Packet*p,char*d,const char*s,size_t n){size_t l=strlen(s);if(l>=n)fail(p,COH_LIMIT);memcpy(d,s,l+1);return d;}
/* Earray storage uses byte copies: typed pointer rows never alias void**.
 * Clue/visit publication is discarded; those lists never affect wire framing. */
static unsigned *list_count(Packet*p,const void*v){if(v==&p->list)return &p->count;if(v==&p->accessible)return &p->accessible_count;if(v==&p->tasks)return &p->task_count;if(v==&p->karma_widget.varList)return &p->karma_var_count;return NULL;}
static void *list_storage(Packet*p,const void*v){if(v==&p->list)return p->rows;if(v==&p->accessible)return p->accessible_rows;if(v==&p->tasks)return p->task_rows;if(v==&p->karma_widget.varList)return p->karma_vars;return p->rows;}
static int list_size(Packet*p,const void*v){unsigned*n=list_count(p,v);return n?(int)*n:0;}
static void list_push(Packet*p,const void*v,void*s){unsigned*n=list_count(p,v);if(!n)return;unsigned max=v==&p->tasks?4:v==&p->karma_widget.varList?2:32;if(*n>=max)fail(p,COH_LIMIT);unsigned char*rows;memcpy(&rows,v,sizeof(rows));if(!rows)fail(p,COH_INVALID);memcpy(rows+(*n)++*sizeof(s),&s,sizeof(s));}
static void list_clear(Packet*p,const void*v){unsigned*n=list_count(p,v);if(n)*n=0;}
static void *list_remove(Packet*p,const void*v,unsigned i){unsigned*n=list_count(p,v);if(!n||i>=*n)fail(p,COH_INVALID);unsigned char*rows;void*s;memcpy(&rows,v,sizeof(rows));memcpy(&s,rows+i*sizeof(s),sizeof(s));memmove(rows+i*sizeof(s),rows+(i+1)*sizeof(s),(--*n-i)*sizeof(s));return s;}
static void truncate_text(char*d,const char*s,size_t n){size_t z=strlen(s);if(z>=n)z=n-1;memcpy(d,s,z);d[z]=0;}
static TaskStatus *task_create(Packet*p){if(p->task_alloc>=4)fail(p,COH_LIMIT);return &p->task[p->task_alloc++];}
static char *source_token(Packet*p,char*s){if(s){p->token_cursor=s;p->tokens=0;}else s=p->token_cursor;if(!s)return NULL;while(*s==' ')s++;if(!*s){p->token_cursor=NULL;return NULL;}char*t=s;while(*s&&*s!=' ')s++;if(*s)*s++=0;p->token_cursor=s;if(p->tokens++>=8)fail(p,COH_LIMIT);return t;}
static int source_int(Packet*p,const char*s){char*end;errno=0;long v=strtol(s,&end,10);if(errno||v<INT_MIN||v>INT_MAX)fail(p,COH_INVALID);(void)end;return (int)v;}
static ContactStatus *contact_create(Packet*p){if(p->allocated>=32)fail(p,COH_LIMIT);return &p->row[p->allocated++];}
static void ContactStatusClear(ContactStatus*s){memset(s,0,sizeof(*s));}
static void pktAlignBitsArray(Packet*p){size_t end=(p->reader.cursor+7)&~(size_t)7;if(end>p->reader.bits)fail(p,COH_INVALID);p->reader.cursor=end;}
static void add_map(Packet*p,VisitedStaticMap*m,int db,int map,int fog,int words,U32*data){(void)m;(void)map;(void)fog;if(words!=256)fail(p,COH_INVALID);U32 checksum=0;for(int i=0;i<words;i++)checksum^=data[i];p->report.static_map_checksum^=checksum;p->report.static_map_rows++;p->report.static_map_dbid=(uint32_t)db;p->report.static_map_cells+=8192;p->report.static_map_words+=(uint32_t)words;}
/* Private UI sink: existing widgets avoid presentation allocations. The whole
 * original Karma receiver still reads every flag/count/value. No UI callback
 * publishes or queues outbound input; staging is retired with the workspace. */
static ScriptUIClientWidget *karma_widget(Packet*p,int index){if(index<0||index>=CKR_COUNT+5)fail(p,COH_INVALID);p->karma_widget.varList=p->karma_vars;p->karma_vars[0]=p->karma_vars[1]=p->strings;p->karma_var_count=2;return &p->karma_widget;}
static void *ui_malloc(Packet*p,size_t n){(void)n;fail(p,COH_STATE);return NULL;}
#define scriptUIKarmaWidgetList pak->karma_list
#define ScriptUIClientWidgetFromId(list,i) ((void)(list),karma_widget(pak,i))
#define ScriptUIDestroyWidget(w) ((void)(w))
#define malloc(n) ui_malloc(pak,n)
#define free(s) ((void)(s))
#define eaDestroy(pp) list_clear(pak,(const void*)(pp))
#define _snprintf_s(d,n,truncate,fmt,value) ((void)(truncate),snprintf(d,n,fmt,(int)(value)))
#define winDefs pak->windows
#define game_state pak->game
#define updateTrialStatus(value) (pak->trial_status=(value))
#define sendWindowToServer(loc,i,update) ((void)(loc),(void)(i),(void)(update))
#define WDW_TURNSTILE_DIALOG 0
#define WINDOW_SHRINKING 0
#define DIALOG_OK 0
#define window_setMode(w,m) ((void)(w),(void)(m))
#define dialogStd(a,b,c,d,e,f,g) ((void)(a),(void)(b),(void)(c),(void)(d),(void)(e),(void)(f),(void)(g))
#define MAX_MAPVISIT_CELLS (32*32*8)
#define automap_getMapStruct(db) ((void)(db),&pak->map)
#define automap_clearStaticMaps(m) ((void)(m))
#define automap_addStaticMapCell(m,db,id,fog,n,data) add_map(pak,(m),(db),(id),(fog),(n),(data))
#define TEST_CLIENT 1
#define visitLocations pak->visits
#define storyClues pak->clues
#define keyClues pak->keys
#define MAX_NAME_LEN 128
#define MAX_ZOWIE_NAME 128
#define USE_CACHED 1
#define PI 3.14159265358979323846
#define ICON_MISSION 1
#define SG_LOCATION 200
#define TASK_LOCATIONS -400
#define TASK_SET_LOCATIONS -100
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define strncpyt(d,s,n) truncate_text(d,s,n)
#define TaskStatusListGetOrAdd(id) ((void)(id),pak->tasks=pak->task_rows,&pak->tasks)
#define TaskStatusCreate() task_create(pak)
#define TaskStatusDestroy(s) ((void)(s))
#define TaskProcessZowieGlowFlags(n) ((void)(n))
#define TaskStatusSetDifficulty(a,b,c,d,e) ((void)(a),(void)(b),(void)(c),(void)(d),(void)(e))
#define TaskStatusSetIndex(id) ((void)(id),0)
#define TaskStatusListRemove(id) ((void)(id))
#define TaskStatusSetsSort() ((void)0)
#define updateAutomapZowies(a,b) ((void)0)
#define PlayerGetActiveTask() ((TaskStatus*)0)
#define compass_SetTaskDestination(a,b) ((void)0)
#define clearDestination(a) ((void)0)
#define atlasLoadTexture(s) ((void)(s),(void*)0)
#define strtok(s,delim) ((void)(delim),source_token(pak,s))
#define atoi(s) source_int(pak,s)
#define StoryClueCreate() (&pak->clue)
#define StoryClueDestroy(s) ((void)(s))
#define souvenirCluePrepareUpdate() ((void)0)
#define flashbackListClear() ((void)0)
#define scCreate() (&pak->souvenir)
#define souvinerClueAdd(s) ((void)(s))
#define scReceiveHeader command_original_scReceiveHeader
#define TaskStatusReceive command_original_TaskStatusReceive
#define ALIGNMENT_POINT_MAX_COUNT 5
#define CONTACT_LOCATIONS -200
#define true 1
#define contacts pak->list
#define contactsAccessibleNow pak->accessible
#define contactsDirty pak->dirty
#define timeWhenCanEarnAlignmentPoint pak->times
#define earnedAlignments pak->earned
#define heroAlignmentPoints_self pak->hero
#define vigilanteAlignmentPoints_self pak->vigilante
#define villainAlignmentPoints_self pak->villain
#define rogueAlignmentPoints_self pak->rogue
#define timerServerTime() 0
#define eaCreate(pp) (*(pp)=list_storage(pak,(const void*)(pp)))
#define eaSize(pp) list_size(pak,(const void*)(pp))
#define eaPush(pp,s) list_push(pak,(const void*)(pp),(void*)(s))
#define eaClearEx(pp,fn) ((void)(fn),list_clear(pak,(const void*)(pp)))
#define eaSetSize(pp,n) ((void)(n),list_clear(pak,(const void*)(pp)))
#define eaPop(pp) list_remove(pak,(const void*)(pp),(unsigned)eaSize(pp)-1)
#define eaRemove(pp,i) list_remove(pak,(const void*)(pp),(unsigned)(i))
#define ContactStatusCreate() contact_create(pak)
#define ContactStatusDestroy(s) ((void)(s))
#define strdup(s) duplicate(pak,s)
#define strcpy(d,s) copy_text(pak,d,s,sizeof(d))
#define TaskUpdateDestination(d) ((void)0)
#define assignContactIcon(s) ((void)(s))
#define PNPCFindDef(n) ((void)(n),(void*)0)
#define entities_max 0
#define entities ((Entity**)0)
#define compass_ClearAllMatchingId(i) ((void)(i))
#define pktGetBitsAuto(p) command_auto_line(p,__LINE__)
#define pktGetBitsPack(p,n) command_pack_line(p,n,__LINE__)
#define ContactStatusReceive command_original_ContactStatusReceive
#define ContactStatusListReceive command_original_ContactStatusListReceive
#define receiveStaticMapCells command_original_receiveStaticMapCells
#define ContactStatusAccessibleListReceive command_original_ContactStatusAccessibleListReceive
#define receiveVisitLocations command_original_receiveVisitLocations
#define TaskStatusListReceive command_original_TaskStatusListReceive
#define ClueReceive command_original_ClueReceive
#define ClueListReceive command_original_ClueListReceive
#define KeyClueListReceive command_original_KeyClueListReceive
#define scReceiveAllHeaders command_original_scReceiveAllHeaders
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-variable"
#include "original_command_tail.inc"
#pragma GCC diagnostic pop
static int known_dispatch(U32 command){switch(command){
#define COH_ORIGINAL_COMMAND_DISPATCH
#define COH_COMMAND_DISPATCH(cmd,handler,covered) case cmd:return 1;
#define COH_COMMAND_DISABLED(cmd,handler,covered)
#include "original_command_tail.inc"
#undef COH_COMMAND_DISABLED
#undef COH_COMMAND_DISPATCH
#undef COH_ORIGINAL_COMMAND_DISPATCH
 default:return 0;}}
static void run(Packet *volatile p){if(!setjmp(p->trap)){for(;;){p->report.command_begin_bit=p->reader.cursor;U32 cmd=pktGetBitsPack(p,1);p->report.active_command=cmd;if(!cmd){p->report.terminator=1;p->report.tail_complete=p->reader.cursor==p->reader.bits;if(!p->report.tail_complete)fail(p,COH_UNSUPPORTED);break;}p->report.commands_read++;if(p->report.trace_count<16)p->report.command_ids[p->report.trace_count++]=cmd;else p->report.trace_omitted++;switch(cmd){case SERVER_BEGIN_BYTE_ALIGNED_DATA:receiveByteAlignmentTag(p);p->report.alignment_markers++;break;case SERVER_TASK_VISITLOCATION_UPDATE:receiveVisitLocations(p);break;case SERVER_TASK_STATUS:TaskStatusListReceive(p);break;case SERVER_CLUE_UPDATE:ClueListReceive(p);break;case SERVER_KEYCLUE_UPDATE:KeyClueListReceive(p);break;case SERVER_SOUVENIRCLUE_UPDATE:scReceiveAllHeaders(p);break;case SERVER_ACCESSIBLE_CONTACT_STATUS:ContactStatusAccessibleListReceive(p);break;case SERVER_CONTACT_STATUS:command_original_ContactStatusListReceive(p);p->report.contact_messages++;p->report.contact_rows=p->count;break;case SERVER_GAME_CMDS:p->report.game_markers++;break;case SERVER_SEND_KARMA_STATS:receiveKarmaStats(p);p->report.karma_messages++;break;case SERVER_EVENT_START_STATUS:turnstileGame_HandleEventStartStatus(p);p->report.event_start_messages++;break;case SERVER_INCARNATE_TRIAL_STATUS:receiveIncarnateTrialStatus(p);p->report.trial_status_messages++;break;case SERVER_CHANGE_WINDOW_COLORS:receiveChangeWindowColors(p);p->report.window_color_messages++;break;case SERVER_ALL_STATIC_MAP_CELLS:command_original_receiveStaticMapCells(p);p->report.static_map_messages++;break;default:p->report.unimplemented_handler=known_dispatch(cmd);p->report.unknown_command=!p->report.unimplemented_handler;fail(p,COH_UNSUPPORTED);}}}}
static int span(const void*p,size_t n){return p&&(uintptr_t)p<=UINTPTR_MAX-n;}
static int apart(const void*a,size_t an,const void*b,size_t bn){return(uintptr_t)a+an<=(uintptr_t)b||(uintptr_t)b+bn<=(uintptr_t)a;}
#define ALIGN(T) offsetof(struct{char c;T v;},v)
CohStatus coh_original_command_tail_receive(const CohRepReader*r,CohOriginalCommandTailWorkspace*w,CohOriginalCommandTailReport*out,size_t budget,size_t retained){Packet*state=(Packet*)w;size_t needed=sizeof(*w)+sizeof(*r)+sizeof(*out)+COH_ORIGINAL_COMMAND_STACK_RESERVE;uint32_t unused;if(!budget||budget>COH_ORIGINAL_COMMAND_AGGREGATE_MAX||!span(r,sizeof(*r))||!span(out,sizeof(*out))||!span(w,sizeof(*w))||(uintptr_t)w%ALIGN(CohOriginalCommandTailWorkspace)||(uintptr_t)r%ALIGN(CohRepReader)||(uintptr_t)out%ALIGN(CohOriginalCommandTailReport))return COH_INVALID;if(!span(r->bytes.data,r->bytes.size))return COH_INVALID;if(!apart(w,sizeof(*w),r,sizeof(*r))||!apart(w,sizeof(*w),out,sizeof(*out))||!apart(w,sizeof(*w),r->bytes.data,r->bytes.size))return COH_INVALID;if(!span(r->bytes.data,r->bytes.size)||!apart(r,sizeof(*r),out,sizeof(*out))||!apart(r,sizeof(*r),r->bytes.data,r->bytes.size)||!apart(out,sizeof(*out),r->bytes.data,r->bytes.size))return COH_INVALID;CohRepReader reader=*r;if(coh_rep_read(&reader,0,&unused)!=COH_OK)return COH_INVALID;if(needed>budget||r->bytes.size>budget-needed)return COH_LIMIT;needed+=r->bytes.size;if(retained>budget-needed)return COH_LIMIT;memset(w,0,sizeof(*w));state->reader=*r;state->report.begin_bit=r->cursor;state->report.packet_bits=r->bits;run(state);state->report.end_bit=state->report.failure_bit=state->reader.cursor;*out=state->report;volatile unsigned char*v=(volatile unsigned char*)w;size_t n=sizeof(*w);while(n--)*v++=0;return out->status;}
