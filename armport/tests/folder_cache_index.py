"""Saved folder-cache index (patch 0122), with the actual prepared code.

Extracts FolderNodeAdd (FolderCacheNode.c) and the scan, index and
FolderCacheAddFolder code (FolderCache.c) from --source, compiles them with
folder_cache_index_fixture.c (POSIX stand-ins for the Win32 calls) and checks:
the index is written after a full scan and rebuilds the identical tree (names,
sizes, timestamps, flags) while listing only the root and the live root bin/;
a changed identity, skip list, sampled size or time, checksum, length or an
unsafe record name each fall back to the full scan and rewrite the index.
--original (unpatched upstream/ouroboros) has no index code and must fail.
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--original', type=Path, help='unpatched upstream/ouroboros (negative control)')
args = parser.parse_args()
root = args.original or args.source
utils = root / 'libs/UtilitiesLib/src/utils'
cache = (utils / 'FolderCache.c').read_text()
nodes = (utils / 'FolderCacheNode.c').read_text()


def function(text, signature):
    start = text.index(signature)
    depth, i = 0, text.index('{', start)
    while True:
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
        i += 1


marker = '// ArmPort: saved folder-cache index (patch 0122)'
if marker not in cache:
    sys.exit('FAIL: no saved folder-cache index in ' + str(utils / 'FolderCache.c'))
skip = cache.index('// ArmPort: ARMPORT_FOLDER_CACHE_SKIP')
extracted = '\n'.join([
    function(nodes, 'FolderNode *FolderNodeAdd(FolderNode **head'),
    cache[skip:cache.index('static void FolderCacheAddFolderToNode(')],
    function(cache, 'static void FolderCacheAddFolderToNode('),
    function(cache, 'static int armportFixedData(void)'),
    cache[cache.index(marker):cache.index('void FolderCacheAddFolder(FolderCache *fc')],
    function(cache, 'void FolderCacheAddFolder(FolderCache *fc')]) + '\n'

failures, checks = [], []


def check(actual, expected, label):
    checks.append(label)
    print(('ok   ' if actual == expected else 'FAIL ') + label + ('' if actual == expected
          else ': got %r, want %r' % (actual, expected)))
    if actual != expected:
        failures.append(label)


with tempfile.TemporaryDirectory(prefix='armport-fci-') as temporary:
    work = Path(temporary)
    (work / 'extracted.inc').write_text(extracted)
    harness = work / 'harness'
    subprocess.run(['cc', '-O1', '-Wall', '-Werror', '-Wno-unused-function', '-Wno-unused-variable',
                    '-Wno-misleading-indentation', '-I', str(work), '-o', str(harness),
                    str(Path(__file__).with_name('folder_cache_index_fixture.c'))], check=True)
    tree = work / 'tree'
    data = tree / 'data'
    for name in ('bin', 'maps/bin', 'maps/City', 'texts', 'scripts.loc', 'Defs/deep/er'):
        (data / name).mkdir(parents=True)
    for i in (1, 2, 3):
        (data / ('maps/City/geo%d.txt' % i)).write_bytes(b'\0' * (7 * i))
    for name, text in (('bin/a.bin', 'a'), ('maps/bin/n.bin', 'nested'), ('texts/T.ms', 't'),
                       ('scripts.loc/x.storyarc', 's'), ('Defs/deep/er/z.def', 'd'), ('texts/ro.txt', 'ro')):
        (data / name).write_text(text + '\n')
    os.chmod(data / 'texts/ro.txt', 0o444)
    os.utime(data / 'maps/City/geo1.txt', (1577836800, 1577836800))
    index = tree / 'index.bin'
    base_env = dict(os.environ, ARMPORT_LOOSE_DATA='1', ARMPORT_FOLDER_CACHE_SKIP='scripts.loc')
    for key in ('ARMPORT_FOLDER_CACHE_INDEX', 'ARMPORT_FOLDER_CACHE_ID'):
        base_env.pop(key, None)
    index_env = dict(base_env, ARMPORT_FOLDER_CACHE_INDEX=str(index), ARMPORT_FOLDER_CACHE_ID='abc123')

    def run(name, env):
        output = subprocess.run([str(harness), name], cwd=tree, env=env, capture_output=True, text=True,
                                check=True).stdout
        lines = [line.split('ARMPORT_FOLDER_CACHE_V1 ', 1)[-1] for line in output.splitlines()
                 if 'phase=index' in line or line.startswith('RESULT')]
        cleaned = [' '.join(part for part in line.split() if not part.startswith(('seconds=', 'bytes=')))
                   for line in lines]
        return cleaned, (tree / name).read_text()

    full = ['RESULT files=8 folders=8 skipped=1 listings=9']
    rescan = lambda reason, result='files=9 folders=8 skipped=1 listings=9': [
        'phase=index result=miss reason=' + reason, 'phase=index result=written', 'RESULT ' + result]
    plain, plain_tree = run('plain.txt', base_env)
    check(plain, full, 'no index variables: the original full scan only')
    first, first_tree = run('first.txt', index_env)
    check(first, ['phase=index result=miss reason=absent', 'phase=index result=written'] + full,
          'no index yet: full scan, then the index is written')
    check(first_tree, plain_tree, 'scan with the index enabled builds the original tree')
    hit, hit_tree = run('hit.txt', index_env)
    check(hit, ['phase=index result=hit reason=match', 'RESULT files=8 folders=8 skipped=1 listings=2'],
          'same identity: nodes from the index, only the root and bin/ listed')
    check(hit_tree, plain_tree, 'the index rebuilds the identical tree (names, sizes, times, flags)')
    (data / 'bin/b.bin').write_text('new\n')
    live, live_tree = run('live.txt', index_env)
    check(live[-1], 'RESULT files=9 folders=8 skipped=1 listings=2', 'the root bin/ (overlay) is scanned live')
    check(('/bin/b.bin 0' in live_tree, '/maps/bin/n.bin 0' in live_tree), (True, True),
          'a new overlay bin is visible; a nested bin/ comes from the index')
    check(run('id.txt', dict(index_env, ARMPORT_FOLDER_CACHE_ID='other'))[0], rescan('header'),
          'changed identity: full scan')
    check(run('skip.txt', dict(index_env, ARMPORT_FOLDER_CACHE_ID='other', ARMPORT_FOLDER_CACHE_SKIP=''))[0],
          rescan('header', 'files=10 folders=9 skipped=0 listings=10'), 'changed skip list: full scan')
    check(run('back.txt', index_env)[0], rescan('header'), 'the index belongs to the last identity')
    (data / 'maps/City/geo2.txt').write_bytes(b'\0' * 99)
    stale, stale_tree = run('stale.txt', index_env)
    check((stale, '/maps/City/geo2.txt 0 99 ' in stale_tree), (rescan('stale'), True),
          'a sampled file changed size: full scan with the new size')
    os.utime(data / 'maps/City/geo1.txt', (1609459200, 1609459200))
    check(run('time.txt', index_env)[0], rescan('stale'), 'a sampled file changed time: full scan')
    raw = bytearray(index.read_bytes()); raw[-3] ^= 0x55; index.write_bytes(raw)
    check(run('sum.txt', index_env)[0], rescan('checksum'), 'corrupted payload: checksum refusal')
    index.write_bytes(index.read_bytes()[:-5])
    check(run('short.txt', index_env)[0], rescan('header'), 'truncated index: length refusal')
    raw = bytearray(index.read_bytes()); at = raw.index(b'T.ms'); raw[at:at + 4] = b'T/ms'
    checksum = 2166136261
    for byte in bytes(raw[348:]):
        checksum = ((checksum ^ byte) * 16777619) & 0xffffffff
    raw[344:348] = checksum.to_bytes(4, 'little'); index.write_bytes(raw)
    check(run('records.txt', index_env)[0], rescan('records'), 'an unsafe record name is refused')
    final, final_tree = run('final.txt', index_env)
    check(final, ['phase=index result=hit reason=match', 'RESULT files=9 folders=8 skipped=1 listings=2'],
          'the rewritten index hits again')
    check(final_tree, run('last.txt', base_env)[1], 'and equals a fresh full scan')
    check(Path(str(index) + '.tmp').exists(), False, 'no temporary index is left behind')
if failures:
    sys.exit('FAIL: %d check(s)' % len(failures))
print('PASS: saved folder-cache index, %d checks' % len(checks))
