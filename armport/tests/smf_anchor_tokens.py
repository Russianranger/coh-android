"""Extracted SMF anchor index control (patch 0110), with ASan/UBSan.

Compiles the actual smf_AnchorToken/smf_AnchorFromToken from the prepared
source over a minimal pointer-earray shim, then checks: a retained token keeps
resolving to its own anchor however many later anchors are pushed (no
recycling), 64-bit pointers above 4 GB round-trip unchanged, 0 and
out-of-range tokens resolve to NULL, and a stack reset invalidates old tokens.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

from power_preview_transition import function

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
text = (args.source / 'Game/src/formatter/smf_util.c').read_text()
code = '\n'.join(function(text, signature) for signature in (
    'int smf_AnchorToken(TextAttribs *pattr, void *pv)',
    'void *smf_AnchorFromToken(TextAttribs *pattr, int token)'))
fixture = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct { int count, size; void *items[]; } Shim;
#define SHIM(h) ((Shim *)((char *)(h) - offsetof(Shim, items)))
static int eaSizeShim(void ***h) { return *h ? SHIM(*h)->count : 0; }
static void eaPushShim(void ***h, void *p) {
    Shim *s = *h ? SHIM(*h) : NULL;
    if (!s || s->count == s->size) {
        int size = s ? s->size * 2 : 4;
        s = realloc(s, sizeof(Shim) + size * sizeof(void *));
        if (!*h) s->count = 0;
        s->size = size;
    }
    s->items[s->count++] = p;
    *h = s->items;
}
static void eaSetSizeShim(void ***h, int n) { if (*h) SHIM(*h)->count = n; }
static void eaDestroyShim(void ***h) { if (*h) free(SHIM(*h)); *h = NULL; }
#define eaSize(h) eaSizeShim((void ***)(h))
#define eaPush(h, p) eaPushShim((void ***)(h), (p))
typedef struct TextAttribs { int *piAnchor; void **ppvAnchors; } TextAttribs;
'''
main = r'''
int main(void) {
    TextAttribs attrs = {0};
    int anchor_object = 7, n;
    void *high = (void *)(uintptr_t)0xFFFFA3E25370ull;   /* Thor fault's upper bits */
    assert(smf_AnchorToken(&attrs, NULL) == 0);
    int first = smf_AnchorToken(&attrs, &anchor_object);
    int far = smf_AnchorToken(&attrs, high);
    for (n = 0; n < 200000; n++)
        assert(smf_AnchorToken(&attrs, (char *)high + 16 * (n + 1)) == far + 1 + n);
    assert(smf_AnchorFromToken(&attrs, first) == &anchor_object);
    assert(smf_AnchorFromToken(&attrs, far) == high);
    assert(smf_AnchorFromToken(&attrs, 0) == NULL && smf_AnchorFromToken(&attrs, -1) == NULL);
    assert(smf_AnchorFromToken(&attrs, eaSize(&attrs.ppvAnchors) + 1) == NULL);
    assert(smf_AnchorFromToken(NULL, first) == NULL && smf_AnchorToken(NULL, high) == 0);
    eaSetSizeShim(&attrs.ppvAnchors, 0);                  /* smf_InitTextAttribs reset */
    assert(smf_AnchorFromToken(&attrs, first) == NULL && smf_AnchorFromToken(&attrs, far) == NULL);
    assert(smf_AnchorToken(&attrs, high) == 1 && smf_AnchorFromToken(&attrs, 1) == high);
    eaDestroyShim(&attrs.ppvAnchors);
    printf("SMF anchor indices: %d tokens without recycling; high pointer round-trip; NULL/range/reset cases pass with ASan/UBSan\n", n + 2);
    return 0;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / 'anchors.c'
    exe = Path(temporary) / 'anchors'
    source.write_text(fixture + code + main)
    subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', str(source), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
