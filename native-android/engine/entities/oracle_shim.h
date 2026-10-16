/* Fixture-only engine adapter. These are deterministic synthetic entities,
 * never credentials, imported characters, or packets captured from a server. */
#include <math.h>
typedef float F32;typedef float Quat[4];
#define PI 3.14159265358979323846
#define HALFPI 1.57079632679489661923
#define quatX(q) ((q)[0])
#define quatY(q) ((q)[1])
#define quatZ(q) ((q)[2])
#define quatW(q) ((q)[3])
#define SQR(x) ((x)*(x))
#define fsqrt sqrtf
#define scaleVec4(q,s,o) do{for(int qi=0;qi<4;qi++)(o)[qi]=(q)[qi]*(s);}while(0)
#define INLINEDBG
#define START_BIT_COUNT(...)
#define STOP_BIT_COUNT(...)
#define PERFINFO_RUN(...)
#define STATIC_INFUNC_ASSERT(...)
#define ENTTYPE(e) ((e)->type)
#define ENTTYPE_PLAYER 2
#define ENTTYPE_CRITTER 4
#define PKT_BITS_TO_REP_SVR_IDX 12
#define PKT_BITS_TO_REP_DB_ID 22
#define kPlayerType_Count 2
#define kPlayerSubType_Count 4
#define kPraetorianProgress_Count 8
#define NULLPOWER ((void*)0)
typedef struct Entity Entity;
typedef struct {U32 crcFullName;} BasePower;
typedef struct {Entity *erSource;float fMagnitude;} AttribMod;
typedef struct {int pclass,porigin,playerTypeByLocation;BasePower *ppowCreatedMe;
 Entity *entParent,*erAssist,*erTargetInstantaneous;AttribMod *pmodTaunt,**ppmodPlacates;
 int inventory_total[5],inventory_used[5],auction_total,boost_total;
} Character;
typedef struct {int pendingCostumeForceTime,current_costume,num_costume_slots,num_costumes_stored,supergroup_mode,hide_supergroup_emblem,npc_costume;void *costume[16];char costumeFxSpecial[128];int isBeingCritter,playerType,playerSubType,praetorianProgress,titleThe,titleColors[2],titleBadge;char *titleTheText,*titleCommon,*titleOrigin,*titleSpecial,*chat_handle;} Player;
typedef struct {char *fileName,*name,*displayClassName;} Villain;
typedef struct {char *name;} PNPCDef;
typedef struct {PNPCDef *pnpcdef;int contact;} PNPCInfo;
typedef struct {int y_used,xz_used,offsets[3];} InterpPosition;
typedef struct {int idx,ticksToDelay,triggerFxNetId;float timeCreated;} TriggeredMove;
struct Entity {
 int type,id,owner,db_id,access_level,commandablePet,petDismissable,specialPowerState,
     fade,randSeed,villainRank,idDetail,dontOverrideName,clear_target,
 npcIndex,costumeIndex,send_all_costume,supergroup_id;
 NetFx *netfx_list;int netfx_count,netfx_effective;
 void *ownedCostume,*customNPC_costume;char *costumeWorldGroup;
 struct {struct {char *name;} *type;} *seq;
 Character *pchar;Player *pl;Entity *erOwner,*erCreator;
 Villain *villainDef;PNPCInfo *persistentNPCInfo;
 char *specialPowerDisplayName,*petName,*name,*favoriteWeaponAnimList;
 U32 net_iqrot[3],pkt_id_qrot[3];Quat net_qrot,old_net_qrot;
 int net_ipos[3],pos_shift,move_instantly,firstRagdollFrame;InterpPosition interp_positions[7];
 float net_pos[3],old_net_pos[3];struct {int generic_end;} pos_history;
 struct {int mode;} state;int set_triggered_moves,triggered_move_count,aiAnimListUpdated;
 TriggeredMove triggered_moves[16];float lastTimeEntSent;char *aiAnimList;
};
static int g_CharacterClasses,g_CharacterOrigins,g_VillainClasses,g_VillainOrigins;
static struct {int clickToSource,netfxdebug;} server_state;
static int classes_GetIndexFromPtr(int *unused,int v){(void)unused;return v;}
static int origins_GetIndexFromPtr(int *unused,int v){(void)unused;return v;}
static Entity *erGetEnt(Entity *e){return e;}
static int isPetDisplayed(Entity *e){(void)e;return 1;}
static char *localizedPrintf(Entity *e,char *s){(void)e;return s;}
static char *villainGroupNameFromEnt(Entity *e){(void)e;return "FixtureGroup";}
static int villainRankConningAdjustment(int rank){return rank;}
#define AT_NO_APPEARANCE 0
#define AT_ENTIRE_COSTUME 1
#define AT_OWNED_COSTUME 2
#define AT_NPC_COSTUME 3
#define AT_SEQ_NAME 4
#define ENTTYPE_HERO 3
#define ENTTYPE_MISSION_ITEM 6
#define CONFUSED_COSTUMES 0
#define MAX_COSTUMES 16
#define kInventoryType_Count 5
#define INV_COUNT_PACKBITS 8
#define verify(x) assert(x)
static int fixture_placates;
static int eaSize(void *p){(void)p;return fixture_placates;}
static int OnArenaMap(void){return 0;}
static int timerSecondsSince2000(void){return 0;}
static void ent_SendCostumeRewards(Packet *p,Entity *e){(void)p;(void)e;assert(0);}
static void costume_send(Packet *p,void *c,int x){(void)p;(void)c;(void)x;assert(0);}
static void NPCcostume_send(Packet *p,void *c){(void)p;(void)c;assert(0);}
static void *costume_makeSupergroup(Entity *e){(void)e;assert(0);return NULL;}
static void *costume_current(Entity *e){(void)e;assert(0);return NULL;}
static int character_GetInvSize(Character *c,int type){return c->inventory_used[type];}
static int character_GetInvTotalSize(Character *c,int type){return c->inventory_total[type];}
static int character_GetAuctionInvTotalSize(Character *c){return c->auction_total;}
static int character_GetBoostInvTotalSize(Character *c){return c->boost_total;}


#define POS_BITS 24
#define TOTAL_ENT_MODES 3
#define MAX_PACKETDELAY_COMPENSATION 15
#define MINMAX(v,l,h) ((v)<(l)?(l):((v)>(h)?(h):(v)))
#define BIT_RANGE(l,h) (((1u<<((h)+1))-1)&~((1u<<(l))-1))
#define vecXidx 0
#define vecYidx 1
#define vecZidx 2
static struct {int interp_level,interp_bits;} send_ent;
static const int binpos_level[]={0,1,1,2,2,2,2},binpos_parent[]={0,0,0,1,1,2,2};
static void entSetGenericInterpPositions(Packet *p,Entity *e,InterpPosition *ip,int *y,int *xz,float *a,float *b,float *c,float *d){(void)p;(void)e;(void)ip;(void)y;(void)xz;(void)a;(void)b;(void)c;(void)d;assert(0);}
#define MAX_DELETES 10240
#define TSTB(a,i) ((a)[(i)/32]&(1u<<((i)%32)))
#define CLRB(a,i) ((a)[(i)/32]&=~(1u<<((i)%32)))
typedef struct {U32 sent_ids[320];} EntNetLink;
static int ent_delete_count,ent_deletes[MAX_DELETES],ent_delete_ids[MAX_DELETES],entities_max;
static Entity *entities[10240];

#define assertmsg(x,m) assert(x)
#define ABSTIME_SECOND 3000
#define SELECTED_ENT ((Entity*)0)
static int demo_recording;
static struct {int netfxdebug;} game_state;
static void setNetFxParams(Entity *e){(void)e;assert(0);}
static int entSendGetInterpStoreEntityId(void){return 0;}
static void debugShowNetfx(Entity *e,NetFx *fx){(void)e;(void)fx;assert(0);}
static NetFx *entrecvAllocNetFx(Entity *e){assert(e->netfx_count<32);return &e->netfx_list[e->netfx_count++];}
static const char *textStd(const char *s){return s;}
static void Errorf(const char *s){(void)s;assert(0);}
static void demoSetAbsTimeOffset(float f){(void)f;assert(0);}
static void demoRecordFx(NetFx *fx){(void)fx;assert(0);}
