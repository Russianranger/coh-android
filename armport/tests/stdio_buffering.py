#!/usr/bin/env python3
"""Prove the startup block calls CRT setvbuf, not the FileWrapper macro.

The host negative control models the wrapper's non-CRT/no-op branch. It
proves macro routing and live visibility, not the Windows CRT FILE layout.
The same source can be emitted for the app's Wine with the real wrapper.
"""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile
from power_preview_transition import function


def harness(source, original=False, windows=False):
    text = (source / 'Game/src/win/win_init.c').read_text()
    start = text.index('    {\n        // ArmPort: a GUI program')
    block = text[start:text.index('\n#endif', start)]
    if original:
        assert block.count('(setvbuf)(') == 2
        block = block.replace('(setvbuf)(', 'setvbuf(')
    header = (source / 'libs/UtilitiesLib/include/utilitieslib/utils/file.h').read_text()
    macro = re.search(r'^#define setvbuf\(.*$', header, re.M)[0]
    prefix = '''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int routed_to_wrapper;
'''
    if windows:
        prefix += '#include <windows.h>\n#include <io.h>\n'
        prefix += '''typedef enum { IO_CRT } IOMode;
typedef struct { void *fptr; IOMode iomode; } FileWrapper;
'''
        file_c = (source / 'libs/UtilitiesLib/src/utils/file.c').read_text()
        wrapper = function(file_c, 'int x_setvbuf(')
        prefix += wrapper.replace('{', '{\n    ++routed_to_wrapper;', 1) + '\n'
    else:
        prefix += '''#include <unistd.h>
#define _dup2 dup2
#define _fileno fileno
static int x_setvbuf(void *stream, char *buffer, int mode, size_t size)
{ ++routed_to_wrapper; return 0; } /* model the original non-CRT no-op branch */
'''
    return prefix + macro + '\nint main(int argc, char **argv)\n{\n' + block + '''
    printf("LIVE_STAGE_MARKER\\n");
    /* A separate descriptor observes bytes while stdout is still open. */
    FILE *readback = fopen(getenv("ARMPORT_STDIO_LOG"), "rb");
    char data[256] = {0};
    size_t n = readback ? fread(data, 1, sizeof(data)-1, readback) : 0;
    if (readback) fclose(readback);
    int visible = strstr(data, "LIVE_STAGE_MARKER") != NULL;
    int expected = atoi(argv[1]);
    fprintf(stderr, "live_visible=%d wrapper_calls=%d\\n", visible, routed_to_wrapper);
    return visible == expected && routed_to_wrapper == (expected ? 0 : 2) ? 0 : 7;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--emit-windows', type=Path)
    parser.add_argument('--original', action='store_true')
    args = parser.parse_args()
    if args.emit_windows:
        args.emit_windows.write_text(harness(args.source, args.original, windows=True))
        return
    import os
    with tempfile.TemporaryDirectory() as tmp:
        c, exe, log = Path(tmp)/'control.c', Path(tmp)/'control', Path(tmp)/'stdio.txt'
        for original in (True, False):
            c.write_text(harness(args.source, original))
            subprocess.run(['cc', '-std=gnu11', '-O1', str(c), '-o', str(exe)], check=True)
            log.unlink(missing_ok=True)
            subprocess.run([str(exe), str(int(not original))], check=True,
                env=dict(os.environ, ARMPORT_STDIO_LOG=str(log)))
            print(('original' if original else 'patched') + ': ' +
                  next(line for line in log.read_text().splitlines() if line.startswith('live_visible=')))


if __name__ == '__main__':
    main()
