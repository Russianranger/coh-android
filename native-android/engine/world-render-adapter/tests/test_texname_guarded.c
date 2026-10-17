#include "../coh_wr_texname_guarded.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "texname_fixture.h"
static unsigned checks,safe_cases,repaired_cases,captured_closed;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"guardedname line%d %s\n",__LINE__,#x);exit(1);}}while(0)
extern int original_fix_direct(const char*,char*,int);
extern int guarded_fix_direct(const char*,char*,int);
extern CohWrTexNameProjection original_texname(const CohWrTexNameInput*,int,int*);
extern CohWrTexNameProjection guarded_original_texname(const CohWrTexNameInput*,int,int*);
static void compare(const char*name,const CohWrMaterialNameSwap*swaps,uint32_t count){
 CohWrTexNameInput q={name,1,swaps,count};CohWrTexNameProjection got,strict;
 CohStatus old=coh_wr_texname_project(&q,&strict);CHECK(old==COH_OK||old==COH_UNSUPPORTED);
 CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_OK);
 if(old==COH_OK)CHECK(!memcmp(&got,&strict,sizeof(got)));
 for(int missing=0;missing<2;missing++){
  int fallback=-1;CohWrTexNameProjection corrected=guarded_original_texname(&q,missing,&fallback);
  CHECK(!memcmp(&got,&corrected,sizeof(got)));CHECK(fallback==(missing&&got.branch==COH_WR_TEXNAME_COMPOSITE_LOOKUP));
  if(old==COH_OK){CohWrTexNameProjection original=original_texname(&q,missing,&fallback);CHECK(!memcmp(&got,&original,sizeof(got)));safe_cases++;}
  else repaired_cases++;
 }
}
int main(void){
 for(unsigned n=0;n<=127;n++)for(unsigned pattern=0;pattern<4;pattern++){
  char input[128],copied[128],inplace[128],baseline[128];memset(input,'x',n);input[n]=0;
  if(pattern==1&&n>=4)memcpy(input+n-4,".tga",4);
  if(pattern==2&&n>=8)memcpy(input+n-8,".texture",8);
  if(pattern==3&&n>=8)memcpy(input+n-8,".abcdefg",8);
  int a=guarded_fix_direct(input,copied,0),b=guarded_fix_direct(input,inplace,1);CHECK(a==b&&!strcmp(copied,inplace));
  if(n<4||n>=8||input[n-4]=='.'){
   int c=original_fix_direct(input,baseline,0);CHECK(c==a&&!strcmp(copied,baseline));
   c=original_fix_direct(input,baseline,1);CHECK(c==a&&!strcmp(copied,baseline));
  }
 }

 CohWrMaterialNameSwap swaps[]={{"WHITE","qualified_white_query_only"},{"white","must_not_override"},{"Bar_vert_sign","retained_name.tga"},{"BLUE","short"},{"short","do_not_chain"}};
 for(unsigned i=0;i<TEXNAME_FIXTURE_COUNT;i++)for(unsigned mode=0;mode<2;mode++)compare(texname_fixture[i],mode?swaps:NULL,mode?5:0);
 static const char*authored[]={"abcd","abcde","abcdef","abcdefg","abc","abcdefgh",".tga","!abcd.tga","!!abcd.tga","abcd.abc.tga","abcd.abcdefg.tga","!PORTAL.tga"};
 for(unsigned i=0;i<sizeof(authored)/sizeof(authored[0]);i++)for(unsigned mode=0;mode<2;mode++)compare(authored[i],mode?swaps:NULL,mode?5:0);
 for(unsigned i=0;i<TEXNAME_CAPTURED_COUNT;i++){
  CohWrTexNameInput captured={texname_fixture[i],1,NULL,0};CohWrTexNameProjection observed;CohStatus status=coh_wr_texname_project(&captured,&observed);CHECK(status==COH_OK||status==COH_UNSUPPORTED);
  if(status==COH_UNSUPPORTED){CHECK(coh_wr_texname_project_guarded(&captured,&observed)==COH_OK);captured_closed++;}
 }
 CHECK(captured_closed==36);
 CohWrTexNameInput q={NULL,0,NULL,0};CohWrTexNameProjection got,strict;CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_OK);CHECK(coh_wr_texname_project(&q,&strict)==COH_OK&&!memcmp(&got,&strict,sizeof(got)));
 CohWrTexNameProjection sentinel;memset(&sentinel,0xa5,sizeof(sentinel));got=sentinel;
 char large[257];memset(large,'x',256);large[256]=0;q=(CohWrTexNameInput){large,1,NULL,0};CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_LIMIT&&!memcmp(&got,&sentinel,sizeof(got)));
 large[128]=0;CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_LIMIT&&!memcmp(&got,&sentinel,sizeof(got)));
 q.name="utf\xc3\xa9name.tga";CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_UNSUPPORTED&&!memcmp(&got,&sentinel,sizeof(got)));
 q.name=NULL;CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_INVALID&&!memcmp(&got,&sentinel,sizeof(got)));
 q.name="white.tga";q.swap_count=1;CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_INVALID&&!memcmp(&got,&sentinel,sizeof(got)));
 q=(CohWrTexNameInput){"abcdefgh",1,NULL,0};memset(&got,0,sizeof(got));strcpy(got.stripped,"abcdefgh");CohWrTexNameProjection alias_before=got;q.name=got.stripped;
 CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_INVALID&&!memcmp(&got,&alias_before,sizeof(got)));
 q.name="abcdefgh";q.scene_material_swaps=(const CohWrMaterialNameSwap*)&got;q.swap_count=1;CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_INVALID&&!memcmp(&got,&alias_before,sizeof(got)));
 CohWrMaterialNameSwap alias_swap={got.stripped,"replacement"};q.scene_material_swaps=&alias_swap;CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_INVALID&&!memcmp(&got,&alias_before,sizeof(got)));
 alias_swap.source="abcdefgh";alias_swap.destination=got.stripped;CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_INVALID&&!memcmp(&got,&alias_before,sizeof(got)));
 alias_swap.source=NULL;alias_swap.destination="replacement";CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_INVALID&&!memcmp(&got,&alias_before,sizeof(got)));
 alias_swap.source="abcdefgh";alias_swap.destination=NULL;CHECK(coh_wr_texname_project_guarded(&q,&got)==COH_INVALID&&!memcmp(&got,&alias_before,sizeof(got)));
 CHECK(coh_wr_texname_project_guarded(&q,(CohWrTexNameProjection*)&q)==COH_INVALID);CHECK(coh_wr_texname_project_guarded(NULL,&got)==COH_INVALID);CHECK(coh_wr_texname_project_guarded(&q,NULL)==COH_INVALID);
 printf("{\"passed\":true,\"checks\":%u,\"safe_unchanged_source_cases\":%u,\"corrected_source_cases\":%u,\"captured_short_keys_closed\":%u,\"direct_copy_inplace_cases\":512,\"strict_default_unchanged\":true,\"fixture_stash_only\":true,\"asset_generation_permit\":false,\"material_authority\":false,\"world_authority\":false}\n",checks,safe_cases,repaired_cases,captured_closed);
}
