"""Inventory isolated full messages; legacy stdio grouping is diagnostic only."""
from collections import Counter
import json
import hashlib
import re


def geometry_paths(text):
    return sorted({name.lower() for name in re.findall(
        r'\b((?:player_library|object_library)/[^\s\'"!?]+\.geo)\b', text, re.I)})


def geometry_lookup(errors, data):
    """Observe actual staged files; a missing model is not a missing file."""
    requested = {name for error in errors['errors'] for name in geometry_paths(error['text'])}
    result = {name: [] for name in sorted(requested)}
    for path in sorted(data.rglob('*')):
        name = path.relative_to(data).as_posix().casefold()
        if name in requested and path.is_file():
            with path.open('rb') as stream:
                sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            result[name].append(dict(path=path.relative_to(data).as_posix(),
                                     bytes=path.stat().st_size, sha256=sha))
    return result



def texture_names(text):
    patterns = (r"Player texture \d+ '([^']+)'", r'nonexistent texture (\S+)',
                r'references missing texture "([^"]+)"',
                r'referencing missing \S+ texture (\S+)')
    names = {name for pattern in patterns for name in re.findall(pattern, text, re.I)}
    if 'TexSwap' in text:
        names.update(re.findall(r"(?:texture|swap with) '([^']+)'", text))
    return sorted({re.sub(r'\.(?:tga|texture|dds)$', '', name.casefold()) for name in names})


def group_references(text):
    patterns = (r'Deleted reference ([^\r\n]+)', r"can't find member ([^\r\n]+)",
                r'Cant find root geo ([^\r\n]+)')
    return sorted({name.casefold() for pattern in patterns for name in re.findall(pattern, text, re.I)})


def error_class(text):
    for needle, name in (('Deleted reference ', 'deleted_group_reference'),
                         ("can't find member ", 'missing_group_member'),
                         ('Cant find root geo ', 'missing_root_geometry'),
                         ('CUSTOM TEXTURE ERROR:', 'custom_texture'),
                         ('Player texture ', 'player_texture'),
                         ('Texture Trick ', 'texture_trick'),
                         ('Material trick ', 'material_texture'),
                         ('TexSwap', 'texture_swap'),
                         ('.geo', 'geometry_file_or_model'),
                         ("Couldn't start DirectSound", 'audio_unavailable'),
                         ('No loading screen match', 'loading_screen'),
                         ('ParserLoadFiles:', 'parser_input'),
                         ("Room -1 marker isn't in a room", 'mission_room')):
        if needle in text:
            return name
    return 'unclassified'



def group_definition_lookup(names, data):
    """Observe loose source declarations; do not claim runtime load/model success.

    Public lookup follows groupNameIdx's basename and __ suffix handling.
    As loadGroupNames does, ignore private & definitions and underscore paths.
    A .rootnames declaration names geometry; a .txt group may be composite.
    """
    from pathlib import Path
    requested = {}
    for name in names:
        public = name.rsplit('/', 1)[-1].split('__', 1)[0].casefold()
        requested.setdefault(public, []).append(name)
    result = {name: [] for name in sorted(names)}
    geometry_info = {}
    root = data / 'object_library'
    actual = {p.relative_to(data).as_posix().casefold(): p for p in root.rglob('*') if p.is_file()}
    for relative, path in sorted(actual.items()):
        if path.suffix.casefold() not in ('.txt', '.rootnames') or any(
                part.startswith('_') for part in path.relative_to(root).parts):
            continue
        # The repository group loader tokenizes one Def/name declaration per line.
        for number, line in enumerate(path.read_text(encoding='latin-1').splitlines(), 1):
            found = re.fullmatch(r'\s*Def\s+(?:"([^"]+)"|([^\s]+))\s*(?://.*)?', line, re.I)
            if not found:
                continue
            public = (found[1] or found[2]).casefold()
            if public.endswith('&') or public not in requested:
                continue
            entry = dict(path=path.relative_to(data).as_posix(), line=number,
                         declaration=found[1] or found[2], kind=path.suffix.casefold()[1:])
            if path.suffix.casefold() == '.rootnames':
                geo = str(Path(relative).with_suffix('.geo')).replace('\\', '/')
                actual_geo = actual.get(geo)
                entry['geometry_path'] = geo
                entry['geometry_present'] = actual_geo is not None
                if actual_geo:
                    if geo not in geometry_info:
                        with actual_geo.open('rb') as stream:
                            sha = hashlib.file_digest(stream, 'sha256').hexdigest()
                        geometry_info[geo] = dict(geometry_sha256=sha, geometry_bytes=actual_geo.stat().st_size)
                    entry.update(geometry_info[geo])
            for name in requested[public]:
                result[name].append(entry)
    return result


def asset_lookup(errors, data):
    """Resolve named textures against staged files, without fetching any assets.

    Group names are symbolic references, not file paths. Retain them separately;
    an absent definition/model cannot be inferred from an absent loose filename.
    """
    requested = {name for error in errors['errors'] for name in texture_names(error['text'])}
    textures = {name: [] for name in sorted(requested)}
    for path in sorted((data / 'texture_library').rglob('*')):
        if path.is_file() and path.suffix.casefold() == '.texture':
            relative = path.relative_to(data).as_posix()
            keys = {path.stem.casefold(), path.relative_to(data / 'texture_library').with_suffix('').as_posix().casefold()}
            for name in keys & requested:
                with path.open('rb') as stream:
                    sha = hashlib.file_digest(stream, 'sha256').hexdigest()
                textures[name].append(dict(path=relative, bytes=path.stat().st_size, sha256=sha))
    classes, references = Counter(), Counter()
    for error in errors['errors']:
        classes[error_class(error['text'])] += error['count']
        for name in group_references(error['text']):
            references[name] += error['count']
    phases = Counter()
    for error in errors['phase_errors']:
        phases[(error['phase'], error_class(error['text']))] += error['count']
    return dict(textures=textures, group_references=dict(sorted(references.items())),
                group_definitions=group_definition_lookup(references, data),
                group_reference_scope='symbolic; file absence not inferred',
                classes=dict(sorted(classes.items())),
                phase_classes=[dict(phase=phase, error_class=kind, count=count)
                               for (phase, kind), count in sorted(phases.items())])

def inventory(path, output, trace=None, expected_dispatches=None):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('Missing or oversized game stdio evidence')
    counts, phases, isolated_markers, stdio_markers = Counter(), Counter(), Counter(), Counter()
    pending, failures = [], []
    thread_errors = Counter()
    replay_started = draining = drained = False
    drain_windows = 0
    map_windows = map_drain_windows = 0
    map_draining = False
    start = re.compile(r'client\.(?:error|fatal)|Assertion failed|assertion failure|ARMPORT_ZONE_LOG_FAILED', re.I)
    marker = re.compile(r'ArmPort zone: \d+ (client\.(?:error|fatal))\b')
    isolated = trace is not None
    trace_records = dispatches = 0
    active = None
    phase = 'startup'
    map_active = False
    map_finished = False
    if isolated:
        if trace.is_symlink() or not trace.is_file() or not 0 < trace.stat().st_size <= 256 * 1024 * 1024:
            raise ValueError('Missing or oversized isolated zone trace')
        with trace.open(encoding='ascii') as stream:
            for line in stream:
                row = json.loads(line)
                if (not line.endswith('\n') or set(row) not in ({'stage', 'text'}, {'stage', 'text', 'tid'})
                        or not isinstance(row.get('stage'), str) or not isinstance(row.get('text'), str)
                        or ('tid' in row and (type(row['tid']) is not int or not 0 < row['tid'] <= 0xffffffff))):
                    raise ValueError('Malformed isolated zone trace')
                if expected_dispatches is not None and 'tid' not in row:
                    failures.append('Missing isolated writer thread ID')
                trace_records += 1
                stage, text = row['stage'], row['text']
                if stage == 'replay.map.begin':
                    if map_active or active is not None or replay_started or map_windows:
                        failures.append('Nested map-load boundary')
                    map_active, phase = True, 'map_load'
                elif stage == 'replay.map.drain.begin':
                    if not map_active or map_draining or map_drain_windows or replay_started:
                        failures.append('Invalid map-load drain begin')
                    map_draining = True
                elif stage == 'replay.map.drain.end':
                    if not map_active or not map_draining or replay_started:
                        failures.append('Unpaired map-load drain end')
                    map_draining = False
                    map_drain_windows += 1
                elif stage == 'replay.map.end':
                    if (not map_active or active is not None or map_draining
                            or expected_dispatches is not None and map_drain_windows != 1):
                        failures.append('Unpaired map-load boundary')
                    map_active, phase = False, 'outside_dispatch'
                    map_windows += 1
                elif stage == 'replay.dispatch.begin':
                    if active is not None or text != str(dispatches) or map_active or draining or drained:
                        failures.append('Missing, nested or out-of-order dispatch begin: ' + text)
                    if expected_dispatches is not None and (map_windows != 1 or map_drain_windows != 1):
                        failures.append('Dispatch before completed map-load drain')
                    active = text
                    replay_started = True
                elif stage == 'replay.dispatch.end':
                    if active is None or text != active or text != str(dispatches):
                        failures.append('Unpaired or out-of-order dispatch end: ' + text)
                    active = None
                    dispatches += 1
                elif stage == 'replay.drain.begin':
                    if (not replay_started or active is not None or map_active or draining or drained
                            or text != str(dispatches)
                            or (expected_dispatches is not None and dispatches != expected_dispatches)):
                        failures.append('Missing, nested or out-of-order loader drain begin')
                    draining = True
                elif stage == 'replay.drain.end':
                    if not draining or active is not None or text != str(dispatches):
                        failures.append('Unpaired loader drain end')
                    draining, drained = False, True
                    drain_windows += 1
                elif stage in ('map.start', 'group.load.begin'):
                    phase = 'map_load'
                elif stage == 'map.finish.done':
                    map_finished = True
                    phase = 'after_map_load'
                if stage in ('client.error', 'client.fatal'):
                    key = stage + ' ' + text
                    counts[key] += 1
                    # Include inter-dispatch gaps: background errors cannot escape
                    # the dispatch rule simply by landing between two markers.
                    phases[('dispatch' if active is not None or (replay_started and not drained) else phase, key)] += 1
                    thread_errors[row.get('tid', 0)] += 1
                    isolated_markers[stage] += 1
                    if stage == 'client.fatal':
                        failures.append('Game fatal in isolated trace')
        if active is not None or map_active:
            failures.append('Unclosed dispatch or map-load boundary')
        if expected_dispatches is not None and dispatches != expected_dispatches:
            failures.append(f'Expected {expected_dispatches} paired dispatch windows, got {dispatches}')
        if draining or (expected_dispatches is not None and (not drained or drain_windows != 1)):
            failures.append('Missing or unclosed final loader drain window')
        if map_draining or (expected_dispatches is not None and (map_windows != 1 or map_drain_windows != 1)):
            failures.append('Missing or unclosed map-load drain window')

    def finish():
        if pending:
            text = ''.join(pending).rstrip()
            text = re.sub(r'.*?ArmPort zone: \d+ ', '', text)
            text = re.sub(r'\s*tid=\d+', '', text).rstrip()
            counts[text] += 1
            phases[('unlocated_stdio', text)] += 1
            if isolated:
                failures.append('Game assertion or log-write failure in stdio')
            pending.clear()

    with path.open(errors='replace') as stream:
        for line in stream:
            markers = marker.findall(line)
            stdio_markers.update(markers)
            if start.search(line):
                # Fragmented stdout cannot provide complete error text. Count its
                # actual zone markers independently to detect partial trace loss.
                if isolated and markers and not re.search(
                        r'Assertion failed|assertion failure|ARMPORT_ZONE_LOG_FAILED', line, re.I):
                    finish()
                    continue
                finish()
                pending.append(line)
            elif pending:
                if 'ArmPort zone: ' in line:
                    finish()
                else:
                    pending.append(line)
            if pending and re.search(r' tid=\d+\s*$', line):
                finish()
        finish()
    if isolated and stdio_markers != isolated_markers:
        failures.append('Game error/assert: stdio and isolated error/fatal marker counts differ')
    rows = lambda counter: [dict(text=text, count=count) for text, count in sorted(counter.items())]
    outside = Counter()
    for (where, text), count in phases.items():
        if where != 'dispatch':
            outside[text] += count
    result = dict(count=sum(counts.values()), unique=len(counts),
                  source='isolated-jsonl' if isolated else 'legacy-interleaved-stdio',
                  complete_messages=isolated, trace_records=trace_records,
                  phase_counts={where: sum(n for (phase, _), n in phases.items() if phase == where)
                                for where in sorted({phase for phase, _ in phases})},
                  map_load_finished=map_finished,
                  dispatch_windows=dispatches,
                  loader_drain_windows=drain_windows,
                  map_loader_drain_windows=map_drain_windows,
                  error_writer_threads=dict(sorted(thread_errors.items())),
                  dispatch_error_count=sum(n for (where, _), n in phases.items() if where == 'dispatch'),
                  integrity_failures=sorted(set(failures)),
                  stdio_markers=dict(stdio_markers), isolated_markers=dict(isolated_markers),
                  outside_errors=rows(outside),
                  phase_errors=[dict(phase=where, text=text, count=count)
                                for (where, text), count in sorted(phases.items())],
                  errors=rows(counts))
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result
