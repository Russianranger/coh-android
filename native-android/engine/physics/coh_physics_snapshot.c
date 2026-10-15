#include "coh_physics_snapshot.h"
#include <math.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <limits.h>
#define SNAPSHOT_MAGIC 0x50535933u
struct CohPhysicsSnapshot {
    uint32_t magic;
    atomic_uint references;
    CohPhysicsScene *scene;
    CohPhysicsCoverageGrid grid;
    CohPhysicsCoverageCell *cells;
    CohPhysicsSnapshotInfo info;
};
static int bounded(float v){return isfinite(v)&&fabsf(v)<=1000000.f;}
static int valid(const CohPhysicsSnapshot *s){return s&&s->magic==SNAPSHOT_MAGIC;}
static int cancelled(const CohCancel *c){return c&&c->poll&&c->poll(c->context);}
CohStatus coh_physics_snapshot_create(CohPhysicsSnapshot **out,
    const CohPhysicsSegment *segments,uint32_t count,uint32_t generation,
    const CohPhysicsCoverageGrid *g,size_t limit,const CohCancel *cancel){
    CohPhysicsSnapshot *s;size_t cells,bytes;uint32_t i,j;CohStatus status;
    if(!out||*out||!segments||!count||count>COH_PHYSICS_MAX_SEGMENTS||!generation||!g||!g->cells||
       !g->columns||!g->rows||g->columns>COH_PHYSICS_MAX_COVERAGE_CELLS/g->rows||
       !bounded(g->origin_x)||!bounded(g->origin_z)||!bounded(g->cell_size)||g->cell_size<=0||
       !bounded(g->min_y)||!bounded(g->max_y)||g->min_y>=g->max_y||
       !bounded(g->origin_x+(float)g->columns*g->cell_size)||
       !bounded(g->origin_z+(float)g->rows*g->cell_size)||
       g->origin_x+(float)g->columns*g->cell_size<=g->origin_x||
       g->origin_z+(float)g->rows*g->cell_size<=g->origin_z)return COH_INVALID;
    cells=(size_t)g->columns*g->rows;bytes=sizeof(*s)+cells*sizeof(*s->cells);
    if(bytes>limit)return COH_LIMIT;
    for(i=0;i<cells;i++){
        const CohPhysicsCoverageCell *c=&g->cells[i];
        if(cancelled(cancel))return COH_CANCELLED;
        if(c->state>COH_PHYSICS_CELL_LOADED)return COH_INVALID;
        if(c->state!=COH_PHYSICS_CELL_LOADED){if(c->segment||c->generation)return COH_INVALID;continue;}
        for(j=0;j<count;j++)if(segments[j].id==c->segment&&segments[j].generation==c->generation)break;
        if(j==count||!c->segment||!c->generation)return COH_NOT_FOUND;
    }
    s=calloc(1,sizeof(*s));if(!s)return COH_IO;
    s->cells=malloc(cells*sizeof(*s->cells));if(!s->cells){free(s);return COH_IO;}
    status=coh_physics_scene_create(&s->scene,segments,count,generation,limit-bytes,cancel);
    if(status!=COH_OK){free(s->cells);free(s);return status;}
    for(i=0;i<cells;i++){
        s->cells[i]=g->cells[i];
        if(s->cells[i].state==COH_PHYSICS_CELL_LOADED)s->info.loaded_cells++;
        else if(s->cells[i].state==COH_PHYSICS_CELL_EMPTY)s->info.empty_cells++;
        else s->info.missing_cells++;
    }
    s->grid=*g;s->grid.cells=s->cells;s->magic=SNAPSHOT_MAGIC;atomic_init(&s->references,1);
    coh_physics_scene_info(s->scene,&s->info.scene);
    s->info.columns=g->columns;s->info.rows=g->rows;
    s->info.owned_bytes=bytes+s->info.scene.owned_bytes;
    if(cancelled(cancel)){coh_physics_snapshot_release(s);return COH_CANCELLED;}
    *out=s;return COH_OK;
}
CohStatus coh_physics_snapshot_retain(CohPhysicsSnapshot *s){
    unsigned refs;if(!valid(s))return COH_INVALID;
    refs=atomic_load_explicit(&s->references,memory_order_relaxed);
    do{if(!refs)return COH_STATE;if(refs==UINT_MAX)return COH_LIMIT;}
    while(!atomic_compare_exchange_weak_explicit(&s->references,&refs,refs+1,memory_order_relaxed,memory_order_relaxed));
    return COH_OK;
}
void coh_physics_snapshot_release(CohPhysicsSnapshot *s){
    if(!valid(s))return;
    if(atomic_fetch_sub_explicit(&s->references,1,memory_order_acq_rel)!=1)return;
    s->magic=0;coh_physics_scene_destroy(s->scene);free(s->cells);free(s);
}
CohStatus coh_physics_snapshot_info(const CohPhysicsSnapshot *s,CohPhysicsSnapshotInfo *out){
    if(!valid(s)||!out)return COH_INVALID;*out=s->info;return COH_OK;
}
static CohStatus admit(const CohPhysicsSnapshot *s,const float lo[3],const float hi[3],CohPhysicsAdmission *out){
    CohPhysicsAdmission a={0};double x0,x1,z0,z1;uint32_t minx,maxx,minz,maxz,x,z;
    if(out)*out=a;
    if(!valid(s))return COH_INVALID;
    for(x=0;x<3;x++)if(!bounded(lo[x])||!bounded(hi[x])||lo[x]>hi[x])return COH_INVALID;
    if(lo[1]<s->grid.min_y||hi[1]>s->grid.max_y)return COH_NOT_FOUND;
    x0=((double)lo[0]-s->grid.origin_x)/s->grid.cell_size;x1=((double)hi[0]-s->grid.origin_x)/s->grid.cell_size;
    z0=((double)lo[2]-s->grid.origin_z)/s->grid.cell_size;z1=((double)hi[2]-s->grid.origin_z)/s->grid.cell_size;
    if(x0<=0||z0<=0||x1>=s->grid.columns||z1>=s->grid.rows)return COH_NOT_FOUND;
    minx=(uint32_t)floor(x0);maxx=(uint32_t)floor(x1);
    minz=(uint32_t)floor(z0);maxz=(uint32_t)floor(z1);
    /* The lower edge is closed too. Include the preceding cell at exact seams. */
    if(minx&&x0==(double)minx)minx--;
    if(minz&&z0==(double)minz)minz--;
    for(z=minz;z<=maxz;z++)for(x=minx;x<=maxx;x++){
        a.cells_checked++;
        if(s->cells[(size_t)z*s->grid.columns+x].state==COH_PHYSICS_CELL_MISSING)a.missing_cells++;
    }
    if(out)*out=a;return a.missing_cells?COH_NOT_FOUND:COH_OK;
}
CohStatus coh_physics_snapshot_query(const CohPhysicsSnapshot *s,const float start[3],const float end[3],
    float radius,uint32_t flags,CohPhysicsBudget budget,CohPhysicsContact *out,CohPhysicsQueryStats *stats,
    CohPhysicsAdmission *admission){
    float lo[3],hi[3];unsigned k;CohStatus status;
    if(stats)*stats=(CohPhysicsQueryStats){0};if(admission)*admission=(CohPhysicsAdmission){0};
    if(!start||!end||!out||!isfinite(radius)||radius<0||radius>16)return COH_INVALID;
    for(k=0;k<3;k++){if(!bounded(start[k])||!bounded(end[k]))return COH_INVALID;
        lo[k]=fminf(start[k],end[k])-radius;hi[k]=fmaxf(start[k],end[k])+radius;}
    status=admit(s,lo,hi,admission);if(status!=COH_OK)return status;
    return coh_physics_query(s->scene,start,end,radius,flags,budget,out,stats);
}
CohStatus coh_physics_snapshot_walker_prepare(CohPhysicsWalker *w,const CohPhysicsSnapshot *s,
    const float center[3],const float extents[3],const float spawn[3],float yaw,CohPhysicsBudget budget,
    const CohCancel *cancel,CohPhysicsAdmission *admission){
    float lo[3],hi[3];unsigned k;CohStatus status;
    if(admission)*admission=(CohPhysicsAdmission){0};
    if(!w||!center||!extents||!spawn||!isfinite(yaw)||!budget.max_nodes||!budget.max_triangles)return COH_INVALID;
    for(k=0;k<3;k++){
        if(!bounded(center[k])||!bounded(extents[k])||!bounded(spawn[k])||extents[k]<32||extents[k]>4096)return COH_INVALID;
        lo[k]=center[k]-extents[k];hi[k]=center[k]+extents[k];}
    if(cancelled(cancel))return COH_CANCELLED;
    status=admit(s,lo,hi,admission);if(status!=COH_OK)return status;
    return coh_physics_walker_prepare(w,s->scene,center,extents,spawn,yaw,budget,cancel);
}
