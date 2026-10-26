#!/usr/bin/env python3
"""Exercise actual group snapshot writer with bounded native-shaped storage."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    groups = source[source.index('static void fixed_string('):source.index('static void world_receive_state(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 1048576
#define MAX_TEAM_MEMBERS 8
#define MAX_LEAGUE_MEMBERS 48
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef char MemberName[64];
typedef char MapName[256];
typedef struct { int leader, count, *ids, *onMapserver; MemberName *names; } TeamMembers;
typedef struct { TeamMembers members; int team_level, team_mentor, activePlayerDbid; } Teamup;
typedef struct { TeamMembers members; int teamLeaderIDs[48], lockStatus[48]; } League;
typedef struct { int teamup_id, league_id; Teamup *teamup; League *league; } Entity;
static MapName teamMapNames[8], leagueMapNames[48];
''' + formatting + groups + r'''
int main(int argc, char **argv) {
    int mode = argc > 1 ? atoi(argv[1]) : 0, i;
    int ids[48], onmap[48]; MemberName names[48];
    Teamup t = {0}; League l = {0}; Entity e = {31, 93, &t, &l}, before;
    for (i = 0; i < 48; ++i) {
        ids[i] = i + 100; onmap[i] = i % 2;
        memset(names[i], 'A' + i % 26, 63); names[i][63] = 0;
        l.teamLeaderIDs[i] = i / 8 + 100; l.lockStatus[i] = i % 3;
    }
    t.members = (TeamMembers){101, 8, ids, onmap, names};
    l.members = (TeamMembers){102, 48, ids, onmap, names};
    t.team_level = 50; t.team_mentor = 123; t.activePlayerDbid = 147;
    strcpy(teamMapNames[7], "Atlas\"Park");
    memset(leagueMapNames[47], 'Z', 255); leagueMapNames[47][255] = 0;
    if (mode == 1) l.lockStatus[47] = 31;
    if (mode == 2) e.teamup = 0, e.league = 0;
    if (mode == 3) t.members.count = 9;
    if (mode == 4) l.members.count = -1;
    if (mode == 5) l.members.ids = 0;
    if (mode == 6) memset(names[47], 'x', 64);
    if (mode == 7) memset(leagueMapNames[47], 'x', 256);
    if (mode == 8) t.members = (TeamMembers){31, 0, 0, 0, 0};
    if (mode == 9) l.members.count = 49;
    before = e;
    out("{\"entity\":"); entity_groups(&e);
    out(",\"map_names\":"); group_map_names(); out("}");
    check(!memcmp(&before, &e, sizeof(e)));
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
                                  text=True, timeout=15) for i in range(10)]
        for i in (0, 1, 2, 8):
            assert results[i].returncode == 0, (i, results[i].stderr)
        for i in (3, 4, 5, 6, 7, 9):
            assert results[i].returncode == 3, (i, results[i].returncode, results[i].stderr)
        d = json.loads(results[0].stdout)
        t, l = d['entity']['team'], d['entity']['league']
        assert len(t['roster']['members']) == 8 and len(l['roster']['members']) == 48
        assert t['roster']['members'][7] == dict(db_id=107, on_mapserver=1, name='H' * 63)
        assert l['roster']['members'][47] == dict(db_id=147, on_mapserver=1, name='V' * 63)
        assert l['teams'][47] == dict(leader_db_id=105, lock_status=2)
        assert (t['level'], t['mentor'], t['active_player_db_id']) == (50, 123, 147)
        assert d['map_names']['team'] == [''] * 7 + ['Atlas"Park']
        assert d['map_names']['league'] == [''] * 47 + ['Z' * 255]
        changed = json.loads(results[1].stdout)
        changed['entity']['league']['teams'][47]['lock_status'] = 2
        assert changed == d
        absent = json.loads(results[2].stdout)
        assert absent['entity'] == dict(team_id=31, league_id=93, team=None, league=None)
        assert json.loads(results[8].stdout)['entity']['team']['roster'] == dict(leader=31, members=[])
    print('group serializer: active 8/48 member rosters, retained map names, maximum strings, null/empty groups, mutation sensitivity and corrupt count/pointer/string rejection pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
