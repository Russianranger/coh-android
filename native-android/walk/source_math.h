/* Portable arithmetic shim; original math functions retained below. */
#ifndef COH_WALK_SOURCE_MATH_H
#define COH_WALK_SOURCE_MATH_H
#include <stdint.h>
#include <string.h>
#include <math.h>
#define setVec3same(dst,a)            ((dst)[0] = (a), (dst)[1] = (a), (dst)[2] = (a))
#define lengthVec3SquaredXZ(v1)        (SQR((v1)[0]) + SQR((v1)[2]))
#define CLIENT 0
#define MDBG 0
#define INLINEDBG
#define SURFACE_GROUND 0
#define SURFACE_AIR 1
#define SURFTYPE_GROUND 1
#define SURFTYPE_WALL 0
#define COLL_SURFACESLICK (1u<<20)
#define COLL_SURFACEICY (1u<<21)
#define COLL_SURFACEBOUNCY (1u<<22)
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define SQR(a)        ((a)*(a))
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define MINMAX(a,min,max) ((a) < (min) ? (min) : (a) > (max) ? (max) : (a))
#define fsqrt(a)    (float)sqrt(a)
#define fatan2(y,x)    atan2(y,x)
#define copyVec3(src,dst)            (((dst)[0]) = ((src)[0]), ((dst)[1]) = ((src)[1]), ((dst)[2]) = ((src)[2])) 
#define zeroVec3(v1)                setVec3same(v1, 0)
#define scaleVec3(v1,s,r)            ((r)[0] = (v1)[0]*(s), (r)[1] = (v1)[1]*(s), (r)[2] = (v1)[2]*(s))
#define addVec3(v1,v2,r)            ((r)[0] = (v1)[0]+(v2)[0], (r)[1] = (v1)[1]+(v2)[1], (r)[2] = (v1)[2]+(v2)[2])
#define subVec3(v1,v2,r)            ((r)[0] = (v1)[0]-(v2)[0], (r)[1] = (v1)[1]-(v2)[1], (r)[2] = (v1)[2]-(v2)[2])
#define setVec3(dst,a,b,c)            ((dst)[0] = (a), (dst)[1] = (b), (dst)[2] = (c))
#define dotVec3(v1,v2)                ((v1)[0]*(v2)[0] + (v1)[1]*(v2)[1] + (v1)[2]*(v2)[2])
#define lengthVec3Squared(v1)        (SQR((v1)[0]) + SQR((v1)[1]) + SQR((v1)[2]))
#define lengthVec3(v1)                (fsqrt(lengthVec3Squared(v1)))
#define lengthVec3XZ(v1)            (fsqrt(lengthVec3SquaredXZ(v1)))
#define vec3IsZero(v)                ((v)[0] == 0 && (v)[1] == 0 && (v)[2] == 0)
#define sameVec3(v1,v2)                (((v1)[0]==(v2)[0]) && ((v1)[1]==(v2)[1]) && ((v1)[2]==(v2)[2]))
#define nearSameVec3(a,b) sameVec3((a),(b))

typedef float F32;typedef int32_t S32;typedef uint32_t U32;
typedef float Vec3[3];typedef float Mat3[3][3];typedef float Mat4[4][3];

#define MAX(a,b) max((a),(b))
#define MIN(a,b) min((a),(b))
#define TRUE 1
#define FALSE 0
#define copyMat3(a,b) memcpy((b),(a),sizeof(Mat3))
#define crossVec3(a,b,c) do{Vec3 cross_={(a)[1]*(b)[2]-(a)[2]*(b)[1],(a)[2]*(b)[0]-(a)[0]*(b)[2],(a)[0]*(b)[1]-(a)[1]*(b)[0]};copyVec3(cross_,(c));}while(0)
#define scaleAddVec3(a,s,b,c) do{float scale_=(s);Vec3 v_={(a)[0]*scale_+(b)[0],(a)[1]*scale_+(b)[1],(a)[2]*scale_+(b)[2]};copyVec3(v_,(c));}while(0)
#define vecX(v) ((v)[0])
#define vecY(v) ((v)[1])
#define vecZ(v) ((v)[2])
static const Vec3 zerovec3={0,0,0};
static const Mat4 unitmat={{1,0,0},{0,1,0},{0,0,1},{0,0,0}};
static inline void mathutil_sincosf(F32 a,F32*s,F32*c){*s=sinf(a);*c=cosf(a);}

static inline INLINEDBG F32 normalVec3(Vec3 v)
{
F32        mag2,mag,invmag;

    // Is there some way to let the compiler know to generate an atomic inverse
    // square root if the cpu supports it? (ie; sse, 3dnow, r10k, etc.)
    mag2 = SQR(v[0]) + SQR(v[1]) + SQR(v[2]);
    mag = fsqrt(mag2);

    if (mag > 0)
    {
        invmag = 1.f/mag;
        scaleVec3(v,invmag,v);
    }

    return(mag);
}
static inline INLINEDBG void mulVecMat3(const Vec3 vIn,const Mat3 mIn,Vec3 vOut)
{
    vOut[0] = vIn[0]*mIn[0][0] + vIn[1]*mIn[1][0] + vIn[2]*mIn[2][0];
    vOut[1] = vIn[0]*mIn[0][1] + vIn[1]*mIn[1][1] + vIn[2]*mIn[2][1];
    vOut[2] = vIn[0]*mIn[0][2] + vIn[1]*mIn[1][2] + vIn[2]*mIn[2][2];
}
static inline void getVec3YP(const Vec3 dvec,F32 *yawp,F32 *pitp)
{
F32        dist;
    
    *yawp = (F32)fatan2(dvec[0],dvec[2]);
    dist = fsqrt(SQR(dvec[0]) + SQR(dvec[2]));
    *pitp = (F32)fatan2(dvec[1],dist);
}
static inline void createMat3RYP(Mat3 mat,const F32 *pyr)
{
    F32 cosP,sinP,cosY,sinY,cosR,sinR,temp;

    mathutil_sincosf(pyr[0], &sinP, &cosP);
    mathutil_sincosf(pyr[1], &sinY, &cosY);
    mathutil_sincosf(pyr[2], &sinR, &cosR);

    temp =           cosR * sinY;
    mat[0][0] =     cosR * cosY;
    mat[1][0] =     sinR * cosP - temp * sinP;
    mat[2][0] =     sinR * sinP + temp * cosP;
    
    temp =          -sinR * sinY;
    mat[0][1] =  -sinR * cosY;
    mat[1][1] =  cosR * cosP - temp * sinP;
    mat[2][1] = cosR * sinP + temp * cosP;

    mat[0][2] = -sinY;
    mat[1][2] = cosY * -sinP;
    mat[2][2] = cosY * cosP;
}
static inline void camLookAt(const Vec3 lookdir, Mat3 mat)
{
    Vec3 dv;

    dv[2] = 0;
    getVec3YP(lookdir,&dv[1],&dv[0]);
    createMat3RYP(mat,dv);
}
static inline void transposeMat3Copy(const Mat3 uv,Mat3 uv2)
{
    uv2[0][0] = uv[0][0];
    uv2[0][1] = uv[1][0];
    uv2[0][2] = uv[2][0];

    uv2[1][0] = uv[0][1];
    uv2[1][1] = uv[1][1];
    uv2[1][2] = uv[2][1];

    uv2[2][0] = uv[0][2];
    uv2[2][1] = uv[1][2];
    uv2[2][2] = uv[2][2];
}
static inline void mulVecMat3Transpose( const Vec3 uvec, const Mat3 uvs,Vec3 bodvec)
{
    bodvec[0] = uvec[0]*uvs[0][0] + uvec[1]*uvs[0][1] + uvec[2]*uvs[0][2];
    bodvec[1] = uvec[0]*uvs[1][0] + uvec[1]*uvs[1][1] + uvec[2]*uvs[1][2];
    bodvec[2] = uvec[0]*uvs[2][0] + uvec[1]*uvs[2][1] + uvec[2]*uvs[2][2];
}
static inline void mulVecMat4(const Vec3 v,const Mat4 m,Vec3 out){Vec3 x;mulVecMat3(v,m,x);addVec3(x,m[3],out);}
static inline void moveVinX(Vec3 v,const Mat3 m,float d){scaleAddVec3(m[0],d,v,v);}
static inline void moveVinY(Vec3 v,const Mat3 m,float d){scaleAddVec3(m[1],d,v,v);}

static inline float distance3Squared(const Vec3 a,const Vec3 b){Vec3 d;subVec3(a,b,d);return lengthVec3Squared(d);}
#define nearf(a,b) (fabsf((a)-(b))<0.00001f)
static inline float det3Vec3(const Vec3 a,const Vec3 b,const Vec3 c){Vec3 d;crossVec3(b,c,d);return dotVec3(a,d);}
#endif
