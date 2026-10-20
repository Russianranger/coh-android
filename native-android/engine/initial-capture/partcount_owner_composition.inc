/* Synthetic candidate helper reuse only; historical C suite main is not run. */
#define main historical_owner_main_not_executed
#include "../character-dictionary/test_costume_owner.c"
#undef main
#include "coh_initial_partcount_admission.h"
int main(void){
 for(unsigned cycle=0;cycle<128;cycle++){
  build();CHECK(candidate(COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_OK);
  CohCostumeOwnerLease lease={0};CohCostumeOwnerView view;
  CHECK(coh_costume_owner_borrow(owner,&lease,&view)==COH_OK);
  CohCostumeOwnerLease copied=lease;
  CHECK(coh_costume_owner_release(&copied)==COH_STATE&&lease.owner==owner);
  CHECK(coh_costume_owner_destroy(&owner)==COH_STATE&&owner);
  for(unsigned mode=0;mode<2;mode++)for(unsigned flag=0;flag<2;flag++){
   Writer w={{0},0,mode};pack(&w,6,0);bits(&w,32,0);bits(&w,1,1);bits(&w,3,0);bits(&w,1,1);
   for(unsigned i=0;i<102;i++)bits(&w,32,0);
   size_t count_begin=w.bit;bits(&w,1,flag);if(flag)pack(&w,4,1);
   CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){w.data,(w.bit+7)/8},w.bit,mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
   CohRepReader saved=r;CohCostumePacketBinding binding={r.bytes,r.bits,mode,&w,&pins,&bpins,&provider,pins.generation};
   CohInitialCountAdmission d;unsigned alloc_before=allocations;
   CHECK(coh_initial_partcount_admission(&r,owner,&binding,&d)==COH_UNSUPPORTED);
   CHECK(!memcmp(&r,&saved,sizeof(r))&&!d.part_count&&!d.catalog_validated&&d.count_begin_bit==count_begin&&d.end_bit==w.bit);
   CHECK(d.stage==(flag?COH_INITIAL_COUNT_ADMISSION_EXPLICIT_CATALOG:COH_INITIAL_COUNT_ADMISSION_DEFAULT_CATALOG));
   CHECK(allocations==alloc_before);
   binding.generation++;CHECK(coh_initial_partcount_admission(&r,owner,&binding,&d)==COH_STATE&&!d.catalog_validated&&!d.part_count);binding.generation--;
   binding.generation_owner=NULL;CHECK(coh_initial_partcount_admission(&r,owner,&binding,&d)==COH_STATE&&!d.catalog_validated);binding.generation_owner=&provider;
   CHECK(coh_initial_partcount_admission(&r,NULL,&binding,&d)==COH_NOT_FOUND&&!d.catalog_validated);
   /* Actual opaque owner storage, full witness, dictionary and source defs
    * remain byte-for-byte unchanged after attempted output aliases. */
   uint8_t before[32],after[32];CohBytes spans[]={
    {(const uint8_t*)owner,coh_costume_owner_bytes(owner)-coh_ent_costume_dictionary_bytes(view.dictionary)},view.body_witness,
    {(const uint8_t*)view.dictionary,coh_ent_costume_dictionary_bytes(view.dictionary)},view.bodytype_definitions,{(const uint8_t*)&lease,sizeof(lease)}};
   for(unsigned i=0;i<5;i++){
    CHECK(digest(NULL,spans[i],before)==COH_OK);
    CHECK(coh_initial_partcount_admission(&r,owner,&binding,(CohInitialCountAdmission*)(void*)spans[i].data)==COH_INVALID);
    CHECK(digest(NULL,spans[i],after)==COH_OK&&!memcmp(before,after,sizeof(before)));
   }
  }
  CHECK(coh_costume_owner_retire(owner)==COH_OK);
  CHECK(!memcmp(view.body_witness.data,save_body,bn));
  CHECK(coh_costume_owner_destroy(&owner)==COH_STATE&&owner);
  CHECK(coh_costume_owner_release(&lease)==COH_OK);
  CHECK(coh_costume_owner_destroy(&owner)==COH_OK&&!owner);
 }
 CHECK(allocations==frees);
 printf("{\"checks\":%u,\"cycles\":128,\"candidate_allocations\":%u,\"candidate_frees\":%u,\"candidate_charged_peak\":%zu,\"candidate_retained_owner_bytes\":%zu,\"production_query_admissions\":0,\"parts_read\":0}\n",checks,allocations,frees,receipt.charged_peak_bytes,receipt.owner_bytes);
 return 0;
}
