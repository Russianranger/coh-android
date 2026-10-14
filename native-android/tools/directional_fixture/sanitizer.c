#include "coh_locomotion.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    FILE *f=fopen(argv[1],"rb");if(!f)return 3;
    fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);
    if(n<128||n>524288)return 4;
    unsigned char *raw=malloc((size_t)n);if(!raw)return 5;
    if(fread(raw,1,(size_t)n,f)!=(size_t)n)return 6;
    fclose(f);CohLocomotion out;
    for(size_t cut=0;cut<128;cut++) {
        unsigned char *p=malloc(cut?cut:1);if(!p)return 7;
        memcpy(p,raw,cut);if(coh_locomotion_parse(p,cut,&out)!=-1)return 8;free(p);
    }
    if(coh_locomotion_parse(raw,(size_t)n,&out))return 9;
    f=fopen(argv[2],"rb");if(!f)return 10;
    unsigned char morph_bytes[3028];if(fread(morph_bytes,1,sizeof morph_bytes,f)!=sizeof morph_bytes)return 11;
    fclose(f);CohCharacterMorph morph;if(coh_character_parse_morph(morph_bytes,sizeof morph_bytes,&morph))return 12;
    CohLocomotionState state;coh_locomotion_init(&state);CohLocomotionBlend blend;coh_locomotion_blend_init(&blend);
    unsigned masks[9]={0,1,2,4,8,5,9,6,10};
    for(unsigned i=0;i<20000;i++) {
        unsigned mask=masks[(i/15)%9];float distance=(i/100)%2?1.4f:0.f;CohAnimationPose pose;
        if(coh_locomotion_step_directional(&out,&state,mask,1.f,distance,1.3f))return 13;
        if(coh_locomotion_sample_directional(&out,&state,&morph,1.f,&blend,&pose))return 14;
        if(i%70==0)coh_locomotion_blend_init(&blend);
    }
    for(size_t i=0;i<(size_t)n;i+=23) {
        unsigned char old=raw[i];raw[i]^=255;CohLocomotion altered;
        coh_locomotion_parse(raw,(size_t)n,&altered);raw[i]=old;
    }
    free(raw);return 0;
}
