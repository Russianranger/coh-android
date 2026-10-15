"""Full raw certificate and genuine x86 Windows stock/CryptoAPI contracts."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
import map_startup_animation_certificate as certificate
import prepare_map_startup_source as source

PIGG = None
MANIFEST = None
EVIDENCE = None


class SourceTests(unittest.TestCase):
    def test_source_changes_are_server_only_and_preserve_stock_validator_and_base_linking(self):
        raw = (ROOT / 'upstream/ouroboros' / source.SOURCE).read_bytes().replace(b'\r\n', b'\n')
        patched = source.patch_source(raw)
        start = raw.index(b'static void animDebugCheckBoneTrackOnLoad(')
        end = raw.index(b'\nstatic SkeletonAnimTrack * animReadTrackFile', start)
        self.assertIn(raw[start:end], patched)
        start = raw.index(b'static void animLinkToBaseSkeleton(')
        self.assertIn(raw[start:], patched)
        self.assertIn(b'file->iomode == IO_PIG', patched)
        self.assertIn(b'if (!cohCertified)', patched)
        self.assertIn(b'#else\n    fread( skeleton, 1, file_size, file );\n#endif', patched)
        lines, keep, inside = [], True, False
        for line in patched.splitlines(keepends=True):
            if line == b'#ifdef SERVER\n':
                self.assertFalse(inside); inside, keep = True, False
            elif inside and line == b'#else\n':
                keep = True
            elif inside and line == b'#endif\n':
                inside, keep = False, True
            elif keep:
                lines.append(line)
        self.assertFalse(inside)
        self.assertEqual(b''.join(lines), raw, 'Non-SERVER compilation must retain byte-exact stock source')
        self.assertEqual(source.CONTRACT['build_targets'], ['MapServer'])
        self.assertFalse(source.CONTRACT['client_or_renderer_changes'])

    def test_patch_refuses_changed_input(self):
        raw = (ROOT / 'upstream/ouroboros' / source.SOURCE).read_bytes().replace(b'\r\n', b'\n')
        with self.assertRaises(ValueError):
            source.patch_source(raw.replace(b'    int file_size, i;', b'    int file_size, i, changed;'))

    def test_certificate_has_no_environment_or_filename_only_bypass(self):
        raw = (ROOT / source.OVERLAY).read_text()
        self.assertNotIn('GetEnvironmentVariable', raw)
        self.assertNotIn('getenv', raw)
        self.assertIn('CryptHashData(hash, raw, bytes, 0)', raw)
        self.assertIn('memcmp(digest, entry->sha256, sizeof(digest))', raw)
        self.assertIn('if (!pigged', raw)
        self.assertIn('InterlockedCompareExchangePointer', raw)


class FullCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if PIGG is None or MANIFEST is None:
            raise RuntimeError('Original --animations-pigg and --animation-manifest required; no synthetic full acceptance')
        cls.table, cls.receipt = certificate.generate(PIGG, MANIFEST)

    def test_all_original_bytes_full_validation_and_dependency_closure(self):
        self.assertEqual(self.receipt['validated_track_count'], 5878)
        self.assertEqual(self.receipt['validated_raw_bytes'], 88380730)
        closure = self.receipt['dependency_closure']
        self.assertEqual(closure['terminal_base_count'], 385)
        for name in ('invalid_header_names', 'duplicate_casefolded_names', 'missing_base_names',
                     'nonterminal_cycles', 'terminal_bases_without_hierarchy'):
            self.assertEqual(closure[name], [])
        self.assertEqual(self.receipt['generated_table'],
                         {'bytes': len(self.table), 'sha256': hashlib.sha256(self.table).hexdigest()})

    def test_same_original_bytes_produce_same_table_and_source_receipt(self):
        table, receipt = certificate.generate(PIGG, MANIFEST)
        self.assertEqual((table, receipt), (self.table, self.receipt))
        staged = source.expected_receipt(receipt)
        self.assertEqual(staged['monorail_build_input'], source.monorail.expected_receipt())
        self.assertEqual(set(staged['patched_sha256']), {'Common/seq/animtrack.c', 'MapServer/src/svr/wine_monorail.c'})
        self.assertEqual(staged['animation_certificate_canonical_sha256'], source.canonical_hash(receipt))

    def test_typed_receipt_refuses_unbound_table_validator_or_dependency_claims(self):
        for key, value in (('generated_table', {'bytes': 1363915, 'sha256': '0' * 64}),
                           ('validator_sources', {}), ('native_execution_validated', True),
                           ('validated_track_count', True)):
            changed = copy.deepcopy(self.receipt); changed[key] = value
            with self.assertRaises(ValueError): source.expected_receipt(changed)
        changed = copy.deepcopy(self.receipt)
        changed['dependency_closure']['terminal_base_names'][0] = 'forged/base'
        with self.assertRaises(ValueError): source.expected_receipt(changed)

    def test_changed_raw_pack_and_inventory_are_refused(self):
        with tempfile.TemporaryDirectory(prefix='coh-cert-corruption-') as tmp:
            path = Path(tmp) / 'server-animation-manifest.json'
            changed = json.loads(Path(MANIFEST).read_bytes())
            first = next(iter(changed['files']))
            changed['files'][first]['sha256'] = '0' * 64
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError): certificate.generate(PIGG, path)
            path.write_bytes(b'{}')
            with self.assertRaises((ValueError, KeyError)): certificate.generate(PIGG, path)
            altered = Path(tmp) / 'server-animations.pigg'
            shutil.copyfile(PIGG, altered)
            with altered.open('r+b') as stream:
                stream.seek(-1, 2); byte = stream.read(1)
                stream.seek(-1, 2); stream.write(bytes([byte[0] ^ 1]))
            with self.assertRaises(ValueError): certificate.generate(altered, MANIFEST)


@unittest.skipUnless(os.name == 'nt', 'genuine Windows x86 CryptoAPI native fixture')
class WindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cl') or PIGG is None or MANIFEST is None:
            raise RuntimeError('Initialized x86 MSVC and original animation pack required')
        cls.temp = tempfile.TemporaryDirectory(prefix='coh-animation-native-')
        cls.directory = Path(cls.temp.name)
        cls.binary = cls.directory / 'animation_certificate.exe'
        table, cls.receipt = certificate.generate(PIGG, MANIFEST)
        (cls.directory / certificate.HEADER).write_bytes(table)
        shutil.copyfile(ROOT / source.OVERLAY, cls.directory / 'coh_animation_certificate.h')
        stock = (ROOT / 'upstream/ouroboros' / source.SOURCE).read_bytes().replace(b'\r\n', b'\n')
        begin = stock.index(b'static void animDebugCheckBoneTrackOnLoad(')
        end = stock.index(b'\nstatic SkeletonAnimTrack * animReadTrackFile', begin)
        (cls.directory / 'coh_animation_stock_validator.inc').write_bytes(stock[begin:end])
        cls.stock_validator_sha256 = hashlib.sha256(stock[begin:end]).hexdigest()
        subprocess.run(['cl', '/nologo', '/W4', '/WX', '/wd4505', '/O2', '/MT', '/D_CRT_SECURE_NO_WARNINGS',
            '/DCOH_ANIMATION_CERTIFICATE_TEST', '/I' + str(cls.directory),
            str(ROOT / 'database/map-startup/tests/animation_certificate.c'), '/Fe:' + str(cls.binary)],
            cwd=cls.directory, check=True)
        document = certificate.package.verify_package(PIGG, MANIFEST)
        cls.files = {}
        with Path(PIGG).open('rb') as stream:
            stream.seek(certificate.package.HEADER.size)
            entries = stream.read(certificate.package.ENTRY.size * len(document['files']))
            for index, name in enumerate(sorted(document['files'], key=str.upper)):
                _, _, size, _, offset, _, _, _, _ = certificate.package.ENTRY.unpack_from(entries, index * certificate.package.ENTRY.size)
                stream.seek(offset); body = stream.read(size)
                path = cls.directory / ('track-%04d.anim' % index)
                path.write_bytes(body); cls.files[name] = (path, body)
        cls.list = cls.directory / 'tracks.tsv'
        cls.list.write_text(''.join(name + '\t' + str(path) + '\n' for name, (path, _) in cls.files.items()))
        cls.native_results = []
        cls.failed = False

    def tearDown(self):
        result = self._outcome.result
        if any(test is self for test, _ in result.errors + result.failures):
            type(self).failed = True

    @classmethod
    def tearDownClass(cls):
        if EVIDENCE:
            Path(EVIDENCE).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cls.binary, Path(EVIDENCE).with_suffix('.exe'))
            Path(EVIDENCE).write_text(json.dumps({'format': 1, 'status': 'failed' if cls.failed else 'passed',
                'scope': 'genuine Windows x86 raw-byte certificate and exact stock key validator; no MapServer or Thor boot',
                'certificate': cls.receipt, 'exact_stock_validator_sha256': cls.stock_validator_sha256,
                'native_fixture_source': certificate.pin(ROOT / 'database/map-startup/tests/animation_certificate.c'),
                'native_binary_file': Path(EVIDENCE).with_suffix('.exe').name,
                'native_binary': certificate.pin(cls.binary), 'native_results': cls.native_results,
                'physical_startup_timing_validated': False}, indent=2) + '\n')
        cls.temp.cleanup()

    def case(self, name, body, *, pigged=True, crypto=False):
        path = self.directory / 'case.anim'; path.write_bytes(body)
        completed = subprocess.run([str(self.binary), '--case', name, str(path), str(int(pigged)),
            str(int(crypto)), 'fixture'], capture_output=True, text=True, check=True)
        self.native_results.append(completed.stdout)
        match = re.search(r'CASE bounded=(\d) certified=(\d) stock_errors=(\d+)', completed.stdout)
        self.assertIsNotNone(match)
        return tuple(map(int, match.groups()))

    def test_all_5878_actual_raw_tracks_match_and_exact_stock_scans_pass(self):
        completed = subprocess.run([str(self.binary), str(self.list)], capture_output=True, text=True, check=True)
        self.native_results.append(completed.stdout)
        self.assertIn('ALL tracks=5878 actual_stock_validator_errors=0', completed.stdout)
        self.assertIn('opened=5878 certified=5878 fallback=0 crypto_failed=0 raw_bytes=88380730', completed.stdout)

    def test_normalized_name_and_loose_unknown_or_crypto_failure_use_stock(self):
        name, (_, body) = next(iter(self.files.items()))
        self.assertEqual(self.case(name.upper().replace('/', '\\'), body), (1, 1, 0))
        for value, pigged, crypto in ((name, False, False), ('player_library/animations/unknown.anim', True, False),
                                      (name, True, True)):
            self.assertEqual(self.case(value, body, pigged=pigged, crypto=crypto), (1, 0, 0))

    def test_changed_key_bytes_fall_back_and_stock_detects_corruption(self):
        for name, (_, original) in self.files.items():
            count = struct.unpack_from('<I', original, 528)[0]
            table = struct.unpack_from('<I', original, 524)[0]
            for index in range(count):
                flags = original[table + index * 20 + 17]
                if flags & (2 | 128):
                    changed = bytearray(original)
                    offset = struct.unpack_from('<I', original, table + index * 20)[0]
                    changed[offset] = 64
                    result = self.case(name, changed)
                    self.assertEqual(result[:2], (1, 0)); self.assertGreater(result[2], 0)
                    return
        self.fail('No original compressed rotation found')

    def test_changed_padding_bytes_fall_back_even_when_stock_keys_remain_valid(self):
        name, (_, original) = next(iter(self.files.items()))
        table = struct.unpack_from('<I', original, 524)[0]
        changed = bytearray(original); changed[table + 18] ^= 1
        self.assertEqual(self.case(name, changed), (1, 0, 0))

    def test_truncated_header_table_hierarchy_and_offsets_are_refused_before_pointer_setup(self):
        name, (_, original) = next(iter(self.files.items()))
        header = struct.unpack_from('<I', original)[0]
        for body in (original[:595], original[:header - 1]):
            self.assertEqual(self.case(name, body)[:2], (0, 0))
        for offset, value in ((0, 595), (524, 0xffffffff), (528, 100), (540, 1)):
            body = bytearray(original); struct.pack_into('<I', body, offset, value)
            self.assertEqual(self.case(name, body)[:2], (0, 0))
        table = struct.unpack_from('<I', original, 524)[0]
        body = bytearray(original); struct.pack_into('<I', body, table, 0xffffffff)
        self.assertEqual(self.case(name, body)[:2], (0, 0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--animations-pigg', type=Path, required=True)
    parser.add_argument('--animation-manifest', type=Path, required=True)
    parser.add_argument('--native-evidence', type=Path)
    parser.add_argument('--require-windows', action='store_true')
    parser.add_argument('--host-only', action='store_true')
    args, remainder = parser.parse_known_args()
    PIGG, MANIFEST, EVIDENCE = args.animations_pigg, args.animation_manifest, args.native_evidence
    if args.require_windows and (os.name != 'nt' or not shutil.which('cl')):
        raise SystemExit('genuine initialized Windows x86 MSVC required; no accepted skip')
    if args.host_only and args.require_windows:
        raise SystemExit('--host-only and --require-windows are mutually exclusive')
    sys.argv = [sys.argv[0], *(['SourceTests', 'FullCertificateTests'] if args.host_only else []), *remainder]
    unittest.main()
