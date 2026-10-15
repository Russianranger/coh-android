#include "support_animation.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"adapter check failed line %d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(int argc,char **argv) {
    CohBytes clips[3];unsigned char *mem[3];CohSupportAnimation *state=NULL;
    CohAnimationPose pose,expected,before;CohSupportAnimationSnapshot snap,saved;
    CHECK(argc==4);
    for(unsigned i=0;i<3;++i) {
        FILE *f=fopen(argv[i+1],"rb");long length;CHECK(f!=NULL);
        CHECK(!fseek(f,0,SEEK_END));length=ftell(f);CHECK(length>=128 && length<1024*1024);
        CHECK(!fseek(f,0,SEEK_SET));mem[i]=malloc((size_t)length);CHECK(mem[i]!=NULL);
        CHECK(fread(mem[i],1,(size_t)length,f)==(size_t)length);fclose(f);clips[i]=(CohBytes){mem[i],(size_t)length};
    }
    CHECK(coh_support_animation_create(clips,10,&state)==COH_OK && state!=NULL);
    CHECK(coh_support_animation_active_rig(state)!=NULL);
    CHECK(coh_support_animation_sample(state,1,0,&pose)==COH_OK);
    CHECK(!coh_animation_sample(coh_support_animation_active_rig(state),1,&expected));
    CHECK(!memcmp(&pose,&expected,sizeof pose));
    for(unsigned i=1;i<10000;++i) {
        if(i%13==0)CHECK(coh_support_animation_trigger(state,(i/13)%3,i)==COH_OK);
        CHECK(coh_support_animation_sample(state,(i%5)*.5f,i,&pose)==COH_OK);
        CHECK(isfinite(pose.world_rows[0][3]));
    }
    CHECK(coh_support_animation_snapshot(state,&snap)==COH_OK && snap.samples==10000 && snap.triggers>700 && snap.transitions>700);
    saved=snap;before=pose;
    CHECK(coh_support_animation_sample(state,1,9999,&pose)==COH_INVALID);
    CHECK(!memcmp(&pose,&before,sizeof pose));
    CHECK(coh_support_animation_sample(state,NAN,10000,&pose)==COH_INVALID);
    CHECK(coh_support_animation_trigger(state,3,10000)==COH_INVALID);
    CHECK(coh_support_animation_trigger(state,1,9998)==COH_INVALID);
    CHECK(coh_support_animation_snapshot(state,&snap)==COH_OK && !memcmp(&saved,&snap,sizeof snap));
    CHECK(coh_support_animation_trigger(state,0,10001)==COH_OK);
    CHECK(coh_support_animation_sample(state,1,10000,&pose)==COH_INVALID);
    CHECK(coh_support_animation_sample(state,1,10001,&pose)==COH_OK);
    /* Last pending trigger wins deterministically, including same-frame input. */
    CHECK(coh_support_animation_trigger(state,1,10002)==COH_OK);
    CHECK(coh_support_animation_trigger(state,2,10002)==COH_OK);
    CHECK(coh_support_animation_sample(state,1,10002,&pose)==COH_OK);
    CHECK(coh_support_animation_snapshot(state,&snap)==COH_OK && snap.kind==2);
    coh_support_animation_destroy(state);coh_support_animation_destroy(NULL);state=NULL;
    {CohBytes bad[3]={clips[0],clips[1],clips[2]};bad[1].size=100;
        CHECK(coh_support_animation_create(bad,10,&state)==COH_INVALID && state==NULL);}
    CHECK(coh_support_animation_create(NULL,10,&state)==COH_INVALID);
    printf("{\"checks\":%u,\"samples\":10002,\"retained_bytes\":%zu,\"borrowed_bytes\":%zu,\"per_sample_allocations\":0}\n",checks,snap.retained_bytes,snap.borrowed_bytes);
    for(unsigned i=0;i<3;++i)free(mem[i]);
    return 0;
}
