#ifndef COH_CHARACTER_UI_H
#define COH_CHARACTER_UI_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CHARACTER_UI_TRAY_SLOTS 720u
#define COH_CHARACTER_UI_WINDOWS 128u
#define COH_CHARACTER_UI_HELP_WORDS 128u
#define COH_CHARACTER_UI_HELP_LATEST 5u
#define COH_CHARACTER_UI_TEXT_MAX (720u*(256u+32u+256u))
#define COH_CHARACTER_UI_RAM_MAX (8u*1024u*1024u)
#define COH_CHARACTER_UI_STACK_RESERVE 4096u
typedef struct {uint32_t offset,bytes;} CohCharacterUiString;
typedef struct {
 uint32_t type,set,power;
 CohCharacterUiString command,short_name,icon_name;
} CohCharacterTraySlot;
typedef struct {
 uint32_t index,x,y,mode,locked,color,back_color,maximized,
     dimensions_present,width,height,scale_present,scale_word;
} CohCharacterWindow;
typedef struct {
 uint32_t current_trays[4],tray_indexes;
 CohCharacterTraySlot slots[COH_CHARACTER_UI_TRAY_SLOTS];
 uint32_t default_present,default_set,default_power,tray_mode,tray_mode_alt2;
 char name[32],motto[128],description[1024];
 uint32_t help_status[COH_CHARACTER_UI_HELP_WORDS],help_latest[COH_CHARACTER_UI_HELP_LATEST];
 CohCharacterWindow windows[COH_CHARACTER_UI_WINDOWS];
 uint32_t text_bytes;char text[COH_CHARACTER_UI_TEXT_MAX];
 size_t begin_bit,tray_end_bit,strings_end_bit,help_end_bit,end_bit;
} CohCharacterUi;
typedef struct {CohCharacterUi candidate;} CohCharacterUiWorkspace;
/* Exact group4 sendCharacterToClient body from sendTray through 128 windows.
 * Raw ordered events only: no power lookup, command execution, HTML rewriting,
 * window/UI application, prior-state replacement, actor, or completion ACK.
 * Counts/enums are pinned original source constants. Macro bodies retain owned
 * strings; string overflow and nonfinite scale refuse, never truncate. Unknown
 * 5-bit tray types follow pinned sender's no-body fallback; no gameplay support
 * for those types is asserted. All spans must be pairwise disjoint. Output and
 * workspace belong on caller heap/arena. Aggregate cap charges complete input,
 * output, workspace, retained bytes and stack reserve. Refusal preserves
 * reader/output; workspace private scratch. Stops before reward-token count. */
CohStatus coh_character_ui_read(CohRepReader *,CohCharacterUi *,
    CohCharacterUiWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
