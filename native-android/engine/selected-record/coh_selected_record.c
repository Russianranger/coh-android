#include "coh_record_kernel.h"
#include "../entities/coh_taskforce.h"
#include "../entities/coh_very_rare_tail.h"
#include "../entities/coh_teammate_buffs.h"
#include <math.h>
#include <string.h>
typedef struct{CohEntCostumeEnvelope out;CohEntCostumeEnvelopeWorkspace work;}CostumeLoan;
typedef struct{CohEntPowerCustomEnvelope out;CohEntPowerCustomWorkspace work;}PowerLoan;
typedef struct{CohEntTaskforce out;CohEntTaskforceWorkspace work;}TaskforceLoan;
typedef struct{CohEntVeryRareTail out;CohEntVeryRareTailWorkspace work;}TailLoan;
typedef struct{CohEntTeammateBuffs out;CohEntTeammateBuffsWorkspace work;}BuffLoan;
typedef union{long double number;void*pointer;}Alignment;
typedef struct{CohRepReader r;CohStatus status;}Reader;
static uint32_t scalar(Reader*p,unsigned width){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,width,&v);if(p->status==COH_OK&&width<32&&v>=(1u<<width))p->status=COH_INVALID;return v;}
static uint32_t flag(Reader*p){return scalar(p,1);}
static uint32_t pack(Reader*p,unsigned width){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,width,&v);return v;}
static uint32_t opt_pack(Reader*p,unsigned width){return flag(p)?pack(p,width):0;}
static uint32_t opt_bits(Reader*p,unsigned width){return flag(p)?scalar(p,width):0;}
static uint32_t automatic(Reader*p){static const unsigned widths[]={2,10,24,32};uint32_t n=scalar(p,2);return p->status==COH_OK?scalar(p,widths[n]):0;}
static void require(Reader*p,int valid,CohStatus error){if(p->status==COH_OK&&!valid)p->status=error;}
static void optional_anim(Reader*p){if(flag(p)&&flag(p)){for(unsigned i=0;i<1000;i++){if(!scalar(p,8))return;if(p->status!=COH_OK)return;}require(p,0,COH_LIMIT);}}
static int nonzero(const uint8_t*p){uint8_t v=0;for(unsigned i=0;i<32;i++)v|=p[i];return v!=0;}
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(!a||!b||an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
size_t coh_selected_record_stage_bytes(CohSelectedRecordStage stage){switch(stage){case COH_RECORD_COSTUME:return sizeof(CostumeLoan);case COH_RECORD_POWER_CUSTOM:return sizeof(PowerLoan);case COH_RECORD_TASKFORCE:return sizeof(TaskforceLoan);case COH_RECORD_RARE_TAIL:return sizeof(TailLoan);case COH_RECORD_TEAMMATE:return sizeof(BuffLoan);default:return 0;}}
static void pose(Reader*p,CohEntSlot*s,uint32_t id){
 p->status=coh_rep_position(&p->r,id,&s->position);if(p->status==COH_OK)p->status=coh_ent_orientation(&p->r,id,&s->orientation,NULL);
}
CohStatus coh_record_kernel_read(CohRepReader*reader,const CohSelectedRecordContext*context,
 const CohEntSlot*prior,const CohSelectedRecordMemory*memory,CohSelectedRecord*out,
 CohSelectedRecordWorkspace*workspace,CohSelectedRecordFailure*failure,size_t budget,size_t retained,unsigned profile){
 if((profile!=COH_RECORD_PROFILE_SELECTED&&profile!=COH_RECORD_PROFILE_INITIAL_CREATE)||!reader||!context||!prior||!memory||!out||!workspace||!failure||!memory->acquire||!memory->release||(!memory->context&&memory->context_bytes)||(memory->context&&!memory->context_bytes)||!budget||budget>COH_SELECTED_RECORD_RAM_MAX)return COH_INVALID;
 Reader p={*reader,COH_OK};uint32_t ignored;CohStatus check=coh_rep_read(&p.r,0,&ignored);if(check!=COH_OK)return check;
 size_t dict_bytes=0;
 const void*objects[]={reader,context,prior,memory,out,workspace,failure,p.r.bytes.data,memory->context,context->costume_dictionary};
 size_t sizes[]={sizeof(*reader),sizeof(*context),sizeof(*prior),sizeof(*memory),sizeof(*out),sizeof(*workspace),sizeof(*failure),p.r.bytes.size,memory->context_bytes,dict_bytes};
 for(unsigned i=0;i<9;i++){if(sizes[i]&&(!objects[i]||sizes[i]>UINTPTR_MAX-(uintptr_t)objects[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;}
 if(context->costume_dictionary){
  if(!nonzero(context->expected_dictionary_sha256))return COH_STATE;
  /* Refuse obvious fake/aliased opaque handles before invoking its getter. */
  for(unsigned i=0;i<9;i++)if(overlap(context->costume_dictionary,1,objects[i],sizes[i]))return COH_INVALID;
  dict_bytes=coh_ent_costume_dictionary_bytes(context->costume_dictionary);if(!dict_bytes||dict_bytes>COH_COSTUME_DICTIONARY_BYTES_MAX||dict_bytes>UINTPTR_MAX-(uintptr_t)context->costume_dictionary)return COH_INVALID;sizes[9]=dict_bytes;
  for(unsigned i=0;i<9;i++)if(overlap(context->costume_dictionary,dict_bytes,objects[i],sizes[i]))return COH_INVALID;
 }
 memset(failure,0,sizeof(*failure));failure->stage=COH_RECORD_CREATE;failure->bit=p.r.cursor;
 if(!context->selected_dbid||context->selected_dbid>INT32_MAX||!context->packet_id||!context->dictionary_generation||context->interp_level>3||!context->entity_index||context->entity_index>COH_ENT_INDEX_MAX||prior->index!=context->entity_index||prior->present>1){failure->status=COH_INVALID;return COH_INVALID;}
 size_t base=COH_SELECTED_RECORD_STACK_RESERVE;
 for(unsigned i=0;i<10;i++){if(sizes[i]>budget||base>budget-sizes[i]){failure->status=COH_LIMIT;return COH_LIMIT;}base+=sizes[i];}
 if(retained>budget-base){failure->status=COH_LIMIT;return COH_LIMIT;}base+=retained;
 CohSelectedRecord*c=&workspace->candidate;memset(c,0,sizeof(*c));c->packet=p.r.bytes;c->packet_bits=p.r.bits;c->begin_bit=p.r.cursor;c->packet_lease_token=context->packet_lease_token;c->packet_id=context->packet_id;c->dictionary_generation=context->dictionary_generation;memcpy(c->dictionary_manifest_sha256,context->expected_dictionary_sha256,32);c->selected=*prior;
 for(unsigned ordinal=1;ordinal<=COH_SELECTED_RECORD_STAGES;ordinal++){
  CohSelectedRecordStage stage=(CohSelectedRecordStage)ordinal;CohSelectedRecordSpan*span=&c->stages[ordinal-1];span->begin_bit=p.r.cursor;failure->stage=stage;failure->bit=p.r.cursor;
  int present=1;if(stage==COH_RECORD_TRIGGERS||stage==COH_RECORD_COSTUME)present=c->core.medium_rare!=0;else if(stage==COH_RECORD_POWER_CUSTOM||stage==COH_RECORD_TITLES||stage==COH_RECORD_RARE_PREFIX||stage==COH_RECORD_RARE_TAIL||stage==COH_RECORD_TASKFORCE)present=c->core.very_rare!=0;
  if(stage==COH_RECORD_TASKFORCE&&!c->core.identity.is_self)present=0;
  size_t required=present?coh_selected_record_stage_bytes(stage):0;CohSelectedRecordLoan loan={0};size_t occupied=base,limit=budget;
  if(stage==COH_RECORD_RARE_TAIL&&limit>COH_ENT_TAIL_AGGREGATE_MAX)limit=COH_ENT_TAIL_AGGREGATE_MAX;
  if(stage==COH_RECORD_TEAMMATE&&limit>COH_ENT_BUFF_AGGREGATE_MAX)limit=COH_ENT_BUFF_AGGREGATE_MAX;
  if(required){
   if(base>limit||required>limit-base){p.status=COH_LIMIT;goto refused;}
   size_t allowance=limit-base;p.status=memory->acquire(memory->context,required,allowance,&loan);
   if(p.status!=COH_OK){if(loan.data||loan.bytes||loan.charged_bytes)memory->release(memory->context,&loan);goto refused;}
   if(!loan.data||loan.bytes<required||loan.charged_bytes<loan.bytes||(uintptr_t)loan.data%sizeof(Alignment))p.status=COH_INVALID;
   for(unsigned i=0;i<10&&p.status==COH_OK;i++)if(overlap(loan.data,loan.bytes,objects[i],sizes[i]))p.status=COH_INVALID;
   if(p.status==COH_OK&&(overlap(loan.data,loan.bytes,&p,sizeof(p))||overlap(loan.data,loan.bytes,&loan,sizeof(loan))))p.status=COH_INVALID;
   if(p.status==COH_OK&&loan.charged_bytes>allowance)p.status=COH_LIMIT;
   if(p.status!=COH_OK){memory->release(memory->context,&loan);goto refused;}occupied=base+loan.charged_bytes;
  }
  if(present)switch(stage){
  case COH_RECORD_CREATE:{
   p.status=coh_ent_create(&p.r,context->selected_dbid,&c->core.identity,&failure->entity);if(p.status!=COH_OK)break;
   require(&p,!c->core.identity.end&&c->core.identity.create&&(!(profile&COH_RECORD_PROFILE_SELECTED)||c->core.identity.is_self),COH_UNSUPPORTED);
   require(&p,!(prior->present&&context->packet_id<=prior->create_packet)&&context->packet_id>=prior->delete_packet,COH_STATE);if(p.status!=COH_OK)break;
   coh_ent_slot_init(&c->selected,context->entity_index);c->selected.identity=c->core.identity;c->selected.present=1;c->selected.create_packet=context->packet_id;c->selected.delete_packet=prior->delete_packet;c->selected.deleted_entity_id=prior->deleted_entity_id;c->selected_wire_dbid_matched=c->core.identity.is_self;
   c->core.rare=flag(&p);if(c->core.rare){c->core.medium_rare=flag(&p);c->core.very_rare=flag(&p);}
   if(profile&COH_RECORD_PROFILE_INITIAL_CREATE)require(&p,c->core.rare&&c->core.medium_rare&&c->core.very_rare,COH_UNSUPPORTED);
   span->observations[0]=c->core.identity.entity_id;span->observations[1]=c->core.identity.dbid;span->observations[2]=c->core.rare;span->observations[3]=c->core.medium_rare;span->observations[4]=c->core.very_rare;break;}
  case COH_RECORD_POSE_SEQUENCE:{
   if(c->core.medium_rare&&flag(&p)){c->selected.state_mode=opt_pack(&p,3);c->selected.state_packet=context->packet_id;}
   if(p.status==COH_OK)pose(&p,&c->selected,context->packet_id);
   if(c->core.rare&&flag(&p)){c->selected.sequence_index=opt_pack(&p,8);c->selected.sequence_ticks=opt_pack(&p,4);c->selected.sequence_bits=opt_bits(&p,11);require(&p,c->selected.sequence_index<=INT32_MAX&&c->selected.sequence_ticks<=65535,COH_LIMIT);c->selected.sequence_packet=context->packet_id;}
   if(profile&COH_RECORD_PROFILE_INITIAL_CREATE){require(&p,c->selected.state_packet==context->packet_id&&c->selected.position.valid&&c->selected.orientation.valid==7&&c->selected.sequence_packet==context->packet_id,COH_UNSUPPORTED);for(unsigned j=0;j<24;j++)require(&p,c->selected.position.packet_ids[j]==context->packet_id,COH_UNSUPPORTED);for(unsigned j=0;j<3;j++)require(&p,c->selected.orientation.packet_ids[j]==context->packet_id,COH_UNSUPPORTED);}break;}
  case COH_RECORD_TRIGGERS:
   c->core.trigger_count=pack(&p,1);require(&p,c->core.trigger_count<=COH_ENT_TRIGGER_MAX,COH_LIMIT);
   for(unsigned i=0;i<c->core.trigger_count&&p.status==COH_OK;i++){CohEntTrigger*t=&c->core.triggers[i];t->index=pack(&p,10);t->ticks=pack(&p,6);t->fx_id=opt_pack(&p,16);require(&p,t->index<=INT32_MAX&&t->ticks<=INT32_MAX,COH_LIMIT);}optional_anim(&p);span->observations[0]=c->core.trigger_count;break;
  case COH_RECORD_NETFX:{c->core.pchar_things=flag(&p);uint32_t has=flag(&p);if(has&&c->core.pchar_things&&p.status==COH_OK)p.status=coh_ent_netfx(&p.r,&c->core.netfx,&failure->entity);span->observations[0]=c->core.pchar_things;span->observations[1]=c->core.netfx.count;break;}
  case COH_RECORD_COSTUME:{CostumeLoan*v=loan.data;p.status=coh_ent_costume_envelope(&p.r,context->costume_dictionary,context->dictionary_generation,c->core.identity.is_self,&v->work,&v->out,&failure->entity);if(p.status==COH_OK&&memcmp(v->out.manifest_sha256,context->expected_dictionary_sha256,32))p.status=COH_STATE;if(p.status==COH_OK){c->dictionary_manifest_matched=1;c->core.appearance_type=v->out.type;c->selected.appearance.type=v->out.type;c->selected.appearance.packet_id=context->packet_id;c->selected.appearance.translucency=opt_bits(&p,8);c->selected.appearance.translucency_packet=context->packet_id;span->observations[0]=v->out.type;span->observations[1]=v->out.body_count;span->observations[2]=v->out.deferred;span->observations[3]=v->out.npc_present;span->observations[4]=v->out.custom_present;span->observations[5]=v->out.super_present;}break;}
  case COH_RECORD_POWER_CUSTOM:{PowerLoan*v=loan.data;p.status=coh_ent_power_custom(&p.r,c->core.identity.is_self,&v->work,&v->out,&failure->entity);if(p.status==COH_OK){span->observations[0]=v->out.type;span->observations[1]=v->out.list_count;span->observations[2]=v->out.item_count;span->observations[3]=v->out.multiple;}break;}
  case COH_RECORD_TITLES:p.status=coh_ent_titles(&p.r,context->packet_id,&c->titles,&failure->entity);span->observations[0]=c->titles.valid;break;
  case COH_RECORD_RAGDOLL:c->core.ragdoll_bones=opt_bits(&p,5);for(unsigned i=0;i<c->core.ragdoll_bones*3&&p.status==COH_OK;i++)(void)scalar(&p,10);span->observations[0]=c->core.ragdoll_bones;break;
  case COH_RECORD_COMMON:{
   if(c->core.pchar_things&&flag(&p)&&flag(&p)&&p.status==COH_OK)p.status=coh_ent_character_stats(&p.r,context->packet_id,0,&c->selected.stats,&failure->entity);
   c->selected.vision_phases=automatic(&p);c->selected.exclusive_vision_phase=automatic(&p);c->selected.con_yellow=automatic(&p);
   if(c->core.pchar_things){c->selected.combat_mod_shift=automatic(&p);if(p.status==COH_OK)p.status=coh_ent_target(&p.r,context->packet_id,c->core.identity.is_self,&c->selected.target,&failure->entity);if(flag(&p)&&p.status==COH_OK)p.status=coh_ent_status_effects(&p.r,context->packet_id,&c->selected.status_effects,&failure->entity);if(c->core.identity.is_self&&p.status==COH_OK)p.status=coh_ent_inventory_sizes(&p.r,&c->selected.inventory,&failure->entity);}break;}
  case COH_RECORD_TASKFORCE:{TaskforceLoan*v=loan.data;p.status=coh_ent_taskforce(&p.r,context->costume_dictionary,context->dictionary_generation,&v->work,&v->out,&failure->entity);if(p.status==COH_OK&&v->out.costume_body&&memcmp(v->out.costume.manifest_sha256,context->expected_dictionary_sha256,32))p.status=COH_STATE;if(p.status==COH_OK){if(v->out.costume_body)c->dictionary_manifest_matched=1;span->observations[0]=v->out.architect_update;span->observations[1]=v->out.on_architect;span->observations[2]=v->out.costume_body;span->observations[3]=v->out.custom_body;span->observations[4]=v->out.review_present;span->observations[5]=v->out.parameter_update;}break;}
  case COH_RECORD_RARE_PREFIX:p.status=coh_ent_rare_prefix(&p.r,&c->rare_prefix,&failure->entity);break;
  case COH_RECORD_RARE_TAIL:{TailLoan*v=loan.data;size_t extra=occupied-p.r.bytes.size-sizeof(v->out)-sizeof(v->work)-COH_ENT_TAIL_STACK_RESERVE;p.status=coh_ent_very_rare_tail(&p.r,&v->out,&v->work,extra,limit);if(p.status==COH_OK){span->observations[0]=v->out.supergroup_update;span->observations[1]=v->out.pact_update;span->observations[2]=v->out.logout_update;span->observations[3]=v->out.token_count;span->observations[4]=v->out.recipe_count;span->observations[5]=v->out.detail_count;}break;}
  case COH_RECORD_TEAMMATE:{BuffLoan*v=loan.data;size_t extra=occupied-p.r.bytes.size-sizeof(v->out)-sizeof(v->work)-COH_ENT_BUFF_STACK_RESERVE;p.status=coh_ent_teammate_buffs(&p.r,&v->out,&v->work,extra,limit);if(p.status==COH_OK){span->observations[0]=v->out.teammate;span->observations[1]=v->out.buffs_present;span->observations[2]=v->out.count;span->observations[3]=v->out.mods_count;span->observations[4]=v->out.diffs_only;span->observations[5]=v->out.not_getting_buffs;}break;}
  default:p.status=COH_INVALID;break;
  }
  if(required)memory->release(memory->context,&loan);
  if(p.status!=COH_OK)goto refused;
  span->end_bit=p.r.cursor;c->stage_count=ordinal;failure->validated_stages=ordinal;
 }
 c->core.end_bit=c->end_bit=p.r.cursor;c->raw_record_validated=1;*out=*c;*reader=p.r;memset(failure,0,sizeof(*failure));return COH_OK;
refused:failure->status=p.status;failure->bit=p.r.cursor;return p.status;
}

/* Preserve the original constrained public selected-only profile. */
CohStatus coh_selected_record_read(CohRepReader*r,const CohSelectedRecordContext*c,
 const CohEntSlot*p,const CohSelectedRecordMemory*m,CohSelectedRecord*out,
 CohSelectedRecordWorkspace*w,CohSelectedRecordFailure*f,size_t budget,size_t retained){
 return coh_record_kernel_read(r,c,p,m,out,w,f,budget,retained,COH_RECORD_PROFILE_SELECTED);
}
