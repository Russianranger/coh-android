/* Synthetic owned source objects, deterministic lookup/clock/UI shells.
 * Full sender/receiver function bodies below this include are unchanged.
 * No source dictionary, account, scene or entity authority is asserted. */
#include <math.h>
#include "tail_observation.h"
typedef int bool;typedef float F32;typedef char MemberName[64];
#define FALSE 0
#define TRUE 1
#define INLINEDBG
#define MAX_NAME_LEN 128
#define MAX_ZOWIE_NAME 128
#define MAX_ZOWIE_TYPE 8
#define MAX_LEVELINGPACT_MEMBERS 2
#define MAX_PATH 260
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define ENTTYPE_PLAYER 2
#define ENTTYPE(e) ((e)->type)
#define COUNT(x) ((void)(x))
#define PI 3.14159265358979323846
#define SG_LOCATION 101
#define TASK_LOCATIONS 102
#define TASK_SET_LOCATIONS 103
#define ICON_MISSION 104
#define CONTACTDEST_EXPLICITTASK 4
#define LOG(...) ((void)0)
#define LOG_ERROR 0
#define LOG_LEVEL_IMPORTANT 0
#define TEST_CLIENT 1
#define SAFE_FREE(p) do {free(p);(p)=NULL;} while(0)
static void strncpyt(char *dst,const char *src,size_t size){assert(size);size_t n=strlen(src);if(n>=size)n=size-1;memcpy(dst,src,n);dst[n]=0;}
static void strcat_s(char *dst,size_t size,const char *src){assert(strlen(dst)+strlen(src)<size);strcat(dst,src);}
typedef struct {size_t count;void *items[300];} TailArray;
static TailArray *array_owner(void *const *p){return p?(TailArray*)((char*)p-offsetof(TailArray,items)):NULL;}
#define eaSize(pp) ((*(pp))?(int)array_owner((void *const*)*(pp))->count:0)
static void array_push(void ***p,void *value){if(!*p){TailArray *a=calloc(1,sizeof(*a));assert(a);*p=a->items;}TailArray *a=array_owner(*p);assert(a->count<300);a->items[a->count++]=value;}
#define eaPush(pp,v) array_push((void***)(pp),(void*)(v))
static void array_clear(void ***p,void (*destroy)(void*)){if(*p){TailArray *a=array_owner(*p);for(size_t i=0;i<a->count;i++)if(destroy)destroy(a->items[i]);a->count=0;}}
#define eaClearEx(pp,d) array_clear((void***)(pp),d)
static void array_destroy(void ***p){if(*p){free(array_owner(*p));*p=NULL;}}
#define eaDestroy(pp) array_destroy((void***)(pp))
#define EAINRANGE(i,p) ((i)>=0&&(i)<eaSize(&(p)))
typedef struct {int levelAdjust,teamSize,dontReduceBoss,alwaysAV;} StoryDifficulty;
typedef struct {int context,subhandle;} StoryHandle;
typedef struct {int type,iconBInCompass,dbid,context,subhandle,contactType,id;void *icon,*iconB;float angle,world_location[4][3];char mapName[512],name[256];} Destination;
typedef struct TaskStatus {
    int ownerDbid,context,subhandle,level,alliance;StoryDifficulty difficulty;
    char description[256],owner[MAX_NAME_LEN+1],state[256],detail[1024],filename[256];
    unsigned isComplete,isMission,hasRunningMission,isSGMission,hasLocation,detailInvalid,zoneTransfer,teleportOnComplete,enforceTimeLimit,isAbandonable,isZowie;
    Destination location;U32 timeout,timezero,timerType,failOnTimeout,zinfo,zseed,zmap_id;
    char ztype[MAX_ZOWIE_NAME],zname[MAX_ZOWIE_NAME];int zpoolSize[MAX_ZOWIE_TYPE];
} TaskStatus;
typedef struct {const char *logicalname,*inprogress_description,*filename,*taskLocationMap,*villainMap,*zowieType,*zowieDisplayName,*zowiePoolSize;int sg,force;} TaskDef;
typedef struct {TaskDef *def;StoryHandle sahandle;StoryDifficulty difficulty;int level,alliance;U32 timeout,timezero,timerType,failOnTimeout,completeSideObjectives,seed;int complete,mission,running,zone,teleport,abandon,zowie,location;const char *status;} StoryTaskInfo;
typedef struct {float coord[3];int type,mapID;} StoryLocation;
typedef struct {int unused;} ScriptVarsTable;
typedef struct {int unused;} ContactDef;
typedef struct {const char *reward;int val,timer;} RewardToken;
typedef struct {const char *pchName;} DetailRecipe;
typedef struct {const char *pchName;} Detail;
typedef struct {const DetailRecipe *recipe;int count;} RecipeInvItem;
typedef struct {const Detail *pDetail;U32 creation_time,expiration_time,iFlags;int bValid;} SpecialDetail;
typedef struct {int count,*ids,*onMapserver,*mapIds;MemberName *names;} TeamMembers;
typedef struct {TeamMembers members;int count;} Levelingpact;
typedef struct {char name[64],emblem[128];U32 colors[2];int spacesForItemsOfPower;StoryTaskInfo *activetask;TaskStatus *sgMission;RewardToken **rewardTokens;RecipeInvItem **invRecipes;SpecialDetail **specialDetails;} Supergroup;
typedef struct Entity {int type,db_id,supergroup_id,levelingpact_id,logout_bad_connection;float logout_timer;char name[MAX_NAME_LEN],supergroup_name[64],supergroup_emblem[128];U32 supergroup_color[2],pkt_id_supergroup,pkt_id_logout;void *pchar;Supergroup *supergroup;Levelingpact *levelingpact;struct {int map_id;} *teamup;} Entity;
static struct {int clickToSource;} server_state;
static struct {int is_endgame_raid,local_server;} db_state;
static StoryLocation fixture_location;
static Destination waypointDest;
static DetailRecipe fixture_recipes[]={{"RecipeA"},{"RecipeB"},{"UnknownRecipe"}};
static Detail fixture_details[]={{"DetailA"},{"DetailB"},{"UnknownDetail"}};
static int costume_HashTable;
static Entity fixture_local_member;
#define TASK_IS_SGMISSION(d) ((d)->sg)
#define TASK_FORCE_TIMELIMIT(d) ((d)->force)
#define saBuildScriptVarsTable(...) ((void)0)
static int ContactGetHandleFromDefinition(const ContactDef *d){(void)d;return 1;}
static const ContactDef *ContactDefinition(int n){static ContactDef c;(void)n;return &c;}
static const char *saUtilTableAndEntityLocalize(const char *s,ScriptVarsTable *v,Entity *e){(void)v;(void)e;return s;}
static const char *saUtilDirtyFileName(const char *s){return s;}
static void ContactTaskConstructStatus(char *dst,Entity *e,StoryTaskInfo *t,const ContactDef *d){(void)e;(void)d;strcpy(dst,t->status);}
static int storyTaskInfoGetAlliance(StoryTaskInfo *t){return t->alliance;}
static int TaskCompleted(StoryTaskInfo *t){return t->complete;}
static int fixture_mission;
static int TaskContainsMission(StoryHandle *h){(void)h;return fixture_mission;}
static int TaskIsRunningMission(Entity *e,StoryTaskInfo *t){(void)e;return t->running;}
static int TaskIsZoneTransfer(StoryTaskInfo *t){return t->zone;}
static int TaskCanTeleportOnComplete(StoryTaskInfo *t){return t->teleport;}
static int TaskCanBeAbandoned(Entity *e,StoryTaskInfo *t){(void)e;return t->abandon;}
static int TaskIsZowie(StoryTaskInfo *t){return t->zowie;}
static StoryLocation *ContactTaskGetLocations(Entity *e,StoryTaskInfo *t,int *n){(void)e;*n=t->location;return &fixture_location;}
static const char *saUtilCurrentMapFile(void){return "maps/local_fixture.txt";}
static const char *dbGetMapName(int n){assert(n==7);return "maps/fixture.txt";}
static int dbGetMapId(const char *n){assert(!strcmp(n,"fixture.txt"));return 123;}
static void saUtilFilePrefix(char *dst,const char *s){(void)s;strcpy(dst,"fixture");}
static void *atlasLoadTexture(const char *s){(void)s;return NULL;}
static void compass_ClearAllMatchingId(int n){(void)n;}
static void compass_SetTaskDestination(Destination *d,TaskStatus *t){(void)d;(void)t;}
static TaskStatus *TaskStatusCreate(void){TaskStatus *p=calloc(1,sizeof(*p));assert(p);return p;}
static void TaskStatusDestroy(TaskStatus *p){free(p);}
static Supergroup *createSupergroup(void){Supergroup *p=calloc(1,sizeof(*p));assert(p);return p;}
static int stashFindElementConst(int table,const char *name,void *unused){(void)table;(void)unused;return !strcmp(name,"KnownEmblem");}
static int rewardtoken_IdxFromName(RewardToken ***p,const char *name){for(int i=0;i<eaSize(p);i++)if(!strcmp((*p)[i]->reward,name))return i;return -1;}
static int rewardtoken_Award(RewardToken ***p,const char *name,int id){(void)id;if(!*name)return -1;RewardToken *r=calloc(1,sizeof(*r));assert(r);char *copy=malloc(strlen(name)+1);assert(copy);strcpy(copy,name);r->reward=copy;eaPush(p,r);return eaSize(p)-1;}
static const DetailRecipe *detailrecipedict_RecipeFromName(const char *name){for(unsigned i=0;i<2;i++)if(!strcmp(name,fixture_recipes[i].pchName))return &fixture_recipes[i];return NULL;}
static void sgrp_SetRecipeNoLock(Supergroup *s,const DetailRecipe *r,int count,int unlimited){(void)unlimited;for(int i=0;i<eaSize(&s->invRecipes);i++)if(s->invRecipes[i]->recipe==r){s->invRecipes[i]->count=count;return;}RecipeInvItem *v=calloc(1,sizeof(*v));assert(v);v->recipe=r;v->count=count;eaPush(&s->invRecipes,v);}
static void DestroyRecipeInvItemAdapter(void *p){free(p);}
static const Detail *basedata_GetDetailByName(const char *name){for(unsigned i=0;i<2;i++)if(!strcmp(name,fixture_details[i].pchName))return &fixture_details[i];return NULL;}
static void levelingpactListUiUpdate(void){}
static Levelingpact *createLevelingpact(void){Levelingpact *p=calloc(1,sizeof(*p));assert(p);return p;}
static void destroyLevelingpact(Levelingpact *p){free(p->members.ids);free(p->members.onMapserver);free(p->members.names);free(p->members.mapIds);free(p);}
static Entity *entFromDbId(int id){return id==777?&fixture_local_member:NULL;}
