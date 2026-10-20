#ifndef COH_ORIGINAL_COSTUME_RECEIVE_H
#define COH_ORIGINAL_COSTUME_RECEIVE_H
#include "../replication/coh_replication.h"
#include "coh_client_costume_slots.h"
#include <setjmp.h>
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ORIGINAL_COSTUME_WORKSPACE_BYTES 65536u
#define COH_ORIGINAL_COSTUME_STACK_RESERVE 4096u
enum {COH_ORIGINAL_COSTUME_HEADER=0,COH_ORIGINAL_COSTUME_ENTTYPE=1,
 COH_ORIGINAL_COSTUME_PREFIX=2,COH_ORIGINAL_COSTUME_GEOM=3,
 COH_ORIGINAL_COSTUME_TEX1=4,COH_ORIGINAL_COSTUME_TEX2=5,
 COH_ORIGINAL_COSTUME_FX=6,COH_ORIGINAL_COSTUME_COLOR=7,
 COH_ORIGINAL_COSTUME_REGION=8,COH_ORIGINAL_COSTUME_BODYSET=9};
enum {COH_ORIGINAL_COSTUME_NO_DICTIONARY=0,COH_ORIGINAL_COSTUME_STRINGS=1,
 COH_ORIGINAL_COSTUME_EXTRA_STRINGS=2,COH_ORIGINAL_COSTUME_PALETTE=3};
typedef struct {
 CohStatus status;size_t begin_bit,end_bit,failure_bit;
 uint32_t field,part,part_count,parts_read,strings_read,colors_read,
  literal_strings,string_cache_entries,color_cache_entries,dictionary_required,
  bodytype_validated,count_validated,costume_complete;
} CohOriginalCostumeReport;
/* Thin source-member storage declarations are exposed solely so callers can
 * provide an actual typed off-stack object. The union state member avoids
 * casting a declared char array to an unrelated struct under strict aliasing.
 * These member subsets do not claim the original engine object/ABI layout. */
typedef struct{uint32_t integer;} CohOriginalCostumeColor;
typedef struct{uint32_t SGBitSetLow,SGBitSetHigh;} CohOriginalCostumeSGColor;
typedef struct{
 const char *entTypeFile,*costumeFilePrefix;int bodytype,convertedScale,currentSuperColorSet,iNumParts;
 CohOriginalCostumeColor colorSkin;float fScales[30];
 CohOriginalCostumeSGColor superColorsPrimaryU[6],superColorsSecondaryU[6],superColorsPrimary2U[6],superColorsSecondary2U[6],superColorsTertiaryU[6],superColorsQuaternaryU[6];
} CohOriginalCostumeAppearance;
typedef struct{
 const char *pchGeom,*pchTex1,*pchTex2,*pchFxName,*displayName,*regionName,*bodySetName;CohOriginalCostumeColor color[4];
} CohOriginalCostumePart;
typedef struct{CohOriginalCostumeAppearance appearance;CohOriginalCostumePart *parts[30];} CohOriginalCostumeObject;
enum {COH_ORIGINAL_SNAPSHOT_GEOM=0,COH_ORIGINAL_SNAPSHOT_TEX1=1,
 COH_ORIGINAL_SNAPSHOT_TEX2=2,COH_ORIGINAL_SNAPSHOT_FX=3,
 COH_ORIGINAL_SNAPSHOT_REGION=4,COH_ORIGINAL_SNAPSHOT_BODYSET=5};
typedef struct{
 uint32_t present_mask,colors[4];char strings[6][260];
} CohOriginalCostumeSnapshotPart;
/* A lossless, pointer-free copy of one successfully received costume body.
 * Null and empty strings remain distinct through presence bits. BodyType is
 * the original packet value (0..8), never a renderer-selected substitute.
 * super_colors order: primary, secondary, primary2, secondary2, tertiary,
 * quaternary; each retains the six original low/high slot pairs. */
typedef struct{
 uint32_t bodytype,part_count,header_present,color_skin;
 int32_t converted_scale,current_super_color;float scales[30];
 CohOriginalCostumeSGColor super_colors[6][6];
 char ent_type[260],geometry_prefix[260];
 CohOriginalCostumeSnapshotPart parts[30];
} CohOriginalCostumeSnapshot;
typedef struct{
 CohOriginalCostumeObject costume;CohOriginalCostumePart parts[30];const char *strings[120];int colors[120];
 int string_count,string_order,color_count,color_order;
 char literals[182][260];unsigned literal_count,wire_literal_count,part_strings,extra_strings,header_flags,after_count;
} CohOriginalCostumeScratch;
typedef struct{
 CohRepReader reader;CohOriginalCostumeReport report;CohOriginalCostumeScratch scratch;jmp_buf trap;
 const CohClientCostumeSlots *client_slots;
 uint32_t body_parts;int hasDebugInfo;unsigned cache_mode,cache_first,cache_index,cache_count;
} CohOriginalCostumeState;
typedef union{
 CohOriginalCostumeState state;uint8_t bytes[COH_ORIGINAL_COSTUME_WORKSPACE_BYTES];
 long double alignment;void *pointer_alignment;
} CohOriginalCostumeWorkspace;
/* Compile/execute the WHOLE unchanged pinned original costume_receive and its
 * original cache/indexed-string/color functions with bounded packet/storage
 * primitives. at_costume_begin is before the two optional name flags, not at
 * part_count. body_parts is the caller's verified local source catalog count;
 * there is no runtime-generation policy or producer lease in this function.
 * Original bodytype table/getBodyTypeCount supplies9; local capacity remains30.
 * Literal/cache paths continue. At the first indexed dictionary dependency the
 * original receiver stops BEFORE its index Pack, preserving the exact cursor.
 * No guessed stash width, synthetic string/palette or skipped part is used.
 * COH_OK means this costume's complete original wire body only, not actor/world
 * authority or application ACK. All source pointers/strings and scratch are
 * wiped before return. Caller reader is never mutated; output is transactional
 * for invalid API/alias input. workspace is off-stack, exclusive for the call;
 * no heap allocation or external global cache. All caller spans are disjoint.
 * Caller charges actual64KiB workspace, packet, report,4KiB stack reserve and
 * all retained resources to the unchanged8MiB initial aggregate budget. */
/* Same unchanged source receiver, with the verified CLIENT primary-slot view.
 * Indexed strings use existing scratch storage; no decoded pointers escape the
 * call. Missing tables still stop before their index Pack. Supplied slots are
 * immutable and live through this call; caller charges raw+index+view alongside
 * packet, workspace, all retained owners and stack in the8MiB aggregate. */
CohStatus coh_original_costume_receive_slots(const CohRepReader *at_costume_begin,
 uint32_t body_parts,const CohClientCostumeSlots *,CohOriginalCostumeWorkspace *,
 CohOriginalCostumeReport *);
/* Optional caller-owned capture publishes only for COH_OK/complete body, before
 * the original scratch is wiped. Failure preserves the previous capture.
 * The complete snapshot span must be disjoint from every other caller span;
 * caller charges sizeof(*capture) once alongside packet/workspace/source slots
 * and native stack under the existing 8 MiB initial aggregate. No extra heap
 * or snapshot-sized stack temporary is used. This grants no actor authority. */
CohStatus coh_original_costume_receive_slots_capture(const CohRepReader *,
 uint32_t body_parts,const CohClientCostumeSlots *,CohOriginalCostumeWorkspace *,
 CohOriginalCostumeReport *,CohOriginalCostumeSnapshot *capture);
CohStatus coh_original_costume_receive(const CohRepReader *at_costume_begin,
 uint32_t body_parts,CohOriginalCostumeWorkspace *,CohOriginalCostumeReport *);
#ifdef __cplusplus
}
#endif
#endif
