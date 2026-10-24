/* Deterministic, explicitly partial receiver-state observations. No pointers,
 * padding, clocks, interpolation or normalized rendering quaternions are hashed.
 * Power/inventory/team/task/UI-tail coverage still needs implementation/review.
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
