#!/usr/bin/env python3
"""Exercise actual clue writers and the patched read-only server souvenir view."""
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
    story = source[source.index('static void story_clues('):source.index('static void task_difficulty(')]
    ui = (args.source / 'Game/src/UI/uiClue.c').read_text()
    start = ui.index('const SouvenirClue *const *armportReplaySouvenirClues(void)')
    assert ui[start - len('#ifdef COH_ARMPORT_REPLAY\n'):start] == '#ifdef COH_ARMPORT_REPLAY\n'
    view = ui[start:ui.index('\n#endif', start)]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 1048576
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { char *filename, *name, *displayname, *introstring, *detailtext, *iconfile; } StoryClue;
typedef struct { int uid; const char *filename, *name, *displayName, *icon, *description; } SouvenirClue;
static StoryClue **storyClues, **keyClues;
static char **visitLocations;
static struct { SouvenirClue **souvenirClues; } souvenirData[2];
static void *array_addresses[4]; static int counts[4]={3, 2, 3, 3};
static int size(const void *array) {
    int i; if (!array) return 0;
    for(i=0;i<4;++i) if(array_addresses[i]==array) return counts[i];
    exit(4);
}
#define eaSize(p) size(*(p))
''' + formatting + view + story + r'''
int main(int argc, char **argv) {
    int mode=argc>1?atoi(argv[1]):0;
    StoryClue clue={0}, key={0}, before;
    StoryClue *stories[]={&clue,NULL,&clue}, *keys[]={NULL,&key};
    SouvenirClue souvenir={0}, local={0}, souvenir_before;
    SouvenirClue *souvenirs[]={NULL,&souvenir,&souvenir}, *locals[]={&local};
    char *locations[]={"Atlas\nPark",NULL,""};
    clue.name="clue"; clue.filename=""; clue.displayname="escaped\"\\";
    clue.introstring="intro"; clue.detailtext="\200\n"; clue.iconfile="icon";
    key.name="key"; souvenir.uid=31; souvenir.displayName="Souvenir"; souvenir.description="server detail";
    local.uid=999; local.description="local file must not be observed";
    storyClues=stories; keyClues=keys; visitLocations=locations;
    souvenirData[0].souvenirClues=souvenirs; souvenirData[1].souvenirClues=locals;
    array_addresses[0]=stories; array_addresses[1]=keys;
    array_addresses[2]=souvenirs; array_addresses[3]=locations;
    if(mode==1) souvenir.description="changed detail";
    if(mode==2) key.name="changed key";
    if(mode==3) storyClues=NULL, keyClues=NULL, visitLocations=NULL, souvenirData[0].souvenirClues=NULL;
    if(mode==4) counts[0]=8193;
    if(mode==5) counts[2]=-1;
    if(mode==6) counts[3]=8193;
    if(mode==7) local.uid=7, local.description="different local content";
    if(mode==8) {
        static char large[CAPACITY+1];
        memset(large,'z',CAPACITY); large[CAPACITY]=0; clue.detailtext=large;
    }
    before=clue; souvenir_before=souvenir;
    story_receive_state();
    check(!memcmp(&before,&clue,sizeof(clue)) && !memcmp(&souvenir_before,&souvenir,sizeof(souvenir)));
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
        for i in (0, 1, 2, 3, 7):
            assert results[i].returncode == 0, (i, results[i].stderr)
        for i in (4, 5, 6, 8):
            assert results[i].returncode == 3, (i, results[i].stderr)
        d = json.loads(results[0].stdout)
        assert d['clues'][1] is None and d['clues'][0] == d['clues'][2]
        assert d['clues'][0] == dict(name='clue', filename='', display_name='escaped"\\',
                                    intro='intro', detail='\x80\n', icon='icon')
        assert d['key_clues'][0] is None and d['key_clues'][1]['name'] == 'key'
        assert d['server_souvenirs'] == [None] + [dict(uid=31, name=None, filename=None,
            display_name='Souvenir', icon=None, description='server detail')] * 2
        assert d['visit_locations'] == ['Atlas\nPark', None, '']
        changed = json.loads(results[1].stdout)
        assert changed['server_souvenirs'][2]['description'] == 'changed detail'
        assert json.loads(results[2].stdout)['key_clues'][1]['name'] == 'changed key'
        assert json.loads(results[3].stdout) == dict(clues=[], key_clues=[], server_souvenirs=[], visit_locations=[])
        assert results[7].stdout == results[0].stdout
    print('story serializer: ordered/null clue, key, server-souvenir and visit-location arrays; '
          'full strings/raw byte escapes, server-only accessor, mutation sensitivity and '
          'invalid count/output-size rejection pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
