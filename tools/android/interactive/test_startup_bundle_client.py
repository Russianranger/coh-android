"""Qualify the actual new root decoder and missing-texture reporting functions."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'android/guest'))
import package_startup_bundle_client as package
import package_responsiveness_native as baseline
import prepare_client_texture_source as texture
import prepare_client_graphics_source as graphics
import prepare_character_events_source as events
import texture_header_index as index
from prepare_resume_client_source import apply_patch
from test_package_reference_runtime import pe_file


class Context:
    def check(self): pass


class StartupBundleClientTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self): self.temporary.cleanup()

    def frozen_source(self):
        source = self.root / 'source'
        source.mkdir()
        for name in set((*texture.FILES, *graphics.GRAPHICS_FILES, *baseline.SCHEMA_FILES,
                *events.EVENTS_FILES, *events.progress.game.GAME_FILES)):
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / 'upstream/ouroboros' / name).read_bytes().replace(b'\r\n', b'\n'))
        texture.apply_texture_overlay(source)
        graphics.apply_graphics_overlay(source)
        apply_patch(source, events.progress.game.patch_bytes())
        apply_patch(source, events.progress.patch_bytes())
        apply_patch(source, events.patch_bytes())
        for name, content in events.overlay_bytes().items():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (source / 'character-events-build-input.json').write_text(json.dumps(events.expected_events_receipt()))
        return source

    def test_layer_preserves_frozen_inputs_and_serializer_sources(self):
        expected = package.expected_receipt()
        source = self.frozen_source()
        original = {name: (source / name).read_bytes() for name in
            (*baseline.SCHEMA_FILES, texture.OVERLAY_FILE, graphics.OVERLAY_FILES[0], graphics.GRAPHICS_FILES[0])}
        receipts = {name: (source / name).read_bytes() for _, name, _ in baseline.INPUTS.values()}
        self.assertEqual(expected, package.apply_overlay(source))
        for name, value in {**original, **receipts}.items(): self.assertEqual(value, (source / name).read_bytes())
        self.assertEqual(expected, package.validate_source(source)[0])
        with self.assertRaisesRegex(ValueError, 'already exists'): package.apply_overlay(source)

    def test_changed_baseline_rejected_before_layer(self):
        source = self.frozen_source()
        path = source / 'Game/src/render/tex.c'
        path.write_bytes(path.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'Frozen texture source changed'): package.apply_overlay(source)
        self.assertFalse((source / package.RECEIPT).exists())

    def test_package_checks_actual_producer_bytes_and_refuses_linked_members(self):
        source = self.frozen_source()
        package.apply_overlay(source)
        binaries = self.root / 'bin'
        binaries.mkdir()
        (binaries / 'CityOfHeroes.exe').write_bytes(pe_file(('KERNEL32.dll',)))
        cache = self.root / 'CMakeCache.txt'
        cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n')
        directory = self.root / 'package'
        document = package.package(SimpleNamespace(directory=binaries, source=source, cache=cache,
            output=directory, repository_commit='a' * 40,
            run_url='https://github.com/Russianranger/coh-android/actions/runs/123'))
        self.assertEqual(document, package.validate_package(directory, 'a' * 40))
        self.assertEqual({'CityOfHeroes.exe'}, set(document['files']))
        for name in ('CityOfHeroes.exe', 'CMakeCache.txt', package.MANIFEST):
            path = directory / name
            backup = self.root / ('backup-' + name)
            path.rename(backup)
            path.symlink_to(backup)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Linked'):
                package.validate_package(directory, 'a' * 40)
            path.unlink()
            backup.rename(path)
        path = directory / 'CityOfHeroes.exe'
        path.write_bytes(path.read_bytes() + b'foreign')
        with self.assertRaisesRegex(ValueError, 'executable bytes differ'):
            package.validate_package(directory, 'a' * 40)

    def test_actual_decoder_exact_root_headers_and_unmatched_fallbacks(self):
        compiler = shutil.which('cc') or shutil.which('gcc')
        self.assertIsNotNone(compiler)
        source = self.frozen_source()
        package.apply_overlay(source)
        # Exercise the real little-endian parser and its new absolute-path adapter,
        # including the old scanner's primary/secondary-root callback shapes.
        header = struct.pack('<IIIIIffB3s', 76, 8, 16, 32, 0, 0.1, 0.2, 1, b'TX2')
        extra = b'texture_library/test/a\0\x10\x00\x01original-mip-data'
        header = struct.pack('<I', 32 + len(extra)) + header[4:] + extra
        original = self.root / 'a.texture'
        original.write_bytes(header + b'original')
        packed, _ = index.make_pack([('texture_library/test/a.texture', original)], 'b' * 64, Context())
        pack = self.root / 'headers.bin'
        pack.write_bytes(packed)
        harness = self.root / 'decoder.c'
        harness.write_text('#include <stdio.h>\n#include "' +
            str(source / package.OVERLAY_FILE) + '"\n' + r'''
int main(int argc, char **argv) {
    FILE *f; unsigned char *p; long bytes; CohTextureHeaderIndex index;
    const CohTextureHeaderEntry *entry;
    if (argc != 4) return 2;
    f = fopen(argv[1], "rb"); if (!f) return 3;
    fseek(f, 0, SEEK_END); bytes = ftell(f); fseek(f, 0, SEEK_SET);
    p = malloc(bytes); if (!p || fread(p, 1, bytes, f) != (size_t)bytes) return 4; fclose(f);
    if (!cohThiParse(&index, p, bytes, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")) return 1;
    entry = cohThiFindVerifiedRoot(&index, argv[2], argv[3]);
    if (entry) fwrite(entry->header, 1, entry->bytes, stdout);
    cohThiFree(&index); free(p); return entry ? 0 : 5;
}
''')
        executable = self.root / 'decoder'
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', str(harness), '-o', str(executable)], check=True)
        root = 'Z:/state/diagnostic/client-work-285adbfb0389ed61b577b734/data'
        for path, prefix in [('texture_library/test/a.texture', ''),
                ('TEXTURE_LIBRARY\\TEST\\A.TEXTURE', ''),
                (root + '/texture_library/test/a.texture', root),
                (root.upper().replace('/', '\\') + '\\TEXTURE_LIBRARY\\TEST\\A.TEXTURE', root + '/')]:
            with self.subTest(path=path):
                result = subprocess.run([str(executable), str(pack), path, prefix], capture_output=True)
                self.assertEqual(0, result.returncode)
                self.assertEqual(header, result.stdout)
        for path, prefix in [(root + '/texture_library/test/a.texture', ''),
                (root + '-foreign/texture_library/test/a.texture', root),
                (root + '/texture_library/test/a.texture', root + '-foreign'),
                (root + '/texture_library/test/../test/a.texture', root),
                (root + '/./texture_library/test/a.texture', root),
                (root + '//texture_library/test/a.texture', root),
                (root + '/texture_library/test/a.texture', 'Z:/state/../state/diagnostic/data'),
                ('\\\\server\\share\\texture_library\\test\\a.texture', root),
                ('texture_library/../texture_library/test/a.texture', root),
                ('texture_library/test/absent.texture', root), ('a' * 260, root)]:
            with self.subTest(path=path):
                result = subprocess.run([str(executable), str(pack), path, prefix], capture_output=True)
                self.assertEqual(5, result.returncode)
                self.assertEqual(b'', result.stdout)

    def test_actual_missing_diagnostic_reporting_bound_and_stage_reset(self):
        compiler = shutil.which('cc') or shutil.which('gcc')
        source = self.frozen_source()
        package.apply_overlay(source)
        text = (source / 'Game/src/render/tex.c').read_text()
        section = text[text.index('static StashTable coh_missing_texture_diagnostics;'):
            text.index('// texFillInBind:')]
        harness = self.root / 'reporting.c'
        harness.write_text(r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define false 0
#define StashDeepCopyKeys 1
typedef struct Table { unsigned int count; char *keys[8192]; } *StashTable;
static StashTable stashTableCreateWithStringKeys(int capacity, int flags) {
    (void)capacity; (void)flags; return calloc(1, sizeof(struct Table));
}
static void stashTableClear(StashTable table) {
    unsigned int i; for (i = 0; i < table->count; ++i) free(table->keys[i]); table->count = 0;
}
static int stashFindInt(StashTable table, const char *key, int *seen) {
    unsigned int i;
    for (i = 0; i < table->count; ++i) {
        if (!strcmp(table->keys[i], key)) { *seen = 1; return 1; }
    }
    return 0;
}
static unsigned int stashGetValidElementCount(StashTable table) { return table->count; }
static void stashAddInt(StashTable table, const char *key, int value, int overwrite) {
    (void)value; (void)overwrite;
    if (table->count >= 8192) abort();
    table->keys[table->count++] = strdup(key);
}
''' + section + r'''
int main(void) {
    unsigned int i, reported = 0; char name[50];
    setenv("COH_TEXTURE_DIAGNOSTIC_DEDUP", "1", 1);
    setenv("COH_STARTUP_DIAGNOSTIC_BOUND", "1", 1);
    texMissingDiagnosticBegin();
    for (i = 0; i < 20000; ++i) {
        sprintf(name, "unique-%u", i);
        reported += texMissingDiagnosticShouldReport("original/file.nd", name);
    }
    if (reported != 1024 || coh_missing_texture_suppressed != 18976 ||
        stashGetValidElementCount(coh_missing_texture_diagnostics) != 8192) return 1;
    if (texMissingDiagnosticShouldReport("original/file.nd", "unique-1") ||
        coh_missing_texture_duplicates != 1) return 2;
    texMissingDiagnosticEnd("npc");
    if (!texMissingDiagnosticShouldReport("original/file.nd", "unique-1")) return 3;
    texMissingDiagnosticBegin();
    if (!texMissingDiagnosticShouldReport("original/file.nd", "unique-1") ||
        coh_missing_texture_reported != 1 || coh_missing_texture_suppressed) return 4;
    texMissingDiagnosticEnd("costume");
    unsetenv("COH_STARTUP_DIAGNOSTIC_BOUND");
    texMissingDiagnosticBegin();
    reported = 0;
    for (i = 0; i < 1100; ++i) { sprintf(name, "unique-%u", i);
        reported += texMissingDiagnosticShouldReport("original/file.nd", name); }
    if (reported != 1100 || coh_missing_texture_suppressed) return 5;
    unsetenv("COH_TEXTURE_DIAGNOSTIC_DEDUP");
    texMissingDiagnosticBegin();
    if (!texMissingDiagnosticShouldReport("original/file.nd", "unique-1") ||
        !texMissingDiagnosticShouldReport("original/file.nd", "unique-1")) return 6;
    return 0;
}
''')
        executable = self.root / 'reporting'
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', str(harness), '-o', str(executable)], check=True)
        result = subprocess.run([str(executable)], capture_output=True, timeout=15, check=True)
        self.assertIn(b'reported_records=1024 duplicate_records=1 suppressed_records=18976', result.stdout)
        self.assertIn(b'stage=costume reported_records=1 duplicate_records=0 suppressed_records=0', result.stdout)


if __name__ == '__main__': unittest.main()
