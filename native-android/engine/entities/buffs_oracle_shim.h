/* Fixture-only synthetic entity/dictionary/UI/stash shells. Source functions
 * extracted after this include execute unchanged. No account/world authority. */
#include <stdbool.h>
#include <math.h>
#define CLIENT 0
#define LOG_ENT(...) ((void)0)
#define START_BIT_COUNT(...)
#define STOP_BIT_COUNT(...)
typedef float F32;
typedef struct {U32 crcFullName;} BasePower;
typedef struct {int unused;} PowerDictionary;
typedef struct {int iHash;} AttribDescription;
typedef struct {float fMag;int iHash;} BuffMagnitude;
typedef struct {const BasePower *ppow;float time_remaining;U32 uiID;int mod_cnt,addedOrChangedThisTick;BuffMagnitude mod[65];} UniqueBuff;
typedef struct {unsigned count;U32 keys[512];} BuffStash;
typedef struct Entity Entity;
typedef struct {Entity *entParent;BuffStash *stSentBuffs,*stNewBuffs;int update_buffs;} Character;
typedef struct {U32 buffSettings;} Player;
struct Entity {int db_id,id,teamup_id,league_id,iCntBuffs,team_buff_full_update,*diffBuffs;Entity *erOwner;Character *pchar;Player *pl;UniqueBuff aBuffs[300];};
BUFF_SETTINGS_FROM_SOURCE
static PowerDictionary g_PowerDictionary;
static BasePower fixture_powers[]={{1},{1023},{0x10203040},{0x80000000},{0xffffffff}};
static int fixture_diff_count;
#define eaiSize(pp) ((void)(pp),fixture_diff_count)
static Entity *erGetEnt(Entity *e){return e;}
static BuffStash fixture_new_stash,fixture_sent_stash;
static BuffStash *stashTableCreateInt(int n){(void)n;assert(0);return NULL;}
static int stashIntFindInt(BuffStash *s,U32 key,void *out){(void)out;for(unsigned i=0;i<s->count;i++)if(s->keys[i]==key)return 1;return 0;}
static int stashIntAddInt(BuffStash *s,U32 key,U32 value,int overwrite){(void)value;(void)overwrite;if(!stashIntFindInt(s,key,NULL)){assert(s->count<512);s->keys[s->count++]=key;}return 1;}
static const BasePower *powerdict_GetBasePowerByCRC(const PowerDictionary *d,int crc){(void)d;for(unsigned i=0;i<sizeof(fixture_powers)/sizeof(fixture_powers[0]);i++)if(fixture_powers[i].crcFullName==(U32)crc)return &fixture_powers[i];return NULL;}
static U32 observation[32768],observation_used;
static void emit(U32 n){assert(observation_used<32768);observation[observation_used++]=n;}
static void markPowerBuff(Entity *e){(void)e;emit(1);}
static void clearMarkedPowerBuff(Entity *e){(void)e;emit(2);}
static void markBuffForDeletion(Entity *e,int uid){(void)e;emit(4);emit((U32)uid);}
static AttribDescription fixture_descs[65];
static unsigned fixture_desc_count,fixture_mag_count;
static AttribDescription *fixture_desc_ptrs[65];
static float fixture_mags[65];
static AttribDescription *attribDescriptionGet(int hash){if((U32)hash==0xffffffff)return NULL;assert(fixture_desc_count<65);fixture_descs[fixture_desc_count].iHash=hash;return &fixture_descs[fixture_desc_count];}
static void push_desc(AttribDescription ***p,AttribDescription *d){assert(fixture_desc_count<65);fixture_desc_ptrs[fixture_desc_count++]=d;*p=fixture_desc_ptrs;}
static void push_mag(float **p,float f){assert(fixture_mag_count<65);fixture_mags[fixture_mag_count++]=f;*p=fixture_mags;}
#define eaPush(p,v) push_desc(p,v)
#define eafPush(p,v) push_mag(p,v)
static void destroy_desc(AttribDescription ***p){*p=NULL;fixture_desc_count=fixture_mag_count=0;}
#define eaDestroy(p) destroy_desc(p)
static void addUpdatePowerBuff(Entity *e,const BasePower *p,int blink,int uid,AttribDescription **desc,float *mags){(void)e;(void)desc;(void)mags;emit(3);emit(p->crcFullName);emit((U32)blink);emit((U32)uid);emit(fixture_desc_count);assert(fixture_desc_count==fixture_mag_count);for(unsigned i=0;i<fixture_desc_count;i++){U32 u;memcpy(&u,&fixture_mags[i],4);emit((U32)fixture_desc_ptrs[i]->iHash);emit(u);}}
static int pktEnd(Packet *p){return bsGetCursorBitPosition(&p->stream)>=p->stream.bitLength;}
