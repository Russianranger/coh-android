#include "coh_character_ui.h"
#include <math.h>
#include <string.h>
typedef struct {CohRepReader r;CohStatus status;} UiReader;
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static uint32_t scalar(UiReader*p,unsigned width){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,width,&v);if(p->status==COH_OK&&width<32&&v>=(UINT32_C(1)<<width))p->status=COH_INVALID;return v;}
static uint32_t packed(UiReader*p,unsigned width){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,width,&v);return v;}
static void text(UiReader*p,char*out,size_t size){
 if(p->status!=COH_OK)return;
 for(size_t i=0;i<size;i++){uint32_t c=scalar(p,8);if(p->status!=COH_OK)return;out[i]=(char)c;if(!c)return;}
 p->status=COH_LIMIT;
}
static void pooled(UiReader*p,CohCharacterUi*v,CohCharacterUiString*out,size_t size){
 if(p->status!=COH_OK)return;
 if(size>COH_CHARACTER_UI_TEXT_MAX-v->text_bytes){p->status=COH_LIMIT;return;}
 char*target=v->text+v->text_bytes;text(p,target,size);if(p->status!=COH_OK)return;
 out->offset=v->text_bytes;out->bytes=(uint32_t)strlen(target);v->text_bytes+=out->bytes+1;
}
CohStatus coh_character_ui_read(CohRepReader*reader,CohCharacterUi*out,
 CohCharacterUiWorkspace*workspace,size_t budget,size_t retained){
 UiReader p;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||!budget||budget>COH_CHARACTER_UI_RAM_MAX)return COH_INVALID;
 p.r=*reader;p.status=coh_rep_read(&p.r,0,&ignored);if(p.status!=COH_OK)return p.status;
 const void*objects[]={reader,out,workspace,p.r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),p.r.bytes.size};
 for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_CHARACTER_UI_STACK_RESERVE;
 if(fixed>budget||p.r.bytes.size>budget-fixed||retained>budget-fixed-p.r.bytes.size)return COH_LIMIT;
 CohCharacterUi*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=p.r.cursor;
 for(unsigned i=0;i<4;i++)v->current_trays[i]=scalar(&p,32);
 v->tray_indexes=scalar(&p,32);
 for(unsigned i=0;i<COH_CHARACTER_UI_TRAY_SLOTS&&p.status==COH_OK;i++){
  CohCharacterTraySlot*s=&v->slots[i];s->type=scalar(&p,5);
  if(s->type==1){s->set=scalar(&p,32);s->power=scalar(&p,32);}
  else if(s->type==2){s->set=packed(&p,3);s->power=packed(&p,3);}
  else if(s->type==6||s->type==17){pooled(&p,v,&s->command,256);pooled(&p,v,&s->short_name,32);pooled(&p,v,&s->icon_name,256);}
 }
 v->default_present=scalar(&p,1);if(v->default_present){v->default_set=scalar(&p,32);v->default_power=scalar(&p,32);}v->tray_end_bit=p.r.cursor;
 v->tray_mode=scalar(&p,1);v->tray_mode_alt2=scalar(&p,1);
 text(&p,v->name,sizeof(v->name));text(&p,v->motto,sizeof(v->motto));text(&p,v->description,sizeof(v->description));v->strings_end_bit=p.r.cursor;
 for(unsigned i=0;i<COH_CHARACTER_UI_HELP_WORDS;i++)v->help_status[i]=scalar(&p,32);
 for(unsigned i=0;i<COH_CHARACTER_UI_HELP_LATEST;i++)v->help_latest[i]=scalar(&p,32);
 v->help_end_bit=p.r.cursor;
 for(unsigned i=0;i<COH_CHARACTER_UI_WINDOWS&&p.status==COH_OK;i++){
  CohCharacterWindow*w=&v->windows[i];w->index=packed(&p,1);w->x=packed(&p,1);w->y=packed(&p,1);w->mode=packed(&p,1);w->locked=packed(&p,1);w->color=packed(&p,1);w->back_color=packed(&p,1);w->maximized=scalar(&p,1);w->dimensions_present=scalar(&p,1);if(w->dimensions_present){w->width=packed(&p,1);w->height=packed(&p,1);}w->scale_present=scalar(&p,1);if(w->scale_present){float f;w->scale_word=scalar(&p,32);memcpy(&f,&w->scale_word,4);if(p.status==COH_OK&&!isfinite(f))p.status=COH_INVALID;}
 }
 if(p.status!=COH_OK)return p.status;
 v->end_bit=p.r.cursor;*out=*v;*reader=p.r;return COH_OK;
}
