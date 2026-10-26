#!/usr/bin/env python3
"""Exercise actual retained power-customization writer under ASan/UBSan."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    identity = source[source.index('static void base_power('):source.index('static void boost(')]
    writer = source[source.index('static void power_customization_list('):source.index('static void player_receive_core(')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024*1024)
#define MAX_COSTUMES 10
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { const char *pchFullName; } BasePower;
typedef union { unsigned integer; unsigned char rgba[4]; } Color;
typedef struct { Color primary, secondary; } ColorPair;
typedef struct { const char *powerFullName; const BasePower *power; ColorPair customTint; const char *token; } PowerCustomization;
typedef struct { PowerCustomization **powerCustomizations; } PowerCustomizationList;
typedef struct { int current_powerCust; PowerCustomizationList *powerCustomizationLists[10]; } EntPlayer;
typedef struct { PowerCustomizationList *powerCust, *ownedPowerCustomizationList; EntPlayer *pl; } Entity;
static int eaSize(const void *address) {
 void *items; memcpy(&items,address,sizeof(items));
 return items ? (int)((size_t *)items)[-1] : 0;
}
''' + formatting + identity + writer + r'''
int main(int argc, char **argv) {
 int mode = argc > 1 ? atoi(argv[1]) : 0;
 BasePower power={"Primary.Set.Power"}, alternate=power;
 PowerCustomization c={"StoredName",&power,{{0x80000000U},{0xffffffffU}},"Token\n\"\377"}, empty={NULL,NULL,{{0},{1}},NULL}, before;
 struct {size_t n; PowerCustomization *v[8192];} array={3,{&c,NULL,&empty}};
 PowerCustomizationList list={array.v}, empty_list={NULL};
 EntPlayer p={9,{&list,NULL,NULL,NULL,NULL,NULL,NULL,NULL,&empty_list,&list}}, p_before;
 Entity e={&list,&empty_list,&p}, e_before;
 if(mode==1) c.customTint.secondary.integer=17;
 if(mode==2) c.power=&alternate;
 if(mode==3) array.n=8193;
 if(mode==4) array.n=(size_t)-1;
 if(mode==5) e.powerCust=e.ownedPowerCustomizationList=NULL,e.pl=NULL;
 if(mode==6) used=CAPACITY-2;
 if(mode==7) array.n=8192,array.v[8191]=&c;
 if(mode==8) array.v[0]=&empty,array.v[2]=&c;
 if(mode==9) p.powerCustomizationLists[9]=NULL;
 if(mode==10) c.token="Different";
 if(mode==11) list.powerCustomizations=NULL;
 before=c; p_before=p; e_before=e;
 entity_power_customizations(&e);
 check(!memcmp(&before,&c,sizeof(c)) && !memcmp(&p_before,&p,sizeof(p)) && !memcmp(&e_before,&e,sizeof(e)));
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
                                  text=True, timeout=15) for i in range(12)]
        for i, result in enumerate(results):
            assert result.returncode == (3 if i in (3, 4, 6) else 0), (i, result.returncode, result.stderr)
        d = json.loads(results[0].stdout)
        item = dict(full_name='StoredName', power='Primary.Set.Power', primary_rgba_u32=0x80000000,
                    secondary_rgba_u32=0xffffffff, token='Token\n"\xff')
        empty = dict(full_name=None, power=None, primary_rgba_u32=0, secondary_rgba_u32=1, token=None)
        assert d['active'] == [item, None, empty] and d['owned'] == []
        assert d['player'] == dict(current=9, slots=[d['active']] + [None]*7 + [[], d['active']])
        assert results[2].stdout == results[0].stdout
        assert json.loads(results[5].stdout) == dict(active=None, owned=None, player=None)
        for mode, key, value in [(1, 'secondary_rgba_u32', 17), (10, 'token', 'Different')]:
            changed = json.loads(results[mode].stdout)
            for array in (changed['active'], changed['player']['slots'][0], changed['player']['slots'][9]):
                assert array[0][key] == value
                array[0][key] = item[key]
            assert changed == d
        maximum = json.loads(results[7].stdout)
        assert len(maximum['active']) == 8192 and maximum['active'][-1] == item
        assert json.loads(results[8].stdout)['active'] == [empty, None, item]
        last_slot = json.loads(results[9].stdout)
        assert last_slot['player']['slots'][9] is None
        last_slot['player']['slots'][9] = d['active']; assert last_slot == d
        assert json.loads(results[11].stdout)['active'] == []
    print('power customization writer: active/owned/all ten player slots, null/empty/order, literal identity/token bytes, RGBA U32 values, source immutability, address independence, mutation sensitivity and count/output bounds pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
