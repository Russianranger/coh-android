#include "coh_inventory_phase.h"
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
CohStatus coh_inventory_phase_read(CohRepReader*reader,CohInventoryPhase*out,CohInventoryPhaseWorkspace*workspace,size_t budget,size_t retained){
 CohRepReader r;CohStatus status;uint32_t ignored;size_t fixed,extra;
 if(!reader||!out||!workspace||!budget||budget>COH_INVENTORY_PHASE_RAM_MAX)return COH_INVALID;
 r=*reader;status=coh_rep_read(&r,0,&ignored);if(status!=COH_OK)return status;
 const void*objects[]={reader,out,workspace,r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_INVENTORY_PHASE_STACK_RESERVE;if(fixed>budget||r.bytes.size>budget-fixed||retained>budget-fixed-r.bytes.size)return COH_LIMIT;
 CohInventoryPhase*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=r.cursor;
 extra=fixed-sizeof(v->inventory)-sizeof(workspace->inventory)-COH_INVENTORY_STACK_RESERVE+retained;status=coh_inventory_update_read(&r,&v->inventory,&workspace->inventory,budget,extra);if(status!=COH_OK)return status;v->inventory_end_bit=r.cursor;
 extra=fixed-sizeof(v->invention)-sizeof(workspace->invention)-COH_INVENTION_STACK_RESERVE+retained;status=coh_invention_update_read(&r,&v->invention,&workspace->invention,budget,extra);if(status!=COH_OK)return status;if(!v->invention.original_consumer_compatible)return COH_UNSUPPORTED;v->invention_end_bit=r.cursor;
 status=coh_rep_string(&r,v->workshop,sizeof(v->workshop));if(status!=COH_OK)return status;
 v->end_bit=r.cursor;*out=*v;*reader=r;return COH_OK;
}
