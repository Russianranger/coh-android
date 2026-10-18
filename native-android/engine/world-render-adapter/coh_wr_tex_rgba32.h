#ifndef COH_WR_TEX_RGBA32_H
#define COH_WR_TEX_RGBA32_H
#include "coh_wr_tex_namespace.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_WR_TEX_RGBA32_MAX_MIPS 15u
#define COH_WR_TEX_RGBA32_PREPARATION_RESERVE 16384u
typedef struct CohWrTexRgba32 CohWrTexRgba32;
typedef struct {size_t owned_limit,aggregate_limit,external_bytes;} CohWrTexRgba32Limits;
typedef struct {uint32_t width,height,source_level;CohBytes rgba;} CohWrTexRgba32Mip;
typedef struct {
 CohAssetId asset;
 uint8_t sha256[32];
 uint32_t source_row,source_input_generation,source_mip_count,skipped_mips,mip_count;
 size_t owned_bytes,aggregate_reserved_bytes;
 CohWrTexRgba32Mip mips[COH_WR_TEX_RGBA32_MAX_MIPS];
} CohWrTexRgba32View;
/* Synchronous, one owner thread. The input is an actual live namespace owner,
 * not a caller-forged Basic/byte association. Acquire revalidates its exact
 * selected whole-body hash and holds the real source pin through all parsing
 * and copying. Success owns independent immutable RGBA bytes plus copied
 * path/generation/SHA; the source lease is then released and its owner may
 * retire. No source pixels, cached TX2 bytes or protected decoder are modified.
 *
 * Only the original TEXFMT_ARGB_8888 tight 2D layout is admitted: flags0x41,
 * 32bits, zero FourCC, canonical BGRA masks, <=16384 dimensions, and either a
 * complete terminating mip chain or source count0/base-only. Original ddsLoad
 * ignores RGB masks/pitch; this safe subset refuses other layouts explicitly.
 * Source texCopyDirect's inclusive mip_count loop is bounded here by a complete
 * chain ending at1x1. No implicit mip synthesis or row padding is accepted.
 * skip_mips is the supplied texGetNumMipsToSkip result, not a qualified choice
 * of graphics/entity policy. It must leave at least one source level.
 * Wrapped cached/DDS dimensions and whole payload length must agree exactly.
 * BGRA->RGBA preserves every alpha byte and row order; invisible alpha clearing,
 * TexOpt, defaults, compositing, samplers, material and GPU remain unresolved.
 *
 * A fixed16KiB own preparation reserve plus owned bytes and external_bytes are
 * charged. external_bytes must cover at least the source owner's full recorded
 * aggregate reservation (enforced before acquire), plus actual external peaks
 * not already included. No allocator overhead, RSS or global budget claim.
 * *out must be NULL. Refusals preserve outputs, release the source lease, and
 * free all candidate storage, including late cancellation. Request/output
 * storage must be outside the opaque source owner/provider storage and remain
 * unchanged through callbacks; limits and known metadata aliases are checked.
 * Views live until destroy. Output spans may not overlap owned storage.
 */
CohStatus coh_wr_tex_rgba32_build(CohWrTexNamespace*,uint32_t row,uint32_t skip_mips,const CohWrTexRgba32Limits*,CohCancel,CohWrTexRgba32**);
CohStatus coh_wr_tex_rgba32_view(const CohWrTexRgba32*,CohWrTexRgba32View*);
CohStatus coh_wr_tex_rgba32_destroy(CohWrTexRgba32**);
#ifdef __cplusplus
}
#endif
#endif
