#!/usr/bin/env python3
"""Exercise actual badge snapshot formatting, including final array entries."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    badges = source[source.index('static void player_badges('):source.index('static void fixed_string(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 1048576
#define BADGE_ENT_MAX_BADGES 4096
#define BADGE_ENT_RECENT_BADGES 50
#define MAX_BADGE_MONITOR_ENTRIES 10
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct {
    unsigned aiBadges[BADGE_ENT_MAX_BADGES];
    struct { int idx; unsigned timeAwarded; } recentBadges[BADGE_ENT_RECENT_BADGES];
    struct { int iIdx; } badgeMonitorInfo[MAX_BADGE_MONITOR_ENTRIES];
} EntPlayer;
static char *g_pchBadgeFilename[BADGE_ENT_MAX_BADGES];
static char *g_pchBadgeText[BADGE_ENT_MAX_BADGES];
static int g_DebugBadgeDisplayMode;
''' + formatting + badges + r'''
int main(int argc, char **argv) {
    int mode = argc > 1 ? atoi(argv[1]) : 0;
    EntPlayer p = {0}, before;
    p.aiBadges[0] = 1; p.aiBadges[4095] = 0xffffffffU;
    p.recentBadges[49].idx = 31; p.recentBadges[49].timeAwarded = mode == 1 ? 32 : 31;
    p.badgeMonitorInfo[9].iIdx = 4095;
    g_DebugBadgeDisplayMode = 2;
    g_pchBadgeFilename[4095] = "badge\"\\file";
    g_pchBadgeText[4095] = mode == 2 ? "Other localized text" : "Localized text";
    before = p;
    out("{\"player\":"); player_badges(&p);
    out(",\"client\":"); badge_client_state(); out("}");
    check(!memcmp(&p, &before, sizeof(p)));
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
                                  text=True, timeout=15) for i in (0, 1, 2, 0)]
        assert all(r.returncode == 0 for r in results), [(r.returncode, r.stderr) for r in results]
        assert results[0].stdout == results[2].stdout == results[3].stdout
        d = json.loads(results[0].stdout)
        assert d['player']['states'] == [1] + [0] * 4094 + [0xffffffff]
        assert d['player']['recent'] == [dict(index=0, time_awarded=0)] * 49 + [dict(index=31, time_awarded=31)]
        assert d['player']['monitor'] == [0] * 9 + [4095]
        assert d['client']['debug_display_mode'] == 2
        assert d['client']['filenames'] == [None] * 4095 + ['badge"\\file']
        changed = json.loads(results[1].stdout)
        changed['player']['recent'][49]['time_awarded'] = 31
        assert changed == d
    print('badge serializer: 4096 statuses/filenames, 50 wire-timestamp histories, 10 monitor entries, final slots, mutation sensitivity and localized-text exclusion pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
