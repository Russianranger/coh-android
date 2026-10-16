/* Include after the unchanged original groupnetsend.c in the SAME translation
 * unit, where its static sendDef is visible. The embedding server initializes
 * the normal packet subsystem and supplies an exclusive, stable group_info
 * snapshot for the whole call, including callbacks. Original property writing
 * also uses process globals, so concurrent packet/property serialization is
 * not supported. No GroupDef, GroupFile, tracker or NetLink is modified here.
 *
 * The output callback must consume/copy each span before returning exactly 1.
 * It must stage output until success: a callback error or a changed snapshot
 * can leave a partial envelope. This adapter never sends a packet, opens a
 * file, or uses a network link. asset_generation is a caller-owned identity,
 * not a claim that this source snapshot is authoritative for another asset set.
 *
 * All records are the complete unmodified sendDef output, including id+1.
 * pktSetCompression(...,1) selects byte-aligned field encoding; no packet
 * transport header or zlib compression is applied. Private packet debug tags
 * are disabled. The original trusted packet allocator may grow transiently
 * before the record admission limit is checked. These output limits are not a
 * hard allocation bound on that upstream allocator; the native catalog decoder
 * must independently enforce its input and ownership budgets.
 */
#ifndef COH_SOURCE_CATALOG_EXPORT_INCLUDED
#define COH_SOURCE_CATALOG_EXPORT_INCLUDED

#include <string.h>

typedef char CohSourceCatalogU32MustHaveFourBytes[
    sizeof(unsigned int) == 4 ? 1 : -1];

#define COH_SOURCE_CATALOG_VERSION 1u
#define COH_SOURCE_CATALOG_HEADER_BYTES 48u
#define COH_SOURCE_CATALOG_MAX_FILES 1024u
#define COH_SOURCE_CATALOG_MAX_SLOTS 65536u
#define COH_SOURCE_CATALOG_MAX_DEFINITIONS 65536u
#define COH_SOURCE_CATALOG_MAX_CHILDREN 262144u
#define COH_SOURCE_CATALOG_MAX_ACTIVE_ROOTS 65536u
#define COH_SOURCE_CATALOG_MAX_ROOT_SLOTS 65536u
#define COH_SOURCE_CATALOG_MAX_NAME_BYTES 256u
#define COH_SOURCE_CATALOG_MAX_RECORD_BYTES (4u * 1024u * 1024u)
#define COH_SOURCE_CATALOG_MAX_BYTES (32u * 1024u * 1024u)
#define COH_SOURCE_CATALOG_NO_INDEX 0xffffffffu

typedef int (*CohSourceCatalogOutputFn)(void *context,
    const unsigned char *bytes, unsigned int size);

typedef enum CohSourceCatalogExportStatus
{
    COH_SOURCE_CATALOG_OK = 0,
    COH_SOURCE_CATALOG_ARGUMENT = 1,
    COH_SOURCE_CATALOG_LIMIT = 2,
    COH_SOURCE_CATALOG_SOURCE = 3,
    COH_SOURCE_CATALOG_PACKET = 4,
    COH_SOURCE_CATALOG_OUTPUT = 5,
    COH_SOURCE_CATALOG_CHANGED = 6
} CohSourceCatalogExportStatus;

typedef struct CohSourceCatalogExportReport
{
    unsigned int status;
    unsigned int failure_file;
    unsigned int failure_slot;
    unsigned int files;
    unsigned int definitions;
    unsigned int slots;
    unsigned int children;
    unsigned int wire_bytes;
    unsigned int total_bytes;
    unsigned int emitted_bytes;
} CohSourceCatalogExportReport;

static int coh_source_catalog_fail(CohSourceCatalogExportReport *report,
    int status, unsigned int file, unsigned int slot)
{
    report->status = (unsigned int)status;
    report->failure_file = file;
    report->failure_slot = slot;
    return status;
}

/* Match the decoder's nonempty visible-ASCII name admission exactly. Returns
 * bytes including NUL, or zero for an inadmissible or overlong source name. */
static unsigned int coh_source_catalog_name_bytes(const char *name)
{
    unsigned int i;
    unsigned char c;
    if (!name)
        return 0;
    for (i = 0; i < COH_SOURCE_CATALOG_MAX_NAME_BYTES; ++i)
    {
        c = (unsigned char)name[i];
        if (!c)
            return i ? i + 1u : 0;
        if (c < 32u || c > 126u)
            return 0;
    }
    return 0;
}

static int coh_source_catalog_same_name(const char *a, const char *b)
{
    unsigned int ca, cb;
    while (*a && *b)
    {
        ca = (unsigned char)*a++;
        cb = (unsigned char)*b++;
        if (ca >= 'A' && ca <= 'Z')
            ca += 'a' - 'A';
        if (cb >= 'A' && cb <= 'Z')
            cb += 'a' - 'A';
        if (ca != cb)
            return 0;
    }
    return *a == *b;
}

static void coh_source_catalog_put_u32(unsigned char *out, unsigned int value)
{
    out[0] = (unsigned char)value;
    out[1] = (unsigned char)(value >> 8);
    out[2] = (unsigned char)(value >> 16);
    out[3] = (unsigned char)(value >> 24);
}

static int coh_source_catalog_emit(CohSourceCatalogOutputFn output,
    void *context, CohSourceCatalogExportReport *report,
    const unsigned char *bytes, unsigned int size,
    unsigned int file, unsigned int slot)
{
    if (size > report->total_bytes - report->emitted_bytes)
        return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_CHANGED,
            file, slot);
    if (output(context, bytes, size) != 1)
        return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_OUTPUT,
            file, slot);
    report->emitted_bytes += size;
    return COH_SOURCE_CATALOG_OK;
}

/* Packet ownership always stays with this adapter. Every successful return
 * gives the caller one packet which it must pktFree after using stream.data. */
static Packet *coh_source_catalog_record(GroupDef *def,
    unsigned int *wire_bits, unsigned int *wire_bytes)
{
    Packet *pak;
    pak = pktCreate();
    if (!pak)
        return 0;
    pak->hasDebugInfo = 0;
    pktSetCompression(pak, 1);
    sendDef(pak, def);
    *wire_bits = pak->stream.bitLength;
    *wire_bytes = *wire_bits / 8u;
    if (pak->stream.errorFlags || !pak->stream.data ||
        !pak->stream.byteAlignedMode || (*wire_bits & 7u) ||
        pak->stream.cursor.bit || pak->stream.cursor.byte != *wire_bytes ||
        !*wire_bytes)
    {
        pktFree(pak);
        return 0;
    }
    return pak;
}

/* Returns COH_SOURCE_CATALOG_OK (zero) on complete success. The report is
 * optional, and retains the measured counts and successfully emitted byte
 * count on failure. Null slots are represented only by file.slot_count;
 * allocated tombstones are actual sendDef records and are never omitted. */
int coh_source_catalog_export(CohSourceCatalogOutputFn output, void *context,
    unsigned int asset_generation, CohSourceCatalogExportReport *report)
{
    CohSourceCatalogExportReport local_report;
    unsigned int records[COH_SOURCE_CATALOG_MAX_FILES];
    unsigned char header[COH_SOURCE_CATALOG_HEADER_BYTES];
    unsigned char fields[20];
    unsigned int file_count, root_slots, f, s, j, count, name_bytes;
    unsigned int wire_bits, wire_bytes, active_roots, defs_crc, refs_crc;
    unsigned int second_definitions, second_wire_bytes, second_slots;
    unsigned int second_children, second_records;
    int status;
    GroupFile *file;
    GroupDef *def;
    Packet *pak;

    if (!report)
        report = &local_report;
    memset(report, 0, sizeof(*report));
    report->failure_file = COH_SOURCE_CATALOG_NO_INDEX;
    report->failure_slot = COH_SOURCE_CATALOG_NO_INDEX;
    report->total_bytes = COH_SOURCE_CATALOG_HEADER_BYTES;
    if (!output || !asset_generation)
        return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_ARGUMENT,
            COH_SOURCE_CATALOG_NO_INDEX, COH_SOURCE_CATALOG_NO_INDEX);
    if (group_info.file_count < 0 ||
        (unsigned int)group_info.file_count > COH_SOURCE_CATALOG_MAX_FILES)
        return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_LIMIT,
            COH_SOURCE_CATALOG_NO_INDEX, COH_SOURCE_CATALOG_NO_INDEX);
    if (group_info.ref_count >= 0 &&
        (unsigned int)group_info.ref_count > COH_SOURCE_CATALOG_MAX_ROOT_SLOTS)
        return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_LIMIT,
            COH_SOURCE_CATALOG_NO_INDEX, COH_SOURCE_CATALOG_NO_INDEX);
    file_count = (unsigned int)group_info.file_count;
    report->files = file_count;
    if ((file_count && !group_info.files) || group_info.ref_count < 0 ||
        (group_info.ref_count && !group_info.refs))
        return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_SOURCE,
            COH_SOURCE_CATALOG_NO_INDEX, COH_SOURCE_CATALOG_NO_INDEX);

    root_slots = (unsigned int)group_info.ref_count;

    /* First pass validates the source shape and measures native bytes before
     * any callback is invoked. It never invokes sendGroupFile, whose normal
     * saved-definition filtering and force_reload mutation are inappropriate. */
    for (f = 0; f < file_count; ++f)
    {
        file = group_info.files[f];
        if (!file || file->count < 0 || (file->count && !file->defs))
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_SOURCE,
                f, COH_SOURCE_CATALOG_NO_INDEX);
        count = (unsigned int)file->count;
        if (count > COH_SOURCE_CATALOG_MAX_SLOTS - report->slots)
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_LIMIT,
                f, COH_SOURCE_CATALOG_NO_INDEX);
        name_bytes = coh_source_catalog_name_bytes(file->fullname);
        if (!name_bytes)
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_SOURCE,
                f, COH_SOURCE_CATALOG_NO_INDEX);
        for (j = 0; j < f; ++j)
        {
            if (coh_source_catalog_same_name(file->fullname,
                group_info.files[j]->fullname))
                return coh_source_catalog_fail(report,
                    COH_SOURCE_CATALOG_SOURCE, f, COH_SOURCE_CATALOG_NO_INDEX);
        }
        if (20u + name_bytes >
            COH_SOURCE_CATALOG_MAX_BYTES - report->total_bytes)
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_LIMIT,
                f, COH_SOURCE_CATALOG_NO_INDEX);
        report->total_bytes += 20u + name_bytes;
        report->slots += count;
        records[f] = 0;
        for (s = 0; s < count; ++s)
        {
            def = file->defs[s];
            if (!def)
                continue;
            if (def->id < 0 || (unsigned int)def->id != s ||
                def->in_use > 1)
                return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_SOURCE,
                    f, s);
            if (report->definitions == COH_SOURCE_CATALOG_MAX_DEFINITIONS)
                return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_LIMIT,
                    f, s);
            ++report->definitions;
            ++records[f];
            if (def->in_use)
            {
                if (def->count < 0 || (def->count && !def->entries) ||
                    !coh_source_catalog_name_bytes(def->name) ||
                    !def->name[0])
                    return coh_source_catalog_fail(report,
                        COH_SOURCE_CATALOG_SOURCE, f, s);
                if ((unsigned int)def->count >
                    COH_SOURCE_CATALOG_MAX_CHILDREN - report->children)
                    return coh_source_catalog_fail(report,
                        COH_SOURCE_CATALOG_LIMIT, f, s);
                report->children += (unsigned int)def->count;
                for (j = 0; j < (unsigned int)def->count; ++j)
                {
                    if (!def->entries[j].def ||
                        !coh_source_catalog_name_bytes(
                            def->entries[j].def->name) ||
                        !def->entries[j].def->name[0])
                        return coh_source_catalog_fail(report,
                            COH_SOURCE_CATALOG_SOURCE, f, s);
                }
            }
            pak = coh_source_catalog_record(def, &wire_bits, &wire_bytes);
            if (!pak)
                return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_PACKET,
                    f, s);
            if (wire_bytes > COH_SOURCE_CATALOG_MAX_RECORD_BYTES ||
                wire_bytes + 16u >
                    COH_SOURCE_CATALOG_MAX_BYTES - report->total_bytes)
            {
                pktFree(pak);
                return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_LIMIT,
                    f, s);
            }
            report->wire_bytes += wire_bytes;
            report->total_bytes += 16u + wire_bytes;
            pktFree(pak);
        }
    }
    /* These are the independent original traversal functions. Check the
     * tracker pointers they dereference before invoking either CRC oracle. */
    for (s = 0; s < root_slots; ++s)
    {
        if (!group_info.refs[s])
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_SOURCE,
                COH_SOURCE_CATALOG_NO_INDEX, s);
        def = group_info.refs[s]->def;
        if (def && def->count && !def->entries)
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_SOURCE,
                COH_SOURCE_CATALOG_NO_INDEX, s);
    }
    defs_crc = (unsigned int)groupInfoCrcDefs();
    refs_crc = (unsigned int)groupInfoCrcRefs();
    active_roots = (unsigned int)groupInfoRefCount();
    if (active_roots > COH_SOURCE_CATALOG_MAX_ACTIVE_ROOTS)
        return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_LIMIT,
            COH_SOURCE_CATALOG_NO_INDEX, COH_SOURCE_CATALOG_NO_INDEX);

    memset(header, 0, sizeof(header));
    memcpy(header, "COHCAT01", 8);
    coh_source_catalog_put_u32(header + 8, COH_SOURCE_CATALOG_VERSION);
    coh_source_catalog_put_u32(header + 12, COH_SOURCE_CATALOG_HEADER_BYTES);
    coh_source_catalog_put_u32(header + 16, report->total_bytes);
    coh_source_catalog_put_u32(header + 20, asset_generation);
    coh_source_catalog_put_u32(header + 24, file_count);
    coh_source_catalog_put_u32(header + 28, report->definitions);
    coh_source_catalog_put_u32(header + 32, defs_crc);
    coh_source_catalog_put_u32(header + 36, refs_crc);
    coh_source_catalog_put_u32(header + 40, active_roots);
    status = coh_source_catalog_emit(output, context, report, header,
        sizeof(header), COH_SOURCE_CATALOG_NO_INDEX, COH_SOURCE_CATALOG_NO_INDEX);
    if (status)
        return status;

    second_definitions = 0;
    second_wire_bytes = 0;
    second_slots = 0;
    second_children = 0;
    for (f = 0; f < file_count; ++f)
    {
        if (group_info.file_count != (int)file_count || !group_info.files ||
            !(file = group_info.files[f]) || file->count < 0 ||
            (file->count && !file->defs))
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_CHANGED,
                f, COH_SOURCE_CATALOG_NO_INDEX);
        count = (unsigned int)file->count;
        name_bytes = coh_source_catalog_name_bytes(file->fullname);
        if (!name_bytes || count > COH_SOURCE_CATALOG_MAX_SLOTS - second_slots)
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_CHANGED,
                f, COH_SOURCE_CATALOG_NO_INDEX);
        second_slots += count;
        coh_source_catalog_put_u32(fields, f);
        coh_source_catalog_put_u32(fields + 4, (unsigned int)file->bounds_checksum);
        coh_source_catalog_put_u32(fields + 8, count);
        coh_source_catalog_put_u32(fields + 12, records[f]);
        coh_source_catalog_put_u32(fields + 16, name_bytes);
        status = coh_source_catalog_emit(output, context, report, fields,
            20u, f, COH_SOURCE_CATALOG_NO_INDEX);
        if (status)
            return status;
        status = coh_source_catalog_emit(output, context, report,
            (const unsigned char *)file->fullname, name_bytes, f,
            COH_SOURCE_CATALOG_NO_INDEX);
        if (status)
            return status;
        second_records = 0;
        for (s = 0; s < count; ++s)
        {
            def = file->defs[s];
            if (!def)
                continue;
            if (def->id < 0 || (unsigned int)def->id != s || def->in_use > 1 ||
                ++second_records > records[f])
                return coh_source_catalog_fail(report,
                    COH_SOURCE_CATALOG_CHANGED, f, s);
            if (def->in_use)
            {
                if (def->count < 0 || (def->count && !def->entries) ||
                    (unsigned int)def->count >
                        COH_SOURCE_CATALOG_MAX_CHILDREN - second_children ||
                    !coh_source_catalog_name_bytes(def->name) ||
                    !def->name[0])
                    return coh_source_catalog_fail(report,
                        COH_SOURCE_CATALOG_CHANGED, f, s);
                second_children += (unsigned int)def->count;
                for (j = 0; j < (unsigned int)def->count; ++j)
                {
                    if (!def->entries[j].def ||
                        !coh_source_catalog_name_bytes(
                            def->entries[j].def->name) ||
                        !def->entries[j].def->name[0])
                        return coh_source_catalog_fail(report,
                            COH_SOURCE_CATALOG_CHANGED, f, s);
                }
            }
            pak = coh_source_catalog_record(def, &wire_bits, &wire_bytes);
            if (!pak)
                return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_PACKET,
                    f, s);
            if (wire_bytes > COH_SOURCE_CATALOG_MAX_RECORD_BYTES)
            {
                pktFree(pak);
                return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_CHANGED,
                    f, s);
            }
            coh_source_catalog_put_u32(fields, s);
            coh_source_catalog_put_u32(fields + 4, wire_bits);
            coh_source_catalog_put_u32(fields + 8, wire_bytes);
            coh_source_catalog_put_u32(fields + 12, 1u);
            status = coh_source_catalog_emit(output, context, report, fields,
                16u, f, s);
            if (!status)
                status = coh_source_catalog_emit(output, context, report,
                    pak->stream.data, wire_bytes, f, s);
            pktFree(pak);
            if (status)
                return status;
            ++second_definitions;
            second_wire_bytes += wire_bytes;
        }
        if (second_records != records[f])
            return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_CHANGED,
                f, COH_SOURCE_CATALOG_NO_INDEX);
    }
    if (second_definitions != report->definitions ||
        second_slots != report->slots || second_children != report->children ||
        second_wire_bytes != report->wire_bytes ||
        report->emitted_bytes != report->total_bytes ||
        group_info.file_count != (int)file_count ||
        group_info.ref_count != (int)root_slots ||
        (unsigned int)groupInfoCrcDefs() != defs_crc ||
        (unsigned int)groupInfoCrcRefs() != refs_crc ||
        (unsigned int)groupInfoRefCount() != active_roots)
        return coh_source_catalog_fail(report, COH_SOURCE_CATALOG_CHANGED,
            COH_SOURCE_CATALOG_NO_INDEX, COH_SOURCE_CATALOG_NO_INDEX);
    return COH_SOURCE_CATALOG_OK;
}

#endif /* COH_SOURCE_CATALOG_EXPORT_INCLUDED */
