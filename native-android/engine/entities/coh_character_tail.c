#include "coh_character_tail.h"
#include "coh_character_options_schema.h"
#include <math.h>
#include <string.h>
typedef struct{CohRepReader r;CohStatus status;}TailReader;
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static uint32_t scalar(TailReader*p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,n,&v);if(p->status==COH_OK&&n<32&&v>=(UINT32_C(1)<<n))p->status=COH_INVALID;return v;}
static uint32_t pack(TailReader*p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,n,&v);return v;}
static uint32_t automatic(TailReader*p){static const unsigned widths[]={2,10,24,32};uint32_t b=scalar(p,2);return p->status==COH_OK?scalar(p,widths[b]):0;}
static uint32_t number(TailReader*p){uint32_t u=scalar(p,32);float f;memcpy(&f,&u,4);if(p->status==COH_OK&&!isfinite(f))p->status=COH_INVALID;return u;}
static void text(TailReader*p,char*d,size_t capacity){if(p->status!=COH_OK)return;for(size_t i=0;i<capacity;i++){uint32_t c=scalar(p,8);if(p->status!=COH_OK)return;d[i]=(char)c;if(!c)return;}p->status=COH_LIMIT;}
static void pooled(TailReader*p,CohCharacterTail*v,CohCharacterTailString*s,size_t capacity){if(p->status!=COH_OK)return;if(capacity>COH_CHARACTER_TAIL_TEXT_MAX-v->text_bytes){p->status=COH_LIMIT;return;}char*d=v->text+v->text_bytes;text(p,d,capacity);if(p->status!=COH_OK)return;s->offset=v->text_bytes;s->bytes=(uint32_t)strlen(d);v->text_bytes+=s->bytes+1;}
static void bit_array(TailReader*p,uint32_t*out,unsigned words){
 if(p->status!=COH_OK)return;
 size_t padding=(8u-(p->r.cursor&7u))&7u;
 if(padding>p->r.bits-p->r.cursor||words>(p->r.bits-p->r.cursor-padding)/32u){p->status=COH_INVALID;return;}
 p->r.cursor+=padding;
 for(unsigned i=0;i<words;i++)out[i]=scalar(p,32);
}
CohStatus coh_character_tail_read(CohRepReader*reader,CohCharacterTail*out,CohCharacterTailWorkspace*workspace,size_t budget,size_t retained){
 TailReader p;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||!budget||budget>COH_CHARACTER_TAIL_RAM_MAX)return COH_INVALID;
 p.r=*reader;p.status=coh_rep_read(&p.r,0,&ignored);if(p.status!=COH_OK)return p.status;
 const void*objects[]={reader,out,workspace,p.r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),p.r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_CHARACTER_TAIL_STACK_RESERVE;if(fixed>budget||p.r.bytes.size>budget-fixed||retained>budget-fixed-p.r.bytes.size)return COH_LIMIT;
 CohCharacterTail*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=p.r.cursor;
 for(unsigned which=0;which<2;which++){
  uint32_t count=automatic(&p);if(p.status==COH_OK&&count>COH_CHARACTER_TAIL_TOKENS_MAX)p.status=COH_LIMIT;if(which)v->active_reward_count=count;else v->reward_count=count;
  for(uint32_t i=0;i<count&&p.status==COH_OK;i++){CohCharacterRewardToken*t=which?&v->active_rewards[i]:&v->rewards[i];pooled(&p,v,&t->name,1024);t->value=pack(&p,1);t->timer=pack(&p,1);}
 }
 v->rewards_end_bit=p.r.cursor;v->lfg=scalar(&p,10);v->hidden=scalar(&p,10);v->supergroup_mode=scalar(&p,1);v->hide_emblem=scalar(&p,1);v->skills_unlocked=scalar(&p,1);v->team_buff_display=scalar(&p,1);v->dock_mode=scalar(&p,32);v->inspiration_mode=scalar(&p,32);v->new_features=scalar(&p,32);
 v->help_chat_added=scalar(&p,1);v->chat_send_channel=pack(&p,1);v->user_send_channel=pack(&p,1);v->chat_options=pack(&p,1);v->primary_chat_minimized=pack(&p,1);
 for(unsigned i=0;i<5;i++){CohCharacterChatWindow*w=&v->chat_windows[i];w->selected_top=pack(&p,1);w->selected_bottom=pack(&p,1);w->tab_bits=pack(&p,1);w->divider_word=number(&p);}
 for(unsigned i=0;i<20;i++){CohCharacterChatTab*t=&v->chat_tabs[i];text(&p,t->name,sizeof(t->name));bit_array(&p,t->system_channels,2);t->user_bits=pack(&p,1);t->options=pack(&p,1);t->default_channel=pack(&p,1);t->default_type=pack(&p,1);}
 for(unsigned i=0;i<15;i++){CohCharacterChatChannel*c=&v->chat_channels[i];text(&p,c->name,sizeof(c->name));c->options=pack(&p,1);c->colors[0]=scalar(&p,32);c->colors[1]=scalar(&p,32);}v->chat_end_bit=p.r.cursor;
 v->title_the=pack(&p,5);text(&p,v->title_the_text,sizeof(v->title_the_text));text(&p,v->title_common,sizeof(v->title_common));text(&p,v->title_origin,sizeof(v->title_origin));v->title_colors[0]=automatic(&p);v->title_colors[1]=automatic(&p);v->title_badge=scalar(&p,32);text(&p,v->title_special,sizeof(v->title_special));text(&p,v->description,sizeof(v->description));text(&p,v->motto,sizeof(v->motto));text(&p,v->comment,sizeof(v->comment));text(&p,v->key_profile,sizeof(v->key_profile));
 for(unsigned i=0;i<256;i++){CohCharacterKeybind*k=&v->keybinds[i];pooled(&p,v,&k->command,256);k->key=scalar(&p,32);k->modifier=scalar(&p,32);}v->keybinds_end_bit=p.r.cursor;
 v->options_saved=scalar(&p,1);if(v->options_saved){for(unsigned i=0;i<114;i++)v->option_words[i]=coh_character_option_widths[i]<0?number(&p):scalar(&p,(unsigned)coh_character_option_widths[i]);}else{v->mouse_invert=scalar(&p,1);v->mouse_speed_word=number(&p);v->turn_speed_word=number(&p);}v->options_end_bit=p.r.cursor;
 for(unsigned i=0;i<8;i++)v->dividers[i]=pack(&p,9);
 v->control_first=scalar(&p,1);v->control_no_collision=scalar(&p,2);v->friends_full_update=pack(&p,1);v->friend_count=pack(&p,1);if(p.status==COH_OK&&v->friend_count>COH_CHARACTER_TAIL_FRIENDS_MAX)p.status=COH_LIMIT;
 for(unsigned i=0;i<v->friend_count&&p.status==COH_OK;i++){CohCharacterFriend*f=&v->friends[i];f->present=scalar(&p,1);if(f->present){f->dbid=pack(&p,1);f->online=scalar(&p,1);text(&p,f->name,sizeof(f->name));f->class_index=pack(&p,1);f->origin_index=pack(&p,1);if(f->online){f->map_id=pack(&p,1);text(&p,f->map_name,sizeof(f->map_name));}}}
 for(unsigned i=0;i<10;i++){CohCharacterCombatMonitor*m=&v->monitors[i];m->key_present=scalar(&p,1);if(m->key_present)m->key=pack(&p,8);m->order_present=scalar(&p,1);if(m->order_present)m->order=scalar(&p,4);}
 v->rename=scalar(&p,1);if(p.status!=COH_OK)return p.status;v->end_bit=p.r.cursor;*out=*v;*reader=p.r;return COH_OK;
}
