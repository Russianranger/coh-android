#!/usr/bin/env python3
"""Exercise actual fixed player receive destinations with host fixtures."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    fixed = source[source.index('static void fixed_string('):source.index('static void group_members(')]
    writer = source[source.index('static void player_receive_core('):source.index('unsigned armportReplayStateSave(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 65536
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct {
 int playerType,playerSubType,praetorianProgress,hidden,skillsUnlocked,newFeaturesVersion;
 char primarySet[32],secondarySet[32],comment[128];
 unsigned auth_user_data[4],popHelpStatus[5]; int popHelpLatest[3];
 unsigned unrelated_local_clock;
} EntPlayer;
''' + formatting + fixed + writer + r'''
int main(int argc, char **argv) {
 int mode=argc>1?atoi(argv[1]):0;
 EntPlayer p={1,2,3,1023,1,-1,"Primary\"","Secondary","Comment\n\377",
  {1,2,0x80000000U,0xffffffffU},{0,1,2,3,0x80000001U},{-1,0,(int)0x80000000U},123},before;
 if(mode==1) p.auth_user_data[3]=17;
 if(mode==2) p.popHelpStatus[4]=17;
 if(mode==3) p.popHelpLatest[2]=17;
 if(mode==4) p.unrelated_local_clock=999;
 if(mode==5) memset(p.primarySet,'X',sizeof(p.primarySet));
 if(mode==6) memset(p.secondarySet,'X',sizeof(p.secondarySet));
 if(mode==7) memset(p.comment,'X',sizeof(p.comment));
 if(mode==8) used=CAPACITY-2;
 if(mode==9) memset(&p,0,sizeof(p));
 if(mode==10) memset(p.comment,'X',sizeof(p.comment)-1),p.comment[127]=0;
 before=p;player_receive_core(&p);check(!memcmp(&before,&p,sizeof(p)));
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
                                  text=True, timeout=15) for i in range(11)]
        for i, result in enumerate(results):
            assert result.returncode == (3 if i in (5, 6, 7, 8) else 0), (i, result.returncode, result.stderr)
        d = json.loads(results[0].stdout)
        assert d == dict(player_type=1, player_subtype=2, praetorian_progress=3, hidden=1023,
            skills_unlocked=1, new_features_u32=0xffffffff, primary_set='Primary"', secondary_set='Secondary',
            comment='Comment\n\xff', account_game_flags_u32=[1,2,0x80000000,0xffffffff],
            pop_help_status_u32=[0,1,2,3,0x80000001], pop_help_latest_u32=[0xffffffff,0,0x80000000])
        for mode,key in [(1,'account_game_flags_u32'),(2,'pop_help_status_u32'),(3,'pop_help_latest_u32')]:
            changed=json.loads(results[mode].stdout);assert changed[key][-1]==17
            changed[key][-1]=d[key][-1];assert changed==d
        assert results[4].stdout==results[0].stdout
        empty=json.loads(results[9].stdout)
        assert all(v=='' if isinstance(v,str) else all(x==0 for x in v) if isinstance(v,list) else v==0 for v in empty.values())
        assert json.loads(results[10].stdout)['comment']=='X'*127
    print('player core writer: received scalar/flag fields, full fixed arrays and literal strings, high-bit U32 values, source immutability, last-slot mutation sensitivity, local-clock exclusion and string/output bounds pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
