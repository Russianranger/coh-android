#!/usr/bin/env python3
"""Source-derived selection-boundary control for M4 run 40167305715.

Exercise the real whitespace helper with heap strings and negative/zero/positive
indices. Revert only the signed boundary fix for the crashing negative control.
String edits use bounded fixture implementations, not the game's EString allocator.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile
from power_preview_transition import function

FIXTURE = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stdio.h>
enum { SMFInputMode_PlayerNames=1, SMFInputMode_PlayerNamesAndHandles=2 };
typedef struct { char *rawString; int inputMode; } SMFBlock;
static void estrRemove(char **s, int at, int n) {
 assert(at >= 0 && n >= 0 && at+n <= strlen(*s));
 memmove(*s+at,*s+at+n,strlen(*s+at+n)+1);
}
static void estrInsert(char **s, int at, const char *v, int n) {
 assert(at >= 0 && at <= strlen(*s));
 memmove(*s+at+n,*s+at,strlen(*s+at)+1); memcpy(*s+at,v,n);
}
/* SOURCE */
int main(int argc,char **argv) {
 SMFBlock b={calloc(64,1),0}; assert(b.rawString);
 if(argc>1) { strcpy(b.rawString,"x"); smf_SwitchBreakingToNonBreakingSpace(&b,-1); return 0; }
 for(int mode=0;mode<=2;mode++) {
  b.inputMode=mode;
  strcpy(b.rawString,"x");
  smf_SwitchBreakingToNonBreakingSpace(&b,-1);
  smf_SwitchBreakingToNonBreakingSpace(&b,0);
  smf_SwitchBreakingToNonBreakingSpace(&b,1);
  assert(!strcmp(b.rawString,"x"));
  b.rawString[0]=0; smf_SwitchBreakingToNonBreakingSpace(&b,0);
  strcpy(b.rawString,"a  b"); smf_SwitchBreakingToNonBreakingSpace(&b,2);
  assert(!strcmp(b.rawString,mode?"a b":"a&nbsp; b"));
 }
 free(b.rawString); puts("fixed: negative, zero, empty, terminator and adjacent-space cases pass for all 3 input modes");
}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args()
 t=(a.source/'Game/src/formatter/smf_interact.c').read_text()
 f=function(t,'static void smf_SwitchBreakingToNonBreakingSpace(')
 for delimiter in ('>','<'):
  assert "workingEarlyIndex >= deletedEarlyIndex && pSMFBlock->rawString[workingEarlyIndex] != '"+delimiter+"'" in t
 with tempfile.TemporaryDirectory() as td:
  c=Path(td)/'case.c';exe=Path(td)/'case'
  for old in (True,False):
   src=f
   if old:
    src=src.replace('int rawIndex','unsigned int rawIndex').replace('rawIndex > 0 && ','')
   c.write_text(FIXTURE.replace('/* SOURCE */',src))
   subprocess.run(['cc','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(c),'-o',str(exe)],check=True)
   r=subprocess.run([str(exe)]+(['negative'] if old else []),capture_output=True,text=True)
   if old:
    assert r.returncode and 'AddressSanitizer' in r.stderr,r.stderr
    print('old unsigned boundary: ASan rejects index -1 converted to UINT_MAX')
   else:
    assert r.returncode==0,r.stderr
    print(r.stdout,end='')
if __name__=='__main__':main()
