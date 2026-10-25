#!/usr/bin/env python3
"""Exercise original option reads, const table view and actual snapshot writer."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    args=p.parse_args()
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    formatting=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    writer=state[state.index('static void options_receive_state('):state.index('static void friends_receive_state(')]
    native=(args.source/'Game/src/UI/uiOptions.c').read_text()
    start=native.index('const UserOption *armportReplayOptions(')
    assert native[start-len('#ifdef COH_ARMPORT_REPLAY\n'):start]=='#ifdef COH_ARMPORT_REPLAY\n'
    accessor=native[start:native.index('#endif',start)]
    native=(args.source/'Game/src/UI/uiNet.c').read_text()
    start=native.index('void receiveOptions(')
    receiver=native[start:native.index('\n}',start)+2]
    header=(args.source/'Game/src/UI/uiOptions_Type.h').read_text()
    header=header[header.index('typedef struct UserOption'):header.index('}UserOption;')+len('}UserOption;')]
    fixture=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 4096
#define check(x) do { if (!(x)) _Exit(3); } while(0)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
typedef float F32;
static char buffer[CAPACITY];static size_t used;
''' + header + r'''
static UserOption game_options[]={{1,"float",99,0,0,-1,NULL,0},{2,"u32",0,1,0,32,NULL,0},{3,"flag",0,2,0,1,NULL,0},{4,"seven",0,3,0,7,NULL,0}};
enum {kUO_OptionTotal=5};static int initializations;
static UserOption *userOptionGet(int id) {int i;++initializations;for(i=0;i<4;++i)if(game_options[i].id==id)return &game_options[i];return NULL;}
typedef struct {int floats,words;} Packet;
static float pktGetF32(Packet *p) {unsigned bits=0x7fc01234U;float f;++p->floats;memcpy(&f,&bits,4);return f;}
static unsigned pktGetBits(Packet *p,int n) {++p->words;return n==32?0xffffffffU:n==1?1:127;}
''' + formatting + accessor + writer + receiver + r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,count;unsigned bits=0x80000000U;Packet p={0};UserOption saved[4];
 receiveOptions(&p);assert(p.floats==1 && p.words==3 && initializations==4);
 assert(armportReplayOptions(&count)==game_options && count==4 && initializations==4);
 if(mode==1) memcpy(&game_options[0].fVal,&bits,4);
 if(mode==2) game_options[3].iVal=17;
 if(mode==3) {game_options[0].data=&p;game_options[0].delaySave=123;game_options[1].pchDisplayName="changed label";game_options[2].doNotWrite=1;}
 if(mode==4) used=CAPACITY-2;
 if(mode==5) {game_options[0].iVal=17;game_options[1].fVal=17;}
 if(mode==6) {UserOption temp=game_options[0];game_options[0]=game_options[3];game_options[3]=temp;}
 if(mode==7) game_options[3].id=-31,game_options[3].bitSize=32,game_options[3].iVal=(int)0x80000000U;
 memcpy(saved,game_options,sizeof(saved));options_receive_state();
 assert(initializations==4 && !memcmp(saved,game_options,sizeof(saved)));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        p=Path(temporary);(p/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer',str(p/'fixture.c'),'-o',str(p/'fixture')],check=True)
        results=[subprocess.run([str(p/'fixture'),str(i)],capture_output=True,text=True,timeout=15) for i in range(8)]
        for i,r in enumerate(results):assert r.returncode==(3 if i==4 else 0),(i,r.returncode,r.stderr)
        values={i:json.loads(r.stdout) for i,r in enumerate(results) if r.returncode==0}
        expected=[dict(id=1,bit_size=-1,value_f32_bits=[0x7fc01234]),dict(id=2,bit_size=32,value_u32=0xffffffff),dict(id=3,bit_size=1,value_u32=1),dict(id=4,bit_size=7,value_u32=127)]
        assert values[0]==expected and values[3]==expected and values[5]==expected
        assert values[1][0]['value_f32_bits']==[0x80000000] and values[2][-1]['value_u32']==17
        assert values[6]==[expected[3],expected[1],expected[2],expected[0]]
        assert values[7][-1]==dict(id=-31,bit_size=32,value_u32=0x80000000)
    print('options original receiver/actual const view/writer: 8 cases pass; original float/integer reads, literal table order/IDs/bit sizes, selected F32/U32 representation, NaN/negative-zero/high bits, unused storage/cache exclusion, no lazy stash initialization, source immutability and output bounds; ASan/UBSan enabled')


if __name__=='__main__':
    main()
