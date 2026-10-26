"""Collect data-error evidence without accepting any rejected replay."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_receiver_evidence as evidence
replay = evidence.replay


class ReplayRunSeries(unittest.TestCase):
    def run_main(self, failures, exit_code=2):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / 'runtime'
            runtime.mkdir()
            out = root / 'evidence'
            observed = []
            def check(path, *args, **kwargs):
                observed.append(path.parent.name)
                # Accepted-run repeat comparison still needs the two transcripts.
                path.write_text('same transcript')
                value = failures[len(observed) - 1]
                if value is not None:
                    raise value
                return dict(dispatches=117, m3_replay_complete=False)
            arguments = ['run_ci.py', '--runtime', str(runtime), '--out', str(out),
                '--target', 'arm64', '--host-netns', 'host', '--seh-control', str(root / 'control.exe')]
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(sys, 'argv', arguments))
                stack.enter_context(patch.object(replay.os, 'readlink', return_value='private'))
                stack.enter_context(patch.object(replay.os, 'geteuid', return_value=1000))
                stack.enter_context(patch.object(replay.subprocess, 'check_output', return_value='[{"ifname":"lo"}]'))
                stack.enter_context(patch.object(replay.subprocess, 'Popen', return_value=Mock()))
                stack.enter_context(patch.object(replay.subprocess, 'run', return_value=SimpleNamespace(returncode=0)))
                stack.enter_context(patch.object(replay.time, 'sleep'))
                stack.enter_context(patch.object(replay, 'fixtures', return_value=[]))
                stack.enter_context(patch.object(replay, 'check_exception_control'))
                stack.enter_context(patch.object(replay, 'check_client_output', return_value={}))
                stack.enter_context(patch.object(replay.exit_diagnostics, 'collect', return_value={}))
                stack.enter_context(patch.object(replay.process_observation, 'run', return_value=SimpleNamespace(returncode=exit_code)))
                stack.enter_context(patch.object(replay, 'check_output', side_effect=check))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                error = None
                try:
                    replay.main()
                except (ValueError, RuntimeError) as exc:
                    error = str(exc)
            return observed, json.loads((out / 'report.json').read_text()), error

    def test_three_data_error_runs_are_collected_but_job_still_fails(self):
        observed, report, error = self.run_main([replay.DispatchGameErrors(1) for _ in range(3)])
        self.assertEqual(observed, ['id1-a', 'id1-b', 'id31'])
        self.assertIn('id1-a, id1-b, id31', error)
        self.assertEqual([r['accepted'] for r in report['runs']], [False] * 3)
        self.assertNotIn('cursor_stage_passed', report)
        self.assertFalse(report['m3_replay_complete'])

    def test_later_success_cannot_rescue_first_rejection(self):
        observed, report, error = self.run_main([replay.DispatchGameErrors(1), None, None])
        self.assertEqual(len(observed), 3)
        self.assertIn('qualification failed', error)
        self.assertNotIn('cursor_stage_passed', report)

    def test_other_validation_failures_stop_without_continuation(self):
        for failure in ('Wine exception/fatal', 'Game fatal in isolated trace',
                        'receiver cursor mismatch', 'state snapshot digest mismatch'):
            with self.subTest(failure=failure):
                observed, report, error = self.run_main([ValueError(failure)])
                self.assertEqual(observed, ['id1-a'])
                self.assertEqual(error, failure)
                self.assertNotIn('cursor_stage_passed', report)

    def test_abnormal_exit_still_stops_before_receiver_acceptance(self):
        observed, report, error = self.run_main([], exit_code=3)
        self.assertEqual(observed, [])
        self.assertIn('expected incomplete-stage exit 2, got 3', error)
        self.assertNotIn('cursor_stage_passed', report)

    def test_three_clean_runs_keep_existing_cursor_only_result(self):
        observed, report, error = self.run_main([None] * 3)
        self.assertEqual(len(observed), 3)
        self.assertIsNone(error)
        self.assertTrue(report['cursor_stage_passed'])
        self.assertFalse(report['m3_replay_complete'])

    def test_data_errors_do_not_skip_real_transcript_and_snapshot_validation(self):
        fixture = evidence.ReceiverEvidenceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        trace = fixture.path / 'zone-trace.jsonl'
        rows = trace.read_text().splitlines(True)
        rows.insert(5, json.dumps(dict(stage='client.error', text='missing texture', tid=1)) + '\n')
        trace.write_text(''.join(rows))
        (fixture.path / 'client-stdio.txt').write_text('ArmPort zone: 1 client.error missing texture tid=1\n')
        with self.assertRaises(replay.DispatchGameErrors):
            fixture.check()
        fixture.rows[-1]['dispatches'] = 116
        with self.assertRaisesRegex(ValueError, 'incomplete milestone result') as error:
            fixture.check()
        self.assertNotIsInstance(error.exception, replay.DispatchGameErrors)
        fixture.rows[-1]['dispatches'] = 117
        (fixture.path / 'state-000.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'state snapshot digest mismatch') as error:
            fixture.check()
        self.assertNotIsInstance(error.exception, replay.DispatchGameErrors)
