#include "coh_hud_gles.h"
#include <math.h>
static int rect(CohUiRect r){
    return isfinite(r.x)&&isfinite(r.y)&&isfinite(r.w)&&isfinite(r.h)&&fabsf(r.x)<=1000000&&fabsf(r.y)<=1000000&&
        r.w>=0&&r.h>=0&&r.w<=1000000&&r.h<=1000000;
}
CohStatus coh_hud_quad(const CohUiDraw *d,uint32_t gen,CohHudVertex out[6]){
    CohHudVertex v;float x,y,u,w;static const unsigned index[6]={0,1,2,0,2,3};size_t i;
    if(!d||!out||!gen||d->surface_generation!=gen||d->kind<COH_UI_DRAW_RECT||d->kind>COH_UI_DRAW_GLYPH||
       !rect(d->rect)||!rect(d->clip)||!rect(d->uv)||d->uv.x<0||d->uv.y<0||d->uv.x+d->uv.w>1||d->uv.y+d->uv.h>1||
       (d->kind!=COH_UI_DRAW_RECT&&!d->resource_id))return COH_INVALID;
    v.r=(float)((d->color>>24)&255u)/255;v.g=(float)((d->color>>16)&255u)/255;
    v.b=(float)((d->color>>8)&255u)/255;v.a=(float)(d->color&255u)/255;
    for(i=0;i<6;i++){
        unsigned corner=index[i];x=corner==1||corner==2?1.0f:0.0f;y=corner>=2?1.0f:0.0f;u=x;w=y;
        v.x=d->rect.x+x*d->rect.w;v.y=d->rect.y+y*d->rect.h;
        v.u=d->uv.x+u*d->uv.w;v.v=d->uv.y+w*d->uv.h;out[i]=v;
    }return COH_OK;
}
CohStatus coh_hud_scissor(CohUiRect clip,int width,int height,int out[4]){
    float left,top,right,bottom;
    if(!out||width<1||height<1||width>32768||height>32768||!rect(clip))return COH_INVALID;
    left=floorf(fminf((float)width,fmaxf(0,clip.x)));
    right=ceilf(fminf((float)width,fmaxf(0,clip.x+clip.w)));
    top=floorf(fminf((float)height,fmaxf(0,clip.y)));
    bottom=ceilf(fminf((float)height,fmaxf(0,clip.y+clip.h)));
    out[0]=(int)left;out[1]=height-(int)bottom;out[2]=(int)(right-left);out[3]=(int)(bottom-top);
    return COH_OK;
}
