"""Message-store variable-definition indices are pointer-sized (patch 0117).

TextMessage.variableDefNameIndices is an Array whose elements are pushed as
(void*)(intptr_t)index. The 64-bit client read that storage as int* when it
rebuilt a message's parameter list, and the shared-heap compaction copied
sizeof(int) per element. With the PlayerPowerHit definition
{EnemyName %s},{powerName %r},{ToHit %.2f},{roll %.2f} that produced the Thor
error "Bad parameter for: PlayerPowerHit:powerName".

Runs, on this 64-bit host, the reconstruction loop of msvaPrintfInternalEx and
the index copy of copyTextMessageStructsToShared, both extracted from the given
source. --original takes both from the unpatched upstream file and must fail.
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
text = (root / 'libs/UtilitiesLib/src/language/MessageStore.c').read_text()
if not args.original:
    assert 'variableIndex = (int)(intptr_t)textMessage->variableDefNameIndices->storage[uiIndex]' in text, 'patch 0117 is missing'

loop_start = text.index('        for (uiIndex=0; uiIndex < uiNumVariableDefs; ++uiIndex)')
loop_end = text.index('    msGetTypeDefPointers(messageTypeDef, arg);', loop_start)
loop = text[loop_start:loop_end]
loop = loop[:loop.rindex('}')]           # drop the enclosing if-block's brace
copy_start = text.index('            Array* indices = pNewTm->variableDefNameIndices = (Array*)pCurrentAddress;')
copy_end = text.index('        // Fix the messageId pointer', copy_start)
copy = text[copy_start:copy_end]
copy = copy[:copy.rindex('}')]

fixture = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <alloca.h>
#define _alloca alloca
typedef unsigned int U32; typedef unsigned char U8;
typedef struct Array { int size, maxSize; void **storage; } Array;
typedef struct { const char *variableName, *variableType; U8 variableTypeChar; void *variablePointer; } NamedVariableDef;
typedef struct { Array *variableDefNameIndices; } TextMessage;
typedef struct { void *variableStringTable; } MessageStore;
/* Variable string table: name at an even index, its type at index + 1. */
static const char *strings[] = {"PetName", "%s", "EnemyName", "%s", "powerName", "%r", "ToHit", "%.2f", "roll", "%.2f"};
static const char *strTableGetConstString(void *table, int index) {
    (void)table; return index >= 0 && index < 10 ? strings[index] : "<out of range>"; }
static void initVariableNameAndType(NamedVariableDef *def, const char *name, const char *type) {
    def->variableName = name; def->variableType = type; def->variableTypeChar = 0; }

static int reconstruct(const TextMessage *textMessage, NamedVariableDef *out) {
    MessageStore storeValue = {0}, *store = &storeValue;
    Array *messageTypeDef;
    U32 uiNumVariableDefs = textMessage->variableDefNameIndices->size;
    U32 uiIndex;
    messageTypeDef = malloc(sizeof(Array));
    messageTypeDef->size = messageTypeDef->maxSize = uiNumVariableDefs;
    messageTypeDef->storage = malloc(sizeof(*messageTypeDef->storage) * uiNumVariableDefs);
''' + loop + r'''
    for (uiIndex = 0; uiIndex < uiNumVariableDefs; ++uiIndex) out[uiIndex] = *(NamedVariableDef *)messageTypeDef->storage[uiIndex];  /* copy: the defs are _alloca'd */
    return uiNumVariableDefs;
}
static void compact(const TextMessage *pOldTMValue, TextMessage *pNewTmValue, char *pCurrentAddress) {
    const TextMessage *pOldTM = pOldTMValue; TextMessage *pNewTm = pNewTmValue;
    U32 uiNumNamedVariableDefIndices = pOldTM->variableDefNameIndices->size;
''' + copy + r'''
}
static int check(const char *label, const TextMessage *tm) {
    static const char *names[] = {"EnemyName", "powerName", "ToHit", "roll"};
    static const char *types[] = {"%s", "%r", "%.2f", "%.2f"};
    NamedVariableDef defs[4]; int ok = reconstruct(tm, defs) == 4;
    for (int i = 0; i < 4 && ok; i++) ok = !strcmp(defs[i].variableName, names[i]) && !strcmp(defs[i].variableType, types[i]);
    printf("%s: %s %s %s %s\n", label, defs[0].variableName, defs[1].variableName, defs[2].variableName, defs[3].variableName);
    return ok;
}
int main(void) {
    /* PlayerPowerHit as built by addTextMessageDefNameIndex. */
    void *elements[4] = {(void *)(intptr_t)2, (void *)(intptr_t)4, (void *)(intptr_t)6, (void *)(intptr_t)8};
    Array built = {4, 4, elements};
    TextMessage message = {&built}, shared;
    char *heap = calloc(1, 4096);
    int loaded = check("loaded", &message);
    compact(&message, &shared, heap);
    int compacted = check("shared heap", &shared);
    return loaded && compacted ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / 'indices.c'
    exe = Path(temporary) / 'indices'
    source.write_text(fixture)
    subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-w', '-fsanitize=address,undefined',
                    str(source), '-o', str(exe)], check=True)
    result = subprocess.run([str(exe)], capture_output=True, text=True,
                            env={'ASAN_OPTIONS': 'detect_leaks=0'})
    print(" | ".join(result.stdout.split("\n")).strip(" |")); print(result.stderr[-1500:]) if result.returncode else None
    raise SystemExit(result.returncode)
