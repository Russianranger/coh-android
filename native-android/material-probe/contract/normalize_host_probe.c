#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <xmmintrin.h>
static uint32_t word(const unsigned char *p){uint32_t v;memcpy(&v,p,4);return v;}
static float scalar(const unsigned char *p){float v;memcpy(&v,p,4);return v;}
static unsigned char *load(const char*path,size_t *length){FILE*f=fopen(path,"rb");if(!f)return NULL;fseek(f,0,SEEK_END);*length=(size_t)ftell(f);rewind(f);unsigned char*b=malloc(*length);if(!b||fread(b,1,*length,f)!=*length){free(b);fclose(f);return NULL;}fclose(f);return b;}
int main(int argc,char**argv){
 if(argc!=3)return 2;
 size_t ml,pl;unsigned char*m=load(argv[1],&ml),*p=load(argv[2],&pl);if(!m||!p||ml<64||pl<64)return 3;
 if(memcmp(m,"COHMESH1",8)||memcmp(p,"COHPOSE1",8))return 4;
 uint32_t vertices=word(m+16),stride=word(m+28),offset=word(m+32),bones=word(p+24),gold=word(p+36)+bones*48;
 if(stride!=48||offset>ml||vertices>(ml-offset)/stride||gold>pl||vertices>(pl-gold)/24)return 5;
 unsigned pm=0,nm=0,rm=0;float pe=0,ne=0,re=0;uint32_t first=UINT32_MAX;float first_expected=0,first_actual=0;
 for(uint32_t v=0;v<vertices;v++){
  float normal[3];for(unsigned k=0;k<3;k++){float actual=scalar(m+offset+v*stride+k*4),expected=scalar(p+gold+v*24+k*4),d=fabsf(actual-expected);if(d>pe)pe=d;if(d>1e-4f)pm++;normal[k]=scalar(m+offset+v*stride+(k+3)*4);}
  float sq=normal[0]*normal[0]+normal[1]*normal[1];sq=sq+normal[2]*normal[2];
  float inv=_mm_cvtss_f32(_mm_rsqrt_ss(_mm_set_ss(sq)));float inv2=inv*inv;float term=.5f*sq;term=term*inv2;float correction=1.5f-term;float refined=inv*correction;
  for(unsigned k=0;k<3;k++){float expected=scalar(p+gold+v*24+(k+3)*4),actual=normal[k]*inv,after=normal[k]*refined,d=fabsf(expected-actual),rd=fabsf(expected-after);if(d>ne)ne=d;if(rd>re)re=rd;if(d>1e-4f){nm++;if(first==UINT32_MAX){first=v*3+k;first_expected=expected;first_actual=actual;}}if(rd>1e-4f)rm++;}
 }
 printf("{\"kind\":\"host-SSE-approximate-rsqrt\",\"vertices\":%u,\"position_mismatches\":%u,\"max_position_error\":%.9g,\"normal_mismatches\":%u,\"max_normal_error\":%.9g,\"refined_mismatches\":%u,\"max_refined_error\":%.9g,\"first_normal_component\":%u,\"first_expected\":%.9g,\"first_approximate\":%.9g,\"tolerance\":0.0001}\n",vertices,pm,pe,nm,ne,rm,re,first,first_expected,first_actual);
 free(m);free(p);return 0;
}
