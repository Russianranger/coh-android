#include "coh_inventory.h"
#include "inventory_reader.h"
CohStatus coh_inventory_update_read(CohRepReader*reader,CohInventoryUpdate*out,CohInventoryWorkspace*workspace,size_t budget,size_t retained){
 InventoryReader p;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||!budget||budget>COH_INVENTORY_RAM_MAX)return COH_INVALID;
 p.r=*reader;p.status=coh_rep_read(&p.r,0,&ignored);if(p.status!=COH_OK)return p.status;
 const void*objects[]={reader,out,workspace,p.r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),p.r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(inventory_overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_INVENTORY_STACK_RESERVE;if(fixed>budget||p.r.bytes.size>budget-fixed||retained>budget-fixed-p.r.bytes.size)return COH_LIMIT;
 CohInventoryUpdate*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=p.r.cursor;v->count=inventory_pack(&p,1);if(p.status==COH_OK&&v->count>COH_INVENTORY_ITEMS_MAX)p.status=COH_LIMIT;
 for(uint32_t i=0;i<v->count&&p.status==COH_OK;i++){CohInventoryItem*item=&v->items[i];item->type=inventory_pack(&p,5);item->index=inventory_pack(&p,5);item->amount=inventory_pack(&p,5);item->id=inventory_pack(&p,5);if(item->type==1)for(unsigned j=0;j<4;j++)item->variable_words[j]=inventory_number(&p);}v->items_end_bit=p.r.cursor;
 static const unsigned widths[]={2,10,24,32};uint32_t bin=inventory_scalar(&p,2);v->auction_updated=p.status==COH_OK?inventory_scalar(&p,widths[bin]):0;
 if(v->auction_updated&&p.status==COH_OK){size_t i;for(i=0;i<COH_INVENTORY_AUCTION_BYTES;i++){uint32_t c=inventory_scalar(&p,8);if(p.status!=COH_OK)break;v->auction_text[i]=(char)c;if(!c){v->auction_bytes=(uint32_t)i;break;}}if(p.status==COH_OK&&i==COH_INVENTORY_AUCTION_BYTES)p.status=COH_LIMIT;}
 if(p.status!=COH_OK)return p.status;
 v->end_bit=p.r.cursor;*out=*v;*reader=p.r;return COH_OK;
}
