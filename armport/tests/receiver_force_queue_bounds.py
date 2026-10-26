#!/usr/bin/env python3
"""Check actual force-queue receiver bounds and preservation of valid inputs."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--original', type=Path)
    args = parser.parse_args()
    helper = function((args.source/'libs/UtilitiesLib/src/utils/utils.c').read_text(), 'char *strncpyt(')
    native = (args.source/'Game/src/UI/uiTurnstile.c').read_text()
    prefix = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static char sForceQueueEvent[128];
typedef struct Packet { const char *text; int reads; } Packet;
static int windows;
#define WDW_TURNSTILE 1
#define WINDOW_GROWING 2
static const char *pktGetString(Packet *p) { ++p->reads; return p->text; }
static void window_setMode(int w,int m) { assert(w==1 && m==2); ++windows; }
static int strncpy_s(char *d,size_t capacity,const char *s,size_t count) {
 size_t n=strlen(s); assert(capacity>0 && count<capacity);
 if(n>count)n=count; memcpy(d,s,n);d[n]=0;return 0;
}
'''
    suffix = r'''
int main(int argc,char **argv) {
 size_t n=strtoul(argv[1],NULL,10),kept=n<127?n:127;
 char *input=malloc(n+1),*before=malloc(n+1); assert(input && before);
 for(size_t i=0;i<n;++i)input[i]='A'+i%26;
 input[n]=0;memcpy(before,input,n+1);
 Packet p={input,0};turnstileGame_handleForceQueue(&p);
 assert(p.reads==1 && windows==1 && !memcmp(input,before,n+1));
 assert(strlen(sForceQueueEvent)==kept && !memcmp(sForceQueueEvent,input,kept));
 printf("%s\n",sForceQueueEvent);
 p.text="After";turnstileGame_handleForceQueue(&p);
 assert(p.reads==2 && windows==2 && !strcmp(sForceQueueEvent,"After"));
 p.text="";turnstileGame_handleForceQueue(&p);
 assert(p.reads==3 && windows==3 && !sForceQueueEvent[0]);
 free(before);free(input);return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        def build(text,label):
            src=root/(label+'.c'); exe=root/label
            src.write_text(prefix+helper+function(text,'void turnstileGame_handleForceQueue(')+suffix)
            subprocess.run([os.environ.get('CC','cc'),'-std=c99','-O1','-g',
                            '-U_FORTIFY_SOURCE','-D_FORTIFY_SOURCE=0',
                            '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                            '-fno-omit-frame-pointer',str(src),'-o',str(exe)],check=True)
            return exe
        fixed=build(native,'fixed'); outputs={}
        for size in (0,1,126,127,128,129,256,4096):
            r=subprocess.run([str(fixed),str(size)],capture_output=True,text=True,timeout=15)
            assert r.returncode==0,(size,r.returncode,r.stderr)
            outputs[size]=r.stdout
        print('force-queue bounds: 8 ASan/UBSan cases pass; 0..4096-byte names, exact 127-byte prefix/termination, one read/window action, source nonmutation and subsequent short/empty replacement')
        if args.original:
            old=build(args.original.read_text(),'original')
            for size in (0,1,126,127):
                r=subprocess.run([str(old),str(size)],capture_output=True,text=True,timeout=15)
                assert r.returncode==0 and r.stdout==outputs[size],(size,r.returncode,r.stderr)
            for size in (128,4096):
                r=subprocess.run([str(old),str(size)],capture_output=True,text=True,timeout=15)
                assert r.returncode!=0 and 'AddressSanitizer' in r.stderr and 'global-buffer-overflow' in r.stderr,(size,r.returncode,r.stderr)
            print('Original receiver reproduces two global-buffer-overflows; four defined input cases remain identical. Host CRT/window/packet adapters do not qualify native ABI or complete UI behavior.')


if __name__=='__main__':
    main()
