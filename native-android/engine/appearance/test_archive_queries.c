#define _POSIX_C_SOURCE 200809L
#include "../assets/coh_asset_zip.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static FILE *input;static uint64_t length,reads,largest;
static CohStatus read_source(void*ctx,uint64_t offset,void*dst,size_t bytes){(void)ctx;assert(bytes<=65557);if(bytes>largest)largest=bytes;if(offset>length||bytes>length-offset||fseeko(input,(off_t)offset,SEEK_SET)||fread(dst,1,bytes,input)!=bytes)return COH_IO;reads++;return COH_OK;}
int main(int argc,char**argv){
 assert(argc==2);input=fopen(argv[1],"rb");assert(input&&!fseeko(input,0,SEEK_END));length=(uint64_t)ftello(input);
 CohAssetSource source={read_source,NULL,length,1};CohAssetZip *zip=NULL;
 CohAssetZipMember old={"data/player_library/v_huge_spadr.geo",1500000};
 assert(coh_asset_zip_open(source,&old,1,(CohCancel){0},&zip)==COH_INVALID&&!zip);
 CohAssetZipQuery want[]={{"DATA/PLAYER_LIBRARY/V_HUGE_SPADR.GEO",0,COH_ZIP_QUERY_PATH},{"Chest_Stripe_1",0,COH_ZIP_QUERY_TEXTURE},{"data/player_library/missing.geo",0,COH_ZIP_QUERY_PATH},{"Face_V_Helmet_Robotic_01",0,COH_ZIP_QUERY_TEXTURE},{"MASK_Reference",0,COH_ZIP_QUERY_TEXTURE}};
 assert(coh_asset_zip_open_queries(source,want,5,(CohCancel){0},&zip)==COH_OK&&zip);
 const char *path=NULL;uint32_t bytes=0,matches=0;
 assert(coh_asset_zip_query(zip,0,&path,&bytes,&matches)==COH_OK&&bytes==1500000&&matches==1&&!strcmp(path,"data/player_library/v_huge_spadr.geo"));
 unsigned char*body=malloc(bytes);assert(body);memset(body,0xa5,bytes);
 assert(coh_asset_zip_read(zip,0,body,bytes-1)==COH_INVALID&&body[0]==0xa5);
 assert(coh_asset_zip_read(zip,0,body,bytes)==COH_OK);
 for(uint32_t i=0;i<bytes;i++)assert(body[i]==(unsigned char)(i%251));
 assert(coh_asset_zip_read(zip,0,zip,bytes)==COH_INVALID);
 assert(coh_asset_zip_query(zip,1,&path,&bytes,&matches)==COH_OK&&bytes==3&&matches==2&&!strcmp(path,"data/texture_library/first/chest_stripe_1.texture"));
 unsigned char texture[3]={0};assert(coh_asset_zip_read(zip,1,texture,sizeof texture)==COH_OK&&!memcmp(texture,"one",3));
 assert(coh_asset_zip_query(zip,3,&path,&bytes,&matches)==COH_OK&&bytes==4&&matches==2&&!strcmp(path,"texture_library/v_players/avatar/male/face/helmets/face_v_helmet_robotic_01.texture"));
 unsigned char face[4];assert(coh_asset_zip_read(zip,3,face,4)==COH_OK&&!memcmp(face,"face",4));
 assert(coh_asset_zip_query(zip,4,&path,&bytes,&matches)==COH_OK&&bytes==4&&matches==1&&!strcmp(path,"ASSETS/Texture_Library/Other/MaSk_ReFeReNcE.texture"));
 const char*saved=path;uint32_t saved_bytes=bytes,saved_matches=matches;
 assert(coh_asset_zip_query(zip,2,&path,&bytes,&matches)==COH_NOT_FOUND&&path==saved&&bytes==saved_bytes&&matches==saved_matches);
 assert(coh_asset_zip_query(zip,0,(const char**)zip,&bytes,&matches)==COH_INVALID);
 assert(coh_asset_zip_query(zip,0,&path,&bytes,&bytes)==COH_INVALID);
 CohAssetZipStats stats=coh_asset_zip_stats(zip);assert(stats.owned_bytes==coh_asset_zip_allocation_bytes(5)&&stats.decoded_bytes==1500007);
 coh_asset_zip_free(zip);zip=NULL;free(body);
 CohAssetZipMember small={"data/texture_library/first/chest_stripe_1.texture",3};
 assert(coh_asset_zip_open(source,&small,1,(CohCancel){0},&zip)==COH_OK);
 assert(coh_asset_zip_read(zip,0,texture,sizeof texture)==COH_OK&&!memcmp(texture,"one",3));
 coh_asset_zip_free(zip);zip=NULL;
 want[0].bytes=1499999;assert(coh_asset_zip_open_queries(source,want,5,(CohCancel){0},&zip)==COH_INVALID&&!zip);
 want[0].bytes=0;want[0].kind=2;assert(coh_asset_zip_open_queries(source,want,5,(CohCancel){0},&zip)==COH_INVALID&&!zip);
 fclose(input);printf("{\"passed\":true,\"decoded_body_bytes\":1500000,\"checks\":1500015,\"world_1MiB_unchanged\":true,\"first_spelling_preserved\":true,\"duplicate_count\":2,\"largest_read\":%llu,\"reads\":%llu}\n",(unsigned long long)largest,(unsigned long long)reads);return 0;
}
