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


def inventory(path, output, trace=None):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('Missing or oversized game stdio evidence')
    counts = Counter()
    pending = []
    start = re.compile(r'client\.(?:error|fatal)|Assertion failed|assertion failure|ARMPORT_ZONE_LOG_FAILED', re.I)
    isolated = trace is not None
    trace_records = 0
    stdio_error = False
    if isolated:
        if trace.is_symlink() or not trace.is_file() or not 0 < trace.stat().st_size <= 256 * 1024 * 1024:
            raise ValueError('Missing or oversized isolated zone trace')
        with trace.open(encoding='ascii') as stream:
            for line in stream:
                row = json.loads(line)
                if (not line.endswith('\n') or set(row) != {'stage', 'text'}
                        or not all(isinstance(v, str) for v in row.values())):
                    raise ValueError('Malformed isolated zone trace')
                trace_records += 1
                if row['stage'] in ('client.error', 'client.fatal'):
                    counts[row['stage'] + ' ' + row['text']] += 1

    def finish():
        if pending:
            text = ''.join(pending).rstrip()
            text = re.sub(r'.*?ArmPort zone: \d+ ', '', text)
            text = re.sub(r'\s*tid=\d+', '', text).rstrip()
            counts[text] += 1
            pending.clear()

    with path.open(errors='replace') as stream:
        for line in stream:
            if start.search(line):
                # Keep assertion and log-write failures from stdio. Error/fatal
                # grouping comes exclusively from complete isolated records.
                if isolated and re.search(r'client\.(?:error|fatal)', line):
                    stdio_error = True
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
    if isolated and stdio_error and not counts:
        counts['client.error/fatal in stdio without isolated error record'] += 1
    result = dict(count=sum(counts.values()), unique=len(counts),
                  source='isolated-jsonl' if isolated else 'legacy-interleaved-stdio',
                  complete_messages=isolated, trace_records=trace_records,
                  errors=[dict(text=text, count=count) for text, count in sorted(counts.items())])
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result
