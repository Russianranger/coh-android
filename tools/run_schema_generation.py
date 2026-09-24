#!/usr/bin/env python3
"""Run the separately patched, asset-free database schema generator on Windows.

This consumes a text-only prepared runtime plus the schema-build MapServer/DLLs.
It does not turn that build into a gameplay runtime, start a database, or claim
serializer equivalence. Only fresh schema/template/dbidmap outputs are archived;
incidental caches from this deliberately restricted mode must not enter gameplay.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import zipfile

import generate_runtime_data as generation
from package_reference_runtime import pe_info
from prepare_runtime import input_files
from prepare_schema_source import expected_schema_receipt

ROOT = Path(__file__).resolve().parents[1]
SUCCESS = 'schema_data_only_outputs_checked_runtime_unvalidated'
COMPLETION = 'COH_DB_TEMPLATES_ONLY_WRITTEN'
LOG_LIMIT = 16 * 1024 * 1024  # Per stream/internal log; overflow fails the evidence gate.
WARNING = re.compile(r'\b(?:warn(?:ing)?|queued errors?)\b', re.I)


def require(value, message):
    if not value:
        raise ValueError(message)


def check_inputs(runtime, build_input, executable_sha256, root):
    require(runtime.is_dir() and not runtime.is_symlink(), 'Runtime must be a real staged directory')
    runtime = runtime.resolve()
    require(runtime != (root / 'upstream').resolve() and (root / 'upstream').resolve() not in runtime.parents,
            'Cannot generate inside immutable upstream snapshots')
    # Inspect the whole namespace before execution: even an empty symlinked output
    # directory could redirect writes before output_snapshot has a file to check.
    for _ in input_files(runtime):
        pass
    require(not (runtime / 'gamedatadir.txt').exists(), 'External gamedatadir.txt roots are not supported')
    require(not (runtime / '.runtime-staging-incomplete').exists(), 'Runtime staging is incomplete')
    inputs_path = runtime / 'runtime-inputs.json'
    require(inputs_path.is_file(), 'Missing staged runtime-inputs.json')
    inputs = json.loads(inputs_path.read_text(encoding='utf-8'))
    require(inputs.get('source_commit') == generation.SOURCE_COMMIT, 'Wrong staged source commit')
    require(inputs.get('data_commit') == generation.DATA_COMMIT, 'Wrong staged text-data commit')
    require(inputs.get('executables_supplied') is False and not inputs.get('build_file_sha256'),
            'Use a text-only staged runtime, then copy the separate schema-build executables; '
            'do not change the gameplay build manifest')
    require(inputs.get('binary_assets_supplied') is False, 'Schema-only generation expects a text-only runtime')
    require((runtime / 'data').is_dir(), 'Missing staged data directory')
    require(build_input.is_file() and not build_input.is_symlink(), 'Missing schema-build source receipt')
    receipt = json.loads(build_input.read_text(encoding='utf-8'))
    require(receipt == expected_schema_receipt(root, postgresql_build_input=receipt.get('postgresql_build_input')),
            'Schema-build source receipt differs from the pinned PostgreSQL/source/schema patch inputs')
    require(re.fullmatch(r'[0-9a-f]{64}', executable_sha256), 'Expected full MapServer SHA-256')
    executable = runtime / 'MapServer.exe'
    require(executable.is_file() and not executable.is_symlink(), 'Missing schema-build MapServer.exe')
    require(generation.sha256(executable) == executable_sha256, 'Schema MapServer executable SHA-256 mismatch')
    executable_info = pe_info(executable.read_bytes())
    dlls = {p.name: {'bytes': p.stat().st_size, 'sha256': generation.sha256(p)}
            for p in sorted(runtime.iterdir()) if p.is_file() and p.suffix.casefold() == '.dll'}
    return inputs, receipt, executable_info, dlls


def bounded_process(command, runtime, stdout_path, stderr_path, timeout, log_limit=LOG_LIMIT):
    """Drain pipes concurrently, keep bounded logs, kill the tree on overflow/time."""
    overflow = threading.Event()
    capture_errors = []
    record = {'exit_code': None, 'timed_out': False, 'log_limit_exceeded': False,
              'log_limit_bytes_per_stream': log_limit}
    start = time.monotonic()
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        options = {'cwd': runtime, 'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE,
                   'stdin': subprocess.DEVNULL, 'shell': False}
        if os.name == 'nt':
            options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options['start_new_session'] = True
        try:
            process = subprocess.Popen(command, **options)
        except OSError as error:
            record['launch_error'] = str(error)
            record['elapsed_seconds'] = round(time.monotonic() - start, 3)
            return record

        def drain(stream, destination):
            remaining = log_limit
            try:
                while True:
                    block = stream.read1(65536)
                    if not block:
                        break
                    kept = block[:remaining]
                    destination.write(kept)
                    remaining -= len(kept)
                    if len(kept) != len(block):
                        overflow.set()
            except (OSError, ValueError) as error:
                capture_errors.append(str(error))
                overflow.set()
            finally:
                stream.close()

        threads = [threading.Thread(target=drain, args=(process.stdout, stdout), daemon=True),
                   threading.Thread(target=drain, args=(process.stderr, stderr), daemon=True)]
        for thread in threads:
            thread.start()
        while process.poll() is None:
            if overflow.is_set() or time.monotonic() - start >= timeout:
                record['timed_out'] = not overflow.is_set()
                generation.terminate_tree(process)
                break
            try:
                process.wait(timeout=min(0.1, max(0.01, timeout - (time.monotonic() - start))))
            except subprocess.TimeoutExpired:
                pass
        for thread in threads:
            thread.join(timeout=10)
        record['exit_code'] = process.returncode
        record['log_limit_exceeded'] = overflow.is_set()
        if any(thread.is_alive() for thread in threads):
            record['capture_error'] = 'Log pipes did not close after the process exited'
        elif capture_errors:
            record['capture_error'] = '; '.join(capture_errors)
    record['elapsed_seconds'] = round(time.monotonic() - start, 3)
    return record


def archive_schema_outputs(runtime, output, records):
    runtime = Path(runtime).resolve()
    archive_path = output / 'schema-outputs.zip'
    partial = output / 'schema-outputs.zip.partial'
    archived = []
    try:
        with zipfile.ZipFile(partial, 'x', zipfile.ZIP_DEFLATED) as archive:
            for record in records:
                relative = record['path']
                lower = relative.casefold()
                eligible = (lower.startswith(('data/server/db/templates/', 'data/server/db/schemas/')) or
                            (lower.startswith('data/defs/') and lower.endswith('.dbidmap')))
                if not eligible:
                    continue
                path = runtime / relative
                require(path.is_file() and not path.is_symlink() and runtime in path.resolve().parents,
                        'Unsafe schema output: ' + relative)
                require(generation.sha256(path) == record['sha256'], 'Schema output changed before archiving: ' + relative)
                archive.write(path, relative)
                archived.append(record)
        partial.replace(archive_path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return {'path': archive_path.name, 'bytes': archive_path.stat().st_size,
            'sha256': generation.sha256(archive_path), 'files': archived}


def run_schema_generation(runtime, build_input, executable_sha256, output, timeout=900,
                          root=ROOT, runner=(), log_limit=LOG_LIMIT):
    # runner is used only by synthetic subprocess tests; the CLI executes the
    # Windows build directly and never substitutes a gameplay executable.
    runtime, output = Path(runtime), Path(output)
    require(not runtime.is_symlink(), 'Runtime must not be a symlink')
    runtime = runtime.resolve()
    require(not output.exists() and not output.is_symlink(), 'Evidence output must be a new directory')
    output = output.resolve()
    require(runtime != output and runtime not in output.parents,
            'Evidence must be outside the disposable runtime')
    require(output != (root / 'upstream').resolve() and (root / 'upstream').resolve() not in output.parents,
            'Evidence must be outside immutable upstream snapshots')
    require(0 < timeout <= 86400 and 0 < log_limit <= LOG_LIMIT, 'Invalid process/log bound')
    inputs, receipt, executable_info, dlls = check_inputs(runtime, Path(build_input), executable_sha256, root)
    before = generation.output_snapshot(runtime)
    before_logs = generation.internal_log_snapshot(runtime)
    output.mkdir(parents=True)
    command = list(runner) + [str(runtime / 'MapServer.exe'), '-nogui', '-dbtemplatesonly']
    report = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'schema_data_only_generation_failed',
        'build_role': 'data_only_db_schema_generation',
        'source_commit': inputs['source_commit'], 'data_commit': inputs['data_commit'],
        'schema_build_input': receipt, 'schema_build_input_sha256': generation.sha256(Path(build_input)),
        'runtime_inputs_sha256': generation.sha256(runtime / 'runtime-inputs.json'),
        'executable_sha256': executable_sha256, 'executable_pe': executable_info,
        'dependent_dll_files': dlls, 'command': command, 'timeout_seconds': timeout,
        'gameplay_validated': False, 'database_started': False,
        'serializer_equivalence': 'unverified', 'nonfatal_queued_errors_reviewed': False,
        'scope': 'separately patched asset-free schema generation; freshness and Parse6 envelope checks only',
        'incidental_cache_policy': 'not reusable by gameplay and excluded from schema-outputs.zip',
    }
    stdout_path, stderr_path = output / 'stdout.log', output / 'stderr.log'
    report.update(bounded_process(command, runtime, stdout_path, stderr_path, timeout, log_limit))
    text = stdout_path.read_text(encoding='utf-8', errors='replace') + '\n' + stderr_path.read_text(encoding='utf-8', errors='replace')
    failures, internal_records = [], []
    try:
        after_logs = generation.internal_log_snapshot(runtime)
        for relative, record in generation.changed_outputs(before_logs, after_logs).items():
            source = runtime / relative
            destination = output / 'internal' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Copy only a bounded prefix, recording overflow as failure; full
            # diagnostics remain in the disposable runtime for investigation.
            with source.open('rb') as stream, destination.open('wb') as target:
                data = stream.read(log_limit + 1)
                target.write(data[:log_limit])
            if len(data) > log_limit:
                failures.append('internal log exceeded capture bound: ' + relative)
                text += '\n' + data[:log_limit].decode('utf-8', errors='replace')
            else:
                text += '\n' + generation.new_log_text(source, before_logs.get(relative))
            internal_records.append({**record, 'captured_bytes': min(len(data), log_limit),
                                     'capture_sha256': generation.sha256(destination)})
        after = generation.output_snapshot(runtime)
        report.update(generation.validate_outputs('templates', runtime, before, after, text))
        failures.extend(report['failures'])
    except (OSError, ValueError) as error:
        failures.append('Output inspection failed: ' + str(error))
    report['internal_logs'] = internal_records
    completion = [re.fullmatch(re.escape(COMPLETION) + r' queued_errors=(\d+)', line.strip())
                  for line in text.splitlines()]
    queued = [int(match.group(1)) for match in completion if match]
    report['completion_marker_seen'] = bool(queued)
    report['queued_error_counts'] = queued
    report['schema_diagnostic_lines'] = [line[:2000] for line in text.splitlines()
                                         if 'COH_DB_TEMPLATES_ONLY_DIAGNOSTIC:' in line]
    if not queued:
        failures.append('missing schema-only completion marker: ' + COMPLETION)
    elif any(queued):
        failures.append('schema-only generation reported queued data errors')
    if report['timed_out']:
        failures.append('schema generation exceeded timeout; process tree terminated')
    if report['log_limit_exceeded']:
        failures.append('process output exceeded capture bound; process tree terminated if running')
    if report.get('capture_error'):
        failures.append('Process output capture failed: ' + report['capture_error'])
    if report['exit_code'] != 0:
        failures.append('schema-generation process did not exit successfully')
    warnings = [line[:2000] for line in text.splitlines() if WARNING.search(line)]
    report['warning_line_count'] = len(warnings)
    report['warning_lines'] = warnings[:1000]
    report['warning_summary_truncated'] = len(warnings) > 1000
    report['stdout_sha256'], report['stderr_sha256'] = generation.sha256(stdout_path), generation.sha256(stderr_path)
    if not failures:
        try:
            report['schema_outputs_archive'] = archive_schema_outputs(runtime, output, report['written_outputs'])
            report['status'] = SUCCESS
        except (OSError, ValueError) as error:
            failures.append('Schema output archiving failed: ' + str(error))
    report['failures'] = failures
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (output / 'schema-generation-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--build-input', type=Path, required=True)
    parser.add_argument('--executable-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout-seconds', type=float, default=900)
    args = parser.parse_args()
    try:
        report = run_schema_generation(args.runtime, args.build_input, args.executable_sha256,
                                       args.output, args.timeout_seconds)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print(report['status'] + ': ' + str(args.output / 'schema-generation-report.json'))
    return 0 if report['status'] == SUCCESS else 1


if __name__ == '__main__':
    sys.exit(main())
