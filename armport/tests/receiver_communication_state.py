#!/usr/bin/env python3
"""Exercise retained friends/chat writers and the original saved-keybind receiver."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    args=p.parse_args()
    source=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    formatting=source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    fixed=source[source.index('static void fixed_string('):source.index('static void group_members(')]
    writers=source[source.index('static void friends_receive_state('):source.index('static void turnstile_mission_state(')]
    chat=(args.source/'Common/entity/chatSettings.h').read_text()
    constants='\n'.join(re.findall(r'^#define\s+(?:MAX_CHAT_WINDOWS|MAX_CHAT_CHANNELS|MAX_CHAT_TABS|MAX_TAB_NAME_LEN)\s+\d+.*$',chat,re.M))
    chat=chat[chat.index('typedef struct ChatWindowSettings'):chat.index('}ChatSettings;')+len('}ChatSettings;')]
    key=(args.source/'Game/src/UI/uiKeybind.h').read_text()
    key=key[key.index('typedef struct KeyBind\n'):key.index('} KeyBind;')+len('} KeyBind;')]
    friends=(args.source/'Common/entity/friendCommon.h').read_text()
    friends=friends[friends.index('typedef struct Friend'):friends.index('}Friend;')+len('}Friend;')]
    ui=(args.source/'Game/src/UI/uiNet.c').read_text()
    start=ui.index('void keybinds_recieve(')
    receiver=ui[start:ui.index('\n}',start)+2]
    fixture=r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024*1024)
#define BIND_MAX 256
#define MOD_TOTAL 4
#define MAX_FRIENDS 25
#define MAX_CHANNELNAME 21
/* Host fixture word count; native compilation checks actual header layouts. */
#define SYSTEM_CHANNEL_BITFIELD_SIZE 4
#define check(x) do { if (!(x)) _Exit(3); } while(0)
typedef unsigned U32;typedef struct StaticMapInfo StaticMapInfo;
static char buffer[CAPACITY];static size_t used;static int development;
''' + constants + '\n' + chat + '\n' + key + '\n' + friends + r'''
typedef struct {char keyProfile[32];KeyBind *keybinds;ChatSettings chat_settings;int helpChatAdded,chatSendChannel;} EntPlayer;
typedef struct {int friendCount;Friend *friends;EntPlayer *pl;} Entity;
typedef struct {int strings,words;} Packet;
static int isDevelopmentMode(void) {return development;}
static const char *pktGetString(Packet *p) {int i=p->strings++;return i==0?"Default":i==256?"last\"\\\200\n":"command";}
static unsigned pktGetBits(Packet *p,int n) {unsigned i=(unsigned)p->words++;assert(n==32);return i%2?0x80000000U:(0xabcdef00U | ((i/2)&255));}
static void strncpyt(char *to,const char *from,size_t n) {assert(n);strncpy(to,from,n-1);to[n-1]=0;}
''' + formatting + fixed + writers + receiver + r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,i;EntPlayer pl={0},saved;Entity e={MAX_FRIENDS,NULL,&pl};
 Friend friends[MAX_FRIENDS]={{0}},saved_friends[MAX_FRIENDS];KeyBind binds[BIND_MAX]={{0}},saved_binds[BIND_MAX];
 Packet packet={0};unsigned bits=0x80000000U;
 pl.keybinds=binds;e.friends=friends;development=mode==1;
 keybinds_recieve(&packet,pl.keyProfile,binds);assert(packet.strings==257 && packet.words==512);
 pl.helpChatAdded=1;pl.chatSendChannel=-1;pl.chat_settings.userSendChannel=14;pl.chat_settings.options=(int)0x80000000U;pl.chat_settings.primaryChatMinimized=1;
 for(i=0;i<MAX_CHAT_WINDOWS;++i){pl.chat_settings.windows[i].tabListBF=(int)0x80000000U+i;pl.chat_settings.windows[i].selectedtop=i;pl.chat_settings.windows[i].selectedbot=-1;memcpy(&pl.chat_settings.windows[i].divider,&bits,4);}
 for(i=0;i<MAX_CHAT_TABS;++i){ChatTabSettings *t=&pl.chat_settings.tabs[i];snprintf(t->name,sizeof(t->name),"tab%d",i);t->systemChannels[SYSTEM_CHANNEL_BITFIELD_SIZE-1]=0xffffffffU;t->userBF=(int)0x80000000U;t->optionsBF=-1;t->defaultChannel=i;t->defaultType=2;}
 for(i=0;i<MAX_CHAT_CHANNELS;++i){ChatChannelSettings *c=&pl.chat_settings.channels[i];snprintf(c->name,sizeof(c->name),"channel%d",i);c->optionsBF=-1;c->color1=(int)0x80000000U;c->color2=-1;}
 friends[0].dbid=17;friends[0].online=1;friends[0].map_id=31;friends[0].name="Friend\"\\\200";friends[0].mapname="Atlas";friends[0].origin="Magic";friends[0].arch="Blaster";
 friends[24].dbid=31;friends[24].name="Last";
 if(mode==2) pl.keybinds=NULL;
 if(mode==3) e.friendCount=0,e.friends=NULL;
 if(mode==4) e.friendCount=26;
 if(mode==5) e.friendCount=-1;
 if(mode==6) e.friends=NULL;
 if(mode==7) memset(pl.keyProfile,'x',sizeof(pl.keyProfile));
 if(mode==8) memset(pl.chat_settings.tabs[19].name,'x',sizeof(pl.chat_settings.tabs[19].name));
 if(mode==9) memset(pl.chat_settings.channels[14].name,'x',sizeof(pl.chat_settings.channels[14].name));
 if(mode==10) used=CAPACITY-2;
 if(mode==11) {friends[0].send=31;friends[0].static_info=(StaticMapInfo*)&e;strcpy(friends[0].description,"local");binds[255].uID=31;binds[255].pressed[0]=1;binds[255].command[1]="runtime bind";pl.chat_settings.tabs[19].systemBF=-1;}
 if(mode==12) {friends[24].mapname="changed";binds[255].key=17;pl.chat_settings.windows[4].selectedbot=19;pl.chat_settings.tabs[19].systemChannels[3]=17;pl.chat_settings.channels[14].color2=17;}
 if(mode==13) {free(binds[255].command[0]);binds[255].command[0]=NULL;}
 if(mode==14) {static char large[CAPACITY+1];memset(large,'x',CAPACITY);friends[24].name=large;}
 if(mode==15) {memset(pl.keyProfile,'P',31);pl.keyProfile[31]=0;memset(pl.chat_settings.tabs[19].name,'T',18);pl.chat_settings.tabs[19].name[18]=0;memset(pl.chat_settings.channels[14].name,'C',21);pl.chat_settings.channels[14].name[21]=0;}
 if(mode==16) {Friend f=friends[0];friends[0]=friends[24];friends[24]=f;}
 saved=pl;memcpy(saved_friends,friends,sizeof(friends));memcpy(saved_binds,binds,sizeof(binds));
 out("{\"friends\":");friends_receive_state(&e);out(",\"keybinds\":");player_keybind_state(&pl);out(",\"chat\":");player_chat_state(&pl);out("}");
 assert(!memcmp(&saved,&pl,sizeof(pl)) && !memcmp(saved_friends,friends,sizeof(friends)) && !memcmp(saved_binds,binds,sizeof(binds)));
 puts(buffer);for(i=0;i<BIND_MAX;++i)free(binds[i].command[0]);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        p=Path(temporary);(p/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer',str(p/'fixture.c'),'-o',str(p/'fixture')],check=True)
        results=[subprocess.run([str(p/'fixture'),str(i)],capture_output=True,text=True,timeout=15) for i in range(17)]
        for i,r in enumerate(results):
            assert r.returncode==(3 if i in (4,5,6,7,8,9,10,14) else 0),(i,r.returncode,r.stderr)
        values={i:json.loads(r.stdout) for i,r in enumerate(results) if r.returncode==0};d=values[0]
        assert len(d['friends'])==25 and d['friends'][0]==dict(db_id=17,online=1,map_id=31,send_id=0,name='Friend"\\\x80',map_name='Atlas',origin='Magic',**{'class':'Blaster'})
        assert d['friends'][24]['name']=='Last' and d['friends'][1]['name'] is None
        assert d['keybinds']['profile']=='Default' and len(d['keybinds']['bindings'])==256
        assert d['keybinds']['bindings'][255]==dict(key=255,modifier=-2147483648,secondary=0xf00,command='last"\\\x80\n')
        assert values[1]['keybinds']['profile']=='Dev' and values[2]['keybinds']['bindings'] is None and values[3]['friends']==[]
        assert d['chat']['windows'][-1]==dict(tabs=0x80000004,selected_top=4,selected_bottom=-1,divider_f32_bits=[0x80000000])
        assert len(d['chat']['tabs'])==20 and d['chat']['tabs'][-1]==dict(name='tab19',system_channels=[0,0,0,0xffffffff],user_channels=0x80000000,options=0xffffffff,default_channel=19,default_type=2)
        assert len(d['chat']['channels'])==15 and d['chat']['channels'][-1]==dict(name='channel14',options=0xffffffff,color1=0x80000000,color2=0xffffffff)
        assert values[11]['friends'][0]['send_id']==31
        values[11]['friends'][0]['send_id']=0
        assert values[11]==d
        changed=values[12];assert changed['friends'][-1]['map_name']=='changed' and changed['keybinds']['bindings'][-1]['key']==17
        assert changed['chat']['windows'][-1]['selected_bottom']==19 and changed['chat']['tabs'][-1]['system_channels'][-1]==17 and changed['chat']['channels'][-1]['color2']==17
        assert values[13]['keybinds']['bindings'][-1]['command'] is None
        assert values[15]['keybinds']['profile']=='P'*31 and values[15]['chat']['tabs'][-1]['name']=='T'*18 and values[15]['chat']['channels'][-1]['name']=='C'*21
        assert values[16]['friends'][0]==d['friends'][-1] and values[16]['friends'][-1]==d['friends'][0]
    print('friends/keybind/chat actual writers: 17 cases pass; original keybind receiver 257 strings/512 words, masked keys/secondary values, Dev profile, all fixed slots/final words, null/order/raw escapes, unsigned masks/colors and F32 bits, source immutability, cache exclusions and literal per-friend packet-order word and count/storage/string/output rejection; ASan/UBSan enabled')


if __name__=='__main__':
    main()
