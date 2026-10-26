#!/usr/bin/env python3
"""Actual NPC/Architect receivers plus snapshot writers; host adapters explicit."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    source = ap.parse_args().source
    state = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    native = (source / 'Common/entity/costume.c').read_text()
    ent = (source / 'Game/src/entity/entrecv.c').read_text()
    code = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
#define CAPACITY 1048576
#define check(x) do {if(!(x)) _Exit(3);}while(0)
static char buffer[CAPACITY];static size_t used;
typedef union {unsigned integer;unsigned char bytes[4];} Color;
typedef struct {const char *regionName;Color color[2];} CustomNPCCostumePart;
typedef struct {char *originalNPCName;CustomNPCCostumePart **parts;Color skinColor;} CustomNPCCostume;
typedef struct {int marker;} Costume; typedef Costume cCostume;
typedef struct {int architect_id,architect_flags,architect_authid;char architect_contact_name[32];int architect_contact_override,architect_useCachedCostume;Costume *architect_contact_costume;CustomNPCCostume *architect_contact_npc_costume;} TaskForce;
typedef struct {TaskForce *taskforce;int onArchitect,architect_invincible,architect_untargetable;} Entity;
typedef struct {int n;CustomNPCCostumePart *v[8193];} Array;
static Array *array(CustomNPCCostumePart *const *v){return (Array*)((char*)v - offsetof(Array,v));}
#define eaSize(p) (*(p)?array(*(p))->n:0)
static void eaPush(CustomNPCCostumePart ***v,CustomNPCCostumePart *p){if(!*v){Array *a=calloc(1,sizeof(*a));assert(a);*v=a->v;}Array *a=array(*v);assert(a->n<8193);a->v[a->n++]=p;}
#define StructAllocRaw(n) calloc(1,n)
#define ParseCustomNPCCostume 1
static void StructInitFields(int schema,CustomNPCCostume *c){assert(schema==1);memset(c,0,sizeof(*c));}
static void StructDestroy(int schema,CustomNPCCostume *c){assert(schema==1);if(c){for(int i=0;i<eaSize(&c->parts);i++){if(c->parts[i]){free((void*)c->parts[i]->regionName);free(c->parts[i]);}}if(c->parts)free(array(c->parts));free(c);}}
static const char *allocAddString(const char *s){return strdup(s);}
typedef struct {int kind,width;unsigned value;const char *string;} Token;
typedef struct {Token t[512];int n,cursor;} Packet;
static unsigned take(Packet *p,int kind,int width){assert(p->cursor<p->n);Token t=p->t[p->cursor++];assert(t.kind==kind && t.width==width);return t.value;}
static unsigned pktGetBits(Packet *p,int w){return take(p,0,w);}
static unsigned pktGetBitsAuto(Packet *p){return take(p,1,0);}
static char *pktGetString(Packet *p){assert(p->cursor<p->n);Token t=p->t[p->cursor++];assert(t.kind==2);return (char*)t.string;}
static void bit(Packet *p,int width,unsigned value){p->t[p->n++]=(Token){0,width,value,NULL};}
static void num(Packet *p,unsigned value){p->t[p->n++]=(Token){1,0,value,NULL};}
static void str(Packet *p,const char *value){p->t[p->n++]=(Token){2,0,0,value};}
static void npc(Packet *p,int count){bit(p,32,0xffffffffU);bit(p,6,count);for(int i=0;i<count;i++){bit(p,32,0x80000000U+i);bit(p,32,31+i);str(p,i%2?"legs":"head\\\"");}}
#define devassert(x) assert(x)
#define stricmp strcasecmp
#define SAFE_FREE(x) free(x)
static int GetBodyPartCount(void){return 1;}
static Costume *costume_create(int n){assert(n==1);return calloc(1,sizeof(Costume));}
static void costume_init(Costume *c){c->marker=0;}
static void costume_receive(Packet *p,Costume *c){c->marker=pktGetBitsAuto(p);}
static void costume_destroy(Costume *c){free(c);}
static int reviews;
static void missionReview_Set(int id,int flags,char *name,char *author,char *description,int rating,int euro){assert(id==31 && flags==-1 && !strcmp(name,"mission") && !strcmp(author,"author") && !strcmp(description,"desc") && rating==3 && euro==1);reviews++;}
'''
    code += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code += function(state, 'static void fixed_string(')
    # Full costume writer has its own actual-writer suite; this adapter exposes calls/identity only.
    code += 'static void costume(const Costume *c){if(c)out("%d",c->marker);else out("null");}\n'
    code += function(state, 'static void npc_costume_state(')
    code += function(state, 'static void entity_architect_state(')
    code += function(native, 'int NPCcostume_receive(')
    code += function(ent, 'static void entRecieveTaskforceArchitectInfo(')
    code += r'''
static void receive(Entity *e,int cc,int nc,int review){Packet p={0};bit(&p,1,1);bit(&p,1,1);num(&p,0xffffffffU);num(&p,31);num(&p,1);str(&p,"Contact");bit(&p,1,cc>=0);if(cc>=0){bit(&p,1,cc);if(cc)num(&p,777);}bit(&p,1,nc>=0);if(nc>=0){bit(&p,1,nc);if(nc)npc(&p,2);}bit(&p,1,review);if(review){str(&p,"mission");str(&p,"author");str(&p,"desc");num(&p,3);num(&p,1);num(&p,1);num(&p,0);}entRecieveTaskforceArchitectInfo(&p,e);assert(p.cursor==p.n);}
int main(int argc,char **argv){int mode=atoi(argv[1]);TaskForce t={0},saved;Entity e={.taskforce=&t},esaved;CustomNPCCostume *c=calloc(1,sizeof(*c));Packet p={0};(void)argc;
 npc(&p,mode==1?0:mode==2?63:2);assert(NPCcostume_receive(&p,c)==1 && p.cursor==p.n);
 if(mode==3)eaPush(&c->parts,NULL);
 if(mode==4)c->originalNPCName="retained";
 receive(&e,1,1,1);assert(reviews==1 && t.architect_contact_costume->marker==777);
 if(mode==5){t.architect_useCachedCostume=1;receive(&e,0,0,0);assert(t.architect_useCachedCostume==1);}
 if(mode==6)receive(&e,-1,-1,0);
 if(mode==7){Packet q={0};bit(&q,1,0);entRecieveTaskforceArchitectInfo(&q,&e);assert(q.cursor==q.n && !e.onArchitect);}
 if(mode==8){Packet q={0};bit(&q,1,1);bit(&q,1,0);entRecieveTaskforceArchitectInfo(&q,&e);assert(q.cursor==q.n && !e.onArchitect);}
 if(mode==9){t.architect_useCachedCostume=1;strcpy(t.architect_contact_name,"different");receive(&e,0,0,0);assert(t.architect_useCachedCostume==0);}
 if(mode==10)e.taskforce=NULL;
 if(mode==11)memset(t.architect_contact_name,'x',32);
 if(mode==12)array(c->parts)->n=8193;
 if(mode==13)array(c->parts)->n=-1;
 if(mode==14)used=CAPACITY-1;
 if(mode==17)array(c->parts)->n=8192;
 if(mode==18){free((void*)c->parts[0]->regionName);c->parts[0]->regionName=NULL;}
 if(mode==15){t.architect_id=1;t.architect_flags=(int)0x80000000U;t.architect_contact_override=-2147483647-1;e.architect_invincible=-1;e.architect_untargetable=31;}
 saved=t;esaved=e;CustomNPCCostume copy=*c;
 out("{\"npc\":");npc_costume_state(mode==16?NULL:c);out(",\"architect\":");entity_architect_state(&e);out("}");
 assert(!memcmp(&t,&saved,sizeof(t))&&!memcmp(&e,&esaved,sizeof(e))&&!memcmp(c,&copy,sizeof(copy)));
 puts(buffer);StructDestroy(1,c);costume_destroy(t.architect_contact_costume);StructDestroy(1,t.architect_contact_npc_costume);return 0;}
'''
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp)/'probe.c'; c.write_text(code); exe=c.with_suffix('')
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(c),'-o',str(exe)],check=True)
        for mode in range(19):
            r = subprocess.run([str(exe),str(mode)],capture_output=True,text=True,timeout=20)
            assert r.returncode == (3 if mode in (11,12,13,14) else 0),(mode,r.returncode,r.stderr)
            if r.returncode: continue
            v=json.loads(r.stdout); n=v['npc']; a=v['architect']; t=a['taskforce']
            if mode==16: assert n is None
            else:
                assert n['skin_u32']==0xffffffff
                assert len(n['parts'])=={1:0,2:63,3:3,17:8192}.get(mode,2)
                for i, part in enumerate(n['parts']):
                    if (mode==3 and i==2) or (mode==17 and i>=2):
                        assert part is None
                    else:
                        assert part['colors_u32']==[0x80000000+i,31+i]
                        expected = None if mode==18 and i==0 else ('legs' if i%2 else 'head\\"')
                        assert part['region']==expected, (mode,i,part,expected)
                if mode==3: assert n['parts'][2] is None
                assert n['original_npc_name']==('retained' if mode==4 else None)
            assert a['on_architect']==(0 if mode in (7,8) else 1)
            if mode==10: assert t is None; continue
            assert t['id']==(1 if mode==15 else 31)
            assert t['flags']==(-2147483648 if mode==15 else -1)
            assert t['contact_name']=='Contact'
            assert t['contact_costume']==(None if mode==6 else 777)
            if mode==6: assert t['contact_npc_costume'] is None
            else: assert len(t['contact_npc_costume']['parts'])==2
            assert t['use_cached_costume']==(1 if mode==5 else 0), (mode, t)
            if mode==15: assert a['invincible']==-1 and a['untargetable']==31 and t['contact_override']==-2147483648
    print('19 NPC/Architect receiver/writer sanitizer cases pass; host adapters do not qualify native ABI or full mission-review UI state')

if __name__=='__main__': main()
