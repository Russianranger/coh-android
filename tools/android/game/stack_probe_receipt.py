"""Bind the separate Windows hang observer to its source and PE32 bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from package_reference_runtime import pe_info

SOURCE = 'database/wine-game/GameStackProbe.c'
FLAGS = '/nologo /W4 /O2 /MT /D_WIN32_WINNT=0x0601'


def receipt(directory, commit):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid observer source commit')
    path = directory / 'GameStackProbe.exe'
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= 2 * 1024 * 1024:
        raise ValueError('Missing, linked or oversized observer executable')
    raw = path.read_bytes()
    pe = pe_info(raw)
    if pe['pe_machine'] != 0x14c:
        raise ValueError('Observer must be PE32')
    return {'format': 1, 'role': 'wine_game_hang_observer', 'repository_commit': commit,
            'source_sha256_lf': hashlib.sha256((ROOT / SOURCE).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            'source': SOURCE, 'compiler': 'MSVC', 'flags': FLAGS,
            'executable': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), **pe}}


def verify(directory, commit):
    path = directory / 'stack-probe-build.json'
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 65536:
        raise ValueError('Missing or invalid observer build receipt')
    actual = receipt(directory, commit)
    if json.loads(path.read_text()) != actual:
        raise ValueError('Observer source or executable differs from build receipt')
    return actual


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    value = receipt(args.directory, args.repository_commit)
    (args.directory / 'stack-probe-build.json').write_text(json.dumps(value, indent=2) + '\n')
