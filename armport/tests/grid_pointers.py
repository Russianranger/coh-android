#!/usr/bin/env python3
"""Exercise original grid insertion, removal and both node lookup paths.

Only includes, memory allocation and unrelated collision geometry are adapted.
High addresses are opaque tokens; the test never dereferences them. The old
source must lose pointer identity, while patched code must preserve it.
"""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def harness(source):
    root = source / 'Common/gridcoll'
    strip = lambda s: re.sub(r'^#include[^\n]*\n', '', s, flags=re.M)
    collision = (root / 'gridcoll.c').read_text()
    start = collision.index('static int checkGridCellObjs(')
    end = collision.index('\nDefTracker *last_coll_obj', start)
    collision = collision[start:end]
    before = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
typedef uint32_t U32;
typedef uint8_t U8;
typedef float F32;
typedef float Vec3[3];
typedef void GfxNode;
typedef struct Pool { size_t size; } *MemoryPool;
static MemoryPool createMemoryPool(void) { return calloc(1,sizeof(struct Pool)); }
static void initMemoryPool(MemoryPool p,size_t n,int unused) { p->size=n; }
static void *mpAlloc(MemoryPool p) { return calloc(1,p->size); }
static void mpFree(MemoryPool p,void *v) { free(v); }
static void destroyMemoryPool(MemoryPool p) { free(p); }
#define MP_DEFINE(T)
#define MP_CREATE(T,n)
#define MP_ALLOC(T) ((T*)calloc(1,sizeof(T)))
#define MP_FREE(T,p) free(p)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define setVec3(v,a,b,c) ((v)[0]=(a),(v)[1]=(b),(v)[2]=(c))
#define copyVec3(a,b) memcpy(b,a,sizeof(Vec3))
#define subVec3(a,b,c) do { for(int vi=0;vi<3;vi++) (c)[vi]=(a)[vi]-(b)[vi]; } while(0)
#define addVec3(a,b,c) do { for(int vi=0;vi<3;vi++) (c)[vi]=(a)[vi]+(b)[vi]; } while(0)
#define qtruncVec3(a,b) do { for(int vi=0;vi<3;vi++) (b)[vi]=(int)(a)[vi]; } while(0)
'''
    middle = r'''
typedef struct Def { int volume_trigger,has_volume,is_tray; } Def;
typedef struct DefTracker { int coll_time; Def *def; } DefTracker;
typedef int GridEntryCallback(void *);
typedef struct CollInfo {
    Grid *grid; int flags; struct { int backside; } tri_state;
    int (*node_callback)(DefTracker*,int);
} CollInfo;
#define COLL_NOTTRACKERS 1
#define COLL_NODECALLBACK 2
#define COLL_FINDINSIDE 4
static void **curr_obj_list;
static int curr_obj_count,curr_obj_max;
static int sphereNearLine(DefTracker *t,CollInfo *c) { abort(); }
static void dynArrayAddp(void ***p,int *n,int *m,void *t) { abort(); }
static uintptr_t unpacked;
static GridIdxList *active_indices;
static void groupUnpackGrid(Grid *g,DefTracker *t) {
    unpacked=(uintptr_t)t;
    gridClearAndFreeIdxList(g,&active_indices);
}
'''
    # Rename only the second file's private helper to keep both original bodies.
    find = strip((root / 'gridfind.c').read_text()).replace('gridSplitPlanes', 'findSplitPlanes')
    after = r'''
static int roundtrip(uintptr_t token,int tagged,int collision) {
    Grid g={0}; Vec3 min={-1,-1,-1},max={1,1,1},point={0,0,0};
    void *found[8]={0}; int count=0,ok=1; unpacked=0;
    assert(gridAdd(&g,(void*)token,min,max,tagged,&active_indices));
    if(tagged && collision) {
        /* The inserted entry's actual cell, found through its removal index. */
        GridEnts e={0}; GridCell cell={0}; CollInfo coll={0};
        e.entries[0]=*active_indices->entries[0]; cell.entries=&e; coll.grid=&g;
        /* Callback clears the original index; also clear this view to terminate. */
        active_indices->entries[0]=&e.entries[0];
        checkGridCellObjs(&cell,&coll); ok=unpacked==token;
    } else {
        count=gridFindObjectsInSphere(&g,found,8,point,4);
        ok=tagged ? unpacked==token : count==1 && (uintptr_t)found[0]==token;
    }
    if(active_indices)gridClearAndFreeIdxList(&g,&active_indices);
    assert(active_indices==NULL);
    /* Cleared grid entries must no longer be returned. */
    if(!collision)assert(gridFindObjectsInSphere(&g,found,8,point,4)==0);
    gridFreeAll(&g); return ok;
}
static int distinct_high_tokens(void) {
    Grid g={0}; Vec3 min={-1,-1,-1},max={1,1,1},point={0,0,0};
    void *found[8]={0}; GridIdxList *a=0,*b=0;
    uintptr_t one=(uintptr_t)UINT64_C(0x200000008),two=(uintptr_t)UINT64_C(0x400000008);
    assert(gridAdd(&g,(void*)one,min,max,0,&a));
    assert(gridAdd(&g,(void*)two,min,max,0,&b));
    int n=gridFindObjectsInSphere(&g,found,8,point,4);
    int ok=n==2 && ((found[0]==(void*)one && found[1]==(void*)two) ||
                   (found[1]==(void*)one && found[0]==(void*)two));
    gridClearAndFreeIdxList(&g,&a);gridClearAndFreeIdxList(&g,&b);gridFreeAll(&g);
    return ok;
}
int main(int argc,char **argv) {
    assert(argc==2); assert(sizeof(uintptr_t)==8);
    int expected=atoi(argv[1]);
    /* Both retain the low 32 bits seen at the Atlas fault. */
    uintptr_t high=(uintptr_t)UINT64_C(0x0000000143dde180);
    int stored=roundtrip(high,0,0),find=roundtrip(high,1,0),coll=roundtrip(high,1,1);
    int distinct=distinct_high_tokens();
    printf("grid pointer identity: storage=%d sphere=%d collision=%d distinct=%d expected=%d\n",
           stored,find,coll,distinct,expected);
    return stored==expected && find==expected && coll==expected && distinct==expected ? 0:1;
}
'''
    return before + strip((root / 'grid.h').read_text()) + middle + strip((root / 'grid.c').read_text()) + find + collision + after


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--expect-full-width', type=int, choices=[0, 1], required=True)
    p.add_argument('--emit-windows', type=Path)
    args = p.parse_args()
    code = harness(args.source)
    if args.emit_windows:
        args.emit_windows.write_text(code)
    with tempfile.TemporaryDirectory() as folder:
        c = Path(folder) / 'grid.c'
        exe = Path(folder) / 'grid'
        c.write_text(code)
        subprocess.run(['cc', '-std=gnu11', '-O2', str(c), '-lm', '-o', str(exe)], check=True)
        subprocess.run([str(exe), str(args.expect_full_width)], check=True, timeout=15)


if __name__ == '__main__':
    main()
