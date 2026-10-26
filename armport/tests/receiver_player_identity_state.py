#!/usr/bin/env python3
"""Exercise actual identity/token/string writers; host fixtures are not ABI proof."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    fixed = source[source.index('static void fixed_string('):source.index('static void group_members(')]
    writer = source[source.index('static void player_reward_tokens('):source.index('static void character_receive_core(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024*1024)
#define MAX_COMBAT_STATS 10
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { const char *reward; int val; unsigned timer; } RewardToken;
typedef struct { int iKey,iOrder; } CombatMonitorStat;
typedef struct {
 int titleThe; char titleTheText[10],titleCommon[32],titleOrigin[32],titleSpecial[128];
 int titleColors[2],titleBadge; char workshopInteracting[32];
 RewardToken **rewardTokens,**activePlayerRewardTokens; unsigned titleSpecialExpires;
 int pvpSwitch,bIsGanker; CombatMonitorStat combatMonitorStats[MAX_COMBAT_STATS];
} EntPlayer;
typedef struct { char playerDescription[1024],motto[128]; } EntStrings;
static int eaSize(const void *address) {
 void *items; memcpy(&items,address,sizeof(items));
 return items ? (int)((size_t *)items)[-1] : 0;
}
''' + formatting + fixed + writer + r'''
int main(int argc, char **argv) {
 int mode=argc>1?atoi(argv[1]):0;
 RewardToken t={"Token\"\n\377",-7,0xffffffffU},other={NULL,0,0},tb;
 struct {size_t n; RewardToken *v[8192];} tokens={3,{&t,NULL,&other}},active={2,{NULL,&t}};
 EntPlayer p={31,"The","Common","Origin","Special",{-1,(int)0x80000000U},-1,"Workshop",tokens.v,active.v,123},pb;
 EntStrings s={"Description\n\377","Motto\""},sb; const EntStrings *sp=&s;
 char same_name[128];
 p.pvpSwitch=1;p.bIsGanker=1;p.combatMonitorStats[0].iKey=71;
 p.combatMonitorStats[9].iKey=-1;p.combatMonitorStats[9].iOrder=15;
 if(mode==1) sp=NULL;
 if(mode==2) p.rewardTokens=NULL,p.activePlayerRewardTokens=NULL;
 if(mode==3) tokens.n=8193;
 if(mode==4) active.n=8193;
 if(mode==5) tokens.n=(size_t)-1;
 if(mode==6) active.n=(size_t)-1;
 if(mode>=7 && mode<=13) {
   char *fields[]={p.titleTheText,p.titleCommon,p.titleOrigin,p.titleSpecial,p.workshopInteracting,s.playerDescription,s.motto};
   size_t sizes[]={sizeof(p.titleTheText),sizeof(p.titleCommon),sizeof(p.titleOrigin),sizeof(p.titleSpecial),sizeof(p.workshopInteracting),sizeof(s.playerDescription),sizeof(s.motto)};
   memset(fields[mode-7],'X',sizes[mode-7]);
 }
 if(mode==14) used=CAPACITY-2;
 if(mode==15) t.timer=17,p.titleSpecialExpires=999;
 if(mode==16) t.val=17;
 if(mode==17) tokens.n=8192,tokens.v[8191]=&t;
 if(mode==18) active.n=8192,active.v[8191]=&other;
 if(mode==19) p.titleColors[1]=17;
 if(mode==20) strcpy(p.workshopInteracting,"Changed");
 if(mode==21) strcpy(s.motto,"Changed");
 if(mode==22) strcpy(same_name,t.reward),t.reward=same_name;
 if(mode==23) memset(s.playerDescription,'X',sizeof(s.playerDescription)-1),s.playerDescription[1023]=0;
 if(mode==24) memset(&p,0,sizeof(p)),memset(&s,0,sizeof(s));
 if(mode==25) p.combatMonitorStats[9].iKey=17;
 if(mode==26) p.combatMonitorStats[9].iOrder=3;
 if(mode==27) p.pvpSwitch=0,p.bIsGanker=0;
 pb=p;sb=s;tb=t;
 out("{\"player\":"); player_identity_state(&p);out(",\"strings\":");entity_strings(sp);out("}");
 check(!memcmp(&p,&pb,sizeof(p)) && !memcmp(&s,&sb,sizeof(s)) && !memcmp(&t,&tb,sizeof(t)));
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
                                  text=True, timeout=15) for i in range(28)]
        for i, result in enumerate(results):
            assert result.returncode == (3 if 3 <= i <= 14 else 0), (i, result.returncode, result.stderr)
        values = {i: json.loads(result.stdout) for i, result in enumerate(results) if result.returncode == 0}
        token = dict(name='Token"\n\xff', value=-7)
        p = dict(title_the=31, title_the_text='The', title_common='Common', title_origin='Origin',
                 title_special='Special', title_colors_u32=[0xffffffff, 0x80000000],
                 title_badge_u32=0xffffffff, workshop='Workshop', reward_tokens=[token, None, dict(name=None, value=0)],
                 active_player_reward_tokens=[None, token],pvp_switch=1,is_ganker=1,
                 combat_monitor=[dict(key=71,order=0)]+[dict(key=0,order=0) for _ in range(8)]+[dict(key=-1,order=15)])
        assert values[0] == dict(player=p, strings=dict(description='Description\n\xff', motto='Motto"'))
        assert values[1]['strings'] is None
        assert values[2]['player']['reward_tokens'] == values[2]['player']['active_player_reward_tokens'] == []
        assert values[15] == values[22] == values[0]  # local clocks/pointer identity never hashed
        changed = values[16]
        assert changed['player']['reward_tokens'][0]['value'] == changed['player']['active_player_reward_tokens'][1]['value'] == 17
        changed['player']['reward_tokens'][0]['value'] = changed['player']['active_player_reward_tokens'][1]['value'] = -7
        assert changed == values[0]
        assert len(values[17]['player']['reward_tokens']) == 8192
        assert values[17]['player']['reward_tokens'][-1] == token
        assert len(values[18]['player']['active_player_reward_tokens']) == 8192
        assert values[18]['player']['active_player_reward_tokens'][-1] == dict(name=None, value=0)
        for mode, group, field, replacement in [(19,'player','title_colors_u32',[0xffffffff,17]),
                (20,'player','workshop','Changed'),(21,'strings','motto','Changed')]:
            assert values[mode][group][field] == replacement
            values[mode][group][field] = values[0][group][field]
            assert values[mode] == values[0]
        assert values[23]['strings']['description'] == 'X' * 1023
        assert values[24]['strings'] == dict(description='', motto='')
        assert values[24]['player']['title_colors_u32'] == [0, 0]
        for mode, field, value in [(25,'key',17),(26,'order',3)]:
            assert values[mode]['player']['combat_monitor'][-1][field] == value
            values[mode]['player']['combat_monitor'][-1][field] = values[0]['player']['combat_monitor'][-1][field]
            assert values[mode] == values[0]
        assert values[27]['player']['pvp_switch'] == values[27]['player']['is_ganker'] == 0
    print('player identity writer: ordered/null reward lists, literal titles/descriptions, high-bit colors/badge, PvP flags, all 10 combat-monitor slots, full-bound strings, mutation sensitivity, source immutability, pointer/timer exclusion and count/output bounds pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
