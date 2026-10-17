#include "../coh_wr_texname.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "texname_fixture.h"
static unsigned checks,compared,unsafe;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"texname line%d %s\n",__LINE__,#x);exit(1);}}while(0)
extern CohWrTexNameProjection original_texname(const CohWrTexNameInput*,int,int*);
static void compare(const char*name,const CohWrMaterialNameSwap*swaps,uint32_t count){
 CohWrTexNameInput q={name,1,swaps,count};CohWrTexNameProjection got;
 CohStatus status=coh_wr_texname_project(&q,&got);
 if(status==COH_UNSUPPORTED){unsafe++;return;}
 CHECK(status==COH_OK);
 for(int missing=0;missing<2;missing++){
  int fallback=-1;CohWrTexNameProjection expected=original_texname(&q,missing,&fallback);
  CHECK(!memcmp(&got,&expected,sizeof(got)));CHECK(fallback==(missing&&got.branch==COH_WR_TEXNAME_COMPOSITE_LOOKUP));compared++;
 }
}
int main(int argc,char**argv){
 CHECK(argc==2);
 static const char*authored[]={"a.tga","abc","abcd","abcde","abcdef","abcdefg","abcdefgh","abcdefghi","!abcdefgh.tga","!!abcdefgh.tga","abc.xyz.tga","abc.texture.tga","abc.TEXTURE.tga","abc.tga.dds","name.period.texture.tga","dir.ext/path.tga","PORTAL.tga","!PortalName.dds","verylong_portal_name.tga",".tga","!abc.tga","abcd.tga","texture_name.JPG","texture_name.dds"};
 CohWrMaterialNameSwap swaps[]={{"BAR_VERT_SIGN","first.destination.tga"},{"bar_vert_sign","second_destination"},{"ASPHALT_SQUAREMASK","!not_renormalized.texture"},{"abcdefgh","short"},{"short","do_not_chain"}};
 for(unsigned i=0;i<TEXNAME_FIXTURE_COUNT;i++)for(unsigned mode=0;mode<2;mode++)compare(texname_fixture[i],mode?swaps:NULL,mode?5:0);
 for(unsigned i=0;i<sizeof(authored)/sizeof(authored[0]);i++)for(unsigned mode=0;mode<2;mode++)compare(authored[i],mode?swaps:NULL,mode?5:0);
 CohWrTexNameInput q={NULL,0,NULL,0};CohWrTexNameProjection got;CHECK(coh_wr_texname_project(&q,&got)==COH_OK);int fallback=-1;CohWrTexNameProjection expected=original_texname(&q,1,&fallback);CHECK(!memcmp(&got,&expected,sizeof(got))&&!fallback);
 CohWrTexNameProjection sentinel;memset(&sentinel,0xa5,sizeof(sentinel));got=sentinel;
 q=(CohWrTexNameInput){"abcd.tga",1,NULL,0};CHECK(coh_wr_texname_project(&q,&got)==COH_UNSUPPORTED);CHECK(!memcmp(&got,&sentinel,sizeof(got)));
 q.name=NULL;CHECK(coh_wr_texname_project(&q,&got)==COH_INVALID);CHECK(!memcmp(&got,&sentinel,sizeof(got)));
 q.name="abcdefgh";q.swap_count=1;CHECK(coh_wr_texname_project(&q,&got)==COH_INVALID);CHECK(!memcmp(&got,&sentinel,sizeof(got)));
 q.swap_count=257;CHECK(coh_wr_texname_project(&q,&got)==COH_LIMIT);q.swap_count=0;q.texture_count=65537;CHECK(coh_wr_texname_project(&q,&got)==COH_LIMIT);
 char large[257];memset(large,'x',256);large[256]=0;q=(CohWrTexNameInput){large,1,NULL,0};CHECK(coh_wr_texname_project(&q,&got)==COH_LIMIT);CHECK(!memcmp(&got,&sentinel,sizeof(got)));
 large[128]=0;CHECK(coh_wr_texname_project(&q,&got)==COH_LIMIT);large[127]=0;CHECK(coh_wr_texname_project(&q,&got)==COH_OK);
 q.name="utf\xc3\xa9name.tga";got=sentinel;CHECK(coh_wr_texname_project(&q,&got)==COH_UNSUPPORTED);CHECK(!memcmp(&got,&sentinel,sizeof(got)));
 q=(CohWrTexNameInput){"abcdefgh",1,NULL,0};memset(&got,0,sizeof(got));strcpy(got.stripped,"abcdefgh");CohWrTexNameProjection alias_before=got;q.name=got.stripped;
 CHECK(coh_wr_texname_project(&q,&got)==COH_INVALID);CHECK(!memcmp(&got,&alias_before,sizeof(got)));
 q.name="abcdefgh";q.scene_material_swaps=(const CohWrMaterialNameSwap*)&got;q.swap_count=1;CHECK(coh_wr_texname_project(&q,&got)==COH_INVALID);CHECK(!memcmp(&got,&alias_before,sizeof(got)));
 CohWrMaterialNameSwap alias_swap={got.stripped,"replacement"};q.scene_material_swaps=&alias_swap;CHECK(coh_wr_texname_project(&q,&got)==COH_INVALID);CHECK(!memcmp(&got,&alias_before,sizeof(got)));
 alias_swap.source="abcdefgh";alias_swap.destination=got.stripped;CHECK(coh_wr_texname_project(&q,&got)==COH_INVALID);CHECK(!memcmp(&got,&alias_before,sizeof(got)));
 CHECK(coh_wr_texname_project(&q,(CohWrTexNameProjection*)&q)==COH_INVALID);CHECK(coh_wr_texname_project(NULL,&got)==COH_INVALID);CHECK(coh_wr_texname_project(&q,NULL)==COH_INVALID);
 FILE*refused=fopen(argv[1],"wb");CHECK(refused);
 for(unsigned i=0;i<TEXNAME_CAPTURED_COUNT;i++){CohWrTexNameInput candidate={texname_fixture[i],1,NULL,0};CohStatus status=coh_wr_texname_project(&candidate,&got);CHECK(status==COH_OK||status==COH_UNSUPPORTED);if(status==COH_UNSUPPORTED)CHECK(fprintf(refused,"%s\n",texname_fixture[i])>0);}
 CHECK(!fclose(refused));
 printf("{\"passed\":true,\"checks\":%u,\"original_chain_cases\":%u,\"source_unsafe_projection_refusals\":%u,\"fixture_names\":%u,\"captured_source_names\":1769,\"fixture_stash_only\":true,\"asset_generation_permit\":false,\"material_authority\":false,\"world_authority\":false}\n",checks,compared,unsafe,TEXNAME_FIXTURE_COUNT);
}
