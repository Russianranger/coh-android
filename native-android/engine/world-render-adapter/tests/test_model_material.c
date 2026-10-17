/* Private constant/alias controls compile exact native production bytes. */
#include "../coh_wr_model_material.c"
#include "../coh_wr_texopt.h"
#include "../coh_wr_trick.h"
#include "model-policy-fixtures.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
static unsigned checks,cases,allocations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"ModelPolicy line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);
void*__wrap_malloc(size_t n){allocations++;return __real_malloc(n);}void*__wrap_calloc(size_t n,size_t s){allocations++;return __real_calloc(n,s);}
extern CohWrModelMaterialProjection original_model_project(const CohWrModelMaterialInput*);extern uint32_t original_model_constant(const char*);
static CohWrModelMaterialProjection compare_policy(const CohWrModelMaterialInput*q){
 CohWrModelMaterialInput saved=*q;CohWrModelMaterialPart parts[256];memcpy(parts,q->parts,q->part_count*sizeof(*parts));
 CohWrModelMaterialProjection expected=original_model_project(q),actual;memset(&actual,0x55,sizeof(actual));unsigned before=allocations;
 CHECK(coh_wr_model_material_project(q,&actual)==COH_OK);CHECK(before==allocations);CHECK(!memcmp(&saved,q,sizeof(saved))&&!memcmp(parts,q->parts,q->part_count*sizeof(*parts)));
 if(memcmp(&expected,&actual,sizeof(actual))){fprintf(stderr,"case%u model%s parts%u nativeflags%x sourceflags%x sourcepart%d/%x nativepart%d/%x\n",cases,q->model_name,q->part_count,actual.model_flags,expected.model_flags,expected.parts[0].shader,expected.parts[0].bits,actual.parts[0].shader,actual.parts[0].bits);}
 CHECK(!memcmp(&expected,&actual,sizeof(actual)));cases++;return actual;
}
static void refuse(const CohWrModelMaterialInput*q){CohWrModelMaterialProjection old,out;memset(&old,0x66,sizeof(old));out=old;unsigned before=allocations;CHECK(coh_wr_model_material_project(q,&out)==COH_INVALID&&!memcmp(&old,&out,sizeof(old))&&allocations==before);}
static CohWrModelMaterialPart part(int shader){CohWrModelMaterialPart p={0};p.name="selected_bind_fixture";p.blend=(CohWrModelBlend){shader,0};p.layer_present_mask=2047;return p;}
typedef struct{uint8_t*data;size_t size;}Source;
static Source readfile(const char*path,size_t expected){FILE*f=fopen(path,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&(size_t)n==expected);rewind(f);Source s={malloc((size_t)n),(size_t)n};CHECK(s.data&&fread(s.data,1,s.size,f)==s.size&&!fclose(f));return s;}
static CohStatus readat(void*v,uint64_t off,void*out,size_t n){Source*s=v;if(off>s->size||n>s->size-off)return COH_IO;memcpy(out,s->data+(size_t)off,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
int main(int argc,char**argv){
 CHECK(argc==3);
#include "model-policy-constant-checks.h"
 CohWrModelMaterialPart parts[256];parts[0]=part(0);parts[1]=part(1);CohWrModelMaterialInput q={"world_policy_fixture",parts,2,0,0,0,0,0,1,0,0};
 const uint32_t alpha[]={0,1,2,8,64,256,2047,16};const uint32_t bits[]={0,16,32,32768,65535};
 for(unsigned caps=0;caps<2;caps++)for(unsigned water=0;water<5;water++)for(unsigned a=0;a<10;a++)for(unsigned b=0;b<10;b++)for(unsigned variant=0;variant<32;variant++){
  parts[0]=part((int)a);parts[1]=part((int)b);q.bumpmaps_enabled=caps;q.water_mode=water;q.normals_present=variant&1;q.bone_info_present=(variant>>1)&1;q.model_name=variant&4?"GEO_Eyes_PolicyFixture":"world_policy_fixture";
  q.selected_trick_present=1;q.trick_flags1=(variant&8?TRICK_ADDITIVE:0)|(variant&16?TRICK_ALPHACUTOUT:0);q.trick_flags2=0;q.trick_model_flags=(variant&2?OBJ_FORCEOPAQUE:0)|(variant&4?OBJ_ALLOW_MULTISPLIT:0)|(variant&8?OBJ_TREEDRAW:0)|(variant&16?OBJ_WORLDFX:0);
  for(unsigned j=0;j<2;j++){parts[j].layer_alpha_mask=alpha[(variant+j)%8];parts[j].mask_is_exact_white=(variant+j)&1;parts[j].blend.bits=bits[(variant+j)%5];parts[j].texopt_present=1;parts[j].texopt_flags=(variant&1?TEXOPT_NORANDOMADDGLOW:0)|(variant&2?TEXOPT_ALWAYSADDGLOW:0)|(variant&4?TEXOPT_FALLBACKFORCEOPAQUE:0);parts[j].texopt_model_flags=variant&8?OBJ_FANCYWATER:0;parts[j].multiply1_reflect=(variant>>4)&1;parts[j].is_fallback=(variant>>2)&1;}
  compare_policy(&q);
 }
 /* Policy facts independent of caller material allocation or namespace. */
 parts[0]=part(0);parts[1]=part(3);q=(CohWrModelMaterialInput){"world",parts,2,0,0,0,0,0,1,1,0};CohWrModelMaterialProjection out=compare_policy(&q);CHECK(out.parts[0].shader==3&&out.parts[1].shader==3&&(out.trick_flags2&TRICK2_HASADDGLOW));
 parts[0]=part(2);parts[1]=part(2);parts[0].blend.bits=16;parts[1].blend.bits=32;out=compare_policy(&q);CHECK(out.common_blend.shader==2&&out.common_blend.bits==16&&out.parts[1].bits==32);
 parts[0]=part(0);parts[1]=part(0);parts[0].name="ClearAlpha_something";parts[1].name="INVISIBLE";out=compare_policy(&q);CHECK(out.model_flags&OBJ_HIDE);parts[1].name="churn_col_alpha_01";compare_policy(&q);parts[1].name="invisible_suffix";out=compare_policy(&q);CHECK(!(out.model_flags&OBJ_HIDE));
 parts[0]=part(1);parts[1]=part(2);q.selected_trick_present=1;q.trick_model_flags=OBJ_FORCEOPAQUE;out=compare_policy(&q);CHECK(out.parts[0].shader==2&&out.common_blend.shader==0);
 q.trick_model_flags=0;q.trick_flags1=TRICK_SUBTRACTIVE;out=compare_policy(&q);CHECK((out.model_flags&(OBJ_ALPHASORT|OBJ_ALPHASORTALL))==(OBJ_ALPHASORT|OBJ_ALPHASORTALL));
 q.trick_flags1=TRICK_ALPHACUTOUT;out=compare_policy(&q);CHECK((out.model_flags&(OBJ_FORCEOPAQUE|OBJ_ALLOW_MULTISPLIT))==(OBJ_FORCEOPAQUE|OBJ_ALLOW_MULTISPLIT));
 q.trick_flags1=0;q.trick_flags2=1u<<31;q.trick_model_flags=1u<<31;out=compare_policy(&q);CHECK(out.trick_flags2&(1u<<31));CHECK(out.model_flags&(1u<<31));
 q=(CohWrModelMaterialInput){"world",parts,1,0,0,0,0,0,1,1,0};parts[0]=part(8);parts[0].layer_alpha_mask=1u<<8;parts[0].mask_is_exact_white=1;out=compare_policy(&q);CHECK(!(out.model_flags&OBJ_ALPHASORT));parts[0].mask_is_exact_white=0;out=compare_policy(&q);CHECK(out.model_flags&OBJ_ALPHASORT);parts[0].mask_is_exact_white=1;parts[0].layer_alpha_mask=1u<<3;out=compare_policy(&q);CHECK(out.model_flags&OBJ_ALPHASORT);
 parts[0]=part(1);parts[0].layer_alpha_mask=1;parts[0].texopt_present=1;parts[0].texopt_flags=TEXOPT_FALLBACKFORCEOPAQUE;parts[0].is_fallback=1;out=compare_policy(&q);CHECK(!(out.model_flags&OBJ_ALPHASORT));parts[0].is_fallback=0;out=compare_policy(&q);CHECK(out.model_flags&OBJ_ALPHASORT);
 for(unsigned shader=0;shader<10;shader++){parts[0]=part((int)shader);out=compare_policy(&q);CHECK(out.parts[0].shader==(shader? (int)shader:1));CHECK(out.unrepresented_shader_mask==(shader>=4?1u<<shader:0));}
 q.model_name="GEO_Eyes_Fixture";parts[0]=part(0);parts[0].texopt_present=1;parts[0].texopt_model_flags=OBJ_WORLDFX;out=compare_policy(&q);CHECK(out.parts[0].shader==2&&(out.trick_flags1&TRICK_DOUBLESIDED));
 /* Every layer-alpha combination, both exact white-mask identities, and all
  * shader pairs; force-opaque exercises merged-first-part alpha classification. */
 q=(CohWrModelMaterialInput){"world",parts,2,1,0,0,OBJ_FORCEOPAQUE,0,1,1,0};
 for(unsigned shader=0;shader<10;shader++)for(unsigned mask=0;mask<2048;mask++)for(unsigned white_mask=0;white_mask<2;white_mask++){
  parts[0]=part((int)shader);parts[1]=part(8);parts[0].layer_alpha_mask=mask;parts[0].mask_is_exact_white=white_mask;parts[1].mask_is_exact_white=white_mask;compare_policy(&q);
 }
 /* Captured model names/ordered partition counts and SERVER Trick scalar fields
  * are real observations. All TexBind/normal/capability selections below are
  * explicit derived policy fixtures, never authentic current CLIENT bindings. */
 for(unsigned i=0;i<sizeof(root_fixtures)/sizeof(*root_fixtures);i++){
  const RootFixture*f=&root_fixtures[i];q=(CohWrModelMaterialInput){f->name,parts,f->parts,f->trick,f->f1,f->f2,f->flags,0,1,1,0};
  for(unsigned j=0;j<f->parts;j++){parts[j]=part((int)((i+j)%10));}
  compare_policy(&q);
 }
 /* Existing bounded native dictionary owners supply actual historical values;
  * there is no model/texture association claim for these independent controls. */
 Source cache=readfile(argv[1],13537052),states=readfile(argv[2],15380);CohAssetLoader*l=NULL;CohAssetLimits al={16u<<20,15u<<20,16u<<20,16u<<20,4,4,4};CHECK(coh_asset_create(&al,&l)==COH_OK&&coh_asset_mount_file(l,"data/bin/tricks.bin",(CohAssetSource){readat,&cache,cache.size,17})==COH_OK);CohWrSurfaceStates*surface=NULL;CohWrSurfaceLimits sl={1u<<20,96u<<20,64u<<20};CHECK(coh_wr_surface_prepare((CohBytes){states.data,states.size},17,digest,NULL,&sl,(CohCancel){0},&surface)==COH_OK);CohWrTexOptCache*t=NULL;CohWrTexOptLimits tl={1u<<20,96u<<20,16u<<20,64u<<20};CHECK(coh_wr_texopt_cache_open(l,(CohAssetId){"data/bin/tricks.bin",17},digest,NULL,&tl,(CohCancel){0},&t)==COH_OK);CohWrTrickCache*tricks=NULL;CohWrTrickLimits trl={1u<<20,96u<<20,16u<<20,64u<<20};CHECK(coh_wr_trick_open(l,t,digest,NULL,&trl,(CohCancel){0},&tricks)==COH_OK);
 const unsigned ordinals[]={0,1,100,500,1000,2913,5000,14714};for(unsigned i=0;i<sizeof(ordinals)/sizeof(*ordinals);i++){
  CohWrTexOptRecord*r=NULL;CohWrTexOptView v;CHECK(coh_wr_texopt_record_create(t,ordinals[i],surface,&tl,(CohCancel){0},&r)==COH_OK&&coh_wr_texopt_record_view(r,&v)==COH_OK);parts[0]=part((int)v.blend_mode);parts[0].name=v.name;parts[0].texopt_present=1;parts[0].texopt_flags=v.flags;parts[0].texopt_model_flags=v.model_flags;parts[0].multiply1_reflect=v.multiply1_reflect;q=(CohWrModelMaterialInput){"independent_historical_TexOpt_fixture",parts,1,0,0,0,0,0,1,1,0};compare_policy(&q);coh_wr_texopt_record_release(&r);
 }
 for(unsigned i=0;i<3644;i++){CohWrTrickView v;CHECK(coh_wr_trick_numeric_projection(tricks,i,&v)==COH_OK);parts[0]=part((int)(i%10));q=(CohWrModelMaterialInput){"independent_historical_Trick_fixture",parts,1,1,v.flags1,v.flags2,v.model_flags,0,1,1,0};compare_policy(&q);}
 coh_wr_trick_release(&tricks);coh_wr_texopt_cache_release(&t);coh_wr_surface_release(&surface);coh_asset_trim(l);CHECK(!coh_asset_stats(l).pinned_blobs&&!coh_asset_stats(l).resident_bytes&&coh_asset_destroy(&l)==COH_OK);free(cache.data);free(states.data);
 q=(CohWrModelMaterialInput){"world",parts,256,0,0,0,0,0,1,1,0};for(unsigned i=0;i<256;i++)parts[i]=part((int)(i%10));out=compare_policy(&q);CHECK(out.part_count==256&&out.unrepresented_shader_mask);
 q.part_count=1;parts[0]=part(1);CohWrModelMaterialInput good=q;
 for(unsigned i=0;i<10;i++){q=good;if(i==0)q.parts=NULL;if(i==1)q.part_count=0;if(i==2)q.part_count=257;if(i==3)q.selected_trick_present=2;if(i==4)q.bone_info_present=2;if(i==5)q.normals_present=2;if(i==6)q.bumpmaps_enabled=2;if(i==7)q.water_mode=5;if(i==8)q.trick_flags1=1;if(i==9)q.model_name="\xff";refuse(&q);}
 q=good;for(unsigned i=0;i<14;i++){parts[0]=part(1);if(i==0)parts[0].name="";if(i==1)parts[0].name=NULL;if(i==2)parts[0].blend.shader=-1;if(i==3)parts[0].blend.shader=10;if(i==4)parts[0].blend.bits=65536;if(i==5)parts[0].layer_present_mask=2048;if(i==6)parts[0].layer_alpha_mask=2048;if(i==7)parts[0].layer_present_mask=0;if(i==8){parts[0].layer_present_mask=1;parts[0].layer_alpha_mask=2;}if(i==9){parts[0].mask_is_exact_white=1;parts[0].layer_present_mask=1;}if(i==10)parts[0].texopt_present=2;if(i==11)parts[0].multiply1_reflect=2;if(i==12)parts[0].is_fallback=2;if(i==13)parts[0].texopt_flags=1;refuse(&q);}
 parts[0]=part(1);char long_name[257];memset(long_name,'x',256);long_name[256]=0;q.model_name=long_name;refuse(&q);q=good;parts[0].name=long_name;refuse(&q);parts[0]=part(1);
 union{CohWrModelMaterialInput input;CohWrModelMaterialProjection output;}alias;memset(&alias,0,sizeof(alias));alias.input=good;CHECK(coh_wr_model_material_project(&alias.input,&alias.output)==COH_INVALID);
 CHECK(coh_wr_model_material_project(&good,(CohWrModelMaterialProjection*)(void*)parts)==COH_INVALID);CHECK(coh_wr_model_material_project(NULL,&out)==COH_INVALID);CHECK(coh_wr_model_material_project(&good,NULL)==COH_INVALID);
 printf("{\"passed\":true,\"checks\":%u,\"source_cases\":%u,\"actual_root_model_scalar_controls\":%zu,\"independent_historical_TexOpt_controls\":8,\"independent_historical_Trick_controls\":3644,\"current_TexBind_selection_proven\":false,\"render_material_created\":false,\"world_authority\":false}\n",checks,cases,sizeof(root_fixtures)/sizeof(*root_fixtures));return 0;
}
