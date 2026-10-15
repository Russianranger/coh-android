#ifndef COH_UI_H
#define COH_UI_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Caller-owned fixed arenas: zero allocation after init, single owner thread. */
#define COH_UI_WIDGETS 128u
#define COH_UI_TEXT 256u
#define COH_UI_DRAWS 4096u
#define COH_UI_EVENTS 64u
#define COH_UI_BASE_WIDTH 1024.0f
#define COH_UI_BASE_HEIGHT 768.0f
typedef struct { float x,y,w,h; } CohUiRect;
typedef enum { COH_UI_PANEL, COH_UI_WINDOW, COH_UI_LABEL, COH_UI_BUTTON,
               COH_UI_INPUT, COH_UI_ICON, COH_UI_PROGRESS } CohUiKind;
typedef enum { COH_UI_SCALE_XY, COH_UI_SCALE_NONE, COH_UI_SCALE_FIT } CohUiScale;
enum { COH_UI_VISIBLE=1u, COH_UI_ENABLED=2u, COH_UI_FOCUSABLE=4u };
typedef struct {
    uint32_t id, parent, binding; CohUiKind kind; uint32_t flags;
    CohUiRect rect; float anchor_x,anchor_y; /* 0=left/top, .5=center, 1=right/bottom */
    uint32_t color,text_color,resource_id,font_id; /* straight 0xRRGGBBAA; resource IDs are NOT GL handles */
    float font_size; /* logical pixels; text clipped to widget; no automatic wrapping */
} CohUiDesc;
typedef struct {
    uint32_t resource_id; CohUiRect uv;
    float width,height,bearing_x,bearing_y,advance; /* logical-pixel font metrics */
} CohUiGlyph;
/* Synchronous borrowed result. Must not mutate/reenter UI. Font/atlas work is outside GL draw consumption. */
typedef CohStatus (*CohUiGlyphFn)(void *context,uint32_t font_id,uint32_t codepoint,float logical_size,CohUiGlyph *glyph);
typedef enum { COH_UI_DRAW_RECT, COH_UI_DRAW_IMAGE, COH_UI_DRAW_GLYPH } CohUiDrawKind;
typedef struct {
    CohUiDrawKind kind; uint32_t widget,resource_id,color;
    CohUiRect rect,uv,clip; uint32_t surface_generation;
} CohUiDraw;
typedef enum { COH_UI_EVENT_FOCUS,COH_UI_EVENT_ACTIVATE,COH_UI_EVENT_TEXT,COH_UI_EVENT_SUBMIT } CohUiEventKind;
typedef struct { CohUiEventKind kind; uint32_t widget,binding; } CohUiEvent;
typedef enum { COH_UI_TOUCH_DOWN,COH_UI_TOUCH_UP,COH_UI_TOUCH_CANCEL } CohUiTouch;
typedef enum { COH_UI_NEXT,COH_UI_PREVIOUS,COH_UI_UP,COH_UI_DOWN,COH_UI_LEFT,
               COH_UI_RIGHT,COH_UI_ACTIVATE,COH_UI_BACKSPACE,COH_UI_SUBMIT,COH_UI_CANCEL } CohUiAction;
typedef struct {
    CohUiDesc desc; char text[COH_UI_TEXT]; float value;
    CohUiRect logical,pixels,clip; uint8_t effective_visible,effective_enabled;
} CohUiWidget;
typedef struct {
    uint64_t layouts,frames,draw_limit_hits,event_limit_hits,rejected_text,missing_glyphs;
    size_t arena_bytes,widget_high_water,draw_high_water,event_high_water;
} CohUiStats;
typedef struct {
    CohUiWidget widgets[COH_UI_WIDGETS]; CohUiDraw draws[COH_UI_DRAWS]; CohUiEvent events[COH_UI_EVENTS];
    size_t widget_count,draw_count,event_count;
    uint32_t focus,capture,capture_pointer,surface_generation;
    float width,height,scale_x,scale_y,offset_x,offset_y;
    CohUiScale scaling; int surface_ready,dirty,draw_ready;
    CohUiGlyphFn glyph; void *glyph_context; CohUiStats stats;
} CohUi;

void coh_ui_init(CohUi *ui,CohUiScale scaling,CohUiGlyphFn glyph,void *context);
void coh_ui_destroy(CohUi *ui); /* idempotent; borrowed glyph backend remains caller-owned */
CohStatus coh_ui_add(CohUi *ui,const CohUiDesc *desc,const char *utf8);
CohStatus coh_ui_remove(CohUi *ui,uint32_t id); /* removes entire subtree */
CohStatus coh_ui_set_flags(CohUi *ui,uint32_t id,uint32_t flags);
CohStatus coh_ui_set_rect(CohUi *ui,uint32_t id,CohUiRect rect);
CohStatus coh_ui_set_text(CohUi *ui,uint32_t id,const char *utf8);
const CohUiWidget *coh_ui_widget(const CohUi *ui,uint32_t id);
/* Binding updates are transactional; one binding can drive several widgets. */
CohStatus coh_ui_bind_text(CohUi *ui,uint32_t binding,const char *utf8);
CohStatus coh_ui_bind_value(CohUi *ui,uint32_t binding,float normalized_value);
CohStatus coh_ui_bind_enabled(CohUi *ui,uint32_t binding,int enabled);
/* Generation is nonzero and changes on recreation. Loss invalidates drawlist, never logical state. */
CohStatus coh_ui_surface(CohUi *ui,uint32_t generation,float width,float height);
void coh_ui_surface_lost(CohUi *ui);
CohStatus coh_ui_layout(CohUi *ui);
CohStatus coh_ui_build(CohUi *ui); /* on failure draw_count=0; complete list or no list */
int coh_ui_drawlist_valid(const CohUi *ui,uint32_t generation);
CohStatus coh_ui_focus(CohUi *ui,uint32_t id); /* id 0 releases focus */
CohStatus coh_ui_touch(CohUi *ui,CohUiTouch action,uint32_t pointer,float pixel_x,float pixel_y);
CohStatus coh_ui_action(CohUi *ui,CohUiAction action);
CohStatus coh_ui_text_commit(CohUi *ui,const char *utf8); /* valid scalar UTF-8; append; single line */
int coh_ui_keyboard_requested(const CohUi *ui);
int coh_ui_poll(CohUi *ui,CohUiEvent *event);
/* UTF-8 validator is public for Android IME boundary; output length only written on success. */
CohStatus coh_ui_utf8(const char *text,int single_line,size_t *bytes);
#ifdef __cplusplus
}
#endif
#endif
