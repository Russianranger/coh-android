"""Execute opt-in archive/probe/fallback ownership and actual Android selection code."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_gpu_profile as gpu
import diagnostic as base
import game_device_diagnostic as device

JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
SESSION = '0123456789abcdef0123456789abcdef'


def native_result():
    return {'format': 1, 'pointer_bits': 64, 'status': 'passed', 'failure_stage': '',
        'vendor_id': 0x5143, 'device_id': 0x43050a01, 'device_type': 1, 'api_version': (1 << 22) | (2 << 12),
        'driver_version': 26 << 22, 'driver_id': 18, 'native_gpu_executed': True, 'fill_verified': True,
        'bytes_verified': 4096, 'expected_bytes': 4096, 'elapsed_ms': 20,
        'kgsl_chip_id': 0x43050a01, 'kgsl_verified': True}


def wgl_result():
    value = {'format': 1, 'pointer_bits': 32, 'scope': 'bounded_wgl_gpu_prerequisites', 'status': 'passed',
        'passed': True, 'failure': '', 'win32_error': 0, 'gl_error': 0, 'gl_vendor': 'Mesa',
        'gl_renderer': 'zink Vulkan 1.3(Turnip Adreno 740)', 'gl_version': '4.6 Mesa',
        'fp_max_local_parameters': 32, 'fp_max_temporaries': 17, 'fp_max_native_temporaries': 17}
    value['build_marker'] = 'COH_GPU_PROBE_BUILD:production'
    value.update({key: True for key in gpu.WGL_TRUE})
    value.update({key: False for key in gpu.AUTHORITY_FALSE})
    return value


def marker(prefix, value):
    return prefix + json.dumps(value) + '\n'


def archive_fixture(path, mutate=None, extras=None):
    content = {name: ('payload-' + name).encode() for name in gpu.MEMBERS - {gpu.MANIFEST}}
    files = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                   'mode': 0o755 if name == 'coh-vulkan-gpu-probe' else 0o644}
             for name, raw in content.items()}
    manifest = {'format': 1, 'role': 'client_hardware_renderer', 'repository_commit': 'a' * 40,
        'run_url': 'https://github.com/Russianranger/coh-android/actions/runs/123',
        'mesa_version': '26.0.0', 'mesa_source_sha256': gpu.MESA_SOURCE_SHA256,
        'platform': 'linux-arm64-gnu-bookworm', 'driver': 'turnip_kgsl', 'gpu': 'Adreno740',
        'files': files, 'software_default': True, 'physical_hardware_validated': False}
    if mutate:
        mutate(manifest, content)
    content[gpu.MANIFEST] = json.dumps(manifest).encode()
    with zipfile.ZipFile(path, 'w') as archive:
        for name, raw in content.items():
            entry = zipfile.ZipInfo(name)
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, raw)
        for entry, raw in extras or []:
            archive.writestr(entry, raw)
    return hashlib.sha256(path.read_bytes()).hexdigest(), manifest


def make_owner(directory, requested='turnip'):
    assets = directory / 'assets'; assets.mkdir()
    work = directory / 'diagnostic'; work.mkdir()
    digest, _ = archive_fixture(assets / gpu.ARCHIVE)
    report = {'asset_sha256': {gpu.ARCHIVE: digest}, 'client_renderer_attribution': {
        'verified': True, 'client_executable_sha256': gpu.GAME_SHA256, 'repository_commit': gpu.GAME_SOURCE_COMMIT}}
    owner = SimpleNamespace(root=work, args=SimpleNamespace(session_id=SESSION, assets=assets,
        wine=directory / 'wine', wineserver=directory / 'wineserver'), ctx=mock.Mock(report=report),
        client_renderer_attribution=True, client_executable_sha256=gpu.GAME_SHA256)
    baseline = {'COH_CLIENT_GPU_PROFILE': requested, 'DISPLAY': ':101', 'WINEPREFIX': '/accepted-prefix',
        'COH_CLIENT_GRAPHICS_PROFILE': 'performance', 'COH_WINE_SESSION': 'original-token',
        'FEX_ROOTFS': '/retained-fex', 'COH_CLIENT_FRAME_TIMING': '1',
        'MESA_GL_VERSION_OVERRIDE': '9.9', 'GALLIUM_DRIVER': 'llvmpipe', 'LIBGL_ALWAYS_SOFTWARE': '1'}
    return owner, baseline


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_exact_closed_archive_and_private_modes_are_verified(self):
        path = self.directory / gpu.ARCHIVE; digest, manifest = archive_fixture(path)
        destination = self.directory / 'out'
        result = gpu.verify_archive(path, digest, destination)
        self.assertEqual(result['manifest'], manifest)
        self.assertEqual(result['archive_sha256'], digest)
        self.assertEqual({file.name for file in destination.iterdir()}, gpu.MEMBERS)
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)
        for name, pin in manifest['files'].items():
            self.assertEqual(stat.S_IMODE((destination / name).stat().st_mode), pin['mode'])
            self.assertEqual(hashlib.sha256((destination / name).read_bytes()).hexdigest(), pin['sha256'])

    def test_foreign_source_scope_modes_sizes_and_member_pins_are_rejected(self):
        mutations = [lambda m, c: m.update(mesa_source_sha256='f' * 64),
            lambda m, c: m.update(format=True), lambda m, c: m.update(physical_hardware_validated=True),
            lambda m, c: m.update(driver='llvmpipe'), lambda m, c: m.update(platform='android-bionic'),
            lambda m, c: m['files']['coh-gpu-probe.exe'].update(mode=0o755),
            lambda m, c: m['files']['coh-gpu-probe.exe'].update(bytes=True),
            lambda m, c: m['files']['coh-gpu-probe.exe'].update(sha256='e' * 64),
            lambda m, c: m['files'].pop('THIRD_PARTY_NOTICES.md')]
        for index, mutation in enumerate(mutations):
            path = self.directory / ('bad-' + str(index) + '.zip')
            digest, _ = archive_fixture(path, mutate=mutation)
            with self.subTest(index=index), self.assertRaises(gpu.GPUProfileError):
                gpu.verify_archive(path, digest, self.directory / ('out-' + str(index)))

    def test_missing_asset_pin_link_and_foreign_archive_bytes_are_rejected(self):
        path = self.directory / gpu.ARCHIVE; digest, _ = archive_fixture(path)
        for expected in (None, '', 'a' * 64):
            with self.subTest(expected=expected), self.assertRaises(gpu.GPUProfileError):
                gpu.verify_archive(path, expected, self.directory / 'out')
        link = self.directory / 'linked.zip'; link.symlink_to(path)
        with self.assertRaises(gpu.GPUProfileError): gpu.verify_archive(link, digest, self.directory / 'out')

    def test_duplicate_traversal_and_linked_members_are_rejected(self):
        for name in ('../escape', '/absolute', 'coh-gpu-probe.exe', 'extra-file'):
            path = self.directory / ('extra-' + str(len(name)) + '.zip')
            with mock.patch('warnings.warn'):
                digest, _ = archive_fixture(path, extras=[(name, b'bad')])
            with self.subTest(name=name), self.assertRaises(gpu.GPUProfileError):
                gpu.verify_archive(path, digest, self.directory / 'out')
        path = self.directory / 'link-member.zip'; _, manifest = archive_fixture(path)
        with zipfile.ZipFile(path) as archive: contents = {name: archive.read(name) for name in archive.namelist()}
        with zipfile.ZipFile(path, 'w') as archive:
            for name, raw in contents.items():
                entry = zipfile.ZipInfo(name)
                entry.external_attr = ((stat.S_IFLNK | 0o777) if name == 'coh-gpu-probe.exe' else stat.S_IFREG | 0o644) << 16
                archive.writestr(entry, raw)
        with self.assertRaises(gpu.GPUProfileError):
            gpu.verify_archive(path, hashlib.sha256(path.read_bytes()).hexdigest(), self.directory / 'out')

    def test_existing_destination_cannot_replace_prior_files(self):
        path = self.directory / gpu.ARCHIVE; digest, _ = archive_fixture(path)
        destination = self.directory / 'out'; destination.mkdir(); (destination / 'preserved').write_bytes(b'prior')
        with self.assertRaises(gpu.GPUProfileError): gpu.verify_archive(path, digest, destination)
        self.assertEqual((destination / 'preserved').read_bytes(), b'prior')


class ProbeTests(unittest.TestCase):
    def test_only_hardware_kgsl_turnip_with_real_fill_receipt_is_accepted(self):
        value = native_result()
        self.assertEqual(gpu.validate_vulkan_probe(marker(gpu.NATIVE_PREFIX, value)), value)
        for chip in (0x43050b00, 0x07040000, 0x070400ff):
            changed = dict(value, device_id=chip, kgsl_chip_id=chip)
            self.assertEqual(gpu.validate_vulkan_probe(marker(gpu.NATIVE_PREFIX, changed)), changed)

    def test_cpu_spoofing_raw_id_mismatch_partial_execution_and_untyped_native_fields_rejected(self):
        value = native_result()
        variants = [('device_type', 4), ('vendor_id', 0), ('device_id', 740), ('kgsl_chip_id', 0x43050b00),
            ('kgsl_verified', 1), ('driver_id', 13), ('driver_version', 25 << 22), ('api_version', 1),
            ('native_gpu_executed', False), ('fill_verified', 1), ('bytes_verified', 4095), ('elapsed_ms', 60001)]
        for key, bad in variants:
            with self.subTest(key=key), self.assertRaises(gpu.GPUProfileError):
                gpu.validate_vulkan_probe(marker(gpu.NATIVE_PREFIX, dict(value, **{key: bad})))
        for key, item in value.items():
            if type(item) is int:
                for bad in (True, float(item), -1):
                    with self.subTest(key=key, bad=bad), self.assertRaises(gpu.GPUProfileError):
                        gpu.validate_vulkan_probe(marker(gpu.NATIVE_PREFIX, dict(value, **{key: bad})))

    def test_complete_real_win32_pixel_capability_receipt_required_without_game_authority(self):
        value = wgl_result(); self.assertEqual(gpu.validate_wgl_probe(marker(gpu.WGL_PREFIX, value)), value)
        for key in gpu.WGL_TRUE:
            for bad in (False, 1, 1.0, None):
                with self.subTest(key=key, bad=bad), self.assertRaises(gpu.GPUProfileError):
                    gpu.validate_wgl_probe(marker(gpu.WGL_PREFIX, dict(value, **{key: bad})))
        for key in gpu.AUTHORITY_FALSE:
            with self.subTest(key=key), self.assertRaises(gpu.GPUProfileError):
                gpu.validate_wgl_probe(marker(gpu.WGL_PREFIX, dict(value, **{key: True})))
        for key, bad in [('fp_max_native_temporaries', 16), ('fp_max_temporaries', 16),
                ('fp_max_local_parameters', 31), ('pointer_bits', True), ('win32_error', 1), ('gl_error', 1),
                ('gl_renderer', 'zink llvmpipe'), ('gl_renderer', 'lavapipe'), ('gl_renderer', 'Adreno 740')]:
            with self.subTest(key=key, bad=bad), self.assertRaises(gpu.GPUProfileError):
                gpu.validate_wgl_probe(marker(gpu.WGL_PREFIX, dict(value, **{key: bad})))
        with self.assertRaises(gpu.GPUProfileError):
            gpu.validate_wgl_probe(marker(gpu.WGL_PREFIX, dict(value, build_marker='COH_GPU_PROBE_BUILD:host_fixture')))

    def test_duplicate_json_duplicate_marker_incomplete_and_oversized_output_fail_closed(self):
        valid = marker(gpu.WGL_PREFIX, wgl_result())
        cases = [valid + valid, '', valid[:-2], valid.replace('"format": 1', '"format": 1, "format": 1'),
                 'x' * (gpu.PROBE_OUTPUT_LIMIT + 1) + valid]
        for output in cases:
            with self.subTest(size=len(output)), self.assertRaises((gpu.GPUProfileError, ValueError)):
                gpu.validate_wgl_probe(output)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.owner, self.baseline = make_owner(self.directory)

    def test_software_default_never_reads_driver_or_starts_probe_and_keeps_exact_environment(self):
        self.baseline['COH_CLIENT_GPU_PROFILE'] = 'software'
        before = copy.deepcopy(self.baseline)
        with mock.patch.object(gpu, 'verify_archive', side_effect=AssertionError('Software opened GPU archive')):
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                self.assertEqual(gpu.apply_profile(self.owner, self.baseline, label), before)
        self.owner.ctx.start.assert_not_called()
        self.assertEqual(self.baseline, before)
        self.assertEqual(self.owner.ctx.report['client_gpu_profile']['state'], 'software_default')

    def test_candidate_clears_all_forcing_flags_only_on_its_clone(self):
        baseline = dict(self.baseline, MESA_GLSL_VERSION_OVERRIDE='9.9', LIBGL_KOPPER_DISABLE='1',
            TU_FORCE_GPU_ID='FD740', MESA_VK_DEVICE_SELECT='fake', VK_INSTANCE_LAYERS='fake',
            ZINK_DEBUG='fake', __GLX_VENDOR_LIBRARY_NAME='fake', LP_NUM_THREADS='1')
        before = dict(baseline)
        candidate = gpu.candidate_environment(baseline, '/owned/icd.json')
        for key in ('MESA_GLSL_VERSION_OVERRIDE', 'MESA_GL_VERSION_OVERRIDE', 'LIBGL_KOPPER_DISABLE',
                'TU_FORCE_GPU_ID', 'MESA_VK_DEVICE_SELECT', 'VK_INSTANCE_LAYERS', 'ZINK_DEBUG',
                '__GLX_VENDOR_LIBRARY_NAME', 'LP_NUM_THREADS', 'GALLIUM_DRIVER', 'LIBGL_ALWAYS_SOFTWARE'):
            self.assertNotIn(key, candidate)
        self.assertEqual(candidate['MESA_LOADER_DRIVER_OVERRIDE'], 'zink')
        self.assertEqual(candidate['MESA_VK_WSI_DEBUG'], 'sw')
        self.assertEqual(candidate['VK_DRIVER_FILES'], candidate['VK_ICD_FILENAMES'])
        for key in ('DISPLAY', 'WINEPREFIX', 'FEX_ROOTFS', 'COH_CLIENT_GRAPHICS_PROFILE', 'COH_CLIENT_FRAME_TIMING'):
            self.assertEqual(candidate[key], baseline[key])
        self.assertEqual(baseline, before)

    def test_qualified_initial_and_retry_require_both_probes_and_return_the_owned_environment(self):
        before = copy.deepcopy(self.baseline)
        def wine(_owner, environment, executable, directory, receipt):
            self.assertEqual(environment['WINEPREFIX'], '/accepted-prefix')
            self.assertEqual(executable.name, 'coh-gpu-probe.exe')
            receipt['probe_cleanup_safe'] = True
            return wgl_result()
        with (mock.patch.object(gpu, 'platform_is_arm64', return_value=True),
                mock.patch.object(base, 'arm64_elf'), mock.patch.object(base, 'verify_pe32'),
                mock.patch.object(gpu, 'run_probe', return_value=marker(gpu.NATIVE_PREFIX, native_result())) as native,
                mock.patch.object(gpu, 'private_wgl_probe', side_effect=wine) as wgl):
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                candidate = gpu.apply_profile(self.owner, self.baseline, label)
                receipt = self.owner.ctx.report['client_gpu_profile']
                self.assertEqual(receipt['selected'], 'turnip'); self.assertEqual(receipt['launch_label'], label)
                self.assertEqual(receipt['session_id'], SESSION)
                self.assertEqual(candidate['MESA_LOADER_DRIVER_OVERRIDE'], 'zink')
                for flag in ('game_rendering_validated', 'hardware_acceleration_validated', 'physical_fps_improvement_validated'):
                    self.assertIs(receipt[flag], False)
            self.assertEqual(native.call_count, 2); self.assertEqual(wgl.call_count, 2)
        self.assertEqual(self.baseline, before)
        self.assertNotEqual(self.owner.ctx.report['client_gpu_profile_attempts'][0]['candidate_environment']['VK_DRIVER_FILES'],
                            self.owner.ctx.report['client_gpu_profile_attempts'][1]['candidate_environment']['VK_DRIVER_FILES'])

    def test_rejected_native_or_gl_prerequisite_returns_fresh_unchanged_software_before_game(self):
        for phase in ('native', 'wgl'):
            directory = self.directory / phase; directory.mkdir(); owner, baseline = make_owner(directory)
            before = dict(baseline)
            with (mock.patch.object(gpu, 'platform_is_arm64', return_value=True),
                    mock.patch.object(base, 'arm64_elf'), mock.patch.object(base, 'verify_pe32'),
                    mock.patch.object(gpu, 'run_probe', return_value=marker(gpu.NATIVE_PREFIX,
                        dict(native_result(), device_type=4) if phase == 'native' else native_result())),
                    mock.patch.object(gpu, 'private_wgl_probe', side_effect=gpu.GPUProfileError('Unsupported GL'))):
                fallback = gpu.apply_profile(owner, baseline, 'actual-coh-client')
            self.assertEqual(fallback, before); self.assertIsNot(fallback, baseline)
            self.assertEqual(owner.ctx.report['client_gpu_profile']['state'], 'software_fallback')
            self.assertTrue(owner.ctx.report['client_gpu_profile']['fallback_reason'])
            owner.ctx.start.assert_not_called(); self.assertEqual(baseline, before)

    def test_cancellation_and_unproved_cleanup_cannot_return_fallback(self):
        for failure in (gpu.GPUCleanupError('Unsafe'), base.Cancelled('Stop')):
            with (mock.patch.object(gpu, 'platform_is_arm64', return_value=True),
                    mock.patch.object(gpu, 'verify_archive', side_effect=failure)):
                self.owner.ctx.check.side_effect = base.Cancelled('Stop') if isinstance(failure, base.Cancelled) else None
                with self.assertRaises(type(failure)): gpu.apply_profile(self.owner, self.baseline, 'actual-coh-client')
            self.owner.ctx.start.assert_not_called()

    def test_missing_current_game_producer_cannot_enable_gpu(self):
        for value in (False, True, 1, '1'):
            self.owner.client_renderer_attribution = value
            self.owner.ctx.report['client_renderer_attribution']['verified'] = 1
            fallback = gpu.apply_profile(self.owner, self.baseline, 'actual-coh-client')
            self.assertEqual(fallback, self.baseline)
            self.assertEqual(self.owner.ctx.report['client_gpu_profile']['selected'], 'software')
        self.owner.ctx.start.assert_not_called()

    def test_foreign_game_source_or_game_bytes_cannot_enable_gpu(self):
        for key, wrong in (('repository_commit', 'f' * 40), ('client_executable_sha256', 'e' * 64)):
            prior = dict(self.owner.ctx.report['client_renderer_attribution'])
            self.owner.ctx.report['client_renderer_attribution'][key] = wrong
            with mock.patch.object(gpu, 'verify_archive', side_effect=AssertionError('Foreign Game opened GPU payload')):
                self.assertEqual(gpu.apply_profile(self.owner, self.baseline, 'actual-coh-client'), self.baseline)
            self.owner.ctx.report['client_renderer_attribution'] = prior
        self.owner.ctx.start.assert_not_called()

    def test_created_payloads_retained_while_game_lives_then_removed_after_owned_cleanup(self):
        self.owner.cleanup_status = {'owned_processes_reaped': False}
        directory = self.owner.root / ('gpu-profile-' + SESSION + '-1')
        directory.mkdir(); (directory / 'driver').write_bytes(b'owned payload')
        gpu.record_directory(self.owner, directory)
        self.assertEqual(gpu.cleanup_directories(self.owner), [])
        self.assertTrue(directory.exists())
        self.owner.cleanup_status['owned_processes_reaped'] = True
        self.assertEqual(gpu.cleanup_directories(self.owner), [])
        self.assertFalse(directory.exists())

    def test_partially_extracted_payload_failure_is_owned_and_removed_after_process_cleanup(self):
        archive = self.owner.args.assets / gpu.ARCHIVE
        digest, _ = archive_fixture(archive, mutate=lambda manifest, content:
            manifest['files']['coh-gpu-probe.exe'].update(sha256='e' * 64))
        self.owner.ctx.report['asset_sha256'][gpu.ARCHIVE] = digest
        with mock.patch.object(gpu, 'platform_is_arm64', return_value=True):
            self.assertEqual(gpu.apply_profile(self.owner, self.baseline, 'actual-coh-client'), self.baseline)
        self.assertEqual(len(self.owner.gpu_profile_directories), 1)
        self.owner.cleanup_status = {'owned_processes_reaped': True}
        self.assertEqual(gpu.cleanup_directories(self.owner), [])
        self.assertFalse(self.owner.gpu_profile_directories[0][0].exists())

    def test_replaced_or_linked_payload_directory_cannot_delete_unowned_files(self):
        directory = self.owner.root / ('gpu-profile-' + SESSION + '-1'); directory.mkdir()
        gpu.record_directory(self.owner, directory)
        renamed = self.owner.root / 'original'; directory.rename(renamed)
        external = self.directory / 'preserved'; external.mkdir(); (external / 'data').write_bytes(b'keep')
        directory.symlink_to(external, target_is_directory=True)
        self.owner.cleanup_status = {'owned_processes_reaped': True}
        self.assertTrue(gpu.cleanup_directories(self.owner))
        self.assertEqual((external / 'data').read_bytes(), b'keep'); self.assertTrue(renamed.exists())

    def test_native_probe_stop_exception_or_open_reader_is_fatal_and_still_recorded(self):
        for stop_raises in (False, True):
            child = mock.Mock(started=0, output=bytearray(), overflow=False)
            child.process.poll.return_value = None
            child.reader.is_alive.return_value = True; child.writer.is_alive.return_value = False
            if stop_raises: child.stop.side_effect = RuntimeError('stop failed')
            owner = SimpleNamespace(ctx=mock.Mock())
            owner.ctx.start.return_value = child
            with self.subTest(stop_raises=stop_raises), self.assertRaises(gpu.GPUCleanupError):
                gpu.run_probe(owner, 'native-stop-unproved', ['/pinned/probe'], {}, 0)
            child.stop.assert_called_once(); owner.ctx.record.assert_called_once_with(child, refresh=True)

    def test_actual_owned_process_output_timeout_and_nonzero_exit_are_recorded_and_reaped(self):
        context = base.Context(self.directory, 30)
        context.event = mock.Mock()
        owner = SimpleNamespace(ctx=context)
        self.assertEqual(gpu.run_probe(owner, 'success', [sys.executable, '-c', 'print("actual")'], dict(os_environment()), 2), 'actual\n')
        for label, script, timeout in [('failure', 'raise SystemExit(7)', 2),
                ('overflow', 'print("x"*70000)', 2), ('timeout', 'import time;time.sleep(2)', .1)]:
            with self.subTest(label=label), self.assertRaises(gpu.GPUProfileError):
                gpu.run_probe(owner, label, [sys.executable, '-c', script], dict(os_environment()), timeout)
        self.assertTrue(all(child.process.poll() is not None and not child.reader.is_alive() and not child.writer.is_alive()
                            for child in context.children))
        self.assertEqual(len(context.report['processes']), 4)

    def test_wine_leader_exit_does_not_wait_for_initialization_services_stdout(self):
        context = base.Context(self.directory, 30); context.event = mock.Mock()
        owner = SimpleNamespace(ctx=context)
        script = 'import subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;time.sleep(3)"]);print("probe done")'
        try:
            child = gpu.run_probe(owner, 'cold-prefix-stdout', [sys.executable, '-c', script],
                                  os_environment(), 1, allow_background_output=True)
            self.assertEqual(child.process.poll(), 0)
            self.assertTrue(child.reader.is_alive())
            self.assertEqual(child.text(), 'probe done\n')
            self.assertTrue(child.completion['output_capture_open'])
            self.assertLess(child.completion['elapsed_seconds'], 1)
        finally:
            for owned in context.children: owned.stop()
        self.assertTrue(all(not owned.reader.is_alive() for owned in context.children))

    def test_isolated_wine_prefix_token_and_descendant_cleanup_never_touch_game_prefix(self):
        directory = self.directory / 'probe'; directory.mkdir()
        tokens = {'COH_WINE_SESSION': 'probe-only-token'}
        process_owner = mock.Mock(environment=tokens, receipt={'complete': True, 'remaining': 0})
        self.owner.ctx.secrets = []
        self.owner.ctx.run.return_value = {'exit_code': 0}
        receipt = {'probe_cleanup_safe': True}
        child = SimpleNamespace(reader=mock.Mock(), writer=mock.Mock(), output=bytearray(),
                                overflow=False, completion={'output_capture_open': True},
                                text=lambda: marker(gpu.WGL_PREFIX, wgl_result()))
        child.reader.is_alive.return_value = False; child.writer.is_alive.return_value = False
        with (mock.patch.object(device, 'DeviceWineProcessOwner', return_value=process_owner),
                mock.patch.object(gpu, 'run_probe', return_value=child) as probe):
            result = gpu.private_wgl_probe(self.owner, self.baseline, directory / 'coh-gpu-probe.exe', directory, receipt)
        environment = probe.call_args.args[3]
        self.assertEqual(environment['WINEPREFIX'], str(directory / 'wineprefix'))
        self.assertEqual(environment['COH_WINE_SESSION'], 'probe-only-token')
        self.assertEqual(self.baseline['WINEPREFIX'], '/accepted-prefix')
        self.assertEqual(self.baseline['COH_WINE_SESSION'], 'original-token')
        self.assertFalse((directory / 'wineprefix').exists())
        process_owner.cleanup.assert_called_once(); self.assertIs(receipt['probe_cleanup_safe'], True)
        self.assertEqual(result, wgl_result())

    def test_final_probe_owner_failure_marks_parent_cleanup_unsafe(self):
        owner = mock.Mock(); owner.args.wineserver = Path('/wine/wineserver')
        receipt = {'probe_cleanup_safe': False}
        process_owner = mock.Mock(receipt={'complete': False})
        process_owner.cleanup.side_effect = gpu.GPUProfileError('survivor')
        owner.gpu_probe_owners = [(process_owner, {'WINEPREFIX': '/probe-only'}, None, receipt)]
        self.assertTrue(gpu.cleanup_probes(owner)); self.assertIs(receipt['probe_cleanup_safe'], False)


def os_environment():
    import os
    return os.environ.copy()


def actual_method(text, signature):
    start = text.index(signature); cursor = text.index('{', start); depth = 1; end = cursor + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[start:end]


class AndroidSelectionTests(unittest.TestCase):
    def test_actual_selection_preferences_snapshot_and_receipt_gate_execute(self):
        source = (JAVA / 'ClientRuntime.java').read_text()
        methods = '\n'.join(actual_method(source, signature) for signature in
            ('public static String gpuProfileEnabled(', 'public static synchronized void setGpuProfileEnabled(',
             'private boolean gpuProfileReportMatches('))
        harness = r'''
import java.util.*;
public final class GPUProfileHost {
 static final class JSONObject extends HashMap<String,Object> {
  JSONObject putValue(String k,Object v){put(k,v);return this;}
  Object opt(String k){return get(k);} boolean isNull(String k){return !containsKey(k)||get(k)==null;}
  String optString(String k){Object v=get(k);return v instanceof String?(String)v:"";}
  String getString(String k){return (String)get(k);}
  JSONObject optJSONObject(String k){Object v=get(k);return v instanceof JSONObject?(JSONObject)v:null;}
  JSONObject getJSONObject(String k){return (JSONObject)get(k);}
 }
 static final class Context {
  static final int MODE_PRIVATE=0; String value; Context getSharedPreferences(String p,int mode){return this;}
  String getString(String key,String fallback){return value==null?fallback:value;}
  Context edit(){return this;} Context putString(String key,String v){value=v;return this;} void apply(){}
 }
 static boolean active; static boolean operationInProgress(){return active;}
 String session="owned",gpuProfileRequested="software"; JSONObject manifest=new JSONObject();
 ACTUAL_METHODS
 static void require(boolean ok){if(!ok)throw new AssertionError();}
 static JSONObject receipt(String requested,String selected,String state){
  JSONObject r=new JSONObject().putValue("format",1).putValue("session_id","owned")
   .putValue("requested",requested).putValue("selected",selected).putValue("state",state)
   .putValue("launch_label","actual-coh-client").putValue("probe_cleanup_safe",true);
  for(String f:new String[]{"shared_wine_environment_modified","game_prefix_modified_by_probe",
   "game_rendering_validated","hardware_acceleration_validated","physical_fps_improvement_validated",
   "automatic_mid_game_fallback"})r.putValue(f,false);return r;
 }
 public static void main(String[] args)throws Exception {
  Context c=new Context();require(gpuProfileEnabled(c).equals("software"));c.value="hostile";
  require(gpuProfileEnabled(c).equals("software"));setGpuProfileEnabled(c,"turnip");require(c.value.equals("turnip"));
  active=true;setGpuProfileEnabled(c,"software");require(c.value.equals("turnip"));active=false;
  try{setGpuProfileEnabled(c,"hostile");throw new AssertionError();}catch(IllegalArgumentException expected){}
  GPUProfileHost owner=new GPUProfileHost();
  JSONObject r=receipt("software","software","software_default"),report=new JSONObject().putValue("client_gpu_profile",r);
  require(owner.gpuProfileReportMatches(report));r.putValue("format",true);require(!owner.gpuProfileReportMatches(report));r.putValue("format",1);
  r.putValue("requested","turnip");require(!owner.gpuProfileReportMatches(report));owner.gpuProfileRequested="turnip";
  r=receipt("turnip","software","software_fallback").putValue("fallback_reason","No KGSL");report.putValue("client_gpu_profile",r);
  require(owner.gpuProfileReportMatches(report));r.putValue("probe_cleanup_safe",false);require(!owner.gpuProfileReportMatches(report));
  r=receipt("turnip","turnip","selected_after_probes").putValue("archive_sha256","pin")
   .putValue("vulkan_probe",new JSONObject().putValue("status","passed"))
   .putValue("wine_gl_probe",new JSONObject().putValue("status","passed").putValue("passed",true));
  owner.manifest.putValue("files",new JSONObject().putValue("hardware-renderer.zip",new JSONObject().putValue("sha256","pin")));
  report.putValue("client_gpu_profile",r);require(owner.gpuProfileReportMatches(report));
  r.putValue("archive_sha256","other");require(!owner.gpuProfileReportMatches(report));r.putValue("archive_sha256","pin");
  r.putValue("session_id","foreign");require(!owner.gpuProfileReportMatches(report));
  System.out.println("GPU actual Android selection and receipt gates passed");
 }
}'''.replace('ACTUAL_METHODS', methods)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); file = directory / 'GPUProfileHost.java'; file.write_text(harness)
            subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                            '-d', str(directory), str(file)], check=True, capture_output=True, text=True)
            result = subprocess.run(['java', '-cp', str(directory), 'GPUProfileHost'], check=True, capture_output=True, text=True)
        self.assertIn('GPU actual Android selection and receipt gates passed', result.stdout)
        body = actual_method(source, 'private Result runCharacter(')
        self.assertEqual(body.count('gpuProfileRequested=gpuProfileEnabled(context);'), 1)
        self.assertIn('"COH_CLIENT_GPU_PROFILE="+gpuProfileRequested', body)

    def test_sidebar_selection_is_disabled_during_owned_operation_and_uses_fixed_labels(self):
        source = (JAVA / 'ClientActivity.java').read_text()
        self.assertIn('new String[]{"Software (current)","GPU test"}', source)
        self.assertIn('gpuProfile.setEnabled(idle)', source)
        self.assertIn('position==1?"turnip":"software"', source)


if __name__ == '__main__': unittest.main()
