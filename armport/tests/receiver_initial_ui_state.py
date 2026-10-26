#!/usr/bin/env python3
"""Check original initial UI receivers and actual read-only snapshot helpers."""
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
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    header = (source / 'Common/gameComm/wdwbase.h').read_text()
    structs = header[header.index('typedef enum WindowName'):header.index('extern Wdw winDefs')]
    net = (source / 'Game/src/UI/uiNet.c').read_text()
    window = (source / 'Common/gameComm/wdwbase.c').read_text()
    group = (source / 'Game/src/UI/uiGroupWindow.c').read_text()
    inspiration = (source / 'Game/src/UI/uiInspiration.c').read_text()
    initial = (source / 'Game/src/entity/entrecv.c').read_text()
    begin = initial.index('        game_state.enableBoostDiminishing =')
    server_reads = initial[begin:initial.index('    STOP_BIT_COUNT(pak);', begin)]
    begin = initial.index('    control_state.first = pktGetBits(')
    control_reads = initial[begin:initial.index('\n\n', begin)]
    globals_header = (source / 'Game/src/UI/uiListView.h').read_text()
    globals_start = globals_header.index('extern int gDivSuperName;')
    dividers = globals_header[globals_start:globals_header.index('extern int gDivLfgMap;', globals_start) + len('extern int gDivLfgMap;')].replace('extern ', '')
    fixture = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (256*1024)
#define check(x) do { if (!(x)) _Exit(3); } while(0)
#define TRUE 1
#define FALSE 0
#define C_DECLARATIONS_BEGIN
#define C_DECLARATIONS_END
#define ICON_WD 40
typedef struct CBox { float lx,ly,hx,hy; } CBox;
''' + structs + dividers + r'''
static Wdw winDefs[MAX_CUSTOM_WINDOW_COUNT+MAX_WINDOW_COUNT];
static int gWindowRGBA[4]={1,2,3,255},gShowBuffs,trayState;
static struct { int enableBoostDiminishing,enablePowerDiminishing,no_base_edit,beta_base,base_raid,unobserved; } game_state;
static struct { int first,nocoll,unobserved; } control_state;
static struct Character { int iNumInspirationRows,iNumInspirationCols; } character={5,3};
static struct Entity { struct Character *pchar; } entity={&character};
static struct Entity *playerPtr(void) { return &entity; }
static int dimension_calls;
static void window_setDims(int window,int x,int y,int w,int h) {
 assert(window==WDW_INSPIRATION && x==-1 && y==-1 && w==-1);
 winDefs[window].loc.ht=h;++dimension_calls;
}
static int divider_saves;
static void setSavedDividerSettings(void) { ++divider_saves; }
typedef struct Packet { unsigned values[32];int count,cursor,float_reads;unsigned float_bits; } Packet;
static unsigned pktGetBitsPack(Packet *pak,int n) {assert(n==1||n==2||n==9);assert(pak->cursor<pak->count);return pak->values[pak->cursor++];}
static unsigned pktGetBits(Packet *pak,int n) {assert(n==1||n==2||n==32);assert(pak->cursor<pak->count);return pak->values[pak->cursor++];}
static float pktGetIfSetF32(Packet *pak) {float f;++pak->float_reads;memcpy(&f,&pak->float_bits,4);return f;}
static char buffer[CAPACITY];static size_t used;
'''
    fixture += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for text, signature in [
        (group, 'int armportReplayTeamBuffMode('),
        (inspiration, 'int armportReplayInspirationMode('),
        (group, 'void setTeamBuffMode('),
        (inspiration, 'void inspiration_setMode('),
        (net, 'void receiveTeamBuffMode('),
        (net, 'void receiveInspirationMode('),
        (net, 'void receiveDividers('),
        (net, 'void receiveDockMode('),
        (window, 'void receiveWindow('),
        (state, 'static void initial_ui_state('),
        (state, 'static void initial_server_state('),
    ]:
        fixture += function(text, signature)
    fixture += 'static void receive_server_flags(Packet *pak) {\n' + server_reads + control_reads + '\n}\n'
    fixture += r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,i; Wdw saved[MAX_WINDOW_COUNT];
 Packet flags={{1,2,3,4,5,1,3},7,0,0,0};
 Packet dividers={{10,20,30,40,50,60,70,80},8,0,0,0};
 Packet buffs={{1},1,0,0,0},insp={{1},1,0,0,0},dock={{0xffffffffU},1,0,0,0};
 Packet w={{123,456,2,1,0xffffffffU,0x80000000U,1,1,300,400},10,0,0,0x3f000000U};
 if(mode==1) dividers.values[0]=0;
 if(mode==2) {w.values[7]=0;w.count=8;w.float_bits=0;}
 if(mode==3) w.float_bits=0x7fc01234U;
 if(mode==4) buffs.values[0]=0,insp.values[0]=0;
 if(mode==5) dividers.values[7]=0xffffffffU;
 receive_server_flags(&flags);assert(flags.cursor==7);
 receiveDividers(&dividers);assert(dividers.cursor==8 && divider_saves==(mode!=1));
 receiveTeamBuffMode(&buffs);receiveInspirationMode(&insp);receiveDockMode(&dock);
 assert(buffs.cursor==1 && insp.cursor==1 && dock.cursor==1 && dimension_calls==(mode!=4));
 receiveWindow(&w,&winDefs[MAX_WINDOW_COUNT-1].loc);
 assert(w.cursor==w.count && w.float_reads==1);
 if(mode==6) { winDefs[0].timer=123;winDefs[0].fadeTimer=456;winDefs[0].loc_minimized.xp=9;winDefs[0].icon="unused";game_state.unobserved=8;control_state.unobserved=9; }
 if(mode==7) winDefs[MAX_WINDOW_COUNT-1].below=1;
 if(mode==8) winDefs[0].loc.start_shrunk=1;
 if(mode==9) control_state.nocoll=2;
 if(mode==10) game_state.beta_base=-17;
 if(mode==11) used=CAPACITY-1;
 memcpy(saved,winDefs,sizeof(saved));
 out("{\"ui\":");initial_ui_state();out(",\"server\":");initial_server_state();out("}");
 assert(!memcmp(saved,winDefs,sizeof(saved)) && divider_saves==(mode!=1) && dimension_calls==(mode!=4));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary)
        (path / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(path/'fixture.c'), '-o', str(path/'fixture')], check=True)
        values = {}
        for i in range(12):
            result = subprocess.run([str(path/'fixture'), str(i)], capture_output=True, text=True, timeout=15)
            assert result.returncode == (3 if i == 11 else 0), (i, result.returncode, result.stderr)
            if result.returncode == 0:
                values[i] = json.loads(result.stdout)
        baseline = values[0]
        ui = baseline['ui']
        assert ui['team_buffs'] == 1 and ui['inspiration_mode'] == 1
        assert ui['dividers'] == list(range(10,81,10)) and ui['window_rgba'] == [1,2,3,255]
        assert ui['windows'][-1] == dict(index=len(ui['windows'])-1, x=123, y=456, width=300, height=400, draggable=1, locked=1, start_shrunk=0, color=0xffffffff, back_color=0x80000000, scale_f32_bits=[0x3f000000], maximized=1, mode=2, below=0)
        assert sum(window['height']==220 for window in ui['windows']) == 1
        assert baseline['server'] == dict(boost_diminishing=1, power_diminishing=2, no_base_edit=3, beta_base=4, base_raid=5, first_person=1, nocoll=3)
        assert values[1]['ui']['dividers'] == [0]*8
        assert values[2]['ui']['windows'][-1]['scale_f32_bits'] == [0x3f800000]
        assert values[2]['ui']['windows'][-1]['width'] == 0
        assert values[3]['ui']['windows'][-1]['scale_f32_bits'] == [0x7fc01234]
        assert values[4]['ui']['team_buffs']==0 and values[4]['ui']['inspiration_mode']==0
        assert values[5]['ui']['dividers'][-1] == -1
        assert values[6] == baseline
        assert values[7]['ui']['windows'][-1]['below'] == 1
        assert values[8]['ui']['windows'][0]['start_shrunk'] == 1
        assert values[9]['server']['nocoll'] == 2 and values[10]['server']['beta_base'] == -17
    print('initial UI/server original receiver fragments and actual snapshot: 12 cases pass; window fields/default scale/NaN, retained dividers and zero gate, team/inspiration modes and original dimension call, literal server/control flags, unsigned colors, local-cache exclusion, source immutability and bounded output; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
