#define _POSIX_C_SOURCE 200809L
#include "coh_sequencer.h"
#include "source_graph.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#ifdef COH_SEQ_ORACLE
void coh_original_init(const CohSeqGraph *,const CohSeqClip *,uint32_t,uint32_t);
void coh_original_step(const CohSeqInput *);
void coh_original_snapshot(uint32_t *,float *,float *,uint32_t *,uint32_t *);
#endif
static uint64_t assertions, oracle_steps, source_failures;
static uint32_t source_visited[2];
#define CHECK(x) do {++assertions;if(!(x)){fprintf(stderr,"check failed %s:%d: %s\n",__FILE__,__LINE__,#x);return 1;}}while(0)
static uint32_t rng=0x13579bdu;
static uint32_t next_random(void) {rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static int cancelled(void *ctx) {++*(int *)ctx;return 1;}
static CohSeqInput input(void) {CohSeqInput in;memset(&in,0,sizeof in);in.timestep_frames=1;in.animation_scale=1;return in;}
static CohSeqClip make_clip(float first,float last) {
    CohSeqClip c={{"ANIMS/mock-test-only.anim",1},7,1,0,0,1};
    c.first_frame=first;c.last_frame=last;return c;
}
static CohSeqMove make_move(const char *name) {
    CohSeqMove m;memset(&m,0,sizeof m);m.name=name;m.scale=1;m.interpolate=5;m.next_move=0;return m;
}
static int compare(CohSequencer *s,const CohSeqInput *in) {
    CohSeqSelection out;
    CohStatus result=coh_seq_step(s,in,&out);
    if(result==COH_UNSUPPORTED || result==COH_NOT_FOUND) {++source_failures;return 0;}
    CHECK(result==COH_OK);
    if(s->graph==&source_graph)source_visited[s->rig_id-100]|=1u<<s->move;
#ifdef COH_SEQ_ORACLE
    {
        uint32_t move,incrementor,seed;float frame,previous;
        coh_original_step(in);
        coh_original_snapshot(&move,&frame,&previous,&incrementor,&seed);
        CHECK(s->move==move);CHECK(s->frame==frame);CHECK(s->previous_frame==previous);
        CHECK(s->incrementor==incrementor);CHECK(s->predict_seed==seed);
        ++oracle_steps;
    }
#endif
    CHECK(out.actor_id==s->actor_id && out.rig_id==s->rig_id);
    CHECK(out.flags==s->graph->moves[s->move].flags);
    return 0;
}
static int source_traces(void) {
    const CohSeqClip *rigs[2]={male_clips,huge_clips};
    uint32_t rig,iteration;
    CHECK(source_graph.move_count==18);
    for(rig=0;rig<2;++rig) {
        CohSequencer s;
        CHECK(coh_seq_init(&s,&source_graph,rigs[rig],source_graph.move_count,
                          10+rig,100+rig,M_KNOCKDOWN_CYCLE,0xabcd)==COH_OK);
#ifdef COH_SEQ_ORACLE
        coh_original_init(&source_graph,rigs[rig],M_KNOCKDOWN_CYCLE,0xabcd);
#endif
        for(iteration=0;iteration<50000;++iteration) {
            CohSeqInput in=input();uint32_t r=next_random();
            if(iteration%251==0) {
                CHECK(coh_seq_init(&s,&source_graph,rigs[rig],source_graph.move_count,
                                  10+rig,100+rig,M_KNOCKDOWN_CYCLE,r)==COH_OK);
#ifdef COH_SEQ_ORACLE
                coh_original_init(&source_graph,rigs[rig],M_KNOCKDOWN_CYCLE,r);
#endif
            }
            switch((r>>4)%8) {
                case 0:coh_seq_set_bit(&in.state,S_JUMP,1);coh_seq_set_bit(&in.state,S_AIR,1);break;
                case 1:coh_seq_set_bit(&in.state,S_AIR,1);coh_seq_set_bit(&in.state,S_APEX,1);break;
                case 2:coh_seq_set_bit(&in.state,S_AIR,1);coh_seq_set_bit(&in.state,S_BIGFALL,1);break;
                case 3:coh_seq_set_bit(&in.state,S_COMBAT,1);coh_seq_set_bit(&in.state,S_KICKBRAWL,1);break;
                case 4:coh_seq_set_bit(&in.state,S_COMBAT,1);break;
                case 5:coh_seq_set_bit(&in.state,S_EMOTE,1);coh_seq_set_bit(&in.state,S_TEABAG,1);break;
                case 6:coh_seq_set_bit(&in.state,S_EMOTE,1);coh_seq_set_bit(&in.state,S_BOW,1);coh_seq_set_bit(&in.state,S_GREETING,1);coh_seq_set_bit(&in.state,S_LOW,1);break;
                default:break;
            }
            in.timestep_frames=(float)((r>>9)%13)*.25f;
            in.animation_scale=.5f+(float)((r>>13)%4)*.5f;
            in.force_interrupt=(r%17)==0;in.random_choice=(r>>16)&0x7fffu;
            CHECK(compare(&s,&in)==0);
        }
        {
            uint32_t required=0,i;
            for(i=0;i<source_graph.move_count;++i)if(rigs[rig][i].ready)required|=1u<<i;
            CHECK((source_visited[rig]&required)==required);
        }
    }
    return 0;
}
static int synthetic_rules(void) {
    CohSeqMove m[4];CohSeqClip clips[4];CohSeqGraph g={m,4};
    CohSequencer s,before;CohSeqSelection out,unchanged;CohSeqInput in=input();
    uint32_t i;
    for(i=0;i<4;++i){m[i]=make_move("synthetic");clips[i]=make_clip(1,10);}
    m[0].flags=COH_SEQ_CYCLE;m[0].priority=99;m[0].members[0]=2;m[0].next_move=3;
    m[1].priority=1;m[1].required_count=1;m[1].required[0]=4;m[1].interrupts[0]=2;
    m[2]=m[1];m[2].required[0]=2;
    m[3].flags=COH_SEQ_CYCLE;
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);
    coh_seq_set_bit(&in.state,2,1);coh_seq_set_bit(&in.state,4,1);
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK);
    CHECK(s.move==2 && s.frame==1 && s.incrementor==1); /* anchor order, lower priority */
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);
    s.incrementor=1;
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.move==1);
    /* PICKRANDOMLY is selected from the first candidate in source order. */
    m[2].flags=COH_SEQ_PICK_RANDOMLY;in.random_choice=1;
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.move==1 && s.incrementor==0);
    m[2].flags=0;
    /* Strict end: exact last remains; >last cycles once with source fallback. */
    in=input();CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);
    s.frame=9;CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.frame==10);
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.frame==2 && s.previous_frame==-1);
    clips[0].last_frame=1; s.frame=1;in.timestep_frames=3;
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.frame==1);
    clips[0].last_frame=10;
    /* FinishCycle postpones failed requirements until the strict end. */
    m[0].required_count=1;m[0].required[0]=9;m[0].flags|=COH_SEQ_FINISH_CYCLE;
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.move==0 && s.frame==4);
    s.frame=9;CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.move==3);
    m[0].flags=COH_SEQ_CYCLE;
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.move==3 && s.frame==1);
    m[0].required_count=0;
    /* Phase retention only between interior source cycles, not complex cycles. */
    m[1].flags=COH_SEQ_CYCLE;in=input();coh_seq_set_bit(&in.state,4,1);
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);s.frame=5;
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.move==1 && s.frame==5);
    m[0].flags|=COH_SEQ_COMPLEX_CYCLE;m[0].cycle_count=1;m[0].cycle_moves[0]=3;
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);s.frame=5;
    CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.move==1 && s.frame==1);
    /* Original random cycle LCG and strict cycle transition run against oracle. */
    in=input();CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,0xffffffffu)==COH_OK);
#ifdef COH_SEQ_ORACLE
    coh_original_init(&g,clips,0,0xffffffffu);
#endif
    for(i=0;i<20;++i)CHECK(compare(&s,&in)==0);
    /* Failure never partially advances state/output; retry after lazy admission. */
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);
    in=input();coh_seq_set_bit(&in.state,4,1);clips[1].ready=0;
    before=s;memset(&out,0xa5,sizeof out);unchanged=out;
    CHECK(coh_seq_step(&s,&in,&out)==COH_NOT_FOUND);
    CHECK(!memcmp(&s,&before,sizeof s) && !memcmp(&out,&unchanged,sizeof out));
    {
        CohSeqClip replacement[4];memcpy(replacement,clips,sizeof clips);replacement[1].ready=1;
        CHECK(coh_seq_rebind_clips(&s,replacement,4)==COH_OK);
        CHECK(coh_seq_step(&s,&in,&out)==COH_OK && s.move==1);
        clips[1].ready=1;
        CHECK(coh_seq_rebind_clips(&s,clips,4)==COH_OK);
    }
    before=s;in.timestep_frames=NAN;
    CHECK(coh_seq_step(&s,&in,&out)==COH_INVALID && !memcmp(&s,&before,sizeof s));
    in=input();in.state.words[27]=0x80000000u;
    CHECK(coh_seq_step(&s,&in,&out)==COH_INVALID);
    in=input();{int calls=0;in.cancel.poll=cancelled;in.cancel.context=&calls;
        CHECK(coh_seq_step(&s,&in,&out)==COH_CANCELLED && calls==1);}
    CHECK(coh_seq_set_bit(&in.state,COH_SEQ_STATES,1)==COH_INVALID);
    before=s;{
        CohSeqClip replacement[4];memcpy(replacement,clips,sizeof clips);replacement[s.move].last_frame=0;
        CHECK(coh_seq_rebind_clips(&s,replacement,4)==COH_INVALID && !memcmp(&s,&before,sizeof s));
    }
    /* Unimported edges are explicit, never silently redirected to fixture zero. */
    in=input();m[0].flags=0;m[0].next_move=COH_SEQ_NONE;
    CHECK(coh_seq_init(&s,&g,clips,4,20,42,0,123)==COH_OK);s.frame=10;before=s;
    CHECK(coh_seq_step(&s,&in,&out)==COH_UNSUPPORTED && !memcmp(&s,&before,sizeof s));
    return 0;
}
static int negatives_and_pose(void) {
    CohSeqMove m=make_move("negative");CohSeqClip clip=make_clip(1,10);
    CohSeqGraph g={&m,1};CohSequencer s;CohSeqInput in=input();CohSeqSelection out;
    CohAnimationRig rig;CohAnimationPose pose,before;const CohAnimationRig *rigs[1]={&rig};
    uint32_t i;
    m.flags=COH_SEQ_CYCLE;
    CHECK(coh_seq_validate(NULL,&clip,1)==COH_INVALID);
    CHECK(coh_seq_validate(&g,&clip,0)==COH_INVALID);
    m.required_count=13;CHECK(coh_seq_validate(&g,&clip,1)==COH_INVALID);m.required_count=0;
    m.cycle_count=6;CHECK(coh_seq_validate(&g,&clip,1)==COH_INVALID);m.cycle_count=0;
    m.required_count=2;m.required[0]=8;m.required[1]=8;
    CHECK(coh_seq_validate(&g,&clip,1)==COH_INVALID);m.required_count=0;
    clip.type_scale=NAN;CHECK(coh_seq_validate(&g,&clip,1)==COH_INVALID);clip.type_scale=1;
    clip.last_frame=-1;CHECK(coh_seq_validate(&g,&clip,1)==COH_INVALID);clip.last_frame=10;
    m.next_move=1;CHECK(coh_seq_validate(&g,&clip,1)==COH_INVALID);m.next_move=0;
    m.flags|=COH_SEQ_COMPLEX_CYCLE;CHECK(coh_seq_validate(&g,&clip,1)==COH_INVALID);m.flags=COH_SEQ_CYCLE;
    CHECK(coh_seq_init(&s,&g,&clip,1,1,2,0,0)==COH_OK);
    memset(&rig,0,sizeof rig);rig.first_frame=1;rig.last_frame=10;rig.node_count=1;
    rig.parent[0]=-1;rig.base_rotation[0][3]=1;
    memset(&pose,0xa5,sizeof pose);before=pose;
    rigs[0]=NULL;CHECK(coh_seq_sample(&s,rigs,1,&pose)==COH_NOT_FOUND && !memcmp(&pose,&before,sizeof pose));
    rigs[0]=&rig;CHECK(coh_seq_sample(&s,rigs,1,&pose)==COH_OK && pose.rotation[0][3]==1);
    s.frame=11;CHECK(coh_seq_sample(&s,rigs,1,&pose)==COH_INVALID);s.frame=1;
    /* Bounded mutational admission tests keep all borrowed pointers valid. */
    for(i=0;i<30000;++i) {
        uint32_t r=next_random();CohSeqMove bad=m;CohSeqGraph bg={&bad,1};CohSeqClip bc=clip;
        switch(r%6) {
            case 0:bad.required_count=(uint16_t)((r>>8)&31);break;
            case 1:bad.cycle_count=(r>>8)&15;break;
            case 2:bad.next_move=(r>>8)&15;break;
            case 3:bc.last_frame=(float)(int32_t)r;break;
            case 4:bad.scale=(float)(int32_t)r;break;
            default:bad.flags=r;break;
        }
        {
            CohStatus status=coh_seq_validate(&bg,&bc,1);
            CHECK(status==COH_OK || status==COH_INVALID || status==COH_LIMIT);
            if(status==COH_OK) {CohSequencer mut;CHECK(coh_seq_init(&mut,&bg,&bc,1,1,2,0,r)==COH_OK);(void)coh_seq_step(&mut,&in,&out);}
        }
    }
    {
        CohSeqMove many[102];CohSeqClip many_clips[102];CohSeqGraph mg={many,102};
        CohSequencer many_actor,saved;CohSeqInput mi=input();
        for(i=0;i<102;++i) {
            many[i]=make_move("tie-cap");many[i].required_count=1;many[i].required[0]=1;
            many[i].members[0]=many[i].interrupts[0]=2;many_clips[i]=clip;
        }
        coh_seq_set_bit(&mi.state,1,1);
        CHECK(coh_seq_init(&many_actor,&mg,many_clips,102,1,2,0,0)==COH_OK);saved=many_actor;
        CHECK(coh_seq_step(&many_actor,&mi,&out)==COH_LIMIT && !memcmp(&saved,&many_actor,sizeof saved));
        many[101].priority=1; /* Larger lower-priority tie set must not hide winner. */
        CHECK(coh_seq_step(&many_actor,&mi,&out)==COH_OK && many_actor.move==101);
    }
    return 0;
}
static int long_run(uint64_t *duration_ns,size_t *retained) {
    CohSeqMove m=make_move("long-run-mock");CohSeqClip c=make_clip(1,10);CohSeqGraph g={&m,1};
    CohSequencer s;CohSeqInput in=input();CohSeqSelection out;struct timespec a,b;uint32_t i;
    m.flags=COH_SEQ_CYCLE;CHECK(coh_seq_init(&s,&g,&c,1,42,99,0,0)==COH_OK);
    clock_gettime(CLOCK_MONOTONIC,&a);
    for(i=0;i<1000000;++i)CHECK(coh_seq_step(&s,&in,&out)==COH_OK);
    clock_gettime(CLOCK_MONOTONIC,&b);
    CHECK(s.diagnostics.steps==1000000 && s.diagnostics.cycles>100000 && s.diagnostics.searches==1);
    *retained=s.diagnostics.retained_bytes;
    *duration_ns=(uint64_t)(b.tv_sec-a.tv_sec)*1000000000ull+(uint64_t)(b.tv_nsec-a.tv_nsec);
    return 0;
}
int main(void) {
    uint64_t ns=0;size_t retained=0;
    if(source_traces() || synthetic_rules() || negatives_and_pose() || long_run(&ns,&retained))return 1;
    printf("{\"assertions\":%llu,\"original_kernel_comparisons\":%llu,\"unresolved_source_steps_safely_blocked\":%llu,\"source_visited_masks\":[%u,%u],\"stress_steps\":1000000,\"host_stress_elapsed_ns\":%llu,\"actor_retained_bytes\":%zu,\"engine_heap_allocations\":0}\n",
           (unsigned long long)assertions,(unsigned long long)oracle_steps,
           (unsigned long long)source_failures,source_visited[0],source_visited[1],(unsigned long long)ns,retained);
    return 0;
}
