#!/usr/bin/env python3
"""Exercise the actual nested task-state serializer with sanitizers."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    fixed = source[source.index('static void fixed_string('):source.index('static void group_members(')]
    tasks = source[source.index('static void task_difficulty('):source.index('static void contact_states(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 1048576
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { int levelAdjust, teamSize, alwaysAV, dontReduceBoss; } StoryDifficulty;
typedef struct { int contactType; char mapName[512], name[256]; float world_location[4][3]; } Destination;
typedef struct {
    int ownerDbid, context, subhandle, level, alliance; StoryDifficulty difficulty;
    char description[256], owner[33], state[256], detail[20001], intro[256], filename[256];
    unsigned isComplete:1, isMission:1, hasRunningMission:1, isSGMission:1, hasLocation:1,
        detailInvalid:1, zoneTransfer:1, teleportOnComplete:1, enforceTimeLimit:1,
        isAbandonable:1, isZowie:1;
    Destination location; unsigned timeout, timezero; int timerType; unsigned failOnTimeout, iAskedWhen;
    unsigned zinfo, zseed; int zmap_id; char ztype[128]; int zpoolSize[8]; char zname[128];
    int zIndices[50]; void *pSMFBlock;
} TaskStatus;
typedef struct { int dbid; StoryDifficulty difficulty; TaskStatus **list; } TaskStatusSet;
static TaskStatusSet **teamTaskSets;
static void *addresses[2]; static int counts[2]={3,3};
static int size(const void *array) {
    int i; if (!array) return 0;
    for(i=0;i<2;++i) if(addresses[i]==array) return counts[i];
    exit(4);
}
#define eaSize(p) size(*(p))
''' + formatting + fixed + tasks + r'''
int main(int argc, char **argv) {
    int mode=argc>1?atoi(argv[1]):0, i;
    TaskStatus t={0}, before; TaskStatus *list[]={&t,NULL,&t};
    TaskStatusSet s={0}, set_before; TaskStatusSet *sets[]={NULL,&s,&s};
    unsigned bits[]={0x80000000,0x7fc01234,0x3f800000};
    t.ownerDbid=31; t.context=1; t.subhandle=2; t.level=50; t.alliance=1;
    t.difficulty=(StoryDifficulty){-1,8,1,0};
    strcpy(t.description,"task\n\""); strcpy(t.owner,"owner"); strcpy(t.state,"running");
    memset(t.detail,'D',20000); t.detail[20000]=0;
    strcpy(t.intro,"intro"); strcpy(t.filename,"file");
    t.timeout=0xffffffffU; t.timezero=0x80000000U; t.timerType=-1; t.failOnTimeout=1;
    t.isComplete=t.isMission=t.hasLocation=t.detailInvalid=t.enforceTimeLimit=t.isAbandonable=1;
    t.location.contactType=3; strcpy(t.location.mapName,"Atlas"); strcpy(t.location.name,"Door");
    memcpy(t.location.world_location[3],bits,12);
    t.zinfo=0xffffffffU; t.zseed=31; t.zmap_id=1; strcpy(t.ztype,"A B"); strcpy(t.zname,"Zowie");
    for(i=0;i<8;++i)t.zpoolSize[i]=i-1;
    s.dbid=93; s.difficulty=(StoryDifficulty){4,1,0,1}; s.list=list;
    teamTaskSets=sets; addresses[0]=sets; addresses[1]=list;
    if(mode==1)t.zpoolSize[7]=31;
    if(mode==2)teamTaskSets=NULL;
    if(mode==3)counts[0]=4097;
    if(mode==4)counts[1]=-1;
    if(mode==5)memset(t.owner,'x',sizeof(t.owner));
    if(mode==6)t.iAskedWhen=123456,t.pSMFBlock=(void*)1,t.zIndices[49]=31;
    if(mode==7)t.isZowie=1;
    if(mode==8)t.hasLocation=0;
    if(mode==9)s.list=NULL;
    if(mode==10)memset(t.location.mapName,'x',sizeof(t.location.mapName));
    if(mode==11)t.timezero=31;
    before=t; set_before=s; task_sets();
    check(!memcmp(&before,&t,sizeof(t)) && !memcmp(&set_before,&s,sizeof(s)));
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
                                  text=True, timeout=15) for i in range(12)]
        for i in (0, 1, 2, 6, 7, 8, 9, 11):
            assert results[i].returncode == 0, (i, results[i].stderr)
        for i in (3, 4, 5, 10):
            assert results[i].returncode == 3, (i, results[i].stderr)
        d = json.loads(results[0].stdout)
        assert d[0] is None and d[1] == d[2] and d[1]['dbid'] == 93
        s = d[1]
        assert s['difficulty'] == dict(level_adjust=4, team_size=1, always_av=0, dont_reduce_boss=1)
        t = s['tasks'][0]
        assert s['tasks'][1] is None and s['tasks'][2] == t
        assert t['owner_dbid'] == 31 and t['context'] == 1 and t['subhandle'] == 2
        assert t['description'] == 'task\n"' and t['detail'] == 'D' * 20000
        assert t['difficulty'] == dict(level_adjust=-1, team_size=8, always_av=1, dont_reduce_boss=0)
        assert (t['timeout'], t['timezero'], t['timer_type']) == (0xffffffff, 0x80000000, -1)
        assert [t[n] for n in ('complete','mission','has_location','detail_invalid','enforce_time_limit','abandonable')] == [1]*6
        assert [t[n] for n in ('running_mission','sg_mission','zone_transfer','teleport_on_complete','zowie')] == [0]*5
        assert t['location'] == dict(contact_type=3, map='Atlas', name='Door',
            received_position_f32_bits=[0x80000000,0x7fc01234,0x3f800000])
        assert t['zpool_size'] == list(range(-1,7)) and t['zinfo'] == 0xffffffff
        assert json.loads(results[1].stdout)[2]['tasks'][2]['zpool_size'][7] == 31
        assert json.loads(results[2].stdout) == []
        assert results[6].stdout == results[0].stdout
        for i in (7,8):
            assert json.loads(results[i].stdout)[1]['tasks'][0]['location']['received_position_f32_bits'] is None
        assert json.loads(results[9].stdout)[2]['tasks'] == []
        assert json.loads(results[11].stdout)[1]['tasks'][0]['timezero'] == 31
    print('task serializer: nested order/nulls, retained detail strings, individual flags, received U32 times, '
          'raw ordinary-location bits, zowie fields, mutation sensitivity, local-clock/cache exclusion '
          'and invalid count/string rejection pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
