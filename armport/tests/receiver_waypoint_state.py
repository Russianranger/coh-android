#!/usr/bin/env python3
"""Exercise the actual server-waypoint writer with a bounded const-stash fixture."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    fixed = source[source.index('static void fixed_string('):source.index('static void group_members(')]
    writer = source[source.index('typedef struct ArmPortWaypointEntry'):source.index('void armportReplayDesaturation(')]
    fixture = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024*1024)
/* Match native ExitProcess failure without requiring negative-path cleanup. */
#define check(x) do { if (!(x)) _Exit(3); } while (0)
static char buffer[CAPACITY];static size_t used;
typedef struct { char *name; void *data; int skin,width,height; } AtlasTex;
typedef struct { int navOn,type,id;unsigned pulseBIcon:1;char name[256],mapName[512];float angle,world_location[4][3],map_location[2];AtlasTex *icon,*iconB;unsigned creationTime;void *destEntity; } Destination;
typedef struct { const char *key; const Destination *value; } Element;
typedef const Element *cStashElement;
typedef struct { unsigned declared,actual;Element entries[8193]; } Table;
typedef struct {const Table *table;unsigned index;} cStashTableIterator;
static Table *serverDestList;
static unsigned stashGetValidElementCount(const Table *t) {return t->declared;}
static void stashGetIteratorConst(const Table *t,cStashTableIterator *it) {it->table=t;it->index=0;}
static int stashGetNextElementConst(cStashTableIterator *it,cStashElement *e) {
 if(it->index==it->table->actual)return 0;*e=&it->table->entries[it->index++];return 1;
}
static const char *stashElementGetStringKey(cStashElement e) {return e->key;}
static const void *stashElementGetPointerConst(cStashElement e) {return e->value;}
''' + formatting + fixed + writer + r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,i;static Table table={3,3,{{0}}},before_table;
 Destination d={0},other={0},before_d;AtlasTex icon={"escaped\"\\\200",0,0,0,0},background={NULL,0,0,0,0};
 unsigned angle=0x80000000U,pos[3]={0x7fc01234U,0x7f800000U,0xff800000U};static char keys[8192][20];
 d.navOn=1;d.type=2;d.id=-31;d.pulseBIcon=1;strcpy(d.name,"Atlas\nPark");strcpy(d.mapName,"maps/City_00_01");
 memcpy(&d.angle,&angle,4);memcpy(d.world_location[3],pos,12);d.icon=&icon;d.iconB=&background;
 other.id=-1;table.entries[0]=(Element){"31",&d};table.entries[1]=(Element){"1",&other};table.entries[2]=(Element){"17",NULL};serverDestList=&table;
 if(mode==1) {Element temp=table.entries[0];table.entries[0]=table.entries[2];table.entries[2]=temp;}
 if(mode==2) serverDestList=NULL;
 if(mode==3) table.declared=table.actual=0;
 if(mode==4) table.declared=8193;
 if(mode==5) table.declared=2;
 if(mode==6) table.declared=4;
 if(mode==7) table.entries[2].key=NULL;
 if(mode==8) table.entries[2].key="31";
 if(mode==9) memset(d.name,'x',sizeof(d.name));
 if(mode==10) memset(d.mapName,'x',sizeof(d.mapName));
 if(mode==11) used=CAPACITY-2;
 if(mode==12) d.world_location[3][2]=17;
 if(mode==13) d.creationTime=31,d.destEntity=&other,d.map_location[0]=19,icon.data=&d,icon.width=999;
 if(mode==14) d.icon=NULL;
 if(mode==15) {strcpy(d.name,"changed");d.id=-17;d.navOn=0;d.pulseBIcon=0;}
 if(mode==16) {table.actual=table.declared=8192;for(i=0;i<8192;++i){snprintf(keys[i],20,"%d",i+1);table.entries[i]=(Element){keys[i],NULL};}}
 if(mode==17) {memset(d.name,'A',sizeof(d.name)-1);d.name[sizeof(d.name)-1]=0;memset(d.mapName,'B',sizeof(d.mapName)-1);d.mapName[sizeof(d.mapName)-1]=0;}
 before_d=d;before_table=table;server_waypoint_state();
 assert(!memcmp(&before_d,&d,sizeof(d)) && !memcmp(&before_table,&table,sizeof(table)));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        p = Path(temporary)
        (p / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(p / 'fixture.c'), '-o', str(p / 'fixture')], check=True)
        results = [subprocess.run([str(p / 'fixture'), str(i)], capture_output=True,
                                  text=True, timeout=15) for i in range(18)]
        for i, result in enumerate(results):
            assert result.returncode == (3 if 4<=i<=11 else 0), (i,result.returncode,result.stderr)
        values = {i:json.loads(r.stdout) for i,r in enumerate(results) if r.returncode==0}
        target=dict(nav_on=1,type=2,id=-31,pulse=1,name='Atlas\nPark',map='maps/City_00_01',
                    angle_f32_bits=[0x80000000],position_f32_bits=[0x7fc01234,0x7f800000,0xff800000],
                    icon_name='escaped"\\\x80',background_icon_name=None)
        empty=dict(nav_on=0,type=0,id=-1,pulse=0,name='',map='',angle_f32_bits=[0],
                   position_f32_bits=[0,0,0],icon_name=None,background_icon_name=None)
        expected=[dict(key='1',destination=empty),dict(key='17',destination=None),dict(key='31',destination=target)]
        assert values[0]==expected and values[1]==expected and values[2]==[] and values[3]==[]
        assert values[13]==expected and values[14][-1]['destination']['icon_name'] is None
        assert values[12][-1]['destination']['position_f32_bits'][-1]==0x41880000
        assert values[15][-1]['destination']['id']==-17 and values[15][-1]['destination']['pulse']==0
        assert len(values[16])==8192 and {e['key'] for e in values[16]}=={str(i+1) for i in range(8192)}
        assert values[16]==sorted(values[16],key=lambda e:e['key'])
        assert values[17][-1]['destination']['name']=='A'*255 and values[17][-1]['destination']['map']=='B'*511
    print('waypoint actual writer: 18 cases pass; literal key/value map independent of stash bucket order, null/empty state, signed IDs, raw F32 bits, resolved icon names, fixed strings, source immutability, mutation sensitivity, local cache exclusion, 8192 entries and count/key/string/output rejection; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
