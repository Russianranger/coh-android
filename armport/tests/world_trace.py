#!/usr/bin/env python3
"""Exercise the actual bounded world-trace controller with host-only fixtures."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    graphics = args.source / 'Game/src/graphics'
    source = (graphics / 'groupdraw.c').read_text()
    start = source.index('ArmPortWorldTrace armport_world_trace;')
    stop = source.index('\n#else', start)
    controller = source[start:stop]
    ui_source = (args.source / 'Game/src/UI/uiWindows.c').read_text()
    compass = (args.source / 'Game/src/UI/uiCompass.c').read_text()
    assert 'if (activeTaskDest.type == ICON_MISSION)' in compass
    assert '&activeTaskDest, 1' in compass and '&waypointDest, 0' in compass
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
typedef struct {int svr_idx,net_ipos[3];float position[3];} Entity;
static Entity player = {17,{100,200,300},{1,2,3}};
static int player_present, player_reads;
static const Entity *playerPtr(void) {++player_reads;return player_present?&player:NULL;}
#define ENTPOS(e) ((e)->position)
static struct {float cammat[4][3],viewmat[4][3];} cam_info;
/* Host stand-ins for native layout; actual read-only window getter below. */
enum { WDW_COMPASS, WDW_MAP, ICON_MISSION = 9 };
typedef struct { int type; char name[256], mapName[512]; } Destination;
static Destination activeTaskDest, waypointDest;
static struct {int mission_map;} game_state;
static struct {struct {int mode;} loc;} winDefs[2];
static int ui_records, expected_task, expected_type, expected_name, expected_map;
static int shell, records, model_records, camera_records;
static int shellMode(void) { return shell; }
static void armportZoneTrace(const char *stage, const char *detail)
{
    unsigned frame = 0;
    if (!strcmp(stage, "world.ui")) {
        int compass_mode,map_mode,mission,task,type,name,map,n=0;
        assert(strlen(detail)<256);
        assert(sscanf(detail,"frame=%u compass_mode=%d map_mode=%d mission_map=%d selected_task=%d selected_type=%d name_present=%d map_present=%d%n",
            &frame,&compass_mode,&map_mode,&mission,&task,&type,&name,&map,&n)==8);
        assert(detail[n]==0);
        assert(frame == (ui_records ? (unsigned)ui_records * 600 : 1));
        assert(compass_mode==winDefs[0].loc.mode && map_mode==winDefs[1].loc.mode);
        assert(mission==game_state.mission_map && task==expected_task && type==expected_type);
        assert(name==expected_name && map==expected_map);
        ++ui_records;return;
    }
    if (!strcmp(stage, "world.camera")) {
        assert(strlen(detail)<1024);
        assert(sscanf(detail,"frame=%u",&frame)==1);
        assert(frame == (camera_records ? (unsigned)camera_records * 600 : 1));
        assert(strstr(detail,"camera=10,20,30 view0=1,2,3 view1=4,5,6 view2=7,8,9 view3=10,11,12"));
        assert(strstr(detail,player_present?"player=1 player_svr_idx=17 player_pos=1,2,3 player_net_ipos=100,200,300":"player=0 player_svr_idx=0 player_pos=0,0,0 player_net_ipos=0,0,0"));
        ++camera_records;return;
    }
    if (!strcmp(stage, "world.models")) {
        unsigned frame=0;
        assert(sscanf(detail,"frame=%u",&frame)==1);
        assert(frame == (model_records ? (unsigned)model_records * 600 : 1));
        assert(strstr(detail,"visits=5 editor_skip=1 distance_skip=1 frustum_skip=1 postchecks=2"));
        ++model_records; return;
    }
    assert(!strcmp(stage, "world.draw"));
    assert(strlen(detail) < 512);
    assert(sscanf(detail, "frame=%u", &frame) == 1);
    assert(frame == (records ? (unsigned)records * 600 : 1));
    assert(strstr(detail, "refs=3 roots=2 root_models=1 vis=0 outside=1 zocc=0 fog=0"));
    assert(strstr(detail, "visits=1 editor_skip=0 distance_skip=0 frustum_skip=0 model_calls=1 not_loaded=0 alpha_zero=0 sort_requests=1"));
    ++records;
}
''' + function(ui_source, 'int window_getMode(') + controller + r'''
int main(int argc, char **argv)
{
    int i, on = argc == 2 && !strcmp(argv[1], "on");
    Def defs[2] = {{(void *)1}, {0}};
    DefTracker trackers[3] = {{&defs[0]}, {&defs[1]}, {0}};
    DefTracker *refs[3] = {&trackers[0], &trackers[1], &trackers[2]};
    unsigned char saved_camera[sizeof(cam_info)],saved_player[sizeof(player)];
    for(i=0;i<12;++i) cam_info.viewmat[i/3][i%3]=(float)(i+1);
    cam_info.cammat[3][0]=10;cam_info.cammat[3][1]=20;cam_info.cammat[3][2]=30;
    memcpy(saved_camera,&cam_info,sizeof(cam_info));memcpy(saved_player,&player,sizeof(player));
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
        Destination saved_task,saved_waypoint;
        unsigned sample = i==1 ? 0 : (unsigned)i/600;
        /* All eight combinations of selection/name/map, including completely
         * unterminated arrays: the diagnostic may inspect only their first byte. */
        expected_task=!!(sample&4);expected_name=!!(sample&2);expected_map=!!(sample&1);
        memset(&activeTaskDest,0,sizeof(activeTaskDest));memset(&waypointDest,0,sizeof(waypointDest));
        activeTaskDest.type=expected_task?ICON_MISSION:-7;waypointDest.type=3;
        expected_type=expected_task?ICON_MISSION:3;
        memset(activeTaskDest.name,expected_task?expected_name:!expected_name,sizeof(activeTaskDest.name));
        memset(activeTaskDest.mapName,expected_task?expected_map:!expected_map,sizeof(activeTaskDest.mapName));
        memset(waypointDest.name,expected_task?!expected_name:expected_name,sizeof(waypointDest.name));
        memset(waypointDest.mapName,expected_task?!expected_map:expected_map,sizeof(waypointDest.mapName));
        winDefs[0].loc.mode=(int)sample;winDefs[1].loc.mode=-(int)sample;
        game_state.mission_map=(int)(sample&1);
        memcpy(&saved_task,&activeTaskDest,sizeof(saved_task));memcpy(&saved_waypoint,&waypointDest,sizeof(saved_waypoint));
        player_present = i==1 || i%1200==0;
        armportWorldBegin();
        assert(!!armport_world_trace.active == (on && (i == 1 || (i <= 4200 && i % 600 == 0))));
        if (armport_world_trace.active) {
            unsigned reason;
            assert(armport_world_trace.frame == (unsigned)i);
            for (reason = 0; reason < 4; ++reason) {
                assert(!armport_world_trace.detail_samples[reason] && !armport_world_trace.model_detail_samples[reason]);
                armport_world_trace.detail_samples[reason] = 4; armport_world_trace.model_detail_samples[reason] = 4;
            }
        }
        if (armport_world_trace.active) {
            assert(!armport_world_trace.model_visits && !armport_world_trace.editor_model_skip &&
                !armport_world_trace.distance_model_skip && !armport_world_trace.frustum_model_skip && !armport_world_trace.postchecks_model);
            armport_world_trace.model_visits=5;armport_world_trace.editor_model_skip=1;
            armport_world_trace.distance_model_skip=1;armport_world_trace.frustum_model_skip=1;
            armport_world_trace.postchecks_model=2;
        }
        ARMPORT_WORLD_COUNT(visits);
        ARMPORT_WORLD_COUNT(model_calls);
        ARMPORT_WORLD_COUNT(sort_requests);
        armportWorldEnd(0);
        assert(!memcmp(&saved_task,&activeTaskDest,sizeof(saved_task)));
        assert(!memcmp(&saved_waypoint,&waypointDest,sizeof(saved_waypoint)));
        assert(winDefs[0].loc.mode==(int)sample && winDefs[1].loc.mode==-(int)sample);
        assert(game_state.mission_map==(int)(sample&1));
        assert(!armport_world_trace.active);
        previous = armport_world_trace.visits;
        ARMPORT_WORLD_COUNT(visits);
        assert(armport_world_trace.visits == previous);
    }
    assert(records == (on ? 8 : 0) && model_records == records && camera_records==records && player_reads==records && ui_records==records);
    assert(group_info.ref_count == 3 && group_info.refs == refs);
    assert(!memcmp(saved_camera,&cam_info,sizeof(cam_info)) && !memcmp(saved_player,&player,sizeof(player)));
    printf("world trace %s: records=%d, 5000 frames, matching model/camera/UI summaries, eight UI selection/name/map combinations, unterminated arrays, nullable player, bounded reads, per-frame reset and visibility/pose/UI inputs unchanged\n", on ? "on" : "off", records);
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
