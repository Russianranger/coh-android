#!/usr/bin/env python3
"""Exercise original model lookup calls/results and bounded diagnostic sampling."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True)
    source=parser.parse_args().source;root=Path(__file__).resolve().parents[2]
    rel='Common/group/group.c';changed=(source/rel).read_text();original=(root/'upstream/ouroboros'/rel).read_text()
    begin=changed.index('#if CLIENT && ((defined(__aarch64__)')
    helper=changed[begin:changed.index('Model * groupModelFind(',begin)]
    helper=helper.replace('#include <utilitieslib/utils/armport_zone_trace.h>','/* trace/atomic/environment adapters below */')
    fixture=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <stdint.h>
#define MAX_PATH 260
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP_CHECKED(a) ((void)0)
#define LOAD_NOW 1
#define LOAD_HEADER 8
#define GEO_INIT_FOR_DRAWING 2
#define GEO_DONT_INIT_FOR_DRAWING 16
#define GEO_USED_BY_WORLD 4
#define _snprintf snprintf
typedef int32_t LONG;
#define InterlockedCompareExchange(p,value,old) __sync_val_compare_and_swap(p,old,value)
typedef struct {const char *name;}GroupFileEntry;
typedef struct {unsigned loadstate;int vert_count,tri_count;}Model;
static GroupFileEntry entry={"object_library/fixture.txt"};static Model model={4,24,12};
static int enabled=1;static unsigned lookup_calls,find_calls,ext_calls,records;
static char log_records[48][512];static pthread_mutex_t log_mutex=PTHREAD_MUTEX_INITIALIZER;
static char *environment(const char*n){assert(!strcmp(n,"ARMPORT_STDIO_LOG")||!strcmp(n,"ARMPORT_ZONE_LOG"));return enabled?(char*)"yes":NULL;}
#define getenv environment
static GroupFileEntry*objectLibraryEntryFromObj(const char*n){assert(n);__sync_fetch_and_add(&lookup_calls,1);return *n=='M'?NULL:&entry;}
static void changeFileExt(const char*a,const char*b,char*c){assert(!strcmp(a,entry.name)&&!strcmp(b,".geo"));__sync_fetch_and_add(&ext_calls,1);strcpy(c,"object_library/fixture.geo");}
static Model*modelFind(const char*n,const char*p,int load,int flags){assert(!strcmp(p,"object_library/fixture.geo"));assert(load==(CLIENT?LOAD_NOW:LOAD_HEADER));assert(flags==((CLIENT?GEO_INIT_FOR_DRAWING:GEO_DONT_INIT_FOR_DRAWING)|GEO_USED_BY_WORLD));__sync_fetch_and_add(&find_calls,1);return *n=='N'?NULL:&model;}
static void armportZoneTrace(const char*stage,const char*text){assert(!strcmp(stage,"group.model"));assert(strlen(text)<512);pthread_mutex_lock(&log_mutex);assert(records<48);strcpy(log_records[records++],text);pthread_mutex_unlock(&log_mutex);}
'''
    fixture+=function(original,'Model * groupModelFind(').replace('groupModelFind(', 'originalGroupModelFind(')
    fixture+=helper+function(changed,'Model * groupModelFind(')
    fixture+=r'''
static void *worker(void*unused){int i;for(i=0;i<100;i++){assert(!groupModelFind("path/Missing"));assert(!groupModelFind("path/NoModel"));assert(groupModelFind("path/Good")==&model);}return NULL;}
int main(void){
 const char*names[]={"leaf","path/Missing","dir/NoModel","dir/Good","nested/a/Good","path/",""};
 unsigned i,j,seen[3]={0};int disabled_records;
 enabled=0;
 for(i=0;i<sizeof(names)/sizeof(*names);i++){
  Model*before,*after;unsigned counts[3];lookup_calls=find_calls=ext_calls=0;
  before=originalGroupModelFind(names[i]);counts[0]=lookup_calls;counts[1]=find_calls;counts[2]=ext_calls;
  lookup_calls=find_calls=ext_calls=0;after=groupModelFind(names[i]);
  assert(before==after&&lookup_calls==counts[0]&&find_calls==counts[1]&&ext_calls==counts[2]);
 }
 assert(records==0);enabled=1;
#if CLIENT && (defined(COH_ARMPORT_REFERENCE_I686) || (defined(__aarch64__) && defined(__MINGW32__)))
 {char longname[400];char label[97];memset(longname,'q',sizeof(longname));longname[399]=0;
  longname[0]='"';longname[1]='\\';longname[2]=' ';longname[3]=(char)0xff;
  armportGroupModelLabel(label,sizeof(label),longname);assert(strlen(label)==96&&!strncmp(label,"____",4));
  armportGroupModelLabel(label,sizeof(label),NULL);assert(!label[0]);
  armportGroupModelResult(2,longname,longname,&model);assert(records==1&&strlen(log_records[0])<512);
  armportGroupModelResult(3,longname,longname,&model);assert(records==1);
 }
#endif
 {pthread_t threads[8];for(i=0;i<8;i++)assert(!pthread_create(&threads[i],NULL,worker,NULL));for(i=0;i<8;i++)assert(!pthread_join(threads[i],NULL));}
#if CLIENT && (defined(COH_ARMPORT_REFERENCE_I686) || (defined(__aarch64__) && defined(__MINGW32__)))
 assert(records==48);
 for(i=0;i<records;i++){unsigned kind,sample;assert(sscanf(log_records[i],"outcome=%u sample=%u",&kind,&sample)==2);assert(kind<3&&sample>=1&&sample<=16);assert(!(seen[kind]&(1U<<(sample-1))));seen[kind]|=1U<<(sample-1);
  if(kind==0)assert(strstr(log_records[i],"geo=\"\" model=0"));
  if(kind==1)assert(strstr(log_records[i],"geo=\"object_library/fixture.geo\" model=0"));
  if(kind==2)assert(strstr(log_records[i],"model=1 loadstate=4 verts=24 tris=12"));
 }
 for(j=0;j<3;j++)assert(seen[j]==65535);
#else
 assert(records==0);
#endif
 disabled_records=records;enabled=0;worker(NULL);assert(records==(unsigned)disabled_records);
 printf("original/observed lookup results and call counts equal; records=%u; bounded labels and eight-thread independent budgets; disabled opt-in/build inert\n",records);
 return 0;
}
'''
    configs=[['-DCLIENT=1','-DCOH_ARMPORT_REFERENCE_I686=1'],['-DCLIENT=1','-D__aarch64__=1','-D__MINGW32__=1'],['-DCLIENT=1'],['-DCLIENT=0','-DCOH_ARMPORT_REFERENCE_I686=1']]
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp);(path/'fixture.c').write_text(fixture)
        for flags in configs:
            subprocess.run([os.environ.get('CC','cc'),'-std=c11','-O1','-g','-pthread','-fsanitize=address,undefined','-fno-omit-frame-pointer',*flags,str(path/'fixture.c'),'-o',str(path/'fixture')],check=True)
            subprocess.run([str(path/'fixture')],check=True)
    print('Four actual-source build-guard configurations pass ASan/UBSan. Fixture substitutes object/model loading, Win32 atomic operation, environment and trace sink; does not qualify runtime model availability, native ABI or root cause.')

if __name__=='__main__':main()
