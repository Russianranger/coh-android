#!/usr/bin/env python3
"""Actual power-update timestamp assignment and recharge receive loop controls."""
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
    source = (root / 'Common/entity/PowerInfo.c').read_text()
    net = (root / 'Common/entity/character_net.c').read_text()
    start = source.index('        int timerCount;', source.index('void entity_ReceivePowerInfoUpdate'))
    timers = source[source.rfind('    {', 0, start):source.index('\n    {\n        int iCnt;', start)]
    start = source.index('                if(ppow!=NULL)', source.index('// If ppow is NULL, then something bad is happening.'))
    accepted = source[start:source.index('                for(j=0; j<iCntBoosts; j++)', start)]
    c = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
#define CLIENT 1
#define TEST_CLIENT 0
#define CAPACITY 65536
#define check(x) do{if(!(x))_Exit(3);}while(0)
#define min(a,b) ((a)<(b)?(a):(b))
typedef struct PowerRef {int buildNum,powerSet,power;} PowerRef;
typedef struct PowerRechargeTimer {PowerRef ppowRef;float rechargeCountdown;} PowerRechargeTimer;
typedef struct PowerInfo {PowerRechargeTimer **rechargeTimers;} PowerInfo;
typedef struct BasePower {int iMaxBoosts;const char *pchFullName;} BasePower;
typedef struct Power {BasePower *ppowBase;void **ppBoosts;int iUniqueID,iLevelBought,iNumCharges,bEnabled,bDisabledManually,iNumBoostsBought;float fUsageTime,fAvailableTime;unsigned ulCreationTime;} Power;
typedef struct Character {int iLevel;} Character;
typedef struct Entity {int svr_idx;unsigned id;PowerInfo *powerInfo;Character *pchar;} Entity;
typedef struct Packet {unsigned values[10],floats[2];int at,ft,kind[10];} Packet;
static unsigned pktGetBitsPack(Packet *p,int n){assert(p->at<10);p->kind[p->at]=n;return p->values[p->at++];}
static unsigned pktGetBitsAuto(Packet *p){return pktGetBitsPack(p,0);}
static unsigned pktGetBits(Packet *p,int n){assert(n==1);return pktGetBitsPack(p,-1);}
static float pktGetF32(Packet *p){float f;assert(p->ft<2);memcpy(&f,&p->floats[p->ft++],4);return f;}
static PowerRechargeTimer pool[2],*items[2];static int alloc_calls,push_calls,count;
static PowerRechargeTimer *powerInfo_PowerGetRechargeTimer(PowerInfo *info,PowerRef ref){for(int i=0;i<count;i++)if(!memcmp(&items[i]->ppowRef,&ref,sizeof(ref)))return items[i];return NULL;}
static PowerRechargeTimer *powerRechargeTimer_Create(void){assert(alloc_calls<2);return &pool[alloc_calls++];}
static void eaPush(PowerRechargeTimer ***a,PowerRechargeTimer *v){assert(count<2);*a=items;items[count++]=v;++push_calls;}
static int active;static char *buffer;static size_t used;
static int orientation[1],alignment_delays[1],desaturation;
static unsigned taskforce_time_count,reward_time_count,power_creation_time_count;
static struct {struct {int piFreeBoostSlotsOnPower;}aSchedules;}g_Schedules;
static int destroy_calls,size_calls,creation_calls;
static int CountForLevel(int level,int schedule){assert(level==45);return 2;}
static void power_DestroyAllBoosts(Power *p,void *unused){++destroy_calls;}
static void eaSetSize(void ***p,int n){assert(n==4);++size_calls;}
static void armportReplayPowerCreationTime(const Entity *e,int build,int set,int power,int received,int retained,const char *name,unsigned seconds){++creation_calls;assert(e&&build==7&&set==2&&power==9&&received==99&&retained==-17&&strcmp(name,"Power.Name")==0&&seconds==0xffffffffU);}
'''
    c += re.search(r'^static struct \{ int svr_idx, build, set, power;[^\n]+', state, re.M).group(0) + '\nstatic unsigned power_recharge_time_count;\n'
    c += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for name in ('void armportReplayStateInit(', 'void armportReplayPowerRechargeTime(', 'static void power_recharge_time_receives('):
        c += function(state, name)
    c += function(net, 'void powerRef_Receive(')
    for name in ('void powerRechargeTimer_Receive(', 'void powerInfo_ChangeRechargeTimer('):
        c += function(source, name)
    c += 'static void receive(Packet *pak,Entity *e){\n' + timers + '}\n'
    c += '#define armportReplayPowerRechargeTime(...) ((void)0)\nstatic void original(Packet *pak,Entity *e){\n' + timers + '}\n#undef armportReplayPowerRechargeTime\n'
    c += 'static void update_creation(Entity *e,Power *ppow){PowerRef ppowRef={7,2,9};int uniqueID=99,iLevelBought=5,iNumCharges=6,bEnabled=1,bDisabledManually=0,iCntBoosts=4;float fUsageTime=1.5f,fAvailableTime=2.5f;unsigned ulCreationTime=0xffffffffU;\n' + accepted + '}\n'
    c += r'''
int main(int argc,char **argv){
 int mode=argc>1?atoi(argv[1]):0;PowerInfo info={items};Character character={50};Entity e={9,0xffffffffU,&info,&character};
 Packet p={{3,1,7,2,9,0,1,0,1,4},{0x80000000U,0x7fc12345U},0,0,{0}};
 if(mode==1)p.values[7]=7,p.values[8]=2,p.values[9]=9;
 if(mode==2)p.values[0]=1,p.values[1]=0;
 if(mode==4)p.floats[0]=0,p.floats[1]=0x7f800000U;
 if(mode==5)p.values[2]=0xffffffffU,p.values[3]=0x80000000U,p.values[4]=0x7fffffffU;
 Packet original_packet=p;original(&original_packet,&e);PowerRechargeTimer original_pool[2];memcpy(original_pool,pool,sizeof(pool));int original_count=count,original_alloc=alloc_calls,original_push=push_calls;
 count=alloc_calls=push_calls=0;memset(pool,0,sizeof(pool));memset(items,0,sizeof(items));
 power_recharge_time_count=77;armportReplayStateInit();assert(power_recharge_time_count==0);
 if(mode==3)active=0;
 receive(&p,&e);assert(p.at==(mode==2?2:10)&&p.ft==(mode==2?0:2));
 assert(!memcmp(&p,&original_packet,sizeof(p))&&!memcmp(pool,original_pool,sizeof(pool))&&count==original_count&&alloc_calls==original_alloc&&push_calls==original_push);
 if(mode==6)armportReplayPowerRechargeTime(NULL,0,0,0,&pool[0].rechargeCountdown);
 if(mode==7)armportReplayPowerRechargeTime(&e,0,0,0,NULL);
 if(mode==8){power_recharge_time_count=8192;armportReplayPowerRechargeTime(&e,0,0,0,&pool[0].rechargeCountdown);}
 if(mode==9){power_recharge_time_count=8193;power_recharge_time_receives();}
 if(mode==10)used=CAPACITY-1;
 if(mode==11){power_recharge_time_count=8191;armportReplayPowerRechargeTime(&e,-1,-2,-3,&pool[0].rechargeCountdown);assert(power_recharge_time_count==8192&&power_recharge_times[8191].bits==0x80000000U);power_recharge_time_count=2;}
 if(mode==12){active=0;armportReplayPowerRechargeTime(NULL,0,0,0,NULL);active=1;}
 if(mode==13){pool[0].rechargeCountdown=999;pool[1].rechargeCountdown=555;count=0;}
 unsigned saved_count=power_recharge_time_count;unsigned char *saved=malloc(sizeof(power_recharge_times));memcpy(saved,power_recharge_times,sizeof(power_recharge_times));
 power_recharge_time_receives();assert(saved_count==power_recharge_time_count&&!memcmp(saved,power_recharge_times,sizeof(power_recharge_times)));
 BasePower base={3,"Power.Name"};Power pow={.ppowBase=&base,.iUniqueID=-17};
 update_creation(&e,NULL);assert(!creation_calls&&!destroy_calls&&!size_calls);
 update_creation(&e,&pow);assert(creation_calls==1&&destroy_calls==1&&size_calls==1&&pow.ulCreationTime==0xffffffffU&&pow.iUniqueID==-17&&pow.iNumBoostsBought==2&&pow.iLevelBought==5&&pow.iNumCharges==6&&pow.fUsageTime==1.5f&&pow.fAvailableTime==2.5f&&pow.bEnabled==1&&!pow.bDisabledManually);
 puts(buffer);free(saved);free(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp); source_file = path / 'fixture.c'; exe = path / 'fixture'
        source_file.write_text(c)
        cc = os.environ.get('CC', 'cc')
        subprocess.run([cc, '-std=c99', '-O1', '-g', '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', str(source_file), '-o', str(exe)], check=True)
        for mode in range(14):
            result = subprocess.run([str(exe), str(mode)], capture_output=True, text=True, timeout=15)
            assert result.returncode == (3 if 6 <= mode <= 10 else 0), (mode, result.returncode, result.stderr)
            if result.returncode:
                continue
            expected = [dict(svr_idx=9, entity_id=0xffffffff, build=7, set=2, power=9, received_f32_bits=0x80000000), dict(svr_idx=9, entity_id=0xffffffff, build=0, set=1, power=4, received_f32_bits=0x7fc12345)]
            if mode == 1:
                expected[1].update(build=7, set=2, power=9)
            if mode in (2, 3):
                expected = []
            if mode == 4:
                expected[0]['received_f32_bits'] = 0; expected[1]['received_f32_bits'] = 0x7f800000
            if mode == 5:
                expected[0].update(build=-1, set=-2147483648, power=2147483647)
            assert json.loads(result.stdout) == expected, (mode, result.stdout, expected)
        source_file.write_text('#include "' + str(root / 'Game/src/clientcomm/armport_replay.h') + '"\nint main(void){int x=0;armportReplayPowerRechargeTime(x++,x++,x++,x++,x++);return x;}\n')
        subprocess.run([cc, str(source_file), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print('power update times: 14 ASan/UBSan cases and disabled-header inertness pass; actual recharge loop/reference/F32 reads and change handler, original-vs-observed packet/call/storage equality, repeated refs, skipped entries, raw NaN/zero/infinity bits, signed refs, inactive/reset/bounds/nonmutation, later timer overwrite/removal exclusion, accepted/null creation-time assignment; dependencies substituted, not whole update packet/native ABI/lifetime proof')


if __name__ == '__main__':
    main()
