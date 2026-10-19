#ifndef COH_INITIAL_AIANIM_PROBE_H
#define COH_INITIAL_AIANIM_PROBE_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_AIANIM_INPUT=1,COH_INITIAL_AIANIM_UPDATE,COH_INITIAL_AIANIM_STRING_FLAG,
 COH_INITIAL_AIANIM_STRING,COH_INITIAL_AIANIM_NETFX
} CohInitialAiAnimStage;
typedef struct {
 CohStatus status;CohInitialAiAnimStage stage;
 size_t begin_bit,ai_end_bit,failure_bit;
 uint32_t update_seen,string_present,string_bytes,ai_animation_validated;
} CohInitialAiAnimProbe;
#define COH_INITIAL_AIANIM_TEXT_MAX 1000u /* includes terminating NUL */
/* INITIAL full-create AI leaf after the validated triggered list in SAME loan.
 * The enclosing owner supplies triggered_end_bit; no scan/byte realignment.
 * Source create forces send_appearance, hence outer update1 is required. The
 * inner optional string may be absent (NULL/empty source text). Read raw bytes
 * through NUL under the existing native1000-byte cap; original char* producer
 * has no such cap. Packed text preserves bit offset; rounded compressed flags
 * must still be Boolean. No UTF-8 or dictionary requirement is invented.
 *
 * No string buffer, text retention, animation lookup/assignment or event call.
 * string_bytes excludes NUL (or counts only the bounded nonzero prefix on
 * refusal). Inputs immutable; invalid API inputs/aliases preserve output.
 * Complete leaf returns UNSUPPORTED before NetFX envelope flags, or INVALID
 * there with ai_animation_validated true if no following bits exist.
 * Numeric observations never grant character/resource ownership or ACK.
 * No allocation; existing4MiB decoded cap and fixed report limit apply.
 */
CohStatus coh_initial_aianim_probe(const CohRepReader *,CohInitialAiAnimProbe *);
#define COH_INITIAL_AIANIM_REPORT_MAX 1024u
int coh_initial_aianim_probe_json(const CohInitialAiAnimProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
