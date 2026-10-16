/* Nonshipping paired sink; includes source_sink.inc's unchanged path checks.
 * Both outputs are created in a private C-drive directory, never replaced.
 * A completed pair is still untrusted until the hosted exact-SHA admission.
 */
#ifndef COH_SOURCE_RUNTIME_SNAPSHOT_SINK_INCLUDED
#define COH_SOURCE_RUNTIME_SNAPSHOT_SINK_INCLUDED
#if defined(SERVER) && defined(_WIN32)
typedef struct CohSnapshotPairWriter
{
    CohCatalogSinkWriter catalog, sidecar;
    unsigned char catalog_header[48];
    unsigned int header_present;
} CohSnapshotPairWriter;

static int coh_snapshot_catalog_write(void *context, const unsigned char *bytes, unsigned int size)
{
    CohSnapshotPairWriter *writer = (CohSnapshotPairWriter *)context;
    if (!writer->catalog.bytes)
    {
        if (size != sizeof(writer->catalog_header)) return 0;
        memcpy(writer->catalog_header, bytes, sizeof(writer->catalog_header));
        writer->header_present = 1u;
    }
    return coh_catalog_sink_output(&writer->catalog, bytes, size);
}
static int coh_snapshot_sidecar_write(void *context, const unsigned char *bytes, unsigned int size)
{
    CohSnapshotPairWriter *writer = (CohSnapshotPairWriter *)context;
    if (size > COH_SNAPSHOT_MAX_BYTES - writer->sidecar.bytes) return 0;
    return coh_catalog_sink_output(&writer->sidecar, bytes, size);
}

void coh_source_runtime_snapshot_startup(void)
{
    char paths[2][COH_CATALOG_SINK_PATH_MAX + 1u];
    char partial[2][COH_CATALOG_SINK_PATH_MAX + 9u];
    char generation_text[12];
    DWORD lengths[2], gen_length;
    unsigned int generation = 0, status = 2, i, created[2] = {0,0}, removed[2] = {0,0};
    CohSnapshotPairWriter writer;
    CohSourceCatalogExportReport catalog;
    CohSourceSnapshotReport snapshot;
    CohCatalogSinkWriter *sinks[2];
    int result;
    memset(&writer,0,sizeof(writer)); memset(&catalog,0,sizeof(catalog)); memset(&snapshot,0,sizeof(snapshot));
    sinks[0] = &writer.catalog; sinks[1] = &writer.sidecar;
    sinks[0]->handle = sinks[1]->handle = INVALID_HANDLE_VALUE;
    lengths[0] = GetEnvironmentVariableA("COH_NATIVE_SCENE_CATALOG_OUTPUT",paths[0],sizeof(paths[0]));
    lengths[1] = GetEnvironmentVariableA("COH_NATIVE_RUNTIME_SNAPSHOT_OUTPUT",paths[1],sizeof(paths[1]));
    if (!lengths[0] && !lengths[1]) return;
    if (!lengths[0] || !lengths[1] || lengths[0] >= sizeof(paths[0]) || lengths[1] >= sizeof(paths[1])) goto done;
    gen_length = GetEnvironmentVariableA("COH_NATIVE_SCENE_CATALOG_GENERATION",generation_text,sizeof(generation_text));
    if (!gen_length || gen_length >= sizeof(generation_text) || !coh_catalog_sink_generation(generation_text,&generation)) goto done;
    status = 3;
    for (i = 0; i < 2u; ++i)
    {
        if (!coh_catalog_sink_path(paths[i], lengths[i])) goto done;
        memcpy(partial[i],paths[i],lengths[i]); memcpy(partial[i]+lengths[i],".partial",9);
        if (GetFileAttributesA(paths[i]) != INVALID_FILE_ATTRIBUTES || GetLastError() != ERROR_FILE_NOT_FOUND) goto done;
    }
    if (coh_source_catalog_same_name(paths[0],paths[1]) ||
        coh_source_catalog_same_name(paths[0],partial[1]) || coh_source_catalog_same_name(paths[1],partial[0])) goto done;
    status = 4;
    for (i = 0; i < 2u; ++i)
    {
        sinks[i]->handle = CreateFileA(partial[i],GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
        if (sinks[i]->handle == INVALID_HANDLE_VALUE) goto cleanup;
        created[i] = 1u;
    }
    status = 5;
    /* One contiguous owner-thread scope: no packet send or lazy load occurs. */
    result = coh_source_catalog_export(coh_snapshot_catalog_write,&writer,generation,&catalog);
    if (result || catalog.status || !writer.header_present || writer.catalog.failed ||
        catalog.total_bytes != writer.catalog.bytes || catalog.emitted_bytes != writer.catalog.bytes) goto cleanup;
    result = coh_source_runtime_snapshot_export(coh_snapshot_sidecar_write,&writer,writer.catalog_header,&catalog,&snapshot);
    if (result || snapshot.status || writer.sidecar.failed ||
        snapshot.total_bytes != writer.sidecar.bytes || snapshot.emitted_bytes != writer.sidecar.bytes) goto cleanup;
    status = 6;
    for (i = 0; i < 2u; ++i)
        if (!FlushFileBuffers(sinks[i]->handle)) goto cleanup;
    status = 7;
    for (i = 0; i < 2u; ++i)
    {
        if (!CloseHandle(sinks[i]->handle)) goto cleanup;
        sinks[i]->handle = INVALID_HANDLE_VALUE;
    }
    status = 8;
    for (i = 0; i < 2u; ++i)
    {
        if (!MoveFileExA(partial[i],paths[i],MOVEFILE_WRITE_THROUGH)) goto cleanup;
        created[i] = 0;
    }
    status = 1;
cleanup:
    for (i = 0; i < 2u; ++i)
    {
        if (sinks[i]->handle != INVALID_HANDLE_VALUE)
        { CloseHandle(sinks[i]->handle); sinks[i]->handle = INVALID_HANDLE_VALUE; }
        if (created[i]) removed[i] = DeleteFileA(partial[i]) ? 1u : 0u;
    }
done:
    printf("COH_RUNTIME_SNAPSHOT_V1 status=%u catalog_status=%u snapshot_status=%u "
        "catalog_bytes=%u snapshot_bytes=%u files=%u slots=%u definitions=%u children=%u "
        "root_slots=%u active_roots=%u external_count=%u external_children=%u "
        "defs_crc=%u refs_crc=%u partial_remaining=%u\n",status,catalog.status,snapshot.status,
        writer.catalog.bytes,writer.sidecar.bytes,catalog.files,catalog.slots,catalog.definitions,catalog.children,
        snapshot.root_slots,snapshot.active_roots,snapshot.external_count,snapshot.external_children,
        snapshot.defs_crc,snapshot.refs_crc,(created[0]&&!removed[0])+(created[1]&&!removed[1]));
}
#else
void coh_source_runtime_snapshot_startup(void) { }
#endif
#endif
