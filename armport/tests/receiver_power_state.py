#!/usr/bin/env python3
"""Run the actual snapshot power serializer with adversarial host fixtures."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    powers = source[source.index('static void base_power('):source.index('static void inventory_item(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024 * 1024)
#define MAX_BUILD_NUM 2
#define CHAR_INSP_MAX_COLS 5
#define CHAR_INSP_MAX_ROWS 4
#define CHAR_BOOST_MAX 70
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY];
static size_t used;
typedef struct { const char *pchFullName; } BasePower, BasePowerSet;
typedef struct { struct { int type; const char *name; } reward; int filled; } PowerupSlot;
typedef struct { const BasePower *ppowBase; int idx, iLevel, iNumCombines;
    float afVars[4], fTimer; PowerupSlot aPowerupSlots[10]; } Boost;
typedef struct { const BasePower *ppowBase, *ppowOriginal;
    int idx, iUniqueID, iLevelBought, iNumCharges, iNumBoostsBought, bEnabled, bDisabledManually;
    float fRangeLast, fUsageTime, fAvailableTime, fTimer;
    unsigned ulCreationTime; Boost **ppBoosts, **ppGlobalBoosts; } Power;
typedef struct { const BasePowerSet *psetBase; int idx, iLevelBought; Power **ppPowers; } PowerSet;
typedef struct { int iCurBuild, iActiveBuild, iBuildLevels[MAX_BUILD_NUM];
    PowerSet **ppPowerSets, **ppBuildPowerSets[MAX_BUILD_NUM];
    int iNumInspirationCols, iNumInspirationRows, iNumBoostSlots;
    const BasePower *aInspirations[CHAR_INSP_MAX_COLS][CHAR_INSP_MAX_ROWS];
    Boost *aBoosts[CHAR_BOOST_MAX]; } Character;
/* Fixture-only earray backing; the native compiler checks real headers. */
static int eaSize(const void *address)
{
    void *items; memcpy(&items, address, sizeof(items));
    return items ? (int)((size_t *)items)[-1] : 0;
}
'''
    fixture += formatting + powers + r'''
int main(int argc, char **argv)
{
    int mode = argc > 1 ? atoi(argv[1]) : 0;
    BasePower base = {"Category.Set.Power\"\\\n"};
    BasePowerSet setbase = {"Category.Set"};
    Boost b = {0}; Power p = {0}; PowerSet set = {0}; Character c = {0};
    struct { size_t n; Boost *v[3]; } boosts_array = {3, {&b, NULL, &b}};
    struct { size_t n; Power *v[2]; } powers_array = {2, {NULL, &p}};
    struct { size_t n; PowerSet *v[2]; } sets_array = {2, {&set, NULL}};
    unsigned vars[4] = {0x80000000U, 0x7fc01234U, 0x00000001U, 0x7f800000U};
    b.ppowBase = &base; b.idx = 2; b.iLevel = 12; b.iNumCombines = 3;
    memcpy(b.afVars, vars, sizeof(vars));
    b.aPowerupSlots[9].reward.type = 7;
    b.aPowerupSlots[9].reward.name = "last slot";
    b.aPowerupSlots[9].filled = 1;
    p.ppowBase = &base; p.ppowOriginal = NULL; p.iUniqueID = 31;
    p.iNumCharges = mode == 2 ? 5 : 4; p.bEnabled = 1;
    p.fRangeLast = -0.0f; p.fUsageTime = 1.0f; p.fAvailableTime = 2.0f;
    p.ppBoosts = boosts_array.v;
    set.psetBase = &setbase; set.ppPowers = powers_array.v;
    c.ppPowerSets = sets_array.v; c.ppBuildPowerSets[1] = sets_array.v;
    c.iActiveBuild = 1; c.iBuildLevels[1] = 31;
    c.iNumInspirationCols = 5; c.iNumInspirationRows = 4;
    c.aInspirations[4][3] = &base; c.aBoosts[69] = &b; c.iNumBoostSlots = 70;
    if (mode == 1) { p.fTimer = 1000; p.ulCreationTime = 1000000; b.fTimer = -99; }
    if (mode == 3) sets_array.n = 4097;
    power_inventory(&c);
    check(c.ppPowerSets == sets_array.v && sets_array.v[0] == &set);
    check(p.iNumCharges == (mode == 2 ? 5 : 4));
    puts(buffer);
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(root / 'fixture.c'), '-o', str(root / 'fixture')], check=True)
        results = [subprocess.run([str(root / 'fixture'), str(i)], capture_output=True,
                                  text=True, timeout=15) for i in (0, 1, 2, 3, 0)]
        assert [r.returncode for r in results] == [0, 0, 0, 3, 0], [(r.returncode, r.stderr) for r in results]
        assert results[0].stdout == results[1].stdout == results[4].stdout
        d = json.loads(results[0].stdout)
        assert d['build_sets'][0] == [] and d['current_sets'][1] is None
        p = d['current_sets'][0]['powers'][1]
        assert d['current_sets'][0]['powers'][0] is None
        assert p['original'] is None and p['unique_id'] == 31
        assert p['base'] == 'Category.Set.Power"\\\n'
        assert p['range_f32_bits'] == [0x80000000]
        assert p['usage_f32_bits'] == [0x3f800000]
        assert p['boosts'][1] is None and p['boosts'][0] == p['boosts'][2]
        b = p['boosts'][0]
        assert b['vars_f32_bits'] == [0x80000000, 0x7fc01234, 1, 0x7f800000]
        assert b['powerup_slots'][9] == dict(type=7, name='last slot', filled=1)
        assert d['boost_inventory'][69] == b and d['boost_inventory'][:69] == [None] * 69
        assert d['inspirations'][4][3] == p['base']
        changed = json.loads(results[2].stdout)
        changed['current_sets'][0]['powers'][1]['charges'] = 4
        changed['build_sets'][1][0]['powers'][1]['charges'] = 4
        assert changed == d
    print('power serializer: null slots, identity escaping, raw float bits, build arrays, final inventory slots, timer exclusion and bound rejection pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
