"""Corrupt-pack, native-read evidence and optional-install boundary tests.

The tiny synthetic tracks here are parser fixtures, never native qualification.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'android/guest'))
spec = importlib.util.spec_from_file_location('server_animation_producer_tests', Path(__file__).with_name('prepare_server_animations.py'))
producer = importlib.util.module_from_spec(spec); spec.loader.exec_module(producer)
package = producer.package


def track(name='male/skel_ready', base='male/skel_ready'):
    # One root bone, unchanged legacy 32-bit offsets and compressed keys.
    bone = 612; header = bone + 20
    body = bytearray(header + 11)
    struct.pack_into('<i', body, 0, header)
    body[4:4 + len(name)] = name.encode(); body[260:260 + len(base)] = base.encode()
    struct.pack_into('<ffIiiiI', body, 516, 0, 23.5, bone, 1, 0, 0, 596)
    struct.pack_into('<iiii', body, 596, 0, -1, -1, 0)
    struct.pack_into('<IIHHHHbBH', body, bone, header, header + 5, 1, 1, 1, 1, 0, 18, 0)
    return bytes(body)


def inputs():
    bodies = {'player_library/animations/male/skel_ready.anim': track(),
              'player_library/animations/male/test.anim': track('male/test')}
    files = {name: {**producer.observer.package.pin_bytes(body), 'timestamp': producer.observer.package.EPOCH}
             for name, body in bodies.items()}
    return bodies, files


class ServerAnimationPackTests(unittest.TestCase):
    def test_complete_accepted_inventory_and_native_source_pins(self):
        files = producer.accepted_inventory()
        self.assertEqual(len(files), 5878)
        self.assertEqual(sum(x['bytes'] for x in files.values()), 88380730)
        baseline = json.loads((ROOT / 'docs/source-manifest.json').read_text())
        pins = {entry['path']: entry for entry in baseline['entries']}
        for name in producer.SOURCES:
            if not name.startswith('upstream/ouroboros/'): continue
            relative = name[len('upstream/ouroboros/'):]
            with self.subTest(name=name):
                self.assertEqual(package.file_pin(ROOT / name),
                                 {'bytes': pins[relative]['size'], 'sha256': pins[relative]['sha256']})

    def test_pack_preserves_all_body_header_and_native_lastframe_bytes(self):
        bodies, files = inputs()
        with tempfile.TemporaryDirectory() as temporary:
            pigg = Path(temporary) / package.PIGG
            proof, dependency = producer.write_pigg(pigg, files, bodies.__getitem__)
            observed = package.verify_pigg(pigg, files, exact=False)
            self.assertEqual(observed, proof)
            self.assertEqual(dependency['terminal_base_count'], 1)
            self.assertEqual(proof['original_animation_bytes'], sum(map(len, bodies.values())))
            data = pigg.read_bytes()
            for body in bodies.values(): self.assertIn(body, data)
            self.assertEqual(struct.unpack_from('<f', bodies[next(iter(bodies))], 520)[0], 23.5)

    def test_corrupt_native_entry_offsets_timestamps_and_packed_flag_rejected(self):
        bodies, files = inputs()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / package.PIGG
            producer.write_pigg(path, files, bodies.__getitem__)
            original = path.read_bytes()
            for offset, value in ((16 + 12, 0), (16 + 16, 0), (16 + 44, 1), (16 + 24, 999)):
                data = bytearray(original); struct.pack_into('<I', data, offset, value); path.write_bytes(data)
                with self.subTest(offset=offset), self.assertRaises(ValueError):
                    package.verify_pigg(path, files, exact=False)
            path.write_bytes(original[:-1])
            with self.assertRaises(ValueError): package.verify_pigg(path, files, exact=False)

    def test_payload_or_cached_header_mismatch_rejected(self):
        bodies, files = inputs()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / package.PIGG
            result, _ = producer.write_pigg(path, files, bodies.__getitem__)
            original = path.read_bytes()
            data = bytearray(original); data[-1] ^= 1; path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'payload differs'): package.verify_pigg(path, files, exact=False)
            data = bytearray(original)
            # Flip the header prefix in the first cached-header pool item.
            with path.open('wb') as stream: stream.write(original)
            with path.open('rb') as stream:
                stream.seek(16 + 48 * len(files)); package.pool(stream, 0x6789, maximum=package.MAX_METADATA)
                first_header = stream.tell() + 12 + 4
            data[first_header + 520] ^= 1; path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'cached native header'): package.verify_pigg(path, files, exact=False)

    def test_missing_base_and_logical_animation_name_mismatch_rejected(self):
        bodies, files = inputs()
        for replacement in (track('male/test', 'male/missing'), track('female/not_test')):
            key = 'player_library/animations/male/test.anim'
            bodies[key] = replacement; files[key].update(producer.observer.package.pin_bytes(replacement))
            with tempfile.TemporaryDirectory() as temporary, self.assertRaises(ValueError):
                producer.write_pigg(Path(temporary) / package.PIGG, files, bodies.__getitem__)

    def test_production_inventory_cannot_accept_small_fixture_or_path_traversal(self):
        bodies, files = inputs()
        with self.assertRaisesRegex(ValueError, 'accepted animation closure'): package.validate_inventory(files)
        for name in ('player_library/animations/../escape.anim', 'player_library/animations/MALE/test.anim',
                     'server/bin/powers.bin', '/player_library/animations/a.anim'):
            self.assertFalse(package.safe_name(name))

    def test_source_can_never_change_between_header_and_body_packing(self):
        bodies, files = inputs(); calls = {}
        def read(name):
            calls[name] = calls.get(name, 0) + 1
            return bodies[name] if calls[name] == 1 else bodies[name][:-1] + bytes([1])
        with tempfile.TemporaryDirectory() as temporary, self.assertRaisesRegex(ValueError, 'changed during'):
            producer.write_pigg(Path(temporary) / package.PIGG, files, read)

    def test_optional_absent_package_leaves_runtime_completely_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); runtime = root / 'runtime'; runtime.mkdir()
            result = package.install(root / 'absent.pigg', root / 'absent.json', runtime)
            self.assertFalse(result['installed']); self.assertEqual(list(runtime.iterdir()), [])

    def test_private_install_reuses_exact_pack_and_preserves_loose_inputs(self):
        bodies, files = inputs()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); runtime = root / 'runtime'; runtime.mkdir()
            binary = runtime / 'MapServer.exe'; binary.write_bytes(b'native fixture')
            loose = runtime / 'data/player_library/animations/male/test.anim'
            loose.parent.mkdir(parents=True); loose.write_bytes(bodies['player_library/animations/male/test.anim'])
            pigg = root / package.PIGG
            result, _ = producer.write_pigg(pigg, files, bodies.__getitem__)
            manifest = {'pigg': result, 'identity': {'mapserver_sha256': package.file_pin(binary)['sha256']}}
            with mock.patch.object(package, 'verify_package', return_value=manifest):
                first = package.install(pigg, root / 'manifest.json', runtime)
                second = package.install(pigg, root / 'manifest.json', runtime)
                self.assertFalse(first['reused']); self.assertTrue(second['reused'])
                self.assertEqual(loose.read_bytes(), bodies['player_library/animations/male/test.anim'])
                target = runtime / 'piggs' / package.PIGG; target.chmod(0o600); target.write_bytes(b'corrupt')
                with self.assertRaisesRegex(ValueError, 'Existing animation Pig differs'):
                    package.install(pigg, root / 'manifest.json', runtime)

    def test_foreign_pigs_and_symlinked_destination_refused(self):
        bodies, files = inputs()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); runtime = root / 'runtime'; runtime.mkdir()
            binary = runtime / 'MapServer.exe'; binary.write_bytes(b'native fixture')
            pigg = root / package.PIGG; result, _ = producer.write_pigg(pigg, files, bodies.__getitem__)
            manifest = {'pigg': result, 'identity': {'mapserver_sha256': package.file_pin(binary)['sha256']}}
            directory = runtime / 'piggs'; directory.mkdir(); (directory / 'other.pigg').write_bytes(b'foreign')
            with mock.patch.object(package, 'verify_package', return_value=manifest):
                with self.assertRaisesRegex(ValueError, 'Foreign or unowned'): package.install(pigg, root / 'manifest.json', runtime)
                (directory / 'other.pigg').unlink(); target = directory / package.PIGG; target.symlink_to(pigg)
                with self.assertRaisesRegex(ValueError, 'Existing animation Pig'): package.install(pigg, root / 'manifest.json', runtime)


class NativeAnimationTraceTests(unittest.TestCase):
    def observe(self, lines):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); path = root / 'trace.1'
            path.write_text(lines)
            return producer.animation_trace([path], '/host/runtime', 100)

    def test_native_successful_content_reads_required_beyond_metadata(self):
        result = self.observe('read(6</host/runtime/piggs/server-animations.pigg>, "bytes", 4096) = 4096\n')
        self.assertTrue(result['packed_only_loading_proven'])
        for lines in ('openat(AT_FDCWD, "/host/runtime/piggs/server-animations.pigg", O_RDONLY) = 6\n',
                      'read(6</host/runtime/piggs/server-animations.pigg>, "bytes", 128) = 128\n',
                      'read(6</host/runtime/piggs/server-animations.pigg>, "bytes", 4096) = -1 EIO\n'):
            with self.subTest(lines=lines): self.assertFalse(self.observe(lines)['packed_only_loading_proven'])

    def test_loose_fallback_or_native_write_prevents_packed_only_claim(self):
        packed = 'pread64(6</host/runtime/piggs/server-animations.pigg>, "bytes", 4096, 0) = 4096\n'
        for addition in ('read(7</host/runtime/data/player_library/animations/male/test.anim>, "bytes", 8) = 8\n',
                         'write(6</host/runtime/piggs/server-animations.pigg>, "bytes", 8) = 8\n',
                         'unlink("/host/runtime/piggs/server-animations.pigg") = 0\n'):
            with self.subTest(addition=addition): self.assertFalse(self.observe(packed + addition)['packed_only_loading_proven'])

    def test_mapped_loose_animation_and_unfinished_content_read_refused(self):
        for lines in ('mmap(NULL, 4096, PROT_READ, MAP_PRIVATE, 7</host/runtime/data/player_library/animations/male/test.anim>, 0) = 0x10000\n',
                      'read(6</host/runtime/piggs/server-animations.pigg>, <unfinished ...>\n'):
            with self.subTest(lines=lines), self.assertRaises(ValueError): self.observe(lines)


if __name__ == '__main__': unittest.main()
