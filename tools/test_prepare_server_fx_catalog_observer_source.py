"""Source conservation for the nonshipping native FX observer only."""
import hashlib
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import prepare_server_fx_catalog_observer_source as observer


class SourceTests(unittest.TestCase):
    def test_observer_changes_only_notification_after_success_and_registry_observation(self):
        original, changed = observer.observed_sources()
        self.assertEqual(set(changed), {observer.FX, observer.PARSER})
        fx = changed[observer.FX].decode()
        restored = fx.replace(observer.OBSERVER+'\n', '').replace(
            '    stringReorder();\n#ifdef SERVER\n    cohHostOnlyFxObserve();\n#endif\n}',
            '    stringReorder();\n}')
        self.assertEqual(restored.encode(), original[observer.FX])
        parser = changed[observer.PARSER].decode().replace('int cohHostOnlyFxBinaryAccepted = 0;\n\n', '').replace(
            '    if (success && filename && !stricmp(filename, "bin/fxinfo.bin"))\n'
            '        ++cohHostOnlyFxBinaryAccepted;\n', '')
        self.assertEqual(parser.encode(), original[observer.PARSER])

    def test_receipt_requires_nonshipping_role_exact_base_and_full_native_roundtrips(self):
        value = observer.expected()
        self.assertEqual(value['base_monorail'], observer.monorail.expected_receipt())
        self.assertFalse(value['contract']['shipping_executable'])
        self.assertTrue(value['contract']['ship_observer_forbidden'])
        self.assertEqual(value['contract']['indexed_names'], 19606)
        self.assertEqual(value['contract']['outer_records'], 19607)
        self.assertEqual(value['contract']['schema_crc'], '4cb7d9cb')
        self.assertEqual(value['contract']['after'], 'stock_fxBuildFxStringHandles_stringReorder')
        self.assertEqual(value['build_targets'], ['MapServer'])
        self.assertEqual(value['patched_sha256'], {
            n: hashlib.sha256(raw).hexdigest() for n, raw in observer.observed_sources()[1].items()})

    def test_host_only_code_uses_create_new_full_writes_flush_and_exact_id_roundtrip(self):
        code = observer.OBSERVER
        for fragment in ('GetEnvironmentVariableA', 'CREATE_NEW', 'written != length',
                         'FlushFileBuffers', 'CloseHandle', 'stringFromReference(i)',
                         'stringToReference(name)', 'reference != i', 'cohHostOnlyFxBinaryAccepted != 1'):
            self.assertIn(fragment, code)
        self.assertLess(code.index('if (!length) return;'), code.index('CreateFileA'))


if __name__ == '__main__': unittest.main()
