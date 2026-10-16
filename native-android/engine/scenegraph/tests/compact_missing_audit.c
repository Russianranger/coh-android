/* Host diagnostic only: walk every original record, emit names and child names.
 * No compact candidate, missing-edge suppression, or graph publication occurs. */
#include "../../scenecatalog/coh_scenecatalog.h"
#include <stdio.h>
#include <stdlib.h>
static CohStatus file(void*context,const CohCatalogFileView*v){(void)context;return printf("F\t%u\t%s\n",v->index,v->name)<0?COH_STATE:COH_OK;}
static CohStatus slot(void*context,const CohCatalogSlotView*v){
    (void)context;if(!v->allocated||!v->definition->in_use)return COH_OK;
    const CohSgDefinition*d=v->definition;
    if(printf("D\t%u\t%u\t%s\n",v->file->index,v->slot,d->name)<0)return COH_STATE;
    for(uint32_t i=0;i<d->child_count;i++)if(printf("C\t%u\t%u\t%u\t%s\n",v->file->index,v->slot,i,d->children[i].name)<0)return COH_STATE;
    return COH_OK;
}
int main(int argc,char**argv){
    if(argc!=2)return 2;
    FILE*f=fopen(argv[1],"rb");if(!f)return 2;
    if(fseek(f,0,SEEK_END)){fclose(f);return 2;}long n=ftell(f);
    if(n<48||n>COH_CATALOG_INPUT_MAX||fseek(f,0,SEEK_SET)){fclose(f);return 2;}
    unsigned char*bytes=malloc((size_t)n);if(!bytes){fclose(f);return 2;}
    if(fread(bytes,1,(size_t)n,f)!=(size_t)n||fgetc(f)!=EOF){fclose(f);free(bytes);return 2;}
    if(fclose(f)){free(bytes);return 2;}
    uint32_t generation=(uint32_t)bytes[20]|(uint32_t)bytes[21]<<8|(uint32_t)bytes[22]<<16|(uint32_t)bytes[23]<<24;
    CohCatalogVisitor visitor={NULL,file,slot};CohCatalogWalkBudget budget={COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,0};CohCatalogWalkReport report;
    CohStatus status=coh_scenecatalog_walk((CohBytes){bytes,(size_t)n},generation,&budget,&visitor,&report);
    free(bytes);if(status!=COH_OK)return 2;
    if(printf("R\t%u\t%u\t%u\t%u\t%zu\n",report.catalog.files,report.catalog.slots,report.records_validated,report.catalog.children,report.peak_record_owned_bytes)<0||fflush(stdout))return 2;
    return 0;
}
