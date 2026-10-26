#!/usr/bin/env python3
"""Actual entity receive-extras snapshot writer with fixture entities.

Checks literal access level/db flag/logout timer bits, the owned-costume
hook (null and present), the four entReceiveTitles player values with a full
127-character costume FX name (unterminated storage fails closed), the IgnoreCombatMods pair, null player/character and
nonmutation. The original receivers are not compiled (entrecv.c dependencies).
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
    ap.add_argument('--source', type=Path, required=False)
    ap.parse_args()
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#define CAPACITY 1048576
#define check(x) do { if (!(x)) _Exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef float F32; typedef unsigned U32;
typedef struct { int marker; } Costume; typedef Costume cCostume;
typedef struct { int glowieUnlocked, attachArticle, respecTokens; char costumeFxSpecial[128]; int helperStatus; } EntPlayer;
typedef struct { bool bIgnoreCombatMods; int ignoreCombatModLevelShift; } Character;
typedef enum { ACCESS_USER = 0 } AccessLevel; typedef unsigned DbFlag;
typedef struct { AccessLevel access_level; DbFlag db_flags; F32 logout_timer; Costume *ownedCostume;
    EntPlayer *pl; Character *pchar; } Entity;
'''
    code += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code += state[state.index('static void fixed_string('):state.index('static void group_members(')]
    code += 'static void costume(const cCostume *c){if(c)out("%d",c->marker);else out("null");}\n'
    code += function(state, 'static void entity_receive_extras_state(')
    code += r'''
int main(int argc, char **argv) {
    int mode = atoi(argv[1]); (void)argc;
    Costume owned = {7}; EntPlayer pl; Character ch; Entity e;
    memset(&pl, 0, sizeof(pl)); memset(&ch, 0, sizeof(ch)); memset(&e, 0, sizeof(e));
    pl.glowieUnlocked = 1; pl.attachArticle = 1; pl.respecTokens = -1; pl.helperStatus = 3;
    memset(pl.costumeFxSpecial, 'A', sizeof(pl.costumeFxSpecial) - (mode == 3 ? 0 : 1));
    ch.bIgnoreCombatMods = true; ch.ignoreCombatModLevelShift = -8;
    e.access_level = (AccessLevel)9; e.db_flags = 0x80000001U; e.logout_timer = 30.0f;
    e.ownedCostume = mode == 1 ? NULL : &owned; e.pl = mode == 1 ? NULL : &pl; e.pchar = mode == 1 ? NULL : &ch;
    if (mode == 2) used = CAPACITY - 1;
    Entity copy = e; EntPlayer pcopy = pl; Character ccopy = ch;
    entity_receive_extras_state(&e);
    assert(!memcmp(&copy, &e, sizeof(e)) && !memcmp(&pcopy, &pl, sizeof(pl)) && !memcmp(&ccopy, &ch, sizeof(ch)));
    puts(buffer); return 0; }
'''
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'extras.c'
        c.write_text(code)
        exe = c.with_suffix('')
        subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-sanitize-recover=all', str(c), '-o', str(exe)], check=True)
        for mode in range(4):
            r = subprocess.run([str(exe), str(mode)], capture_output=True, text=True, timeout=20)
            assert r.returncode == (3 if mode in (2, 3) else 0), (mode, r.returncode, r.stderr)
            if r.returncode:
                continue
            v = json.loads(r.stdout)
            assert (v['access_level'], v['db_flags_u32'], v['logout_timer_f32_bits']) == (9, 0x80000001, [0x41f00000])
            if mode == 1:
                assert v['owned_costume'] is None and v['player'] is None and v['character'] is None
                continue
            assert v['owned_costume'] == 7
            assert v['player'] == dict(glowie_unlocked=1, attach_article=1, respec_tokens_u32=0xffffffff,
                                       helper_status=3, costume_fx_special='A' * 127)
            assert v['character'] == dict(ignore_combat_mods=1, ignore_combat_mod_level_shift=-8)
    print('4 entity receive-extras writer cases pass: access/db flags/logout bits, owned costume, titles player '
          'values with full 127-byte FX name (unterminated storage fails closed), IgnoreCombatMods, nulls, bounds, nonmutation')


if __name__ == '__main__':
    main()
