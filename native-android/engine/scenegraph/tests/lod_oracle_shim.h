#include "coh_group_lod.h"
#include <math.h>
#include <string.h>
typedef float F32;
typedef float Vec3[3];
typedef struct Model {Vec3 min,max;} Model;
typedef struct GroupDef {
 float lod_near,lod_nearfade,lod_far,lod_farfade,lod_scale,shadow_dist;
 unsigned lod_fromfile,lod_fromtrick,lod_autogen;
 struct {float lod_far,lod_farfade,lod_scale;} from_file;
 Model *model;
} GroupDef;
#define subVec3(a,b,c) ((c)[0]=(a)[0]-(b)[0],(c)[1]=(a)[1]-(b)[1],(c)[2]=(a)[2]-(b)[2])
#define SQR(a) ((a)*(a))
#define lengthVec3(v) ((float)sqrt(SQR((v)[0])+SQR((v)[1])+SQR((v)[2])))
