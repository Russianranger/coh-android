#include "coh_initial_list.h"
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(!a||!b||an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static CohStatus acquire(void*opaque,size_t minimum,size_t maximum,CohSelectedRecordLoan*loan){
 CohInitialListAllocator*a=opaque;CohStatus status=a->original->acquire(a->original->context,minimum,maximum,loan);
 if(status!=COH_OK)return status;
 for(unsigned i=0;i<10;i++)if(overlap(loan->data,loan->bytes,a->spans[i].pointer,a->spans[i].bytes))return COH_INVALID;
 return COH_OK;
}
static void release(void*opaque,CohSelectedRecordLoan*loan){CohInitialListAllocator*a=opaque;a->original->release(a->original->context,loan);}
static CohStatus refuse(CohInitialListFailure*f,CohStatus status,size_t bit){f->status=status;f->bit=bit;return status;}
CohStatus coh_initial_list_read(CohRepReader*reader,const CohSelectedRecordContext*context,
 const CohSelectedRecordMemory*memory,CohInitialListEntry*entries,size_t capacity,CohInitialList*out,
 CohInitialListWorkspace*w,CohInitialListFailure*failure,size_t budget,size_t retained){
 if(!reader||!context||!memory||!memory->acquire||!memory->release||!entries||!capacity||capacity>COH_ENT_LIST_MAX||!out||!w||!failure||!budget||budget>COH_SELECTED_RECORD_RAM_MAX||(!memory->context&&memory->context_bytes)||(memory->context&&!memory->context_bytes))return COH_INVALID;
 CohRepReader probe=*reader;uint32_t ignored;CohStatus status=coh_rep_read(&probe,0,&ignored);if(status!=COH_OK)return status;
 CohInitialListSpan spans[10]={{reader,sizeof(*reader)},{context,sizeof(*context)},{memory,sizeof(*memory)},{entries,capacity*sizeof(*entries)},{out,sizeof(*out)},{w,sizeof(*w)},{failure,sizeof(*failure)},{probe.bytes.data,probe.bytes.size},{memory->context,memory->context_bytes},{context->costume_dictionary,0}};
 for(unsigned i=0;i<9;i++){if(spans[i].bytes&&(!spans[i].pointer||spans[i].bytes>UINTPTR_MAX-(uintptr_t)spans[i].pointer))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i].pointer,spans[i].bytes,spans[j].pointer,spans[j].bytes))return COH_INVALID;}
 if(context->costume_dictionary){
  for(unsigned i=0;i<9;i++)if(overlap(context->costume_dictionary,1,spans[i].pointer,spans[i].bytes))return COH_INVALID;
  spans[9].bytes=coh_ent_costume_dictionary_bytes(context->costume_dictionary);if(!spans[9].bytes||spans[9].bytes>COH_COSTUME_DICTIONARY_BYTES_MAX||spans[9].bytes>UINTPTR_MAX-(uintptr_t)context->costume_dictionary)return COH_INVALID;
  for(unsigned i=0;i<9;i++)if(overlap(spans[9].pointer,spans[9].bytes,spans[i].pointer,spans[i].bytes))return COH_INVALID;
 }
 memset(failure,0,sizeof(*failure));failure->bit=probe.cursor;
 if(context->entity_index||!context->selected_dbid||context->selected_dbid>INT32_MAX||!context->packet_id||!context->dictionary_generation||!context->packet_lease_token||context->interp_level>3)return refuse(failure,COH_INVALID,probe.cursor);
 size_t occupied=COH_INITIAL_LIST_STACK_RESERVE;
 for(unsigned i=0;i<10;i++){if(spans[i].bytes>budget||occupied>budget-spans[i].bytes)return refuse(failure,COH_LIMIT,probe.cursor);occupied+=spans[i].bytes;}
 if(retained>budget-occupied)return refuse(failure,COH_LIMIT,probe.cursor);
 occupied+=retained;
 size_t child_fixed=COH_SELECTED_RECORD_STACK_RESERVE+sizeof(w->reader)+sizeof(w->context)+sizeof(w->prior)+sizeof(w->adapter)+sizeof(w->record)+sizeof(w->record_workspace)+sizeof(failure->record)+probe.bytes.size+sizeof(w->allocator)+spans[9].bytes;
 if(child_fixed>occupied)return refuse(failure,COH_INVALID,probe.cursor);
 size_t child_extra=occupied-child_fixed;
 w->reader=probe;w->context=*context;w->allocator.original=memory;memcpy(w->allocator.spans,spans,sizeof(spans));w->adapter=(CohSelectedRecordMemory){&w->allocator,sizeof(w->allocator),acquire,release};
 CohInitialList*c=&w->candidate;memset(c,0,sizeof(*c));c->packet=probe.bytes;c->packet_bits=probe.bits;c->begin_bit=probe.cursor;c->packet_lease_token=context->packet_lease_token;c->packet_id=context->packet_id;c->selected_dbid=context->selected_dbid;
 int32_t previous=-1;
 for(;;){
  uint32_t delta,create,end=0,index;size_t begin=w->reader.cursor;failure->ordinal=c->count;failure->index=0;
  status=coh_rep_pack(&w->reader,1,&delta);if(status!=COH_OK)return refuse(failure,status,w->reader.cursor);
  index=(uint32_t)previous+delta+UINT32_C(1);probe=w->reader;
  status=coh_rep_read(&probe,1,&create);if(status!=COH_OK)return refuse(failure,status,probe.cursor);if(create>1)return refuse(failure,COH_INVALID,probe.cursor);
  if(create){status=coh_rep_read(&probe,1,&end);if(status!=COH_OK)return refuse(failure,status,probe.cursor);if(end>1)return refuse(failure,COH_INVALID,probe.cursor);}
  if(end){
   if(delta)return refuse(failure,COH_INVALID,probe.cursor);
   if(!c->unique_selected_self)return refuse(failure,COH_STATE,probe.cursor);
   c->end_bit=probe.cursor;c->raw_list_validated=1;memcpy(entries,w->entries,c->count*sizeof(*entries));*out=*c;*reader=probe;memset(failure,0,sizeof(*failure));return COH_OK;
  }
  failure->index=index;
  if(!index||index>COH_ENT_INDEX_MAX)return refuse(failure,COH_LIMIT,w->reader.cursor);
  if(c->count>=capacity)return refuse(failure,COH_LIMIT,w->reader.cursor);
  for(unsigned i=0;i<c->count;i++)if(w->entries[i].index==index)return refuse(failure,COH_INVALID,w->reader.cursor);
  w->context.entity_index=index;coh_ent_slot_init(&w->prior,index);
  status=coh_initial_record_read(&w->reader,&w->context,&w->prior,&w->adapter,&w->record,&w->record_workspace,&failure->record,budget,child_extra);
  if(status!=COH_OK)return refuse(failure,status,failure->record.bit);
  const CohEntCreate*identity=&w->record.core.identity;
  for(unsigned i=0;i<c->count;i++)if(w->entries[i].entity_id==identity->entity_id||(identity->dbid&&w->entries[i].dbid==identity->dbid))return refuse(failure,COH_STATE,w->reader.cursor);
  if(identity->is_self){if(c->unique_selected_self)return refuse(failure,COH_STATE,w->reader.cursor);c->unique_selected_self=1;c->self_index=index;c->selected_record=w->record;}
  CohInitialListEntry*entry=&w->entries[c->count];memset(entry,0,sizeof(*entry));entry->index=index;entry->entity_id=identity->entity_id;entry->dbid=identity->dbid;entry->type=identity->type;entry->is_self=identity->is_self;entry->rare_flags=w->record.core.rare|(w->record.core.medium_rare<<1)|(w->record.core.very_rare<<2);entry->begin_bit=begin;entry->end_bit=w->reader.cursor;entry->position=w->record.selected.position.position;entry->position_valid=w->record.selected.position.valid;memcpy(entry->quaternion,w->record.selected.orientation.quaternion,sizeof(entry->quaternion));entry->orientation_valid=w->record.selected.orientation.valid;
  c->count++;previous=(int32_t)index;
 }
}
