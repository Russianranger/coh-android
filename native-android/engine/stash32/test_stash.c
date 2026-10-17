#include "coh_stash32.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x)do{checks++;if(!(x)){fprintf(stderr,"%d %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t size;uint32_t seed,value;}HashFixture;
typedef struct{uint32_t key,seed,value;}IntFixture;
typedef struct{uint32_t index,key;}SlotPair;
typedef struct{const uint32_t*keys;size_t count;uint32_t initial;const SlotPair*slots;size_t pair_count;uint32_t max,valid,resizes,duplicates,zeros;}TableFixture;
#include "fixtures.h"
static CohStash32IntWorkspace workspace;static CohStash32IntSnapshot output,prior;static uint32_t expected[COH_STASH32_SLOT_MAX];
int main(void){
 for(size_t n=0;n<sizeof(hashes)/sizeof(hashes[0]);n++){uint32_t out=0;CHECK(coh_stash32_string_hash((CohBytes){hashes[n].data,hashes[n].size},hashes[n].seed,&out)==COH_OK);CHECK(out==hashes[n].value);}
 for(size_t n=0;n<sizeof(integer_hashes)/sizeof(integer_hashes[0]);n++)CHECK(coh_stash32_int_hash(integer_hashes[n].key,integer_hashes[n].seed)==integer_hashes[n].value);
 for(size_t n=0;n<sizeof(tables)/sizeof(tables[0]);n++){
  const TableFixture*t=&tables[n];CHECK(coh_stash32_int_prefix(t->keys,t->count,t->initial,&workspace,&output,COH_STASH32_BUDGET_MAX,0)==COH_OK);CHECK(output.max_size==t->max&&output.valid_count==t->valid&&output.resize_count==t->resizes&&output.duplicate_count==t->duplicates&&output.zero_count==t->zeros);CHECK(output.source_hash_bits==32&&output.source_prefix_only&&!output.complete_global_dictionary&&!output.actor_authority);
  memset(expected,0,sizeof(expected));for(size_t i=0;i<t->pair_count;i++){CHECK(t->slots[i].index<t->max);expected[t->slots[i].index]=t->slots[i].key;}CHECK(!memcmp(expected,output.slots,sizeof(expected)));
  size_t exact=sizeof(workspace)+sizeof(output)+t->count*sizeof(uint32_t)+COH_STASH32_STACK_RESERVE;prior=output;CHECK(coh_stash32_int_prefix(t->keys,t->count,t->initial,&workspace,&output,exact-1,0)==COH_LIMIT);CHECK(!memcmp(&prior,&output,sizeof(output)));CHECK(coh_stash32_int_prefix(t->keys,t->count,t->initial,&workspace,&output,exact,0)==COH_OK);prior=output;CHECK(coh_stash32_int_prefix(t->keys,t->count,t->initial,&workspace,&output,COH_STASH32_BUDGET_MAX,SIZE_MAX)==COH_LIMIT);CHECK(!memcmp(&prior,&output,sizeof(output)));
 }
 uint32_t value=0xa5a5a5a5;CHECK(coh_stash32_string_hash((CohBytes){NULL,1},0,&value)==COH_INVALID&&value==0xa5a5a5a5);CHECK(coh_stash32_string_hash((CohBytes){(const uint8_t*)(uintptr_t)(UINTPTR_MAX-2),259},0,&value)==COH_INVALID);CHECK(coh_stash32_string_hash((CohBytes){(const uint8_t*)&value,4},0,&value)==COH_INVALID);CHECK(coh_stash32_string_hash((CohBytes){NULL,0},0,&value)==COH_OK);CHECK(coh_stash32_string_hash((CohBytes){hashes[0].data,260},0,&value)==COH_INVALID);
 prior=output;CHECK(coh_stash32_int_prefix(NULL,1,128,&workspace,&output,COH_STASH32_BUDGET_MAX,0)==COH_INVALID);CHECK(coh_stash32_int_prefix((const uint32_t*)&output,1,128,&workspace,&output,COH_STASH32_BUDGET_MAX,0)==COH_INVALID);CHECK(coh_stash32_int_prefix(NULL,0,7,&workspace,&output,COH_STASH32_BUDGET_MAX,0)==COH_INVALID);CHECK(coh_stash32_int_prefix((const uint32_t*)(uintptr_t)(UINTPTR_MAX-2),1,128,&workspace,&output,COH_STASH32_BUDGET_MAX,0)==COH_INVALID);CHECK(!memcmp(&prior,&output,sizeof(output)));
 printf("{\"passed\":true,\"checks\":%u,\"string_hashes\":%zu,\"integer_hashes\":%zu,\"tables\":%zu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"actor_authority\":false}\n",checks,sizeof(hashes)/sizeof(hashes[0]),sizeof(integer_hashes)/sizeof(integer_hashes[0]),sizeof(tables)/sizeof(tables[0]),sizeof(output),sizeof(workspace));return 0;
}
