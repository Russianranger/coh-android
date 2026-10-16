/* Source-oracle-only type/storage adapter. The attribute schema declarations,
 * struct walker and scalar packers below this adapter are extracted unchanged.
 * This deterministic POD is not an engine Character or imported character. */
#include <stddef.h>
typedef int bool;
#define true 1
#define false 0
#define devassert assert
typedef unsigned long long StructTypeField;
typedef struct ParseTable ParseTable;
struct ParseTable {const char *name;StructTypeField type;size_t offset,param;ParseTable *subtable;};
typedef ParseTable TokenizerParseInfo;
typedef struct {float fHitPoints,fAbsorb,fEndurance,fMeter,fPerceptionRadius,fStealthRadiusPlayer,fConfused,fToHit;} CharacterAttributes;
typedef struct {CharacterAttributes attrCur,attrMax;int iLevel,iCombatLevel,iExperiencePoints,iExperienceDebt,iExperienceRest,iInfluencePoints;} StatsCharacter;
typedef int FloatAccuracy;
#define FLOAT_HUNDRETHS 1
#define FLOAT_TENTHS 2
#define FLOAT_ONES 3
#define FLOAT_FIVES 4
#define FLOAT_TENS 5
#define TOK_IGNORE 0
#define TOK_START 4
#define TOK_END 5
#define TOK_REDUNDANTNAME (1ull<<40)
#define TOK_GET_TYPE(t) ((t)&255)
#define TOK_GET_PRECISION_DEF(t,d) (((t)>>8)&255?((t)>>8)&255:(d))
#define TOK_GET_FLOAT_ROUNDING(t) (((t)>>16)&255)
#define TOK_MINBITS(n) ((n)<<8)
#define TOK_FLOAT_ROUNDING(n) ((n)<<16)
#define TOK_INT(T,m,d) 1,offsetof(T,m),0,NULL
#define TOK_F32(T,m,d) 2,offsetof(T,m),0,NULL
#define TOK_EMBEDDEDSTRUCT(T,m,t) 3,offsetof(T,m),sizeof(((T*)0)->m),t
#define TOK_NULLSTRUCT(t) 3,0,0,t
#define FORALL_PARSEINFO(t,i) for(i=0;(t)[i].name;i++)
static int TokenStoreGetInt(ParseTable *t,int c,void *s,int i){(void)i;return *(int*)((char*)s+t[c].offset);}
static float TokenStoreGetF32(ParseTable *t,int c,void *s,int i){(void)i;return *(float*)((char*)s+t[c].offset);}
static void *TokenStoreGetPointer(ParseTable *t,int c,void *s,int i){(void)i;return (char*)s+t[c].offset;}
static int fixture_compare(ParseTable *t,int c,void *a,void *b,int i){(void)t;(void)c;(void)a;(void)b;(void)i;assert(0);return 0;}
typedef void (*SendDiff)(Packet*,ParseTable*,int,void*,void*,int,bool,bool,bool,StructTypeField,StructTypeField);
typedef struct {int(*compare)(ParseTable*,int,void*,void*,int);SendDiff senddiff;void(*recvdiff)(Packet*,ParseTable*,int,void*,int,int,void**);} StatsOps;
static StatsOps stats_ops[4];
#define TOKARRAY_INFO(t) stats_ops[TOK_GET_TYPE(t)]
static void packDelta(Packet *p,int d){(void)p;(void)d;assert(0);}
void sdPackStruct(ParseTable*,Packet*,void*,void*,bool,bool,StructTypeField,StructTypeField);
void ParserSend(ParseTable*,Packet*,void*,void*,bool,bool,bool,StructTypeField,StructTypeField);
#define PTR_TO_U32(p) ((U32)(uintptr_t)(p))
#define U32_TO_PTR(p) ((void*)(uintptr_t)(p))
static const char *invalidName="incompatible",*outOfSyncName="out-of-sync";
static int s_inSync,g_bAssertOnBitStreamError;
static int ParseTableCountFields(ParseTable *p){int n=0;while(p[n].name)n++;return n;}
static void TokenStoreSetInt(ParseTable *t,int c,void *s,int i,int v){(void)i;*(int*)((char*)s+t[c].offset)=v;}
static void TokenStoreSetF32(ParseTable *t,int c,void *s,int i,float v){(void)i;*(float*)((char*)s+t[c].offset)=v;}
static int unpackDelta(Packet *p){(void)p;assert(0);return 0;}
static void *TokenStoreAlloc(ParseTable *t,int c,void *s,int i,size_t size,void *a,void *b){(void)t;(void)c;(void)s;(void)i;(void)size;(void)a;(void)b;assert(0);return NULL;}
static void struct_destroystruct(ParseTable *t,int c,void *s,int i){(void)t;(void)c;(void)s;(void)i;assert(0);}
static void ParserFreePktIds(ParseTable *t,void ***ids){(void)t;(void)ids;assert(0);}
void sdUnpackStruct(ParseTable*,Packet*,void*,void***,bool);
