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
typedef struct Entity{TaskForce*taskforce;int onFlashback;}Entity;
typedef struct Packet{U32 data[35];int count,cursor;}Packet;
static U32 take(Packet*p){assert(p->cursor<p->count);return p->data[p->cursor++];}
static U32 pktGetBitsPack(Packet*p,int n){assert(n==1);return take(p);}
static U32 pktGetBits(Packet*p,int n){assert(n==1);return take(p);}
static U32 pktGetBitsAuto(Packet*p){return take(p);}
static U32 clock_value=1000;static int clock_calls;
static U32 timerSecondsSince2000(void){clock_calls++;return clock_value;}
static char buffer[CAPACITY];static size_t used;
'''
    c+=function(helpers,'bool TaskForceIsParameterEnabled(')+receiver
    c+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]+function(state,'static void entity_taskforce_parameters(')
    c+=r'''
int main(int argc,char**argv){
 int mode=argc>1?atoi(argv[1]):0,i;TaskForce t={0},saved;Entity e={&t,0},saved_e;Packet p={0};U32 mask=0xffffffffU;
 for(i=0;i<32;i++)t.parameters[i]=900+i;t.parametersSet=123;
 if(mode==1)mask=0;if(mode==2)mask=0x80000000U;if(mode==3)mask=1;if(mode==4)mask=(1U<<1)|(1U<<23);
 if(mode==6)e.taskforce=NULL;
 if(mode==7)clock_value=2000;
 p.data[p.count++]=1;p.data[p.count++]=mode==5?0:1;
 if(mode!=5){p.data[p.count++]=mask;for(i=0;i<32;i++)if(mask&(1U<<i))p.data[p.count++]=0xffffff00U+i;}
 assert(entReceiveTaskforceParameters(&p,&e)==1&&p.cursor==p.count);assert(e.onFlashback==1);
 if(e.taskforce&&mode!=5){assert(t.parametersSet==mask);for(i=0;i<32;i++){U32 want=mask&(1U<<i)?0xffffff00U+i:900+i;if((i==1||i==23)&&(mask&(1U<<i)))want+=clock_value;assert(t.parameters[i]==want);}}
 assert(clock_calls==(mode==0||mode==4||mode==7||mode==8?2:0));
 if(mode==8)used=CAPACITY-1;
 saved=t;saved_e=e;entity_taskforce_parameters(&e);assert(!memcmp(&saved,&t,sizeof(t))&&!memcmp(&saved_e,&e,sizeof(e)));puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for negative in (False,True):
            code=c.replace('(1U << count)','(1 << count)') if negative else c
            src=root/('old.c' if negative else 'current.c');src.write_text(code);exe=src.with_suffix('')
            subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(src),'-o',str(exe)],check=True)
            if negative:
                r=subprocess.run([str(exe),'1'],capture_output=True,text=True,timeout=15)
                assert r.returncode!=0 and 'left shift of 1 by 31' in r.stderr,(r.returncode,r.stderr)
                continue
            for mode in range(9):
                r=subprocess.run([str(exe),str(mode)],capture_output=True,text=True,timeout=15)
                assert r.returncode==(3 if mode==8 else 0),(mode,r.returncode,r.stderr)
                if mode==8:continue
                v=json.loads(r.stdout)
                if mode==6:assert v is None;continue
                mask={1:0,2:0x80000000,3:1,4:(1<<1)|(1<<23),5:123}.get(mode,0xffffffff)
                assert v['enabled_mask']==mask
                expected=[None if i in (1,23) else 0xffffff00+i if mode!=5 and mask&(1<<i) else 900+i for i in range(32)]
                assert v['nonclock_slots']==expected,(mode,v)
    print('taskforce parameters: 9 passing ASan/UBSan cases plus old signed-shift negative control; original receiver/enable helper, all32 bits, retained disabled slots, absent update/null taskforce, exact clock addition and exclusion, nonmutation and output bounds; packet/clock dependencies substituted; raw two time slots remain unobserved')

if __name__=='__main__':main()
