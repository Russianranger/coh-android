#!/usr/bin/env python3
"""Exercise the actual bounded world-trace controller with host-only fixtures."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    graphics = args.source / 'Game/src/graphics'
    source = (graphics / 'groupdraw.c').read_text()
    start = source.index('ArmPortWorldTrace armport_world_trace;')
    stop = source.index('\n#else', start)
    controller = source[start:stop]
    program = r'''
#define _POSIX_C_SOURCE 200809L
#define COH_ARMPORT_REFERENCE_I686 1
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "armport_world_trace.h"
#define _snprintf snprintf
typedef struct { void *model; } Def;
typedef struct { Def *def; } DefTracker;
static struct { int mainViewport; } gfx_state;
static struct { int ref_count; DefTracker **refs; } group_info;
static struct { unsigned see_outside, zocclusion; int fog_clip; } group_draw;
static int shell, records;
static int shellMode(void) { return shell; }
static void armportZoneTrace(const char *stage, const char *detail)
{
    unsigned frame = 0;
    assert(!strcmp(stage, "world.draw"));
    assert(strlen(detail) < 512);
    assert(sscanf(detail, "frame=%u", &frame) == 1);
    assert(frame == (records ? (unsigned)records * 600 : 1));
    assert(strstr(detail, "refs=3 roots=2 root_models=1 vis=0 outside=1 zocc=0 fog=0"));
    assert(strstr(detail, "visits=1 editor_skip=0 distance_skip=0 frustum_skip=0 model_calls=1 not_loaded=0 alpha_zero=0 sort_requests=1"));
    ++records;
}
''' + controller + r'''
int main(int argc, char **argv)
{
    int i, on = argc == 2 && !strcmp(argv[1], "on");
    Def defs[2] = {{(void *)1}, {0}};
    DefTracker trackers[3] = {{&defs[0]}, {&defs[1]}, {0}};
    DefTracker *refs[3] = {&trackers[0], &trackers[1], &trackers[2]};
    if (on) setenv("ARMPORT_STDIO_LOG", "fixture", 1);
    else unsetenv("ARMPORT_STDIO_LOG");
    group_info.refs = refs;
    gfx_state.mainViewport = 1;
    group_draw.see_outside = 1;
    for (i = -1; i <= 0; ++i) {
        group_info.ref_count = i;
        armportWorldBegin(); assert(!armport_world_trace.active); armportWorldEnd(0);
    }
    group_info.ref_count = 3;
    shell = 1;
    armportWorldBegin(); assert(!armport_world_trace.active); armportWorldEnd(0);
    shell = 0; gfx_state.mainViewport = 0;
    armportWorldBegin(); assert(!armport_world_trace.active); armportWorldEnd(0);
    gfx_state.mainViewport = 1;
    assert(!records && !armport_world_frames);
    for (i = 1; i <= 5000; ++i) {
        unsigned previous;
        armportWorldBegin();
        assert(!!armport_world_trace.active == (on && (i == 1 || (i <= 4200 && i % 600 == 0))));
        if (armport_world_trace.active) {
            unsigned reason;
            assert(armport_world_trace.frame == (unsigned)i);
            for (reason = 0; reason < 4; ++reason) {
                assert(!armport_world_trace.detail_samples[reason]);
                armport_world_trace.detail_samples[reason] = 4;
            }
        }
        ARMPORT_WORLD_COUNT(visits);
        ARMPORT_WORLD_COUNT(model_calls);
        ARMPORT_WORLD_COUNT(sort_requests);
        armportWorldEnd(0);
        assert(!armport_world_trace.active);
        previous = armport_world_trace.visits;
        ARMPORT_WORLD_COUNT(visits);
        assert(armport_world_trace.visits == previous);
    }
    assert(records == (on ? 8 : 0));
    assert(group_info.ref_count == 3 && group_info.refs == refs);
    printf("world trace %s: records=%d, 5000 frames, visibility inputs unchanged\n", on ? "on" : "off", records);
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_file = root / 'world.c'
        source_file.write_text(program)
        executable = root / 'world'
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-I', str(graphics), str(source_file), '-o', str(executable)], check=True)
        for mode in ('off', 'on'):
            subprocess.run([str(executable), mode], check=True)


if __name__ == '__main__':
    main()
