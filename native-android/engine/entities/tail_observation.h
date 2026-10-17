#ifndef COH_TAIL_OBSERVATION_H
#define COH_TAIL_OBSERVATION_H
/* Test-only exact serialization of original receiver state, never a public ABI. */
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define TAIL_OBSERVATION_MAX (192u*1024u)
typedef struct { uint32_t used; unsigned char bytes[TAIL_OBSERVATION_MAX]; } TailObservation;
static void observe_word(TailObservation *o,uint32_t value) {
    assert(o->used<=TAIL_OBSERVATION_MAX-4);
    for(unsigned i=0;i<4;i++)o->bytes[o->used++]=(unsigned char)(value>>(8*i));
}
static void observe_text(TailObservation *o,const char *text,size_t cap) {
    size_t length=0;while(length+1<cap&&text[length])length++;
    assert(length+1<=TAIL_OBSERVATION_MAX-o->used);
    memcpy(o->bytes+o->used,text,length);o->used+=(uint32_t)length;o->bytes[o->used++]=0;
}
static void observe_float(TailObservation *o,float f) {uint32_t bits;memcpy(&bits,&f,4);observe_word(o,bits);}
#endif
