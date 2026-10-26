#!/usr/bin/env python3
"""Check original entity status receivers and retained-state observations."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from receiver_tray_state import function


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    source=parser.parse_args().source
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    entity=(source/'Game/src/entity/entrecv.c').read_text()
    character=(source/'Game/src/entity/character_net_client.c').read_text()
    header=(source/'Common/entity/entPlayer.h').read_text()
    constant=re.search(r'^#define MAX_AFK_STRING\s+\d+',header,re.M).group(0)
    fixture=r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>
#define CAPACITY 8192
#define check(x) do {if(!(x)) _Exit(3);} while(0)
typedef unsigned U32;typedef float F32;
''' + constant + r'''
typedef struct Entity Entity;
typedef struct Character {char **designerStatuses;Entity *entParent;} Character;
typedef struct EntPlayer {unsigned afk:1;char afk_string[MAX_AFK_STRING];} EntPlayer;
struct Entity {EntPlayer *pl;Character *pchar;U32 ulStatusEffects,bitfieldVisionPhases;int exclusiveVisionPhase;F32 xlucency,logout_timer,curr_xlucency;unsigned logout_bad_connection:1;};
static int status_count,forced_count=-1;
static int fixture_size(char ***array) {return !*array?0:forced_count>=0?forced_count:status_count;}
#define eaSize(p) fixture_size(p)
static void eaClearEx(char ***array,void *unused) {int i;for(i=0;i<status_count;++i)free((*array)[i]);status_count=0;}
static void eaPush(char ***array,char *value) {*array=realloc(*array,sizeof(char*)*(status_count+1));assert(*array);(*array)[status_count++]=value;}
typedef struct Packet {unsigned numbers[12];int count,cursor,string_count,string_cursor;const char *strings[4];} Packet;
static unsigned take(Packet *p) {assert(p->cursor<p->count);return p->numbers[p->cursor++];}
static unsigned pktGetBits(Packet *p,int n) {assert(n==1||n==10);return take(p);}
static unsigned pktGetIfSetBits(Packet *p,int n) {assert(n==8);return take(p);}
static unsigned pktGetIfSetBitsPack(Packet *p,int n) {assert(n==5);return take(p);}
static unsigned pktGetBitsAuto(Packet *p) {return take(p);}
static char *pktGetString(Packet *p) {assert(p->string_cursor<p->string_count);return (char*)p->strings[p->string_cursor++];}
static char buffer[CAPACITY];static size_t used;
''' + state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for signature in ['static void fixed_string(', 'static void entity_status_state(']:
        fixture+=function(state,signature)
    for signature in ['static int entReceiveXlucency(', 'static int entReceiveAFK(', 'static int entReceiveLogoutUpdate(']:
        fixture+=function(entity,signature)
    fixture+=function(character,'void character_ReceiveStatusEffects(')
    fixture+=r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,oo=mode==1;unsigned before_count;
 Entity e={0},saved;EntPlayer player={0},old_player;Character character={0};
 Packet x={{128},1,0,0,0,{0}},afk={{1,1},2,0,1,0,{"away \"now\"\n"}},logout={{1,1,2},3,0,0,0,{0}};
 Packet status={{1023,0x80000000U,99,2},4,0,2,0,{"held","sleep"}};
 e.pl=&player;e.pchar=&character;character.entParent=&e;e.xlucency=1;e.ulStatusEffects=17;e.exclusiveVisionPhase=42;
 eaPush(&character.designerStatuses,strdup("prior"));strcpy(player.afk_string,"previous message");
 if(mode==2) status.numbers[3]=0,status.string_count=0;
 if(mode==3) character.entParent=NULL;
 if(mode==4) afk.numbers[0]=0,afk.count=1,afk.string_count=0;
 if(mode==5) afk.numbers[1]=0,afk.string_count=0;
 if(mode==6) x.numbers[0]=255;
 if(mode==7) x.numbers[0]=0;
 entReceiveXlucency(&x,&e,oo);entReceiveAFK(&afk,&e,oo);entReceiveLogoutUpdate(&logout,&e,oo);
 character_ReceiveStatusEffects(&status,mode==8?NULL:&character,oo);
 assert(x.cursor==x.count && afk.cursor==afk.count && afk.string_cursor==afk.string_count && logout.cursor==logout.count && status.cursor==status.count && status.string_cursor==status.string_count);
 assert(e.exclusiveVisionPhase==42); /* original consumes but does not retain it */
 if(mode==9) e.curr_xlucency=99,e.logout_timer=123;
 if(mode==10) e.pl=NULL,e.pchar=NULL;
 if(mode==11) memset(player.afk_string,'x',sizeof(player.afk_string));
 if(mode==12) forced_count=8193;
 if(mode==13) used=CAPACITY-1;
 if(mode==14) {free(character.designerStatuses[1]);character.designerStatuses[1]=NULL;}
 saved=e;old_player=player;before_count=status_count;
 entity_status_state(&e);
 assert(!memcmp(&saved,&e,sizeof(e)) && !memcmp(&old_player,&player,sizeof(player)) && before_count==status_count);
 puts(buffer);eaClearEx(&character.designerStatuses,NULL);free(character.designerStatuses);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        path=Path(temporary);(path/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'fixture.c'),'-o',str(path/'fixture')],check=True)
        values={}
        for i in range(15):
            result=subprocess.run([str(path/'fixture'),str(i)],capture_output=True,text=True,timeout=15)
            assert result.returncode==(3 if i in (11,12,13) else 0),(i,result.returncode,result.stderr)
            if result.returncode==0:values[i]=json.loads(result.stdout)
        baseline=values[0]
        assert baseline['effects']==1023 and baseline['designer_statuses']==['held','sleep']
        assert baseline['logout_bad_connection']==1 and baseline['afk']==dict(enabled=1,message='away "now"\n')
        assert baseline['translucency_f32_bits']==[0x3efefeff]
        assert values[1]==dict(effects=17,translucency_f32_bits=[0x3f800000],logout_bad_connection=0,afk=dict(enabled=0,message='previous message'),designer_statuses=['prior'])
        assert values[2]['designer_statuses']==[] and values[3]['designer_statuses']==[] and values[3]['effects']==17
        assert values[4]['afk']==dict(enabled=0,message='previous message') and values[5]['afk']==dict(enabled=1,message='previous message')
        assert values[6]['translucency_f32_bits']==[0] and values[7]['translucency_f32_bits']==[0x3f800000]
        assert values[8]['effects']==17 and values[8]['designer_statuses']==['prior']
        assert values[9]==baseline and values[10]['afk'] is None and values[10]['designer_statuses'] is None
        assert values[14]['designer_statuses']==['held',None]
    print('entity status original receivers/actual writer: 15 cases pass; current/stale/null-parent semantics, all reads consumed, translucency bits, AFK retained strings, status list replacement/order/nulls, logout connection flag, ignored exclusive-phase field, local timer exclusion, immutability and bounds; ASan/UBSan enabled')


if __name__=='__main__':
    main()
