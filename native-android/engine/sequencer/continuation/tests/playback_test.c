#define _POSIX_C_SOURCE 200809L
#include "coh_seq_playback.h"
#include "coh_locomotion.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"failed %s:%d: %s\n",__FILE__,__LINE__,#x);return 1;}}while(0)
static uint64_t checks,scalars; static float maximum;
#ifdef COH_PLAYBACK_ORACLE
void original_reset(void);
void original_playback(const CohAnimationRig *,const CohAnimationPose *,int,float,float,uint32_t,CohAnimationPose *);
#endif
static unsigned u32(const unsigned char *p){return p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
static int compare(const CohAnimationRig *r,const CohAnimationPose *a,const CohAnimationPose *b) {
    unsigned i,j;
    for(i=0;i<r->node_count;++i) {
        unsigned id=r->order[i];
        for(j=0;j<19;++j) {
            float x,y,error;
            if(j<3){x=a->position[id][j];y=b->position[id][j];}
            else if(j<7){x=a->rotation[id][j-3];y=b->rotation[id][j-3];}
            else{x=a->world_rows[id][j-7];y=b->world_rows[id][j-7];}
            error=fabsf(x-y);if(error>maximum)maximum=error;++scalars;
            CHECK(error<=.000003f+.000003f*fabsf(y));
        }
    }
    return 0;
}
static int cancel(void *p){++*(int *)p;return 1;}
static int tests(const unsigned char *bundle,size_t size) {
    CohAnimationRig rigs[12],male; CohLocomotion accepted; CohSeqPoseBinding bindings[12],replacement[12];
    CohSeqMarker markers[]={{0,10,1,1},{0,11,2,1.5f},{0,12,3,60},{1,20,4,1},{1,21,5,5}};
    CohSeqPlayback p,before; CohSeqSelection sel={0}; CohAnimationPose out,raw,expected,saved;
    CohSeqPlaybackEvent events[300],unchanged[300]; size_t n,oldn; unsigned i; uint64_t generation=0;
    CHECK(size>=128 && !memcmp(bundle,"COHLOCO2",8) && u32(bundle+16)==12);
    for(i=0;i<12;++i) {
        unsigned off=u32(bundle+24+i*8),len=u32(bundle+28+i*8);
        CHECK(off<=size && len<=size-off && !coh_animation_parse(bundle+off,len,&rigs[i]));
    }
    male=rigs[5];
    /* Reuse the unchanged accepted ParentType/animDelta adapter rather than
     * inventing a cross-skeleton retargeting implementation here. */
    CHECK(!coh_locomotion_parse(bundle,size,&accepted));memcpy(rigs,accepted.rigs,sizeof rigs);
    for(i=0;i<12;++i)bindings[i]=(CohSeqPoseBinding){i,7,&rigs[i]};
    CHECK(coh_seq_playback_init(&p,100,7,bindings,12,markers,5)==COH_OK);
    CHECK(p.diagnostics.retained_bytes==sizeof p);
    sel.actor_id=100;sel.rig_id=7;sel.move=0;sel.clip_id=0;sel.frame=1;sel.interpolate_frames=5;
    memset(&out,0xa5,sizeof out);saved=out;memset(events,0xa5,sizeof events);memcpy(unchanged,events,sizeof events);n=42;
    before=p;
    CHECK(coh_seq_playback_sample(&p,&sel,generation,1,0,(CohCancel){0},&out,events,1,&n)==COH_LIMIT);
    CHECK(!memcmp(&p,&before,sizeof p) && !memcmp(&out,&saved,sizeof out) && !memcmp(events,unchanged,sizeof events) && n==42);
    CHECK(coh_seq_playback_sample(&p,&sel,generation,1,0,(CohCancel){0},&out,events,300,&n)==COH_OK);
    CHECK(n==2 && events[0].type==COH_SEQ_EVENT_ENTER && events[1].token==1);
    CHECK(!coh_animation_sample(&rigs[0],1,&raw));CHECK(compare(&rigs[0],&out,&raw)==0);
#ifdef COH_PLAYBACK_ORACLE
    original_reset();original_playback(&rigs[0],&raw,1,1,5,0,&expected);
    CHECK(compare(&rigs[0],&out,&expected)==0);
#endif
    sel.frame=1.5f;
    CHECK(coh_seq_playback_sample(&p,&sel,0,.5f,1,(CohCancel){0},&out,events,300,&n)==COH_OK);
    CHECK(n==1 && events[0].token==2 && events[0].tick==1);
#ifdef COH_PLAYBACK_ORACLE
    CHECK(!coh_animation_sample(&rigs[0],sel.frame,&raw));original_playback(&rigs[0],&raw,0,.5f,5,0,&expected);
    CHECK(compare(&rigs[0],&out,&expected)==0);
#endif
    /* Authentic encoded-key transitions, interruption of an unfinished blend,
     * source NOINTERP stores, zero timestep and self-entry generations. */
    for(i=2;i<18002;++i) {
        int entry=0;float dt=(float)(i%7)*.5f;unsigned cycle=0;
        if(i%5==2) {sel.move=(i/5)%12;sel.clip_id=sel.move;++generation;entry=1;sel.frame=rigs[sel.move].first_frame;
            sel.interpolate_frames=(i%17==0)?0:(i%11==0)?8:5;}
        else {sel.frame+=dt;if(sel.frame>rigs[sel.move].last_frame){sel.frame=rigs[sel.move].first_frame;cycle=COH_SEQ_CAUSE_CYCLE;}}
        sel.flags=(i%101<3)?COH_SEQ_PLAYBACK_NOINTERP:0;
        sel.cause=cycle;
        CHECK(!coh_animation_sample(&rigs[sel.move],sel.frame,&raw));
        {CohStatus result=coh_seq_playback_sample(&p,&sel,generation,dt,i,(CohCancel){0},&out,events,300,&n);
            if(result!=COH_OK)fprintf(stderr,"iteration %u move %u frame %g status %u previous %u\n",i,sel.move,sel.frame,result,p.move);
            CHECK(result==COH_OK);}
#ifdef COH_PLAYBACK_ORACLE
        original_playback(&rigs[sel.move],&raw,entry,dt,sel.interpolate_frames,sel.flags,&expected);
        CHECK(compare(&rigs[sel.move],&out,&expected)==0);
#else
        (void)entry;
#endif
        CHECK(p.interpolation_frame<=1004);
    }
    CHECK(p.diagnostics.samples==18002 && p.diagnostics.transitions>3000 && p.diagnostics.blended_bones>0);
    /* Wrap cue ordering: tail of old cycle before first-frame cue of new. */
    CHECK(coh_seq_playback_init(&p,100,7,bindings,12,markers,5)==COH_OK);
    sel.move=0;sel.clip_id=0;sel.flags=0;sel.cause=0;sel.frame=59;generation=0;
    CHECK(coh_seq_playback_sample(&p,&sel,0,1,0,(CohCancel){0},&out,events,300,&n)==COH_OK);
    sel.cause=COH_SEQ_CAUSE_CYCLE;sel.frame=1.5f;
    CHECK(coh_seq_playback_sample(&p,&sel,0,1,1,(CohCancel){0},&out,events,300,&n)==COH_OK);
    CHECK(n==4 && events[0].type==COH_SEQ_EVENT_CYCLE && events[1].token==3 && events[2].token==1 && events[3].token==2);
    /* Fresh tick without motion does not redeliver threshold markers. */
    sel.cause=0;CHECK(coh_seq_playback_sample(&p,&sel,0,0,2,(CohCancel){0},&out,events,300,&n)==COH_OK && n==0);
    /* Retry/negative/cancellation all leave actor and outputs unchanged. */
    before=p;saved=out;oldn=n;
    CHECK(coh_seq_playback_sample(&p,&sel,0,0,2,(CohCancel){0},&out,events,300,&n)==COH_INVALID);
    CHECK(!memcmp(&p,&before,sizeof p) && !memcmp(&out,&saved,sizeof out) && n==oldn);
    {int calls=0;CHECK(coh_seq_playback_sample(&p,&sel,0,1,3,(CohCancel){cancel,&calls},&out,events,300,&n)==COH_CANCELLED && calls==1);}
    sel.frame=NAN;CHECK(coh_seq_playback_sample(&p,&sel,0,1,3,(CohCancel){0},&out,events,300,&n)==COH_INVALID);sel.frame=1.5f;
    CHECK(coh_seq_playback_sample(&p,&sel,0,4,3,(CohCancel){0},&out,events,300,&n)==COH_INVALID);
    sel.move=1;sel.clip_id=1;sel.frame=1;
    CHECK(coh_seq_playback_sample(&p,&sel,0,1,3,(CohCancel){0},&out,events,300,&n)==COH_STATE);
    sel.actor_id=101;CHECK(coh_seq_playback_sample(&p,&sel,1,1,3,(CohCancel){0},&out,events,300,&n)==COH_INVALID);sel.actor_id=100;
    memcpy(replacement,bindings,sizeof bindings);replacement[1].rig=NULL;
    CHECK(coh_seq_playback_rebind(&p,replacement,12)==COH_OK);
    before=p;CHECK(coh_seq_playback_sample(&p,&sel,1,1,3,(CohCancel){0},&out,events,300,&n)==COH_NOT_FOUND);
    CHECK(!memcmp(&p,&before,sizeof p));CHECK(coh_seq_playback_rebind(&p,bindings,12)==COH_OK);
    replacement[0].rig=NULL;CHECK(coh_seq_playback_rebind(&p,replacement,12)==COH_STATE);
    {CohSeqMarker bad=markers[0];bad.frame=-1;CHECK(coh_seq_playback_init(&before,1,7,bindings,12,&bad,1)==COH_INVALID);}
    {CohSeqMarker bad[2]={markers[1],markers[0]};CHECK(coh_seq_playback_init(&before,1,7,bindings,12,bad,2)==COH_INVALID);}
    {CohAnimationRig bad=rigs[0];bad.order[1]=bad.order[0];memcpy(replacement,bindings,sizeof bindings);replacement[0].rig=&bad;
        CHECK(coh_seq_playback_init(&before,1,7,replacement,12,NULL,0)==COH_INVALID);}
    {CohSeqBits base={{0}},result,savedbits;CohSeqStateUpdate updates[]={{5,1},{6,1},{297,1},{5,0}};
        CHECK(coh_seq_playback_state(&base,updates,4,&result)==COH_OK);
        CHECK(result.words[0]==(1u<<6) && result.words[9]==(1u<<9));savedbits=result;updates[3].bit=876;
        CHECK(coh_seq_playback_state(&base,updates,4,&result)==COH_INVALID && !memcmp(&result,&savedbits,sizeof result));
        updates[3].bit=0;updates[3].on=2;CHECK(coh_seq_playback_state(&base,updates,4,&result)==COH_INVALID);
    }
    /* Bounded malformed metadata fuzzing never constructs invalid pointers. */
    for(i=0;i<20000;++i) {
        CohSeqMarker m=markers[0];CohStatus status;unsigned value=i*2654435761u;
        switch(i%5) {
            case 0:m.move=value%20;break;
            case 1:m.frame=(float)(int32_t)value;break;
            case 2:m.frame=NAN;break;
            case 3:m.frame=INFINITY;break;
            default:m.frame=(float)(value%70);break;
        }
        status=coh_seq_playback_init(&before,100,7,bindings,12,&m,1);
        CHECK(status==COH_OK || status==COH_INVALID);
        if(status==COH_OK) {
            CohSeqBits bits={{0}},copied;CohSeqStateUpdate update={(uint16_t)(value%1024),(uint8_t)(value%3)};
            status=coh_seq_playback_state(&bits,&update,1,&copied);
            CHECK(status==COH_OK || status==COH_INVALID);
        }
    }
    /* Every declared cue fits the documented fixed upper output bound. */
    {CohSeqMarker maximum_markers[COH_SEQ_PLAYBACK_MARKERS];
        for(i=0;i<COH_SEQ_PLAYBACK_MARKERS;++i)maximum_markers[i]=(CohSeqMarker){0,1,i,1};
        CHECK(coh_seq_playback_init(&p,100,7,bindings,12,maximum_markers,COH_SEQ_PLAYBACK_MARKERS)==COH_OK);
        sel=(CohSeqSelection){0};sel.actor_id=100;sel.rig_id=7;sel.frame=1;sel.interpolate_frames=5;
        CHECK(coh_seq_playback_sample(&p,&sel,0,1,0,(CohCancel){0},&out,events,COH_SEQ_PLAYBACK_EVENTS-1,&n)==COH_LIMIT);
        CHECK(coh_seq_playback_sample(&p,&sel,0,1,0,(CohCancel){0},&out,events,COH_SEQ_PLAYBACK_EVENTS,&n)==COH_OK && n==COH_SEQ_PLAYBACK_EVENTS);
        for(i=0;i<COH_SEQ_PLAYBACK_MARKERS;++i)CHECK(events[i+1].token==i);
        /* Force self-reentry is an explicit sequencer transition generation. */
        CHECK(coh_seq_playback_sample(&p,&sel,1,1,1,(CohCancel){0},&out,events,COH_SEQ_PLAYBACK_EVENTS,&n)==COH_OK && events[0].type==COH_SEQ_EVENT_ENTER);
    }
    /* Different logical rigs and actors require no engine branches. Use the
     * actual male idle base/motion binding from accepted fallback corpus. */
    for(i=0;i<12;++i)replacement[i]=(CohSeqPoseBinding){i,99,&rigs[i]};
    replacement[5].rig=&male;
    CHECK(coh_seq_playback_init(&p,900,99,replacement,12,NULL,0)==COH_OK);
    sel=(CohSeqSelection){0};sel.actor_id=900;sel.rig_id=99;sel.move=5;sel.clip_id=5;sel.frame=1;sel.interpolate_frames=5;
    CHECK(coh_seq_playback_sample(&p,&sel,0,1,0,(CohCancel){0},&out,events,300,&n)==COH_OK);
    CHECK(!coh_animation_sample(&male,1,&raw) && !memcmp(&raw,&out,sizeof raw));
    printf("{\"checks\":%llu,\"source_pose_scalar_comparisons\":%llu,\"maximum_error\":%.9g,\"raw_rigs\":12,\"retained_actor_bytes\":%zu,\"heap_calls_per_sample\":0,\"frames\":18002}\n",(unsigned long long)checks,(unsigned long long)scalars,maximum,sizeof p);
    return 0;
}
int main(int argc,char **argv) {
    FILE *f;long length;unsigned char *data;int result;
    if(argc!=2 || !(f=fopen(argv[1],"rb")))return 2;
    if(fseek(f,0,SEEK_END) || (length=ftell(f))<0 || length>512*1024 || fseek(f,0,SEEK_SET))return 2;
    data=malloc((size_t)length);if(!data || fread(data,1,(size_t)length,f)!=(size_t)length)return 2;fclose(f);
    result=tests(data,(size_t)length);free(data);return result;
}
