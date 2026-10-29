"""Ragdoll packets without PhysX on ARM64 (patch 0118), extracted from the given source.

ARM64 compiles PhysX out; armport/standins/physx/ragdoll_standin.c makes
nwCreateRagdollNoPhysics return NULL. Upstream entGetRagdoll then wrote the
first pose through the NULL ragdoll (Thor fault writing 0x38 in mat3ToQuat
after defeating an enemy: qCurrentRot is at offset 0x34 on 64-bit).

1. The entity-update dispatch region of entrecv.c, compiled with __aarch64__
   defined, must read the ragdoll bits through entGetRagdollIgnore and leave
   the packet positioned exactly after them (stream stays in sync).
2. Both "create a ragdoll" blocks (live and demo playback) run with the NULL
   stand-in under ASan and must not dereference it.
--original takes the code from the unpatched upstream file and must fail.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--original', type=Path, help='unpatched upstream/ouroboros (negative control)')
args = parser.parse_args()
root = args.original or args.source
text = (root / 'Game/src/entity/entrecv.c').read_text()
standin = (Path(__file__).resolve().parents[1] / 'standins/physx/ragdoll_standin.c').read_text()
assert 'return 0;' in standin.split('nwCreateRagdollNoPhysics', 1)[1].split('}', 1)[0], 'stand-in no longer returns NULL'

dispatch_start = text.index('    START_BIT_COUNT(pak, "entGetRagdoll");')
dispatch_end = text.index('    STOP_BIT_COUNT(pak);', dispatch_start) + len('    STOP_BIT_COUNT(pak);')
dispatch = text[dispatch_start:dispatch_end]
ignore_start = text.index('static int entGetRagdollIgnore(Packet *pak,Entity *e)')
ignore = text[ignore_start:text.index('\n}\n', ignore_start) + 3]
marker = '        if (!e->ragdoll)\n        {\n            Mat4 mWorldSpaceMat;'
blocks = []
position = 0
while True:
    start = text.find(marker, position)
    if start < 0:
        break
    end = text.index('\n        }\n', text.index('bCreatedRagdoll = true;', start)) + len('\n        }\n')
    blocks.append(text[start:end])
    position = end
assert len(blocks) == 2, 'expected the live and demo-playback creation blocks, found %d' % len(blocks)

fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
typedef float F32; typedef float Vec3[3]; typedef Vec3 Mat4[4]; typedef F32 Quat[4]; typedef unsigned char U8;
#define NUM_BITS_PER_RAGDOLL_QUAT_ELEM 10
#define RAGDOLL 1
typedef struct Packet { int position, bits; } Packet;
typedef struct GfxNode { struct GfxNode *child; Mat4 mat; } GfxNode;
typedef struct SeqInst { GfxNode *gfx_root; } SeqInst;
/* 64-bit layout of ragdoll.h: qCurrentRot at offset 0x34. */
typedef struct Ragdoll { struct Ragdoll *child, *next, *parent; int boneId; void *pActor, *pJointToParent;
                         U8 numBones; Quat qCurrentRot; } Ragdoll;
typedef struct Entity { SeqInst *seq; Ragdoll *ragdoll; Mat4 mat; } Entity;
#define ENTMAT(e) ((e)->mat)
#define START_BIT_COUNT(pak, name)
#define STOP_BIT_COUNT(pak)
static int pktGetBits(Packet *pak, int bits) { pak->position += bits; return 1; }
static int pktGetIfSetBits(Packet *pak, int bits) { pak->position += 1 + bits; return 3; }
static int full_reader_used;
static int entGetRagdoll(Packet *pak, Entity *e) { (void)pak; (void)e; full_reader_used = 1; return 0; }
static void mulMat4(Mat4 a, Mat4 b, Mat4 out) { (void)a; (void)b; memset(out, 0, sizeof(Mat4)); }
static void mat3ToQuat(Mat4 m, Quat q) { (void)m; q[0] = q[1] = q[2] = 0; q[3] = 1; }
static void quatNormalize(Quat q) { (void)q; }
Ragdoll *nwCreateRagdollNoPhysics(Entity *e);
#define __aarch64__ 1   /* the ARM64 client build */
''' + ignore + r'''
static void dispatch_update(Packet *pak, Entity *e) {
''' + dispatch + r'''
}
''' + ''.join(r'''
static void create_%d(Entity *e) {
    int bCreatedRagdoll = 0;
''' % i + block + r'''
    (void)bCreatedRagdoll;
}
''' for i, block in enumerate(blocks)) + r'''
int main(void) {
    GfxNode child = {0}, gfx_root = {&child}; SeqInst seq = {&gfx_root}; Entity e = {&seq, NULL};
    Packet pak = {0};
    dispatch_update(&pak, &e);
    int expected = 1 + 5 + 3 * 3 * NUM_BITS_PER_RAGDOLL_QUAT_ELEM;   /* num_bones flag+bits, then 9 elements */
    printf("dispatch: full_reader=%d bits_consumed=%d expected=%d\n", full_reader_used, pak.position, expected);
    int dispatched = !full_reader_used && pak.position == expected;
    create_0(&e); create_1(&e);
    printf("creation with the NULL stand-in: survived, ragdoll=%p\n", (void *)e.ragdoll);
    return dispatched ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / 'ragdoll.c'
    exe = Path(temporary) / 'ragdoll'
    source.write_text(fixture)
    (Path(temporary) / 'standin.c').write_text(standin)
    subprocess.run(['cc', '-std=gnu11', '-O0', '-g', '-w', '-fsanitize=address,undefined',
                    str(source), str(Path(temporary) / 'standin.c'), '-o', str(exe)], check=True)
    result = subprocess.run([str(exe)], capture_output=True, text=True, env={'ASAN_OPTIONS': 'detect_leaks=0'})
    print(' | '.join(line for line in result.stdout.splitlines()))
    if result.returncode:
        crash = [line for line in result.stderr.splitlines() if 'ERROR: AddressSanitizer' in line or 'runtime error' in line]
        print('failed: ' + (crash[0].strip() if crash else 'exit %d' % result.returncode))
    raise SystemExit(result.returncode)
