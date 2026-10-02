"""Cross-language header equivalence, corruption fallback and generation reuse."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('texture_header_index', ROOT / 'android/guest/texture_header_index.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Context:
    def check(self): pass
    def event(self, *args, **kwargs): pass


def texture(name, mip=b''):
    extra = ('texture_library/test/' + name).encode() + b'\0' + mip
    return struct.pack('<IIIIIffB3s', 32 + len(extra), 8, 16, 32, 0, 0.1, 0.2, 1, b'TX2') + extra + b'original'


class TextureIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.work = self.root / 'work'
        self.imported = self.root / 'imported'
        self.imported.mkdir()
        folder = self.work / 'data/texture_library/test'
        folder.mkdir(parents=True)
        for name, mip in [('a', b'\x10\x00\x01mip-data'), ('b', b'')]:
            target = self.imported / (name + '.texture')
            target.write_bytes(texture(name, mip))
            target.chmod(0o444)
            (folder / target.name).symlink_to(target)
        (self.work / 'client-work.json').write_text(json.dumps({'source_data': str(self.imported), 'format': 1}))
        self.identity = {'generation': 'generation-' + 'a' * 32}
    def tearDown(self): self.temp.cleanup()

    def prepare(self, exe='b' * 64):
        return module.prepare(self.work, self.identity, exe, Context())

    def test_exact_mip_and_warm_reuse(self):
        first, env = self.prepare()
        self.assertFalse(first['reused'])
        second, _ = self.prepare()
        self.assertTrue(second['reused'])
        self.assertEqual(2, second['native_file_opens_avoidable'])
        records, _, _ = module.texture_inputs(self.work, Context())
        pack = (self.work / module.PACK).read_bytes()
        expected, _ = module.make_pack(records, env['COH_TEXTURE_HEADER_ID'], Context())
        self.assertEqual(expected, pack)
        self.assertIn(b'mip-data', pack)
        self.assertNotIn(b'original', pack)

    def test_executable_and_content_changes_invalidate(self):
        before, _ = self.prepare()
        changed, _ = self.prepare('c' * 64)
        self.assertFalse(changed['reused'])
        self.assertNotEqual(before['identity'], changed['identity'])
        target = self.imported / 'a.texture'
        old_mtime = target.stat().st_mtime_ns
        target.chmod(0o644)
        target.write_bytes(texture('a', b'changed!'))
        target.chmod(0o444)
        os.utime(target, ns=(old_mtime, old_mtime))
        after, _ = self.prepare('c' * 64)
        self.assertFalse(after['reused'])
        self.assertNotEqual(changed['identity'], after['identity'])

    def test_corrupt_pack_regenerated(self):
        first, _ = self.prepare()
        pack = self.work / module.PACK
        pack.chmod(0o600)
        data = bytearray(pack.read_bytes()); data[-1] ^= 1; pack.write_bytes(data)
        after, _ = self.prepare()
        self.assertFalse(after['reused'])
        self.assertEqual(first['sha256'], after['sha256'])

    def test_link_escape_refused(self):
        target = self.work / 'data/texture_library/test/a.texture'
        target.unlink()
        outside = self.root / 'outside.texture'; outside.write_bytes(texture('a')); outside.chmod(0o444)
        target.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.prepare()

    def test_native_decoder_equivalence_and_rejection(self):
        compiler = shutil.which('cc') or shutil.which('gcc')
        self.assertIsNotNone(compiler, 'Native parser qualification requires a C compiler')
        _, env = self.prepare()
        pack = self.work / module.PACK
        source = self.root / 'decoder.c'
        header = ROOT / 'database/client-texture-index/overlay/Game/src/render/coh_texture_header_index.h'
        source.write_text('#include <stdio.h>\n#include "' + str(header) + '"\n' + r'''
int main(int argc, char **argv) {
    FILE *f; unsigned char *p; long size; CohTextureHeaderIndex index;
    const CohTextureHeaderEntry *entry; int valid;
    if (argc != 4) return 2;
    f = fopen(argv[1], "rb"); if (!f) return 3;
    fseek(f, 0, SEEK_END); size = ftell(f); fseek(f, 0, SEEK_SET);
    p = malloc(size); if (!p || fread(p, 1, size, f) != (size_t)size) return 4; fclose(f);
    valid = cohThiParse(&index, p, size, argv[2]);
    if (!valid) { free(p); return 1; }
    entry = cohThiFind(&index, argv[3]);
    if (entry) fwrite(entry->header, 1, entry->bytes, stdout);
    cohThiFree(&index); free(p); return entry ? 0 : 5;
}
''')
        executable = self.root / 'decoder'
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(executable)], check=True)
        identity = env['COH_TEXTURE_HEADER_ID']
        def run(path=pack, digest=identity, search='TEXTURE_LIBRARY\\TEST\\A.TEXTURE'):
            return subprocess.run([str(executable), str(path), digest, search], capture_output=True)
        result = run()
        original = (self.imported / 'a.texture').read_bytes()
        self.assertEqual(0, result.returncode)
        self.assertEqual(original[:struct.unpack_from('<I', original)[0]], result.stdout)
        self.assertEqual(5, run(search='texture_library/test/absent.texture').returncode)
        self.assertEqual(1, run(digest='d' * 64).returncode)
        for offset in (0, 8, 12, 16, 20, 24, 28, 65, len(pack.read_bytes()) - 1):
            altered = bytearray(pack.read_bytes()); altered[offset] ^= 128
            corrupt = self.root / ('bad-' + str(offset)); corrupt.write_bytes(altered)
            self.assertEqual(1, run(path=corrupt).returncode, offset)
        # Valid checksum must not admit duplicate/unsorted or traversing paths.
        altered = bytearray(pack.read_bytes())
        altered[68:84] = b'texture_library/'  # unchanged prefix
        altered[84:89] = b'../x/'
        struct.pack_into('<I', altered, 24, zlib.crc32(altered[64:]))
        corrupt = self.root / 'traversal'; corrupt.write_bytes(altered)
        self.assertEqual(1, run(path=corrupt).returncode)


if __name__ == '__main__': unittest.main()
