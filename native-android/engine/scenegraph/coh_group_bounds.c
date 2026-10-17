#include "coh_group_bounds.h"
#include <math.h>
#include <string.h>
static int vector_ok(const float *v) {
    return isfinite(v[0]) && isfinite(v[1]) && isfinite(v[2]);
}
static int box_ok(const float *a,const float *b) {
    return vector_ok(a) && vector_ok(b) && a[0]<=b[0] && a[1]<=b[1] && a[2]<=b[2];
}
static int bounds_ok(const CohGroupBounds *b) {
    return box_ok(b->min,b->max) && vector_ok(b->mid) && isfinite(b->radius) && b->radius>=0;
}
static void transform(const float *v,const float m[4][3],float *o) {
    int i;
    for(i=0;i<3;i++) o[i]=v[0]*m[0][i]+v[1]*m[1][i]+v[2]*m[2][i]+m[3][i];
}
static float length3(const float *v) {
    return (float)sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);
}
static int transformed(const CohGroupBoundsChild *c,float *lo,float *hi) {
    int x,y,z,i; float v[3],t[3];
    for(i=0;i<3;i++) {lo[i]=(float)8e16;hi[i]=(float)-8e16;}
    for(x=0;x<2;x++) for(y=0;y<2;y++) for(z=0;z<2;z++) {
        v[0]=x?c->bounds->max[0]:c->bounds->min[0];
        v[1]=y?c->bounds->max[1]:c->bounds->min[1];
        v[2]=z?c->bounds->max[2]:c->bounds->min[2];
        transform(v,c->matrix,t);
        if(!vector_ok(t)) return 0;
        for(i=0;i<3;i++) {if(t[i]<lo[i])lo[i]=t[i];if(t[i]>hi[i])hi[i]=t[i];}
    }
    return 1;
}
CohGroupBoundsStatus coh_group_bounds_compute(const CohGroupBoundsInput *in,CohGroupBounds *out) {
    CohGroupBounds result; size_t n; int i,j,set=0;
    float lo[3]={8e8f,8e8f,8e8f},hi[3]={-8e8f,-8e8f,-8e8f},dv[3];
    float model_radius=0,max_radius=0;
    if(!in || !out) return COH_GROUP_BOUNDS_INVALID;
    if(in->child_count>COH_GROUP_BOUNDS_MAX_CHILDREN) return COH_GROUP_BOUNDS_LIMIT;
    if(in->model_present>1 || in->has_volume>1 || in->pre_alloc>1 ||
       (in->child_count && !in->children)) return COH_GROUP_BOUNDS_INVALID;
    if(in->pre_alloc) return COH_GROUP_BOUNDS_PREALLOC;
    if(in->model_present) {
        if(!box_ok(in->model_min,in->model_max)) return COH_GROUP_BOUNDS_INVALID;
        for(i=0;i<3;i++) {lo[i]=in->model_min[i];hi[i]=in->model_max[i];dv[i]=hi[i]-lo[i];}
        model_radius=length3(dv)*0.5f;set=1;
        if(!isfinite(model_radius)) return COH_GROUP_BOUNDS_INVALID;
    }
    if(in->has_volume && (!vector_ok(in->box_scale) || in->box_scale[0]<0 ||
       in->box_scale[1]<0 || in->box_scale[2]<0)) return COH_GROUP_BOUNDS_INVALID;
    for(n=0;n<in->child_count;n++) {
        const CohGroupBoundsChild *c=&in->children[n]; float a[3],b[3],mid[3];
        if(in->cancelled && in->cancelled(in->context)) return COH_GROUP_BOUNDS_CANCELLED;
        if(!c->bounds) continue;
        if(!bounds_ok(c->bounds)) return COH_GROUP_BOUNDS_INVALID;
        for(i=0;i<4;i++) if(!vector_ok(c->matrix[i])) return COH_GROUP_BOUNDS_INVALID;
        if(!transformed(c,a,b)) return COH_GROUP_BOUNDS_INVALID;
        for(j=0;j<3;j++) if(b[j]-a[j]<c->bounds->radius*2) break;
        if(j==3) {
            transform(c->bounds->mid,c->matrix,mid);
            for(i=0;i<3;i++) {a[i]=mid[i]-c->bounds->radius;b[i]=mid[i]+c->bounds->radius;}
            if(!vector_ok(a)||!vector_ok(b)) return COH_GROUP_BOUNDS_INVALID;
        }
        for(i=0;i<3;i++) {if(a[i]<lo[i])lo[i]=a[i];if(b[i]>hi[i])hi[i]=b[i];}set=1;
    }
    if(in->has_volume) {
        for(i=0;i<3;i++) {hi[i]=in->box_scale[i]*0.5f;lo[i]=hi[i]*-1;}
        lo[1]=0;hi[1]=in->box_scale[1];set=1;
    }
    if(!set) for(i=0;i<3;i++) lo[i]=hi[i]=0;
    for(i=0;i<3;i++) {dv[i]=hi[i]-lo[i];result.min[i]=lo[i];result.max[i]=hi[i];}
    result.radius=length3(dv)*0.5f;
    for(i=0;i<3;i++) result.mid[i]=dv[i]*0.5f+lo[i];
    if(!bounds_ok(&result)) return COH_GROUP_BOUNDS_INVALID;
    if(!in->has_volume) for(n=0;n<in->child_count;n++) {
        const CohGroupBoundsChild *c=&in->children[n];float r;
        if(in->cancelled && in->cancelled(in->context)) return COH_GROUP_BOUNDS_CANCELLED;
        if(!c->bounds) continue;
        transform(c->bounds->mid,c->matrix,dv);
        for(i=0;i<3;i++) dv[i]-=result.mid[i];
        r=length3(dv)+c->bounds->radius;
        if(!isfinite(r)) return COH_GROUP_BOUNDS_INVALID;
        if(r>max_radius) max_radius=r;
    }
    if(max_radius) result.radius=max_radius;
    if(model_radius>result.radius) result.radius=model_radius;
    if(in->cancelled && in->cancelled(in->context)) return COH_GROUP_BOUNDS_CANCELLED;
    *out=result;return COH_GROUP_BOUNDS_OK;
}
