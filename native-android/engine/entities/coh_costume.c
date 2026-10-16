#include "coh_costume.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
struct CohEntCostumeDictionary {
    uint32_t generation,body_parts,body_types,string_count,extra_count,palette_count;
    uint8_t manifest_sha256[32];size_t bytes;
    CohBytes *strings,*extra;uint32_t *palette;uint8_t *present;
};
static int nonzero(const uint8_t *v){unsigned i;uint8_t n=0;for(i=0;i<32;i++)n|=v[i];return n!=0;}
static CohStatus string_table_size(CohEntCostumeStringTable t,size_t *bytes){
    uint32_t i;if(t.max_size<2||t.max_size>COH_COSTUME_DICTIONARY_SLOT_MAX||!t.slots)return COH_LIMIT;
    *bytes+=(size_t)t.max_size*sizeof(CohBytes);
    for(i=0;i<t.max_size;i++){
        CohBytes b=t.slots[i];if(!b.data){if(b.size)return COH_INVALID;continue;}
        if(b.size>259||memchr(b.data,0,b.size))return COH_LIMIT;
        *bytes+=b.size+1;if(*bytes>COH_COSTUME_DICTIONARY_BYTES_MAX)return COH_LIMIT;
    }
    return COH_OK;
}
CohStatus coh_ent_costume_dictionary_load(CohEntCostumeDictionary **out,const CohEntCostumeDictionaryInput *in,uint32_t gen,const uint8_t sha[32]){
    CohEntCostumeDictionary *d;size_t bytes=sizeof(*d);uint32_t i,t;uint8_t *cursor;CohStatus status;
    if(!out||*out||!in||!sha||!gen||in->generation!=gen||!nonzero(sha)||memcmp(in->manifest_sha256,sha,32))return COH_STATE;
    if(!in->body_parts||in->body_parts>COH_COSTUME_PART_MAX||!in->body_types||in->body_types>64||
       in->palette_max_size<2||in->palette_max_size>COH_COSTUME_DICTIONARY_SLOT_MAX||!in->palette||!in->palette_present)return COH_LIMIT;
    status=string_table_size(in->strings,&bytes);if(status!=COH_OK)return status;
    status=string_table_size(in->extra_strings,&bytes);if(status!=COH_OK)return status;
    bytes+=(size_t)in->palette_max_size*(sizeof(uint32_t)+1);
    if(bytes>COH_COSTUME_DICTIONARY_BYTES_MAX)return COH_LIMIT;
    for(i=0;i<in->palette_max_size;i++)if(in->palette_present[i]>1)return COH_INVALID;
    d=(CohEntCostumeDictionary*)calloc(1,bytes);if(!d)return COH_LIMIT;
    d->generation=gen;d->body_parts=in->body_parts;d->body_types=in->body_types;d->bytes=bytes;memcpy(d->manifest_sha256,sha,32);
    d->string_count=in->strings.max_size;d->extra_count=in->extra_strings.max_size;d->palette_count=in->palette_max_size;
    cursor=(uint8_t*)(d+1);d->strings=(CohBytes*)cursor;cursor+=(size_t)d->string_count*sizeof(CohBytes);
    d->extra=(CohBytes*)cursor;cursor+=(size_t)d->extra_count*sizeof(CohBytes);
    d->palette=(uint32_t*)cursor;cursor+=(size_t)d->palette_count*sizeof(uint32_t);
    d->present=cursor;cursor+=d->palette_count;
    memcpy(d->palette,in->palette,(size_t)d->palette_count*sizeof(uint32_t));memcpy(d->present,in->palette_present,d->palette_count);
    for(t=0;t<2;t++){
        CohBytes *dst=t?d->extra:d->strings;const CohBytes *src=t?in->extra_strings.slots:in->strings.slots;uint32_t count=t?d->extra_count:d->string_count;
        for(i=0;i<count;i++)if(src[i].data){dst[i]=(CohBytes){cursor,src[i].size};memcpy(cursor,src[i].data,src[i].size);cursor+=src[i].size+1;}
    }
    *out=d;return COH_OK;
}
void coh_ent_costume_dictionary_free(CohEntCostumeDictionary *d){free(d);}
size_t coh_ent_costume_dictionary_bytes(const CohEntCostumeDictionary *d){return d?d->bytes:0;}
typedef struct {CohRepReader r;CohStatus status;CohEntStage stage;} Parse;
static uint32_t bits(Parse *p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,n,&v);if(n<32&&v>=(1u<<n)&&p->status==COH_OK)p->status=COH_INVALID;return v;}
static uint32_t pack(Parse *p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,n,&v);return v;}
static void need(Parse *p,int yes,CohStatus s){if(p->status==COH_OK&&!yes)p->status=s;}
static CohStatus failed(Parse *p,CohEntFailure *f){if(f)*f=(CohEntFailure){p->status,p->stage,p->r.cursor};return p->status;}
static unsigned width(uint32_t max){unsigned n=0;uint32_t v=1;while(v<max){v*=2;n++;}return n;}
static void text(Parse *p,char *out){size_t i;for(i=0;i<260&&p->status==COH_OK;i++){out[i]=(char)bits(p,8);if(!out[i])return;}need(p,0,COH_LIMIT);}
static void indexed_string(Parse *p,const CohBytes *table,uint32_t count,CohEntCostumeText *out){
    uint32_t index;memset(out,0,sizeof(*out));out->present=bits(p,1);if(!out->present)return;
    if(bits(p,1)){
        index=pack(p,width(count));need(p,index<count,COH_LIMIT);if(p->status!=COH_OK)return;
        need(p,table[index].data!=NULL,COH_NOT_FOUND);if(p->status!=COH_OK)return;
        memcpy(out->value,table[index].data,table[index].size);
    }else text(p,out->value);
}
static void cached_string(Parse *p,const CohEntCostumeDictionary *d,CohEntCostumeWorkspace *w,CohEntCostumeText *out){
    if(bits(p,1)){
        uint32_t index;need(p,w->string_count>0,COH_INVALID);index=w->string_count>1?bits(p,w->string_order):0;
        need(p,index<w->string_count,COH_INVALID);if(p->status==COH_OK)*out=w->strings[index];
    }else{
        need(p,w->string_count<COH_COSTUME_CACHE_MAX,COH_LIMIT);if(p->status!=COH_OK)return;
        indexed_string(p,d->strings,d->string_count,out);if(p->status!=COH_OK)return;
        w->strings[w->string_count]=*out;if(w->string_count>((1u<<w->string_order)-1))w->string_order++;w->string_count++;
    }
}
static uint32_t cached_color(Parse *p,const CohEntCostumeDictionary *d,CohEntCostumeWorkspace *w){
    uint32_t value=0;
    if(bits(p,1)){
        uint32_t index;need(p,w->color_count>0,COH_INVALID);index=w->color_count>1?bits(p,w->color_order):0;
        need(p,index<w->color_count,COH_INVALID);if(p->status==COH_OK)value=w->colors[index];
    }else{
        need(p,w->color_count<COH_COSTUME_CACHE_MAX,COH_LIMIT);if(p->status!=COH_OK)return 0;
        if(bits(p,1)){uint32_t index=pack(p,width(d->palette_count));need(p,index<d->palette_count,COH_LIMIT);if(p->status==COH_OK){need(p,d->present[index],COH_NOT_FOUND);value=d->palette[index];}}
        else value=bits(p,32);
        if(p->status!=COH_OK)return 0;
        w->colors[w->color_count]=value;if(w->color_count>((1u<<w->color_order)-1))w->color_order++;w->color_count++;
    }
    return value;
}
static float float32(Parse *p){uint32_t v=bits(p,32);float f;memcpy(&f,&v,4);need(p,isfinite(f),COH_INVALID);return f;}
CohStatus coh_ent_costume(CohRepReader *r,const CohEntCostumeDictionary *d,uint32_t gen,CohEntCostumeWorkspace *w,CohEntCostume *out,CohEntFailure *failure){
    Parse p;CohEntCostume *s;uint32_t unused,i,j,k;
    if(!r||!d||!gen||!w||!out||out==&w->candidate)return COH_INVALID;
    p=(Parse){*r,COH_OK,COH_ENT_STAGE_COSTUME_DICTIONARY};p.status=coh_rep_read(&p.r,0,&unused);need(&p,gen==d->generation,COH_STATE);if(p.status!=COH_OK)return failed(&p,failure);
    memset(w,0,sizeof(*w));s=&w->candidate;s->generation=gen;memcpy(s->manifest_sha256,d->manifest_sha256,32);p.stage=COH_ENT_STAGE_COSTUME_BODY;
    if(bits(&p,1))cached_string(&p,d,w,&s->entity_type_file);
    if(bits(&p,1))cached_string(&p,d,w,&s->prefix);
    s->body_type=pack(&p,6);s->skin_color=bits(&p,32);s->converted_scale=bits(&p,1);s->super_color_set=bits(&p,3);s->extra_info=bits(&p,1);
    need(&p,s->body_type<d->body_types,COH_LIMIT);
    for(i=0;i<6;i++)for(j=0;j<12;j++)s->super_colors[i][j]=bits(&p,32);
    for(i=0;i<COH_COSTUME_SCALE_COUNT;i++)s->scales[i]=(i==0||s->extra_info)?float32(&p):bits(&p,6)*2.0f/63.0f-1.0f;
    s->part_count=bits(&p,1)?pack(&p,4):d->body_parts;need(&p,s->part_count<=d->body_parts,COH_LIMIT);
    for(i=0;i<s->part_count&&p.status==COH_OK;i++){
        CohEntCostumePart *part=&s->parts[i];uint32_t colors;
        cached_string(&p,d,w,&part->geometry);cached_string(&p,d,w,&part->texture1);cached_string(&p,d,w,&part->texture2);cached_string(&p,d,w,&part->fx);
        colors=bits(&p,1)?4:2;for(k=0;k<colors;k++)part->colors[k]=cached_color(&p,d,w);
        if(s->extra_info){indexed_string(&p,d->extra,d->extra_count,&part->region);indexed_string(&p,d->extra,d->extra_count,&part->body_set);}
    }
    if(p.status!=COH_OK)return failed(&p,failure);
    s->end_bit=p.r.cursor;*out=*s;*r=p.r;if(failure)memset(failure,0,sizeof(*failure));return COH_OK;
}
CohStatus coh_ent_custom_costume(CohRepReader *r,CohEntCustomCostume *out,CohEntFailure *failure){
    Parse p;CohEntCustomCostume s={0};uint32_t unused,i;
    if(!r||!out)return COH_INVALID;
    p=(Parse){*r,COH_OK,COH_ENT_STAGE_CUSTOM_COSTUME};p.status=coh_rep_read(&p.r,0,&unused);
    s.skin_color=bits(&p,32);s.count=bits(&p,6);need(&p,s.count<=COH_COSTUME_CUSTOM_MAX,COH_LIMIT);
    for(i=0;i<s.count&&p.status==COH_OK;i++){s.parts[i].colors[0]=bits(&p,32);s.parts[i].colors[1]=bits(&p,32);text(&p,s.parts[i].region);}
    if(p.status!=COH_OK)return failed(&p,failure);
    s.end_bit=p.r.cursor;*out=s;*r=p.r;if(failure)memset(failure,0,sizeof(*failure));return COH_OK;
}
static void envelope_body(Parse *p,const CohEntCostumeDictionary *d,CohEntCostumeEnvelopeWorkspace *w,CohEntCostume *out){
    CohEntFailure f;if(p->status!=COH_OK)return;
    p->status=coh_ent_costume(&p->r,d,d->generation,&w->body,out,&f);
    if(p->status!=COH_OK){p->stage=f.stage;p->r.cursor=f.bit;}
}
CohStatus coh_ent_costume_envelope(CohRepReader *r,const CohEntCostumeDictionary *d,uint32_t gen,int self,CohEntCostumeEnvelopeWorkspace *w,CohEntCostumeEnvelope *out,CohEntFailure *failure){
    Parse p;CohEntCostumeEnvelope *s;uint32_t unused,i,j;
    if(!r||!d||!gen||(self!=0&&self!=1)||!w||!out||out==&w->candidate)return COH_INVALID;
    p=(Parse){*r,COH_OK,COH_ENT_STAGE_COSTUME_DICTIONARY};p.status=coh_rep_read(&p.r,0,&unused);need(&p,gen==d->generation,COH_STATE);if(p.status!=COH_OK)return failed(&p,failure);
    memset(w,0,sizeof(*w));s=&w->candidate;s->generation=gen;memcpy(s->manifest_sha256,d->manifest_sha256,32);p.stage=COH_ENT_STAGE_APPEARANCE;
    s->type=bits(&p,1)?pack(&p,2):0;need(&p,s->type<=4,COH_UNSUPPORTED);
    if(s->type==1){
        s->is_self=bits(&p,1);need(&p,s->is_self==(uint32_t)self,COH_STATE);
        if(s->is_self){
            for(i=0;i<2&&p.status==COH_OK;i++){
                s->reward_count[i]=bits(&p,32);need(&p,s->reward_count[i]<=COH_COSTUME_REWARDS_MAX,COH_LIMIT);
                for(j=0;j<s->reward_count[i]&&p.status==COH_OK;j++)if(bits(&p,1)){
                    indexed_string(&p,d->strings,d->string_count,&s->rewards[i][j]);need(&p,s->rewards[i][j].present,COH_INVALID);
                }
            }
            s->deferred=bits(&p,1);s->current_slot=bits(&p,8);s->additional_slots=bits(&p,8);
            need(&p,s->current_slot<COH_COSTUME_STORED_MAX,COH_LIMIT);
        }else s->deferred=bits(&p,1);
        s->multiple=bits(&p,1);s->body_count=s->multiple?bits(&p,4):1;
        need(&p,s->body_count>0&&s->body_count<=COH_COSTUME_STORED_MAX,COH_LIMIT);
        need(&p,!s->multiple||s->is_self,COH_INVALID);
        if(s->multiple)need(&p,s->current_slot<s->body_count,COH_LIMIT);
        for(i=0;i<s->body_count&&p.status==COH_OK;i++)envelope_body(&p,d,w,&s->bodies[i]);
        s->super_present=bits(&p,1);
        if(s->super_present){envelope_body(&p,d,w,&s->super_body);s->super_mode=bits(&p,1);s->hide_emblem=bits(&p,1);}
        s->special_fx.present=bits(&p,1);if(s->special_fx.present)text(&p,s->special_fx.value);
        s->npc_present=bits(&p,1);
    }else if(s->type==2){s->body_count=1;envelope_body(&p,d,w,&s->bodies[0]);}
    else if(s->type==3)s->npc_present=1;
    else if(s->type==4){text(&p,s->sequence);s->world_group.present=bits(&p,1);if(s->world_group.present)text(&p,s->world_group.value);}
    if(s->npc_present){
        s->npc_index=pack(&p,12);s->npc_costume_index=pack(&p,1);
        need(&p,s->npc_index<=INT32_MAX&&s->npc_costume_index<=INT32_MAX,COH_LIMIT);
        s->world_group.present=bits(&p,1);if(s->world_group.present)text(&p,s->world_group.value);
        s->custom_present=pack(&p,1);need(&p,s->custom_present<=1,COH_INVALID);
        if(s->custom_present&&p.status==COH_OK){CohEntFailure f;p.status=coh_ent_custom_costume(&p.r,&s->custom,&f);if(p.status!=COH_OK){p.stage=f.stage;p.r.cursor=f.bit;}}
    }
    if(p.status!=COH_OK)return failed(&p,failure);
    s->end_bit=p.r.cursor;*out=*s;*r=p.r;if(failure)memset(failure,0,sizeof(*failure));return COH_OK;
}
static uint32_t auto_bits(Parse *p){static const unsigned widths[]={2,10,24,32};uint32_t n=bits(p,2);return p->status==COH_OK?bits(p,widths[n]):0;}
static void power_list(Parse *p,CohEntPowerCustomEnvelope *s,uint32_t n){
    CohEntPowerCustomRange *range=&s->lists[n];uint32_t i;
    range->present=bits(p,1);range->first=s->item_count;
    if(range->present){
        range->count=auto_bits(p);need(p,range->count<=COH_POWER_CUSTOM_LIST_MAX&&range->count<=COH_POWER_CUSTOM_TOTAL_MAX-s->item_count,COH_LIMIT);
        for(i=0;i<range->count&&p->status==COH_OK;i++){
            CohEntPowerCustom *item=&s->items[s->item_count++];
            item->power_crc=auto_bits(p);item->colors[0]=auto_bits(p);item->colors[1]=auto_bits(p);text(p,item->token);
        }
    }
    range->end_bit=p->r.cursor;
}
CohStatus coh_ent_power_custom(CohRepReader *r,int self,CohEntPowerCustomWorkspace *w,CohEntPowerCustomEnvelope *out,CohEntFailure *failure){
    Parse p;CohEntPowerCustomEnvelope *s;uint32_t unused,i;
    if(!r||(self!=0&&self!=1)||!w||!out||out==&w->candidate)return COH_INVALID;
    p=(Parse){*r,COH_OK,COH_ENT_STAGE_POWER_CUSTOM};p.status=coh_rep_read(&p.r,0,&unused);if(p.status!=COH_OK)return failed(&p,failure);
    memset(w,0,sizeof(*w));s=&w->candidate;s->type=bits(&p,1)?pack(&p,2):0;need(&p,s->type<=2,COH_UNSUPPORTED);
    if(s->type==1){
        s->is_self=bits(&p,1);need(&p,s->is_self==(uint32_t)self,COH_STATE);
        if(s->is_self){
            s->current_slot=bits(&p,8);s->additional_slots=bits(&p,8);need(&p,s->current_slot<COH_COSTUME_STORED_MAX,COH_LIMIT);
            s->multiple=bits(&p,1);s->list_count=s->multiple?bits(&p,4):1;
            need(&p,s->list_count>0&&s->list_count<=COH_COSTUME_STORED_MAX,COH_LIMIT);if(s->multiple)need(&p,s->current_slot<s->list_count,COH_LIMIT);
        }
    }else if(s->type==2)s->list_count=1;
    for(i=0;i<s->list_count&&p.status==COH_OK;i++)power_list(&p,s,i);
    if(p.status!=COH_OK)return failed(&p,failure);
    s->end_bit=p.r.cursor;*out=*s;*r=p.r;if(failure)memset(failure,0,sizeof(*failure));return COH_OK;
}
