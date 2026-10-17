/* Exact original type declarations retained privately for source-qualified cache inputs. */
#ifndef COH_WR_TEXOPT_TYPES_H
#define COH_WR_TEXOPT_TYPES_H
#include <stdint.h>
typedef float F32;typedef uint8_t U8;typedef uint32_t U32;typedef F32 Vec2[2];typedef F32 Vec3[3];
typedef enum ModelFlags
{
    OBJ_ALPHASORT        = 1 << 0, // At least some of the subs on this model need to be alpha sorted
    OBJ_FANCYWATER        = 1 << 1,
    OBJ_FULLBRIGHT        = 1 << 2,
    OBJ_SUNFLARE        = 1 << 3,
    OBJ_NOLIGHTANGLE    = 1 << 4,


    OBJ_LOD                = 1 << 7,
    OBJ_TREEDRAW        = 1 << 8,
    OBJ_ALLOW_MULTISPLIT = 1 << 9,
    OBJ_FORCEOPAQUE        = 1 << 10,
    OBJ_BUMPMAP            = 1 << 11,
    OBJ_WORLDFX            = 1 << 12, //draw this object using model draw
    OBJ_CUBEMAP            = 1 << 13,
    OBJ_DRAWBONED        = 1 << 14, //draw this object using model draw boned node
    OBJ_STATICFX        = 1 << 15, //add static lighting to this object
    OBJ_HIDE            = 1 << 16, //don't draw me except in wireframe

    OBJ_ALPHASORTALL    = 1 << 18, // All subs on this model must be alpha sorted

    OBJ_DONTCASTSHADOWMAP    = 1 << 19,            // will not appear in the shadow map
    OBJ_DONTRECEIVESHADOWMAP    = 1 << 20,        // will not receive shadows from the shadow map

} ModelFlags;
typedef enum TexOptFlags
{
    TEXOPT_FADE                    = 1 << 0,
    TEXOPT_TRUECOLOR            = 1 << 1,
    TEXOPT_TREAT_AS_MULTITEX    = 1 << 2, // New texture, possibly rendered with old shader, but treat it as a new one
    TEXOPT_MULTITEX                = 1 << 3, // New texture TEXLAYERing scheme
    TEXOPT_NORANDOMADDGLOW        = 1 << 4,
    TEXOPT_FULLBRIGHT            = 1 << 5,
    TEXOPT_CLAMPS                = 1 << 6,
    TEXOPT_CLAMPT                = 1 << 7,
    TEXOPT_ALWAYSADDGLOW        = 1 << 8,
    TEXOPT_MIRRORS                = 1 << 9,
    TEXOPT_MIRRORT                = 1 << 10,
    TEXOPT_REPLACEABLE            = 1 << 11,
    TEXOPT_BUMPMAP                = 1 << 12,
    TEXOPT_REPEATS                = 1 << 13,
    TEXOPT_REPEATT                = 1 << 14,
    TEXOPT_CUBEMAP                = 1 << 15,
    TEXOPT_NOMIP                = 1 << 16,
    TEXOPT_JPEG                    = 1 << 17,
    TEXOPT_NODITHER                = 1 << 18,
    TEXOPT_NOCOLL                = 1 << 19,
    TEXOPT_SURFACESLICK            = 1 << 20,
    TEXOPT_SURFACEICY            = 1 << 21,
    TEXOPT_SURFACEBOUNCY        = 1 << 22,
    TEXOPT_BORDER                = 1 << 23,
    TEXOPT_OLDTINT                = 1 << 24,
    TEXOPT_DOUBLEFUSION            = 1 << 25,  // deprecated
    TEXOPT_POINTSAMPLE            = 1 << 26,
    TEXOPT_NORMALMAP            = 1 << 27,
    TEXOPT_SPECINALPHA            = 1 << 28,
    TEXOPT_FALLBACKFORCEOPAQUE    = 1 << 29,
} TexOptFlags;
typedef enum BlendModeShader
{
    BLENDMODE_MODULATE,
    BLENDMODE_MULTIPLY,
    BLENDMODE_COLORBLEND_DUAL,
    BLENDMODE_ADDGLOW,            // building windows, neon, etc
    BLENDMODE_ALPHADETAIL,
    BLENDMODE_BUMPMAP_MULTIPLY,
    BLENDMODE_BUMPMAP_COLORBLEND_DUAL,
    BLENDMODE_WATER,
    BLENDMODE_MULTI,
    BLENDMODE_SUNFLARE,
    BLENDMODE_NUMENTRIES
} BlendModeShader;
typedef enum BlendIndex
{
    BLEND_OLD_TEX_BASE,
    BLEND_OLD_TEX_GENERIC_BLEND,
    BLEND_BASE1,
    BLEND_MULTIPLY1,
    BLEND_BUMPMAP1,
    BLEND_DUALCOLOR1,
    BLEND_MASK,
    BLEND_BASE2,
    BLEND_MULTIPLY2,
    BLEND_BUMPMAP2,
    BLEND_DUALCOLOR2,
    BLEND_ADDGLOW1,
    BLEND_CUBEMAP,
    BLEND_NUM_BLEND_NAMES,
} BlendIndex;
typedef enum TexOptScrollType
{
    TEXOPTSCROLL_NORMAL,
    TEXOPTSCROLL_PINGPONG,
    TEXOPTSCROLL_OVAL,
} TexOptScrollType;
typedef struct TexOpt TexOpt;
typedef struct ScrollsScales
{
    F32        texopt_scale[BLEND_NUM_BLEND_NAMES][2];
    F32        texopt_scroll[BLEND_NUM_BLEND_NAMES][2];
    TexOptScrollType texopt_scrollType[BLEND_NUM_BLEND_NAMES];
    U8        alphaMask; // Use just the alpha channel of the Mask layer
    U8        hasRgb34;
    U8        multiply1Reflect;
    U8        multiply2Reflect;
    U8        baseAddGlow;
    U8        minAddGlow;
    U8        maxAddGlow;
    U8        addGlowMat2;            // flag to add the glow texture to MULTI sub-material 2 instead of sub-material 1 (the default)
    U8        tintGlow;                // flag to tint the glow by the current tint 'const color 1'
    U8        tintReflection;            // flag to tint environment reflections by current tint 'const color 1'
    U8        desaturateReflection;    // flag to desaturate the environment reflection to grayscale before applying
    U8        alphaWater;                // flag to honor base1 texture alpha value when applying water (e.g. for puddles)
    U8        rgba3[4];
    U8        rgba4[4];
    U8        specularRgba1[4];
    U8        specularRgba2[4];
    F32        specularExponent1;
    F32        specularExponent2;
    F32        reflectivity; // for environment mapping (deprecated)
    F32        reflectivityBase;
    F32        reflectivityScale;
    F32        reflectivityPower;
    F32        maskWeight;
    Vec3    diffuseScale;
    Vec3    ambientScale;
    Vec3    diffuseScaleTrick;
    Vec3    ambientScaleTrick;
    Vec3    ambientMin;
    TexOpt *debug_backpointer;
} ScrollsScales;
typedef struct TexOptFallback
{
    char *base_name;
    char *blend_name;
    char *bumpmap;
    BlendModeShader    blend_mode;
    Vec2 scaleST[2];
    Vec3    diffuseScaleTrick;
    Vec3    ambientScaleTrick;
    Vec3    ambientMin;
    U8    useFallback;
} TexOptFallback;
typedef struct TexOpt
{
    char    *file_name;    // used for artist debug
    char    *name; // modified after text parser finishes (skips beginning slashes and truncstes at period)
    const char *blend_names[BLEND_NUM_BLEND_NAMES];
    U8        swappable[BLEND_NUM_BLEND_NAMES];    // Whether or not each layer can be swapped
    F32        texopt_fade[2];
    ScrollsScales scrollsScales;
    TexOptFlags    flags;
    BlendModeShader    blend_mode;
    int        surface; //seq state flag
    char    *surface_name;
    char    *df_name;
    F32        gloss;
    F32        specularExponent1_parser;
    F32        specularExponent2_parser;
    U32        fileAge;
    ModelFlags model_flags; // Trickle-down flags to apply to a model this texture is on
    TexOptFallback fallback;
} TexOpt;
_Static_assert(sizeof(F32)==4 && sizeof(U32)==4 && sizeof(TexOptFlags)==4 && sizeof(BlendModeShader)==4,"source scalar layout");
#endif
