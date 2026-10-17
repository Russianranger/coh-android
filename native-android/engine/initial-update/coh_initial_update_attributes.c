#include "coh_initial_update_attributes.h"
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(!a||!b||an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static CohStatus acquire(void*opaque,size_t minimum,size_t maximum,CohSelectedRecordLoan*loan){CohInitialUpdateAttributesAllocator*a=opaque;CohStatus s=a->original->acquire(a->original->context,minimum,maximum,loan);if(s!=COH_OK)return s;for(unsigned i=0;i<13;i++)if(overlap(loan->data,loan->bytes,a->spans[i].pointer,a->spans[i].bytes))return COH_INVALID;return COH_OK;}
static void release(void*opaque,CohSelectedRecordLoan*loan){CohInitialUpdateAttributesAllocator*a=opaque;a->original->release(a->original->context,loan);}
static CohStatus suffix_acquire(void*opaque,size_t minimum,size_t maximum,CohSuffixLoan*loan){CohSelectedRecordLoan raw={0};CohStatus s=acquire(opaque,minimum,maximum,&raw);loan->data=raw.data;loan->bytes=raw.bytes;loan->charged_bytes=raw.charged_bytes;return s;}
static void suffix_release(void*opaque,CohSuffixLoan*loan){CohSelectedRecordLoan raw={loan->data,loan->bytes,loan->charged_bytes};release(opaque,&raw);memset(loan,0,sizeof(*loan));}
static CohStatus refused(CohInitialUpdateReport*f,CohStatus s,size_t bit){f->status=s;f->bit=bit;return s;}
/* Original SERVER_GAME_CMDS=15 and SERVER_BEGIN_BYTE_ALIGNED_DATA=197;
 * Common/comm_game.h starts enum at COMM_MAX_CMD=2. No body for either marker.
 * Original bsAlignByte READ ignores padding values; only advance is bounded.
 * entServerSendPackets appends Pack1 zero, not rounded-byte implicit padding. */
static CohStatus command_tail(CohRepReader*r,CohInitialUpdateReport*f){
 for(unsigned i=0;i<256;i++){
  uint32_t command;CohStatus s=coh_rep_pack(r,1,&command);if(s!=COH_OK)return s;
  if(!command){if(r->cursor!=r->bits)return COH_INVALID;f->validated.transport_end_verified=1;return COH_OK;}
  f->validated.command_count++;
  if(command==15)continue;
  if(command==197){size_t padding=(8-(r->cursor&7))&7;if(padding>r->bits-r->cursor)return COH_INVALID;r->cursor+=padding;continue;}
  f->refused_command=command;return COH_UNSUPPORTED;
 }
 return COH_LIMIT;
}
CohStatus coh_initial_update_attributes_diagnostic(CohRepReader*reader,const CohInitialUpdateAttributesContext*profile,
 const CohRepSchema*schema,const CohSelectedRecordMemory*memory,CohInitialUpdateAttributesWorkspace*w,
 CohInitialUpdateReport*f,size_t budget,size_t retained){
 if(!profile)return COH_INVALID;
 const CohInitialUpdateContext*context=&profile->base;
 if(!reader||!context||!schema||!memory||!memory->acquire||!memory->release||!w||!f||!budget||budget>COH_SELECTED_RECORD_RAM_MAX||(!memory->context&&memory->context_bytes)||(memory->context&&!memory->context_bytes))return COH_INVALID;
 CohRepReader probe=*reader;uint32_t ignored,command;CohStatus s=coh_rep_read(&probe,0,&ignored);if(s!=COH_OK)return s;
 CohInitialUpdateSpan spans[13]={{reader,sizeof(*reader)},{profile,sizeof(*profile)},{schema,sizeof(*schema)},{memory,sizeof(*memory)},{w,sizeof(*w)},{f,sizeof(*f)},{probe.bytes.data,probe.bytes.size},{memory->context,memory->context_bytes},{context->record.costume_dictionary,0},{profile->attribute_schema,profile->attribute_schema?sizeof(*profile->attribute_schema):0},{NULL,0},{profile->attribute_control,profile->attribute_control?sizeof(*profile->attribute_control):0},{NULL,0}};
 for(unsigned i=0;i<13;i++){if(spans[i].bytes&&(!spans[i].pointer||spans[i].bytes>UINTPTR_MAX-(uintptr_t)spans[i].pointer))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i].pointer,spans[i].bytes,spans[j].pointer,spans[j].bytes))return COH_INVALID;}
 if(profile->attribute_schema){spans[10]=(CohInitialUpdateSpan){profile->attribute_schema->input.data,profile->attribute_schema->input.size};if(!spans[10].pointer||!spans[10].bytes||spans[10].bytes>COH_ATTRIBUTE_DICTIONARY_INPUT_MAX)return COH_INVALID;}
 size_t control_scratch=0;
 if(profile->attribute_control){const CohAttribReadControl*c=profile->attribute_control;spans[12]=(CohInitialUpdateSpan){c->cancel.context,c->context_bytes};control_scratch=c->scratch_reserve;if((!c->cancel.context&&c->context_bytes)||(c->cancel.context&&!c->context_bytes)||(!c->cancel.poll&&(c->cancel.context||c->context_bytes||c->scratch_reserve)))return COH_INVALID;}
 if(context->record.costume_dictionary){for(unsigned i=0;i<13;i++)if(i!=8&&overlap(spans[8].pointer,1,spans[i].pointer,spans[i].bytes))return COH_INVALID;spans[8].bytes=coh_ent_costume_dictionary_bytes(context->record.costume_dictionary);if(!spans[8].bytes||spans[8].bytes>COH_COSTUME_DICTIONARY_BYTES_MAX)return COH_INVALID;}
 for(unsigned i=0;i<13;i++){if(spans[i].bytes&&(!spans[i].pointer||spans[i].bytes>UINTPTR_MAX-(uintptr_t)spans[i].pointer))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i].pointer,spans[i].bytes,spans[j].pointer,spans[j].bytes))return COH_INVALID;}
 memset(f,0,sizeof(*f));f->stage=COH_INITIAL_HEADER;f->bit=probe.cursor;
 if(context->record.entity_index||!context->record.selected_dbid||context->record.selected_dbid>INT32_MAX||!context->record.packet_id||!context->record.packet_lease_token||!context->session_generation||context->session_generation!=context->schema_generation||context->legacy_commands>1||schema->count>COH_REP_SHORTCUT_MAX)return refused(f,COH_INVALID,probe.cursor);
 for(size_t i=0;i<schema->count;i++){if(!schema->entries[i].id||schema->entries[i].kind>10)return refused(f,COH_INVALID,probe.cursor);for(size_t j=0;j<i;j++)if(schema->entries[i].id==schema->entries[j].id)return refused(f,COH_INVALID,probe.cursor);}
 size_t occupied=COH_INITIAL_UPDATE_STACK_RESERVE;
 for(unsigned i=0;i<13;i++){if(spans[i].bytes>budget||occupied>budget-spans[i].bytes)return refused(f,COH_LIMIT,probe.cursor);occupied+=spans[i].bytes;}
 if(retained>budget-occupied)return refused(f,COH_LIMIT,probe.cursor);
 occupied+=retained;
 if(control_scratch>budget-occupied)return refused(f,COH_LIMIT,probe.cursor);
 occupied+=control_scratch;
 w->reader=probe;w->allocator.original=memory;memcpy(w->allocator.spans,spans,sizeof(spans));w->record_memory=(CohSelectedRecordMemory){&w->allocator,sizeof(w->allocator),acquire,release};w->suffix_memory=(CohSuffixMemory){&w->allocator,sizeof(w->allocator),suffix_acquire,suffix_release};
 CohInitialUpdateDiagnostic*c=&f->validated;c->packet=probe.bytes;c->packet_bits=probe.bits;c->begin_bit=probe.cursor;c->packet_id=context->record.packet_id;c->session_generation=context->session_generation;c->packet_lease_token=context->record.packet_lease_token;
 f->stage=COH_INITIAL_COMMAND;s=coh_rep_pack(&w->reader,1,&command);if(s!=COH_OK)return refused(f,s,w->reader.cursor);
 if(context->legacy_commands){if(command<7)return refused(f,COH_UNSUPPORTED,w->reader.cursor);command-=5;}if(command!=COH_REP_ALLENTS)return refused(f,COH_UNSUPPORTED,w->reader.cursor);
 f->stage=COH_INITIAL_HEADER;s=coh_rep_update_prefix(&w->reader,schema,command,&c->header);if(s!=COH_OK)return refused(f,s,w->reader.cursor);if(!c->header.odd_send)return refused(f,COH_INVALID,w->reader.cursor);if(c->header.has_debug_info)return refused(f,COH_UNSUPPORTED,w->reader.cursor);c->header_end_bit=w->reader.cursor;
 w->record_context=context->record;w->record_context.interp_level=c->header.interp_level;
 size_t list_fixed=COH_INITIAL_LIST_STACK_RESERVE+sizeof(w->reader)+sizeof(w->record_context)+sizeof(w->record_memory)+sizeof(w->entries)+sizeof(c->list)+sizeof(w->list_workspace)+sizeof(f->list)+probe.bytes.size+sizeof(w->allocator)+spans[8].bytes;
 if(list_fixed>occupied)return refused(f,COH_INVALID,w->reader.cursor);
 f->stage=COH_INITIAL_LIST;s=coh_initial_list_read(&w->reader,&w->record_context,&w->record_memory,w->entries,COH_ENT_LIST_MAX,&c->list,&w->list_workspace,&f->list,budget,occupied-list_fixed);if(s!=COH_OK)return refused(f,s,f->list.bit);c->list_end_bit=w->reader.cursor;
 f->stage=COH_INITIAL_CONTROL;s=coh_control_read(&w->reader,&c->control,&f->control);if(s!=COH_OK)return refused(f,s,f->control.bit);c->control_end_bit=w->reader.cursor;
 f->stage=COH_INITIAL_DELETES;s=coh_ent_deletes(&w->reader,&c->deletes,&f->deletes);if(s!=COH_OK)return refused(f,s,w->reader.cursor);
 for(uint32_t i=0;i<c->deletes.count;i++){uint32_t j;for(j=0;j<c->list.count;j++)if(w->entries[j].index==c->deletes.entries[i].index)break;if(j==c->list.count)return refused(f,COH_NOT_FOUND,w->reader.cursor);}
 c->deletes_end_bit=w->reader.cursor;
 w->suffix_context=(CohSuffixAttributesContext){{1,context->record.packet_id,context->diagnostic_dynamic_count,context->record.packet_lease_token,context->character},profile->attribute_schema,{0},profile->attribute_lease,profile->attribute_control};memcpy(w->suffix_context.expected_attribute_sha256,profile->expected_attribute_sha256,32);
 size_t suffix_fixed=COH_SUFFIX_STACK_RESERVE+sizeof(w->reader)+sizeof(w->suffix_context)+sizeof(w->suffix_memory)+sizeof(w->suffix_output)+sizeof(f->suffix)+probe.bytes.size+sizeof(w->allocator)+spans[9].bytes+spans[10].bytes+spans[11].bytes+spans[12].bytes+control_scratch;
 if(suffix_fixed>occupied)return refused(f,COH_INVALID,w->reader.cursor);
 f->stage=COH_INITIAL_SUFFIX;s=coh_initial_suffix_attributes_diagnostic(&w->reader,&w->suffix_context,&w->suffix_memory,&w->suffix_output,&f->suffix,budget,occupied-suffix_fixed);
 c->suffix=f->suffix.validated;
 if(s!=COH_UNSUPPORTED||!c->suffix.raw_suffix_syntax_validated||c->suffix.stage_count!=COH_SUFFIX_STAGE_COUNT)return refused(f,s,f->suffix.bit);
 /* Preserve child's authority refusal: advance only this scratch reader using
  * its fully validated raw span, then qualify command framing diagnostically. */
 w->reader.cursor=c->suffix.end_bit;c->suffix_end_bit=w->reader.cursor;
 f->stage=COH_INITIAL_COMMAND_TAIL;s=command_tail(&w->reader,f);if(s!=COH_OK)return refused(f,s,w->reader.cursor);
 c->end_bit=w->reader.cursor;c->raw_initial_syntax_validated=1;f->stage=COH_INITIAL_AUTHORITY;
 return refused(f,COH_UNSUPPORTED,w->reader.cursor);
}
