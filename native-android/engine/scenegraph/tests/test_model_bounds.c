#include "coh_model_bounds.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"line%d\n",__LINE__);abort();}}while(0)
extern unsigned original_model_bounds(const CohModelBoundsTable *,const CohModelBoundsView *);
static void put(uint8_t*p,uint32_t v){for(unsigned n=0;n<4;n++)p[n]=(uint8_t)(v>>(8*n));}
static void number(uint8_t*p,float f){uint32_t v;memcpy(&v,&f,4);put(p,v);}
static size_t fixture(uint8_t *b,uint32_t version){
 memset(b,0,1024);size_t fields=version>=2&&version<=6?5u:4u;put(b+8,16);memcpy(b+fields*4,"source_fixture",15);size_t model=fields*4+16;put(b+model+136,1);size_t at=model+140;
 size_t scale=version<3?92u:version==8?72u:68u;size_t size=version<3?216u:version==4?256u:version>=7?(version==8?244u:228u):204u;
 if(version>=3)put(b+at,(uint32_t)size);
 number(b+at+4,17.25f);
 for(unsigned n=0;n<3;n++){number(b+at+scale+4*n,1.25f+n);number(b+at+scale+12+4*n,-7.5f-n);number(b+at+scale+24+4*n,9.25f+n);}
 return at+size;
}
static void refuse(CohBytes h,uint32_t version){CohModelBoundsTable t,before;memset(&t,0x51,sizeof(t));before=t;CHECK(coh_model_bounds_open(h,version,&t)!=COH_OK);CHECK(!memcmp(&t,&before,sizeof(t)));}
int main(void){uint8_t header[1024],saved[1024];uint32_t versions[]={0,2,3,4,5,7,8};unsigned original_checks=0;
 for(unsigned k=0;k<7;k++){
  size_t n=fixture(header,versions[k]);memcpy(saved,header,sizeof(header));CohModelBoundsTable t;CHECK(coh_model_bounds_open((CohBytes){header,n},versions[k],&t)==COH_OK);CHECK(t.models==1&&t.version==versions[k]);CohModelBoundsCursor cursor;CHECK(coh_model_bounds_begin(&t,&cursor)==COH_OK);CohModelBoundsView view;CHECK(coh_model_bounds_next(&cursor,&view)==COH_OK);CHECK(!strcmp(view.name,"source_fixture")&&view.disk_row==0);original_checks+=original_model_bounds(&t,&view);CohModelBoundsView before=view;CHECK(coh_model_bounds_next(&cursor,&view)==COH_NOT_FOUND&&!memcmp(&view,&before,sizeof(view)));
  uint32_t mask=999;CHECK(coh_model_bounds_compare(&view.numbers,&view.numbers,&mask)==COH_OK&&!mask);
  for(unsigned group=0;group<4;group++)for(unsigned j=0;j<(group==3?1u:3u);j++){CohModelBoundsNumbers other=view.numbers;float *a[]={other.min,other.max,other.scale,&other.radius};a[group][j]+=0.25f;CHECK(coh_model_bounds_compare(&view.numbers,&other,&mask)==COH_OK&&mask==(1u<<(3*group+j)));}
  for(size_t cut=0;cut<n;cut++)refuse((CohBytes){header,cut},versions[k]);
  number(header+t.records_offset+(versions[k]<3?104:versions[k]==8?84:80),NAN);refuse((CohBytes){header,n},versions[k]);memcpy(header,saved,sizeof(header));
  CHECK(coh_model_bounds_open((CohBytes){header,n},versions[k],(CohModelBoundsTable*)header)==COH_INVALID);CHECK(!memcmp(header,saved,sizeof(header)));
  CHECK(coh_model_bounds_begin(&t,(CohModelBoundsCursor*)&t)==COH_INVALID);CHECK(coh_model_bounds_begin(&t,&cursor)==COH_OK);CHECK(coh_model_bounds_next(&cursor,(CohModelBoundsView*)&cursor)==COH_INVALID);
 }
 refuse((CohBytes){header,fixture(header,8)},6);CohModelBoundsNumbers a={0},b={0};a.radius=-0.f;uint32_t mask=999;CHECK(coh_model_bounds_compare(&a,&b,&mask)==COH_OK&&mask==(1u<<9));a.radius=0;a.min[0]=NAN;mask=999;CHECK(coh_model_bounds_compare(&a,&b,&mask)==COH_INVALID&&mask==999);a.min[0]=0;CHECK(coh_model_bounds_compare(&a,&b,(uint32_t*)&a)==COH_INVALID);
 printf("{\"passed\":true,\"checks\":%u,\"original_copy_and_trick_checks\":%u,\"versions\":7,\"world_authority\":false}\n",checks,original_checks);return 0;}
