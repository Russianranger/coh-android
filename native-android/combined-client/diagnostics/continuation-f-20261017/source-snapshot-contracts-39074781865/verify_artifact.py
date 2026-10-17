#!/usr/bin/env python3
"""Verify the retained new-only hosted proof; never rerun its native suite."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shlex
import stat
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
COMMIT = 'fd213266f1b6665acece877dabb7dab6663e647c'
TREE = 'ff86ef76821a5aace6d4ffb53671cc37aaa2247e'
RUN = 39074781865
JOB = 117519562485
ARTIFACT = 12117045136
ZIP_SHA = 'dffcbfc3569cd12cb5e4ebc4b3bc9be6aaffa67d6cfb5c6b41e5d4a5af20b7e8'
INNER_SHA = 'c5a16359e01758c92073b931d64a0aad2f2b42fdf23781deb28907c5884edd84'
PREFIX = 'native-android/engine/scenecatalog-server/'
WORKFLOW = '.github/workflows/native-source-snapshot-contracts.yml'
FIXTURE = 'native-android/combined-client/diagnostics/primary-authority-20261017/unit-groups-fixture.cohgtx'


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(command, root):
    value = subprocess.run(list(map(str, command)), cwd=root, capture_output=True, timeout=60)
    require(value.returncode == 0 and len(value.stdout) + len(value.stderr) < 1024**2, 'READ_ONLY_TOOL_REFUSED')
    return value.stdout


def verify(root):
    metadata = json.loads((HERE / 'artifacts.json').read_bytes())['artifacts']
    require(len(metadata) == 1, 'ARTIFACT_SET')
    artifact = metadata[0]
    require(artifact['id'] == ARTIFACT and artifact['size_in_bytes'] == 2794
            and artifact['digest'] == 'sha256:' + ZIP_SHA and artifact['expired'] is False
            and artifact['workflow_run']['id'] == RUN
            and artifact['workflow_run']['head_sha'] == COMMIT, 'ARTIFACT_IDENTITY')
    run_info = json.loads((HERE / 'run.json').read_bytes())
    require(run_info['id'] == RUN and run_info['head_sha'] == COMMIT
            and run_info['head_branch'] == 'native-android'
            and run_info['head_commit']['tree_id'] == TREE
            and run_info['path'] == WORKFLOW and run_info['run_attempt'] == 1
            and run_info['status'] == 'completed' and run_info['conclusion'] == 'success', 'RUN_IDENTITY')
    jobs = json.loads((HERE / 'jobs.json').read_bytes())['jobs']
    require(len(jobs) == 1 and jobs[0]['id'] == JOB and jobs[0]['run_id'] == RUN
            and jobs[0]['status'] == 'completed' and jobs[0]['conclusion'] == 'success'
            and all(row['status'] == 'completed' and row['conclusion'] == 'success'
                    for row in jobs[0]['steps']), 'COMPLETE_JOB_OUTCOME')
    raw = (HERE / 'artifact.zip').read_bytes()
    require(len(raw) == 2794 and sha(raw) == ZIP_SHA, 'ZIP_IDENTITY')
    with zipfile.ZipFile(HERE / 'artifact.zip') as archive:
        rows = archive.infolist()
        require(len(rows) == 1 and rows[0].filename == 'native-verifier.json'
                and rows[0].file_size == 8276 and not rows[0].flag_bits & 1
                and stat.S_IFMT(rows[0].external_attr >> 16) in (0, stat.S_IFREG)
                and archive.testzip() is None, 'ZIP_MEMBER')
        body = archive.read(rows[0])
    require(sha(body) == INNER_SHA and body == (HERE / 'native-verifier.json').read_bytes(), 'INNER_BYTES')
    proof = json.loads(body)
    require(proof['schema'] == 'coh-source-snapshot-verifier-host-v1' and proof['passed'] is True
            and proof['source_revision'] == COMMIT and proof['checks'] == 328, 'PROOF_IDENTITY')
    for key in ('fixtures_synthetic_only', 'original_source_layout_fixture_reused',
                'owner_and_resource_observations_synthetic', 'named_memory_only_not_process_rss',
                'qualification_helper_committed_before_run_and_unchanged'):
        require(proof[key] is True, 'SYNTHETIC_SCOPE')
    for key in ('live_capture_executed', 'source_generation_admitted', 'world_authority', 'leak_sanitizer'):
        require(proof[key] is False, 'AUTHORITY_SCOPE')
    require(set(proof['modes']) == set(proof['allocation_modes']) == {'release', 'asan', 'ubsan'}, 'MODE_SET')
    counts = proof['modes']['release']['counts']
    for mode, value in proof['modes'].items():
        require(value['checks'] == 29 and value['refusals'] == 26 and value['counts'] == counts
                and value['saved_tail_with_four_roots_passed'] is True
                and 0 < value['maximum_static_frame_bytes'] < 512 * 1024, 'NATIVE_MODE')
        require(proof['allocation_modes'][mode] == {'successful_native_allocation_calls': 77,
                'allocation_failure_refusals': 77, 'final_live_native_allocations_each_case': 0}, 'NATIVE_OWNERSHIP')
    require(counts['named_aggregate_limit_bytes'] == 96 * 1024**2
            and counts['named_peak_reservation_bytes'] == 34081469, 'NAMED_COMPONENT_RESERVATION')
    require(run(['git', 'rev-parse', COMMIT + '^{tree}'], root).decode().strip() == TREE, 'PUBLISHED_TREE')
    sources = {}
    current_differences = {}
    for name, digest in proof['source_sha256'].items():
        require(name.startswith('native-android/') and '..' not in Path(name).parts, 'SOURCE_PATH')
        source = run(['git', 'show', COMMIT + ':' + name], root)
        require(sha(source) == digest, 'EXACT_COMMITTED_SOURCE')
        sources[name] = source
        current = root / name
        if not current.is_file() or sha(current.read_bytes()) != digest:
            current_differences[name] = None if not current.is_file() else sha(current.read_bytes())
    require(len(sources) == 37, 'SOURCE_COUNT')
    checker = PREFIX + 'check_source_snapshot_verifier.py'
    values = {}
    for node in ast.parse(sources[checker]).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('SOURCES', 'FLAGS'):
                    values[target.id] = ast.literal_eval(node.value)
    # Preprocess exact historical source bytes in a fresh temporary tree. This
    # only inventories dependencies; it compiles/runs no native test or module.
    with tempfile.TemporaryDirectory(prefix='coh-f-hosted-source-dependencies-') as temporary:
        exact = Path(temporary)
        for name, source in sources.items():
            path = exact / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(source)
        command = ['cc', *values['FLAGS'], '-I' + str(exact / 'native-android/include'), '-MM',
                   *[exact / 'native-android' / name for name in values['SOURCES']]]
        dependencies = run(command, exact).decode().replace('\\\n', ' ')
        found = {checker, PREFIX + 'inspect_groups_capture.py', PREFIX + 'test_source_snapshot_verifier.py'}
        for line in dependencies.splitlines():
            words = shlex.split(line)
            require(words and words[0].endswith(':'), 'DEPENDENCY_FORMAT')
            found.update(Path(name).resolve().relative_to(exact).as_posix() for name in words[1:])
        require(found == set(sources), 'COMPLETE_RECORDED_DEPENDENCY_SET')
    fixture = run(['git', 'show', COMMIT + ':' + FIXTURE], root)
    require(proof['fixture'] == {'bytes': len(fixture), 'sha256': sha(fixture)}, 'EXACT_SYNTHETIC_FIXTURE')
    log = (HERE / 'job.log').read_text(encoding='utf-8-sig')
    require('Ran 11 tests' in log and 'Ran 10 tests' in log and '"checks": 328' in log
            and ZIP_SHA in log and str(ARTIFACT) in log and COMMIT in log, 'HOSTED_LOG_OUTCOME')
    control_names = [WORKFLOW, *[PREFIX + name for name in (
        'admit_source_snapshot.py', 'test_source_snapshot_admission.py',
        'retain_fresh_source_snapshot.py', 'test_fresh_source_retention.py',
        'admit_graphical_fixture.py', 'capture_graphical_fixture.py',
        'graphical_fixture_backup_guest.py', 'summarize_groups_capture.py',
        'groups_capture_stages.py', 'capture_groups_transaction.py', 'delivery.py')]]
    control_pins = {name: sha(run(['git', 'show', COMMIT + ':' + name], root)) for name in control_names}
    return {'schema': 'coh-independent-new-only-hosted-source-proof-v1', 'passed': True,
            'run_id': RUN, 'job_id': JOB, 'artifact_id': ARTIFACT,
            'source_commit': COMMIT, 'source_tree': TREE,
            'archive': {'bytes': len(raw), 'sha256': ZIP_SHA},
            'member': {'path': 'native-verifier.json', 'bytes': len(body), 'sha256': INNER_SHA},
            'native_source_entries_verified_against_exact_commit': len(sources),
            'exact_native_source_sha256': proof['source_sha256'],
            'compiler_dependency_set_recomputed_from_exact_published_sources': True,
            'source_differences_in_current_worktree_no_current_requalification_claim': current_differences,
            'workflow_and_primary_python_control_sources_sha256': control_pins,
            'synthetic_fixture_path': FIXTURE, 'synthetic_fixture': proof['fixture'],
            'hosted_python_controls_passed': {'source_admission': 11, 'fresh_retention': 10},
            'hosted_native_checks': 328, 'native_refusals_per_mode': 26,
            'native_allocation_refusals_per_mode': 77, 'final_tracked_native_live_allocations': 0,
            'synthetic_named_peak_reservation_bytes': 34081469,
            'named_memory_only_not_process_rss': True,
            'review_repeated_hosted_tests_or_former_qualifiers': False,
            'live_capture_executed': False, 'source_generation_admitted': False,
            'world_authority': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = verify(args.source_root.resolve())
    with args.output.open('x') as output:
        json.dump(value, output, sort_keys=True, indent=2)
        output.write('\n')
    print(json.dumps({'passed': True, 'source_entries_verified': 37, 'world_authority': False}))
