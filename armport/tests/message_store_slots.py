"""Message-store variadic slot layout (patch 0115), extracted from the prepared source.

Runs the actual msGetTypeDefPointers from MessageStore.c against the Windows
64-bit variadic layout (ARM64 and x64: va_list is a char *, and every
argument, int, pointer or double, occupies one 8-byte slot). The fixture is
localizeCombatMessage's type, "{PlayerDest, %s}, {PowerName, %r},
{Damage, %g}, {PlayerSource, %s}", with Damage = 1.75: the Thor combat fault
read 3FFC000000000000 (1.75 as a double) as the PlayerSource string.
--original removes the patch's _WIN64 block and must fail.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--original', action='store_true')
args = parser.parse_args()
text = (args.source / 'libs/UtilitiesLib/src/language/MessageStore.c').read_text()
start = text.index('static void msGetTypeDefPointers(Array* messageTypeDef, va_list arg)')
end = text.index('static char getFormatChar(', start)
function = text[start:end]
if args.original:
    function, count = re.subn(r'#if defined\(_WIN64\).*?#endif\n', '', function, flags=re.S)
    assert count == 1, 'patch block not found'
else:
    assert '#if defined(_WIN64)' in function, 'patch 0115 is missing'

fixture = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define _WIN64 1
typedef unsigned char U8;
typedef char *win64_va_list;           /* Windows ARM64/x64 va_list */
#define va_list win64_va_list
typedef struct Array { int size; void **storage; } Array;
typedef struct { const char *variableName; const char *variableType; U8 variableTypeChar;
                 void *variablePointer; } NamedVariableDef;
'''
main = r'''
int main(void) {
    /* One 8-byte slot per argument, as the Windows 64-bit callee sees them. */
    static const char dest[] = "Hellion", power[] = "P1703759751", source[] = "THORHERO";
    double damage = 1.75;
    unsigned char slots[4 * 8];
    const char *p = dest; memcpy(slots + 0, &p, 8);
    p = power; memcpy(slots + 8, &p, 8);
    memcpy(slots + 16, &damage, 8);
    p = source; memcpy(slots + 24, &p, 8);
    NamedVariableDef defs[4] = {{"PlayerDest", "%s", 's'}, {"PowerName", "%r", 'r'},
                                {"Damage", "%g", 'g'}, {"PlayerSource", "%s", 's'}};
    void *storage[4] = {&defs[0], &defs[1], &defs[2], &defs[3]};
    Array types = {4, storage};
    msGetTypeDefPointers(&types, (va_list)slots);
    const char *s0 = *(const char **)defs[0].variablePointer, *s1 = *(const char **)defs[1].variablePointer,
               *s3 = *(const char **)defs[3].variablePointer;
    double d2; memcpy(&d2, defs[2].variablePointer, 8);
    int ok = s0 == dest && s1 == power && d2 == 1.75 && s3 == source;
    printf("message slots: offsets %d %d %d %d, PowerName %s, PlayerSource %s\n",
           (int)((unsigned char *)defs[0].variablePointer - slots), (int)((unsigned char *)defs[1].variablePointer - slots),
           (int)((unsigned char *)defs[2].variablePointer - slots), (int)((unsigned char *)defs[3].variablePointer - slots),
           s1 == power ? "ok" : "wrong", s3 == source ? "ok" : "wrong (would dereference another slot)");
    return ok ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / 'slots.c'
    exe = Path(temporary) / 'slots'
    source.write_text(fixture + function + main)
    subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-w', '-fsanitize=address,undefined',
                    str(source), '-o', str(exe)], check=True)
    result = subprocess.run([str(exe)], capture_output=True, text=True)
    print(result.stdout.strip())
    raise SystemExit(result.returncode)
