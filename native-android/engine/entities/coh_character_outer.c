#include "coh_character_outer.h"
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
CohStatus coh_character_outer_read(CohRepReader*reader,const CohCharacterWireProfile*profile,uint32_t packet_id,CohCharacterOuter*out,CohCharacterOuterWorkspace*workspace,size_t budget,size_t retained){
 CohRepReader r;CohStatus status;uint32_t ignored;size_t fixed,extra;
 if(!reader||!profile||!packet_id||!out||!workspace||!budget||budget>COH_CHARACTER_OUTER_RAM_MAX)return COH_INVALID;
 r=*reader;status=coh_rep_read(&r,0,&ignored);if(status!=COH_OK)return status;
 const void*objects[]={reader,profile,out,workspace,r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*profile),sizeof(*out),sizeof(*workspace),r.bytes.size};for(unsigned i=0;i<5;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_CHARACTER_OUTER_STACK_RESERVE;if(fixed>budget||r.bytes.size>budget-fixed||retained>budget-fixed-r.bytes.size)return COH_LIMIT;
 CohCharacterOuter*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=r.cursor;
 extra=fixed-sizeof(v->creation)-sizeof(workspace->creation)-COH_CHARACTER_CREATION_STACK_RESERVE+retained;
 status=coh_character_creation_read(&r,profile,packet_id,&v->creation,&workspace->creation,budget,extra);if(status!=COH_OK)return status;v->creation_end_bit=r.cursor;
 extra=fixed-sizeof(v->tail)-sizeof(workspace->tail)-COH_CHARACTER_TAIL_STACK_RESERVE+retained;
 status=coh_character_tail_read(&r,&v->tail,&workspace->tail,budget,extra);if(status!=COH_OK)return status;
 v->end_bit=r.cursor;*out=*v;*reader=r;return COH_OK;
}
