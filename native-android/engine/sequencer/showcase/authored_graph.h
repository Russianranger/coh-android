/* Generated from the unchanged source subset in
 * continuation/fixtures/expanded_graph.json; missing graph edges stay explicit.
 * Reproduce using showcase/check.py. Neutral clip rigs stay external. */
#ifndef COH_SEQ_SHOWCASE_AUTHORED_GRAPH_H
#define COH_SEQ_SHOWCASE_AUTHORED_GRAPH_H
/* Generated from hash-pinned original sequencer data. */
#include "coh_sequencer.h"
#define COH_SHOWCASE_STATE_COMBAT 20u
#define COH_SHOWCASE_STATE_PUNCH 256u
#define COH_SHOWCASE_STATE_COMBO2 292u
#define COH_SHOWCASE_STATE_JUMPNSMASH 354u
#define COH_SHOWCASE_STATE_STRONG 682u
#define COH_SHOWCASE_STATE_RAISEDEAD 323u
#define COH_SHOWCASE_MOVE_JUMPPOST 0u
#define COH_SHOWCASE_MOVE_1_2PUNCH 1u
#define COH_SHOWCASE_MOVE_1_2PUNCHPOST 2u
#define COH_SHOWCASE_MOVE_JUMPNSMASH 3u
#define COH_SHOWCASE_MOVE_JUMPNSMASH_POST 4u
#define COH_SHOWCASE_MOVE_FALLOUT 5u
static const CohSeqMove coh_showcase_moves[] = {
{"JumpPost", 0u, 0, {0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, 0u, {18u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, {0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, COH_SEQ_NONE, {0}, 0, 0.7f, 1.0f},
{"1_2punch", 128u, 3, {20u,256u,292u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, 3u, {2u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, {2u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, 2u, {0}, 0, 1.0f, 5.0f},
{"1_2punchpost", 136u, 0, {20u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, 1u, {18u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, {0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, COH_SEQ_NONE, {0}, 0, 0.5f, 5.0f},
{"jumpNsmash", 128u, 2, {20u,354u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, 2u, {2u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, {2u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, 4u, {0}, 0, 1.0f, 5.0f},
{"jumpNsmash_post", 136u, 0, {20u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, 1u, {18u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, {0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, COH_SEQ_NONE, {0}, 0, 0.5f, 5.0f},
{"Fallout", 640u, 2, {682u,323u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, 2u, {0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, {28u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u}, COH_SEQ_NONE, {0}, 0, 1.0f, 5.0f},
};
static const CohSeqGraph coh_showcase_graph={coh_showcase_moves,sizeof coh_showcase_moves/sizeof coh_showcase_moves[0]};
static const CohSeqClip coh_showcase_male_clips[] = {
{{"ANIMS/male/comb_postjump.anim",1},0,1,1.0f,69.0f,1.0f},
{{"ANIMS/male/1_2punch.anim",1},1,1,1.0f,40.0f,1.0f},
{{"ANIMS/male/1_2punch.anim",1},2,1,40.0f,62.0f,1.0f},
{{"ANIMS/male/jump_n_smash.anim",1},3,1,1.0f,98.0f,1.0f},
{{"ANIMS/male/jump_n_smash.anim",1},4,1,98.0f,124.0f,1.0f},
{{"ANIMS/male/fallout.anim",1},5,1,1.0f,147.0f,1.0f},
};
static const CohSeqClip coh_showcase_huge_clips[] = {
{{"ANIMS/huge/combat_postjump.anim",1},0,1,1.0f,69.0f,1.0f},
{{"ANIMS/huge/1_2punch.anim",1},1,1,1.0f,40.0f,1.0f},
{{"ANIMS/huge/1_2punch.anim",1},2,1,40.0f,62.0f,1.0f},
{{"ANIMS/huge/jump_n_smash.anim",1},3,1,1.0f,98.0f,1.0f},
{{"ANIMS/huge/jump_n_smash.anim",1},4,1,98.0f,124.0f,1.0f},
{{"ANIMS/huge/fallout.anim",1},5,1,1.0f,147.0f,1.0f},
};

static const CohSeqClip coh_showcase_fem_clips[]={
{{"ANIMS/fem/combat_postjump.anim",1},0,1,1.0f,32.0f,1.0f},
{{"ANIMS/fem/1_2punch.anim",1},1,1,1.0f,40.0f,1.0f},
{{"ANIMS/fem/1_2punch.anim",1},2,1,40.0f,62.0f,1.0f},
{{"ANIMS/fem/jump_n_smash.anim",1},3,1,1.0f,98.0f,1.0f},
{{"ANIMS/fem/jump_n_smash.anim",1},4,1,98.0f,124.0f,1.0f},
{{"ANIMS/fem/fallout.anim",1},5,1,1.0f,147.0f,1.0f},
};

#endif
