#include "coh_wr_sampler.h"
#include <string.h>
#define BIT(n) (UINT32_C(1)<<(n))
CohStatus coh_wr_sampler_project(const CohWrSamplerSource *s,CohRenderTexture *out){
    if(!s||!out||!s->width||!s->height||s->mip_count>32||!s->available_levels)
        return COH_INVALID;
    if(s->target!=0x0de1u || (s->effective_flags&(BIT(15)|BIT(17)|BIT(23))) ||
       (s->effective_flags&UINT32_C(0xc0000000)) || s->clamp_to_edge!=1 || s->anisotropy!=1.f)
        return COH_UNSUPPORTED;
    uint32_t levels=1,w=s->width,h=s->height;
    while(w>1||h>1){w=w>1?w/2:1;h=h>1?h/2:1;levels++;}
    if(s->mip_count>levels||s->available_levels!=(s->mip_count?s->mip_count:1))return COH_INVALID;
    uint32_t f=s->effective_flags;
    int mip=!(f&BIT(16))&&s->mip_count;
    /* POINTSAMPLE selects GL_NEAREST even when original mipmap storage exists. */
    if(mip&&!(f&BIT(26))&&s->available_levels!=levels)return COH_UNSUPPORTED;
    CohRenderTexture t;memset(&t,0,sizeof(t));
    t.wrap_s=(f&BIT(6))?COH_WRAP_CLAMP:(f&BIT(9))?COH_WRAP_MIRROR:COH_WRAP_REPEAT;
    t.wrap_t=(f&BIT(7))?COH_WRAP_CLAMP:(f&BIT(10))?COH_WRAP_MIRROR:COH_WRAP_REPEAT;
    t.mag_filter=(f&BIT(26))?COH_FILTER_NEAREST:COH_FILTER_LINEAR;
    t.min_filter=(f&BIT(26))?COH_FILTER_NEAREST:mip?COH_FILTER_MIP_LINEAR:COH_FILTER_LINEAR;
    *out=t;return COH_OK;
}
