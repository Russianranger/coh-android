#!/usr/bin/env python3
"""Exercise original control receive fragments and literal retained-state view."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    source=parser.parse_args().source
    root=Path(__file__).resolve().parents[2]
    state=(root/'armport/replay/state.c').read_text()
    receive=(source/'Game/src/entity/entrecv.c').read_text()
    original=(root/'upstream/ouroboros/Game/src/entity/entrecv.c').read_text()
    def fragments(text):
        flags=text[text.index('    control_state.first = pktGetBits( pak, 1 );'):text.index('    START_BIT_COUNT(pak, "receiveFriendsList");')]
        start=text.index('            // Receive the QROT for a slave.')
        slave=text[start:text.index('            // Get rid of any remaining unclaimed floaters,',start)]
        return flags,slave
    flags,slave=fragments(receive)
    assert (flags,slave)==fragments(original),'Original receive bodies changed'
    fixture=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 4096
#define check(x) do {if(!(x)) _Exit(3);} while(0)
static char buffer[CAPACITY];static size_t used;
static struct {struct {float cur[3],motion[3];unsigned prev[3],send[3];}pyr;int first,nocoll;unsigned local_clock;}control_state;
typedef struct {unsigned data[8];unsigned cursor,count;}Packet;
static unsigned take(Packet*p){assert(p->cursor<p->count);return p->data[p->cursor++];}
static unsigned pktGetBits(Packet*p,int n){unsigned x=take(p);assert((n==1||n==2)&&x<(1U<<n));return x;}
static float pktGetF32(Packet*p){unsigned x=take(p);float f;memcpy(&f,&x,4);return f;}
static void flags_receive(Packet*pak){
'''+flags+'}\nstatic void slave_receive(Packet*pak){\n'+slave+'}\n'
    fixture+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    fixture+=function(state,'static void retained_control_state(')
    fixture+=r'''
int main(int argc,char**argv){
 unsigned mode=argc>1?(unsigned)atoi(argv[1]):0,bits[3]={0x80000000U,0x7fc12345U,0xff800000U};
 unsigned char saved[sizeof(control_state)];Packet flags={{mode&1,(mode>>1)&3},0,2};
 Packet slave={{mode<8,0x3f800000U,0xc0200000U,0},0,mode<8?4:1};
 memcpy(control_state.pyr.cur,bits,sizeof(bits));control_state.first=-7;control_state.nocoll=42;
 flags_receive(&flags);slave_receive(&slave);assert(flags.cursor==flags.count&&slave.cursor==slave.count);
 if(mode==10){control_state.local_clock=0xffffffff;memset(control_state.pyr.motion,0xff,sizeof(control_state.pyr.motion));memset(control_state.pyr.prev,0xff,sizeof(control_state.pyr.prev));memset(control_state.pyr.send,0xff,sizeof(control_state.pyr.send));}
 if(mode==11)used=CAPACITY-1;
 memcpy(saved,&control_state,sizeof(saved));retained_control_state();assert(!memcmp(saved,&control_state,sizeof(saved)));puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp);(path/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'fixture.c'),'-o',str(path/'fixture')],check=True)
        for mode in range(12):
            result=subprocess.run([str(path/'fixture'),str(mode)],capture_output=True,text=True,timeout=15)
            assert result.returncode==(3 if mode==11 else 0),(mode,result.returncode,result.stderr)
            if mode==11:continue
            data=json.loads(result.stdout)
            assert data==dict(first=mode&1,nocoll=(mode>>1)&3,pyr_f32_bits=[0x3f800000,0xc0200000,0] if mode<8 else [0x80000000,0x7fc12345,0xff800000]),(mode,data)
    print('retained controls: 12 ASan/UBSan cases; original unchanged receive fragments, all first/nocoll combinations, present/absent slave orientation, exact F32 bits including NaN/negative zero/infinity, unchanged consumption and state, excluded local fields and overflow rejection; packet primitives and surrounding receiver lifecycle substituted, not native ABI/full control-state qualification')

if __name__=='__main__':main()
