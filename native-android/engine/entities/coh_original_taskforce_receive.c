#include "coh_original_taskforce_receive.h"
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <strings.h>
typedef uint32_t U32;typedef uint8_t U8;
typedef struct{unsigned unused;}Costume;
typedef CohOriginalCostumeColor Color;
typedef struct{Color color[2];const char *regionName;}CustomNPCCostumePart;
typedef struct{Color skinColor;CustomNPCCostumePart **parts;char *originalNPCName;}CustomNPCCostume;
typedef struct{
 int architect_id,architect_flags,architect_contact_override,architect_useCachedCostume;
 char architect_contact_name[32];Costume *architect_contact_costume;
 CustomNPCCostume *architect_contact_npc_costume;U32 parametersSet,parameters[32];
}TaskForce;
typedef struct{int onArchitect,onFlashback,architect_invincible,architect_untargetable;TaskForce *taskforce;}Entity;
typedef struct{
 CohRepReader reader;CohOriginalTaskforceReport report;jmp_buf trap;
 const CohClientCostumeSlots *slots;CohOriginalCostumeWorkspace *workspace;uint32_t body_parts;
 TaskForce taskforce;Entity entity;Costume dummy;
 CustomNPCCostume custom;CustomNPCCostumePart parts[63];CustomNPCCostumePart *pointers[63];unsigned part_count;
 char literal[4096],review_name[256],review_author[128],review_description[4096];unsigned review_index;
}Packet;
static void fail(Packet *pak,CohStatus s){pak->report.status=s;longjmp(pak->trap,1);}
static U32 pktGetBits(Packet *pak,int bits){U32 v=0;CohStatus s=coh_rep_read(&pak->reader,(unsigned)bits,&v);if(s!=COH_OK)fail(pak,s);if(bits<32&&v>=(1u<<(unsigned)bits))fail(pak,COH_INVALID);return v;}
static U32 pktGetBitsPack(Packet *pak,int bits){U32 v=0;CohStatus s=coh_rep_pack(&pak->reader,(unsigned)bits,&v);if(s!=COH_OK)fail(pak,s);return v;}
static U32 pktGetBitsAuto(Packet *pak){static const unsigned widths[]={2,10,24,32};U32 bin=pktGetBits(pak,2);return pktGetBits(pak,(int)widths[bin]);}
static char *pktGetString(Packet *pak){for(unsigned i=0;i<sizeof(pak->literal);i++){pak->literal[i]=(char)pktGetBits(pak,8);if(!pak->literal[i])return pak->literal;}fail(pak,COH_LIMIT);return NULL;}
static void copy_string(Packet *pak,char *out,size_t cap,const char *in){size_t n=strlen(in);if(n>=cap)fail(pak,COH_LIMIT);memcpy(out,in,n+1);}
static char *review_copy(Packet *pak,const char *s){char *out;size_t cap;pak->report.field=COH_ORIGINAL_TASKFORCE_REVIEW;if(pak->review_index>=3)fail(pak,COH_INVALID);if(!pak->review_index){out=pak->review_name;cap=sizeof(pak->review_name);}else if(pak->review_index==1){out=pak->review_author;cap=sizeof(pak->review_author);}else{out=pak->review_description;cap=sizeof(pak->review_description);}copy_string(pak,out,cap,s);pak->report.review_bytes[pak->review_index++]=(uint32_t)strlen(out);return out;}
static void *source_alloc(Packet *pak,size_t n){if(n==sizeof(CustomNPCCostume)){memset(&pak->custom,0,sizeof(pak->custom));return &pak->custom;}if(n==sizeof(CustomNPCCostumePart)){if(pak->part_count>=63)fail(pak,COH_LIMIT);return &pak->parts[pak->part_count];}fail(pak,COH_INVALID);return NULL;}
static void source_custom_init(Packet *pak,CustomNPCCostume *c){memset(c,0,sizeof(*c));memset(pak->pointers,0,sizeof(pak->pointers));pak->part_count=0;c->parts=pak->pointers;pak->report.field=COH_ORIGINAL_TASKFORCE_CUSTOM;}
static void source_custom_push(Packet *pak,CustomNPCCostumePart ***a,CustomNPCCostumePart *p){if(pak->part_count>=63)fail(pak,COH_LIMIT);(*a)[pak->part_count++]=p;pak->report.custom_parts=pak->part_count;}
static const char *allocAddString(const char *s){return s;}
static int costume_receive(Packet *pak,Costume *c){(void)c;pak->report.field=COH_ORIGINAL_TASKFORCE_BODY;CohStatus s=coh_original_costume_receive_slots_capture(&pak->reader,pak->body_parts,pak->slots,pak->workspace,&pak->report.body,NULL);if(s!=COH_OK){pak->reader.cursor=pak->report.body.failure_bit;fail(pak,s);}if(!pak->report.body.costume_complete)fail(pak,COH_INVALID);pak->reader.cursor=pak->report.body.end_bit;pak->report.body_count++;return 1;}
static void missionReview_Set(int id,int flags,const char *name,const char *author,const char *description,int rating,int european){(void)id;(void)flags;(void)name;(void)author;(void)description;(void)rating;(void)european;}
#define devassert(v) do{if(!(v))fail(pak,COH_INVALID);}while(0)
#define stricmp strcasecmp
#define strcpy(d,s) copy_string(pak,(d),sizeof(d),(s))
#define strdup(s) review_copy(pak,(s))
#define SAFE_FREE(p) ((void)(p))
#define GetBodyPartCount() ((int)pak->body_parts)
#define costume_create(n) ((void)(n),&pak->dummy)
#define costume_init(c) ((void)(c))
#define costume_destroy(c) ((void)(c))
#define ParseCustomNPCCostume 0
#define StructAllocRaw(n) source_alloc(pak,(n))
#define StructInitFields(schema,c) ((void)(schema),source_custom_init(pak,(c)))
#define StructDestroy(schema,c) ((void)(schema),(void)(c))
#define eaPush(a,p) source_custom_push(pak,(a),(p))
#define MAX_TASKFORCE_PARAMETERS 32
#define TFPARAM_TIME_LIMIT 2
#define TFPARAM_START_TIME 24
#define TaskForceIsParameterEnabled(e,n) ((void)(e),(void)(n),0)
#define timerSecondsSince2000() 0
#define NPCcostume_receive taskforce_original_NPCcostume_receive
/* Whole legacy source uses signed1<<31; suppress only that operation class in
 * this one original function. New native readers/copies remain instrumented. */
static int entReceiveTaskforceParameters(Packet *,Entity *) __attribute__((no_sanitize("shift")));
#include "original_taskforce_receive.inc"
static void run(Packet *volatile pak){if(!setjmp(pak->trap)){entRecieveTaskforceArchitectInfo(pak,&pak->entity);pak->report.on_architect=(uint32_t)pak->entity.onArchitect;pak->report.review_present=pak->review_index==3;pak->report.field=COH_ORIGINAL_TASKFORCE_PARAMETERS;(void)entReceiveTaskforceParameters(pak,&pak->entity);pak->report.on_flashback=(uint32_t)pak->entity.onFlashback;pak->report.parameter_mask=pak->taskforce.parametersSet;memcpy(pak->report.parameters,pak->taskforce.parameters,sizeof(pak->report.parameters));pak->report.complete=1;pak->report.field=COH_ORIGINAL_TASKFORCE_COMPLETE;}}
static int span(const void*p,size_t n){return p&&(uintptr_t)p<=UINTPTR_MAX-n;}
static int apart(const void*a,size_t an,const void*b,size_t bn){return(uintptr_t)a+an<=(uintptr_t)b||(uintptr_t)b+bn<=(uintptr_t)a;}
#define ALIGN(T) offsetof(struct{char byte;T value;},value)
CohStatus coh_original_taskforce_receive(const CohRepReader *r,uint32_t parts,const CohClientCostumeSlots *slots,CohOriginalCostumeWorkspace *w,CohOriginalTaskforceReport *out){
 const void *p[7];size_t n[7];unsigned count=4;Packet state;
 if(!span(r,sizeof(*r))||!span(w,sizeof(*w))||!span(out,sizeof(*out))||!parts||parts>30||(uintptr_t)r%ALIGN(CohRepReader)||(uintptr_t)w%ALIGN(CohOriginalCostumeWorkspace)||(uintptr_t)out%ALIGN(CohOriginalTaskforceReport))return COH_INVALID;
 p[0]=r;n[0]=sizeof(*r);p[1]=w;n[1]=sizeof(*w);p[2]=out;n[2]=sizeof(*out);p[3]=r->bytes.data;n[3]=r->bytes.size;
 if(slots){if(!span(slots,sizeof(*slots))||(uintptr_t)slots%ALIGN(CohClientCostumeSlots))return COH_INVALID;p[count]=slots;n[count++]=sizeof(*slots);p[count]=slots->raw.data;n[count++]=slots->raw.size;p[count]=slots->index;n[count++]=COH_CLIENT_COSTUME_INDEX_BYTES;}
 for(unsigned i=0;i<count;i++){if(!n[i]||!span(p[i],n[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(p[i],n[i],p[j],n[j]))return COH_INVALID;}
 size_t cap=r->max_bytes?r->max_bytes:COH_REP_MESSAGE_MAX;if(cap>COH_REP_BOUNDED_MESSAGE_MAX||r->bytes.size>cap||r->cursor>r->bits||r->bits>r->bytes.size*8||r->compressed>1||(r->compressed&&(r->cursor&7)))return COH_INVALID;
 if(slots&&(slots->raw.size!=COH_CLIENT_COSTUME_RAW_BYTES||slots->capacity[0]!=32768||slots->capacity[1]!=256||slots->capacity[2]!=512))return COH_INVALID;
 memset(&state,0,sizeof(state));state.reader=*r;state.report.begin_bit=r->cursor;state.report.packet_bits=r->bits;state.report.field=COH_ORIGINAL_TASKFORCE_ARCHITECT;state.body_parts=parts;state.slots=slots;state.workspace=w;state.entity.taskforce=&state.taskforce;
 run(&state);state.report.end_bit=state.report.failure_bit=state.reader.cursor;*out=state.report;volatile unsigned char *v=(volatile unsigned char*)&state;size_t bytes=sizeof(state);while(bytes--)*v++=0;return out->status;
}
