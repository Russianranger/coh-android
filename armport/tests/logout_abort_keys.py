"""A logout survives the Enter that asked for it (patch 0127), extracted from the given source.

/quittologin is typed into chat and sent with Enter. The chat window acts on the
Enter's WM_KEYDOWN during the frame's windowProcessMessages; Wine's DirectInput
keyboard hook queues the same press during that pump, after the frame's
inpUpdate, so its edge is read one frame later. checkLogoutProgress cancels a
logout ("Press any key to abort") on any key edge once the server's logout timer
is back, and at 2 frames per second (CI) it is back by the next frame: the stock
client cancelled its own logout (no logout line, client left in the zone, no
save). The fixture compiles the key-edge update and inpEdge from input.c, the
quit request time from clientcomm.c and the abort loop of checkLogoutProgress
from game.c, and runs the client's frame order (inpUpdate, windowProcessMessages,
net, UI, checkLogoutProgress) for:
  1. Enter sent between frames, Wine order, timer back in the next frame: the
     logout continues;
  2. a key pressed after the request: it still cancels (stock behaviour);
  3. the same at 10 frames per second with the timer back two frames later;
  4. Windows order (the press already queued at inpUpdate): the logout continues.
--original takes the code from the unpatched upstream files and must fail case 1.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--original', type=Path, help='unpatched upstream/ouroboros (negative control)')
args = parser.parse_args()
root = args.original or args.source
game = (root / 'Game/src/game.c').read_text(encoding='latin-1')
input_c = (root / 'Game/src/win/input.c').read_text(encoding='latin-1')
input_h = (root / 'Game/src/win/input.h').read_text(encoding='latin-1')
comm = (root / 'Game/src/clientcomm/clientcomm.c').read_text(encoding='latin-1')


def function(text, signature, required=True):
    if signature not in text:
        assert not required, 'missing ' + signature
        return ''
    begin = text.index(signature)
    return text[begin:text.index('\n}\n', begin) + 3]


def block(text, start):
    """The brace block that follows the line starting at text.index(start)."""
    begin = text.index(start)
    depth, position = 0, text.index('{', begin)
    while True:
        character = text[position]
        depth += character == '{'
        depth -= character == '}'
        position += 1
        if depth == 0:
            return text[begin:position]


logout = function(game, 'void checkLogoutProgress()')
abort_loop = block(logout, '        if (quitSeconds >= 0 && GetFocus())')
assert 'inpEdge(i)' in abort_loop and 'commSendQuitGame(1);' in abort_loop
keep = function(game, 'static int armportKeyPressedBeforeQuit(int key)', required=False)
update = function(input_c, 'void inpUpdateKeyEx(int keyIndex, int keyState, int timeStamp, int x, int y )')
edge = function(input_c, 'int inpEdge(int idx)')
edge_time = function(input_c, 'U32 inpEdgeTime(int idx)', required=False)
edge_times = 'static U32 inp_edge_times[256];\n' if 'static U32 inp_edge_times[256];' in input_c else ''
note = function(comm, 'void armportNoteQuitRequest(int abort_quit)', required=False)
assert bool(keep) == bool(edge_time) == bool(edge_times) == bool(note), 'partial patch 0127'
if note:
    assert 'void commSendQuitGame(int abort_quit)\n{\n    armportNoteQuitRequest(abort_quit);\n' in comm
    assert re.search(r'^U32 g_armport_quit_request_ms;$', comm, re.M)
    note = 'U32 g_armport_quit_request_ms;\n' + note
else:
    note = 'static void armportNoteQuitRequest(int abort_quit) { (void)abort_quit; }\n'
defines = '\n'.join(line for line in input_h.splitlines() if re.match(r'#define INP_[A-Z0-9_]+\s+[(0-9]', line))

fixture = r'''
#include <stdio.h>
#include <string.h>
typedef unsigned int U32; typedef int S32;
''' + defines + r'''
#define MENU_GAME 1
char inp_levels[256], inp_edges[256];
''' + edge_times + r'''
static int just_lost_focus_debug, g_isBindingKey;
static int okToInput(int key) { (void)key; return 0; }
static void bindKeyExecEx(int key, int state, int time, int x, int y) { (void)key; (void)state; (void)time; (void)x; (void)y; }
static int isMenu(int menu) { return menu == MENU_GAME; }
static int isGameReturnKeybind(int key) { (void)key; return 0; }
static void cmdParse(const char *command) { (void)command; }
static U32 now_ms = 100000;                     /* the client's millisecond clock */
static U32 timeGetTime(void) { return now_ms; }
static int GetFocus(void) { return 1; }
static void windowExitDlg(void *data) { (void)data; }
static void dialogRemove(void *a, void (*code)(void *), void *b) { (void)a; (void)code; (void)b; }
''' + update + edge + edge_time + note + keep + r'''
static int aborts, requests, reply_at_frame, frame, logout_timer;
static void commSendQuitGame(int abort_quit) {          /* commSendQuitGame's first line, then the packet */
    armportNoteQuitRequest(abort_quit);
    if (abort_quit) { aborts++; logout_timer = 0; reply_at_frame = -1; } else requests++;
}
static void abort_check(int quitSeconds) {
    int i;
''' + abort_loop + r'''
}
/* Hardware key events the host sent, and DirectInput's queue (Wine: filled by its hook during the pump). */
static struct { int key, down, at_frame; } host[8]; static int host_count;
static struct { int key, down; U32 time; } queue[16]; static int queued;
static int chat_enter, windows_order, frame_ms, reply_frames;
static void send_key(int key, int down, int at_frame) { host[host_count].key = key; host[host_count].down = down; host[host_count++].at_frame = at_frame; }
static void hook(int key, int down) { queue[queued].key = key; queue[queued].down = down; queue[queued++].time = now_ms; }
static void run_frame(void) {
    U32 start = now_ms; int i;
    if (windows_order)                                    /* Windows: DirectInput has the press before the frame */
        for (i = 0; i < host_count; i++) if (host[i].at_frame == frame) hook(host[i].key, host[i].down);
    memset(inp_edges, 0, sizeof(inp_edges));              /* inpUpdate */
    for (i = 0; i < queued; i++) inpUpdateKeyEx(queue[i].key, queue[i].down ? 0x80 : 0, (int)queue[i].time, 0, 0);
    queued = 0;
    now_ms = start + 1;                                   /* windowProcessMessages */
    for (i = 0; i < host_count; i++) if (host[i].at_frame == frame) {
        if (!windows_order) hook(host[i].key, host[i].down);
        if (host[i].down && host[i].key == INP_RETURN) chat_enter = 1;   /* WM_KEYDOWN to the chat window */
    }
    now_ms = start + 2;                                   /* engine_update_net: the server's logout update */
    if (reply_at_frame >= 0 && frame >= reply_at_frame) logout_timer = 30 * 30;
    now_ms = start + 5;                                   /* UI: the chat window sends /quittologin */
    if (chat_enter) { chat_enter = 0; commSendQuitGame(0); reply_at_frame = frame + reply_frames; }
    now_ms = start + 8;                                   /* checkLogoutProgress */
    if (logout_timer) { abort_check((int)(logout_timer / 30.f - 1.0f)); logout_timer -= frame_ms * 30 / 1000; }
    now_ms = start + frame_ms; frame++;
}
static int scenario(const char *name, int fps, int replies_after, int order, int later_key) {
    int f;
    memset(inp_levels, 0, sizeof(inp_levels)); host_count = queued = aborts = requests = frame = logout_timer = chat_enter = 0;
    reply_at_frame = -1; frame_ms = 1000 / fps; reply_frames = replies_after; windows_order = order;
    send_key(INP_RETURN, 1, 2);                           /* the host's Enter: pressed before frame 2, */
    send_key(INP_RETURN, 0, 3);                           /* released 0.3 s later */
    if (later_key) { send_key(INP_ESCAPE, 1, 8); send_key(INP_ESCAPE, 0, 9); }
    for (f = 0; f < 20; f++) run_frame();
    printf("%s: requests=%d aborts=%d\n", name, requests, aborts);
    return requests == 1 ? aborts : -1;
}
int main(void) {
    int wine = scenario("wine_2fps_timer_next_frame", 2, 1, 0, 0);
    int cancel = scenario("wine_2fps_later_escape", 2, 1, 0, 1);
    int fast = scenario("wine_10fps_timer_two_frames", 10, 2, 0, 0);
    int windows = scenario("windows_order_2fps", 2, 1, 1, 0);
    if (wine) { printf("FAIL: the Enter that sent /quittologin cancelled the logout\n"); return 1; }
    if (cancel != 1) { printf("FAIL: a key pressed after the request did not cancel the logout\n"); return 1; }
    if (fast || windows) { printf("FAIL: logout cancelled without a later key\n"); return 1; }
    printf("PASS: logout kept through the Enter that sent it; a later key still cancels\n");
    return 0;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / 'logout_abort.c'
    source.write_text(fixture)
    exe = Path(temporary) / 'logout_abort'
    subprocess.run(['cc', '-std=gnu11', '-O1', '-Wall', '-Wno-unused-function', '-Werror', str(source), '-o', str(exe)],
                   check=True)
    result = subprocess.run([str(exe)], capture_output=True, text=True)
    print(result.stdout.strip().replace('\n', ' | '))
    raise SystemExit(result.returncode)
