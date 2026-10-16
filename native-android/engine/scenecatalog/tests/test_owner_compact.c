/* Host-only composed ownership measurement. Neither capture nor graph publish. */
#include "coh_catalog_owner.h"
#include "coh_scene_compact.h"
#include <openssl/sha.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define HARNESS_RESERVE (64u*1024u)
#define PROVIDER_RESERVE (64u*1024u)
typedef struct {void *pointer;size_t size;} Allocation;
static Allocation allocations[512];
static size_t live_bytes,peak_bytes,live_count,peak_count;
static unsigned checks;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"composition:%d: %s\n",__LINE__,#x);abort();}} while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void *);
static void track(void *pointer,size_t bytes){
    if(!pointer)return;
    for(size_t i=0;i<sizeof(allocations)/sizeof(*allocations);i++)if(!allocations[i].pointer){
        allocations[i]=(Allocation){pointer,bytes};live_bytes+=bytes;live_count++;
        if(live_bytes>peak_bytes)peak_bytes=live_bytes;
        if(live_count>peak_count)peak_count=live_count;
        return;
    }abort();
}
void *__wrap_malloc(size_t bytes){void *p=__real_malloc(bytes);track(p,bytes);return p;}
void *__wrap_calloc(size_t count,size_t bytes){assert(!bytes||count<=SIZE_MAX/bytes);void *p=__real_calloc(count,bytes);track(p,count*bytes);return p;}
void __wrap_free(void *pointer){
    if(!pointer)return;
    for(size_t i=0;i<sizeof(allocations)/sizeof(*allocations);i++)if(allocations[i].pointer==pointer){
        live_bytes-=allocations[i].size;live_count--;allocations[i]=(Allocation){0};__real_free(pointer);return;
    }abort();
}
static int hex(const char *text,uint8_t out[32]){
    if(strlen(text)!=64)return 0;
    for(unsigned i=0;i<32;i++){
        unsigned n=0;
        for(unsigned j=0;j<2;j++){
            unsigned c=(unsigned char)text[i*2+j];
            if(c>='0'&&c<='9')c-='0';else if(c>='a'&&c<='f')c=c-'a'+10;else return 0;
            n=n*16+c;
        }out[i]=(uint8_t)n;
    }return 1;
}
static CohStatus sha256(void *unused,CohBytes bytes,uint8_t out[32]){
    SHA256_CTX state;(void)unused;
    return SHA256_Init(&state)&&SHA256_Update(&state,bytes.data,bytes.size)&&SHA256_Final(out,&state)?COH_OK:COH_STATE;
}
int main(int argc,char **argv){
    CHECK(argc==6);char *end;errno=0;unsigned long generation=strtoul(argv[2],&end,10);
    CHECK(!errno&&!*end&&generation&&generation<=UINT32_MAX);
    CohCatalogBinding binding={0};binding.owner_generation=1;binding.catalog_generation=(uint32_t)generation;binding.asset_generation=1;
    CHECK(hex(argv[3],binding.catalog_sha256)&&hex(argv[4],binding.source_sha256)&&hex(argv[5],binding.inventory_sha256));
    FILE *file=fopen(argv[1],"rb");CHECK(file);CHECK(!fseek(file,0,SEEK_END));long length=ftell(file);
    CHECK(length>=48&&length<=COH_CATALOG_INPUT_MAX&&!fseek(file,0,SEEK_SET));
    uint8_t *raw=malloc((size_t)length);CHECK(raw);CHECK(fread(raw,1,(size_t)length,file)==(size_t)length&&fgetc(file)==EOF&&!ferror(file));CHECK(!fclose(file));
    CohCatalogOwner *owner=NULL;CohCatalogOwnerReport owner_report;
    CohCatalogOwnerBudget owner_budget={COH_CATALOG_MEMORY_MAX,COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,HARNESS_RESERVE+PROVIDER_RESERVE};
    CohCatalogDigest provider={NULL,sha256};peak_bytes=live_bytes;
    CHECK(coh_catalog_owner_create(NULL,(CohBytes){raw,(size_t)length},&binding,&owner_budget,&provider,&owner,&owner_report)==COH_OK);
    size_t owner_creation_payload_peak=peak_bytes;
    CHECK(owner_report.peak_aggregate_bytes==peak_bytes+COH_CATALOG_WALK_STACK_RESERVE+HARNESS_RESERVE+PROVIDER_RESERVE);
    size_t owner_owned=coh_catalog_owner_owned_bytes(owner);CohBytes span;
    CHECK(coh_catalog_owner_bytes(owner,&span)==COH_OK&&span.data!=raw&&span.size==(size_t)length);
    /* The compact borrower owns a retained pin. Drop the original creator pin
     * and external source buffer before preparing the compact candidate. */
    CHECK(coh_catalog_owner_retain(owner)==COH_OK);coh_catalog_owner_release(owner);
    memset(raw,0,(size_t)length);free(raw);raw=NULL;
    CHECK(live_bytes==owner_owned&&owner_owned>=span.size);
    size_t owner_extra=owner_owned-span.size;
    CohSgCompactBinding compact_binding={0};compact_binding.generation=1;
    compact_binding.catalog_generation=binding.catalog_generation;compact_binding.asset_generation=binding.asset_generation;
    memcpy(compact_binding.catalog_sha256,binding.catalog_sha256,32);memcpy(compact_binding.source_sha256,binding.source_sha256,32);
    CohSgCompactBudget compact_budget={COH_SG_TRANSACTION_MAX,owner_extra+HARNESS_RESERVE};
    CohSgCompactAudit audit;memset(&audit,0xa5,sizeof(audit));peak_bytes=live_bytes;
    CHECK(coh_sg_compact_audit(span,&compact_binding,&compact_budget,NULL,&audit)==COH_NOT_FOUND);
    size_t composed_payload_peak=peak_bytes;
    CHECK(live_bytes==owner_owned&&audit.references_checked==130314&&audit.missing_references==7&&audit.missing_stored==7&&!audit.diagnostics_truncated);
    CHECK(!audit.complete_name_closure&&audit.definitions_crc_verified&&!audit.references_crc_verified&&!audit.topology.roots_bound&&!audit.topology.assets_bound);
    CHECK(audit.topology.input_bytes==span.size&&audit.topology.retained_bytes==owner_extra+HARNESS_RESERVE+sizeof(audit));
    CHECK(audit.topology.aggregate_peak_bytes==peak_bytes+audit.topology.stack_reserve+HARNESS_RESERVE+sizeof(audit));
    CHECK(audit.topology.aggregate_peak_bytes==owner_owned+audit.topology.owned_bytes+audit.topology.peak_record_bytes+audit.topology.stack_reserve+HARNESS_RESERVE+sizeof(audit));
    const struct {uint32_t file,slot,child;const char *name;} missing[]={
        {110,61,1,"_cot_warpgate_base"},{110,61,2,"_cot_warpgate_glow"},
        {376,32,1,"_mmayhem_curtain_8_01c"},{376,33,1,"_mmayhem_curtain_8_02c"},
        {376,34,1,"_mmayhem_curtain_8_03c"},{376,35,1,"_mmayhem_curtain_16_01c"},
        {376,36,1,"_mmayhem_curtain_16_02c"}};
    for(unsigned i=0;i<7;i++){
        CHECK(audit.missing[i].file==missing[i].file&&audit.missing[i].slot==missing[i].slot&&audit.missing[i].child==missing[i].child&&!strcmp(audit.missing[i].name,missing[i].name));
        CohCatalogRecordIdentity id;CHECK(coh_catalog_owner_record(owner,missing[i].file,missing[i].slot,&id)==COH_OK&&id.in_use&&!strcmp(id.name,audit.missing[i].definition_name));
    }
    /* Strict constructor must still refuse; the diagnostic path cannot turn
     * source futures into a candidate. Its output report remains untouched. */
    CohSgCompact *candidate=NULL;CohSgCompactReport strict_report,prior;memset(&strict_report,0xa5,sizeof(strict_report));memcpy(&prior,&strict_report,sizeof(prior));
    compact_budget.retained_bytes+=sizeof(audit);peak_bytes=live_bytes;
    CHECK(coh_sg_compact_build(NULL,span,&compact_binding,&compact_budget,NULL,&candidate,&strict_report)==COH_NOT_FOUND);
    CHECK(!candidate&&!memcmp(&prior,&strict_report,sizeof(prior))&&live_bytes==owner_owned);
    size_t strict_payload_peak=peak_bytes;
    /* Combined admission refuses a budget below fixed owner/input ownership,
     * without indexing caller bytes or modifying the previous audit. */
    CohSgCompactAudit before;memcpy(&before,&audit,sizeof(before));
    compact_budget.aggregate_limit=owner_extra+HARNESS_RESERVE;
    compact_budget.retained_bytes=owner_extra+HARNESS_RESERVE;
    CHECK(coh_sg_compact_audit(span,&compact_binding,&compact_budget,NULL,&audit)==COH_LIMIT&&!memcmp(&before,&audit,sizeof(audit))&&live_bytes==owner_owned);
    uint8_t after[32];CHECK(sha256(NULL,span,after)==COH_OK&&!memcmp(after,binding.catalog_sha256,32));
    coh_catalog_owner_release(owner);CHECK(!live_bytes&&!live_count);
    printf("{\"passed\":true,\"checks\":%u,\"catalog_bytes\":%zu,\"owner_owned_bytes\":%zu,\"owner_additional_bytes\":%zu,\"owner_creation_payload_peak\":%zu,\"owner_creation_accounted_peak\":%zu,\"compact_owned_bytes\":%zu,\"record_peak_bytes\":%zu,\"compact_stack_reserve\":%zu,\"audit_output_bytes\":%zu,\"harness_reserve_bytes\":%u,\"composed_payload_peak\":%zu,\"composed_accounted_peak\":%zu,\"composed_accounted_without_harness\":%zu,\"strict_refusal_payload_peak\":%zu,\"peak_native_allocations\":%zu,\"references_checked\":%u,\"missing_references\":%u,\"index_charged_once\":true,\"original_buffer_released\":true,\"all_native_allocations_released\":true,\"graph_published\":false,\"roots_bound\":false,\"assets_bound\":false,\"renderer_authorized\":false}\n",
        checks,span.size,owner_owned,owner_extra,owner_creation_payload_peak,owner_report.peak_aggregate_bytes,
        audit.topology.owned_bytes,audit.topology.peak_record_bytes,audit.topology.stack_reserve,sizeof(audit),HARNESS_RESERVE,
        composed_payload_peak,audit.topology.aggregate_peak_bytes,audit.topology.aggregate_peak_bytes-HARNESS_RESERVE,
        strict_payload_peak,peak_count,audit.references_checked,audit.missing_references);
    return 0;
}
