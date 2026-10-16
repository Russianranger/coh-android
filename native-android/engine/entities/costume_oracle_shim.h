/* Deterministic storage/dictionary adapters only. Original costume, cache,
 * indexed string/color and scalar functions are compiled unchanged below. */
#include <strings.h>
#include "coh_costume.h"
typedef float F32;typedef int bool;
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define stricmp strcasecmp
#define START_BIT_COUNT(...)
#define STOP_BIT_COUNT(...)
#define NUM_SG_COLOR_SLOTS 6
#define MAX_BODY_SCALES 30
#define SERVER 0
#define CLIENT 1
static int g_bAssertOnBitStreamError=1,do_not_assert_on_bad_indexed_string_read;
typedef struct {uint32_t integer;} Color;
typedef struct {uint32_t SGBitSetLow,SGBitSetHigh;} SGColorBits;
typedef struct {
 const char *entTypeFile,*costumeFilePrefix;int bodytype,convertedScale,currentSuperColorSet,iNumParts;
 Color colorSkin;float fScales[30];
 SGColorBits superColorsPrimaryU[6],superColorsSecondaryU[6],superColorsPrimary2U[6],superColorsSecondary2U[6],superColorsTertiaryU[6],superColorsQuaternaryU[6];
} Appearance;
typedef struct {const char *pchGeom,*pchTex1,*pchTex2,*pchFxName,*displayName,*regionName,*bodySetName;Color color[4];} CostumePart;
typedef struct {Appearance appearance;CostumePart *parts[30];} Costume;
typedef struct {Color color[2];const char *regionName;} CustomNPCCostumePart;
typedef struct {Color skinColor;CustomNPCCostumePart **parts;} CustomNPCCostume;
typedef struct {unsigned max_size;const char *strings[16];uint32_t colors[16];uint8_t present[16];} Table;
typedef const Table *cStashTable;
static Table strings_table={16,{NULL,"None",NULL,"Male","FixtureEntity","FixtureGeometry"}},extra_table={8,{NULL,NULL,"Upper",NULL,"BodySet"}},palette_table={8,{0},{0,0,0x11223344,0,0,0x55667788},{0,0,1,0,0,1}};
static cStashTable costume_HashTable=&strings_table,costume_HashTableExtraInfo=&extra_table,costume_PaletteTable=&palette_table;
static unsigned stashGetMaxSize(cStashTable t){return t->max_size;}
static int stashFindIndexByKey(cStashTable t,const char *s,int *idx){for(unsigned i=0;i<t->max_size;i++)if(t->strings[i]&&!strcasecmp(s,t->strings[i])){*idx=(int)i;return 1;}return 0;}
static int stashFindKeyByIndex(cStashTable t,int i,const char **out){if(i<0||(unsigned)i>=t->max_size||!t->strings[i])return 0;*out=t->strings[i];return 1;}
static int stashIntFindIndexByKey(cStashTable t,uint32_t v,uint32_t *idx){for(unsigned i=0;i<t->max_size;i++)if(t->present[i]&&t->colors[i]==v){*idx=i;return 1;}return 0;}
static int stashIntFindKeyByIndex(cStashTable t,uint32_t i,int *out){if(i>=t->max_size||!t->present[i])return 0;*out=(int)t->colors[i];return 1;}
static int stashIntFindPointer(cStashTable t,int v,void *out){uint32_t i;(void)out;return stashIntFindIndexByKey(t,(uint32_t)v,&i);}
static char literal_strings[512][260];static unsigned literal_count;
static const char *allocAddString(const char *s){return s;}
static char *pktGetString(Packet *p){unsigned i;char *s;assert(literal_count<512);s=literal_strings[literal_count++];for(i=0;i<260;i++){s[i]=(char)pktGetBits(p,8);if(!s[i])return s;}assert(0);return NULL;}
static int GetBodyPartCount(void){return 4;}
static int getBodyTypeCount(void){return 6;}
static int isNullOrNone(const char *s){return !s||!strcasecmp(s,"None");}
static void init_costume(Costume *c){memset(&c->appearance,0,sizeof(c->appearance));for(unsigned i=0;i<30;i++)memset(c->parts[i],0,sizeof(*c->parts[i]));}
static unsigned custom_count;
static CustomNPCCostumePart *custom_parts[63];
static void init_custom(CustomNPCCostume *c){memset(c,0,sizeof(*c));memset(custom_parts,0,sizeof(custom_parts));c->parts=custom_parts;custom_count=0;}
#define ParseCostume init_costume
#define ParseCustomNPCCostume init_custom
#define StructInitFields(fn,p) fn(p)
#define StructAllocRaw(n) calloc(1,n)
#define eaSize(p) ((void)(p),(int)custom_count)
#define eaPush(p,v) do{assert(custom_count<63);(*(p))[custom_count++]=(v);}while(0)
static int num_colors_lookup[]={2,4},num_colors_inv_lookup[]={-1,-1,0,-1,1};
static const char *stringcache[120];static int stringcachecount,stringcacheorder;
static int colorcache[120],colorcachecount,colorcacheorder;
