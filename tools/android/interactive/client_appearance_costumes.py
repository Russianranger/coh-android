#!/usr/bin/env python3
"""Finite stock Atlas NPC appearance edges, following native costume naming.

This module only discovers original asset dependencies.  It does not rewrite
costumes, alias missing geometry, or alter native loading/rendering behaviour.
The caller supplies frozen donor metadata (including cached GEO headers), then
uses its ordinary original-file/material closure to resolve these requests.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import client_visual_geometry as geometry
import client_visual_tricks as tricks


BODY_TYPES = (
    ('male', 'SM'), ('fem', 'SF'), ('bm', 'BM'), ('bf', 'BF'),
    ('huge', 'SH'), ('enemy', 'EY'), ('enemy', 'EY'),
    ('enemy2', 'EY'), ('enemy3', 'EY'),
)
CHEST_LINKED = {'collar', 'capeharness', 'broach', 'back', 'cape'}
NATIVE_RULES = {
    'appearance_bodytype': 'upstream/ouroboros/Common/gameComm/NPC.c:112',
    'bodytype_prefixes': 'upstream/ouroboros/Common/entity/costume.c:1984-1996',
    'costume_prefix': 'upstream/ouroboros/Common/entity/costume.c:2024-2038',
    'geometry': 'upstream/ouroboros/Game/src/entity/costume_client.c:221-375',
    'texture': 'upstream/ouroboros/Game/src/entity/costume_client.c:386-478',
    'gender_prefix': 'upstream/ouroboros/Game/src/entity/costume_client.c:71-99',
    'texture_pass_type': 'upstream/ouroboros/Game/src/entity/costume_client.c:522-547',
    'player_library_root': 'upstream/ouroboros/Game/src/entity/entclient.c:3280-3331',
    'persistent_npc_filename': 'upstream/ouroboros/MapServer/src/storyarc/pnpc.c:130-145',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def unique(rows):
    return [json.loads(row) for row in sorted({canonical(row).decode() for row in rows})]


def strip_comments(text):
    """Remove //, # and /* */ comments without losing source line positions."""
    pattern = re.compile(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\r\n]*|\#[^\r\n]*', re.S)
    def replace(match):
        token = match.group()
        return token if token.startswith('"') else '\n' * token.count('\n')
    return pattern.sub(replace, text)


def line_tokens(text):
    """Tokens with line numbers; quoted backslashes are stock path separators."""
    pattern = re.compile(r'"(?:\\.|[^"\\])*"|[{},=]|[^\s{},=]+')
    for line, content in enumerate(strip_comments(text).splitlines(), 1):
        row = []
        for match in pattern.finditer(content):
            token = match.group()
            if token.startswith('"'):
                token = token[1:-1].replace('\\"', '"')
            row.append(token)
        if row:
            yield line, row


@dataclass
class Node:
    key: str
    args: list[str]
    line: int
    children: list['Node'] = field(default_factory=list)


def brace_nodes(text):
    """Parse balanced stock brace blocks, independent of nested part contents."""
    roots, stack = [], []
    last = None
    for line, tokens in line_tokens(text):
        statement = []
        def flush():
            nonlocal last
            if statement:
                last = Node(statement[0], statement[1:], line)
                (stack[-1].children if stack else roots).append(last)
                statement.clear()
        for token in tokens:
            if token == '{':
                flush()
                if last is None:
                    raise ValueError(f'Anonymous opening brace at line {line}')
                stack.append(last)
                last = None
            elif token == '}':
                flush()
                if not stack:
                    raise ValueError(f'Unbalanced closing brace at line {line}')
                stack.pop()
                last = None
            elif token != ',':
                statement.append(token)
        flush()
    if stack:
        raise ValueError('Unclosed stock brace block')
    return roots


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)


def named_brace_nodes(text, keyword, selected_names=None):
    """Isolate each named root before balanced parsing.

    A few unused stock .nd entries are malformed. They must not prevent auditing
    valid unrelated NPCs, nor silently lend their incomplete parts to the next
    entry. Selected malformed definitions are returned as explicit gaps.
    """
    lines = text.splitlines(keepends=True)
    starts = [(line, tokens[1]) for line, tokens in line_tokens(text)
              if tokens[0].casefold() == keyword.casefold() and len(tokens) > 1]
    for index, (line, name) in enumerate(starts):
        if selected_names is not None and name.casefold() not in selected_names:
            continue
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        try:
            nodes = brace_nodes(''.join(lines[line - 1:end]))
            for node in walk(nodes):
                node.line += line - 1
            selected = [node for node in nodes if node.key.casefold() == keyword.casefold()]
            if len(selected) != 1 or not selected[0].children:
                raise ValueError('Named root lacks one balanced definition')
            yield name, line, selected[0], None
        except ValueError as error:
            yield name, line, None, str(error)


def value(node, key, default=None):
    selected = [item for item in node.children if item.key.casefold() == key.casefold()]
    return selected[-1].args[0] if selected and selected[-1].args else default


def bodyparts(text):
    result, current = {}, None
    for line, tokens in line_tokens(text):
        key = tokens[0].casefold()
        if key == 'bodypart':
            if current is not None:
                raise ValueError('BodyPart block missing End')
            current = {'line': line}
        elif key == 'end':
            if current is not None:
                result[current['name'].casefold()] = current
                current = None
        elif current is not None and len(tokens) > 1:
            current[key] = tokens[1]
    if current is not None:
        raise ValueError('Unclosed BodyPart block')
    return result


def appearance(enttype, costume_prefix=None, bodytype=None):
    """NPC postprocess resolves type from the enttype prefix before first _."""
    if bodytype is None:
        prefix = (enttype or 'male').split('_', 1)[0].casefold()
        bodytype = next((i for i, pair in enumerate(BODY_TYPES)
                         if pair[0].casefold()[:len(prefix)] == prefix), 0)
    if not 0 <= bodytype < len(BODY_TYPES):
        raise ValueError('Invalid native appearance body type')
    body_name, tex_prefix = BODY_TYPES[bodytype]
    return {'bodytype': bodytype, 'enttype': enttype or body_name,
            'costume_file_prefix': costume_prefix,
            'costume_prefix': costume_prefix or (body_name if bodytype != 6 else None),
            'texture_prefix': (costume_prefix if bodytype == 6 else tex_prefix)}


def texture_names(bp, app, name1, name2, native_texture_stems):
    """determineTextureNames, including explicit ! and conditional gender fixup."""
    if name1 is None:
        return []
    explicit1 = name1.startswith('!')
    explicit2 = bool(name2 and name2.startswith('!'))
    none1 = name1.lstrip('!').casefold() == 'none'
    none2 = name2 is None or name2.lstrip('!').casefold() == 'none'
    single = name1[-1:].casefold() == 'x'
    dual = name1[-1:].casefold() == 'a'
    out1 = 'none' if none1 else name1[1:] if explicit1 else bp['texname'] + '_' + name1
    if none2 or single:
        out2 = 'none'
    elif explicit2:
        out2 = name2[1:]
    elif dual and app.get('costume_file_prefix') and out1[-3:].casefold() == '01a':
        out2 = out1[:-1] + 'B'
    else:
        out2 = bp['texname'] + '_' + name2
    result = []
    for channel, output, literal, explicit, absent in (
        (1, out1, name1, explicit1, none1),
        (2, out2, name2, explicit2, none2 or single),
    ):
        if absent:
            continue
        prefixed = (app['texture_prefix'] or '') + '_' + output
        if not explicit and tricks.texture_stem(prefixed) in native_texture_stems:
            output = prefixed
        result.append({'channel': channel, 'literal': literal, 'target': output,
                       'stem': tricks.texture_stem(output), 'explicit': explicit})
    return result


def geometry_names(bp, app, name, chest_names=('tight',), model_exists=None):
    """doChangeGeo's exact candidate order; absent Larm geometry is kept as evidence.

    model_exists(file, model) must look in frozen native GEO model tables.  This
    lets a chest-linked part choose its supported native variant; it never picks
    a similar name or a geometry from another filename.
    """
    if not name or name.casefold() == 'none':
        return []
    count = int(bp.get('bonecount', '0'))
    if count <= 0:
        return []
    linked = bp['name'].casefold() in CHEST_LINKED
    explicit = re.search(r'\.geo/', name, re.I)
    candidates = []
    if explicit:
        file = 'data/player_library/' + name[:explicit.start()].casefold() + '.geo'
        model = name[explicit.end():]
        if linked:
            choices = [model + '_' + chest for chest in chest_names]
            selected = next((item for item in choices if model_exists and model_exists(file, item)), model)
            candidates.append((file, selected))
        elif count == 2:
            if '*' in model:
                candidates.extend((file, model.replace('*', side, 1)) for side in ('R', 'L'))
            elif any(item in model.casefold() for item in ('larmr', 'larml', 'llegr', 'llegl')):
                candidates.append((file, model))
            # Native deliberately applies no update for an unrecognized paired
            # explicit model without *, rather than inventing a second limb.
        else:
            candidates.append((file, model))
    else:
        if not app['costume_prefix']:
            raise ValueError('Native villain costume has no geometry prefix')
        file = 'data/player_library/' + app['costume_prefix'].casefold() + '_' + bp['basename'].casefold() + '.geo'
        base = 'GEO_' + bp['geoname']
        for side in (('R', 'L') if count == 2 else ('',)):
            model = base + side + '_' + name
            if linked:
                choices = [base + side + '_' + chest + '_' + name for chest in chest_names]
                model = next((item for item in choices if model_exists and model_exists(file, item)), model)
            candidates.append((file, model))
    return [{'file': file, 'model': model, 'literal': name} for file, model in candidates]


def end_blocks(text, block_keys):
    """Read nested End blocks used by spawnarea and object-library source."""
    roots, stack = [], []
    for line, tokens in line_tokens(text):
        key = tokens[0].casefold()
        if key == 'end':
            if stack:
                stack.pop()
            continue
        item = Node(tokens[0], [token for token in tokens[1:] if token != ','], line)
        (stack[-1].children if stack else roots).append(item)
        if key in block_keys:
            stack.append(item)
    return roots


class Sources:
    def __init__(self, root):
        root = Path(root)
        self.repo = root if (root / 'upstream/i24/data').is_dir() else None
        self.root = root / 'upstream/i24/data' if self.repo else root
        self.paths = {path.relative_to(self.root).as_posix().casefold(): path
                      for path in self.root.rglob('*') if path.is_file()}
        self.pins = {}
        self.cache = {}

    def resolve(self, name):
        name = name.replace('\\', '/').removeprefix('data/').casefold()
        return self.paths.get(name)

    def read(self, path, *, pin=True):
        path = Path(path)
        key = path.relative_to(self.root).as_posix()
        if key not in self.cache:
            raw = path.read_bytes()
            self.cache[key] = (raw.decode('utf-8-sig', errors='replace'),
                               {'path': path.relative_to(self.repo).as_posix() if self.repo else 'data/' + key,
                                'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        text, identity = self.cache[key]
        if pin:
            self.pins[identity['path']] = identity
        return text

    def witness(self, path, line, **extra):
        self.read(path)
        key = (Path(path).relative_to(self.repo).as_posix() if self.repo
            else 'data/' + Path(path).relative_to(self.root).as_posix())
        return {'scope': 'atlas_stock_appearance_dependency', 'source': key,
                'source_sha256': self.pins[key]['sha256'], 'line': line, **extra}


def atlas_requests(root, files, *, map_files=None, extra_npcs=(), extra_enttypes=(), extra_factions=()):
    """Discover the finite Atlas map → actor/generator → costume/type closure.

    ``files`` keys may have or omit data/. GEO cached_header fields are bytes.
    Output geometry rows have ``model`` when a native model was requested;
    EntType Graphics files intentionally request the whole original table.
    ``fx`` maps data/fx/... paths to source witnesses for the caller's FX walker.
    Source pins include every selected stock definition and native rule source.
    """
    sources = Sources(root)
    files = {name.removeprefix('data/').casefold(): row for name, row in files.items()}
    stems = {PurePosixPath(name).stem for name in files if name.startswith('texture_library/')}
    models = {}
    def model_exists(name, model):
        name = name.removeprefix('data/').casefold()
        if name not in models:
            row = files.get(name)
            try:
                models[name] = {item['name'].split('__', 1)[0].casefold()
                                for item in geometry.tables(row['cached_header'])[1]} if row and row.get('cached_header') else set()
            except ValueError as error:
                models[name] = set()
                out['unresolved'].append({'kind': 'geometry_header_for_chest_link',
                    'target': 'data/' + name, 'reason': str(error)})
        return model.casefold() in models[name]
    out = {'geometry': defaultdict(list), 'textures': defaultdict(list), 'fx': defaultdict(list),
           'enttypes': defaultdict(list), 'source_files': [], 'closure': {}, 'unresolved': []}
    selected_npcs, selected_types, selected_groups, selected_factions, selected_villains = (defaultdict(list) for _ in range(5))
    pending_scripts, pending_npcs = deque(), deque()
    map_paths = [Path(path) for path in map_files] if map_files is not None else [
        path for key, path in sources.paths.items()
        if key.startswith('maps/city_zones/city_01_01/') and key.endswith('.txt')]
    encounter_groups, generators = {}, defaultdict(list)
    map_seen, object_seen = set(), set()
    # Def names inside encounter source files have no one-to-one filename map.
    object_index = defaultdict(list)
    for key, path in sorted(sources.paths.items()):
        if key.startswith('object_library/omni/encounterspawns/') and key.endswith('.txt'):
            for line, tokens in line_tokens(sources.read(path, pin=False)):
                if tokens[0].casefold() == 'def' and len(tokens) > 1:
                    object_index[tokens[1].casefold()].append(path)

    def scan_map_source(path, selected=None):
        rows = line_tokens(sources.read(path)) if selected is None else (
            (node.line, [node.key, *node.args]) for node in walk([selected]))
        for line, tokens in rows:
            key = tokens[0].casefold()
            if key == 'include' and len(tokens) > 1:
                found = sources.resolve(tokens[1])
                if found:
                    map_paths.append(found)
            elif key == 'group' and len(tokens) > 1 and 'encounterspawns/' in tokens[1].replace('\\', '/').casefold():
                group = tokens[1].replace('\\', '/').rsplit('/', 1)[-1].casefold()
                encounter_groups.setdefault(group, sources.witness(path, line, group=tokens[1]))
            elif key == 'property' and len(tokens) >= 3:
                field_name, target = tokens[1].casefold(), tokens[2]
                witness = sources.witness(path, line, property=tokens[1], target=target)
                if field_name == 'persistentnpc':
                    pending_npcs.append((target, witness))
                elif field_name == 'generator':
                    generators[target.casefold()].append(witness)
                elif target.casefold().endswith(('.spawndef', '.spawninc')):
                    pending_scripts.append((target, witness))
    while map_paths:
        path = map_paths.pop()
        if path not in map_seen:
            map_seen.add(path)
            scan_map_source(path)
    groups_done, object_nodes = set(), {}
    while set(encounter_groups) - groups_done:
        group = sorted(set(encounter_groups) - groups_done)[0]
        groups_done.add(group)
        for path in object_index.get(group, []):
            if path not in object_nodes:
                object_nodes[path] = {node.args[0].casefold(): node for node in
                    end_blocks(sources.read(path), {'def', 'group', 'rootmod'})
                    if node.key.casefold() == 'def' and node.args}
            selected = object_nodes[path].get(group)
            if selected:
                object_seen.add(path)
                scan_map_source(path, selected)
        # Includes within object sources may themselves carry actor properties.
        while map_paths:
            path = map_paths.pop()
            if path not in map_seen and path not in object_seen:
                map_seen.add(path)
                scan_map_source(path)

    for npc in extra_npcs:
        selected_npcs[npc.casefold()].append({'scope': 'recorded_client_npc_appearance', 'npc': npc})
    for enttype in extra_enttypes:
        selected_types[enttype.casefold()].append({'scope': 'recorded_client_enttype_appearance', 'enttype': enttype})
    for faction in extra_factions:
        selected_factions[faction.casefold()].append({'scope': 'recorded_client_faction_appearance', 'faction': faction})
    seen_npcdefs = set()
    while pending_npcs:
        name, incoming = pending_npcs.popleft()
        path = sources.resolve('scripts.loc/' + name) or sources.resolve('scripts/' + name)
        if not path:
            # PNPCPreload matches a cleaned marker substring inside the stock
            # filename. Require uniqueness rather than guessing load order.
            cleaned = name.replace('\\', '/').casefold()
            candidates = [value for key, value in sources.paths.items()
                if key.startswith(('scripts.loc/', 'scripts/')) and key.endswith('.npc') and cleaned in key]
            if len(candidates) == 1:
                path = candidates[0]
        if not path:
            out['unresolved'].append({'kind': 'persistentnpc_source', 'target': name, 'sources': [incoming]})
            continue
        if path in seen_npcdefs:
            continue
        seen_npcdefs.add(path)
        for node in walk(brace_nodes(sources.read(path))):
            if node.key.casefold() == 'model':
                for model in node.args:
                    selected_npcs[model.casefold()].append(sources.witness(path, node.line, npc=model, via=incoming))

    # Global definitions precede map overrides exactly as the server loads them.
    spawn_index, generator_index = {}, {}
    spawn_paths = [sources.resolve('server/spawnarea/globals.txt'), sources.resolve('server/spawnarea/city_01_01.txt')]
    for path in filter(None, spawn_paths):
        for node in walk(end_blocks(sources.read(path), {'spawnarea', 'npc', 'critter', 'car', 'generator', 'group', 'member'})):
            if node.key.casefold() in {'npc', 'critter', 'car', 'generator', 'group'} and node.args:
                index = generator_index if node.key.casefold() in {'generator', 'group'} else spawn_index
                index[node.args[0].casefold()] = (path, node)
    for generator, witnesses in generators.items():
        found = generator_index.get(generator)
        if not found:
            out['unresolved'].append({'kind': 'generator_source', 'target': generator, 'sources': unique(witnesses)})
            continue
        path, node = found
        for child in walk(node.children):
            if child.key.casefold() == 'generatedtypes':
                for target in child.args:
                    if not target.replace('.', '', 1).isdigit():
                        selected_groups[target.casefold()].append(sources.witness(path, child.line,
                            generator=generator, target=target, field=child.key))

    seen_scripts = set()
    while pending_scripts:
        name, incoming = pending_scripts.popleft()
        path = sources.resolve('scripts.loc/' + name) or sources.resolve('scripts/' + name)
        if not path:
            out['unresolved'].append({'kind': 'spawndef_source', 'target': name, 'sources': [incoming]})
            continue
        if path in seen_scripts:
            continue
        seen_scripts.add(path)
        nodes = brace_nodes(sources.read(path))
        variables = {}
        for node in walk(nodes):
            if node.key.casefold() == 'var' and len(node.args) >= 3 and '=' in node.args:
                equals = node.args.index('=')
                variables[node.args[0].casefold()] = [item for item in node.args[equals + 1:] if item != ',']
        def expand(name, visited=()):
            quoted = re.fullmatch(r'<<([^<>\s]+)>>', name)
            if quoted:
                name = quoted.group(1)
            key = name.casefold()
            if key in visited:
                raise ValueError('Cyclic stock spawn variable: ' + name)
            return [leaf for child in variables[key] for leaf in expand(child, (*visited, key))] if key in variables else [name]
        for node in walk(nodes):
            key = node.key.casefold()
            if key in {'model', 'villain', 'villaindef', 'villaingroup'}:
                for original in node.args:
                    for target in expand(original):
                        witness = sources.witness(path, node.line, field=node.key, literal=original, target=target)
                        if key == 'model':
                            selected_groups[target.casefold()].append(witness)
                        elif key == 'villaingroup':
                            selected_factions[target.casefold()].append(witness)
                        else:
                            selected_villains[target.casefold()].append(witness)
            for target in node.args:
                if target.casefold().endswith(('.spawndef', '.spawninc', '.varinc')):
                    pending_scripts.append((target, sources.witness(path, node.line, target=target)))
    groups_queue = deque(sorted(selected_groups))
    expanded_groups = set()
    while groups_queue:
        name = groups_queue.popleft()
        if name in expanded_groups:
            continue
        expanded_groups.add(name)
        found = spawn_index.get(name) or generator_index.get(name)
        if not found:
            selected_npcs[name].extend(selected_groups[name])
            continue
        path, node = found
        for child in walk(node.children):
            if child.key.casefold() in {'type', 'generatedtypes'}:
                for target in child.args:
                    if target.replace('.', '', 1).isdigit():
                        continue
                    selected_groups[target.casefold()].append(sources.witness(path, child.line,
                        group=name, target=target, field=child.key))
                    groups_queue.append(target.casefold())

    for key, path in sorted(sources.paths.items()):
        if not key.startswith('defs/') or not key.endswith('.villain'):
            continue
        for node in brace_nodes(sources.read(path, pin=False)):
            if node.key.casefold() != 'villaindef' or not node.args:
                continue
            name = node.args[0]
            faction = value(node, 'VillainGroup', '').casefold()
            if name.casefold() not in selected_villains and faction not in selected_factions:
                continue
            seen_costumes = set()
            for child in walk(node.children):
                if child.key.casefold() == 'costumes':
                    for npc in child.args:
                        if npc.casefold() in seen_costumes:
                            continue
                        seen_costumes.add(npc.casefold())
                        selected_npcs[npc.casefold()].append(sources.witness(path, child.line,
                            npc=npc, villain=name, faction=faction))

    bp_path = sources.resolve('defs/ui/bodyparts.bp')
    chest_path = sources.resolve('defs/chestgeolink.def')
    bps = bodyparts(sources.read(bp_path))
    chest_links = {value(node, 'BonesetName', '').casefold(): next(
        (tuple(item.args) for item in node.children if item.key.casefold() == 'geostrings'), ('tight',))
        for node in brace_nodes(sources.read(chest_path)) if node.key.casefold() == 'chestgeolink'}
    npc_index = defaultdict(list)
    for key, path in sorted(sources.paths.items()):
        if key.startswith('defs/') and key.endswith('.nd'):
            for name, line, node, error in named_brace_nodes(sources.read(path, pin=False), 'npc', selected_npcs):
                npc_index[name.casefold()].append((path, line, node, error))
    processed_npcs = []
    for name, selection in sorted(selected_npcs.items()):
        candidates = npc_index.get(name, [])
        if not candidates:
            # Server generators may directly use an ent_type without .nd.
            if sources.resolve('ent_types/' + name + '.txt'):
                selected_types[name].extend(selection)
            else:
                out['unresolved'].append({'kind': 'npc_costume_source', 'target': name, 'sources': unique(selection)})
            continue
        for path, line, npc, error in candidates:
            if error:
                out['unresolved'].append({'kind': 'npc_costume_source_parse', 'target': name,
                    'reason': error, 'sources': [sources.witness(path, line, npc=name)]})
                continue
            processed_npcs.append(npc.args[0])
            for costume in (node for node in npc.children if node.key.casefold() == 'costume'):
                app = appearance(value(costume, 'EntTypeFile'), value(costume, 'CostumeFilePrefix'))
                witness = sources.witness(path, costume.line, npc=npc.args[0], enttype=app['enttype'])
                selected_types[app['enttype'].casefold()].append(witness)
                parts = [node for node in costume.children if node.key.casefold() == 'costumepart']
                chest = next((part for part in parts if part.args and part.args[0].casefold() == 'chest'), None)
                chest_names = chest_links.get(value(chest, 'BodySetName', '').casefold(), ('tight',)) if chest else ('tight',)
                for part_index, part in enumerate(parts):
                    bp_name = part.args[0] if part.args and part.args[0] else (
                        list(bps)[part_index] if part_index < len(bps) else '')
                    if bp_name.casefold() not in bps:
                        out['unresolved'].append({'kind': 'costume_bodypart', 'target': part.args, 'sources': [witness]})
                        continue
                    bp = bps[bp_name.casefold()]
                    for edge in geometry_names(bp, app, value(part, 'Geometry'), chest_names, model_exists):
                        out['geometry'][edge['file']].append(sources.witness(path, part.line,
                            npc=npc.args[0], part=bp['name'], model=edge['model'], literal=edge['literal'],
                            enttype=app['enttype'], native_rule=NATIVE_RULES['geometry']))
                    for edge in texture_names(bp, app, value(part, 'Texture1'), value(part, 'Texture2'), stems):
                        out['textures'][edge['stem']].append(sources.witness(path, part.line,
                            npc=npc.args[0], part=bp['name'], channel=edge['channel'], target=edge['target'],
                            literal=edge['literal'], explicit=edge['explicit'], enttype=app['enttype'],
                            native_rule=NATIVE_RULES['texture']))
                    fx = value(part, 'Fx')
                    if fx and fx.casefold() != 'none':
                        target = 'data/fx/' + fx.replace('\\', '/').casefold().removeprefix('fx/')
                        out['fx'][target].append(sources.witness(path, part.line, npc=npc.args[0],
                            part=bp['name'], literal=fx, target=target))

    for name, selection in sorted(selected_types.items()):
        path = sources.resolve('ent_types/' + name.removesuffix('.txt') + '.txt')
        if not path:
            out['unresolved'].append({'kind': 'enttype_source', 'target': name, 'sources': unique(selection)})
            continue
        out['enttypes'][name] = unique(selection)
        for line, tokens in line_tokens(sources.read(path)):
            key = tokens[0].casefold()
            if len(tokens) < 2:
                continue
            literal = tokens[1]
            target = literal.replace('\\', '/').casefold().removeprefix('data/')
            witness = sources.witness(path, line, enttype=name, field=tokens[0], literal=literal, target=target)
            if key in {'graphics', 'bonescaleskinny', 'bonescalefat'} and target.endswith('.geo'):
                out['geometry']['data/' + target].append(witness)
            elif key == 'shadowtexture' and tricks.valid_texture_name(target):
                out['textures'][tricks.texture_stem(target)].append(witness)
            elif key == 'fx' and target.endswith('.fx'):
                out['fx']['data/fx/' + target.removeprefix('fx/')].append(witness)
    # Pin naming logic as well as selected data. These pins are repo-relative.
    if sources.repo:
        for rel in sorted({rule.split(':', 1)[0] for rule in NATIVE_RULES.values()}):
            raw = (sources.repo / rel).read_bytes()
            sources.pins[rel] = {'path': rel, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    out['source_files'] = [sources.pins[key] for key in sorted(sources.pins)]
    out['closure'] = {'map_files': len(map_seen), 'encounter_source_files': len(object_seen),
        'persistent_npc_files': len(seen_npcdefs), 'spawn_source_files': len(seen_scripts),
        'generator_names': sorted(generators), 'selected_npcs': sorted(set(processed_npcs), key=str.casefold),
        'npc_selection_evidence': {name: unique(rows) for name, rows in sorted(selected_npcs.items())},
        'faction_selection_evidence': {name: unique(rows) for name, rows in sorted(selected_factions.items())},
        'selected_factions': sorted(selected_factions), 'selected_enttypes': sorted(out['enttypes']),
        'native_rules': NATIVE_RULES,
        'scope': 'all_stock_atlas_map_layers_and_referenced_encounter_actor_appearance_closure',
        'stock_optional_layers_included': True, 'runtime_costume_rewriting': False}
    for key in ('geometry', 'textures', 'fx', 'enttypes'):
        out[key] = {name: unique(rows) for name, rows in sorted(out[key].items())}
    out['unresolved'] = unique(out['unresolved'])
    return out
