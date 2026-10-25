#!/usr/bin/env python3
"""Exercise actual tray const views, mode receiver and retained-state writers."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def function(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    level = 1
    pos = opening + 1
    while level:
        level += (text[pos] == '{') - (text[pos] == '}')
        pos += 1
    return text[start:pos] + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    header = (args.source / 'Common/gameComm/trayCommon.h').read_text()
    native = (args.source / 'Common/gameComm/trayCommon.c').read_text()
    ui = (args.source / 'Game/src/UI/uiTray.c').read_text()
    net = (args.source / 'Game/src/UI/uiNet.c').read_text()
    enums = header[header.index('typedef enum\n'):header.index('CurTrayMask curtraytype_to_altmask')]
    item = header[header.index('typedef enum TrayItemType'):header.index('InventoryType InventoryType_FromTrayItemType')]
    structs = header[header.index('#define IS_TRAY_MACRO'):header.index('typedef struct Packet Packet;', header.index('typedef struct Tray\n'))]
    internals = native[native.index('typedef struct TrayInternals'):native.index('} TrayInternals;') + len('} TrayInternals;')]
    accessor = function(native, 'const TrayObj *const *armportReplayTraySlots(')
    assert '#ifdef COH_ARMPORT_REPLAY\n' + accessor.rstrip() in native
    assert '#ifdef COH_ARMPORT_REPLAY\n' + function(ui, 'int armportReplayTrayStickyMask(').rstrip() in ui
    fixture = r"""
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define CAPACITY (256*1024)
#define check(x) do { if (!(x)) _Exit(3); } while(0)
#define INRANGE(x,lo,hi) ((x)>=(lo)&&(x)<(hi))
typedef float F32;
typedef struct AtlasTex AtlasTex;
typedef struct Boost Boost;
typedef struct uiTab uiTab;
typedef struct BasePower { const char *pchFullName; } BasePower;
typedef struct PowerSet { int idx; } PowerSet;
typedef struct Power { int idx, iUniqueID; PowerSet *psetParent; const BasePower *ppowBase, *ppowOriginal; } Power;
static char buffer[CAPACITY]; static size_t used;
""" + enums + item + structs + internals + r"""
static int s_TrayStickyMask, s_TrayMomentaryMask;
static int forced_count=-1;
static TrayObj *player_slots[720], *server_slots[10];
static int fixture_size(const void *array) {
 if (!array) return 0;
 if (forced_count>=0) return forced_count;
 if (array==player_slots) return 720;
 if (array==server_slots) return 10;
 abort();
}
#define eaSize(p) fixture_size(*(p))
typedef struct Packet { int bits[2], cursor; } Packet;
static unsigned pktGetBits(Packet *p,int n) { assert(n==1 && p->cursor<2); return p->bits[p->cursor++]; }
"""
    fixture += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for name in ['static void fixed_string(', 'static void base_power(', 'static void tray_slots_state(', 'static void player_tray_state(', 'static void default_power_state(']:
        if 'tray_slots' in name:
            fixture += accessor
        fixture += function(state, name)
    fixture += function(ui, 'int armportReplayTrayStickyMask(')
    fixture += function(ui, 'void tray_setMode(') + function(net, 'void receiveTrayMode(')
    fixture += r"""
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,i;
 TrayObj objs[4]={{0}}, saved[4];
 TrayInternals internals={player_slots,server_slots}, old_internals;
 Tray tray={{0,8,4,7},1,0,(int)0x89abcdefU,&internals}, old_tray;
 BasePower base={"Cat.Set.Power"}; PowerSet set={7}; Power power={9,-42,&set,&base,NULL};
 Packet packet={{mode&1,(mode>>1)&1},0};
 receiveTrayMode(&packet); assert(packet.cursor==2);
 assert(armportReplayTrayStickyMask()==(((mode&3)<<1)|1));
 assert(!armportReplayTraySlots(NULL,0) && !armportReplayTraySlots(&tray,-1) && !armportReplayTraySlots(&tray,2));
 objs[0].type=kTrayItemType_Power; objs[0].iset=3; objs[0].ipow=8; objs[0].autoPower=1;
 objs[0].pchPowerName="Power";objs[0].pchPowerSetName="Set";objs[0].pchCategory="Cat";
 objs[1].type=kTrayItemType_Inspiration;objs[1].iset=4;objs[1].ipow=2;
 objs[2].type=kTrayItemType_Macro;strcpy(objs[2].command,"say \"hello\"\n");strcpy(objs[2].shortName,"macro");strcpy(objs[2].iconName,"icon");
 objs[3].type=kTrayItemType_MacroHideName;strcpy(objs[3].command,"powexec_name test");
 player_slots[0]=&objs[0];player_slots[89]=&objs[1];player_slots[719]=&objs[2];server_slots[9]=&objs[3];
 if(mode==4) tray.internals=NULL;
 if(mode==5) internals.slot=NULL;
 if(mode==6) internals.serverSlot=NULL;
 if(mode==7) forced_count=8193;
 if(mode==8) used=CAPACITY-1;
 if(mode==9) memset(objs[2].command,'x',sizeof(objs[2].command));
 if(mode==10) power.psetParent=NULL,power.ppowBase=NULL,power.ppowOriginal=&base;
 if(mode==11) objs[0].pchPowerName=NULL,objs[0].autoPower=0;
 if(mode==12) {for(i=0;i<4;++i) {objs[i].icat=99;objs[i].itray=100;objs[i].islot=101;objs[i].scale=123;objs[i].state=33;objs[i].icon=(AtlasTex*)&tray;} s_TrayMomentaryMask=127;}
 if(mode==13) {player_slots[0]=NULL;player_slots[1]=&objs[0];}
 if(mode==14) memset(objs[2].shortName,'x',sizeof(objs[2].shortName));
 if(mode==15) memset(objs[2].iconName,'x',sizeof(objs[2].iconName));
 if(mode==16) objs[3].type=kTrayItemType_BodyItem;
 memcpy(saved,objs,sizeof(saved));old_tray=tray;old_internals=internals;
 out("{\"tray\":");player_tray_state(mode==17?NULL:&tray);
 out(",\"default\":");default_power_state(mode==18?NULL:&power);
 out(",\"sticky\":%d}",armportReplayTrayStickyMask());
 assert(!memcmp(saved,objs,sizeof(saved)) && !memcmp(&old_tray,&tray,sizeof(tray)) && !memcmp(&old_internals,&internals,sizeof(internals)));
 puts(buffer);return 0;
}
"""
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary)
        (path / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'fixture.c'),'-o',str(path/'fixture')],check=True)
        results = [subprocess.run([str(path/'fixture'),str(i)],capture_output=True,text=True,timeout=15) for i in range(19)]
        values = {}
        for i, result in enumerate(results):
            assert result.returncode == (3 if i in (7,8,9,14,15) else 0), (i,result.returncode,result.stderr)
            if result.returncode == 0:
                values[i] = json.loads(result.stdout)
        baseline = values[0]
        tray = baseline['tray']
        assert tray['current']==[0,8,4,7] and tray['indexes']==0x89abcdef
        assert len(tray['player_slots'])==720 and len(tray['server_slots'])==10
        assert sum(x is not None for x in tray['player_slots'])==3
        assert tray['player_slots'][0]==dict(type=1,set=3,power=8,auto=1,power_name='Power',set_name='Set',category='Cat')
        assert tray['player_slots'][89]==dict(type=2,set=4,power=2)
        assert tray['player_slots'][719]['short_name']=='macro' and tray['server_slots'][9]['type']==17
        for i in (1,2,3,12):
            assert values[i]['tray']==tray and values[i]['default']==baseline['default']
            assert values[i]['sticky']==((i&3)<<1)|1
        assert values[4]['tray']['has_storage'] is False and values[4]['tray']['player_slots']==[]
        assert values[5]['tray']['player_slots']==[] and values[5]['tray']['server_slots']==tray['server_slots']
        assert values[6]['tray']['server_slots']==[] and values[6]['tray']['player_slots']==tray['player_slots']
        assert baseline['default']==dict(index=9,unique_id=-42,set_index=7,base='Cat.Set.Power',original=None)
        assert values[10]['default']==dict(index=9,unique_id=-42,set_index=None,base=None,original='Cat.Set.Power')
        assert values[11]['tray']['player_slots'][0]['power_name'] is None
        assert values[13]['tray']['player_slots'][0] is None and values[13]['tray']['player_slots'][1]==tray['player_slots'][0]
        assert values[16]['tray']['server_slots'][9]==dict(type=3)
        assert values[17]['tray'] is None and values[18]['default'] is None
    print('tray original mode receiver/actual const views/writers: 19 cases pass; separate player/server slots, all builds and null slots, power/inspiration/macro fields, default-power identity/nulls, four sticky modes, source immutability, cache exclusion, bounded counts/strings/output; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
