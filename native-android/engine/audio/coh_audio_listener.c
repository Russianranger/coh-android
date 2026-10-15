#include "coh_audio_listener.h"
#include <float.h>
#include <math.h>

static int finite3(CohVec3 v) { return isfinite(v.x)&&isfinite(v.y)&&isfinite(v.z); }
CohStatus coh_audio_listener_pose(CohVec3 position,CohVec3 right,CohAudioListenerPose *out) {
    if(!out||!finite3(position)||!finite3(right))return COH_INVALID;
    double x=right.x,y=right.y,z=right.z,n=sqrt(x*x+y*y+z*z);
    if(!isfinite(n)||n==0)return COH_INVALID;
    CohAudioListenerPose p={position,{(float)(x/n),(float)(y/n),(float)(z/n)}};
    *out=p;return COH_OK;
}
CohStatus coh_audio_listener_source_view(const float v[12],CohAudioListenerPose *out) {
    if(!v||!out)return COH_INVALID;
    for(unsigned i=0;i<12;i++)if(!isfinite(v[i]))return COH_INVALID;
    /* Each column is a unit orthogonal vector. The pinned source view always
     * has reflection parity -1 after rdrFixMat, independent of camera pose. */
    for(unsigned a=0;a<3;a++)for(unsigned b=a;b<3;b++) {
        double dot=0;for(unsigned r=0;r<3;r++)dot+=(double)v[a*3+r]*v[b*3+r];
        if(fabs(dot-(a==b?1.:0.))>.002)return COH_INVALID;
    }
    double det=(double)v[0]*((double)v[4]*v[8]-(double)v[5]*v[7])
              -(double)v[3]*((double)v[1]*v[8]-(double)v[2]*v[7])
              +(double)v[6]*((double)v[1]*v[5]-(double)v[2]*v[4]);
    if(fabs(det+1.)>.003)return COH_INVALID;
    float pos[3];
    for(unsigned c=0;c<3;c++) {
        double x=-((double)v[c*3]*v[9]+(double)v[c*3+1]*v[10]+(double)v[c*3+2]*v[11]);
        if(!isfinite(x)||fabs(x)>FLT_MAX)return COH_INVALID;
        pos[c]=(float)x;
    }
    return coh_audio_listener_pose((CohVec3){pos[0],pos[1],pos[2]},
                                   (CohVec3){-v[0],-v[3],-v[6]},out);
}
CohStatus coh_audio_listener_apply(CohMixer *m,const CohAudioListenerPose *pose) {
    if(!m||!pose)return COH_INVALID;
    /* Validation/normalization also protects a manually constructed pose. */
    CohAudioListenerPose valid;
    CohStatus r=coh_audio_listener_pose(pose->position,pose->right,&valid);
    return r?r:coh_mixer_listener(m,valid.position,valid.right);
}
