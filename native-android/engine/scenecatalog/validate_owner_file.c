/* Host-only complete ownership replay. OpenSSL is an explicit test provider,
 * not a new dependency of the portable native catalog library or any APK. */
#include "coh_catalog_owner.h"
#include <openssl/sha.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int hex(const char *text,uint8_t out[32]){
    if(strlen(text)!=64)return 0;
    for(unsigned i=0;i<32;i++){
        unsigned v=0;
        for(unsigned j=0;j<2;j++){unsigned c=(unsigned char)text[i*2+j];
            if(c>='0'&&c<='9')c-='0';else if(c>='a'&&c<='f')c=c-'a'+10;else return 0;v=v*16+c;
        }out[i]=(uint8_t)v;
    }return 1;
}
static CohStatus sha256(void *context,CohBytes input,uint8_t out[32]){
    SHA256_CTX ctx;(void)context;
    return SHA256_Init(&ctx)&&SHA256_Update(&ctx,input.data,input.size)&&SHA256_Final(out,&ctx)?COH_OK:COH_STATE;
}
int main(int argc,char **argv){
    CohCatalogOwner *owner=NULL;CohCatalogBinding b={0};CohCatalogOwnerReport report={0};
    CohCatalogOwnerBudget budget={COH_CATALOG_MEMORY_MAX,COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,64u*1024u};
    CohCatalogDigest digest={NULL,sha256};CohStatus status=COH_INVALID;FILE *f=NULL;uint8_t *raw=NULL;
    uint32_t files=0,slots=0,records=0,children=0,tombstones=0;long extent=0;unsigned long generation;char *end;
    if(argc!=6||!*argv[2])goto done;
    for(const char *c=argv[2];*c;c++)if(*c<'0'||*c>'9')goto done;
    errno=0;generation=strtoul(argv[2],&end,10);if(errno||*end||!generation||generation>UINT32_MAX)goto done;
    b.owner_generation=1;b.catalog_generation=(uint32_t)generation;b.asset_generation=1;
    if(!hex(argv[3],b.catalog_sha256)||!hex(argv[4],b.source_sha256)||!hex(argv[5],b.inventory_sha256))goto done;
    f=fopen(argv[1],"rb");if(!f)goto done;
    if(fseek(f,0,SEEK_END)||(extent=ftell(f))<48||extent>(long)COH_CATALOG_INPUT_MAX||fseek(f,0,SEEK_SET))goto done;
    raw=malloc((size_t)extent);if(!raw){status=COH_LIMIT;goto done;}
    if(fread(raw,1,(size_t)extent,f)!=(size_t)extent||fgetc(f)!=EOF||ferror(f))goto done;
    status=coh_catalog_owner_create(NULL,(CohBytes){raw,(size_t)extent},&b,&budget,&digest,&owner,&report);
    if(status!=COH_OK)goto done;
    /* No caller buffer survives: file/slot lookup must use the owned copy. */
    memset(raw,0,(size_t)extent);free(raw);raw=NULL;
    for(files=0;files<report.walk.catalog.files;files++){
        CohCatalogFileView view;status=coh_catalog_owner_file(owner,files,&view);if(status!=COH_OK)goto done;
        for(uint32_t s=0;s<view.slots;s++){
            CohCatalogRecordIdentity id;status=coh_catalog_owner_record(owner,files,s,&id);if(status!=COH_OK)goto done;
            slots++;records+=id.allocated;children+=id.child_count;tombstones+=id.allocated&&!id.in_use;
        }
    }
done:
    printf("{\"schema\":1,\"status\":%u,\"owner_created\":%s,\"generation\":%u,\"files\":%u,\"slots\":%u,\"definitions\":%u,\"children\":%u,\"tombstones\":%u,\"owned_bytes\":%zu,\"index_bytes\":%zu,\"peak_record_owned_bytes\":%zu,\"peak_aggregate_bytes\":%zu,\"provider_reserve_bytes\":65536,\"map_binding_present\":false,\"graph_published\":false,\"renderer_authorized\":false}\n",
        (unsigned)status,owner?"true":"false",b.catalog_generation,files,slots,records,children,tombstones,
        report.owned_bytes,report.index_bytes,report.walk.peak_record_owned_bytes,report.peak_aggregate_bytes);
    if(f)fclose(f);
    free(raw);coh_catalog_owner_release(owner);return status==COH_OK?0:2;
}
