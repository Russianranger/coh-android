#include "coh_animation.h"
#include <float.h>
#include <math.h>
#include <string.h>
_Static_assert(sizeof(float)==4,"Animation needs binary32-sized floats");
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint16_t u16(const uint8_t *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static int32_t i32(const uint8_t *p){uint32_t v=u32(p);return v<=INT32_MAX?(int32_t)v:(int32_t)((int64_t)v-4294967296LL);}
static float f32(const uint8_t *p){uint32_t v=u32(p);float f;memcpy(&f,&v,4);return f;}
static int span(size_t n,size_t off,size_t count,size_t width){return off<=n && (!width||count<=(n-off)/width);}
static int finite_array(const float *p,size_t n){for(size_t i=0;i<n;i++)if(!isfinite(p[i]))return 0;return 1;}
static int decode_rotation(const uint8_t *p,float out[4]){
    if(p[0]>=64)return 1;
    uint32_t packed=u32(p+1),idx[3]={((packed>>24)&255)|((uint32_t)(p[0]&15)<<8),(packed>>12)&4095,packed&4095};
    unsigned missing=p[0]>>4,k=0;float q[4];float maximum=(float)(1.0/sqrtf(2.0f));
    for(unsigned i=0;i<4;i++)q[i]=i==missing?0.f:(float)(2.0*maximum*((float)idx[k++]/4096.f)-maximum);
    float s;
    if(missing==3)s=((1-q[2]*q[2])-q[1]*q[1])-q[0]*q[0];
    else if(missing==2)s=(float)(((1-q[3]*q[3])-q[1]*q[1])-q[0]*q[0]+0.001);
    else if(missing==1)s=((1-q[3]*q[3])-q[2]*q[2])-q[0]*q[0];
    else s=((1-q[3]*q[3])-q[2]*q[2])-q[1]*q[1];
    if(!isfinite(s)||s<(missing==3?-.1f:-.001f))return 1;
    if(s<0)s=0;
    q[missing]=(float)sqrt((double)s);
    if(!finite_array(q,4))return 1;
    memcpy(out,q,sizeof q);return 0;
}
static int decode_position(const CohAnimationTrack *t,uint32_t key,float out[3]){
    if(key>=t->position_keys)return 1;
    float p[3];
    if(t->flags&8){for(unsigned i=0;i<3;i++)p[i]=f32(t->position+(size_t)key*12+i*4);}
    else {for(unsigned i=0;i<3;i++){uint16_t v=u16(t->position+(size_t)key*6+i*2);int s=v<=INT16_MAX?v:(int)v-65536;p[i]=(float)(0.00003125*(float)s);}}
    if(!finite_array(p,3))return 1;
    for(unsigned i=0;i<3;i++)if(fabsf(p[i])>2000000.f)return 1;
    memcpy(out,p,sizeof p);return 0;
}
static int normalize(float q[4]){
    float m=q[0]*q[0]+q[1]*q[1]+q[2]*q[2]+q[3]*q[3];
    if(!isfinite(m)||m<=FLT_MIN)return 1;
    float inverse=1.f/(float)sqrt((double)m);
    for(unsigned i=0;i<4;i++)q[i]*=inverse;
    return !finite_array(q,4);
}
static void track_indices(uint16_t count,float frame,uint32_t *a,uint32_t *b,float *fraction){
    if(count==1){*a=*b=0;*fraction=0;return;}
    if(frame>(float)(count-1)){*a=count-1;*b=0;*fraction=0;return;}
    *a=(uint32_t)frame;*fraction=frame-(float)*a;*b=*a+1;if(*b>=count)*b=0;
}
static int sample_track(const CohAnimationTrack *t,float frame,float q[4],float p[3]){
    uint32_t a,b;float fraction,qa[4],qb[4],pa[3],pb[3];
    track_indices(t->rotation_frames,frame,&a,&b,&fraction);
    if(decode_rotation(t->rotation+(size_t)a*5,qa)||decode_rotation(t->rotation+(size_t)b*5,qb))return 1;
    float beta=1.f-fraction;float dot=qa[0]*qb[0]+qa[1]*qb[1]+qa[2]*qb[2]+qa[3]*qb[3];
    if(dot<0)fraction=-fraction;
    for(unsigned i=0;i<4;i++)q[i]=beta*qa[i]+fraction*qb[i];
    if(normalize(q))return 1;
    track_indices(t->position_frames,frame,&a,&b,&fraction);
    if(decode_position(t,a,pa)||decode_position(t,b,pb))return 1;
    for(unsigned i=0;i<3;i++)p[i]=pa[i]+(pb[i]-pa[i])*fraction;
    return !finite_array(p,3);
}
static int raw_file(const uint8_t *p,size_t n,CohAnimationFile *out){
    if(!p||n<596||n>4u*1024u*1024u)return 1;
    uint32_t header=u32(p),off=u32(p+524),count=u32(p+528),hier=u32(p+540);
    if(header<596||header>n||!count||count>COH_ANIMATION_BONES||off<596||!span(header,off,count,20)||
       !isfinite(f32(p+516))||!isfinite(f32(p+520))||f32(p+520)<0)return 1;
    if(!memchr(p+4,0,256)||!memchr(p+260,0,256))return 1;
    if(hier&&(hier<596||!span(header,hier,1,1204)||((size_t)off<(size_t)hier+1204&&(size_t)hier<(size_t)off+(size_t)count*20)))return 1;
    CohAnimationFile f={0};f.bytes=p;f.byte_count=n;f.track_count=count;
    for(uint32_t i=0;i<count;i++){
        const uint8_t *b=p+off+(size_t)i*20;uint8_t id=b[16],flags=b[17];
        if(id>=COH_ANIMATION_BONES||f.tracks[id].present||(flags!=(2|8)&&flags!=(2|16))||u16(b+18))return 1;
        CohAnimationTrack t={0};t.id=id;t.flags=flags;t.present=1;t.rotation_keys=u16(b+8);t.position_keys=u16(b+10);t.rotation_frames=u16(b+12);t.position_frames=u16(b+14);
        uint32_t ro=u32(b),po=u32(b+4),ps=flags&8?12:6;
        if(!t.rotation_keys||!t.position_keys||t.rotation_keys>COH_ANIMATION_MAX_KEYS||t.position_keys>COH_ANIMATION_MAX_KEYS||
           !t.rotation_frames||!t.position_frames||t.rotation_frames>t.rotation_keys||t.position_frames>t.position_keys||
           ro<header||po<header||!span(n,ro,t.rotation_keys,5)||!span(n,po,t.position_keys,ps))return 1;
        t.rotation=p+ro;t.position=p+po;
        float q[4],pos[3];for(uint32_t k=0;k<t.rotation_keys;k++)if(decode_rotation(t.rotation+(size_t)k*5,q))return 1;
        for(uint32_t k=0;k<t.position_keys;k++)if(decode_position(&t,k,pos))return 1;
        f.tracks[id]=t;
    }
    *out=f;return 0;
}
static int visit(CohAnimationRig *r,const uint8_t *hier,int node,int parent,unsigned depth,uint8_t seen[COH_ANIMATION_BONES]){
    if(depth>COH_ANIMATION_BONES)return 1;
    while(node!=-1){
        if(node<0||node>=(int)COH_ANIMATION_BONES||seen[node]||r->node_count>=COH_ANIMATION_BONES||!r->base.tracks[node].present)return 1;
        const uint8_t *entry=hier+4+(size_t)node*12;
        int child=i32(entry),next=i32(entry+4),id=i32(entry+8);
        if(id!=node||child< -1||child>=(int)COH_ANIMATION_BONES||next< -1||next>=(int)COH_ANIMATION_BONES)return 1;
        seen[node]=1;r->parent[node]=(int16_t)parent;r->order[r->node_count++]=(uint8_t)node;
        if(child!=-1&&visit(r,hier,child,node,depth+1,seen))return 1;
        node=next;
    }
    return 0;
}
static unsigned clean_name(unsigned c){if(c=='\\')c='/';if(c>='A'&&c<='Z')c+='a'-'A';return c;}
static int same_name(const uint8_t *a,const uint8_t *b){for(unsigned i=0;i<256;i++){if(clean_name(a[i])!=clean_name(b[i]))return 0;if(!a[i])return 1;}return 0;}
int coh_animation_parse(const uint8_t *p,size_t n,CohAnimationRig *out){
    if(!p||!out||n<128||n>8u*1024u*1024u||memcmp(p,"COHRIG01",8)||u32(p+8)!=1||u32(p+12)!=128||u32(p+44))return 1;
    for(unsigned i=64;i<128;i+=4)if(u32(p+i))return 1;
    uint32_t bo=u32(p+16),bn=u32(p+20),mo=u32(p+24),mn=u32(p+28),po=u32(p+32),pc=u32(p+36),socket=u32(p+40);
    if(bo!=128||!span(n,bo,1,bn)||mo!=(size_t)bo+bn||!span(n,mo,1,mn)||po!=(size_t)mo+mn||!pc||pc>COH_ANIMATION_PALETTE||
       !span(n,po,pc,4)||(size_t)po+pc*4!=n||u32(p+60)!=n||socket>=COH_ANIMATION_BONES)return 1;
    CohAnimationRig r={0};r.bytes=p;r.byte_count=n;r.palette_count=pc;r.socket_id=socket;r.first_frame=f32(p+48);r.last_frame=f32(p+52);r.ticks_per_second=f32(p+56);
    if(!isfinite(r.first_frame)||!isfinite(r.last_frame)||!isfinite(r.ticks_per_second)||r.first_frame<0||r.last_frame<=r.first_frame||r.last_frame>COH_ANIMATION_MAX_KEYS||r.ticks_per_second<=0||r.ticks_per_second>120)return 1;
    if(raw_file(p+bo,bn,&r.base)||raw_file(p+mo,mn,&r.motion)||!same_name(r.base.bytes+4,r.base.bytes+260)||!same_name(r.base.bytes+4,r.motion.bytes+260))return 1;
    uint32_t ho=u32(r.base.bytes+540);if(!ho)return 1;
    const uint8_t *hier=r.base.bytes+ho;int root=i32(hier);uint8_t seen[COH_ANIMATION_BONES]={0};
    for(unsigned i=0;i<COH_ANIMATION_BONES;i++)r.parent[i]=-2;
    if(root!=0||visit(&r,hier,root,-1,0,seen)||r.node_count!=r.base.track_count||!seen[socket])return 1;
    /* Authored moves can retain tracks not used by the selected base skeleton
     * (e.g.huge/postrun tracks50/51/52). raw_file has validated every record
     * and encoded key already. Source animPlayInst walks the base hierarchy;
     * the samplers below likewise visit only r.order and ignore spare tracks. */
    for(uint32_t i=0;i<pc;i++){uint32_t id=u32(p+po+(size_t)i*4);if(id>=COH_ANIMATION_BONES||!seen[id])return 1;for(uint32_t j=0;j<i;j++)if(r.palette_ids[j]==id)return 1;r.palette_ids[i]=id;}
    for(uint32_t i=0;i<r.node_count;i++){
        unsigned id=r.order[i];const CohAnimationTrack *base=&r.base.tracks[id];
        if(decode_rotation(base->rotation,r.base_rotation[id])||decode_position(base,0,r.base_position[id]))return 1;
        if(id!=0 && r.parent[id]>=0){int parent=r.parent[id];for(unsigned j=0;j<3;j++)r.bind_translation[id][j]=r.bind_translation[parent][j]+r.base_position[id][j];}
        if(r.motion.tracks[id].present){float first[3];if(decode_position(&r.motion.tracks[id],0,first))return 1;for(unsigned j=0;j<3;j++)r.animation_delta[id][j]=first[j]-r.base_position[id][j];}
        if(!finite_array(r.bind_translation[id],3)||!finite_array(r.animation_delta[id],3))return 1;
    }
    *out=r;return 0;
}
static void quaternion_rows(const float q[4],const float p[3],float m[12]){
    float tx=2.f*q[0],ty=2.f*q[1],tz=2.f*q[2],wx=tx*q[3],wy=ty*q[3],wz=tz*q[3];
    float xx=tx*q[0],xy=ty*q[0],xz=tz*q[0],yy=ty*q[1],yz=tz*q[1],zz=tz*q[2];
    m[0]=1.f-(yy+zz);m[1]=xy+wz;m[2]=xz-wy;m[3]=p[0];
    m[4]=xy-wz;m[5]=1.f-(xx+zz);m[6]=yz+wx;m[7]=p[1];
    m[8]=xz+wy;m[9]=yz-wx;m[10]=1.f-(xx+yy);m[11]=p[2];
}
static void point(const float m[12],const float p[3],float out[3]){float v[3];for(unsigned r=0;r<3;r++)v[r]=p[0]*m[r*4]+p[1]*m[r*4+1]+p[2]*m[r*4+2]+m[r*4+3];memcpy(out,v,sizeof v);}
static void compose(const float a[12],const float b[12],float out[12]){
    float result[12];for(unsigned r=0;r<3;r++){for(unsigned c=0;c<3;c++)result[r*4+c]=b[c]*a[r*4]+b[4+c]*a[r*4+1]+b[8+c]*a[r*4+2];result[r*4+3]=b[3]*a[r*4]+b[7]*a[r*4+1]+b[11]*a[r*4+2]+a[r*4+3];}memcpy(out,result,sizeof result);
}
int coh_animation_sample(const CohAnimationRig *r,float frame,CohAnimationPose *out){
    if(!r||!out||!isfinite(frame)||frame<0||frame>1000000.f||!r->node_count||r->node_count>COH_ANIMATION_BONES)return 1;
    CohAnimationPose result={0};result.frame=frame;
    for(uint32_t i=0;i<r->node_count;i++){
        unsigned id=r->order[i];if(id>=COH_ANIMATION_BONES)return 1;
        if(r->motion.tracks[id].present){if(sample_track(&r->motion.tracks[id],frame,result.rotation[id],result.position[id]))return 1;for(unsigned j=0;j<3;j++)result.position[id][j]-=r->animation_delta[id][j];}
        else {memcpy(result.rotation[id],r->base_rotation[id],sizeof result.rotation[id]);memcpy(result.position[id],r->base_position[id],sizeof result.position[id]);}
        float local[12];quaternion_rows(result.rotation[id],result.position[id],local);int parent=r->parent[id];
        if(parent==-1)memcpy(result.world_rows[id],local,sizeof local);
        else {if(parent<0||parent>=(int)COH_ANIMATION_BONES)return 1;compose(result.world_rows[parent],local,result.world_rows[id]);}
        if(!finite_array(result.world_rows[id],12))return 1;
    }
    *out=result;return 0;
}
int coh_animation_palette(const CohAnimationRig *r,const CohAnimationPose *pose,uint32_t socket,const uint32_t *ids,uint32_t count,float *out){
    if(!r||!pose||!ids||!out||socket>=COH_ANIMATION_BONES||r->parent[socket]==-2||!count||count>COH_ANIMATION_PALETTE)return 1;
    float result[COH_ANIMATION_PALETTE*12];
    for(uint32_t i=0;i<count;i++){
        uint32_t id=ids[i];if(id>=COH_ANIMATION_BONES||r->parent[id]==-2||!finite_array(pose->world_rows[id],12))return 1;
        float *m=result+i*12;memcpy(m,pose->world_rows[id],12*sizeof(float));float inverse[3],translation[3];
        for(unsigned j=0;j<3;j++)inverse[j]=-r->bind_translation[id][j];
        point(m,inverse,translation);for(unsigned j=0;j<3;j++)m[j*4+3]=translation[j];
        point(m,r->bind_translation[socket],translation);for(unsigned j=0;j<3;j++)m[j*4+3]=translation[j];
        if(!finite_array(m,12))return 1;
    }
    memcpy(out,result,(size_t)count*12*sizeof(float));return 0;
}
int coh_animation_default_palette(const CohAnimationRig *r,const CohAnimationPose *pose,float *out){if(!r)return 1;return coh_animation_palette(r,pose,r->socket_id,r->palette_ids,r->palette_count,out);}
int coh_animation_step(const CohAnimationRig *r,float current,float timestep,float rate,int cycle,float *out){
    if(!r||!out||!isfinite(current)||!isfinite(timestep)||!isfinite(rate)||current<r->first_frame||current>r->last_frame||timestep<0||timestep>1000000.f||rate<0||rate>100.f||(cycle!=0&&cycle!=1))return 1;
    float next=current+rate*timestep;if(!isfinite(next))return 1;
    if(next>r->last_frame){if(cycle){next-=r->last_frame-r->first_frame;if(next>r->last_frame)next=r->first_frame;}else return 2;}
    *out=next;return 0;
}
