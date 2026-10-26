#!/usr/bin/env python3
"""Exercise the actual retained-costume writer, including every SG color half."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    costumes = source[source.index('static void super_colors('):source.index('/* Persist logical identities')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 1048576
#define NUM_SG_COLOR_SLOTS 6
#define MAX_COSTUMES 10
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { unsigned SGBitSetLow, SGBitSetHigh; } SGColorBits;
typedef struct {
    const char *entTypeFile, *costumeFilePrefix;
    int bodytype, iVillainIdx, convertedScale;
    float fScales[30]; int compressedScales[7]; unsigned colorSkin;
    SGColorBits superColorsPrimaryU[6], superColorsSecondaryU[6], superColorsPrimary2U[6],
        superColorsSecondary2U[6], superColorsTertiaryU[6], superColorsQuaternaryU[6];
    int currentSuperColorSet, iNumParts;
} Appearance;
typedef struct {
    const char *pchName, *pchTex1, *pchTex2, *pchGeom, *pchFxName, *regionName, *bodySetName;
    unsigned color[4], colorTmp[4]; const char *displayName, *sourceFile; int costumeNum;
} CostumePart;
typedef struct { Appearance appearance; const CostumePart **parts; int containsRestrictedStoreParts; } cCostume;
typedef cCostume Costume;
typedef struct {
    int current_costume, current_supercostume, num_costume_slots, num_costumes_stored,
        npc_costume, supergroup_mode, hide_supergroup_emblem, pendingCostumeNumber;
    Costume *costume[10], *superCostume, *pendingCostume;
    unsigned pendingCostumeForceTime, pendingCostumeIgnoreTime;
} EntPlayer;
static int part_count=3;
#define eaSize(p) (*(p) ? part_count : 0)
''' + formatting + costumes + r'''
int main(int argc, char **argv) {
    int i, mode = argc > 1 ? atoi(argv[1]) : 0;
    cCostume c={0}, before; EntPlayer p={0}, player_before; CostumePart part={0}, part_before;
    const CostumePart *parts[3] = {&part, NULL, &part};
    unsigned nan=0x7fc01234, negzero=0x80000000;
    c.appearance.bodytype=4; c.appearance.iNumParts=2; c.parts=parts;
    c.appearance.convertedScale=1; c.appearance.currentSuperColorSet=5;
    c.appearance.colorSkin=0xfedcba98;
    memcpy(&c.appearance.fScales[0], &nan, 4); memcpy(&c.appearance.fScales[29], &negzero, 4);
    for (i=0;i<6;++i) {
        c.appearance.superColorsPrimaryU[i]=(SGColorBits){1+i, 0xffffffffU-i};
        c.appearance.superColorsSecondaryU[i]=(SGColorBits){11+i, 21+i};
        c.appearance.superColorsPrimary2U[i]=(SGColorBits){31+i, 41+i};
        c.appearance.superColorsSecondary2U[i]=(SGColorBits){51+i, 61+i};
        c.appearance.superColorsTertiaryU[i]=(SGColorBits){71+i, 81+i};
        c.appearance.superColorsQuaternaryU[i]=(SGColorBits){91+i, 101+i};
    }
    part.pchName="HIPS\""; part.pchTex1=""; part.color[3]=0x80000000U;
    p.current_costume=9; p.current_supercostume=1; p.num_costume_slots=4;
    p.num_costumes_stored=10; p.npc_costume=31; p.supergroup_mode=1;
    p.hide_supergroup_emblem=1; p.pendingCostumeNumber=256;
    p.costume[0]=&c; p.costume[9]=&c; p.superCostume=&c; p.pendingCostume=&c;
    if (mode==1) c.appearance.superColorsQuaternaryU[5].SGBitSetHigh=0x80000000U;
    if (mode==2) p.costume[9]=0;
    if (mode==3) part_count=257;
    if (mode==4) c.appearance.iNumParts=-1;
    if (mode==5) c.appearance.iNumParts=4;
    if (mode==6) c.parts=0, c.appearance.iNumParts=0;
    if (mode==7) {
        p.pendingCostumeForceTime=123456; p.pendingCostumeIgnoreTime=456789;
        part.colorTmp[3]=123; part.displayName="derived"; part.sourceFile="local";
        part.costumeNum=7; c.containsRestrictedStoreParts=1;
    }
    if (mode==8) c.appearance.convertedScale=0, c.appearance.currentSuperColorSet=2;
    before=c; player_before=p; part_before=part;
    player_costumes(&p);
    check(!memcmp(&before,&c,sizeof(c)) && !memcmp(&player_before,&p,sizeof(p)) &&
          !memcmp(&part_before,&part,sizeof(part)));
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
                                  text=True, timeout=15) for i in range(9)]
        for i in (0, 1, 2, 6, 7, 8):
            assert results[i].returncode == 0, (i, results[i].stderr)
        for i in (3, 4, 5):
            assert results[i].returncode == 3, (i, results[i].stderr)
        d = json.loads(results[0].stdout)
        c = d['slots'][0]
        assert len(d['slots']) == 10 and d['slots'][1:9] == [None] * 8
        assert d['slots'][9] == d['super'] == d['pending'] == c
        assert (d['current'], d['npc_index'], d['pending_number']) == (9, 31, 256)
        assert c['scales_f32_bits'][0] == 0x7fc01234 and c['scales_f32_bits'][29] == 0x80000000
        assert c['num_parts'] == 2 and len(c['parts']) == 3 and c['parts'][1] is None
        assert c['parts'][0]['name'] == 'HIPS"' and c['parts'][0]['tex1'] == ''
        assert c['parts'][0]['tex2'] is None and c['parts'][2]['colors'][3] == 0x80000000
        expected = {'primary': [[i+1, 0xffffffff-i] for i in range(6)]}
        for n, name in enumerate(('secondary', 'primary2', 'secondary2', 'tertiary', 'quaternary')):
            expected[name] = [[11+20*n+i, 21+20*n+i] for i in range(6)]
        assert c['super_colors'] == expected
        changed = json.loads(results[1].stdout)
        assert changed['slots'][9]['super_colors']['quaternary'][5][1] == 0x80000000
        assert json.loads(results[2].stdout)['slots'][9] is None
        assert json.loads(results[6].stdout)['slots'][0]['parts'] == []
        assert results[7].stdout == results[0].stdout
        changed = json.loads(results[8].stdout)['slots'][9]
        assert (changed['converted_scale'], changed['current_super_color_set']) == (0, 2)
    print('costume serializer: six color sets with all low/high halves, raw float bits, '
          '10 retained/null slots plus super/pending, logical/storage counts, mutation sensitivity, '
          'timer/editor exclusion and invalid counts pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
