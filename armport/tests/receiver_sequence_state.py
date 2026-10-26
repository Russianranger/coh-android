#!/usr/bin/env python3
"""Check original sequence receives, retained queues and excluded local timing."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);source=p.parse_args().source
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    receive=(source/'Game/src/entity/entrecv.c').read_text()
    header=(source/'Common/entity/entity.h').read_text()
    fixture=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>
#define CAPACITY 8192
#define check(x) do {if(!(x)) _Exit(3);} while(0)
#define STATIC_INFUNC_ASSERT(x) assert(x)
typedef float F32;typedef uint8_t U8;typedef uint16_t U16;typedef uint32_t U32;
'''
    for name in ['MAX_TRIGGEREDMOVES','NEXTMOVEBIT_COUNT']:
        fixture+=re.search(r'^#define\s+'+name+r'\s+\d+',header,re.M).group(0)+'\n'
    fixture+=(source/'Common/seq/TriggeredMove.h').read_text()+'\n'
    fixture+=r'''
typedef struct Entity {int next_move_idx;U16 next_move_bits;float move_change_timer;void*seq;struct {int send_on_odd_send;}info;TriggeredMove triggered_moves[MAX_TRIGGEREDMOVES];int triggered_move_count;} Entity;
#define ENTINFO(e) ((e)->info)
static int auto_delay=99,last_abs_time=5000,demo_recording=0;static struct{int client_abs;}global_state={3000};
#define TIMESTEP 1
#define ABSTIME_SECOND 3000
#define Errorf(...) assert(0)
static int demo_calls;
static void demoSetAbsTimeOffset(int n){demo_calls++;}
static void demoRecordMove(Entity*e,int idx,int bits){demo_calls++;}
typedef struct Packet {unsigned data[256];int cursor,count;} Packet;
static unsigned take(Packet*p){assert(p->cursor<p->count);return p->data[p->cursor++];}
static unsigned pktGetBits(Packet*p,int n){assert(n==1);return take(p);}
static unsigned pktGetBitsPack(Packet*p,int n){assert(n==1||n==6||n==10);return take(p);}
static unsigned pktGetIfSetBitsPack(Packet*p,int n){assert(n==4||n==8||n==16);return take(p);}
static unsigned pktGetIfSetBits(Packet*p,int n){assert(n==NEXTMOVEBIT_COUNT);return take(p);}
static char buffer[CAPACITY];static size_t used;
'''
    fixture+=function(receive,'static int entReceiveSeqMoveUpdate(')+function(receive,'static int entReceiveSeqTriggeredMoves(')
    fixture+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    fixture+=function(state,'static void entity_sequence_receive_state(')
    fixture+=r'''
int main(int argc,char**argv){
 int mode=argc>1?atoi(argv[1]):0,i,count=2,oo=mode==1;Entity e={0},saved;Packet move={{1,42,15,2047},0,4},trigger={0};
 e.next_move_idx=7;e.next_move_bits=3;e.move_change_timer=123;e.seq=&e;
 if(mode==2)move=(Packet){{0},0,1};
 if(mode==3)count=0;
 if(mode==4||mode==5||mode==6){e.triggered_move_count=mode==4?19:20;for(i=0;i<20;i++)e.triggered_moves[i]=(TriggeredMove){.idx=100+i,.ticksToDelay=i,.triggerFxNetId=200+i};}
 if(mode==6)oo=1;
 if(mode==7)e.info.send_on_odd_send=1;
 if(mode==8)auto_delay=-500;
 if(mode==9)demo_recording=1;
 if(mode==10)move.data[3]=65535;
 if(mode==11)count=MAX_TRIGGEREDMOVES;
 trigger.data[trigger.count++]=count;
 for(i=0;i<count;i++){trigger.data[trigger.count++]=50+i;trigger.data[trigger.count++]=60+i;trigger.data[trigger.count++]=70+i;}
 assert(entReceiveSeqMoveUpdate(&move,&e,oo)==(mode==2?0:1));
 assert(entReceiveSeqTriggeredMoves(&trigger,&e,oo)==count);
 assert(move.cursor==move.count&&trigger.cursor==trigger.count);
 assert(demo_calls==(mode==9?3:0));
 if(mode==7||mode==8)assert(e.move_change_timer==0);
 if(mode==12){e.move_change_timer=-999;for(i=0;i<20;i++){e.triggered_moves[i].timeCreated=999;e.triggered_moves[i].move_found=1;memset(e.triggered_moves[i].state,0xff,sizeof(e.triggered_moves[i].state));}}
 if(mode==13)e.triggered_move_count=-1;
 if(mode==14)e.triggered_move_count=MAX_TRIGGEREDMOVES+1;
 if(mode==15)used=CAPACITY-1;
 if(mode==16)e.triggered_moves[1].triggerFxNetId=-1;
 saved=e;entity_sequence_receive_state(&e);assert(!memcmp(&e,&saved,sizeof(e)));puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);(root/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(root/'fixture.c'),'-o',str(root/'fixture')],check=True)
        for mode in range(17):
            r=subprocess.run([str(root/'fixture'),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if mode in (13,14,15) else 0),(mode,r.returncode,r.stderr)
            if mode in (13,14,15):continue
            v=json.loads(r.stdout)
            assert v['next_index']==(7 if mode in (1,2,6) else 42)
            assert v['next_bits']==(3 if mode in (1,2,6) else 65535 if mode==10 else 2047)
            if mode in (4,5,6):
                expected=[dict(index=100+i,delay_ticks=i,trigger_fx_id=200+i) for i in range(19 if mode==4 else 20)]
                if mode==4:expected.append(dict(index=50,delay_ticks=60,trigger_fx_id=70))
            else:expected=[dict(index=50+i,delay_ticks=60+i,trigger_fx_id=-1 if mode==16 and i==1 else 70+i) for i in range(0 if mode in (1,3) else 20 if mode==11 else 2)]
            assert v['triggered']==expected,(mode,v)
    print('sequence receive state: 17 ASan/UBSan cases; original move and triggered-move receivers; current/stale/absent, append/saturation/dummy consumption, full queue, demo/odd-send/negative timer paths, literal fields, local timing exclusion, source immutability and count/output rejection; packet and demo dependencies substituted')

if __name__=='__main__':main()
