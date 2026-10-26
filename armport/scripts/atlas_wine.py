"""Atlas-only startup RPC exception accounting; replay remains strict.

The map witness is appended by the client to the same file descriptor stream
as Wine's traces, before the isolated map.start record. No cross-file clock or
line-number inference is used. A 6ba dispatch must unwind and restore its
handler's target on the same thread before this witness.
"""
import json
import re

BOUNDARY = 'ARMPORT_ATLAS_MAP_START_V1'
FATAL = re.compile(
    r':err:seh:|unhandled (?:exception|page fault)|'
    r'wine(?: client| server)?:[^\n]*(?:fatal|could not load|failed to|unimplemented function)|'
    r'wine (?:client|server) error:|'
    r':err:module:(?:import_dll|LdrInitializeThunk)', re.I)
DISPATCH = re.compile(r'^([0-9a-f]+):trace:seh:dispatch_exception code=0*6ba '
                      r'\(RPC_S_SERVER_UNAVAILABLE\) flags=0 addr=[0-9a-f]+$', re.I)
UNWIND = re.compile(r'^([0-9a-f]+):trace:seh:RtlUnwindEx code=0*6ba flags=2 '
                    r'end_frame=([0-9a-f]+) target_ip=([0-9a-f]+)$', re.I)
RESTORE = re.compile(r'^([0-9a-f]+):trace:seh:RtlRestoreContext returning to '
                     r'([0-9a-f]+) stack [0-9a-f]+$', re.I)
CODE = re.compile(r'(?:dispatch_exception|raise_exception|RtlUnwindEx)\s+code=', re.I)


def inventory(wine, trace):
    if (wine.is_symlink() or not wine.is_file() or wine.stat().st_size > 64 * 1024**2
            or trace.is_symlink() or not trace.is_file() or not 0 < trace.stat().st_size <= 256 * 1024**2):
        raise ValueError('Missing or oversized Atlas Wine/boundary evidence')
    with trace.open(encoding='ascii') as stream:
        isolated_count = sum(json.loads(line).get('stage') == 'map.start' for line in stream)
    failures, pending, count, boundaries = [], {}, 0, 0
    with wine.open(errors='replace') as stream:
        for number, raw in enumerate(stream, 1):
            line = raw.rstrip('\r\n')
            if BOUNDARY in line:
                if line != BOUNDARY or not raw.endswith('\n') or pending:
                    failures.append(f'Invalid map boundary or unfinished RPC at line {number}')
                boundaries += 1
            if FATAL.search(line):
                failures.append(f'Wine fatal at line {number}: {line[:300]}')
            dispatch, unwind, restore = DISPATCH.fullmatch(line), UNWIND.fullmatch(line), RESTORE.fullmatch(line)
            if dispatch:
                tid = int(dispatch[1], 16)
                if boundaries or tid in pending:
                    failures.append(f'RPC dispatch after map.start or nested at line {number}')
                pending[tid] = None
            elif unwind:
                tid, frame, target = (int(x, 16) for x in unwind.groups())
                if boundaries or tid not in pending or pending[tid] is not None or not frame or not target:
                    failures.append(f'Unpaired/late RPC unwind at line {number}')
                pending[tid] = target
            elif CODE.search(line):
                failures.append(f'Unapproved Wine exception at line {number}: {line[:300]}')
            elif restore:
                tid, target = int(restore[1], 16), int(restore[2], 16)
                if tid in pending and pending[tid] == target and not boundaries:
                    del pending[tid]
                    count += 1
                else:
                    failures.append(f'Unpaired exception restore at line {number}')
    if pending:
        failures.append('Startup RPC lacks matching handler restoration')
    if not boundaries or boundaries != isolated_count:
        failures.append('Wine map boundary count differs from isolated map.start or is absent')
    return dict(allowed_startup_rpc_exceptions=count, map_boundaries=boundaries,
                isolated_map_starts=isolated_count, failures=failures, passed=not failures)
