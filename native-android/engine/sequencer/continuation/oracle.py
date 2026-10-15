"""Extract original per-bone transition routine and scalar math unchanged."""
import hashlib,re
from pathlib import Path
def extract(text,name):
    match=re.search(r'^(?:static\s+)?(?:INLINEDBG\s+)?(?:void|int|F32)\s+'+name+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not match:raise ValueError('missing original function '+name)
    start=match.start();i=text.index('{',start)+1;depth=1
    while depth:
        if text[i]=='{':depth+=1
        elif text[i]=='}':depth-=1
        i+=1
    return text[start:i]+'\n'
PREAMBLE=r'''
#include "coh_seq_playback.h"
#include <string.h>
#include <math.h>
typedef float F32;typedef float Quat[4];typedef float Vec3[3];typedef float Mat3[3][3];
#define INLINEDBG
#define quatX(q) ((q)[0])
#define quatY(q) ((q)[1])
#define quatZ(q) ((q)[2])
#define quatW(q) ((q)[3])
#define SQR(a) ((a)*(a))
#define fsqrt(a) (float)sqrt(a)
#define scaleVec4(a,s,b) do{for(int k=0;k<4;k++)(b)[k]=(a)[k]*(s);}while(0)
#define subVec3(a,b,c) do{for(int k=0;k<3;k++)(c)[k]=(a)[k]-(b)[k];}while(0)
#define addVec3(a,b,c) do{for(int k=0;k<3;k++)(c)[k]=(a)[k]+(b)[k];}while(0)
#define scaleVec3(a,s,b) do{for(int k=0;k<3;k++)(b)[k]=(a)[k]*(s);}while(0)
#define CHANGE_SINGLE 2
#define CLOSE_ENOUGH_ROT 0.0003
#define CLOSE_ENOUGH_XLATE 0.001
typedef struct {float rotations[99][4],translations[99][3];unsigned char stored[99],rb[99],tb[99];float curr_interp_frame;} SeqInst;
static float TIMESTEP;
static SeqInst ref;
static int seqIsBoneAnimationStored(SeqInst*s,int id){return s->stored[id];}
static void seqSetBoneNeedsRotationBlending(SeqInst*s,int id,int v){s->rb[id]=(unsigned char)v;}
static void seqSetBoneNeedsTranslationBlending(SeqInst*s,int id,int v){s->tb[id]=(unsigned char)v;}
static int seqBoneNeedsRotationBlending(SeqInst*s,int id){return s->rb[id];}
static int seqBoneNeedsTranslationBlending(SeqInst*s,int id){return s->tb[id];}
static void seqGetLastRotations(SeqInst*s,int id,float*out){memcpy(out,s->rotations[id],16);}
static float *seqLastTranslations(SeqInst*s,int id){return s->translations[id];}
'''
WRAPPERS=r'''
void original_reset(void){memset(&ref,0,sizeof ref);}
void original_playback(const CohAnimationRig *r,const CohAnimationPose *raw,int entry,float timestep,float interpolate,uint32_t flags,CohAnimationPose *out){
    SeqInst *seq=&ref;float percent_new;int change=0;TIMESTEP=timestep;*out=*raw;
    if(entry){seq->curr_interp_frame=0;for(int i=0;i<99;i++)seq->rb[i]=seq->tb[i]=1;}
    /* Source animPlayInst interpolation arithmetic, exact expression. */
    seq->curr_interp_frame += TIMESTEP;
    if( seq->curr_interp_frame < interpolate )
        percent_new = 1 / (1 + interpolate - seq->curr_interp_frame);
    else percent_new=1.0;
    if(!(flags&COH_SEQ_PLAYBACK_NOINTERP))for(unsigned i=0;i<r->node_count;i++){
        unsigned id=r->order[i];float *q=out->rotation[id],*p=out->position[id];
        if((seq->rb[id]||seq->tb[id])&&percent_new<1.0)
            animInterpNodeWithLastPosition(seq,id,q,p,percent_new,&change);
        memcpy(seq->rotations[id],q,16);memcpy(seq->translations[id],p,12);seq->stored[id]=1;
    }
    for(unsigned i=0;i<r->node_count;i++){
        unsigned id=r->order[i];Mat3 m;float local[12];quatToMat(out->rotation[id],m);
        for(unsigned row=0;row<3;row++){for(unsigned col=0;col<3;col++)local[row*4+col]=m[col][row];local[row*4+3]=out->position[id][row];}
        float *target=out->world_rows[id];int parent=r->parent[id];
        if(parent<0)memcpy(target,local,48);
        else {const float *a=out->world_rows[parent];for(unsigned row=0;row<3;row++){
            for(unsigned col=0;col<3;col++)target[row*4+col]=local[col]*a[row*4]+local[col+4]*a[row*4+1]+local[col+8]*a[row*4+2];
            target[row*4+3]=local[3]*a[row*4]+local[7]*a[row*4+1]+local[11]*a[row*4+2]+a[row*4+3];}}
    }
}
'''
def write(root,target):
    files={
        'quat':root/'libs/UtilitiesLib/src/utils/Quat.c',
        'math':root/'libs/UtilitiesLib/src/utils/mathutil.c',
        'mathh':root/'libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h',
        'seq':root/'Common/seq/seqanimate.c'}
    texts={k:p.read_text() for k,p in files.items()}
    pairs=[('quat','quatNormalize'),('quat','quatInterp'),('quat','quatToMat'),('math','posInterp'),('mathh','nearSameVec3Tol'),('seq','animInterpNodeWithLastPosition')]
    code=PREAMBLE;hashes={}
    for k,name in pairs:
        snippet=extract(texts[k],name);hashes[name]=hashlib.sha256(snippet.encode()).hexdigest();code+=snippet
    # Verify the adapter clock against the actual source expression before use.
    source=texts['seq'];assert 'percent_new = 1 / (1 + (F32)seq->animation.move->interpolate - seq->curr_interp_frame)' in source
    target.write_text(code+WRAPPERS)
    return {'files':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in files.values()},'unchanged_functions':hashes,'timing':'original animPlayInst percent_new expression, neutral source timestep'}
