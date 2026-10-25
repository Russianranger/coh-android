#!/usr/bin/env python3
"""Exercise the actual dynamic-group/sky snapshot writer under sanitizers."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    world = source[source.index('static void world_receive_state('):source.index('static void story_clues(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 1048576
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { unsigned char hp:7; unsigned char repair:1; } DynGroupStatus;
static DynGroupStatus *dyn_group_status;
static int dyn_group_count;
static struct { int skyFade1, skyFade2; float skyFadeWeight; } game_state;
''' + formatting + world + r'''
int main(int argc, char **argv) {
    int mode = argc > 1 ? atoi(argv[1]) : 0;
    DynGroupStatus values[] = {{0,0},{127,1},{31,0}}, before[3];
    unsigned bits = mode == 1 ? 0x80000000U : 0x7fc01234U;
    dyn_group_count = 3; dyn_group_status = values;
    game_state.skyFade1 = -1; game_state.skyFade2 = 31;
    memcpy(&game_state.skyFadeWeight, &bits, 4);
    if (mode == 2) values[2].repair = 1;
    if (mode == 3) dyn_group_status = 0, dyn_group_count = 0;
    if (mode == 4) dyn_group_status = 0;
    if (mode == 5) dyn_group_count = -1;
    if (mode == 6) dyn_group_count = 1048577;
    memcpy(before, values, sizeof(values));
    world_receive_state();
    check(!memcmp(before, values, sizeof(values)));
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
                                  text=True, timeout=15) for i in range(7)]
        for i in range(4):
            assert results[i].returncode == 0, (i, results[i].stderr)
        for i in range(4, 7):
            assert results[i].returncode == 3, (i, results[i].stderr)
        d = json.loads(results[0].stdout)
        assert d == dict(dynamic_groups=[dict(hp=0, repair=0), dict(hp=127, repair=1),
                                        dict(hp=31, repair=0)],
                         sky1=-1, sky2=31, sky_weight_f32_bits=[0x7fc01234])
        changed = json.loads(results[1].stdout)
        assert changed['sky_weight_f32_bits'] == [0x80000000]
        changed['sky_weight_f32_bits'] = [0x7fc01234]
        assert changed == d
        changed = json.loads(results[2].stdout)
        assert changed['dynamic_groups'][2]['repair'] == 1
        changed['dynamic_groups'][2]['repair'] = 0
        assert changed == d
        assert json.loads(results[3].stdout)['dynamic_groups'] == []
    print('world serializer: individual hp/repair fields, original order, raw NaN/negative-zero sky weights, null-empty state and invalid count/storage rejection pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
