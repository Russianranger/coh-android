"""Original shortcut initialization and concrete continuation storage for replay."""
import hashlib
import json
from pathlib import Path
import re
import subprocess


def extract(text, name):
    match = re.search(r'^(?:void|char\s*\*)\s*' + name + r'\s*\([^;{}]*\)\s*\{', text, re.M)
    assert match, name
    end = text.index('{', match.start()) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end] + '\n'


def prepare(root, work, replay, bounded=False, fallback=False):
    raw = replay.read_bytes()
    assert (len(raw), hashlib.sha256(raw).hexdigest()) in (
        (37795, '148a4a687d709d2f9ae298bf457e1b067e82b90e70928bd47712ba733fd533ba'),
        (37977, '74d85be47f23fe674e32178296aaa0f93f8830bb9ec4a08e166ee6f4f4e1a234'),
        (37977, '2b5645a49693dda2b4e64030ecba32c00ce840c9f5c8fb012316bbb95baad58a'))
    assert hashlib.sha256(raw[88:]).digest() == raw[56:88]
    paths = ['Common/cmdparse/cmdcommon.c', 'MapServer/src/cmdparse/cmdserver.c',
             'libs/UtilitiesLib/src/utils/cmdoldparse.c']
    source = {name: subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:upstream/ouroboros/' + name]).decode().replace('\r\n', '\n') for name in paths}
    names = {}
    for table in ('control_cmds', 'server_visible_cmds'):
        block = source[paths[0]].split('Cmd ' + table + '[]', 1)[1].split('\n};', 1)[0]
        names[table] = re.findall(r'\{\s*\d+\s*,\s*"([^"]+)"', block)
    assert len(names['control_cmds']) == 25 and len(names['server_visible_cmds']) == 10
    visible = ['time', 'timescale', 'timestepscale', 'pause', 'disablegurneys',
               'nodynamiccollisions', 'noentcollisions', 'pvpmap', 'svr_fog_dist', 'svr_fog_color']
    assert names['server_visible_cmds'] == visible
    functions = [extract(source[paths[2]], name) for name in ('cmdOldAddShortcut', 'cmdOldShortcutName')]
    functions.append(extract(source[paths[1]], 'cmdOldServerInitShortcuts'))
    code = '''#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef struct {char *name;} Cmd;
typedef struct {char name[32];int idx;} CmdShortcut;
static CmdShortcut storage[35],*shortcuts;static int shortcut_count,shortcut_max;
static void*add(CmdShortcut**p,size_t n,int*count,int*maximum,int amount){assert(p==&shortcuts&&n==sizeof(storage[0])&&amount==1&&*count<35);*p=storage;*maximum=35;return &storage[(*count)++];}
#define dynArrayAdd add
#define Strncpyt(d,s) do{assert(strlen(s)<sizeof(d));memcpy(d,s,strlen(s)+1);}while(0)
'''
    for table, rows in names.items():
        code += 'static Cmd ' + table + '[]={' + ','.join('{' + json.dumps(name) + '}' for name in rows) + ',{0}};\n'
    code += ''.join(functions)
    code += 'int main(void){cmdOldServerInitShortcuts();assert(shortcut_count==35&&!cmdOldShortcutName(0)&&!cmdOldShortcutName(36));for(int i=1;i<=35;i++)printf("%d %s\\n",i,cmdOldShortcutName(i));return 0;}\n'
    oracle = work / 'original-shortcuts.c'
    oracle.write_text(code)
    subprocess.run(['cc', '-std=c99', '-O0', '-Wall', '-Wextra', '-Werror', oracle, '-o', work / 'original-shortcuts'], check=True, capture_output=True)
    rows = [line.split(' ', 1) for line in subprocess.check_output([work / 'original-shortcuts'], text=True).splitlines()]
    assert [int(index) for index, _ in rows] == list(range(1, 36))
    assert [name for _, name in rows] == names['control_cmds'] + names['server_visible_cmds']

    # Execute the real product sizeof/offsetof calculation. Unused networking
    # functions are discarded, so this probe opens no transport or database.
    measurement = work / 'continuation-size.c'
    measurement.write_text('#include "coh_initial_local.c"\n#include <stdio.h>\nstatic CohInitialCapture owner;int main(void){printf("%zu\\n",coh_initial_capture_continuation_bytes(&owner));return 0;}\n')
    engine = root / 'native-android/engine/initial-capture'
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-DCOH_FRAME_CAPTURE_DIAGNOSTIC=1',
                    *(['-DCOH_BOUNDED_CONTINUATION_DIAGNOSTIC=1'] if bounded else []),
                    *(['-DCOH_INITIAL_ACK_FALLBACK_DIAGNOSTIC=1'] if fallback else []),
                    '-ffunction-sections', '-fdata-sections', '-I', engine, '-I', root / 'native-android/include',
                    measurement, engine / 'coh_initial_map.c', '-Wl,--gc-sections', '-o', work / 'continuation-size'], check=True, capture_output=True)
    charged = int(subprocess.check_output([work / 'continuation-size'], text=True))
    assert 0 < charged < 8388608
    header = work / 'actual-initial-source-fixture.h'
    header.write_text('static const CohRepShortcut actual_shortcuts[]={' + ','.join('{%s,%d}' % (index, visible.index(name) + 1 if name in visible else 0) for index, name in rows) + '};\n#define COH_ACTUAL_CONTINUATION_BYTES %du\n' % charged)
    inputs = {root / 'upstream/ouroboros' / name for name in paths if (root / 'upstream/ouroboros' / name).is_file()}
    inputs.update(engine / name for name in ('coh_initial_local.c', 'coh_initial_map.c', 'coh_initial_capture_private.h'))
    proof = {'scope': 'Whole original shortcut initializer/add/name functions on fresh bounded fixture storage; source table name projection. Explicit test-owned selection context, not live session authority.',
             'source_sha256_lf': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in source.items()},
             'original_function_sha256_lf': [hashlib.sha256(text.encode()).hexdigest() for text in functions],
             'source_commit': subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], text=True).strip(),
             'shortcut_count': len(rows), 'visible_ids': list(range(26, 36)), 'concrete_product_continuation_bytes': charged,
             'replay_sha256': hashlib.sha256(raw).hexdigest(), 'payload_sha256': hashlib.sha256(raw[88:]).hexdigest()}
    return proof, inputs
