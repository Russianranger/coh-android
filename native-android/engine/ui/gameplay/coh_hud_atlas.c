#include "coh_hud_atlas.h"
#include <math.h>
static int scalar(uint32_t c){return c<=0x10ffffu&&!(c>=0xd800u&&c<=0xdfffu)&&c>=32&&c!=127;}
static int metric(float x){return isfinite(x)&&x>=0&&x<=4096;}
CohStatus coh_hud_atlas_validate(const CohHudAtlas *a){
    size_t i;
    if(!a||!a->font_id||!isfinite(a->design_size)||a->design_size<1||a->design_size>256||
       !a->entries||!a->count||a->count>COH_HUD_ATLAS_GLYPHS)return COH_INVALID;
    for(i=0;i<a->count;i++){
        const CohHudAtlasEntry *e=a->entries+i;const CohUiGlyph *g=&e->glyph;
        if(!scalar(e->codepoint)||(i&&a->entries[i-1].codepoint>=e->codepoint)||
           !metric(g->width)||!metric(g->height)||!metric(g->advance)||
           !isfinite(g->bearing_x)||!isfinite(g->bearing_y)||fabsf(g->bearing_x)>4096||fabsf(g->bearing_y)>4096||
           !isfinite(g->uv.x)||!isfinite(g->uv.y)||!isfinite(g->uv.w)||!isfinite(g->uv.h)||
           g->uv.x<0||g->uv.y<0||g->uv.w<0||g->uv.h<0||g->uv.x+g->uv.w>1||g->uv.y+g->uv.h>1||
           (g->width>0&&g->height>0&&!g->resource_id))return COH_INVALID;
    }
    if(a->fallback_codepoint){
        for(i=0;i<a->count;i++)if(a->entries[i].codepoint==a->fallback_codepoint)return COH_OK;
        return COH_INVALID;
    }
    return COH_OK;
}
CohStatus coh_hud_atlas_glyph(void *context,uint32_t font,uint32_t cp,float size,CohUiGlyph *out){
    CohHudAtlas *a=context;size_t lo=0,hi;float scale;
    if(!a||!out||!isfinite(size)||size<1||size>256||font!=a->font_id||!a->entries||
       !a->count||a->count>COH_HUD_ATLAS_GLYPHS||!isfinite(a->design_size)||a->design_size<1)return COH_INVALID;
    hi=a->count;while(lo<hi){size_t mid=lo+(hi-lo)/2;if(a->entries[mid].codepoint<cp)lo=mid+1;else hi=mid;}
    if(lo==a->count||a->entries[lo].codepoint!=cp){
        if(!a->fallback_codepoint||cp==a->fallback_codepoint)return COH_NOT_FOUND;
        return coh_hud_atlas_glyph(context,font,a->fallback_codepoint,size,out);
    }
    *out=a->entries[lo].glyph;scale=size/a->design_size;
    out->width*=scale;out->height*=scale;out->advance*=scale;out->bearing_x*=scale;out->bearing_y*=scale;
    return COH_OK;
}
