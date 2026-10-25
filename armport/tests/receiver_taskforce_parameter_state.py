#!/usr/bin/env python3
"""Check all taskforce parameter bits and reproduce the original signed-shift defect."""
import argparse,json,os,re,subprocess,tempfile
from pathlib import Path
from receiver_tray_state import function


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);source=p.parse_args().source
    header=(source/'Common/entity/teamCommon.h').read_text();receive=(source/'Game/src/entity/entrecv.c').read_text();helpers=(source/'Common/entity/TaskforceParams.c').read_text()
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text();receiver=function(receive,'static int entReceiveTaskforceParameters(')
    assert '(1U << count)' in receiver
    c=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>
#define CAPACITY 8192
#define check(x) do {if(!(x)) _Exit(3);} while(0)
#define devassert(x) ((void)0)
typedef uint32_t U32;
'''+re.search(r'^#define MAX_TASKFORCE_PARAMETERS\s+\d+',header,re.M).group(0)+'\n'
    c+=header[header.index('typedef enum TaskForceParameter'):header.index('} TaskForceParameter;')+len('} TaskForceParameter;')]
    c+=r'''
typedef struct TaskForce{U32 parametersSet,parameters[MAX_TASKFORCE_PARAMETERS];}TaskForce;
typedef struct Entity{TaskForce*taskforce;int onFlashback;int svr_idx,taskforce_id;unsigned id;}Entity;
typedef struct Packet{U32 data[35];int count,cursor;}Packet;
static U32 take(Packet*p){assert(p->cursor<p->count);return p->data[p->cursor++];}
static U32 pktGetBitsPack(Packet*p,int n){assert(n==1);return take(p);}
static U32 pktGetBits(Packet*p,int n){assert(n==1);return take(p);}
static U32 pktGetBitsAuto(Packet*p){return take(p);}
static U32 clock_value=1000;static int clock_calls;
static U32 timerSecondsSince2000(void){clock_calls++;return clock_value;}
static char buffer[CAPACITY];static size_t used;
'''
    c+=function(helpers,'bool TaskForceIsParameterEnabled(')
    c+='\nvoid armportReplayTaskforceTime(const Entity*,unsigned,unsigned);\n'+receiver
    c+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]+function(state,'static void entity_taskforce_parameters(')
    c+='\nstatic int active=1;\n'+re.search(r'^static struct \{ int svr_idx, taskforce_id;[^\n]+',state,re.M).group(0)+'\nstatic unsigned taskforce_time_count;\n'
    c+=function(state,'void armportReplayTaskforceTime(')+function(state,'static void taskforce_time_receives(')
    c+=r'''
int main(int argc,char**argv){
 int mode=argc>1?atoi(argv[1]):0,i;TaskForce t={0},saved;Entity e={.taskforce=&t,.svr_idx=4,.taskforce_id=88,.id=123},saved_e;Packet p={0};U32 mask=0xffffffffU;unsigned history_count;unsigned char history[sizeof(taskforce_times)];
 for(i=0;i<32;i++)t.parameters[i]=900+i;t.parametersSet=123;
 if(mode==1)mask=0;if(mode==2)mask=0x80000000U;if(mode==3)mask=1;if(mode==4)mask=(1U<<1)|(1U<<23);
 if(mode==6)e.taskforce=NULL;
 if(mode==7)clock_value=2000;
 if(mode==9)active=0;
 p.data[p.count++]=1;p.data[p.count++]=mode==5?0:1;
 if(mode!=5){p.data[p.count++]=mask;for(i=0;i<32;i++)if(mask&(1U<<i))p.data[p.count++]=0xffffff00U+i;}
 assert(entReceiveTaskforceParameters(&p,&e)==1&&p.cursor==p.count);assert(e.onFlashback==1);
 if(e.taskforce&&mode!=5){assert(t.parametersSet==mask);for(i=0;i<32;i++){U32 want=mask&(1U<<i)?0xffffff00U+i:900+i;if((i==1||i==23)&&(mask&(1U<<i)))want+=clock_value;assert(t.parameters[i]==want);}}
 assert(clock_calls==(mode==0||mode==4||mode>=7?2:0));
 if(mode==8)used=CAPACITY-1;
 if(mode==10){e.id=124;e.taskforce_id=89;armportReplayTaskforceTime(&e,1,0);armportReplayTaskforceTime(&e,23,0xffffffffU);}
 if(mode==11){taskforce_time_count=8192;armportReplayTaskforceTime(&e,1,1);}
 if(mode==12){taskforce_time_count=8193;taskforce_time_receives();}
 if(mode==13){taskforce_time_count=0;armportReplayTaskforceTime(NULL,1,1);}
 if(mode==14){taskforce_time_count=8191;armportReplayTaskforceTime(&e,23,7);assert(taskforce_time_count==8192&&taskforce_times[8191].seconds==7);taskforce_time_count=2;}
 history_count=taskforce_time_count;memcpy(history,taskforce_times,sizeof(taskforce_times));saved=t;saved_e=e;out("{\"parameters\":");entity_taskforce_parameters(&e);out(",\"time_receives\":");taskforce_time_receives();out("}");assert(!memcmp(&saved,&t,sizeof(t))&&!memcmp(&saved_e,&e,sizeof(e)));assert(history_count==taskforce_time_count&&!memcmp(history,taskforce_times,sizeof(taskforce_times)));puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        disabled=root/'disabled.c'
        disabled.write_text('#include <stdint.h>\n#include "'+str(source/'Game/src/clientcomm/armport_replay.h')+'"\nint main(void){int x=0,y=0,z=0;armportReplayTaskforceTime((const Entity*)(uintptr_t)x++,y++,z++);return x+y+z;}\n')
        subprocess.run([os.environ.get('CC','cc'),str(disabled),'-o',str(root/'disabled')],check=True)
        subprocess.run([str(root/'disabled')],check=True)
        for negative in (False,True):
            code=c.replace('(1U << count)','(1 << count)') if negative else c
            src=root/('old.c' if negative else 'current.c');src.write_text(code);exe=src.with_suffix('')
            subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(src),'-o',str(exe)],check=True)
            if negative:
                r=subprocess.run([str(exe),'1'],capture_output=True,text=True,timeout=15)
                assert r.returncode!=0 and 'left shift of 1 by 31' in r.stderr,(r.returncode,r.stderr)
                continue
            for mode in range(15):
                r=subprocess.run([str(exe),str(mode)],capture_output=True,text=True,timeout=15)
                assert r.returncode==(3 if mode in (8,11,12,13) else 0),(mode,r.returncode,r.stderr)
                if mode in (8,11,12,13):continue
                result=json.loads(r.stdout);v=result['parameters']
                expected_events=[] if mode in (1,2,3,5,6,9) else [dict(svr_idx=4,entity_id=123,taskforce_id=88,slot=i,received_seconds=0xffffff00+i) for i in (1,23)]
                if mode==10:expected_events += [dict(svr_idx=4,entity_id=124,taskforce_id=89,slot=1,received_seconds=0),dict(svr_idx=4,entity_id=124,taskforce_id=89,slot=23,received_seconds=0xffffffff)]
                assert result['time_receives']==expected_events,(mode,result)
                if mode==6:assert v is None;continue
                mask={1:0,2:0x80000000,3:1,4:(1<<1)|(1<<23),5:123}.get(mode,0xffffffff)
                assert v['enabled_mask']==mask
                expected=[None if i in (1,23) else 0xffffff00+i if mode!=5 and mask&(1<<i) else 900+i for i in range(32)]
                assert v['nonclock_slots']==expected,(mode,v)
    print('taskforce parameters: 15 passing ASan/UBSan cases plus old signed-shift negative control; original receiver/enable helper, all32 bits, retained disabled slots, absent update/null taskforce, exact clock addition and exclusion, nonmutation and output bounds; packet/clock dependencies substituted; raw accepted time receipts captured in bounded ordered history before clock addition, inactive/nonclock and actual disabled-header inertness, changed entity/taskforce IDs and full-width time values')

if __name__=='__main__':main()
