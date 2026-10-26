#!/usr/bin/env python3
"""Check actual scalar/string metadata observations, not native ABI or decode."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    writer = source[source.index('static void entity_receive_metadata('):source.index('static void visited_map_state(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 8192
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct {
 struct {int mode;} state;
 int bitfieldVisionPhases,exclusiveVisionPhase,shouldIConYellow,pvpClientZoneTimer;
 int taskforce_id,onFlashback,npcIndex,gender,name_gender;
 const char *costumeWorldGroup,*aiAnimList,*petName,*specialPowerDisplayName;
 int petVisibility,specialPowerState;
 unsigned noDrawOnClient:1,showOnMap:1,notSelectable:1,contactOrPnpc:1;
 unsigned contactArchitect:1,alwaysCon:1,seeThroughWalls:1,commandablePet:1,petDismissable:1;
 unsigned long pvpUpdateTime;
} Entity;
''' + formatting + writer + r'''
int main(int argc, char **argv) {
 int mode=argc>1?atoi(argv[1]):0;
 Entity e={0},before;
 e.state.mode=-1;e.bitfieldVisionPhases=(int)0x80000000U;
 e.exclusiveVisionPhase=-7;e.shouldIConYellow=1;e.pvpClientZoneTimer=31;
 e.taskforce_id=17;e.onFlashback=1;e.npcIndex=39;e.gender=2;e.name_gender=3;
 e.costumeWorldGroup="Group\"\n\377";e.aiAnimList="Anim";e.petName="Pet";e.specialPowerDisplayName="Power";
 e.petVisibility=2;e.specialPowerState=-1;e.pvpUpdateTime=123;
 e.noDrawOnClient=e.showOnMap=e.notSelectable=e.contactOrPnpc=e.contactArchitect=1;
 e.alwaysCon=e.seeThroughWalls=e.commandablePet=e.petDismissable=1;
 if(mode==1) e.costumeWorldGroup=e.aiAnimList=e.petName=e.specialPowerDisplayName=NULL;
 if(mode==2) e.pvpUpdateTime=999;
 if(mode==3) used=CAPACITY-2;
 if(mode==4) e.state.mode=17;
 if(mode==5) e.bitfieldVisionPhases=31;
 if(mode==6) e.pvpClientZoneTimer=17;
 if(mode==7) e.noDrawOnClient=0;
 if(mode==8) e.showOnMap=0;
 if(mode==9) e.notSelectable=0;
 if(mode==10) e.contactOrPnpc=0;
 if(mode==11) e.contactArchitect=0;
 if(mode==12) e.alwaysCon=0;
 if(mode==13) e.seeThroughWalls=0;
 if(mode==14) e.commandablePet=0;
 if(mode==15) e.petDismissable=0;
 if(mode==16) e.petVisibility=0;
 if(mode==17) e.specialPowerState=17;
 if(mode==18) e.petName="Changed";
 before=e;entity_receive_metadata(&e);check(!memcmp(&before,&e,sizeof(e)));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(root / 'fixture.c'), '-o', str(root / 'fixture')], check=True)
        results = [subprocess.run([str(root / 'fixture'), str(i)], capture_output=True,
                                  text=True, timeout=15) for i in range(19)]
        for i, result in enumerate(results):
            assert result.returncode == (3 if i == 3 else 0), (i,result.returncode,result.stderr)
        values = {i: json.loads(r.stdout) for i,r in enumerate(results) if r.returncode == 0}
        expected=dict(mode_u32=0xffffffff,vision_phases_u32=0x80000000,exclusive_vision_phase=-7,
            con_yellow=1,pvp_received_seconds=31,taskforce_id=17,on_flashback=1,npc_index=39,
            gender=2,name_gender=3,world_group='Group"\n\xff',ai_anim_list='Anim',
            no_draw=1,show_on_map=1,not_selectable=1,contact_or_pnpc=1,contact_architect=1,
            always_con=1,see_through_walls=1,commandable_pet=1,pet_dismissable=1,pet_visibility=2,
            pet_name='Pet',special_power_display_name='Power',special_power_state=-1)
        assert values[0]==values[2]==expected
        for key in ('world_group','ai_anim_list','pet_name','special_power_display_name'):
            assert values[1][key] is None
        cases=[(4,'mode_u32',17),(5,'vision_phases_u32',31),(6,'pvp_received_seconds',17),
            (7,'no_draw',0),(8,'show_on_map',0),(9,'not_selectable',0),(10,'contact_or_pnpc',0),
            (11,'contact_architect',0),(12,'always_con',0),(13,'see_through_walls',0),
            (14,'commandable_pet',0),(15,'pet_dismissable',0),(16,'pet_visibility',0),
            (17,'special_power_state',17),(18,'pet_name','Changed')]
        for mode,key,value in cases:
            assert values[mode][key]==value
            values[mode][key]=expected[key]
            assert values[mode]==expected
    print('entity metadata writer: literal mode/vision bits, scalar identities, nullable names, individual flags/pet fields, received PvP seconds, local-clock exclusion, per-field mutations, source immutability and output bounds pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
