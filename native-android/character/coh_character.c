#include "coh_character.h"
/* One translation unit deliberately reuses the unchanged qualified raw-key
 * implementation. This makes its static raw sampler available before morph
 * translation and animDelta subtraction, preserving source operation order.
 * Compile this file instead of also compiling animation/coh_animation.c. */
#include "../animation/coh_animation.c"

static float character_clamp(float v) {return v < -1.f ? -1.f : v > 1.f ? 1.f : v;}
static void character_diagonal(const float v[3],float out[12]) {
    memset(out,0,12*sizeof(float));out[0]=v[0];out[5]=v[1];out[10]=v[2];
}
/* seqregistration scaleBone is a basis post-multiply, unscaleBone a basis
 * pre-multiply. Both preserve the original local translation unchanged. */
static void character_basis_scale(float m[12],const float s[3],int pre) {
    float diag[12],result[12];character_diagonal(s,diag);
    if(pre)compose(diag,m,result);else compose(m,diag,result);
    for(unsigned r=0;r<3;r++)result[r*4+3]=m[r*4+3];
    memcpy(m,result,sizeof result);
}
static void character_local_rows(const CohCharacterMorph *m,unsigned id,const float q[4],const float p[3],float local[12]) {
    quaternion_rows(q,p,local);
    float leg=1.f+m->leg_scale,arm=1.f+m->arm_scale;
    if(id==0&&m->leg_scale) {float s[3]={1.f,1.f/(1.f+m->leg_scale_ratio*m->leg_scale),1.f};character_basis_scale(local,s,1);}
    else if(id==4) {float s[3]={1.f+m->effective_head_scales[0],1.f+m->effective_head_scales[1],1.f+m->effective_head_scales[2]};character_basis_scale(local,s,0);}
    else if((id==23||id==24)&&m->leg_scale) {float s[3]={1.f,leg,1.f};character_basis_scale(local,s,0);}
    else if((id==25||id==26)&&m->leg_scale) {float a[3]={1.f,1.f/leg,1.f},b[3]={1.f,leg,1.f};character_basis_scale(local,a,1);character_basis_scale(local,b,0);}
    else if((id==27||id==28)&&m->leg_scale) {float s[3]={1.f,1.f/leg,1.f};character_basis_scale(local,s,1);}
    else if((id==9||id==10)&&m->arm_scale) {float s[3]={arm,arm,arm};character_basis_scale(local,s,0);}
    else if((id==41||id==42)&&m->arm_scale) {float s[3]={1.f/arm,1.f/arm,1.f/arm};character_basis_scale(local,s,1);}
}
int coh_character_parse_morph(const uint8_t *p,size_t n,CohCharacterMorph *out) {
    if(!p||!out||n!=3028u||memcmp(p,"COHMOR01",8)||u32(p+8)!=1u||u32(p+12)!=256u||
       u32(p+16)!=COH_ANIMATION_BONES||u32(p+20)!=256u||u32(p+24)!=28u||u32(p+28)!=n||
       u32(p+32)!=4u||u32(p+36)||u32(p+252))return 1;
    CohCharacterMorph m={0};m.bytes=p;m.byte_count=n;m.body_type=4;
    float header[53];for(unsigned i=0;i<53;i++)header[i]=f32(p+40+i*4);
    if(!finite_array(header,53))return 1;
    memcpy(m.geom_scale,header,12);m.bone_scale=header[3];m.shoulder_scale=header[4];
    m.chest_scale=header[5];m.waist_scale=header[6];m.hip_scale=header[7];
    m.leg_scale=header[8];m.arm_scale=header[9];memcpy(m.head_scales,header+10,12);
    m.leg_scale_ratio=header[13];memcpy(m.shoulder_skinny,header+14,12);
    memcpy(m.shoulder_fat,header+17,12);memcpy(m.hip,header+20,12);memcpy(m.neck,header+23,12);
    memcpy(m.head_min,header+26,12);memcpy(m.head_max,header+29,12);memcpy(m.face_scales,header+32,84);
    for(unsigned j=0;j<3;j++)if(m.face_scales[0][j]!=m.head_scales[j])return 1; /* Original Appearance union. */
    for(unsigned j=0;j<3;j++)if(m.geom_scale[j]<=0.f||m.geom_scale[j]>32.f)return 1;
    for(unsigned j=3;j<53;j++)if(fabsf(header[j])>16.f)return 1;
    if(m.leg_scale<=-.95f||m.arm_scale<=-.95f||m.leg_scale_ratio<0.f||m.leg_scale_ratio>4.f)return 1;
    float hip_correction=1.f+(m.leg_scale_ratio*m.leg_scale);
    if(hip_correction<=.05f||hip_correction>16.f)return 1;
    for(unsigned j=0;j<3;j++) {
        m.effective_head_scales[j]=m.head_scales[j]*(m.head_scales[j]>0.f?m.head_max[j]:m.head_min[j]);
        if(1.f+m.effective_head_scales[j]<=.05f)return 1;
    }
    m.neck_scale=m.bone_scale<=0.f?m.bone_scale:0.f;
    for(unsigned id=0;id<COH_ANIMATION_BONES;id++) {
        const uint8_t *record=p+256+id*28;if(u32(record)!=id)return 1;
        for(unsigned j=0;j<3;j++) {
            float fat=f32(record+4+j*4),skinny=f32(record+16+j*4);
            if(!isfinite(fat)||!isfinite(skinny)||fat<=0.f||skinny<=0.f||fat>16.f||skinny>16.f)return 1;
            m.fat_model_scale[id][j]=fat;m.skinny_model_scale[id][j]=skinny;
            float ratio=0.f;
            if(id==1)ratio=m.waist_scale;
            else if(id>=73&&id<=78)ratio=m.face_scales[id-73+1][j];
            else if(id!=4) {
                ratio=m.bone_scale;
                if(id==2)ratio=m.chest_scale;
                else if(id==68||id==69)ratio=0.f;
            }
            ratio=character_clamp(ratio);float model=ratio<0.f?skinny:ratio>0.f?fat:1.f;
            m.bone_scales[id][j]=1.f+((model-1.f)*fabsf(ratio));
            if(!isfinite(m.bone_scales[id][j])||m.bone_scales[id][j]<=0.f)return 1;
        }
    }
    character_diagonal(m.geom_scale,m.actor_root_rows);
    if(m.leg_scale) {float s[3]={1.f,hip_correction,1.f};character_basis_scale(m.actor_root_rows,s,0);}
    if(!finite_array(m.actor_root_rows,12))return 1;
    *out=m;return 0;
}
int coh_character_sample(const CohAnimationRig *r,const CohCharacterMorph *m,float frame,CohAnimationPose *out) {
    if(!r||!m||!out||m->body_type!=4u||!isfinite(frame)||frame<0.f||frame>1000000.f||
       !r->node_count||r->node_count>COH_ANIMATION_BONES||!finite_array(m->actor_root_rows,12))return 1;
    CohAnimationPose result={0};result.frame=frame;
    for(unsigned i=0;i<r->node_count;i++) {
        unsigned id=r->order[i];if(id>=COH_ANIMATION_BONES)return 1;
        if(r->motion.tracks[id].present) {
            if(sample_track(&r->motion.tracks[id],frame,result.rotation[id],result.position[id]))return 1;
        } else {memcpy(result.rotation[id],r->base_rotation[id],16);memcpy(result.position[id],r->base_position[id],12);}
        float *p=result.position[id],dv[3]={0.f,0.f,0.f};
        if(id==5||id==6) {
            const float *source=m->shoulder_scale<=0.f?m->shoulder_skinny:m->shoulder_fat;
            float ratio=m->shoulder_scale<=0.f?-m->shoulder_scale:m->shoulder_scale;
            for(unsigned j=0;j<3;j++)dv[j]=source[j]*ratio;
            if(id==6)dv[0]*=-1.f;
        } else if(id==3||id==4) {dv[1]=-(m->neck[1]*m->neck_scale);}
        else if(id==23||id==24) {for(unsigned j=0;j<3;j++)dv[j]=m->hip[j]*m->hip_scale;if(id==24)dv[0]*=-1.f;}
        if(id==5||id==6||id==3||id==4||id==23||id==24)for(unsigned j=0;j<3;j++)p[j]+=dv[j];
        for(unsigned j=0;j<3;j++)p[j]-=r->animation_delta[id][j];
        float local[12];character_local_rows(m,id,result.rotation[id],p,local);
        int parent=r->parent[id];
        if(parent==-1)compose(m->actor_root_rows,local,result.world_rows[id]);
        else {if(parent<0||parent>=(int)COH_ANIMATION_BONES)return 1;compose(result.world_rows[parent],local,result.world_rows[id]);}
        if(!finite_array(result.world_rows[id],12)||!finite_array(p,3))return 1;
    }
    *out=result;return 0;
}
int coh_character_palette(const CohAnimationRig *r,const CohCharacterMorph *m,const CohAnimationPose *pose,
                          uint32_t socket,const uint32_t *ids,uint32_t count,float *out) {
    if(!r||!m||!pose||!ids||!out||socket>=COH_ANIMATION_BONES||r->parent[socket]==-2||
       !count||count>COH_ANIMATION_PALETTE)return 1;
    float result[COH_ANIMATION_PALETTE*12];
    for(unsigned i=0;i<count;i++) {
        unsigned id=ids[i];if(id>=COH_ANIMATION_BONES||r->parent[id]==-2||
            !finite_array(pose->world_rows[id],12)||!finite_array(m->bone_scales[id],3))return 1;
        float diag[12],local[12],scaled_local[12],*matrix=result+i*12;
        character_diagonal(m->bone_scales[id],diag);
        character_local_rows(m,id,pose->rotation[id],pose->position[id],local);
        compose(local,diag,scaled_local);
        int parent=r->parent[id];
        if(parent==-1)compose(m->actor_root_rows,scaled_local,matrix);
        else {if(parent<0||parent>=(int)COH_ANIMATION_BONES||!finite_array(pose->world_rows[parent],12))return 1;compose(pose->world_rows[parent],scaled_local,matrix);}
        float inverse[3],translation[3];for(unsigned j=0;j<3;j++)inverse[j]=-r->bind_translation[id][j];
        point(matrix,inverse,translation);for(unsigned j=0;j<3;j++)matrix[j*4+3]=translation[j];
        point(matrix,r->bind_translation[socket],translation);for(unsigned j=0;j<3;j++)matrix[j*4+3]=translation[j];
        if(!finite_array(matrix,12))return 1;
    }
    memcpy(out,result,(size_t)count*12*sizeof(float));return 0;
}
