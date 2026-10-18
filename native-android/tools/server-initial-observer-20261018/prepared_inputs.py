"""Reconstruct only the three new hook TUs through the accepted source chain.

No old preparer entrypoint, compiler, qualifier or service is executed. Git
applies only explicitly selected hunks in a fresh private temporary directory.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
TICK = 'MapServer/src/svr/svr_tick.c'
ENTS = 'MapServer/src/entity/entsend.c'
CHAR = 'MapServer/src/entity/entserver.c'
TUS = (TICK, ENTS, CHAR)
CHAIN = (
 ('patches/postgresql/0001-dbserver-postgresql.patch', '03898e46aa0d8aa34b97234a296307e075c8859f438567450cfb4024f5a282ad'),
 ('patches/game-loopback/0001-game-loopback-bindings.patch', '7c4f4b25ab134a0dac2f4501f7cf2a5cccbfcd9482775350e3be0e1df532b8a6'),
 ('patches/mapserver-progress/0001-mapserver-progress.patch', '0fc278d0f04c979b5153421278156978f11fc58584c3413645937ecd83021b2c'),
 ('patches/character-events/0001-character-events.patch', '79db1abc8538d4fcdbc7e544639e11f809a1527de8a5dbfb258c051235fd49b7'),
 ('patches/monorail/0001-monorail.patch', '47e524db02d80bb9be0b1c834f8c0d3b808abff1591f440aa04a24367ac5b026'),
)
ORIGINAL = {TICK: '790635fec2f21e49981c776815eb8e927e79ef5a277324b0e3601cc3b4bbade0',
 ENTS: '045a5ecb5b64b956229583143fc61316dd8113d8eacf92183ad4756abad0a054',
 CHAR: '01da7bf37f633c98a39cd65176810e7b9c4bef4f834b896ed888ec6c52f47806'}
PREPARED = {**ORIGINAL, TICK: 'a3810c112556b258ee2456a51eb28d6afeefd14b81c2fa97ed431659ae42a3d5'}
PRODUCERS = ('tools/prepare_runtime.py', 'tools/prepare_game_loopback_source.py',
 'tools/prepare_mapserver_progress_source.py', 'tools/prepare_character_events_source.py',
 'tools/prepare_monorail_source.py', 'tools/prepare_map_startup_source.py',
 'tools/map_startup_monorail_budget.py')


def need(ok, code):
    if not ok:
        raise ValueError(code)


def lf(path):
    path = Path(path)
    need(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents))
         and path.stat().st_nlink == 1, 'PREPARED_REGULAR_SOURCE')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    need(b'\r' not in raw, 'PREPARED_SOURCE_NEWLINES')
    return raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_paths(root):
    need(Path(root).resolve() == HERE.parents[2], 'PREPARED_OWN_CHECKOUT')
    return {HERE.relative_to(Path(root).resolve()).as_posix() + '/prepared_inputs.py',
            *PRODUCERS, *('upstream/ouroboros/' + n for n in TUS), *(n for n, _ in CHAIN)}


def reconstruct(root, *, with_proof=False):
    root = Path(root).resolve()
    paths = source_paths(root)
    before = {name: sha(lf(root / name)) for name in paths}
    patches = {}
    for name, expected in CHAIN:
        raw = lf(root / name)
        need(sha(raw) == expected, 'PREPARED_CHAIN_PATCH_PIN')
        patches[name] = raw
    # Refuse an undeclared patch touching any new hook TU.
    for path in (root / 'patches').rglob('*.patch'):
        names = {row[6:] for row in lf(path).decode().splitlines() if row.startswith('+++ b/')}
        if names.intersection(TUS):
            need(path.relative_to(root).as_posix() in patches, 'PREPARED_UNDECLARED_PATCH')
    environment = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        environment.pop(name, None)
    transitions = []
    with tempfile.TemporaryDirectory(prefix='coh-new-inherited-three-tu-') as temporary:
        staged = Path(temporary)
        environment['GIT_CEILING_DIRECTORIES'] = str(staged.parent)
        for name in TUS:
            raw = lf(root / 'upstream/ouroboros' / name)
            need(sha(raw) == ORIGINAL[name], 'PREPARED_ORIGINAL_TU_PIN')
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        for name, _ in CHAIN:
            raw = patches[name]
            touched = {row[6:] for row in raw.decode().splitlines() if row.startswith('+++ b/')}
            selected = [n for n in TUS if n in touched]
            if selected:
                command = ['git', '-c', 'core.autocrlf=false', 'apply',
                           *('--include=' + n for n in selected)]
                for tail in (['--check', '-'], ['-']):
                    subprocess.run(command + tail, cwd=staged, env=environment, input=raw,
                                   check=True, capture_output=True)
            transitions.append({'patch': name, 'patch_sha256': sha(raw), 'selected_tus': selected,
                                'post_patch_sha256': {n: sha(lf(staged / n)) for n in TUS}})
        result = {name: lf(staged / name) for name in TUS}
    need({n: sha(v) for n, v in result.items()} == PREPARED, 'PREPARED_FINAL_TU_PIN')
    need({name: sha(lf(root / name)) for name in paths} == before, 'PREPARED_SOURCE_CHANGED')
    proof = {'schema': 'coh-server-initial-inherited-three-tu-v1',
             'source_sha256_lf': before, 'ordered_patch_transitions': transitions,
             'prepared': {n: {'bytes': len(v), 'sha256': sha(v)} for n, v in result.items()},
             'accepted_preparer_entrypoints_reexecuted': False, 'compiler_executed': False,
             'services_executed': False, 'world_authority': False}
    return (result, proof) if with_proof else result
