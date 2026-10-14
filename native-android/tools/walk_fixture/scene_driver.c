#include "../../walk/coh_walk.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
static uint32_t u32(const unsigned char *b){return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static float f32(const unsigned char *b){uint32_t u=u32(b);float f;memcpy(&f,&u,4);return f;}
#define CHECK(c) do{checks++;if(!(c)){failed++;fprintf(stderr,"authored check failed line %d: %s\n",__LINE__,#c);}}while(0)
int main(int argc,char **argv){
 unsigned checks=0,failed=0;CohWalkWorld w={0};CohWalkState s;float lo[3],hi[3],spawn[3],ob_lo[3],ob_hi[3],stopped[3];
 if(argc!=2)return 2;
 FILE *file=fopen(argv[1],"rb");if(!file)return 2;
 if(fseek(file,0,SEEK_END)){fclose(file);return 2;}long n=ftell(file);if(n<128||n>16*1024*1024||fseek(file,0,SEEK_SET)){fclose(file);return 2;}
 unsigned char *bytes=malloc((size_t)n);if(!bytes){fclose(file);return 2;}if(fread(bytes,1,(size_t)n,file)!=(size_t)n){free(bytes);fclose(file);return 2;}fclose(file);
 if(memcmp(bytes,"COHWALK1",8)||u32(bytes+8)!=1){free(bytes);return 2;}
 uint32_t count=u32(bytes+24),off=u32(bytes+52);if(!count||count>8192||off>(uint32_t)n||count>((uint32_t)n-off)/40){free(bytes);return 2;}
 CohWalkTriangle *tri=calloc(count,sizeof(*tri));if(!tri){free(bytes);return 2;}
 for(unsigned i=0;i<count;i++){for(unsigned v=0;v<3;v++)for(unsigned k=0;k<3;k++)tri[i].v[v][k]=f32(bytes+off+i*40+(v*3+k)*4);tri[i].flags=u32(bytes+off+i*40+36);}
 for(unsigned k=0;k<3;k++){lo[k]=f32(bytes+68+k*4);hi[k]=f32(bytes+80+k*4);spawn[k]=f32(bytes+92+k*4);ob_lo[k]=INFINITY;ob_hi[k]=-INFINITY;}
 float yaw=f32(bytes+104);free(bytes);
 for(unsigned i=0;i<count;i++){
  int obstacle=0;for(unsigned v=0;v<3;v++)if(tri[i].v[v][1]>spawn[1]+.01f)obstacle=1;
  if(obstacle)for(unsigned v=0;v<3;v++)for(unsigned k=0;k<3;k++){if(tri[i].v[v][k]<ob_lo[k])ob_lo[k]=tri[i].v[v][k];if(tri[i].v[v][k]>ob_hi[k])ob_hi[k]=tri[i].v[v][k];}
 }
 CHECK(coh_walk_world_init(&w,tri,count,lo,hi));free(tri);
 CHECK(coh_walk_init(&s,&w,spawn,yaw));if(failed){coh_walk_world_destroy(&w);return 1;}
 CHECK(s.grounded&&fabsf(s.position[1]-spawn[1])<.001f);
 for(unsigned i=0;i<70;i++){CHECK(coh_walk_step(&s,&w,COH_MOTION_FORWARD,yaw));CHECK(s.grounded&&fabsf(s.position[1]-spawn[1])<.001f);}
 memcpy(stopped,s.position,sizeof(stopped));CHECK(s.blocked_steps>30);CHECK(s.wall_hits>0);CHECK(s.bounded_steps==0);
 CHECK(fabsf(s.position[2]-spawn[2])>2);CHECK(s.position[2]>ob_hi[2]+.9f);
 for(unsigned i=0;i<30;i++)CHECK(coh_walk_step(&s,&w,COH_MOTION_FORWARD,yaw));
 CHECK(fabsf(s.position[0]-stopped[0])<.001f&&fabsf(s.position[2]-stopped[2])<.001f);
 float before_x=s.position[0];for(unsigned i=0;i<8;i++)CHECK(coh_walk_step(&s,&w,COH_MOTION_FORWARD|COH_MOTION_RIGHT,yaw));
 CHECK(fabsf(s.position[0]-before_x)>1);CHECK(s.slide_steps>=3);CHECK(s.bounded_steps==0);CHECK(s.grounded);
 float reverse_z=s.position[2];for(unsigned i=0;i<10;i++)CHECK(coh_walk_step(&s,&w,COH_MOTION_BACKWARD,yaw));CHECK(s.position[2]>reverse_z+1);
 float held[3];memcpy(held,s.position,sizeof held);coh_walk_clear(&s);for(unsigned i=0;i<6;i++)CHECK(coh_walk_step(&s,&w,0,yaw));
 CHECK(fabsf(s.position[0]-held[0])<.001f&&fabsf(s.position[2]-held[2])<.001f);CHECK(s.physics.vel[0]==0&&s.physics.vel[2]==0);
 CHECK(coh_walk_init(&s,&w,spawn,yaw));CHECK(fabsf(s.position[0]-spawn[0])<.001f&&fabsf(s.position[2]-spawn[2])<.001f);
 /* A support gap near the fixture perimeter is held by the documented scene
  * guard. This is an adapter test, separate from bench collision evidence. */
 for(unsigned i=0;i<150;i++)CHECK(coh_walk_step(&s,&w,COH_MOTION_BACKWARD,yaw));
 CHECK(s.bounded_steps>0);CHECK(s.grounded&&fabsf(s.position[1]-spawn[1])<.001f);
 coh_walk_world_destroy(&w);
 printf("{\"passed\":%s,\"checks\":%u,\"failed\":%u,\"authored_triangles\":%u,\"ground_y\":%.9g,\"forward_blocked_position\":[%.9g,%.9g,%.9g],\"source_wall_queries\":true,\"forward_slide_test_bounded_steps\":0,\"scene_guard_separately_exercised\":true}\n",failed?"false":"true",checks,failed,count,spawn[1],stopped[0],stopped[1],stopped[2]);return failed?1:0;
}
