#!/usr/bin/env python3
"""Actual cmdOldReceive plus the command-destination snapshot writer.

The original cmdOldReceivePacked/cmdOldReceive/doDataSwap bodies are compiled
with host packet, shortcut and lookup adapters. The writer must name exactly
the tables in entrecv.c's cmd_list, dump every argument of every command, keep
float bits and bounded strings, and not mutate the destinations.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    source = ap.parse_args().source
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    parse = (source / 'libs/UtilitiesLib/src/utils/cmdoldparse.c').read_text()
    types = (source / 'libs/UtilitiesLib/include/utilitieslib/utils/cmdoldparsetypes.h').read_text()
    entrecv = (source / 'Game/src/entity/entrecv.c').read_text()

    # The writer must cover exactly the receive list, in order.
    found = re.search(r'static CmdList cmd_list =\s*\{\s*\{\{\s*(\w+)\s*\},\s*\{\s*(\w+)\s*\},\s*\{\s*0\s*\}\}\s*\};', entrecv)
    assert found, 'entrecv.c cmd_list shape changed'
    writer = function(state, 'static void command_destination_state(')
    assert re.findall(r'command_table_state\((\w+)\)', writer) == list(found.groups()), writer
    assert 'context = {0}' in entrecv.replace('CmdContext  context = {0}', 'context = {0}')

    code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define CAPACITY 1048576
#define check(x) do { if (!(x)) _Exit(3); } while (0)
#define xcase break; case
static char buffer[CAPACITY]; static size_t used;
typedef float F32; typedef F32 Vec3[3]; typedef uint32_t U32;
''' + types[types.index('typedef enum CmdParseType'):types.index('#endif')] + r'''
#define CMDMAXARGS 11
#define CMDMAXDATASWAPS 4
typedef struct DataDesc { CmdParseType type; void *ptr; int maxval; } DataDesc;
typedef struct Cmd { int access_level; char *name; int num; DataDesc data[CMDMAXARGS]; int flags; char *comment; void *handler; int send; int num_args; } Cmd;
typedef struct CmdDataSwap { void *source; intptr_t size; void *dest; } CmdDataSwap;
typedef struct CmdContext { int access_level; CmdDataSwap data_swap[CMDMAXDATASWAPS]; int numDataSwaps; } CmdContext;
typedef struct CmdGroup { Cmd *cmds; } CmdGroup;
typedef struct CmdList { CmdGroup groups[4]; } CmdList;
typedef struct { int kind; unsigned value; F32 f; const char *s; } Token;
typedef struct Packet { Token t[256]; int n, cursor; } Packet;
static Token take(Packet *p, int kind) { assert(p->cursor < p->n && p->t[p->cursor].kind == kind); return p->t[p->cursor++]; }
static unsigned pktGetBitsPack(Packet *p, int minbits) { (void)minbits; return take(p, 0).value; }
static unsigned pktGetBits(Packet *p, int bits) { assert(bits == 14); return take(p, 1).value; }
static F32 pktGetF32(Packet *p) { return take(p, 2).f; }
static char *pktGetString(Packet *p) { return (char *)take(p, 3).s; }
static F32 unpackEuler(unsigned v, int bits) { assert(bits == 14); return (F32)v / 16.0f; }
static void strncpy_s(char *dst, size_t size, const char *src, size_t count) { size_t n = strlen(src); if (n > count) n = count; assert(n < size); memcpy(dst, src, n); dst[n] = 0; }
static char *cmdOldVarsLookup(char *s) { return s; }
static const char *shortcuts[8];
static char *cmdOldShortcutName(int idx) { return idx > 0 && idx < 8 ? (char *)shortcuts[idx] : NULL; }
static Cmd *cmdOldListFind(CmdList *list, const char *name, const char *h, void *x) {
    (void)h; (void)x;
    for (int g = 0; list->groups[g].cmds; g++) for (Cmd *c = list->groups[g].cmds; c->name; c++) if (!strcmp(c->name, name)) return c;
    return NULL; }
'''
    code += function(parse, 'void *doDataSwap(')
    code += function(parse, 'static int cmdOldReceivePacked(')
    code += function(parse, 'void cmdOldReceive(')
    code += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code += function(state, 'static void fixed_string(')
    code += r'''
static int s32 = 7, gated = 5; static unsigned u32 = 0; static F32 f32 = 1.5f, euler = 0, v3[3] = {0};
static char str[8] = "old", sentence[16] = "keep"; static int unreceived = -9; static F32 never = -0.0f;
static struct { U32 abs_time; } server_visible_state;
static Cmd control_cmds[] = {
    {0, "s32", 0, {{PARSETYPE_S32, &s32}}},
    {0, "u32", 0, {{PARSETYPE_U32, &u32}}},
    {0, "f32", 0, {{PARSETYPE_FLOAT, &f32}, {PARSETYPE_EULER, &euler}}},
    {9, "gated", 0, {{PARSETYPE_S32, &gated}}},
    {0, "unreceived", 0, {{PARSETYPE_S32, &unreceived}, {PARSETYPE_FLOAT, &never}, {PARSETYPE_MAT4, NULL}}},
    {0}};
static Cmd server_visible_cmds[] = {
    {0, "v3", 0, {{PARSETYPE_VEC3, v3}}},
    {0, "str", 0, {{PARSETYPE_STR, str, sizeof(str)}, {PARSETYPE_SENTENCE, sentence, sizeof(sentence)}}},
    {0}};
static CmdList cmd_list = {{{control_cmds}, {server_visible_cmds}, {0}}};
'''
    code += function(state, 'static void command_table_state(')
    code += writer
    code += r'''
static void num(Packet *p, unsigned v) { p->t[p->n++] = (Token){0, v, 0, NULL}; }
static void bits(Packet *p, unsigned v) { p->t[p->n++] = (Token){1, v, 0, NULL}; }
static void flt(Packet *p, F32 f) { p->t[p->n++] = (Token){2, 0, f, NULL}; }
static void txt(Packet *p, const char *s) { p->t[p->n++] = (Token){3, 0, 0, s}; }
int main(int argc, char **argv) {
    int mode = atoi(argv[1]); (void)argc;
    const char *names[] = {NULL, "s32", "u32", "f32", "gated", "v3", "str", "unreceived"};
    memcpy(shortcuts, names, sizeof(names));
    for (int g = 0; cmd_list.groups[g].cmds; g++) for (Cmd *c = cmd_list.groups[g].cmds; c->name; c++) { c->num_args = 0; while (c->num_args < CMDMAXARGS && c->data[c->num_args].type) c->num_args++; }
    Packet p = {0}; CmdContext context = {0}; context.access_level = 1;
    num(&p, 1); num(&p, 0x80000000U);
    num(&p, 2); num(&p, 0xffffffffU);
    num(&p, 3); { union { unsigned u; F32 f; } nan = {0x7fc00001U}; flt(&p, nan.f); } bits(&p, 16);
    num(&p, 4); num(&p, 99);
    num(&p, 5); flt(&p, -0.0f); flt(&p, 1e-40f); flt(&p, 2.0f);
    num(&p, 6); txt(&p, mode == 1 ? "abcdefghij" : "xy"); txt(&p, "sentence words");
    num(&p, 0);
    server_visible_state.abs_time = 0xfffffffeU;
    cmdOldReceive(&p, &cmd_list, &context);
    assert(p.cursor == p.n);
    if (mode == 2) control_cmds[0].num_args = CMDMAXARGS + 1;
    if (mode == 3) used = CAPACITY - 1;
    if (mode == 4) memset(str, 'z', sizeof(str));
    char before[64]; memcpy(before, str, sizeof(str)); int s32_before = s32;
    command_destination_state();
    assert(!memcmp(before, str, sizeof(str)) && s32 == s32_before);
    puts(buffer); return 0; }
'''
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'probe.c'
        c.write_text(code)
        exe = c.with_suffix('')
        subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-sanitize-recover=all', '-Wno-incompatible-pointer-types', str(c), '-o', str(exe)], check=True)
        for mode in range(5):
            r = subprocess.run([str(exe), str(mode)], capture_output=True, text=True, timeout=20)
            assert r.returncode == (0 if mode in (0, 1) else 3), (mode, r.returncode, r.stderr)
            if r.returncode:
                continue
            v = json.loads(r.stdout)
            control = {c['name']: c['args'] for c in v['control_cmds']}
            server = {c['name']: c['args'] for c in v['server_visible_cmds']}
            assert [c['name'] for c in v['control_cmds']] == ['s32', 'u32', 'f32', 'gated', 'unreceived']
            assert control['s32'] == [{'type': 1, 'value': -2147483648}]
            assert control['u32'] == [{'type': 2, 'value': 4294967295}]
            assert control['f32'] == [{'type': 3, 'value': [0x7fc00001]}, {'type': 4, 'value': [0x3f800000]}]
            assert control['gated'] == [{'type': 1, 'value': 5}], 'access-level gate keeps the old value'
            assert control['unreceived'] == [{'type': 1, 'value': -9}, {'type': 3, 'value': [0x80000000]},
                                             {'type': 6, 'value': None}]
            assert server['v3'] == [{'type': 5, 'value': [0x80000000, 0x000116c2, 0x40000000]}]
            assert server['str'] == [{'type': 7, 'value': 'abcdefg' if mode == 1 else 'xy'},
                                     {'type': 8, 'value': 'sentence words'}]
            assert v['abs_time'] == 0xfffffffe
    print('5 command-destination cases pass: actual cmdOldReceive, table parity with entrecv.c cmd_list, '
          'bits, gating, unreceived commands, bounds; host adapters do not qualify native ABI')


if __name__ == '__main__':
    main()
