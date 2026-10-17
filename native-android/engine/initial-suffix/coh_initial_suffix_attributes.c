#include "coh_initial_suffix_attributes.h"
#include "../entity-globals/coh_power_info.h"
#include "../entity-globals/coh_entity_globals.h"
#include "../entity-globals/coh_badges.h"
#include "../entity-inventory/coh_inventory_phase.h"
#include "../entity-social/coh_social.h"
#include "../entity-attributes/coh_attrib_monitor.h"
#include "../entity-dynamic/coh_dynamic.h"
#include "../entity-view/coh_view.h"
#include <string.h>
typedef struct{CohCharacterOuter out;CohCharacterOuterWorkspace work;}CharacterLoan;
typedef struct{CohPowerInfoUpdate out;CohPowerInfoWorkspace work;}PowerLoan;
typedef struct{CohPowerModes out;CohPowerModeEvent event;}ModesLoan;
typedef struct{CohBadgeUpdate out;CohBadgeWorkspace work;}BadgesLoan;
typedef struct{CohBadgeMonitor out;}MonitorLoan;
typedef struct{CohInventoryPhase out;CohInventoryPhaseWorkspace work;}InventoryLoan;
typedef struct{CohSocialPhase out;CohSocialWorkspace work;}SocialLoan;
typedef struct{CohAttribDescription out;CohAttribDescriptionWorkspace work;}AttributesLoan;
typedef struct{CohDynamicDiagnostic out;CohDynamicWorkspace work;}DynamicLoan;
typedef struct{CohWorldView out;CohWorldViewWorkspace work;}ViewLoan;
typedef union{long double ld;void*pointer;}LoanAlignment;
size_t coh_initial_suffix_attributes_stage_bytes(CohSuffixStage stage){
 return stage==COH_SUFFIX_ATTRIBUTES?sizeof(AttributesLoan):coh_initial_suffix_stage_bytes(stage);
}
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static CohStatus boolean(CohRepReader*r,uint32_t*out){CohStatus s=coh_rep_read(r,1,out);return s==COH_OK&&*out>1?COH_INVALID:s;}
CohStatus coh_initial_suffix_attributes_diagnostic(CohRepReader*reader,const CohSuffixAttributesContext*profile,
 const CohSuffixMemory*memory,CohSuffixDiagnostic*out,CohSuffixReport*report,size_t budget,size_t retained){
 if(!profile)return COH_INVALID;
 const CohSuffixContext*context=&profile->base;
 CohRepReader r;CohSuffixDiagnostic candidate;CohStatus status;uint32_t ignored;size_t base;
 if(!reader||!context||!memory||!out||!report||!memory->acquire||!memory->release||(!memory->context&&memory->context_bytes)||(memory->context&&!memory->context_bytes)||!budget||budget>COH_SUFFIX_RAM_MAX)return COH_INVALID;
 r=*reader;status=coh_rep_read(&r,0,&ignored);if(status!=COH_OK)return status;
 const void*objects[]={reader,profile,memory,out,report,r.bytes.data,memory->context,profile->attribute_schema,NULL,profile->attribute_control,NULL};
 size_t sizes[]={sizeof(*reader),sizeof(*profile),sizeof(*memory),sizeof(*out),sizeof(*report),r.bytes.size,memory->context_bytes,profile->attribute_schema?sizeof(*profile->attribute_schema):0,0,profile->attribute_control?sizeof(*profile->attribute_control):0,0};
 for(unsigned i=0;i<10;i++){if(sizes[i]&&(!objects[i]||sizes[i]>UINTPTR_MAX-(uintptr_t)objects[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;}
 if(profile->attribute_schema){objects[8]=profile->attribute_schema->input.data;sizes[8]=profile->attribute_schema->input.size;if(!objects[8]||!sizes[8]||sizes[8]>COH_ATTRIBUTE_DICTIONARY_INPUT_MAX)return COH_INVALID;}
 size_t control_scratch=0;
 if(profile->attribute_control){const CohAttribReadControl*c=profile->attribute_control;objects[10]=c->cancel.context;sizes[10]=c->context_bytes;control_scratch=c->scratch_reserve;if((!c->cancel.context&&c->context_bytes)||(c->cancel.context&&!c->context_bytes)||(!c->cancel.poll&&(c->cancel.context||c->context_bytes||c->scratch_reserve)))return COH_INVALID;}
 for(unsigned i=0;i<11;i++){if(sizes[i]&&(!objects[i]||sizes[i]>UINTPTR_MAX-(uintptr_t)objects[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;}
 memset(&candidate,0,sizeof(candidate));candidate.packet=r.bytes;candidate.packet_bits=r.bits;candidate.begin_bit=r.cursor;candidate.end_bit=r.cursor;
 candidate.packet_lease_token=context->packet_lease_token;candidate.packet_id=context->packet_id;candidate.full_update=context->full_update;
 memset(report,0,sizeof(*report));report->validated=candidate;
 if(context->full_update!=1){report->status=COH_UNSUPPORTED;return COH_UNSUPPORTED;}
 base=sizeof(*reader)+sizeof(*profile)+sizeof(*memory)+sizeof(*out)+sizeof(*report)+COH_SUFFIX_STACK_RESERVE;
 if(base>budget||memory->context_bytes>budget-base){report->status=COH_LIMIT;return COH_LIMIT;}base+=memory->context_bytes;
 for(unsigned i=7;i<11;i++){if(sizes[i]>budget-base){report->status=COH_LIMIT;return COH_LIMIT;}base+=sizes[i];}
 if(control_scratch>budget-base){report->status=COH_LIMIT;return COH_LIMIT;}base+=control_scratch;
 if(r.bytes.size>budget-base||retained>budget-base-r.bytes.size){report->status=COH_LIMIT;return COH_LIMIT;}base+=retained;
 for(unsigned ordinal=1;ordinal<=COH_SUFFIX_STAGE_COUNT;ordinal++){
  CohSuffixStage stage=(CohSuffixStage)ordinal;size_t required=coh_initial_suffix_attributes_stage_bytes(stage);CohSuffixLoan loan={0};
  report->stage=stage;report->bit=r.cursor;CohSuffixSpan*span=&candidate.stages[ordinal-1];span->begin_bit=r.cursor;
  size_t stage_limit=stage==COH_SUFFIX_BADGES&&budget>COH_BADGE_AGGREGATE_MAX?COH_BADGE_AGGREGATE_MAX:budget;
  if(stage==COH_SUFFIX_ATTRIBUTES&&stage_limit>COH_ATTRIB_DESCRIPTION_RAM_MAX)stage_limit=COH_ATTRIB_DESCRIPTION_RAM_MAX;
  if(base>stage_limit||r.bytes.size>stage_limit-base||required>stage_limit-base-r.bytes.size){status=COH_LIMIT;goto refused;}
  size_t allowance=stage_limit-base-r.bytes.size;
  status=memory->acquire(memory->context,required,allowance,&loan);
  if(status!=COH_OK){if(loan.data||loan.bytes||loan.charged_bytes)memory->release(memory->context,&loan);goto refused;}
  if(!loan.data||loan.bytes<required||loan.charged_bytes<loan.bytes||(uintptr_t)loan.data%sizeof(LoanAlignment))status=COH_INVALID;
  for(unsigned i=0;i<11&&status==COH_OK;i++)if(overlap(loan.data,loan.bytes,objects[i],sizes[i]))status=COH_INVALID;
  if(status==COH_OK&&(overlap(loan.data,loan.bytes,&r,sizeof(r))||overlap(loan.data,loan.bytes,&candidate,sizeof(candidate))||overlap(loan.data,loan.bytes,&loan,sizeof(loan))))status=COH_INVALID;
  if(status==COH_OK&&loan.charged_bytes>allowance)status=COH_LIMIT;
  if(status!=COH_OK){memory->release(memory->context,&loan);goto refused;}
  size_t occupied=base+loan.charged_bytes;
  switch(stage){
  case COH_SUFFIX_CHARACTER:{CharacterLoan*p=loan.data;size_t extra=occupied-sizeof(p->out)-sizeof(p->work)-COH_CHARACTER_OUTER_STACK_RESERVE;status=coh_character_outer_read(&r,&context->character_profile,context->packet_id,&p->out,&p->work,budget,extra);if(status==COH_OK){CohCharacterData*d=&p->out.creation.initial.character;span->observations[0]=d->build_count;span->observations[1]=d->set_count;span->observations[2]=d->power_count;span->observations[3]=p->out.tail.friend_count;}break;}
  case COH_SUFFIX_POWER_INFO:{PowerLoan*p=loan.data;size_t extra=occupied-sizeof(p->out)-sizeof(p->work)-8192u;status=coh_global_power_info(&r,&p->out,&p->work,extra,budget);if(status==COH_OK){span->observations[0]=p->out.has_updates;span->observations[1]=p->out.definition_count;span->observations[2]=p->out.range_count;}break;}
  case COH_SUFFIX_POWER_MODES:{ModesLoan*p=loan.data;memset(p,0,sizeof(*p));status=coh_global_power_modes(&r,&p->out,&p->event);if(status==COH_OK){span->observations[0]=p->event.replacement_present;span->observations[1]=p->out.count;}break;}
  case COH_SUFFIX_BADGES:{BadgesLoan*p=loan.data;size_t extra=occupied-sizeof(p->out)-sizeof(p->work)-8192u;size_t limit=budget<COH_BADGE_AGGREGATE_MAX?budget:COH_BADGE_AGGREGATE_MAX;status=coh_global_badges(&r,&p->out,&p->work,extra,limit);if(status==COH_OK){span->observations[0]=p->out.player_count;span->observations[1]=p->out.supergroup_count;span->observations[2]=p->out.history_count;}break;}
  case COH_SUFFIX_BADGE_MONITOR:{MonitorLoan*p=loan.data;status=coh_global_badge_monitor(&r,&p->out);if(status==COH_OK)span->observations[0]=COH_BADGE_MONITOR_MAX;break;}
  case COH_SUFFIX_INVENTORY:{InventoryLoan*p=loan.data;size_t extra=occupied-sizeof(p->out)-sizeof(p->work)-COH_INVENTORY_PHASE_STACK_RESERVE;status=coh_inventory_phase_read(&r,&p->out,&p->work,budget,extra);if(status==COH_OK){span->observations[0]=p->out.inventory.count;span->observations[1]=p->out.inventory.auction_updated;span->observations[2]=p->out.invention.status_change;}break;}
  case COH_SUFFIX_SOCIAL:{SocialLoan*p=loan.data;size_t extra=occupied-sizeof(p->out)-sizeof(p->work)-COH_SOCIAL_STACK_RESERVE;status=coh_social_phase_read(&r,&p->out,&p->work,budget,extra);if(status==COH_OK){span->observations[0]=p->out.team_up_to_date;span->observations[1]=p->out.team.count;span->observations[2]=p->out.superstats.count;span->observations[3]=p->out.league_up_to_date;span->observations[4]=p->out.league.count;if(p->out.team_up_to_date||p->out.league_up_to_date)status=COH_INVALID;}break;}
  case COH_SUFFIX_ATTRIBUTES:{AttributesLoan*p=loan.data;uint32_t present;status=boolean(&r,&present);if(status==COH_OK){span->observations[0]=present;if(present){size_t child_fixed=sizeof(p->out)+sizeof(p->work)+COH_ATTRIB_DESCRIPTION_STACK_RESERVE+sizeof(r)+sizes[7]+sizes[8]+32+sizes[9]+sizes[10]+control_scratch;if(child_fixed>occupied){status=COH_INVALID;break;}size_t extra=occupied-child_fixed;status=coh_attrib_description_read(&r,profile->attribute_schema,profile->expected_attribute_sha256,profile->attribute_lease,profile->attribute_control,&p->out,&p->work,budget<COH_ATTRIB_DESCRIPTION_RAM_MAX?budget:COH_ATTRIB_DESCRIPTION_RAM_MAX,extra);if(status==COH_OK){span->observations[1]=p->out.new_target;span->observations[2]=p->out.full;span->observations[3]=p->out.value_count;span->observations[4]=p->out.modifier_count;}}}break;}
  case COH_SUFFIX_DYNAMIC:{DynamicLoan*p=loan.data;size_t extra=occupied-sizeof(p->out)-sizeof(p->work)-COH_DYNAMIC_STACK_RESERVE;status=coh_dynamic_diagnostic_read(&r,context->diagnostic_dynamic_count,&p->out,&p->work,budget,extra);if(status==COH_OK){span->observations[0]=p->out.modified_count;span->observations[1]=p->out.expected_count;span->observations[2]=p->out.raw_bytes;}break;}
  case COH_SUFFIX_VIEW:{ViewLoan*p=loan.data;size_t extra=occupied-sizeof(p->out)-sizeof(p->work)-COH_VIEW_STACK_RESERVE;status=coh_world_view_read(&r,&p->out,&p->work,budget,extra);if(status==COH_OK){span->observations[0]=p->out.sky_interesting;span->observations[1]=p->out.sky1;span->observations[2]=p->out.sky2;span->observations[3]=p->out.slave_present;}break;}
  default:status=COH_INVALID;break;
  }
  memory->release(memory->context,&loan);
  if(status!=COH_OK)goto refused;
  span->end_bit=r.cursor;candidate.stage_count=ordinal;candidate.end_bit=r.cursor;report->validated=candidate;
 }
 candidate.raw_suffix_syntax_validated=1;report->validated=candidate;
 report->stage=COH_SUFFIX_DYNAMIC;report->bit=candidate.stages[COH_SUFFIX_DYNAMIC-1].begin_bit;status=COH_UNSUPPORTED;
refused:
 report->status=status;return status;
}
