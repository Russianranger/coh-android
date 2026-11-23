"""0.13.81: the client keeps object library bounds and skips those files at a zone load (patch 0132).

CI run 45121536099 (0.13.80, patch 0131's totals): of a zone's 508 group files the client loaded
341 object library files in full at every zone load, 6.4-7.5 s of 6.7-7.9 s; the engine's own
shortcut (a geobin .bounds file matching the server's checksum) never applied. With
ARMPORT_LIBRARY_BOUNDS_CACHE set, a file loaded in full has its public definitions' bounds kept
and is not loaded at later zone loads. Off by default. The drawn world has no CI check.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'armport/patches/0132-armport-library-bounds-kept.patch'
HEADER = 'Game/src/group/armport_library_bounds.h'
TOTALS = 'Game/src/group/armport_group_load_log.h'
RECEIVE = 'Game/src/group/groupnetrecv.c'
FIXTURE = ROOT / 'armport/tests/library_bounds'


def sections(patch):
    found, name = {}, None
    for line in patch.splitlines():
        match = re.match(r'diff --git a/(\S+)', line)
        if match:
            name = match.group(1); found[name] = {'added': [], 'before': [], 'after': []}
        elif name is None or line.startswith(('+++', '---', '@@', 'index ', 'new file')):
            continue
        elif line.startswith('+'):
            found[name]['added'].append(line[1:]); found[name]['after'].append(line[1:])
        elif line.startswith('-'):
            found[name]['before'].append(line[1:])
        elif line.startswith(' '):
            found[name]['before'].append(line[1:]); found[name]['after'].append(line[1:])
    return found


class LibraryBoundsKept(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.sections = sections(cls.patch)

    def test_it_is_in_the_series_and_touches_three_client_files(self):
        series = (ROOT / 'armport/patches/series').read_text().split()
        self.assertEqual(series[series.index(PATCH.name) + 1:], ['0133-armport-group-bins-kept.patch'])
        self.assertEqual(sorted(self.sections), sorted([HEADER, TOTALS, RECEIVE]))
        for pinned in ('groupfileload.c', 'groupfilelib.c', 'FolderCache.c'):
            self.assertNotIn(pinned, self.patch)

    def test_the_engine_check_runs_first_and_a_kept_file_is_not_loaded(self):
        after = '\n'.join(self.sections[RECEIVE]['after'])
        added = '\n'.join(self.sections[RECEIVE]['added'])
        # The new branch sits after the engine's accepted-bounds branch (patch 0131 counts it) and
        # before the full load; 0131's own test pins the order of the engine's two checks.
        order = [after.index(text) for text in (
            'armport_group_load.bounds++;', 'else if (armportLibraryBoundsUse(fname))',
            'groupLoadFull(fname);', 'armportLibraryBoundsKeep(fname);')]
        self.assertEqual(order, sorted(order))
        previous = (ROOT / 'armport/patches/0131-armport-group-load-totals.patch').read_text()
        self.assertRegex(previous, r'\+\s+if \(groupFileFind\(fname\)\)\s+\+\s+armport_group_load\.known\+\+;\s+'
                                   r'\+\s+else if \(objectLibraryLoadBoundsFile\(fname,checksum\)\)\s+\+\s+\{\s+'
                                   r'\+\s+armport_group_load\.bounds\+\+;')
        self.assertEqual(after.count('groupLoadFull(fname);'), 1)
        # Kept bounds reach the engine through the call its own shortcut makes, and nothing else.
        self.assertIn('objectLibrarySetBounds(name, (GroupBounds*)bounds);', added)
        engine = set(re.findall(r'\b(objectLibrary\w+|group[A-Z]\w+|fileLastChanged)\(', added))
        self.assertEqual(engine, {'objectLibrarySetBounds', 'groupFileFind', 'groupIsPublic', 'fileLastChanged'})
        # What is kept is what objectLibraryWriteBoundsFile writes: the public definitions' bounds.
        self.assertRegex(added, r'if \(def && def->name && groupIsPublic\(def\)\)\s+'
                                r'armportLibraryBoundsAdd\(def->name, \(void\*\)def->min\);')
        self.assertIn('if (!file || !file->idx)\n        return;', added)
        # One write per zone load, before the totals line that reports it.
        self.assertLess(after.index('armport_group_load.kept = armportLibraryBoundsFlush();'),
                        after.index('armportGroupLoadEnd();'))
        self.assertEqual(added.count('armportLibraryBoundsEnabled(sizeof(GroupBounds))'), 2)

    def test_it_is_off_without_the_variable(self):
        header = '\n'.join(self.sections[HEADER]['added'])
        self.assertEqual(header.count('getenv("ARMPORT_LIBRARY_BOUNDS_CACHE")'), 1)
        self.assertIn('armport_lb.state = -1;', header)
        self.assertIn('if (armport_lb.state <= 0 || !length || (found = armportLbFind(key, length)) < 0)\n        return 0;', header)
        self.assertIn('if (armport_lb.state <= 0 || armport_lb.failed || !length)\n        return;', header)
        self.assertIn('if (armport_lb.state <= 0 || !armport_lb.dirty || armport_lb.open != ~0u)\n        return 0;', header)
        # The game's own file layer is not used: three Win32 calls read, four write.
        self.assertEqual(sorted(set(re.findall(r'\b(CreateFileA|ReadFile|WriteFile|MoveFileExA|DeleteFileA|GetFileSize|'
                                               r'CloseHandle|fopen|fileOpen|fwrite)\(', header))),
                         ['CloseHandle', 'CreateFileA', 'DeleteFileA', 'GetFileSize', 'MoveFileExA', 'ReadFile', 'WriteFile'])

    def test_the_totals_line_reports_it(self):
        totals = '\n'.join(self.sections[TOTALS]['after'])
        self.assertIn('" cached=%u cached_ms=%u kept=%u\\n",', totals)
        self.assertIn('t->cached, armportGroupLoadMs(t->cached_time), t->kept);', totals)

    def test_the_store_round_trips_and_ignores_damaged_files(self):
        compiler = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
        if compiler is None:
            self.skipTest('no host C compiler')
        header = '\n'.join(self.sections[HEADER]['added']) + '\n'
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / 'utilitieslib/utils').mkdir(parents=True)
            (work / 'utilitieslib/utils/wininclude.h').write_text((FIXTURE / 'wininclude_shim.h').read_text())
            (work / 'armport_library_bounds.h').write_text(header)
            (work / 'check.c').write_text((FIXTURE / 'store_check.c').read_text())
            flags = ['-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-I', str(work)]
            sanitized = flags + ['-fsanitize=address,undefined']
            built = subprocess.run([compiler, *sanitized, str(work / 'check.c'), '-o', str(work / 'check')],
                                   capture_output=True, text=True)
            if built.returncode:      # a compiler without the sanitizer runtime still runs the checks
                subprocess.run([compiler, *flags, str(work / 'check.c'), '-o', str(work / 'check')], check=True)
            result = subprocess.run([str(work / 'check'), str(work / 'kept.bin')], capture_output=True, text=True,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
            self.assertEqual((result.returncode, result.stderr), (0, ''), result.stderr)
            self.assertTrue((work / 'kept.bin').is_file())
            self.assertFalse((work / 'kept.bin.tmp').exists())

    def test_ci_input_and_app_option_reach_the_guest(self):
        import sys
        from unittest import mock
        sys.path[:0] = [str(ROOT / 'armport/app')]
        import interactive_host as host
        for value, expected in (('', False), ('0', False), ('1', True)):
            with mock.patch.dict(os.environ, {'COH_CLIENT_LIBRARY_BOUNDS': value}):
                self.assertIs(host.client_library_bounds_requested(), expected)
        with mock.patch.dict(os.environ, {'COH_CLIENT_LIBRARY_BOUNDS': 'on'}), self.assertRaises(ValueError):
            host.client_library_bounds_requested()
        source = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertIn("command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_LIBRARY_BOUNDS=1')", source)
        record = {'format': 1, 'requested': True, 'applied': True, 'file': 'armport-library-bounds-0.bin',
                  'bytes_before_launch': 412345, 'removed_other_identities': 0, 'error': None}
        line = host.start_options_line({'client_library_bounds': record}, 'reopen')
        self.assertIn('"client_library_bounds":{"requested":true,"applied":true,"bytes_before_launch":412345,"error":null}', line)
        self.assertIn('"client_library_bounds":null', host.start_options_line({}, 'reopen'))
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn('      client_library_bounds:\n', workflow)
        self.assertIn("  COH_CLIENT_LIBRARY_BOUNDS: ${{ inputs.client_library_bounds && '1' || '' }}\n", workflow)
        # The CI summary of a zone load carries the new counters as the client wrote them.
        loads = host.client_zone_loads('ArmPort zone: 5 map.start maps/a/b.txt tid=1\n'
                                       'ARMPORT_GROUP_LOAD_V1 total_ms=400 files=508 known=166 full=0 cached=341 cached_ms=90 kept=0\n')
        self.assertTrue(loads[0]['group_load'].endswith('cached=341 cached_ms=90 kept=0'))


if __name__ == '__main__':
    unittest.main()
