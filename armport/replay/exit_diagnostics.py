"""Bounded failure evidence; never changes replay acceptance."""
import json
import re


def collect(folder):
    result = dict(terminal_receiver=None, terminal_zone=None, cleanup_begin=False,
                  exit_begin=False, receiver_failure=None, client_failure=None,
                  wine_exception=None, failed_inventory=None, read_errors=[])
    for name, key in (('receiver.jsonl', 'terminal_receiver'), ('zone-trace.jsonl', 'terminal_zone')):
        try:
            with (folder / name).open(encoding='utf-8') as source:
                for number, line in enumerate(source, 1):
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict) or not line.endswith('\n'):
                            raise ValueError('incomplete/non-object row')
                        # Keep notices bounded even if a failure text is oversized.
                        result[key] = {k: v[:500] if isinstance(v, str) else v
                                       for k, v in row.items() if k in
                                       ('type', 'stage', 'text', 'index', 'id', 'command',
                                        'cursor', 'error_flags', 'reason', 'message')}
                        if row.get('type') in ('failure', 'unknown_command'):
                            result['receiver_failure'] = result[key]
                        if row.get('stage') == 'replay.cleanup.begin':
                            result['cleanup_begin'] = True
                        if row.get('stage') == 'replay.exit.begin':
                            result['exit_begin'] = True
                        if row.get('stage') == 'client.fatal':
                            result['client_failure'] = result[key]
                    except ValueError:
                        if len(result['read_errors']) < 8:
                            result['read_errors'].append(f'{name}:{number}: malformed row')
        except (OSError, UnicodeError) as error:
            result['read_errors'].append(f'{name}: {error}')
    patterns = (
        ('client-stdio.txt', 'client_failure', r'Exception caught:|Program crash detected|ArmPort replay state failed|assertion failed|fatal error'),
        ('wine-output.txt', 'wine_exception', r'dispatch_exception code=|:err:seh:|unhandled (?:exception|page fault)'),
    )
    for name, key, pattern in patterns:
        try:
            with (folder / name).open(errors='replace') as source:
                for number, line in enumerate(source, 1):
                    if re.search(pattern, line, re.I):
                        result[key] = dict(line=number, text=line.strip()[:500])
        except OSError as error:
            result['read_errors'].append(f'{name}: {error}')
    try:
        with (folder / 'failed-exit-inventory.txt').open(errors='replace') as source:
            result['failed_inventory'] = source.read(2000).strip()
    except OSError as error:
        result['read_errors'].append(str(error))
    return result
