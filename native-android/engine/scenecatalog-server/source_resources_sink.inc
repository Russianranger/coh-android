/* Nonshipping triple sink; includes source_sink.inc's unchanged path checks.
 * All three outputs are created in a private C-drive directory, never replaced.
 * A completed triple is still untrusted until the hosted exact-SHA admission.
 */
#ifndef COH_SOURCE_RESOURCE_SNAPSHOT_SINK_INCLUDED
#define COH_SOURCE_RESOURCE_SNAPSHOT_SINK_INCLUDED
#if defined(SERVER) && defined(_WIN32)
extern int folder_cache_update_enable,folder_cache_manual_callback_check;
int coh_resource_quiescence_begin(void);
int coh_resource_quiescence_end(void);
typedef struct CohResourceTripleWriter
{
    CohCatalogSinkWriter catalog, sidecar, resources;
    unsigned char catalog_header[48];
    unsigned int header_present;
} CohResourceTripleWriter;

static int coh_resource_catalog_write(void *context, const unsigned char *bytes, unsigned int size)
{
    CohResourceTripleWriter *writer = (CohResourceTripleWriter *)context;
    if (!writer->catalog.bytes)
    {
        if (size != sizeof(writer->catalog_header)) return 0;
        memcpy(writer->catalog_header, bytes, sizeof(writer->catalog_header));
        writer->header_present = 1u;
    }
    return coh_catalog_sink_output(&writer->catalog, bytes, size);
}
static int coh_resource_sidecar_write(void *context, const unsigned char *bytes, unsigned int size)
{
    CohResourceTripleWriter *writer = (CohResourceTripleWriter *)context;
    if (size > COH_SNAPSHOT_MAX_BYTES - writer->sidecar.bytes) return 0;
    return coh_catalog_sink_output(&writer->sidecar, bytes, size);
}

static int coh_resource_rows_write(void *context,const unsigned char*bytes,unsigned int size)
{
    CohResourceTripleWriter*writer=(CohResourceTripleWriter*)context;
    if(size>COH_RESOURCE_TOTAL_MAX-writer->resources.bytes)return 0;
    return coh_catalog_sink_output(&writer->resources,bytes,size);
}

void coh_source_resource_snapshot_startup(void)
{
    char paths[3][COH_CATALOG_SINK_PATH_MAX + 1u];
    char partial[3][COH_CATALOG_SINK_PATH_MAX + 9u];
    char generation_text[12];
    DWORD lengths[3], gen_length;
    unsigned int generation = 0, status = 2, i, created[3] = {0,0,0}, published[3] = {0,0,0}, removed[3] = {0,0,0}, final_removed[3] = {0,0,0}, j;
    CohResourceTripleWriter writer;
    CohSourceCatalogExportReport catalog;
    CohSourceSnapshotReport snapshot;
    CohSourceResourceReport resources;
    static unsigned char resource_scratch[COH_RESOURCE_RECORD_MAX];
    CohCatalogSinkWriter *sinks[3];
    int result;
    unsigned quiet_held=0,quiet_status=0,quiet_observed=0,quiet_released=0;
    memset(&writer,0,sizeof(writer)); memset(&catalog,0,sizeof(catalog)); memset(&snapshot,0,sizeof(snapshot));memset(&resources,0,sizeof(resources));
    sinks[0] = &writer.catalog; sinks[1] = &writer.sidecar;sinks[2] = &writer.resources;
    sinks[0]->handle = sinks[1]->handle = sinks[2]->handle = INVALID_HANDLE_VALUE;
    lengths[0] = GetEnvironmentVariableA("COH_NATIVE_SCENE_CATALOG_OUTPUT",paths[0],sizeof(paths[0]));
    lengths[1] = GetEnvironmentVariableA("COH_NATIVE_RUNTIME_SNAPSHOT_OUTPUT",paths[1],sizeof(paths[1]));
    lengths[2] = GetEnvironmentVariableA("COH_NATIVE_RESOURCE_SNAPSHOT_OUTPUT",paths[2],sizeof(paths[2]));
    if (!lengths[0] && !lengths[1] && !lengths[2]) return;
    for(i=0;i<3u;i++)if(!lengths[i]||lengths[i]>=sizeof(paths[i]))goto done;
    gen_length = GetEnvironmentVariableA("COH_NATIVE_SCENE_CATALOG_GENERATION",generation_text,sizeof(generation_text));
    if (!gen_length || gen_length >= sizeof(generation_text) || !coh_catalog_sink_generation(generation_text,&generation)) goto done;
    status = 3;
    for (i = 0; i < 3u; ++i)
    {
        if (!coh_catalog_sink_path(paths[i], lengths[i])) goto done;
        memcpy(partial[i],paths[i],lengths[i]); memcpy(partial[i]+lengths[i],".partial",9);
        if (GetFileAttributesA(paths[i]) != INVALID_FILE_ATTRIBUTES || GetLastError() != ERROR_FILE_NOT_FOUND) goto done;
    }
    for(i=0;i<3u;i++)for(j=i+1;j<3u;j++)
        if(coh_source_catalog_same_name(paths[i],paths[j])||
            coh_source_catalog_same_name(paths[i],partial[j])||
            coh_source_catalog_same_name(paths[j],partial[i]))goto done;
    status = 4;
    for (i = 0; i < 3u; ++i)
    {
        sinks[i]->handle = CreateFileA(partial[i],GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
        if (sinks[i]->handle == INVALID_HANDLE_VALUE) goto cleanup;
        created[i] = 1u;
    }
    status=9;
    if(folder_cache_update_enable||!folder_cache_manual_callback_check)goto cleanup;
    quiet_status=(unsigned)coh_resource_quiescence_begin();if(quiet_status!=1)goto cleanup;
    quiet_held=quiet_observed=1;
    status = 5;
    /* One contiguous owner-thread scope: no packet send or lazy load occurs. */
    result = coh_source_catalog_export(coh_resource_catalog_write,&writer,generation,&catalog);
    if (result || catalog.status || !writer.header_present || writer.catalog.failed ||
        catalog.total_bytes != writer.catalog.bytes || catalog.emitted_bytes != writer.catalog.bytes) goto cleanup;
    result = coh_source_runtime_snapshot_export(coh_resource_sidecar_write,&writer,writer.catalog_header,&catalog,&snapshot);
    if (result || snapshot.status || writer.sidecar.failed ||
        snapshot.total_bytes != writer.sidecar.bytes || snapshot.emitted_bytes != writer.sidecar.bytes) goto cleanup;
    result=coh_source_resources_export(coh_resource_rows_write,&writer,writer.catalog_header,&catalog,
        resource_scratch,sizeof(resource_scratch),&resources);
    if(result||resources.status||writer.resources.failed||resources.total_bytes!=writer.resources.bytes||
        resources.emitted_bytes!=writer.resources.bytes)goto cleanup;
    quiet_released=(unsigned)coh_resource_quiescence_end();if(!quiet_released)goto cleanup;quiet_held=0;
    status = 6;
    for (i = 0; i < 3u; ++i)
        if (!FlushFileBuffers(sinks[i]->handle)) goto cleanup;
    status = 7;
    for (i = 0; i < 3u; ++i)
    {
        if (!CloseHandle(sinks[i]->handle)) goto cleanup;
        sinks[i]->handle = INVALID_HANDLE_VALUE;
    }
    status = 8;
    for (i = 0; i < 3u; ++i)
    {
        if (!MoveFileExA(partial[i],paths[i],MOVEFILE_WRITE_THROUGH)) goto cleanup;
        created[i] = 0;published[i]=1;
    }
    status = 1;
cleanup:
    if(quiet_held){quiet_released=(unsigned)coh_resource_quiescence_end();quiet_held=quiet_released?0u:1u;}
    for (i = 0; i < 3u; ++i)
    {
        if (sinks[i]->handle != INVALID_HANDLE_VALUE)
        { CloseHandle(sinks[i]->handle); sinks[i]->handle = INVALID_HANDLE_VALUE; }
        if (created[i]) removed[i] = DeleteFileA(partial[i]) ? 1u : 0u;
        if(status!=1&&published[i])final_removed[i]=DeleteFileA(paths[i])?1u:0u;
    }
done:
    printf("COH_RESOURCE_SNAPSHOT_V1 status=%u catalog_status=%u snapshot_status=%u resource_status=%u "
        "catalog_bytes=%u snapshot_bytes=%u resource_bytes=%u files=%u slots=%u definitions=%u children=%u "
        "root_slots=%u active_roots=%u external_count=%u external_children=%u "
        "resource_records=%u resource_models=%u resource_missing_models=%u resource_textures=%u model_row_comparisons=%u "
        "client_materials_available=0 client_lods_available=0 source_quiescence_status=%u source_quiescence_held=%u source_quiescence_released=%u defs_crc=%u refs_crc=%u partial_remaining=%u failed_final_remaining=%u\n",
        status,catalog.status,snapshot.status,resources.status,writer.catalog.bytes,writer.sidecar.bytes,writer.resources.bytes,
        catalog.files,catalog.slots,catalog.definitions,catalog.children,snapshot.root_slots,snapshot.active_roots,
        snapshot.external_count,snapshot.external_children,resources.records,resources.models,resources.missing_models,resources.textures,resources.model_row_comparisons,
        quiet_status,quiet_observed,quiet_released,snapshot.defs_crc,snapshot.refs_crc,(unsigned)((created[0]&&!removed[0])+(created[1]&&!removed[1])+(created[2]&&!removed[2])),
        status==1?0u:(unsigned)((published[0]&&!final_removed[0])+(published[1]&&!final_removed[1])+(published[2]&&!final_removed[2])));
}
#else
void coh_source_resource_snapshot_startup(void) { }
#endif
#endif
