#ifndef COH_INPUT_H
#define COH_INPUT_H
#include <stdint.h>
#define COH_INPUT_KEYS 24u
/* 0..7: left/right/up/down of left then right source joystick.
 * 8..23: A,B,X,Y,L1,R1,L2,R2,SELECT,START,L3,R3,HAT_UP,DOWN,LEFT,RIGHT. */
enum { COH_TOUCH_BEGIN=0, COH_TOUCH_MOVE=1, COH_TOUCH_END=2, COH_TOUCH_CANCEL=3 };
typedef struct {
    uint8_t levels[COH_INPUT_KEYS], edges[COH_INPUT_KEYS], released[COH_INPUT_KEYS];
    uint8_t focused, invert, mlook;
    float axes[4], pyr[3], target_pyr[3], touch_x, touch_y;
    int32_t touch_id, pending_x, pending_y;
    uint32_t frames, clear_count, rejected, clipped;
} CohInputState;
typedef struct {
    uint32_t held, pressed, released, frames, clear_count, rejected, clipped;
    uint8_t levels[COH_INPUT_KEYS];
    int32_t delta_x, delta_y;
    float pyr[3], target_pyr[3], axes[4];
} CohInputFrame;
typedef struct {
    uint32_t checks, failed, source_cases, adapter_cases;
    float max_source_error;
} CohInputProof;
void coh_input_init(CohInputState *state);
/* Focus/disconnect/cancel clear held keys, edges, axes and pending motion. */
void coh_input_focus(CohInputState *state, int focused);
int coh_input_key(CohInputState *state, uint32_t key, int down);
/* Android normalized X,Y,Z,RZ values; converted to source integer +/-1000. */
int coh_input_axes(CohInputState *state, float x, float y, float z, float rz);
/* Stable pointer ID, normalized view coordinates -1..1. */
int coh_input_touch(CohInputState *state, int action, int32_t pointer_id, float x, float y);
/* Adapter rate is 2 radians/second after .15 right-stick dead zone.
 * Source integer mouse deltas are bounded +/-500 per frame.
 * seconds must be finite, 0..0.05; no backlog or smoothing state. */
int coh_input_frame(CohInputState *state, float seconds, CohInputFrame *frame);
/* Golden checks produced from unchanged pinned original source kernels. */
int coh_input_selftest(CohInputProof *proof);
#endif
