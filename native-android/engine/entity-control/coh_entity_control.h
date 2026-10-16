#ifndef COH_ENTITY_CONTROL_H
#define COH_ENTITY_CONTROL_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CONTROL_PUSH_MAX 32u
#define COH_CONTROL_SURFACE_BYTES 40u
#define COH_CONTROL_FLAG_COUNT 17u
/* Bit order is the original sender's wire order, not a compiler bitfield ABI. */
enum {
    COH_CONTROL_FLY=1u<<0, COH_CONTROL_STUN=1u<<1,
    COH_CONTROL_JUMPPACK=1u<<2, COH_CONTROL_GLIDE=1u<<3,
    COH_CONTROL_NINJA_RUN=1u<<4, COH_CONTROL_WALK=1u<<5,
    COH_CONTROL_BEAST_RUN=1u<<6, COH_CONTROL_STEAM_JUMP=1u<<7,
    COH_CONTROL_HOVER_BOARD=1u<<8, COH_CONTROL_MAGIC_CARPET=1u<<9,
    COH_CONTROL_PARKOUR_RUN=1u<<10, COH_CONTROL_NO_PHYSICS=1u<<11,
    COH_CONTROL_HIT_STUMBLE=1u<<12, COH_CONTROL_INPUT_IGNORED=1u<<13,
    COH_CONTROL_SHELL_DISABLED=1u<<14, COH_CONTROL_NO_ENT_COLLISION=1u<<15,
    COH_CONTROL_NO_JUMP_REPEAT=1u<<16
};
typedef struct {
    uint32_t net_id_start, physics_ticks, abs_time, knockback_animation;
    CohVec3 velocity;
} CohControlPush;
typedef struct {
    uint32_t update_id, flags;
    CohVec3 speed;
    float speed_back, jump_height;
    /* Exact source Win32 little-endian IEEE754 SurfaceParams[2] bytes:
     * ground then air, each traction/friction/bounce/gravity/max_speed.
     * Never memcpy this into an unrelated native physics struct. */
    uint8_t surface_le[COH_CONTROL_SURFACE_BYTES];
} CohControlServer;
typedef struct {
    uint32_t position_id, falling;
    CohVec3 position, velocity, pyr;
} CohControlForced;
typedef struct {
    uint32_t push_count, has_server, has_forced;
    CohControlPush pushes[COH_CONTROL_PUSH_MAX];
    CohRepPhysics physics;
    CohControlServer server;
    CohControlForced forced;
    size_t end_bit;
} CohControlUpdate;
typedef enum { COH_CONTROL_FUTURE_PUSHES=1, COH_CONTROL_PHYSICS,
    COH_CONTROL_SERVER, COH_CONTROL_SURFACE, COH_CONTROL_FORCED } CohControlStage;
typedef struct { CohStatus status; CohControlStage stage; size_t bit; } CohControlFailure;
/* This POD is staging state, not simulation or render publication. A new
 * session requires explicit init with a nonzero generation. */
typedef struct {
    uint32_t generation, server_packet, forced_packet, physics_position_packet;
    uint32_t server_valid, forced_valid, physics_valid;
    CohControlServer server;
    CohControlForced forced;
    CohRepPhysics physics;
} CohControlState;
/* One original playerReceiveControlState substructure, starting before the
 * future-push list. Borrows input synchronously; no allocations/callbacks.
 * Reader/output unchanged on any error. Diagnostic recording is unsupported.
 * No end-of-packet, entity ownership, ACK, readiness or live-world claim. */
CohStatus coh_control_read(CohRepReader *, CohControlUpdate *, CohControlFailure *);
/* Read ten source floats without assuming host padding/endianness. Surface
 * index 0=ground,1=air; member 0..4 follows the order documented above. */
CohStatus coh_control_surface_value(const CohControlServer *, unsigned surface,
    unsigned member, float *);
CohStatus coh_control_state_init(CohControlState *, uint32_t generation);
/* Apply a successful decoder output only to the caller's transaction staging
 * copy. Strict original per-section packet ordering, no serial wrap guessing.
 * Requires nonzero packet ID and matching generation. Future pushes remain
 * events in update; the owning full transaction must deduplicate and retain
 * them, then resolve physics history. This function never executes them.
 * Forced pitch is consumed but ignored as in the original client; yaw/roll
 * are recorded without changing the camera. State is atomic on failure. */
CohStatus coh_control_stage(CohControlState *, uint32_t generation,
    uint32_t packet_id, const CohControlUpdate *);
#ifdef __cplusplus
}
#endif
#endif
