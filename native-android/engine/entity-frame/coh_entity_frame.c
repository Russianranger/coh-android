#include "coh_entity_frame.h"
#include <limits.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static CohStatus refusal(CohEntityFrameFailure*f,CohStatus s,CohEntityFrameStage stage,size_t bit){f->status=s;f->stage=stage;f->bit=bit;return s;}
CohStatus coh_entity_frame_read(CohRepReader*reader,const CohEntityFrameContext*context,
 const CohRepSchema*schema,const uint32_t*indices,size_t count,CohEntityFrame*out,
 CohEntityFrameWorkspace*workspace,CohEntityFrameFailure*failure,size_t budget,size_t retained){
 CohRepReader r;CohStatus status;uint32_t ignored,command;size_t fixed;
 if(!reader||!context||!schema||!indices||!count||count>COH_ENT_LIST_MAX||!out||!workspace||!failure||!budget||budget>COH_ENTITY_FRAME_RAM_MAX)return COH_INVALID;
 r=*reader;status=coh_rep_read(&r,0,&ignored);if(status!=COH_OK)return status;
 const void*objects[]={reader,context,schema,indices,out,workspace,failure,r.bytes.data};
 const size_t sizes[]={sizeof(*reader),sizeof(*context),sizeof(*schema),count*sizeof(*indices),sizeof(*out),sizeof(*workspace),sizeof(*failure),r.bytes.size};
 for(unsigned i=0;i<8;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 memset(failure,0,sizeof(*failure));
 if(!context->selected_dbid||context->selected_dbid>INT32_MAX||!context->packet_id||!context->session_generation||context->session_generation!=context->schema_generation||context->legacy_commands>1||schema->count>COH_REP_SHORTCUT_MAX)return refusal(failure,COH_INVALID,COH_FRAME_HEADER,r.cursor);
 fixed=sizeof(*reader)+sizeof(*context)+sizeof(*schema)+count*sizeof(*indices)+sizeof(*out)+sizeof(*workspace)+sizeof(*failure)+COH_ENTITY_FRAME_STACK_RESERVE;
 if(fixed>budget||r.bytes.size>budget-fixed||retained>budget-fixed-r.bytes.size)return refusal(failure,COH_LIMIT,COH_FRAME_HEADER,r.cursor);
 for(size_t i=0;i<schema->count;i++){if(!schema->entries[i].id||schema->entries[i].kind>10)return refusal(failure,COH_INVALID,COH_FRAME_HEADER,r.cursor);for(size_t j=0;j<i;j++)if(schema->entries[i].id==schema->entries[j].id)return refusal(failure,COH_INVALID,COH_FRAME_HEADER,r.cursor);}
 for(size_t i=0;i<count;i++){if(!indices[i]||indices[i]>COH_ENT_INDEX_MAX)return refusal(failure,COH_INVALID,COH_FRAME_LIST,r.cursor);for(size_t j=0;j<i;j++)if(indices[j]==indices[i])return refusal(failure,COH_INVALID,COH_FRAME_LIST,r.cursor);coh_ent_slot_init(&workspace->slots[i],indices[i]);}
 CohEntityFrame*v=&workspace->candidate;memset(v,0,sizeof(*v));v->packet=r.bytes;v->packet_bits=r.bits;v->begin_bit=r.cursor;v->packet_lease_token=context->packet_lease_token;v->packet_id=context->packet_id;v->session_generation=context->session_generation;
 status=coh_rep_pack(&r,1,&command);if(status!=COH_OK)return refusal(failure,status,COH_FRAME_COMMAND,r.cursor);
 if(context->legacy_commands){if(command<7)return refusal(failure,COH_UNSUPPORTED,COH_FRAME_COMMAND,r.cursor);command-=5;}
 if(command!=COH_REP_ALLENTS)return refusal(failure,COH_UNSUPPORTED,COH_FRAME_COMMAND,r.cursor);
 status=coh_rep_update_prefix(&r,schema,command,&v->header);if(status!=COH_OK)return refusal(failure,status,COH_FRAME_HEADER,r.cursor);
 if(!v->header.odd_send)return refusal(failure,COH_INVALID,COH_FRAME_HEADER,r.cursor);
 if(v->header.has_debug_info)return refusal(failure,COH_UNSUPPORTED,COH_FRAME_HEADER,r.cursor);
 v->header_end_bit=r.cursor;
 status=coh_ent_list(&r,context->selected_dbid,context->packet_id,v->header.interp_level,workspace->slots,count,&workspace->list,&v->list,&failure->entity);if(status!=COH_OK)return refusal(failure,status,COH_FRAME_LIST,r.cursor);v->list_end_bit=r.cursor;
 if(!v->list.self_index||v->list.self_dbid!=context->selected_dbid)return refusal(failure,COH_STATE,COH_FRAME_SELECTED,r.cursor);
 /* Source receiveGlobalEntDebugInfo has no wire reads when hasEntDebugInfo0;
  * per-entity debug list is also conditional on the same parsed header bit. */
 status=coh_control_read(&r,&v->control,&failure->control);if(status!=COH_OK)return refusal(failure,status,COH_FRAME_CONTROL,r.cursor);v->control_end_bit=r.cursor;
 status=coh_ent_deletes(&r,&v->deletes,&failure->entity);if(status!=COH_OK)return refusal(failure,status,COH_FRAME_DELETES,r.cursor);
 status=coh_ent_stage_deletes(workspace->slots,count,&v->deletes,context->packet_id);if(status!=COH_OK)return refusal(failure,status,COH_FRAME_DELETES,r.cursor);
 size_t self=count;for(size_t i=0;i<count;i++)if(workspace->slots[i].index==v->list.self_index)self=i;
 if(self==count||!workspace->slots[self].present||!workspace->slots[self].identity.is_self||workspace->slots[self].identity.dbid!=context->selected_dbid||workspace->slots[self].identity.entity_id!=v->list.self_entity_id||!workspace->slots[self].position.valid)return refusal(failure,COH_STATE,COH_FRAME_SELECTED,r.cursor);
 v->selected=workspace->slots[self];v->selected_wire_identity_matched=1;v->end_bit=r.cursor;*out=*v;*reader=r;memset(failure,0,sizeof(*failure));return COH_OK;
}
