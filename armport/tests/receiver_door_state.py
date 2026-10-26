#!/usr/bin/env python3
"""Execute original door receivers and the actual non-expiring state view."""
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
    native = (source/'Game/src/gameComm/dooranimclient.c').read_text()
    header = (source/'Common/gameComm/dooranimcommon.h').read_text()
    state = (Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    definitions = header[header.index('typedef enum DoorAnimAnimState'):header.index('int DoorAnimMove(')]
    fixture = r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <math.h>
#define CAPACITY 4096
#define check(x) do { if (!(x)) _Exit(3); } while(0)
#define SHOW_GAME 2
#define FADEIN_TIME 15
#define verbose_printf(...) ((void)0)
typedef unsigned U32;
typedef float F32;
typedef float Vec3[3];
''' + definitions + r'''
typedef struct EntPlayer { DoorAnimState *door_anim; } EntPlayer;
typedef struct Entity { EntPlayer *pl; } Entity;
static EntPlayer player_data; static Entity player={&player_data};static int has_player=1;
static Entity *playerPtr(void) { return has_player?&player:NULL; }
static int waiting_for_door,dooranim_animfadeout,dooranim_doorfade=1;
static U32 waiting_for_door_time,last_forced_move_pakid;
enum {DALT_NONE,DALT_WAITINGFORMOVE,DALT_WAITINGFORTEXLOAD} dooranim_loadingtextures;
static F32 dooranim_fadePercent=100,targetPercent=100,startPercent,endTime,curTime;
static struct { int game_mode; } game_state;
static int change_allowed=1,game_mode_calls,timer_reads;
static int okayToChangeGameMode(void) { return change_allowed; }
static void toggle_3d_game_modes(int mode) {game_state.game_mode=mode;++game_mode_calls;}
static int nearf(float a,float b) {return fabsf(a-b)<0.0001f;}
static U32 timerCpuSeconds(void) {++timer_reads;return 1000;}
typedef struct Packet {U32 id;int bit_cursor,float_cursor,string_cursor;int new_location,with_string;} Packet;
static unsigned pktGetBits(Packet *p,int bits) {++p->bit_cursor;assert(bits==1||bits==32);return bits==32?DOORANIM_ORIENT:p->with_string?p->with_string:p->new_location;}
static float pktGetF32(Packet *p) {static const float values[]={1,-2,3,4,5,6,2.75f};assert(p->float_cursor<7);return values[p->float_cursor++];}
static const char *pktGetString(Packet *p) {++p->string_cursor;return "door animation";}
static char buffer[CAPACITY];static size_t used;
'''
    fixture += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for signature in ['void DoorAnimFadeIn(', 'int DoorAnimIsFadedOut(', 'void doneWaitForDoorMode(', 'int waitingForDoor(', 'void armportReplayDoorState(', 'void DoorAnimReceiveStart(', 'void DoorAnimReceiveExit(']:
        fixture += function(native, signature)
    fixture += function(state, 'static void door_animation_state(')
    fixture += function(state, 'static void door_transition_state(')
    fixture += r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,i;
 Packet start={1,0,0,0,0,mode==8?0:1},exit={31,0,0,0,1,0};
 DoorAnimState saved;
 waiting_for_door=1;waiting_for_door_time=0;
 if(mode==1) exit.new_location=0;
 if(mode==2) last_forced_move_pakid=31;
 if(mode==3) last_forced_move_pakid=32;
 if(mode==4) targetPercent=0,dooranim_fadePercent=0;
 if(mode==5) targetPercent=0,dooranim_fadePercent=0,change_allowed=0;
 if(mode==6) dooranim_doorfade=0,exit.new_location=0;
 DoorAnimReceiveStart(&start);assert(start.float_cursor==7 && start.bit_cursor==2 && start.string_cursor==(mode!=8));
 if(mode==9) {player_data.door_anim->finalpos[0]=99;player_data.door_anim->speed=17;}
 if(mode==10) player_data.door_anim->entrypos[2]=33;
 if(mode==11) player_data.door_anim->clientack=1,player_data.door_anim->pastthreshold=1;
 saved=*player_data.door_anim;
 out("{\"before\":");door_animation_state(player_data.door_anim);
 out(",\"before_transition\":");door_transition_state();
 assert(!memcmp(&saved,player_data.door_anim,sizeof(saved)) && waiting_for_door==1 && timer_reads==0);
 if(mode==7) has_player=0;
 DoorAnimReceiveExit(mode==12?NULL:&exit);
 assert(exit.bit_cursor==(mode==12?0:1) && !waiting_for_door);
 assert(game_mode_calls==((mode==5||mode==7)?0:1));
 if(mode!=7) assert(player_data.door_anim==NULL);
 if(mode==13) used=CAPACITY-1;
 out(",\"after\":");door_animation_state(player_data.door_anim);
 out(",\"after_transition\":");door_transition_state();out("}");
 assert(timer_reads==0);
 if(player_data.door_anim) {free(player_data.door_anim->animation);free(player_data.door_anim);}
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        path=Path(temporary);(path/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'fixture.c'),'-lm','-o',str(path/'fixture')],check=True)
        values={}
        for i in range(14):
            result=subprocess.run([str(path/'fixture'),str(i)],capture_output=True,text=True,timeout=15)
            assert result.returncode==(3 if i==13 else 0),(i,result.returncode,result.stderr)
            if result.returncode==0: values[i]=json.loads(result.stdout)
        initial=values[0]['before']
        assert initial['entry_f32_bits']==[0x3f800000,0xc0000000,0x40400000]
        assert initial['target_f32_bits']==[0x40800000,0x40a00000,0x40c00000]
        assert initial['entry_radius']==2 and initial['animation']=='door animation'
        assert values[0]['before_transition']==dict(waiting=1,loading=0,anim_fadeout=1,game_mode=0)
        assert values[0]['after_transition']==dict(waiting=0,loading=1,anim_fadeout=1,game_mode=2)
        for i in (1,2,3,6,12):
            assert values[i]['after'] is None and values[i]['after_transition']==dict(waiting=0,loading=0,anim_fadeout=1,game_mode=2)
        assert values[5]['after_transition']['game_mode']==0
        assert values[7]['after']==initial and values[7]['after_transition']['game_mode']==0
        assert values[8]['before']['animation'] is None
        assert values[9]==values[0]
        assert values[10]['before']['entry_f32_bits'][-1]==0x42040000
        assert values[11]['before']['client_ack']==-1 and values[11]['before']['past_threshold']==-1
    print('door original start/exit receivers and actual snapshot: 14 cases pass; raw retained positions/radius/string, state/null/free transition, packet-order branch without normalization, waiting/loading/game mode, no timeout getter or clock reads, derived-motion exclusion, source immutability and output bounds; ASan/UBSan enabled')


if __name__=='__main__':
    main()
