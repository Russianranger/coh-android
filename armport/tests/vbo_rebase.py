"""Extracted VBO stream rebase control (patch 0112), with ASan/UBSan.

Runs the actual rebase block of modelSetupVertexObject from the prepared
source on a fake VBO whose streams live above 4 GB: the copy path
(VBOS_DONTUSE, used by shadow volumes and capes) must keep every stream at the
same byte offset from the copied vertices, and the VBO path must turn each
stream into its exact buffer offset. --original applies the int arithmetic
the patch replaced and must fail.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--original', action='store_true')
args = parser.parse_args()
text = (args.source / 'Game/src/render/model_cache.c').read_text()
start = text.index('    delta = (intptr_t)vbo->verts;')
end = text.index('    if (!vbo->verts)\n        rdrQueueSend();', start)
block = text[start:end]
if args.original:
    block = block.replace('(intptr_t)', '(int)').replace('(char *)', '(int)')
fixture = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
typedef int TexID;
typedef struct VBO { void *verts, *tris, *norms, *sts, *sts2, *sts3, *tangents, *weights, *matidxs;
    TexID *tex_ids; int vert_buffer_bytes, tri_count, tex_count; } VBO;
enum { VBOS_USE, VBOS_DONTUSE };
static struct { int use_vbos; } rdr_caps = {1};
static void *high_malloc(size_t bytes) {
    static char *next;
    if (!next) {
        next = mmap((void *)0x7f1234500000ull, 1 << 24, PROT_READ | PROT_WRITE,
                    MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
        assert(next != MAP_FAILED && (uintptr_t)next > 0xffffffffull);
    }
    void *result = next; next += (bytes + 63) & ~(size_t)63; return result;
}
static void rebase(VBO *vbo, int useVbos) {
    intptr_t delta;
'''
main = r'''
}
static int run(int useVbos) {
    static char source[4096];
    char *base = high_malloc(4096);
    memcpy(base, source, sizeof(source));
    VBO vbo = {0};
    size_t offsets[] = {96, 192, 288, 384, 480, 576, 672};
    void **streams[] = {&vbo.norms, &vbo.sts, &vbo.sts2, &vbo.sts3, &vbo.tangents, &vbo.weights, &vbo.matidxs};
    vbo.verts = base; vbo.vert_buffer_bytes = 4096; vbo.tri_count = 1; vbo.tex_count = 1;
    static int tris[3]; static TexID tex[1]; vbo.tris = tris; vbo.tex_ids = tex;
    for (int i = 0; i < 7; i++) *streams[i] = base + offsets[i];
    rebase(&vbo, useVbos);
    int ok = 1;
    for (int i = 0; i < 7; i++) {
        uintptr_t expected = useVbos == VBOS_DONTUSE ? (uintptr_t)vbo.verts + offsets[i] : offsets[i];
        ok &= (uintptr_t)*streams[i] == expected;
    }
    if (useVbos == VBOS_DONTUSE) { free(vbo.tris); free(vbo.verts); free(vbo.tex_ids); }
    return ok;
}
int main(void) {
    int copy = run(VBOS_DONTUSE), buffer = run(VBOS_USE);
    printf("VBO rebase: copy_path=%d vbo_offsets=%d\n", copy, buffer);
    return copy && buffer ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / 'rebase.c'
    exe = Path(temporary) / 'rebase'
    source.write_text(fixture + block + main)
    subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-w', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', str(source), '-o', str(exe)], check=True)
    raise SystemExit(subprocess.run([str(exe)]).returncode)
