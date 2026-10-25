#!/usr/bin/env python3
"""Run original buff receiving/updating and the const view/snapshot under sanitizers."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile

from receiver_tray_state import function


def check_build_guard(source, native, header):
    """Preprocess the actual ordered includes and guarded view, without fixture defines."""
    includes = re.findall(r'^#include "(?:clientcomm/armport_replay.h|UI/uiBuff.h)"$',
                          native, re.MULTILINE)
    start = native.index('#ifdef COH_ARMPORT_REPLAY')
    block = native[start:native.index('#endif', start) + len('#endif')]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root/'UI').mkdir()
        (root/'clientcomm').mkdir()
        (root/'UI/uiBuff.h').write_text(header)
        (root/'UI/comm_game.h').write_text('/* unrelated dependency omitted for preprocessing */\n')
        (root/'clientcomm/armport_replay.h').write_bytes(
            (source/'Game/src/clientcomm/armport_replay.h').read_bytes())
        def preprocess(lines, defines):
            return subprocess.run([os.environ.get('CC', 'cc'), '-E', '-P', '-x', 'c',
                                   '-I', str(root), *defines, '-'],
                                  input='\n'.join(lines)+'\n'+block,
                                  capture_output=True, text=True, check=True).stdout
        for defines in (['-D__aarch64__', '-D__MINGW32__'],
                        ['-DCOH_ARMPORT_REFERENCE_I686']):
            text = preprocess(includes, defines)
            assert 'typedef struct ArmPortReplayBuffView' in text
            for name in ('armportReplayBuffCount', 'armportReplayBuffAt'):
                assert len(re.findall(r'\b'+name+r'\s*\(', text)) == 2, name
            # The old missing include hides both declarations and definitions.
            old = preprocess([line for line in includes if 'armport_replay.h' not in line], defines)
            assert 'armportReplayBuffCount' not in old
        off = preprocess(includes, [])
        assert 'armportReplayBuffCount' not in off
    print('buff build guard: ARM64/i686 declarations and definitions enabled; normal build and missing-include negative controls disabled')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    source=parser.parse_args().source
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    native=(source/'Game/src/UI/uiBuff.c').read_text()
    header=(source/'Game/src/UI/uiBuff.h').read_text()
    check_build_guard(source, native, header)
    receiver=(source/'Game/src/entity/character_net_client.c').read_text()
    fixture=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>
#define CAPACITY 32768
#define check(x) do {if(!(x)) _Exit(3);} while(0)
typedef unsigned U32;typedef float F32;
typedef struct ToolTip {int ignored;} ToolTip;
typedef struct BasePower {const char *pchFullName;} BasePower;
typedef struct AttribDescription {int iKey;const char *pchName;} AttribDescription;
typedef struct PowerBuff PowerBuff;
typedef struct Entity {PowerBuff **ppowBuffs;} Entity;
/* A bounded arena owns fixture arrays; this is not an ownership/leak test. */
typedef struct Array {size_t count,width;union {double d;void *p;} alignment;unsigned char bytes[4096];} Array;
static Array *arena[128];static int allocations,forced_count=-1;static const void *forced_array;
static Array *array_header(const void *a){return a?(Array*)((char*)a-offsetof(Array,bytes)):NULL;}
static unsigned arena_hash(void){unsigned h=2166136261U;int i;size_t j;for(i=0;i<allocations;++i)for(j=0;j<sizeof(*arena[i]);++j)h=(h^((unsigned char*)arena[i])[j])*16777619U;return h;}
static int array_size(const void *a){if(a&&a==forced_array)return forced_count;return a?(int)array_header(a)->count:0;}
static void *array_new(size_t width){Array*a=calloc(1,sizeof(*a));assert(a&&allocations<128);a->width=width;arena[allocations++]=a;return a->bytes;}
static void array_push(void **p,const void *value,size_t width){Array*a;if(!*p)*p=array_new(width);a=array_header(*p);assert(a->width==width&&(a->count+1)*width<=sizeof(a->bytes));memcpy(a->bytes+a->count++*width,value,width);}
static void array_copy(void **dst,const void *src){if(!src){*dst=NULL;return;}Array*a=array_header(src);*dst=array_new(a->width);array_header(*dst)->count=a->count;memcpy(*dst,src,a->count*a->width);}
static void array_destroy(void **p){*p=NULL;}
static void *array_remove(void **p,int i){void*v=((void**)*p)[i];Array*a=array_header(*p);assert(i>=0&&(size_t)i<a->count);--a->count;memmove((void**)*p+i,(void**)*p+i+1,(a->count-i)*a->width);return v;}
static void push_ptr(void **p,void *v){array_push(p,&v,sizeof(v));}
static void push_float(void **p,float v){array_push(p,&v,sizeof(v));}
#define eaSize(p) array_size(*(p))
#define eafSize(p) array_size(*(p))
#define eaPush(p,v) push_ptr((void**)(p),(void*)(v))
#define eafPush(p,v) push_float((void**)(p),(v))
#define eaDestroy(p) array_destroy((void**)(p))
#define eafDestroy(p) array_destroy((void**)(p))
#define eaCopy(p,v) array_copy((void**)(p),*(v))
#define eafCopy(p,v) array_copy((void**)(p),*(v))
#define eaRemove(p,i) array_remove((void**)(p),(i))
static Entity player;static int player_present=1,player_reads;
static Entity *playerPtr(void){++player_reads;return player_present?&player:NULL;}
static int g_PowerDictionary;
static BasePower power={"Primary.Set.Power"};
static AttribDescription descriptions[2]={{11,"Damage"},{22,"Speed"}};
static AttribDescription *attribDescriptionGet(int key){return key==11?&descriptions[0]:key==22?&descriptions[1]:NULL;}
typedef struct Packet {unsigned numbers[32];int count,cursor;} Packet;
static unsigned take(Packet*p){assert(p->cursor<p->count);return p->numbers[p->cursor++];}
static unsigned pktGetBits(Packet*p,int n){assert(n==1);return take(p);}
static unsigned pktGetBitsPack(Packet*p,int n){assert(n==4||n==5||n==10||n==20);return take(p);}
static int pktEnd(Packet*p){return p->cursor==p->count;}
static const BasePower *basepower_Receive(Packet*p,void*d,Entity*e){(void)d;(void)e;return take(p)?&power:NULL;}
static char buffer[CAPACITY];static size_t used;
'''
    fixture+=native[native.index('typedef struct PowerBuff'):native.index('}PowerBuff;')+len('}PowerBuff;')]
    fixture+='\n'+header[header.index('typedef struct ArmPortReplayBuffView'):header.index('int armportReplayBuffCount')]
    for signature in ['PowerBuff * findPowerBuff(', 'void addUpdatePowerBuff(', 'void markPowerBuff(', 'void markBuffForDeletion(']:
        fixture+=function(native,signature)
    fixture+='static void freePowerBuff(void *buff){free(buff);}\n'  # UI/ownership dependency substituted explicitly
    fixture+=function(native,'void clearMarkedPowerBuff(')
    fixture+=function(receiver,'void character_ReceiveBuffs(')
    for signature in ['int armportReplayBuffCount(', 'int armportReplayBuffAt(']:
        fixture+=function(native,signature)
    fixture+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    fixture+=function(state,'static void base_power(')+function(state,'static void entity_buff_state(')
    fixture+=r'''
int main(int argc,char **argv){
 unsigned storage_before;int mode=argc>1?atoi(argv[1]):0,i,j,reads,count;Entity e={0},saved;PowerBuff old[4];
 AttribDescription **initial_desc=NULL;float *initial_mag=NULL;ArmPortReplayBuffView untouched,before;
 Packet p={{0,0,1,1,1,1,7,1,2,125,11,(unsigned)-250,22},13,0};
 eaPush(&initial_desc,&descriptions[1]);eafPush(&initial_mag,2.0f);addUpdatePowerBuff(&e,&power,0,7,initial_desc,initial_mag);
 if(mode==2||mode==3||mode==9)p=(Packet){{0,1,1,0,1,1,0,7,0},9,0};
 if(mode==3)p.numbers[3]=1;
 if(mode==4||mode==5)p=(Packet){{1},1,0};
 if(mode==6)p.numbers[3]=0;
 if(mode==7)player_present=0;
 if(mode==8)p.numbers[6]=8;
 if(mode==9)p.numbers[7]=8;
 if(mode==10)p=(Packet){{0,0,1},3,0};
 if(mode==19)p.numbers[12]=999;
 character_ReceiveBuffs(&p,&e,mode==1||mode==5);assert(p.cursor==p.count);
 if(mode==11)eaPush(&e.ppowBuffs,NULL);
 if(mode==12){e.ppowBuffs[0]->ppow=NULL;e.ppowBuffs[0]->ppDesc[0]=NULL;}
 if(mode==13)array_header(e.ppowBuffs[0]->ppDesc)->count=1;
 if(mode==14)forced_array=e.ppowBuffs,forced_count=8193;
 if(mode==15)used=CAPACITY-1;
 if(mode==16)forced_array=e.ppowBuffs[0]->ppfMag,forced_count=8193;
 if(mode==17)e.ppowBuffs[0]->ppDesc=NULL;
 if(mode==20)e.ppowBuffs[0]->timer=999,e.ppowBuffs[0]->window=45,e.ppowBuffs[0]->tip.ignored=876;
 memset(&untouched,0x5a,sizeof(untouched));before=untouched;
 assert(armportReplayBuffAt(NULL,0,&untouched)==-1&&armportReplayBuffAt(&e,-1,&untouched)==-1&&armportReplayBuffAt(&e,10000,&untouched)==-1&&armportReplayBuffAt(&e,0,NULL)==-1&&!memcmp(&before,&untouched,sizeof(before)));
 count=(int)array_header(e.ppowBuffs)->count;assert(count<=4);saved=e;reads=player_reads;
 for(i=0;i<count;++i)if(e.ppowBuffs[i])old[i]=*e.ppowBuffs[i];
 storage_before=arena_hash();
 if(mode==11)assert(armportReplayBuffAt(&e,1,&untouched)==0&&!memcmp(&before,&untouched,sizeof(before)));
 entity_buff_state(mode==18?NULL:&e);
 assert(storage_before==arena_hash());
 assert(!memcmp(&e,&saved,sizeof(e))&&reads==player_reads);
 for(i=0;i<count;++i)if(e.ppowBuffs[i]){assert(!memcmp(&old[i],e.ppowBuffs[i],sizeof(old[i])));free(e.ppowBuffs[i]);}
 puts(buffer);for(j=0;j<allocations;++j)free(arena[j]);return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        path=Path(temporary);(path/'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'fixture.c'),'-o',str(path/'fixture')],check=True)
        values={}
        for i in range(21):
            result=subprocess.run([str(path/'fixture'),str(i)],capture_output=True,text=True,timeout=15)
            assert result.returncode==(3 if i in (14,15,16) else 0),(i,result.returncode,result.stderr)
            if result.returncode==0:values[i]=json.loads(result.stdout)
        new=dict(power='Primary.Set.Power',uid=7,blink=3,delete_mark=0,descriptions=[dict(key=11,name='Damage'),dict(key=22,name='Speed')],magnitude_f32_bits=[0x3fa00000,0xc0200000])
        old=dict(new,blink=0,descriptions=[dict(key=22,name='Speed')],magnitude_f32_bits=[0x40000000])
        assert values[0]==values[20]==[new]
        assert values[1]==[dict(old,delete_mark=1)] # original marks full stale packets before oo_data check
        assert values[2]==[dict(old,blink=2)]
        for i in (3,4,6,7,10,18):assert values[i]==[],(i,values[i])
        assert values[5]==[old]
        assert values[8]==[dict(new,uid=8)]
        assert values[9]==[old,dict(new,uid=8,blink=2,descriptions=[],magnitude_f32_bits=[])]
        assert values[11]==[new,None]
        assert values[12]==[dict(new,power=None,descriptions=[None,new['descriptions'][1]])]
        assert values[13]==[dict(new,descriptions=new['descriptions'][:1])]
        assert values[17]==[dict(new,descriptions=[])]
        assert values[19]==[dict(new,descriptions=new['descriptions'][:1],magnitude_f32_bits=new['magnitude_f32_bits'][:1])]
    print('buff state original receiver/update/find/mark/clear and actual view/writer: 21 cases pass; full/diff/delete/stale/no-player/unknown-descriptor paths, retained absent mods, order/nulls/mismatched arrays, F32 bits, bounds, const views and timer/UI exclusion; ASan/UBSan enabled; fixture arena and free substitute do not qualify ownership')


if __name__=='__main__':main()
