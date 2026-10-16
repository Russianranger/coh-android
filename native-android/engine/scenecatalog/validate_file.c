/* Standalone off-device capture validator. No graph/actor/render authority. */
#include "coh_scenecatalog.h"
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <string.h>
int main(int argc,char **argv){
    FILE *f=NULL; unsigned char *raw=NULL; CohSceneCatalog *catalog=NULL;
    CohCatalogReport report={0}; CohCatalogWalkReport walk={0}; int streaming=0;
    long size; char *end; const char *digit; unsigned long generation;
    CohStatus status=COH_STATE;
    if(argc==4&&!strcmp(argv[3],"--stream"))streaming=1;
    else if(argc!=3)goto done;
    if(!*argv[2])goto done;
    for(digit=argv[2];*digit;digit++)if(*digit<'0'||*digit>'9')goto done;
    errno=0;generation=strtoul(argv[2],&end,10);
    if(errno||!*argv[2]||*end||!generation||generation>UINT_MAX)goto done;
    f=fopen(argv[1],"rb");if(!f)goto done;
    if(fseek(f,0,SEEK_END)||((size=ftell(f))<48)||size>(long)COH_CATALOG_INPUT_MAX||fseek(f,0,SEEK_SET))goto done;
    raw=malloc((size_t)size);if(!raw){status=COH_LIMIT;goto done;}
    if(fread(raw,1,(size_t)size,f)!=(size_t)size||fgetc(f)!=EOF||ferror(f))goto done;
    if(streaming){
        CohCatalogWalkBudget budget={COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,0};
        status=coh_scenecatalog_walk((CohBytes){raw,(size_t)size},(uint32_t)generation,&budget,NULL,&walk);
        report=walk.catalog;
    }else status=coh_scenecatalog_load(&catalog,(CohBytes){raw,(size_t)size},(uint32_t)generation,&report);
 done:
    if(f)fclose(f);
    printf("{\"schema\":1,\"status\":%d,\"native_decode_completed\":%s,\"validation_mode\":\"%s\",\"catalog_materialized\":%s,\"generation\":%u,\"files\":%u,\"definitions\":%u,\"slots\":%u,\"children\":%u,\"definitions_crc\":%u,\"references_crc\":%u,\"active_roots\":%u,\"input_bytes\":%zu,\"owned_bytes\":%zu,\"minimum_materialized_bytes\":%zu,\"stage\":%u,\"file\":%u,\"slot\":%u,\"offset\":%zu,\"records_validated\":%u,\"peak_record_owned_bytes\":%zu,\"peak_working_bytes\":%zu,\"peak_aggregate_bytes\":%zu,\"failed_record_peak_unknown\":%s,\"working_upper_bound\":%zu,\"aggregate_upper_bound\":%zu,\"graph_published\":false,\"renderer_authorized\":false}\n",(int)status,status==COH_OK?"true":"false",streaming?"stream":"materialize",catalog?"true":"false",report.generation,report.files,report.definitions,report.slots,report.children,report.source_defs_crc,report.source_refs_crc,report.source_active_roots,report.input_bytes,report.owned_bytes,report.minimum_owned_bytes,(unsigned)report.stage,report.file,report.slot,report.offset,walk.records_validated,walk.peak_record_owned_bytes,walk.peak_working_bytes,walk.peak_aggregate_bytes,walk.failed_record_peak_unknown?"true":"false",walk.working_upper_bound,walk.aggregate_upper_bound);
    coh_scenecatalog_free(catalog);free(raw);return status==COH_OK?0:2;
}
