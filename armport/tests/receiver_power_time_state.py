#!/usr/bin/env python3
"""Original power receive/accept block and raw-time observer, with dependency stubs."""
import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from receiver_tray_state import function


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    root = parser.parse_args().source
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    source = (root / 'Common/entity/character_net.c').read_text()
    start = source.index('                    const BasePower *ppowBase', source.index('for(j=0; j<iCntPows; j++)'))
    block = source[start:source.index('                    // Get all the boosts', start)]
    c = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <strings.h>
#define CLIENT 1
#define TEST_CLIENT 0
#define MAX_BUILD_NUM 8
#define CAPACITY (128*1024)
#define check(x) do{if(!(x))_Exit(3);}while(0)
#define min(a,b) ((a)<(b)?(a):(b))
#define stricmp strcasecmp
typedef struct Entity {int svr_idx;unsigned id;} Entity;
typedef struct Category {const char *pchName;} Category;
typedef struct BaseSet {Category *pcatParent;} BaseSet;
typedef struct BasePower {BaseSet *psetParent;char *pchFullName;int iMaxBoosts;} BasePower;
typedef struct Power {BasePower *ppowBase;int iUniqueID,iNumBoostsBought,iLevelBought,iNumCharges,bEnabled,bDisabledManually;float fRangeLast,fUsageTime,fAvailableTime;unsigned long ulCreationTime;} Power;
typedef struct PowerSet {BaseSet *psetBase;int iLevelBought;} PowerSet;
typedef struct Character {Entity *entParent;int iLevel;} Character;
typedef struct Packet {unsigned words[7];int at,ft;float floats[3];} Packet;
static unsigned pktGetBitsPack(Packet *p,int n){static const int want[]={5,3,24,0,0,0,4};assert(p->at<7&&want[p->at]==n);return p->words[p->at++];}
static unsigned pktGetBitsAuto(Packet *p){return pktGetBitsPack(p,0);}
static float pktGetF32(Packet *p){assert(p->ft<3);return p->floats[p->ft++];}
static int g_PowerDictionary;static struct {struct {int piFreeBoostSlotsOnPower;} aSchedules;} g_Schedules;
static int mode,base_calls,buy_calls,owns_calls,add_calls,final_calls,clock_calls;
static unsigned local_clock=123;
static BasePower base;static Power power;static PowerSet set;
static const BasePower *basepower_Receive(Packet *p,void *dictionary,Entity *e){++base_calls;return mode==3?NULL:&base;}
static PowerSet *character_BuyPowerSet(Character *p,BaseSet *b){++buy_calls;return mode==4?NULL:&set;}
static Power *character_OwnsPower(Character *p,const BasePower *b){++owns_calls;return mode==6||mode==7?&power:NULL;}
static Power *powerset_AddNewPower(PowerSet *s,const BasePower *b,int id,void *unused){++add_calls;if(mode==5)return NULL;++clock_calls;power.ulCreationTime=local_clock;power.iUniqueID=id;return &power;}
static int CountForLevel(int level,int schedule){return 2;}
static void power_LevelFinalize(Power *p){++final_calls;if(mode==10)p->ulCreationTime=local_clock;}
static int active;static char *buffer;static size_t used;
static int orientation[1],alignment_delays[1],desaturation;
static unsigned power_recharge_time_count;
static unsigned taskforce_time_count,reward_time_count;
'''
    c += re.search(r'^static struct \{ int entity_valid, svr_idx, build[^\n]+', state, re.M).group(0)
    c += '\nstatic unsigned power_creation_time_count;\n'
    c += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for name in ('void armportReplayStateInit(', 'void armportReplayPowerCreationTime(', 'static void power_creation_time_receives('):
        c += function(state, name)
    signature = '(Packet *pak,Character *pchar){int iBuild=7,i=2,j=3,iSetLevelBought=4;Power *ppow=NULL;\n'
    c += 'static void observed' + signature + block + '}\n'
    c += '#define armportReplayPowerCreationTime(...) ((void)0)\n'
    c += 'static void original' + signature + block + '}\n'
    c += '#undef armportReplayPowerCreationTime\n'
    c += r'''
int main(int argc,char **argv){
 mode=argc>1?atoi(argv[1]):0;char name[1025]="Cat.Set.Pow\"\n\377";
 Category cat={mode==7?"Temporary_Powers":"Normal"};BaseSet bs={&cat};
 Entity e={9,0xffffffffU};Character character={mode==11?NULL:&e,50};Character *pchar=mode==2?NULL:&character;
 base=(BasePower){&bs,name,3};set=(PowerSet){&bs,0};power=(Power){.ppowBase=&base,.iUniqueID=-17,.ulCreationTime=42};
 Packet p={{5,6,0xffffffffU,1,0,99,4},0,0,{1.5f,2.5f,3.5f}},saved_packet=p;
 if(mode==1)local_clock=987;
 if(mode==9)p.words[2]=0,saved_packet=p;
 if(mode==12){memset(name,'X',1023);name[1023]=0;}
 if(mode==13){memset(name,'X',1024);name[1024]=0;}
 Power before=power;PowerSet before_set=set;
 original(&p,pchar);Power expected_power=power;PowerSet expected_set=set;
 int calls[]={base_calls,buy_calls,owns_calls,add_calls,final_calls,clock_calls};
 base_calls=buy_calls=owns_calls=add_calls=final_calls=clock_calls=0;
 power=before;set=before_set;p=saved_packet;
 power_creation_time_count=77;armportReplayStateInit();assert(power_creation_time_count==0);
 if(mode==8)active=0;
 observed(&p,pchar);
 assert(p.at==7&&p.ft==3);
 assert(!memcmp(&power,&expected_power,sizeof(power))&&!memcmp(&set,&expected_set,sizeof(set)));
 int after[]={base_calls,buy_calls,owns_calls,add_calls,final_calls,clock_calls};assert(!memcmp(calls,after,sizeof(calls)));
 if(mode==14)name[0]='Z';
 if(mode==15){power_creation_time_count=8192;armportReplayPowerCreationTime(&e,0,0,0,0,0,name,1);}
 if(mode==16){power_creation_time_count=8193;power_creation_time_receives();}
 if(mode==17)armportReplayPowerCreationTime(&e,-1,0,0,0,0,name,1);
 if(mode==18)armportReplayPowerCreationTime(&e,8,0,0,0,0,name,1);
 if(mode==19)armportReplayPowerCreationTime(&e,0,-1,0,0,0,name,1);
 if(mode==20)armportReplayPowerCreationTime(&e,0,0,-1,0,0,name,1);
 if(mode==21)armportReplayPowerCreationTime(&e,0,0,0,0,0,NULL,1);
 if(mode==22)used=CAPACITY-1;
 if(mode==23){power_creation_time_count=8191;armportReplayPowerCreationTime(NULL,7,2147483647,2147483647,-1,-2,name,0x80000000U);assert(power_creation_time_count==8192&&power_creation_times[8191].seconds==0x80000000U);power_creation_time_count=1;}
 if(mode==24){active=0;armportReplayPowerCreationTime(NULL,-1,-1,-1,0,0,NULL,0);active=1;}
 if(mode==25){e.id=17;e.svr_idx=10;armportReplayPowerCreationTime(&e,0,0,1,19,18,"Second",0x80000000U);}
 unsigned count=power_creation_time_count;unsigned char *saved=malloc(sizeof(power_creation_times));memcpy(saved,power_creation_times,sizeof(power_creation_times));
 power_creation_time_receives();assert(count==power_creation_time_count&&!memcmp(saved,power_creation_times,sizeof(power_creation_times)));
 puts(buffer);free(saved);free(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp); source_file = path / 'fixture.c'; exe = path / 'fixture'
        source_file.write_text(c)
        cc = os.environ.get('CC', 'cc')
        subprocess.run([cc, '-std=c99', '-O1', '-g', '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', str(source_file), '-o', str(exe)], check=True)
        for mode in range(26):
            result = subprocess.run([str(exe), str(mode)], capture_output=True, text=True, timeout=15)
            assert result.returncode == (3 if mode == 13 or 15 <= mode <= 22 else 0), (mode, result.returncode, result.stderr)
            if result.returncode:
                continue
            expected = [dict(entity_valid=1, svr_idx=9, entity_id=0xffffffff, build=7, set_ordinal=2, power_ordinal=3, received_unique_id=99, retained_unique_id=-17 if mode == 6 else 99, received_seconds=0 if mode == 9 else 0xffffffff, name='Cat.Set.Pow"\n\xff')]
            if mode in (2, 3, 4, 5, 8):
                expected = []
            if mode == 11:
                expected[0].update(entity_valid=0, svr_idx=0, entity_id=0)
            if mode == 12:
                expected[0]['name'] = 'X' * 1023
            if mode == 25:
                expected.append(dict(entity_valid=1, svr_idx=10, entity_id=17, build=0, set_ordinal=0, power_ordinal=1, received_unique_id=19, retained_unique_id=18, received_seconds=0x80000000, name='Second'))
            assert json.loads(result.stdout) == expected, (mode, result.stdout, expected)
        source_file.write_text('#include "' + str(root / 'Game/src/clientcomm/armport_replay.h') + '"\nint main(void){int x=0;armportReplayPowerCreationTime(x++,x++,x++,x++,x++,x++,x++,x++);return x;}\n')
        subprocess.run([cc, str(source_file), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print('power creation times: 26 ASan/UBSan cases and disabled-header inertness passed; actual receive/accept block, original-vs-observed reads/calls/storage equality, failed acceptance, existing/temp powers, copied names, nullable parent, U32 extremes, local-clock exclusion, bounds/reset/nonmutation; dependency stubs do not qualify native ABI or full lifetime state')


if __name__ == '__main__':
    main()
