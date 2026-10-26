#!/usr/bin/env python3
"""Original INITIAL token loops plus raw-time observer; allocator/packet stubs."""
import argparse,json,os,re,subprocess,tempfile
from pathlib import Path
from receiver_tray_state import function


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);root=p.parse_args().source
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    receive=(root/'Game/src/entity/entrecv.c').read_text()
    pos=receive.index('int idx = rewardtoken_IdxFromName( &e->pl->rewardTokens, tokenName );')
    start=receive.rfind('    count = pktGetBitsAuto( pak );',0,pos)
    loops=receive[start:receive.index('    START_BIT_COUNT(pak, "lfg");',pos)]
    c=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (128*1024)
#define check(x) do{if(!(x))_Exit(3);}while(0)
typedef struct RewardToken {const char *reward;int val;unsigned timer;}RewardToken;
typedef struct Player {RewardToken **rewardTokens,**activePlayerRewardTokens;}Player;
typedef struct Entity {Player *pl;int svr_idx;unsigned id;}Entity;
typedef struct Packet {unsigned values[6];int cursor,string_cursor;char*names[2];}Packet;
static unsigned pktGetBitsAuto(Packet*p){assert(p->cursor<6);return p->values[p->cursor++];}
static unsigned pktGetBitsPack(Packet*p,int n){assert(n==1);return pktGetBitsAuto(p);}
static char*pktGetString(Packet*p){assert(p->string_cursor<2);return p->names[p->string_cursor++];}
static int award_fail,award_calls,lookup_calls,clock_calls;static unsigned local_clock=123;
static int rewardtoken_IdxFromName(RewardToken***items,const char*name){++lookup_calls;return (*items)[0]?0:-1;}
static RewardToken created[2];
static int rewardtoken_Award(RewardToken***items,const char*name,int val){int n=award_calls++;if(award_fail)return -1;assert(n<2);++clock_calls;created[n]=(RewardToken){name,val,local_clock};(*items)[0]=&created[n];return 0;}
#define EAINRANGE(i,a) ((i)>=0&&(i)<1&&(a)[i])
static int active;static char*buffer;static size_t used;
static int orientation[1],alignment_delays[1],desaturation;static unsigned power_recharge_time_count;
static unsigned taskforce_time_count,power_creation_time_count;
'''
    c+=re.search(r'^static struct \{ int svr_idx, active_player[^\n]+',state,re.M).group(0)+'\nstatic unsigned reward_time_count;\n'
    c+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    c+=function(state,'void armportReplayStateInit(')+function(state,'void armportReplayRewardTime(')+function(state,'static void reward_time_receives(')
    c+='static void receive_initial(Packet*pak,Entity*e){int i,count;\n'+loops+'}\n'
    c+=r'''
int main(int argc,char**argv){
 int mode=argc>1?atoi(argv[1]):0;char name[1025]="Token\"\n\377",other[]="Other";
 RewardToken a={name,-1,11},b={other,-2,22};RewardToken*av[1]={NULL},*bv[1]={NULL};Player pl={av,bv};Entity e={&pl,7,0xffffffffU};
 Packet p={{1,17,0xffffffffU,1,19,0x80000000U},0,0,{name,other}};
 reward_time_count=77;taskforce_time_count=55;armportReplayStateInit();assert(reward_time_count==0&&taskforce_time_count==0);
 if(mode==1)local_clock=999;
 if(mode==2)active=0;
 if(mode==3)award_fail=1;
 if(mode==4)av[0]=&a,bv[0]=&b;
 if(mode==5)p.values[2]=0,p.values[5]=1;
 if(mode==6){memset(name,'X',1023);name[1023]=0;}
 if(mode==7){memset(name,'X',1024);name[1024]=0;}
 receive_initial(&p,&e);
 assert(p.cursor==6&&p.string_cursor==2&&lookup_calls==2);
 assert(award_calls==(mode==4?0:2)&&clock_calls==((mode==3||mode==4)?0:2));
 if(!award_fail){assert(av[0]->val==17&&bv[0]->val==19&&av[0]->timer==p.values[2]&&bv[0]->timer==p.values[5]);}
 if(mode==8){name[0]='Q';other[0]='R';}
 if(mode==9){reward_time_count=8192;armportReplayRewardTime(&e,0,0,name,1);}
 if(mode==10){reward_time_count=8193;reward_time_receives();}
 if(mode==11)armportReplayRewardTime(NULL,0,0,name,1);
 if(mode==12)armportReplayRewardTime(&e,2,0,name,1);
 if(mode==13)armportReplayRewardTime(&e,0,-1,name,1);
 if(mode==14)armportReplayRewardTime(&e,0,8192,name,1);
 if(mode==15)armportReplayRewardTime(&e,0,0,NULL,1);
 if(mode==16)used=CAPACITY-1;
 if(mode==17){reward_time_count=8191;armportReplayRewardTime(&e,1,8191,name,0);assert(reward_time_count==8192&&reward_times[8191].seconds==0);reward_time_count=2;}
 if(mode==18){active=0;armportReplayRewardTime(NULL,2,-1,NULL,0);active=1;}
 if(mode==19){e.id=17;e.svr_idx=9;armportReplayRewardTime(&e,1,0,"New",7);}
 unsigned count=reward_time_count;unsigned char*saved=malloc(sizeof(reward_times));memcpy(saved,reward_times,sizeof(reward_times));
 reward_time_receives();assert(count==reward_time_count&&!memcmp(saved,reward_times,sizeof(reward_times)));puts(buffer);free(saved);free(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        d=Path(tmp);f=d/'fixture.c';f.write_text(c);exe=d/'fixture'
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(f),'-o',str(exe)],check=True)
        baseline=None
        for mode in range(20):
            r=subprocess.run([str(exe),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if mode==7 or 9<=mode<=16 else 0),(mode,r.returncode,r.stderr)
            if r.returncode:continue
            v=json.loads(r.stdout)
            want=[dict(svr_idx=7,entity_id=0xffffffff,active_player=i,index=0,received_seconds=[0xffffffff,0x80000000][i],name=['Token"\n\xff','Other'][i]) for i in range(2)]
            if mode in (2,3):want=[]
            if mode==5:want[0]['received_seconds']=0;want[1]['received_seconds']=1
            if mode==6:want[0]['name']='X'*1023
            if mode==19:want.append(dict(svr_idx=9,entity_id=17,active_player=1,index=0,received_seconds=7,name='New'))
            assert v==want,(mode,v,want)
        f=d/'disabled.c';f.write_text('#include "'+str(root/'Game/src/clientcomm/armport_replay.h')+'"\nint main(void){int x=0;armportReplayRewardTime(x++,x++,x++,x++,x++);return x;}\n')
        subprocess.run([os.environ.get('CC','cc'),str(f),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
    print('reward raw times: 20 ASan/UBSan cases and disabled-header inertness passed; actual two INITIAL loops, original field assignments/read counts, accepted-only history, normal/active lists, copied names, full U32, local-clock exclusion, reset, bounds and nonmutation; packet/award/clock dependencies substituted, not native ABI proof')

if __name__=='__main__':main()
