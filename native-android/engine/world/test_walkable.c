#include "../../walk/coh_walk.h"
#include "../../walkable/coh_walkable_scene.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"expanded WALK assertion %u line%d: %s\n",checks,__LINE__,#x);exit(2);}}while(0)
int main(int argc,char **argv){
 CHECK(argc==3);FILE *f=fopen(argv[1],"rb");CHECK(f);CHECK(fseek(f,0,SEEK_END)==0);long length=ftell(f);rewind(f);CHECK(length>0&&length<16*1024*1024);unsigned char *raw=malloc((size_t)length);CHECK(raw);CHECK(fread(raw,1,(size_t)length,f)==(size_t)length);fclose(f);CohWalkableScene scene;CHECK(coh_walkable_scene_parse(raw,(size_t)length,&scene)==0);CHECK(scene.part_count==22&&scene.texture_count==6&&scene.triangle_count==2304);CohWalkWorld world={0};CHECK(coh_walk_world_init(&world,scene.triangles,scene.triangle_count,scene.bounds_min,scene.bounds_max));CohWalkState actor;
 /* Repeat the accepted functional scenario only because its collision world
  * now contains nine additional source-authored obstacle instances. */
 CHECK(coh_walk_init(&actor,&world,scene.spawn,scene.spawn_yaw));CHECK(actor.grounded);
 for(unsigned tick=0;tick<70;tick++){CHECK(coh_walk_step(&actor,&world,COH_MOTION_FORWARD,scene.spawn_yaw));CHECK(actor.grounded);CHECK(fabsf(actor.position[1]-74)<.001f);}
 CHECK(actor.blocked_steps>30&&actor.wall_hits>0&&actor.bounded_steps==0);float stopped[3];memcpy(stopped,actor.position,sizeof stopped);for(unsigned tick=0;tick<30;tick++)CHECK(coh_walk_step(&actor,&world,COH_MOTION_FORWARD,scene.spawn_yaw));CHECK(fabsf(stopped[0]-actor.position[0])<.001f&&fabsf(stopped[2]-actor.position[2])<.001f);float beforex=actor.position[0];for(unsigned tick=0;tick<6;tick++)CHECK(coh_walk_step(&actor,&world,COH_MOTION_FORWARD|COH_MOTION_RIGHT,scene.spawn_yaw));CHECK(actor.grounded&&actor.bounded_steps==0&&actor.slide_steps>0&&fabsf(actor.position[0]-beforex)>.25f);
 /* Contact coverage for every source collider. Benches have sloping backs and
  * seats; original WALK may climb those surfaces. Record that behavior instead
  * of asserting that all source shapes are infinitely tall flat walls. */
 f=fopen(argv[2],"r");CHECK(f);unsigned benches=0,contacts=0,blocked=0,sloped_ticks=0;float max_y=74;unsigned long long world_queries=0,wall_hits=0;float x,z,lo,hi;
 while(fscanf(f,"%f %f %f %f",&x,&z,&lo,&hi)==4){float spawn[3]={x,74,z+6*hi},yaw=hi>0?scene.spawn_yaw:0;CHECK(coh_walk_init(&actor,&world,spawn,yaw));for(unsigned tick=0;tick<70;tick++){CHECK(coh_walk_step(&actor,&world,COH_MOTION_FORWARD,yaw));for(unsigned j=0;j<3;j++)CHECK(isfinite(actor.position[j]));if(actor.position[1]>max_y)max_y=actor.position[1];if(!actor.physics.falling&&actor.physics.surf_normal[1]<.3f)sloped_ticks++;}CHECK(actor.wall_hits>0&&actor.collision_queries>0);contacts++;if(actor.blocked_steps)blocked++;world_queries+=actor.collision_queries;wall_hits+=actor.wall_hits;benches++;(void)lo;(void)hi;}
 CHECK(benches==10&&contacts==10);fclose(f);coh_walk_world_destroy(&world);free(raw);printf("{\"passed\":true,\"assertions\":%u,\"authored_triangles\":2304,\"bench_instances\":%u,\"contact_instances\":%u,\"blocked_contact_instances\":%u,\"source_steep_contact_ticks\":%u,\"maximum_contact_height\":%.9g,\"source_collision_queries\":%llu,\"source_wall_hits\":%llu,\"accepted_block_slide_regression_passed\":true,\"all_benches_flat_ground_asserted\":false}\n",checks,benches,contacts,blocked,sloped_ticks,max_y,world_queries,wall_hits);return 0;
}
