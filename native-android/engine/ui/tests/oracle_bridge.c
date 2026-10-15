#include "../coh_ui.h"
static CohUi oracle_ui;
int native_scale(int mode,int width,int height,float *out){
    CohStatus s;coh_ui_init(&oracle_ui,(CohUiScale)mode,0,0);
    s=coh_ui_surface(&oracle_ui,1,(float)width,(float)height);if(s!=COH_OK)return s;
    out[0]=oracle_ui.scale_x;out[1]=oracle_ui.scale_y;out[2]=oracle_ui.offset_x;out[3]=oracle_ui.offset_y;return 0;
}
void native_focus_init(void){
    CohUiDesc d={0};int i;coh_ui_init(&oracle_ui,COH_UI_SCALE_XY,0,0);
    (void)coh_ui_surface(&oracle_ui,1,1024,768);
    for(i=1;i<=3;i++){
        d.id=(uint32_t)i;d.kind=i==3?COH_UI_INPUT:COH_UI_BUTTON;
        d.flags=COH_UI_VISIBLE|COH_UI_ENABLED|COH_UI_FOCUSABLE;d.rect=(CohUiRect){(float)(i*100),10,90,40};d.font_size=16;
        (void)coh_ui_add(&oracle_ui,&d,"");
    }
}
int native_focus_set(int id){CohUiEvent e;int s=coh_ui_focus(&oracle_ui,(uint32_t)id);while(coh_ui_poll(&oracle_ui,&e)){}return s;}
int native_focus_id(void){return (int)oracle_ui.focus;}
int native_focus_editable(void){return coh_ui_keyboard_requested(&oracle_ui);}
