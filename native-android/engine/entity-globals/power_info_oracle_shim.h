/* Explicit small fixture entities/earrays and numeric setters. No imported
 * dictionary, gameplay allocator, actual UI or real character is simulated. */
#include "coh_power_info.h"
#include <stddef.h>
typedef float F32;typedef int bool;
#define SERVER 1
#define CLIENT 0
#define TEST_CLIENT 1
#define ACTIVE_STATUS_QUEUED_MASK 2
#define CHAR_INSP_MAX_ROWS 4
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define POWERUPSLOT_COUNT_PACKBITS 1
#define POWERUPSLOT_TYPE_PACKBITS 1
#define POWERUPSLOT_ID_PACKBITS 5
#define LOG_ENT(...) ((void)0)
enum {kTargetType_Any,kTargetType_Location,kTargetType_Teleport,kTargetType_Position};
typedef struct {size_t count;void*items[32];} FixtureArray;
typedef struct {size_t count;int items[32];} FixtureInts;
static int eaSize(const void*v){void*const*a=*(void*const*const*)v;return a?(int)((const FixtureArray*)((const char*)a - offsetof(FixtureArray,items)))->count:0;}
static int eaiSize(const void*v){const int*a=*(const int*const*)v;return a?(int)((const FixtureInts*)((const char*)a - offsetof(FixtureInts,items)))->count:0;}
static void fixture_ea_push(void*v,void*p){void**a=*(void***)v;FixtureArray*f=(FixtureArray*)((char*)a - offsetof(FixtureArray,items));assert(f->count<32);a[f->count++]=p;}
#define eaPush(a,p) fixture_ea_push((a),(void*)(p))
static void eaClearEx(void*v,void(*destroy)(void*)){void**a=*(void***)v;if(!a)return;FixtureArray*f=(FixtureArray*)((char*)a - offsetof(FixtureArray,items));for(size_t i=0;i<f->count;i++)if(a[i]!=(void*)-1&&a[i])destroy(a[i]);f->count=0;}
static void eaiSetSize(void*v,int n){int*a=*(int**)v;assert(n==0);if(a)((FixtureInts*)((char*)a - offsetof(FixtureInts,items)))->count=0;}
typedef struct {U32 buildNum,powerSet,power;} PowerRef;
typedef struct {PowerRef ppowRef;float rechargeCountdown;} PowerRechargeTimer;
typedef struct {int type;const char*name;} Reward;
typedef struct {Reward reward;int filled;} PowerupSlot;
typedef struct BasePower {U32 crcFullName;int eTargetType,eTargetTypeSecondary;} BasePower;
typedef struct {const BasePower*ppowBase;int iLevel,iNumCombines;float afVars[4];PowerupSlot aPowerupSlots[10];} Boost;
typedef struct PowerSet PowerSet;
typedef struct {float fRechargeTime;} Attributes;
typedef struct Power {
    const BasePower *ppowOriginal,*ppowBase;PowerSet*psetParent;
    int iLevelBought,iNumCharges;float fRangeLast,fUsageTime,fAvailableTime,fTimer;
    U32 ulCreationTime,bEnabled,bDisabledManually,iUniqueID,bActive;
    Boost **ppBoosts,**ppGlobalBoosts;Attributes*pattrStrength;
} Power;
struct PowerSet {int iLevelBought;Power**ppPowers;};
typedef struct Character {int iCurBuild;PowerSet**ppPowerSets;Power*ppowDefault,*ppowQueued,*ppowTried;const BasePower*aInspirations[5][4];Boost*aBoosts[70];}Character;
typedef struct Entity {Character*pchar;PowerRef**activeStatusChange,**enabledStatusChange,**usageStatusChange,**rechargeStatusChange,**powerDefChange;int*inspirationStatusChange,*boostStatusChange;}Entity;
static PowerRef fixture_refs[32];static unsigned fixture_refs_used;
static PowerRef*powerRef_CreateFromIdxs(int b,int s,int p){assert(fixture_refs_used<32);PowerRef*r=&fixture_refs[fixture_refs_used++];*r=(PowerRef){(U32)b,(U32)s,(U32)p};return r;}
static void powerRef_Destroy(PowerRef*p){(void)p;}
static Power*SafeGetPowerByIdx(Character*c,int b,int s,int p){if(b!=c->iCurBuild||s<0||s>=eaSize(&c->ppPowerSets)||p<0||p>=eaSize(&c->ppPowerSets[s]->ppPowers))return NULL;return c->ppPowerSets[s]->ppPowers[p];}
static int powerupslot_ValidCount(PowerupSlot*s,int n){int i=0;while(i<n&&s[i].reward.name)i++;return i;}
static int rewarditemtype_IdFromName(int t,const char*n){(void)t;return atoi(n);}
static float character_PowerRange(Character*c,Power*p){(void)c;(void)p;return 37.5f;}
static float character_PowerRange2(Character*c,Power*p){(void)c;(void)p;return -3.25f;}
static void pktSendIfSetBitsPack(Packet*p,int n,U32 v){pktSendBits(p,1,v!=0);if(v)pktSendBitsPack(p,n,v);}
