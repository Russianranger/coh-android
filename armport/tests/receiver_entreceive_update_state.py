#!/usr/bin/env python3
"""Actual entReceiveUpdate retained-state writer and db_time observer.

Fixture globals stand in for the original statics/globals (the native
accessor is patch 0106). Checks literal interpolation settings, the debug
selector, full-width last_pkt_id/abs_time values, raw db_time (null before
receipt, inert while inactive), the raw 100-slot time_since bits, both
client_pos_id values and nonmutation. Original receivers are not compiled.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define CAPACITY 1048576
#define check(x) do { if (!(x)) _Exit(3); } while (0)
static char *buffer; static size_t used; static int active;
typedef float F32; typedef unsigned U32;
typedef struct { int interp_data_level, interp_data_precision; unsigned last_abs_time, last_packet_abs_time; } ArmPortEntReceiveUpdateState;
static ArmPortEntReceiveUpdateState fixture;
static void armportReplayEntReceiveUpdateState(ArmPortEntReceiveUpdateState *s) { *s = fixture; }
static struct { F32 time_since[100]; U32 abs_time; } global_state;
static struct { int hasEntDebugInfo; } game_state;
static struct { int client_pos_id; } control_state;
U32 last_pkt_id; int glob_client_pos_id;
static struct { unsigned valid, value; } received_db_time;
'''
    out_fn = state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    out_fn = out_fn.replace('static char *buffer;', '').replace('static size_t used;', '')
    code += out_fn
    code += function(state, 'void armportReplayDbTime(')
    body = function(state, 'static void entreceive_update_state(')
    code += body
    code += r'''
int main(int argc, char **argv) {
    int mode = atoi(argv[1]); (void)argc;
    union { U32 u; F32 f; } nan = {0x7fc00001U};
    static char storage[CAPACITY]; buffer = storage;
    fixture.interp_data_level = 3; fixture.interp_data_precision = 2;
    fixture.last_abs_time = 0xffffffffU; fixture.last_packet_abs_time = 1;
    game_state.hasEntDebugInfo = 1; last_pkt_id = 0x80000000U; global_state.abs_time = 155;
    global_state.time_since[0] = -0.0f; global_state.time_since[99] = nan.f;
    control_state.client_pos_id = -1; glob_client_pos_id = 7;
    armportReplayDbTime(5);             /* inactive: ignored */
    active = 1;
    if (mode == 0) armportReplayDbTime(0xfffffffeU);
    if (mode == 2) used = CAPACITY - 1;
    ArmPortEntReceiveUpdateState copy = fixture; U32 id = last_pkt_id;
    entreceive_update_state();
    assert(!memcmp(&copy, &fixture, sizeof(copy)) && id == last_pkt_id);
    puts(buffer); return 0; }
'''
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'update.c'
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
            assert (v['interp_data_level'], v['interp_data_precision'], v['has_ent_debug_info']) == (3, 2, 1)
            assert (v['last_pkt_id'], v['last_abs_time'], v['last_packet_abs_time'], v['abs_time']) == (0x80000000, 0xffffffff, 1, 155)
            assert v['db_time'] == (0xfffffffe if mode == 0 else None)
            bits = v['time_since_f32_bits']
            assert len(bits) == 100 and bits[0] == 0x80000000 and bits[99] == 0x7fc00001 and set(bits[1:99]) == {0}
            assert (v['client_pos_id'], v['glob_client_pos_id']) == (-1, 7)
    print('3 entReceiveUpdate state writer cases pass: interpolation settings, debug selector, full-width packet/abs '
          'times, raw db_time (null/inactive), 100 raw time_since bits, client_pos_id values, bounds, nonmutation')


if __name__ == '__main__':
    main()
