/* Bounded Phase9 source world/camera adapter. Compile with -ffp-contract=off.
 * Arithmetic order follows pinned source kernels; unrelated original state is
 * excluded. References are never inputs to these runtime operations. */
#include "coh_world.h"
#include <math.h>
#include <string.h>
typedef float Mat4[4][3];
typedef float Mat3[3][3];
typedef float Mat44[4][4];
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float read_float(const uint8_t *p){uint32_t v=u32(p);float f;memcpy(&f,&v,4);return f;}
static int bounded(float f,float lo,float hi){return isfinite(f)&&f>=lo&&f<=hi;}
static int valid_node(const CohWorldNode *n,uint32_t i){
 if(n->parent!=(i?i-1u:UINT32_MAX))return 0;
 for(uint32_t j=0;j<3;j++)if(!bounded(n->position[j],-32768.f,32768.f)||!bounded(n->pyr_degrees[j],-360.f,360.f))return 0;
 return 1;
}
static int valid_camera(const CohWorldCamera *c){
 for(uint32_t j=0;j<3;j++)if(!bounded(c->position[j],-32768.f,32768.f)||!bounded(c->pyr_degrees[j],-360.f,360.f))return 0;
 return bounded(c->fovy,10.f,120.f)&&bounded(c->aspect,.25f,8.f)&&bounded(c->znear,.001f,100.f)&&bounded(c->zfar,c->znear+.001f,100000.f)&&c->flip_x<=1&&c->flip_y<=1;
}
int coh_world_parse_inputs(const uint8_t *b,size_t n,CohWorldInputs *out){
 if(!b||!out||n!=COH_WORLD_INPUT_BYTES||memcmp(b,"COHWRI09",8))return -1;
 const uint32_t expected[9]={1,64,6,6,64,232,520,28,48};
 for(uint32_t i=0;i<9;i++)if(u32(b+8+i*4)!=expected[i])return -2;
 for(uint32_t i=44;i<64;i++)if(b[i])return -2;
 CohWorldInputs candidate;memset(&candidate,0,sizeof candidate);
 for(uint32_t i=0;i<6;i++){
  const uint8_t *p=b+64+i*28;CohWorldNode *v=&candidate.nodes[i];v->parent=u32(p);
  for(uint32_t j=0;j<3;j++){v->position[j]=read_float(p+4+j*4);v->pyr_degrees[j]=read_float(p+16+j*4);}
  if(!valid_node(v,i))return -3;
 }
 for(uint32_t i=0;i<6;i++){
  const uint8_t *p=b+232+i*48;CohWorldCamera *c=&candidate.cameras[i];
  for(uint32_t j=0;j<3;j++){c->position[j]=read_float(p+j*4);c->pyr_degrees[j]=read_float(p+12+j*4);}
  c->fovy=read_float(p+24);c->aspect=read_float(p+28);c->znear=read_float(p+32);c->zfar=read_float(p+36);c->flip_x=u32(p+40);c->flip_y=u32(p+44);
  if(!valid_camera(c))return -4;
 }
 *out=candidate;return 0;
}
static void create_ypr(Mat3 mat,const float *pyr){
 float cosP,sinP,cosY,sinY,cosR,sinR,temp;
 sinP=sinf(pyr[0]);cosP=cosf(pyr[0]);sinY=sinf(pyr[1]);cosY=cosf(pyr[1]);sinR=sinf(pyr[2]);cosR=cosf(pyr[2]);
 temp=sinY*sinP;
 mat[0][0]=cosY*cosR+temp*sinR;mat[1][0]=cosY*sinR-temp*cosR;mat[2][0]=sinY*cosP;
 mat[0][1]=-cosP*sinR;mat[1][1]=cosP*cosR;mat[2][1]=sinP;
 temp=-cosY*sinP;
 mat[0][2]=-sinY*cosR-temp*sinR;mat[1][2]=-sinY*sinR+temp*cosR;mat[2][2]=cosY*cosP;
}
static void source_local(const float *pos,const float *deg,Mat4 m){
 float pyr[3];for(uint32_t i=0;i<3;i++)pyr[i]=(float)(((double)deg[i]*3.14159265358979323846)*(1.0f/180.0f));
 create_ypr(m,pyr);memcpy(m[3],pos,12);
}
static void multiply(const Mat4 a,const Mat4 b,Mat4 c){
 for(uint32_t i=0;i<3;i++)for(uint32_t j=0;j<3;j++)c[i][j]=b[i][0]*a[0][j]+b[i][1]*a[1][j]+b[i][2]*a[2][j];
 for(uint32_t j=0;j<3;j++)c[3][j]=b[3][0]*a[0][j]+b[3][1]*a[1][j]+b[3][2]*a[2][j]+a[3][j];
}
static void vec3(const float *v,const Mat3 m,float *o){for(uint32_t j=0;j<3;j++)o[j]=v[0]*m[0][j]+v[1]*m[1][j]+v[2]*m[2][j];}
static void point3(const float *v,const Mat4 m,float *o){for(uint32_t j=0;j<3;j++)o[j]=v[0]*m[0][j]+v[1]*m[1][j]+v[2]*m[2][j]+m[3][j];}
int coh_world_group_matrices(const CohWorldInputs *in,float local[6][12],float world[6][12]){
 if(!in||!local||!world||local==world)return -1;
 Mat4 locals[6],worlds[6];
 for(uint32_t i=0;i<6;i++){
  if(!valid_node(&in->nodes[i],i))return -2;
  source_local(in->nodes[i].position,in->nodes[i].pyr_degrees,locals[i]);
  if(i)multiply(worlds[i-1],locals[i],worlds[i]);else memcpy(worlds[i],locals[i],48);
 }
 memcpy(local,locals,sizeof locals);memcpy(world,worlds,sizeof worlds);return 0;
}
int coh_world_group_eye_matrices(const CohWorldInputs *in,const float view[12],float eye[6][12]){
 if(!in||!view||!eye)return -1;
 for(uint32_t j=0;j<12;j++)if(!isfinite(view[j]))return -2;
 Mat4 eyes[6],local;
 for(uint32_t i=0;i<6;i++){
  if(!valid_node(&in->nodes[i],i))return -2;
  source_local(in->nodes[i].position,in->nodes[i].pyr_degrees,local);
  multiply(i?eyes[i-1]:(const float(*)[3])view,local,eyes[i]);
 }
 memcpy(eye,eyes,sizeof eyes);return 0;
}
static void source_view(const Mat4 camera,Mat4 view){
 memcpy(view,camera,48);float tmp;
 tmp=view[0][1];view[0][1]=view[1][0];view[1][0]=tmp;
 tmp=view[0][2];view[0][2]=view[2][0];view[2][0]=tmp;
 tmp=view[1][2];view[1][2]=view[2][1];view[2][1]=tmp;
 /* rdrFixMat: mulMat3(diag(-1,+1,+1),view,temp), retain source sums. */
 Mat4 fix={{-1,0,0},{0,1,0},{0,0,1},{0,0,0}},rot;
 multiply(fix,view,rot);memcpy(view,rot,36);
 float negative[3]={0.f-view[3][0],0.f-view[3][1],0.f-view[3][2]};vec3(negative,view,view[3]);
}
static void source_perspective(float fovy,float aspect,float near,float far,uint32_t fx,uint32_t fy,Mat44 p){
 float l,r,b,t;t=(float)(near*tan(fovy*3.14159265358979323846/360.0));b=-t;l=b*aspect;r=t*aspect;
 if(fy){t=-t;b=-b;}if(fx){l=-l;r=-r;}
 memset(p,0,64);p[0][0]=2*near/(r-l);p[1][1]=2*near/(t-b);p[2][0]=(r+l)/(r-l);p[2][1]=(t+b)/(t-b);p[2][2]=-(far+near)/(far-near);p[2][3]=-1;p[3][2]=-2*far*near/(far-near);
}
int coh_world_camera(const CohWorldInputs *in,uint32_t index,float aspect,float view[12],float projection[16]){
 if(!in||!view||!projection||index>=6||!isfinite(aspect)||aspect<0)return -1;
 const CohWorldCamera *c=&in->cameras[index];if(!valid_camera(c)||(aspect!=0&&!bounded(aspect,.25f,8.f)))return -2;
 Mat4 camera,v;Mat44 p;source_local(c->position,c->pyr_degrees,camera);source_view(camera,v);source_perspective(c->fovy,aspect?aspect:c->aspect,c->znear,c->zfar,c->flip_x,c->flip_y,p);
 memcpy(view,v,48);memcpy(projection,p,64);return 0;
}
void coh_world_gl_matrix(const float source[12],float gl[16]){for(uint32_t c=0;c<4;c++){for(uint32_t r=0;r<3;r++)gl[c*4+r]=source[c*3+r];gl[c*4+3]=c==3?1.f:0.f;}}
int coh_world_vertex(const float world[12],const float modelview[12],const float projection[16],const float position[3],const float normal[3],float out[13]){
 if(!world||!modelview||!projection||!position||!normal||!out)return -1;
 for(uint32_t j=0;j<12;j++)if(!isfinite(world[j])||!isfinite(modelview[j]))return -2;
 for(uint32_t j=0;j<16;j++)if(!isfinite(projection[j]))return -2;
 for(uint32_t j=0;j<3;j++)if(!isfinite(position[j])||!isfinite(normal[j]))return -2;
 float candidate[13];point3(position,(const float(*)[3])world,candidate);vec3(normal,(const float(*)[3])modelview,candidate+3);point3(position,(const float(*)[3])modelview,candidate+6);
 const float(*p)[4]=(const float(*)[4])projection;const float *v=candidate+6;
 for(uint32_t j=0;j<4;j++)candidate[9+j]=v[0]*p[0][j]+v[1]*p[1][j]+v[2]*p[2][j]+p[3][j];
 for(uint32_t j=0;j<13;j++)if(!isfinite(candidate[j]))return -3;
 memcpy(out,candidate,sizeof candidate);return 0;
}
