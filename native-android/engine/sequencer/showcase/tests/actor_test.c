#include "coh_seq_actor.h"
#include "expanded_graph.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void coh_original_init(const CohSeqGraph *,const CohSeqClip *,uint32_t,uint32_t);
void coh_original_step(const CohSeqInput *);
void coh_original_snapshot(uint32_t *,float *,float *,uint32_t *,uint32_t *);
void original_reset(void);
void original_playback(const CohAnimationRig *,const CohAnimationPose *,int,float,float,uint32_t,CohAnimationPose *);
#define BODIES 3
#define CLIPS 4
#define MOVES 6
#define REQUIRE(x) do{++checks;if(!(x)){fprintf(stderr,"%s:%d failed: %s\n",__FILE__,__LINE__,#x);return 1;}}while(0)
static unsigned long checks,scalar_comparisons,successes,unavailable,marker_events;
static double max_error;
static CohAnimationRig rigs[BODIES][CLIPS];
static CohSeqPoseBinding poses[BODIES][MOVES];
static CohSeqClip clips[BODIES][MOVES];
static CohSeqMarker markers[BODIES][MOVES*3];
static CohSeqCueRoute routes[BODIES][3];
static CohSeqActor actor[BODIES],reference[BODIES];
static CohSeqActorCue cues[COH_SEQ_PLAYBACK_EVENTS],before_cues[COH_SEQ_PLAYBACK_EVENTS];
static CohAnimationPose pose,before_pose,raw,expected;
static CohSeqActorResources resources[BODIES];
static void *backing[BODIES][CLIPS];
static int near(float a,float b) {
    double d=fabs((double)a-b);++scalar_comparisons;if(d>max_error)max_error=d;
    return d<=3e-6+3e-6*fabs(b);
}
static int cancel(void *context){++*(unsigned *)context;return 1;}
int main(int argc,char **argv) {
    const CohSeqClip *authored[BODIES]={male_clips,fem_clips,huge_clips};
    static const unsigned map[MOVES]={3,0,0,1,1,2};
    uint32_t random=13579;
    if(argc!=1+BODIES*CLIPS)return 2;
    REQUIRE(source_graph.move_count==MOVES);
    for(unsigned body=0;body<BODIES;++body) {
        for(unsigned i=0;i<CLIPS;++i) {
            FILE *f=fopen(argv[1+body*CLIPS+i],"rb");long length;
            REQUIRE(f);REQUIRE(!fseek(f,0,SEEK_END));length=ftell(f);REQUIRE(length>0 && length<8*1024*1024);
            rewind(f);backing[body][i]=malloc((size_t)length);REQUIRE(backing[body][i]);
            REQUIRE(fread(backing[body][i],1,(size_t)length,f)==(size_t)length);fclose(f);
            REQUIRE(!coh_animation_parse(backing[body][i],(size_t)length,&rigs[body][i]));
        }
        for(unsigned move=0;move<MOVES;++move) {
            clips[body][move]=authored[body][move];
            poses[body][move]=(CohSeqPoseBinding){clips[body][move].clip_id,100+body,&rigs[body][map[move]]};
            float frame=clips[body][move].first_frame;
            for(unsigned j=0;j<3;++j)markers[body][move*3+j]=(CohSeqMarker){move,10+j,20+j,frame};
        }
        for(unsigned j=0;j<3;++j)routes[body][j]=(CohSeqCueRoute){10+j,20+j,COH_SEQ_CUE_AUDIO+j,200+j,
            j==0?COH_SEQ_SOCKET_ROOT:rigs[body][0].order[4+j]};
        resources[body]=(CohSeqActorResources){.actor_id=10+body,.rig_id=100+body,
            .appearance_generation=2000+body,.rig_generation=3000+body,.resource_generation=1,
            .graph=&source_graph,.clips=clips[body],.poses=poses[body],.move_count=MOVES,
            .markers=markers[body],.marker_count=MOVES*3,.routes=routes[body],.route_count=3};
        REQUIRE(coh_seq_actor_init(&actor[body],&resources[body],0,random)==COH_OK);
        REQUIRE(coh_seq_actor_active_rig(&actor[body])==NULL);
        coh_original_init(&source_graph,clips[body],0,random);original_reset();
        for(unsigned i=0;i<4000;++i) {
            CohSeqInput in={0};CohSeqActor before=actor[body];size_t count=111;
            random=random*1664525u+1013904223u;unsigned wanted=random%MOVES;
            const CohSeqMove *move=&source_graph.moves[wanted];
            for(unsigned j=0;j<move->required_count;++j)coh_seq_set_bit(&in.state,move->required[j],1);
            in.timestep_frames=(float)((random>>8)%7)*.5f;in.animation_scale=1;in.force_interrupt=i%5==0;in.random_choice=random>>16;
            memset(&pose,0xcd,sizeof pose);before_pose=pose;memset(cues,0xda,sizeof cues);memcpy(before_cues,cues,sizeof cues);
            CohStatus status=coh_seq_actor_step(&actor[body],&in,(uint64_t)i+1,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count);
            if(status==COH_NOT_FOUND || status==COH_UNSUPPORTED) {
                ++unavailable;REQUIRE(!memcmp(&before,&actor[body],sizeof before));REQUIRE(!memcmp(&before_pose,&pose,sizeof pose));
                REQUIRE(!memcmp(before_cues,cues,sizeof cues));REQUIRE(count==111);continue;
            }
            REQUIRE(status==COH_OK);++successes;
            coh_original_step(&in);uint32_t actual,incrementor,seed;float frame,previous;
            coh_original_snapshot(&actual,&frame,&previous,&incrementor,&seed);
            REQUIRE(actual==actor[body].sequencer.move && frame==actor[body].sequencer.frame &&
                previous==actor[body].sequencer.previous_frame && incrementor==actor[body].sequencer.incrementor && seed==actor[body].sequencer.predict_seed);
            const CohAnimationRig *rig=coh_seq_actor_active_rig(&actor[body]);REQUIRE(rig && rig==poses[body][actual].rig);
            REQUIRE(!coh_animation_sample(rig,frame,&raw));
            int entry=!before.playback.initialized || before.sequencer.diagnostics.transitions!=actor[body].sequencer.diagnostics.transitions;
            original_playback(rig,&raw,entry,in.timestep_frames,actor[body].selection.interpolate_frames,actor[body].selection.flags,&expected);
            for(unsigned bone=0;bone<rig->node_count;++bone) {
                unsigned id=rig->order[bone];
                for(unsigned j=0;j<3;++j)REQUIRE(near(pose.position[id][j],expected.position[id][j]));
                for(unsigned j=0;j<4;++j)REQUIRE(near(pose.rotation[id][j],expected.rotation[id][j]));
                for(unsigned j=0;j<12;++j)REQUIRE(near(pose.world_rows[id][j],expected.world_rows[id][j]));
            }
            for(size_t cue=0;cue<count;++cue) {
                REQUIRE(cues[cue].animation.actor_id==10+body && cues[cue].animation.rig_id==100+body);
                REQUIRE(cues[cue].appearance_generation==2000+body && cues[cue].rig_generation==3000+body && cues[cue].resource_generation==1);
                if(cues[cue].animation.type==COH_SEQ_EVENT_MARKER) {
                    ++marker_events;unsigned kind=cues[cue].animation.kind-10;REQUIRE(kind<3);
                    REQUIRE(cues[cue].kind==COH_SEQ_CUE_AUDIO+kind && cues[cue].resource_id==200+kind);
                    if(kind)REQUIRE(!memcmp(cues[cue].socket_rows,pose.world_rows[routes[body][kind].socket_bone],sizeof cues[cue].socket_rows));
                    else REQUIRE(cues[cue].socket_bone==COH_SEQ_SOCKET_ROOT && cues[cue].socket_rows[0]==1 && cues[cue].socket_rows[5]==1 && cues[cue].socket_rows[10]==1);
                }else REQUIRE(cues[cue].kind==COH_SEQ_CUE_NONE);
            }
        }
        CohSeqActorSnapshot snapshot;REQUIRE(coh_seq_actor_snapshot(&actor[body],&snapshot)==COH_OK);
        REQUIRE(snapshot.successful_ticks && snapshot.actor_id==10+body && snapshot.retained_bytes==sizeof(CohSeqActor));
    }
    /* Three simultaneous independent actors: alternate source actions and prove
     * that scheduling order cannot contaminate another actor's pose/history. */
    for(unsigned body=0;body<BODIES;++body) {
        REQUIRE(coh_seq_actor_init(&actor[body],&resources[body],0,42+body)==COH_OK);reference[body]=actor[body];
    }
    for(unsigned tick=1;tick<=3000;++tick)for(unsigned body=0;body<BODIES;++body) {
        CohSeqInput in={0};size_t count=0,other_count=0;CohAnimationPose other_pose;
        CohSeqActorCue other_cues[COH_SEQ_PLAYBACK_EVENTS];
        const CohSeqMove *move=&source_graph.moves[(tick/20+body)%MOVES];
        for(unsigned j=0;j<move->required_count;++j)coh_seq_set_bit(&in.state,move->required[j],1);
        in.timestep_frames=.5f;in.animation_scale=1;in.force_interrupt=tick%20==0;
        CohStatus status=coh_seq_actor_step(&actor[body],&in,tick,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count);
        CohStatus other=coh_seq_actor_step(&reference[body],&in,tick,&other_pose,other_cues,COH_SEQ_PLAYBACK_EVENTS,&other_count);
        REQUIRE(status==other);REQUIRE(!memcmp(&actor[body],&reference[body],sizeof actor[body]));
        if(status==COH_OK){REQUIRE(!memcmp(&pose,&other_pose,sizeof pose));REQUIRE(count==other_count);REQUIRE(!memcmp(cues,other_cues,count*sizeof cues[0]));}
    }
    /* A full cue buffer failure and explicit cancellation must not consume
     * selection, original random seed, interpolation, cues or lifecycle tick. */
    REQUIRE(coh_seq_actor_init(&actor[0],&resources[0],0,42)==COH_OK);
    CohSeqInput input={0};input.animation_scale=1;input.timestep_frames=.5f;
    CohSeqActor before=actor[0];size_t count=123;
    memset(&pose,0x63,sizeof pose);before_pose=pose;memset(cues,0x72,sizeof cues);memcpy(before_cues,cues,sizeof cues);
    REQUIRE(coh_seq_actor_step(&actor[0],&input,1,&pose,cues,0,&count)==COH_LIMIT);
    REQUIRE(!memcmp(&actor[0],&before,sizeof before) && !memcmp(&pose,&before_pose,sizeof pose) && !memcmp(cues,before_cues,sizeof cues) && count==123);
    REQUIRE(coh_seq_actor_step(&actor[0],&input,1,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count)==COH_OK);
    before=actor[0];unsigned polls=0;input.cancel=(CohCancel){cancel,&polls};before_pose=pose;
    REQUIRE(coh_seq_actor_step(&actor[0],&input,2,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count)==COH_CANCELLED);
    REQUIRE(polls==1 && !memcmp(&actor[0],&before,sizeof before) && !memcmp(&pose,&before_pose,sizeof pose));
    input.cancel=(CohCancel){0};
    REQUIRE(coh_seq_actor_step(&actor[0],&input,1,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count)==COH_INVALID);
    /* Hot reload preserves state and tags new outputs while rejecting stale
     * generations, arbitrary morph changes and unknown attachment sockets. */
    CohSeqActorResources replacement=resources[0];replacement.resource_generation=2;
    REQUIRE(coh_seq_actor_rebind(&actor[0],&replacement)==COH_OK);
    REQUIRE(coh_seq_actor_rebind(&actor[0],&replacement)==COH_INVALID);
    REQUIRE(actor[0].playback.frame==before.playback.frame && actor[0].playback.tick==before.playback.tick);
    replacement.resource_generation=3;replacement.rig_generation++;
    REQUIRE(coh_seq_actor_rebind(&actor[0],&replacement)==COH_INVALID);
    CohSeqCueRoute invalid_route=routes[0][0];invalid_route.socket_bone=0;
    for(unsigned bone=0;bone<COH_ANIMATION_BONES;++bone) {
        unsigned found=0;for(unsigned j=0;j<rigs[0][3].node_count;++j)found|=rigs[0][3].order[j]==bone;
        if(!found){invalid_route.socket_bone=bone;break;}
    }
    replacement=resources[0];replacement.routes=&invalid_route;replacement.route_count=1;
    REQUIRE(coh_seq_actor_init(&reference[0],&replacement,0,42)==COH_UNSUPPORTED);
    replacement=resources[0];replacement.appearance_generation=0;
    REQUIRE(coh_seq_actor_init(&reference[0],&replacement,0,42)==COH_INVALID);
    REQUIRE(coh_seq_actor_step(&actor[0],&input,2,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count)==COH_OK);
    for(size_t i=0;i<count;++i)REQUIRE(cues[i].resource_generation==2);
    /* A genuinely unresolved authored JumpPost next edge is reported rather
     * than substituted with an invented idle transition. */
    REQUIRE(coh_seq_actor_init(&actor[0],&resources[0],0,42)==COH_OK);
    input=(CohSeqInput){0};input.animation_scale=1;input.timestep_frames=3;
    unsigned missing_edge=0;
    for(unsigned tick=1;tick<200;++tick) {
        before=actor[0];before_pose=pose;memcpy(before_cues,cues,sizeof cues);count=789;
        CohStatus status=coh_seq_actor_step(&actor[0],&input,tick,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count);
        if(status==COH_UNSUPPORTED) {
            ++unavailable;missing_edge=1;
            REQUIRE(!memcmp(&actor[0],&before,sizeof before) && !memcmp(&pose,&before_pose,sizeof pose) && !memcmp(cues,before_cues,sizeof cues) && count==789);
            break;
        }
        REQUIRE(status==COH_OK);
    }
    REQUIRE(missing_edge);
    /* A lazily missing genuine action must preserve the complete source
     * selection and resume at the same tick only after explicit generation. */
    CohSeqClip lazy_clips[MOVES];CohSeqPoseBinding lazy_poses[MOVES];
    memcpy(lazy_clips,clips[0],sizeof lazy_clips);memcpy(lazy_poses,poses[0],sizeof lazy_poses);
    lazy_clips[1].ready=0;lazy_poses[1].rig=NULL;
    CohSeqActorResources lazy=resources[0];lazy.clips=lazy_clips;lazy.poses=lazy_poses;
    REQUIRE(coh_seq_actor_init(&actor[0],&lazy,0,42)==COH_OK);before=actor[0];
    input=(CohSeqInput){0};input.animation_scale=1;input.timestep_frames=.5f;input.force_interrupt=1;
    for(unsigned j=0;j<source_graph.moves[1].required_count;++j)
        coh_seq_set_bit(&input.state,source_graph.moves[1].required[j],1);
    before_pose=pose;memcpy(before_cues,cues,sizeof cues);count=456;
    REQUIRE(coh_seq_actor_step(&actor[0],&input,1,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count)==COH_NOT_FOUND);
    REQUIRE(!memcmp(&actor[0],&before,sizeof before) && !memcmp(&pose,&before_pose,sizeof pose) && !memcmp(cues,before_cues,sizeof cues) && count==456);
    replacement=resources[0];replacement.resource_generation=2;
    REQUIRE(coh_seq_actor_rebind(&actor[0],&replacement)==COH_OK);
    REQUIRE(coh_seq_actor_step(&actor[0],&input,1,&pose,cues,COH_SEQ_PLAYBACK_EVENTS,&count)==COH_OK);
    REQUIRE(actor[0].selection.move==1 && actor[0].playback.tick==1);
    /* Rebinding a newly allocated table must not silently change authored
     * ranges or appearance generation while preserving the old active pose. */
    memcpy(lazy_clips,clips[0],sizeof lazy_clips);lazy_clips[1].last_frame-=1;
    replacement.clips=lazy_clips;replacement.resource_generation=3;before=actor[0];
    REQUIRE(coh_seq_actor_rebind(&actor[0],&replacement)==COH_STATE);
    REQUIRE(!memcmp(&actor[0],&before,sizeof before));
    for(unsigned body=0;body<BODIES;++body)for(unsigned i=0;i<CLIPS;++i)free(backing[body][i]);
    printf("{\"checks\":%lu,\"source_scalar_comparisons\":%lu,\"source_step_comparisons\":%lu,\"explicit_missing_source_edges\":%lu,\"maximum_pose_error\":%.9g,\"routed_markers\":%lu,\"simultaneous_actors\":3,\"interleaved_ticks\":9000,\"retained_actor_bytes\":%zu,\"per_tick_allocations\":0}\n",checks,scalar_comparisons,successes,unavailable,max_error,marker_events,sizeof(CohSeqActor));
    return 0;
}
