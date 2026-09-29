"""Boundaries of the isolated imported-data Android Atlas guest adapter."""
import argparse
import copy
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import signal
import subprocess
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_device_diagnostic as guest


def sha(value):
    return hashlib.sha256(value).hexdigest()


class ImportBoundaryTests(unittest.TestCase):
    def generation(self, root, contract='a' * 64):
        generation = root / ('generation-' + 'b' * 32)
        (generation / 'data').mkdir(parents=True)
        receipt = (f'generation={generation.name}\ncontract.sha256={contract}\n'
                   f'count={guest.DATA_COUNT}\nbytes={guest.DATA_BYTES}\n')
        (generation / 'complete.properties').write_text(receipt)
        return generation

    def test_actual_import_receipt_sha256_keys_and_current_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generation = self.generation(root)
            result = guest.import_receipt(generation, 'a' * 64)
            self.assertEqual(result['generation'], generation.name)
            self.assertEqual(result['file_count'], 173011)
            self.assertEqual(result['total_bytes'], 2977730517)
            self.assertEqual(result['receipt_sha256'], sha((generation / 'complete.properties').read_bytes()))
            self.assertFalse(result['private_copy_verified'])
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'contract differs'):
                guest.import_receipt(generation, 'c' * 64)

    def test_current_repository_import_contract_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'atlas-import.properties'
            current = 'c' * 40
            value = {'format': '1', 'source.commit': guest.SOURCE_COMMIT, 'data.commit': guest.DATA_COMMIT,
                     'repository.commit': current, 'total.count': str(guest.DATA_COUNT),
                     'total.bytes': str(guest.DATA_BYTES), 'asset.archive.bytes': '615541018',
                     'asset.archive.sha256': '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07',
                     'asset.manifest.sha256': 'cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f',
                     'text.index.sha256': 'd' * 64}
            path.write_text(''.join(key + '=' + item + '\n' for key, item in sorted(value.items())))
            self.assertEqual(guest.import_contract(path, current), sha(path.read_bytes()))
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'candidate repository'):
                guest.import_contract(path, 'e' * 40)
            path.write_text(path.read_text() + 'contract.sha256=a\ncontract.sha256=b\n')
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Duplicate'):
                guest.read_properties(path, 16384)

    def test_receipt_bad_generation_extra_fields_link_or_wrong_totals_refused(self):
        mutations = {
            'alias': lambda generation: (generation / 'complete.properties').write_text(
                (generation / 'complete.properties').read_text().replace(generation.name, 'generation-' + 'd' * 32)),
            'extra': lambda generation: (generation / 'complete.properties').write_text(
                (generation / 'complete.properties').read_text() + 'extra=true\n'),
            'total': lambda generation: (generation / 'complete.properties').write_text(
                (generation / 'complete.properties').read_text().replace('count=173011', 'count=1')),
            'linked-data': lambda generation: ((generation / 'data').rmdir(),
                (generation / 'data').symlink_to(generation.parent, target_is_directory=True)),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                generation = self.generation(Path(temporary))
                mutate(generation)
                with self.assertRaises(guest.base.DiagnosticError):
                    guest.import_receipt(generation, 'a' * 64)

    def test_linked_manifest_parent_and_duplicate_json_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / 'real'
            real.mkdir()
            (real / 'metadata.json').write_text('{"format":1,"format":2}')
            linked = root / 'linked'
            linked.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Linked'):
                guest.checked_file(linked / 'metadata.json', 16384)
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Duplicate'):
                guest.pinned_json(real / 'metadata.json', sha((real / 'metadata.json').read_bytes()), 16384)

    def test_manifest_adapter_cannot_redirect_data_files(self):
        manifest = Path('/independent/inventory.json')
        view = guest.ManifestDirectory(manifest)
        self.assertEqual(view / 'game-data-manifest.json', manifest)
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Unexpected'):
            view / 'data/anything'

    def test_android_host_default_policy_rejected_before_input_access(self):
        args = SimpleNamespace(execution_platform='android', listener_policy='host-default')
        context = SimpleNamespace(report={})
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Android requires'):
            guest.DeviceGameDiagnostic(args, context)


class VerifiedCopyTests(unittest.TestCase):
    def test_copy_is_independent_and_every_byte_rehashed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'target'
            source.write_bytes(b'accepted source')
            record = {'bytes': source.stat().st_size, 'sha256': sha(source.read_bytes())}
            check = Mock()
            guest.copy_verified(source, target, record, check)
            self.assertNotEqual(source.stat().st_ino, target.stat().st_ino)
            target.write_bytes(b'generated cache')
            self.assertEqual(source.read_bytes(), b'accepted source')
            self.assertGreaterEqual(check.call_count, 4)
            target.unlink()
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'hash differs'):
                guest.copy_verified(source, target, dict(record, sha256='0' * 64), Mock())

    def test_copy_rejects_links_and_cancels_before_whole_file_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'target'
            source.write_bytes(b'x' * (3 * guest.COPY_BLOCK))
            record = {'bytes': source.stat().st_size, 'sha256': sha(source.read_bytes())}
            check = Mock(side_effect=[None, guest.base.Cancelled('stop')])
            with self.assertRaises(guest.base.Cancelled):
                guest.copy_verified(source, target, record, check)
            self.assertEqual(target.stat().st_size, guest.COPY_BLOCK)
            target.unlink()
            linked = root / 'hardlink'
            os.link(source, linked)
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'linked'):
                guest.copy_verified(source, target, record, Mock())
            linked.unlink()
            linked.symlink_to(source)
            with self.assertRaises(OSError):
                guest.copy_verified(linked, target, record, Mock())

    def diagnostic(self, root):
        generation = root / ('generation-' + 'b' * 32)
        payloads = {'data/server/db/servers.cfg': b'original configuration', 'data/Defs/first.def': b'original data'}
        for name, content in payloads.items():
            path = generation / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        schema, package = root / 'schema', root / 'package'
        schema.mkdir()
        package.mkdir()
        names = ['data/defs/first.def'] + ['data/generated/' + str(number) + '.def' for number in range(61)]
        for name in names:
            path = schema / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'accepted schema overlay')
        (package / 'MapServer.exe').write_bytes(b'accepted binary fixture')
        total = sum(map(len, payloads.values()))
        (generation / 'complete.properties').write_text(
            f'generation={generation.name}\ncontract.sha256={"a" * 64}\ncount=2\nbytes={total}\n')
        value = object.__new__(guest.DeviceGameDiagnostic)
        value.root, value.runtime = root, root / 'private-game'
        value.import_generation = generation
        value.data = {'file_count': 2, 'total_bytes': total,
                      'files': {name: {'bytes': len(content), 'sha256': sha(content)} for name, content in payloads.items()}}
        value.schema = {'files': dict.fromkeys(names, {})}
        value.package = {'files': {'MapServer.exe': {}}}
        value.args = SimpleNamespace(schema=schema, game_package=package)
        value.ctx = SimpleNamespace(stage=Mock(), check=Mock(), event=Mock(), passed=Mock())
        with patch.object(guest, 'DATA_COUNT', 2), patch.object(guest, 'DATA_BYTES', total):
            value.imported = guest.import_receipt(generation, 'a' * 64)
        return value, payloads, total

    def run_staging(self, value, total):
        with patch.object(guest, 'DATA_COUNT', 2), patch.object(guest, 'DATA_BYTES', total), \
                patch.object(guest.shutil, 'disk_usage', return_value=SimpleNamespace(free=10 * 1024**3)):
            value.prepare_runtime()

    def test_fresh_private_staging_overlays_schema_without_changing_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            value, payloads, total = self.diagnostic(Path(temporary))
            receipt = (value.import_generation / 'complete.properties').read_bytes()
            self.run_staging(value, total)
            self.assertEqual((value.runtime / 'data/Defs/first.def').read_bytes(), b'accepted schema overlay')
            for name, payload in payloads.items():
                self.assertEqual((value.import_generation / name).read_bytes(), payload)
                self.assertNotEqual((value.import_generation / name).stat().st_ino, (value.runtime / name).stat().st_ino)
            self.assertEqual((value.import_generation / 'complete.properties').read_bytes(), receipt)
            self.assertTrue(value.imported['private_copy_verified'])
            self.assertTrue(value.imported['source_generation_unchanged'])
            value.ctx.passed.assert_called_once_with(input_files=2, input_bytes=total, accepted_schema_overlay_files=62)

    def test_unexpected_import_file_fails_before_schema_or_binary_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            value, payloads, total = self.diagnostic(Path(temporary))
            (value.import_generation / 'unreviewed.exe').write_bytes(b'extra')
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'extra/missing'):
                self.run_staging(value, total)
            self.assertFalse((value.runtime / 'MapServer.exe').exists())
            self.assertFalse(value.imported['private_copy_verified'])

    def test_cancelled_staging_preserves_source_and_never_launches(self):
        with tempfile.TemporaryDirectory() as temporary:
            value, payloads, total = self.diagnostic(Path(temporary))
            value.ctx.check.side_effect = guest.base.Cancelled('stop')
            with self.assertRaises(guest.base.Cancelled):
                self.run_staging(value, total)
            for name, payload in payloads.items():
                self.assertEqual((value.import_generation / name).read_bytes(), payload)
            self.assertFalse((value.runtime / 'MapServer.exe').exists())

    def test_low_storage_fails_before_allocating_private_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            value, payloads, total = self.diagnostic(Path(temporary))
            with patch.object(guest, 'DATA_COUNT', 2), patch.object(guest, 'DATA_BYTES', total), \
                    patch.object(guest.shutil, 'disk_usage', return_value=SimpleNamespace(free=1)):
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'storage'):
                    value.prepare_runtime()
            self.assertFalse(value.runtime.exists())


class DeviceStartupBudgetTests(unittest.TestCase):
    """Exercise the actual accepted start_services order using a simulated clock."""
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.clock = 0.0
        self.listener_at = 12.0
        self.main_loop_at = 60.0
        self.cancel_at = None
        self.exit_at = None
        self.publication_error = None
        self.value = object.__new__(guest.DeviceGameDiagnostic)
        value = self.value
        value.runtime = Path(temporary.name)
        value.wine_env = {'WINEPREFIX': '/private/test-wine'}
        value.loopback_enabled = value.game_listener_enabled = False
        value.check_fixed_inputs = Mock()
        value.dispatch_paths, value.dispatch_stages = {}, {'8': 'SQL_KEEPALIVE_QUEUE', '13': 'NM_MONITOR'}
        value.schema = {'expected_tables': {'ents': ['containerid']}}
        value.schema_snapshot = Mock(return_value={'table_count': 99})
        value.sql = Mock(return_value='1')  # Already persisted before restart.
        value.game = {'dispatch_progress': {'phases': {}}, 'phases': []}
        value.readiness_count = 0
        value.services = []
        value.pg = SimpleNamespace(process=SimpleNamespace(poll=lambda: None))
        value.ctx = SimpleNamespace(stage=Mock(), passed=Mock(), event=Mock(), check=self.check, deadline=1000)
        self.launches = []
        def start_game(label, executable, arguments, **options):
            child = SimpleNamespace(label=label, overflow=False,
                process=SimpleNamespace(poll=lambda: 1 if self.exit_at is not None and self.clock >= self.exit_at else None),
                text=lambda: guest.dbserver.FIXED_INPUTS_ACK + '\n' if executable == 'DbServer.exe' else '')
            self.launches.append((label, self.clock))
            value.services.append(child)
            return child
        value.start_game = start_game
        value.map_status = Mock(side_effect=[{'ready': False, 'not_started': True}, {'ready': True}])
        def dispatch(*args):
            if self.publication_error:
                raise self.publication_error
            return {'loop_count': int(self.clock >= self.main_loop_at), 'stage': 'SQL_KEEPALIVE_QUEUE',
                    'sequence': 10, 'windows_pid': 32, 'main_thread_id': 36}
        socket = Mock()
        socket.connect_ex.side_effect = lambda address: 0 if self.clock >= self.listener_at else 1
        socket_context = Mock()
        socket_context.__enter__ = Mock(return_value=socket)
        socket_context.__exit__ = Mock(return_value=False)
        for patcher in (
                patch.object(guest.time, 'monotonic', side_effect=lambda: self.clock),
                patch.object(guest.time, 'sleep', side_effect=self.sleep),
                patch.object(guest.game, 'check_game_port'),
                patch.object(guest.game.socket, 'socket', return_value=socket_context),
                patch.object(guest.game.hang_evidence, 'read_dispatch_record', side_effect=dispatch),
                patch.object(guest.game.evidence, 'map_ready_current', side_effect=lambda sample: sample['ready'])):
            self.addCleanup(patcher.stop)
            patcher.start()

    def sleep(self, seconds):
        self.clock += seconds

    def check(self):
        if self.cancel_at is not None and self.clock >= self.cancel_at:
            raise guest.base.Cancelled('Stop during DbServer startup')
        guest.require(self.clock < self.value.ctx.deadline, 'Overall diagnostic deadline exceeded')

    def test_retained_schema_can_precede_legitimate_main_loop_by_more_than_thirty_seconds(self):
        self.value.start_services('restart')
        self.assertEqual([label for label, _ in self.launches], ['restart-dbserver', 'restart-atlas'])
        self.assertGreaterEqual(self.launches[1][1], 60)
        self.assertEqual(self.value.game['dispatch_progress']['phases']['restart']['loop_count'], 1)
        record = self.value.game['device_dbserver_startup']['restart']
        self.assertEqual(record['budget_seconds'], 600)
        self.assertLess(record['milestones']['schema_and_listener']['elapsed_since_startup_seconds'], 13)
        self.assertGreaterEqual(record['milestones']['positive_main_loop']['elapsed_since_startup_seconds'], 60)
        self.assertIsNone(self.value._dbserver_startup)

    def test_same_causal_sequence_fails_the_original_separate_thirty_second_wait(self):
        with patch.object(guest.DeviceGameDiagnostic, 'wait', guest.game.GameDiagnostic.wait):
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'main-thread dispatch publication'):
                self.value.start_services('restart')
        self.assertGreaterEqual(self.clock, 42)
        self.assertLess(self.clock, 43)
        self.assertEqual([label for label, _ in self.launches], ['restart-dbserver'])

    def test_slow_schema_does_not_allocate_another_six_hundred_seconds_to_dispatch(self):
        self.listener_at, self.main_loop_at = 590, 620
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'shared DbServer startup budget'):
            self.value.start_services('restart')
        self.assertGreaterEqual(self.clock, 600)
        self.assertLess(self.clock, 601)
        self.assertEqual([label for label, _ in self.launches], ['restart-dbserver'])
        self.assertEqual(self.value.game['device_dbserver_startup']['restart']['milestones']['positive_main_loop']['status'], 'failed')
        self.assertIsNone(self.value._dbserver_startup)

    def test_zero_loop_count_never_becomes_ready_and_overall_deadline_still_wins(self):
        self.main_loop_at = 10000
        self.value.ctx.deadline = 45
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Overall diagnostic deadline'):
            self.value.start_services('first')
        self.assertLess(self.clock, 46)
        self.assertEqual(self.value.game['dispatch_progress']['phases'], {})
        self.assertEqual([label for label, _ in self.launches], ['first-dbserver'])

    def test_stop_still_aborts_before_atlas(self):
        # Stop occurs during the same real publication wait, before
        # fixed-input/listener acceptance can authorize the Atlas launch.
        self.cancel_at = 20
        with self.assertRaises(guest.base.Cancelled):
            self.value.start_services('restart')
        self.assertEqual(self.value.game['device_dbserver_startup']['restart']['milestones']['positive_main_loop']['status'], 'cancelled')
        self.assertEqual([label for label, _ in self.launches], ['restart-dbserver'])
        self.assertIsNone(self.value._dbserver_startup)

    def test_exited_owned_dbserver_is_not_hidden_by_startup_budget(self):
        self.exit_at = 20
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Owned game service exited'):
            self.value.start_services('restart')
        self.assertEqual([label for label, _ in self.launches], ['restart-dbserver'])

    def test_malformed_dispatch_is_not_retried_as_pending(self):
        self.publication_error = guest.base.DiagnosticError('Invalid dispatch identity')
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Invalid dispatch identity'):
            self.value.start_services('restart')
        self.assertLess(self.clock, 13)
        self.assertEqual([label for label, _ in self.launches], ['restart-dbserver'])
        self.assertIsNone(self.value._dbserver_startup)

    def test_predicate_finishing_after_shared_deadline_cannot_publish_success(self):
        self.value._dbserver_startup = {'started': 0, 'deadline': 5, 'record': {'milestones': {}}}
        def late_positive():
            self.sleep(6)
            return {'loop_count': 1}
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'shared DbServer startup budget'):
            self.value.wait(late_positive, 30, 'DbServer main-thread dispatch publication')
        milestone = self.value._dbserver_startup['record']['milestones']['positive_main_loop']
        self.assertEqual(milestone['status'], 'failed')
        self.assertEqual(milestone['elapsed_since_startup_seconds'], 6)

    def test_unrelated_waits_keep_their_original_duration(self):
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Atlas readiness'):
            self.value.wait(lambda: False, 7, 'Atlas readiness')
        self.assertGreaterEqual(self.clock, 7)
        self.assertLess(self.clock, 8)


class DeviceOwnershipTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = guest.base.Context(self.root)
        self.owner = guest.DeviceWineProcessOwner(self.context, self.root)
        self.owner.initialized = True
        self.owner.real_uid = 42
        self.owner.excluded = set()
        self.owner.direct_pid_view = True
        self.owner.diagnostic_starttime = 1
        self.group = self.root / '123'
        self.task = self.group / 'task/124'
        self.task.mkdir(parents=True)
        self.leader = {'pid': 123, 'state': 'Z', 'parent': 1, 'starttime': 10}
        self.worker = {'pid': 124, 'state': 'S', 'parent': 1, 'starttime': 11}
        self.status = {'uid': 42, 'pid': 123, 'tgid': 123, 'namespace_pids': [123]}
        self.worker_status = {**self.status, 'pid': 124, 'namespace_pids': [124]}
        status = patch.object(self.owner, 'status', side_effect=lambda path:
            dict(self.status if path == self.group else self.worker_status))
        identity = patch.object(self.owner, 'process_stat', side_effect=lambda path:
            dict(self.leader if path == self.group else self.worker))
        self.addCleanup(status.stop)
        self.addCleanup(identity.stop)
        status.start()
        identity.start()

    def test_worker_permission_transition_to_zombie_is_verified_before_exclusion(self):
        def denied(path):
            self.worker['state'] = 'Z'
            raise PermissionError(13, 'worker exited')
        with patch.object(self.owner, 'has_token', side_effect=denied):
            self.assertIsNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(self.owner.receipt['worker_exit_rechecks'], 1)
        observed = self.owner.receipt['permission_observations']
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]['operation'], 'worker_environment')
        self.assertEqual(observed[0]['worker_tid'], 124)
        self.assertEqual(observed[0]['resolution'], 'same_worker_became_zombie')
        self.assertEqual(self.owner.receipt['inspection_failures'], 0)
        self.assertEqual(self.owner.receipt['owned_live_workers'], 0)

    def test_live_group_esrch_is_not_swallowed_by_signal_owned(self):
        self.leader['state'] = 'S'
        for operation in ('has_token', 'pid_namespace'):
            self.owner.direct_pid_view = operation != 'pid_namespace'
            self.owner.namespace_depth, self.owner.namespace = 1, 'pid:[111]'
            before = self.owner.receipt['inspection_failures']
            with self.subTest(operation=operation), \
                    patch.object(self.owner, operation, side_effect=ProcessLookupError(3, 'sensitive text')), \
                    patch.object(guest.os, 'pidfd_open', return_value=19), patch.object(guest.os, 'close'), \
                    patch.object(guest.signal, 'pidfd_send_signal') as send, patch.object(guest.os, 'kill') as kill:
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'live Wine ownership'):
                    self.owner.signal_owned({'proc_pid': 123, 'pid': 123, 'starttime': 10}, signal.SIGTERM,
                                            time.monotonic() + 1)
                send.assert_not_called()
                kill.assert_not_called()
            failure = self.owner.receipt['last_inspection_failure']
            self.assertEqual(failure['error_type'], 'ProcessLookupError')
            self.assertEqual(failure['errno'], 3)
            self.assertEqual(failure['resolution'], 'persistent_live_read_failure')
            self.assertEqual(self.owner.receipt['inspection_failures'], before + 1)
            self.assertNotIn('sensitive text', json.dumps(self.owner.receipt))

    def test_group_environ_esrch_during_leader_exit_preserves_live_worker(self):
        self.leader['state'] = 'S'
        def read(path):
            if path == self.group:
                self.leader['state'] = 'Z'
                raise ProcessLookupError(3, 'mm is gone but worker is alive')
            return True
        with patch.object(self.owner, 'has_token', side_effect=read):
            self.assertEqual(self.owner.inspect(123, time.monotonic() + 1),
                             {'proc_pid': 123, 'pid': 123, 'starttime': 10})
        self.assertEqual(self.owner.receipt['owned_live_workers'], 1)
        self.assertEqual(self.owner.receipt['leader_exit_retries'], 1)
        self.assertEqual(self.owner.receipt['proc_read_observations'][0]['resolution'],
                         'same_leader_became_zombie_check_workers')

    def test_group_namespace_esrch_checks_worker_namespace_and_token(self):
        self.leader['state'] = 'S'
        self.owner.direct_pid_view = False
        self.owner.namespace_depth, self.owner.namespace = 1, 'pid:[111]'
        def namespace(path):
            if path == self.group:
                self.leader['state'] = 'Z'
                raise ProcessLookupError(3, 'leader exiting')
            return self.owner.namespace
        with patch.object(self.owner, 'pid_namespace', side_effect=namespace) as read_ns, \
                patch.object(self.owner, 'has_token', return_value=True) as token:
            self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(read_ns.call_count, 2)
        token.assert_called_once_with(self.task)

    def test_worker_esrch_requires_fresh_full_ownership_and_respects_deadline(self):
        with patch.object(self.owner, 'has_token', side_effect=[ProcessLookupError(3, 'temporary'), True]) as token, \
                patch.object(guest.time, 'sleep'):
            self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(token.call_count, 2)
        self.assertEqual(self.owner.receipt['proc_read_observations'][-1]['resolution'], 'complete_ownership_read')
        with patch.object(self.owner, 'has_token', side_effect=ProcessLookupError(3, 'still live')) as token, \
                patch.object(guest.time, 'sleep') as wait:
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'live Wine ownership'):
                self.owner.inspect(123, time.monotonic() + .001)
        token.assert_called_once()
        wait.assert_not_called()

    def test_identity_recheck_failure_keeps_original_error_and_recheck_operation(self):
        original = self.owner.process_stat.side_effect
        def read(path):
            self.owner.process_stat.side_effect = lambda selected: (
                (_ for _ in ()).throw(OSError(5, 'private recheck text'))
                if selected == self.task else original(selected))
            raise ProcessLookupError(3, 'private original text')
        with patch.object(self.owner, 'has_token', side_effect=read), \
                patch.object(guest.os, 'pidfd_open', return_value=19), patch.object(guest.os, 'close'), \
                patch.object(guest.signal, 'pidfd_send_signal') as send:
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'live Wine ownership'):
                self.owner.signal_owned({'proc_pid': 123, 'pid': 123, 'starttime': 10}, signal.SIGTERM,
                                        time.monotonic() + 1)
            send.assert_not_called()
        self.assertEqual(self.owner.receipt['inspection_failures'], 1)
        failure = self.owner.receipt['last_inspection_failure']
        self.assertEqual((failure['operation'], failure['error_type'], failure['errno']),
                         ('worker_environment', 'ProcessLookupError', 3))
        self.assertEqual((failure['recheck_operation'], failure['recheck_error_type'], failure['recheck_errno']),
                         ('worker_identity_after_read', 'OSError', 5))
        self.assertNotIn('private', json.dumps(failure))

    def test_esrch_recheck_permission_failure_cannot_be_skipped_as_hidden_foreign_uid(self):
        original_stat = self.owner.process_stat.side_effect
        def read(path):
            self.owner.status.side_effect = PermissionError(13, 'now hidden')
            self.owner.process_stat.side_effect = lambda selected: (
                (_ for _ in ()).throw(PermissionError(13, 'recheck hidden'))
                if selected == self.task else original_stat(selected))
            raise ProcessLookupError(3, 'initial environment failure')
        with patch.object(self.owner, 'has_token', side_effect=read):
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'live Wine ownership'):
                self.owner.cleanup(time.monotonic() + 1)
        self.assertFalse(self.owner.receipt['complete'])
        self.assertEqual(self.owner.receipt['inspection_failures'], 1)
        failure = self.owner.receipt['last_inspection_failure']
        self.assertEqual((failure['error_type'], failure['errno']), ('ProcessLookupError', 3))
        self.assertEqual((failure['recheck_error_type'], failure['recheck_errno']), ('PermissionError', 13))

    def test_worker_esrch_exit_does_not_skip_remaining_live_worker(self):
        another = self.group / 'task/125'
        another.mkdir()
        next_worker = {**self.worker, 'pid': 125, 'starttime': 12}
        self.owner.process_stat.side_effect = lambda path: dict(
            self.leader if path == self.group else next_worker if path == another else self.worker)
        self.owner.status.side_effect = lambda path: dict(self.status if path == self.group else
            {**self.worker_status, 'pid': 125} if path == another else self.worker_status)
        def read(path):
            if path == self.task:
                self.worker['state'] = 'Z'
                raise ProcessLookupError(3, 'worker exiting')
            return True
        with patch.object(self.owner, 'has_token', side_effect=read), \
                patch.object(self.owner, 'live_tasks', return_value=iter([(self.task, dict(self.worker)),
                                                                       (another, next_worker)])):
            self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(self.owner.owned_workers, {(123, 10, 125, 12)})
        self.assertEqual(self.owner.receipt['worker_exit_rechecks'], 1)

    def test_worker_esrch_retry_is_bounded_and_persistent_failure_is_counted(self):
        with patch.object(self.owner, 'has_token', side_effect=ProcessLookupError(3, 'not gone')) as read, \
                patch.object(guest.time, 'sleep') as wait:
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'live Wine ownership'):
                self.owner.cleanup(time.monotonic() + 1)
        self.assertEqual(read.call_count, 3)
        self.assertEqual(wait.call_count, 2)
        self.assertEqual(self.owner.receipt['proc_read_retries'], 2)
        self.assertEqual(self.owner.receipt['inspection_failures'], 1)
        self.assertFalse(self.owner.receipt['complete'])
        self.assertEqual(self.owner.receipt['last_inspection_failure']['operation'], 'worker_environment')

    def test_esrch_rechecks_never_authorize_changed_worker_group_or_membership(self):
        for changed, field in ((self.worker, 'starttime'), (self.leader, 'starttime'),
                               (self.worker_status, 'tgid')):
            original = changed[field]
            before = self.owner.receipt['inspection_failures']
            def read(path):
                changed[field] += 1
                raise ProcessLookupError(3, 'identity changed')
            with self.subTest(field=field, pid=changed['pid']), \
                    patch.object(self.owner, 'has_token', side_effect=read), patch.object(guest.time, 'sleep'), \
                    patch.object(guest.os, 'pidfd_open', return_value=19), patch.object(guest.os, 'close'), \
                    patch.object(guest.signal, 'pidfd_send_signal') as send, patch.object(guest.os, 'kill') as kill:
                with self.assertRaises(guest.base.DiagnosticError):
                    self.owner.signal_owned({'proc_pid': 123, 'pid': 123, 'starttime': 10}, signal.SIGTERM,
                                            time.monotonic() + 1)
                send.assert_not_called()
                kill.assert_not_called()
            self.assertEqual(self.owner.receipt['inspection_failures'], before + 1)
            changed[field] = original
        # A later clean sweep can release resources; it cannot erase earlier
        # uncertainty from the cumulative native acceptance guard.
        self.worker['state'] = 'Z'
        self.owner.cleanup(time.monotonic() + 1)
        self.assertTrue(self.owner.receipt['complete'])
        self.assertEqual(self.owner.receipt['inspection_failures'], 3)

    def test_task_iteration_esrch_is_not_swallowed_in_signal_recheck_or_fallback(self):
        candidate = {'proc_pid': 123, 'pid': 123, 'starttime': 10}
        for fallback in (False, True):
            before = self.owner.receipt['inspection_failures']
            with self.subTest(fallback=fallback), contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(guest.base.WineProcessOwner, 'live_tasks',
                                                side_effect=ProcessLookupError(3, 'directory unavailable')))
                if fallback:
                    stack.enter_context(patch.object(self.owner, 'inspect', return_value=None))
                stack.enter_context(patch.object(guest.os, 'pidfd_open', return_value=19))
                stack.enter_context(patch.object(guest.os, 'close'))
                send = stack.enter_context(patch.object(guest.signal, 'pidfd_send_signal'))
                kill = stack.enter_context(patch.object(guest.os, 'kill'))
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'live Wine ownership'):
                    self.owner.signal_owned(candidate, signal.SIGTERM, time.monotonic() + 1)
                send.assert_not_called()
                kill.assert_not_called()
            self.assertEqual(self.owner.receipt['inspection_failures'], before + 1)
            self.assertEqual(self.owner.receipt['last_inspection_failure']['operation'], 'task_inspection')

    def test_terminal_error_survives_observation_saturation_and_keeps_operation(self):
        for _ in range(self.owner.OBSERVATION_LIMIT + 2):
            self.owner.observe_proc({'operation': 'stat', 'resolution': 'task_disappeared'})
        self.leader['state'] = 'S'
        with patch.object(guest.base.WineProcessOwner, 'has_token', side_effect=OSError(5, 'secret contents')):
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Cannot verify Wine descendant'):
                self.owner.cleanup(time.monotonic() + 1)
        failure = self.owner.receipt['last_inspection_failure']
        self.assertEqual((failure['operation'], failure['error_type'], failure['errno']), ('environment', 'OSError', 5))
        self.assertEqual(failure['group_pid'], 123)
        self.assertEqual(self.owner.receipt['inspection_failures'], 1)
        self.assertEqual(len(self.owner.receipt['proc_read_observations']), self.owner.OBSERVATION_LIMIT)
        self.assertNotIn('secret contents', json.dumps(self.owner.receipt))

    def test_malformed_status_or_stat_remains_a_failure_with_sanitized_operation(self):
        for operation in ('status', 'process_stat'):
            with self.subTest(operation=operation), \
                    patch.object(guest.base.WineProcessOwner, operation, side_effect=ValueError('private data')):
                # Bypass the synthetic identity fixture to exercise real candidate read wrappers.
                with patch.object(self.owner, operation, side_effect=lambda path:
                        getattr(guest.DeviceWineProcessOwner, operation)(self.owner, path)):
                    with self.assertRaisesRegex(guest.base.DiagnosticError, 'Cannot verify Wine descendant'):
                        self.owner.cleanup(time.monotonic() + 1)
            self.assertEqual(self.owner.receipt['last_inspection_failure']['operation'],
                             'stat' if operation == 'process_stat' else 'status')
            self.assertEqual(self.owner.receipt['last_inspection_failure']['error_type'], 'ValueError')
            self.assertNotIn('private data', json.dumps(self.owner.receipt))

    def test_vanished_worker_is_checked_without_treating_a_live_denial_as_dead(self):
        original = self.owner.process_stat.side_effect
        def denied(path):
            def vanished(selected):
                if selected == self.task:
                    raise FileNotFoundError('worker disappeared')
                return original(selected)
            self.owner.process_stat.side_effect = vanished
            raise PermissionError(13, 'worker exiting')
        with patch.object(self.owner, 'has_token', side_effect=denied):
            self.assertIsNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(self.owner.receipt['permission_observations'][0]['resolution'], 'verified_disappearance')
        self.assertEqual(self.owner.receipt['worker_exit_rechecks'], 1)

    def test_transient_denial_requires_fresh_complete_token_group_and_identity_reads(self):
        with patch.object(self.owner, 'has_token', side_effect=[PermissionError(13, 'transient'), True]) as token, \
                patch.object(guest.time, 'sleep') as wait:
            result = self.owner.inspect(123, time.monotonic() + 1)
        self.assertEqual(result, {'proc_pid': 123, 'pid': 123, 'starttime': 10})
        self.assertEqual(token.call_count, 2)
        wait.assert_called_once_with(self.owner.PERMISSION_PAUSE)
        self.assertEqual(self.owner.receipt['permission_read_retries'], 1)
        self.assertEqual(self.owner.receipt['owned_live_workers'], 1)
        self.assertEqual(self.owner.receipt['permission_observations'][0]['resolution'], 'complete_ownership_read')
        encoded = json.dumps(self.owner.receipt)
        self.assertNotIn(self.owner.environment[self.owner.ENV_KEY], encoded)
        self.assertNotIn('transient', encoded, 'Raw exception messages must not enter ownership evidence')

    def test_persistently_inaccessible_live_worker_still_fails_cleanup(self):
        with patch.object(self.owner, 'has_token', side_effect=PermissionError(13, 'private-token must not be exposed')) as read, \
                patch.object(guest.time, 'sleep') as wait, patch.object(guest.os, 'kill') as kill:
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Cannot inspect same-UID'):
                self.owner.cleanup(time.monotonic() + 1)
        self.assertEqual(read.call_count, 3)
        self.assertEqual(wait.call_count, 2)
        self.assertFalse(self.owner.receipt['complete'])
        self.assertEqual(self.owner.receipt['inspection_failures'], 1)
        self.assertEqual(self.owner.receipt['permission_observations'][-1]['resolution'], 'persistent_live_permission_denied')
        kill.assert_not_called()

    def test_permission_retry_never_extends_cleanup_deadline(self):
        with patch.object(self.owner, 'has_token', side_effect=PermissionError(13, 'denied')) as read, \
                patch.object(guest.time, 'sleep') as wait:
            with self.assertRaises(PermissionError):
                self.owner.inspect(123, time.monotonic() + .001)
        self.assertEqual(read.call_count, 1)
        wait.assert_not_called()

    def test_worker_or_group_pid_reuse_during_denial_cannot_authorize_signal(self):
        candidate = {'proc_pid': 123, 'pid': 123, 'starttime': 10}
        for changed in (self.worker, self.leader):
            def denied(path):
                changed['starttime'] += 1
                raise PermissionError(13, 'identity changed')
            with self.subTest(pid=changed['pid']), patch.object(self.owner, 'has_token', side_effect=denied), \
                    patch.object(guest.os, 'pidfd_open', return_value=19), patch.object(guest.os, 'close'), \
                    patch.object(guest.signal, 'pidfd_send_signal') as send, patch.object(guest.os, 'kill') as kill:
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'identity changed'):
                    self.owner.signal_owned(candidate, signal.SIGTERM, time.monotonic() + 1)
                send.assert_not_called()
                kill.assert_not_called()
            self.worker['starttime'], self.leader['starttime'] = 11, 10

    def test_wrong_worker_group_on_retry_cannot_authorize_signal(self):
        def denied(path):
            self.worker_status['tgid'] = 999
            raise PermissionError(13, 'temporary')
        with patch.object(self.owner, 'has_token', side_effect=denied), patch.object(guest.time, 'sleep'), \
                patch.object(guest.os, 'pidfd_open', return_value=19), patch.object(guest.os, 'close'), \
                patch.object(guest.signal, 'pidfd_send_signal') as send, patch.object(guest.os, 'kill') as kill:
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'group membership'):
                self.owner.signal_owned({'proc_pid': 123, 'pid': 123, 'starttime': 10}, signal.SIGTERM,
                                        time.monotonic() + 1)
            send.assert_not_called()
            kill.assert_not_called()

    def test_namespace_denial_retries_full_read_but_wrong_namespace_or_token_cannot_signal(self):
        self.owner.direct_pid_view = False
        self.owner.namespace_depth = 2
        self.owner.namespace = 'pid:[111]'
        self.status['namespace_pids'] = [123, 456]
        self.worker_status['namespace_pids'] = [124, 457]
        candidate = {'proc_pid': 123, 'pid': 456, 'starttime': 10}
        with patch.object(guest.os, 'readlink', side_effect=[PermissionError(13, 'transient'), 'pid:[111]']), \
                patch.object(self.owner, 'has_token', return_value=True), patch.object(guest.time, 'sleep'):
            self.assertEqual(self.owner.inspect(123, time.monotonic() + 1), candidate)
        self.assertEqual(self.owner.receipt['permission_observations'][0]['operation'], 'worker_pid_namespace')
        for namespace, token in (('pid:[222]', True), ('pid:[111]', False)):
            with self.subTest(namespace=namespace, token=token), \
                    patch.object(guest.os, 'readlink', return_value=namespace), \
                    patch.object(self.owner, 'has_token', return_value=token), \
                    patch.object(guest.os, 'pidfd_open', return_value=19), patch.object(guest.os, 'close'), \
                    patch.object(guest.signal, 'pidfd_send_signal') as send, patch.object(guest.os, 'kill') as kill:
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'identity changed'):
                    self.owner.signal_owned(candidate, signal.SIGTERM, time.monotonic() + 1)
                send.assert_not_called()
                kill.assert_not_called()

    def test_group_denial_keeps_context_and_failure_without_worker_fallback(self):
        self.leader['state'] = 'S'
        with patch.object(self.owner, 'has_token', side_effect=PermissionError(13, 'group inaccessible')), \
                patch.object(self.owner, 'inspect_dead_leader', side_effect=AssertionError('unsafe fallback')):
            with self.assertRaises(PermissionError):
                self.owner.inspect(123, time.monotonic() + 1)
        observation = self.owner.receipt['permission_observations'][0]
        self.assertEqual(observation['operation'], 'group_inspection')
        self.assertEqual(observation['resolution'], 'unresolved_group_permission_denied')
        self.assertEqual(observation['group_pid'], 123)

    def test_hidden_foreign_processes_do_not_fill_permission_evidence_budget(self):
        for statuses in ([PermissionError(13, 'hidden')] * 3,
                         [PermissionError(13, 'initial denial'), {'uid': 999}, {'uid': 999}]):
            with self.subTest(statuses=statuses), patch.object(self.owner, 'status', side_effect=statuses):
                self.assertEqual(self.owner.scan(time.monotonic() + 1), [])
            self.assertEqual(self.owner.receipt['permission_observations'], [])
            self.assertEqual(self.owner.receipt['permission_observations_omitted'], 0)
            self.assertEqual(self.owner.receipt['inspection_failures'], 0)

    def test_optional_sampler_cannot_mutate_main_nested_permission_evidence(self):
        diagnostic = SimpleNamespace(ctx=self.context, wine_owner=self.owner, wine_started=True)
        sampler = guest.WineMemorySampler(diagnostic)
        before = copy.deepcopy(self.owner.receipt)
        sampler.scanner.observe_permission(self.leader, self.worker, 'worker_environment', PermissionError(13, 'denied'), 1)
        sampler.scanner.receipt['inspection_failures'] += 1
        sampler.scanner.dead_leaders.add((123, 10))
        self.assertEqual(self.owner.receipt, before)
        self.assertEqual(self.owner.dead_leaders, set())
        self.assertIs(type(sampler.scanner), guest.DeviceWineProcessOwner)

    def test_later_cleanup_cannot_amend_prior_restart_permission_observations(self):
        self.owner.observe_permission(self.leader, self.worker, 'worker_environment', PermissionError(13, 'first'), 1)
        restart = dict(self.owner.receipt)
        self.owner.observe_permission(self.leader, self.worker, 'worker_status', PermissionError(13, 'later'), 1)
        self.assertEqual(len(restart['permission_observations']), 1)
        self.assertEqual(len(self.owner.receipt['permission_observations']), 2)

    def test_real_dead_leader_worker_is_reaped_and_unrelated_same_shape_sentinel_survives(self):
        # Reuse the existing native pthread fixture and its actual pipe/PID
        # assertions, changing only the ownership implementation under test.
        spec = importlib.util.spec_from_file_location('atlas_base_owner_tests', ROOT / 'tools/android/test_diagnostic.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        case = module.WineProcessOwnerTests('test_dead_leader_live_worker_is_reaped_and_same_shape_sentinel_survives')
        case.setUp()
        try:
            class ExitRaceOwner(guest.DeviceWineProcessOwner):
                injected = False
                def has_token(self, path):
                    if 'task' in path.parts and not self.injected:
                        self.injected = True
                        raise ProcessLookupError(3, 'simulated worker read race')
                    return super().has_token(path)
            case.owner = ExitRaceOwner(case.context)
            case.test_dead_leader_live_worker_is_reaped_and_same_shape_sentinel_survives()
            self.assertTrue(case.owner.injected)
            self.assertEqual(case.owner.receipt['proc_read_retries'], 1)
        finally:
            case.doCleanups()

    def test_constructed_device_diagnostic_uses_new_owner_and_matching_child_token(self):
        args = SimpleNamespace(execution_platform='android', listener_policy='device',
            assets=self.root / 'assets', import_contract=self.root / 'contract', game_data=self.root / 'imported',
            game_package=self.root / 'package', schema=self.root / 'schema',
            game_data_manifest=self.root / 'manifest', android_metadata=None)
        args.game_data_manifest.write_bytes(b'{}')
        package = {'repository_commit': guest.GAME_COMMIT, 'source_commit': guest.SOURCE_COMMIT,
            'data_commit': guest.DATA_COMMIT, 'dbserver_profile': 'loopback', 'game_listener_profile': 'loopback',
            'postgresql_persistence_fixture': False}
        initial_token = []
        def original_constructor(value, adapted, context):
            value.ctx = context
            value.wine_started = False
            value.wine_owner = guest.base.WineProcessOwner(context)
            value.wine_env = dict(value.wine_owner.environment)
            initial_token.append(value.wine_env[value.wine_owner.ENV_KEY])
        with patch.object(guest, 'candidate_metadata', return_value={'candidate_repository_commit': 'a' * 40}), \
                patch.object(guest, 'import_contract', return_value='b' * 64), \
                patch.object(guest, 'import_receipt', return_value={}), \
                patch.object(guest, 'pinned_json', return_value=package), \
                patch.object(guest, 'checked_file', side_effect=lambda path, limit: path), \
                patch.object(guest, 'DATA_MANIFEST_BYTES', 2), \
                patch.object(guest.base, 'file_hash', return_value=guest.DATA_MANIFEST_SHA256), \
                patch.object(guest.game.GameDiagnostic, '__init__', original_constructor):
            value = guest.DeviceGameDiagnostic(args, self.context)
        self.assertIs(type(value.wine_owner), guest.DeviceWineProcessOwner)
        key = value.wine_owner.ENV_KEY
        self.assertEqual(value.wine_env[key], value.wine_owner.environment[key])
        self.assertNotEqual(value.wine_env[key], initial_token[0])
        self.assertIs(type(self.context.memory_sampler.scanner), guest.DeviceWineProcessOwner)
        self.assertFalse(value.wine_started)


class RealProcExitTests(unittest.TestCase):
    def test_real_held_status_and_stat_fds_after_reaping_are_task_disappearance(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        handles = {}
        try:
            parent = guest.base.WineProcessOwner.process_stat(Path('/proc/self'))['pid']
            matches = []
            for path in Path('/proc').iterdir():
                if not path.name.isdecimal():
                    continue
                try:
                    status = guest.base.WineProcessOwner.status(path)
                    identity = guest.base.WineProcessOwner.process_stat(path)
                except (OSError, ValueError, KeyError, IndexError):
                    continue
                if identity['parent'] == parent and status['namespace_pids'][-1:] == [child.pid]:
                    matches.append(path)
            self.assertEqual(len(matches), 1, 'Must identify only the owned child')
            path = matches[0]
            for name in ('status', 'stat'):
                handles[name] = (path / name).open('rb', buffering=0)
            child.kill()
            child.wait(timeout=3)
            context = SimpleNamespace(secrets=[])
            owner = guest.DeviceWineProcessOwner(context)
            for name, handle in handles.items():
                with self.subTest(operation=name):
                    with self.assertRaises(ProcessLookupError):
                        handle.read(32768)
                    # Redirect only Path's input to the already-open real proc
                    # FD. The kernel, not a mocked exception, produces ESRCH.
                    with patch.object(Path, 'read_text', side_effect=lambda: handle.read(32768).decode()):
                        with self.assertRaises(FileNotFoundError):
                            (owner.status if name == 'status' else owner.process_stat)(path)
                    observed = owner.receipt['proc_read_observations'][-1]
                    self.assertEqual((observed['operation'], observed['errno']), (name, 3))
                    self.assertEqual(observed['resolution'], 'task_disappeared')
            self.assertEqual(owner.receipt['inspection_failures'], 0)
            self.assertIsNone(owner.receipt['last_inspection_failure'])
        finally:
            for handle in handles.values():
                handle.close()
            if child.poll() is None:
                child.kill()
                child.wait(timeout=3)


class ResourceAndCompletionTests(unittest.TestCase):
    def test_memory_samples_are_owned_bounded_and_do_not_modify_cleanup_observer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = SimpleNamespace(report={}, secrets=[], stage_name='game_services_first')
            owner = guest.base.WineProcessOwner(context, proc_root=root)
            diagnostic = SimpleNamespace(ctx=context, wine_owner=owner, wine_started=True)
            sampler = guest.WineMemorySampler(diagnostic)
            original = dict(owner.receipt)
            (root / '12').mkdir()
            (root / '12/status').write_text('VmRSS:\t123 kB\n')
            sampler.scanner.scan = Mock(return_value=[{'proc_pid': 12, 'starttime': 40}])
            sampler.scanner.process_stat = Mock(return_value={'pid': 12, 'starttime': 40, 'state': 'S'})
            sampler.sample()
            self.assertEqual(sampler.report['maximum_sampled_rss_kib'], 123)
            self.assertEqual(sampler.report['successful_samples'], 1)
            self.assertEqual(owner.receipt, original)
            self.assertIsNot(owner.receipt, sampler.scanner.receipt)
            sampler.sample()
            self.assertEqual(sampler.scanner.scan.call_count, 1)
            sampler.next_sample = 0
            sampler.scanner.scan.side_effect = PermissionError('unavailable')
            sampler.sample()
            self.assertEqual(sampler.report['unavailable_samples'], 1)
            self.assertFalse(sampler.report['instantaneous_peak_measured'])

    def test_reused_pid_is_not_counted_and_stop_precedes_resource_sampling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = guest.DeviceGameContext(root, 60)
            context.event = Mock()
            context.memory_sampler = Mock()
            context.cancel_requested = True
            with self.assertRaises(guest.base.Cancelled):
                context.check()
            context.memory_sampler.sample.assert_not_called()
            owner = guest.base.WineProcessOwner(context, proc_root=root)
            diagnostic = SimpleNamespace(ctx=context, wine_owner=owner, wine_started=True)
            sampler = guest.WineMemorySampler(diagnostic)
            (root / '12').mkdir()
            (root / '12/status').write_text('VmRSS: 999999 kB\n')
            sampler.scanner.scan = Mock(return_value=[{'proc_pid': 12, 'starttime': 40}])
            sampler.scanner.process_stat = Mock(return_value={'pid': 12, 'starttime': 41, 'state': 'S'})
            sampler.sample()
            self.assertIsNone(sampler.report['maximum_sampled_rss_kib'])
            self.assertEqual(sampler.report['unavailable_samples'], 1)

    def test_guest_android_flag_never_attests_device_and_cleanup_controls_success(self):
        for cleanup_failure in (False, True):
            with self.subTest(cleanup_failure=cleanup_failure), tempfile.TemporaryDirectory() as temporary:
                state = Path(temporary)
                diagnostic = Mock()
                diagnostic.cleanup_status = {'postgres_graceful': True, 'wine_prefix_stopped': True,
                                             'owned_processes_reaped': not cleanup_failure}
                diagnostic.cleanup.return_value = []
                with patch.object(guest, 'DeviceGameDiagnostic', return_value=diagnostic), \
                        patch.object(guest.signal, 'signal'), contextlib.redirect_stdout(io.StringIO()):
                    result = guest.main(['--execution-platform', 'android', '--state', str(state)])
                report = json.loads((state / 'latest-report.json').read_text())
                self.assertEqual(result, 1 if cleanup_failure else 0)
                for field in ('android_execution_validated', 'gameplay_validated', 'android_surface_validated',
                              'hardware_acceleration_validated', 'interactive_rendering_validated',
                              'android_listener_binding_validated'):
                    self.assertIs(report[field], False)
                diagnostic.cleanup.assert_called_once()
                diagnostic.export_captures.assert_called_once()
                diagnostic.export_service_captures.assert_called_once()

    def test_cancelled_execution_still_cleans_and_exports_current_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            diagnostic = Mock()
            diagnostic.execute.side_effect = guest.base.Cancelled('Stop requested')
            diagnostic.cleanup_status = dict.fromkeys(('postgres_graceful', 'wine_prefix_stopped', 'owned_processes_reaped'), True)
            diagnostic.cleanup.return_value = []
            with patch.object(guest, 'DeviceGameDiagnostic', return_value=diagnostic), \
                    patch.object(guest.signal, 'signal'), contextlib.redirect_stdout(io.StringIO()):
                result = guest.main(['--execution-platform', 'host', '--state', str(state)])
            report = json.loads((state / 'latest-report.json').read_text())
            self.assertEqual(result, 2)
            self.assertEqual(report['status'], 'cancelled')
            self.assertFalse(report['passed'])
            diagnostic.cleanup.assert_called_once()
            diagnostic.export_captures.assert_called_once()
            diagnostic.export_service_captures.assert_called_once()

    def test_stop_before_wine_distinguishes_never_started_from_failed_shutdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            real_type = guest.DeviceGameDiagnostic
            def initialized(args, context):
                # Exercise the real accepted cleanup with an initialized
                # workspace, before either PostgreSQL or Wine was launched.
                value = object.__new__(real_type)
                guest.base.Diagnostic.__init__(value, args, context)
                value.private_connections = []
                value.execute = Mock(side_effect=guest.base.Cancelled('Stop during input copy'))
                value.export_captures = Mock()
                value.export_service_captures = Mock()
                return value
            with patch.object(guest, 'DeviceGameDiagnostic', side_effect=initialized), \
                    patch.object(guest.signal, 'signal'), contextlib.redirect_stdout(io.StringIO()):
                result = guest.main(['--execution-platform', 'android', '--state', str(state)])
            report = json.loads((state / 'latest-report.json').read_text())
            self.assertEqual(result, 2)
            self.assertEqual(report['cleanup_execution'], {'diagnostic_initialized': True,
                'wine_started': False, 'postgres_started': False, 'owned_child_count': 0})
            self.assertEqual(report['cleanup'], {'postgres_graceful': False,
                'wine_prefix_stopped': False, 'owned_processes_reaped': True})
            self.assertTrue(report['cleanup_complete'])
            self.assertEqual(report['processes'], [])

    def test_preflight_failure_records_no_initialized_runtime_or_children(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            with patch.object(guest, 'DeviceGameDiagnostic', side_effect=guest.base.DiagnosticError('bad input')), \
                    patch.object(guest.signal, 'signal'), contextlib.redirect_stdout(io.StringIO()):
                result = guest.main(['--execution-platform', 'host', '--state', str(state)])
            report = json.loads((state / 'latest-report.json').read_text())
            self.assertEqual(result, 1)
            self.assertEqual(report['cleanup_execution'], {'diagnostic_initialized': False,
                'wine_started': False, 'postgres_started': False, 'owned_child_count': 0})
            self.assertTrue(report['cleanup_complete'])

    def test_cleanup_facts_keep_prior_starts_and_include_stop_helper_children(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            def child(label):
                return SimpleNamespace(label=label, process=SimpleNamespace(poll=lambda: 0),
                    reader=SimpleNamespace(is_alive=lambda: False), writer=SimpleNamespace(is_alive=lambda: False))
            def initialized(args, context):
                value = Mock()
                value.wine_started = True
                value.execute.side_effect = guest.base.Cancelled('stop')
                context.children.append(child('postgres_first_start'))
                value.cleanup_status = dict.fromkeys(('postgres_graceful', 'wine_prefix_stopped', 'owned_processes_reaped'), True)
                def cleanup():
                    value.wine_started = False
                    context.children.append(child('owned-wine-stop'))
                    return []
                value.cleanup.side_effect = cleanup
                return value
            with patch.object(guest, 'DeviceGameDiagnostic', side_effect=initialized), \
                    patch.object(guest.signal, 'signal'), contextlib.redirect_stdout(io.StringIO()):
                result = guest.main(['--execution-platform', 'android', '--state', str(state)])
            report = json.loads((state / 'latest-report.json').read_text())
            self.assertEqual(result, 2)
            self.assertEqual(report['cleanup_execution'], {'diagnostic_initialized': True,
                'wine_started': True, 'postgres_started': True, 'owned_child_count': 2})


if __name__ == '__main__':
    unittest.main()
