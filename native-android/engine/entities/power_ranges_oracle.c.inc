/* Synthetic fixture state only. Full source range producer/consumer follow. */
#include <stdbool.h>
#define CLIENT 0
#define LOG_ENT(...) ((void)0)
enum {kTargetType_Location=1,kTargetType_Teleport=2,kTargetType_Position=3};
typedef struct {U32 crcFullName;int eTargetType,eTargetTypeSecondary;} BasePower;
typedef struct {int unused;} PowerDictionary;
typedef struct Entity Entity;
typedef struct {BasePower *ppowBase,*ppowOriginal;float fRangeLast,range1,range2;} Power;
typedef struct {Power **ppPowers;} PowerSet;
typedef struct {PowerSet **ppPowerSets;Entity *entParent;} Character;
struct Entity {Character*pchar;void **activeStatusChange,**enabledStatusChange,**usageStatusChange,**rechargeStatusChange;int *inspirationStatusChange,*boostStatusChange;void **powerDefChange;};
static BasePower fixture_bases[1026];static Power fixture_powers[4][1026];
static Power*fixture_power_ptrs[4][1026];static PowerSet fixture_sets[4],*fixture_set_ptrs[4];
static int fixture_set_count,fixture_power_counts[4];
static PowerDictionary g_PowerDictionary;
static U32 fixture_last_crc,fixture_observation[4096],fixture_observed;
static int fixture_array_count(void*p) {
 if(p==fixture_set_ptrs)return fixture_set_count;
 for(int i=0;i<4;i++)if(p==fixture_power_ptrs[i])return fixture_power_counts[i];
 assert(!p);return 0;
}
#define eaSize(p) fixture_array_count((void*)*(p))
#define eaiSize(p) fixture_array_count((void*)*(p))
static float character_PowerRange(Character*p,Power*w){(void)p;return w->range1;}
static float character_PowerRange2(Character*p,Power*w){(void)p;return w->range2;}
static const BasePower*powerdict_GetBasePowerByCRC(const PowerDictionary*d,int crc) {
 (void)d;fixture_last_crc=(U32)crc;
 if(!crc)return NULL;
 for(int i=0;i<1026;i++)if(fixture_bases[i].crcFullName==(U32)crc)return &fixture_bases[i];
 return NULL;
}
static Power*character_OwnsPower(Character*p,const BasePower*b) {
 for(int i=0;i<fixture_set_count;i++)for(int j=0;j<fixture_power_counts[i];j++)
  if(p->ppPowerSets[i]->ppPowers[j]&&p->ppPowerSets[i]->ppPowers[j]->ppowOriginal==b)return p->ppPowerSets[i]->ppPowers[j];
 return NULL;
}
static float pktGetF32(Packet*p) {
 float value=bsReadF32(&p->stream);U32 word;memcpy(&word,&value,4);
 assert(fixture_observed+2<4096);fixture_observation[fixture_observed++]=fixture_last_crc;
 fixture_observation[fixture_observed++]=word;return value;
}
