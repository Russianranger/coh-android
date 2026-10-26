#!/usr/bin/env python3
"""Exercise original NetFx receiving and active-field snapshot observations."""
import argparse,json,os,re,subprocess,tempfile
from pathlib import Path
from receiver_tray_state import function


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);source=p.parse_args().source
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text();receive=(source/'Game/src/entity/entrecv.c').read_text()
    header=(source/'Common/entity/netfx.h').read_text();header=re.sub(r'^#include[^\n]*\n','',header,flags=re.M)
    code=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (8*1024*1024)
#define check(x) do {if(!(x)) _Exit(3);} while(0)
typedef uint8_t U8;typedef uint32_t U32;typedef float F32;typedef float Vec3[3];
typedef struct ColorPair {union{U32 integer;}primary,secondary;}ColorPair;
'''+header+r'''
typedef struct Entity{NetFx*netfx_list;int netfx_count,netfx_max;}Entity;
static int demo_recording,demo_calls,debug_calls,error_calls;static struct{int netfxdebug;}game_state;static Entity*selected;
#define SELECTED_ENT selected
#define ABSTIME_SECOND 3000
#define START_BIT_COUNT(p,n) ((void)0)
#define STOP_BIT_COUNT(p) ((void)0)
static const char*textStd(const char*s){return s;}
static void Errorf(const char*s){error_calls++;}
static void demoSetAbsTimeOffset(int n){demo_calls++;}
static void demoRecordFx(NetFx*f){demo_calls++;}
static void debugShowNetfx(Entity*e,NetFx*f){debug_calls++;}
/* Array allocator substitute preserves old entries and zeros new entries. */
static void*dynArrayAdd(void*base,int size,int*count,int*max,int n){void**p=base;int old=*count;*p=realloc(*p,size*(old+n));assert(*p);memset((char*)*p+size*old,0,size*n);*count=*max=old+n;return (char*)*p+size*old;}
typedef struct Packet{U32 words[512];int count,cursor;}Packet;
static U32 take(Packet*p){assert(p->cursor<p->count);return p->words[p->cursor++];}
static U32 pktGetBitsPack(Packet*p,int n){return take(p);}
static U32 pktGetIfSetBitsPack(Packet*p,int n){return take(p);}
static U32 pktGetBits(Packet*p,int n){return take(p);}
static U32 pktGetIfSetBits(Packet*p,int n){return take(p);}
static F32 pktGetF32(Packet*p){U32 n=take(p);F32 f;memcpy(&f,&n,4);return f;}
static F32 pktGetIfSetF32(Packet*p){return pktGetF32(p);}
static char buffer[CAPACITY];static size_t used;
'''
    code+=function(receive,'NetFx *entrecvAllocNetFx(')+function(receive,'static void entReceiveNetFx(')
    code+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code+=function(state,'static void entity_netfx_receive_state(')
    code+=r'''
static void push(Packet*p,U32 v){assert(p->count<512);p->words[p->count++]=v;}
static void effect(Packet*p,int origin,int target,int tint,int command){
 push(p,command);push(p,0xf1234567U);push(p,1);push(p,15);push(p,99);push(p,tint);
 if(tint){push(p,0xffffffff);push(p,0x80000000);}
 push(p,17);push(p,0xffffffff);push(p,0x80000000);push(p,0x7fc01234);push(p,10);push(p,0x80000001);
 push(p,origin);if(origin==1){push(p,0x3f800000);push(p,0x80000000);push(p,0x7fc04321);}else if(origin==0){push(p,123);push(p,7);}
 push(p,target);if(target==1){push(p,0x40000000);push(p,0x40400000);push(p,0xc0800000);push(p,456);}else if(target==0)push(p,456);
}
int main(int argc,char**argv){
 int mode=argc>1?atoi(argv[1]):0,i;Entity e={0},saved;Packet p={0};NetFx*before;int n=mode==4?0:mode==5?2:1;
 push(&p,n);for(i=0;i<n;i++)effect(&p,mode==1||mode==3?1:mode==6?2:0,mode==2||mode==3?1:mode==6?2:0,mode!=0,mode==5&&i==1?3:1);
 if(mode==7)demo_recording=1,game_state.netfxdebug=1,selected=&e;
 entReceiveNetFx(&p,&e);assert(p.cursor==p.count);assert(error_calls==(mode==6?2:0));assert(demo_calls==(mode==7?3:0)&&debug_calls==(mode==7?1:0));
 if(mode==8){Packet q={0};push(&q,1);effect(&q,1,1,0,2);entReceiveNetFx(&q,&e);assert(q.cursor==q.count);}
 if(mode==9){NetFx*f=&e.netfx_list[0];f->serverTimeout=123;f->timeCalled=456;f->commandStatus=2;f->dont_send_to_self=1;memset(f->originPos,0xff,sizeof(f->originPos));memset(f->targetPos,0xff,sizeof(f->targetPos));}
 if(mode==10)e.netfx_count=-1;
 if(mode==11)e.netfx_count=8193;
 if(mode==12)e.netfx_max=0;
 if(mode==13){free(e.netfx_list);e.netfx_list=NULL;}
 if(mode==14)used=CAPACITY-1;
 if(mode==15){NetFx v=e.netfx_list[0];free(e.netfx_list);e.netfx_count=e.netfx_max=8192;e.netfx_list=malloc(sizeof(NetFx)*8192);assert(e.netfx_list);for(i=0;i<8192;i++)e.netfx_list[i]=v;}
 if(mode==16)e.netfx_list[0].targetEnt=0xffffffff;
 if(mode==17){e.netfx_list[0].hasColorTint=0;e.netfx_list[0].colorTint.primary.integer=9;e.netfx_list[0].colorTint.secondary.integer=8;}
 if(mode==18)e.netfx_count=0; /* allocated-empty list is emitted empty */
 if(mode>=10&&mode<=14){entity_netfx_receive_state(&e);assert(0);}
 saved=e;before=malloc(sizeof(NetFx)*(e.netfx_count?e.netfx_count:1));assert(before);if(e.netfx_count)memcpy(before,e.netfx_list,sizeof(NetFx)*e.netfx_count);
 entity_netfx_receive_state(&e);assert(!memcmp(&saved,&e,sizeof(e)));if(e.netfx_count)assert(!memcmp(before,e.netfx_list,sizeof(NetFx)*e.netfx_count));puts(buffer);free(before);free(e.netfx_list);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);(root/'fixture.c').write_text(code)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(root/'fixture.c'),'-o',str(root/'fixture')],check=True)
        for mode in range(19):
            r=subprocess.run([str(root/'fixture'),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if 10<=mode<=14 else 0),(mode,r.returncode,r.stderr)
            if 10<=mode<=14:continue
            v=json.loads(r.stdout);assert len(v)==(0 if mode in (4,18) else 2 if mode in (5,8) else 8192 if mode==15 else 1)
            for i,f in enumerate(v):
                origin=1 if mode in (1,3) or mode==8 and i==1 else 2 if mode==6 else 0
                target=1 if mode in (2,3) or mode==8 and i==1 else 2 if mode==6 else 0
                tint=mode not in (0,17) and not(mode==8 and i==1)
                expected=dict(command=3 if mode==5 and i==1 else 2 if mode==8 and i==1 else 1,net_id=0xf1234567,handle=99,pitch=1,power_flags=15,has_tint=int(tint),tint=[0xffffffff,0x80000000] if tint else None,delay_f32_bits=[0x41880000],trigger_fx_id=0xffffffff,duration_f32_bits=[0x80000000],radius_f32_bits=[0x7fc01234],power=10,debris=0x80000001,origin_type=origin,origin=[0x3f800000,0x80000000,0x7fc04321] if origin==1 else dict(entity=123,bone=7) if origin==0 else None,target_type=target,target=dict(position_f32_bits=[0x40000000,0x40400000,0xc0800000],entity=456) if target==1 else dict(entity=0xffffffff if mode==16 else 456) if target==0 else None)
                assert f==expected,(mode,i,f)
    print('NetFx receive state: 19 ASan/UBSan cases; original receive/allocation caller and actual writer, position/entity/invalid-type branches, tint/no-tint, ordered append and destroy command, full-width IDs and F32 bits, demo/debug, inactive/cache exclusion, immutable storage, null/count/capacity/output rejection and 8192 boundary; packet/allocator/demo dependencies substituted; renderer execution excluded')

if __name__=='__main__':main()
