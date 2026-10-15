#include "../coh_hud_axis_navigation.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static CohHud hud;
static CohHudState state;
static CohHudAxisNavigation nav;
static void base(void){
    size_t i;assert(coh_hud_init(&hud,NULL,NULL)==COH_OK);memset(&state,0,sizeof(state));
    state.power_count=COH_HUD_POWERS;
    for(i=0;i<state.power_count;i++){state.powers[i].id=100+(uint32_t)i;state.powers[i].enabled=1;}
    assert(coh_hud_set_state(&hud,&state)==COH_OK);
    assert(coh_hud_surface(&hud,1,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
    assert(coh_hud_focus(&hud,COH_HUD_BIND_POWER_FIRST)==COH_OK);coh_hud_axis_reset(&nav);
}
static unsigned slot(void){
    const CohUiWidget*w=coh_ui_widget(&hud.ui,hud.ui.focus);assert(w&&w->desc.binding>=COH_HUD_BIND_POWER_FIRST);
    return w->desc.binding-COH_HUD_BIND_POWER_FIRST;
}
int main(void){
    uint64_t before;unsigned i;CohHudAxisNavigation saved;base();
    assert(coh_hud_axis_step(&hud,&nav,.8f,0,1000)==COH_OK&&slot()==1);
    assert(coh_hud_axis_step(&hud,&nav,.8f,0,1349)==COH_OK&&slot()==1);
    assert(coh_hud_axis_step(&hud,&nav,.8f,0,1350)==COH_OK&&slot()==2);
    assert(coh_hud_axis_step(&hud,&nav,.8f,0,1459)==COH_OK&&slot()==2);
    assert(coh_hud_axis_step(&hud,&nav,.8f,0,1460)==COH_OK&&slot()==3);
    assert(nav.actions==3&&nav.repeats==2);
    assert(coh_hud_axis_step(&hud,&nav,.54f,0,1470)==COH_OK&&slot()==3);
    assert(coh_hud_axis_step(&hud,&nav,.36f,0,1480)==COH_OK&&slot()==3);
    assert(coh_hud_axis_step(&hud,&nav,.34f,0,1490)==COH_OK&&!nav.direction);
    assert(coh_hud_axis_step(&hud,&nav,.54f,0,1500)==COH_OK&&!nav.direction);
    assert(coh_hud_axis_step(&hud,&nav,.56f,0,1510)==COH_OK&&slot()==4);
    assert(coh_hud_axis_step(&hud,&nav,-.8f,0,1520)==COH_OK&&slot()==3&&!nav.repeating);
    /* Strong-axis selection and hysteresis keep diagonal noise from flipping. */
    assert(coh_hud_axis_step(&hud,&nav,.8f,.79f,1530)==COH_OK&&slot()==4);
    before=nav.actions;assert(coh_hud_axis_step(&hud,&nav,.79f,.8f,1540)==COH_OK&&nav.actions==before);
    assert(coh_hud_axis_step(&hud,&nav,.55f,.9f,1550)==COH_OK&&nav.actions==before+1&&nav.blocked==1);
    /* A ten-second stall generates one focus step, never a catch-up burst. */
    base();assert(coh_hud_axis_step(&hud,&nav,1,0,0)==COH_OK&&slot()==1);
    assert(coh_hud_axis_step(&hud,&nav,1,0,10000)==COH_OK&&slot()==2&&nav.repeats==1);
    assert(coh_hud_axis_step(&hud,&nav,1,0,10000)==COH_OK&&slot()==2);
    assert(coh_hud_axis_step(&hud,&nav,1,0,10109)==COH_OK&&slot()==2);
    assert(coh_hud_axis_step(&hud,&nav,1,0,10110)==COH_OK&&slot()==3);
    /* Invalid input and reversed time preserve held direction/timing. */
    saved=nav;assert(coh_hud_axis_step(&hud,&nav,NAN,0,10111)==COH_INVALID);saved.rejected++;
    assert(!memcmp(&saved,&nav,sizeof(nav)));
    assert(coh_hud_axis_step(&hud,&nav,0,INFINITY,10111)==COH_INVALID);
    assert(coh_hud_axis_step(&hud,&nav,1.01f,0,10111)==COH_INVALID);
    assert(coh_hud_axis_step(&hud,&nav,1,0,10109)==COH_INVALID);
    assert(coh_hud_axis_step(&hud,NULL,1,0,10111)==COH_INVALID);
    /* UINT64_MAX elapsed time cannot overflow a repeat deadline. */
    assert(coh_hud_axis_step(&hud,&nav,1,0,UINT64_MAX)==COH_OK&&slot()==4);
    before=nav.actions;assert(coh_hud_axis_step(&hud,&nav,1,0,UINT64_MAX)==COH_OK&&nav.actions==before);
    /* Full queues and lost Surfaces do not consume an axis edge. */
    base();for(i=0;i<COH_HUD_INTENTS;i++)assert(coh_hud_action(&hud,COH_UI_ACTIVATE)==COH_OK);
    assert(coh_hud_axis_step(&hud,&nav,1,0,0)==COH_LIMIT&&!nav.direction&&!nav.clock_seen);
    base();coh_hud_surface_lost(&hud);assert(coh_hud_axis_step(&hud,&nav,1,0,0)==COH_STATE&&!nav.direction);
    assert(coh_hud_surface(&hud,2,720,1280,(CohHudInsets){12,12,12,12})==COH_OK);
    assert(coh_hud_axis_step(&hud,&nav,1,0,0)==COH_OK&&slot()==1);
    coh_hud_axis_reset(&nav);assert(coh_hud_axis_step(&hud,&nav,1,0,1)==COH_OK&&slot()==2);
    assert(!hud.intent_count); /* analog navigation emits no gameplay intent */
    printf("{\"focus_timing_hysteresis_groups\":7,\"invalid_samples\":5,\"overflow_and_same_timestamp\":true,\"catchup_burst\":false,\"gameplay_intents\":0,\"arena_bytes\":%zu}\n",sizeof(nav));
    return 0;
}
