#!/usr/bin/env python3
"""Run the original force-queue receiver with the actual observer/writer."""
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
    source = p.parse_args().source
    native = (source/'Game/src/UI/uiTurnstile.c').read_text()
    state = (Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    assert '#define MAX_NAME_LEN 128' in (source/'Common/entity/gametypes.h').read_text()
    accessor = function(native, 'const char *armportReplayTurnstileForceQueue(')
    assert '#ifdef COH_ARMPORT_REPLAY\n'+accessor in native
    code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 4096
#define check(x) do { if (!(x)) _Exit(3); } while(0)
static char buffer[CAPACITY]; static size_t used;
static char sForceQueueEvent[128];
typedef struct Packet { const char *text; int reads; } Packet;
static int window_calls;
#define WDW_TURNSTILE 1
#define WINDOW_GROWING 2
static const char *pktGetString(Packet *p) { ++p->reads; return p->text; }
static void window_setMode(int w,int m) { assert(w==1 && m==2); ++window_calls; }
'''
    code += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code += function(state,'static void fixed_string(')+accessor
    code += function(state,'static void turnstile_force_queue_state(')
    code += function(native,'void turnstileGame_handleForceQueue(')
    code += r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0; char before[128]; unsigned capacity;
 Packet packet={"Event \"quoted\"\n",0};
 if(mode!=1) {turnstileGame_handleForceQueue(&packet);assert(packet.reads==1 && window_calls==1);}
 if(mode==2) {packet.text="Replacement";turnstileGame_handleForceQueue(&packet);assert(packet.reads==2 && window_calls==2);}
 if(mode==3) sForceQueueEvent[0]=0; /* original UI consumes the deferred name */
 if(mode==4) {char long_name[128];memset(long_name,'x',127);long_name[127]=0;packet.text=long_name;turnstileGame_handleForceQueue(&packet);}
 if(mode==5) memset(sForceQueueEvent,'x',128); /* invalid retained storage rejects */
 if(mode==6) used=CAPACITY-1;
 memcpy(before,sForceQueueEvent,128);
 assert(armportReplayTurnstileForceQueue(&capacity)==sForceQueueEvent && capacity==128);
 turnstile_force_queue_state();
 assert(!memcmp(before,sForceQueueEvent,128));
 puts(buffer); return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); (root/'test.c').write_text(code)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(root/'test.c'),'-o',str(root/'test')],check=True)
        values={}
        for mode in range(7):
            r=subprocess.run([str(root/'test'),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if mode in (5,6) else 0),(mode,r.returncode,r.stderr)
            if r.returncode==0: values[mode]=json.loads(r.stdout)
        assert values=={0:'Event "quoted"\n',1:'',2:'Replacement',3:'',4:'x'*127},values
    print('force-queue receiver/accessor/writer: 7 ASan/UBSan cases pass; reads, UI call, replacement, local consumption, bounds and nonmutation. Host adapters do not qualify native ABI or arbitrary-length original packet input.')


if __name__=='__main__':
    main()
