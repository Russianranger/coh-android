"""Boundaries of the isolated imported-data Android Atlas guest adapter."""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
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
