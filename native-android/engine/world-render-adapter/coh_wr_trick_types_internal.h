/* Exact original private persisted structure declarations; runtime pointers unresolved. */
#ifndef COH_WR_TRICK_TYPES_H
#define COH_WR_TRICK_TYPES_H
#include "coh_wr_texopt_types_internal.h"
typedef uint64_t U64;typedef struct BoneAnimTrack BoneAnimTrack;typedef struct TrickInfo TrickInfo;
typedef struct StAnim
{
    const BoneAnimTrack * btTex0;  
    const BoneAnimTrack * btTex1;
    char    *name;                //skeleton name of animation in tscroll.anm, corresponds to a WRL file
    F32        speed_scale;
    F32        st_scale;
    int        flags;
} StAnim;
typedef struct AutoLOD
{
    float        max_error;
    F32            lod_near, lod_far, lod_nearfade, lod_farfade;
    int            flags;
    U32            modelname_specified : 1;
    char        *lod_modelname, *lod_filename;
} AutoLOD;
typedef struct TrickNode
{
    F32        tex_scale_y;        // Only used by FX
    F32        st_anim_age;
    U8        trick_rgba[4];
    U8        trick_rgba2[4];        // Keep this right after trick_rgba, as it is referenced as a [2][4]
    union {
        struct {
            int        flags1;
            int        flags2;
        };
        U64 flags64;
    };
    TrickInfo    *info;
} TrickNode;
typedef struct TrickInfo
{
    char        *file_name; // file this trick was loaded from, for artist debug
    char        *name;
    TrickNode    tnode;
    ModelFlags    model_flags;
    U32            group_flags;
//    BlendModeType    blend_mode;
    F32            lod_near,lod_far,lod_nearfade,lod_farfade;
    StAnim        **stAnim;  //only ever one 
    F32            shadow_dist;
    F32            alpha_ref;    // 0-1
    F32            alpha_ref_parser; // The value read from the parser (0-255)
    F32            tex_bias;
    F32            nightglow_times[2];
    Vec2        sway; // 0 ~ speed, 1 ~ amount
    Vec2        sway_random;  // 0 ~ speed, 1 ~ amount
    Vec2        sway_pitch;
    Vec2        sway_roll;
    F32            lod_scale;
    F32            tighten_up;
    U32            fileAge;
    Vec3        texScrollAmt[2];
    F32            alpha_sort_mod;
    F32            water_reflection_skew;
    F32            water_reflection_strength;
    AutoLOD        **auto_lod; // if NULL, use the model geometry.  if present, each of these generates an LOD.
} TrickInfo;
#define TRICK2_TEXBIAS 1 << 27
#define TRICK2_ALPHAREF 1 << 25
#define TRICK2_CASTSHADOW 1 << 22
#define TRICK2_NIGHTGLOW 1 << 28
#define TRICK2_HAS_SWAY 1 << 4
#define TRICK2_STSCROLL0 1 << 1
#define TRICK2_STSCROLL1 1 << 9
#define GROUP_VIS_TRAY (1 << 3)
#endif
