/* Test-only read access to coordinator-owned integration packets. This file
 * is never included in the Android target. No movement or rendering backdoor. */
#include "../app/src/main/cpp/session_stream_world.c"
int coh_stream_test_packet(const CohSessionWorld *w,uint32_t index,CohRenderDraw *out) {
    if(!w||!out||index>=w->draw_count)return 0;
    *out=w->draws[index];return 1;
}
uint32_t coh_stream_test_packet_count(const CohSessionWorld *w) {return w?w->draw_count:0;}
int coh_stream_test_instance(const CohSessionWorld *w,uint32_t index,CohWorldInstance *out) {
    if(!w||!out||index>=w->selection.count)return 0;
    *out=w->selection.instances[index];return 1;
}
CohBridgeStats coh_stream_test_bridge_stats(const CohSessionWorld *w) {return coh_bridge_stats(w?w->bridge:NULL);}
CohAssetStats coh_stream_test_asset_stats(const CohSessionWorld *w) {return coh_asset_stats(w?w->loader:NULL);}
