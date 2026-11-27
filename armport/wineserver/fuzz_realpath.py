#!/usr/bin/env python3
"""Random trees of folders, files and links: the realpath cache must answer exactly as glibc.

Usage: fuzz_realpath.py LIBRARY CHECK_BINARY SEED ROUNDS   (prints "rounds N different M")
Links are absolute, relative, with "./" and "../", with a trailing slash, dangling and looping;
paths add missing names, "." and ".." and empty components. Both answers and errno are compared.
"""
import os, random, shutil, subprocess, sys, tempfile
from pathlib import Path
lib, binary, seed, rounds = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rng = random.Random(seed)
bad = 0
for r in range(rounds):
    work = Path(tempfile.mkdtemp(prefix='rpf-'))
    try:
        server = work / 'wineserver'; shutil.copy2(binary, server)
        root = work / 't'; root.mkdir()
        dirs, files, names = [root], [], ['a', 'b', 'c', 'd', 'e']
        for _ in range(rng.randint(5, 25)):
            d = rng.choice(dirs) / rng.choice(names)
            if not d.exists() and not d.is_symlink():
                d.mkdir(); dirs.append(d)
        for _ in range(rng.randint(5, 25)):
            f = rng.choice(dirs) / (rng.choice(names) + '.f')
            if not f.exists() and not f.is_symlink():
                f.write_text('x'); files.append(f)
        every = dirs + files
        for _ in range(rng.randint(5, 30)):
            l = rng.choice(dirs) / ('l' + rng.choice(names))
            if l.exists() or l.is_symlink(): continue
            t = rng.choice(every + [root / 'missing', l.parent / ('l' + rng.choice(names))])
            kind = rng.randint(0, 5)
            if kind == 0: target = str(t)
            elif kind == 1: target = os.path.relpath(t, l.parent)
            elif kind == 2: target = './' + os.path.relpath(t, l.parent)
            elif kind == 3: target = os.path.relpath(t, l.parent) + '/'
            elif kind == 4: target = str(t).replace('/t/', '/t/./', 1)
            else: target = '../' * rng.randint(0, 3) + rng.choice(names)
            os.symlink(target, l); every.append(l)
        paths = []
        for _ in range(300):
            p = str(rng.choice(every))
            for _ in range(rng.randint(0, 3)):
                p += '/' + rng.choice(names + ['la', 'lb', 'lc', '..', '.', 'a.f', ''])
            paths.append(p)
        env = {k: v for k, v in os.environ.items() if k != 'LD_PRELOAD'}
        a = subprocess.run([str(server), '--repeat', '2', *paths], env=env, stdout=subprocess.PIPE).stdout
        b = subprocess.run([str(server), '--repeat', '2', *paths], env=dict(env, LD_PRELOAD=lib, ARMPORT_REALPATH_CACHE='1'), stdout=subprocess.PIPE).stdout
        if a != b:
            bad += 1
            al, bl = a.decode().splitlines(), b.decode().splitlines()
            for i, (x, y) in enumerate(zip(al, bl)):
                if x != y: print('DIFF', paths[i // 2], '|', x, '|', y); break
    finally:
        shutil.rmtree(work, ignore_errors=True)
print('rounds', rounds, 'different', bad)
