#include "coh_group_bounds.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static unsigned checks;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"line %d\n",__LINE__);abort();}}while(0)
static int cancel(void *p){int *n=p;return --*n<=0;}
typedef struct BoundsFixture {
 unsigned model_present,has_volume;float model_min[3],model_max[3],box_scale[3];size_t child_count;
 struct {unsigned present;CohGroupBounds bounds;float matrix[4][3];} children[8];CohGroupBounds expected;
} BoundsFixture;
static CohGroupBounds out;
#include "fixtures.h"
int main(void){
 CohGroupBounds sentinel;CohGroupBoundsInput in={0};CohGroupBoundsChild c={0};CohGroupBounds child={0};int n;
 memset(&sentinel,0x52,sizeof(sentinel));out=sentinel;
 {size_t f,k;for(f=0;f<sizeof(fixtures)/sizeof(fixtures[0]);f++) {
 const BoundsFixture *v=&fixtures[f];CohGroupBoundsInput input={0};CohGroupBoundsChild children[8];
 input.model_present=v->model_present;input.has_volume=v->has_volume;input.child_count=v->child_count;input.children=children;
 memcpy(input.model_min,v->model_min,sizeof(input.model_min));memcpy(input.model_max,v->model_max,sizeof(input.model_max));memcpy(input.box_scale,v->box_scale,sizeof(input.box_scale));
 for(k=0;k<input.child_count;k++){children[k].bounds=v->children[k].present?&v->children[k].bounds:NULL;memcpy(children[k].matrix,v->children[k].matrix,sizeof(children[k].matrix));}
 CHECK(coh_group_bounds_compute(&input,&out)==0);CHECK(!memcmp(&out,&v->expected,sizeof(out)));
 }}
 out=sentinel;CHECK(coh_group_bounds_compute(NULL,&out)==COH_GROUP_BOUNDS_INVALID);CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 CHECK(coh_group_bounds_compute(&in,NULL)==COH_GROUP_BOUNDS_INVALID);
 in.pre_alloc=1;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_PREALLOC);in.pre_alloc=0;
 in.child_count=COH_GROUP_BOUNDS_MAX_CHILDREN+1u;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_LIMIT);
 in.child_count=1;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);in.children=&c;
 in.model_present=1;in.model_min[0]=NAN;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);
 in.model_min[0]=0;in.model_max[0]=INFINITY;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);
 in.model_max[0]=3.4e38f;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);
 in.model_max[0]=0;in.has_volume=1;in.box_scale[2]=-1;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);in.box_scale[2]=0;
 in.cancelled=cancel;in.context=&n;n=1;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_CANCELLED);
 n=2;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_CANCELLED);CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 in.cancelled=NULL;in.has_volume=0;in.model_present=0;c.bounds=&child;
 child.radius=-1;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);child.radius=0;
 child.min[0]=1;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);child.min[0]=0;
 c.matrix[1][2]=NAN;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);c.matrix[1][2]=0;
 child.mid[0]=INFINITY;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_INVALID);child.mid[0]=0;
 CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 in.cancelled=cancel;in.context=&n;n=2;CHECK(coh_group_bounds_compute(&in,&out)==COH_GROUP_BOUNDS_CANCELLED);CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 printf("{\"passed\":true,\"checks\":%u,\"heap_bytes\":0}\n",checks);return 0;
}
