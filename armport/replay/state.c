/* Deterministic, explicitly partial receiver-state observations. No pointers,
 * padding, clocks, interpolation or normalized rendering quaternions are hashed.
 * Entity/player/UI-tail observations remain partial; other receive
 * destinations still need implementation/review.
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
#include "entity/classes.h"
#include "entity/origins.h"
#include "entity/costume.h"
#include "entity/powers.h"
#include "entity/power_customization.h"
#include "entity/boost.h"
#include "entity/character_inventory.h"
#include "entity/salvage.h"
#include "entity/Concept.h"
#include "bases/DetailRecipe.h"
#include "bases/basedata.h"
#include "player/badges_client.h"
#include "entity/teamCommon.h"
#include "entity/Supergroup.h"
#include "entity/RewardToken.h"
#include "entity/friendCommon.h"
#include "UI/uiGroupWindow.h"
#include "UI/uiAutomap.h"
#include "UI/uiCompass.h"
#include "UI/uiTurnstile.h"
#include "UI/uiKeybind.h"
#include "UI/uiOptions_Type.h"
#include "gameComm/trayCommon.h"
#include "gameComm/itemselect.h"
#include "UI/uiCursor.h"
#include "UI/uiTarget.h"
#include "UI/uiBuff.h"
#include "entity/attrib_description.h"
#include "entity/attrib_net.h"
#include "entity/netfx.h"
#include <utilitieslib/utils/textparser.h>
#include "gameComm/wdwbase.h"
#include "gameComm/dooranimcommon.h"
#include "UI/uiWindows.h"
#include "UI/uiListView.h"
#include "cmdparse/cmdcommon.h"
#include "graphics/textureatlas.h"
#include "group/groupdyn.h"
#include "cmdparse/cmdgame.h"
#include "storyarc/storyarcClient.h"
#include "storyarc/contactClient.h"
#include <utilitieslib/components/earray.h>
#include <utilitieslib/components/StashTable.h>

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
static struct { unsigned seconds, valid; } alignment_delays[ALIGNMENT_POINT_MAX_COUNT];
static struct { unsigned valid, bits[4]; } desaturation;

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
    memset(alignment_delays, 0, sizeof(alignment_delays));
    memset(&desaturation, 0, sizeof(desaturation));
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
void armportReplayAlignmentDelay(unsigned index, unsigned seconds)
{
    if (!active) return;
    check(index < ALIGNMENT_POINT_MAX_COUNT);
    alignment_delays[index].seconds = seconds;
    alignment_delays[index].valid = 1;
}
static void super_colors(const SGColorBits *values)
{
    int i;
    out("[");
    for (i = 0; i < NUM_SG_COLOR_SLOTS; ++i)
        out("%s[%u,%u]", i ? "," : "", values[i].SGBitSetLow, values[i].SGBitSetHigh);
    out("]");
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
    out(",\"converted_scale\":%d,\"current_super_color_set\":%d,\"super_colors\":{\"primary\":",
        c->appearance.convertedScale, c->appearance.currentSuperColorSet);
    super_colors(c->appearance.superColorsPrimaryU);
    out(",\"secondary\":"); super_colors(c->appearance.superColorsSecondaryU);
    out(",\"primary2\":"); super_colors(c->appearance.superColorsPrimary2U);
    out(",\"secondary2\":"); super_colors(c->appearance.superColorsSecondary2U);
    out(",\"tertiary\":"); super_colors(c->appearance.superColorsTertiaryU);
    out(",\"quaternary\":"); super_colors(c->appearance.superColorsQuaternaryU);
    out("}");
    count = eaSize(&c->parts);
    check(count >= 0 && count <= 256);
    check(c->appearance.iNumParts >= 0 && c->appearance.iNumParts <= count);
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

/* Read all retained receive destinations, including inactive/deferred slots.
 * The local deferred-change clock deadlines are deliberately not serialized.
 * Temporary editor colors and derived display/source/store metadata are absent. */
static void player_costumes(const EntPlayer *p)
{
    int i;
    out("{\"current\":%d,\"current_super\":%d,\"unlocked_slots\":%d,\"stored_count\":%d,"
        "\"npc_index\":%d,\"supergroup_mode\":%d,\"hide_emblem\":%d,\"pending_number\":%d,\"slots\":[",
        p->current_costume, p->current_supercostume, p->num_costume_slots, p->num_costumes_stored,
        p->npc_costume, p->supergroup_mode, p->hide_supergroup_emblem, p->pendingCostumeNumber);
    for (i = 0; i < MAX_COSTUMES; ++i) {
        if (i) out(",");
        costume((const cCostume *)p->costume[i]);
    }
    out("],\"super\":"); costume((const cCostume *)p->superCostume);
    out(",\"pending\":"); costume((const cCostume *)p->pendingCostume);
    out("}");
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


/* Badge award timestamps below are received U32 values, not host clocks.
 * Localized badge text/buttons are derived UI data and remain excluded. */
static void player_badges(const EntPlayer *p)
{
    int i;
    out("{\"states\":"); words(p->aiBadges, sizeof(p->aiBadges));
    out(",\"recent\":[");
    for (i = 0; i < BADGE_ENT_RECENT_BADGES; ++i)
        out("%s{\"index\":%d,\"time_awarded\":%u}", i ? "," : "",
            p->recentBadges[i].idx, p->recentBadges[i].timeAwarded);
    out("],\"monitor\":[");
    for (i = 0; i < MAX_BADGE_MONITOR_ENTRIES; ++i)
        out("%s%d", i ? "," : "", p->badgeMonitorInfo[i].iIdx);
    out("]}");
}
static void badge_client_state(void)
{
    int i;
    out("{\"debug_display_mode\":%d,\"filenames\":[", g_DebugBadgeDisplayMode);
    for (i = 0; i < BADGE_ENT_MAX_BADGES; ++i) {
        if (i) out(",");
        string(g_pchBadgeFilename[i]);
    }
    out("]}");
}

/* Only active member slots are observed here. Unused allocation tails and
 * derived league UI rosters are not a full-state claim. Fixed strings must
 * terminate inside their original storage, before string() can scan them. */
static void fixed_string(const char *value, size_t capacity)
{
    check(memchr(value, 0, capacity) != NULL);
    string(value);
}
static void group_members(const TeamMembers *members, int maximum)
{
    int i;
    check(members->count >= 0 && members->count <= maximum);
    check(!members->count || (members->ids && members->onMapserver && members->names));
    out("{\"leader\":%d,\"members\":[", members->leader);
    for (i = 0; i < members->count; ++i) {
        out("%s{\"db_id\":%d,\"on_mapserver\":%d,\"name\":", i ? "," : "",
            members->ids[i], members->onMapserver[i]);
        fixed_string(members->names[i], sizeof(MemberName)); out("}");
    }
    out("]}");
}
static void entity_groups(const Entity *e)
{
    int i;
    out("{\"team_id\":%d,\"league_id\":%d,\"team\":", e->teamup_id, e->league_id);
    if (e->teamup) {
        const Teamup *t = e->teamup;
        out("{\"level\":%d,\"mentor\":%d,\"active_player_db_id\":%d,\"roster\":",
            t->team_level, t->team_mentor, t->activePlayerDbid);
        group_members(&t->members, MAX_TEAM_MEMBERS); out("}");
    } else out("null");
    out(",\"league\":");
    if (e->league) {
        const League *l = e->league;
        out("{\"roster\":"); group_members(&l->members, MAX_LEAGUE_MEMBERS);
        out(",\"teams\":[");
        for (i = 0; i < l->members.count; ++i)
            out("%s{\"leader_db_id\":%d,\"lock_status\":%d}", i ? "," : "",
                l->teamLeaderIDs[i], l->lockStatus[i]);
        out("]}");
    } else out("null");
    out("}");
}
static void group_map_names(void)
{
    int i;
    out("{\"team\":[");
    for (i = 0; i < MAX_TEAM_MEMBERS; ++i) {
        if (i) out(",");
        fixed_string(teamMapNames[i], sizeof(MapName));
    }
    out("],\"league\":[");
    for (i = 0; i < MAX_LEAGUE_MEMBERS; ++i) {
        if (i) out(",");
        fixed_string(leagueMapNames[i], sizeof(MapName));
    }
    out("]}");
}

static void world_receive_state(void)
{
    int i;
    check(dyn_group_count >= 0 && dyn_group_count <= 1048576);
    check(!dyn_group_count || dyn_group_status);
    out("{\"dynamic_groups\":[");
    for (i = 0; i < dyn_group_count; ++i)
        out("%s{\"hp\":%u,\"repair\":%u}", i ? "," : "",
            (unsigned)dyn_group_status[i].hp, (unsigned)dyn_group_status[i].repair);
    out("],\"sky1\":%d,\"sky2\":%d,\"sky_weight_f32_bits\":",
        game_state.skyFade1, game_state.skyFade2);
    words(&game_state.skyFadeWeight, sizeof(game_state.skyFadeWeight));
    out("}");
}

static void story_clues(StoryClue *const *items)
{
    int i, n = eaSize(&items);
    check(n >= 0 && n <= 8192);
    out("[");
    for (i = 0; i < n; ++i) {
        const StoryClue *c = items[i];
        if (i) out(",");
        if (!c) { out("null"); continue; }
        out("{\"name\":"); string(c->name);
        out(",\"filename\":"); string(c->filename);
        out(",\"display_name\":"); string(c->displayname);
        out(",\"intro\":"); string(c->introstring);
        out(",\"detail\":"); string(c->detailtext);
        out(",\"icon\":"); string(c->iconfile);
        out("}");
    }
    out("]");
}
static void story_receive_state(void)
{
    const SouvenirClue *const *clues = armportReplaySouvenirClues();
    int i, n = eaSize(&clues);
    check(n >= 0 && n <= 8192);
    out("{\"clues\":"); story_clues(storyClues);
    out(",\"key_clues\":"); story_clues(keyClues);
    out(",\"server_souvenirs\":[");
    for (i = 0; i < n; ++i) {
        const SouvenirClue *c = clues[i];
        if (i) out(",");
        if (!c) { out("null"); continue; }
        out("{\"uid\":%d,\"name\":", c->uid); string(c->name);
        out(",\"filename\":"); string(c->filename);
        out(",\"display_name\":"); string(c->displayName);
        out(",\"icon\":"); string(c->icon);
        out(",\"description\":"); string(c->description);
        out("}");
    }
    out("],\"visit_locations\":[");
    n = eaSize(&visitLocations);
    check(n >= 0 && n <= 8192);
    for (i = 0; i < n; ++i) {
        if (i) out(",");
        string(visitLocations[i]);
    }
    out("]}");
}

static void task_difficulty(const StoryDifficulty *d)
{
    out("{\"level_adjust\":%d,\"team_size\":%d,\"always_av\":%d,\"dont_reduce_boss\":%d}",
        d->levelAdjust, d->teamSize, d->alwaysAV, d->dontReduceBoss);
}
static void task_state(const TaskStatus *t)
{
    if (!t) { out("null"); return; }
    out("{\"owner_dbid\":%d,\"context\":%d,\"subhandle\":%d,\"level\":%d,\"alliance\":%d,\"difficulty\":",
        t->ownerDbid, t->context, t->subhandle, t->level, t->alliance);
    task_difficulty(&t->difficulty);
    out(",\"description\":"); fixed_string(t->description, sizeof(t->description));
    out(",\"owner\":"); fixed_string(t->owner, sizeof(t->owner));
    out(",\"state\":"); fixed_string(t->state, sizeof(t->state));
    out(",\"detail\":"); fixed_string(t->detail, sizeof(t->detail));
    out(",\"intro\":"); fixed_string(t->intro, sizeof(t->intro));
    out(",\"filename\":"); fixed_string(t->filename, sizeof(t->filename));
    /* timeout/timezero are received U32 values, not the local iAskedWhen clock. */
    out(",\"timeout\":%u,\"timezero\":%u,\"timer_type\":%d,\"fail_on_timeout\":%u,"
        "\"complete\":%u,\"mission\":%u,\"running_mission\":%u,\"sg_mission\":%u,"
        "\"has_location\":%u,\"detail_invalid\":%u,\"zone_transfer\":%u,\"teleport_on_complete\":%u,"
        "\"enforce_time_limit\":%u,\"abandonable\":%u,\"zowie\":%u,\"location\":{\"contact_type\":%d,\"map\":",
        t->timeout, t->timezero, t->timerType, t->failOnTimeout,
        t->isComplete, t->isMission, t->hasRunningMission, t->isSGMission,
        t->hasLocation, t->detailInvalid, t->zoneTransfer, t->teleportOnComplete,
        t->enforceTimeLimit, t->isAbandonable, t->isZowie, t->location.contactType);
    fixed_string(t->location.mapName, sizeof(t->location.mapName));
    out(",\"name\":"); fixed_string(t->location.name, sizeof(t->location.name));
    /* Zowie destination positions may already have been replaced by local
     * automap selection. Preserve only ordinary received location coordinates. */
    out(",\"received_position_f32_bits\":");
    if (t->hasLocation && !t->isZowie) words(t->location.world_location[3], sizeof(t->location.world_location[3]));
    else out("null");
    out("},\"zinfo\":%u,\"zseed\":%u,\"zmap_id\":%d,\"ztype\":", t->zinfo, t->zseed, t->zmap_id);
    fixed_string(t->ztype, sizeof(t->ztype));
    out(",\"zname\":"); fixed_string(t->zname, sizeof(t->zname));
    out(",\"zpool_size\":[");
    {
        unsigned i;
        for (i = 0; i < sizeof(t->zpoolSize) / sizeof(t->zpoolSize[0]); ++i)
            out("%s%d", i ? "," : "", t->zpoolSize[i]);
    }
    out("]}");
}
static void task_sets(void)
{
    int i, j, n = eaSize(&teamTaskSets);
    check(n >= 0 && n <= 4096);
    out("[");
    for (i = 0; i < n; ++i) {
        const TaskStatusSet *s = teamTaskSets[i];
        int count;
        if (i) out(",");
        if (!s) { out("null"); continue; }
        out("{\"dbid\":%d,\"difficulty\":", s->dbid); task_difficulty(&s->difficulty);
        out(",\"tasks\":[");
        count = eaSize(&s->list);
        check(count >= 0 && count <= 8192);
        for (j = 0; j < count; ++j) {
            if (j) out(",");
            task_state(s->list[j]);
        }
        out("]}");
    }
    out("]");
}

static void contact_states(ContactStatus *const *items)
{
    int i, n = eaSize(&items);
    check(n >= 0 && n <= 8192);
    out("[");
    for (i = 0; i < n; ++i) {
        const ContactStatus *c = items[i];
        if (i) out(",");
        if (!c) { out("null"); continue; }
        out("{\"name\":"); string(c->name);
        out(",\"location_description\":"); string(c->locationDescription);
        out(",\"filename\":"); string(c->filename);
        out(",\"call_override\":"); string(c->callOverride);
        out(",\"ask_override\":"); string(c->askAboutOverride);
        out(",\"leave_override\":"); string(c->leaveOverride);
        out(",\"image_override\":"); string(c->imageOverride);
        out(",\"npc\":%d,\"handle\":%d,\"task_context\":%d,\"task_subhandle\":%d,"
            "\"points\":%d,\"friend_points\":%d,\"confidant_points\":%d,\"complete_points\":%d,\"heist_points\":%d,"
            "\"tip_type\":%u,\"notify\":%u,\"has_task\":%u,\"can_use_cell\":%u,\"has_location\":%u,"
            "\"newspaper\":%u,\"story_arc\":%u,\"mini_arc\":%u,\"wont_interact\":%u,\"meta_contact\":%u,"
            "\"alliance\":%d,\"universe\":%d,\"location\":{\"map\":",
            c->npcNum, c->handle, c->taskcontext, c->tasksubhandle,
            c->currentCP, c->friendCP, c->confidantCP, c->completeCP, c->heistCP,
            c->tipType, c->notifyPlayer, c->hasTask, c->canUseCell, c->hasLocation,
            c->isNewspaper, c->onStoryArc, c->onMiniArc, c->wontInteract, c->metaContact,
            c->alliance, c->universe);
        fixed_string(c->location.mapName, sizeof(c->location.mapName));
        out(",\"name\":"); fixed_string(c->location.name, sizeof(c->location.name));
        out(",\"received_position_f32_bits\":");
        if (c->hasLocation) words(c->location.world_location[3], sizeof(c->location.world_location[3]));
        else out("null");
        out("}}");
    }
    out("]");
}
static void contact_receive_state(void)
{
    unsigned i;
    out("{\"known\":"); contact_states(contacts);
    out(",\"accessible\":"); contact_states(contactsAccessibleNow);
    out(",\"alignment_delay_seconds\":[");
    for (i = 0; i < ALIGNMENT_POINT_MAX_COUNT; ++i) {
        if (i) out(",");
        if (alignment_delays[i].valid) out("%u", alignment_delays[i].seconds);
        else out("null");
    }
    out("],\"earned_alignments\":"); words(earnedAlignments, sizeof(earnedAlignments));
    out(",\"hero_points\":%u,\"vigilante_points\":%u,\"villain_points\":%u,\"rogue_points\":%u}",
        heroAlignmentPoints_self, vigilanteAlignmentPoints_self, villainAlignmentPoints_self, rogueAlignmentPoints_self);
}


/* Retained destinations of entReceiveOtherSupergroupInfo. No pointers,
 * local display caches or SpecialDetail's internal bValid bookkeeping.
 * Token/detail timestamps below are received server values, not host clocks. */
static void entity_supergroup_state(const Entity *e)
{
    const Supergroup *sg = e->supergroup;
    int i, count;
    out("{\"id\":%d,\"name\":", e->supergroup_id);
    fixed_string(e->supergroup_name, sizeof(e->supergroup_name));
    out(",\"emblem\":"); fixed_string(e->supergroup_emblem, sizeof(e->supergroup_emblem));
    out(",\"colors_u32\":[%u,%u],\"retained\":", (unsigned)e->supergroup_color[0], (unsigned)e->supergroup_color[1]);
    if (!sg) { out("null}"); return; }
    out("{\"spaces_for_items_of_power\":%d,\"mission\":", sg->spacesForItemsOfPower);
    task_state(sg->sgMission);
    count = eaSize(&sg->rewardTokens);
    check(count >= 0 && count <= 8192);
    out(",\"reward_tokens\":[");
    for (i = 0; i < count; ++i) {
        const RewardToken *token = sg->rewardTokens[i];
        if (i) out(",");
        if (!token) { out("null"); continue; }
        out("{\"name\":"); string(token->reward);
        out(",\"value\":%d,\"received_time\":%u}", token->val, token->timer);
    }
    count = eaSize(&sg->invRecipes);
    check(count >= 0 && count <= 8192);
    out("],\"recipes\":[");
    for (i = 0; i < count; ++i) {
        const RecipeInvItem *item = sg->invRecipes[i];
        if (i) out(",");
        if (!item) { out("null"); continue; }
        out("{\"count_u32\":%u,\"recipe\":", item->count);
        if (!item->recipe) out("null");
        else {
            out("{\"id\":%d,\"name\":", item->recipe->id);
            string(item->recipe->pchName); out("}");
        }
        out("}");
    }
    count = eaSize(&sg->specialDetails);
    check(count >= 0 && count <= 8192);
    out("],\"special_details\":[");
    for (i = 0; i < count; ++i) {
        const SpecialDetail *item = sg->specialDetails[i];
        if (i) out(",");
        if (!item) { out("null"); continue; }
        out("{\"creation_time\":%u,\"expiration_time\":%u,\"flags\":%u,\"detail\":",
            item->creation_time, item->expiration_time, item->iFlags);
        if (!item->pDetail) out("null");
        else {
            out("{\"id\":%d,\"name\":", item->pDetail->id);
            string(item->pDetail->pchName); out("}");
        }
        out("}");
    }
    out("]}}");
}

static unsigned deletes;
static void deletion(unsigned pkt_id, int idx, int id)
{
    out("%s{\"svr_idx\":%d,\"id\":%d,\"pkt_id\":%u}", deletes++ ? "," : "", idx, id, pkt_id);
}

/* The original receiver resolves and orders these retained lists. Preserve
 * that order and logical power identity, never allocator addresses or padding. */
static void tray_slots_state(const TrayObj *const *slots)
{
    int i, count = eaSize(&slots);
    check(count >= 0 && count <= 8192);
    out("[");
    for (i = 0; i < count; ++i) {
        const TrayObj *obj = slots[i];
        if (i) out(",");
        if (!obj) { out("null"); continue; }
        out("{\"type\":%d", (int)obj->type);
        if (obj->type == kTrayItemType_Power || obj->type == kTrayItemType_Inspiration)
            out(",\"set\":%d,\"power\":%d", obj->iset, obj->ipow);
        if (obj->type == kTrayItemType_Power) {
            out(",\"auto\":%d,\"power_name\":", obj->autoPower); string(obj->pchPowerName);
            out(",\"set_name\":"); string(obj->pchPowerSetName);
            out(",\"category\":"); string(obj->pchCategory);
        } else if (IS_TRAY_MACRO(obj->type)) {
            out(",\"command\":"); fixed_string(obj->command, sizeof(obj->command));
            out(",\"short_name\":"); fixed_string(obj->shortName, sizeof(obj->shortName));
            out(",\"icon_name\":"); fixed_string(obj->iconName, sizeof(obj->iconName));
        }
        out("}");
    }
    out("]");
}
static void player_tray_state(const Tray *tray)
{
    int i;
    if (!tray) { out("null"); return; }
    out("{\"current\":[");
    for (i = 0; i < kCurTrayType_Count; ++i) out("%s%d", i ? "," : "", tray->current_trays[i]);
    out("],\"mode\":%d,\"mode_alt2\":%d,\"indexes\":%u,\"has_storage\":%s,\"player_slots\":",
        tray->mode, tray->mode_alt2, (unsigned)tray->trayIndexes, tray->internals ? "true" : "false");
    tray_slots_state(armportReplayTraySlots(tray, 0));
    out(",\"server_slots\":"); tray_slots_state(armportReplayTraySlots(tray, 1));
    out("}");
}
static void default_power_state(const Power *power)
{
    if (!power) { out("null"); return; }
    out("{\"index\":%d,\"unique_id\":%d,\"set_index\":", power->idx, power->iUniqueID);
    if (power->psetParent) out("%d", power->psetParent->idx); else out("null");
    out(",\"base\":"); base_power(power->ppowBase);
    out(",\"original\":"); base_power(power->ppowOriginal);
    out("}");
}

static void leveling_pact_state(const Entity *e)
{
    out("{\"id\":%d,\"pact\":", e->levelingpact_id);
    if (!e->levelingpact) out("null");
    else {
        out("{\"count\":%d,\"roster\":", e->levelingpact->count);
        group_members(&e->levelingpact->members, MAX_LEVELINGPACT_MEMBERS);
        out("}");
    }
    out("}");
}

static void entity_pet_owner_state(const Entity *e)
{
    out("{\"owner_ref_words\":"); words(&e->erOwner, sizeof(e->erOwner));
    out(",\"creator_ref_words\":"); words(&e->erCreator, sizeof(e->erCreator));
    out(",\"created_by_power\":"); base_power(e->pchar ? e->pchar->ppowCreatedMe : NULL);
    out("}");
}

static void entity_netfx_receive_state(const Entity *e)
{
    int i;
    check(e->netfx_count >= 0 && e->netfx_count <= 8192);
    check(e->netfx_count <= e->netfx_max && (!e->netfx_count || e->netfx_list));
    out("[");
    for (i = 0; i < e->netfx_count; ++i) {
        const NetFx *f = &e->netfx_list[i];
        out("%s{\"command\":%u,\"net_id\":%u,\"handle\":%u,\"pitch\":%u,\"power_flags\":%u,"
            "\"has_tint\":%u,\"tint\":", i ? "," : "", (unsigned)f->command,
            f->net_id, f->handle, (unsigned)f->pitchToTarget, (unsigned)f->powerTypeflags,
            (unsigned)f->hasColorTint);
        if (f->hasColorTint) out("[%u,%u]", f->colorTint.primary.integer, f->colorTint.secondary.integer);
        else out("null");
        out(",\"delay_f32_bits\":"); words(&f->clientTimer, sizeof(f->clientTimer));
        out(",\"trigger_fx_id\":%u,\"duration_f32_bits\":", f->clientTriggerFx);
        words(&f->duration, sizeof(f->duration)); out(",\"radius_f32_bits\":"); words(&f->radius, sizeof(f->radius));
        out(",\"power\":%u,\"debris\":%u,\"origin_type\":%u,\"origin\":", (unsigned)f->power,
            f->debris, (unsigned)f->originType);
        if (f->originType == NETFX_POSITION) words(f->originPos, sizeof(f->originPos));
        else if (f->originType == NETFX_ENTITY) out("{\"entity\":%u,\"bone\":%u}", f->originEnt, (unsigned)f->bone_id);
        else out("null");
        out(",\"target_type\":%u,\"target\":", (unsigned)f->targetType);
        if (f->targetType == NETFX_POSITION) {
            out("{\"position_f32_bits\":"); words(f->targetPos, sizeof(f->targetPos));
            out(",\"entity\":%u}", f->targetEnt);
        } else if (f->targetType == NETFX_ENTITY) out("{\"entity\":%u}", f->targetEnt);
        else out("null");
        out("}");
    }
    /* Observe only the active receive union selected by each type. Unwritten
     * inactive coordinates/tint and renderer/server bookkeeping are excluded.
     */
    out("]");
}

static void entity_sequence_receive_state(const Entity *e)
{
    int i;
    check(e->triggered_move_count >= 0 && e->triggered_move_count <= MAX_TRIGGEREDMOVES);
    out("{\"next_index\":%d,\"next_bits\":%u,\"triggered\":[",
        e->next_move_idx, (unsigned)e->next_move_bits);
    for (i = 0; i < e->triggered_move_count; ++i) {
        const TriggeredMove *m = &e->triggered_moves[i];
        out("%s{\"index\":%d,\"delay_ticks\":%d,\"trigger_fx_id\":%d}",
            i ? "," : "", m->idx, m->ticksToDelay, m->triggerFxNetId);
    }
    /* move_change_timer mixes the received delay with local timing. Neither
     * it nor sequencer-created timestamps/state belong in this observation.
     */
    out("]}");
}

static void attribute_packet_ids(const ParseTable *schema, void *const *ids, unsigned depth)
{
    unsigned i;
    if (!ids) { out("null"); return; }
    check(schema != NULL && depth < 4);
    out("[");
    for (i = 0; (schema[i].name && schema[i].name[0]) || schema[i].type; ++i) {
        unsigned type = TOK_GET_TYPE(schema[i].type);
        check(i < 128);
        /* These receive tables contain only direct scalars/embedded structs.
         * Fail closed if their storage contract changes. No parser cache calls.
         */
        check((schema[i].type & ~(TOK_TYPE_MASK | TOK_PRECISION_MASK)) == 0);
        check(type == TOK_INT_X || type == TOK_F32_X || type == TOK_STRUCT_X);
        out("%s{\"field\":", i ? "," : ""); string(schema[i].name);
        out(",\"ids\":");
        if (type == TOK_STRUCT_X)
            attribute_packet_ids(schema[i].subtable, (void *const *)ids[i], depth + 1);
        else {
            /* Primitive recvdiff stores a U32 packet ID in a pointer slot. */
            UINT_PTR value = (UINT_PTR)ids[i];
            check(value <= 0xffffffffU);
            out("%u", (unsigned)value);
        }
        out("}");
    }
    out("]");
}

static void entity_attribute_packet_order_state(const Entity *e)
{
    out("{\"self\":"); attribute_packet_ids(SendCharacterToSelf, e->pkt_id_fullAttrDef, 0);
    out(",\"basic\":"); attribute_packet_ids(SendBasicCharacter, e->pkt_id_basicAttrDef, 0);
    out("}");
}

static void entity_packet_order_state(const Entity *e)
{
    /* Literal retained IDs; no additions to INITIAL-ID canonicalization. */
    out("{");
    out("\"pkt_id_friendslist\":%u", (unsigned)e->pkt_id_friendslist);
    out(",\"pkt_id_seq_move\":%u", (unsigned)e->pkt_id_seq_move);
    out(",\"pkt_id_seq_triggermove\":%u", (unsigned)e->pkt_id_seq_triggermove);
    out(",\"pkt_id_logout\":%u", (unsigned)e->pkt_id_logout);
    out(",\"pkt_id_supergroup\":%u", (unsigned)e->pkt_id_supergroup);
    out(",\"pkt_id_costume\":%u", (unsigned)e->pkt_id_costume);
    out(",\"pkt_id_powerCust\":%u", (unsigned)e->pkt_id_powerCust);
    out(",\"pkt_id_xlucency\":%u", (unsigned)e->pkt_id_xlucency);
    out(",\"pkt_id_titles\":%u", (unsigned)e->pkt_id_titles);
    out(",\"pkt_id_character_stats\":%u", (unsigned)e->pkt_id_character_stats);
    out(",\"pkt_id_targetting\":%u", (unsigned)e->pkt_id_targetting);
    out(",\"pkt_id_status_effects\":%u", (unsigned)e->pkt_id_status_effects);
    out(",\"pkt_id_buffs\":%u", (unsigned)e->pkt_id_buffs);
    out(",\"pkt_id_debug_info\":%u", (unsigned)e->pkt_id_debug_info);
    out(",\"pkt_id_rare_bits\":%u", (unsigned)e->pkt_id_rare_bits);
    out(",\"pkt_id_state_mode\":%u", (unsigned)e->pkt_id_state_mode);
    out("}");
}

static void entity_buff_state(const Entity *entity)
{
    int i, count = armportReplayBuffCount(entity);
    check(count >= 0 && count <= 8192);
    out("[");
    for (i = 0; i < count; ++i) {
        ArmPortReplayBuffView view;
        int j, present = armportReplayBuffAt(entity, i, &view);
        check(present >= 0 && present <= 1);
        if (i) out(",");
        if (!present) { out("null"); continue; }
        check(view.description_count >= 0 && view.description_count <= 8192);
        check(view.magnitude_count >= 0 && view.magnitude_count <= 8192);
        out("{\"power\":"); base_power(view.power);
        out(",\"uid\":%d,\"blink\":%d,\"delete_mark\":%d,\"descriptions\":[", view.uid, view.blink, view.delete_mark);
        for (j = 0; j < view.description_count; ++j) {
            const AttribDescription *description = view.descriptions[j];
            if (j) out(",");
            if (!description) { out("null"); continue; }
            out("{\"key\":%d,\"name\":", description->iKey); string(description->pchName); out("}");
        }
        out("],\"magnitude_f32_bits\":"); words(view.magnitudes, view.magnitude_count * sizeof(*view.magnitudes));
        out("}");
    }
    out("]");
}

static void character_target_state(const Character *p)
{
    /* EntityRef is S64, not a pointer. Preserve both literal U32 words. */
    out("{\"target_ref_words\":"); words(&p->erTargetInstantaneous, sizeof(p->erTargetInstantaneous));
    out(",\"assist_ref_words\":"); words(&p->erAssist, sizeof(p->erAssist));
    out("}");
}
static void target_receive_state(void)
{
    int i, count = eaSize(&g_pperPlacators);
    check(count >= 0 && count <= 8192);
    out("{\"taunter_ref_words\":"); words(&g_erTaunter, sizeof(g_erTaunter));
    out(",\"placator_ref_words\":[");
    for (i = 0; i < count; ++i) {
        if (i) out(",");
        if (g_pperPlacators[i]) words(g_pperPlacators[i], sizeof(*g_pperPlacators[i]));
        else out("null");
    }
    out("],\"selected_dbid\":%d,\"selected_handle\":", gSelectedDBID);
    fixed_string(gSelectedHandle, sizeof(gSelectedHandle));
    out(",\"current_target\":");
    if (!current_target) out("null");
    else out("{\"svr_idx\":%d,\"id\":%u,\"db_id\":%d}",
        current_target->svr_idx, current_target->id, current_target->db_id);
    out("}");
}

static void entity_status_state(const Entity *e)
{
    int i, count;
    out("{\"effects\":%u,\"translucency_f32_bits\":", (unsigned)e->ulStatusEffects);
    words(&e->xlucency, sizeof(e->xlucency));
    out(",\"logout_bad_connection\":%u,\"afk\":", (unsigned)e->logout_bad_connection);
    if (e->pl) {
        out("{\"enabled\":%u,\"message\":", (unsigned)e->pl->afk);
        fixed_string(e->pl->afk_string, sizeof(e->pl->afk_string)); out("}");
    } else out("null");
    out(",\"designer_statuses\":");
    if (!e->pchar) out("null");
    else {
        count = eaSize(&e->pchar->designerStatuses);
        check(count >= 0 && count <= 8192);
        out("[");
        for (i = 0; i < count; ++i) {
            if (i) out(",");
            string(e->pchar->designerStatuses[i]);
        }
        out("]");
    }
    out("}");
}
static void initial_ui_state(void)
{
    int i;
    out("{\"team_buffs\":%d,\"inspiration_mode\":%d,\"dividers\":[%d,%d,%d,%d,%d,%d,%d,%d],\"window_rgba\":[",
        armportReplayTeamBuffMode(), armportReplayInspirationMode(),
        gDivSuperName, gDivSuperMap, gDivSuperTitle, gDivEmailFrom,
        gDivEmailSubject, gDivFriendName, gDivLfgName, gDivLfgMap);
    for (i = 0; i < 4; ++i) out("%s%d", i ? "," : "", gWindowRGBA[i]);
    out("],\"windows\":[");
    for (i = 0; i < MAX_WINDOW_COUNT; ++i) {
        const Wdw *window = &winDefs[i];
        const WdwBase *loc = &window->loc;
        out("%s{\"index\":%d,\"x\":%d,\"y\":%d,\"width\":%d,\"height\":%d,\"draggable\":%d,\"locked\":%d,\"start_shrunk\":%d,\"color\":%u,\"back_color\":%u,\"scale_f32_bits\":",
            i ? "," : "", i, loc->xp, loc->yp, loc->wd, loc->ht,
            loc->draggable_frame, loc->locked, loc->start_shrunk,
            (unsigned)loc->color, (unsigned)loc->back_color);
        words(&loc->sc, sizeof(loc->sc));
        out(",\"maximized\":%d,\"mode\":%d,\"below\":%d}",
            loc->maximized, (int)loc->mode, window->below);
    }
    out("]}");
}
static void door_transition_state(void)
{
    int waiting, loading, animfadeout;
    armportReplayDoorState(&waiting, &loading, &animfadeout);
    out("{\"waiting\":%d,\"loading\":%d,\"anim_fadeout\":%d,\"game_mode\":%d}",
        waiting, loading, animfadeout, game_state.game_mode);
}
static void door_animation_state(const DoorAnimState *door)
{
    if (!door) { out("null"); return; }
    out("{\"state\":%d,\"entry_f32_bits\":", (int)door->state);
    words(door->entrypos, sizeof(door->entrypos));
    out(",\"target_f32_bits\":"); words(door->targetpos, sizeof(door->targetpos));
    out(",\"entry_radius\":%d,\"client_ack\":%d,\"past_threshold\":%d,\"animation\":",
        door->entryPointRadius, door->clientack, door->pastthreshold);
    string(door->animation); out("}");
}
static void initial_server_state(void)
{
    out("{\"boost_diminishing\":%d,\"power_diminishing\":%d,\"no_base_edit\":%d,\"beta_base\":%d,\"base_raid\":%d,\"first_person\":%d,\"nocoll\":%d}",
        game_state.enableBoostDiminishing, game_state.enablePowerDiminishing,
        game_state.no_base_edit, game_state.beta_base, game_state.base_raid,
        control_state.first, control_state.nocoll);
}

static void options_receive_state(void)
{
    int i, count = -1;
    const UserOption *options = armportReplayOptions(&count);
    check(count >= 0 && count <= 8192 && (!count || options));
    out("[");
    for (i = 0; i < count; ++i) {
        const UserOption *option = &options[i];
        out("%s{\"id\":%d,\"bit_size\":%d,", i ? "," : "", option->id, option->bitSize);
        if (option->bitSize < 0) {
            out("\"value_f32_bits\":"); words(&option->fVal, sizeof(option->fVal));
        } else out("\"value_u32\":%u", (unsigned)option->iVal);
        out("}");
    }
    out("]");
}

static void friends_receive_state(const Entity *e)
{
    int i;
    check(e->friendCount >= 0 && e->friendCount <= MAX_FRIENDS);
    check(!e->friendCount || e->friends != NULL);
    out("[");
    for (i = 0; i < e->friendCount; ++i) {
        const Friend *f = &e->friends[i];
        out("%s{\"db_id\":%d,\"online\":%d,\"map_id\":%d,\"name\":", i ? "," : "", f->dbid, f->online, f->map_id);
        string(f->name); out(",\"map_name\":"); string(f->mapname);
        out(",\"class\":"); string(f->arch); out(",\"origin\":"); string(f->origin);
        out("}");
    }
    out("]");
}
static void player_keybind_state(const EntPlayer *p)
{
    int i;
    out("{\"profile\":"); fixed_string(p->keyProfile, sizeof(p->keyProfile));
    out(",\"bindings\":");
    if (!p->keybinds) out("null");
    else {
        out("[");
        for (i = 0; i < BIND_MAX; ++i) {
            const KeyBind *b = &p->keybinds[i];
            out("%s{\"key\":%d,\"modifier\":%d,\"secondary\":%d,\"command\":", i ? "," : "", b->key, b->modifier, b->secondary);
            string(b->command[0]); out("}");
        }
        out("]");
    }
    out("}");
}
static void player_chat_state(const EntPlayer *p)
{
    const ChatSettings *s = &p->chat_settings;
    int i;
    out("{\"help_added\":%d,\"send_channel\":%d,\"user_send_channel\":%d,\"options\":%u,\"minimized\":%d,\"windows\":[",
        p->helpChatAdded, p->chatSendChannel, s->userSendChannel, (unsigned)s->options, s->primaryChatMinimized);
    for (i = 0; i < MAX_CHAT_WINDOWS; ++i) {
        const ChatWindowSettings *w = &s->windows[i];
        out("%s{\"tabs\":%u,\"selected_top\":%d,\"selected_bottom\":%d,\"divider_f32_bits\":", i ? "," : "", (unsigned)w->tabListBF, w->selectedtop, w->selectedbot);
        words(&w->divider, sizeof(w->divider)); out("}");
    }
    out("],\"tabs\":[");
    for (i = 0; i < MAX_CHAT_TABS; ++i) {
        const ChatTabSettings *t = &s->tabs[i];
        if (i) out(",");
        out("{\"name\":"); fixed_string(t->name, sizeof(t->name));
        out(",\"system_channels\":"); words(t->systemChannels, sizeof(t->systemChannels));
        out(",\"user_channels\":%u,\"options\":%u,\"default_channel\":%d,\"default_type\":%d}",
            (unsigned)t->userBF, (unsigned)t->optionsBF, t->defaultChannel, t->defaultType);
    }
    out("],\"channels\":[");
    for (i = 0; i < MAX_CHAT_CHANNELS; ++i) {
        const ChatChannelSettings *c = &s->channels[i];
        if (i) out(",");
        out("{\"name\":"); fixed_string(c->name, sizeof(c->name));
        out(",\"options\":%u,\"color1\":%u,\"color2\":%u}", (unsigned)c->optionsBF, (unsigned)c->color1, (unsigned)c->color2);
    }
    out("]}");
}

static void turnstile_mission_state(const TurnstileMissionClient *m)
{
    if (!m) { out("null"); return; }
    out("{\"name\":"); string(m->name);
    out(",\"average_wait_f32_bits\":"); words(&m->avgWait, sizeof(m->avgWait));
    out(",\"weekly\":%d,\"selected\":%d,\"index\":%d,\"category\":%d,\"eligible\":%d}",
        m->isWeeklyTF, m->selected, m->index, (int)m->category, m->eligible);
}
static void turnstile_receive_state(void)
{
    const TurnstileMissionClient *const *missions = armportReplayTurnstileMissions();
    const float *wait = armportReplayTurnstileWait();
    int i, count = eaSize(&missions);
    check(count >= 0 && count <= 8192 && wait != NULL);
    out("{\"in_queue\":%d,\"current_wait_f32_bits\":", armportReplayTurnstileQueue());
    words(wait, sizeof(*wait));
    out(",\"missions\":[");
    for (i = 0; i < count; ++i) {
        if (i) out(",");
        turnstile_mission_state(missions[i]);
    }
    out("],\"all_dummy\":"); turnstile_mission_state(armportReplayTurnstileDummy(-1));
    out(",\"category_dummies\":[");
    for (i = 0; i < kTurnstileCategory_Count; ++i) {
        if (i) out(",");
        turnstile_mission_state(armportReplayTurnstileDummy(i));
    }
    out("]}");
}
static void player_turnstile_state(const EntPlayer *p)
{
    out("{\"last_event_id\":%d,\"last_mission_id\":%d}",
        p->lastTurnstileEventID, p->lastTurnstileMissionID);
}

typedef struct ArmPortWaypointEntry {
    const char *key;
    const Destination *destination;
} ArmPortWaypointEntry;
static int waypoint_entry_compare(const void *left, const void *right)
{
    const ArmPortWaypointEntry *a = left, *b = right;
    return strcmp(a->key, b->key);
}
static void server_waypoint_state(void)
{
    unsigned count, used_entries = 0, i;
    ArmPortWaypointEntry *entries;
    cStashTableIterator iterator;
    cStashElement element;
    if (!serverDestList) { out("[]"); return; }
    count = stashGetValidElementCount(serverDestList);
    check(count <= 8192);
    entries = malloc((count ? count : 1) * sizeof(*entries));
    check(entries != NULL);
    stashGetIteratorConst(serverDestList, &iterator);
    while (stashGetNextElementConst(&iterator, &element)) {
        check(used_entries < count);
        entries[used_entries].key = stashElementGetStringKey(element);
        check(entries[used_entries].key != NULL);
        entries[used_entries++].destination = stashElementGetPointerConst(element);
    }
    check(used_entries == count);
    /* Stash bucket order is allocation-dependent; retain the literal key/value map. */
    qsort(entries, count, sizeof(*entries), waypoint_entry_compare);
    out("[");
    for (i = 0; i < count; ++i) {
        const Destination *d = entries[i].destination;
        if (i) { check(strcmp(entries[i-1].key, entries[i].key) < 0); out(","); }
        out("{\"key\":"); string(entries[i].key);
        out(",\"destination\":");
        if (!d) out("null");
        else {
            out("{\"nav_on\":%d,\"type\":%d,\"id\":%d,\"pulse\":%u,\"name\":",
                d->navOn, d->type, d->id, (unsigned)d->pulseBIcon);
            fixed_string(d->name, sizeof(d->name));
            out(",\"map\":"); fixed_string(d->mapName, sizeof(d->mapName));
            out(",\"angle_f32_bits\":"); words(&d->angle, sizeof(d->angle));
            out(",\"position_f32_bits\":"); words(d->world_location[3], sizeof(d->world_location[3]));
            out(",\"icon_name\":"); string(d->icon ? d->icon->name : NULL);
            out(",\"background_icon_name\":"); string(d->iconB ? d->iconB->name : NULL);
            out("}");
        }
        out("}");
    }
    out("]");
    free(entries);
}

void armportReplayDesaturation(const float *delay, const float *weight, const float *target, const float *fade)
{
    if (!active) return;
    check(sizeof(*delay) == sizeof(desaturation.bits[0]));
    memcpy(&desaturation.bits[0], delay, sizeof(*delay));
    memcpy(&desaturation.bits[1], weight, sizeof(*weight));
    memcpy(&desaturation.bits[2], target, sizeof(*target));
    memcpy(&desaturation.bits[3], fade, sizeof(*fade));
    desaturation.valid = 1;
}
static void desaturation_receive_state(void)
{
    if (!desaturation.valid) { out("null"); return; }
    words(desaturation.bits, sizeof(desaturation.bits));
}

static void karma_receive_state(void)
{
    int i, j, count = eaSize(&scriptUIKarmaWidgetList);
    check(count >= 0 && count <= 8192);
    out("[");
    for (i = 0; i < count; ++i) {
        const ScriptUIClientWidget *widget = scriptUIKarmaWidgetList[i];
        int variables;
        if (i) out(",");
        if (!widget) { out("null"); continue; }
        variables = eaSize(&widget->varList);
        check(variables >= 0 && variables <= 8192);
        out("{\"type\":%d,\"id\":%u,\"variables\":[", (int)widget->type, widget->uniqueID);
        for (j = 0; j < variables; ++j) {
            if (j) out(",");
            string(widget->varList[j]);
        }
        out("]}");
    }
    out("]");
}

static void power_customization_list(const PowerCustomizationList *list)
{
    int i, count;
    if (!list) { out("null"); return; }
    count = eaSize(&list->powerCustomizations);
    check(count >= 0 && count <= 8192);
    out("[");
    for (i = 0; i < count; ++i) {
        const PowerCustomization *item = list->powerCustomizations[i];
        if (i) out(",");
        if (!item) { out("null"); continue; }
        out("{\"full_name\":"); string(item->powerFullName);
        out(",\"power\":"); base_power(item->power);
        out(",\"primary_rgba_u32\":%u,\"secondary_rgba_u32\":%u,\"token\":",
            item->customTint.primary.integer, item->customTint.secondary.integer);
        string(item->token); out("}");
    }
    out("]");
}
static void entity_power_customizations(const Entity *e)
{
    int i;
    out("{\"active\":"); power_customization_list(e->powerCust);
    out(",\"owned\":"); power_customization_list(e->ownedPowerCustomizationList);
    out(",\"player\":");
    if (!e->pl) out("null");
    else {
        out("{\"current\":%d,\"slots\":[", e->pl->current_powerCust);
        for (i = 0; i < MAX_COSTUMES; ++i) {
            if (i) out(",");
            power_customization_list(e->pl->powerCustomizationLists[i]);
        }
        out("]}");
    }
    out("}");
}


/* Fixed retained player destinations in receiveCharacterFromServer and
 * receiveFullPopHelp. These are account/game flags, not authentication keys.
 * Chat/window/keybind/options receivers still need separate coverage. */
static void player_receive_core(const EntPlayer *p)
{
    out("{\"player_type\":%d,\"player_subtype\":%d,\"praetorian_progress\":%d,\"hidden\":%d,\"skills_unlocked\":%d,\"new_features_u32\":%u,\"primary_set\":",
        p->playerType, p->playerSubType, p->praetorianProgress, p->hidden,
        p->skillsUnlocked, (unsigned)p->newFeaturesVersion);
    fixed_string(p->primarySet, sizeof(p->primarySet));
    out(",\"secondary_set\":"); fixed_string(p->secondarySet, sizeof(p->secondarySet));
    out(",\"comment\":"); fixed_string(p->comment, sizeof(p->comment));
    out(",\"account_game_flags_u32\":"); words(p->auth_user_data, sizeof(p->auth_user_data));
    out(",\"pop_help_status_u32\":"); words(p->popHelpStatus, sizeof(p->popHelpStatus));
    out(",\"pop_help_latest_u32\":"); words(p->popHelpLatest, sizeof(p->popHelpLatest));
    out("}");
}

/* INITIAL overwrites token timers with received values, but receiveRewardToken
 * calls rewardtoken_Award without overwriting its local-clock timer. Exclude
 * this mixed-provenance field until a separate wire observer is qualified.
 * No reward helper is called by this read-only writer. */
static void player_reward_tokens(RewardToken *const *items)
{
    int i, count = eaSize(&items);
    check(count >= 0 && count <= 8192);
    out("[");
    for (i = 0; i < count; ++i) {
        const RewardToken *token = items[i];
        if (i) out(",");
        if (!token) { out("null"); continue; }
        out("{\"name\":"); string(token->reward);
        out(",\"value\":%d}", token->val);
    }
    out("]");
}
static void player_identity_state(const EntPlayer *p)
{
    int i;
    out("{\"title_the\":%d,\"title_the_text\":", p->titleThe);
    fixed_string(p->titleTheText, sizeof(p->titleTheText));
    out(",\"title_common\":"); fixed_string(p->titleCommon, sizeof(p->titleCommon));
    out(",\"title_origin\":"); fixed_string(p->titleOrigin, sizeof(p->titleOrigin));
    out(",\"title_special\":"); fixed_string(p->titleSpecial, sizeof(p->titleSpecial));
    out(",\"title_colors_u32\":[%u,%u],\"title_badge_u32\":%u,\"workshop\":",
        (unsigned)p->titleColors[0], (unsigned)p->titleColors[1], (unsigned)p->titleBadge);
    fixed_string(p->workshopInteracting, sizeof(p->workshopInteracting));
    out(",\"reward_tokens\":"); player_reward_tokens(p->rewardTokens);
    out(",\"active_player_reward_tokens\":"); player_reward_tokens(p->activePlayerRewardTokens);
    out(",\"pvp_switch\":%d,\"is_ganker\":%d,\"combat_monitor\":[", p->pvpSwitch, p->bIsGanker);
    for (i = 0; i < MAX_COMBAT_STATS; ++i)
        out("%s{\"key\":%d,\"order\":%d}", i ? "," : "", p->combatMonitorStats[i].iKey, p->combatMonitorStats[i].iOrder);
    out("]");
    out("}");
}
static void entity_strings(const EntStrings *s)
{
    if (!s) { out("null"); return; }
    /* Retained strings after original bounded copy/HTML handling; no
     * localized title/menu lookup or transformation is performed here. */
    out("{\"description\":"); fixed_string(s->playerDescription, sizeof(s->playerDescription));
    out(",\"motto\":"); fixed_string(s->motto, sizeof(s->motto)); out("}");
}

/* Retained destinations of character_Receive, SendLevels and ally/PvP
 * receives. Definition identity uses logical names, never addresses. */
static void character_receive_core(const Character *p)
{
    out("{\"class\":"); string(p->pclass ? p->pclass->pchName : NULL);
    out(",\"origin\":"); string(p->porigin ? p->porigin->pchName : NULL);
    out(",\"combat_level\":%d,\"combat_mod_shift\":%d,\"player_type_by_location\":%d,"
        "\"ally_id\":%d,\"gang_id\":%d,\"pvp_active\":%d}", p->iCombatLevel, p->iCombatModShift,
        p->playerTypeByLocation, p->iAllyID, p->iGangID, p->bPvPActive);
}

/* Individual retained scalar/string destinations. No bitfield storage,
 * local PvP update clock, entity-reference pointers or new packet-ID fields. */
static void entity_receive_metadata(const Entity *e)
{
    out("{\"mode_u32\":%u,\"vision_phases_u32\":%u,\"exclusive_vision_phase\":%d,\"con_yellow\":%d,"
        "\"pvp_received_seconds\":%d,\"taskforce_id\":%d,\"on_flashback\":%d,"
        "\"npc_index\":%d,\"gender\":%d,\"name_gender\":%d,\"world_group\":",
        (unsigned)e->state.mode, (unsigned)e->bitfieldVisionPhases, e->exclusiveVisionPhase, e->shouldIConYellow,
        e->pvpClientZoneTimer, e->taskforce_id, e->onFlashback, e->npcIndex, e->gender, e->name_gender);
    string(e->costumeWorldGroup);
    out(",\"ai_anim_list\":"); string(e->aiAnimList);
    out(",\"no_draw\":%u,\"show_on_map\":%u,\"not_selectable\":%u,\"contact_or_pnpc\":%u,"
        "\"contact_architect\":%u,\"always_con\":%u,\"see_through_walls\":%u,"
        "\"commandable_pet\":%u,\"pet_dismissable\":%u,\"pet_visibility\":%d,\"pet_name\":",
        (unsigned)e->noDrawOnClient, (unsigned)e->showOnMap, (unsigned)e->notSelectable,
        (unsigned)e->contactOrPnpc, (unsigned)e->contactArchitect, (unsigned)e->alwaysCon,
        (unsigned)e->seeThroughWalls, (unsigned)e->commandablePet, (unsigned)e->petDismissable, e->petVisibility);
    string(e->petName);
    out(",\"special_power_display_name\":"); string(e->specialPowerDisplayName);
    out(",\"special_power_state\":%d}", e->specialPowerState);
}

/* Original static-map receive storage, in its retained owner/map order. The
 * accessor never invokes the ordinary lazy file-loading/creating getter.
 * Local visited-map files can also populate this storage; their retained data
 * is compared literally. Derived minimap textures/fog grids are not included. */
static void visited_map_state(void)
{
    const VisitedStaticMap *const *owners = armportReplayVisitedMaps();
    int i, j, count = eaSize(&owners);
    check(count >= 0 && count <= 8192);
    out("[");
    for (i = 0; i < count; ++i) {
        const VisitedStaticMap *owner = owners[i];
        int maps;
        if (i) out(",");
        if (!owner) { out("null"); continue; }
        out("{\"db_id\":%d,\"maps\":[", owner->db_id);
        maps = eaSize(&owner->staticMaps);
        check(maps >= 0 && maps <= 8192);
        for (j = 0; j < maps; ++j) {
            const VisitedMap *map = owner->staticMaps[j];
            if (j) out(",");
            if (!map) { out("null"); continue; }
            out("{\"db_id\":%d,\"map_id\":%d,\"opaque_fog\":%d,\"cells_u32\":",
                map->db_id, map->map_id, map->opaque_fog);
            words(map->cells, sizeof(map->cells)); out("}");
        }
        out("]}");
    }
    out("]");
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
        fixed_string(e->name, sizeof(e->name));
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
            out(",\"receive_core\":"); character_receive_core(p);
            out(",\"default_power\":"); default_power_state(p->ppowDefault);
            out(",\"target_state\":"); character_target_state(p);
            out("}");
        } else out("null");
        out(",\"player\":");
        if (e->pl) {
            out("{\"lastClientStatePktId\":%u,\"badges\":", e->pl->lastClientStatePktId);
            player_badges(e->pl);
            out(",\"costumes\":"); player_costumes(e->pl);
            out(",\"receive_core\":"); player_receive_core(e->pl);
            out(",\"identity_state\":"); player_identity_state(e->pl);
            out(",\"turnstile_state\":"); player_turnstile_state(e->pl);
            out(",\"keybind_state\":"); player_keybind_state(e->pl);
            out(",\"chat_state\":"); player_chat_state(e->pl);
            out(",\"tray_state\":"); player_tray_state(e->pl->tray);
            out(",\"door_animation\":"); door_animation_state(e->pl->door_anim);
            out(",\"taskforce_mode\":%d,\"lfg\":%d}", e->pl->taskforce_mode, e->pl->lfg);
        } else out("null");
        out(",\"groups\":"); entity_groups(e);
        out(",\"leveling_pact\":"); leveling_pact_state(e);
        out(",\"supergroup\":"); entity_supergroup_state(e);
        out(",\"power_customizations\":"); entity_power_customizations(e);
        out(",\"strings\":"); entity_strings(e->strings);
        out(",\"receive_metadata\":"); entity_receive_metadata(e);
        out(",\"status_state\":"); entity_status_state(e);
        out(",\"packet_order\":"); entity_packet_order_state(e);
        out(",\"attribute_packet_order\":"); entity_attribute_packet_order_state(e);
        out(",\"pet_ownership\":"); entity_pet_owner_state(e);
        out(",\"sequence_receive\":"); entity_sequence_receive_state(e);
        out(",\"netfx_receive\":"); entity_netfx_receive_state(e);
        out(",\"buffs\":"); entity_buff_state(e);
        out(",\"friends\":"); friends_receive_state(e);
        out("}");
    }
    out("],\"delete_history\":["); deletes = 0; armportReplayDeletes(deletion);
    out("],\"badge_client\":"); badge_client_state();
    out(",\"group_map_names\":"); group_map_names();
    out(",\"world\":"); world_receive_state();
    out(",\"story\":"); story_receive_state();
    out(",\"visited_maps\":"); visited_map_state();
    out(",\"karma_widgets\":"); karma_receive_state();
    out(",\"desaturation_received_f32_bits\":"); desaturation_receive_state();
    out(",\"server_waypoints\":"); server_waypoint_state();
    out(",\"turnstile\":"); turnstile_receive_state();
    out(",\"user_options\":"); options_receive_state();
    out(",\"tray_sticky_mask\":%d", armportReplayTrayStickyMask());
    out(",\"initial_ui\":"); initial_ui_state();
    out(",\"initial_server_state\":"); initial_server_state();
    out(",\"door_transition\":"); door_transition_state();
    out(",\"target_state\":"); target_receive_state();
    out(",\"task_sets\":"); task_sets();
    out(",\"contacts\":"); contact_receive_state(); out("}\n");
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
