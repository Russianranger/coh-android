#include "coh_physics.h"
#include "../../walk/source_types.h"
#include <float.h>
#include <limits.h>
#define SCENE_MAGIC 0x50485932u
#define LEAF 8u
typedef struct {
    CohWalkTriangle source; CTri ctri; float lo[3],hi[3];
    uint64_t segment; uint32_t generation,triangle,rank;
} Triangle;
typedef struct { float lo[3],hi[3]; uint32_t left,right,first,count; } Node;
struct CohPhysicsScene {
    uint32_t magic,generation,count,segments,nodes;
    size_t bytes; Triangle *triangles; uint32_t *order; Node *tree;
};
static int finite3(const float *v) {
    unsigned k;if(!v)return 0;
    for(k=0;k<3;k++)if(!isfinite(v[k])||fabsf(v[k])>1000000.f)return 0;
    return 1;
}
static int valid(const CohPhysicsScene *s) {
    return s&&s->magic==SCENE_MAGIC&&s->count&&s->nodes&&s->triangles&&s->tree&&s->order;
}
static int cancelled(const CohCancel *c){return c&&c->poll&&c->poll(c->context);}
/* Sorting prepared triangle values makes comparator state local and build
 * thread safe; rank restores input order for deterministic ties and WALK. */
static int cmp_axis(const Triangle *a,const Triangle *b,unsigned k) {
    float aa=a->lo[k]+a->hi[k],bb=b->lo[k]+b->hi[k];
    return aa<bb?-1:aa>bb?1:a->rank<b->rank?-1:a->rank>b->rank;
}
static int cmp_x(const void *a,const void *b){return cmp_axis(a,b,0);}
static int cmp_y(const void *a,const void *b){return cmp_axis(a,b,1);}
static int cmp_z(const void *a,const void *b){return cmp_axis(a,b,2);}
static int cmp_rank(const void *aa,const void *bb){
    uint32_t a=*(const uint32_t*)aa,b=*(const uint32_t*)bb;return a<b?-1:a>b;
}
static uint32_t build(CohPhysicsScene *s,uint32_t first,uint32_t count) {
    uint32_t index=s->nodes++,i,j;Node *n=&s->tree[index];unsigned axis=0;
    for(j=0;j<3;j++){n->lo[j]=FLT_MAX;n->hi[j]=-FLT_MAX;}
    for(i=first;i<first+count;i++)for(j=0;j<3;j++){
        n->lo[j]=fminf(n->lo[j],s->triangles[i].lo[j]);
        n->hi[j]=fmaxf(n->hi[j],s->triangles[i].hi[j]);
    }
    if(count<=LEAF){n->first=first;n->count=count;return index;}
    for(j=1;j<3;j++)if(n->hi[j]-n->lo[j]>n->hi[axis]-n->lo[axis])axis=j;
    qsort(s->triangles+first,count,sizeof(Triangle),axis==0?cmp_x:axis==1?cmp_y:cmp_z);
    n->left=build(s,first,count/2);n->right=build(s,first+count/2,count-count/2);
    return index;
}
CohStatus coh_physics_scene_create(CohPhysicsScene **out,const CohPhysicsSegment *seg,
    uint32_t count,uint32_t generation,size_t limit,const CohCancel *cancel) {
    CohPhysicsScene *s;uint32_t total=0,i,j,k,v,at=0;size_t bytes;
    if(!out||*out||!seg||!count||count>COH_PHYSICS_MAX_SEGMENTS||!generation)return COH_INVALID;
    for(i=0;i<count;i++){
        if(!seg[i].id||!seg[i].generation||!seg[i].triangles||!seg[i].count||
            seg[i].count>COH_PHYSICS_MAX_TRIANGLES-total)return COH_LIMIT;
        for(j=0;j<i;j++)if(seg[j].id==seg[i].id)return COH_INVALID;
        total+=seg[i].count;
    }
    bytes=sizeof(*s)+(size_t)total*(sizeof(Triangle)+sizeof(uint32_t)+2*sizeof(Node));
    if(bytes>limit)return COH_LIMIT;
    if(cancelled(cancel))return COH_CANCELLED;
    s=calloc(1,sizeof(*s));if(!s)return COH_IO;
    s->triangles=calloc(total,sizeof(Triangle));s->order=calloc(total,sizeof(uint32_t));
    s->tree=calloc((size_t)total*2,sizeof(Node));s->magic=SCENE_MAGIC;
    if(!s->triangles||!s->order||!s->tree){coh_physics_scene_destroy(s);return COH_IO;}
    s->generation=generation;s->count=total;s->segments=count;s->bytes=bytes;
    for(i=0;i<count;i++)for(j=0;j<seg[i].count;j++,at++){
        Triangle *t=&s->triangles[at];t->source=seg[i].triangles[j];
        if(cancelled(cancel)){coh_physics_scene_destroy(s);return COH_CANCELLED;}
        if(t->source.flags&~((1u<<27)-1)){coh_physics_scene_destroy(s);return COH_INVALID;}
        for(v=0;v<3;v++)if(!finite3(t->source.v[v])){coh_physics_scene_destroy(s);return COH_INVALID;}
        for(k=0;k<3;k++){
            t->lo[k]=t->hi[k]=t->source.v[0][k];
            for(v=1;v<3;v++){
                t->lo[k]=fminf(t->lo[k],t->source.v[v][k]);
                t->hi[k]=fmaxf(t->hi[k],t->source.v[v][k]);
            }
        }
        if(!createCTri(&t->ctri,t->source.v[0],t->source.v[1],t->source.v[2])){
            coh_physics_scene_destroy(s);return COH_INVALID;
        }
        t->ctri.flags=t->source.flags;t->segment=seg[i].id;t->generation=seg[i].generation;
        t->triangle=j;t->rank=at;
    }
    build(s,0,total);
    for(i=0;i<total;i++)s->order[s->triangles[i].rank]=i;
    if(cancelled(cancel)){coh_physics_scene_destroy(s);return COH_CANCELLED;}
    *out=s;return COH_OK;
}
void coh_physics_scene_destroy(CohPhysicsScene *s) {
    if(!s||s->magic!=SCENE_MAGIC)return;
    s->magic=0;free(s->tree);free(s->order);free(s->triangles);free(s);
}
CohStatus coh_physics_scene_info(const CohPhysicsScene *s,CohPhysicsSceneInfo *out) {
    if(!valid(s)||!out)return COH_INVALID;
    *out=(CohPhysicsSceneInfo){s->generation,s->segments,s->count,s->nodes,s->bytes};return COH_OK;
}
static int overlaps(const float a[3],const float b[3],const float lo[3],const float hi[3]) {
    unsigned k;for(k=0;k<3;k++)if(b[k]<lo[k]||a[k]>hi[k])return 0;return 1;
}
static int contact(const Triangle *tc,const float start[3],const float end[3],
    float radius,uint32_t flags,CohPhysicsContact *out) {
    /* Source functions accept mutable CTri but do not change it. Private copy
     * guarantees immutable scenes remain safely concurrently readable. */
    CTri tri=tc->ctri;Vec3 a,b,hit,delta,vertices[3];CtriState state={0};float d,len;
    copyVec3(start,a);copyVec3(end,b);subVec3(end,start,delta);len=lengthVec3(delta);
    state.inv_linemag=len>0?1.f/len:1.f;state.linelen=len;state.linelen2=len*.5f;
    state.early_exit=!(flags&(COLL_BOTHSIDES|COLL_DISTFROMCENTER));
    d=ctriCollideRad(&tri,a,b,hit,radius,&state);
    if(d<0||!isfinite(d)||!finite3(hit))return 0;
    if(flags&COLL_CYLINDER){float radial=0;int ret;expandCtriVerts(&tri,vertices);
        ret=ctriCylCheck(hit,a,b,radius,vertices,&radial);if(!ret)return 0;
        if(ret>0&&(flags&COLL_DISTFROMSTART))d=radial;
    }
    if(flags&COLL_DISTFROMSTARTEXACT){Mat4 ident;memcpy(ident,unitmat,sizeof ident);
        expandCtriVerts(&tri,vertices);d=ctriGetPointClosestToStart(hit,a,b,radius,vertices,tri.norm,ident);
    }
    if(flags&COLL_DISTFROMSTART){float line=d;subVec3(hit,start,delta);d=lengthVec3Squared(delta)-line;
        if(d<0)d=0;d=sqrtf(d)+(1-tri.norm[1])/64.f;d*=d;
    }
    if(!isfinite(d)||!finite3(hit))return 0;
    *out=(CohPhysicsContact){tc->segment,tc->generation,tc->triangle,1,tri.flags,{0},{0},d};
    copyVec3(hit,out->position);copyVec3(tri.norm,out->normal);return 1;
}
CohStatus coh_physics_query(const CohPhysicsScene *s,const float start[3],const float end[3],
    float radius,uint32_t flags,CohPhysicsBudget budget,CohPhysicsContact *out,CohPhysicsQueryStats *stats) {
    uint32_t stack[32],top=0,i,best=UINT32_MAX;CohPhysicsQueryStats st={0};
    CohPhysicsContact result={0};float lo[3],hi[3];
    uint32_t mask=COLL_DISTFROMSTART|COLL_DISTFROMCENTER|COLL_HITANY|COLL_BOTHSIDES|COLL_CYLINDER|COLL_DISTFROMSTARTEXACT;
    if(stats)*stats=st;
    if(!valid(s)||!out||!finite3(start)||!finite3(end)||!isfinite(radius)||radius<0||radius>16||
        flags&~mask||!budget.max_nodes||!budget.max_triangles)return COH_INVALID;
    for(i=0;i<3;i++){lo[i]=fminf(start[i],end[i])-radius;hi[i]=fmaxf(start[i],end[i])+radius;}
    stack[top++]=0;result.squared_distance=8e16f;
    while(top){const Node *n=&s->tree[stack[--top]];
        if(st.nodes==budget.max_nodes)goto limit;st.nodes++;
        if(!overlaps(lo,hi,n->lo,n->hi))continue;
        if(!n->count){if(top+2>32)goto limit;stack[top++]=n->right;stack[top++]=n->left;continue;}
        for(i=n->first;i<n->first+n->count;i++){
            const Triangle *t=&s->triangles[i];CohPhysicsContact c;
            if(!(t->ctri.flags&(COH_WALK_NORMALTRI|COH_WALK_NOTSELECTABLE))||!overlaps(lo,hi,t->lo,t->hi))continue;
            if(st.triangles==budget.max_triangles)goto limit;st.triangles++;
            if(!contact(t,start,end,radius,flags,&c))continue;st.candidates++;
            if((flags&COLL_HITANY)?t->rank<best:
                c.squared_distance<result.squared_distance||(c.squared_distance==result.squared_distance&&t->rank<best)){
                result=c;best=t->rank;
            }
        }
    }
    if(stats)*stats=st;*out=result;return COH_OK;
limit:if(stats)*stats=st;return COH_LIMIT;
}
/* Gather in source input order. Off-tick preparation uses a BVH mark pass then
 * rank-order extraction; storage never exceeds accepted WALK capacity. */
CohStatus coh_physics_walker_prepare(CohPhysicsWalker *w,const CohPhysicsScene *s,
    const float center[3],const float extents[3],const float spawn[3],float yaw,
    CohPhysicsBudget budget,const CohCancel *cancel) {
    uint32_t stack[32],top=0,count=0,i,k,visited=0,tested=0;CohPhysicsWalker next={0};
    uint32_t *indices=NULL;CohWalkTriangle *tri=NULL;float lo[3],hi[3],wlo[3],whi[3];CohStatus status=COH_OK;
    if(!w||!valid(s)||!finite3(center)||!finite3(extents)||!finite3(spawn)||!isfinite(yaw)||
        !budget.max_nodes||!budget.max_triangles||w->ready>1)return COH_INVALID;
    for(k=0;k<3;k++){
        if(extents[k]<32||extents[k]>4096)return COH_INVALID;
        lo[k]=center[k]-extents[k];hi[k]=center[k]+extents[k];wlo[k]=FLT_MAX;whi[k]=-FLT_MAX;
        if((w->ready?w->state.position[k]:spawn[k])<lo[k]+16||
            (w->ready?w->state.position[k]:spawn[k])>hi[k]-16)return COH_INVALID;
    }
    if(cancelled(cancel))return COH_CANCELLED;
    indices=malloc(COH_WALK_MAX_TRIANGLES*sizeof(uint32_t));
    tri=malloc(COH_WALK_MAX_TRIANGLES*sizeof(CohWalkTriangle));
    if(!indices||!tri){status=COH_IO;goto done;}
    stack[top++]=0;
    while(top){const Node *n=&s->tree[stack[--top]];
        if(visited++==budget.max_nodes){status=COH_LIMIT;goto done;}
        if(cancelled(cancel)){status=COH_CANCELLED;goto done;}
        if(!overlaps(lo,hi,n->lo,n->hi))continue;
        if(!n->count){if(top+2>32){status=COH_LIMIT;goto done;}stack[top++]=n->right;stack[top++]=n->left;continue;}
        for(i=n->first;i<n->first+n->count;i++){
            const Triangle *t=&s->triangles[i];
            if(!overlaps(lo,hi,t->lo,t->hi))continue;
            if(tested++==budget.max_triangles||count==COH_WALK_MAX_TRIANGLES){status=COH_LIMIT;goto done;}
            indices[count++]=t->rank;
        }
    }
    if(!count){status=COH_NOT_FOUND;goto done;}
    qsort(indices,count,sizeof(*indices),cmp_rank);
    for(i=0;i<count;i++){
        const Triangle *t=&s->triangles[s->order[indices[i]]];tri[i]=t->source;
        for(k=0;k<3;k++){wlo[k]=fminf(wlo[k],t->lo[k]);whi[k]=fmaxf(whi[k],t->hi[k]);}
    }
    /* Preserve ground-query Y guard and actual triangle bounds; never synthesize floor. */
    if(!coh_walk_world_init(&next.world,tri,count,wlo,whi)){status=COH_LIMIT;goto done;}
    if(w->ready){CohWalkState support;
        if(w->generation!=s->generation&&!coh_walk_init(&support,&next.world,w->state.position,w->state.controls.control_yaw)){
            status=COH_NOT_FOUND;goto done;
        }
        next.state=w->state;next.steps=w->steps;next.refresh_requests=w->refresh_requests;
    }else if(!coh_walk_init(&next.state,&next.world,spawn,yaw)){status=COH_NOT_FOUND;goto done;}
    next.generation=s->generation;next.ready=1;next.owned_triangle_bytes=(size_t)count*sizeof(CohWalkTriangle);
    copyVec3(lo,next.query_min);copyVec3(hi,next.query_max);
    if(cancelled(cancel)){status=COH_CANCELLED;goto done;}
    coh_walk_world_destroy(&w->world);*w=next;memset(&next,0,sizeof next);
done:coh_walk_world_destroy(&next.world);free(tri);free(indices);return status;
}
CohStatus coh_physics_walker_step(CohPhysicsWalker *w,uint32_t generation,uint32_t directions,float yaw) {
    unsigned k;CohWalkState next;
    if(!w||w->ready!=1)return COH_STATE;
    if(generation!=w->generation)return COH_STATE;
    for(k=0;k<3;k++)if(w->state.position[k]<w->query_min[k]+16||w->state.position[k]>w->query_max[k]-16){
        if(w->refresh_requests<UINT64_MAX)w->refresh_requests++;return COH_NOT_FOUND;
    }
    next=w->state;if(!coh_walk_step(&next,&w->world,directions,yaw))return COH_INVALID;
    w->state=next;if(w->steps<UINT64_MAX)w->steps++;return COH_OK;
}
void coh_physics_walker_clear(CohPhysicsWalker *w){if(w&&w->ready==1)coh_walk_clear(&w->state);}
void coh_physics_walker_destroy(CohPhysicsWalker *w){if(!w)return;coh_walk_world_destroy(&w->world);memset(w,0,sizeof *w);}
