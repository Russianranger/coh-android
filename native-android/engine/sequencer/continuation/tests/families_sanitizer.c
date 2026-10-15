#include "coh_seq_playback.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    unsigned samples=0;
    for(int a=1;a<argc;++a) {
        FILE *f=fopen(argv[a],"rb");if(!f)return 2;
        if(fseek(f,0,SEEK_END))return 2;
        long length=ftell(f);
        if(length<128 || length>1024*1024 || fseek(f,0,SEEK_SET))return 2;
        unsigned char *mem=malloc((size_t)length);if(!mem || fread(mem,1,(size_t)length,f)!=(size_t)length)return 2;fclose(f);
        CohAnimationRig rig; if(coh_animation_parse(mem,(size_t)length,&rig))return 3;
        CohSeqPoseBinding binding={0,1,&rig};CohSeqPlayback playback;CohAnimationPose pose;
        CohSeqPlaybackEvent event[1];size_t count;CohSeqSelection selection={0};
        selection.actor_id=1;selection.rig_id=1;selection.interpolate_frames=5;
        if(coh_seq_playback_init(&playback,1,1,&binding,1,NULL,0))return 3;
        for(unsigned i=0;i<2000;++i) {
            selection.frame=rig.first_frame+(rig.last_frame-rig.first_frame)*(float)(i%100)/100.f;
            if(coh_seq_playback_sample(&playback,&selection,i/100,1,i,(CohCancel){0},&pose,event,1,&count))return 4;
            ++samples;
        }
        /* Truncated raw containers always fail without touching output. */
        for(unsigned n=0;n<128;++n)if(!coh_animation_parse(mem,n,&rig))return 5;
        free(mem);
    }
    printf("{\"authentic_family_samples\":%u,\"rig_files\":%d}\n",samples,argc-1);return 0;
}
