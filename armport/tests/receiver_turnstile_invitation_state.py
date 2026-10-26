#!/usr/bin/env python3
"""Exercise the original invitation receiver, callbacks and retained ID writer."""
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
    source = parser.parse_args().source
    native = (source / 'Game/src/UI/uiTurnstile.c').read_text()
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    accessor = function(native, 'void armportReplayTurnstileInvitation(')
    assert '#ifdef COH_ARMPORT_REPLAY\n' + accessor in native
    code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>
#define CAPACITY 4096
#define check(x) do { if (!(x)) _Exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
static int ts_inviter_db_id, ts_inviter_mission_id;
typedef struct Packet { const char *strings[2]; uint32_t values[2]; int reads; } Packet;
static const char *pktGetString(Packet *p) { assert(p->reads<2); return p->strings[p->reads++]; }
static uint32_t pktGetBitsAuto(Packet *p) { assert(p->reads>=2 && p->reads<4); return p->values[p->reads++ - 2]; }
static char *copy_string(const char *s) { size_t n=strlen(s)+1; char *r=malloc(n); assert(r); memcpy(r,s,n); return r; }
#define strdup copy_string
static void estrConcatf(char **s,const char *format,const char *name) {
 assert(!*s && !strcmp(format,"LFG_Mission_%s"));
 *s=malloc(strlen(name)+13); assert(*s); sprintf(*s,format,name);
}
static void estrDestroy(char **s) { free(*s); *s=NULL; }
static int translations,dialogs,commands;
static const char *textStd(const char *key,...) { ++translations; return key; }
static void (*accept_callback)(void *),(*decline_callback)(void *);
#define DIALOG_YES_NO 1
static void dialogStd(int kind,const char *text,void *a,void *b,void (*yes)(void *),void (*no)(void *),int flag) {
 assert(kind==1 && !strcmp(text,"IncarnateTrialJoinLeader") && !a && !b && flag==1);
 ++dialogs; accept_callback=yes; decline_callback=no;
}
static char command[128];
static void cmdParse(const char *s) { assert(strlen(s)<sizeof(command)); strcpy(command,s); ++commands; }
'''
    code += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code += accessor + function(state, 'static void turnstile_invitation_state(')
    for name in ('static void sendJoinLeaderAccept(', 'static void sendJoinLeaderDecline(',
                 'void turnstileGame_handleJoinLeader('):
        code += function(native, name)
    code += r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0, db_before,mission_before,db_after,mission_after;
 Packet packet={{"Leader","Trial"},{123,456},0};
 if(mode==3) packet.values[0]=1,packet.values[1]=31;
 if(mode==4) packet.values[0]=0x80000000U,packet.values[1]=0xffffffffU;
 if(mode==5) packet.values[0]=INT_MAX,packet.values[1]=0;
 if(mode==6) packet.strings[0]="",packet.strings[1]="";
 if(mode!=1) {
  turnstileGame_handleJoinLeader(&packet);
  assert(packet.reads==4 && dialogs==1 && translations==2 && commands==0);
  assert(accept_callback==sendJoinLeaderAccept && decline_callback==sendJoinLeaderDecline);
 }
 if(mode==2) {
  Packet replacement={{"Other","Other Trial"},{987,654},0};
  turnstileGame_handleJoinLeader(&replacement);
  assert(replacement.reads==4 && dialogs==2 && translations==4 && commands==0);
 }
 armportReplayTurnstileInvitation(&db_before,&mission_before);
 if(mode==7 || mode==8) {
  char expected[128];
  sprintf(expected,"turnstile_invite_player_accept %i %i %i",db_before,mode==7,mission_before);
  (mode==7?accept_callback:decline_callback)(NULL);
  assert(commands==1 && !strcmp(command,expected));
 }
 if(mode==9) used=CAPACITY-1;
 turnstile_invitation_state();
 armportReplayTurnstileInvitation(&db_after,&mission_after);
 assert(db_before==db_after && mission_before==mission_after);
 assert(commands==((mode==7 || mode==8)?1:0));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'test.c').write_text(code)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                        '-fno-omit-frame-pointer', str(root / 'test.c'),
                        '-o', str(root / 'test')], check=True)
        values = {}
        for mode in range(10):
            result = subprocess.run([str(root / 'test'), str(mode)],
                                    capture_output=True, text=True, timeout=15)
            assert result.returncode == (3 if mode == 9 else 0), (mode, result.returncode, result.stderr)
            if result.returncode == 0:
                values[mode] = json.loads(result.stdout)
        baseline = dict(db_id=123, mission_id=456)
        assert values == {0: baseline, 1: dict(db_id=0, mission_id=0),
                          2: dict(db_id=987, mission_id=654),
                          3: dict(db_id=1, mission_id=31),
                          4: dict(db_id=-2147483648, mission_id=-1),
                          5: dict(db_id=2147483647, mission_id=0),
                          6: baseline, 7: baseline, 8: baseline}, values
    print('turnstile invitation: 10 ASan/UBSan cases pass; original ordered reads, dialog callbacks, accept/decline commands, retained IDs after responses, replacement, signed extremes, literal 1/31 IDs, output bounds and nonmutation. Host substitutes do not qualify native ABI or live dialog lifecycle.')


if __name__ == '__main__':
    main()
