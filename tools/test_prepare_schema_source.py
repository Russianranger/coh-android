"""Exercise real patch application and provenance gates without compiling CoH."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import prepare_schema_source as schema


class SchemaSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / 'source'
        self.source.mkdir()
        self.expected = schema.expected_schema_receipt()
        pg = self.expected['postgresql_build_input']
        original = schema.ROOT / 'upstream/ouroboros'
        for name in (*schema.SCHEMA_FILES, *pg['patched_sha256']):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original / name, target)
        schema.apply_patch(self.source, (schema.ROOT / 'patches/postgresql/0001-dbserver-postgresql.patch')
                           .read_bytes().replace(b'\r\n', b'\n'))
        for name in pg['overlay_sha256']:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(schema.ROOT / 'database/postgresql/overlay' / name, target)
        self.pg_path = self.source / 'postgresql-build-input.json'
        self.pg_path.write_text(json.dumps(pg))

    def test_real_patch_records_expected_hashes_without_changing_upstream(self):
        receipt = schema.apply_schema_overlay(self.source)
        self.assertEqual(receipt, self.expected)
        self.assertEqual(json.loads((self.source / schema.RECEIPT).read_text()), receipt)
        for name, digest in receipt['patched_sha256'].items():
            self.assertEqual(schema.sha256(self.source / name), digest)
            self.assertEqual(schema.sha256(schema.ROOT / 'upstream/ouroboros' / name),
                             receipt['source_sha256'][name])
        self.assertEqual(json.loads(self.pg_path.read_text()), receipt['postgresql_build_input'])
        self.assertEqual(receipt['runtime_validation'], 'unverified')

    def test_dirty_schema_source_is_rejected_before_other_files_change(self):
        target = self.source / schema.SCHEMA_FILES[0]
        target.write_bytes(target.read_bytes() + b'\n// unrecorded edit\n')
        with self.assertRaisesRegex(ValueError, 'Staged source SHA-256 mismatch'):
            schema.apply_schema_overlay(self.source)
        untouched = schema.SCHEMA_FILES[1]
        self.assertEqual(schema.sha256(self.source / untouched), self.expected['source_sha256'][untouched])
        self.assertFalse((self.source / schema.RECEIPT).exists())

    def test_pg_source_or_overlay_drift_rejected(self):
        pg = self.expected['postgresql_build_input']
        for names in (pg['patched_sha256'], pg['overlay_sha256']):
            with self.subTest(category=next(iter(names))):
                target = self.source / next(iter(names))
                original = target.read_bytes()
                target.write_bytes(original + b'\n')
                with self.assertRaisesRegex(ValueError, 'Staged source SHA-256 mismatch'):
                    schema.apply_schema_overlay(self.source)
                target.write_bytes(original)
        self.assertFalse((self.source / schema.RECEIPT).exists())

    def test_stale_pg_receipt_rejected(self):
        pg = json.loads(self.pg_path.read_text())
        pg['source_commit'] = 'f' * 40
        self.pg_path.write_text(json.dumps(pg))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            schema.apply_schema_overlay(self.source)

    def test_known_crlf_overlay_profile_keeps_actual_raw_receipt(self):
        pg = json.loads(self.pg_path.read_text())
        for name in pg['overlay_sha256']:
            target = self.source / name
            target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            pg['overlay_sha256'][name] = schema.sha256(target)
        self.pg_path.write_text(json.dumps(pg))
        receipt = schema.apply_schema_overlay(self.source)
        self.assertEqual(receipt, schema.expected_schema_receipt(postgresql_build_input=pg))
        self.assertEqual(receipt['postgresql_build_input'], pg)
        self.assertEqual(receipt['postgresql_build_input_canonical_sha256'], schema.canonical_hash(pg))

    def test_unknown_overlay_profile_rejected_even_with_matching_local_bytes(self):
        pg = json.loads(self.pg_path.read_text())
        name = next(iter(pg['overlay_sha256']))
        target = self.source / name
        target.write_bytes(target.read_bytes() + b'// unexpected change\n')
        pg['overlay_sha256'][name] = schema.sha256(target)
        self.pg_path.write_text(json.dumps(pg))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            schema.apply_schema_overlay(self.source)

    def test_second_application_and_upstream_target_rejected(self):
        schema.apply_schema_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            schema.apply_schema_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'immutable snapshots'):
            schema.apply_schema_overlay(schema.ROOT / 'upstream/ouroboros')

    def test_preexisting_output_rejected_without_invoking_pg_stager(self):
        with self.assertRaisesRegex(ValueError, 'new directory'):
            schema.prepare(self.source)

    @unittest.skipUnless(shutil.which('cc'), 'Optional narrow C diagnostic probe requires a C compiler')
    def test_queued_error_branch_uses_stdio_safely_with_filewrapper_macro(self):
        """Compile the actual patched branch under the conflicting upstream macro.

        This tests only logging/exit behavior; it does not compile or execute CoH.
        The old fprintf(stderr, ...) produced a FILE*/FileWrapper* mismatch.
        """
        schema.apply_schema_overlay(self.source)
        source = (self.source / 'MapServer/src/svr/svr_init.c').read_text()
        branch = 'char *queued_error;' + source.split('char *queued_error;', 1)[1].split('        }\n        exit(0);', 1)[0]
        probe = self.source / 'diagnostic_probe.c'
        probe.write_text('''#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
typedef struct FileWrapper { int unused; } FileWrapper;
int x_fprintf(FileWrapper *file, const char *format, ...);
#define fprintf x_fprintf
void printf_stderr(const char *format, ...) {
    va_list args; va_start(args, format); vfprintf(stderr, format, args); va_end(args);
}
static int has_error;
char *errorGetQueued(void) {
    if (has_error) { has_error = 0; return "synthetic definition error"; }
    return NULL;
}
int main(int argc, char **argv) {
    has_error = argc > 1;
''' + branch + '\n}\n')
        executable = self.source / 'diagnostic_probe'
        subprocess.run([shutil.which('cc'), '-Werror=incompatible-pointer-types',
                        str(probe), '-o', str(executable)], check=True, capture_output=True)
        clean = subprocess.run([str(executable)], capture_output=True, text=True)
        error = subprocess.run([str(executable), 'error'], capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0)
        self.assertIn('queued_errors=0', clean.stdout)
        self.assertEqual(error.returncode, 1)
        self.assertIn('queued_errors=1', error.stdout)
        self.assertIn('COH_DB_TEMPLATES_ONLY_DIAGNOSTIC: synthetic definition error', error.stderr)


if __name__ == '__main__':
    unittest.main()
