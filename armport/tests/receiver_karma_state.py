#!/usr/bin/env python3
"""Exercise the original karma receiver and actual state writer with host fixtures."""
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
    writer = source[source.index('static void karma_receive_state('):source.index('static void power_customization_list(')]
    native = (args.source / 'Game/src/UI/uiNet.c').read_text()
    start = native.index('void receiveKarmaStats(')
    receiver = native[start:native.index('\n////////////////////////////////////////////////////////////////', start)]
    enums = (args.source / 'Common/storyarc/ScriptUIEnum.h').read_text()
    enums = enums[enums.index('typedef enum ScriptUIType'):enums.index('} ScriptUIType;') + len('} ScriptUIType;')]
    fixture = r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY (1024*1024)
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
''' + enums + r'''
typedef struct { int type; void *tooltip; char **varList; unsigned *packetOrder,uniqueID; unsigned showHours:1,hidden:1; } ScriptUIClientWidget;
static ScriptUIClientWidget **scriptUIKarmaWidgetList;
typedef struct { size_t size; void *items[8192]; } Array;
static int eaSize(const void *address) {
 void **items;memcpy(&items,address,sizeof(items));
 return items ? (int)((size_t *)items)[-1] : 0;
}
static void push(void *address, void *value) {
 void **items; Array *a;memcpy(&items,address,sizeof(items));
 a=items ? (Array *)((size_t *)items-1) : calloc(1,sizeof(*a));
 assert(a && a->size<8192);a->items[a->size++]=value;items=a->items;memcpy(address,&items,sizeof(items));
}
#define eaPush(p,v) push(p,v)
static void eaDestroy(void *address) {
 void **items;memcpy(&items,address,sizeof(items));
 if(items) free((size_t *)items-1);items=NULL;memcpy(address,&items,sizeof(items));
}
static ScriptUIClientWidget *ScriptUIClientWidgetFromId(ScriptUIClientWidget **items,unsigned id) {
 int i;for(i=0;i<eaSize(&items);++i) if(items[i] && items[i]->uniqueID==id)return items[i];return NULL;
}
static void ScriptUIDestroyWidget(ScriptUIClientWidget *w) {
 int i;if(!w)return;for(i=0;i<eaSize(&w->varList);++i) free(w->varList[i]);eaDestroy(&w->varList);free(w);
}
typedef struct { unsigned values[11]; int cursor; } Packet;
static unsigned pktGetBits(Packet *p,int bits) {assert(bits==1);return p->values[p->cursor++];}
static unsigned pktGetBitsAuto(Packet *p) {assert(p->cursor<11);return p->values[p->cursor++];}
#define _snprintf_s(b,n,max,fmt,value) snprintf(b,n,fmt,value)
''' + formatting + writer + receiver + r'''
static void clear(void) { Packet p={{0},0};receiveKarmaStats(&p);assert(p.cursor==1); }
int main(int argc,char **argv) {
 int mode=argc>1?atoi(argv[1]):0,i;ScriptUIClientWidget copy;
 Packet p={{1,9,0,1,2,3,4,5,6,2147483647U,0xffffffffU},0};
 if(mode==1) p.values[1]=0;
 receiveKarmaStats(&p);assert(p.cursor==(mode==1?2:11));
 if(mode==2) { Packet q={{1,2,99,17},0};receiveKarmaStats(&q);assert(q.cursor==4); }
 if(mode==3) clear();
 if(mode==4) { eaPush(&scriptUIKarmaWidgetList,NULL);eaPush(&scriptUIKarmaWidgetList[2]->varList,NULL);eaPush(&scriptUIKarmaWidgetList[2]->varList,strdup("quote\"\\\200\n")); }
 if(mode==5) ((size_t *)scriptUIKarmaWidgetList)[-1]=8193;
 if(mode==6) ((size_t *)scriptUIKarmaWidgetList)[-1]=(size_t)-1;
 if(mode==7) ((size_t *)scriptUIKarmaWidgetList[2]->varList)[-1]=8193;
 if(mode==8) ((size_t *)scriptUIKarmaWidgetList[2]->varList)[-1]=(size_t)-1;
 if(mode==9) used=CAPACITY-2;
 if(mode==10) { scriptUIKarmaWidgetList[2]->tooltip=&p;scriptUIKarmaWidgetList[2]->packetOrder=p.values;scriptUIKarmaWidgetList[2]->showHours=1; }
 if(mode==11) { ScriptUIClientWidget *w=scriptUIKarmaWidgetList[2];scriptUIKarmaWidgetList[2]=scriptUIKarmaWidgetList[10];scriptUIKarmaWidgetList[10]=w; }
 if(mode==12) scriptUIKarmaWidgetList[10]->type=71,scriptUIKarmaWidgetList[10]->uniqueID=0x80000000U;
 if(mode==13) { char *large=malloc(CAPACITY+1);memset(large,'z',CAPACITY);large[CAPACITY]=0;free(scriptUIKarmaWidgetList[2]->varList[1]);scriptUIKarmaWidgetList[2]->varList[1]=large; }
 if(eaSize(&scriptUIKarmaWidgetList)>2) copy=*scriptUIKarmaWidgetList[2];
 karma_receive_state();
 if(eaSize(&scriptUIKarmaWidgetList)>2) assert(!memcmp(&copy,scriptUIKarmaWidgetList[2],sizeof(copy)));
 /* Repeating the read must preserve all source strings, counts and array order. */
 { char *first=strdup(buffer);used=0;karma_receive_state();assert(!strcmp(first,buffer));free(first); }
 puts(buffer);clear();return 0;
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
            assert result.returncode == (3 if i in (5,6,7,8,9,13) else 0), (i,result.returncode,result.stderr)
        values = {i: json.loads(r.stdout) for i,r in enumerate(results) if r.returncode == 0}
        names=['PowerClick','BuffPowerClick','TeamObjComplete','AllPlayObjComplete',
               'CurrentTotal','Median','Average','ActiveKarmaPlayers','NumBubbles']
        numbers=['0','1','2','3','4','5','6','2147483647','-1']
        expected=[dict(type=4,id=0xffffffff,variables=['Karma','Karma']),
                  dict(type=5,id=0xfffffffe,variables=['KarmaList','KarmaList'])]
        expected += [dict(type=11,id=i,variables=[name,numbers[i]]) for i,name in enumerate(names)]
        assert values[0]==expected and values[1]==[] and values[3]==[]
        changed=json.loads(json.dumps(expected))
        changed[2]['variables'][1]='99';changed[3]['variables'][1]='17'
        assert values[2]==changed  # Original short update retains the later widgets.
        assert values[4][-1] is None and values[4][2]['variables']==['PowerClick','0',None,'quote"\\\x80\n']
        assert values[10]==expected
        changed=json.loads(json.dumps(expected));changed[2],changed[10]=changed[10],changed[2]
        assert values[11]==changed
        assert values[12][-1]==dict(type=71,id=0x80000000,variables=['NumBubbles','-1'])
    print('karma original receiver/actual writer: 14 cases pass; create/update/short-update retention/clear, ordered/null widgets and variables, unsigned sentinel identities, raw escaped strings, final slot, local cache exclusion, source immutability, invalid count/output bounds; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
