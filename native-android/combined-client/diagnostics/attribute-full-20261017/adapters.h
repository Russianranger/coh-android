#define bool int
#define CLIENT 0
#include <stddef.h>
#define ENTTYPE(e) ((e)->type)
#define LOG_ENT(...) assert(!"missing fixture power")
#define AINRANGE(i,a) ((unsigned)(i)<ARRAY_SIZE(a))
static int auto_bins[]={2,10,24,32},g_bAssertOnBitStreamError;
typedef struct{unsigned crcFullName;}BasePower;
typedef struct{int unused;}PowerDictionary;static PowerDictionary g_PowerDictionary;
typedef struct AttribContributer AttribContributer;
typedef struct{F32 fVal;int buffOrDebuff,key;AttribContributer*ppContributers[32];unsigned contributors;}AttribDescription;
typedef struct{AttribDescription**ppAttrib;unsigned count;}AttribCategory;
static struct{AttribCategory**ppCategories;}g_AttribCategoryList;
typedef struct{F32 fDelay;int key;BasePower*ppowBase;}AttribModTemplate;
typedef struct{AttribModTemplate*ptemplate;F32 fTimer,fChance,fMagnitude;int bSuppressedByStacking;unsigned erSource;}AttribMod;
typedef struct{AttribMod*mods;unsigned count;}AttribModList;
typedef struct{AttribModList*list;unsigned index;}AttribModListIter;
typedef struct{AttribModList listMod;}Character;
typedef struct{WdwBase*winLocs;struct{int iKey;}combatMonitorStats[MAX_COMBAT_STATS];}AttribPlayer;
typedef struct Entity{AttribPlayer*pl;int newAttribTarget;unsigned attributesTarget,owner;Character*pchar;int type,id,npcIndex;const char*name;}Entity;
static Entity*g_pAttribTarget,*fixture_player,*fixture_target;static Entity sources[4];
static struct{int enablePowerDiminishing;}server_state;
static struct{struct{const char*displayName;}*npcDefs[1];}npcDefList;
static AttribDescription descriptions[69];static AttribDescription*attrrows[7][69];static AttribCategory cats[7],*catptrs[7];static BasePower powers[4];
static unsigned scenario,window_calls;
static Entity*erGetEnt(unsigned id){if(id==99)return fixture_target;if(id==1)return scenario%3?fixture_target:fixture_player;if(id>=2&&id<=4)return sources+id-1;return NULL;}
static Entity*validEntFromId(unsigned id){assert(fixture_target&&fixture_target->owner==id);return fixture_target;}
static int eaSize(void*p){
 if(p==&g_AttribCategoryList.ppCategories)return 7;
 for(unsigned i=0;i<7;i++)if(p==&cats[i].ppAttrib)return cats[i].count;
 assert(!"unsupported array identity");return 0;
}
static void eaClearEx(void*p,void*f){(void)f;for(unsigned i=0;i<69;i++)if(p==&descriptions[i].ppContributers){descriptions[i].contributors=0;return;}assert(0);}
static void eaPush(void*p,void*v){for(unsigned i=0;i<69;i++)if(p==&descriptions[i].ppContributers){assert(descriptions[i].contributors<32);descriptions[i].ppContributers[descriptions[i].contributors++]=v;return;}assert(0);}
static AttribDescription*attribDescriptionGet(int key){for(unsigned i=0;i<69;i++)if(descriptions[i].key==key)return descriptions+i;return NULL;}
static F32 attrib_GetVal(Character*c,AttribDescription*d,unsigned*buff){(void)c;*buff=(d->key+scenario)&3;return ((F32)d->key-(F32)scenario)/16.f;}
static AttribMod*modlist_GetFirstMod(AttribModListIter*i,AttribModList*l){i->list=l;i->index=0;return l->count?l->mods:NULL;}
static AttribMod*modlist_GetNextMod(AttribModListIter*i){i->index++;return i->index<i->list->count?i->list->mods+i->index:NULL;}
static int modGetBuffHash(const AttribModTemplate*t){return t->key;}
static const BasePower*powerdict_GetBasePowerByCRC(const PowerDictionary*d,unsigned crc){(void)d;for(unsigned i=0;i<4;i++)if(powers[i].crcFullName==crc)return powers+i;assert(!"unregistered fixture power");return NULL;}
static void window_setMode(int a,int b){assert(a==WDW_COMBATNUMBERS&&b==WINDOW_DISPLAYING);window_calls++;}
static void Errorf(const char*f,...){(void)f;assert(!"missing fixture description");}
static AttribContributer*findMatchingMod(AttribDescription*d,AttribContributer*c){(void)d;(void)c;return NULL;}
static AttribContributer*allocated[32];static unsigned allocation_count;
static void*fixture_contributor_allocate(size_t n){assert(allocation_count<32);void*p=calloc(1,n);assert(p);allocated[allocation_count++]=p;return p;}

static char interned_names[32][256];static unsigned interned_count;
static const char*allocAddString(const char*s){assert(interned_count<32&&strlen(s)<256);strcpy(interned_names[interned_count],s);return interned_names[interned_count++];}
