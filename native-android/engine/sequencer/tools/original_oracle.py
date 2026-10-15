"""Compile original, unedited seqsequence.c kernels behind minimal host types.

Stubs supply graph storage, explicit size scale and qrand values; rendering,
ragdolls and debug-only branches are intentionally disabled. The original
functions are extracted to temporary build output, never rewritten.
"""
import re
from pathlib import Path

FUNCTIONS = ["sparseRequiresMet", "seqSetMove", "seqCycleFrame", "seqStep", "seqAInterruptsB", "getSetBits", "seqSearchInterrupts", "seqProcessInst"]

def extract(text, name):
    match=re.search(r"(?m)^[A-Za-z_][^\n]*\b"+name+r"\s*\([^;]*?\)\s*\{",text)
    if not match: raise ValueError("function not found: "+name)
    start=match.start(); body=text.index("{",match.start()); depth=0
    token=re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',re.S)
    for t in token.finditer(text,body):
        if t.group()=="{": depth+=1
        elif t.group()=="}":
            depth-=1
            if not depth: return text[start:t.end()]
    raise ValueError("unterminated function: "+name)

STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "coh_sequencer.h"
typedef uint32_t U32; typedef float F32;
#define MAXSTATES 876
#define STATE_ARRAY_SIZE 28
#define MAX_IRQ_ARRAY_SIZE 14
#define TSTB(a,b) ((a)[(b)/32]&(1u<<((b)%32)))
#define Prefetch(a) ((void)0)
#define eaiGet(a,b) ((*(a))[(b)])
#define CONTEXT_CORRECT_LOADTYPE 0
#define GFXNODE_HIDE 1u
#define SEQPROCESSINST 0
#define cpp_const_cast(t) (t)
#define SEQMOVE_CYCLE COH_SEQ_CYCLE
#define SEQMOVE_FINISHCYCLE COH_SEQ_FINISH_CYCLE
#define SEQMOVE_REQINPUTS COH_SEQ_REQ_INPUTS
#define SEQMOVE_COMPLEXCYCLE COH_SEQ_COMPLEX_CYCLE
#define SEQMOVE_PICKRANDOMLY COH_SEQ_PICK_RANDOMLY
#define SEQMOVE_NODRAW (1u<<25)
#define NEWMOVE_FOUND_BY_SEARCH_OF_INTERRUPTS 1
#define NEWMOVE_FOUND_BY_REQUIREMENTS_FAILED_IN_CYCLE_OR_REQINPUTS 2
#define NEWMOVE_FOUND_BY_REQUIREMENTS_FAILED_IN_FINISHCYCLE 2
#define NEWMOVE_FOUND_BY_NONCYCLING_MOVE_ENDED 4
#define NEWMOVE_FOUND_BY_COMPLEX_CYCLING 8
typedef struct {U32 count; uint16_t bits[12];} SparseBits;
typedef struct {int firstFrame,lastFrame;} AnimP;
typedef struct {float scale; AnimP *animP[1]; int ragdollFrame,animTrack;} TypeGfx;
typedef struct {
    SparseBits required;
    U32 memberBitArray[14],interruptsBitArray[14];
    uint16_t nextMove[4],cycleMove[5],idx;
    uint8_t cycleMoveCnt;
} Raw;
typedef struct SeqMove {const char *name;int priority;U32 flags;float scale;Raw raw;const TypeGfx *typeGfx[1];} SeqMove;
typedef struct {int cnt;int *movesRemainingThatRequireMe;} SeqBitInfo;
typedef struct {const SeqMove **moves;SeqBitInfo *bits;const char *name;} SeqInfo;
typedef struct {const TypeGfx *typeGfx;const SeqMove *move,*prev_move,*move_lastframe,*move_to_send;float frame,prev_frame;bool bRagdoll;} Animation;
typedef struct {U32 flags;} GfxRoot;
typedef struct {const char *name,*seqTypeName;} SeqType;
typedef struct {Animation animation;const SeqInfo *info;U32 state[28],state_lastframe[28];bool forceInterrupt,bCurrentlyInRagdollMode;int anim_incrementor,move_predict_seed;GfxRoot *gfx_root;const char *calculatedSeqTypeName;const SeqType *type;} SeqInst;
static struct {int quickLoadAnims;} state_stub;
#define STATE_STRUCT state_stub
static int g_MaxUsedStates=876;
static float supplied_scale;
static uint32_t supplied_qrand;
static int pointer_count(const void *const *p) {int n=0;while(p[n])++n;return n;}
#define eaSize(p) pointer_count((const void *const *)*(p))
static int isDevelopmentMode(void) {return 0;}
static int isSharedMemory(const void *p) {(void)p;return 0;}
static void Errorf(const char *msg,...) {(void)msg;assert(0);}
static const TypeGfx *seqGetTypeGfx(const SeqInfo *i,const SeqMove *m,const char *n) {(void)i;(void)n;return m->typeGfx[0];}
static void seqAttachAnAnim(TypeGfx *t,int n) {(void)t;(void)n;}
static int testSparseBit(const SparseBits *s,U32 b) {U32 i;for(i=0;i<s->count;++i)if(s->bits[i]==b)return 1;return 0;}
static int qrand(void) {return (int)supplied_qrand;}
static float seqGetAnimScale(const SeqInst *s) {(void)s;return supplied_scale;}
static int seqScaledOnServer(const SeqInst *s) {(void)s;return 0;}
static void seqDebugPrintState(const SeqInst *s,const SeqMove *m,int c,int p) {(void)s;(void)m;(void)c;(void)p;}
'''

BRIDGE = r'''
static SeqMove o_move[130];
static const SeqMove *o_moves[132];
static TypeGfx o_type[130];
static AnimP o_anim[130];
static SeqBitInfo o_bits[876];
static int o_lists[876][130];
static SeqInfo o_info;
static SeqInst o_seq;
void coh_original_init(const CohSeqGraph *g,const CohSeqClip *c,uint32_t move,uint32_t seed) {
    uint32_t i,j;
    assert(g->move_count<129);
    memset(o_move,0,sizeof o_move); memset(o_moves,0,sizeof o_moves);
    memset(o_type,0,sizeof o_type); memset(o_anim,0,sizeof o_anim);
    memset(o_bits,0,sizeof o_bits); memset(&o_seq,0,sizeof o_seq);
    for(i=0;i<g->move_count;++i) {
        const CohSeqMove *m=&g->moves[i];
        SeqMove *o=&o_move[i];
        o->name=m->name; o->flags=m->flags; o->priority=m->priority;o->scale=m->scale;
        o->raw.idx=(uint16_t)i; o->raw.required.count=m->required_count;
        memcpy(o->raw.required.bits,m->required,sizeof m->required);
        memcpy(o->raw.memberBitArray,m->members,sizeof m->members);
        memcpy(o->raw.interruptsBitArray,m->interrupts,sizeof m->interrupts);
        o->raw.nextMove[0]=(uint16_t)(m->next_move==COH_SEQ_NONE?g->move_count:m->next_move);
        o->raw.cycleMoveCnt=(uint8_t)m->cycle_count;
        for(j=0;j<m->cycle_count;++j)o->raw.cycleMove[j]=(uint16_t)m->cycle_moves[j];
        o_anim[i].firstFrame=(int)c[i].first_frame;o_anim[i].lastFrame=(int)c[i].last_frame;
        o_type[i].scale=c[i].type_scale;o_type[i].animP[0]=&o_anim[i];
        o->typeGfx[0]=&o_type[i]; o_moves[i]=o;
        if(m->required_count) {
            U32 bits=0,b=m->required[0];
            for(j=0;j<14;++j)bits|=m->interrupts[j];
            if(bits) o_lists[b][o_bits[b].cnt++]=(int)i;
        }
    }
    /* External edges are never compared; sentinel keeps original assertion's
     * allmovesSize larger than the possible equal-priority candidate count. */
    o_moves[g->move_count]=&o_move[g->move_count];
    for(i=0;i<876;++i)o_bits[i].movesRemainingThatRequireMe=o_lists[i];
    o_info.moves=o_moves;o_info.bits=o_bits;o_seq.info=&o_info;
    o_seq.animation.move=o_moves[move];o_seq.animation.typeGfx=o_moves[move]->typeGfx[0];
    o_seq.animation.frame=c[move].first_frame;o_seq.animation.prev_frame=-1;
    memcpy(&o_seq.move_predict_seed,&seed,sizeof seed);
}
void coh_original_step(const CohSeqInput *in) {
    memcpy(o_seq.state,in->state.words,sizeof o_seq.state);
    o_seq.forceInterrupt=!!in->force_interrupt;
    supplied_scale=in->animation_scale;supplied_qrand=in->random_choice;
    (void)seqProcessInst(&o_seq,in->timestep_frames);
}
void coh_original_snapshot(uint32_t *move,float *frame,float *previous,uint32_t *incrementor,uint32_t *seed) {
    *move=o_seq.animation.move->raw.idx;*frame=o_seq.animation.frame;
    *previous=o_seq.animation.prev_frame;*incrementor=(uint32_t)o_seq.anim_incrementor;
    memcpy(seed,&o_seq.move_predict_seed,sizeof *seed);
}
'''

def write(source_root,output):
    root=Path(source_root)
    text=(root/"Common/seq/seqsequence.c").read_text()
    random=(root/"libs/UtilitiesLib/src/utils/mathutil.c").read_text()
    parts=[STUBS,extract(random,"randUIntGivenSeed")]
    for fn in FUNCTIONS: parts.append(extract(text,fn))
    Path(output).write_text("\n\n".join(parts)+BRIDGE)
