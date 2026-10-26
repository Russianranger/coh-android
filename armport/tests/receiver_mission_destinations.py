#!/usr/bin/env python3
"""Probe original mission/keydoor receivers and their retained-array writer."""
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
    native = (source/'Game/src/UI/uiCompass.c').read_text()
    state = (Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdarg.h>
#define CAPACITY (1024*1024)
#define check(x) do { if (!(x)) _Exit(3); } while (0)
static char buffer[CAPACITY];static size_t used;
typedef uint32_t U32;
typedef struct {const char *name;} AtlasTex;
typedef struct {int navOn,type,id,color,colorB,uid;char name[256],mapName[512];
 float world_location[4][3],orig_world_pos[3],map_location[2];
 unsigned showWaypoint:1,iconBInCompass:1;U32 creationTime;AtlasTex *icon,*iconB;void *destEntity;
} Destination;
enum { ICON_PLAYER=1,ICON_TEAMMATE,ICON_LEAGUEMATE,ICON_MISSION_WAYPOINT=15,ICON_MISSION_KEYDOOR=16 };
#define MISSION_WAYPOINT_LOCATION 400
#define MISSION_KEYDOOR_LOCATION 600
#define WAYPOINT_TIMETHRESHOLD 3
#define TRUE 1
#define copyVec3(a,b) memcpy((b),(a),3*sizeof(float))
static Destination **missionDest,**keydoorDest,waypointDest,activeTaskDest;
static int destUID,requests;
static char gMapName[]="maps/Atlas";
typedef struct {int n;Destination *v[8193];} Array;
static Array *array(Destination *const *v) {return (Array *)((char *)v - offsetof(Array,v));}
static int array_size(Destination *const *v) {return v?array(v)->n:0;}
#define eaSize(a) array_size(*(a))
static void eaPush(Destination ***v,Destination *d) {
 if(!*v){Array *a=calloc(1,sizeof(*a));assert(a);*v=a->v;}
 Array *a=array(*v);assert(a->n<8193);a->v[a->n++]=d;
}
static void eaRemove(Destination ***v,int i) {Array *a=array(*v);assert(i>=0 && i<a->n);memmove(a->v+i,a->v+i+1,(--a->n-i)*sizeof(*a->v));}
static void eaDestroy(Destination ***v) {if(*v)free(array(*v));*v=NULL;}
typedef struct {float pos[3];} Entity;
static Entity player={{0,0,0}};static int have_player;
static Entity *playerPtr(void) {return have_player?&player:NULL;}
#define ENTPOS(e) ((e)->pos)
static float distance3SquaredXZ(const float *a,const float *b) {return (a[0]-b[0])*(a[0]-b[0])+(a[2]-b[2])*(a[2]-b[2]);}
typedef struct {int kind,width;U32 bits;} Token;
typedef struct {Token t[64];int n,read;} Packet;
static U32 take(Packet *p,int kind,int width) {assert(p->read<p->n);Token t=p->t[p->read++];assert(t.kind==kind && t.width==width);return t.bits;}
static U32 pktGetBits(Packet *p,int w) {return take(p,0,w);}
static U32 pktGetBitsPack(Packet *p,int w) {return take(p,1,w);}
static U32 pktGetBitsAuto(Packet *p) {return take(p,2,0);}
static float pktGetF32(Packet *p) {U32 u=take(p,3,32);float f;memcpy(&f,&u,4);return f;}
static void token(Packet *p,int k,int w,U32 b) {assert(p->n<64);p->t[p->n++]=(Token){k,w,b};}
static int sent;static Packet outgoing;
#define CLIENTINP_REQUEST_WAYPOINT 7
#define START_INPUT_PACKET(p,c) Packet *p=&outgoing;assert((c)==7);sent=0
static void pktSendF32(Packet *p,float f) {(void)f;assert(p==&outgoing && sent<3);++sent;}
static void pktSendBitsPack(Packet *p,int w,int id) {assert(p==&outgoing && sent==3 && w==1 && id==destUID);++sent;}
#define END_INPUT_PACKET assert(sent==4);++requests;
static AtlasTex icons[2]={{"map_enticon_mission_a.tga"},{"map_enticon_mission_b.tga"}};
static AtlasTex *atlasLoadTexture(const char *name) {for(int i=0;i<2;++i)if(!strcmp(name,icons[i].name))return &icons[i];assert(0);return NULL;}
'''
    code += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code += function(state, 'static void fixed_string(')
    code += function(state, 'static void mission_destination_state(')
    for name in ('static void compass_UpdateWaypoint(', 'void compass_SetDestination(',
                 'void clearDestination(', 'void compass_ClearAllMatchingId(',
                 'static Destination* DestinationFind(', 'Destination* DestinationFindClosest(',
                 'void MissionWaypointReceive(', 'static void MissionKeydoorTurnOffAll(',
                 'void MissionKeydoorReceive(', 'void MissionClearAll('):
        code += function(native, name)
    code += r'''
static void waypoint(int adding,int id,U32 time,U32 x) {
 Packet p={0};token(&p,0,1,adding);token(&p,0,1,1);token(&p,1,1,id);
 if(adding){token(&p,2,0,time);token(&p,3,32,x);token(&p,3,32,0x80000000U);token(&p,3,32,0x3f800000U);}
 token(&p,0,1,0);MissionWaypointReceive(&p);assert(p.read==p.n);
}
static void keydoor(int adding,int id,U32 x) {
 Packet p={0};token(&p,1,1,1);token(&p,1,1,id);token(&p,0,1,adding);
 if(adding){token(&p,3,32,x);token(&p,3,32,0x80000000U);token(&p,3,32,0x7fc01234U);}
 MissionKeydoorReceive(&p);assert(p.read==p.n);
}
int main(int argc,char **argv) {
 int mode=atoi(argv[1]),before_requests,before_uid;Destination before[4];
 (void)argc;
 if(mode!=7){waypoint(1,1,0xffffffffU,0x7f800000U);waypoint(1,31,17,0xff800000U);
 keydoor(1,1,0x3f800000U);keydoor(1,31,0x40000000U);assert(requests==6);}
 if(mode==1){waypoint(1,1,31,0x40400000U);keydoor(1,1,0x40800000U);assert(eaSize(&missionDest)==2 && eaSize(&keydoorDest)==2);}
 if(mode==2)waypoint(0,1,0,0);
 if(mode==3){waypoint(0,1,0,0);waypoint(0,31,0,0);}
 if(mode==4)keydoor(0,31,0);
 if(mode==5){waypoint(0,99,0,0);keydoor(0,99,0);}
 if(mode==6){missionDest[0]->uid=999;missionDest[0]->map_location[0]=42;missionDest[0]->destEntity=(void *)1;}
 if(mode==8){have_player=1;waypoint(1,1,17,0x3f800000U);waypoint(1,31,17,0x40000000U);assert(waypointDest.id==401);waypoint(0,1,0,0);assert(waypointDest.id==0);}
 if(mode==9){memset(missionDest[0]->name,'x',256);}
 if(mode==10){memset(missionDest[0]->mapName,'x',512);}
 if(mode==11)array(missionDest)->n=8193;
 if(mode==12)array(missionDest)->n=-1;
 if(mode==13)used=CAPACITY-2;
 if(mode==14){free(missionDest[0]);missionDest[0]=NULL;}
 if(mode==15){memset(missionDest[0]->name,'x',255);missionDest[0]->name[255]=0;}
 if(mode==16){for(int i=2;i<8192;++i)eaPush(&missionDest,NULL);}
 before_requests=requests;before_uid=destUID;
 if(mode<9 || mode==15){for(int i=0;i<eaSize(&missionDest);++i)memcpy(&before[i],missionDest[i],sizeof(Destination));for(int i=0;i<eaSize(&keydoorDest);++i)memcpy(&before[2+i],keydoorDest[i],sizeof(Destination));}
 out("{\"waypoints\":");mission_destination_state(missionDest);out(",\"keydoors\":");mission_destination_state(keydoorDest);out("}");
 assert(requests==before_requests && destUID==before_uid);
 if(mode<9 || mode==15){for(int i=0;i<eaSize(&missionDest);++i)assert(!memcmp(&before[i],missionDest[i],sizeof(Destination)));for(int i=0;i<eaSize(&keydoorDest);++i)assert(!memcmp(&before[2+i],keydoorDest[i],sizeof(Destination)));}
 puts(buffer);MissionClearAll();assert(!missionDest && !keydoorDest);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p/'test.c').write_text(code)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                        '-fno-omit-frame-pointer', str(p/'test.c'), '-o', str(p/'test')], check=True)
        results = [subprocess.run([str(p/'test'), str(i)], capture_output=True, text=True, timeout=15)
                   for i in range(17)]
        for i, r in enumerate(results):
            assert r.returncode == (3 if 9 <= i <= 13 else 0), (i, r.returncode, r.stderr)
        values = {i: json.loads(r.stdout) for i, r in enumerate(results) if r.returncode == 0}
        first = values[0]['waypoints'][0]
        assert [d['id'] for d in values[0]['waypoints']] == [401,431]
        assert first['creation_time'] == 0xffffffff
        assert first['position_f32_bits'] == first['original_position_f32_bits'] == [0x7f800000,0x80000000,0x3f800000]
        assert first['color'] == 0xffffffff and first['background_color'] == 0xff0000ff
        assert first['map'] == 'maps/Atlas' and first['name'] == ''
        assert first['icon_name'] == 'map_enticon_mission_a.tga'
        assert first['show_waypoint'] == 0 and first['nav_on'] == 1
        assert [d['nav_on'] for d in values[0]['keydoors']] == [0,1]
        assert values[0]['keydoors'][1]['position_f32_bits'][2] == 0x7fc01234
        assert values[1]['waypoints'][0]['creation_time'] == 31
        assert values[1]['waypoints'][0]['position_f32_bits'][0] == 0x40400000
        assert [d['nav_on'] for d in values[1]['keydoors']] == [1,0]
        assert [d['id'] for d in values[2]['waypoints']] == [431]
        assert values[3]['waypoints'] == []
        assert [d['nav_on'] for d in values[4]['keydoors']] == [0,0]
        assert values[5] == values[6] == values[0]
        assert values[7] == dict(waypoints=[],keydoors=[])
        assert [d['id'] for d in values[8]['waypoints']] == [431]
        assert values[14]['waypoints'][0] is None
        assert values[15]['waypoints'][0]['name'] == 'x'*255
        assert len(values[16]['waypoints']) == 8192 and all(d is None for d in values[16]['waypoints'][2:])
    print('Mission/keydoor actual receivers and writer: 17 ASan/UBSan cases pass; exact typed reads, create/replace/delete/disable, original closest selection, ordered IDs/times/raw F32 bits, nulls, bounds, nonmutation and local-cache exclusion. Host packet/earray/texture/network fixtures do not establish native ABI or complete UI lifecycle.')


if __name__ == '__main__':
    main()
