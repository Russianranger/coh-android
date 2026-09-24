#!/usr/bin/env python3
"""Run bounded reference data generation in a disposable staged runtime.

Default: template generation only. Use --phase all for templates, server bins,
then client bins. Run directly on Windows, or supply e.g. --runner-json '["wine"]'
under Linux (client binning still needs a display/GL context, such as Xvfb).
Never starts a database or modifies the immutable upstream source snapshots.

Flags/outputs follow the pinned MapServer/src/svr/svr_init.c,
MapServer/src/container/containerloadsave.c, MapServer/src/dbcomm/dbcontainer.c,
Game/src/main.c and Game/src/game.c. Parse6 envelope checks follow
libs/UtilitiesLib/src/utils/{serialize,textparser,structInternals}.c.
Receipts prove bounded generation and output checks, not a complete/playable
installation: the engine can queue nonfatal data errors before early exits.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA_COMMIT = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
TEMPLATES = (
    'testdatabasetypes email ents teamups supergroups taskforces petitions '
    'mapgroups arenaevents arenaplayers baseraids sgraidinfos base '
    'statserver_supergroupstats itemofpowergames itemsofpower offline '
    'miningaccumulator levelingpacts leagues eventhistory autocommands shardaccounts'
).split()
ATTRIBUTES = ('vars badges badgestats pophelp supergroup_badges '
              'supergroup_badgestats').split()
SCHEMAS = [name for name in TEMPLATES if name != 'statserver_supergroupstats']
PHASES = {
    # -templates must be last: source consumes the following argument as a dir.
    'templates': ('MapServer.exe', ['-nogui', '-templates']),
    'server-bins': ('MapServer.exe', ['-nogui', '-createbins']),
    'client-bins': ('CityOfHeroes.exe', ['-createbins', '-nogui', '1', '-console', '1']),
}
CACHE_DIRS = ('data/bin', 'data/server/bin', 'data/geobin')
TRACKED_DIRS = CACHE_DIRS + ('data/server/db/templates', 'data/server/db/schemas')
ERROR_LINE = re.compile(
    r'\b(?:FatalError|fatal error|assertion failed|ParserWriteBinaryFile: could not|'
    r'SerializeWriteOpen: failed)\b|^\s*(?:ERROR|Error):', re.I)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def file_record(path, runtime):
    path, runtime = Path(path), Path(runtime)
    # Check the supplied leaf before resolving it: a symlink output must not be
    # accepted just because its target is inside the runtime. Resolve both sides
    # afterward so Windows short/long aliases share one containment namespace.
    require(not path.is_symlink(), 'Symlink output is not allowed: ' + str(path))
    require(path.is_file(), 'Expected regular file: ' + str(path))
    canonical, runtime = path.resolve(), runtime.resolve()
    require(runtime in canonical.parents, 'Output escaped runtime: ' + str(path))
    stat = canonical.stat()
    return {'path': canonical.relative_to(runtime).as_posix(), 'bytes': stat.st_size,
            'sha256': sha256(canonical), 'mtime_ns': stat.st_mtime_ns}


def output_snapshot(runtime):
    """Track generated areas and dbidmaps, without hashing the entire asset tree."""
    paths = set()
    for relative in TRACKED_DIRS:
        directory = runtime / relative
        require(not directory.is_symlink(), 'Symlink generated directory: ' + str(directory))
        if directory.exists():
            for path in directory.rglob('*'):
                require(not path.is_symlink(), 'Symlink output: ' + str(path))
                if path.is_file():
                    paths.add(path)
    defs = runtime / 'data/defs'
    require(not defs.is_symlink(), 'Symlink definitions directory')
    if defs.is_dir():
        paths.update(defs.rglob('*.dbidmap'))
    result = {}
    for path in sorted(paths):
        record = file_record(path, runtime)
        key = record['path'].casefold()
        require(key not in result, 'Case-colliding generated paths: ' + key)
        result[key] = record
    return result


def changed_outputs(before, after):
    return {name: record for name, record in after.items()
            if name not in before or any(before[name][key] != record[key]
                                        for key in ('bytes', 'sha256', 'mtime_ns'))}


def parse6_envelope(path):
    """Check Files1 and the outer Parse6 body bounds, not schema field semantics."""
    data = path.read_bytes()
    if not data.startswith(b'CrypticS'):
        return {'format': 'other_binary', 'schema_compatibility': 'unverified'}

    def uint(pos):
        require(pos + 4 <= len(data), 'truncated serialized integer')
        return struct.unpack_from('<I', data, pos)[0]

    def pascal(pos):
        require(pos + 2 <= len(data), 'truncated serialized string')
        length, = struct.unpack_from('<H', data, pos)
        end = pos + ((length + 2 + 3) & ~3)
        require(end <= len(data), 'serialized string exceeds file')
        return data[pos + 2:pos + 2 + length], end

    require(len(data) >= 20, 'truncated CrypticS header')
    signature, position = pascal(12)
    require(signature == b'Parse6', 'unexpected serialized signature: ' + repr(signature))
    section, position = pascal(position)
    require(section == b'Files1', 'missing Files1 dependency section')
    block_size = uint(position)
    block_end = position + 4 + block_size
    position += 4
    require(block_end <= len(data), 'dependency block exceeds file')
    count = uint(position)
    position += 4
    require(count <= block_size // 8, 'invalid dependency count')
    for _ in range(count):
        _, position = pascal(position)
        uint(position)
        position += 4
        require(position <= block_end, 'dependency exceeds its block')
    require(position == block_end, 'dependency block length mismatch')
    data_size = uint(position)
    require(position + 4 + data_size == len(data), 'Parse6 data block length mismatch')
    return {'format': 'Parse6', 'schema_crc': f'{uint(8):08x}',
            'dependency_count': count, 'body_bytes': data_size,
            'schema_compatibility': 'unverified'}


def validate_outputs(phase, runtime, before, after, output_text):
    changed = changed_outputs(before, after)
    failures, caches = [], []
    if phase == 'templates':
        expected = [(f'data/server/db/templates/{n}.template', True) for n in TEMPLATES]
        expected += [(f'data/server/db/templates/{n}.attribute', False) for n in ATTRIBUTES]
        expected += [(f'data/server/db/schemas/{n}.schema.html', True) for n in SCHEMAS]
        for relative, nonempty in expected:
            record = after.get(relative)
            if record is None:
                failures.append('missing expected output: ' + relative)
            elif nonempty and not record['bytes']:
                failures.append('empty expected output: ' + relative)
            elif relative not in changed:
                failures.append('expected output was not written during this run: ' + relative)
    else:
        marker = ('Removing old bins..' if phase == 'server-bins'
                  else 'Client binning process complete!')
        if marker not in output_text:
            failures.append('missing source completion marker: ' + marker)
    for name, record in changed.items():
        if name.endswith('.bin') and any(name.startswith(p + '/') for p in CACHE_DIRS):
            try:
                envelope = parse6_envelope(runtime / record['path'])
                caches.append({'path': record['path'], **envelope})
            except (ValueError, struct.error) as error:
                failures.append(record['path'] + ': ' + str(error))
    if phase != 'templates':
        parser_caches = [x for x in caches if x['format'] == 'Parse6']
        if not parser_caches:
            failures.append('no newly written Parse6 cache passed envelope checks')
        if phase == 'server-bins' and not any(
                key.startswith('data/geobin/') and key.endswith('.bin') for key in changed):
            failures.append('server binning wrote no geometry/map bin files')
    error_lines = [line[:1000] for line in output_text.splitlines() if ERROR_LINE.search(line)]
    if error_lines:
        failures.append('explicit failure diagnostics appeared in captured output')
    return {'failures': failures, 'written_outputs': list(changed.values()),
            'removed_outputs': sorted(set(before) - set(after)),
            'cache_envelopes': caches, 'failure_diagnostic_lines': error_lines[:100]}


def terminate_tree(process):
    if os.name == 'nt':
        try:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            # Still kill the direct child and preserve timeout failure evidence.
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def internal_log_snapshot(runtime):
    result = {}
    directory = runtime / 'logs'
    require(not directory.is_symlink(), 'Runtime logs cannot be a symlink')
    if directory.is_dir():
        for path in sorted(directory.rglob('*')):
            require(not path.is_symlink(), 'Runtime log cannot be a symlink')
            if path.is_file():
                record = file_record(path, runtime)
                result[record['path']] = record
    return result


def new_log_text(path, previous):
    """Read appended text, or the whole replacement when a log was overwritten."""
    data = path.read_bytes()
    offset = 0
    if previous and len(data) >= previous['bytes']:
        prefix = data[:previous['bytes']]
        if hashlib.sha256(prefix).hexdigest() == previous['sha256']:
            offset = previous['bytes']
    return data[offset:].decode('utf-8', errors='replace')


def check_runtime(runtime, phases):
    runtime = Path(runtime).resolve()
    require(runtime.is_dir(), 'Runtime directory does not exist')
    require(not (ROOT / 'upstream').resolve() in runtime.parents,
            'Cannot generate inside immutable upstream snapshots')
    require((runtime / 'data').is_dir() and not (runtime / 'data').is_symlink(),
            'Runtime needs a regular staged data directory')
    inputs_path = runtime / 'runtime-inputs.json'
    require(inputs_path.is_file() and not inputs_path.is_symlink(),
            'Missing staged runtime-inputs.json')
    inputs = json.loads(inputs_path.read_text(encoding='utf-8'))
    require(inputs.get('source_commit') == SOURCE_COMMIT, 'Wrong source commit in runtime manifest')
    require(inputs.get('data_commit') == DATA_COMMIT, 'Wrong text-data commit in runtime manifest')
    hashes = inputs.get('build_file_sha256', {})
    for phase in phases:
        name = PHASES[phase][0]
        executable = runtime / name
        require(executable.is_file() and not executable.is_symlink(), 'Missing phase executable: ' + name)
        require(hashes.get(name) == sha256(executable), 'Executable SHA-256 does not match staging receipt: ' + name)
    require(not (runtime / 'gamedatadir.txt').exists(),
            'External data roots via gamedatadir.txt are not supported; use isolated runtime/data')
    return inputs


def run_generation(runtime, output, phases=('templates',), runner=(), timeout=600):
    runtime, output = Path(runtime).resolve(), Path(output).resolve()
    require(0 < timeout <= 86400, 'Timeout must be in (0,86400] seconds')
    require(phases and all(p in PHASES for p in phases), 'Unknown generation phase')
    require(isinstance(runner, (list, tuple)) and all(isinstance(x, str) and x for x in runner),
            'Runner must be a JSON array of nonempty strings')
    require(not output.exists(), 'Evidence output must be a new directory')
    require(output != runtime and runtime / 'data' not in output.parents,
            'Evidence output cannot be runtime root or inside data')
    inputs = check_runtime(runtime, phases)
    output.mkdir(parents=True)
    report = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'generation_failed', 'source_commit': SOURCE_COMMIT, 'data_commit': DATA_COMMIT,
        'runtime': str(runtime), 'runtime_inputs_sha256': sha256(runtime / 'runtime-inputs.json'),
        'gameplay_validated': False, 'database_started': False,
        'nonfatal_queued_errors_reviewed': False,
        'scope': 'process completion, fresh output receipts and Parse6 outer envelopes; '
                 'not complete data semantics, schema compatibility, or gameplay validation',
        'phases': [],
    }
    for phase in phases:
        phase_output = output / phase
        phase_output.mkdir()
        before = output_snapshot(runtime)
        before_logs = internal_log_snapshot(runtime)
        exe, flags = PHASES[phase]
        # Relative .exe is recognized by Wine and by native Windows with cwd set.
        command = list(runner) + ([exe] if runner else [str(runtime / exe)]) + flags
        stdout_path, stderr_path = phase_output / 'stdout.log', phase_output / 'stderr.log'
        record = {'phase': phase, 'command': command, 'timeout_seconds': timeout,
                  'executable_sha256': inputs['build_file_sha256'][exe],
                  'status': 'failed', 'timed_out': False}
        start = time.monotonic()
        with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
            try:
                options = {'cwd': runtime, 'stdout': stdout, 'stderr': stderr,
                           'stdin': subprocess.DEVNULL, 'shell': False}
                if os.name == 'nt':
                    options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
                else:
                    options['start_new_session'] = True
                process = subprocess.Popen(command, **options)
                try:
                    record['exit_code'] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    record['timed_out'] = True
                    terminate_tree(process)
                    record['exit_code'] = process.returncode
            except OSError as error:
                record['launch_error'] = str(error)
                record['exit_code'] = None
        record['elapsed_seconds'] = round(time.monotonic() - start, 3)
        output_text = stdout_path.read_text(encoding='utf-8', errors='replace') + '\n' + (
            stderr_path.read_text(encoding='utf-8', errors='replace'))
        after_logs = internal_log_snapshot(runtime)
        record['internal_logs'] = []
        for relative, log_record in changed_outputs(before_logs, after_logs).items():
            source = runtime / relative
            destination = phase_output / 'internal' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            record['internal_logs'].append(log_record)
            output_text += '\n' + new_log_text(source, before_logs.get(relative))
        after = output_snapshot(runtime)
        record.update(validate_outputs(phase, runtime, before, after, output_text))
        if record['timed_out']:
            record['failures'].insert(0, 'generation exceeded timeout; process tree terminated')
        elif record['exit_code'] != 0:
            record['failures'].insert(0, 'generation process did not exit successfully')
        if not record['failures']:
            record['status'] = 'output_checks_passed_runtime_unvalidated'
        record['stdout_sha256'], record['stderr_sha256'] = sha256(stdout_path), sha256(stderr_path)
        report['phases'].append(record)
        (output / 'generation-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if record['failures']:
            break
    if len(report['phases']) == len(phases) and all(not p['failures'] for p in report['phases']):
        report['status'] = 'output_checks_passed_runtime_unvalidated'
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (output / 'generation-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New directory for evidence')
    parser.add_argument('--phase', choices=tuple(PHASES) + ('all',), default='templates')
    parser.add_argument('--runner-json', default='[]', help='Command prefix JSON, e.g. ["wine"]')
    parser.add_argument('--timeout-seconds', type=float, default=600)
    args = parser.parse_args()
    phases = tuple(PHASES) if args.phase == 'all' else (args.phase,)
    try:
        report = run_generation(args.runtime, args.output, phases,
                                json.loads(args.runner_json), args.timeout_seconds)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(report['status'] + ': ' + str(args.output / 'generation-report.json'))
    return 0 if report['status'] == 'output_checks_passed_runtime_unvalidated' else 1


if __name__ == '__main__':
    sys.exit(main())
