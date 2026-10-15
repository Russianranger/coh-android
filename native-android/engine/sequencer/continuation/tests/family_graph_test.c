#include "coh_sequencer.h"
#include "expanded_graph.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
void coh_original_init(const CohSeqGraph *,const CohSeqClip *,uint32_t,uint32_t);
void coh_original_step(const CohSeqInput *);
void coh_original_snapshot(uint32_t *,float *,float *,uint32_t *,uint32_t *);
int main(void) {
    const CohSeqClip *bindings[3]={male_clips,huge_clips,fem_clips};unsigned compares=0,unavailable=0;uint32_t random=12345;
    for(unsigned body=0;body<3;++body)for(unsigned start=0;start<source_graph.move_count;++start) {
        CohSequencer seq;if(!bindings[body][start].ready)continue;
        if(coh_seq_init(&seq,&source_graph,bindings[body],source_graph.move_count,1,body,start,random))return 2;
        coh_original_init(&source_graph,bindings[body],start,random);
        for(unsigned i=0;i<2000;++i) {
            CohSeqInput in={0};CohSeqSelection selection;
            random=random*1664525u+1013904223u;unsigned wanted=random%source_graph.move_count;
            const CohSeqMove *move=&source_graph.moves[wanted];
            for(unsigned j=0;j<move->required_count;++j)coh_seq_set_bit(&in.state,move->required[j],1);
            in.timestep_frames=(float)((random>>8)%7)*.5f;in.animation_scale=1;in.force_interrupt=i%5==0;in.random_choice=random>>16;
            CohStatus status=coh_seq_step(&seq,&in,&selection);
            if(status==COH_NOT_FOUND || status==COH_UNSUPPORTED){++unavailable;continue;}
            if(status!=COH_OK)return 3;
            coh_original_step(&in);uint32_t actual,incrementor,seed;float frame,previous;
            coh_original_snapshot(&actual,&frame,&previous,&incrementor,&seed);
            if(actual!=seq.move || frame!=seq.frame || previous!=seq.previous_frame || incrementor!=seq.incrementor || seed!=seq.predict_seed)return 4;
            ++compares;
        }
    }
    printf("{\"source_graph_move_count\":%u,\"source_step_comparisons\":%u,\"explicit_missing_clip_or_edge\":%u}\n",source_graph.move_count,compares,unavailable);return compares?0:5;
}
