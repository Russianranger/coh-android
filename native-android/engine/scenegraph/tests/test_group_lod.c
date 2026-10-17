#include "coh_group_lod.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do {checks++;if(!(x))abort();}while(0)
typedef struct LodFixture {CohGroupLodInput input;CohGroupLodState expected;} LodFixture;
#include "lod_fixtures.h"
int main(void) {
 size_t i;CohGroupLodState out,sentinel;CohGroupLodInput in={0};
 for(i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++) {
  CHECK(coh_group_lod_apply_file_defaults(&fixtures[i].input,&out)==1);
  CHECK(!memcmp(&out,&fixtures[i].expected,sizeof(out)));
 }
 memset(&sentinel,0x51,sizeof(sentinel));out=sentinel;
 CHECK(!coh_group_lod_apply_file_defaults(NULL,&out));CHECK(!coh_group_lod_apply_file_defaults(&in,NULL));
 in.prior.from_file=2;CHECK(!coh_group_lod_apply_file_defaults(&in,&out));in.prior.from_file=0;
 in.prior.near_distance=NAN;CHECK(!coh_group_lod_apply_file_defaults(&in,&out));in.prior.near_distance=0;
 in.model_present=1;in.model_max[0]=3.4e38f;CHECK(!coh_group_lod_apply_file_defaults(&in,&out));
 in.model_max[0]=-1;CHECK(!coh_group_lod_apply_file_defaults(&in,&out));in.model_max[0]=0;
 in.prior.from_file=1;in.file_scale=INFINITY;CHECK(!coh_group_lod_apply_file_defaults(&in,&out));
 CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 printf("{\"passed\":true,\"checks\":%u}\n",checks);return 0;
}
