#define _GNU_SOURCE
#include "coh_original_initial_tail.h"
#include "coh_character_outer.h"
#include "../entity-control/coh_entity_control.h"
#include "../entity-globals/coh_power_info.h"
#include "../entity-globals/coh_entity_globals.h"
#include "../entity-globals/coh_badges.h"
#include "../entity-inventory/coh_inventory_phase.h"
#include "../entity-social/coh_social.h"
#include "../entity-attributes/coh_attrib_monitor.h"
#include "../entity-dynamic/coh_dynamic.h"
#include "../entity-view/coh_view.h"
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
typedef struct {CohEntCreate create;CohControlUpdate control;CohEntDeletes deletes;} Prelude;
typedef struct {CohCharacterOuter out;CohCharacterOuterWorkspace work;} Character;
typedef struct {CohPowerInfoUpdate out;CohPowerInfoWorkspace work;} Power;
typedef struct {CohPowerModes out;CohPowerModeEvent event;} Modes;
typedef struct {CohBadgeUpdate out;CohBadgeWorkspace work;} Badges;
typedef struct {CohBadgeMonitor out;} Monitor;
typedef struct {CohInventoryPhase out;CohInventoryPhaseWorkspace work;} Inventory;
typedef struct {CohSocialPhase out;CohSocialWorkspace work;} Social;
typedef struct {CohAttribMonitor out;CohAttribMonitorWorkspace work;} Attributes;
typedef struct {CohDynamicDiagnostic out;CohDynamicWorkspace work;} Dynamic;
typedef struct {CohWorldView out;CohWorldViewWorkspace work;} View;
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(!a||!b||an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static size_t storage(uint32_t stage){switch(stage){case 1:case 2:case 3:return sizeof(Prelude);case 4:return sizeof(Character);case 5:return sizeof(Power);case 6:return sizeof(Modes);case 7:return sizeof(Badges);case 8:return sizeof(Monitor);case 9:return sizeof(Inventory);case 10:return sizeof(Social);case 11:return sizeof(Attributes);case 12:return sizeof(Dynamic);case 13:return sizeof(View);default:return 0;}}
static CohStatus flag(CohRepReader*r,uint32_t*v){CohStatus s=coh_rep_read(r,1,v);return s==COH_OK&&*v>1?COH_INVALID:s;}
const char *coh_original_initial_field_name(uint32_t s){static const char*const n[]={"none","entity-list sentinel","player control state","entity deletes","character definition","power activation update","power modes","badges","badge monitor","inventory/invention/workshop","team/supergroup/league","attribute monitor","dynamic groups","sky/slave orientation","source update tail complete"};return s<sizeof(n)/sizeof(n[0])?n[s]:"unknown source field";}
CohStatus coh_original_initial_tail(const CohRepReader*reader,uint32_t previous,uint32_t packet_id,CohOriginalInitialTailReport*out,size_t budget,size_t retained){
 if(!reader||!out||previous>COH_ENT_INDEX_MAX||!packet_id||!budget||budget>COH_ORIGINAL_INITIAL_RAM_MAX)return COH_INVALID;
 CohRepReader r=*reader;uint32_t ignored;CohStatus s=coh_rep_read(&r,0,&ignored);if(s!=COH_OK)return s;
 if(overlap(reader,sizeof(*reader),out,sizeof(*out))||overlap(reader,sizeof(*reader),r.bytes.data,r.bytes.size)||overlap(out,sizeof(*out),r.bytes.data,r.bytes.size))return COH_INVALID;
 size_t base=sizeof(*reader)+sizeof(*out)+COH_ORIGINAL_INITIAL_STACK_RESERVE;
 if(base>budget||r.bytes.size>budget-base||retained>budget-base-r.bytes.size)return COH_LIMIT;
 base+=r.bytes.size+retained;long page_long=sysconf(_SC_PAGESIZE);if(page_long<=0)return COH_INVALID;size_t page=(size_t)page_long;
 memset(out,0,sizeof(*out));out->begin_bit=out->end_bit=r.cursor;out->packet_bits=r.bits;out->source_shared_count=26;
 /* SHA256 of sorted path->SHA256 JSON for the287 locked CLIENT .powersets and
  * .categories files. Generation is the digest's low32 bits, a content token
  * used solely by the existing raw character parser; no runtime owner claimed. */
 const CohCharacterWireProfile profile={1233492836u,26,1,1,{0x64,0x9b,0x85,0x49,0x3d,0xcd,0x6b,0xdc,0x0e,0xbd,0x76,0x69,0xee,0xd9,0xce,0x61,0x53,0x6d,0x87,0x88,0x75,0x50,0x75,0x26,0x5b,0x17,0xa0,0x90,0x5a,0x83,0xbd,0x11}};
 for(uint32_t stage=1;stage<=13;stage++){
  out->stage=stage;CohOriginalInitialSpan*span=&out->spans[stage-1];span->begin_bit=r.cursor;
  size_t bytes=storage(stage);if(!bytes||bytes>SIZE_MAX-(page-1)){s=COH_LIMIT;goto failed;}size_t charged=((bytes+page-1)/page)*page;
  size_t limit=stage==COH_ORIGINAL_INITIAL_BADGES&&budget>COH_BADGE_AGGREGATE_MAX?COH_BADGE_AGGREGATE_MAX:budget;
  if(base>limit||charged>limit-base){s=COH_LIMIT;goto failed;}
  void*block=mmap(NULL,charged,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(block==MAP_FAILED){s=COH_LIMIT;goto failed;}
  if(charged>out->peak_mapped_bytes)out->peak_mapped_bytes=charged;
  if(base+charged>out->peak_aggregate_bytes)out->peak_aggregate_bytes=base+charged;
  size_t occupied=base+charged;
  switch(stage){
  case COH_ORIGINAL_INITIAL_SENTINEL:{Prelude*p=block;CohEntFailure f;uint32_t index;s=coh_ent_next_index(&r,(int32_t)previous,&index,&f);if(s==COH_OK)s=coh_ent_create(&r,0,&p->create,&f);if(s==COH_OK&&(!p->create.create||!p->create.end)){out->unexpected_entity_index=index;s=COH_UNSUPPORTED;}if(s==COH_OK){out->entity_list_complete=1;out->list_end_bit=r.cursor;}break;}
  case COH_ORIGINAL_INITIAL_CONTROL:{Prelude*p=block;CohControlFailure f;s=coh_control_read(&r,&p->control,&f);if(s==COH_OK){out->control_end_bit=r.cursor;span->values[0]=p->control.push_count;span->values[1]=p->control.has_server;span->values[2]=p->control.has_forced;}break;}
  case COH_ORIGINAL_INITIAL_DELETES:{Prelude*p=block;CohEntFailure f;s=coh_ent_deletes(&r,&p->deletes,&f);if(s==COH_OK){out->deletes_end_bit=r.cursor;span->values[0]=p->deletes.count;}break;}
  case COH_ORIGINAL_INITIAL_CHARACTER:{Character*p=block;s=coh_character_outer_read(&r,&profile,packet_id,&p->out,&p->work,budget,occupied-sizeof(*p)-COH_CHARACTER_OUTER_STACK_RESERVE);if(s==COH_OK){CohCharacterData*d=&p->out.creation.initial.character;out->character_complete=1;out->character_end_bit=r.cursor;span->values[0]=d->build_count;span->values[1]=d->set_count;span->values[2]=d->power_count;span->values[3]=p->out.tail.friend_count;}break;}
  case COH_ORIGINAL_INITIAL_POWER_INFO:{Power*p=block;s=coh_global_power_info(&r,&p->out,&p->work,occupied-sizeof(*p)-8192u,budget);if(s==COH_OK){span->values[0]=p->out.has_updates;span->values[1]=p->out.definition_count;span->values[2]=p->out.range_count;}break;}
  case COH_ORIGINAL_INITIAL_POWER_MODES:{Modes*p=block;s=coh_global_power_modes(&r,&p->out,&p->event);if(s==COH_OK)span->values[0]=p->out.count;break;}
  case COH_ORIGINAL_INITIAL_BADGES:{Badges*p=block;s=coh_global_badges(&r,&p->out,&p->work,occupied-sizeof(*p)-8192u,limit);if(s==COH_OK){span->values[0]=p->out.player_count;span->values[1]=p->out.supergroup_count;span->values[2]=p->out.history_count;}break;}
  case COH_ORIGINAL_INITIAL_BADGE_MONITOR:{Monitor*p=block;s=coh_global_badge_monitor(&r,&p->out);if(s==COH_OK)span->values[0]=COH_BADGE_MONITOR_MAX;break;}
  case COH_ORIGINAL_INITIAL_INVENTORY:{Inventory*p=block;s=coh_inventory_phase_read(&r,&p->out,&p->work,budget,occupied-sizeof(*p)-COH_INVENTORY_PHASE_STACK_RESERVE);if(s==COH_OK){span->values[0]=p->out.inventory.count;span->values[1]=p->out.invention.status_change;}break;}
  case COH_ORIGINAL_INITIAL_SOCIAL:{Social*p=block;s=coh_social_phase_read(&r,&p->out,&p->work,budget,occupied-sizeof(*p)-COH_SOCIAL_STACK_RESERVE);if(s==COH_OK){span->values[0]=p->out.team.count;span->values[1]=p->out.superstats.count;span->values[2]=p->out.league.count;}break;}
  case COH_ORIGINAL_INITIAL_ATTRIBUTES:{Attributes*p=block;uint32_t present=0;s=flag(&r,&present);span->values[0]=present;if(s==COH_OK&&present)s=coh_attrib_monitor_read(&r,&p->out,&p->work,budget,occupied-sizeof(*p)-COH_ATTRIB_MONITOR_STACK_RESERVE);break;}
  case COH_ORIGINAL_INITIAL_DYNAMIC:{Dynamic*p=block;CohRepReader peek=r;uint32_t count,zip,raw;s=coh_rep_pack(&peek,1,&count);if(s==COH_OK&&count==UINT32_MAX){s=coh_rep_pack(&peek,1,&zip);if(s==COH_OK)s=coh_rep_pack(&peek,1,&raw);if(s==COH_OK){out->dynamic_count=raw;out->dynamic_count_from_wire=1;}}else if(s==COH_OK){out->dynamic_count=0;out->dynamic_count_from_wire=0;}
   /* Full status declares its own raw byte count. Delta indices are bounded
    * by native capacity only; an absent world table cannot change wire bits. */
   if(s==COH_OK)s=coh_dynamic_diagnostic_read(&r,out->dynamic_count_from_wire?out->dynamic_count:COH_DYNAMIC_COUNT_MAX,&p->out,&p->work,budget,occupied-sizeof(*p)-COH_DYNAMIC_STACK_RESERVE);
   if(s==COH_OK){span->values[0]=p->out.modified_count;span->values[1]=p->out.raw_bytes;span->values[2]=p->out.compressed_bytes;}break;}
  case COH_ORIGINAL_INITIAL_VIEW:{View*p=block;s=coh_world_view_read(&r,&p->out,&p->work,budget,occupied-sizeof(*p)-COH_VIEW_STACK_RESERVE);if(s==COH_OK){span->values[0]=p->out.sky_interesting;span->values[1]=p->out.slave_present;}break;}
  default:s=COH_INVALID;break;
  }
  memset(block,0,charged);if(munmap(block,charged)!=0){s=COH_IO;goto failed;}if(s!=COH_OK)goto failed;
  span->end_bit=r.cursor;out->end_bit=r.cursor;out->stage_count=stage;
 }
 out->stage=COH_ORIGINAL_INITIAL_TAIL_COMPLETE;out->source_tail_complete=1;out->status=COH_OK;return COH_OK;
failed:out->status=s;return s;
}
