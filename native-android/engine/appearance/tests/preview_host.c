#include "../coh_appearance_preview.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned rejects;
static void rejected(const uint8_t*p,size_t n){CohAppearancePreview*owner=NULL;assert(coh_appearance_preview_create((CohBytes){p,n},&owner)!=COH_OK&&!owner);rejects++;}
int main(int argc,char**argv){
 assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long end=ftell(f);assert(end>0&&end<4*1024*1024);rewind(f);size_t n=(size_t)end;uint8_t*p=malloc(n),*copy=malloc(n);assert(p&&copy&&fread(p,1,n,f)==n);fclose(f);
 CohAppearancePreview*owner=NULL;assert(coh_appearance_preview_create((CohBytes){p,n},&owner)==COH_OK&&owner);CohAppearancePreview*old=owner;assert(coh_appearance_preview_create((CohBytes){p,n},&owner)==COH_INVALID&&owner==old);rejects++;
 CohAppearancePreviewStats expected=coh_appearance_preview_stats(owner);assert(expected.parts==8&&expected.vertices==943&&expected.indices==3792&&expected.surface_uploads==0&&expected.frames==0);coh_appearance_preview_destroy(owner,0);
 for(size_t i=0;i<64;i++)rejected(p,i);
 rejected(p,n-1);rejected(NULL,n);
 const size_t offsets[]={0,8,12,16,20,24,28,32,36,40,64,68,72,76,64+16+4,64+16+8,64+16+12,64+8*1328,64+8*1328+4,64+8*1328+8,64+8*1328+12};
 for(size_t i=0;i<sizeof offsets/sizeof offsets[0];i++){memcpy(copy,p,n);memset(copy+offsets[i],0xff,4);rejected(copy,n);}
 /* Every fixed source name requires a terminating printable ASCII identity. */
 for(size_t i=16;i<16+5*256;i+=256){memcpy(copy,p,n);memset(copy+64+16+i,'x',256);rejected(copy,n);}
 for(unsigned i=0;i<64;i++){owner=NULL;assert(coh_appearance_preview_create((CohBytes){p,n},&owner)==COH_OK);CohAppearancePreviewStats current=coh_appearance_preview_stats(owner);assert(current.owned_cpu_bytes==expected.owned_cpu_bytes);coh_appearance_preview_destroy(owner,0);}
 printf("{\"passed\":true,\"negative_cases\":%u,\"create_destroy_cycles\":64,\"cpu_bytes\":%zu,\"package_bytes\":%zu,\"texture_bytes\":%zu,\"parts\":8,\"vertices\":943,\"indices\":3792,\"GL_calls_during_create\":false}\n",rejects,expected.owned_cpu_bytes,n,expected.texture_bytes);free(copy);free(p);return 0;
}
