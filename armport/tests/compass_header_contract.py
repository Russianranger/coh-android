#!/usr/bin/env python3
"""Probe original default compass text; not a rendering acceptance test."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    source = parser.parse_args().source
    native = (source/'Game/src/UI/uiCompass.c').read_text()
    code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
#include <stdbool.h>
typedef float F32;
typedef struct { char name[128],mapName[128]; int type,dbid,context,subhandle; } Destination;
typedef struct { int unused; } TaskStatus;
typedef struct { char text[2048]; } SMFBlock;
static char observed[2048];
static char gMapName[]="maps/City_Zones/City_01_01/City_01_01.txt";
static int scriptUIIsDetached=1,scriptUIWidgetList,g_display_exit_button,s_taCompassTask;
#define stricmp strcasecmp
#define ICON_MISSION 9
#define PIX3 3
#define R10 10
#define D_MOUSEHIT 1
#define CLR_BLUE 0
#define WDW_ARENA_RESULT 0
#define WINDOW_GROWING 0
#define SMAlignment_Center 0
#define SMAlignment_Left 1
#define TRANSLATE_NOPREPEND 0
static int compass_showExitButton(float x,float y,float z,float h,float w,float *b,float s) { return 0; }
static int eaSize(void *p) { return 0; }
static char *getArenaCompassString(void) { return NULL; }
static char *getArenaInfoString(void) { assert(0); return NULL; }
static char *getSGRaidCompassString(void) { return NULL; }
static char *getSGRaidInfoString(void) { assert(0); return NULL; }
static int drawStdButton(float x,float y,float z,float w,float h,int c,const char *t,float s,int f) { assert(0); return 0; }
static void window_setMode(int a,int b) { assert(0); }
static TaskStatus *TaskStatusGet(int a,int b,int c) { assert(0);return NULL; }
static void mission_displayCompass(float x,float y,float z,float w,float h,float s,TaskStatus *t,int a,char **text,float *b) { assert(0); }
static void smf_SetFlags(SMFBlock *s,...) { assert(0); }
static void estrCreate(char **s) { *s=calloc(2048,1);assert(*s); }
static void estrClear(char **s) { **s=0; }
static void estrConcatf(char **s,const char *format,...) {
 size_t n=strlen(*s);va_list a;va_start(a,format);
 int result=vsnprintf(*s+n,2048-n,format,a);va_end(a);
 assert(result>=0 && (size_t)result<2048-n);
}
static void estrConcatStaticCharArray(char **s,const char *text) { estrConcatf(s,"%s",text); }
static void estrDestroy(char **s) { free(*s);*s=NULL; }
/* Explicit identity/translation substitute: the original localization/GPU are not exercised. */
static const char *textStd(const char *s) {
 assert(s);if(!strcmp(s,gMapName))return "Atlas Park";
 if(!strcmp(s,"maps/City_Zones/City_02_01/City_02_01.txt"))return "Kings Row";
 return s;
}
static const char *textStdEx(int flags,const char *s) { return textStd(s); }
static void smf_SetRawText(SMFBlock *s,const char *text,int flag) { assert(!flag);strcpy(s->text,text); }
static int smf_Display(SMFBlock *s,...) { strcpy(observed,s->text);return 0; }
'''
    code += function(native, 'int compass_DrawHeaderText(')
    code += r'''
int main(int argc,char **argv) {
 int mode=atoi(argv[1]);Destination d={0},before;
 if(mode==1)strcpy(d.name,"Waypoint");
 if(mode==2 || mode==3) {strcpy(d.name,"Waypoint");strcpy(d.mapName,gMapName);}
 if(mode==3)strcpy(d.mapName,"maps/City_Zones/City_02_01/City_02_01.txt");
 if(mode==4)strcpy(d.mapName,gMapName);
 memcpy(&before,&d,sizeof(d));
 compass_DrawHeaderText(0,0,0,40,400,1,&d,0);
 assert(!memcmp(&before,&d,sizeof(d)));puts(observed);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);(root/'test.c').write_text(code)
        subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g',
                        '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                        '-fno-omit-frame-pointer',str(root/'test.c'),'-o',str(root/'test')],check=True)
        expected=['','<span align=center>Waypoint</span>',
                  '<span align=center>Waypoint</span>',
                  '<span align=center>Waypoint</span><scale .8><span align=center>Kings Row</span></scale>','']
        for mode,want in enumerate(expected):
            r=subprocess.run([str(root/'test'),str(mode)],capture_output=True,text=True,timeout=15)
            assert r.returncode==0 and r.stdout.rstrip('\n')==want,(mode,r.returncode,r.stdout,r.stderr)
    print('Original compass header: 5 ASan/UBSan probes pass. Empty/no-name destination emits no text; same-map destination omits map label; different-map destination emits its label. Destination is unchanged. Localization/SMF/UI state are substituted: no runtime rendering or screenshot acceptance is established.')


if __name__=='__main__':
    main()
