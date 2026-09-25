#!/usr/bin/env python3
"""Compare ordinary, asset-backed MapServer -templates with accepted data-only output.

Use a NEW prepared runtime and the separately extracted, fixture-OFF reference
package. Only the six attribute maps and five generated dbidmaps are seeded to
preserve accepted IDs. All 56 outputs must be freshly rewritten and identical.
Incidental caches are inspected but never published or approved for gameplay.

The unmodified MapServer exits before reporting its queued error count. Passing
this comparison proves equality of the checked files for these inputs, not absence
of queued errors, complete asset coverage, runtime compatibility, or gameplay.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

import generate_runtime_data as generation
from prepare_runtime import (ASSET_SUFFIXES, excluded_reason, input_files, require,
                             safe_relative, sha256, verify_binaries)
from prepare_schema_source import expected_schema_receipt
from run_schema_generation import (SUCCESS as SCHEMA_SUCCESS, LOG_LIMIT, WARNING,
                                   archive_schema_outputs, bounded_process)

ROOT = Path(__file__).resolve().parents[1]
SUCCESS = 'reference_template_comparison_passed_gameplay_unvalidated'
DBIDMAPS = tuple('data/defs/' + name for name in (
    'dbidmaps/invbasedetail.dbidmap', 'dbidmaps/invrecipe.dbidmap',
    'dbidmaps/invsalvage.dbidmap', 'dbidmaps/invstoredsalvage.dbidmap',
    'proficiencyids.dbidmap'))
ATTRIBUTES = tuple('data/server/db/templates/' + name + '.attribute'
                   for name in generation.ATTRIBUTES)
EXPECTED = frozenset(
    ['data/server/db/templates/' + name + '.template' for name in generation.TEMPLATES] +
    list(ATTRIBUTES) + list(DBIDMAPS) +
    ['data/server/db/schemas/' + name + '.schema.html' for name in generation.SCHEMAS])
SEEDS = frozenset(ATTRIBUTES + DBIDMAPS)
USED_MARKER = '.reference-template-comparison-used'


def regular_json(path):
    require(path.is_file() and not path.is_symlink(), 'Missing regular JSON input: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def accepted_schema(report_path, root=ROOT, archive_path=None):
    report = regular_json(report_path)
    require(report.get('status') == SCHEMA_SUCCESS and report.get('exit_code') == 0 and
            report.get('failures') == [] and report.get('queued_error_counts') == [0] and
            report.get('strict_reload_executed') is True and report.get('attribute_files_stable') is True,
            'Schema generation has not passed strict bootstrap/reload acceptance')
    require(report.get('source_commit') == generation.SOURCE_COMMIT and
            report.get('data_commit') == generation.DATA_COMMIT, 'Schema source/data pin mismatch')
    receipt = report.get('schema_build_input', {})
    require(receipt == expected_schema_receipt(root, postgresql_build_input=receipt.get('postgresql_build_input')),
            'Accepted schema source receipt mismatch')
    metadata = report.get('schema_outputs_archive', {})
    archive = archive_path or report_path.parent / 'schema-outputs.zip'
    require(archive.is_file() and not archive.is_symlink(), 'Missing accepted schema archive')
    require(archive.stat().st_size == metadata.get('bytes') and sha256(archive) == metadata.get('sha256'),
            'Accepted schema archive hash/size mismatch')
    records = {}
    for record in metadata.get('files', []):
        name = record['path']
        safe_relative(name)
        key = name.casefold()
        require(key in EXPECTED and key not in records, 'Unexpected/duplicate accepted schema output: ' + name)
        records[key] = record
    require(set(records) == EXPECTED, 'Accepted schema archive must contain exactly the expected 56 files')
    payloads = {}
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        require(len(entries) == len(EXPECTED) and sum(e.file_size for e in entries) <= 200 * 1024 * 1024,
                'Accepted archive count/expanded size outside expected bounds')
        for entry in entries:
            safe_relative(entry.filename)
            key = entry.filename.casefold()
            require(key in records and key not in payloads and not entry.is_dir() and
                    (entry.external_attr >> 16) & 0o170000 != 0o120000, 'Unsafe/duplicate schema archive member')
            record = records[key]
            require(entry.filename == record['path'] and entry.file_size == record['bytes'],
                    'Schema archive entry differs from accepted record')
            value = source.read(entry)
            require(hashlib.sha256(value).hexdigest() == record['sha256'],
                    'Accepted schema payload hash mismatch: ' + entry.filename)
            payloads[key] = value
    return report, records, payloads


def pinned_text_records(root, source_lock, data_lock):
    """Reconstruct prepare_runtime's text selection using immutable manifests."""
    result = {}
    for lock, source_configs in ((data_lock, False), (source_lock, True)):
        manifest = regular_json(root / lock['manifest'])
        entries = manifest.get('entries', [])
        require(manifest.get('commit') == lock['commit'] and len(entries) == lock['files'] and
                sum(e['size'] for e in entries) == lock['bytes'], 'Pinned manifest differs from its lock')
        seen = set()
        for entry in entries:
            name = entry['path']
            safe_relative(name)
            require(name not in seen, 'Duplicate pinned manifest path')
            seen.add(name)
            lower = name.casefold()
            if source_configs:
                selected = lower.startswith('data/server/db/') and lower.endswith('.cfg')
            else:
                selected = name.startswith('data/') and excluded_reason(name.removeprefix('data/')) is None
            if selected:
                if lower in result and not source_configs:
                    require(result[lower]['sha256'] == entry['sha256'], 'Conflicting pinned text namespace')
                result[lower] = entry
    return result


def check_runtime(runtime, reference, root=ROOT):
    require(runtime.is_dir() and not runtime.is_symlink(), 'Runtime must be a real directory')
    require(reference.is_dir() and not reference.is_symlink(), 'Reference binaries must be a real directory')
    runtime, reference, root = runtime.resolve(), reference.resolve(), root.resolve()
    upstream = root / 'upstream'
    require(runtime != root and runtime != upstream and upstream not in runtime.parents,
            'Cannot execute inside immutable upstream or repository root')
    require(runtime != reference and runtime not in reference.parents and reference not in runtime.parents,
            'Use a separate extracted reference package')
    for name in ('.runtime-staging-incomplete', USED_MARKER, 'gamedatadir.txt'):
        require(not (runtime / name).exists(), 'Incomplete, reused, or redirected runtime: ' + name)
    # Reject symlink directories, including empty ones that could redirect writes.
    actual = {}
    for name, path in input_files(runtime):
        key = name.casefold()
        require(key not in actual, 'Case-colliding runtime path: ' + name)
        actual[key] = path
    inputs = regular_json(runtime / 'runtime-inputs.json')
    require(inputs.get('status') == 'staged_not_gameplay_validated' and
            inputs.get('source_commit') == generation.SOURCE_COMMIT and
            inputs.get('data_commit') == generation.DATA_COMMIT and
            inputs.get('executables_supplied') is True and inputs.get('binary_assets_supplied') is True,
            'Expected complete, pinned runtime stage with assets and reference executables')
    source_lock, data_lock = regular_json(root / 'upstream-lock.json'), regular_json(root / 'content-lock.json')
    require(source_lock['commit'] == generation.SOURCE_COMMIT and data_lock['commit'] == generation.DATA_COMMIT,
            'Source/data lock pins differ from the reference contract')
    package, binaries, hashes = verify_binaries(reference, root, source_lock)
    require(inputs.get('reference_repository_commit') == package['repository_commit'] and
            inputs.get('postgresql_build_input') == package['postgresql_build_input'] and
            inputs.get('build_file_sha256') == hashes, 'Staging and reference build receipts differ')
    require(not any('schema-generation' in name.casefold() for name in binaries),
            'Schema-only build may not be used as the reference')
    for name, digest in hashes.items():
        require(name.casefold() in actual and sha256(actual[name.casefold()]) == digest,
                'Staged reference file hash mismatch: ' + name)
    allowed_roots = {name.casefold() for name in hashes} | {'runtime-inputs.json'}
    require(all(name.startswith(('data/', 'tools/')) or name in allowed_roots for name in actual),
            'Unlisted runtime root file could affect ordinary execution')
    expected = pinned_text_records(root, source_lock, data_lock)
    assets = inputs.get('binary_asset_files', {})
    require(isinstance(assets, dict) and assets, 'No binary assets recorded in stage')
    asset_keys = set()
    for name, digest in assets.items():
        safe_relative(name)
        key = 'data/' + name.casefold()
        require(key not in expected and key not in asset_keys and
                Path(name).suffix.casefold() in ASSET_SUFFIXES and excluded_reason(name) is None and
                re.fullmatch(r'[0-9a-f]{64}', digest), 'Invalid/duplicate staged asset record: ' + name)
        asset_keys.add(key)
        expected[key] = {'sha256': digest}
    require({name for name in actual if name.startswith('data/')} == set(expected),
            'Runtime data namespace differs from pinned text plus recorded assets; use a fresh stage')
    for name, record in expected.items():
        require(sha256(actual[name]) == record['sha256'], 'Staged data hash mismatch: ' + name)
    before = generation.output_snapshot(runtime)
    # Fresh pinned text includes six dbidmaps. Only those may predate this run.
    require(all(name.endswith('.dbidmap') and name in expected and name not in asset_keys for name in before),
            'Preexisting generated templates or caches require a fresh stage')
    return {'inputs': inputs, 'package': package, 'hashes': hashes,
            'verified_text_files': len(expected) - len(asset_keys), 'verified_asset_files': len(asset_keys)}


def seed_identifiers(runtime, payloads):
    # Preserve any existing Windows casing from the pinned text namespace.
    existing = {relative.casefold(): path for relative, path in input_files(runtime / 'data/defs')}
    for name in sorted(SEEDS):
        target = existing.get(name.removeprefix('data/defs/'), runtime / name) if name in DBIDMAPS else runtime / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payloads[name])
    return {name: hashlib.sha256(payloads[name]).hexdigest() for name in sorted(SEEDS)}


def compare_outputs(before, after, expected):
    changed = generation.changed_outputs(before, after)
    differences, records = [], []
    for name in sorted(EXPECTED):
        actual = after.get(name)
        if actual is None:
            differences.append({'path': name, 'reason': 'missing'})
        elif name not in changed:
            differences.append({'path': name, 'reason': 'not freshly rewritten'})
        elif actual['sha256'] != expected[name]['sha256'] or actual['bytes'] != expected[name]['bytes']:
            differences.append({'path': name, 'reason': 'bytes differ',
                                'expected_sha256': expected[name]['sha256'], 'actual_sha256': actual['sha256']})
        else:
            records.append(actual)
    return differences, records


def run(runtime, reference, schema_report, output, timeout=900, root=ROOT,
        schema_archive=None, runner=(), log_limit=LOG_LIMIT):
    # The runner hook exists for synthetic tests only; the CLI runs Windows PE directly.
    runtime, reference, output = Path(runtime), Path(reference), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Evidence output must be a new directory')
    output, root = output.resolve(), Path(root).resolve()
    for protected in (runtime.resolve(), reference.resolve(), root / 'upstream'):
        require(output != protected and protected not in output.parents and output not in protected.parents,
                'Evidence output overlaps protected inputs')
    require(output != root and 0 < timeout <= 3600 and 0 < log_limit <= LOG_LIMIT, 'Invalid output/process bounds')
    context = check_runtime(runtime, reference, root)
    accepted, expected, payloads = accepted_schema(Path(schema_report), root,
                                                   Path(schema_archive) if schema_archive else None)
    runtime = runtime.resolve()
    output.mkdir(parents=True)
    report = {
        'status': 'reference_template_comparison_failed', 'started_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': generation.SOURCE_COMMIT, 'data_commit': generation.DATA_COMMIT,
        'reference_repository_commit': context['package']['repository_commit'],
        'postgresql_build_input': context['package']['postgresql_build_input'],
        'runtime_inputs_sha256': sha256(runtime / 'runtime-inputs.json'),
        'schema_report_sha256': sha256(Path(schema_report)),
        'accepted_schema_archive_sha256': accepted['schema_outputs_archive']['sha256'],
        'mapserver_sha256': context['hashes']['MapServer.exe'],
        'verified_text_files': context['verified_text_files'], 'verified_asset_files': context['verified_asset_files'],
        'gameplay_validated': False, 'database_started': False, 'asset_coverage_complete': False,
        'nonfatal_queued_errors_reviewed': False, 'queued_error_count': None,
        'queued_error_limit': 'Unmodified MapServer -templates exits before reporting its queued error count',
        'scope': 'Fresh ordinary -templates outputs compared byte-for-byte with accepted data-only outputs',
        'incidental_cache_policy': 'not approved for gameplay and excluded from output archive',
        'serializer_equivalence': 'unverified', 'failures': [], 'internal_logs': [],
    }
    try:
        # Preserve the exact checked manifest so later map tests can bind their
        # fresh stage to the assets used in this comparison, not just its count.
        (output / 'comparison-runtime-inputs.json').write_bytes((runtime / 'runtime-inputs.json').read_bytes())
        (runtime / USED_MARKER).write_text('Disposable comparison runtime; do not reuse for validation.\n')
        report['seeded_identifier_sha256'] = seed_identifiers(runtime, payloads)
        before, before_logs = generation.output_snapshot(runtime), generation.internal_log_snapshot(runtime)
        command = list(runner) + [str(runtime / 'MapServer.exe'), '-nogui', '-templates']
        report.update(command=command, timeout_seconds=timeout)
        stdout, stderr = output / 'stdout.log', output / 'stderr.log'
        report.update(bounded_process(command, runtime, stdout, stderr, timeout, log_limit))
        text = stdout.read_text(encoding='utf-8', errors='replace') + '\n' + stderr.read_text(encoding='utf-8', errors='replace')
        after_logs = generation.internal_log_snapshot(runtime)
        for relative, record in generation.changed_outputs(before_logs, after_logs).items():
            source, target = runtime / relative, output / 'internal' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as stream:
                value = stream.read(log_limit + 1)
            target.write_bytes(value[:log_limit])
            if len(value) > log_limit:
                report['failures'].append('Internal log exceeded capture bound: ' + relative)
                text += '\n' + value[:log_limit].decode('utf-8', errors='replace')
            else:
                text += '\n' + generation.new_log_text(source, before_logs.get(relative))
            report['internal_logs'].append({**record, 'captured_bytes': min(len(value), log_limit),
                                            'capture_sha256': sha256(target)})
        after = generation.output_snapshot(runtime)
        validation = generation.validate_outputs('templates', runtime, before, after, text)
        report['failures'].extend(validation.pop('failures'))
        report.update(validation)
        differences, compared = compare_outputs(before, after, expected)
        report.update(output_differences=differences, identical_fresh_output_count=len(compared),
                      expected_output_count=len(EXPECTED))
        if differences:
            report['failures'].append('Expected reference outputs are missing, stale, or byte-different')
        if report.get('exit_code') != 0 or report.get('timed_out') or report.get('log_limit_exceeded') or report.get('capture_error'):
            report['failures'].append('Reference MapServer did not exit cleanly within process/log bounds')
        if 'COH_DB_TEMPLATES_ONLY_' in text:
            report['failures'].append('Schema-only executable diagnostics appeared in ordinary reference run')
        warnings = [line[:2000] for line in text.splitlines() if WARNING.search(line)]
        report.update(warning_line_count=len(warnings), warning_lines=warnings[:1000],
                      warning_summary_truncated=len(warnings) > 1000,
                      stdout_sha256=sha256(stdout), stderr_sha256=sha256(stderr))
        if not report['failures']:
            report['compared_outputs_archive'] = archive_schema_outputs(runtime, output, compared)
            report['status'] = SUCCESS
            report['serializer_equivalence'] = '56_generated_files_byte_equal_for_checked_inputs'
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        report['failures'].append(str(error))
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'reference-template-comparison-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--reference-binaries', type=Path, required=True)
    parser.add_argument('--schema-report', type=Path, required=True)
    parser.add_argument('--schema-archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout-seconds', type=float, default=900)
    args = parser.parse_args()
    try:
        report = run(args.runtime, args.reference_binaries, args.schema_report, args.output,
                     args.timeout_seconds, schema_archive=args.schema_archive)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(report['status'] + ': ' + str(args.output / 'reference-template-comparison-report.json'))
    return 0 if report['status'] == SUCCESS else 1


if __name__ == '__main__':
    sys.exit(main())
