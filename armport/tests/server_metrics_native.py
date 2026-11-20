#!/usr/bin/env python3
"""Execute the prepared MapServer loop, fileAlloc bodies and metric producer.

Adapters supply deterministic Windows clocks and file I/O, not a second copy of
the measurement logic. --original executes the upstream loop/file functions
with the same assertions and must fail because no metrics are produced. This
does not qualify the actual Windows binary or a packaged server producer.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile

CASES = ['window', 'disabled', 'files', 'thread', 'slow', 'clock', 'saturation',
         'startup', 'startup_disabled', 'startup_clock']
NEGATIVE_ASSERTION = 's->ticks == 4 && s->file_calls == 4 && s->window_start == 0'
STARTUP_NEGATIVE_ASSERTION = 'startup->enabled && startup->sequence == 17'
TRUSTED_NEGATIVE_ASSERTION = 'scans == 0 && list_reads == 0'
TEXTPARSER = 'libs/UtilitiesLib/src/utils/textparser.c'
TRUSTED_CASES = ['trusted_bins', 'trusted_bins_disabled']
SPARE_HEADER = 'MapServer/src/svr/armport_spare_server.h'
SPARE_NEGATIVE_ASSERTION = 'reads == 3 && sleeps == 2 && db_state.map_id == 5001'
SPARE_CASES = ['spare_server', 'spare_server_disabled', 'spare_server_invalid']
GROUPFILELIB = 'Common/group/groupfilelib.c'
OBJECT_LIBRARY_NEGATIVE_ASSERTION = 'scans == 0 && date_checks == 0'
OBJECT_LIBRARY_CASES = ['object_library', 'object_library_disabled', 'object_library_rebuild']
NWWRAPPER = 'Common/NovodeX/NwWrapper.cpp'
PHYSX_HEADER = 'Common/NovodeX/armport_physx_cache.h'
PHYSX_NEGATIVE_ASSERTION = 'cooks == 0 && creates == 4'
PHYSX_CASES = ['physx_cache', 'physx_cache_disabled', 'physx_cache_damaged']
INITCOMMON = 'Common/gameComm/initCommon.c'
MESSAGESTORE = 'libs/UtilitiesLib/src/language/MessageStore.c'
START_TREES_NEGATIVE_ASSERTION = 'requests == 4 && listings == 0 && date_checks == 0'
START_TREES_CASES = ['start_trees', 'start_trees_disabled',
                     'message_bins', 'message_bins_disabled', 'message_bins_fallback']
LOAD_PROFILE_HEADER = 'Common/group/armport_map_load_profile.h'
LOAD_PROFILE_SOURCES = ('Common/group/group.c', 'Common/group/groupgrid.c', 'MapServer/src/group/groupnetdb.c')
LOAD_PROFILE_NEGATIVE_ASSERTION = ('armport_map_load.calls[ARMPORT_MAP_LOAD_BOUNDS_FILES] == 3 '
                                   '&& armport_map_load.ticks[ARMPORT_MAP_LOAD_OTHER] == 360')
LOAD_PROFILE_CASES = ['map_load_profile', 'map_load_profile_disabled']


def test_cases(source):
    text = (source / 'MapServer/src/svr/svr_init.c').read_text()
    parser = (source / TEXTPARSER).read_text()
    return (CASES + (['progress_markers'] if 'cohMapProgressMark(COH_MAP_STAGE_LOOP_PRE_TICK);' in text else [])
            + (TRUSTED_CASES if 'static int armportTrustedBin(' in parser else [])
            + (SPARE_CASES if (source / SPARE_HEADER).is_file() else [])
            + (OBJECT_LIBRARY_CASES if 'static int armportTrustedObjectLibrary('
               in (source / GROUPFILELIB).read_text() else [])
            + (PHYSX_CASES if (source / PHYSX_HEADER).is_file() else [])
            + (START_TREES_CASES if 'static int armportTrustedStartTrees('
               in (source / INITCOMMON).read_text() else [])
            + (LOAD_PROFILE_CASES if (source / LOAD_PROFILE_HEADER).is_file() else []))


def spare_fixture(source):
    """Run the shipping spare-server header over recorded Win32 file, clock and map-list shims."""
    svr = (source / 'MapServer/src/svr/svr_init.c').read_text()
    header = source / SPARE_HEADER
    if header.is_file():
        # The shipping call site: after every shared load, before any DbServer traffic.
        main = svr[svr.index('int __cdecl main(int argc,char **argv)'):]
        order = [main.index(text) for text in ('    checkTsr();', '        cmdCfgLoad();\n        armportSpareWait();\n',
                                               '        connectToDbserver(NO_TIMEOUT);')]
        assert order == sorted(order) and svr.count('armportSpareWait();') == 1, order
        assert svr.index('#include <utilitieslib/utils/wininclude.h>') < svr.index('#include "armport_spare_server.h"')
        body = header.read_text()
    else:
        assert 'armportSpare' not in svr
        body = 'static void armportSpareWait(void) {}\n'
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t DWORD; typedef void *HANDLE;
#define INVALID_HANDLE_VALUE ((HANDLE)-1)
#define GENERIC_READ 1
#define FILE_SHARE_READ 1
#define FILE_SHARE_WRITE 2
#define FILE_SHARE_DELETE 4
#define OPEN_EXISTING 3
#define FILE_ATTRIBUTE_NORMAL 0
typedef struct StaticMapInfo { int mapID, baseMapID, instanceID; } StaticMapInfo;
static struct { int map_id, base_map_id, instance_id, cookie, local_server; } db_state;
static const char *contents[8]; static const char *opened; static int reads, sleeps, ticks;
static HANDLE CreateFileA(const char *path, int access, int share, void *security, int disposition, int flags, void *template) {
    (void)access; (void)share; (void)security; (void)disposition; (void)flags; (void)template;
    opened = path; return contents[reads] ? (HANDLE)1 : (++reads, INVALID_HANDLE_VALUE); }
static int ReadFile(HANDLE handle, char *buffer, DWORD wanted, DWORD *got, void *overlapped) {
    const char *text = contents[reads++]; size_t length = strlen(text);
    (void)handle; (void)overlapped;
    if (length > wanted) length = wanted;
    memcpy(buffer, text, length); *got = (DWORD)length; return 1; }
static void CloseHandle(HANDLE handle) { (void)handle; }
static void Sleep(int milliseconds) { sleeps += milliseconds == 100; }
static DWORD GetTickCount(void) { return (DWORD)(ticks += 250); }
static DWORD GetCurrentProcessId(void) { return 42; }
static StaticMapInfo clone = {5001, 50, 2};
static StaticMapInfo *staticMapInfoFind(int id) { return id == 5001 ? &clone : NULL; }
#define fileGetStdout() stdout      /* svr_init.c flushes its console this way */
''' + body + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "";
    (void)contents; (void)opened; (void)clone; (void)staticMapInfoFind; (void)CreateFileA; (void)ReadFile;
    (void)CloseHandle; (void)Sleep; (void)GetTickCount; (void)GetCurrentProcessId;
    db_state.map_id = 71; db_state.base_map_id = 71;
    if (!strcmp(mode, "spare_server")) {
        CHECK(setenv("ARMPORT_SPARE_FILE", "Z:\\state\\spare-assign", 1) == 0);
        contents[2] = "ARMPORT_SPARE_ASSIGN_V1 map_id=5001 cookie=7\n";      /* absent twice, then published */
        armportSpareWait();
        CHECK(reads == 3 && sleeps == 2 && db_state.map_id == 5001);
        CHECK(db_state.base_map_id == 50 && db_state.instance_id == 2 && db_state.cookie == 7);
        CHECK(opened && !strcmp(opened, "Z:\\state\\spare-assign"));
        reads = 0; contents[0] = "ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=2147483647\n"; contents[2] = NULL;
        armportSpareWait();                                                  /* a zone without a base map */
        CHECK(db_state.map_id == 71 && db_state.base_map_id == 71 && db_state.instance_id == 0);
        CHECK(db_state.cookie == 2147483647);
        return 0;
    }
    if (!strcmp(mode, "spare_server_disabled")) {
        unsetenv("ARMPORT_SPARE_FILE");
        armportSpareWait();
        CHECK(setenv("ARMPORT_SPARE_FILE", "", 1) == 0);
        armportSpareWait();
        CHECK(reads == 0 && sleeps == 0 && db_state.map_id == 71 && db_state.cookie == 0);
        return 0;
    }
    if (!strcmp(mode, "spare_server_invalid")) {
        CHECK(setenv("ARMPORT_SPARE_FILE", "assign", 1) == 0);
        contents[0] = argc > 2 ? argv[2] : "";
        db_state.local_server = argc > 3;
        armportSpareWait();                                                  /* must exit(3) itself */
        return 0;
    }
    return 2;
}
'''


def physx_fixture(source):
    """Run the shipping nwCookAndLoadMeshShape and cache header over PhysX and Win32 file shims."""
    wrapper = (source / NWWRAPPER).read_text()
    header = source / PHYSX_HEADER
    if header.is_file():
        assert wrapper.count('#include "NovodeX/armport_physx_cache.h"') == 1
        support = header.read_text() + '\n#define RESTART() memset(&armport_physx, 0, sizeof(armport_physx))\n'
    else:
        assert 'armportPhysx' not in wrapper
        support = '#define RESTART() ((void)0)\n'
    body = function(wrapper, 'void* nwCookAndLoadMeshShape(') + function(wrapper, 'void nwFreeStreamBuffer()')
    return r'''
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
typedef uint32_t DWORD; typedef int32_t LONG; typedef int BOOL; typedef void *HANDLE;
typedef struct { long long QuadPart; } LARGE_INTEGER;
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define INVALID_SET_FILE_POINTER ((DWORD)-1)
#define GENERIC_READ 1u
#define GENERIC_WRITE 2u
#define FILE_SHARE_READ 1u
#define OPEN_EXISTING 3u
#define CREATE_ALWAYS 2u
#define FILE_ATTRIBUTE_NORMAL 0x80u
#define FILE_BEGIN 0u
#define MOVEFILE_REPLACE_EXISTING 1u
static int opens, open_now, fail_writes;
static long long clock_ticks;
static HANDLE CreateFileA(const char *path, DWORD access, DWORD share, void *security, DWORD how, DWORD flags, void *model) {
    int fd;
    (void)share; (void)security; (void)flags; (void)model;
    fd = (access == GENERIC_WRITE && how == CREATE_ALWAYS) ? open(path, O_WRONLY | O_CREAT | O_TRUNC, 0600)
        : (access == GENERIC_READ && how == OPEN_EXISTING) ? open(path, O_RDONLY) : -1;
    if (fd < 0) return INVALID_HANDLE_VALUE;
    ++opens; ++open_now;
    return (HANDLE)(intptr_t)(fd + 1);
}
static int descriptor(HANDLE h) { assert(h && h != INVALID_HANDLE_VALUE); return (int)(intptr_t)h - 1; }
static DWORD GetFileSize(HANDLE h, DWORD *high) { struct stat st; if (fstat(descriptor(h), &st)) abort(); *high = 0; return (DWORD)st.st_size; }
static BOOL ReadFile(HANDLE h, void *bytes, DWORD length, DWORD *got, void *overlapped) {
    ssize_t n = read(descriptor(h), bytes, length > 5000 ? 5000 : length);      /* short reads */
    (void)overlapped;
    if (n < 0)
        return 0;
    *got = (DWORD)n;
    return 1; }
static BOOL WriteFile(HANDLE h, const void *bytes, DWORD length, DWORD *wrote, void *overlapped) {
    ssize_t n;
    (void)overlapped;
    if (fail_writes)
        return 0;
    n = write(descriptor(h), bytes, length > 7000 ? 7000 : length);              /* short writes */
    if (n < 0)
        return 0;
    *wrote = (DWORD)n;
    return 1; }
static DWORD SetFilePointer(HANDLE h, LONG to, LONG *high, DWORD from) {
    off_t at;
    assert(!high && from == FILE_BEGIN);
    at = lseek(descriptor(h), to, SEEK_SET);
    return at < 0 ? INVALID_SET_FILE_POINTER : (DWORD)at; }
static BOOL CloseHandle(HANDLE h) { --open_now; return close(descriptor(h)) == 0; }
static BOOL MoveFileExA(const char *from, const char *to, DWORD flags) { assert(flags == MOVEFILE_REPLACE_EXISTING); return rename(from, to) == 0; }
static BOOL DeleteFileA(const char *path) { return unlink(path) == 0; }
static BOOL QueryPerformanceCounter(LARGE_INTEGER *value) { value->QuadPart = (clock_ticks += 1000); return 1; }
static BOOL QueryPerformanceFrequency(LARGE_INTEGER *value) { value->QuadPart = 1000000; return 1; }

typedef unsigned char NxU8; typedef unsigned int NxU32;
struct NwSharedStream {
    static NxU8 *pTempBuffer; static NxU32 uiBufferSize; NxU8 *pCursor;
    NwSharedStream(const char *name, bool load) { (void)name; (void)load;
        if (!pTempBuffer) { uiBufferSize = 1024; pTempBuffer = (NxU8 *)calloc(uiBufferSize, 1); }
        pCursor = pTempBuffer; }
    void resetByteCounter() { pCursor = pTempBuffer; }
    void checkTempBufferSize(NxU32 size) {
        if (pCursor + size >= pTempBuffer + uiBufferSize) {
            NxU8 *old = pTempBuffer; NxU32 grown = uiBufferSize + (uiBufferSize >> 1) + size;
            pTempBuffer = (NxU8 *)malloc(grown); memcpy(pTempBuffer, old, (size_t)(pCursor - old));
            pCursor += pTempBuffer - old; uiBufferSize = grown; free(old); } }
    static void freeTempBuffer() { free(pTempBuffer); pTempBuffer = NULL; }
    NxU8 *getBuffer() { return pTempBuffer; }
    int getBufferSize() { return (int)(pCursor - pTempBuffer); }
    void storeBuffer(const void *bytes, NxU32 size) { checkTempBufferSize(size); memcpy(pCursor, bytes, size); pCursor += size; }
};
NxU8 *NwSharedStream::pTempBuffer; NxU32 NwSharedStream::uiBufferSize;
struct NxTriangleMeshDesc { NxU32 numVertices, pointStrideBytes, numTriangles, triangleStrideBytes, flags; const void *points, *triangles; };
struct NxTriangleMesh { NxU32 size; NxU8 *bytes; };
struct NxTriangleMeshShapeDesc { NxTriangleMesh *meshData; };
static int cooks, creates, refuse_creates;
static void NxInitCooking() {}
/* A stand-in cooker: a tag, the counts, then every input byte changed in a fixed way. */
static bool NxCookTriangleMesh(const NxTriangleMeshDesc &desc, NwSharedStream &stream) {
    NxU32 i, n; const NxU8 *p;
    ++cooks;
    stream.storeBuffer("COOK", 4); stream.storeBuffer(&desc.numVertices, 4); stream.storeBuffer(&desc.numTriangles, 4);
    p = (const NxU8 *)desc.points; n = desc.numVertices * desc.pointStrideBytes;
    for (i = 0; i < n; ++i) { NxU8 b = (NxU8)(p[i] ^ 0x5a); stream.storeBuffer(&b, 1); }
    p = (const NxU8 *)desc.triangles; n = desc.numTriangles * desc.triangleStrideBytes;
    for (i = 0; i < n; ++i) { NxU8 b = (NxU8)(p[i] + 7); stream.storeBuffer(&b, 1); }
    return true; }
static struct Sdk {
    NxTriangleMesh *createTriangleMesh(NwSharedStream &stream) {
        NxU32 verts, tris, size; NxTriangleMesh *mesh;
        ++creates;
        if (refuse_creates > 0) { --refuse_creates; return NULL; }
        if (memcmp(stream.pCursor, "COOK", 4)) return NULL;
        memcpy(&verts, stream.pCursor + 4, 4); memcpy(&tris, stream.pCursor + 8, 4);
        size = 12 + verts * 12 + tris * 12;
        mesh = new NxTriangleMesh; mesh->size = size; mesh->bytes = (NxU8 *)malloc(size);
        memcpy(mesh->bytes, stream.pCursor, size); stream.pCursor += size;
        return mesh; }
} sdk, *nxSDK = &sdk;
static struct { int meshShapeCount; } nx_state;
#define PERFINFO_AUTO_START(name, n) ((void)0)
#define PERFINFO_AUTO_STOP_START(name, n) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
''' + support + body + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static float verts[3][600][3]; static int tris[3][900][3];
static NxU8 *expected[3]; static NxU32 expected_size[3];
static int same(void *shape, int which) {
    NxTriangleMesh *mesh = ((NxTriangleMeshShapeDesc *)shape)->meshData;
    return mesh && mesh->size == expected_size[which] && !memcmp(mesh->bytes, expected[which], mesh->size); }
static void *load(int which) {
    return nwCookAndLoadMeshShape("mesh", verts[which], 200 * (which + 1), 12, tris[which], 300 * (which + 1), 12); }
/* One world load: three meshes, the second one twice (two definitions of one model). */
static int world(void) {
    void *a = load(0), *b = load(1), *c = load(1), *d = load(2);
    int good = same(a, 0) && same(b, 1) && same(c, 1) && same(d, 2);
    nwFreeStreamBuffer();
    return good; }
static long size_of(const char *path) { struct stat st; return stat(path, &st) ? -1 : (long)st.st_size; }
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "", *path = argc > 2 ? argv[2] : "";
    char other[600];
    int w, i, j;
    long full;
    for (w = 0; w < 3; ++w) {
        for (i = 0; i < 600; ++i) for (j = 0; j < 3; ++j) verts[w][i][j] = (float)(w * 1000 + i * 3 + j) * 0.25f;
        for (i = 0; i < 900; ++i) for (j = 0; j < 3; ++j) tris[w][i][j] = (i * 7 + j + w) % (200 * (w + 1)); }
    /* What the cooker makes of each mesh, taken once without the cache. */
    unsetenv("ARMPORT_PHYSX_CACHE");
    for (w = 0; w < 3; ++w) {
        NxTriangleMesh *mesh = ((NxTriangleMeshShapeDesc *)load(w))->meshData;
        expected[w] = mesh->bytes; expected_size[w] = mesh->size; }
    nwFreeStreamBuffer();
    CHECK(cooks == 3 && creates == 3 && opens == 0);
    RESTART(); cooks = creates = 0;
    snprintf(other, sizeof(other), "%s.new", path);
    if (!strcmp(mode, "physx_cache_disabled")) {
        CHECK(world() && cooks == 4 && creates == 4 && opens == 0 && size_of(path) == -1);
        return 0;
    }
    CHECK(setenv("ARMPORT_PHYSX_CACHE", path, 1) == 0);
    if (!strcmp(mode, "physx_cache")) {
        CHECK(world());                                   /* a first start: everything is cooked */
        CHECK(cooks == 4 && creates == 4 && open_now == 0);
        full = size_of(path);
        RESTART(); cooks = creates = 0;
        CHECK(world());                                   /* the next start: nothing is cooked */
        CHECK(cooks == 0 && creates == 4);
        /* Three records (the model used twice is stored once), and the file is not written again. */
        CHECK(full == 24 + 3 * 36 + (long)(expected_size[0] + expected_size[1] + expected_size[2]));
        CHECK(open_now == 0 && size_of(path) == full && size_of(other) == -1);
        return 0;
    }
    if (!strcmp(mode, "physx_cache_damaged")) {
        int fd; unsigned char byte;
        long first = 24 + 36 + (long)expected_size[0], second = first + 36 + (long)expected_size[1];
        CHECK(world() && cooks == 4);
        full = size_of(path);
        CHECK(full == second + 36 + (long)expected_size[2]);
        /* One changed byte in the second record's stream: that mesh is cooked again, the others are read. */
        fd = open(path, O_RDWR); CHECK(fd >= 0);
        CHECK(pread(fd, &byte, 1, first + 36 + 100) == 1); byte ^= 1;
        CHECK(pwrite(fd, &byte, 1, first + 36 + 100) == 1); close(fd);
        RESTART(); cooks = creates = 0;
        CHECK(world() && cooks == 2 && creates == 4 && open_now == 0);      /* both definitions of that model */
        CHECK(size_of(path) == full + 36 + (long)expected_size[1]);
        RESTART(); cooks = creates = 0;
        CHECK(world() && cooks == 0 && open_now == 0);                      /* the new record comes first */
        /* A stored stream this PhysX refuses is cooked again, and the game gets the same mesh. */
        RESTART(); cooks = creates = 0; refuse_creates = 1;
        CHECK(world() && cooks == 1 && creates == 5 && refuse_creates == 0 && open_now == 0);
        RESTART(); cooks = creates = 0;
        CHECK(world() && cooks == 0 && open_now == 0);
        /* A file cut inside its last stream, then inside a record head: whole records before the cut are used. */
        CHECK(unlink(path) == 0);
        RESTART(); cooks = creates = 0;
        CHECK(world() && cooks == 4 && size_of(path) == full);
        CHECK(truncate(path, full - 10) == 0);
        RESTART(); cooks = creates = 0;
        CHECK(world() && cooks == 1 && open_now == 0);                      /* the third mesh */
        CHECK(unlink(path) == 0);
        RESTART(); cooks = creates = 0;
        CHECK(world() && cooks == 4 && size_of(path) == full);
        CHECK(truncate(path, first + 20) == 0);
        RESTART(); cooks = creates = 0;
        CHECK(world() && cooks == 3 && open_now == 0);                      /* all but the first mesh */
        CHECK(size_of(path) == full);
        /* Another program's file under this name is left unread and replaced. */
        fd = open(path, O_WRONLY | O_TRUNC); CHECK(fd >= 0 && write(fd, "not a cooked mesh file, but long enough", 39) == 39); close(fd);
        RESTART(); cooks = creates = 0;
        CHECK(world() && cooks == 4 && open_now == 0);
        CHECK(size_of(path) == full);
        /* A file that cannot be written changes nothing for the game or the old file. */
        CHECK(truncate(path, first) == 0);
        RESTART(); cooks = creates = 0; fail_writes = 1;
        CHECK(world() && cooks == 3 && open_now == 0);
        CHECK(size_of(path) == first && size_of(other) == -1);
        return 0;
    }
    return 2;
}
'''


def load_profile_fixture(source):
    '''Run the shipping map load profile header over a recorded clock; check its call sites.'''
    header = source / LOAD_PROFILE_HEADER
    if header.is_file():
        model, grid, loader = ((source / name).read_text() for name in LOAD_PROFILE_SOURCES)
        include = '#include "group/armport_map_load_profile.h"\n'
        assert model.count(include) == grid.count(include) == loader.count(include) == 1
        # One translation unit holds the state; the other two only call into it.
        define = '#define ARMPORT_MAP_LOAD_PROFILE_IMPLEMENTATION\n'
        assert loader.count(define + include) == 1 and define not in model and define not in grid
        find = function(model, 'Model * groupModelFind(const char *name)')
        assert find.count('armportMapLoadEnter(ARMPORT_MAP_LOAD_MODEL_FIND);') == 1
        assert find.count('    return ') == find.count('armportMapLoadLeave();') == 2      # every way out leaves
        assert all(part.rstrip().endswith('PERFINFO_AUTO_STOP_CHECKED("groupModelFind");')
                   and 'armportMapLoadLeave();' in part[-120:] for part in find.split('    return ')[:2])
        activate = function(grid, 'void groupRefActivate(DefTracker *ref)')
        order = [activate.index(text) for text in (
            '        return;\n', '    armportMapLoadEnter(ARMPORT_MAP_LOAD_REF_ACTIVATE);\n',
            '    groupLoadIfPreload(ref->def);\n', '    collGridAddGroup(&obj_grid,ref,ref);\n',
            '    armportMapLoadLeave();\n')]
        assert order == sorted(order) and activate.count('return') == 1, order
        load = function(loader, 'void groupLoadMap(char *mapname,int import,int do_beacon_reload)')
        order = [load.index(text) for text in (
            '    loadstart_printf("loading map: %s..",mapname);\n    armportMapLoadBegin();\n',
            '    armportMapLoadEnter(ARMPORT_MAP_LOAD_RECALC_BOUNDS);\n    groupRecalcAllBounds();\n    armportMapLoadLeave();\n',
            '            armportMapLoadEnter(ARMPORT_MAP_LOAD_BOUNDS_FILES);\n'
            '            objectLibraryWriteBoundsFileIfDifferent(group_info.files[i]);\n            armportMapLoadLeave();\n',
            '    armportMapLoadEnter(ARMPORT_MAP_LOAD_SCENE);\n',
            '        sceneLoad(group_info.scenefile);\n    armportMapLoadLeave();\n',
            '        armportMapLoadEnter(ARMPORT_MAP_LOAD_SPAWN_AREAS);\n        spawnAreaReload(pchMap);\n'
            '        armportMapLoadLeave();\n',
            '    loadend_printf("done"); // map load\n    armportMapLoadReport();\n')]
        assert order == sorted(order), order
        assert (loader.count('armportMapLoadBegin();') == loader.count('armportMapLoadReport();') == 1
                and loader.count('armportMapLoadEnter(') == loader.count('armportMapLoadLeave();') == 4)
        # No way out of the load between its first and last line.
        section = load[load.index('    armportMapLoadBegin();\n'):load.index('    armportMapLoadReport();\n')]
        assert 'return' not in section
        body = header.read_text()
        include = '#include <utilitieslib/utils/timing.h>\n'
        assert body.count(include) == 1
        support = '#define ARMPORT_MAP_LOAD_PROFILE_IMPLEMENTATION\n' + body.replace(include, '')
    else:
        support = '''
enum { ARMPORT_MAP_LOAD_OTHER, ARMPORT_MAP_LOAD_MODEL_FIND, ARMPORT_MAP_LOAD_REF_ACTIVATE,
       ARMPORT_MAP_LOAD_RECALC_BOUNDS, ARMPORT_MAP_LOAD_BOUNDS_FILES, ARMPORT_MAP_LOAD_SCENE,
       ARMPORT_MAP_LOAD_SPAWN_AREAS, ARMPORT_MAP_LOAD_STEPS };
static struct { int active; S64 ticks[ARMPORT_MAP_LOAD_STEPS]; unsigned int calls[ARMPORT_MAP_LOAD_STEPS]; } armport_map_load;
static void armportMapLoadBegin(void) { (void)timerCpuTicks64(); (void)timerCpuSpeed64(); }
static void armportMapLoadEnter(int step) { (void)step; }
static void armportMapLoadLeave(void) {}
static void armportMapLoadReport(void) {}
'''
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define SERVER 1
typedef long long S64;
static S64 clock_now, clock_speed = 1000;            /* one tick is one millisecond */
static S64 timerCpuTicks64(void) { return clock_now; }
static S64 timerCpuSpeed64(void) { return clock_speed; }
''' + support + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static void step(int name, S64 until) { armportMapLoadEnter(name); clock_now = until; armportMapLoadLeave(); }
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "";
    int i;
    if (!strcmp(mode, "map_load_profile")) {
        CHECK(setenv("ARMPORT_SERVER_METRICS", "1", 1) == 0);
        step(ARMPORT_MAP_LOAD_MODEL_FIND, 50);                       /* outside a load: not counted */
        armportMapLoadBegin();                                       /* the load begins at 50 */
        clock_now = 150;                                             /* other 100 */
        armportMapLoadEnter(ARMPORT_MAP_LOAD_MODEL_FIND);
        clock_now = 180;                                             /* model_find 30 */
        step(ARMPORT_MAP_LOAD_REF_ACTIVATE, 185);                    /* a nested step: 5, not the model's */
        clock_now = 200;                                             /* model_find 15 more */
        armportMapLoadLeave();
        clock_now = 450;                                             /* other 250 */
        step(ARMPORT_MAP_LOAD_RECALC_BOUNDS, 470);
        for (i = 0; i < 3; i++) step(ARMPORT_MAP_LOAD_BOUNDS_FILES, clock_now + 2);
        step(ARMPORT_MAP_LOAD_SCENE, 481);
        step(ARMPORT_MAP_LOAD_SPAWN_AREAS, 550);
        clock_now = 560;                                             /* other 10 */
        armportMapLoadLeave();                                       /* one leave too many changes nothing */
        armportMapLoadReport();
        CHECK(armport_map_load.calls[ARMPORT_MAP_LOAD_BOUNDS_FILES] == 3 && armport_map_load.ticks[ARMPORT_MAP_LOAD_OTHER] == 360);
        CHECK(armport_map_load.active == 0);
        step(ARMPORT_MAP_LOAD_MODEL_FIND, 600);                      /* after the load: not counted */
        armportMapLoadReport();                                      /* and no second record */
        CHECK(armport_map_load.calls[ARMPORT_MAP_LOAD_MODEL_FIND] == 1);
        armportMapLoadBegin();                                       /* a second load starts from zero */
        for (i = 0; i < 40; i++) { armportMapLoadEnter(ARMPORT_MAP_LOAD_REF_ACTIVATE); ++clock_now; }
        for (i = 0; i < 40; i++) armportMapLoadLeave();              /* deeper than the stack: still balanced */
        armportMapLoadReport();
        armportMapLoadBegin();
        clock_speed = 0;
        armportMapLoadReport();
        return 0;
    }
    if (!strcmp(mode, "map_load_profile_disabled")) {
        unsetenv("ARMPORT_SERVER_METRICS");
        armportMapLoadBegin();
        step(ARMPORT_MAP_LOAD_MODEL_FIND, 50);
        armportMapLoadReport();
        CHECK(armport_map_load.active == 0 && armport_map_load.calls[ARMPORT_MAP_LOAD_MODEL_FIND] == 0);
        CHECK(setenv("ARMPORT_SERVER_METRICS", "1", 1) == 0);        /* read once: still off */
        armportMapLoadBegin();
        armportMapLoadReport();
        return 0;
    }
    return 2;
}
'''


def start_trees_fixture(source):
    '''Run the shipping cacheRelevantFolders and LoadMessageStore bodies over recorded shims.'''
    common = (source / INITCOMMON).read_text()
    store = (source / MESSAGESTORE).read_text()
    helpers = ''.join(function(text, name) for text, name in (
        (common, 'static int armportTrustedStartTrees('), (store, 'static int armportTrustedMessageBins('))
        if name in text)
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define SERVER 1
#define MAX_PATH 260
#define OUTPUT_DEBUG 0
typedef int __time32_t;
typedef struct SharedHeapHandle { int unused; } SharedHeapHandle;
typedef enum { SHAR_Error, SHAR_DataAcquired, SHAR_FirstCaller } SharedHeapAcquireResult;
typedef enum { MSLOAD_DEFAULT = 0, MSLOAD_RELOADING = 1, MSLOAD_NOFILES = 2, MSLOAD_SERVERONLY = 4,
               MSLOAD_FORCEBINS = 8 } MessageStoreLoadFlags;
typedef struct MessageStore { SharedHeapHandle *pHandle; int localeID; int from_bin; int texts; } MessageStore;
typedef struct MSFileInfo { __time32_t time_write; char filename[16]; } MSFileInfo;
static struct { int unused; } *folder_cache;
static int quickload;
static char requested[8][64];
static int requests, listings, date_checks, bin_reads, bin_writes, text_loads, loaded_without_list, created, destroyed;
static int bin_exists = 1, read_works = 1, development = 1;
static MSFileInfo listed[2] = {{1, "texts/a.ms"}, {1, "texts/b.ms"}};
static MSFileInfo *listed_rows[2] = {&listed[0], &listed[1]};
static void writeConsole(int level, const char *format, ...) { (void)level; (void)format; }
static void FolderCacheRequestTree(void *cache, const char *path) {
    (void)cache; if (requests < 8) snprintf(requested[requests], sizeof requested[0], "%s", path); ++requests; }
static MessageStore *createMessageStore(MessageStoreLoadFlags flags) { (void)flags; ++created; return calloc(1, sizeof(MessageStore)); }
static void destroyMessageStore(MessageStore *store) { ++destroyed; free(store); }
static int isDevelopmentMode(void) { return development; }
static int isProductionMode(void) { return !development; }
static const char *locGetAlpha2(int locid) { (void)locid; return "en"; }
static char *fileLocateRead(const char *path, char *buffer) {
    if (!bin_exists) return NULL;
    snprintf(buffer, MAX_PATH, "%s", path); return buffer; }
static char *fileLocateWrite(const char *path, char *buffer) { snprintf(buffer, MAX_PATH, "%s", path); return buffer; }
static void FatalErrorFilenamef(const char *file, const char *format, ...) { (void)file; (void)format; abort(); }
static void ErrorFilenamef(const char *file, const char *format, ...) { (void)file; (void)format; abort(); }
static void Sleep(int ms) { (void)ms; abort(); }
#define STR_COMBINE_SSD(buffer, a, b, d) snprintf(buffer, sizeof(buffer), "%s%s%d", a, b, d)
static SharedHeapAcquireResult sharedHeapAcquire(SharedHeapHandle **handle, const char *name) {
    (void)handle; (void)name; abort(); }
static void setStorePointersToSharedHeap(MessageStore *store) { (void)store; }
static bool msMoveStoreIntoSharedHeap(MessageStore *store) { (void)store; return true; }
static void msSetPrepend(MessageStore *store, const char *prepend) { (void)store; (void)prepend; }
static void msGetDirFilesList(MSFileInfo ***dirfiles, char **dirs) { (void)dirs; ++listings; *dirfiles = listed_rows; }
static int eaSize(MSFileInfo ***rows) { return *rows ? 2 : 0; }
static void eaDestroyEx(MSFileInfo ***rows, void *destructor) { (void)destructor; *rows = NULL; }
static __time32_t fileLastChanged(const char *path) { (void)path; ++date_checks; return 2; }
static int msReadBin(const char *name, MessageStore *store) { (void)name; ++bin_reads; store->from_bin = read_works; return read_works; }
static int msWriteBin(const char *name, MessageStore *store) { (void)name; (void)store; ++bin_writes; return 1; }
static void initMessageStore(MessageStore *store, int locid, const char *prepend) { (void)store; (void)locid; (void)prepend; }
static void msAddMessages(MessageStore *store, MessageStoreLoadFlags flags, const char *messages, const char *types) {
    (void)flags; (void)types; ++text_loads; ++store->texts;
    if (strcmp(messages, "texts/a.ms") && strcmp(messages, "texts/b.ms") && strcmp(messages, "texts/x.ms")) ++loaded_without_list; }
static void mkdirtree(char *path) { (void)path; }
''' + helpers + function(common, 'void cacheRelevantFolders() {') + function(store, 'void LoadMessageStore( MessageStore **pStore,') + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static char *files[] = {"texts/x.ms", NULL, NULL};
static char *dirs[] = {"texts/English", NULL};
static MessageStore *load(char *persist, MessageStoreLoadFlags flags) {
    MessageStore *store = NULL;
    LoadMessageStore(&store, files, dirs, 0, NULL, persist, NULL, flags);
    return store;
}
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "";
    MessageStore *store;
    if (!strcmp(mode, "start_trees") || !strcmp(mode, "start_trees_disabled")) {
        int trusted = !strcmp(mode, "start_trees");
        if (trusted) CHECK(setenv("ARMPORT_TRUSTED_BINS", "1", 1) == 0); else unsetenv("ARMPORT_TRUSTED_BINS");
        cacheRelevantFolders();
        if (trusted) {
            store = load("messages", MSLOAD_SERVERONLY);
            CHECK(requests == 4 && listings == 0 && date_checks == 0);
            CHECK(store && store->from_bin == 1);
            free(store);
            CHECK(!strcmp(requested[0], "player_library/animations/male") && !strcmp(requested[3], "player_library/animations/Vahzilok"));
        } else {
            CHECK(requests == 6 && !strcmp(requested[0], "Defs") && !strcmp(requested[1], "Menu"));
            CHECK(!strcmp(requested[2], "player_library/animations/male") && !strcmp(requested[5], "player_library/animations/Vahzilok"));
        }
        requests = 0; quickload = 1;                      /* the game's own quickload switch is as before */
        cacheRelevantFolders();
        CHECK(requests == (trusted ? 0 : 2));
        return 0;
    }
    if (!strcmp(mode, "message_bins")) {
        CHECK(setenv("ARMPORT_TRUSTED_BINS", "1", 1) == 0);
        store = load("messages", MSLOAD_SERVERONLY);
        CHECK(store && store->from_bin == 1 && store->texts == 0);
        CHECK(listings == 0 && date_checks == 0 && bin_reads == 1 && text_loads == 0 && bin_writes == 0);
        free(store);
        store = load("menuMessages", MSLOAD_DEFAULT);       /* a client-and-server bin: the same */
        CHECK(store && store->from_bin == 1 && listings == 0 && date_checks == 0 && bin_reads == 2);
        free(store);
        store = load("messages", MSLOAD_SERVERONLY | MSLOAD_RELOADING);   /* a reload reads the text files */
        CHECK(store && store->texts == 3 && listings == 1 && bin_reads == 2 && bin_writes == 1);
        free(store);
        store = load("messages", MSLOAD_SERVERONLY | MSLOAD_FORCEBINS);   /* forced bins: listed, rebuilt */
        CHECK(store && store->texts == 3 && listings == 2 && bin_reads == 2 && bin_writes == 2);
        free(store);
        store = load(NULL, MSLOAD_DEFAULT);                 /* no bin asked for: the text files */
        CHECK(store && store->texts == 3 && listings == 3 && bin_reads == 2 && bin_writes == 2);
        free(store);
        development = 0;                                    /* production mode is as before */
        store = load("messages", MSLOAD_SERVERONLY);
        CHECK(store && store->from_bin == 1 && listings == 3 && date_checks == 0 && bin_reads == 3);
        free(store);
        CHECK(loaded_without_list == 0);
        return 0;
    }
    if (!strcmp(mode, "message_bins_disabled")) {
        unsetenv("ARMPORT_TRUSTED_BINS");
        store = load("messages", MSLOAD_SERVERONLY);
        CHECK(store && store->from_bin == 1 && store->texts == 0);
        CHECK(listings == 1 && date_checks == 2 && bin_reads == 1 && text_loads == 0);
        free(store);
        return 0;
    }
    if (!strcmp(mode, "message_bins_fallback")) {
        CHECK(setenv("ARMPORT_TRUSTED_BINS", "1", 1) == 0);
        read_works = 0;                                     /* a bin msReadBin refuses: list, load text, write */
        store = load("messages", MSLOAD_SERVERONLY);
        CHECK(store && store->from_bin == 0 && store->texts == 3);
        CHECK(listings == 1 && date_checks == 0 && bin_reads == 1 && text_loads == 3 && bin_writes == 1);
        CHECK(created == 2 && destroyed == 1);
        free(store);
        bin_exists = 0;                                     /* no bin: the same without a read */
        store = load("messages", MSLOAD_SERVERONLY);
        CHECK(store && store->texts == 3 && listings == 2 && bin_reads == 1 && text_loads == 6 && bin_writes == 2);
        free(store);
        CHECK(loaded_without_list == 0);
        return 0;
    }
    return 2;
}
'''


def object_library_fixture(source):
    """Run the shipping UpdateObjectLibraryBin body over recorded file-list and parser shims."""
    text = (source / GROUPFILELIB).read_text()
    name = 'static int armportTrustedObjectLibrary('
    helper = function(text, name) if name in text else ''
    body = function(text, 'static int UpdateObjectLibraryBin(')
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct SimpleBuf { int pos; } *SimpleBufHandle;
typedef struct ParseTable { int unused; } ParseTable;
typedef struct FileEntry { const char *path; } FileEntry;
typedef FileEntry **FileList;
struct _finddata32_t { unsigned attrib; char name[260]; };
typedef int FileScanAction;
#define PARSE_SIG "Parse6"
#define verbose_printf(...) ((void)0)
static struct SimpleBuf bin_buffer;
static FileEntry *disk_list[1];
static ParseTable GroupNamesSaveInfo[1];
static struct { int unused; } group_names;
static FileList object_lib_disk = 0;
static int scans, date_checks, list_reads, bin_reads, closes, rebuilds, writes, rebuilt_without_list;
static int bin_exists = 1, crc_matches = 1, read_works = 1;
static FileScanAction populateFileList(char *dir, struct _finddata32_t *data) { (void)dir; (void)data; return 0; }
static void FileListCreate(FileList *list) { *list = disk_list; }
static void FileListDestroy(FileList *list) { *list = NULL; }
static void fileScanAllDataDirs(const char *dir, FileScanAction (*callback)(char *, struct _finddata32_t *)) {
    if (strcmp(dir, "object_library") || callback != populateFileList) abort();
    ++scans; }
static int fileExists(const char *path) { (void)path; return bin_exists; }
static int ParserCRCFromParseInfo(ParseTable pti[], void *defines) { (void)pti; (void)defines; return 7; }
static SimpleBufHandle SerializeReadOpen(const char *name, const char *type, int crc, int ignore_crc) {
    (void)name; (void)type; return (crc_matches && (crc == 7 || ignore_crc)) ? &bin_buffer : NULL; }
static int SimpleBufTell(SimpleBufHandle h) { return h->pos; }
static void SimpleBufSeek(SimpleBufHandle h, int pos, int whence) { (void)whence; h->pos = pos; }
static void SerializeClose(SimpleBufHandle h) { (void)h; ++closes; }
static int FileListRead(FileList *list, SimpleBufHandle h) { (void)h; ++list_reads; *list = NULL; return 1; }
static int FileListIsBinUpToDate(FileList *bin, FileList *disk) { (void)bin; (void)disk; ++date_checks; return 1; }
static int ParserReadBinaryFile(SimpleBufHandle h, void *a, ParseTable pti[], void *data, void *b, void *c) {
    (void)h; (void)a; (void)pti; (void)data; (void)b; (void)c; ++bin_reads; return read_works; }
static void loadGroupNamesFromFileList(FileList *list) { ++rebuilds; if (*list != disk_list) ++rebuilt_without_list; }
static void ParserWriteBinaryFile(const char *name, ParseTable pti[], void *data, FileList *list, void *a, int b, int c) {
    (void)name; (void)pti; (void)data; (void)list; (void)a; (void)b; (void)c; ++writes; }
''' + helper + body + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "";
    if (!strcmp(mode, "object_library")) {
        CHECK(setenv("ARMPORT_TRUSTED_BINS", "1", 1) == 0);
        CHECK(UpdateObjectLibraryBin(0, 0) == 1);
        CHECK(scans == 0 && date_checks == 0);
        CHECK(list_reads == 1 && bin_reads == 1 && rebuilds == 0 && writes == 0);
        CHECK(UpdateObjectLibraryBin(0, 1) == 1);          /* a forced rebuild check still scans and compares */
        CHECK(scans == 1 && date_checks == 1 && rebuilds == 0);
        CHECK(UpdateObjectLibraryBin(1, 0) == 1);          /* production mode is as before: no scan */
        CHECK(scans == 1 && date_checks == 1);
        return 0;
    }
    if (!strcmp(mode, "object_library_disabled")) {
        unsetenv("ARMPORT_TRUSTED_BINS");
        CHECK(UpdateObjectLibraryBin(0, 0) == 1);
        CHECK(scans == 1 && date_checks == 1 && rebuilds == 0);
        return 0;
    }
    if (!strcmp(mode, "object_library_rebuild")) {
        CHECK(setenv("ARMPORT_TRUSTED_BINS", "1", 1) == 0);
        bin_exists = 0;                                     /* no bin: scan, rebuild from the list, write */
        CHECK(UpdateObjectLibraryBin(0, 0) == 0);
        CHECK(scans == 1 && rebuilds == 1 && writes == 1 && rebuilt_without_list == 0);
        bin_exists = 1; crc_matches = 0;                    /* another parse table: the same */
        CHECK(UpdateObjectLibraryBin(0, 0) == 0);
        CHECK(scans == 2 && rebuilds == 2 && writes == 2 && rebuilt_without_list == 0);
        crc_matches = 1; read_works = 0;                    /* unreadable data: the same */
        CHECK(UpdateObjectLibraryBin(0, 0) == 0);
        CHECK(scans == 3 && rebuilds == 3 && writes == 3 && rebuilt_without_list == 0 && date_checks == 0);
        return 0;
    }
    return 2;
}
'''


def trusted_fixture(source):
    """Run the shipping ParserIsPersistNewer body over recorded parser shims."""
    text = (source / TEXTPARSER).read_text()
    helper = function(text, 'static int armportTrustedBin(') if 'static int armportTrustedBin(' in text else ''
    body = function(text, 'SimpleBufHandle ParserIsPersistNewer(')
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int __time32_t;
typedef struct SimpleBuf { int pos; } *SimpleBufHandle;
typedef struct ParseTable { int unused; } ParseTable;
typedef struct DefineContext DefineContext;
typedef struct FileEntry { const char *path; __time32_t date; int seen; } FileEntry;
typedef FileEntry **FileList;
struct _finddata32_t { unsigned attrib; char name[260]; __time32_t time_write; };
typedef int FileScanAction;
#define PARSE_SIG "Parse6"
#define verbose_printf(...) ((void)0)
static struct SimpleBuf bin_buffer;
static FileList lf_filedates;
static int scans, list_reads, closes, production, crc_matches = 1;
static const char *g_StdAdditionalFilePrefixes[] = {""};
static int ParseTableCRC(ParseTable pti[], DefineContext *defines) { (void)pti; (void)defines; return 7; }
static SimpleBufHandle SerializeReadOpen(const char *name, const char *type, int crc, int ignore_crc) {
    (void)name; (void)type; return (crc_matches && (crc == 7 || ignore_crc)) ? &bin_buffer : NULL; }
static int isProductionMode(void) { return production; }
static int SimpleBufTell(SimpleBufHandle h) { return h->pos; }
static void SimpleBufSeek(SimpleBufHandle h, int pos, int whence) { (void)whence; h->pos = pos; }
static void SerializeClose(SimpleBufHandle h) { (void)h; ++closes; }
static int FileListRead(FileList *list, SimpleBufHandle h) { (void)h; ++list_reads; *list = NULL; return 1; }
static void FileListCreate(FileList *list) { *list = NULL; }
static void FileListDestroy(FileList *list) { *list = NULL; }
static void FileListInsert(FileList *list, const char *path, __time32_t date) { (void)list; (void)path; (void)date; }
static FileEntry *FileListFind(FileList *list, const char *path) { (void)list; (void)path; return NULL; }
static int eaSize(FileList *list) { (void)list; return 0; }
static char *addFilePrefix(const char *mask, const char *prefix) { (void)prefix; return (char *)mask; }
static FileScanAction DateCheckCallback(char *dir, struct _finddata32_t *data) { (void)dir; (void)data; return 0; }
static void fileScanAllDataDirs(const char *dir, FileScanAction (*callback)(char *, struct _finddata32_t *)) {
    (void)dir; (void)callback; ++scans; }
static int fileDatesEqual(__time32_t a, __time32_t b, bool exact) { (void)exact; return a == b; }
static __time32_t fileLastChanged(const char *path) { (void)path; return 0; }
static int fileExists(const char *path) { (void)path; return 0; }
''' + helper + body + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(int argc, char **argv) {
    ParseTable pti[1] = {{0}};
    int i;
    const char *mode = argc > 1 ? argv[1] : "";
    if (!strcmp(mode, "trusted_bins")) {
        CHECK(setenv("ARMPORT_TRUSTED_BINS", "1", 1) == 0);
        CHECK(ParserIsPersistNewer("fx", NULL, "bin/fxinfo.bin", pti, NULL) == &bin_buffer);
        CHECK(scans == 0 && list_reads == 0);
        crc_matches = 0;
        CHECK(ParserIsPersistNewer("fx", NULL, "bin/fxinfo.bin", pti, NULL) == NULL);
        crc_matches = 1;
        for (i = 0; i < 300; ++i)
            CHECK(ParserIsPersistNewer("maps", NULL, "bin/minimap.bin", pti, NULL) == &bin_buffer);
        CHECK(scans == 0 && list_reads == 0 && closes == 0);
        return 0;
    }
    if (!strcmp(mode, "trusted_bins_disabled")) {
        unsetenv("ARMPORT_TRUSTED_BINS");
        CHECK(ParserIsPersistNewer("fx", NULL, "bin/fxinfo.bin", pti, NULL) == &bin_buffer);
        CHECK(scans == 1 && list_reads == 1);
        return 0;
    }
    return 2;
}
'''


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 3]


def startup_calls(svr, original=False):
    """Use the shipping call sites, expanding sysInit at its real main call."""
    main = svr[svr.index('int __cdecl main(int argc,char **argv)'):]
    pattern = r'^\s*(armportServerStartup(?:Begin\(\)|Phase\("[a-z_]+", db_state.map_id\));|sysInit\(\);)'
    calls = []
    for call in re.findall(pattern, main, re.MULTILINE):
        if call == 'sysInit();':
            calls.extend(re.findall(pattern, function(svr, 'static void sysInit()'), re.MULTILINE))
        else:
            calls.append(call)
    if not original:
        assert calls[0] == 'armportServerStartupBegin();'
        assert main.index(calls[0]) < main.index('memCheckInit();')
        # Early diagnostic commands can exit in parseArgs1. Their stdout
        # stays quiet even when telemetry was requested.
        assert main.index('parseArgs1(argc,argv);') < main.index(calls[1])
        assert main.index('dbReadyForPlayers();') < main.index('armportServerStartupPhase("ready_published"')
        assert main.index('armportServerStartupPhase("main_loop_begin"') < main.index('armportServerMetricsInit(')
        assert len(calls) == 18, calls
    return '\n'.join(('    ' if i == 0 else '    fake_now += 100; ') + call.replace('db_state.map_id', '2')
                     for i, call in enumerate(calls))


def fixture(source, original=None):
    root = original or source
    files = (root / 'libs/UtilitiesLib/src/utils/file.c').read_text()
    svr = (root / 'MapServer/src/svr/svr_init.c').read_text()
    marker = svr.index('    if (coll_test)\n        gridCollPerfTest();')
    start = svr.index('    for(;;)\n    {', marker)
    end = svr.index('\n    }\n    EXCEPTION_HANDLER_END', start)
    loop = svr[start + len('    for(;;)\n    {'):end]
    if original:
        bodies = function(files, 'void *fileAlloc_dbg(') + function(files, 'void *fileAllocEx_dbg(')
    else:
        bodies = ''.join(function(files, sig) for sig in (
            'static void *fileAllocInternal_dbg(', 'void *fileAlloc_dbg(',
            'static void *fileAllocExInternal_dbg(', 'void *fileAllocEx_dbg('))
        assert '#include "armport_server_metrics_impl.h"' in files
        assert 'armportServerMetricsInit(db_state.map_id);' in svr[marker:start]
        assert loop.index('armportServerMetricsTickBegin();') < loop.index('svrTick();')
        assert loop.index('svrTick();') < loop.index('armportServerMetricsTickEnd();') < loop.index('sleepAndCalcTimers();')
        assert loop.index('sleepAndCalcTimers();') < loop.index('armportServerMetricsLoopEnd();')
        assert loop.strip().startswith('armportServerMetricsTickBegin();')
        assert loop.strip().endswith('armportServerMetricsLoopEnd();')
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#define __declspec(x) __thread
static __thread long long fake_now;
static __thread int clock_calls, clock_ok = 1;
static int frequency_ok = 1;
static int progress_marker_ms;
#include "utilitieslib/utils/wininclude.h"
static int QueryPerformanceCounter(LARGE_INTEGER *p) { ++clock_calls; p->QuadPart = fake_now; return clock_ok; }
static int QueryPerformanceFrequency(LARGE_INTEGER *p) { p->QuadPart = 1000; return frequency_ok; }
static DWORD GetCurrentProcessId(void) { return 42; }
/* Poison the same CRT names file.h replaces. The producer must isolate them. */
#define snprintf forbidden_snprintf
#define fputs forbidden_fputs
#define fflush forbidden_fflush
#define FILE ForbiddenFileWrapper
#include "armport_server_metrics_impl.h"
#undef snprintf
#undef fputs
#undef fflush
#undef FILE
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
#define MEM_DBG_PARMS
#define MEM_DBG_PARMS_CALL
#define MAX_PATH 1024
#define PERFINFO_AUTO_START(a,b)
#define PERFINFO_AUTO_STOP()
#define PERFINFO_AUTO_STOP_START(a,b)
#define PERFINFO_AUTO_STOP_CHECKED(a)
#define cohMapProgressMark(a) (fake_now += progress_marker_ms)
#define assert(x) ((void)0)
typedef int (*FileProcessCallback)(int, int);
static int filealloc_failure_spot;
static int io_failure, nested_once;
static char *fileLocateRead(const char *name, char *buffer) {
    fake_now += 5; if (io_failure == 1) return NULL; strcpy(buffer, name); return buffer;
}
static intptr_t fileSize(const char *name) { (void)name; fake_now += 5; return io_failure == 2 ? -1 : 3; }
static int is_pigged_path(const char *name) { (void)name; return 0; }
static FILE *fake_open(const char *name, const char *mode) { (void)name; (void)mode; fake_now += 10; return io_failure == 3 ? NULL : (FILE *)(uintptr_t)1; }
static size_t fake_read(void *buffer, size_t size, size_t count, FILE *file) {
    (void)size; (void)file; fake_now += 20; memcpy(buffer, "abc", count); return count;
}
static int fake_close(FILE *file) { (void)file; fake_now += 10; return 0; }
static void *fake_malloc(size_t n) { return io_failure == 4 ? NULL : malloc(n); }
#define fopen fake_open
#define fread fake_read
#define fclose fake_close
#define smalloc fake_malloc
#define srealloc realloc
''' + bodies + r'''
#undef fopen
#undef fread
#undef fclose
static int nested(int done, int total) {
    (void)done; (void)total;
    if (!nested_once++) { void *p = fileAlloc_dbg("nested", NULL); free(p); }
    return 1;
}
static void timerTickBegin(void) {}
static void timerTickEnd(void) {}
static void startProfilingCPU(void) {}
static void endProfilingCPU(void) {}
static void svrTick(void) { void *p = fileAlloc_dbg("file", NULL); free(p); fake_now += 200; }
static void sleepAndCalcTimers(void) { fake_now += 750; }
static void one_actual_loop(void) {
''' + loop + r'''
}
static void actual_startup_observations(void) {
''' + startup_calls(svr, original is not None) + r'''
}
static void *background(void *unused) {
    void *p;
    (void)unused;
    /* Main thread opt-in must not enable another thread or share counters. */
    p = fileAlloc_dbg("worker", NULL); free(p);
    return (void *)(uintptr_t)(clock_calls != 0 || armport_server_metrics.enabled != 0);
}
int main(int argc, char **argv) {
    ArmportServerMetrics *s = &armport_server_metrics;
    const char *mode = argc > 1 ? argv[1] : "window";
    int i;
    /* Keep helpers referenced in the original-code negative control. */
    (void)armportServerMetricsFileBegin; (void)armportServerMetricsFileEnd;
    setenv("ARMPORT_SERVER_METRICS", "1", 1);
    if (!strcmp(mode, "startup")) {
        ArmportServerStartup *startup = &armport_server_startup;
        actual_startup_observations();
        CHECK(startup->enabled && startup->sequence == 17);
        CHECK(startup->begin == 0 && startup->previous == 1700);
        CHECK(s->enabled == 0 && s->file_calls == 0 && s->ticks == 0);
        return 0;
    }
    if (!strcmp(mode, "startup_disabled")) {
        const char *options[] = {"0", "", "10", "true"};
        for (i = 0; i < 4; ++i) {
            setenv("ARMPORT_SERVER_METRICS", options[i], 1);
            actual_startup_observations();
        }
        unsetenv("ARMPORT_SERVER_METRICS"); actual_startup_observations();
        CHECK(clock_calls == 0 && armport_server_startup.sequence == 0);
        puts("startup disabled: clocks=0"); return 0;
    }
    if (!strcmp(mode, "startup_clock")) {
        ArmportServerStartup *startup = &armport_server_startup;
        frequency_ok = 0; armportServerStartupBegin();
        CHECK(startup->clock_error && !startup->enabled);
        armportServerStartupPhase("args_parsed", 2);
        CHECK(!startup->clock_error && !startup->enabled && startup->sequence == 0);
        i = clock_calls; armportServerStartupPhase("ignored", 2); CHECK(clock_calls == i);
        frequency_ok = 1; fake_now = 20; armportServerStartupBegin();
        CHECK(startup->enabled && startup->sequence == 0);
        fake_now = 19; armportServerStartupPhase("args_parsed", 2);
        CHECK(!startup->enabled && startup->sequence == 0);
        fake_now = 30; armportServerStartupBegin(); clock_ok = 0;
        armportServerStartupPhase("args_parsed", 2); CHECK(!startup->enabled);
        return 0;
    }
    if (!strcmp(mode, "disabled")) {
        const char *options[] = {"0", "", "10", "true"};
        for (i = 0; i < 4; ++i) {
            setenv("ARMPORT_SERVER_METRICS", options[i], 1);
            armportServerMetricsInit(2);
            one_actual_loop();
        }
        unsetenv("ARMPORT_SERVER_METRICS"); armportServerMetricsInit(2); one_actual_loop();
        CHECK(clock_calls == 0 && s->ticks == 0);
        puts("disabled: clocks=0"); return 0;
    }
    armportServerMetricsInit(2);
    if (!strcmp(mode, "progress_markers")) {
        progress_marker_ms = 10;
        one_actual_loop();
        CHECK(s->ticks == 1 && s->file_calls == 1);
        CHECK(s->max_tick_ms == 280 && s->max_loop_ms == 1040 && s->file_ms == 50);
        puts("progress markers: work_ms=280 loop_ms=1040 file_ms=50"); return 0;
    }
    if (!strcmp(mode, "window")) {
        for (i = 0; i < 4; ++i) one_actual_loop();
        CHECK(s->ticks == 4 && s->file_calls == 4 && s->window_start == 0);
        CHECK(s->max_tick_ms == 250 && s->max_loop_ms == 1000 && s->file_ms == 200);
        one_actual_loop(); /* Exactly five seconds, not strictly greater. */
        CHECK(s->ticks == 0 && s->file_ms == 0 && s->window_start == 5000);
        for (i = 0; i < 5; ++i) one_actual_loop();
        CHECK(s->window_start == 10000); return 0;
    }
    if (!strcmp(mode, "files")) {
        int len = 0, before = clock_calls;
        void *p = fileAlloc_dbg("outside_tick", &len);
        CHECK(p && len == 3 && !memcmp(p, "abc", 4)); free(p);
        CHECK(clock_calls == before && s->file_calls == 0);
        armportServerMetricsTickBegin();
        for (io_failure = 1; io_failure <= 4; ++io_failure) {
            p = fileAlloc_dbg("failed", NULL); CHECK(!p);
        }
        io_failure = 0;
        p = fileAllocEx_dbg("outer", &len, "rb", nested);
        CHECK(p && len == 3 && !memcmp(p, "abc", 4)); free(p);
        /* 5+10+20+30 failed; outer50+nested50; nested is counted once. */
        CHECK(s->file_calls == 5 && s->file_failures == 4 && s->file_ms == 165 && s->file_depth == 0);
        armportServerMetricsTickEnd();
        puts("files: failures=4 outer_calls=5 wall_ms=165"); return 0;
    }
    if (!strcmp(mode, "thread")) {
        pthread_t thread; void *result;
        CHECK(pthread_create(&thread, NULL, background, NULL) == 0);
        CHECK(pthread_join(thread, &result) == 0 && result == NULL);
        CHECK(s->enabled == 1 && s->file_calls == 0);
        puts("thread: uninitialized TLS stays disabled"); return 0;
    }
    if (!strcmp(mode, "slow")) {
        armportServerMetricsTickBegin();
        fake_now = 7000; armportServerMetricsTickEnd();
        fake_now = 7500; armportServerMetricsLoopEnd();
        CHECK(s->window_start == 7500 && s->ticks == 0);
        return 0;
    }
    if (!strcmp(mode, "clock")) {
        clock_ok = 0; armportServerMetricsTickBegin();
        CHECK(!s->enabled && s->ticks == 0);
        i = clock_calls; one_actual_loop(); CHECK(clock_calls == i);
        clock_ok = 1; fake_now = 20; armportServerMetricsInit(2);
        fake_now = 19; armportServerMetricsTickBegin(); CHECK(!s->enabled);
        frequency_ok = 0; armportServerMetricsInit(2); CHECK(!s->enabled);
        return 0;
    }
    if (!strcmp(mode, "saturation")) {
        s->ticks = ULLONG_MAX;
        one_actual_loop(); CHECK(s->ticks == ULLONG_MAX && s->saturated);
        puts("saturation: no counter wrap"); return 0;
    }
    return 2;
}
'''


def run(source, original=None, expect_control_failure=False):
    with tempfile.TemporaryDirectory(prefix='armport-server-metrics-') as directory:
        work = Path(directory)
        inc = work / 'utilitieslib/utils'
        inc.mkdir(parents=True)
        (inc / 'wininclude.h').write_text('#ifndef TEST_WINDOWS\n#define TEST_WINDOWS\ntypedef uint32_t DWORD; typedef long long LONGLONG; typedef struct { LONGLONG QuadPart; } LARGE_INTEGER;\n#endif\n')
        (inc / 'armport_server_metrics.h').write_bytes((source / 'libs/UtilitiesLib/include/utilitieslib/utils/armport_server_metrics.h').read_bytes())
        (work / 'armport_server_metrics_impl.h').write_bytes((source / 'libs/UtilitiesLib/src/utils/armport_server_metrics_impl.h').read_bytes())
        control = fixture(source, original)
        (work / 'control.c').write_text(control)
        exe = work / 'control'
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-but-set-variable',  # upstream fileAllocEx original_total
                        '-fsanitize=address,undefined', '-pthread', '-I', str(work),
                        str(work / 'control.c'), '-o', str(exe)], check=True)
        trusted_root = original or source
        trusted = work / 'trusted'
        (work / 'trusted.c').write_text(trusted_fixture(trusted_root))
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-label', '-fsanitize=address,undefined',
                        str(work / 'trusted.c'), '-o', str(trusted)], check=True)
        control += trusted_fixture(trusted_root)
        spare = work / 'spare'
        (work / 'spare.c').write_text(spare_fixture(trusted_root))
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-function', '-fsanitize=address,undefined',
                        str(work / 'spare.c'), '-o', str(spare)], check=True)
        control += spare_fixture(trusted_root)
        library = work / 'library'
        (work / 'library.c').write_text(object_library_fixture(trusted_root))
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined',
                        str(work / 'library.c'), '-o', str(library)], check=True)
        control += object_library_fixture(trusted_root)
        physx = work / 'physx'
        (work / 'physx.cpp').write_text(physx_fixture(trusted_root))
        subprocess.run(['c++', '-std=gnu++11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                        '-Wno-unused-function', '-fsanitize=address,undefined',
                        str(work / 'physx.cpp'), '-o', str(physx)], check=True)
        control += physx_fixture(trusted_root)
        trees = work / 'trees'
        (work / 'trees.c').write_text(start_trees_fixture(trusted_root))
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                        '-fsanitize=address,undefined',
                        str(work / 'trees.c'), '-o', str(trees)], check=True)
        control += start_trees_fixture(trusted_root)
        profile = work / 'profile'
        (work / 'profile.c').write_text(load_profile_fixture(trusted_root))
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                        '-Wno-missing-field-initializers',   # the header's `= { -1 }` state
                        '-fsanitize=address,undefined',
                        str(work / 'profile.c'), '-o', str(profile)], check=True)
        control += load_profile_fixture(trusted_root)
        environment = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'}
        for mode in (['window', 'startup', 'trusted_bins', 'spare_server', 'object_library', 'physx_cache',
                      'start_trees', 'map_load_profile']
                     if original and expect_control_failure else
                     (['window'] if original else test_cases(source))):
            if mode == 'spare_server_invalid':
                # Every malformed assignment, and a server in local mode, ends the process with
                # status 3 before it has touched its map id or the DbServer.
                invalid = ['ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=1', 'ARMPORT_SPARE_ASSIGN_V1 map_id=0 cookie=1\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=071 cookie=1\n', 'ARMPORT_SPARE_ASSIGN_V1 map_id=100000 cookie=1\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=2147483648\n', 'ARMPORT_SPARE_ASSIGN_V1 map_id=71  cookie=1\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=1 \n', 'ARMPORT_SPARE_ASSIGN_V2 map_id=71 cookie=1\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=-1 cookie=1\n', 'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=1\nmore\n', '\n', 'x' * 200 + '\n']
                for text in invalid:
                    result = subprocess.run([str(spare), mode, text], capture_output=True, text=True, env=environment)
                    assert result.returncode == 3 and result.stdout.splitlines() == [
                        'ARMPORT_SPARE_V1 status=waiting pid=42 placeholder_map_id=71',
                        'ARMPORT_SPARE_V1 status=refused pid=42 reason=invalid_assignment'], (text, result)
                result = subprocess.run([str(spare), mode, 'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=1\n', 'local'],
                                        capture_output=True, text=True, env=environment)
                assert result.returncode == 3 and result.stdout.splitlines()[-1] == \
                    'ARMPORT_SPARE_V1 status=refused pid=42 reason=local_server', result
                print(mode + ': %d malformed assignments and local mode refused' % len(invalid))
                continue
            program = (trusted if mode in TRUSTED_CASES else spare if mode in SPARE_CASES
                       else library if mode in OBJECT_LIBRARY_CASES else physx if mode in PHYSX_CASES
                       else trees if mode in START_TREES_CASES
                       else profile if mode in LOAD_PROFILE_CASES else exe)
            arguments = [str(work / (mode + '-cooked.bin'))] if mode in PHYSX_CASES else []
            for stale in arguments:
                Path(stale).unlink(missing_ok=True)       # the unpatched control runs the same mode again
            result = subprocess.run([str(program), mode, *arguments], capture_output=True, text=True, env=environment)
            print(mode + ': ' + ' | '.join(result.stdout.splitlines()))
            if expect_control_failure:
                assertion = {'window': NEGATIVE_ASSERTION, 'trusted_bins': TRUSTED_NEGATIVE_ASSERTION,
                             'spare_server': SPARE_NEGATIVE_ASSERTION,
                             'object_library': OBJECT_LIBRARY_NEGATIVE_ASSERTION,
                             'physx_cache': PHYSX_NEGATIVE_ASSERTION,
                             'start_trees': START_TREES_NEGATIVE_ASSERTION,
                             'map_load_profile': LOAD_PROFILE_NEGATIVE_ASSERTION}.get(mode, STARTUP_NEGATIVE_ASSERTION)
                assert result.returncode != 0 and 'FAIL line ' in result.stderr and assertion in result.stderr, result.stderr
                print('unpatched negative control: expected missing-' + mode + ' assertion')
                continue
            if result.returncode:
                print(result.stderr)
                raise SystemExit(result.returncode)
            if mode == 'window':
                rows = result.stdout.splitlines()
                assert len(rows) == 2, rows
                expected = {'status': 'ok', 'map_id': '2', 'pid': '42', 'seconds': '5.000000',
                            'ticks': '5', 'max_tick_ms': '250.000', 'max_loop_ms': '1000.000',
                            'filealloc_ms': '250.000', 'filealloc_calls': '5', 'filealloc_failures': '0',
                            'counter_saturated': '0', 'scope': 'post_ready_main_thread_outer_filealloc'}
                for row in rows:
                    assert row.startswith('ARMPORT_SERVER_METRICS_V1 '), row
                    assert dict(field.split('=', 1) for field in row.split()[1:]) == expected, row
            if mode == 'disabled':
                assert 'ARMPORT_SERVER_METRICS_V1' not in result.stdout
            if mode == 'startup':
                rows = result.stdout.splitlines()
                assert len(rows) == 17, rows
                phases = ['args_parsed', 'directory_cache_begin', 'directory_cache_done', 'sys_init_done',
                          'server_state_done', 'map_metadata_done', 'sequencer_info_done', 'definitions_done',
                          'encounter_scripts_done', 'player_animations_done', 'db_connect_begin', 'db_connected',
                          'group_load_begin', 'group_load_done', 'db_setup_done', 'ready_published', 'main_loop_begin']
                for i, (row, phase) in enumerate(zip(rows, phases), 1):
                    assert row.startswith('ARMPORT_SERVER_STARTUP_V1 '), row
                    fields = dict(field.split('=', 1) for field in row.split()[1:])
                    assert fields == {'status': 'ok', 'map_id': '2', 'pid': '42', 'sequence': str(i),
                                      'phase': phase, 'elapsed_ms': f'{i * 100:.3f}', 'phase_ms': '100.000',
                                      'scope': 'main_entry_to_checkpoint'}, row
            if mode == 'startup_disabled':
                assert 'ARMPORT_SERVER_STARTUP_V1' not in result.stdout
            if mode == 'trusted_bins':
                rows = result.stdout.splitlines()
                assert len(rows) == 256, len(rows)
                assert rows[0] == 'ARMPORT_TRUSTED_BINS_V1 status=trusted ordinal=1 bin=bin/fxinfo.bin', rows[0]
                assert rows[1] == 'ARMPORT_TRUSTED_BINS_V1 status=trusted ordinal=2 bin=bin/minimap.bin', rows[1]
                assert rows[-1].endswith('ordinal=256 bin=bin/minimap.bin'), rows[-1]
            if mode == 'trusted_bins_disabled':
                assert 'ARMPORT_TRUSTED_BINS_V1' not in result.stdout
            if mode == 'spare_server':
                assert result.stdout.splitlines() == [
                    'ARMPORT_SPARE_V1 status=waiting pid=42 placeholder_map_id=71',
                    'ARMPORT_SPARE_V1 status=assigned pid=42 map_id=5001 base_map_id=50 instance_id=2 waited_ms=250',
                    'ARMPORT_SPARE_V1 status=waiting pid=42 placeholder_map_id=5001',
                    'ARMPORT_SPARE_V1 status=assigned pid=42 map_id=71 base_map_id=71 instance_id=0 waited_ms=250'], result.stdout
            if mode == 'spare_server_disabled':
                assert 'ARMPORT_SPARE_V1' not in result.stdout
            if mode == 'object_library':
                assert result.stdout.splitlines() == [
                    'ARMPORT_OBJECT_LIBRARY_BIN_V1 status=trusted bin=bin/defnames.bin'], result.stdout
            if mode in ('object_library_disabled', 'object_library_rebuild'):
                assert 'ARMPORT_OBJECT_LIBRARY_BIN_V1' not in result.stdout
            if mode == 'physx_cache':
                rows = [dict(field.split('=', 1) for field in row.split()[1:]) for row in result.stdout.splitlines()]
                assert all(row.startswith('ARMPORT_PHYSX_COOKED_V1 status=ok ') for row in result.stdout.splitlines())
                counts = [{key: row[key] for key in ('loaded', 'hits', 'misses', 'refused', 'added', 'bad_records',
                                                     'written')} for row in rows]
                assert counts == [
                    {'loaded': '0', 'hits': '0', 'misses': '4', 'refused': '0', 'added': '3', 'bad_records': '0',
                     'written': '1'},
                    {'loaded': '3', 'hits': '4', 'misses': '0', 'refused': '0', 'added': '0', 'bad_records': '0',
                     'written': '0'}], counts
            if mode == 'physx_cache_disabled':
                assert 'ARMPORT_PHYSX_COOKED_V1' not in result.stdout
            if mode == 'start_trees':
                assert result.stdout.splitlines() == [
                    'ARMPORT_START_TREES_V1 status=not_read_ahead trees=Defs,Menu',
                    'ARMPORT_MESSAGE_BIN_V1 status=trusted bin=server/bin/messages-en.bin',
                    'ARMPORT_START_TREES_V1 status=not_read_ahead trees=Defs,Menu'], result.stdout
            if mode == 'message_bins':
                assert result.stdout.splitlines() == [
                    'ARMPORT_MESSAGE_BIN_V1 status=trusted bin=server/bin/messages-en.bin',
                    'ARMPORT_MESSAGE_BIN_V1 status=trusted bin=bin/menuMessages-en.bin'], result.stdout
            if mode == 'map_load_profile':
                assert result.stdout.splitlines() == [
                    'ARMPORT_MAP_LOAD_V1 status=ok total_ms=510 other_ms=360 model_find_ms=45 model_finds=1 '
                    'ref_activate_ms=5 ref_activates=1 recalc_bounds_ms=20 bounds_files_ms=6 bounds_files=3 '
                    'scene_ms=5 spawn_areas_ms=69 unbalanced=0',
                    'ARMPORT_MAP_LOAD_V1 status=ok total_ms=40 other_ms=0 model_find_ms=0 model_finds=0 '
                    'ref_activate_ms=40 ref_activates=40 recalc_bounds_ms=0 bounds_files_ms=0 bounds_files=0 '
                    'scene_ms=0 spawn_areas_ms=0 unbalanced=0',
                    'ARMPORT_MAP_LOAD_V1 status=clock_error'], result.stdout
            if mode == 'map_load_profile_disabled':
                assert 'ARMPORT_MAP_LOAD_V1' not in result.stdout
            if mode in ('start_trees_disabled', 'message_bins_disabled', 'message_bins_fallback'):
                assert 'ARMPORT_START_TREES_V1' not in result.stdout and 'ARMPORT_MESSAGE_BIN_V1' not in result.stdout
            if mode == 'startup_clock':
                rows = result.stdout.splitlines()
                assert len(rows) == 3 and all('status=clock_error' in row for row in rows), rows
            if mode == 'slow':
                fields = dict(field.split('=', 1) for field in result.stdout.split()[1:])
                assert fields['ticks'] == '1' and fields['seconds'] == '7.500000'
                assert fields['max_tick_ms'] == '7000.000' and fields['max_loop_ms'] == '7500.000'
        print('server metrics extracted-source controls passed')
        return hashlib.sha256(control.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--original', type=Path,
                        help='Legacy negative invocation: expected assertion exits nonzero')
    parser.add_argument('--negative-control', type=Path,
                        help='Require the original-source missing-metrics assertion after positive checks')
    parser.add_argument('--report', type=Path,
                        help='Write passed host evidence bound to a prepared server source receipt')
    parser.add_argument('--upstream-root', type=Path,
                        default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    if args.original and (args.report or args.negative_control):
        parser.error('--original cannot be combined with --report or --negative-control')
    if args.report and not args.negative_control:
        parser.error('--report requires --negative-control')
    source = args.source.resolve()
    receipt = None
    if args.report:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        import prepare_server_metrics_source as staging
        receipt = staging.verify_prepared(source, args.upstream_root)
        assert args.negative_control.resolve() == (args.upstream_root / 'upstream/ouroboros').resolve()
    positive = run(source, args.original)
    if args.negative_control:
        negative = run(source, args.negative_control.resolve(), expect_control_failure=True)
    if args.report:
        document = {'format': 1, 'role': 'armport_server_metrics_source_checks',
                    'status': 'passed', 'variant': receipt['variant'],
                    'build_input_sha256': staging.digest(staging.canonical(receipt)),
                    'source_sha256': receipt['patched_sha256'],
                    'original_sha256': {name: staging.digest((args.negative_control / name).read_bytes())
                                        for name in (staging.SVR, staging.FILE, staging.TEXTPARSER,
                                                     staging.GROUPFILELIB, staging.NWWRAPPER,
                                                     staging.INITCOMMON, staging.MESSAGESTORE)
                                        + staging.LOAD_PROFILE_SOURCES},
                    'fixture_sha256': {'positive': positive, 'negative': negative},
                    'test_script_sha256': staging.digest(Path(__file__).read_bytes()),
                    'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
                    'execution_environment': 'posix_host_with_windows_clock_and_file_io_shims',
                    'positive_cases': test_cases(source), 'unpatched_control_failed': True,
                    'unpatched_control_failure': 'runtime_missing_metrics_startup_trusted_bin_spare_object_library_physx_cache_start_tree_and_map_load_assertions',
                    'shipping_binary_executed': False}
        staging.validate_test_report(document, receipt, args.upstream_root)
        args.report.write_text(json.dumps(document, indent=2) + '\n')


if __name__ == '__main__':
    main()
