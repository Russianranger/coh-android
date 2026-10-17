#include "../coh_wr_tex_inputs.h"
#include "../coh_wr_texname_guarded.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,hash_calls;static int fail_alloc,stop_at,polls;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"texinputs line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_calloc(size_t,size_t);void*__wrap_calloc(size_t n,size_t size){if(fail_alloc){fail_alloc=0;return NULL;}return __real_calloc(n,size);}
typedef struct{uint8_t*data;size_t size,patch;int overlay;}Source;
static CohStatus readat(void*v,uint64_t off,void*out,size_t count){Source*s=v;if(off>s->size||count>s->size-off)return COH_IO;memcpy(out,s->data+(size_t)off,count);if(s->overlay>=0){char key[6];if(s->overlay==256)memcpy(key,"box-1",6);else if(snprintf(key,sizeof(key),"t%04d",s->overlay)!=5)return COH_INVALID;for(size_t j=0;j<5;j++)if(s->patch+j>=off&&s->patch+j-off<count)((uint8_t*)out)[s->patch+j-(size_t)off]=(uint8_t)key[j];}return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;hash_calls++;SHA256(b.data,b.size,out);return COH_OK;}
static int cancel(void*v){(void)v;polls++;return stop_at&&polls==stop_at;}
static Source load(const char*path){FILE*f=fopen(path,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<1024*1024);rewind(f);Source s={calloc((size_t)n+1,1),(size_t)n,0,-1};CHECK(s.data);CHECK(fread(s.data,1,s.size,f)==s.size);CHECK(!fclose(f));return s;}
static CohAssetLoader*loader(unsigned entries){CohAssetLoader*l=NULL;CohAssetLimits b={16u<<20,14u<<20,1u<<20,1u<<20,entries,entries,entries};CHECK(coh_asset_create(&b,&l)==COH_OK);return l;}
static CohWrTexInputPin mount(CohAssetLoader*l,const char*path,Source*s){CHECK(coh_asset_mount_file(l,path,(CohAssetSource){readat,s,s->size,17})==COH_OK);CohWrTexInputPin p={{path,17},{0}};uint8_t*body=malloc(s->size);CHECK(body);CHECK(readat(s,0,body,s->size)==COH_OK);SHA256(body,s->size,p.sha256);free(body);return p;}
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put32(uint8_t*p,uint32_t v){for(unsigned k=0;k<4;k++)p[k]=(uint8_t)(v>>(k*8));}
static Source named(Source base,const char*name,unsigned alpha){size_t hs=32+strlen(name)+1,old=u32(base.data),payload=base.size-old;Source s={calloc(1,hs+payload),hs+payload,0,-1};CHECK(s.data);memcpy(s.data,base.data,32);put32(s.data,(uint32_t)hs);s.data[28]=(uint8_t)alpha;memcpy(s.data+32,name,strlen(name)+1);memcpy(s.data+hs,base.data+old,payload);return s;}
extern void original_cache_name(const char*,char[256],char[128]);
int main(int argc,char**argv){
 CHECK(argc==4);Source box=load(argv[1]),bar=load(argv[2]),trick=load(argv[3]);CHECK(box.size==43990&&bar.size==22163&&trick.size==56583);
 CohAssetLoader*l=loader(16);CohWrTexInputPin textures[]={mount(l,"data/texture_library/npcs/objects/praetorian_box/box-1.texture",&box),mount(l,"data/texture_library/world/swappables_and_decals/signs/billboard/neon/bar_vert_sign.texture",&bar)};CohWrTexInputPin raw=mount(l,"data/tricks/coh_r/buildings/cohr_shaders_brickfiller.txt",&trick);
 CohWrTexInputsRequest q={textures,&raw,2,1,17,digest,NULL};CohWrTexInputsLimits b={1u<<20,32u<<20,16u<<20,1u<<20};CohWrTexInputs*r=NULL;CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_OK);
 CohWrTexInputsReport report;CHECK(coh_wr_tex_inputs_report(r,&report)==COH_OK&&report.texture_count==2&&report.raw_trick_count==1&&report.unresolved_client_semantics==1);CohWrTexHeaderInput views[2];
 for(unsigned i=0;i<2;i++){CHECK(coh_wr_tex_inputs_header(r,i,&views[i])==COH_OK);CHECK(views[i].input_ordinal==i&&views[i].unresolved_client_semantics==1&&views[i].asset.generation==17);char directory[256],key[128];original_cache_name(views[i].original_name,directory,key);CHECK(!strcmp(directory,views[i].directory)&&!strcmp(key,views[i].basic_key));}
 CHECK(!strcmp(views[0].basic_key,"Box-1")&&!strcmp(views[1].basic_key,"Bar_vert_sign"));CHECK(views[0].cached_flags==192&&views[1].cached_flags==0&&views[1].width==128&&views[1].height==256);
 CohWrTexHeaderInput match;CHECK(coh_wr_tex_inputs_find_basic(r,"bOx-1",&match)==COH_OK&&match.input_ordinal==0);CHECK(coh_wr_tex_inputs_find_basic(r,"BAR_VERT_SIGN",&match)==COH_OK&&match.input_ordinal==1);
 CohWrTexNameInput name={"Bar_vert_sign.tga",1,NULL,0};CohWrTexNameProjection projected;CHECK(coh_wr_texname_project_guarded(&name,&projected)==COH_OK);CHECK(coh_wr_tex_inputs_find_basic(r,projected.composite_key,&match)==COH_OK&&match.input_ordinal==1&&match.unresolved_client_semantics==1);
 name.name="Box-1.tga";CHECK(coh_wr_texname_project_guarded(&name,&projected)==COH_OK);CHECK(coh_wr_tex_inputs_find_basic(r,projected.composite_key,&match)==COH_OK&&match.input_ordinal==0);
 memset(&match,0xa5,sizeof(match));CohWrTexHeaderInput untouched=match;CHECK(coh_wr_tex_inputs_find_basic(r,"asphalt_squaremask",&match)==COH_NOT_FOUND&&!memcmp(&match,&untouched,sizeof(match)));
 CohWrRawTrickInput rv;CHECK(coh_wr_tex_inputs_raw_trick(r,0,&rv)==COH_OK&&!rv.parsed&&rv.raw.size==trick.size&&!memcmp(rv.raw.data,trick.data,trick.size));CHECK(strstr((const char*)trick.data,"Texture asphalt_squaremask")!=NULL);
 CHECK(coh_wr_tex_inputs_header(r,0,(CohWrTexHeaderInput*)views[0].original_name)==COH_INVALID);CHECK(coh_wr_tex_inputs_raw_trick(r,0,(CohWrRawTrickInput*)rv.raw.data)==COH_INVALID);
 CHECK(coh_wr_tex_inputs_report(r,(CohWrTexInputsReport*)r)==COH_INVALID);CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_STATE);
 coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==3);CHECK(!strcmp(views[0].basic_key,"Box-1")&&!memcmp(rv.raw.data,trick.data,trick.size));coh_wr_tex_inputs_release(&r);CHECK(!r&&coh_asset_stats(l).pinned_blobs==0);
 CHECK(report.preparation_reserved_bytes==COH_WR_TEX_INPUTS_PREPARATION_RESERVE);unsigned calls_before=hash_calls;uint64_t reads_before=coh_asset_stats(l).reads;b.aggregate_limit=report.aggregate_reserved_bytes-report.preparation_reserved_bytes;CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_LIMIT&&!r&&hash_calls==calls_before&&coh_asset_stats(l).reads==reads_before);b.aggregate_limit=32u<<20;
 b.owned_limit=report.owned_bytes-1;CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_LIMIT&&!r);b.owned_limit=1u<<20;b.aggregate_limit=report.aggregate_reserved_bytes-1;CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_LIMIT&&!r);b.aggregate_limit=32u<<20;
 textures[1].sha256[0]^=1;CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&coh_asset_stats(l).pinned_blobs==0);textures[1].sha256[0]^=1;
 const char*old_path=textures[0].asset.path;uint64_t reads=coh_asset_stats(l).reads;
 textures[0].asset.path="data/texture_library/_ignored/box-1.texture";CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&coh_asset_stats(l).reads==reads);
 textures[0].asset.path="data/texture_library/box-1.txt";CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&coh_asset_stats(l).reads==reads);textures[0].asset.path=old_path;
 CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},(CohWrTexInputs**)&q)==COH_INVALID);
 textures[1].asset.generation=18;CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r);textures[1].asset.generation=17;
 fail_alloc=1;CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_LIMIT&&!r&&coh_asset_stats(l).pinned_blobs==0);
 for(stop_at=1;stop_at<=10;stop_at++){polls=0;CohStatus s=coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){cancel,NULL},&r);CHECK((s==COH_CANCELLED&&!r)||s==COH_OK);coh_wr_tex_inputs_release(&r);CHECK(coh_asset_stats(l).pinned_blobs==0);}stop_at=0;
 CHECK(coh_asset_destroy(&l)==COH_OK);
 l=loader(512);Source variants[256];CohWrTexInputPin pins[256];char paths[256][64];box.patch=32+strlen((const char*)box.data+32)-9;
 for(unsigned i=0;i<256;i++){variants[i]=box;variants[i].overlay=(int)(255-i);CHECK(snprintf(paths[i],sizeof(paths[i]),"data/texture_library/derived/t%04u.texture",255-i)>0);pins[i]=mount(l,paths[i],variants+i);}
 q=(CohWrTexInputsRequest){pins,NULL,256,0,17,digest,NULL};CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_OK);for(unsigned i=0;i<256;i++){char key[6];CHECK(snprintf(key,sizeof(key),"t%04u",i)==5);CHECK(coh_wr_tex_inputs_find_basic(r,key,&match)==COH_OK&&match.input_ordinal==255-i);}coh_wr_tex_inputs_release(&r);CHECK(coh_asset_stats(l).pinned_blobs==0);CHECK(coh_asset_destroy(&l)==COH_OK);
 l=loader(16);Source lower=box;lower.overlay=256;CohWrTexInputPin duplicates[]={mount(l,"data/texture_library/first/box-1.texture",&box),mount(l,"data/texture_library/second/box-1.texture",&lower)};q=(CohWrTexInputsRequest){duplicates,NULL,2,0,17,digest,NULL};CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_STATE&&!r&&coh_asset_stats(l).pinned_blobs==0);CHECK(coh_asset_destroy(&l)==COH_OK);
 l=loader(16);CohWrTexInputPin wrong_filename=mount(l,"data/texture_library/wrong-name.texture",&box);q=(CohWrTexInputsRequest){&wrong_filename,NULL,1,0,17,digest,NULL};CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&coh_asset_stats(l).pinned_blobs==0);CHECK(coh_asset_destroy(&l)==COH_OK);
 const char*bad_names[]={"texture_library/test/Box-1.dds","data/texture_library/test/Box-1.dds","texture_library/test/short","texture_library/test/utf\xc3\xa9.dds"};
 const CohStatus bad_status[]={COH_INVALID,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED};
 for(unsigned k=0;k<4;k++){Source bad=named(box,bad_names[k],k==0?2:0);l=loader(16);CohWrTexInputPin pin=mount(l,"data/texture_library/malformed.texture",&bad);q=(CohWrTexInputsRequest){&pin,NULL,1,0,17,digest,NULL};CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==bad_status[k]&&!r&&coh_asset_stats(l).pinned_blobs==0);CHECK(coh_asset_destroy(&l)==COH_OK);free(bad.data);}
 l=loader(16);CohWrTexInputPin repeated_raw[]={mount(l,"data/tricks/repeated.txt",&trick),{{"data/tricks/repeated.txt",17},{0}}};memcpy(repeated_raw[1].sha256,repeated_raw[0].sha256,32);q=(CohWrTexInputsRequest){NULL,repeated_raw,0,2,17,digest,NULL};CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_STATE&&!r&&coh_asset_stats(l).pinned_blobs==0);CHECK(coh_asset_destroy(&l)==COH_OK);
 l=loader(16);Source nul_text={(uint8_t*)"a\0b",3,0,-1};CohWrTexInputPin binary_trick=mount(l,"data/tricks/invalid.txt",&nul_text);q=(CohWrTexInputsRequest){NULL,&binary_trick,0,1,17,digest,NULL};CHECK(coh_wr_tex_inputs_build(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&coh_asset_stats(l).pinned_blobs==0);CHECK(coh_asset_destroy(&l)==COH_OK);
 free(box.data);free(bar.data);free(trick.data);
 printf("{\"passed\":true,\"checks\":%u,\"actual_cached_headers\":2,\"actual_raw_trick_files\":1,\"derived_namespace_rows\":256,\"raw_tricks_parsed\":false,\"basic_texture_created\":false,\"texbind_created\":false,\"asset_generation_permit\":false,\"material_authority\":false,\"world_authority\":false}\n",checks);
}
