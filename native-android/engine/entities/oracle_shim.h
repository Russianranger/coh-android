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
typedef struct {int pclass,porigin,playerTypeByLocation;void *ppowCreatedMe;} Character;
typedef struct {int isBeingCritter,playerType,playerSubType,praetorianProgress,titleThe,titleColors[2],titleBadge;char *titleTheText,*titleCommon,*titleOrigin,*titleSpecial,*chat_handle;} Player;
typedef struct {char *fileName,*name,*displayClassName;} Villain;
typedef struct {char *name;} PNPCDef;
typedef struct {PNPCDef *pnpcdef;int contact;} PNPCInfo;
typedef struct {int y_used,xz_used,offsets[3];} InterpPosition;
typedef struct {int idx,ticksToDelay,triggerFxNetId;float timeCreated;} TriggeredMove;
typedef struct Entity Entity;
struct Entity {
 int type,id,owner,db_id,access_level,commandablePet,petDismissable,specialPowerState,
     fade,randSeed,villainRank,idDetail,dontOverrideName;
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
static struct {int clickToSource;} server_state;
static int classes_GetIndexFromPtr(int *unused,int v){(void)unused;return v;}
static int origins_GetIndexFromPtr(int *unused,int v){(void)unused;return v;}
static Entity *erGetEnt(Entity *e){return e;}
static int isPetDisplayed(Entity *e){(void)e;return 1;}
static char *localizedPrintf(Entity *e,char *s){(void)e;return s;}
static char *villainGroupNameFromEnt(Entity *e){(void)e;return "FixtureGroup";}
static int villainRankConningAdjustment(int rank){return rank;}
static void basepower_Send(Packet *pak,void *v){(void)v;pktSendBits(pak,32,0xface);}

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
