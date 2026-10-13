#ifndef COH_ANIMATION_H
#define COH_ANIMATION_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ANIMATION_BONES 99u
#define COH_ANIMATION_PALETTE 15u
#define COH_ANIMATION_MAX_KEYS 4096u
/* Views borrow immutable caller-owned original encoded .anim bytes. This gate
 * admits linear5-byte rotations and compressed6-byte/raw12-byte positions only. */
typedef struct {
    const uint8_t *rotation,*position;
    uint16_t rotation_keys,position_keys,rotation_frames,position_frames;
    uint8_t id,flags,present;
} CohAnimationTrack;
typedef struct {
    const uint8_t *bytes; size_t byte_count;
    uint32_t track_count;
    CohAnimationTrack tracks[COH_ANIMATION_BONES];
} CohAnimationFile;
typedef struct {
    const uint8_t *bytes; size_t byte_count;
    CohAnimationFile base,motion;
    int16_t parent[COH_ANIMATION_BONES];
    uint8_t order[COH_ANIMATION_BONES]; uint32_t node_count;
    float base_position[COH_ANIMATION_BONES][3];
    float base_rotation[COH_ANIMATION_BONES][4];
    float bind_translation[COH_ANIMATION_BONES][3];
    float animation_delta[COH_ANIMATION_BONES][3];
    uint32_t palette_ids[COH_ANIMATION_PALETTE],palette_count,socket_id;
    float first_frame,last_frame,ticks_per_second;
} CohAnimationRig;
typedef struct {
    float frame;
    float position[COH_ANIMATION_BONES][3];
    float rotation[COH_ANIMATION_BONES][4];
    float world_rows[COH_ANIMATION_BONES][12]; /* three affine vec4 rows */
} CohAnimationPose;
/* Return0 on success; outputs are untouched on failure. Canonical COHRIG01
 * contains raw base+motion files, palette IDs and source clock/socket metadata,
 * never baked sampled palettes. All reachable tracks/hierarchy are validated. */
int coh_animation_parse(const uint8_t *,size_t,CohAnimationRig *);
int coh_animation_sample(const CohAnimationRig *,float frame,CohAnimationPose *);
/* Explicit neutral-rig scope: unit bonescale/root, zero body morphs, no move
 * transition blending. Source bpt inverse-bind translation then socket fold. */
int coh_animation_palette(const CohAnimationRig *,const CohAnimationPose *,
                          uint32_t socket_id,const uint32_t *bone_ids,
                          uint32_t bone_count,float *palette_rows);
int coh_animation_default_palette(const CohAnimationRig *,const CohAnimationPose *,float *);
/* Controlled effective rate; same incremental strict-end cycle rule as seqStep.
 * Input timestep is engine frames (e.g.seconds*30), not a wall-clock timestamp.
 * Return2 for a noncycling end-of-move (output untouched); next-move/state
 * selection and movement-derived MoveScale/SmoothSprint are separate. */
int coh_animation_step(const CohAnimationRig *,float current,float timestep_frames,
                       float effective_rate,int cycle,float *next_frame);
#ifdef __cplusplus
}
#endif
#endif
