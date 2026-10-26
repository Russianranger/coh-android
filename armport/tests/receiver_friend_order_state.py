#!/usr/bin/env python3
"""Original friend receiver/accessor/writer; substitute packet, strings and UI prep."""
import argparse,json,os,subprocess,tempfile
from pathlib import Path
from receiver_tray_state import function


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);root=ap.parse_args().source
    ui=(root/'Game/src/UI/uiNet.c').read_text();state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text();header=(root/'Common/entity/friendCommon.h').read_text()
    receiver=function(ui,'void receiveFriendsList(')
    # Replacing local static with file static must not alter the original body.
    previous=(Path(__file__).resolve().parents[2]/'upstream/ouroboros/Game/src/UI/uiNet.c').read_text()
    old=function(previous,'void receiveFriendsList(')
    assert receiver.replace('last_friend_pak_id','last_pak_id').replace('    int oo_packet = 0;\n','    int oo_packet = 0;\n    static int last_pak_id = 0;\n')==old
    c=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 32768
#define MAX_FRIENDS 25
#define TRUE 1
#define check(x) do{if(!(x))_Exit(3);}while(0)
'''+header[header.index('typedef struct StaticMapInfo'):header.index('}Friend;')+len('}Friend;')]+r'''
typedef struct Entity {int friendCount;Friend*friends;}Entity;
typedef struct CharacterClass{const char*pchName;}CharacterClass;
typedef struct CharacterOrigin{const char*pchName;}CharacterOrigin;
static CharacterClass cc={"Blaster"};static const CharacterClass*ccs[]={&cc};static struct{const CharacterClass**ppClasses;}g_CharacterClasses={ccs};
static CharacterOrigin co={"Magic"};static const CharacterOrigin*cos[]={&co};static struct{const CharacterOrigin**ppOrigins;}g_CharacterOrigins={cos};
typedef struct Packet{unsigned id,v[18];int count,cursor,strings;}Packet;
static unsigned pktGetBitsPack(Packet*p,int n){assert(n==1&&p->cursor<p->count);return p->v[p->cursor++];}
static unsigned pktGetBits(Packet*p,int n){return pktGetBitsPack(p,n);}
static char*pktGetString(Packet*p){return (p->strings++%2)?"Atlas":"Friend";}
static const char*allocAddString(const char*s){return s;}
static void strncpyta(char**to,const char*from,int n){size_t z=strlen(from);assert(z<(size_t)n);free(*to);*to=malloc(z+1);memcpy(*to,from,z+1);}
static int prep_calls;static void friendListPrepareUpdate(void){prep_calls++;}
static int last_friend_pak_id=0;static char buffer[CAPACITY];static size_t used;
'''+function(ui,'unsigned armportReplayFriendPacketId(')+receiver
    c+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]+function(state,'static void friends_receive_state(')
    c+=r'''
static Packet packet(unsigned id,int full,int first,int second){Packet p={.id=id};p.v[p.count++]=full;p.v[p.count++]=2;for(int i=0;i<2;i++){int present=i?second:first;p.v[p.count++]=present;if(present){p.v[p.count++]=17+i;p.v[p.count++]=1;p.v[p.count++]=0;p.v[p.count++]=0;p.v[p.count++]=31;}}return p;}
int main(int argc,char**argv){int mode=argc>1?atoi(argv[1]):0;Friend f[25]={{0}},saved[25];Entity e={0,f};Packet p=packet(31,1,1,1);
 if(mode==6)p=packet(31,1,0,1);
 if(mode==7)p.id=0x80000000U;
 if(mode==8)p.id=0xffffffffU;
 if(mode==9)f[0].send=100;
 if(mode==10){p.v[1]=0;p.count=2;}
 if(mode!=14){receiveFriendsList(&p,mode==5?NULL:&e);assert(p.cursor==p.count&&p.strings==(mode==10?0:mode==6?2:4));}
 if(mode>=1&&mode<=4){p=packet(mode==1?30:mode==2?31:mode==3?1:32,mode==2||mode==3,1,1);p.v[3]=99;receiveFriendsList(&p,&e);assert(p.cursor==p.count&&p.strings==4);assert(f[0].dbid==(mode==4?99:17));}
 assert(prep_calls==(mode==14?0:mode>=1&&mode<=4?2:1));
 if(mode==5)assert(e.friendCount==0);
 if(mode==7||mode==8)assert(e.friendCount==2&&f[0].send==0&&f[0].dbid==0&&f[1].send==0);
 if(mode==9)assert(f[0].send==100&&f[1].send==31&&f[0].dbid==0&&f[1].dbid==0);
 if(mode==11)f[0].send=-1;
 if(mode==12)used=CAPACITY-1;
 if(mode==15)e.friends=NULL,e.friendCount=1;
 memcpy(saved,f,sizeof(f));int count=e.friendCount,order=last_friend_pak_id;
 out("{\"last_id\":%u,\"friends\":",armportReplayFriendPacketId());friends_receive_state(&e);out("}");
 assert(!memcmp(saved,f,sizeof(f))&&e.friendCount==count&&last_friend_pak_id==order);puts(buffer);
 for(int i=0;i<25;i++){free(f[i].name);free(f[i].mapname);}return 0;}
'''
    with tempfile.TemporaryDirectory() as tmp:
        d=Path(tmp);src=d/'fixture.c';src.write_text(c);exe=d/'fixture'
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(src),'-o',str(exe)],check=True)
        for mode in range(16):
            r=subprocess.run([str(exe),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if mode in (12,15) else 0),(mode,r.returncode,r.stderr)
            if r.returncode:continue
            v=json.loads(r.stdout);expected={3:1,4:32,7:0x80000000,8:0xffffffff,14:0}.get(mode,31);assert v['last_id']==expected,(mode,v)
            if mode==11:assert v['friends'][0]['send_id']==0xffffffff
            if mode in (5,10,14):assert v['friends']==[]
            if mode==6:assert v['friends'][0]['send_id']==0 and v['friends'][1]['send_id']==31
    print('friend packet order: 16 ASan/UBSan cases passed; actual original receiver body unchanged except static-variable scope/name, literal accessor and writer, full/partial/stale/equal/lower/high-bit IDs, null entity, absent slots, cumulative out-of-order behavior, exact read consumption, full-width words and snapshot nonmutation/bounds; packet/string/UI dependencies substituted, no ID normalization or native ABI claim')

if __name__=='__main__':main()
