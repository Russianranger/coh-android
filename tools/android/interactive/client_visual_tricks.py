"""Read stock TexOpt edges with the retained native generation predicates.

This is read-only asset discovery, not a material rewrite or renderer emulation.
trickCreateTextures admits a composite alias only after all surviving texture
slots and enabled fallback slots exist. Its diagnostic reports the first missing
slot, so a useful sweep must retain the complete dependency set.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
from pathlib import Path
import shlex

TEXTURE_SLOTS = frozenset(('blend', 'bumpmap', 'base1', 'multiply1',
    'dualcolor1', 'addglow1', 'bumpmap1', 'mask', 'base2', 'multiply2',
    'dualcolor2', 'bumpmap2', 'cubemap'))
FALLBACK_SLOTS = frozenset(('base', 'blend', 'bumpmap'))
UNMASKED_REMOVED_SLOTS = frozenset(('mask', 'base2', 'multiply2',
    'bumpmap2', 'dualcolor2'))
MAX_TRICK_SOURCE_BYTES = 8 * 1024**2


def texture_stem(name):
    """Name key used by exact compiled texture discovery, never a fuzzy match."""
    value = name[1:] if name.startswith('!') else name
    value = value.replace('\\', '/').casefold().rsplit('/', 1)[-1]
    # texFind removes exactly one ! then texFixName strips a final dot plus
    # three or seven characters independently of its texture type recognition.
    # This covers original .psd/.ifl references without inventing replacements.
    if len(value) >= 4 and value[-4] == '.':
        return value[:-4]
    if len(value) >= 8 and value[-8] == '.':
        return value[:-8]
    return value


def valid_texture_name(name):
    # Common/seq/tricks.c IsValidTexName and texopt cleanup predicates.
    return bool(name and not name.startswith('%')
        and name.casefold() not in ('none', 'swappable')
        and not name.casefold().startswith('texture_name'))


def trick_name(name):
    """Native TexOpt postprocessing differs from texture binding lookup."""
    value = name[1:] if name.startswith('/') else name
    return value.rsplit('.', 1)[0] if '.' in value else value


def line_tokens(line):
    line = line.split('//', 1)[0].strip()
    if not line or line.startswith('#'):
        return []
    # Stock references are single texture names. shlex preserves quoted names
    # without guessing an alternative token when the syntax is malformed.
    return shlex.split(line, comments=False, posix=True)


def native_slot_key(slot):
    key = slot.casefold()
    # Both deprecated BumpMap and current BumpMap1 write BLEND_BUMPMAP1.
    # The embedded fallback BumpMap writes a separate field.
    return 'bumpmap1' if key == 'bumpmap' else key


def parse_texture_tricks_text(text, source_path):
    """Return declarations and surviving slot edges with exact source lines.

    This intentionally retains only slots that native preprocessing can use:
    None/swappable/dynamic placeholders do not denote donor leaves; unmasked
    secondary layers are cleared except on FancyWater; disabled fallback slots
    cannot block stock composite creation. No source is modified.
    """
    declarations = []
    current, fallback = None, False
    for number, line in enumerate(text.splitlines(), 1):
        tokens = line_tokens(line)
        if not tokens:
            continue
        key = tokens[0].casefold()
        if key in ('texture', 'trick'):
            current, fallback = None, False
            if key == 'texture' and len(tokens) >= 2:
                current = {'name': tokens[1], 'source_path': source_path,
                    'source_line': number, 'edges': [], 'fallback_use': 0,
                    'mask': None, 'objflags': []}
                declarations.append(current)
            continue
        if current is None:
            continue
        if key == 'end':
            if fallback:
                fallback = False
            else:
                current = None
            continue
        if key == 'fallback':
            fallback = True
            continue
        if len(tokens) < 2:
            continue
        if key == 'internalname':
            current['declared_name'] = current['name']
            current['name'] = tokens[1]
        if fallback and key == 'usefallback':
            current['fallback_use'] = int(tokens[1])
        if not fallback and key == 'objflags':
            current['objflags'] = tokens[1:]
        if not fallback and key == 'mask':
            current['mask'] = tokens[1]
        if key in (FALLBACK_SLOTS if fallback else TEXTURE_SLOTS):
            slot = ('Fallback::' if fallback else '') + tokens[0]
            # A repeated native TOK_STRING field replaces its previous value,
            # including a final None that removes an earlier concrete texture.
            current['edges'] = [edge for edge in current['edges']
                if native_slot_key(edge['slot']) != native_slot_key(slot)]
            if valid_texture_name(tokens[1]):
                current['edges'].append({'slot': slot,
                    'alias': tokens[1], 'source_line': number})
    for item in declarations:
        mask = item['mask']
        unmasked = (not valid_texture_name(mask) or mask.casefold() == 'white'
            or mask.casefold().startswith('white.'))
        fancy_water = any(value.casefold() == 'fancywater'
            for value in item['objflags'])
        if unmasked and not fancy_water:
            item['edges'] = [edge for edge in item['edges']
                if edge['slot'].casefold() not in UNMASKED_REMOVED_SLOTS]
        if not item['fallback_use']:
            item['edges'] = [edge for edge in item['edges']
                if not edge['slot'].startswith('Fallback::')]
        item['composite_generation'] = composite_generation_proof(item)
    return declarations


def composite_generation_proof(item):
    """Describe whether stock trickCreateTextures can create this alias."""
    values = {edge['slot'].casefold(): edge['alias'] for edge in item['edges']}
    name = trick_name(item['name'])
    base = values.get('base1')
    if base is None and values.get('blend'):
        # Native old-style Blend setup supplies its postprocessed name as Base1.
        base = name
    matches_base = bool(base and base.casefold().startswith(name.casefold()))
    return {'base1': base, 'base1_exists': base is not None,
        'name_matches_base1_native_prefix_rule': matches_base,
        'composite_alias_can_be_created': bool(base and not matches_base),
        'requires_all_surviving_blend_slots_and_enabled_fallback': True,
        'runtime_rendering_validated': False}


def stock_tricks(root):
    """Return name -> declarations and SHA256/size pins for stock text sources."""
    root = Path(root)
    indexed, sources = defaultdict(list), {}
    directory = root / 'upstream/i24/data/tricks'
    for path in sorted(directory.rglob('*.txt')):
        raw = path.read_bytes()
        if not (0 < len(raw) <= MAX_TRICK_SOURCE_BYTES):
            raise ValueError('Stock trick source exceeds discovery bounds: ' + str(path))
        name = path.relative_to(root).as_posix()
        sources[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        for item in parse_texture_tricks_text(raw.decode('utf-8'), name):
            indexed[trick_name(item['name']).casefold()].append(item)
    return dict(indexed), sources


def matching_tricks(index, name, source_path=None, normalized_key=None):
    key = texture_stem(name) if normalized_key is None else normalized_key
    candidates = index.get(key, [])
    if source_path:
        exact = [item for item in candidates
            if item['source_path'].casefold() == source_path.casefold()]
        if exact:
            candidates = exact
    return candidates


def resolve_trick_closure(index, requests, native_texture_names=None):
    """Expand finite root requests into exact donor-name edges and source proof.

    requests maps already normalized name keys to [{alias,target,scope,...}]
    evidence. Keep raw aliases in evidence: native extension removal is not
    idempotent for original names such as volumemarker._yellow.tga.
    Returned requests retain roots, including aliases absent as native donor
    leaves. A caller must distinguish a proven stock composite from an absent
    donor, and cannot claim device rendering success from this source graph.
    Cycles and ambiguous declarations are reported without guessing. When the
    caller supplies frozen exact donor normalized name keys, native-leaf backedges
    are distinguished from unresolved composite-alias recursion.
    """
    expanded = defaultdict(list)
    for name, reasons in requests.items():
        expanded[name].extend(dict(reason) for reason in reasons)
    definitions, visited, ambiguous, cycles, leaf_backedges = [], set(), [], [], []
    native_names = (None if native_texture_names is None else
        frozenset(native_texture_names))

    def walk(alias, origin, ancestry, normalized_key=None):
        key = texture_stem(alias) if normalized_key is None else normalized_key
        candidates = matching_tricks(index, alias, origin.get('source_path'),
            normalized_key=key)
        if not candidates:
            return
        if len(candidates) != 1:
            ambiguous.append({'alias': alias, 'source_path': origin.get('source_path'),
                'candidates': [{'path': item['source_path'], 'line': item['source_line']}
                    for item in candidates]})
            return
        item = candidates[0]
        identity = item['source_path'], item['source_line']
        if key in ancestry:
            record = {'alias': alias, 'ancestry': list(ancestry),
                'source_path': item['source_path'], 'source_line': item['source_line']}
            if native_names is not None and key in native_names:
                record['exact_donor_leaf_present'] = True
                leaf_backedges.append(record)
            else:
                cycles.append(record)
            return
        if identity in visited:
            return
        visited.add(identity)
        definitions.append(item)
        for edge in item['edges']:
            reason = {'scope': 'stock_material_texture_dependency',
                'target': item['name'], 'alias': edge['alias'], 'slot': edge['slot'],
                'source_path': item['source_path'], 'source_line': edge['source_line'],
                'parent_runtime_target': origin.get('target', origin.get('alias', key))}
            if 'console_line' in origin:
                reason['parent_console_line'] = origin['console_line']
            expanded[texture_stem(edge['alias'])].append(reason)
            walk(edge['alias'], reason, ancestry + (key,))

    for name, reasons in sorted(requests.items()):
        for origin in reasons:
            raw = origin.get('alias', origin.get('target'))
            if raw is None:
                walk(name, origin, (), normalized_key=name)
            else:
                walk(raw, origin, ())
    return {'requests': dict(sorted(expanded.items())),
        'stock_definition_closure': sorted(definitions,
            key=lambda item: (item['source_path'], item['source_line'])),
        'ambiguous_stock_definitions': ambiguous, 'cycles': cycles,
        'native_leaf_backedges': leaf_backedges,
        'runtime_visual_success_claimed': False}
