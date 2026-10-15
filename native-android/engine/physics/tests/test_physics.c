#include "../coh_physics.h"
#include "../../../walk/source_types.h"
#include <stdio.h>
#include <time.h>
static unsigned checks,failed,parity_cases,walk_cases;
static uint64_t alloc_calls,live_allocations;static int track_allocs;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void*,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){void *p;if(track_allocs)alloc_calls++;p=__real_malloc(n);if(p)live_allocations++;return p;}
void *__wrap_calloc(size_t n,size_t m){void *p;if(track_allocs)alloc_calls++;p=__real_calloc(n,m);if(p)live_allocations++;return p;}
void *__wrap_realloc(void *p,size_t n){void *next;if(track_allocs)alloc_calls++;next=__real_realloc(p,n);
    if(!p&&next)live_allocations++;else if(p&&!n)live_allocations--;return next;}
void __wrap_free(void *p){if(track_allocs)alloc_calls++;if(p)live_allocations--;__real_free(p);}
#define CHECK(c) do{checks++;if(!(c)){failed++;fprintf(stderr,"physics check line %d: %s\n",__LINE__,#c);}}while(0)
static const CohPhysicsBudget unlimited={1000000,COH_PHYSICS_MAX_TRIANGLES};
static uint32_t random_state=0x636f6832u;
static uint32_t rnd(void){random_state=random_state*1664525u+1013904223u;return random_state;}
static float randomf(float lo,float hi){return lo+(hi-lo)*(float)(rnd()&65535)/65535.f;}
static int cancel_now(void *p){(void)p;return 1;}
/* Independent brute-force oracle: source collGrid's distance/CTri law, without
 * using the new scene builder/BVH/contact helper/window adapter. */
static CohPhysicsContact reference(const CohPhysicsSegment *seg,unsigned count,const float start[3],
    const float end[3],float radius,unsigned flags){
    CohPhysicsContact result={0};unsigned i,j,k;result.squared_distance=8e16f;
    for(i=0;i<count;i++)for(j=0;j<seg[i].count;j++){
        const CohWalkTriangle *source=&seg[i].triangles[j];CTri tri={0};Vec3 a,b,col,delta;
        CtriState st={0};float sqdist;unsigned valid=1;
        if(!(source->flags&(COH_WALK_NORMALTRI|COH_WALK_NOTSELECTABLE)))continue;
        for(k=0;k<3;k++){
            float lo=fminf(source->v[0][k],fminf(source->v[1][k],source->v[2][k]));
            float hi=fmaxf(source->v[0][k],fmaxf(source->v[1][k],source->v[2][k]));
            if(fmaxf(start[k],end[k])+radius<lo||fminf(start[k],end[k])-radius>hi)valid=0;
        }
        if(!valid||!createCTri(&tri,(float*)source->v[0],(float*)source->v[1],(float*)source->v[2]))continue;
        tri.flags=source->flags;copyVec3(start,a);copyVec3(end,b);subVec3(end,start,delta);
        float len=lengthVec3(delta);st.inv_linemag=len>0?1.f/len:1.f;st.linelen=len;st.linelen2=len*.5f;
        st.early_exit=!(flags&(COLL_BOTHSIDES|COLL_DISTFROMCENTER));
        sqdist=ctriCollideRad(&tri,a,b,col,radius,&st);
        if(sqdist<0||!isfinite(sqdist))continue;
        if(flags&COLL_CYLINDER){Vec3 verts[3];float radial=0;int ret;expandCtriVerts(&tri,verts);
            ret=ctriCylCheck(col,a,b,radius,verts,&radial);if(!ret)continue;
            if(ret>0&&(flags&COLL_DISTFROMSTART))sqdist=radial;
        }
        if(flags&COLL_DISTFROMSTARTEXACT){Vec3 verts[3];Mat4 ident;memcpy(ident,unitmat,sizeof ident);
            expandCtriVerts(&tri,verts);sqdist=ctriGetPointClosestToStart(col,a,b,radius,verts,tri.norm,ident);
        }
        if(flags&COLL_DISTFROMSTART){float line=sqdist;subVec3(col,start,delta);
            sqdist=lengthVec3Squared(delta)-line;if(sqdist<0)sqdist=0;
            float d=sqrtf(sqdist)+(1-tri.norm[1])/64.f;sqdist=d*d;
        }
        if(!isfinite(sqdist))continue;
        if(sqdist<result.squared_distance){result=(CohPhysicsContact){seg[i].id,seg[i].generation,j,1,tri.flags,{0},{0},sqdist};
            copyVec3(col,result.position);copyVec3(tri.norm,result.normal);
        }
        if(flags&COLL_HITANY)return result;
    }
    return result;
}
static void compare_contact(CohPhysicsContact a,CohPhysicsContact b){
    CHECK(a.hit==b.hit);
    if(a.hit&&b.hit){CHECK(a.segment==b.segment&&a.triangle==b.triangle&&a.generation==b.generation&&a.flags==b.flags);
        for(unsigned k=0;k<3;k++){CHECK(fabsf(a.position[k]-b.position[k])<.00001f);CHECK(fabsf(a.normal[k]-b.normal[k])<.00001f);}
        CHECK(fabsf(a.squared_distance-b.squared_distance)<.0001f);
    }
    parity_cases++;
}
static void quad(CohWalkTriangle *t,float x,float z,float y0,float y1,float size){
    *t=(CohWalkTriangle){{{x,y0,z},{x,y0,z+size},{x+size,y1,z}},COH_WALK_NORMALTRI};
    t[1]=(CohWalkTriangle){{{x+size,y1,z},{x,y0,z+size},{x+size,y1,z+size}},COH_WALK_NORMALTRI};
}
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float f32(const unsigned char *p){uint32_t u=u32(p);float f;memcpy(&f,&u,4);return f;}
static void terrain_walk(void){
    /* Synthetic slopes and a half-unit authored step; the accepted source WALK
     * is the oracle. This extends witnesses without inventing terrain laws. */
    for(unsigned family=0;family<2;family++){
        CohWalkTriangle t[6];unsigned count=2;float lo[3]={-64,-4,-64},hi[3]={64,4,64};
        float spawn[3]={-16,-1,-16},extents[3]={128,128,128};
        if(!family)quad(t,-64,-64,-4,4,128);
        else{
            t[0]=(CohWalkTriangle){{{-64,0,-64},{-64,0,64},{0,0,-64}},COH_WALK_NORMALTRI};
            t[1]=(CohWalkTriangle){{{0,0,-64},{-64,0,64},{0,0,64}},COH_WALK_NORMALTRI};
            t[2]=(CohWalkTriangle){{{0,.5f,-64},{0,.5f,64},{64,.5f,-64}},COH_WALK_NORMALTRI};
            t[3]=(CohWalkTriangle){{{64,.5f,-64},{0,.5f,64},{64,.5f,64}},COH_WALK_NORMALTRI};
            t[4]=(CohWalkTriangle){{{0,0,-64},{0,0,64},{0,.5f,64}},COH_WALK_NORMALTRI};
            t[5]=(CohWalkTriangle){{{0,0,-64},{0,.5f,64},{0,.5f,-64}},COH_WALK_NORMALTRI};
            count=6;spawn[1]=0;lo[1]=0;hi[1]=.5f;
        }
        CohWalkWorld direct={0};CohWalkState ds;CohPhysicsScene *scene=NULL;CohPhysicsWalker w={0};
        CohPhysicsSegment segments[2]={{300,1,t,count/2},{301,1,t+count/2,count-count/2}};
        CHECK(coh_walk_world_init(&direct,t,count,lo,hi));CHECK(coh_walk_init(&ds,&direct,spawn,0));
        CHECK(coh_physics_scene_create(&scene,segments,2,30+family,1024*1024,NULL)==COH_OK);
        CHECK(coh_physics_walker_prepare(&w,scene,spawn,extents,spawn,0,unlimited,NULL)==COH_OK);
        if(w.ready){float highest=w.state.position[1];
            track_allocs=1;
            for(unsigned tick=0;tick<64;tick++){
                unsigned directions=tick<40?COH_MOTION_RIGHT:COH_MOTION_LEFT;
                CHECK(coh_walk_step(&ds,&direct,directions,0));
                CHECK(coh_physics_walker_step(&w,30+family,directions,0)==COH_OK);
                CHECK(!memcmp(&ds,&w.state,sizeof ds));walk_cases++;
                highest=fmaxf(highest,w.state.position[1]);
            }
            track_allocs=0;
            CHECK(highest>spawn[1]+.4f);CHECK(w.state.bounded_steps==0);
        }
        coh_physics_walker_destroy(&w);coh_physics_scene_destroy(scene);coh_walk_world_destroy(&direct);
    }
}
static int authored(const char *path){
    FILE *f=fopen(path,"rb");unsigned char *bytes;long n;CohWalkTriangle *t;uint32_t count,off,i,k,v;
    float lo[3],hi[3],spawn[3],extents[3]={4096,4096,4096};CohWalkWorld direct={0};CohWalkState ds;
    CohPhysicsScene *scene=NULL;CohPhysicsWalker walker={0};
    if(!f)return 0;if(fseek(f,0,SEEK_END)){fclose(f);return 0;}n=ftell(f);
    if(n<128||n>16*1024*1024||fseek(f,0,SEEK_SET)){fclose(f);return 0;}
    bytes=malloc((size_t)n);if(!bytes){fclose(f);return 0;}
    if(fread(bytes,1,(size_t)n,f)!=(size_t)n){free(bytes);fclose(f);return 0;}fclose(f);
    if(memcmp(bytes,"COHWALK1",8)||u32(bytes+8)!=1){free(bytes);return 0;}
    count=u32(bytes+24);off=u32(bytes+52);
    if(!count||count>8192||off>(uint32_t)n||count>((uint32_t)n-off)/40){free(bytes);return 0;}
    t=malloc(count*sizeof(*t));if(!t){free(bytes);return 0;}
    for(i=0;i<count;i++){
        for(v=0;v<3;v++)for(k=0;k<3;k++)t[i].v[v][k]=f32(bytes+off+i*40+(v*3+k)*4);
        t[i].flags=u32(bytes+off+i*40+36);
    }
    for(k=0;k<3;k++){lo[k]=f32(bytes+68+k*4);hi[k]=f32(bytes+80+k*4);spawn[k]=f32(bytes+92+k*4);}
    float yaw=f32(bytes+104);free(bytes);
    CohPhysicsSegment segments[2]={{77,1,t,count/2},{78,1,t+count/2,count-count/2}};
    CHECK(coh_physics_scene_create(&scene,segments,2,13,64*1024*1024,NULL)==COH_OK);
    CHECK(coh_walk_world_init(&direct,t,count,lo,hi));CHECK(coh_walk_init(&ds,&direct,spawn,yaw));
    CHECK(coh_physics_walker_prepare(&walker,scene,spawn,extents,spawn,yaw,unlimited,NULL)==COH_OK);
    if(!scene||!walker.ready){coh_walk_world_destroy(&direct);coh_physics_scene_destroy(scene);free(t);return 0;}
    for(i=0;i<1024;i++){
        float start[3],end[3];for(k=0;k<3;k++){start[k]=randomf(lo[k]-2,hi[k]+2);end[k]=start[k]+randomf(-6,6);}
        unsigned flags[]={COLL_DISTFROMSTART|COLL_BOTHSIDES,COLL_DISTFROMCENTER,
            COLL_DISTFROMSTART|COLL_CYLINDER,COLL_DISTFROMSTART|COLL_DISTFROMSTARTEXACT,COLL_HITANY};
        CohPhysicsContact out;CohPhysicsQueryStats stats;float radius=randomf(0,1.2f);
        CHECK(coh_physics_query(scene,start,end,radius,flags[i%5],unlimited,&out,&stats)==COH_OK);
        compare_contact(out,reference(segments,2,start,end,radius,flags[i%5]));
    }
    track_allocs=1;
    for(i=0;i<250;i++){
        unsigned dirs=i<70?COH_MOTION_FORWARD:i<108?COH_MOTION_FORWARD|COH_MOTION_RIGHT:i<128?COH_MOTION_BACKWARD:0;
        CHECK(coh_walk_step(&ds,&direct,dirs,yaw));
        CHECK(coh_physics_walker_step(&walker,13,dirs,yaw)==COH_OK);
        CHECK(!memcmp(&walker.state,&ds,sizeof ds));walk_cases++;
        if(i==128){coh_walk_clear(&ds);coh_physics_walker_clear(&walker);}
    }
    track_allocs=0;
    CohWalkState prior=walker.state;
    CHECK(coh_physics_walker_prepare(&walker,scene,spawn,extents,spawn,yaw,unlimited,NULL)==COH_OK);
    CHECK(!memcmp(&prior,&walker.state,sizeof prior));
    CHECK(coh_physics_walker_step(&walker,14,0,yaw)==COH_STATE);
    CHECK(!memcmp(&prior,&walker.state,sizeof prior));
    CHECK(coh_physics_walker_step(&walker,13,16,yaw)==COH_INVALID);
    CHECK(!memcmp(&prior,&walker.state,sizeof prior));
    CohCancel cancel={cancel_now,NULL};void *owned=walker.world.prepared;
    CHECK(coh_physics_walker_prepare(&walker,scene,spawn,extents,spawn,yaw,unlimited,&cancel)==COH_CANCELLED);
    CHECK(owned==walker.world.prepared&&!memcmp(&prior,&walker.state,sizeof prior));
    CHECK(coh_physics_walker_prepare(&walker,scene,spawn,extents,spawn,yaw,(CohPhysicsBudget){1,1},NULL)==COH_LIMIT);
    CHECK(owned==walker.world.prepared);
    coh_physics_scene_destroy(scene);coh_physics_walker_destroy(&walker);coh_walk_world_destroy(&direct);free(t);return 1;
}
int main(int argc,char **argv){
    enum{SIDE=128,TRIANGLES=SIDE*SIDE*2};unsigned i,k;uint32_t max_nodes=0,max_tests=0;size_t memory=0;
    CohWalkProof proof;CHECK(coh_walk_selftest(&proof));CHECK(proof.failed==0);
    CohWalkTriangle *tri=malloc(TRIANGLES*sizeof(*tri));CohPhysicsScene *scene=NULL;
    CHECK(tri!=NULL);if(!tri)return 1;
    for(i=0;i<SIDE*SIDE;i++){
        unsigned x=i%SIDE,z=i/SIDE;float y=(x%4==0)?2.f:(x%4==1)?4.f:0.f;
        /* Explicitly labelled synthetic varied elevations and slope witnesses. */
        quad(tri+2*i,(float)x*8,(float)z*8,y,y+(z%3==0?2.f:0.f),8);
    }
    CohPhysicsSegment segments[4];for(i=0;i<4;i++)segments[i]=(CohPhysicsSegment){100+i,1,tri+i*(TRIANGLES/4),TRIANGLES/4};
    CHECK(coh_physics_scene_create(&scene,segments,4,1,64*1024*1024,NULL)==COH_OK);
    CohPhysicsSceneInfo info;CHECK(coh_physics_scene_info(scene,&info)==COH_OK);memory=info.owned_bytes;
    CHECK(info.triangle_count==TRIANGLES&&info.segment_count==4);CHECK(info.node_count<TRIANGLES/2);
    CohPhysicsWalker dense={0};
    CHECK(coh_physics_walker_prepare(&dense,scene,(float[]){512,0,512},(float[]){4096,4096,4096},
        (float[]){512,0,512},0,unlimited,NULL)==COH_LIMIT);CHECK(dense.ready==0&&dense.world.prepared==NULL);
    clock_t start_clock=clock();track_allocs=1;
    for(i=0;i<1024;i++){
        float a[3]={randomf(1,1023),12,randomf(1,1023)},b[3]={a[0]+randomf(-1,1),-4,a[2]+randomf(-1,1)};
        unsigned flags=COLL_DISTFROMSTART|((i%2)?COLL_BOTHSIDES:0);CohPhysicsContact result;CohPhysicsQueryStats stats;
        CHECK(coh_physics_query(scene,a,b,.5f,flags,unlimited,&result,&stats)==COH_OK);
        compare_contact(result,reference(segments,4,a,b,.5f,flags));
        if(stats.nodes>max_nodes)max_nodes=stats.nodes;if(stats.triangles>max_tests)max_tests=stats.triangles;
    }
    track_allocs=0;double cpu_seconds=(double)(clock()-start_clock)/CLOCKS_PER_SEC;
    CHECK(max_nodes<128&&max_tests<32);CHECK(alloc_calls==0);
    CohPhysicsContact sentinel;memset(&sentinel,0xa5,sizeof sentinel);CohPhysicsContact out=sentinel;CohPhysicsQueryStats stats;
    CHECK(coh_physics_query(scene,(float[]){0,12,0},(float[]){1024,-4,1024},1,0,
        (CohPhysicsBudget){1,1},&out,&stats)==COH_LIMIT);CHECK(!memcmp(&out,&sentinel,sizeof out));
    CHECK(coh_physics_query(scene,(float[]){NAN,0,0},(float[]){0,0,0},1,0,unlimited,&out,&stats)==COH_INVALID);
    CHECK(!memcmp(&out,&sentinel,sizeof out));
    CHECK(coh_physics_query(scene,(float[]){0,12,0},(float[]){0,0,0},17,0,unlimited,&out,&stats)==COH_INVALID);
    CHECK(coh_physics_query(scene,(float[]){0,12,0},(float[]){0,0,0},1,1u<<31,unlimited,&out,&stats)==COH_INVALID);
    CohPhysicsScene *bad=NULL;CohPhysicsSegment invalid[2]={segments[0],segments[0]};CohCancel cancel={cancel_now,NULL};
    CHECK(coh_physics_scene_create(&bad,invalid,2,1,64*1024*1024,NULL)==COH_INVALID&&bad==NULL);
    CHECK(coh_physics_scene_create(&bad,segments,4,1,1,NULL)==COH_LIMIT&&bad==NULL);
    CHECK(coh_physics_scene_create(&bad,segments,4,1,64*1024*1024,&cancel)==COH_CANCELLED&&bad==NULL);
    CohWalkTriangle malformed=tri[0];malformed.v[0][0]=NAN;CohPhysicsSegment broken={1,1,&malformed,1};
    CHECK(coh_physics_scene_create(&bad,&broken,1,1,1024*1024,NULL)==COH_INVALID&&bad==NULL);
    malformed=tri[0];for(k=0;k<3;k++)memcpy(malformed.v[k],tri[0].v[0],3*sizeof(float));
    CHECK(coh_physics_scene_create(&bad,&broken,1,1,1024*1024,NULL)==COH_INVALID&&bad==NULL);
    malformed=tri[0];malformed.flags=1u<<31;
    CHECK(coh_physics_scene_create(&bad,&broken,1,1,1024*1024,NULL)==COH_INVALID&&bad==NULL);
    /* A small WALK neighborhood stops explicitly before missing scene content.
     * A replacement snapshot can remove the segment; no floor is synthesized. */
    CohPhysicsWalker walker={0};float spawn[3]={400,0,400},extent[3]={32,32,32};
    CohWalkTriangle flat[2];quad(flat,0,0,0,0,1024);CohPhysicsScene *flat_scene=NULL;
    CohPhysicsSegment flat_seg={200,1,flat,2};
    CHECK(coh_physics_scene_create(&flat_scene,&flat_seg,1,10,1024*1024,NULL)==COH_OK);
    CHECK(coh_physics_walker_prepare(&walker,flat_scene,spawn,extent,spawn,0,unlimited,NULL)==COH_OK);
    if(walker.ready){CohStatus status=COH_OK;
        for(i=0;i<200&&status==COH_OK;i++)status=coh_physics_walker_step(&walker,10,COH_MOTION_RIGHT,0);
        CHECK(status==COH_NOT_FOUND);CHECK(walker.refresh_requests==1);
        CHECK(coh_physics_walker_prepare(&walker,flat_scene,walker.state.position,extent,spawn,0,unlimited,NULL)==COH_OK);
        CHECK(coh_physics_walker_step(&walker,10,0,0)==COH_OK);
        CohWalkTriangle remote[2];quad(remote,2000,2000,0,0,128);
        CohPhysicsSegment remote_seg={201,1,remote,2};CohPhysicsScene *removed=NULL;
        CHECK(coh_physics_scene_create(&removed,&remote_seg,1,11,1024*1024,NULL)==COH_OK);
        CohWalkState prior=walker.state;void *owned=walker.world.prepared;
        CHECK(coh_physics_walker_prepare(&walker,removed,walker.state.position,extent,spawn,0,unlimited,NULL)==COH_NOT_FOUND);
        CHECK(owned==walker.world.prepared&&!memcmp(&prior,&walker.state,sizeof prior));
        coh_physics_scene_destroy(removed);
    }
    coh_physics_walker_destroy(&walker);coh_physics_scene_destroy(flat_scene);coh_physics_scene_destroy(scene);free(tri);
    /* Coincident source triangles must resolve by input identity, even after
     * BVH sorting. This also establishes HIT_ANY original traversal semantics. */
    CohWalkTriangle duplicate[2];quad(duplicate,0,0,0,0,16);
    CohPhysicsSegment ties[2]={{902,1,duplicate,2},{901,2,duplicate,2}};
    CohPhysicsScene *tie_scene=NULL;
    CHECK(coh_physics_scene_create(&tie_scene,ties,2,20,1024*1024,NULL)==COH_OK);
    for(i=0;i<2;i++){
        CHECK(coh_physics_query(tie_scene,(float[]){4,8,4},(float[]){4,-8,4},1,
            i?COLL_HITANY:COLL_DISTFROMSTART,unlimited,&out,&stats)==COH_OK);
        CHECK(out.hit&&out.segment==902&&out.generation==1);
        compare_contact(out,reference(ties,2,(float[]){4,8,4},(float[]){4,-8,4},1,
            i?COLL_HITANY:COLL_DISTFROMSTART));
    }
    coh_physics_scene_destroy(tie_scene);
    terrain_walk();
    CHECK(argc==2);if(argc==2)CHECK(authored(argv[1]));
    CHECK(alloc_calls==0);CHECK(live_allocations==0);
    printf("{\"passed\":%s,\"checks\":%u,\"failed\":%u,\"contact_oracle_cases\":%u,\"accepted_walk_exact_steps\":%u,"
        "\"large_scene_triangles\":%u,\"large_scene_owned_bytes\":%zu,\"max_query_nodes\":%u,\"max_query_triangle_tests\":%u,"
        "\"query_and_walk_allocator_calls\":%llu,\"outstanding_tracked_allocations\":%llu,\"synthetic_oracle_batch_cpu_seconds\":%.9g}\n",
        failed?"false":"true",checks,failed,parity_cases,walk_cases,TRIANGLES,memory,max_nodes,max_tests,
        (unsigned long long)alloc_calls,(unsigned long long)live_allocations,cpu_seconds);
    return failed?1:0;
}
