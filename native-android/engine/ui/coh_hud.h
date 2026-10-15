#ifndef COH_HUD_H
#define COH_HUD_H
#include "coh_ui.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Opt-in native game HUD. All storage is caller-owned, all calls on one UI thread.
 * State snapshots and intents contain values, never session/entity pointers. */
#define COH_HUD_POWERS 10u
#define COH_HUD_CHARACTERS 8u
#define COH_HUD_CHAT_LINES 8u
#define COH_HUD_NAME 64u
#define COH_HUD_CHAT_TEXT 192u
#define COH_HUD_INTENTS 32u
enum {
    COH_HUD_BIND_HEALTH=34001, COH_HUD_BIND_ENDURANCE, COH_HUD_BIND_TARGET,
    COH_HUD_BIND_CHAT_INPUT, COH_HUD_BIND_CHARACTER_MENU,
    COH_HUD_BIND_POWER_FIRST=34100, COH_HUD_BIND_CHARACTER_FIRST=34200,
    COH_HUD_BIND_CHAT_FIRST=34300
};
typedef struct {
    uint32_t id,icon; char name[COH_HUD_NAME];
    float cooldown; /* normalized remaining; 0 = ready, 1 = full recharge */
    int enabled;
} CohHudPower;
typedef struct { uint32_t id; char name[COH_HUD_NAME]; int enabled; } CohHudCharacter;
typedef struct {
    uint64_t revision;
    uint32_t actor_id,target_id;
    char actor_name[COH_HUD_NAME],target_name[COH_HUD_NAME];
    float health,max_health,absorb,endurance,max_endurance,target_health,target_max_health;
    int in_phase,show_character_select;
    CohHudPower powers[COH_HUD_POWERS]; size_t power_count;
    CohHudCharacter characters[COH_HUD_CHARACTERS]; size_t character_count;
    char chat[COH_HUD_CHAT_LINES][COH_HUD_CHAT_TEXT]; size_t chat_count;
} CohHudState;
typedef struct { float left,top,right,bottom; } CohHudInsets;
/* IDs resolved by the caller's original-asset/atlas backend, never GL names. */
typedef struct { uint32_t font,status_frame,tray_frame,chat_frame,character_frame; } CohHudSkin;
typedef enum { COH_HUD_USE_POWER,COH_HUD_SEND_CHAT,COH_HUD_SELECT_CHARACTER,
               COH_HUD_OPEN_CHARACTER_MENU,COH_HUD_TARGET,COH_HUD_CLOSE_CHARACTER_MENU } CohHudIntentKind;
typedef struct {
    CohHudIntentKind kind; uint64_t revision; uint32_t actor_id,id,slot;
    char text[COH_UI_TEXT];
} CohHudIntent;
typedef struct {
    uint64_t state_updates,rejected_states,intents_emitted,intent_limit_hits,
             surface_losses,surface_recreates,builds;
    size_t arena_bytes,intent_high_water;
} CohHudStats;
typedef struct {
    CohUi ui; CohHudState state;
    CohHudIntent intents[COH_HUD_INTENTS]; size_t intent_count;
    CohHudInsets insets; float surface_width,surface_height;
    uint32_t tray_ring,tray_numbers[COH_HUD_POWERS];
    int initialized; CohHudStats stats;
} CohHud;

CohStatus coh_hud_init(CohHud *hud,CohUiGlyphFn glyph,void *glyph_context);
void coh_hud_destroy(CohHud *hud);
/* Transactional validation, copied state, no font/asset/GL work. */
CohStatus coh_hud_set_state(CohHud *hud,const CohHudState *state);
CohStatus coh_hud_set_skin(CohHud *hud,const CohHudSkin *skin);
/* Optional original tray artwork. Numbers are supplied in slot order 1..9,0,
 * matching source tray_drawSlot. Values are caller-owned resource IDs, never
 * GL handles; zero clears decoration. Copied once, retained across snapshots
 * and Surface recreation. Does not replace a power's own icon or emit intents. */
CohStatus coh_hud_set_tray_decoration(CohHud *hud,uint32_t ring,const uint32_t numbers[COH_HUD_POWERS]);
CohStatus coh_hud_surface(CohHud *hud,uint32_t generation,float width,float height,CohHudInsets safe);
void coh_hud_surface_lost(CohHud *hud);
CohStatus coh_hud_build(CohHud *hud);
/* Borrow only until the next call. Coordinates and clips include safe insets. */
const CohUiDraw *coh_hud_draws(const CohHud *hud,uint32_t generation,size_t *count);
CohStatus coh_hud_touch(CohHud *hud,CohUiTouch action,uint32_t pointer,float x,float y);
CohStatus coh_hud_action(CohHud *hud,CohUiAction action);
CohStatus coh_hud_text_commit(CohHud *hud,const char *utf8);
CohStatus coh_hud_focus(CohHud *hud,uint32_t binding);
int coh_hud_keyboard_requested(const CohHud *hud);
int coh_hud_poll(CohHud *hud,CohHudIntent *intent);
/* Original uiStatus.c threshold/interp_rgba behavior. Nonfinite input is rejected
 * by snapshot validation; these pure helpers return low colors for NaN. */
uint32_t coh_hud_health_color(int in_phase,float fraction);
uint32_t coh_hud_endurance_color(float fraction);
#ifdef __cplusplus
}
#endif
#endif
