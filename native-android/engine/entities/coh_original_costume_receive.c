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
static uint32_t slot_word(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static CohStatus slot_projection(CohBytes raw,uint32_t *index){
 static const uint32_t caps[3]={32768,256,512},counts[3]={13209,156,224};
 size_t at=0,k=0;unsigned table;uint32_t i,seen;
 for(table=0;table<3;table++){
  if(raw.size-at<8||slot_word(raw.data+at)!=caps[table]||slot_word(raw.data+at+4)!=counts[table])return COH_INVALID;
  at+=8;seen=0;
  for(i=0;i<caps[table];i++,k++){
   uint32_t present,n;if(raw.size-at<4)return COH_INVALID;present=slot_word(raw.data+at);at+=4;
   if(present>1)return COH_INVALID;
   if(index)index[k]=present?(uint32_t)at:0;
   if(!present)continue;
   seen++;if(raw.size-at<4)return COH_INVALID;n=slot_word(raw.data+at);at+=4;
   if(table==2){if(!n)return COH_INVALID;}
   else{if(n>=260)return COH_LIMIT;if(n>raw.size-at||memchr(raw.data+at,0,n))return COH_INVALID;at+=n;}
  }
  if(seen!=counts[table])return COH_INVALID;
 }
 return at==raw.size?COH_OK:COH_INVALID;
}
CohStatus coh_client_costume_slots_prepare(CohBytes raw,uint32_t *index,size_t count,
 const CohCostumeImportDigest *digest,CohClientCostumeSlots *out,size_t budget,size_t retained){
 static const uint8_t expected[32]={0x2e,0x69,0x21,0x24,0x32,0xd1,0xb1,0x6a,0x38,0xf3,0x07,0xac,0xa1,0x6a,0xc8,0x92,0xcc,0xa5,0x6c,0xf5,0x91,0x28,0xd5,0xd8,0xd2,0x5e,0x71,0x38,0x6d,0xa4,0xaf,0x81};
 Span spans[5];size_t i,j,charge=COH_CLIENT_COSTUME_PREPARE_STACK_RESERVE;CohStatus status;uint8_t hash[32];CohClientCostumeSlots result;
 if(!raw.data||raw.size!=COH_CLIENT_COSTUME_RAW_BYTES||!index||count!=COH_CLIENT_COSTUME_INDEX_COUNT||!digest||!out)return COH_INVALID;
 if((uintptr_t)index%sizeof(uint32_t)||(uintptr_t)digest%sizeof(void*)||(uintptr_t)out%sizeof(void*))return COH_INVALID;
 spans[0]=(Span){raw.data,raw.size};spans[1]=(Span){index,COH_CLIENT_COSTUME_INDEX_BYTES};spans[2]=(Span){digest,sizeof(*digest)};spans[3]=(Span){out,sizeof(*out)};
 for(i=0;i<4;i++){if(!span_valid(spans[i]))return COH_INVALID;for(j=0;j<i;j++)if(!disjoint(spans[i],spans[j]))return COH_INVALID;}
 if(!digest->sha256||(!digest->context&&digest->context_bytes))return COH_INVALID;
 spans[4]=(Span){digest->context,digest->context_bytes};if(!span_valid(spans[4]))return COH_INVALID;for(j=0;j<4;j++)if(!disjoint(spans[4],spans[j]))return COH_INVALID;
 if(!budget||budget>8u*1024u*1024u)return COH_LIMIT;
 for(i=0;i<5;i++){if(spans[i].n>budget||charge>budget-spans[i].n)return COH_LIMIT;charge+=spans[i].n;}
 if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)return COH_LIMIT;
 charge+=digest->scratch_reserve;if(retained>budget||charge>budget-retained)return COH_LIMIT;
 charge+=retained;status=slot_projection(raw,NULL);if(status!=COH_OK)return status;
 status=digest->sha256(digest->context,raw,hash);if(status!=COH_OK)return status;if(memcmp(hash,expected,32))return COH_STATE;
 memset(&result,0,sizeof(result));result.raw=raw;result.index=index;result.capacity[0]=32768;result.capacity[1]=256;result.capacity[2]=512;result.present[0]=13209;result.present[1]=156;result.present[2]=224;result.charged_bytes=charge;
 (void)slot_projection(raw,index);*out=result;return COH_OK;
}
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
static char *pktGetString(Packet *pak){unsigned i;char *out;if(pak->scratch.literal_count>=182)fail(pak,COH_LIMIT);out=pak->scratch.literals[pak->scratch.literal_count++];pak->scratch.wire_literal_count++;for(i=0;i<260;i++){out[i]=(char)pktGetBits(pak,8);if(!out[i])return out;}fail(pak,COH_LIMIT);return NULL;}
static const char *allocAddString(const char *s){return s;}
static int missing_dictionary(Packet *pak,cStashTable table){pak->report.dictionary_required=table->kind;fail(pak,COH_UNSUPPORTED);return 0;}
static int slot_bits(Packet *pak,cStashTable table){
 if(!pak->client_slots)return missing_dictionary(pak,table);
 return table->kind==COH_ORIGINAL_COSTUME_STRINGS?15:table->kind==COH_ORIGINAL_COSTUME_EXTRA_STRINGS?8:9;
}
static uint32_t slot_offset(Packet *pak,cStashTable table,uint32_t index){
 const CohClientCostumeSlots *s=pak->client_slots;size_t base;
 if(!s)return(uint32_t)missing_dictionary(pak,table);
 base=table->kind==COH_ORIGINAL_COSTUME_STRINGS?0:table->kind==COH_ORIGINAL_COSTUME_EXTRA_STRINGS?32768:33024;
 if(index>=s->capacity[table->kind-1])return 0;
 return s->index[base+index];
}
static int slot_string(Packet *pak,cStashTable table,uint32_t index,const char **out){
 const CohClientCostumeSlots *s=pak->client_slots;uint32_t offset=slot_offset(pak,table,index),n;char *copy;
 if(!offset){*out=NULL;return 0;}
 if(offset>s->raw.size-4)fail(pak,COH_INVALID);
 n=slot_word(s->raw.data+offset);
 if(n>=260||n>s->raw.size-offset-4)fail(pak,COH_INVALID);
 if(pak->scratch.literal_count>=182)fail(pak,COH_LIMIT);
 copy=pak->scratch.literals[pak->scratch.literal_count++];memcpy(copy,s->raw.data+offset+4,n);copy[n]=0;*out=copy;return 1;
}
static int slot_color(Packet *pak,cStashTable table,uint32_t index,int *out){
 const CohClientCostumeSlots *s=pak->client_slots;uint32_t offset=slot_offset(pak,table,index),value;
 if(!offset){*out=0;return 0;}if(offset>s->raw.size-4)fail(pak,COH_INVALID);value=slot_word(s->raw.data+offset);memcpy(out,&value,4);return 1;
}
static int slot_find_string(Packet *pak,cStashTable table,const char *text,int *out){
 const CohClientCostumeSlots *s=pak->client_slots;size_t base;uint32_t i,n,offset;
 if(!s)return missing_dictionary(pak,table);
 base=table->kind==COH_ORIGINAL_COSTUME_STRINGS?0:32768;
 for(i=0;i<s->capacity[table->kind-1];i++){
  offset=s->index[base+i];if(!offset)continue;if(offset>s->raw.size-4)fail(pak,COH_INVALID);
 n=slot_word(s->raw.data+offset);if(n>=260||n>s->raw.size-offset-4)fail(pak,COH_INVALID);
  if(strlen(text)==n&&!strncasecmp(text,(const char*)s->raw.data+offset+4,n)){*out=(int)i;return 1;}
 }return 0;
}
static int slot_find_color(Packet *pak,cStashTable table,int value){
 const CohClientCostumeSlots *s=pak->client_slots;uint32_t i,bits;int candidate;
 if(!s)return missing_dictionary(pak,table);
 memcpy(&bits,&value,4);
 for(i=0;i<s->capacity[2];i++){if(slot_color(pak,table,i,&candidate)){uint32_t other;memcpy(&other,&candidate,4);if(bits==other)return 1;}}
 return 0;
}
#define defaultBitsPack(ht) slot_bits(pak,(ht))
#define defaultBitsPackGeneric(ht) slot_bits(pak,(ht))
#define stashFindIndexByKey(ht,s,out) slot_find_string(pak,(ht),(s),(out))
#define stashFindKeyByIndex(ht,i,out) slot_string(pak,(ht),(uint32_t)(i),(out))
#define stashIntFindPointer(ht,v,out) ((void)(out),slot_find_color(pak,(ht),(v)))
#define stashIntFindKeyByIndex(ht,i,out) slot_color(pak,(ht),(i),(out))
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
CohStatus coh_original_costume_receive_slots(const CohRepReader *reader,uint32_t parts,const CohClientCostumeSlots *slots,CohOriginalCostumeWorkspace *workspace,CohOriginalCostumeReport *out){
 Span s[7];unsigned i,j;Packet *pak;CohOriginalCostumeReport result;
 if(!reader||!workspace||!out)return COH_INVALID;
 s[0]=(Span){reader,sizeof(*reader)};s[1]=(Span){workspace,sizeof(*workspace)};s[2]=(Span){out,sizeof(*out)};
 for(i=0;i<3;i++){if(!span_valid(s[i]))return COH_INVALID;for(j=0;j<i;j++)if(!disjoint(s[i],s[j]))return COH_INVALID;}
 s[3]=(Span){reader->bytes.data,reader->bytes.size};if(!span_valid(s[3]))return COH_INVALID;for(i=0;i<3;i++)if(!disjoint(s[i],s[3]))return COH_INVALID;
 {size_t cap=reader->max_bytes?reader->max_bytes:COH_REP_MESSAGE_MAX;
 if(!parts||parts>30||cap>COH_REP_BOUNDED_MESSAGE_MAX||reader->bytes.size>cap||reader->cursor>reader->bits||reader->bits>reader->bytes.size*8||reader->compressed>1||(reader->compressed&&(reader->cursor&7)))return COH_INVALID;
 }
 if(slots){
  if((uintptr_t)slots%sizeof(void*))return COH_INVALID;
  s[4]=(Span){slots,sizeof(*slots)};if(!span_valid(s[4]))return COH_INVALID;for(i=0;i<4;i++)if(!disjoint(s[i],s[4]))return COH_INVALID;
  if(slots->raw.size!=COH_CLIENT_COSTUME_RAW_BYTES||slots->capacity[0]!=32768||slots->capacity[1]!=256||slots->capacity[2]!=512||slots->present[0]!=13209||slots->present[1]!=156||slots->present[2]!=224||!slots->raw.data||!slots->index||(uintptr_t)slots->index%sizeof(uint32_t))return COH_INVALID;
  s[5]=(Span){slots->raw.data,slots->raw.size};s[6]=(Span){slots->index,COH_CLIENT_COSTUME_INDEX_BYTES};
  for(i=5;i<7;i++){if(!span_valid(s[i]))return COH_INVALID;for(j=0;j<i;j++)if(!disjoint(s[i],s[j]))return COH_INVALID;}
 }
 pak=&workspace->state;memset(workspace,0,sizeof(*workspace));pak->reader=*reader;pak->body_parts=parts;pak->client_slots=slots;pak->report.begin_bit=reader->cursor;pak->report.status=COH_OK;
 run_source(pak);
 pak->report.end_bit=pak->reader.cursor;pak->report.failure_bit=pak->reader.cursor;
 if(pak->scratch.after_count){pak->report.part_count=(uint32_t)pak->scratch.costume.appearance.iNumParts;
  pak->report.bodytype_validated=pak->scratch.costume.appearance.bodytype>=0&&pak->scratch.costume.appearance.bodytype<getBodyTypeCount();
  pak->report.count_validated=pak->report.bodytype_validated&&pak->report.part_count<=parts;
 }
 pak->report.literal_strings=pak->scratch.wire_literal_count;pak->report.string_cache_entries=(uint32_t)pak->scratch.string_count;pak->report.color_cache_entries=(uint32_t)pak->scratch.color_count;
 result=pak->report;wipe(workspace,sizeof(*workspace));*out=result;return result.status;
}

CohStatus coh_original_costume_receive(const CohRepReader *reader,uint32_t parts,CohOriginalCostumeWorkspace *workspace,CohOriginalCostumeReport *out){
 return coh_original_costume_receive_slots(reader,parts,NULL,workspace,out);
}
