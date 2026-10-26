#!/usr/bin/env python3
"""Exercise the original target receiver/reference packing and actual snapshot."""
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
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    receiver = (source / 'Game/src/entity/entrecv.c').read_text()
    reference = (source / 'Common/entity/entityRef.c').read_text()
    fixture = r'''
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
typedef uint32_t U32;typedef int64_t EntityRef;
typedef struct Character {EntityRef erTargetInstantaneous,erAssist;} Character;
typedef struct Entity {int owner,svr_idx,db_id,confuseRand;U32 id;Character *pchar;} Entity;
static int entities_max=16;
static Entity candidates[3],*current_target;
static EntityRef g_erTaunter,**g_pperPlacators;
static int gSelectedDBID;static char gSelectedHandle[64];
static int placator_count,forced_count=-1,random_calls;
static int fixture_size(EntityRef ***array) {return forced_count>=0?forced_count:!*array?0:placator_count;}
#define eaSize(p) fixture_size(p)
static void eaDestroy(EntityRef ***array) {free(*array);*array=NULL;placator_count=0;}
static void eaPush(EntityRef ***array,EntityRef *value) {*array=realloc(*array,sizeof(EntityRef*)*(placator_count+1));assert(*array);(*array)[placator_count++]=value;}
static Entity *validEntFromId(int id) {return id>=1&&id<=3?&candidates[id-1]:NULL;}
static int fixture_rand(void) {++random_calls;return 731;}
#define rand fixture_rand
typedef struct Packet {unsigned data[20];int count,cursor;} Packet;
static unsigned take(Packet *p) {assert(p->cursor<p->count);return p->data[p->cursor++];}
static unsigned pktGetBits(Packet *p,int n) {assert(n==1);return take(p);}
static unsigned pktGetBitsPack(Packet *p,int n) {assert(n==2||n==PKT_BITS_TO_REP_SVR_IDX);return take(p);}
static char buffer[CAPACITY];static size_t used;
'''
    fixture += reference[reference.index('typedef union'):reference.index('/**********************************************************************func*')]
    fixture += function(reference, 'EntityRef erGetRef(')
    fixture += function(receiver, 'static int entReceiveTargetUpdate(')
    fixture += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    for signature in ['static void fixed_string(', 'static void character_target_state(', 'static void target_receive_state(']:
        fixture += function(state, signature)
    fixture += r'''
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,i,oo=mode==1||mode==8,self=mode!=2&&mode!=14,has;
 Entity entity={0},saved_entity,saved_candidates[3];Character character={99,98},saved_character;
 Entity *subject=&entity;EntityRef saved_taunter,*saved_refs[4],saved_values[4];int saved_count,saved_dbid,saved_random;char saved_handle[64];
 Packet packet={{1,1,1,1,2,1,3,0,3,2,0,4},12,0};
 candidates[0]=(Entity){1,11,42,0,101,NULL};
 candidates[1]=(Entity){2,12,0,0,102,NULL};
 candidates[2]=(Entity){3,13,9,0,103,NULL};
 entity.pchar=&character;entity.confuseRand=27;current_target=&candidates[1];gSelectedDBID=87;strcpy(gSelectedHandle,"@prior");g_erTaunter=97;
 {EntityRef *old=malloc(sizeof(*old));*old=96;eaPush(&g_pperPlacators,old);}
 if(mode==3||mode==14)subject=NULL;
 if(mode==4||mode==15)entity.pchar=NULL;
 if(mode==5)packet=(Packet){{0},1,0};
 if(mode==6)packet=(Packet){{1,0,0,0,0,0},6,0};
 if(mode==7||mode==8||mode==15)packet.data[7]=1;
 if(mode==14)packet.data[7]=1; /* self=false makes this safe with NULL subject */
 if(mode==16)packet.data[6]=4;
 has=entReceiveTargetUpdate(&packet,subject,oo,self);
 assert(packet.cursor==packet.count && has==(mode!=5));
 assert(random_calls==((mode==7||mode==8||mode==15)?1:0));
 if(mode==9){free(g_pperPlacators[0]);g_pperPlacators[0]=NULL;current_target=NULL;}
 if(mode==10)forced_count=8193;
 if(mode==11)memset(gSelectedHandle,'x',sizeof(gSelectedHandle));
 if(mode==12)used=CAPACITY-1;
 if(mode==13){U32 value[2]={0xffffffffU,0x80000000U};memcpy(&character.erAssist,value,sizeof(value));}
 saved_entity=entity;saved_character=character;saved_taunter=g_erTaunter;saved_count=placator_count;saved_dbid=gSelectedDBID;saved_random=random_calls;
 memcpy(saved_handle,gSelectedHandle,sizeof(saved_handle));memcpy(saved_candidates,candidates,sizeof(candidates));
 for(i=0;i<placator_count;++i){saved_refs[i]=g_pperPlacators[i];saved_values[i]=g_pperPlacators[i]?*g_pperPlacators[i]:0;}
 out("{\"character\":");if(entity.pchar)character_target_state(entity.pchar);else out("null");out(",\"global\":");target_receive_state();out("}");
 assert(!memcmp(&saved_entity,&entity,sizeof(entity))&&!memcmp(&saved_character,&character,sizeof(character))&&saved_taunter==g_erTaunter&&saved_count==placator_count&&saved_dbid==gSelectedDBID&&saved_random==random_calls);
 assert(!memcmp(saved_handle,gSelectedHandle,sizeof(saved_handle))&&!memcmp(saved_candidates,candidates,sizeof(candidates)));
 for(i=0;i<placator_count;++i){assert(saved_refs[i]==g_pperPlacators[i]&&saved_values[i]==(g_pperPlacators[i]?*g_pperPlacators[i]:0));free(g_pperPlacators[i]);}
 eaDestroy(&g_pperPlacators);puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary)
        (path / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(path/'fixture.c'), '-o', str(path/'fixture')], check=True)
        values = {}
        for i in range(17):
            result = subprocess.run([str(path/'fixture'), str(i)], capture_output=True, text=True, timeout=15)
            assert result.returncode == (3 if i in (10,11,12) else 0), (i, result.returncode, result.stderr)
            if result.returncode == 0:
                values[i] = json.loads(result.stdout)
        target = dict(target_ref_words=[1,0x8000002a], assist_ref_words=[2,102])
        assert values[0]['character'] == target
        baseline = values[0]['global']
        assert baseline == dict(taunter_ref_words=[3,0x80000009], placator_ref_words=[[2,102],[0,0]], selected_dbid=87, selected_handle='@prior', current_target=dict(svr_idx=12,id=102,db_id=0))
        stale = dict(target_ref_words=[99,0],assist_ref_words=[98,0])
        prior = dict(baseline,taunter_ref_words=[97,0],placator_ref_words=[[96,0]])
        for i in (1,3,5,14):
            assert values[i] == {'character':stale,'global':prior}, (i,values[i])
        assert values[2] == {'character':target,'global':prior}
        assert values[4] == {'character':None,'global':prior}
        assert values[6]['character'] == dict(target_ref_words=[0,0],assist_ref_words=[0,0])
        assert values[6]['global'] == dict(prior,taunter_ref_words=[0,0],placator_ref_words=[])
        cleared = dict(selected_dbid=0,selected_handle='',current_target=None)
        assert values[7] == {'character':target,'global':dict(baseline,**cleared)}
        assert values[8] == {'character':stale,'global':dict(prior,**cleared)}
        assert values[15] == {'character':None,'global':dict(prior,**cleared)}
        assert values[9]['global'] == dict(baseline,placator_ref_words=[None,[0,0]],current_target=None)
        assert values[13]['character']['assist_ref_words'] == [0xffffffff,0x80000000]
        assert values[16]['global'] == dict(baseline,taunter_ref_words=[0,0])
    print('target state original receiver/reference packer/actual writers: 17 cases pass; self/other/stale/null/missing updates, literal 64-bit references, ordered/null placators, target clearing including stale packets, all reads consumed, no observer mutation, bounds; random confusion value excluded; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
