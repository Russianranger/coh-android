#include "coh_ui.h"
#include <float.h>
#include <math.h>
#include <string.h>

static int finite_rect(CohUiRect r) {
    return isfinite(r.x)&&isfinite(r.y)&&isfinite(r.w)&&isfinite(r.h)&&
        fabsf(r.x)<=1000000&&fabsf(r.y)<=1000000&&r.w>=0&&r.h>=0&&r.w<=1000000&&r.h<=1000000;
}
static CohUiWidget *find(CohUi *u,uint32_t id) {
    size_t i; if(!u||!id)return NULL;
    for(i=0;i<u->widget_count;i++)if(u->widgets[i].desc.id==id)return &u->widgets[i];
    return NULL;
}
const CohUiWidget *coh_ui_widget(const CohUi *u,uint32_t id) {
    size_t i; if(!u||!id)return NULL;
    for(i=0;i<u->widget_count;i++)if(u->widgets[i].desc.id==id)return &u->widgets[i];
    return NULL;
}
static int descendant(CohUi *u,uint32_t id,uint32_t parent) {
    size_t i; CohUiWidget *w;
    for(i=0;id&&i<COH_UI_WIDGETS;i++) {
        if(id==parent)return 1;
        w=find(u,id); if(!w)return 0; id=w->desc.parent;
    }
    return 0;
}
static CohUiRect intersect(CohUiRect a,CohUiRect b) {
    float x=fmaxf(a.x,b.x),y=fmaxf(a.y,b.y);
    CohUiRect r={x,y,fmaxf(0,fminf(a.x+a.w,b.x+b.w)-x),fmaxf(0,fminf(a.y+a.h,b.y+b.h)-y)};
    return r;
}
static int inside(CohUiRect r,float x,float y) {
    /* Original CBox is inclusive. Android permits touches at x/y=0. */
    return r.w>0&&r.h>0&&x>=r.x&&x<=r.x+r.w&&y>=r.y&&y<=r.y+r.h;
}
static uint32_t decode(const unsigned char *s,size_t n,size_t *used) {
    uint32_t cp; size_t i,k;
    if(!n)return UINT32_MAX;
    if(s[0]<0x80){*used=1;return s[0];}
    if(s[0]>=0xc2&&s[0]<=0xdf){k=2;cp=s[0]&31u;}
    else if(s[0]>=0xe0&&s[0]<=0xef){k=3;cp=s[0]&15u;}
    else if(s[0]>=0xf0&&s[0]<=0xf4){k=4;cp=s[0]&7u;}
    else return UINT32_MAX;
    if(k>n)return UINT32_MAX;
    for(i=1;i<k;i++){if((s[i]&0xc0u)!=0x80u)return UINT32_MAX;cp=(cp<<6)|(s[i]&63u);}
    if((k==2&&cp<128)||(k==3&&cp<2048)||(k==4&&cp<65536)||
       (cp>=0xd800&&cp<=0xdfff)||cp>0x10ffff)return UINT32_MAX;
    *used=k;return cp;
}
CohStatus coh_ui_utf8(const char *s,int single,size_t *bytes) {
    size_t n=0,i=0,k=0; uint32_t cp;
    if(!s)return COH_INVALID;
    while(n<COH_UI_TEXT&&s[n])n++;
    if(n==COH_UI_TEXT)return COH_LIMIT;
    while(i<n){cp=decode((const unsigned char *)s+i,n-i,&k);
        if(cp==UINT32_MAX||cp==127||(cp<32&&(single||(cp!='\n'&&cp!='\t'))))return COH_INVALID;
        i+=k;
    }
    if(bytes)*bytes=n;
    return COH_OK;
}
static void invalidate(CohUi *u){u->dirty=1;u->draw_count=0;u->draw_ready=0;}
static CohStatus room(CohUi *u,size_t n){
    if(n>COH_UI_EVENTS-u->event_count){u->stats.event_limit_hits++;return COH_LIMIT;}
    return COH_OK;
}
static void event(CohUi *u,CohUiEventKind kind,uint32_t id) {
    CohUiWidget *w=find(u,id); CohUiEvent *e=&u->events[u->event_count++];
    e->kind=kind;e->widget=id;e->binding=w?w->desc.binding:0;
    if(u->event_count>u->stats.event_high_water)u->stats.event_high_water=u->event_count;
}
static int focusable(const CohUiWidget *w){return w&&w->effective_visible&&w->effective_enabled&&w->clip.w>0&&w->clip.h>0&&(w->desc.flags&COH_UI_FOCUSABLE);}
void coh_ui_init(CohUi *u,CohUiScale scaling,CohUiGlyphFn glyph,void *ctx) {
    if(!u)return;
    memset(u,0,sizeof(*u));u->scaling=scaling;u->glyph=glyph;u->glyph_context=ctx;u->dirty=1;u->stats.arena_bytes=sizeof(*u);
}
void coh_ui_destroy(CohUi *u){if(u)memset(u,0,sizeof(*u));}
CohStatus coh_ui_add(CohUi *u,const CohUiDesc *d,const char *text) {
    CohUiWidget *w; size_t n; CohStatus s;
    if(!u||!d||!d->id||find(u,d->id)||d->kind<COH_UI_PANEL||d->kind>COH_UI_PROGRESS||
       (d->flags&~7u)||!finite_rect(d->rect)||!isfinite(d->anchor_x)||!isfinite(d->anchor_y)||
       d->anchor_x<0||d->anchor_x>1||d->anchor_y<0||d->anchor_y>1||
       !isfinite(d->font_size)||d->font_size<1||d->font_size>256)return COH_INVALID;
    if(d->parent&&!find(u,d->parent))return COH_NOT_FOUND;
    s=coh_ui_utf8(text?text:"",d->kind==COH_UI_INPUT,&n);if(s!=COH_OK)return s;
    if(u->widget_count==COH_UI_WIDGETS)return COH_LIMIT;
    w=&u->widgets[u->widget_count++];memset(w,0,sizeof(*w));w->desc=*d;
    memcpy(w->text,text?text:"",n+1);invalidate(u);
    if(u->widget_count>u->stats.widget_high_water)u->stats.widget_high_water=u->widget_count;
    return COH_OK;
}
CohStatus coh_ui_remove(CohUi *u,uint32_t id) {
    size_t i; uint32_t ids[COH_UI_WIDGETS];size_t count=0,j;
    if(!find(u,id))return COH_NOT_FOUND;
    for(i=0;i<u->widget_count;i++)if(descendant(u,u->widgets[i].desc.id,id))ids[count++]=u->widgets[i].desc.id;
    for(j=0;j<count;j++){
        if(u->focus==ids[j])u->focus=0;
        if(u->capture==ids[j])u->capture=0;
        for(i=0;i<u->widget_count;i++)if(u->widgets[i].desc.id==ids[j]){
            memmove(&u->widgets[i],&u->widgets[i+1],(--u->widget_count-i)*sizeof(u->widgets[0]));break;
        }
    }
    /* Prune removed IDs so a caller can safely reuse an ID after removal. */
    for(i=0;i<u->event_count;){
        int removed=0;
        for(j=0;j<count;j++)if(u->events[i].widget==ids[j]){removed=1;break;}
        if(removed)memmove(u->events+i,u->events+i+1,(--u->event_count-i)*sizeof(u->events[0]));
        else i++;
    }
    invalidate(u);return COH_OK;
}
CohStatus coh_ui_set_flags(CohUi *u,uint32_t id,uint32_t flags) {
    CohUiWidget *w=find(u,id);if(!w)return COH_NOT_FOUND;if(flags&~7u)return COH_INVALID;
    w->desc.flags=flags;invalidate(u);return COH_OK;
}
CohStatus coh_ui_set_rect(CohUi *u,uint32_t id,CohUiRect r){
    CohUiWidget *w=find(u,id);if(!w)return COH_NOT_FOUND;if(!finite_rect(r))return COH_INVALID;
    w->desc.rect=r;invalidate(u);return COH_OK;
}
CohStatus coh_ui_set_text(CohUi *u,uint32_t id,const char *text){
    CohUiWidget *w=find(u,id);CohStatus s;size_t n;if(!w)return COH_NOT_FOUND;
    s=coh_ui_utf8(text,w->desc.kind==COH_UI_INPUT,&n);if(s!=COH_OK)return s;
    memmove(w->text,text,n+1);invalidate(u);return COH_OK;
}
CohStatus coh_ui_bind_text(CohUi *u,uint32_t binding,const char *text) {
    size_t i,n;int found=0,single=0;CohStatus s;
    if(!u||!binding)return COH_INVALID;
    for(i=0;i<u->widget_count;i++)if(u->widgets[i].desc.binding==binding){found=1;if(u->widgets[i].desc.kind==COH_UI_INPUT)single=1;}
    if(!found)return COH_NOT_FOUND;
    s=coh_ui_utf8(text,single,&n);if(s!=COH_OK)return s;
    for(i=0;i<u->widget_count;i++)if(u->widgets[i].desc.binding==binding)memmove(u->widgets[i].text,text,n+1);
    invalidate(u);return COH_OK;
}
CohStatus coh_ui_bind_value(CohUi *u,uint32_t binding,float value){
    size_t i;int found=0;if(!u||!binding||!isfinite(value))return COH_INVALID;
    value=fminf(1,fmaxf(0,value));
    for(i=0;i<u->widget_count;i++)if(u->widgets[i].desc.binding==binding){u->widgets[i].value=value;found=1;}
    if(found)invalidate(u);
    return found?COH_OK:COH_NOT_FOUND;
}
CohStatus coh_ui_bind_enabled(CohUi *u,uint32_t binding,int enabled){
    size_t i;int found=0;if(!u||!binding)return COH_INVALID;
    for(i=0;i<u->widget_count;i++)if(u->widgets[i].desc.binding==binding){
        if(enabled)u->widgets[i].desc.flags|=COH_UI_ENABLED;else u->widgets[i].desc.flags&=~COH_UI_ENABLED;found=1;
    }
    if(found)invalidate(u);
    return found?COH_OK:COH_NOT_FOUND;
}
CohStatus coh_ui_surface(CohUi *u,uint32_t generation,float width,float height){
    float x,y;
    if(!u||!generation||!isfinite(width)||!isfinite(height)||width<1||height<1||width>32768||height>32768||
       u->scaling<COH_UI_SCALE_XY||u->scaling>COH_UI_SCALE_FIT)return COH_INVALID;
    x=width/COH_UI_BASE_WIDTH;y=height/COH_UI_BASE_HEIGHT;u->offset_x=u->offset_y=0;
    if(u->scaling==COH_UI_SCALE_NONE)x=y=1;
    if(u->scaling==COH_UI_SCALE_FIT){x=y=fminf(x,y);u->offset_x=(width-x*COH_UI_BASE_WIDTH)*.5f;u->offset_y=(height-y*COH_UI_BASE_HEIGHT)*.5f;}
    u->width=width;u->height=height;u->scale_x=x;u->scale_y=y;u->surface_generation=generation;u->surface_ready=1;
    invalidate(u);return COH_OK;
}
void coh_ui_surface_lost(CohUi *u){if(u){u->surface_ready=0;u->draw_count=0;u->draw_ready=0;u->capture=0;}}
CohStatus coh_ui_layout(CohUi *u){
    size_t i; CohUiRect screen;
    if(!u||!u->surface_ready)return COH_STATE;
    if(!u->dirty)return COH_OK;
    screen=(CohUiRect){0,0,u->width,u->height};
    for(i=0;i<u->widget_count;i++){
        CohUiWidget *w=&u->widgets[i],*p=find(u,w->desc.parent);
        CohUiRect parent=p?p->logical:(CohUiRect){0,0,COH_UI_BASE_WIDTH,COH_UI_BASE_HEIGHT};
        w->logical=w->desc.rect;
        w->logical.x+=parent.x+w->desc.anchor_x*(parent.w-w->logical.w);
        w->logical.y+=parent.y+w->desc.anchor_y*(parent.h-w->logical.h);
        w->pixels=(CohUiRect){u->offset_x+w->logical.x*u->scale_x,u->offset_y+w->logical.y*u->scale_y,w->logical.w*u->scale_x,w->logical.h*u->scale_y};
        w->clip=intersect(p?p->clip:screen,w->pixels);
        w->effective_visible=(uint8_t)((w->desc.flags&COH_UI_VISIBLE)&&(!p||p->effective_visible));
        w->effective_enabled=(uint8_t)((w->desc.flags&COH_UI_ENABLED)&&(!p||p->effective_enabled));
    }
    if(!focusable(find(u,u->focus)))u->focus=0;
    if(!focusable(find(u,u->capture)))u->capture=0;
    u->dirty=0;u->stats.layouts++;return COH_OK;
}
static CohStatus draw(CohUi *u,const CohUiWidget *w,CohUiDrawKind kind,CohUiRect rect,CohUiRect uv,uint32_t resource,uint32_t color){
    CohUiDraw *d;
    if(rect.w<=0||rect.h<=0||w->clip.w<=0||w->clip.h<=0)return COH_OK;
    if(u->draw_count==COH_UI_DRAWS){u->stats.draw_limit_hits++;return COH_LIMIT;}
    d=&u->draws[u->draw_count++];d->kind=kind;d->widget=w->desc.id;d->resource_id=resource;d->color=color;
    d->rect=rect;d->uv=uv;d->clip=w->clip;d->surface_generation=u->surface_generation;
    return COH_OK;
}
static CohStatus text_draw(CohUi *u,const CohUiWidget *w){
    size_t n=strlen(w->text),i=0,k=0;float x=0,y=0;uint32_t cp;CohStatus s;
    if(!n)return COH_OK;
    if(!u->glyph){u->stats.missing_glyphs+=n;return COH_UNSUPPORTED;}
    while(i<n){
        CohUiGlyph g;CohUiRect r;cp=decode((const unsigned char *)w->text+i,n-i,&k);i+=k;
        if(cp=='\n'){x=0;y+=w->desc.font_size;continue;}
        if(cp=='\t'){x+=w->desc.font_size*2;continue;}
        memset(&g,0,sizeof(g));s=u->glyph(u->glyph_context,w->desc.font_id,cp,w->desc.font_size,&g);
        if(s!=COH_OK){u->stats.missing_glyphs++;return s;}
        if(!finite_rect(g.uv)||g.uv.x<0||g.uv.y<0||g.uv.x+g.uv.w>1||g.uv.y+g.uv.h>1||
           !isfinite(g.width)||!isfinite(g.height)||!isfinite(g.bearing_x)||!isfinite(g.bearing_y)||!isfinite(g.advance)||
           fabsf(g.bearing_x)>4096||fabsf(g.bearing_y)>4096||g.width<0||g.width>4096||g.height<0||g.height>4096||g.advance<0||g.advance>4096||
           (g.width>0&&g.height>0&&!g.resource_id))return COH_INVALID;
        r=(CohUiRect){w->pixels.x+(x+g.bearing_x)*u->scale_x,w->pixels.y+(y+g.bearing_y)*u->scale_y,g.width*u->scale_x,g.height*u->scale_y};
        s=draw(u,w,COH_UI_DRAW_GLYPH,r,g.uv,g.resource_id,w->desc.text_color);if(s!=COH_OK)return s;
        x+=g.advance;
    }
    return COH_OK;
}
CohStatus coh_ui_build(CohUi *u){
    size_t i;CohStatus s=coh_ui_layout(u);CohUiRect uv={0,0,1,1};
    if(!u)return COH_INVALID;
    u->draw_count=0;u->draw_ready=0;if(s!=COH_OK)return s;
    for(i=0;i<u->widget_count;i++){
        CohUiWidget *w=&u->widgets[i];if(!w->effective_visible)continue;
        if(w->desc.kind!=COH_UI_LABEL){
            CohUiRect r=w->pixels;if(w->desc.kind==COH_UI_PROGRESS)r.w*=w->value;
            s=draw(u,w,w->desc.kind==COH_UI_ICON?COH_UI_DRAW_IMAGE:COH_UI_DRAW_RECT,r,uv,w->desc.resource_id,w->desc.color);
            if(s!=COH_OK)goto fail;
        }
        s=text_draw(u,w);if(s!=COH_OK)goto fail;
        if(w->desc.id==u->focus){
            CohUiRect r=w->pixels;float line=fminf(2,fminf(r.w,r.h)*.5f);
            CohUiRect edges[4]={{r.x,r.y,r.w,line},{r.x,r.y+r.h-line,r.w,line},{r.x,r.y,line,r.h},{r.x+r.w-line,r.y,line,r.h}};
            size_t j;
            for(j=0;j<4;j++){s=draw(u,w,COH_UI_DRAW_RECT,edges[j],uv,0,w->desc.text_color);if(s!=COH_OK)goto fail;}
        }
    }
    if(u->draw_count>u->stats.draw_high_water)u->stats.draw_high_water=u->draw_count;
    u->draw_ready=1;u->stats.frames++;return COH_OK;
fail:u->draw_count=0;return s;
}
int coh_ui_drawlist_valid(const CohUi *u,uint32_t generation){return u&&u->surface_ready&&u->draw_ready&&!u->dirty&&u->surface_generation==generation;}
CohStatus coh_ui_focus(CohUi *u,uint32_t id){
    CohStatus s=coh_ui_layout(u);if(s!=COH_OK)return s;
    if(id&&!focusable(find(u,id)))return COH_STATE;
    if(u->focus==id)return COH_OK;
    s=room(u,1);if(s!=COH_OK)return s;
    u->focus=id;u->draw_ready=0;u->draw_count=0;event(u,COH_UI_EVENT_FOCUS,id);return COH_OK;
}
CohStatus coh_ui_touch(CohUi *u,CohUiTouch action,uint32_t pointer,float x,float y){
    size_t i; CohUiWidget *w=NULL;CohStatus s=coh_ui_layout(u);
    if(s!=COH_OK)return s;
    if(!isfinite(x)||!isfinite(y)||action<COH_UI_TOUCH_DOWN||action>COH_UI_TOUCH_CANCEL)return COH_INVALID;
    if(action==COH_UI_TOUCH_CANCEL){if(u->capture&&u->capture_pointer==pointer)u->capture=0;return COH_OK;}
    if(action==COH_UI_TOUCH_DOWN){
        if(u->capture)return COH_STATE;
        for(i=u->widget_count;i>0;i--)if(focusable(&u->widgets[i-1])&&inside(u->widgets[i-1].clip,x,y)){w=&u->widgets[i-1];break;}
        s=coh_ui_focus(u,w?w->desc.id:0);if(s!=COH_OK)return s;
        if(w){u->capture=w->desc.id;u->capture_pointer=pointer;}return COH_OK;
    }
    if(!u->capture||u->capture_pointer!=pointer)return COH_STATE;
    w=find(u,u->capture);
    if(w&&inside(w->clip,x,y)&&w->desc.kind!=COH_UI_INPUT){
        s=room(u,1);u->capture=0;if(s!=COH_OK)return s;event(u,COH_UI_EVENT_ACTIVATE,w->desc.id);
    }else u->capture=0;
    return COH_OK;
}
CohStatus coh_ui_text_commit(CohUi *u,const char *text){
    CohUiWidget *w;CohStatus s;size_t n,len;
    s=coh_ui_layout(u);if(s!=COH_OK)return s;
    w=find(u,u->focus);if(!w||w->desc.kind!=COH_UI_INPUT)return COH_STATE;
    s=coh_ui_utf8(text,1,&n);if(s!=COH_OK){u->stats.rejected_text++;return s;}
    len=strlen(w->text);if(n>COH_UI_TEXT-1-len){u->stats.rejected_text++;return COH_LIMIT;}
    if(!n)return COH_OK;
    s=room(u,1);if(s!=COH_OK)return s;
    memmove(w->text+len,text,n+1);event(u,COH_UI_EVENT_TEXT,w->desc.id);invalidate(u);return COH_OK;
}
CohStatus coh_ui_action(CohUi *u,CohUiAction action){
    CohStatus s=coh_ui_layout(u);size_t i,n,start;CohUiWidget *w,*best=NULL;float score=FLT_MAX;
    if(s!=COH_OK)return s;
    if(action<COH_UI_NEXT||action>COH_UI_CANCEL)return COH_INVALID;
    w=find(u,u->focus);
    if(action==COH_UI_CANCEL){u->capture=0;return coh_ui_focus(u,0);}
    if(action==COH_UI_ACTIVATE||action==COH_UI_SUBMIT){
        if(!focusable(w))return COH_STATE;
        s=room(u,1);if(s!=COH_OK)return s;
        event(u,w->desc.kind==COH_UI_INPUT?COH_UI_EVENT_SUBMIT:COH_UI_EVENT_ACTIVATE,w->desc.id);return COH_OK;
    }
    if(action==COH_UI_BACKSPACE){
        if(!w||w->desc.kind!=COH_UI_INPUT)return COH_STATE;
        n=strlen(w->text);if(!n)return COH_OK;
        s=room(u,1);if(s!=COH_OK)return s;do{n--;}while(n&&(((unsigned char)w->text[n]&0xc0u)==0x80u));
        w->text[n]=0;event(u,COH_UI_EVENT_TEXT,w->desc.id);invalidate(u);return COH_OK;
    }
    if(action==COH_UI_NEXT||action==COH_UI_PREVIOUS||!w){
        n=u->widget_count;start=action==COH_UI_PREVIOUS?0:n-1;
        if(w)start=(size_t)(w-u->widgets);
        for(i=1;i<=n;i++){
            size_t j=action==COH_UI_PREVIOUS?(start+n-i)%n:(start+i)%n;
            if(focusable(&u->widgets[j]))return coh_ui_focus(u,u->widgets[j].desc.id);
        }
        return COH_NOT_FOUND;
    }
    for(i=0;i<u->widget_count;i++){
        CohUiWidget *c=&u->widgets[i];float dx,dy,main_axis,cross_axis,cost;
        if(c==w||!focusable(c))continue;
        dx=c->pixels.x+c->pixels.w*.5f-w->pixels.x-w->pixels.w*.5f;
        dy=c->pixels.y+c->pixels.h*.5f-w->pixels.y-w->pixels.h*.5f;
        main_axis=(action==COH_UI_LEFT?-dx:action==COH_UI_RIGHT?dx:action==COH_UI_UP?-dy:dy);
        cross_axis=(action==COH_UI_LEFT||action==COH_UI_RIGHT)?dy:dx;
        if(main_axis<=0)continue;
        cost=main_axis+fabsf(cross_axis)*2;
        if(cost<score){score=cost;best=c;}
    }
    return best?coh_ui_focus(u,best->desc.id):COH_NOT_FOUND;
}
int coh_ui_keyboard_requested(const CohUi *u){
    const CohUiWidget *w=coh_ui_widget(u,u?u->focus:0);
    /* Query only after layout/input on the owner thread. */
    return u&&u->surface_ready&&!u->dirty&&w&&focusable(w)&&w->desc.kind==COH_UI_INPUT;
}
int coh_ui_poll(CohUi *u,CohUiEvent *e){
    if(!u||!e||!u->event_count)return 0;
    *e=u->events[0];
    memmove(u->events,u->events+1,(--u->event_count)*sizeof(u->events[0]));return 1;
}
