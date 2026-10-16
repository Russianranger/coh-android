#ifndef COH_COSTUME_H
#define COH_COSTUME_H
#include "coh_entities.h"
#define COH_COSTUME_PART_MAX 30u
#define COH_COSTUME_CUSTOM_MAX 63u
#define COH_COSTUME_CACHE_MAX 119u
#define COH_COSTUME_SCALE_COUNT 30u
#define COH_COSTUME_DICTIONARY_SLOT_MAX 65536u
#define COH_COSTUME_DICTIONARY_BYTES_MAX (4u*1024u*1024u)
/* Source stash storage slots, including empty slots. Never substitute a dense
 * list: packet widths use ceil(log2(original stashGetMaxSize)). Strings exclude
 * NUL; data=NULL,size=0 is a hole; non-NULL,size=0 is a present empty string. */
typedef struct {uint32_t max_size;const CohBytes *slots;} CohEntCostumeStringTable;
typedef struct {
    uint32_t generation, body_parts, body_types;
    uint8_t manifest_sha256[32];
    CohEntCostumeStringTable strings, extra_strings;
    uint32_t palette_max_size;const uint32_t *palette;const uint8_t *palette_present;
} CohEntCostumeDictionaryInput;
typedef struct CohEntCostumeDictionary CohEntCostumeDictionary;
/* Copies all admitted data into one immutable allocation <= 4 MiB. expected
 * manifest identity must come from a separately verified source/profile import;
 * this API compares the supplied identity, it does not authenticate its origin
 * or calculate a digest of a capture. No authentic dictionary is bundled. */
CohStatus coh_ent_costume_dictionary_load(CohEntCostumeDictionary **,
    const CohEntCostumeDictionaryInput *, uint32_t expected_generation,
    const uint8_t expected_manifest_sha256[32]);
void coh_ent_costume_dictionary_free(CohEntCostumeDictionary *);
size_t coh_ent_costume_dictionary_bytes(const CohEntCostumeDictionary *);
typedef struct {uint32_t present;char value[260];} CohEntCostumeText;
typedef struct {CohEntCostumeText geometry,texture1,texture2,fx,region,body_set;uint32_t colors[4];} CohEntCostumePart;
typedef struct {
    uint32_t generation;uint8_t manifest_sha256[32];
    CohEntCostumeText entity_type_file,prefix;
    uint32_t body_type,skin_color,converted_scale,super_color_set,extra_info;
    uint32_t super_colors[6][12];float scales[COH_COSTUME_SCALE_COUNT];
    uint32_t part_count;CohEntCostumePart parts[COH_COSTUME_PART_MAX];size_t end_bit;
} CohEntCostume;
typedef struct {
    CohEntCostume candidate;
    CohEntCostumeText strings[COH_COSTUME_CACHE_MAX];
    uint32_t colors[COH_COSTUME_CACHE_MAX],string_count,color_count,string_order,color_order;
} CohEntCostumeWorkspace;
/* Raw costume_receive body shared by full/owned costume variants. Off-thread
 * caller-owned workspace; output and reader are unchanged on failure. Exact
 * expected generation prevents reuse against a different dictionary. Parsing
 * resolves wire dictionary strings only, never geometry/material/rig assets.
 * These are non-debug wire APIs. No complete entity/full-update authority. */
CohStatus coh_ent_costume(CohRepReader *,const CohEntCostumeDictionary *,
    uint32_t expected_generation,CohEntCostumeWorkspace *,CohEntCostume *,CohEntFailure *);
typedef struct {uint32_t colors[2];char region[260];} CohEntCustomCostumePart;
typedef struct {uint32_t skin_color,count;CohEntCustomCostumePart parts[COH_COSTUME_CUSTOM_MAX];size_t end_bit;} CohEntCustomCostume;
CohStatus coh_ent_custom_costume(CohRepReader *,CohEntCustomCostume *,CohEntFailure *);
#define COH_COSTUME_STORED_MAX 10u
#define COH_COSTUME_REWARDS_MAX 256u
/* Wire event envelope, not persistent player state. Optional fields retain
 * their source presence flags; deferred changes need an eventual simulation
 * policy. Its full enclosing transaction must apply packet order and identity.
 * In particular, a stale owned-costume body is still validated, never skipped. */
typedef struct {
    uint32_t generation;uint8_t manifest_sha256[32];
    /* additional_slots is source num_costume_slots, NOT total owned slots:
     * costume_get_num_slots adds one and account-product entitlements. */
    uint32_t type,is_self,deferred,current_slot,additional_slots,multiple,body_count;
    uint32_t reward_count[2];CohEntCostumeText rewards[2][COH_COSTUME_REWARDS_MAX];
    CohEntCostume bodies[COH_COSTUME_STORED_MAX];
    uint32_t super_present,super_mode,hide_emblem;CohEntCostume super_body;
    CohEntCostumeText special_fx;
    uint32_t npc_present,npc_index,npc_costume_index,custom_present;
    CohEntCostumeText world_group;CohEntCustomCostume custom;
    char sequence[260];size_t end_bit;
} CohEntCostumeEnvelope;
typedef struct {
    CohEntCostumeEnvelope candidate;CohEntCostumeWorkspace body;
} CohEntCostumeEnvelopeWorkspace;
/* Complete non-debug entReceiveCostume wire envelope only (no translucency,
 * power customization, asset resolution or complete entity admission).
 * expected_self is the transaction owner's already verified entity ownership.
 * Reader/output remain unchanged on failure; workspace must be off stack. */
CohStatus coh_ent_costume_envelope(CohRepReader *,const CohEntCostumeDictionary *,
    uint32_t expected_generation,int expected_self,CohEntCostumeEnvelopeWorkspace *,
    CohEntCostumeEnvelope *,CohEntFailure *);
#define COH_POWER_CUSTOM_LIST_MAX 512u
#define COH_POWER_CUSTOM_TOTAL_MAX 4096u
typedef struct {uint32_t power_crc,colors[2];char token[260];} CohEntPowerCustom;
typedef struct {uint32_t present,first,count;size_t end_bit;} CohEntPowerCustomRange;
typedef struct {
    uint32_t type,is_self,current_slot,additional_slots,multiple,list_count,item_count;
    CohEntPowerCustomRange lists[COH_COSTUME_STORED_MAX];
    CohEntPowerCustom items[COH_POWER_CUSTOM_TOTAL_MAX];size_t end_bit;
} CohEntPowerCustomEnvelope;
typedef struct {CohEntPowerCustomEnvelope candidate;} CohEntPowerCustomWorkspace;
/* Complete standalone non-debug entReceivePowerCust wire envelope. Raw power
 * CRCs remain unresolved; no source power dictionary or asset admission.
 * A list with present=0 retains previous data, while present=1/count=0 clears
 * it when a future complete transaction applies the event. Wire order and
 * duplicate CRCs are retained, not source runtime sorted. Off-stack workspace,
 * no parser allocation; output/reader commit atomically on complete syntax. */
CohStatus coh_ent_power_custom(CohRepReader *,int expected_self,
    CohEntPowerCustomWorkspace *,CohEntPowerCustomEnvelope *,CohEntFailure *);
#endif
