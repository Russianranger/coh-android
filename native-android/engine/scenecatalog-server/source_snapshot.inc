/* NONSHIPPING source snapshot, appended after unchanged sendDef/sendMat4 and
 * source_export.inc. The caller owns a stable, exclusive group_info snapshot
 * for the complete catalog + sidecar pair. Callbacks may only copy/write bytes;
 * they must never yield into the engine, mutate objects or invoke lazy loaders.
 * This is not a network transaction, actor identity or render authorization.
 */
#ifndef COH_SOURCE_RUNTIME_SNAPSHOT_INCLUDED
#define COH_SOURCE_RUNTIME_SNAPSHOT_INCLUDED

#include <string.h>
#if defined(SERVER)
#include "group/groupfilelib.h"
/* Defined by the unchanged Common/group/group.c, absent from group.h. */
extern GroupInfo *group_ptr;
#endif

#define COH_SNAPSHOT_MAX_BYTES (16u * 1024u * 1024u)
#define COH_SNAPSHOT_MAX_EXTERNAL 64u
#define COH_SNAPSHOT_HEADER_BYTES 80u
#define COH_SNAPSHOT_BOUNDS_BYTES 60u
#define COH_SNAPSHOT_NO_INDEX 0xffffffffu

typedef struct CohSourceSnapshotReport
{
    unsigned int status, total_bytes, emitted_bytes;
    unsigned int root_slots, active_roots, external_count, external_children;
    unsigned int defs_crc, refs_crc;
} CohSourceSnapshotReport;

typedef struct CohSnapshotState
{
    GroupDef *external[COH_SNAPSHOT_MAX_EXTERNAL];
    unsigned int external_count, external_children;
    unsigned int files, slots, definitions, children, roots;
    unsigned int total, emitted, pass;
    CohSourceCatalogOutputFn output;
    void *context;
} CohSnapshotState;

static unsigned int coh_snapshot_u32(const unsigned char *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8) |
        ((unsigned int)p[2] << 16) | ((unsigned int)p[3] << 24);
}

static void coh_snapshot_float(unsigned char *out, const F32 *value)
{
    unsigned int bits;
    typedef char CohSnapshotFloatSize[sizeof(F32) == 4 ? 1 : -1];
    (void)sizeof(CohSnapshotFloatSize);
    memcpy(&bits, value, 4);
    coh_source_catalog_put_u32(out, bits);
}

static int coh_snapshot_finite(const unsigned char *raw, unsigned int floats)
{
    unsigned int i;
    for (i = 0; i < floats; ++i)
        if ((coh_snapshot_u32(raw + i * 4u) & 0x7f800000u) == 0x7f800000u)
            return 0;
    return 1;
}

/* Explicit named fields: never serialize native bitfield layout/padding. */
static void coh_snapshot_bounds(unsigned char out[COH_SNAPSHOT_BOUNDS_BYTES],
    const GroupDef *d)
{
    unsigned int i, flags = 0;
    for (i = 0; i < 3u; ++i)
    {
        coh_snapshot_float(out + i * 4u, &d->min[i]);
        coh_snapshot_float(out + 12u + i * 4u, &d->max[i]);
        coh_snapshot_float(out + 24u + i * 4u, &d->mid[i]);
    }
    coh_snapshot_float(out + 36, &d->vis_dist);
    coh_snapshot_float(out + 40, &d->radius);
    coh_snapshot_float(out + 44, &d->lod_scale);
    coh_snapshot_float(out + 48, &d->shadow_dist);
    coh_source_catalog_put_u32(out + 52, (unsigned int)d->recursive_count);
#define COH_SNAPSHOT_FLAG(n, bit) flags |= (d->n ? 1u : 0u) << bit
    COH_SNAPSHOT_FLAG(breakable, 0); COH_SNAPSHOT_FLAG(child_breakable, 1);
    COH_SNAPSHOT_FLAG(is_tray, 2); COH_SNAPSHOT_FLAG(child_tray, 3);
    COH_SNAPSHOT_FLAG(has_ambient, 4); COH_SNAPSHOT_FLAG(child_ambient, 5);
    COH_SNAPSHOT_FLAG(has_light, 6); COH_SNAPSHOT_FLAG(child_light, 7);
    COH_SNAPSHOT_FLAG(has_cubemap, 8); COH_SNAPSHOT_FLAG(child_cubemap, 9);
    COH_SNAPSHOT_FLAG(has_fog, 10); COH_SNAPSHOT_FLAG(child_has_fog, 11);
    COH_SNAPSHOT_FLAG(has_volume, 12); COH_SNAPSHOT_FLAG(child_volume, 13);
    COH_SNAPSHOT_FLAG(has_beacon, 14); COH_SNAPSHOT_FLAG(child_beacon, 15);
    COH_SNAPSHOT_FLAG(open_tracker, 16); COH_SNAPSHOT_FLAG(has_properties, 17);
    COH_SNAPSHOT_FLAG(child_properties, 18); COH_SNAPSHOT_FLAG(no_fog_clip, 19);
    COH_SNAPSHOT_FLAG(child_no_fog_clip, 20); COH_SNAPSHOT_FLAG(is_autogroup, 21);
    COH_SNAPSHOT_FLAG(child_volume_trigger, 22); COH_SNAPSHOT_FLAG(no_coll, 23);
    COH_SNAPSHOT_FLAG(do_welding, 24); COH_SNAPSHOT_FLAG(editor_visible_only, 25);
#undef COH_SNAPSHOT_FLAG
    coh_source_catalog_put_u32(out + 56, flags);
}

static int coh_snapshot_emit(CohSnapshotState *s, const unsigned char *p,
    unsigned int n)
{
    if (n > COH_SNAPSHOT_MAX_BYTES - s->emitted)
        return COH_SOURCE_CATALOG_LIMIT;
    if (s->pass && s->output(s->context, p, n) != 1)
        return COH_SOURCE_CATALOG_OUTPUT;
    s->emitted += n;
    return COH_SOURCE_CATALOG_OK;
}

/* Pointer incidence supplies external identity. Numeric pre_alloc IDs are
 * deliberately NOT unique and its defs/count do not enumerate future objects. */
static int coh_snapshot_identity(CohSnapshotState *s, GroupDef *d,
    unsigned int *kind, unsigned int *file, unsigned int *slot)
{
    unsigned int f, i;
    if (!d || d->in_use != 1 || d->id < 0 || !d->file ||
        !coh_source_catalog_name_bytes(d->name) || groupDefFind(d->name) != d)
        return COH_SOURCE_CATALOG_SOURCE;
    for (f = 0; f < s->files; ++f)
    {
        if (d->file != group_info.files[f])
            continue;
        if (d->pre_alloc || d->file->pre_alloc ||
            (unsigned int)d->id >= (unsigned int)d->file->count ||
            d->file->defs[d->id] != d)
            return COH_SOURCE_CATALOG_SOURCE;
        *kind = 1u; *file = f; *slot = (unsigned int)d->id;
        return COH_SOURCE_CATALOG_OK;
    }
    if (!group_info.pre_alloc || d->file != group_info.pre_alloc ||
        !d->pre_alloc || !d->file->pre_alloc)
        return COH_SOURCE_CATALOG_SOURCE;
    for (i = 0; i < s->external_count; ++i)
    {
        if (s->external[i] == d)
            break;
        if (coh_source_catalog_same_name(s->external[i]->name, d->name))
            return COH_SOURCE_CATALOG_SOURCE;
    }
    if (i == s->external_count)
    {
        if (s->pass || i == COH_SNAPSHOT_MAX_EXTERNAL)
            return s->pass ? COH_SOURCE_CATALOG_CHANGED : COH_SOURCE_CATALOG_LIMIT;
        s->external[s->external_count++] = d;
    }
    *kind = 2u; *file = COH_SNAPSHOT_NO_INDEX; *slot = i;
    return COH_SOURCE_CATALOG_OK;
}

static int coh_snapshot_children(CohSnapshotState *s, GroupDef *d,
    unsigned int *count)
{
    unsigned int i, j, kind, file, slot;
    unsigned char matrix[48];
    int status;
    if (d->count < 0 || (d->count && !d->entries) ||
        (unsigned int)d->count > COH_SOURCE_CATALOG_MAX_CHILDREN - *count)
        return COH_SOURCE_CATALOG_LIMIT;
    *count += (unsigned int)d->count;
    for (i = 0; i < (unsigned int)d->count; ++i)
    {
        if (!d->entries[i].mat) return COH_SOURCE_CATALOG_SOURCE;
        for (j = 0; j < 12u; ++j)
            coh_snapshot_float(matrix + j * 4u, &d->entries[i].mat[j / 3u][j % 3u]);
        if (!coh_snapshot_finite(matrix, 12u)) return COH_SOURCE_CATALOG_SOURCE;
        status = coh_snapshot_identity(s, d->entries[i].def, &kind, &file, &slot);
        if (status)
            return status;
    }
    return COH_SOURCE_CATALOG_OK;
}

static int coh_snapshot_inventory(CohSnapshotState *s)
{
    unsigned int f, i, kind, file, slot, slots = 0, defs = 0, children = 0;
    unsigned int external_children = 0;
    GroupFile *g;
    GroupDef *d;
    int status;
    if (group_ptr != &group_info || group_info.file_count < 0 ||
        (unsigned int)group_info.file_count != s->files ||
        (s->files && !group_info.files) || group_info.ref_count < 0 ||
        (unsigned int)group_info.ref_count != s->roots ||
        (s->roots && !group_info.refs))
        return COH_SOURCE_CATALOG_CHANGED;
    for (f = 0; f < s->files; ++f)
    {
        g = group_info.files[f];
        if (!g || g->pre_alloc || g->count < 0 || (g->count && !g->defs) ||
            (unsigned int)g->count > COH_SOURCE_CATALOG_MAX_SLOTS - slots)
            return COH_SOURCE_CATALOG_SOURCE;
        slots += (unsigned int)g->count;
        for (i = 0; i < (unsigned int)g->count; ++i)
        {
            d = g->defs[i];
            if (!d)
                continue;
            if (d->id != (int)i || d->file != g || d->pre_alloc || d->in_use > 1)
                return COH_SOURCE_CATALOG_SOURCE;
            ++defs;
            if (!d->in_use)
                continue;
            status = coh_snapshot_identity(s, d, &kind, &file, &slot);
            if (!status)
                status = coh_snapshot_children(s, d, &children);
            if (status)
                return status;
        }
    }
    for (i = 0; i < s->roots; ++i)
    {
        if (!group_info.refs[i])
            return COH_SOURCE_CATALOG_SOURCE;
        d = group_info.refs[i]->def;
        if (!d)
            continue;
        status = coh_snapshot_identity(s, d, &kind, &file, &slot);
        if (status)
            return status;
    }
    /* The bound grows as newly reached external children are discovered. */
    for (i = 0; i < s->external_count; ++i)
    {
        status = coh_snapshot_children(s, s->external[i], &external_children);
        if (status)
            return status;
    }
    if (external_children > COH_SOURCE_CATALOG_MAX_CHILDREN - children)
        return COH_SOURCE_CATALOG_LIMIT;
    if (slots != s->slots || defs != s->definitions || children != s->children)
        return COH_SOURCE_CATALOG_CHANGED;
    s->external_children = external_children;
    return COH_SOURCE_CATALOG_OK;
}

static int coh_snapshot_roots(CohSnapshotState *s)
{
    unsigned int i, j, kind, file, slot, bits, bytes, name;
    unsigned char head[32], raw[48];
    GroupDef *d;
    Packet *pak;
    int status;
    for (i = 0; i < s->roots; ++i)
    {
        memset(head, 0, sizeof(head));
        coh_source_catalog_put_u32(head, i);
        coh_source_catalog_put_u32(head + 12, COH_SNAPSHOT_NO_INDEX);
        coh_source_catalog_put_u32(head + 16, COH_SNAPSHOT_NO_INDEX);
        d = group_info.refs[i]->def;
        if (!d)
        {
            status = coh_snapshot_emit(s, head, sizeof(head));
            if (status) return status;
            continue;
        }
        status = coh_snapshot_identity(s, d, &kind, &file, &slot);
        if (status) return status;
        name = coh_source_catalog_name_bytes(d->name);
        for (j = 0; j < 12u; ++j)
            coh_snapshot_float(raw + j * 4u, &group_info.refs[i]->mat[j / 3u][j % 3u]);
        if (!coh_snapshot_finite(raw, 12u)) return COH_SOURCE_CATALOG_SOURCE;
        pak = pktCreate();
        if (!pak) return COH_SOURCE_CATALOG_PACKET;
        pak->hasDebugInfo = 0;
        pktSetCompression(pak, 1);
        sendMat4(pak, group_info.refs[i]->mat);
        bits = pak->stream.bitLength; bytes = bits / 8u;
        if (pak->stream.errorFlags || !pak->stream.data || !pak->stream.byteAlignedMode ||
            (bits & 7u) || bytes > 256u || !bytes)
        {
            pktFree(pak); return COH_SOURCE_CATALOG_PACKET;
        }
        coh_source_catalog_put_u32(head + 4, 1u);
        coh_source_catalog_put_u32(head + 8, kind);
        coh_source_catalog_put_u32(head + 12, file);
        coh_source_catalog_put_u32(head + 16, slot);
        coh_source_catalog_put_u32(head + 20, name);
        coh_source_catalog_put_u32(head + 24, bits);
        coh_source_catalog_put_u32(head + 28, bytes);
        status = coh_snapshot_emit(s, head, sizeof(head));
        if (!status) status = coh_snapshot_emit(s, (const unsigned char *)d->name, name);
        if (!status) status = coh_snapshot_emit(s, raw, sizeof(raw));
        if (!status) status = coh_snapshot_emit(s, pak->stream.data, bytes);
        pktFree(pak);
        if (status) return status;
    }
    return COH_SOURCE_CATALOG_OK;
}

static int coh_snapshot_external(CohSnapshotState *s)
{
    unsigned int i, kind, file, slot, bits, bytes, name, path_bytes;
    unsigned char head[36], bounds[2 * COH_SNAPSHOT_BOUNDS_BYTES];
    GroupDef *d, scratch;
    const char *path;
    Packet *pak;
    int status, found;
    for (i = 0; i < s->external_count; ++i)
    {
        d = s->external[i];
        status = coh_snapshot_identity(s, d, &kind, &file, &slot);
        if (status || kind != 2u || slot != i)
            return status ? status : COH_SOURCE_CATALOG_CHANGED;
        memset(&scratch, 0, sizeof(scratch));
        /* Original function copies into scratch only; never into the live d. */
        found = objectLibraryGetBounds(d->name, &scratch);
        if (found != 0 && found != 1) return COH_SOURCE_CATALOG_SOURCE;
        path = objectLibraryPathFromObj(d->name);
        path_bytes = path ? coh_source_catalog_name_bytes(path) : 0;
        if (path && !path_bytes) return COH_SOURCE_CATALOG_SOURCE;
        name = coh_source_catalog_name_bytes(d->name);
        coh_snapshot_bounds(bounds, d);
        coh_snapshot_bounds(bounds + COH_SNAPSHOT_BOUNDS_BYTES, &scratch);
        if (!coh_snapshot_finite(bounds, 13u) ||
            !coh_snapshot_finite(bounds + COH_SNAPSHOT_BOUNDS_BYTES, 13u)) return COH_SOURCE_CATALOG_SOURCE;
        pak = coh_source_catalog_record(d, &bits, &bytes);
        if (!pak) return COH_SOURCE_CATALOG_PACKET;
        if (bytes > COH_SOURCE_CATALOG_MAX_RECORD_BYTES)
        {
            pktFree(pak); return COH_SOURCE_CATALOG_LIMIT;
        }
        coh_source_catalog_put_u32(head, i);
        coh_source_catalog_put_u32(head + 4, (unsigned int)d->id);
        coh_source_catalog_put_u32(head + 8, 15u);
        coh_source_catalog_put_u32(head + 12, d->model ? 1u : 0u);
        coh_source_catalog_put_u32(head + 16, name);
        coh_source_catalog_put_u32(head + 20, bits);
        coh_source_catalog_put_u32(head + 24, bytes);
        coh_source_catalog_put_u32(head + 28, (unsigned int)found);
        coh_source_catalog_put_u32(head + 32, path_bytes);
        status = coh_snapshot_emit(s, head, sizeof(head));
        if (!status) status = coh_snapshot_emit(s, bounds, sizeof(bounds));
        if (!status) status = coh_snapshot_emit(s, (const unsigned char *)d->name, name);
        if (!status && path_bytes) status = coh_snapshot_emit(s, (const unsigned char *)path, path_bytes);
        if (!status) status = coh_snapshot_emit(s, pak->stream.data, bytes);
        pktFree(pak);
        if (status) return status;
    }
    return COH_SOURCE_CATALOG_OK;
}

/* catalog_header is the exact first48 bytes emitted by the immediately prior
 * successful unchanged catalog exporter. Its full bytes must subsequently
 * match the independently pinned retained SHA256 in the hosted wrapper. */
static int coh_source_runtime_snapshot_export(CohSourceCatalogOutputFn output,
    void *context, const unsigned char catalog_header[48],
    const CohSourceCatalogExportReport *catalog, CohSourceSnapshotReport *report)
{
    CohSnapshotState s;
    unsigned char header[COH_SNAPSHOT_HEADER_BYTES];
    unsigned int pass, defs_crc, refs_crc, active, original_external;
    int status = COH_SOURCE_CATALOG_ARGUMENT;
    if (!report) return COH_SOURCE_CATALOG_ARGUMENT;
    memset(report, 0, sizeof(*report));
    memset(&s, 0, sizeof(s));
    if (!output || !catalog_header || !catalog || catalog->status ||
        catalog->emitted_bytes != catalog->total_bytes ||
        memcmp(catalog_header, "COHCAT01", 8) ||
        coh_snapshot_u32(catalog_header + 8) != 1u ||
        coh_snapshot_u32(catalog_header + 12) != 48u ||
        coh_snapshot_u32(catalog_header + 16) != catalog->total_bytes ||
        !coh_snapshot_u32(catalog_header + 20) ||
        coh_snapshot_u32(catalog_header + 24) != catalog->files ||
        coh_snapshot_u32(catalog_header + 28) != catalog->definitions ||
        coh_snapshot_u32(catalog_header + 44)) goto done;
    s.files = catalog->files; s.slots = catalog->slots;
    s.definitions = catalog->definitions; s.children = catalog->children;
    if (s.files > COH_SOURCE_CATALOG_MAX_FILES ||
        s.slots > COH_SOURCE_CATALOG_MAX_SLOTS ||
        s.definitions > COH_SOURCE_CATALOG_MAX_DEFINITIONS ||
        s.children > COH_SOURCE_CATALOG_MAX_CHILDREN ||
        group_info.ref_count < 0 ||
        (unsigned int)group_info.ref_count > COH_SOURCE_CATALOG_MAX_ROOT_SLOTS)
    { status = COH_SOURCE_CATALOG_LIMIT; goto done; }
    s.roots = (unsigned int)group_info.ref_count;
    status = coh_snapshot_inventory(&s);
    if (status) goto done;
    defs_crc = (unsigned int)groupInfoCrcDefs();
    refs_crc = (unsigned int)groupInfoCrcRefs();
    active = (unsigned int)groupInfoRefCount();
    if (defs_crc != coh_snapshot_u32(catalog_header + 32) ||
        refs_crc != coh_snapshot_u32(catalog_header + 36) ||
        active != coh_snapshot_u32(catalog_header + 40))
    { status = COH_SOURCE_CATALOG_CHANGED; goto done; }
    original_external = s.external_count;
    memset(header, 0, sizeof(header)); memcpy(header, "COHRTS01", 8);
    coh_source_catalog_put_u32(header + 8, 1u);
    coh_source_catalog_put_u32(header + 12, sizeof(header));
    coh_source_catalog_put_u32(header + 20, coh_snapshot_u32(catalog_header + 20));
    coh_source_catalog_put_u32(header + 24, catalog->total_bytes);
    coh_source_catalog_put_u32(header + 28, s.files);
    coh_source_catalog_put_u32(header + 32, s.slots);
    coh_source_catalog_put_u32(header + 36, s.definitions);
    coh_source_catalog_put_u32(header + 40, s.children);
    coh_source_catalog_put_u32(header + 44, s.roots);
    coh_source_catalog_put_u32(header + 48, active);
    coh_source_catalog_put_u32(header + 52, s.external_count);
    coh_source_catalog_put_u32(header + 56, defs_crc);
    coh_source_catalog_put_u32(header + 60, refs_crc);
    s.output = output; s.context = context;
    for (pass = 0; pass < 2u; ++pass)
    {
        s.pass = pass; s.emitted = 0;
        status = coh_snapshot_inventory(&s);
        if (!status) status = coh_snapshot_emit(&s, header, sizeof(header));
        if (!status) status = coh_snapshot_roots(&s);
        if (!status) status = coh_snapshot_external(&s);
        if (status) goto done;
        if (!pass)
        {
            s.total = s.emitted;
            coh_source_catalog_put_u32(header + 16, s.total);
        }
    }
    status = coh_snapshot_inventory(&s);
    if (!status && (s.emitted != s.total || s.external_count != original_external ||
        (unsigned int)groupInfoCrcDefs() != defs_crc ||
        (unsigned int)groupInfoCrcRefs() != refs_crc ||
        (unsigned int)groupInfoRefCount() != active)) status = COH_SOURCE_CATALOG_CHANGED;
done:
    report->status = (unsigned int)status;
    report->total_bytes = s.total; report->emitted_bytes = s.pass ? s.emitted : 0;
    report->root_slots = s.roots; report->external_count = s.external_count;
    report->external_children = s.external_children;
    if (status == COH_SOURCE_CATALOG_OK)
    {
        report->active_roots = active; report->defs_crc = defs_crc; report->refs_crc = refs_crc;
    }
    return status;
}

#endif
