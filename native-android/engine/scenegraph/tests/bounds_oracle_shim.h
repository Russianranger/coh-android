#include "coh_group_bounds.h"
#include <math.h>
#include <string.h>
typedef float Vec3[3];
typedef float Mat4[4][3];
typedef float F32;
typedef struct Model { Vec3 min,max; } Model;
typedef struct GroupDef GroupDef;
typedef struct GroupEnt { GroupDef *def; Mat4 mat; } GroupEnt;
struct GroupDef { Vec3 min,max,mid,box_scale; float radius; int count,has_volume,pre_alloc,bounds_valid; Model *model; GroupEnt *entries; };
static float rad_count,box_count;
#define CLIENT 1
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define setVec3(v,a,b,c) ((v)[0]=(a),(v)[1]=(b),(v)[2]=(c))
#define copyVec3(a,b) memcpy((b),(a),sizeof(Vec3))
#define zeroVec3(v) memset((v),0,sizeof(Vec3))
#define subVec3(a,b,c) ((c)[0]=(a)[0]-(b)[0],(c)[1]=(a)[1]-(b)[1],(c)[2]=(a)[2]-(b)[2])
#define addVec3(a,b,c) ((c)[0]=(a)[0]+(b)[0],(c)[1]=(a)[1]+(b)[1],(c)[2]=(a)[2]+(b)[2])
#define scaleVec3(a,s,b) ((b)[0]=(a)[0]*(s),(b)[1]=(a)[1]*(s),(b)[2]=(a)[2]*(s))
#define SQR(a) ((a)*(a))
#define lengthVec3(v) ((float)sqrt(SQR((v)[0])+SQR((v)[1])+SQR((v)[2])))
#define INLINEDBG
