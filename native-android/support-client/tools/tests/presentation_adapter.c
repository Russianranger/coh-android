#include "support_ui.h"
#include <assert.h>
#include <stdio.h>
/* Uses actual support wrapper, copied mock state, source font and real GLES.
 * Bootstrap and historical HUD pointer/lifecycle tests are linked separately. */
void presentation_adapter_checks(void){
 SupportUi *ui=support_ui_create();SupportUiStats before,after;int consumed=0;assert(ui);
 assert(support_ui_surface(ui,1,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
 assert(support_ui_context_create(ui,1)==COH_OK);assert(support_ui_tick_mock(ui,10)==COH_OK);
 assert(support_ui_draw(ui,1280,720,1)==COH_OK);
 assert(support_ui_presentation(ui,0)==COH_OK);
 assert(support_ui_snapshot(ui,&before)==COH_OK&&before.presentation_visible);
 support_ui_preview_label(ui,1);assert(support_ui_tick_mock(ui,11)==COH_OK);assert(support_ui_draw(ui,1280,720,1)==COH_OK);
 assert(support_ui_snapshot(ui,&after)==COH_OK&&!after.presentation_visible);uint64_t compact_quads=after.gpu.quads-before.gpu.quads;
 /* Hidden tray must not emit or capture an otherwise valid slot touch. */
 (void)support_ui_pointer(ui,0,0,408.4375f,671.25f,&consumed);assert(!consumed);
 (void)support_ui_pointer(ui,1,0,408.4375f,671.25f,&consumed);assert(!consumed);
 assert(support_ui_snapshot(ui,&after)==COH_OK&&after.power_uses==before.power_uses);
 support_ui_preview_label(ui,0);assert(support_ui_snapshot(ui,&before)==COH_OK);assert(support_ui_draw(ui,1280,720,1)==COH_OK);
 assert(support_ui_snapshot(ui,&after)==COH_OK&&after.gpu.quads-before.gpu.quads>compact_quads);
 assert(support_ui_presentation(ui,0)==COH_OK);assert(support_ui_draw(ui,1280,720,1)==COH_OK);
 assert(support_ui_snapshot(ui,&before)==COH_OK&&before.presentation_visible&&before.presentation_tab==0);
 assert(support_ui_presentation(ui,0)==COH_OK);assert(support_ui_draw(ui,1280,720,1)==COH_OK);
 /* 1024x768 fit into 1280x720 gives .9375 scale and 160px x inset. */
 assert(support_ui_pointer(ui,0,0,816.25f,215.625f,&consumed)==COH_OK&&consumed);
 assert(support_ui_pointer(ui,1,0,816.25f,215.625f,&consumed)==COH_OK&&consumed);
 assert(support_ui_snapshot(ui,&after)==COH_OK&&after.presentation_tab==1&&after.presentation_intents>before.presentation_intents);
 /* Panel pointer ownership prevents off-panel DOWN/MOVE/UP scene steering. */
 (void)support_ui_pointer(ui,0,0,100,100,&consumed);assert(consumed);
 (void)support_ui_pointer(ui,2,0,200,200,&consumed);assert(consumed);
 (void)support_ui_pointer(ui,1,0,200,200,&consumed);assert(consumed);
 support_ui_navigation(ui,1,0,1);assert(support_ui_tick_mock(ui,11)==COH_OK);
 assert(support_ui_tick_mock(ui,400)==COH_OK);support_ui_navigation(ui,0,0,0);
 assert(support_ui_key(ui,97,0,0,0)==COH_OK);assert(support_ui_snapshot(ui,&before)==COH_OK&&!before.presentation_visible);
 assert(support_ui_presentation(ui,1)==COH_OK);assert(support_ui_draw(ui,1280,720,1)==COH_OK);
 assert(support_ui_snapshot(ui,&after)==COH_OK&&after.presentation.events==before.presentation.events+1&&after.presentation_cues==before.presentation_cues+1&&after.target_health<before.target_health);
 for(unsigned i=0;i<20;i++)(void)support_ui_presentation(ui,1);
 assert(support_ui_snapshot(ui,&before)==COH_OK&&before.presentation.queue_limits>0);
 assert(support_ui_tick_mock(ui,2000)==COH_OK);assert(support_ui_draw(ui,1280,720,1)==COH_OK);
 assert(support_ui_snapshot(ui,&after)==COH_OK&&after.presentation.expired_effects>0);
 support_ui_context_destroy(ui);assert(support_ui_context_create(ui,2)==COH_OK);
 assert(support_ui_surface(ui,2,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
 assert(support_ui_draw(ui,1280,720,2)==COH_OK);assert(support_ui_snapshot(ui,&after)==COH_OK&&after.gpu.gl_errors==0&&after.presentation.events==before.presentation.events);
 assert(support_ui_presentation(ui,-1)==COH_INVALID);assert(support_ui_presentation(NULL,0)==COH_INVALID);
 printf("{\"presentation_adapter\":true,\"gpu_gl_errors\":0,\"source_font\":true,\"mock_cues\":%llu,\"bounded_event_rejections\":%llu,\"surface_recovery\":true,\"arena_bytes\":%zu}\n",(unsigned long long)after.presentation_cues,(unsigned long long)after.presentation.queue_limits,after.arena_bytes);
 support_ui_context_destroy(ui);support_ui_destroy(ui);
}
