#ifndef COH_SUPPORT_UI_H
#define COH_SUPPORT_UI_H
#include "../../engine/ui/coh_hud.h"
#include "../../engine/ui/gameplay/coh_hud_gles.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct SupportUi SupportUi;
typedef struct {
    CohHudStats hud;CohUiStats widgets;CohHudGlesStats gpu;
    uint64_t intents_processed,power_uses,chat_submits,character_selections,target_clicks,
             menu_opens,menu_closes,intent_history_drops,surface_losses;
    uint32_t generation,last_power,last_character;
    int keyboard_requested,last_status;size_t arena_bytes;
    char chat_input[COH_UI_TEXT],last_intent[COH_UI_TEXT];
} SupportUiStats;
/* One initialization-time allocation. This is an OFFLINE mock HUD, not a
 * session adapter. Character choices are data only; scene remains Wretch. */
SupportUi *support_ui_create(void);
/* Call context_destroy on its GL thread first, or context_lost after actual
 * context loss. This destructor owns CPU memory only and never calls GL. */
void support_ui_destroy(SupportUi *ui);
CohStatus support_ui_surface(SupportUi *ui,uint32_t generation,int width,int height,CohHudInsets safe);
CohStatus support_ui_context_create(SupportUi *ui,uint32_t generation);
void support_ui_context_destroy(SupportUi *ui); /* same current GL context */
void support_ui_context_lost(SupportUi *ui); /* context gone; no GL calls */
CohStatus support_ui_draw(SupportUi *ui,int width,int height,uint32_t generation);
/* Android touch routing is separate from operation status. Only focusable HUD
 * hit targets acquire capture. Once acquired, consume all pointer events until
 * release/cancel, including an UP/CANCEL that clears capture. Background touches
 * report consumed=0 (their UP may return COH_STATE because no capture exists).
 * The caller preserves/cancels its scene gesture when HUD capture takes over. */
CohStatus support_ui_pointer(SupportUi *ui,int masked_action,uint32_t pointer,float x,float y,int *consumed);
CohStatus support_ui_touch(SupportUi *ui,int masked_action,uint32_t pointer,float x,float y);
CohStatus support_ui_key(SupportUi *ui,int keycode,int action,int repeat,int shift);
CohStatus support_ui_text(SupportUi *ui,const char *committed_utf8); /* append committed text */
CohStatus support_ui_composing(SupportUi *ui,const char *utf8);
CohStatus support_ui_focus_chat(SupportUi *ui); /* optional Android chat/IME affordance */
CohStatus support_ui_submit(SupportUi *ui);
int support_ui_keyboard_requested(SupportUi *ui);
/* Monotonic elapsed ms supplied by harness; this intentionally drives mock
 * health/endurance/recharge without a server. No real gameplay is simulated. */
CohStatus support_ui_tick_mock(SupportUi *ui,uint64_t elapsed_ms);
CohStatus support_ui_snapshot(SupportUi *ui,SupportUiStats *stats);
int support_ui_poll_intent(SupportUi *ui,CohHudIntent *intent);
#ifdef __cplusplus
}
#endif
#endif
