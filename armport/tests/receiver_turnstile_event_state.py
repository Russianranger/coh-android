#!/usr/bin/env python3
"""Exercise original event receivers and the retained event accessor/writer."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    native = (args.source / 'Game/src/UI/uiTurnstile.c').read_text()
    header = (args.source / 'Game/src/clientcomm/armport_replay.h').read_text()
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    struct = header[header.index('typedef struct ArmPortTurnstileEventState'):header.index('} ArmPortTurnstileEventState;') + len('} ArmPortTurnstileEventState;')]
    accessor = function(native, 'void armportReplayTurnstileEventState(')
    assert '#ifdef COH_ARMPORT_REPLAY' in native[native.index(accessor)-220:native.index(accessor)]
    fixture = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
#define CAPACITY 4096
#define check(x) do { if (!(x)) _Exit(3); } while (0)
typedef uint32_t U32;
static char buffer[CAPACITY]; static size_t used;
static int eventResponseExpected, event_acceptedCount, event_declinedCount;
static int event_inProgress, event_playerCount, status_playerCount;
static char event_name[256];
static U32 event_instanceID, status_replied1, status_replied2, status_status1, status_status2;
static U32 requestTick,queueTick;
typedef struct Packet {const char *text; U32 values[8]; int reads,widths[8];} Packet;
static const char *pktGetString(Packet *p) {return p->text;}
static U32 pktGetBits(Packet *p,int width) {assert(p->reads<8);p->widths[p->reads]=width;return p->values[p->reads++];}
static U32 pktGetBitsAuto(Packet *p) {return pktGetBits(p,-1);}
static void strncpyt(char *d,const char *s,size_t n) {snprintf(d,n,"%s",s);}
static Packet ack_packet;static int acks,dialogs;static U32 ack_id;
#define CLIENTINP_EVENT_READY_ACK 123
#define START_INPUT_PACKET(pak, command) { Packet *pak=&ack_packet; assert(command==123); ++acks;
#define END_INPUT_PACKET }
static void pktSendBits(Packet *p,int width,U32 value) {assert(p==&ack_packet && width==32);ack_id=value;}
#define _snprintf snprintf
static const char *textStd(const char *key,...) {return key;}
static void turnstileDialogWindowActivate(const char *a,const char *b,const char *c,int delay,const char *d,const char *e,void *f,void *g,void *h,void *i,int hide) {++dialogs;assert(delay==0 && hide==!eventResponseExpected);}
''' + struct + '\n'
    fixture += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    fixture += function(state, 'static void fixed_string(')
    fixture += accessor + function(state, 'static void turnstile_event_state(')
    for name in ('turnstileGame_handleEventReady', 'turnstileGame_handleEventReadyAccept', 'turnstileGame_handleEventStatus'):
        fixture += function(native, 'void '+name+'(')
    fixture += r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0;
 Packet ready={"Event \"name\"\n",{1,127,0x80000001U},0,{0}};
 Packet accept={NULL,{7,2,129},0,{0}};
 Packet status={NULL,{130,0x80000000U,0xffffffffU,0x12345678U,0x87654321U},0,{0}};
 ArmPortTurnstileEventState before,after;
 if(mode!=1) {
  turnstileGame_handleEventReady(&ready);
  assert(ready.reads==3 && ready.widths[0]==1 && ready.widths[1]==-1 && ready.widths[2]==32);
  assert(acks==1 && ack_id==0x80000001U);
  turnstileGame_handleEventReadyAccept(&accept);assert(accept.reads==3 && dialogs==1);
  turnstileGame_handleEventStatus(&status);assert(status.reads==5 && status.widths[0]==-1 && status.widths[4]==32);
 }
 if(mode==2) {Packet p={NULL,{0,0,0,0,0},0,{0}};turnstileGame_handleEventStatus(&p);assert(p.reads==5);}
 if(mode==3) {Packet p={"Replacement",{0,1,31},0,{0}};turnstileGame_handleEventReady(&p);assert(p.reads==3 && acks==2 && ack_id==31);}
 if(mode==4) eventResponseExpected=0;
 if(mode==5) event_acceptedCount=-1,event_declinedCount=-31,event_playerCount=-32,status_playerCount=-155;
 if(mode==6) memset(event_name,'x',255),event_name[255]=0;
 if(mode==7) memset(event_name,'x',256);
 if(mode==8) used=CAPACITY-1;
 if(mode==9) requestTick=0xffffffffU,queueTick=0x80000000U;
 if(mode==10) status_replied1=1,status_status2=31,event_instanceID=1;
 memset(&before,0,sizeof(before));memset(&after,0,sizeof(after));
 armportReplayTurnstileEventState(&before);
 assert(before.name==event_name && before.name_capacity==256);
 turnstile_event_state();
 armportReplayTurnstileEventState(&after);
 assert(!memcmp(&before,&after,sizeof(before)));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)
        (path/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'fixture.c'),'-o',str(path/'fixture')],check=True)
        values={}
        for i in range(11):
            r=subprocess.run([str(path/'fixture'),str(i)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if i in (7,8) else 0),(i,r.returncode,r.stderr)
            if r.returncode==0:values[i]=json.loads(r.stdout)
        baseline=dict(name='Event "name"\n',response_expected=1,accepted_count=7,declined_count=2,in_progress=1,player_count=129,instance_id=0x80000001,status_player_count=130,replied_u32=[0x80000000,0xffffffff],status_u32=[0x12345678,0x87654321])
        assert values[0]==baseline and values[9]==baseline
        assert values[1]==dict(name='',response_expected=0,accepted_count=0,declined_count=0,in_progress=0,player_count=0,instance_id=0,status_player_count=0,replied_u32=[0,0],status_u32=[0,0])
        assert values[2]==dict(baseline,status_player_count=0,replied_u32=[0,0],status_u32=[0,0])
        assert values[3]==dict(baseline,name='Replacement',in_progress=0,player_count=1,instance_id=31)
        assert values[4]==dict(baseline,response_expected=0)
        assert values[5]==dict(baseline,accepted_count=-1,declined_count=-31,player_count=-32,status_player_count=-155)
        assert values[6]==dict(baseline,name='x'*255)
        assert values[10]==dict(baseline,instance_id=1,replied_u32=[1,0xffffffff],status_u32=[0x12345678,31])
    print('turnstile event original receivers/accessor/writer: 11 cases pass; exact reads/ACK, accepted/status replacement, literal high-bit and 1/31 IDs, response changes, signed counts, bounded name/output, local clock exclusion, nonmutation; ASan/UBSan enabled')


if __name__=='__main__':
    main()
