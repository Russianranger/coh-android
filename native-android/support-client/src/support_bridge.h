#ifndef COH_SUPPORT_BRIDGE_H
#define COH_SUPPORT_BRIDGE_H
#include <android/asset_manager.h>
#include "coh_animation.h"
#include "coh_mesh.h"
#include "coh_walk.h"
typedef struct SupportBridge SupportBridge;
SupportBridge *support_bridge_create(const CohWalkTriangle*,unsigned,const float[3],float,unsigned);
/* Success frees and nulls the owner. A failed audio close retains the complete
 * bridge and its borrowed manager/scene dependencies for serialized retry. */
int support_bridge_destroy(SupportBridge**);
int support_bridge_configure(SupportBridge*,AAssetManager*,const void *clips[3],const size_t sizes[3]);
void support_bridge_foreground(SupportBridge*,int);
int support_bridge_walk(SupportBridge*,unsigned,float,CohWalkState*);
void support_bridge_reset(SupportBridge*,const float[3],float,CohWalkState*);
void support_bridge_clear(SupportBridge*);
int support_bridge_pose(SupportBridge*,float,CohAnimationPose*,const CohAnimationRig**);
const CohSkinnedVertex *support_bridge_skin(SupportBridge*,unsigned,const CohMeshVertex*,unsigned,const float*,unsigned);
void support_bridge_surface_begin(SupportBridge*,unsigned);
int support_bridge_draw(SupportBridge*,int,int,unsigned);
void support_bridge_surface_end(SupportBridge*);
void support_bridge_frame_begin(SupportBridge*);
void support_bridge_frame_end(SupportBridge*);
void support_bridge_trigger(SupportBridge*);
int support_bridge_touch(SupportBridge*,int,unsigned,float,float);
int support_bridge_key(SupportBridge*,int,int,int,int);
void support_bridge_text(SupportBridge*,const char*);
void support_bridge_snapshot(SupportBridge*,char*,size_t);
#endif
