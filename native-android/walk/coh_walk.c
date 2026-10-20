#include "coh_walk.h"
#include "source_math.h"
#include "source_types.h"
#include <limits.h>
#define WORLD_MAGIC 0x434f4857u
typedef struct { CTri ctri; Vec3 vertices[3],lo,hi; } PreparedTriangle;
typedef struct { uint32_t magic,count; PreparedTriangle triangle[]; } PreparedWorld;
_Thread_local CollInfo last_surf;
_Thread_local int landed_on_ground;
_Thread_local struct CohSourceScene scene_info;
static _Thread_local const CohWalkWorld *active_world;
static _Thread_local uint32_t queries,tests;
static _Thread_local uint32_t contact_hits,wall_hits,ground_hits;
static _Thread_local int velocity_only;
static _Thread_local int transcript_only,transcript_fallback;
static _Thread_local uint32_t transcript_count,transcript_query,transcript_grid;
static _Thread_local float transcript_contacts[9];
static int finite_vec(const float v[3]) { unsigned i;if(!v)return 0;
    for(i=0;i<3;i++)if(!isfinite(v[i])||fabsf(v[i])>1000000.f)return 0;
    return 1; }
static const PreparedWorld *valid_world(const CohWalkWorld *world) {
    const PreparedWorld *p;unsigned i;
    if(!world||!world->prepared||!world->triangle_count||world->triangle_count>COH_WALK_MAX_TRIANGLES)return NULL;
    p=world->prepared;if(p->magic!=WORLD_MAGIC||p->count!=world->triangle_count)return NULL;
    if(!finite_vec(world->bounds_min)||!finite_vec(world->bounds_max))return NULL;
    for(i=0;i<3;i++)if(world->bounds_max[i]<world->bounds_min[i]||world->bounds_max[i]-world->bounds_min[i]>16384)return NULL;
    return p;
}
int coh_walk_world_init(CohWalkWorld *world,const CohWalkTriangle *triangles,uint32_t count,const float lo[3],const float hi[3]) {
    CohWalkWorld next={0};PreparedWorld *p;unsigned i,j,k;uint32_t flags_mask=(1u<<27)-1;
    if(!world||world->prepared||!triangles||!count||count>COH_WALK_MAX_TRIANGLES||!finite_vec(lo)||!finite_vec(hi))return 0;
    for(j=0;j<3;j++)if(hi[j]<lo[j]||hi[j]-lo[j]>16384)return 0;
    for(i=0;i<count;i++){
        if(triangles[i].flags&~flags_mask)return 0;
        for(j=0;j<3;j++)for(k=0;k<3;k++)if(!isfinite(triangles[i].v[j][k])||triangles[i].v[j][k]<lo[k]-.01f||triangles[i].v[j][k]>hi[k]+.01f)return 0;
    }
    p=calloc(1,sizeof(*p)+(size_t)count*sizeof(p->triangle[0]));if(!p)return 0;p->magic=WORLD_MAGIC;p->count=count;
    for(i=0;i<count;i++){
        PreparedTriangle *t=&p->triangle[i];memcpy(t->vertices,triangles[i].v,sizeof(t->vertices));
        for(k=0;k<3;k++){t->lo[k]=t->hi[k]=t->vertices[0][k];for(j=1;j<3;j++){t->lo[k]=MIN(t->lo[k],t->vertices[j][k]);t->hi[k]=MAX(t->hi[k],t->vertices[j][k]);}}
        if(createCTri(&t->ctri,t->vertices[0],t->vertices[1],t->vertices[2])){
            t->ctri.flags=triangles[i].flags;if(t->ctri.flags&(COH_WALK_NORMALTRI|COH_WALK_NOTSELECTABLE))next.collision_count++;
        }
    }
    if(!next.collision_count){free(p);return 0;}next.prepared=p;next.triangle_count=count;copyVec3(lo,next.bounds_min);copyVec3(hi,next.bounds_max);*world=next;return 1;
}
size_t coh_walk_world_owned_bytes(const CohWalkWorld *world){const PreparedWorld*p=valid_world(world);return p?sizeof(*p)+(size_t)p->count*sizeof(p->triangle[0]):0;}
void coh_walk_world_destroy(CohWalkWorld *world){if(!world)return;if(world->prepared){PreparedWorld *p=world->prepared;if(p->magic==WORLD_MAGIC){p->magic=0;free(p);}}memset(world,0,sizeof(*world));}
/* Bounded broadphase replaces tracker/grid traversal; triangle creation,
 * radius query, cylinder caps and closest-start law are original source.
 * World-space authored vertices share precisely the rendered transforms. */
int collGrid(void *grid,const Vec3 start,const Vec3 end,CollInfo *coll,float radius,int flags) {
    const PreparedWorld *p=valid_world(active_world);Vec3 delta,a,b;uint32_t i;int hit=0;(void)grid;
    if(transcript_only){transcript_grid++;memset(coll,0,sizeof(*coll));return transcript_fallback;}
    memset(coll,0,sizeof(*coll));coll->sqdist=8e16f;copyVec3(start,coll->start);copyVec3(end,coll->end);coll->radius=radius;
    coll->flags=flags|COLL_NORMALTRI;subVec3(end,start,delta);float len=lengthVec3(delta);
    coll->tri_state.inv_linemag=len>0?1.f/len:1.f;coll->tri_state.linelen=len;coll->tri_state.linelen2=len*.5f;
    coll->tri_state.early_exit=!(flags&(COLL_BOTHSIDES|COLL_DISTFROMCENTER));
    if(!p||!isfinite(radius)||radius<0||radius>16||!finite_vec(start)||!finite_vec(end))return 0;
    if(queries<UINT32_MAX)queries++;
    for(i=0;i<p->count;i++){
        PreparedTriangle *t=(PreparedTriangle *)&p->triangle[i];Vec3 contact;float sqdist;unsigned k;
        if(!(t->ctri.flags&coll->flags))continue;
        for(k=0;k<3;k++)if(MAX(start[k],end[k])+radius<t->lo[k]||MIN(start[k],end[k])-radius>t->hi[k])break;
        if(k<3)continue;
        if(tests<UINT32_MAX)tests++;
        copyVec3(start,a);copyVec3(end,b);sqdist=ctriCollideRad(&t->ctri,a,b,contact,radius,&coll->tri_state);
        if(sqdist<0||!isfinite(sqdist)||!finite_vec(contact))continue;
        if(flags&COLL_CYLINDER){Vec3 vertices[3];float radial=0;int ret;expandCtriVerts(&t->ctri,vertices);
            ret=ctriCylCheck(contact,a,b,radius,vertices,&radial);if(!ret)continue;if(ret>0&&(flags&COLL_DISTFROMSTART))sqdist=radial;}
        if(flags&COLL_DISTFROMSTARTEXACT){Vec3 vertices[3];Mat4 ident;memcpy(ident,unitmat,sizeof(ident));expandCtriVerts(&t->ctri,vertices);
            sqdist=ctriGetPointClosestToStart(contact,a,b,radius,vertices,t->ctri.norm,ident);}
        if(flags&COLL_DISTFROMSTART){float line_distance=sqdist;subVec3(contact,start,delta);sqdist=lengthVec3Squared(delta)-line_distance;
            if(sqdist<0)sqdist=0;
            float d=sqrtf(sqdist)+(1-t->ctri.norm[1])/64.f;sqdist=d*d;}
        if(!isfinite(sqdist)||!finite_vec(contact))continue;
        if(sqdist<coll->sqdist){coll->sqdist=sqdist;coll->ctri=&t->ctri;copyVec3(contact,coll->mat[3]);
            copyVec3(t->ctri.norm,coll->mat[1]);coll->tri_idx=(int)i;coll->backside=coll->tri_state.backside;hit=1;if(flags&COLL_HITANY)break;}
    }
    if(hit){if(contact_hits<UINT32_MAX)contact_hits++;
        if(flags&COLL_CYLINDER){if(wall_hits<UINT32_MAX)wall_hits++;}
        else if(coll->mat[1][1]>.3f&&ground_hits<UINT32_MAX)ground_hits++;}
    return hit;
}
int collide(Vec3 start,Vec3 end,CollInfo *coll,float radius,U32 flags){
    if(transcript_only){uint32_t n=transcript_query++;memset(coll,0,sizeof(*coll));if(n<transcript_count){copyVec3(transcript_contacts+3*n,coll->mat[3]);return 1;}return 0;}
    return collGrid(NULL,start,end,coll,radius,(int)(flags|COLL_NOTSELECTABLE));}
void entUpdatePosInterpolated(Entity *e,const Vec3 pos){copyVec3(pos,e->pos);}
int checkEntColl(Entity *e,int bounce,const Mat3 controls){(void)e;(void)bounce;(void)controls;return 0;}
void entWorldMoveMe(Entity *e,SurfaceParams *surf){if(!velocity_only)source_entWorldMoveMe(e,surf);}
static int ground_at(const CohWalkWorld *world,const float at[3],CollInfo *coll) {
    Vec3 top,bot;active_world=world;copyVec3(at,top);copyVec3(at,bot);top[1]+=2.5f;bot[1]-=.1f;
    if(!collGrid(NULL,top,bot,coll,1.f,COLL_DISTFROMSTART|COLL_NOTSELECTABLE))return 0;
    return coll->mat[1][1]>.3f&&fabsf(coll->mat[3][1]-at[1])<=1.5f;
}
int coh_walk_init(CohWalkState *state,const CohWalkWorld *world,const float spawn[3],float yaw) {
    CohWalkState n={0};CollInfo ground;unsigned i;const PreparedWorld *p=valid_world(world);
    if(!state||!p||!finite_vec(spawn)||!coh_motion_init(&n.controls,spawn,yaw,8192))return 0;
    for(i=0;i<3;i++)if(spawn[i]<world->bounds_min[i]-.01f||spawn[i]>world->bounds_max[i]+(i==1?6.01f:.01f))return 0;
    queries=tests=contact_hits=wall_hits=ground_hits=0;if(!ground_at(world,spawn,&ground))return 0;
    copyVec3(spawn,n.position);n.position[1]=ground.mat[3][1];copyVec3(n.position,n.physics.last_pos);
    copyVec3(ground.mat[1],n.physics.surf_normal);copyVec3(ground.mat[1],n.physics.last_surf_normal);copyVec3(ground.mat[1],n.physics.prev_surf_normal);
    n.physics.last_surf_type=SURFTYPE_GROUND;n.physics.lastSurfFlags=(int)ground.ctri->flags;n.physics.lastGroundSurfFlags=n.physics.lastSurfFlags;
    n.physics.on_surf=n.physics.was_on_surf=1;n.physics.highest_height=n.position[1];n.grounded=1;
    for(i=0;i<2;i++)n.physics.input.surf_mods[i]=(SurfaceParams){1,1,1,1,1};
    n.collision_queries=queries;n.triangle_tests=tests;n.contact_hits=contact_hits;
    n.wall_hits=wall_hits;n.ground_hits=ground_hits;*state=n;return 1;
}
static int valid_state(const CohWalkState *s) {
    unsigned i,j;if(!s||!finite_vec(s->position)||!finite_vec(s->physics.vel)||!finite_vec(s->physics.last_pos)||
        !finite_vec(s->physics.surf_normal)||!finite_vec(s->physics.last_surf_normal)||!finite_vec(s->physics.prev_surf_normal)||
        s->grounded>1||s->blocked>1||s->sliding>1||s->physics.falling>1||s->physics.on_surf>1||s->physics.was_on_surf>1||
        s->physics.input.flying||s->physics.input.no_slide_physics||s->physics.input.no_ent_collision||s->physics.input.stunned||s->physics.input.jump_released||
        s->physics.jumping||s->physics.input.vel[1]||s->physics.hitStumbleTractionLoss||s->physics.low_traction_steps_remaining||
        s->physics.jump_held>1||s->physics.on_poly_edge>1||s->physics.last_surf_type<0||s->physics.last_surf_type>1||
        (s->physics.input.max_speed_scale!=0&&s->physics.input.max_speed_scale!=1)||
        !isfinite(s->physics.highest_height)||fabsf(s->physics.highest_height)>1000000||
        s->physics.tickCounter!=s->ticks||s->controls.ticks!=s->ticks||s->ticks>=128848016)return 0;
    for(i=0;i<2;i++){
        const float *mods=(const float *)&s->physics.input.surf_mods[i];
        for(j=0;j<5;j++)if(mods[j]!=1)return 0;
    }
    for(i=0;i<3;i++)if(fabsf(s->physics.vel[i])>10||fabsf(s->physics.last_pos[i]-s->position[i])>.01f||
        fabsf(s->physics.surf_normal[i])>1.001f||fabsf(s->physics.last_surf_normal[i])>1.001f||fabsf(s->physics.prev_surf_normal[i])>1.001f||
        !isfinite(s->physics.input.vel[i])||fabsf(s->physics.input.vel[i])>1.001f||s->physics.addedVel[i])return 0;
    return 1;
}
int coh_walk_step(CohWalkState *state,const CohWalkWorld *world,uint32_t directions,float yaw) {
    CohWalkState n;Entity e;CTri prior={0};unsigned i,j;float timestep=1.f;int numsteps;Vec3 start,delta;uint32_t q,t;
    if(!valid_world(world)||!valid_state(state))return 0;
    n=*state;
    if(!coh_motion_step(&n.controls,directions,yaw))return 0;
    n.physics.input.max_speed_scale=1.f;copyVec3(n.controls.world_input,n.physics.input.vel); /* neutral original server speed modifiers */
    active_world=world;queries=tests=contact_hits=wall_hits=ground_hits=0;velocity_only=0;landed_on_ground=0;
    memset(&last_surf,0,sizeof(last_surf));prior.flags=(uint32_t)n.physics.lastSurfFlags;
    last_surf.ctri=n.physics.on_surf?&prior:NULL;copyVec3(n.physics.last_surf_normal,last_surf.mat[1]);
    scene_info.minHeight=-1000000.f;scene_info.maxHeight=world->bounds_max[1]+6.f;
    e=(Entity){&n.physics,1.f,{0,0,0}};copyVec3(n.position,e.pos);copyVec3(n.position,start);
    /* Original DoPhysics bounded substep rule, at most five. */
    float mag=lengthVec3(n.physics.vel);numsteps=(mag<1.f)?1:(int)(mag+.99f);if(numsteps>5)numsteps=5;
    e.timestep=timestep/numsteps;
    for(i=0;i<(unsigned)numsteps;i++)entWorldCollide(&e,unitmat);
    copyVec3(e.pos,n.position);n.ticks++;n.physics.tickCounter++;n.grounded=!n.physics.falling&&n.physics.surf_normal[1]>.3f;
    n.blocked=n.physics.stuck_head!=0;n.sliding=0;
    subVec3(n.position,start,delta);float expected=lengthVec3XZ(n.physics.input.vel),actual=lengthVec3XZ(delta);
    if(wall_hits&&expected>.01f&&actual<expected*.45f)n.blocked=1;
    if(wall_hits&&expected>.01f&&actual>.01f&&dotVec3(delta,n.physics.input.vel)<actual*expected*.98f){n.sliding=1;n.blocked=1;}
    /* Explicit fixture boundary: absent ground/bounds never create a floor or
     * carry the offline actor away into a full-map streaming hole. */
    int bounded=0;for(j=0;j<3;j++)if(!isfinite(n.position[j])||n.position[j]<world->bounds_min[j]-.01f||n.position[j]>world->bounds_max[j]+(j==1?6.f:.01f))bounded=1;
    if(bounded){copyVec3(start,n.position);copyVec3(start,n.physics.last_pos);zeroVec3(n.physics.vel);n.blocked=1;n.sliding=0;
        n.physics.falling=state->physics.falling;n.physics.on_surf=state->physics.on_surf;copyVec3(state->physics.surf_normal,n.physics.surf_normal);n.grounded=state->grounded;
        if(n.bounded_steps<UINT32_MAX)n.bounded_steps++;}
    for(j=0;j<3;j++)if(fabsf(n.physics.vel[j])<.00001f)n.physics.vel[j]=0;
    if(!valid_state(&n))return 0;
    if(n.grounded&&n.grounded_steps<UINT32_MAX)n.grounded_steps++;
    if(n.blocked&&n.blocked_steps<UINT32_MAX)n.blocked_steps++;
    if(n.sliding&&n.slide_steps<UINT32_MAX)n.slide_steps++;
    q=queries;t=tests;n.collision_queries=UINT32_MAX-n.collision_queries<q?UINT32_MAX:n.collision_queries+q;
    n.triangle_tests=UINT32_MAX-n.triangle_tests<t?UINT32_MAX:n.triangle_tests+t;
    n.contact_hits=UINT32_MAX-n.contact_hits<contact_hits?UINT32_MAX:n.contact_hits+contact_hits;
    n.wall_hits=UINT32_MAX-n.wall_hits<wall_hits?UINT32_MAX:n.wall_hits+wall_hits;
    n.ground_hits=UINT32_MAX-n.ground_hits<ground_hits?UINT32_MAX:n.ground_hits+ground_hits;
    *state=n;return 1;
}
void coh_walk_clear(CohWalkState *state){if(!state)return;coh_motion_clear(&state->controls);zeroVec3(state->physics.input.vel);zeroVec3(state->physics.vel);state->blocked=state->sliding=0;}
/* Internal host witness entry point: source velocity before geometry callbacks. */
void coh_walk_velocity_probe(float timestep,unsigned flags,unsigned bits,const float input[3],const float velocity[3],const float normal[3],float out[3]) {
    MotionState m={0};Entity e={&m,timestep,{0,0,0}};CTri tri={0};unsigned i;tri.flags=flags;
    for(i=0;i<2;i++)m.input.surf_mods[i]=(SurfaceParams){1,1,1,1,1};
    m.falling=!!(bits&1);m.on_surf=!!(bits&2);m.input.flying=!!(bits&4);
    m.low_traction_steps_remaining=!!(bits&8);m.was_on_surf=!!(bits&16);m.jump_held=!!(bits&32);
    m.last_surf_type=SURFTYPE_GROUND;m.lastSurfFlags=m.lastGroundSurfFlags=(int)flags;copyVec3(input,m.input.vel);copyVec3(velocity,m.vel);
    copyVec3(normal,m.surf_normal);copyVec3(normal,m.last_surf_normal);copyVec3(normal,m.prev_surf_normal);
    memset(&last_surf,0,sizeof(last_surf));last_surf.ctri=m.on_surf?&tri:NULL;copyVec3(normal,last_surf.mat[1]);
    velocity_only=1;entWorldCollide(&e,unitmat);velocity_only=0;copyVec3(m.vel,out);
}
extern int coh_walk_source_slide(Entity *e,Vec3 top,Vec3 bot);
void coh_walk_slide_probe(const float topin[3],const float botin[3],const float velin[3],unsigned count,const float contacts[9],int fallback,float out[9],unsigned status[4]) {
    MotionState m={0};Entity e={&m,1.f,{0,0,0}};Vec3 top,bot;copyVec3(topin,top);copyVec3(botin,bot);copyVec3(velin,m.vel);
    transcript_only=1;transcript_count=MIN(count,3);transcript_query=transcript_grid=0;transcript_fallback=fallback;memcpy(transcript_contacts,contacts,sizeof(transcript_contacts));
    memset(&last_surf,0,sizeof(last_surf));m.last_surf_type=SURFTYPE_GROUND;int ret=coh_walk_source_slide(&e,top,bot);
    copyVec3(top,out);copyVec3(bot,out+3);copyVec3(m.vel,out+6);status[0]=(unsigned)ret;status[1]=transcript_query;status[2]=transcript_grid;status[3]=(unsigned)m.last_surf_type;transcript_only=0;
}
