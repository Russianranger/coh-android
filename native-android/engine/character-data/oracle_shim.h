/* Owner/dictionary storage for original-function fixtures; never real assets. */
typedef float F32;typedef struct Character Character;typedef struct BasePower BasePower;
#define SERVER 1
#define CLIENT 0
#define TEST_CLIENT 1
#define MAX_BUILD_NUM 8
#define CHAR_BOOST_MAX 70
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define TYPE_ARRAY_SIZE(t,a) (sizeof(((t*)0)->a)/sizeof(((t*)0)->a[0]))
#define CopyStructs(d,s,n) memcpy((d),(s),(n)*sizeof(*(d)))
#define verify(x) (x)
#define EAINRANGE(i,a) ((i)>=0&&(i)<eaSize(&(a)))
#define ENTTYPE(e) ((e)->type)
#define ENTTYPE_PLAYER 2
#define LOG_ENT(...) ((void)0)
#define POWERUPSLOT_COUNT_PACKBITS 1
#define POWERUPSLOT_TYPE_PACKBITS 1
#define POWERUPSLOT_ID_PACKBITS 5
#define INV_COUNT_PACKBITS 8
#define GENERICINV_TYPE_PACKBITS 5
#define GENERICINV_ID_PACKBITS 5
#define GENERICINV_IDX_PACKBITS 5
#define GENERICINV_AMOUNT_PACKBITS 5
typedef enum {kInventoryType_Salvage,kInventoryType_Concept,kInventoryType_Recipe,kInventoryType_BaseDetail,kInventoryType_StoredSalvage,kInventoryType_Count}InventoryType;
typedef struct Entity {int type;Character*pchar;}Entity;
typedef struct {size_t count;void*items[16];}FixtureArray;
static int eaSize(const void *v){
 const void *const*array=*(const void *const*const*)v;
 return array?(int)((const FixtureArray*)((const char*)array - offsetof(FixtureArray,items)))->count:0;
}
typedef struct{int type;const char*name;}Reward;
typedef struct{Reward reward;int filled;}PowerupSlot;
struct BasePower{U32 crcFullName;};
typedef struct{const BasePower**ppPowers;}BasePowerSet;
typedef struct{const BasePower*ppowBase;int iLevel,iNumCombines;float afVars[4];PowerupSlot aPowerupSlots[10];}Boost;
typedef struct{const BasePower*ppowOriginal;int iLevelBought,iNumCharges;float fRangeLast,fUsageTime,fAvailableTime;U32 ulCreationTime,bEnabled,bDisabledManually,iUniqueID;Boost**ppBoosts,**ppGlobalBoosts;}Power;
typedef struct{int iLevelBought;Power**ppPowers;BasePowerSet*psetBase;}PowerSet;
typedef struct{const char*pchName;}Named;
typedef struct{int id;}ConceptDef;
typedef struct{ConceptDef*def;float afVars[4];}ConceptItem;
typedef struct{ConceptItem*concept;}ConceptInventory;
typedef struct{U32 id,amount;float variables[4];}InventoryFixture;
struct Character{
 Entity*entParent;Named*pclass,*porigin;int iLevel,iCombatModShiftToSendToClient,iCurBuild,playerTypeByLocation,iActiveBuild;
 int iBuildLevels[8];PowerSet**ppPowerSets,**ppBuildPowerSets[8];
 int iNumInspirationCols,iNumInspirationRows;const BasePower*aInspirations[5][4];Boost*aBoosts[70];
 ConceptInventory**conceptInv;InventoryFixture inventory[5][2];int inventory_size[5],inventory_total[5];int auctionInvTotalSlots;
};
typedef struct{int unused;}PowerDictionary;
static PowerDictionary g_PowerDictionary;
static int g_numSharedPowersets;
static BasePower powers_by_crc[8];static CohCharacterData observed;
static int character_GetActiveBuild(Entity*e){return e->pchar->iActiveBuild;}
static void character_SelectBuildLightweight(Entity*e,int b){e->pchar->iCurBuild=b;e->pchar->ppPowerSets=e->pchar->ppBuildPowerSets[b];}
static int powerupslot_ValidCount(PowerupSlot*s,int n){int i=0;while(i<n&&s[i].reward.name)i++;return i;}
static int rewarditemtype_IdFromName(int type,const char*name){(void)type;return atoi(name);}
static const char *rewarditemtype_NameFromId(int type,int id){(void)type;static char values[10][20];static unsigned at;char*p=values[(at++)%10];snprintf(p,20,"%d",id);return p;}
static const BasePower *powerdict_GetBasePowerByCRC(const PowerDictionary*d,U32 crc){(void)d;for(unsigned i=0;i<8;i++)if(powers_by_crc[i].crcFullName==crc)return &powers_by_crc[i];assert(0);return NULL;}
static int character_GetInvSize(Character*p,int t){return p->inventory_size[t];}
static int character_GetInvTotalSize(Character*p,int t){return p->inventory_total[t];}
static int character_GetAuctionInvTotalSize(Character*p){return p->auctionInvTotalSlots;}
static void character_GetInvInfo(Character*p,int*id,int*amount,void*unused,int t,int i){(void)unused;*id=(int)p->inventory[t][i].id;*amount=(int)p->inventory[t][i].amount;}
static void character_SetInspiration(Character*p,const BasePower*b,int x,int y){(void)p;observed.inspirations[x][y]=b->crcFullName;}
static void character_RemoveInspiration(Character*p,int x,int y,void*unused){(void)p;(void)unused;observed.inspirations[x][y]=0;}
static void character_DestroyBoost(Character*p,int i,void*unused){(void)p;(void)unused;memset(&observed.boosts[i],0,sizeof(observed.boosts[i]));}
static void character_SetBoost(Character*p,int i,const BasePower*b,int level,int combines,const float*vars,int n,const PowerupSlot*slots,int count){
 (void)p;assert(n==4&&count<=10);CohCharacterBoost*out=&observed.boosts[i];out->present=1;out->power_crc=b->crcFullName;out->level=(U32)level;out->combines=(U32)combines;memcpy(out->variables,vars,16);out->powerup_count=(U32)count;
 for(int k=0;k<count;k++){out->powerups[k].type=(U32)slots[k].reward.type;out->powerups[k].id=(U32)atoi(slots[k].reward.name);out->powerups[k].filled=(U32)slots[k].filled;}
}
static void character_ClearInventory(Character*p,int t,const char*why){(void)p;(void)why;observed.inventories[t].first=observed.inventory_count;observed.inventories[t].count=0;}
static void character_SetInvTotalSize(Character*p,int t,int total){(void)p;observed.inventories[t].total=(U32)total;}
static void character_SetInventory(Character*p,int t,int id,int index,int amount,const char*why){
 (void)p;(void)why;CohCharacterInventoryItem*i=&observed.items[observed.inventory_count++];i->type=(U32)t;i->id=(U32)id;i->index=(U32)index;i->amount=(U32)amount;observed.inventories[t].count++;
}
static void character_SetConcept(Character*p,int id,float*vars,int index,int amount){character_SetInventory(p,1,id,index,amount,"");memcpy(observed.items[observed.inventory_count-1].variables,vars,16);}
static int pktEnd(Packet*p){return bsGetCursorBitPosition(&p->stream)>=p->stream.bitLength;}
