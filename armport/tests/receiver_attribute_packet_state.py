#!/usr/bin/env python3
"""Observe original AttrDef packet-ID trees without changing receive decisions."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from receiver_tray_state import function


def fixture(source):
    lib=source/'libs/UtilitiesLib'
    header=(lib/'include/utilitieslib/utils/textparser.h').read_text()
    receiver=(lib/'src/utils/textparser.c').read_text()
    net=(lib/'src/utils/structNet.c').read_text()
    tables=(source/'Common/entity/attrib_net.c').read_text()
    state=(Path(__file__).resolve().parents[1]/'replay/state.c').read_text()
    code=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>
#define CAPACITY 32768
#define check(x) do {if(!(x)) _Exit(3);} while(0)
#define STATIC_ASSERT(x)
#define SIZEOF2(s,m) sizeof(((s*)0)->m)
#define PTR_TO_U32(p) ((uint32_t)(uintptr_t)(p))
#define U32_TO_PTR(v) ((void*)(uintptr_t)(uint32_t)(v))
#define SAFE_FREE(p) do {free(p);(p)=NULL;} while(0)
typedef float F32;typedef uintptr_t UINT_PTR;
typedef struct ParseTable {const char *name;unsigned type;size_t storeoffset,param;struct ParseTable *subtable;} ParseTable;
typedef ParseTable TokenizerParseInfo;
typedef struct CharacterAttributes {float fHitPoints,fAbsorb,fEndurance,fMeter,fStealthRadiusPlayer,fPerceptionRadius,fConfused,fToHit;} CharacterAttributes;
typedef struct Character {CharacterAttributes attrCur,attrMax;int iLevel,iCombatLevel,iExperiencePoints,iExperienceDebt,iExperienceRest,iInfluencePoints;} Character;
typedef struct Entity {void **pkt_id_fullAttrDef,**pkt_id_basicAttrDef;} Entity;
static char buffer[CAPACITY];static size_t used;
'''
    code+=header[header.index('#define TOK_TYPE_MASK'):header.index('// options for parsing')]
    code+=header[header.index('#define TOK_PRECISION_MASK'):header.index('// options for different parsing')]
    for name in ['TOK_INT','TOK_F32','TOK_EMBEDDEDSTRUCT','TOK_NULLSTRUCT','FORALL_PARSETABLE']:
        code+=re.search(r'^#define '+name+r'\([^\n]+',header,re.M).group(0)+'\n'
    code+=re.search(r'^#define TOK_REDUNDANTNAME[^\n]+',header,re.M).group(0)+'\n'
    code+='#define FORALL_PARSEINFO FORALL_PARSETABLE\n'
    code+=tables[tables.index('TokenizerParseInfo ParseBasic'):tables.index('/* End of File */')]
    code+=r'''
typedef struct Packet {unsigned id;int hasDebugInfo;int data[512],count,cursor;} Packet;
static int take(Packet*p){assert(p->cursor<p->count);return p->data[p->cursor++];}
static int pktGetBits(Packet*p,int n){assert(n==1);return take(p);}
static int pktGetBitsPack(Packet*p,int n){assert(n>0);return take(p);}
static int unpackDelta(Packet*p){return take(p);}
static float pktGetF32(Packet*p){return take(p);}
/* Quantization/token storage are substitutes: this checks IDs, not attribute values. */
static int ParserFloatMinBits(int a){return 1;}
static float ParserUnpackFloat(int v,int a){return (float)v;}
static int ParserPackFloat(float v,int a){return (int)v;}
static void TokenStoreSetInt(ParseTable*t,int c,void*s,int i,int v){*(int*)((char*)s+t[c].storeoffset)=v;}
static int TokenStoreGetInt(ParseTable*t,int c,void*s,int i){return *(int*)((char*)s+t[c].storeoffset);}
static void TokenStoreSetF32(ParseTable*t,int c,void*s,int i,float v){*(float*)((char*)s+t[c].storeoffset)=v;}
static float TokenStoreGetF32(ParseTable*t,int c,void*s,int i){return *(float*)((char*)s+t[c].storeoffset);}
static void *TokenStoreGetPointer(ParseTable*t,int c,void*s,int i){return (char*)s+t[c].storeoffset;}
static void *TokenStoreAlloc(ParseTable*t,int c,void*s,int i,size_t n,void*a,void*b){assert(0);return NULL;}
static void struct_destroystruct(ParseTable*t,int c,void*s,int i){memset((char*)s+t[c].storeoffset,0,t[c].param);}
static int ParseTableCountFields(ParseTable*t){int n;FORALL_PARSEINFO(t,n);return n;}
static const char *invalidName="invalid",*outOfSyncName="outOfSync";static bool s_inSync;int g_bAssertOnBitStreamError;
typedef struct TypeInfo {void(*recvdiff)(Packet*,ParseTable*,int,void*,int,int,void**);void(*freepktids)(ParseTable*,int,void**);} TypeInfo;
static TypeInfo types[NUM_TOK_TYPE_TOKENS];
#define TOKARRAY_INFO(t) types[TOK_GET_TYPE(t)]
void sdUnpackStruct(ParseTable*,Packet*,void*,void***,bool);
void ParserFreePktIds(ParseTable*,void***);
'''
    for prefix in ['void int_recvdiff(', 'void float_recvdiff(', 'void struct_recvdiff(', 'void struct_freepktids(']:
        code+=function(receiver,prefix)
    code+=function(net,'void sdUnpackStruct(')+function(net,'void ParserFreePktIds(')
    code+=state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code+=function(state,'static void attribute_packet_ids(')+function(state,'static void entity_attribute_packet_order_state(')
    code+=r'''
static void nopfree(ParseTable*t,int c,void**p){}
static void push(Packet*p,int v){assert(p->count<512);p->data[p->count++]=v;}
static void body(Packet*p,ParseTable*t,int absolute,int absent){
 int i;FORALL_PARSEINFO(t,i){push(p,1);push(p,i);
 if(TOK_GET_TYPE(t[i].type)==TOK_STRUCT_X){push(p,!absent);if(!absent){push(p,absolute);body(p,t[i].subtable,absolute,0);}}
 else push(p,5);
 }push(p,0);
}
static void recv(Entity*e,Character*c,unsigned id,int abs,int absent,int nodata){
 Packet p={.id=id};body(&p,SendCharacterToSelf,abs,absent);sdUnpackStruct(SendCharacterToSelf,&p,nodata?NULL:c,&e->pkt_id_fullAttrDef,!abs);assert(p.cursor==p.count);
 p=(Packet){.id=id};body(&p,SendBasicCharacter,abs,absent);sdUnpackStruct(SendBasicCharacter,&p,nodata?NULL:c,&e->pkt_id_basicAttrDef,!abs);assert(p.cursor==p.count);
}
static uint64_t fingerprint(ParseTable*t,void**ids){
 uint64_t h=1469598103934665603ULL;int i,j;if(!ids)return 0;
 FORALL_PARSEINFO(t,i){for(j=0;j<sizeof(void*);j++)h=(h^((unsigned char*)(ids+i))[j])*1099511628211ULL;
 if(TOK_GET_TYPE(t[i].type)==TOK_STRUCT_X)h^=fingerprint(t[i].subtable,(void**)ids[i]);}return h;
}
int main(int argc,char**argv){
 int mode=argc>1?atoi(argv[1]):0;Entity e={0};Character c={0},saved;char before[CAPACITY];uint64_t a,b;
 types[TOK_INT_X]=(TypeInfo){int_recvdiff,nopfree};types[TOK_F32_X]=(TypeInfo){float_recvdiff,nopfree};types[TOK_STRUCT_X]=(TypeInfo){struct_recvdiff,struct_freepktids};
 if(mode!=0){recv(&e,&c,mode==20?0:31,1,0,mode==8);
 if(mode==2)recv(&e,&c,1,1,0,0);
 if(mode==3)recv(&e,&c,32,0,0,0);
 if(mode==4)recv(&e,&c,32,1,0,0);
 if(mode==5)recv(&e,&c,0xffffffffU,1,0,0);
 if(mode==6)recv(&e,&c,1,1,1,0);
 if(mode==7)recv(&e,&c,31,1,0,0);
 if(mode==9)recv(&e,&c,0xffffffffU,1,0,0),recv(&e,&c,0,1,0,0);
 if(mode==19)recv(&e,&c,0,1,0,0);
 if(mode==18){ParserFreePktIds(SendCharacterToSelf,&e.pkt_id_fullAttrDef);e.pkt_id_fullAttrDef=calloc(7,sizeof(void*));}
 if(mode==10){ParserFreePktIds(SendCharacterToSelf,&e.pkt_id_fullAttrDef);ParserFreePktIds(SendBasicCharacter,&e.pkt_id_basicAttrDef);}
 }
 if(mode==11)used=CAPACITY-1;
 if(mode==12)SendCharacterToSelf[3].type=99;
 if(mode==13)SendCharacterToSelf[3].type|=1U<<20;
 if(mode==14)e.pkt_id_fullAttrDef[3]=(void*)(UINT_PTR)(UINT64_C(1)<<32);
 if(mode==15){void*ids[1]={0};attribute_packet_ids(SendCharacterToSelf,ids,4);}
 if(mode==16){void*ids[1]={0};attribute_packet_ids(NULL,ids,0);}
 if(mode==17){ParseTable t[130]={0};void*ids[129]={0};int i;for(i=0;i<129;i++)t[i]=(ParseTable){"x",TOK_INT_X};attribute_packet_ids(t,ids,0);}
 a=fingerprint(SendCharacterToSelf,e.pkt_id_fullAttrDef);b=fingerprint(SendBasicCharacter,e.pkt_id_basicAttrDef);
 saved=c;entity_attribute_packet_order_state(&e);strcpy(before,buffer);
 used=0;entity_attribute_packet_order_state(&e);assert(!strcmp(before,buffer));assert(!memcmp(&saved,&c,sizeof(c)));assert(a==fingerprint(SendCharacterToSelf,e.pkt_id_fullAttrDef)&&b==fingerprint(SendBasicCharacter,e.pkt_id_basicAttrDef));puts(buffer);
 ParserFreePktIds(SendCharacterToSelf,&e.pkt_id_fullAttrDef);ParserFreePktIds(SendBasicCharacter,&e.pkt_id_basicAttrDef);return 0;
}
'''
    return code


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);source=p.parse_args().source
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);(root/'fixture.c').write_text(fixture(source))
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(root/'fixture.c'),'-o',str(root/'fixture')],check=True)
        for mode in range(21):
            r=subprocess.run([str(root/'fixture'),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==(3 if 11<=mode<=17 else 0),(mode,r.returncode,r.stderr)
            if 11<=mode<=17:continue
            result=json.loads(r.stdout)
            if mode in (0,10):assert result==dict(self=None,basic=None);continue
            for label in ('self','basic'):
                rows=result[label]
                if mode==18 and label=='self':
                    assert [x['ids'] for x in rows]==[None,None,None,0,0,0,0];continue
                assert [x['field'] for x in rows]==['CurrentAttribs','MaxAttribs','SendLevels']+(['ExperiencePoints','ExperienceDebt','ExperienceRest','InfluencePoints'] if label=='self' else [])
                expected=0 if mode==20 else 32 if mode==4 else 0xffffffff if mode in (5,9) else 31
                for i,row in enumerate(rows):
                    if i<3:
                        if mode==6:assert row['ids'] is None;continue
                        sub=row['ids'];count=(8 if label=='self' else 5) if i==0 else (7 if label=='self' else 5) if i==1 else 2
                        assert len(sub)==count
                        assert all(x['ids']==expected for x in sub),(mode,label,row)
                    else:assert row['ids']==expected
    print('attribute packet IDs: 21 ASan/UBSan cases; original parse tables and int/float/struct receivers, nested allocation/free, absolute/delta/stale/equal/full-width/no-destination/null trees, schema/order checks, empty allocation, repeated observation, tree and character immutability and fail-closed type/storage/width/depth/count/output checks; packet/token-store/quantization dependencies substituted; no ID normalization')

if __name__=='__main__':main()
