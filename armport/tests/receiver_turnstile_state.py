#!/usr/bin/env python3
"""Exercise original queue/status receivers, const accessors and actual writers."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    args = p.parse_args()
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    writer = ''.join(function(state, name) for name in ('static void turnstile_mission_state(', 'static void turnstile_receive_state(', 'static void player_turnstile_state('))
    native = (args.source / 'Game/src/UI/uiTurnstile.c').read_text()
    start = native.index('const TurnstileMissionClient *const *armportReplayTurnstileMissions(')
    assert native[start-len('#ifdef COH_ARMPORT_REPLAY\n'):start] == '#ifdef COH_ARMPORT_REPLAY\n'
    accessor = native[start:native.index('#endif',start)]
    receivers = ''
    for name in ['turnstileGame_handleQueueStatus','turnstileGame_handleTurnstileGeneralStatus']:
        start=native.index('void '+name+'(')
        receivers += native[start:native.index('\n}',start)+2]+'\n'
    header=(args.source/'Common/turnstile/TurnstileCommon.h').read_text()
    enums=header[header.index('typedef enum'):header.index('} TurnstileCategory;')+len('} TurnstileCategory;')]
    header=(args.source/'Game/src/UI/uiTurnstile.h').read_text()
    mission=header[header.index('typedef struct TurnstileMissionClient'):header.index('} TurnstileMissionClient;')+len('} TurnstileMissionClient;')]
    fixture = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024*1024)
#define MAX_EVENT 1000
#define check(x) do { if (!(x)) _Exit(3); } while (0)
static char buffer[CAPACITY];static size_t used;
''' + enums + mission + r'''
static TurnstileMissionClient **turnstileMissions;
static TurnstileMissionClient s_firstAvailableDummyMission,s_firstAvailableCategoryDummyMission[kTurnstileCategory_Count];
static int inQueue;static float currentWait;static unsigned queueTick,requestTick;
typedef struct {int lastTurnstileEventID,lastTurnstileMissionID;} EntPlayer;
typedef struct {EntPlayer *pl;} Entity;
static Entity *player;static Entity *playerPtr(void) {return player;}
static int eaSize(const void *address) {void *items;memcpy(&items,address,sizeof(items));return items?(int)((size_t*)items)[-1]:0;}
typedef struct {unsigned bits[8];int cursor;} Packet;
static unsigned pktGetBitsAuto(Packet *p) {assert(p->cursor<8);return p->bits[p->cursor++];}
static unsigned pktGetBits(Packet *p,int bits) {assert(bits==1);return pktGetBitsAuto(p);}
static float pktGetF32(Packet *p) {unsigned bits=pktGetBitsAuto(p);float f;memcpy(&f,&bits,4);return f;}
''' + formatting + accessor + writer + receivers + r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,i;unsigned nan=0x7fc01234U;
 TurnstileMissionClient a={"Mission\"A",0,1,0,1,kTurnstileCategory_Trial,0};
 TurnstileMissionClient b={NULL,0,0,0,2,kTurnstileCategory_TaskforceContact,1};
 static struct {size_t count;TurnstileMissionClient *items[8192];} list={2,{NULL}};
 TurnstileMissionClient copy_a,copy_b;EntPlayer pl={17,31},copy_pl;Entity e={&pl};
 Packet queue={{1,0x80000000U,2,0,1},0};
 player=&e;list.items[0]=&a;list.items[1]=&b;turnstileMissions=list.items;
 memcpy(&a.avgWait,&nan,4);
 turnstileGame_handleQueueStatus(&queue);assert(queue.cursor==5 && queueTick==0);
 assert((const void *)armportReplayTurnstileMissions()==(const void *)turnstileMissions);
 assert(armportReplayTurnstileWait()==&currentWait);
 assert(armportReplayTurnstileDummy(-1)==&s_firstAvailableDummyMission);
 assert(!armportReplayTurnstileDummy(-2) && !armportReplayTurnstileDummy(kTurnstileCategory_Count));
 for(i=0;i<kTurnstileCategory_Count;++i)assert(armportReplayTurnstileDummy(i)==&s_firstAvailableCategoryDummyMission[i]);
 if(mode==1) {Packet p={{0},0};turnstileGame_handleQueueStatus(&p);assert(p.cursor==1);}
 if(mode==2 || mode==3) {Packet p={{7,0xffffffffU,17},0};if(mode==3)player=NULL;turnstileGame_handleTurnstileGeneralStatus(&p);assert(p.cursor==3);}
 if(mode==4) turnstileMissions=NULL;
 if(mode==5) list.count=8193;
 if(mode==6) list.count=(size_t)-1;
 if(mode==7) list.count=3,list.items[1]=NULL,list.items[2]=&b;
 if(mode==8) list.items[0]=&b,list.items[1]=&a;
 if(mode==9) used=CAPACITY-2;
 if(mode==10) queueTick=0xffffffffU,requestTick=0x80000000U;
 if(mode==11) list.count=8192,list.items[8191]=&b;
 if(mode==12) {static char large[CAPACITY+1];memset(large,'x',CAPACITY);a.name=large;}
 if(mode==13) a.index=-31,a.category=kTurnstileCategory_HolidayTrial,a.eligible=1,a.isWeeklyTF=0;
 copy_a=a;copy_b=b;copy_pl=pl;
 out("{\"queue\":");turnstile_receive_state();out(",\"player\":");player_turnstile_state(&pl);out("}");
 assert(!memcmp(&a,&copy_a,sizeof(a)) && !memcmp(&b,&copy_b,sizeof(b)) && !memcmp(&pl,&copy_pl,sizeof(pl)));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        p = Path(temporary)
        (p/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g',
                        '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                        str(p/'fixture.c'),'-o',str(p/'fixture')],check=True)
        results=[subprocess.run([str(p/'fixture'),str(i)],capture_output=True,text=True,timeout=15) for i in range(14)]
        for i,r in enumerate(results):
            assert r.returncode==(3 if i in (5,6,9,12) else 0),(i,r.returncode,r.stderr)
        values={i:json.loads(r.stdout) for i,r in enumerate(results) if r.returncode==0}
        mission=dict(name='Mission"A',average_wait_f32_bits=[0x7fc01234],weekly=1,selected=1,index=1,category=0,eligible=0)
        other=dict(name=None,average_wait_f32_bits=[0],weekly=0,selected=1,index=2,category=3,eligible=1)
        dummy=dict(name=None,average_wait_f32_bits=[0],weekly=0,selected=0,index=0,category=0,eligible=0)
        cats=[dict(dummy,selected=int(i in (0,3))) for i in range(4)]
        expected=dict(queue=dict(in_queue=1,current_wait_f32_bits=[0x80000000],missions=[mission,other],all_dummy=dummy,category_dummies=cats),player=dict(last_event_id=17,last_mission_id=31))
        assert values[0]==expected and values[3]==expected and values[10]==expected
        assert values[1]['queue']['in_queue']==0 and values[1]['queue']['current_wait_f32_bits']==[0]
        assert values[1]['queue']['missions'][0]['selected']==0 and values[1]['queue']['missions'][1]['selected']==1
        assert values[2]['queue']['in_queue']==7 and values[2]['player']==dict(last_event_id=-1,last_mission_id=17)
        assert values[4]['queue']['missions']==[] and values[7]['queue']['missions']==[mission,None,other]
        assert values[8]['queue']['missions']==[other,mission]
        assert len(values[11]['queue']['missions'])==8192 and values[11]['queue']['missions'][-1]==other
        assert values[13]['queue']['missions'][0]==dict(mission,index=-31,category=2,eligible=1,weekly=0)
    print('turnstile original receivers/actual accessors/writers: 14 cases pass; queue enter/leave/general-status/no-player, retained mission selections and dummy categories, null/order/final slots, raw wait bits, literal player IDs, clock exclusion, source immutability, count/string/output bounds; ASan/UBSan enabled')


if __name__=='__main__':
    main()
