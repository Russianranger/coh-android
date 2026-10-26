#!/usr/bin/env python3
"""Actual server-control snapshot writer with fixture control_state.

The fixture mirrors the original ServerControlState (cmdcontrols.h, the
CLIENT layout with bitfields) and the control_state fields the writer reads,
using the original header text for ServerControlState and SurfaceParams.
Checks literal packet-ID guards, raw float bits, all 17 flags, the full
100-step physics ring, null server_state and nonmutation. The original
receivers are not compiled here (heavy motion/CSC dependencies).
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    source = ap.parse_args().source
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    controls = (source / 'Common/cmdparse/cmdcontrols.h').read_text()
    motion = (source / 'Common/entity/motion.h').read_text()
    scs = controls[controls.index('typedef struct ServerControlState\n'):controls.index('} ServerControlState;') + 21]
    surf = motion[motion.index('typedef struct SurfaceParams'):motion.index('} SurfaceParams;') + 16]
    surf_enum = motion[motion.index('typedef enum SurfParamIndex'):]
    surf_enum = surf_enum[:surf_enum.index(';') + 1]
    code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define CAPACITY 1048576
#define check(x) do { if (!(x)) _Exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef float F32; typedef F32 Vec3[3]; typedef unsigned U32; typedef unsigned short U16; typedef unsigned char U8;
''' + surf + '\n' + surf_enum + '\n' + scs + r'''
static struct { U8 received_update_id; ServerControlState *server_state;
    struct { struct { Vec3 pos; Vec3 vel; U16 net_id; } step[100]; int end, cur; } svr_phys;
    U32 server_state_pkt_id, forced_move_pkt_id, server_pos_pkt_id; } control_state;
'''
    code += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code += function(state, 'static void server_control_receive_state(')
    code += r'''
int main(int argc, char **argv) {
    int mode = atoi(argv[1]); (void)argc;
    ServerControlState s; memset(&s, 0, sizeof(s));
    union { U32 u; F32 f; } nan = {0x7fc00001U};
    s.speed[0] = -0.0f; s.speed[1] = nan.f; s.speed[2] = 1e-40f; s.speed_back = 2.0f; s.jump_height = -1.5f;
    s.surf_mods[SURFPARAM_MAX - 1].max_speed = 3.0f;
    s.controls_input_ignored = 1; s.fly = 1; s.parkour_run = 1;
    control_state.server_state = mode == 1 ? NULL : &s;
    control_state.received_update_id = 255; control_state.server_state_pkt_id = 1;
    control_state.server_pos_pkt_id = 0xffffffffU; control_state.forced_move_pkt_id = 40;
    control_state.svr_phys.end = 99; control_state.svr_phys.cur = -1;
    control_state.svr_phys.step[99].net_id = 65535; control_state.svr_phys.step[99].vel[2] = -0.0f;
    if (mode == 2) used = CAPACITY - 1;
    ServerControlState copy = s; char before[sizeof(control_state)]; memcpy(before, &control_state, sizeof(before));
    server_control_receive_state();
    assert(!memcmp(&copy, &s, sizeof(s)) && !memcmp(before, &control_state, sizeof(before)));
    puts(buffer); return 0; }
'''
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'control.c'
        c.write_text(code)
        exe = c.with_suffix('')
        subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-sanitize-recover=all', str(c), '-o', str(exe)], check=True)
        for mode in range(3):
            r = subprocess.run([str(exe), str(mode)], capture_output=True, text=True, timeout=20)
            assert r.returncode == (3 if mode == 2 else 0), (mode, r.returncode, r.stderr)
            if r.returncode:
                continue
            v = json.loads(r.stdout)
            assert (v['server_state_pkt_id'], v['server_pos_pkt_id'], v['forced_move_pkt_id'], v['received_update_id']) == (1, 0xffffffff, 40, 255)
            assert (v['physics_end'], v['physics_cur']) == (99, -1) and len(v['physics_steps']) == 100
            assert v['physics_steps'][99] == [65535, [0, 0, 0], [0, 0, 0x80000000]]
            if mode == 1:
                assert v['server_state'] is None
                continue
            st = v['server_state']
            assert st['speed_f32_bits'] == [0x80000000, 0x7fc00001, 0x000116c2]
            assert st['speed_back_f32_bits'] == [0x40000000] and st['jump_height_f32_bits'] == [0xbfc00000]
            assert st['surf_mods_f32_bits'][-1] == 0x40400000
            assert st['flags'] == [1, 0, 0, 1] + [0] * 12 + [1]
    print('3 server-control writer cases pass: literal packet-ID guards, raw float bits, 17 flags, full '
          '100-step physics ring, null state, nonmutation; original receivers not compiled here')


if __name__ == '__main__':
    main()
