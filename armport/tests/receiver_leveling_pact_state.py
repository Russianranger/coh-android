#!/usr/bin/env python3
"""Exercise original leveling-pact receive semantics and retained roster output."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);source=p.parse_args().source
    header=(source/'Common/entity/teamCommon.h').read_text()
    receiver=(source/'Game/src/entity/entrecv.c').read_text()
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    members=header[header.index('typedef struct TeamMembers'):header.index('} TeamMembers;')+len('} TeamMembers;')]
    pact=header[header.index('typedef struct LevelingPact'):header.index('} LevelingPact;')+len('} LevelingPact;')]
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
#define FALSE 0
#define TRUE 1
typedef unsigned U32;
'''+re.search(r'typedef char MemberName\[\d+\];',header).group(0)+'\n'+re.search(r'^#define MAX_LEVELINGPACT_MEMBERS\s+\d+',header,re.M).group(0)+'\n'+members+pact+r'''
typedef struct Entity {int levelingpact_id;LevelingPact *levelingpact;void *pchar;char name[64];} Entity;
static int updates,lookup_present=1;static Entity known;
static void levelingpactListUiUpdate(void){++updates;}
static LevelingPact *createLevelingpact(void){return calloc(1,sizeof(LevelingPact));}
static void destroyLevelingpact(LevelingPact*p){if(!p)return;free(p->members.ids);free(p->members.names);free(p->members.onMapserver);free(p->members.mapIds);free(p);}
static Entity *entFromDbId(int id){assert(id==102);return lookup_present?&known:NULL;}
typedef struct Packet{unsigned numbers[12];int count,cursor;char *name;int string_reads;}Packet;
static unsigned take(Packet*p){assert(p->cursor<p->count);return p->numbers[p->cursor++];}
static unsigned pktGetBits(Packet*p,int n){assert(n==1);return take(p);}
static unsigned pktGetBitsAuto(Packet*p){return take(p);}
static char *pktGetString(Packet*p){++p->string_reads;return p->name;}
static char buffer[CAPACITY];static size_t used;
'''
    fixture+=function(receiver,'static int entReceiveLevelingpactInfo(')
    fixture+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for sig in ('static void fixed_string(','static void group_members(','static void leveling_pact_state('):fixture+=function(state,sig)
    fixture+=r'''
int main(int argc,char **argv){
 int mode=argc>1?atoi(argv[1]):0,ui_before;Entity e={0},saved;LevelingPact old;int ids[2],onmap[2];MemberName names[2];
 Packet packet={{1,55,2,101,1,102,0},7,0,"Remote \"member\"",0};
 e.pchar=&e;strcpy(known.name,"Local member");
 assert(entReceiveLevelingpactInfo(&packet,&e,false)==1&&packet.cursor==7&&packet.string_reads==1);
 assert(e.levelingpact_id==55&&updates==1);packet=(Packet){{1,77,1,102,0},5,0,NULL,0};
 if(mode==1)packet=(Packet){{0},1,0,NULL,0};
 if(mode==2||mode==3)packet=(Packet){{1,0},2,0,NULL,0};
 if(mode==4||mode==5)packet=(Packet){{1,77,0},3,0,NULL,0};
 if(mode==5)e.pchar=NULL;
 if(mode==6)lookup_present=0;
 if(mode!=0)entReceiveLevelingpactInfo(&packet,&e,mode==3||mode==4);
 if(mode!=0)assert(packet.cursor==packet.count&&packet.string_reads==0);
 if(mode==7)e.levelingpact->members.count=3;
 if(mode==8)memset(e.levelingpact->members.names[0],'x',64);
 if(mode==9){free(e.levelingpact->members.ids);e.levelingpact->members.ids=NULL;}
 if(mode==10)used=CAPACITY-1;
 if(mode==11){destroyLevelingpact(e.levelingpact);e.levelingpact=NULL;}
 if(mode==12)e.levelingpact->count=99; /* independently retained, not silently repaired */
 saved=e;ui_before=updates;
 if(e.levelingpact){old=*e.levelingpact;memcpy(names,e.levelingpact->members.names,sizeof(names));memcpy(onmap,e.levelingpact->members.onMapserver,sizeof(onmap));if(e.levelingpact->members.ids)memcpy(ids,e.levelingpact->members.ids,sizeof(ids));}
 leveling_pact_state(&e);assert(!memcmp(&e,&saved,sizeof(e))&&ui_before==updates);
 if(e.levelingpact){assert(!memcmp(&old,e.levelingpact,sizeof(old))&&!memcmp(names,e.levelingpact->members.names,sizeof(names))&&!memcmp(onmap,e.levelingpact->members.onMapserver,sizeof(onmap))&&!memcmp(ids,e.levelingpact->members.ids,sizeof(ids)));}
 puts(buffer);destroyLevelingpact(e.levelingpact);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp);(path/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'fixture.c'),'-o',str(path/'fixture')],check=True)
        values={}
        for mode in range(13):
            r=subprocess.run([str(path/'fixture'),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if mode in (7,8,9,10) else 0),(mode,r.returncode,r.stderr)
            if r.returncode==0:values[mode]=json.loads(r.stdout)
        roster=dict(leader=0,members=[dict(db_id=101,on_mapserver=0,name='Remote "member"'),dict(db_id=102,on_mapserver=1,name='Local member')])
        original=dict(id=55,pact=dict(count=2,roster=roster))
        assert values[0]==values[1]==values[4]==values[5]==original
        assert values[2]==dict(id=0,pact=None)
        assert values[3]==dict(id=55,pact=None) # original destroys stale zero-ID pact but retains ID
        assert values[6]==dict(id=77,pact=dict(count=1,roster=dict(leader=0,members=[dict(db_id=102,on_mapserver=1,name='Remote "member"')])))
        assert values[11]==dict(id=77,pact=None)
        assert values[12]['pact']['count']==99 and len(values[12]['pact']['roster']['members'])==1
    print('leveling-pact original receiver/actual writer: 13 ASan/UBSan cases pass; new/update/absent/zero/stale/no-character, local name lookup and retained tails, null pact, independent counts, source immutability and bounds; stale positive member bodies are not qualified; allocator/UI dependencies substituted')


if __name__=='__main__':main()
