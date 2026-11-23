"""0.13.81: the production client keeps the prepared form of the group files it parses (patch 0133).

CI (0.13.80/0.13.81, patch 0131's totals): the client loads 341 object library files in full
at every zone load, about 20 ms each. It is a production client on loose data whose imported
data holds no .bin files; only a development client writes them. With ARMPORT_GROUP_BINS set
to an absolute folder, a parsed group file is written there and read from there afterwards.
The guest names the folder by the data view's identity. Off by default.
"""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
PATCH = ROOT / 'armport/patches/0133-armport-group-bins-kept.patch'
LOADER = 'Common/group/groupfileload.c'
TOTALS = 'Game/src/group/armport_group_load_log.h'
RECEIVE = 'Game/src/group/groupnetrecv.c'


def sections(patch):
    found, name = {}, None
    for line in patch.splitlines():
        match = re.match(r'diff --git a/(\S+)', line)
        if match:
            name = match.group(1); found[name] = {'added': [], 'removed': [], 'after': []}
        elif name is None or line.startswith(('+++', '---', '@@', 'index ')):
            continue
        elif line.startswith('+'):
            found[name]['added'].append(line[1:]); found[name]['after'].append(line[1:])
        elif line.startswith('-'):
            found[name]['removed'].append(line[1:])
        elif line.startswith(' '):
            found[name]['after'].append(line[1:])
    return found


class GroupBinsKept(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = sections(PATCH.read_text())

    def test_it_is_the_last_patch_and_touches_the_loader_and_the_totals(self):
        self.assertEqual((ROOT / 'armport/patches/series').read_text().split()[-1], PATCH.name)
        self.assertEqual(sorted(self.sections), sorted([LOADER, TOTALS, RECEIVE]))

    def test_without_the_variable_every_line_runs_as_before(self):
        loader = self.sections[LOADER]
        after = '\n'.join(loader['after'])
        # The two removed lines come back unchanged in meaning: the write keeps its arguments,
        # and the development-mode condition is only widened by the new switch.
        self.assertEqual([line.strip() for line in loader['removed']], [
            'ParserWriteBinaryFile(bin_name, parse_group_list, group_file, &g_parselist, NULL, 0, 0);',
            'if ( reprocessBins != BIN_REBUILD_MAP && isDevelopmentMode())'])
        self.assertIn('if (ParserWriteBinaryFile(bin_name, parse_group_list, group_file, &g_parselist, NULL, 0, 0))\n'
                      '        armport_group_bin_writes++;', after)
        self.assertIn('if ( reprocessBins != BIN_REBUILD_MAP && (isDevelopmentMode() || armportGroupBinRoot()))', after)
        # Each use of the folder has the old statement as its else branch.
        self.assertRegex(after, r'if \(armportGroupBinRoot\(\)\)\s+\{[^}]*sprintf\(buf,"%s/%s",armportGroupBinRoot\(\),cs\);\s+\}'
                                r'\s+else\s+sprintf\(buf,"geobin/%s",cs\);')
        self.assertRegex(after, r'if \(armportGroupBinRoot\(\)\)\s+sprintf\(fullbinpath,"%s", bin_name\);[^\n]*\s+else\s+'
                                r'sprintf\(fullbinpath,"%s/%s", fileDataDir\(\), bin_name\);')
        # The switch: an absolute Windows path of bounded length, read once.
        added = '\n'.join(loader['added'])
        self.assertEqual(added.count('getenv("ARMPORT_GROUP_BINS")'), 1)
        self.assertIn("if (length >= 4 && length < 160 && value[1] == ':')", added)
        self.assertIn('return root[0] ? root : NULL;', added)
        # A name too long for the file layer's buffers has no bin and is parsed.
        self.assertIn('if (strlen(armportGroupBinRoot()) + strlen(cs) + 8 >= MAX_PATH)\n            return 0;', added)

    def test_the_counts_reach_the_totals_line(self):
        loader = '\n'.join(self.sections[LOADER]['after'])
        self.assertIn('int armport_group_bin_reads, armport_group_text_loads, armport_group_bin_writes;', loader)
        self.assertIn('if (loadedFromBin)\n                armport_group_bin_reads++;', loader)
        self.assertIn('groupLoadRaw( fname, &group_file );\n        armport_group_text_loads++;', loader)
        receive = '\n'.join(self.sections[RECEIVE]['after'])
        self.assertIn('extern int armport_group_bin_reads, armport_group_text_loads, armport_group_bin_writes;', receive)
        self.assertLess(receive.index('armport_group_load.bin = (unsigned)armport_group_bin_reads;'),
                        receive.index('armport_group_load.bin = (unsigned)armport_group_bin_reads - armport_group_load.bin;'))
        self.assertIn('if (armport_group_load.active)', receive)
        totals = '\n'.join(self.sections[TOTALS]['after'])
        self.assertIn('" cached=%u cached_ms=%u kept=%u bin=%u text=%u wrote=%u\\n",', totals)
        self.assertIn('t->bin, t->text, t->wrote);', totals)

    def client(self):
        return {'data_validation': {'tree_sha256': '1' * 64, 'targets_sha256': '2' * 64, 'links': 5}}

    def environment(self, value, report, root):
        import armport_interactive as armport
        client = armport.ArmPortClient.__new__(armport.ArmPortClient)
        client.root = root
        client.ctx = SimpleNamespace(report=report)
        with mock.patch.dict(os.environ, {'COH_CLIENT_GROUP_BINS': value}):
            return client.client_group_bins_environment('scripts.loc,server')

    def test_the_guest_names_a_folder_per_data_identity_only_when_asked(self):
        import armport_interactive as armport
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = {'armport_client': self.client()}
            for value in ('', '0'):
                self.assertEqual(self.environment(value, report, root), {})
                self.assertEqual((report['client_group_bins']['requested'], report['client_group_bins']['applied']),
                                 (False, False))
            self.assertEqual(list(root.iterdir()), [])                 # off: nothing is created
            identity = armport.package.folder_cache_identity(self.client(), 'scripts.loc,server', 'geobin,server')
            name = 'armport-group-bins-' + identity[:24]
            stale = root / ('armport-group-bins-' + '0' * 24)
            (stale / 'object_library/a').mkdir(parents=True); (stale / 'object_library/a/a.bin').write_bytes(b'old')
            keep = [root / 'armport-folder-cache-index.bin', root / 'armport-group-bins-notes.txt',
                    root / 'armport-library-bounds-0123456789abcdef01234567.bin']
            for path in keep:
                path.write_bytes(b'kept')
            (root / 'client-work-0123').mkdir()
            environment = self.environment('1', report, root)
            self.assertEqual(list(environment), ['ARMPORT_GROUP_BINS'])
            self.assertTrue(environment['ARMPORT_GROUP_BINS'].startswith('Z:') and environment['ARMPORT_GROUP_BINS'].endswith(name))
            self.assertEqual(report['client_group_bins'], {
                'format': 1, 'requested': True, 'applied': True, 'folder': name, 'present_before_launch': False,
                'removed_other_identities': 1, 'error': None})
            self.assertTrue((root / name).is_dir() and not stale.exists() and (root / 'client-work-0123').is_dir())
            self.assertTrue(all(path.exists() for path in keep))          # only folders of its own pattern go
            (root / name / 'object_library').mkdir(); (root / name / 'object_library/x.bin').write_bytes(b'bin')
            self.environment('1', report, root)
            self.assertEqual((report['client_group_bins']['present_before_launch'],
                              report['client_group_bins']['removed_other_identities']), (True, 0))
            self.assertTrue((root / name / 'object_library/x.bin').is_file())
            self.assertEqual(self.environment('0', report, root), {})      # off again: kept, not named
            self.assertTrue((root / name / 'object_library/x.bin').is_file())
            # Incomplete identity, or a link in the folder's place: the client loads as before.
            incomplete = {'armport_client': {'archive_sha256': '4' * 64}}
            self.assertEqual(self.environment('1', incomplete, root), {})
            self.assertEqual(incomplete['client_group_bins']['error'], 'KeyError')
            other = {'armport_client': {'data_validation': {'tree_sha256': '7' * 64, 'targets_sha256': '2' * 64, 'links': 5}}}
            changed = armport.package.folder_cache_identity(other['armport_client'], 'scripts.loc,server', 'geobin,server')
            (root / ('armport-group-bins-' + changed[:24])).symlink_to(root / 'elsewhere')
            self.assertEqual(self.environment('1', other, root), {})
            self.assertEqual((other['client_group_bins']['applied'], other['client_group_bins']['error']),
                             (False, 'DiagnosticError'))
            with mock.patch.dict(os.environ, {'COH_CLIENT_GROUP_BINS': 'yes'}), self.assertRaises(Exception):
                armport.client_keeps_group_bins()
        # The folder's name is short enough for the client's limit on the variable (160 characters).
        self.assertLess(len('Z:\\state\\client\\' + name), 100)

    def test_ci_input_and_app_option_reach_the_guest(self):
        import interactive_host as host
        for value, expected in (('', False), ('0', False), ('1', True)):
            with mock.patch.dict(os.environ, {'COH_CLIENT_GROUP_BINS': value}):
                self.assertIs(host.client_group_bins_requested(), expected)
        with mock.patch.dict(os.environ, {'COH_CLIENT_GROUP_BINS': 'on'}), self.assertRaises(ValueError):
            host.client_group_bins_requested()
        source = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertIn("command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_GROUP_BINS=1')", source)
        record = {'format': 1, 'requested': True, 'applied': True, 'folder': 'armport-group-bins-0',
                  'present_before_launch': True, 'removed_other_identities': 0, 'error': None}
        line = host.start_options_line({'client_group_bins': record}, 'reopen')
        self.assertIn('"client_group_bins":{"requested":true,"applied":true,"present_before_launch":true,"error":null}', line)
        self.assertIn('"client_group_bins":null', host.start_options_line({}, 'reopen'))
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn('      client_group_bins:\n', workflow)
        self.assertIn("  COH_CLIENT_GROUP_BINS: ${{ inputs.client_group_bins && '1' || '' }}\n", workflow)
        loads = host.client_zone_loads('ArmPort zone: 5 map.start maps/a/b.txt tid=1\n'
                                       'ARMPORT_GROUP_LOAD_V1 total_ms=2100 full=341 full_ms=1800 bin=341 text=0 wrote=0\n')
        self.assertTrue(loads[0]['group_load'].endswith('bin=341 text=0 wrote=0'))
        runtime = (ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java').read_text()
        self.assertIn('"COH_CLIENT_GROUP_BINS="+(clientGroupBinsRequested?"1":"0")', runtime)
        self.assertNotIn('COH_CLIENT_LIBRARY_BOUNDS', runtime)          # the kept bounds stay a CI switch


if __name__ == '__main__':
    unittest.main()
