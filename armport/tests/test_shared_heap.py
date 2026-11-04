"""Shared server memory experiment: off by default, one switch, evidence from the native console."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import local_character_server as character  # noqa: E402

UPSTREAM = ROOT / 'upstream/ouroboros'
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
# The Thor 0.13.53 Atlas console (export 20261104-195518) with the option present.
OFF = ('COH_GAME_LOOPBACK_ONLY=1 active: IPv4 loopback binding policy\n'
       'Not using shared memory due to -nosharedmemory\n'
       'reserving shared heap space... failed: no shared heap                 (0.00)\n')
ON = 'reserving shared heap space... reserved 1024 MB                 (0.01)\n'


class SharedHeap(unittest.TestCase):
    def test_option_is_off_unless_requested(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('COH_SHARED_HEAP', None)
            self.assertEqual(character.mapserver_memory_arguments(), ['-nosharedmemory'])
        for value, expected in (('0', ['-nosharedmemory']), ('1', []), ('yes', ['-nosharedmemory'])):
            with self.subTest(value=value), patch.dict(os.environ, {'COH_SHARED_HEAP': value}):
                self.assertEqual(character.mapserver_memory_arguments(), expected)

    def test_console_markers_are_the_native_strings(self):
        sources = ''.join((UPSTREAM / path).read_text(errors='replace') for path in (
            'MapServer/src/svr/svr_init.c', 'libs/UtilitiesLib/src/components/SharedMemory.c'))
        sources += (UPSTREAM / 'libs/UtilitiesLib/src/components/SharedHeap.c').read_text(errors='replace')
        for _, marker in character.SHARED_HEAP_LINES:
            self.assertIn(marker, sources)
        self.assertIn('" reserved %d MB"', sources)
        self.assertIn('" ' + character.SHARED_HEAP_FAILED + '"', sources)

    def test_console_summary(self):
        off = character.shared_heap_console(OFF)
        self.assertFalse(off['shared_heap_active'])
        self.assertEqual(off['lines']['disabled_by_option'], 1)
        on = character.shared_heap_console('header\n' + ON)
        self.assertTrue(on['shared_heap_active'])
        self.assertEqual(on['reserved_mib'], 1024)
        fallback = character.shared_heap_console(
            'Program address space does not include our desired address!  Running in non-SharedMemory mode.\n' + ON)
        self.assertFalse(fallback['shared_heap_active'])
        self.assertEqual(off['lines']['heap_unavailable'], 1)

    def test_first_caller_output_splits_the_reservation_line(self):
        # CI run 41931773800 (shared heap on): the first caller prints inside the
        # reservation, so the outcome lands on a later line and v1 matched nothing.
        split = ('reserving shared heap space...initSharedHeapMemoryManager: SMAR_FirstCaller\n'
                 ' reserved 1024 MB                 (0.02)\n')
        on = character.shared_heap_console('header\n' + split + 'more miscellany..done\n')
        self.assertTrue(on['shared_heap_active'])
        self.assertEqual((on['reserved_mib'], on['lines']['first_caller'], on['lines']['reserve_started']), (1024, 1, 1))
        self.assertEqual(on['excerpt'][0], 'reserving shared heap space...initSharedHeapMemoryManager: SMAR_FirstCaller')
        failed = character.shared_heap_console(
            'reserving shared heap space...initSharedHeapMemoryManager: SMAR_FirstCaller\n'
            'Shared heap disabled: Failed to reserve any shared heap space\n failed: no shared heap   (0.00)\n'
            'later: reserved 5 MB of something else\n')
        self.assertFalse(failed['shared_heap_active'])
        self.assertEqual((failed['reserved_mib'], failed['lines']['heap_unavailable']), (None, 1))
        self.assertEqual(failed['disabled_reasons'], ['Failed to reserve any shared heap space'])
        silent = character.shared_heap_console('no marker here\n reserved 64 MB\n')
        self.assertEqual((silent['reserved_mib'], silent['excerpt'], silent['shared_heap_active']), (None, [], False))
        bounded = character.shared_heap_console('reserving shared heap space...\x1b[31m' + 'q' * 900 + '\n' * 40)
        self.assertLessEqual(len(bounded['excerpt']), 6)
        self.assertTrue(all(len(line) <= 160 and line.isprintable() for line in bounded['excerpt']))

    def test_both_launch_sites_use_the_switch(self):
        for path in ('android/guest/local_character_server.py', 'android/guest/character_zoning.py'):
            text = (ROOT / path).read_text()
            self.assertIn('mapserver_memory_arguments()', text)
            launch = text[text.index("'MapServer.exe')"):][:400]
            self.assertNotIn("'-nosharedmemory'", launch)

    def test_app_option_and_ci_input(self):
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        self.assertIn('"COH_SHARED_HEAP="+(sharedHeapRequested?"1":"0")', runtime)
        self.assertIn('.getBoolean("shared-server-memory", false)', runtime)
        self.assertIn('ClientRuntime.sharedHeapEnabled(this)', (JAVA / 'ClientActivity.java').read_text())
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn("COH_SHARED_HEAP: ${{ inputs.shared_heap && '1' || '' }}", workflow)
        import interactive_host
        for value, expected in (('', False), ('0', False), ('1', True)):
            with patch.dict(os.environ, {'COH_SHARED_HEAP': value}):
                self.assertEqual(interactive_host.shared_heap_requested(), expected)
        with patch.dict(os.environ, {'COH_SHARED_HEAP': '2'}), self.assertRaises(ValueError):
            interactive_host.shared_heap_requested()


if __name__ == '__main__':
    unittest.main()
