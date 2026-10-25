#!/usr/bin/env python3
"""Inspect partial snapshots from rejected runs; never qualifies execution."""
import argparse
import itertools
import json
from pathlib import Path
import tempfile

from compare_state import canonical_initial_ids, differences
import run_ci


def diagnose(root, commit):
    executions = []
    outside_baseline = None
    outside_equal = True
    with tempfile.TemporaryDirectory() as temporary:
        expected = run_ci.fixtures(Path(temporary))
    for target in ('arm64', 'i686'):
        report = json.loads((root / target / 'report.json').read_text())
        if report.get('target') != target or report.get('source_commit') != commit:
            raise ValueError('Reference identity differs: ' + target)
        for label, initial_id in (('id1-a', 1), ('id1-b', 1), ('id31', 31)):
            folder = root / target / label
            process = json.loads((folder / 'process-observation.json').read_text())
            if type(process.get('returncode')) is not int:
                raise ValueError('Missing process return code: ' + str(folder))
            dispatch_errors = 0
            # This still verifies Wine, isolated trace integrity, cursors,
            # ACKs, all 117 snapshot hashes and the native INITIAL subset.
            # Only the explicitly typed data-error rejection is retained
            # as diagnostic evidence; all other validation failures abort.
            try:
                run_ci.check_output(folder / 'receiver.jsonl', expected,
                                    initial_id, folder / 'wine-output.txt')
            except run_ci.DispatchGameErrors as error:
                dispatch_errors = error.count
            inventory = json.loads((folder / 'client-errors.json').read_text())
            outside = inventory['outside_errors']
            if outside_baseline is None:
                outside_baseline = outside
            outside_equal = outside_equal and outside == outside_baseline
            executions.append(dict(target=target, label=label,
                returncode=process['returncode'],
                host_timeout_kill=process.get('host_timeout_kill', False),
                dispatch_errors=dispatch_errors,
                outside_error_count=sum(row['count'] for row in outside),
                dispatch_error_inventory=[row for row in inventory['phase_errors']
                                          if row['phase'] == 'dispatch'],
                source_cursor_stage_passed=report.get('cursor_stage_passed') is True))
    pairs = [(('arm64', label), ('i686', label), False)
             for label in ('id1-a', 'id1-b', 'id31')]
    for target in ('arm64', 'i686'):
        pairs += [((target, 'id1-a'), (target, 'id1-b'), False),
                  ((target, 'id1-a'), (target, 'id31'), True)]
    comparisons = []
    for left, right, sensitivity in pairs:
        mismatches = []
        for index in range(117):
            a_raw = (root.joinpath(*left) / f'state-{index:03d}.json').read_bytes()
            b_raw = (root.joinpath(*right) / f'state-{index:03d}.json').read_bytes()
            a, b = json.loads(a_raw), json.loads(b_raw)
            if sensitivity:
                a, b = canonical_initial_ids(a, 1), canonical_initial_ids(b, 31)
            equal = a == b if sensitivity else a_raw == b_raw
            if not equal:
                mismatches.append(dict(index=index,
                    fields=list(itertools.islice(differences(a, b), 20))))
        comparisons.append(dict(left=left, right=right,
            id_sensitivity=sensitivity, snapshots=117,
            equal=not mismatches, mismatches=mismatches))
    return dict(scope='rejected_run_partial_snapshot_diagnostic',
                source_commit=commit, executions=executions, comparisons=comparisons,
                diagnostic_snapshots_equal=all(row['equal'] for row in comparisons),
                diagnostic_outside_error_inventories_equal=outside_equal,
                execution_qualified=False, state_schema_complete=False,
                state_comparison_complete=False, m3_replay_complete=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.root, args.commit)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'comparisons'}))
    # Zero means the diagnostic was produced, never replay acceptance.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
