#!/usr/bin/env python3
"""The persisted English MessageStore source scope of the accepted MapServer.

Read the byte-pinned native declarations rather than assuming that messages use
an .ms extension. MultiMessageStore's directory scanner loads every non-.bak
leaf; its explicit type paths are unlocalized, while message paths are English.
The separate command-message store has no persisted binary and is outside this
scope. This host-only module is a native-consumption evidence gate.
"""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
NATIVE_SOURCES = {
    'upstream/ouroboros/MapServer/src/language/langServerUtil.c':
        'b049353bb2e7797dca4ed96639aa5dd0643ac849d46a8a26b00501fe20b9e692',
    'upstream/ouroboros/MapServer/src/storyarc/storyarcutil.c':
        '04b021ff8a5c58812139a6d135a98fbcf16db3ed88ad8e9f5aef521149fc27d1',
    'upstream/ouroboros/libs/UtilitiesLib/src/language/MultiMessageStore.c':
        '7d631a417d9690ae26f0d6a749fe518e4636b36594c761a72dbebae9ebd764a0',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uncomment(source):
    # Preserve quoted strings: a native file-scan pattern such as "%s/*.*" is
    # not a block comment. Preserve newlines to keep declarations separated.
    tokens = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*.*?\*/|//[^\n]*'
    return re.sub(tokens, lambda match: match[0] if match[0][0] in '\"\''
                  else '\n' * match[0].count('\n'), source, flags=re.S)


def declaration(source, name):
    matches = re.findall(r'\b' + re.escape(name) + r'\s*\[\s*\]\s*=\s*\{([^}]+)\}',
                         uncomment(source), re.S)
    require(len(matches) == 1, 'Expected one native MessageStore array: ' + name)
    body = matches[0]
    token = r'"(?:\\.|[^"\\])*"|\bNULL\b|,|\s+'
    require(not re.sub(token, '', body), 'Unsupported native MessageStore array expression: ' + name)
    entries = re.findall(r'"(?:\\.|[^"\\])*"|\bNULL\b', body)
    require(entries and entries[-1] == 'NULL', 'Native MessageStore array has no terminator: ' + name)
    values = []
    for value in entries[:-1]:
        if value == 'NULL':
            values.append(None)
            continue
        # These pinned paths contain only literal ASCII path characters and
        # escaped backslashes; reject C escapes that JSON would reinterpret.
        require(re.fullmatch(r'"[A-Za-z0-9_./\\-]+"', value),
                'Unsupported native MessageStore path: ' + name)
        path = json.loads(value).replace('\\', '/').strip('/').casefold()
        require(path.startswith('texts/') and all(part not in ('', '.', '..')
                for part in path.split('/')), 'Unsafe native MessageStore path')
        values.append(path)
    return values


def derive_contract(sources):
    require(set(sources) == set(NATIVE_SOURCES), 'Native MessageStore source closure differs')
    decoded = {}
    for name, expected in NATIVE_SOURCES.items():
        raw = sources[name]
        require(isinstance(raw, bytes) and hashlib.sha256(raw).hexdigest() == expected,
                'Accepted MapServer MessageStore source bytes differ: ' + name)
        decoded[name] = raw.decode('utf-8')
    menu = decoded['upstream/ouroboros/MapServer/src/language/langServerUtil.c']
    story = decoded['upstream/ouroboros/MapServer/src/storyarc/storyarcutil.c']
    fixed, prefixes = set(), set()
    for source, name in ((menu, 'apchMessageFiles'), (story, 'staticMessageFiles')):
        files = declaration(source, name)
        require(len(files) % 2 == 0, 'Native MessageStore message/type pair differs')
        for message, types in zip(files[::2], files[1::2]):
            require(message is not None, 'Native MessageStore message path is NULL')
            fixed.add('data/texts/english/' + message.removeprefix('texts/'))
            if types is not None:
                fixed.add('data/' + types)
    for source, name in ((menu, 'apchMessageDirs'), (story, 'storyarcMessageDirs')):
        for directory in declaration(source, name):
            require(directory is not None, 'Native MessageStore directory path is NULL')
            prefixes.add('data/texts/english/' + directory.removeprefix('texts/') + '/')
    require(len(fixed) == 5 and len(prefixes) == 27, 'Accepted MessageStore source inventory differs')
    return {'fixed_files': tuple(sorted(fixed)), 'directory_prefixes': tuple(sorted(prefixes))}


@lru_cache(maxsize=1)
def persisted_source_contract():
    return derive_contract({name: (ROOT / name).read_bytes() for name in NATIVE_SOURCES})


def is_persisted_source(name: str) -> bool:
    if not isinstance(name, str):
        return False
    name = name.replace('\\', '/').casefold()
    if (not name.startswith('data/texts/') or name.endswith('/')
            or any(part in ('', '.', '..') for part in name.split('/'))):
        return False
    contract = persisted_source_contract()
    return (name in contract['fixed_files'] or
            (not name.endswith('.bak') and any(name.startswith(prefix)
             for prefix in contract['directory_prefixes'])))
