#!/usr/bin/env python3
"""Actual receiveSuperStats plus the super-stats snapshot writer.

The original receiver body (Game/src/UI/uiNet.c) is compiled with host
packet/earray/UI adapters; fixture structs mirror the fields it writes.
Checks: header/rank/member/ally/stat destinations, the own-rank copy, the
no-update and destroy paths, unterminated strncpy storage, nulls, bounds
and nonmutation. Host adapters do not qualify the native ABI.
"""
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
    ui = (source / 'Game/src/UI/uiNet.c').read_text()
    header = (source / 'Common/entity/Supergroup.h').read_text()
    perms = header[header.index('typedef enum sgroupPermissionEnum'):]
    perms = perms[:perms.index(';') + 1]
    code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <stdarg.h>
#include <stdbool.h>
#define CAPACITY 4194304
#define check(x) do { if (!(x)) _Exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef unsigned U32;
#define SG_NAME_LEN 64
#define SG_TITLE_LEN 64
#define SG_MESSAGE_LEN 256
#define SG_MOTTO_LEN 256
#define SG_DESCRIPTION_LEN 512
#define NUM_SG_RANKS 7
#define MAX_SUPERGROUP_ALLIES 10
#define PKT_BITS_TO_REP_DB_ID 20
''' + perms + r'''
typedef struct { char name[SG_TITLE_LEN]; U32 permissionInt[(SG_PERM_COUNT+31)/32]; } SupergroupRank;
typedef struct { int db_id, minDisplayRank, dontTalkTo; char name[SG_NAME_LEN]; } SupergroupAlly;
typedef struct { int dbid, rank; } SupergroupMemberInfo;
typedef struct { int db_id, rank, total_time_played, member_since, last_online, online, level, map_id, prestige, playerType;
                 char zone[256], name[32], origin[32], arch[32]; void *static_info; } SupergroupStats;
typedef int SgrpBaseEntryPermission;
typedef struct { char name[SG_NAME_LEN], msg[SG_MESSAGE_LEN], motto[SG_MOTTO_LEN], description[SG_DESCRIPTION_LEN], emblem[128];
                 int colors[2]; SupergroupAlly allies[MAX_SUPERGROUP_ALLIES]; int alliance_minTalkRank, tithe, demoteTimeout,
                 influence, playerType, spacesForItemsOfPower, prestige, prestigeBase, prestigeAddedUpkeep;
                 struct { int prtgRentDue; U32 secsRentDueDate; } upkeep; SgrpBaseEntryPermission entryPermission;
                 SupergroupMemberInfo **memberranks; SupergroupRank rankList[NUM_SG_RANKS]; } Supergroup;
typedef struct { int supergroup_mode; } EntPlayer;
typedef struct { Supergroup *supergroup; int supergroup_id, db_id; EntPlayer *pl; SupergroupStats *superstat, **sgStats; } Entity;
typedef struct { int n; void *v[9000]; } Array;
static Array *arr(void *v) { return (Array *)((char *)v - offsetof(Array, v)); }
#define eaSize(p) (*(p) ? arr(*(p))->n : 0)
#define eaCreate(p) (*(p) = (void *)((Array *)calloc(1, sizeof(Array)))->v)
#define eaPush(p, x) do { if (!*(p)) eaCreate(p); arr(*(p))->v[arr(*(p))->n++] = (x); } while (0)
#define eaDestroyEx(p, f) do { if (*(p)) { for (int z = 0; z < arr(*(p))->n; z++) f(arr(*(p))->v[z]); free(arr(*(p))); *(p) = NULL; } } while (0)
#define eaClearEx(p, f) do { if (*(p)) { for (int z = 0; z < arr(*(p))->n; z++) f(arr(*(p))->v[z]); arr(*(p))->n = 0; } } while (0)
typedef struct { int kind; unsigned v; const char *s; } Token;
typedef struct { Token t[2048]; int n, cursor; } Packet;
static Token take(Packet *p, int kind) { assert(p->cursor < p->n && p->t[p->cursor].kind == kind); return p->t[p->cursor++]; }
static int pktGetBitsPack(Packet *p, int b) { (void)b; return (int)take(p, 0).v; }
static unsigned pktGetBits(Packet *p, int b) { (void)b; return take(p, 1).v; }
static unsigned pktGetBitsAuto(Packet *p) { return take(p, 2).v; }
static char *pktGetString(Packet *p) { return (char *)take(p, 3).s; }
static void pktGetBitsArray(Packet *p, int bits, void *data) { U32 *d = data; for (int i = 0; i < bits / 32; i++) d[i] = take(p, 1).v; }
static char *unescapeString(char *s) { return s; }
static char *strncpyt(char *b, const char *s, int n) { strncpy(b, s, n - 1); b[n - 1] = 0; return b; }
static Supergroup *createSupergroup(void) { return calloc(1, sizeof(Supergroup)); }
static void destroySupergroup(Supergroup *s) { free(s); }
static SupergroupStats *createSupergroupStats(void) { return calloc(1, sizeof(SupergroupStats)); }
static void destroySupergroupStatsCallback(void *s) { free(s); }
static SupergroupMemberInfo *createSupergroupMemberInfo(void) { return calloc(1, sizeof(SupergroupMemberInfo)); }
static void destroySupergroupMemberInfoAdapter(void *s) { free(s); }
static void sgListPrepareUpdate(void) {}
static int creatingSupergroup(void) { return 0; }
static int isMenu(int m) { (void)m; return 0; }
static void srClearAll(void) {}
static void recipeInventoryReparse(void) {}
static void addSystemChatMsg(const char *m, int c, int x) { (void)m; (void)c; (void)x; }
static const char *textStd(const char *f, ...) { return f; }
#define MENU_SUPER_REG 1
#define MENU_SUPERCOSTUME 2
#define INFO_SUPERGROUP_COM 0
static struct { int edit_base; } game_state;
static struct { int periodRent; } g_baseUpkeep;
static int gSentMoTD = 1, g_PrestigeDiff, g_CurrentPrestige;
static void entSetMutableCostumeUnowned(Entity *e, void *c) { (void)e; (void)c; }
static void *costume_current(Entity *e) { (void)e; return NULL; }
static void start_menu(int m) { (void)m; }
#define MENU_GAME 0
static char *timerMakeOffsetDateStringNoYearNoSecFromSecondsSince2000(int s) { (void)s; return ""; }
static unsigned timerSecondsSince2000(void) { return 0; }
'''
    code += function(ui, 'void receiveSuperStats(')
    code += state[state.index('static void out('):state.index('void armportReplayStateInit(')]
    code += function(state, 'static void super_stat_record(')
    code += function(state, 'static void entity_super_stats_state(')
    code += r'''
static void num(Packet *p, unsigned v) { p->t[p->n++] = (Token){0, v, NULL}; }
static void bits(Packet *p, unsigned v) { p->t[p->n++] = (Token){1, v, NULL}; }
static void autov(Packet *p, unsigned v) { p->t[p->n++] = (Token){2, v, NULL}; }
static void str(Packet *p, const char *s) { p->t[p->n++] = (Token){3, 0, s}; }
static char long_rank[80];
static void full(Packet *p, int count, int update) {
    num(p, count);
    if (!count) return; /* destroy path reads nothing else */
    num(p, 0x80000000U); num(p, 7); num(p, 3); num(p, 4); num(p, 5); num(p, 0xffffffffU); num(p, 2);
    bits(p, update);
    if (!update) return;
    for (int i = 0; i < count; i++) {
        str(p, i ? "Member\"" : "Self"); num(p, i ? 900 + i : 77); num(p, i + 1); num(p, 50);
        bits(p, 0xfffffffeU); bits(p, i == 0); str(p, "Arch"); str(p, "Origin"); bits(p, 123); bits(p, 0x80000000U); num(p, 1);
        if (i == 0) str(p, "Atlas Park");
    }
    if (count > 0) {
        str(p, "Group"); str(p, "Motto"); str(p, "Msg"); str(p, "Emblem"); str(p, "Desc");
        num(p, 0x11223344U); num(p, 0x80000000U); num(p, 9); num(p, 10); bits(p, 0xffffffffU);
        for (int r = 0; r < NUM_SG_RANKS; r++) { str(p, r == 3 ? long_rank : "Rank"); for (int w = 0; w < (SG_PERM_COUNT+31)/32; w++) bits(p, 0x80000001U + r); }
        autov(p, 3);
        num(p, 2); num(p, 77); num(p, 5); num(p, 88); num(p, 0);
        for (int a = 0; a < MAX_SUPERGROUP_ALLIES; a++) { bits(p, a == 1 ? 4242 : 0); if (a == 1) { bits(p, 1); autov(p, 6); str(p, "Ally"); } }
        autov(p, 2);
    }
}
int main(int argc, char **argv) {
    int mode = atoi(argv[1]); (void)argc;
    memset(long_rank, 'r', 70); long_rank[70] = 0;
    /* Static: the receiver's allocations stay reachable for LeakSanitizer. */
    static EntPlayer pl = {1}; static Entity e; e.pl = &pl; e.db_id = 77; e.supergroup_id = 5;
    Packet p = {0};
    if (mode == 1) e.pl = NULL;
    full(&p, mode == 2 ? 0 : 2, mode == 3 ? 0 : 1);
    receiveSuperStats(&p, &e); assert(p.cursor == p.n);
    if (mode == 4) arr(e.sgStats)->n = 8193;
    if (mode == 5) used = CAPACITY - 1;
    if (mode == 6) eaPush(&e.supergroup->memberranks, NULL);
    Entity before = e;
    entity_super_stats_state(&e);
    assert(!memcmp(&before, &e, sizeof(e)));
    puts(buffer); return 0; }
'''
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'super.c'
        c.write_text(code)
        exe = c.with_suffix('')
        subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-sanitize-recover=all', '-Wno-int-conversion', str(c), '-o', str(exe)], check=True)
        for mode in range(7):
            r = subprocess.run([str(exe), str(mode)], capture_output=True, text=True, timeout=20)
            assert r.returncode == (3 if mode in (4, 5) else 0), (mode, r.returncode, r.stderr)
            if r.returncode:
                continue
            v = json.loads(r.stdout)
            assert v['supergroup_mode'] == (None if mode == 1 else (0 if mode == 2 else 1)), (mode, v)
            if mode == 2:
                assert v['header'] is None and v['member_stats'] == [] and v['own_stat'] is None
                continue
            h = v['header']
            assert (h['influence'], h['prestige'], h['prestige_base'], h['prestige_added_upkeep']) == (-2147483648, 7, 3, 4)
            assert (h['rent_due'], h['rent_due_date'], h['player_type']) == (5, 0xffffffff, 2)
            if mode == 3:
                assert v['member_stats'] == [] and h['name'] == '' and h['ranks'][0]['name'] == ''
                continue
            stats = v['member_stats']
            assert len(stats) == 2 and stats[0]['name'] == 'Self' and stats[0]['zone'] == 'Atlas Park'
            assert stats[1]['name'] == 'Member"' and stats[1]['zone'] == '' and stats[1]['last_online'] == -2
            assert stats[0]['prestige'] == -2147483648 and stats[0]['member_since'] == 123
            assert v['own_stat']['rank'] == 1 and v['own_stat']['db_id'] == 0
            assert (h['name'], h['motto'], h['msg'], h['emblem'], h['description']) == ('Group', 'Motto', 'Msg', 'Emblem', 'Desc')
            assert h['colors'] == [0x11223344, -2147483648] and h['tithe'] == 9 and h['demote_timeout'] == -1
            assert h['ranks'][3]['name'] == 'r' * 64, 'unterminated strncpy storage stays literal'
            assert h['ranks'][1]['permission_words'][0] == 0x80000002
            assert h['entry_permission'] == 3 and h['alliance_min_talk_rank'] == 2
            assert h['member_ranks'] == ([[77, 5], [88, 0], None] if mode == 6 else [[77, 5], [88, 0]])
            assert h['allies'][1] == {'db_id': 4242, 'dont_talk_to': 1, 'min_display_rank': 6, 'name': 'Ally'}
            assert h['allies'][0]['db_id'] == 0 and len(h['allies']) == 10
    print('7 super-stats cases pass: actual receiveSuperStats destinations, own-rank copy, no-update and '
          'destroy paths, literal unterminated rank storage, nulls, bounds, nonmutation; host adapters only')


if __name__ == '__main__':
    main()
