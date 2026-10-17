#include "coh_invention.h"
#include "inventory_reader.h"
CohStatus coh_invention_update_read(CohRepReader*reader,CohInventionUpdate*out,CohInventionWorkspace*workspace,size_t budget,size_t retained){
 InventoryReader p;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||!budget||budget>COH_INVENTION_RAM_MAX)return COH_INVALID;
 p.r=*reader;p.status=coh_rep_read(&p.r,0,&ignored);if(p.status!=COH_OK)return p.status;
 const void*objects[]={reader,out,workspace,p.r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),p.r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(inventory_overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_INVENTION_STACK_RESERVE;if(fixed>budget||p.r.bytes.size>budget-fixed||retained>budget-fixed-p.r.bytes.size)return COH_LIMIT;
 CohInventionUpdate*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=p.r.cursor;v->status_change=inventory_pack(&p,1);v->original_consumer_compatible=v->status_change==0;
 if(v->status_change){v->state=inventory_pack(&p,1);if(v->state){v->recipe_id=inventory_pack(&p,1);v->boost_inventory_index=inventory_pack(&p,1);for(unsigned i=0;i<4;i++)v->variable_words[i]=inventory_number(&p);for(unsigned i=0;i<COH_INVENTION_POWERUPS;i++){CohInventionPowerup*slot=&v->powerups[i];slot->type=inventory_pack(&p,1);slot->id=inventory_pack(&p,1);slot->filled=inventory_pack(&p,1);}for(unsigned i=0;i<COH_INVENTION_SLOTS&&p.status==COH_OK;i++){CohInventionSlot*slot=&v->slots[i];slot->state=inventory_pack(&p,1);slot->concept_first=v->concept_count;slot->concept_count=inventory_pack(&p,1);if(p.status==COH_OK&&(slot->concept_count>COH_INVENTION_CONCEPTS_PER_SLOT||slot->concept_count>COH_INVENTION_CONCEPTS_MAX-v->concept_count))p.status=COH_LIMIT;for(unsigned j=0;j<slot->concept_count&&p.status==COH_OK;j++){CohInventionConcept*concept=&v->concepts[v->concept_count++];concept->id=inventory_pack(&p,5);for(unsigned k=0;k<4;k++)concept->variable_words[k]=inventory_number(&p);}}}}
 if(p.status!=COH_OK)return p.status;
 v->end_bit=p.r.cursor;*out=*v;*reader=p.r;return COH_OK;
}
