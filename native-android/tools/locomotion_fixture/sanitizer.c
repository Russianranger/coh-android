#include "coh_locomotion.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    FILE *f=fopen(argv[1],"rb");if(!f)return 3;
    fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);
    if(n<64||n>131072)return 4;
    unsigned char *raw=malloc((size_t)n);if(!raw)return 5;
    if(fread(raw,1,(size_t)n,f)!=(size_t)n)return 6;fclose(f);
    CohLocomotion out;
    for(size_t cut=0;cut<64;cut++) {
        unsigned char *p=malloc(cut?cut:1);if(!p)return 7;memcpy(p,raw,cut);
        if(coh_locomotion_parse(p,cut,&out)!=-1)return 8;free(p);
    }
    if(coh_locomotion_parse(raw,(size_t)n,&out))return 9;
    CohLocomotionState state;coh_locomotion_init(&state);
    for(unsigned i=0;i<20000;i++)
        if(coh_locomotion_step(&out,&state,(i/100)%2,1.f,(i/100)%2?1.4f:0.f,1.3f))return 10;
    for(size_t i=0;i<(size_t)n;i+=23) {
        unsigned char old=raw[i];raw[i]^=255;
        CohLocomotion altered;coh_locomotion_parse(raw,(size_t)n,&altered);raw[i]=old;
    }
    free(raw);return 0;
}
