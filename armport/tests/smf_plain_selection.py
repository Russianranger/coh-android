from pathlib import Path
import argparse,subprocess,tempfile
from smf_selection_boundary import FIXTURE
from power_preview_transition import function
parser=argparse.ArgumentParser(description='Extracted plain-text selection deletion control; tag recognition and EString allocation are fixtures.')
parser.add_argument('--source',type=Path,required=True)
args=parser.parse_args()
s=(args.source/'Game/src/formatter/smf_interact.c').read_text()
fixture=FIXTURE[:FIXTURE.index('int main(')].replace('int inputMode;', 'int inputMode; bool editedThisFrame;')
pre=r'''
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define strnicmp strncasecmp
#include <strings.h>
enum {SMFSelectionCommand_None,SMFSelectionCommand_Delete,SMFSelectionCommand_InsertTags};
static int smf_Interact_selectionStartRawIndex,smf_Interact_selectionEndRawIndex;
static int smf_selectionStartDisplayIndex,smf_selectionEndDisplayIndex;
static int smf_selectionEndCharacterXOffset,smf_selectionEndCharacterYOffset,smf_selectionEndCharacterYHeight;
static int smf_aTagDefs;
static int smf_GetSelectionCommand(void){return SMFSelectionCommand_Delete;}
static bool smf_IsBlockEditable(SMFBlock *b){return true;}
static bool smfBlock_HasFocus(SMFBlock *b){return true;}
static char *smf_GetSelectionPreTag(void){return "";}
static char *smf_GetSelectionPostTag(void){return "";}
static int estrLength(char **s){return strlen(*s);}
static int sm_ParseTagName(char *s,int len,int tags){return -1;}
'''
code=pre+'\n'+'\n'.join(function(s,f) for f in ['static void smf_SwitchBreakingToNonBreakingSpace(', 'static void smf_removeLeadingWhiteSpace(', 'static void smf_modifyRawStringSection(', 'static void smf_UpdateSelectionInRawString('])
main=r'''
int main(void){
 SMFBlock b={calloc(64,1),0,false};int cases=0;
 for(int mode=0;mode<3;mode++)for(int a=0;a<=5;a++)for(int z=a;z<=5;z++){
  strcpy(b.rawString,"hello");b.inputMode=mode;
  smf_Interact_selectionStartRawIndex=a;smf_Interact_selectionEndRawIndex=z;
  smf_selectionStartDisplayIndex=a;smf_selectionEndDisplayIndex=z;
  char expect[64]="hello";memmove(expect+a,expect+z,6-z);
  smf_UpdateSelectionInRawString(&b);
  assert(!strcmp(expect,b.rawString));assert(smf_selectionStartDisplayIndex==a&&smf_selectionEndDisplayIndex==a);cases++;
 }
 free(b.rawString);printf("complete extracted selection updater: %d plain-text delete/empty-selection ranges pass with ASan/UBSan\n",cases);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'selection.c';exe=Path(tmp)/'selection'
 p.write_text(fixture.replace('/* SOURCE */',code)+main)
 subprocess.run(['cc','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
