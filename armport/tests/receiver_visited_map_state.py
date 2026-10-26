#!/usr/bin/env python3
"""Exercise the actual map accessor/writer with bounded host earray fixtures."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    writer = source[source.index('static void visited_map_state('):source.index('unsigned armportReplayStateSave(')]
    native = (args.source / 'Game/src/UI/uiAutomap.c').read_text()
    start = native.index('const VisitedStaticMap *const *armportReplayVisitedMaps(')
    accessor = native[start:native.index('#endif', start)]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024*1024)
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { int db_id,map_id,opaque_fog; unsigned cells[256]; } VisitedMap;
typedef struct { int db_id; VisitedMap **staticMaps; } VisitedStaticMap;
static VisitedStaticMap **g_vsm;
static int eaSize(const void *address) {
 void *items; memcpy(&items,address,sizeof(items));
 return items ? (int)((size_t *)items)[-1] : 0;
}
''' + formatting + accessor + writer + r'''
int main(int argc, char **argv) {
 int mode=argc>1?atoi(argv[1]):0;
 VisitedMap map={17,31,1,{0x80000000U}},empty={17,1,0,{0}},before;
 struct {size_t n; VisitedMap *v[8192];} maps={3,{&map,NULL,&empty}};
 VisitedStaticMap owner={17,maps.v},other={31,NULL},ob;
 struct {size_t n; VisitedStaticMap *v[8192];} owners={3,{&owner,NULL,&other}};
 VisitedStaticMap **original; const VisitedStaticMap *const *view;
 map.cells[255]=0xffffffffU;g_vsm=owners.v;
 if(mode==1) g_vsm=NULL;
 if(mode==2) owner.staticMaps=NULL;
 if(mode==3) owners.n=8193;
 if(mode==4) owners.n=(size_t)-1;
 if(mode==5) maps.n=8193;
 if(mode==6) maps.n=(size_t)-1;
 if(mode==7) map.cells[255]=17;
 if(mode==8) map.map_id=17;
 if(mode==9) map.db_id=31;
 if(mode==10) owner.db_id=31;
 if(mode==11) map.opaque_fog=0;
 if(mode==12) owners.n=8192,owners.v[8191]=&other;
 if(mode==13) maps.n=8192,maps.v[8191]=&empty;
 if(mode==14) used=CAPACITY-2;
 if(mode==15) maps.v[0]=&empty,maps.v[2]=&map;
 before=map;ob=owner;original=g_vsm;view=armportReplayVisitedMaps();
 check((const void *)view==(const void *)g_vsm);
 visited_map_state();
 check(g_vsm==original && !memcmp(&before,&map,sizeof(map)) && !memcmp(&ob,&owner,sizeof(owner)));
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
                                  text=True, timeout=15) for i in range(16)]
        for i, result in enumerate(results):
            assert result.returncode == (3 if i in (3,4,5,6,14) else 0), (i,result.returncode,result.stderr)
        values = {i: json.loads(r.stdout) for i,r in enumerate(results) if r.returncode == 0}
        map0=dict(db_id=17,map_id=31,opaque_fog=1,cells_u32=[0x80000000]+[0]*254+[0xffffffff])
        map1=dict(db_id=17,map_id=1,opaque_fog=0,cells_u32=[0]*256)
        expected=[dict(db_id=17,maps=[map0,None,map1]),None,dict(db_id=31,maps=[])]
        assert values[0]==expected and values[1]==[]
        assert values[2][0]['maps']==[]
        assert values[7][0]['maps'][0]['cells_u32'][-1]==17
        values[7][0]['maps'][0]['cells_u32'][-1]=0xffffffff
        assert values[7]==expected
        for mode,field,value in [(8,'map_id',17),(9,'db_id',31),(11,'opaque_fog',0)]:
            assert values[mode][0]['maps'][0][field]==value
            values[mode][0]['maps'][0][field]=map0[field]
            assert values[mode]==expected
        assert values[10][0]['db_id']==31 and values[10][0]['maps'][0]['db_id']==17
        assert len(values[12])==8192 and values[12][-1]==dict(db_id=31,maps=[])
        assert len(values[13][0]['maps'])==8192 and values[13][0]['maps'][-1]==map1
        assert values[15][0]['maps']==[map1,None,map0]
    print('visited-map actual accessor/writer: existing/null storage, original owner/map order, all 256 U32 words including final/high bits, literal IDs, source immutability, mutation sensitivity and 8192/count/output bounds pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
