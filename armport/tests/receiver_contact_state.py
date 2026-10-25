#!/usr/bin/env python3
"""Exercise contact snapshots and the actual clock-independent receive observer."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    fixed = source[source.index('static void fixed_string('):source.index('static void group_members(')]
    observer = source[source.index('void armportReplayAlignmentDelay('):source.index('static void super_colors(')]
    contacts = source[source.index('static void contact_states('):source.index('static void entity_supergroup_state(')]
    receiver = (args.source / 'Game/src/storyarc/contactClient.c').read_text()
    start = receiver.index('    for (pointIndex = 0; pointIndex < ALIGNMENT_POINT_MAX_COUNT; pointIndex++)')
    loop = receiver[start:receiver.index('    heroAlignmentPoints_self =', start)]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 1048576
#define ALIGNMENT_POINT_MAX_COUNT 5
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef unsigned U32;
static int active=1;
static struct { unsigned seconds, valid; } alignment_delays[5];
typedef struct { char mapName[512], name[256]; float world_location[4][3]; } Destination;
typedef struct {
    char *name, *locationDescription, *filename, *callOverride, *askAboutOverride, *leaveOverride, *imageOverride;
    int npcNum, handle, taskcontext, tasksubhandle, currentCP, friendCP, confidantCP, completeCP, heistCP;
    unsigned tipType;
    unsigned notifyPlayer:1, hasTask:1, canUseCell:1, hasLocation:1, isNewspaper:1,
        onStoryArc:1, onMiniArc:1, wontInteract:1, metaContact:1;
    unsigned currentOverheadIconState, timeAutoRemokes;
    Destination location; int alliance, universe;
} ContactStatus;
static ContactStatus **contacts, **contactsAccessibleNow;
static unsigned timeWhenCanEarnAlignmentPoint[5], earnedAlignments[5];
static unsigned heroAlignmentPoints_self=0xffffffffU, vigilanteAlignmentPoints_self=31,
    villainAlignmentPoints_self=1, rogueAlignmentPoints_self=0;
static unsigned feed[]={0xffffffffU,1, 0,31, 1,0xffffffffU, 31,100, 0x80000000U,0};
static int consumed;
static unsigned pktGetBitsAuto(int ignored) { (void)ignored; check(consumed<10); return feed[consumed++]; }
static void *addresses[2]; static int counts[2]={3,1};
static int size(const void *array) {
    int i; if (!array) return 0;
    for(i=0;i<2;++i) if(addresses[i]==array) return counts[i];
    exit(4);
}
#define eaSize(p) size(*(p))
''' + formatting + fixed + observer + contacts + r'''
static void receive_delays(U32 now) { int pointIndex, pak=0;
''' + loop + r'''
}
int main(int argc, char **argv) {
    int mode=argc>1?atoi(argv[1]):0,i; U32 now=123456;
    ContactStatus c={0}, before; ContactStatus *known[]={&c,NULL,&c}, *available[]={&c};
    unsigned bits[]={0x80000000,0x7fc01234,0x3f800000};
    c.name="Contact\""; c.locationDescription="place"; c.filename="";
    c.callOverride="Call"; c.leaveOverride="Leave"; c.imageOverride="Image";
    c.npcNum=31; c.handle=1; c.taskcontext=2; c.tasksubhandle=3;
    c.currentCP=5; c.friendCP=10; c.confidantCP=20; c.completeCP=30; c.heistCP=40;
    c.tipType=0xffffffffU; c.notifyPlayer=c.canUseCell=c.hasLocation=c.onStoryArc=c.metaContact=1;
    c.alliance=1; c.universe=2; strcpy(c.location.mapName,"Atlas"); strcpy(c.location.name,"Contact");
    memcpy(c.location.world_location[3],bits,12);
    contacts=known; contactsAccessibleNow=available; addresses[0]=known; addresses[1]=available;
    if(mode==1 || mode==10)active=0;
    if(mode==2)c.currentCP=31;
    if(mode==3)counts[0]=8193;
    if(mode==4)memset(c.location.name,'x',sizeof(c.location.name));
    if(mode==5)contacts=NULL,contactsAccessibleNow=NULL;
    if(mode==6)c.currentOverheadIconState=123,c.timeAutoRemokes=456;
    if(mode==7)feed[8]=32768;
    if(mode==8)now=987654321;
    if(mode==9 || mode==10)armportReplayAlignmentDelay(5,31);
    receive_delays(now);
    check(consumed==10);
    for(i=0;i<5;++i) {
        check(timeWhenCanEarnAlignmentPoint[i]==(U32)(now+feed[2*i]));
        check(earnedAlignments[i]==feed[2*i+1]);
    }
    before=c; contact_receive_state(); check(!memcmp(&before,&c,sizeof(c)));
    puts(buffer); return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(root / 'fixture.c'), '-o', str(root / 'fixture')], check=True)
        results = [subprocess.run([str(root / 'fixture'), str(i)], capture_output=True,
                                  text=True, timeout=15) for i in range(11)]
        for i in (0,1,2,5,6,7,8,10):
            assert results[i].returncode == 0, (i, results[i].stderr)
        for i in (3,4,9):
            assert results[i].returncode == 3, (i, results[i].stderr)
        d = json.loads(results[0].stdout)
        assert d['known'][1] is None and d['known'][0] == d['known'][2] == d['accessible'][0]
        c = d['known'][0]
        assert c['name'] == 'Contact"' and c['filename'] == '' and c['ask_override'] is None
        assert (c['npc'],c['handle'],c['task_context'],c['task_subhandle']) == (31,1,2,3)
        assert [c[k] for k in ('points','friend_points','confidant_points','complete_points','heist_points')] == [5,10,20,30,40]
        assert [c[k] for k in ('notify','can_use_cell','has_location','story_arc','meta_contact')] == [1]*5
        assert [c[k] for k in ('has_task','newspaper','mini_arc','wont_interact')] == [0]*4
        assert c['tip_type'] == 0xffffffff and (c['alliance'],c['universe']) == (1,2)
        assert c['location'] == dict(map='Atlas',name='Contact',received_position_f32_bits=[0x80000000,0x7fc01234,0x3f800000])
        assert d['alignment_delay_seconds'] == [0xffffffff,0,1,31,0x80000000]
        assert d['earned_alignments'] == [1,31,0xffffffff,100,0]
        assert [d[k] for k in ('hero_points','vigilante_points','villain_points','rogue_points')] == [0xffffffff,31,1,0]
        assert json.loads(results[1].stdout)['alignment_delay_seconds'] == [None]*5
        assert results[10].stdout == results[1].stdout
        assert json.loads(results[2].stdout)['known'][2]['points'] == 31
        assert json.loads(results[5].stdout)['known'] == json.loads(results[5].stdout)['accessible'] == []
        assert results[6].stdout == results[8].stdout == results[0].stdout
        assert json.loads(results[7].stdout)['alignment_delay_seconds'][4] == 32768
    print('contact serializer: order/nulls, literal strings/flags/points/location bits; actual receiver '
          'preserves all ten reads and U32 clock-add results; observer captures raw delay, is inert when '
          'off, ignores host clock/UI cache changes and rejects invalid counts/strings/indices; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
