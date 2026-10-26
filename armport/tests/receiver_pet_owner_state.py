#!/usr/bin/env python3
"""Exercise original pet ownership receiving and actual snapshot without changing IDs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    source=parser.parse_args().source
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    receiver=(source/'Game/src/entity/entrecv.c').read_text()
    reference=(source/'Common/entity/entityRef.c').read_text()
    fixture=r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>
#define CAPACITY 8192
#define check(x) do {if(!(x)) _Exit(3);} while(0)
#define PKT_BITS_TO_REP_SVR_IDX 12
#define SAFE_FREE(p) do {free(p);(p)=NULL;} while(0)
typedef uint32_t U32;typedef int64_t EntityRef;
typedef struct BasePower {const char *pchFullName;} BasePower;
typedef struct Character {const BasePower *ppowCreatedMe;} Character;
typedef struct Entity {int owner,db_id;U32 id;EntityRef erOwner,erCreator;Character *pchar;U32 commandablePet,petVisibility,petDismissable;char *petName,*specialPowerDisplayName;int specialPowerState;} Entity;
static Entity candidates[2];static int entities_max=16,g_PowerDictionary;
static BasePower old_power={"Old.Set.Power"},new_power={"New.Set.Power"};
static Entity *entFromId(unsigned id){return id>=1&&id<=2?&candidates[id-1]:NULL;}
typedef struct Packet {unsigned data[12];int count,cursor;const char *display;} Packet;
static unsigned take(Packet*p){assert(p->cursor<p->count);return p->data[p->cursor++];}
static unsigned pktGetBits(Packet*p,int n){assert(n==1);return take(p);}
static unsigned pktGetBitsPack(Packet*p,int n){assert(n==1||n==12);return take(p);}
static const BasePower *basepower_Receive(Packet*p,void*d,Entity*e){(void)d;(void)e;return take(p)?&new_power:NULL;}
static const char *pktGetIfSetString(Packet*p){return p->display;}
/* Name decoding is separately scoped; this dependency consumes one fixture word. */
static void entReceivePetName(Packet*p,Entity*e,bool oo){(void)e;(void)oo;(void)take(p);}
static char buffer[CAPACITY];static size_t used;
'''
    fixture+=reference[reference.index('typedef union'):reference.index('/**********************************************************************func*')]
    fixture+=function(reference,'EntityRef erGetRef(')
    fixture+=function(receiver,'static int entReceivePetInfo(')
    fixture+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    fixture+=function(state,'static void base_power(')+function(state,'static void entity_pet_owner_state(')
    fixture+=r'''
int main(int argc,char**argv){
 int mode=argc>1?atoi(argv[1]):0;Character character={&old_power},saved_character;Entity e={0},saved;
 Packet p={{1,1,2,1,1,1,1,1,3,0},10,0,""};
 candidates[0]=(Entity){.owner=1,.db_id=42,.id=99};candidates[1]=(Entity){.owner=2,.db_id=0,.id=0xf1234567};
 e.pchar=&character;e.erOwner=7;e.erCreator=8;e.specialPowerDisplayName=strdup("old");assert(e.specialPowerDisplayName);
 if(mode==2||mode==3)p=(Packet){{0},1,0,""};
 if(mode==4)p.data[1]=p.data[2]=0;
 if(mode==5)p=(Packet){{1,1,2,0,1,1,1,3,0},9,0,""};
 if(mode==6)p.data[4]=0;
 assert(entReceivePetInfo(&p,&e,mode==1||mode==3)==1);assert(p.cursor==p.count);
 if(mode==7)e.pchar=NULL;
 if(mode==8)e.erOwner=(EntityRef)UINT64_MAX,e.erCreator=(EntityRef)UINT64_C(0x8000000000000000);
 if(mode==9)used=CAPACITY-1;
 saved=e;saved_character=character;entity_pet_owner_state(&e);
 assert(!memcmp(&e,&saved,sizeof(e))&&!memcmp(&character,&saved_character,sizeof(character)));puts(buffer);
 SAFE_FREE(e.specialPowerDisplayName);SAFE_FREE(e.petName);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);(root/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(root/'fixture.c'),'-o',str(root/'fixture')],check=True)
        for mode in range(10):
            r=subprocess.run([str(root/'fixture'),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if mode==9 else 0),(mode,r.returncode,r.stderr)
            if mode==9:continue
            v=json.loads(r.stdout)
            owner,creator=[1,0x8000002a],[2,0x71234567]
            if mode in (1,4):owner,creator=[7,0],[8,0]
            if mode in (2,3):owner=creator=[0,0]
            if mode==8:owner,creator=[0xffffffff,0xffffffff],[0,0x80000000]
            power='Old.Set.Power' if mode in (1,2,3,5) else None if mode in (6,7) else 'New.Set.Power'
            assert v==dict(owner_ref_words=owner,creator_ref_words=creator,created_by_power=power),(mode,v)
    print('pet ownership: 10 ASan/UBSan cases; original receiver and reference packing, current/stale/non-pet/missing-ID/no-power paths, null character, full-width literal references, immutability and output bounds; packet/power/name dependencies substituted; display-string nonempty paths not qualified')


if __name__=='__main__':main()
