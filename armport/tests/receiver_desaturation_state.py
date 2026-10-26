#!/usr/bin/env python3
"""Check actual original/patched reads and raw desaturation observation."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    state = (root / 'armport/replay/state.c').read_text()
    formatting = state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    observer = state[state.index('void armportReplayDesaturation('):state.index('static void karma_receive_state(')]
    rel = 'Game/src/clientcomm/clientcommreceive.c'

    def receiver(text, name):
        start = text.index('void receiveDesaturateInfo(')
        return text[start:text.index('\n}', start)+2].replace('receiveDesaturateInfo(', name+'(')

    original = receiver((root / 'upstream/ouroboros' / rel).read_text(), 'original')
    patched = receiver((args.source / rel).read_text(), 'patched')
    assert patched.count('pktGetF32(pak)') == original.count('pktGetF32(pak)') == 4
    fixture = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 4096
#define check(x) assert(x)
static char buffer[CAPACITY]; static size_t used;
static int active;
static struct {unsigned valid,bits[4];} desaturation;
static struct {float desaturateDelay,desaturateWeight,desaturateWeightTarget,desaturateFadeTime;} game_state;
typedef struct {unsigned bits[4];int cursor;} Packet;
static float pktGetF32(Packet *p) {float f;assert(p->cursor<4);memcpy(&f,&p->bits[p->cursor++],4);return f;}
''' + formatting + observer + original + patched + r'''
int main(void) {
 unsigned inputs[][4]={{0,0x80000000U,0x3f800000U,0x41200000U},
     {0x7fc01234U,0xff800000U,0x7f800000U,0x00000001U},
     {0xbf800000U,0x3e800000U,0x3f000000U,0x7f7fffffU}};
 unsigned saved[4],prior[4];int i,on;
 used=0;desaturation_receive_state();assert(!strcmp(buffer,"null"));
 /* Disabled observation does not even dereference its arguments. */
 armportReplayDesaturation(NULL,NULL,NULL,NULL);assert(!desaturation.valid);
 for(on=0;on<2;++on) for(i=0;i<3;++i) {
   Packet p={{0},0},q={{0},0};memcpy(p.bits,inputs[i],sizeof(p.bits));q=p;
   active=on;memset(&desaturation,0,sizeof(desaturation));memcpy(desaturation.bits,inputs[2],sizeof(prior));
   memcpy(prior,desaturation.bits,sizeof(prior));
   original(&p);memcpy(saved,&game_state,sizeof(saved));
   memset(&game_state,0xcc,sizeof(game_state));patched(&q);
   assert(p.cursor==4 && q.cursor==4 && !memcmp(saved,&game_state,sizeof(saved)));
   assert(!memcmp(p.bits,q.bits,sizeof(p.bits)) && !memcmp(saved,inputs[i],sizeof(saved)));
   assert(desaturation.valid==(unsigned)on);
   assert(!memcmp(desaturation.bits,on?inputs[i]:prior,sizeof(prior)));
   if(on) {
     char expected[256];snprintf(expected,sizeof(expected),"[%u,%u,%u,%u]",inputs[i][0],inputs[i][1],inputs[i][2],inputs[i][3]);
     /* Frame-time changes must not replace the received representation. */
     game_state.desaturateDelay=3;game_state.desaturateWeight=4;game_state.desaturateWeightTarget=5;game_state.desaturateFadeTime=6;
     used=0;desaturation_receive_state();assert(!strcmp(buffer,expected));
     q.cursor=0;memcpy(q.bits,inputs[(i+1)%3],sizeof(q.bits));patched(&q);
     assert(q.cursor==4 && !memcmp(desaturation.bits,q.bits,sizeof(q.bits)));
   }
 }
 puts("desaturation actual original/patched receiver: 6 off/on cases and 3 replacements pass; four packet reads and stored F32 bits unchanged, null-before-receive, inactive no-dereference, NaN/negative-zero/infinity/subnormal bits preserved, frame-time changes excluded; ASan/UBSan enabled");
 return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        p = Path(temporary)
        (p / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(p / 'fixture.c'), '-o', str(p / 'fixture')], check=True)
        subprocess.run([str(p / 'fixture')], check=True)


if __name__ == '__main__':
    main()
