/* Optional coordinator integration QA. Compile against its current SupportUi
 * source/header; this file owns no root implementation or Java source. */
#include "support_ui.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
void root_axis_adapter_checks(void){
    SupportUi *ui=support_ui_create();SupportUiStats stats;unsigned i;
    assert(ui&&support_ui_surface(ui,21,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
    assert(support_ui_context_create(ui,21)==COH_OK);
    assert(support_ui_tick_mock(ui,0)==COH_OK&&support_ui_draw(ui,1280,720,21)==COH_OK);
    /* Explicit focus order: target, chat, first power. */
    for(i=0;i<3;i++)assert(support_ui_key(ui,61,0,0,0)==COH_OK);
    support_ui_navigation(ui,1,1,0);
    assert(support_ui_tick_mock(ui,1)==COH_OK);
    assert(support_ui_tick_mock(ui,350)==COH_OK);
    assert(support_ui_tick_mock(ui,351)==COH_OK);
    assert(support_ui_tick_mock(ui,461)==COH_OK);
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.axis_actions==3&&stats.axis_repeats==2);
    assert(support_ui_key(ui,96,0,0,0)==COH_OK);
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.power_uses==1&&stats.last_power==1003);
    /* OFF is nonblocking and stops held repetition, including a long pause. */
    support_ui_navigation(ui,0,0,0);
    assert(support_ui_tick_mock(ui,10000)==COH_OK);
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.axis_actions==3&&stats.axis_repeats==2);
    /* A reset followed by active input before a tick must create a new edge. */
    support_ui_navigation(ui,1,-1,0);
    assert(support_ui_tick_mock(ui,10001)==COH_OK);
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.axis_actions==4&&stats.axis_repeats==2);
    support_ui_navigation(ui,0,0,0);
    assert(support_ui_focus_chat(ui)==COH_OK&&support_ui_text(ui,"root source chat survives")==COH_OK);
    support_ui_context_destroy(ui);
    assert(support_ui_context_create(ui,22)==COH_OK);
    assert(support_ui_surface(ui,22,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
    assert(support_ui_tick_mock(ui,10002)==COH_OK&&support_ui_draw(ui,1280,720,22)==COH_OK);
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.gpu.gl_errors==0&&stats.generation==22);
    assert(stats.chat_input[0]&&stats.axis_actions==4&&stats.axis_repeats==2);
    support_ui_context_destroy(ui);support_ui_destroy(ui);
    printf("{\"root_axis_adapter\":\"passed\",\"actions\":4,\"repeats\":2,\"last_power\":1003,\"surface_recreate_chat\":true,\"GL_errors\":0}\n");
}
