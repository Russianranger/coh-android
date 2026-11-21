"""PRoot patch 0008: a missing path component that exists in another letter case (PROOT_CASEFOLD_PROGRAMS).

Wine stats a whole Unix path as the Windows program wrote it and, when that fails, walks it one
component at a time. Thor 0.13.73 (20261118-170550): 357,000 newfstatat calls in one zone
server start, about 13 per file opened. The patch adds src/path/casefold.c; this test takes it
out of the patch, compiles it on the host with a stand-in for PRoot's tracee structure and runs
it on a folder tree.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_proot_ioctl_filter import added_file

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'android/native/proot/0008-casefold-missing-components.patch'

HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include "path/casefold.h"

/* argv: executable path of the stand-in tracee, then host paths that do not exist as written. */
int main(int argc, char **argv)
{
	Tracee tracee = { .exe = argv[1][0] == '-' ? NULL : argv[1] };
	uint64_t counts[3];
	int i;

	printf("wanted %d\n", (int) casefold_wanted(&tracee));
	for (i = 2; i < argc; i++) {
		char host_path[PATH_MAX], component[256];
		const char *slash = strrchr(argv[i], '/');
		struct stat statl;
		bool replaced;

		strcpy(host_path, argv[i]);
		strcpy(component, slash + 1);
		replaced = casefold_component(host_path, component);
		printf("%d %s %s %d\n", (int) replaced, host_path, component, lstat(host_path, &statl) == 0);
	}
	casefold_counts(counts);
	printf("counts %llu %llu %llu\n", (unsigned long long) counts[0], (unsigned long long) counts[1],
	       (unsigned long long) counts[2]);
	return 0;
}
'''
TRACEE = '''
#ifndef TRACEE_H
#define TRACEE_H
typedef struct tracee { char *exe; } Tracee;
#endif
'''


def build(work):
    patch = PATCH.read_text()
    (work / 'path').mkdir()
    (work / 'tracee').mkdir()
    (work / 'path/casefold.c').write_text(added_file(patch, 'src/path/casefold.c'))
    (work / 'path/casefold.h').write_text(added_file(patch, 'src/path/casefold.h'))
    (work / 'tracee/tracee.h').write_text(TRACEE)
    (work / 'harness.c').write_text(HARNESS)
    compiler = shutil.which('gcc') or shutil.which('cc')
    subprocess.run([compiler, '-std=gnu11', '-D_GNU_SOURCE', '-Wall', '-Wextra', '-Werror', '-O1', '-I', str(work),
                    '-o', str(work / 'harness'), str(work / 'harness.c'), str(work / 'path/casefold.c')],
                   check=True, cwd=work, timeout=120)
    return work / 'harness'


def run(harness, programs, exe, paths):
    environment = {key: value for key, value in os.environ.items() if key != 'PROOT_CASEFOLD_PROGRAMS'}
    if programs is not None:
        environment['PROOT_CASEFOLD_PROGRAMS'] = programs
    return subprocess.run([str(harness), exe, *paths], check=True, capture_output=True, text=True, timeout=30,
                          env=environment).stdout.splitlines()


class ProotCasefoldTest(unittest.TestCase):
    def test_patch_shape(self):
        patch = PATCH.read_text()
        self.assertEqual(sorted(re.findall(r'^diff --git a/(\S+) ', patch, re.M)), [
            'src/GNUmakefile', 'src/path/canon.c', 'src/path/casefold.c', 'src/path/casefold.h',
            'src/syscall/stop_counts.h'])
        self.assertIn('getenv("PROOT_CASEFOLD_PROGRAMS")', patch)
        # Only after the component's own lstat said "no such entry", and never while a binding is glued.
        self.assertIn('+		if (status < 0 && errno == ENOENT && component != NULL && tracee->glue_type == 0\n'
                      '+		    && casefold_wanted(tracee) && casefold_component(host_path, component)) {', patch)
        # The check after a link was followed passes no component: nothing is replaced there.
        self.assertIn('+		status = substitute_binding_stat(tracee, finality, recursion_level, guest_path, host_path, NULL);', patch)
        self.assertIn('+	path/casefold.o		\\', patch)
        self.assertIn('casefold_replaced=%llu casefold_absent=%llu casefold_listed=%llu', patch)
        source = added_file(patch, 'src/path/casefold.c')
        self.assertIn('if (found == NULL || strlen(*found) != length) {', source)     # same length: written in place
        self.assertIn('#define CASEFOLD_NAMES 16384', source)

    def test_recipe_ci_and_app_wiring(self):
        recipe = (ROOT / 'tools/android/build_proot.py').read_text()
        self.assertIn("'0008-casefold-missing-components.patch')", recipe)
        self.assertIn("'casefold_patch': True, 'casefold_switch': 'PROOT_CASEFOLD_PROGRAMS=<executable names>'", recipe)
        launcher = (ROOT / 'tools/android/dbserver/run_isolated_network.py').read_text()
        self.assertIn('environment["PROOT_CASEFOLD_PROGRAMS"] = CASEFOLD_PROGRAMS', launcher)
        names = 'wine:wine64:wineserver:wine-preloader:wine64-preloader'
        self.assertIn('CASEFOLD_PROGRAMS = "%s"' % names, launcher)
        java = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
        runtime = (java / 'ClientRuntime.java').read_text()
        self.assertIn('CASEFOLD_PROGRAMS="%s";' % names, runtime)
        self.assertIn('.getBoolean("proot-casefold", true)', runtime)
        self.assertIn('prootCasefoldUsed = prootIoctlFilterUsed && prootCasefoldRequested;', runtime)
        self.assertIn('if (prootCasefoldUsed) builder.environment().put("PROOT_CASEFOLD_PROGRAMS", CASEFOLD_PROGRAMS);', runtime)
        self.assertIn('builder.environment().remove("PROOT_CASEFOLD_PROGRAMS");', runtime)
        self.assertLess(runtime.index('builder.environment().remove("PROOT_CASEFOLD_PROGRAMS");'),
                        runtime.index('builder.environment().put("PROOT_CASEFOLD_PROGRAMS", CASEFOLD_PROGRAMS);'))
        self.assertIn('ClientRuntime.setProotCasefoldEnabled(this,checked)', (java / 'ClientActivity.java').read_text())

    @unittest.skipUnless(shutil.which('gcc') or shutil.which('cc'), 'no host C compiler')
    def test_component_replaced_only_by_an_entry_in_another_case(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory).resolve()
            harness = build(work)
            tree = work / 'tree'
            (tree / 'Data/Scripts.loc').mkdir(parents=True)
            (tree / 'Data/Scripts.loc/Generic_V0.spawndef').write_text('x')
            (tree / 'Data/both').write_text('x')
            (tree / 'Data/BOTH').write_text('x')
            (tree / 'Data/longer-name').write_text('x')
            os.symlink('Scripts.loc', tree / 'Data/Link')
            paths = [str(tree / 'data'), str(tree / 'Data/SCRIPTS.LOC'), str(tree / 'Data/Scripts.loc/generic_v0.SPAWNDEF'),
                     str(tree / 'Data/link'), str(tree / 'Data/Both'), str(tree / 'Data/absent'),
                     str(tree / 'Data/longer'), str(tree / 'Nowhere/x'), str(tree / 'Data/both/x')]
            lines = run(harness, 'wine:wineserver', '/opt/wine/bin/wine', paths)
            self.assertEqual(lines[0], 'wanted 1')
            rows = [line.split(' ') for line in lines[1:-1]]
            self.assertEqual(rows[0], ['1', str(tree / 'Data'), 'Data', '1'])
            self.assertEqual(rows[1], ['1', str(tree / 'Data/Scripts.loc'), 'Scripts.loc', '1'])
            self.assertEqual(rows[2], ['1', str(tree / 'Data/Scripts.loc/Generic_V0.spawndef'), 'Generic_V0.spawndef', '1'])
            self.assertEqual(rows[3], ['1', str(tree / 'Data/Link'), 'Link', '1'])
            # Two entries differ from it only in case: one of them, and an existing one.
            self.assertEqual((rows[4][0], rows[4][3]), ('1', '1'))
            self.assertIn(rows[4][2], ('both', 'BOTH'))
            # No such entry, a prefix of one, a missing folder, a file as a folder: unchanged.
            for row, path in zip(rows[5:], paths[5:]):
                self.assertEqual(row, ['0', path, path.rsplit('/', 1)[1], '0'])
            self.assertEqual(lines[-1], 'counts 5 4 3')        # replaced, absent, folders read (tree, Data, Scripts.loc)

    @unittest.skipUnless(shutil.which('gcc') or shutil.which('cc'), 'no host C compiler')
    def test_programs_are_matched_by_executable_file_name(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = build(Path(directory).resolve())
            names = 'wine:wine64:wineserver:wine-preloader:wine64-preloader'
            for exe, expected in (('/opt/wine/bin/wine', 1), ('/opt/wine-10.0/bin/wineserver', 1),
                                  ('/usr/lib/wine/wine64-preloader', 1), ('/usr/bin/python3', 0),
                                  ('/opt/wine/bin/winecfg', 0), ('/opt/wine/bin/win', 0), ('/wine/python3', 0),
                                  ('wine', 1), ('-', 0), ('/opt/wine/bin/', 0)):
                with self.subTest(exe=exe):
                    self.assertEqual(run(harness, names, exe, [])[0], 'wanted %d' % expected)
            self.assertEqual(run(harness, None, '/opt/wine/bin/wine', [])[0], 'wanted 0')
            self.assertEqual(run(harness, '', '/opt/wine/bin/wine', [])[0], 'wanted 0')
            self.assertEqual(run(harness, ':wine::', '/opt/wine/bin/wine', [])[0], 'wanted 1')

    @unittest.skipUnless(shutil.which('gcc') or shutil.which('cc'), 'no host C compiler')
    def test_a_changed_folder_is_read_again(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory).resolve()
            harness = build(work)
            tree = work / 'tree'
            tree.mkdir()
            (tree / 'First.txt').write_text('x')
            # One process, the same folder asked three times: read once.
            lines = run(harness, 'wine', 'wine', [str(tree / 'first.txt')] * 3)
            self.assertEqual(lines[-1], 'counts 3 0 1')


if __name__ == '__main__':
    unittest.main()
