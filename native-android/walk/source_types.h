#ifndef COH_WALK_SOURCE_TYPES_H
#define COH_WALK_SOURCE_TYPES_H
#include "coh_walk.h"
#include "source_math.h"
#include <stdlib.h>
typedef CohWalkSurface SurfaceParams;
typedef CohWalkPhysics MotionState;
typedef struct { MotionState *motion; float timestep; Vec3 pos; } Entity;
#define ENTPOS(e) ((e)->pos)
#define ENTPOSY(e) ((e)->pos[1])
#define STUCK_SLIDE 1
#define STUCK_COMPLETELY 2
typedef struct { Vec3 V1; float v2[2],v3[2],midpt[2],extents[2];
    Vec3 norm; float scale; U32 flags; void *surfTex; } CTri;
typedef struct { float inv_linemag,linelen2,linelen; uint8_t backside,early_exit; } CtriState;
typedef struct { Mat4 mat; float sqdist; CTri *ctri; int flags,node,tri_idx,backside;
    float radius; Vec3 start,end; CtriState tri_state;
    void *tri_colls; int coll_count,coll_max; } CollInfo;
enum { COLL_DISTFROMSTART=1<<0,COLL_DISTFROMCENTER=1<<1,COLL_HITANY=1<<2,
    COLL_PORTAL=1<<5,COLL_EDITONLY=1<<6,COLL_BOTHSIDES=1<<7,
    COLL_CYLINDER=1<<8,COLL_ENTBLOCKER=1<<9,COLL_PLAYERSELECT=1<<10,
    COLL_NORMALTRI=1<<11,COLL_DISTFROMSTARTEXACT=1<<16,
    COLL_NOTSELECTABLE=1<<19 };
extern _Thread_local CollInfo last_surf;
extern _Thread_local int landed_on_ground;
extern _Thread_local struct CohSourceScene { float minHeight,maxHeight; } scene_info;
void entUpdatePosInterpolated(Entity *e,const Vec3 pos);
int collide(Vec3 start,Vec3 end,CollInfo *coll,float rad,U32 flags);
int collGrid(void *grid,const Vec3 start,const Vec3 end,CollInfo *coll,float rad,int flags);
int checkEntColl(Entity *e,int bounce,const Mat3 controls);
void entWorldGetSurface(Entity *e,SurfaceParams *surf);
SurfaceParams *entWorldGetSurfaceModifier(Entity *e);
void entWorldApplySurfMods(SurfaceParams *mod,SurfaceParams *surf);
void entWorldApplyTextureOverrides(SurfaceParams *surf,int flags);
void source_entWorldMoveMe(Entity *e,SurfaceParams *surf);
void entWorldMoveMe(Entity *e,SurfaceParams *surf);
void entWorldCollide(Entity *e,const Mat3 controls);
void expandCtriVerts(CTri *tri,Vec3 verts[3]);
void normScaleToMat(Vec3 normal,float scale,Mat3 mat);
int createCTri(CTri *tri,Vec3 a,Vec3 b,Vec3 c);
float ctriCollideRad(CTri *tri,Vec3 a,Vec3 b,Vec3 col,float radius,CtriState *state);
int ctriCylCheck(Vec3 hit,Vec3 start,Vec3 end,float radius,Vec3 vertices[3],float *distance);
float ctriGetPointClosestToStart(Vec3 hit,Vec3 start,Vec3 end,float radius,Vec3 vertices[3],Vec3 norm,Mat4 transform);
int tri_tri_intersect_with_isectline(float a[3],float b[3],float c[3],float d[3],float e[3],float f[3],int *coplanar,float out1[3],float out2[3]);
#endif
