#ifndef COH_PRESENTATION_H
#define COH_PRESENTATION_H
#include "../../coh_hud.h"
#include "../coh_hud_axis_navigation.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Offline presentation only. One caller-owned arena and one serialized owner.
 * No entity/session pointers, resource ownership, GL handles or network calls. */
#define COH_PRESENTATION_ROWS 8u
#define COH_PRESENTATION_EFFECTS 8u
#define COH_PRESENTATION_QUEUE 16u
typedef enum { COH_PRESENTATION_DETAILS, COH_PRESENTATION_INVENTORY,
    COH_PRESENTATION_ENHANCEMENTS, COH_PRESENTATION_MISSIONS,
    COH_PRESENTATION_CONTACTS, COH_PRESENTATION_TABS } CohPresentationTab;
typedef struct {
    uint32_t id, icon; char name[64], detail[128];
    float progress; /* finite 0..1; e.g. mission progress, never inferred */
    int enabled, completed;
} CohPresentationRow;
typedef struct {
    uint64_t revision; uint32_t actor_id, target_id, level;
    char name[64], archetype[64], origin[64], description[128];
    uint64_t influence;
    CohPresentationRow rows[4][COH_PRESENTATION_ROWS]; size_t counts[4];
} CohPresentationState;
typedef enum { COH_PRESENTATION_OPEN_TAB, COH_PRESENTATION_CLOSE,
    COH_PRESENTATION_INSPECT_ITEM, COH_PRESENTATION_INSPECT_ENHANCEMENT,
    COH_PRESENTATION_INSPECT_MISSION, COH_PRESENTATION_INSPECT_CONTACT } CohPresentationIntentKind;
typedef struct {
    CohPresentationIntentKind kind; uint64_t revision;
    uint32_t actor_id, id, slot; CohPresentationTab tab;
} CohPresentationIntent;
typedef enum { COH_PRESENTATION_ACTIVATE, COH_PRESENTATION_IMPACT } CohPresentationEventKind;
typedef struct {
    uint64_t sequence, revision, now_ms;
    CohPresentationEventKind kind; uint32_t actor_id,target_id,power_id;
    int32_t amount; /* signed source damage (-) or healing (+), never applies HP */
    int victim_is_self, damager_is_owned, absorb;
    float x,y; /* caller-projected logical 1024x768 screen coordinate */
    CohVec3 emitter; uint32_t audio_asset,animation_asset; /* 0 = unavailable */
} CohPresentationEvent;
typedef struct {
    uint64_t sequence, revision; CohPresentationEventKind kind;
    uint32_t actor_id,target_id,power_id,audio_asset,animation_asset; CohVec3 emitter;
} CohPresentationCue;
typedef struct { CohPresentationEvent event; int active; } CohPresentationEffect;
typedef struct {
    uint64_t snapshots,rejected_states,events,rejected_events,queue_limits,
        expired_effects,missing_audio,missing_animation,surface_losses,builds;
    size_t arena_bytes,effect_high_water,draw_high_water;
} CohPresentationStats;
typedef struct {
    CohUi ui; CohPresentationState state; CohHudInsets insets;
    CohPresentationIntent intents[COH_PRESENTATION_QUEUE]; size_t intent_count;
    CohPresentationCue cues[COH_PRESENTATION_QUEUE]; size_t cue_count;
    CohPresentationEffect effects[COH_PRESENTATION_EFFECTS];
    CohPresentationTab tab; uint64_t now_ms,last_sequence;
    int initialized,visible,has_clock,has_state; CohPresentationStats stats;
} CohPresentation;
CohStatus coh_presentation_init(CohPresentation *,CohUiGlyphFn,void *glyph_context);
void coh_presentation_destroy(CohPresentation *);
/* Same actor revisions cannot move backwards. Actor changes clear old effects,
 * intents and cues. All arrays/text are copied after transactional admission. */
CohStatus coh_presentation_set_state(CohPresentation *,const CohPresentationState *);
CohStatus coh_presentation_show(CohPresentation *,int visible,CohPresentationTab);
CohStatus coh_presentation_surface(CohPresentation *,uint32_t generation,float width,float height,CohHudInsets);
void coh_presentation_surface_lost(CohPresentation *);
CohStatus coh_presentation_build(CohPresentation *);
const CohUiDraw *coh_presentation_draws(const CohPresentation *,uint32_t generation,size_t *count);
/* Only route controls here when the optional panel is visible. Caller excludes
 * simultaneous HUD/scene routing; overlays never capture gameplay by themselves. */
CohStatus coh_presentation_action(CohPresentation *,CohUiAction);
CohStatus coh_presentation_touch(CohPresentation *,CohUiTouch,uint32_t pointer,float x,float y);
CohStatus coh_presentation_focus_row(CohPresentation *,size_t row);
CohStatus coh_presentation_axis(CohPresentation *,CohHudAxisNavigation *,float x,float y,uint64_t monotonic_ms);
int coh_presentation_poll(CohPresentation *,CohPresentationIntent *);
/* Timestamp is a monotonic active-presentation clock, including lifecycle policy
 * chosen by caller. Replays/stale actors, full queues and invalid data fail closed. */
CohStatus coh_presentation_event(CohPresentation *,const CohPresentationEvent *);
CohStatus coh_presentation_tick(CohPresentation *,uint64_t now_ms);
int coh_presentation_poll_cue(CohPresentation *,CohPresentationCue *);
/* Exact source addFloatingDamage RGB policy; original low alpha byte retained. */
uint32_t coh_presentation_damage_color(int32_t amount,int victim_is_self,int damager_is_owned,int absorb);
/* Explicit demo data, not recovered character/inventory/mission state. Uses no
 * icon substitutes; callers may provide authenticated icon resources later. */
void coh_presentation_mock_state(CohPresentationState *,const CohHudState *);
#ifdef __cplusplus
}
#endif
#endif
