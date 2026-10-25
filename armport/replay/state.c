/* Deterministic, explicitly partial receiver-state observations. No pointers,
 * padding, clocks, interpolation or normalized rendering quaternions are hashed.
 * Power inventory observations are partial; team/task/UI-tail and other
 * receive destinations still need implementation/review.
 */
#include <winsock2.h>
#include <windows.h>
#include <wincrypt.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include "state.h"
#include "clientcomm/armport_replay.h"
#include "entity/entity.h"
#include "entity/entclient.h"
#include "entity/entPlayer.h"
#include "entity/character_base.h"
#include "entity/costume.h"
#include "entity/powers.h"
#include "entity/boost.h"
#include "entity/character_inventory.h"
#include "entity/salvage.h"
#include "entity/Concept.h"
#include "bases/DetailRecipe.h"
#include "bases/basedata.h"
#include <utilitieslib/components/earray.h>

/* stdtypes.h replaces these with ARRAY_SIZE_CHECKED wrappers. This writer
 * deliberately uses heap-buffer offsets, whose sizeof is only pointer width.
 * Keep the CRT functions and our explicit remaining-capacity bounds. */
#undef vsnprintf
#undef snprintf
#undef sprintf

#define CAPACITY (16 * 1024 * 1024)
static int active;
static char *buffer;
static size_t used;
static struct { unsigned id, create, valid, raw[3]; } orientation[MAX_ENTITIES_PRIVATE];

static void check_at(int ok, const char *condition, int line)
{
    if (!ok) {
        char message[512];
        DWORD written;
        int size = snprintf(message, sizeof(message),
            "ArmPort replay state failed at line %d: %s\n", line, condition);
        if (size > 0 && size < sizeof(message))
            WriteFile(GetStdHandle(STD_ERROR_HANDLE), message, size, &written, NULL);
        ExitProcess(3);
    }
}
#define check(condition) check_at(!!(condition), #condition, __LINE__)
static void out(const char *format, ...)
{
    int count;
    va_list args;
    va_start(args, format);
    count = vsnprintf(buffer + used, CAPACITY - used, format, args);
    va_end(args);
    check(count >= 0 && (size_t)count < CAPACITY - used);
    used += count;
}
static void string(const char *value)
{
    const unsigned char *p = (const unsigned char *)value;
    if (!p) { out("null"); return; }
    out("\"");
    for (; *p; ++p) {
        if (*p == '"' || *p == '\\') out("\\%c", *p);
        else if (*p < 32 || *p >= 127) out("\\u%04x", *p);
        else out("%c", *p);
    }
    out("\"");
}
static void words(const void *data, size_t bytes)
{
    size_t i;
    check(bytes % 4 == 0);
    out("[");
    for (i = 0; i < bytes; i += 4) {
        unsigned value;
        memcpy(&value, (const char *)data + i, 4);
        out("%s%u", i ? "," : "", value);
    }
    out("]");
}
void armportReplayStateInit(void)
{
    check(!active);
    buffer = malloc(CAPACITY);
    check(buffer != NULL);
    memset(orientation, 0, sizeof(orientation));
    active = 1;
}
void armportReplayOrientation(Entity *e, int axis, unsigned value, int accepted)
{
    int idx;
    if (!active || !accepted) return;
    idx = e->svr_idx;
    if (idx <= 0 || idx >= MAX_ENTITIES_PRIVATE || ent_xlat[idx] != e) return;
    check(axis >= 0 && axis < 3 && value < 512);
    if (orientation[idx].id != e->id || orientation[idx].create != e->pkt_id_create) {
        memset(&orientation[idx], 0, sizeof(orientation[idx]));
        orientation[idx].id = e->id;
        orientation[idx].create = e->pkt_id_create;
    }
    orientation[idx].raw[axis] = value;
    orientation[idx].valid |= 1U << axis;
}
static void costume(const cCostume *c)
{
    int i, count;
    if (!c) { out("null"); return; }
    out("{\"bodytype\":%d,\"villain_idx\":%d,\"scales_f32_bits\":", c->appearance.bodytype, c->appearance.iVillainIdx);
    words(c->appearance.fScales, sizeof(c->appearance.fScales));
    out(",\"compressed_scales\":"); words(c->appearance.compressedScales, sizeof(c->appearance.compressedScales));
    out(",\"skin\":"); words(&c->appearance.colorSkin, sizeof(c->appearance.colorSkin));
    out(",\"ent_type_file\":"); string(c->appearance.entTypeFile);
    out(",\"file_prefix\":"); string(c->appearance.costumeFilePrefix);
    count = eaSize(&c->parts);
    check(count >= 0 && count <= 256);
    out(",\"num_parts\":%d,\"parts\":[", c->appearance.iNumParts);
    for (i = 0; i < count; ++i) {
        const CostumePart *p = c->parts[i];
        if (i) out(",");
        if (!p) { out("null"); continue; }
        out("{\"name\":"); string(p->pchName);
        out(",\"tex1\":"); string(p->pchTex1);
        out(",\"tex2\":"); string(p->pchTex2);
        out(",\"geometry\":"); string(p->pchGeom);
        out(",\"fx\":"); string(p->pchFxName);
        out(",\"region\":"); string(p->regionName);
        out(",\"body_set\":"); string(p->bodySetName);
        out(",\"colors\":"); words(p->color, sizeof(p->color));
        out("}");
    }
    out("]}");
}

/* Persist logical identities and individual fields, never object bytes or
 * pointers. Preserve array order/null slots. These observations do not claim
 * full power activation or tail-state coverage. Local power/boost timers and
 * ulCreationTime (also initialized from the host clock by power_Create) are
 * deliberately absent until a wire-provenance observer can separate them. */
static void base_power(const BasePower *p)
{
    string(p ? p->pchFullName : NULL);
}
static void boost(const Boost *b)
{
    int i;
    if (!b) { out("null"); return; }
    out("{\"base\":"); base_power(b->ppowBase);
    out(",\"index\":%d,\"level\":%d,\"combines\":%d,\"vars_f32_bits\":",
        b->idx, b->iLevel, b->iNumCombines);
    words(b->afVars, sizeof(b->afVars));
    out(",\"powerup_slots\":[");
    for (i = 0; i < sizeof(b->aPowerupSlots) / sizeof(b->aPowerupSlots[0]); ++i) {
        const PowerupSlot *slot = &b->aPowerupSlots[i];
        out("%s{\"type\":%d,\"name\":", i ? "," : "", slot->reward.type);
        string(slot->reward.name);
        out(",\"filled\":%d}", slot->filled);
    }
    out("]}");
}
static void boosts(Boost *const *items)
{
    int i, count = eaSize(&items);
    check(count >= 0 && count <= 4096);
    out("[");
    for (i = 0; i < count; ++i) { if (i) out(","); boost(items[i]); }
    out("]");
}
static void power_sets(PowerSet *const *sets)
{
    int i, j, count = eaSize(&sets);
    check(count >= 0 && count <= 4096);
    out("[");
    for (i = 0; i < count; ++i) {
        const PowerSet *set = sets[i];
        int powers;
        if (i) out(",");
        if (!set) { out("null"); continue; }
        out("{\"base\":"); string(set->psetBase ? set->psetBase->pchFullName : NULL);
        out(",\"index\":%d,\"level_bought\":%d,\"powers\":[", set->idx, set->iLevelBought);
        powers = eaSize(&set->ppPowers);
        check(powers >= 0 && powers <= 4096);
        for (j = 0; j < powers; ++j) {
            const Power *power = set->ppPowers[j];
            if (j) out(",");
            if (!power) { out("null"); continue; }
            out("{\"base\":"); base_power(power->ppowBase);
            out(",\"original\":"); base_power(power->ppowOriginal);
            out(",\"index\":%d,\"unique_id\":%d,\"level_bought\":%d,\"charges\":%d,"
                "\"boost_slots_bought\":%d,\"enabled\":%d,\"disabled_manually\":%d,\"range_f32_bits\":",
                power->idx, power->iUniqueID, power->iLevelBought, power->iNumCharges,
                power->iNumBoostsBought, power->bEnabled, power->bDisabledManually);
            words(&power->fRangeLast, sizeof(power->fRangeLast));
            out(",\"usage_f32_bits\":"); words(&power->fUsageTime, sizeof(power->fUsageTime));
            out(",\"available_f32_bits\":"); words(&power->fAvailableTime, sizeof(power->fAvailableTime));
            out(",\"boosts\":"); boosts(power->ppBoosts);
            out(",\"global_boosts\":"); boosts(power->ppGlobalBoosts);
            out("}");
        }
        out("]}");
    }
    out("]");
}
static void power_inventory(const Character *p)
{
    int i, j;
    out("{\"current_build\":%d,\"active_build\":%d,\"build_levels\":", p->iCurBuild, p->iActiveBuild);
    words(p->iBuildLevels, sizeof(p->iBuildLevels));
    out(",\"current_sets\":"); power_sets(p->ppPowerSets);
    out(",\"build_sets\":[");
    for (i = 0; i < MAX_BUILD_NUM; ++i) {
        if (i) out(",");
        power_sets(p->ppBuildPowerSets[i]);
    }
    out("],\"inspiration_cols\":%d,\"inspiration_rows\":%d,\"inspirations\":[",
        p->iNumInspirationCols, p->iNumInspirationRows);
    for (i = 0; i < CHAR_INSP_MAX_COLS; ++i) {
        out("%s[", i ? "," : "");
        for (j = 0; j < CHAR_INSP_MAX_ROWS; ++j) {
            if (j) out(",");
            base_power(p->aInspirations[i][j]);
        }
        out("]");
    }
    out("],\"boost_slots\":%d,\"boost_inventory\":[", p->iNumBoostSlots);
    for (i = 0; i < CHAR_BOOST_MAX; ++i) { if (i) out(","); boost(p->aBoosts[i]); }
    out("]}");
}


/* Read-only inventory destinations of character_ReceiveInventories and
 * entity_ReceiveInvUpdate. Empty definitions remain distinct from null slots;
 * no getter discards their amounts. Concepts retain all four received F32s. */
static void inventory_item(int id, const char *name, unsigned amount)
{
    out("{\"id\":%d,\"name\":", id); string(name);
    out(",\"amount\":%u}", amount);
}
#define INVENTORY_LIST(field, type, definition, idfield, namefield) do { \
    int item_index, item_count = eaSize(&p->field); \
    check(item_count >= 0 && item_count <= 8192); \
    out(",\"" #field "\":["); \
    for (item_index = 0; item_index < item_count; ++item_index) { \
        const type *item = p->field[item_index]; \
        if (item_index) out(","); \
        if (!item) out("null"); \
        else inventory_item(item->definition ? item->definition->idfield : 0, \
                            item->definition ? item->definition->namefield : NULL, item->amount); \
    } \
    out("]"); \
} while (0)
static void generic_inventories(const Character *p)
{
    int i, count = eaSize(&p->conceptInv);
    check(count >= 0 && count <= 8192);
    out("{\"salvage_total\":%d,\"stored_salvage_total\":%d,\"recipe_total\":%d,\"auction_total\":%d",
        p->salvageInvTotalSlots, p->storedSalvageInvTotalSlots, p->recipeInvTotalSlots, p->auctionInvTotalSlots);
    INVENTORY_LIST(salvageInv, SalvageInventoryItem, salvage, salId, pchName);
    INVENTORY_LIST(storedSalvageInv, SalvageInventoryItem, salvage, salId, pchName);
    INVENTORY_LIST(recipeInv, RecipeInventoryItem, recipe, id, pchName);
    INVENTORY_LIST(detailInv, DetailInventoryItem, item, id, pchName);
    out(",\"conceptInv\":[");
    for (i = 0; i < count; ++i) {
        const ConceptInventoryItem *item = p->conceptInv[i];
        const ConceptItem *concept;
        if (i) out(",");
        if (!item) { out("null"); continue; }
        concept = item->concept;
        out("{\"amount\":%u,\"concept\":", item->amount);
        if (!concept) out("null");
        else {
            out("{\"id\":%d,\"name\":", concept->def ? concept->def->id : 0);
            string(concept->def ? concept->def->name : NULL);
            out(",\"vars_f32_bits\":"); words(concept->afVars, sizeof(concept->afVars));
            out("}");
        }
        out("}");
    }
    out("]}");
}
#undef INVENTORY_LIST

static unsigned deletes;
static void deletion(unsigned pkt_id, int idx, int id)
{
    out("%s{\"svr_idx\":%d,\"id\":%d,\"pkt_id\":%u}", deletes++ ? "," : "", idx, id, pkt_id);
}
unsigned armportReplayStateSave(const char *directory, unsigned index, char digest[65])
{
    int idx, axis;
    unsigned count = 0;
    char path[1024];
    HANDLE file;
    DWORD written, hash_size = 32;
    HCRYPTPROV provider = 0;
    HCRYPTHASH hash = 0;
    unsigned char hash_bytes[32];
    check(active);
    used = 0;
    out("{\"schema\":\"armport-receiver-state-v1-partial\",\"state_schema_complete\":false,\"entities\":[");
    for (idx = 1; idx < MAX_ENTITIES_PRIVATE; ++idx) {
        Entity *e = ent_xlat[idx];
        unsigned valid;
        if (!e) continue;
        check(e->svr_idx == idx);
        out("%s{\"svr_idx\":%d,\"id\":%u,\"db_id\":%d,\"type\":%d,\"name\":", count++ ? "," : "", idx, e->id, e->db_id, ENTTYPE(e));
        string(e->name);
        out(",\"pkt_id_create\":%u,\"net_ipos\":[%d,%d,%d],\"wire_qrot9\":[", e->pkt_id_create, e->net_ipos[0], e->net_ipos[1], e->net_ipos[2]);
        valid = orientation[idx].id == e->id && orientation[idx].create == e->pkt_id_create ? orientation[idx].valid : 0;
        for (axis = 0; axis < 3; ++axis) {
            if (axis) out(",");
            if (valid & (1U << axis)) out("%u", orientation[idx].raw[axis]); else out("null");
        }
        out("],\"pkt_id_pos\":"); words(e->pkt_id_pos, sizeof(e->pkt_id_pos));
        out(",\"pkt_id_qrot\":"); words(e->pkt_id_qrot, sizeof(e->pkt_id_qrot));
        out(",\"costume_index\":%d,\"costume\":", e->costumeIndex); costume(e->costume);
        out(",\"character\":");
        if (e->pchar) {
            Character *p = e->pchar;
            out("{\"level\":%d,\"xp\":%d,\"debt\":%d,\"rest\":%d,\"influence\":%d,\"attr_cur_f32_bits\":", p->iLevel, p->iExperiencePoints, p->iExperienceDebt, p->iExperienceRest, p->iInfluencePoints);
            /* CharacterAttributes consists exclusively of F32 fields/arrays. */
            words(&p->attrCur, sizeof(p->attrCur));
            out(",\"attr_max_f32_bits\":"); words(&p->attrMax, sizeof(p->attrMax));
            out(",\"power_inventory\":"); power_inventory(p);
            out(",\"generic_inventories\":"); generic_inventories(p);
            out("}");
        } else out("null");
        out(",\"player\":");
        if (e->pl) out("{\"lastClientStatePktId\":%u}", e->pl->lastClientStatePktId); else out("null");
        out("}");
    }
    out("],\"delete_history\":["); deletes = 0; armportReplayDeletes(deletion); out("]}\n");
    check(snprintf(path, sizeof(path), "%s/state-%03u.json", directory, index) < sizeof(path));
    file = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
    check(file != INVALID_HANDLE_VALUE);
    check(WriteFile(file, buffer, (DWORD)used, &written, NULL) && written == used);
    check(CloseHandle(file));
    check(CryptAcquireContextA(&provider, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT));
    check(CryptCreateHash(provider, CALG_SHA_256, 0, 0, &hash));
    check(CryptHashData(hash, (BYTE *)buffer, (DWORD)used, 0));
    check(CryptGetHashParam(hash, HP_HASHVAL, hash_bytes, &hash_size, 0) && hash_size == 32);
    CryptDestroyHash(hash); CryptReleaseContext(provider, 0);
    for (idx = 0; idx < 32; ++idx) sprintf(digest + idx * 2, "%02x", hash_bytes[idx]);
    return count;
}
