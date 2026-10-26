#!/usr/bin/env python3
"""Actual mode receiver, active-reference helpers and read-only state writers."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from receiver_tray_state import function


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    root = parser.parse_args().source
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    receive = (root / 'Common/entity/PowerInfo.c').read_text()
    c = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
#define CAPACITY 65536
#define check(x) do{if(!(x))_Exit(3);}while(0)
typedef struct PowerRef {int buildNum,powerSet,power;} PowerRef;
typedef struct PowerInfo {PowerRef **activePowers;void *rechargeTimers;} PowerInfo;
typedef struct Character {int *pPowerModes;} Character;
typedef struct Entity {Character *pchar;} Entity;
typedef struct Packet {int values[8],at;} Packet;
static int pktGetBits(Packet *p,int n){assert(n==1);return p->values[p->at++];}
static int pktGetBitsPack(Packet *p,int n){assert(n==3);return p->values[p->at++];}
static int mode_count,active_count,reset_calls,push_calls,alloc_calls,free_calls;
static int mode_values[1025];static PowerRef *active_values[4097],pool[4];
static int eaiSize(int *const *a){return mode_count;}
static void eaiSetSize(int **a,int n){assert(n==0);mode_count=0;++reset_calls;}
static void eaiPush(int **a,int v){assert(mode_count<1025);*a=mode_values;(*a)[mode_count++]=v;++push_calls;}
static int eaSize(const void *a){return active_count;}
static PowerRef *eaGet(PowerRef ***a,int i){assert(i>=0&&i<active_count);return (*a)[i];}
static void eaPush(PowerRef ***a,PowerRef *v){assert(active_count<4097);*a=active_values;(*a)[active_count++]=v;}
static PowerRef *eaRemove(PowerRef ***a,int i){PowerRef *v=(*a)[i];memmove(*a+i,*a+i+1,(--active_count-i)*sizeof(**a));return v;}
static PowerRef *powerRef_Create(void){assert(alloc_calls<4);return &pool[alloc_calls++];}
static void powerRef_Destroy(PowerRef *p){++free_calls;}
static char buffer[CAPACITY];static size_t used;
'''
    c += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for name in ('PowerRef* powerInfo_FindPower(', 'int powerInfo_FindPowerIndex(', 'void powerInfo_ChangeActiveState(', 'void entity_ReceivePowerModeUpdate('):
        c += function(receive, name)
    for name in ('static void power_modes(', 'static void power_activity('):
        c += function(state, name)
    c += r'''
int main(int argc,char **argv){
 int mode=argc>1?atoi(argv[1]):0;
 Character character={mode_values};Entity entity={&character};PowerInfo info={active_values,(void *)(uintptr_t)1};
 Packet p={{1,4,3,-1,2147483647,3},0};PowerRef a={7,2,9},b={0,1,4},absent={1,1,1};
 mode_count=2;mode_values[0]=91;mode_values[1]=92;
 if(mode==1)p.values[0]=0;
 if(mode==2)p.values[1]=0;
 entity_ReceivePowerModeUpdate(&entity,&p);
 assert(p.at==(mode==1?1:mode==2?2:6));
 assert(reset_calls==(mode==1?0:1)&&push_calls==(mode==1||mode==2?0:4));
 powerInfo_ChangeActiveState(&info,a,1);powerInfo_ChangeActiveState(&info,b,1);
 powerInfo_ChangeActiveState(&info,a,1);assert(active_count==2&&alloc_calls==2);
 powerInfo_ChangeActiveState(&info,absent,0);assert(active_count==2&&free_calls==0);
 if(mode==3){powerInfo_ChangeActiveState(&info,a,0);assert(active_count==1&&free_calls==1);}
 if(mode==4){powerInfo_ChangeActiveState(&info,a,0);powerInfo_ChangeActiveState(&info,b,0);assert(active_count==0&&free_calls==2);}
 if(mode==5)info.activePowers[0]=NULL;
 if(mode==6){pool[0]=(PowerRef){-1,-2147483647-1,2147483647};}
 if(mode==7){PowerRef *tmp=info.activePowers[0];info.activePowers[0]=info.activePowers[1];info.activePowers[1]=tmp;}
 if(mode==8)info.rechargeTimers=NULL;
 if(mode==9)mode_count=-1;
 if(mode==10)mode_count=1025;
 if(mode==11)character.pPowerModes=NULL;
 if(mode==12)active_count=-1;
 if(mode==13)active_count=4097;
 if(mode==14)info.activePowers=NULL;
 if(mode==15)used=CAPACITY-1;
 if(mode==17){mode_count=0;character.pPowerModes=NULL;active_count=0;info.activePowers=NULL;}
 if(mode==18){mode_count=1024;for(int i=0;i<1024;i++)mode_values[i]=i;active_count=4096;for(int i=0;i<4096;i++)active_values[i]=NULL;}
 int saved_modes[1025];PowerRef *saved_refs[4097];PowerRef saved_pool[4];
 memcpy(saved_modes,mode_values,sizeof(saved_modes));memcpy(saved_refs,active_values,sizeof(saved_refs));memcpy(saved_pool,pool,sizeof(saved_pool));
 int saved_mode_count=mode_count,saved_active_count=active_count;Character saved_char=character;PowerInfo saved_info=info;
 out("{\"modes\":");power_modes(&character);out(",\"activity\":");power_activity(mode==16?NULL:&info);out("}");
 assert(mode_count==saved_mode_count&&active_count==saved_active_count);
 assert(!memcmp(saved_modes,mode_values,sizeof(saved_modes))&&!memcmp(saved_refs,active_values,sizeof(saved_refs))&&!memcmp(saved_pool,pool,sizeof(saved_pool)));
 assert(!memcmp(&character,&saved_char,sizeof(character))&&!memcmp(&info,&saved_info,sizeof(info)));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp); source = path / 'fixture.c'; exe = path / 'fixture'
        source.write_text(c)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g', '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', str(source), '-o', str(exe)], check=True)
        for mode in range(19):
            result = subprocess.run([str(exe), str(mode)], capture_output=True, text=True, timeout=15)
            assert result.returncode == (3 if 9 <= mode <= 15 else 0), (mode, result.returncode, result.stderr)
            if result.returncode:
                continue
            modes = [3, -1, 2147483647, 3]
            refs = [dict(build=7, set=2, power=9), dict(build=0, set=1, power=4)]
            if mode == 1:
                modes = [91, 92]
            if mode in (2, 17):
                modes = []
            if mode == 3:
                refs = refs[1:]
            if mode in (4, 17):
                refs = []
            if mode == 5:
                refs[0] = None
            if mode == 6:
                refs[0] = dict(build=-1, set=-2147483648, power=2147483647)
            if mode == 7:
                refs.reverse()
            if mode == 18:
                modes = list(range(1024)); refs = [None] * 4096
            assert json.loads(result.stdout) == dict(modes=modes, activity=None if mode == 16 else dict(active_refs=refs)), (mode, result.stdout)
    print('power activity: 19 ASan/UBSan cases pass; actual mode receiver, duplicate/add/remove/absent active helpers, ordered signed modes and refs/nulls, null info, count/storage/output bounds, maximum bounds, nonmutation and inaccessible recharge-array exclusion; packet/earray/allocation dependencies substituted, not native ABI or complete activation/recharge state')


if __name__ == '__main__':
    main()
