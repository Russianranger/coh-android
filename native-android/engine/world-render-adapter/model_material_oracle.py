"""Unchanged original model-level material policy under narrow storage/input observers."""
from pathlib import Path

def create(root,extract,constants):
 root=Path(root);base=root/'upstream/ouroboros';model=(base/'Game/src/render/model.c').read_text();state=(base/'Game/src/render/thread/rt_state.c').read_text();h=(base/'Game/src/render/thread/rt_state.h').read_text();trick=(base/'Common/seq/tricks.h').read_text();tex=(base/'Game/src/render/texEnums.h').read_text();anim=(base/'Common/seq/anim.c').read_text();animh=(base/'Common/seq/anim.h').read_text();gfx=(base/'Game/src/graphics/gfxSettings.h').read_text();caps=(base/'Game/src/render/thread/rt_init.h').read_text();texh=(base/'Game/src/render/tex.h').read_text()
 def decl(text,start,end):p=text.index(start);return text[p:text.index(end,p)+len(end)]
 code=r'''#include "coh_wr_model_material.h"
#include "coh_wr_trick_types_internal.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdbool.h>
typedef uint16_t U16;typedef int16_t S16;
'''
 for name in ['TRICK2_TEXBIAS','TRICK2_ALPHAREF','TRICK2_CASTSHADOW','TRICK2_NIGHTGLOW','TRICK2_HAS_SWAY','TRICK2_STSCROLL0','TRICK2_STSCROLL1']:
  code+='#undef '+name+'\n'
 code+=decl(trick,'enum\n{\n    TRICK_ADDITIVE','\n};')+'\n'+decl(trick,'enum {\n    TRICK2_HASADDGLOW','\n};')+'\n'
 code+=decl(h,'typedef enum BlendModeBits','} BlendModeBits;')+'\n'+decl(h,'typedef union _BlendModeType','} BlendModeType;')+'\n'
 code+=decl(tex,'typedef enum TexLayerIndex','} TexLayerIndex;')+'\n'+decl(texh,'typedef enum TexFlags','} TexFlags;')+'\n'+decl(gfx,'typedef enum OptionWater','} OptionWater;')+'\n'+decl(caps,'typedef enum GfxFeatures','} GfxFeatures;')+'\n'
 code+=r'''
#define CLIENT 1
#define INLINEDBG
static struct{unsigned features;}rdr_caps;
static struct{int waterMode;}game_state;
typedef struct{unsigned flags;}BasicTexture;
typedef struct{const char*name;BlendModeType bind_blend_mode;unsigned is_fallback_material;TexOpt*texopt;BasicTexture*tex_layers[TEXLAYER_MAX_LAYERS];}TexBind;
typedef struct VBO VBO;
typedef struct{const char*name;}GeoLoadData;
typedef struct Model{char*name;U32 flags;int tex_count;TexBind**tex_binds;BlendModeType*blend_modes;BlendModeType common_blend_mode;void*boneinfo;VBO*vbo;TrickNode*trick;GeoLoadData*gld;struct{struct{int unpacksize;}norms;}pack;struct{void*norms;}unpack;}Model;
static BasicTexture white,*white_tex=&white;
static TrickInfo*selected_trick;
static TrickInfo*trickFromObjectName(const char*name,const char*path){assert(name&&path);return selected_trick;}
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static int strnicmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){int d=(int)fold((unsigned char)a[i])-(int)fold((unsigned char)b[i]);if(d||!a[i]||!b[i])return d;}return 0;}
static int stricmp(const char*a,const char*b){size_t n=strlen(a)+1;return strnicmp(a,b,n);}
static char*strstri(const char*s,const char*k){size_t n=strlen(k);for(;*s;s++)if(!strnicmp(s,k,n))return(char*)s;return NULL;}
#define setVec3(v,a,b,c) ((v)[0]=(a),(v)[1]=(b),(v)[2]=(c))
_Static_assert(sizeof(BlendModeType)==4&&sizeof(S16)==2&&sizeof(U16)==2,"source numeric blend storage");
'''
 functions={name:extract(text,signature) for name,text,signature in [('BlendMode',state,'BlendModeType BlendMode('),('blendModeHasBump',state,'bool blendModeHasBump('),('blendModeHasDualColor',state,'bool blendModeHasDualColor('),('promoteBlendMode',state,'BlendModeType promoteBlendMode('),('modelInitTrickNodeFromName',anim,'void modelInitTrickNodeFromName('),('modelHasNorms_CLIENT',animh,'    static INLINEDBG int modelHasNorms(Model *model)'),('texNeedsAlphaSort',model,'U32 texNeedsAlphaSort('),('modelNeedsAlphaSort',model,'U32 modelNeedsAlphaSort('),('allocModelTrick',model,'TrickNode *allocModelTrick('),('modelResetFlags',model,'void modelResetFlags(')]}
 code+='\n'.join(functions.values())
 code+='\nuint32_t original_model_constant(const char*key){\n'+''.join(' if(!strcmp(key,"'+name+'"))return(uint32_t)'+name+';\n' for name in constants)+' abort();\n}\n'
 code+=r'''
/* Original function ABI is observed through bounded fixture structures/storage.
 * TexBind selection/model lookup/capability provenance are explicit inputs. */
static TexOpt opts[256];static TexBind binds[256];static BasicTexture layers[256][TEXLAYER_MAX_LAYERS];static TexBind*list[256];static BlendModeType blends[256];
CohWrModelMaterialProjection original_model_project(const CohWrModelMaterialInput*q){
 memset(opts,0,q->part_count*sizeof(*opts));memset(binds,0,q->part_count*sizeof(*binds));memset(layers,0,q->part_count*sizeof(*layers));memset(blends,0,q->part_count*sizeof(*blends));
 for(unsigned i=0;i<q->part_count;i++){
  const CohWrModelMaterialPart*p=&q->parts[i];TexBind*b=&binds[i];b->name=p->name;b->bind_blend_mode=BlendMode(p->blend.shader,p->blend.bits);b->is_fallback_material=p->is_fallback;
  if(p->texopt_present){b->texopt=&opts[i];b->texopt->flags=p->texopt_flags;b->texopt->model_flags=p->texopt_model_flags;b->texopt->scrollsScales.multiply1Reflect=p->multiply1_reflect;}
  for(unsigned j=0;j<TEXLAYER_MAX_LAYERS;j++)if(p->layer_present_mask&(1u<<j)){layers[i][j].flags=p->layer_alpha_mask&(1u<<j)?TEX_ALPHA:0;b->tex_layers[j]=j==TEXLAYER_MASK&&p->mask_is_exact_white?white_tex:&layers[i][j];}
  list[i]=b;
 }
 TrickInfo trick;memset(&trick,0,sizeof(trick));trick.model_flags=q->trick_model_flags;trick.tnode.flags1=(int)q->trick_flags1;trick.tnode.flags2=(int)q->trick_flags2;selected_trick=q->selected_trick_present?&trick:NULL;
 GeoLoadData gld={"object_library/source_policy_observer.geo"};Model model;memset(&model,0,sizeof(model));model.name=(char*)q->model_name;model.tex_count=(int)q->part_count;model.tex_binds=list;model.blend_modes=blends;model.boneinfo=q->bone_info_present?&gld:NULL;model.gld=&gld;model.pack.norms.unpacksize=q->normals_present?12:0;
 rdr_caps.features=q->bumpmaps_enabled?GFXF_BUMPMAPS:0;game_state.waterMode=(int)q->water_mode;
 modelResetFlags(&model);CohWrModelMaterialProjection out;memset(&out,0,sizeof(out));out.model_flags=model.flags;out.trick_present=model.trick!=NULL;out.trick_info_present=model.trick&&model.trick->info;out.trick_flags1=model.trick?(uint32_t)model.trick->flags1:0;out.trick_flags2=model.trick?(uint32_t)model.trick->flags2:0;out.part_count=q->part_count;out.common_blend=(CohWrModelBlend){model.common_blend_mode.shader,model.common_blend_mode.blend_bits};
 for(unsigned i=0;i<q->part_count;i++){out.parts[i]=(CohWrModelBlend){model.blend_modes[i].shader,model.blend_modes[i].blend_bits};int shader=out.parts[i].shader;if(shader<BLENDMODE_MULTIPLY||shader>BLENDMODE_ADDGLOW)out.unrepresented_shader_mask|=1u<<shader;out.nonzero_blend_bits|=out.parts[i].bits;}
 free(model.trick);return out;
}
'''
 return code,functions
