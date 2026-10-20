#include "coh_original_costume_receive.h"
#include <setjmp.h>
#include <stdint.h>
#include <limits.h>
#include <math.h>
#include <string.h>
#include <strings.h>
typedef uint32_t U32;typedef float F32;typedef int bool;
#define ARRAY_SIZE(x) ((int)(sizeof(x)/sizeof((x)[0])))
#define NUM_SG_COLOR_SLOTS 6
#define MAX_BODY_SCALES 30
#define SERVER 0
#define START_BIT_COUNT(...)
#define STOP_BIT_COUNT(...)
#define stricmp strcasecmp
#define g_BodyTypeInfos coh_original_bodytype_infos
#define getBodyTypeCount coh_original_bodytype_count
#define COH_ORIGINAL_COSTUME_TYPES
#include "original_costume_receive.inc"
#undef COH_ORIGINAL_COSTUME_TYPES
typedef CohOriginalCostumeObject Costume;
typedef struct{unsigned kind;} Table;typedef const Table *cStashTable;
static const Table ordinary={COH_ORIGINAL_COSTUME_STRINGS},extra={COH_ORIGINAL_COSTUME_EXTRA_STRINGS},palette={COH_ORIGINAL_COSTUME_PALETTE};
#define costume_HashTable (&ordinary)
#define costume_HashTableExtraInfo (&extra)
#define costume_PaletteTable (&palette)
typedef CohOriginalCostumeState Packet;
typedef char workspace_size_check[sizeof(Packet)<=COH_ORIGINAL_COSTUME_WORKSPACE_BYTES?1:-1];
typedef struct{const void *p;size_t n;} Span;
static int span_valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:s.n==0;}
static int disjoint(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static void fail(Packet *pak,CohStatus status){pak->report.status=status;longjmp(pak->trap,1);}
static U32 pktGetBits(Packet *pak,int n){
 U32 value=0;CohStatus s=coh_rep_read(&pak->reader,(unsigned)n,&value);
 if(s!=COH_OK)fail(pak,s);
 if(n<32&&value>=(1u<<(unsigned)n))fail(pak,COH_INVALID);
 if(pak->cache_first){pak->cache_first=0;
  if(value){if(!pak->cache_count)fail(pak,COH_INVALID);pak->cache_index=pak->cache_count>1;}
  else if(pak->cache_count>=119)fail(pak,COH_LIMIT);
 }else if(pak->cache_index){pak->cache_index=0;if(value>=pak->cache_count)fail(pak,COH_INVALID);}
 else if(!pak->cache_mode&&!pak->scratch.after_count&&pak->scratch.header_flags<2&&n==1)pak->scratch.header_flags++;
 return value;
}
static U32 pktGetBitsPack(Packet *pak,int n){U32 value=0;CohStatus s=coh_rep_pack(&pak->reader,(unsigned)n,&value);if(s!=COH_OK)fail(pak,s);if(value>INT_MAX)fail(pak,COH_LIMIT);return value;}
static F32 pktGetF32(Packet *pak){U32 bits=pktGetBits(pak,32);F32 v;memcpy(&v,&bits,sizeof(v));if(!isfinite(v))fail(pak,COH_INVALID);return v;}
static char *pktGetString(Packet *pak){unsigned i;char *out;if(pak->scratch.literal_count>=182)fail(pak,COH_LIMIT);out=pak->scratch.literals[pak->scratch.literal_count++];for(i=0;i<260;i++){out[i]=(char)pktGetBits(pak,8);if(!out[i])return out;}fail(pak,COH_LIMIT);return NULL;}
static const char *allocAddString(const char *s){return s;}
static int missing_dictionary(Packet *pak,cStashTable table){pak->report.dictionary_required=table->kind;fail(pak,COH_UNSUPPORTED);return 0;}
#define defaultBitsPack(ht) missing_dictionary(pak,(ht))
#define defaultBitsPackGeneric(ht) missing_dictionary(pak,(ht))
#define stashFindIndexByKey(ht,s,out) missing_dictionary(pak,(ht))
#define stashFindKeyByIndex(ht,i,out) ((void)(i),(void)(out),missing_dictionary(pak,(ht)))
#define stashIntFindPointer(ht,v,out) missing_dictionary(pak,(ht))
#define stashIntFindKeyByIndex(ht,i,out) ((void)(i),(void)(out),missing_dictionary(pak,(ht)))
static const int g_bAssertOnBitStreamError=0,do_not_assert_on_bad_indexed_string_read=0;
#define assert(test) do{if(!(test))fail(pak,COH_INVALID);}while(0)
#define stringcache (pak->scratch.strings)
#define stringcachecount (pak->scratch.string_count)
#define stringcacheorder (pak->scratch.string_order)
#define colorcache (pak->scratch.colors)
#define colorcachecount (pak->scratch.color_count)
#define colorcacheorder (pak->scratch.color_order)
static int source_body_parts(Packet *pak){pak->scratch.after_count=1;return(int)pak->body_parts;}
#define GetBodyPartCount() source_body_parts(pak)
static void source_init(Packet *pak,Costume *costume){unsigned i;memset(costume,0,sizeof(*costume));for(i=0;i<30;i++)costume->parts[i]=&pak->scratch.parts[i];}
#define ParseCostume 0
#define StructInitFields(schema,costume) source_init(pak,(costume))
static const int num_colors_lookup[]={2,4};
static const char *observed_indexed_string(Packet *,cStashTable);
static const char *observed_cached_string(Packet *);
static int observed_cached_color(Packet *);
#define costume_receive source_costume_receive
#include "original_costume_receive.inc"
#undef costume_receive
#undef getCachedIndexedString
#undef getCachedIndexedColor
#undef pktGetIndexedString
static const char *observed_indexed_string(Packet *pak,cStashTable table){const char *v;
 if(table==&extra){pak->report.field=pak->scratch.extra_strings%2?COH_ORIGINAL_COSTUME_BODYSET:COH_ORIGINAL_COSTUME_REGION;}
 v=pktGetIndexedString(pak,table);if(table==&extra)pak->scratch.extra_strings++;return v;
}
static const char *observed_cached_string(Packet *pak){const char *v;
 if(pak->scratch.after_count){pak->report.part=pak->scratch.part_strings/4;pak->report.parts_read=pak->report.part;pak->report.field=COH_ORIGINAL_COSTUME_GEOM+pak->scratch.part_strings%4;}
 else pak->report.field=pak->scratch.header_flags==1?COH_ORIGINAL_COSTUME_ENTTYPE:COH_ORIGINAL_COSTUME_PREFIX;
 pak->cache_mode=1;pak->cache_first=1;pak->cache_index=0;pak->cache_count=(unsigned)pak->scratch.string_count;
 v=getCachedIndexedString(pak);pak->cache_mode=0;if(pak->scratch.after_count)pak->scratch.part_strings++;pak->report.strings_read++;return v;
}
static int observed_cached_color(Packet *pak){int value;pak->report.field=COH_ORIGINAL_COSTUME_COLOR;
 pak->cache_mode=2;pak->cache_first=1;pak->cache_index=0;pak->cache_count=(unsigned)pak->scratch.color_count;
 value=getCachedIndexedColor(pak);pak->cache_mode=0;pak->report.colors_read++;return value;
}
static void run_source(Packet *volatile pak){
 if(!setjmp(pak->trap)){
  if(source_costume_receive(pak,&pak->scratch.costume)){pak->report.costume_complete=1;pak->report.parts_read=(uint32_t)pak->scratch.costume.appearance.iNumParts;}
  else pak->report.status=COH_INVALID;
 }
}
static void wipe(void *p,size_t n){volatile unsigned char *v=p;while(n--)*v++=0;}
CohStatus coh_original_costume_receive(const CohRepReader *reader,uint32_t parts,CohOriginalCostumeWorkspace *workspace,CohOriginalCostumeReport *out){
 Span s[4];unsigned i,j;Packet *pak;CohOriginalCostumeReport result;
 if(!reader||!workspace||!out)return COH_INVALID;
 s[0]=(Span){reader,sizeof(*reader)};s[1]=(Span){workspace,sizeof(*workspace)};s[2]=(Span){out,sizeof(*out)};
 for(i=0;i<3;i++){if(!span_valid(s[i]))return COH_INVALID;for(j=0;j<i;j++)if(!disjoint(s[i],s[j]))return COH_INVALID;}
 s[3]=(Span){reader->bytes.data,reader->bytes.size};if(!span_valid(s[3]))return COH_INVALID;for(i=0;i<3;i++)if(!disjoint(s[i],s[3]))return COH_INVALID;
 {size_t cap=reader->max_bytes?reader->max_bytes:COH_REP_MESSAGE_MAX;
 if(!parts||parts>30||cap>COH_REP_BOUNDED_MESSAGE_MAX||reader->bytes.size>cap||reader->cursor>reader->bits||reader->bits>reader->bytes.size*8||reader->compressed>1||(reader->compressed&&(reader->cursor&7)))return COH_INVALID;
 }
 pak=&workspace->state;memset(workspace,0,sizeof(*workspace));pak->reader=*reader;pak->body_parts=parts;pak->report.begin_bit=reader->cursor;pak->report.status=COH_OK;
 run_source(pak);
 pak->report.end_bit=pak->reader.cursor;pak->report.failure_bit=pak->reader.cursor;
 if(pak->scratch.after_count){pak->report.part_count=(uint32_t)pak->scratch.costume.appearance.iNumParts;
  pak->report.bodytype_validated=pak->scratch.costume.appearance.bodytype>=0&&pak->scratch.costume.appearance.bodytype<getBodyTypeCount();
  pak->report.count_validated=pak->report.bodytype_validated&&pak->report.part_count<=parts;
 }
 pak->report.literal_strings=pak->scratch.literal_count;pak->report.string_cache_entries=(uint32_t)pak->scratch.string_count;pak->report.color_cache_entries=(uint32_t)pak->scratch.color_count;
 result=pak->report;wipe(workspace,sizeof(*workspace));*out=result;return result.status;
}
