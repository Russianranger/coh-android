#!/usr/bin/env python3
"""Check literal entity receive-channel IDs and the original update macro."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from receiver_tray_state import function

FIELDS = '''pkt_id_friendslist pkt_id_seq_move pkt_id_seq_triggermove pkt_id_logout
pkt_id_supergroup pkt_id_costume pkt_id_powerCust pkt_id_xlucency pkt_id_titles
pkt_id_character_stats pkt_id_targetting pkt_id_status_effects pkt_id_buffs
pkt_id_debug_info pkt_id_rare_bits pkt_id_state_mode'''.split()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    source=parser.parse_args().source
    header=(source/'Game/src/entity/entIncludeClient.h').read_text()
    scalar_fields=re.findall(r'^\s*U32\s+(pkt_id_\w+);',header,re.M)
    assert set(scalar_fields)==set(FIELDS)|{'pkt_id_create'}
    declarations='\n'.join(re.search(r'^\s*U32\s+'+field+r';',header,re.M).group(0) for field in FIELDS)
    receiver=(source/'Game/src/entity/entrecv.c').read_text()
    update=re.search(r'^\s*#define UPDATE_PACKET_ID[^\n]+',receiver,re.M).group(0)
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    fixture=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 8192
#define check(x) do {if(!(x)) _Exit(3);} while(0)
typedef unsigned U32;
static char buffer[CAPACITY];static size_t used;
'''
    fixture+='typedef struct Entity {\n'+declarations+'\n} Entity;\n'
    fixture+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    fixture+=function(state,'static void entity_packet_order_state(')
    fixture+=update+r'''
int main(int argc,char **argv){
 int mode=argc>1?atoi(argv[1]):0;Entity e={0},saved;struct Packet{U32 id;} packet={155},*pak=&packet;
'''
    for i,field in enumerate(FIELDS):
        fixture+=f' e.{field}=mode==0?1000U+{i}:mode==1?0:mode==2?1:mode==3||mode==9?31:mode==4?32:mode==5?0xffffffffU:mode==6?100:155;\n'
    fixture+=' if(mode==7)pak->id=31;if(mode==9)pak->id=31;\n if(mode==6||mode==7||mode==9){\n'
    for field in FIELDS:fixture+=f' UPDATE_PACKET_ID(e.{field});\n'
    fixture+=' }\n if(mode==8)used=CAPACITY-1; saved=e;entity_packet_order_state(&e);assert(!memcmp(&e,&saved,sizeof(e)));puts(buffer);return 0;\n}\n'
    with tempfile.TemporaryDirectory() as temporary:
        path=Path(temporary);(path/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'fixture.c'),'-o',str(path/'fixture')],check=True)
        for mode in range(10):
            result=subprocess.run([str(path/'fixture'),str(mode)],capture_output=True,text=True,timeout=15)
            assert result.returncode==(3 if mode==8 else 0),(mode,result.returncode,result.stderr)
            if mode==8:continue
            values=json.loads(result.stdout)
            expected={field:1000+i if mode==0 else {1:0,2:1,3:31,4:32,5:0xffffffff,6:155,7:155,9:31}[mode] for i,field in enumerate(FIELDS)}
            assert values==expected,(mode,values)
    print('literal packet-order writer: 10 ASan/UBSan cases, all 16 scalar fields from original header, original update macro advancing/stale/equal decisions, 0/1/31/32/full-width IDs, source immutability and output bounds; no new canonicalization; structured AttrDef ID maps remain excluded')


if __name__=='__main__':main()
