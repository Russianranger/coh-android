#!/usr/bin/env python3
"""Exercise actual retained-supergroup writer with bounded host fixtures.

Task payload formatting has its own actual-writer control; this fixture checks
that the supergroup writer forwards the retained mission, including null.
Fixture structs/earrays are not native ABI qualification.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    fixed = source[source.index('static void fixed_string('):source.index('static void group_members(')]
    writer = source[source.index('static void entity_supergroup_state('):source.index('static unsigned deletes;')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024*1024)
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { const char *reward; int val; unsigned timer; } RewardToken;
typedef struct { int id; const char *pchName; } DetailRecipe, Detail;
typedef struct { const DetailRecipe *recipe; unsigned count; } RecipeInvItem;
typedef struct { const Detail *pDetail; unsigned creation_time, expiration_time, iFlags; int bValid; } SpecialDetail;
typedef struct { int context; } TaskStatus;
typedef struct { int spacesForItemsOfPower; TaskStatus *sgMission; RewardToken **rewardTokens;
 RecipeInvItem **invRecipes; SpecialDetail **specialDetails; } Supergroup;
typedef struct { Supergroup *supergroup; int supergroup_id; char supergroup_name[64],
 supergroup_emblem[128]; unsigned supergroup_color[2]; } Entity;
static int eaSize(const void *address) {
 void *items; memcpy(&items,address,sizeof(items));
 return items ? (int)((size_t *)items)[-1] : 0;
}
''' + formatting + fixed + r'''
static void task_state(const TaskStatus *t) {
 if (!t) out("null"); else out("{\"fixture_context\":%d}",t->context);
}
''' + writer + r'''
int main(int argc, char **argv) {
 int mode = argc > 1 ? atoi(argv[1]) : 0;
 RewardToken token = {"Token\"\n\377",-7,0xffffffffU}, empty_token={NULL,0,0}, token_before;
 DetailRecipe recipe={81,"Recipe"}; RecipeInvItem item={&recipe,0xffffffffU}, null_recipe={NULL,0};
 Detail detail={93,"Detail"}; SpecialDetail special={&detail,0x80000000U,0xffffffffU,0x80000001U,1}, null_detail={NULL,0,0,0,0}, special_before;
 TaskStatus mission={135};
 struct {size_t n; RewardToken *v[8192];} tokens={3,{&token,NULL,&empty_token}};
 struct {size_t n; RecipeInvItem *v[3];} recipes={3,{NULL,&item,&null_recipe}};
 struct {size_t n; SpecialDetail *v[3];} details={3,{&special,&null_detail,NULL}};
 Supergroup sg={9,&mission,tokens.v,recipes.v,details.v}, sg_before;
 Entity e={&sg,47,"Group\"","Emblem",{0x80000000U,0xffffffffU}}, before;
 char alternate_name[128];
 if(mode==1) e.supergroup=NULL;
 if(mode==2) sg.rewardTokens=NULL,sg.invRecipes=NULL,sg.specialDetails=NULL,sg.sgMission=NULL;
 if(mode==3) tokens.n=8193;
 if(mode==4) recipes.n=8193;
 if(mode==5) details.n=8193;
 if(mode==6) tokens.n=(size_t)-1;
 if(mode==7) recipes.n=(size_t)-1;
 if(mode==8) details.n=(size_t)-1;
 if(mode==9) memset(e.supergroup_name,'X',sizeof(e.supergroup_name));
 if(mode==10) memset(e.supergroup_emblem,'X',sizeof(e.supergroup_emblem));
 if(mode==11) token.timer=17;
 if(mode==12) item.count=17;
 if(mode==13) special.expiration_time=17;
 if(mode==14) special.bValid=0;
 if(mode==15) tokens.n=8192,tokens.v[8191]=&token;
 if(mode==16) used=CAPACITY-2;
 if(mode==17) strcpy(alternate_name,recipe.pchName),recipe.pchName=alternate_name;
 before=e; sg_before=sg; token_before=token; special_before=special;
 entity_supergroup_state(&e);
 check(!memcmp(&before,&e,sizeof(e)) && !memcmp(&sg_before,&sg,sizeof(sg)));
 check(!memcmp(&token_before,&token,sizeof(token)) && !memcmp(&special_before,&special,sizeof(special)));
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
                                  text=True, timeout=15) for i in range(18)]
        rejected = {3, 4, 5, 6, 7, 8, 9, 10, 16}
        for i, result in enumerate(results):
            assert result.returncode == (3 if i in rejected else 0), (i, result.returncode, result.stderr)
        d = json.loads(results[0].stdout)
        assert d['id'] == 47 and d['name'] == 'Group"' and d['emblem'] == 'Emblem'
        assert d['colors_u32'] == [0x80000000, 0xffffffff]
        retained = d['retained']
        assert retained['spaces_for_items_of_power'] == 9
        assert retained['mission'] == {'fixture_context': 135}
        assert retained['reward_tokens'] == [dict(name='Token"\n\xff', value=-7, received_time=0xffffffff),
                                             None, dict(name=None, value=0, received_time=0)]
        assert retained['recipes'] == [None, dict(count_u32=0xffffffff, recipe=dict(id=81, name='Recipe')),
                                       dict(count_u32=0, recipe=None)]
        assert retained['special_details'] == [dict(creation_time=0x80000000, expiration_time=0xffffffff,
            flags=0x80000001, detail=dict(id=93, name='Detail')), dict(creation_time=0, expiration_time=0, flags=0, detail=None), None]
        absent = json.loads(results[1].stdout); absent['retained'] = retained
        assert absent == d
        assert json.loads(results[2].stdout)['retained'] == dict(spaces_for_items_of_power=9, mission=None,
            reward_tokens=[], recipes=[], special_details=[])
        for mode, key, field in [(11, 'reward_tokens', 'received_time'), (12, 'recipes', 'count_u32'),
                                 (13, 'special_details', 'expiration_time')]:
            changed = json.loads(results[mode].stdout)
            index = 1 if mode == 12 else 0
            assert changed['retained'][key][index][field] == 17
            changed['retained'][key][index][field] = 0xffffffff
            assert changed == d
        assert results[14].stdout == results[0].stdout == results[17].stdout
        maximum = json.loads(results[15].stdout)['retained']['reward_tokens']
        assert len(maximum) == 8192 and maximum[-1] == retained['reward_tokens'][0]
    print('supergroup writer: metadata, mission forwarding, ordered/null tokens/recipes/details, U32 sentinels/timestamps, logical identities, source immutability, 8192 boundary, malformed counts/fixed strings/output rejection pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
