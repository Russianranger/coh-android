#!/usr/bin/env python3
"""Check actual retained character writer, without substituting a decoder."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    writer = source[source.index('static void character_receive_core('):source.index('static void entity_receive_metadata(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 4096
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { const char *pchName; } CharacterClass, CharacterOrigin;
typedef struct {
 const CharacterClass *pclass; const CharacterOrigin *porigin;
 int iCombatLevel,iCombatModShift,playerTypeByLocation,iAllyID,iGangID,bPvPActive;
 unsigned unrelated_local_clock;
} Character;
''' + formatting + writer + r'''
int main(int argc, char **argv) {
 int mode=argc>1?atoi(argv[1]):0;
 CharacterClass cls={"Class\"\n\377"},copy=cls;CharacterOrigin origin={"Origin"};
 Character p={&cls,&origin,53,-3,1,-1,2147483647,1,123},before;
 if(mode==1) p.pclass=NULL;
 if(mode==2) p.porigin=NULL;
 if(mode==3) cls.pchName="Changed";
 if(mode==4) p.pclass=&copy;
 if(mode==5) p.iCombatLevel=17;
 if(mode==6) p.iCombatModShift=17;
 if(mode==7) p.playerTypeByLocation=17;
 if(mode==8) p.iAllyID=17;
 if(mode==9) p.iGangID=17;
 if(mode==10) p.bPvPActive=0;
 if(mode==11) used=CAPACITY-2;
 if(mode==12) p.unrelated_local_clock=999;
 if(mode==13) cls.pchName=origin.pchName=NULL;
 before=p;character_receive_core(&p);check(!memcmp(&before,&p,sizeof(p)));
 puts(buffer);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(root / 'fixture.c'), '-o', str(root / 'fixture')], check=True)
        results = [subprocess.run([str(root / 'fixture'), str(i)], capture_output=True,
                                  text=True, timeout=15) for i in range(14)]
        for i, result in enumerate(results):
            assert result.returncode == (3 if i == 11 else 0), (i, result.returncode, result.stderr)
        values = {i: json.loads(result.stdout) for i, result in enumerate(results) if result.returncode == 0}
        expected = {'class': 'Class"\n\xff', 'origin': 'Origin', 'combat_level': 53,
                    'combat_mod_shift': -3, 'player_type_by_location': 1,
                    'ally_id': -1, 'gang_id': 2147483647, 'pvp_active': 1}
        assert values[0] == values[4] == values[12] == expected
        assert values[1]['class'] is None and values[2]['origin'] is None
        assert values[13]['class'] is None and values[13]['origin'] is None
        for mode, key, value in [(3,'class','Changed'),(5,'combat_level',17),
                (6,'combat_mod_shift',17),(7,'player_type_by_location',17),
                (8,'ally_id',17),(9,'gang_id',17),(10,'pvp_active',0)]:
            assert values[mode][key] == value
            values[mode][key] = expected[key]
            assert values[mode] == expected
    print('character core writer: nullable logical class/origin, signed combat/ally/gang fields, location/PvP, individual-field mutation sensitivity, pointer/clock exclusion, source immutability and output bounds pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
