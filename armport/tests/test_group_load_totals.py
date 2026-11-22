"""0.13.80: the client says where a zone load's group-file time goes (patch 0131).

Thor 0.13.79 (export 20261121-202117): "map.start" to "groups.files.done" was 5.5-6.8 s of
every zone load and the quiet log held nothing inside it. Patch 0131 adds up the time of the
calls that span makes (same calls, same order) and prints one ARMPORT_GROUP_LOAD_V1 line per
new world; in the quiet log the map file and its layers also keep their "library." records.
The CI host script reports both per load. Evidence only: nothing here gates a session.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'armport/patches/0131-armport-group-load-totals.patch'
TRACE = 'libs/UtilitiesLib/include/utilitieslib/utils/armport_zone_trace.h'
HEADER = 'Game/src/group/armport_group_load_log.h'
RECEIVE = 'Game/src/group/groupnetrecv.c'


def load_host():
    sys.path[:0] = [str(ROOT / 'armport/app')]
    import interactive_host
    return interactive_host


def sections(patch):
    """Per file: its added lines, and the changed hunks before and after (with their context)."""
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


class GroupLoadTotals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.sections = sections(cls.patch)

    def test_it_is_the_last_patch_and_touches_three_client_files(self):
        self.assertEqual((ROOT / 'armport/patches/series').read_text().split()[-1], PATCH.name)
        self.assertEqual(sorted(self.sections), sorted([HEADER, RECEIVE, TRACE]))
        # The server builds pin these two sources; the measurement stays out of them.
        self.assertNotIn('groupfileload.c', self.patch)
        self.assertNotIn('FolderCache.c', self.patch)

    def test_the_receive_code_keeps_its_calls_and_their_order(self):
        section = self.sections[RECEIVE]
        before, after, added = ('\n'.join(section[key]) for key in ('before', 'after', 'added'))
        # Every game call of the changed hunks is still made, once, in the same order.
        calls = re.compile(r'\b(?:pkt\w+|receive\w+|group\w+|getGeo|objectLibrary\w+|clientLoadMapStart|setClientFlags)\(')
        self.assertEqual(calls.findall(after), calls.findall(before))
        self.assertGreaterEqual(len(calls.findall(before)), 12)
        for call in ('groupLoadRequiredLibsForDef(def);', 'getGeo(pktGetString(pak),def);', 'groupFileFind(fname)',
                     'objectLibraryLoadBoundsFile(fname,checksum)', 'groupLoadFull(fname);', 'groupLoadTo(fname,loadto);',
                     'clientLoadMapStart(fname);', 'receiveDef(pak,def_id,file);'):
            self.assertEqual(after.count(call), 1, call)
        # A library file is only loaded in full when it is neither known nor accepted by its bounds.
        self.assertRegex(after, r'if \(groupFileFind\(fname\)\)\s+armport_group_load\.known\+\+;\s+'
                                r'else if \(objectLibraryLoadBoundsFile\(fname,checksum\)\)')
        self.assertRegex(after, r'else\s+\{\s+long long armport_full = armportGroupLoadNow\(\);\s+'
                                r'armport_group_load\.bounds_time \+= armport_full - armport_began;\s+groupLoadFull\(fname\);')
        # Totals start at map.start and are printed before groups.files.done; no new trace record.
        self.assertLess(after.index('armportZoneTrace("map.start", fname);'), after.index('armportGroupLoadBegin();'))
        self.assertLess(after.index('armportGroupLoadEnd();'), after.index('armportZoneTrace("groups.files.done", NULL);'))
        self.assertNotIn('armportZoneTrace(', added)

    def test_the_line_is_only_written_with_the_stdio_log_and_once_per_world(self):
        header = '\n'.join(self.sections[HEADER]['added'])
        self.assertIn('if (getenv("ARMPORT_STDIO_LOG"))', header)
        self.assertIn('if (!t->active)\n        return;', header)
        self.assertIn('armport_group_load.active = 0;', header)
        fields = re.findall(r'(\w+)=%u', header)
        self.assertEqual(fields, ['total_ms', 'start_ms', 'files', 'sent', 'known', 'bounds', 'bounds_ms', 'full',
                                  'full_ms', 'map_ms', 'defs', 'defs_ms', 'libs_ms', 'geo', 'geo_ms'])

    def test_the_quiet_log_keeps_map_file_records_only(self):
        trace = '\n'.join(self.sections[TRACE]['added'])
        self.assertIn('if (!strncmp(stage, "library.", 8) && armportZoneTraceIsMapFile(detail)) return 0;', trace)
        self.assertIn('if (armportZoneTraceQuietDrops(stage, detail)) return;', trace)
        compiler = shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
        if compiler is None:
            self.skipTest('no host C compiler')
        body = trace[trace.index('static int armportZoneTraceIsMapFile'):trace.index('static int armportZoneTraceQuietDrops')]
        program = '#include <stdio.h>\n' + body + '''
int main(int argc, char **argv) { int i; for (i = 1; i < argc; ++i) putchar('0' + armportZoneTraceIsMapFile(argv[i]));
    putchar('0' + armportZoneTraceIsMapFile(0)); return 0; }
'''
        with tempfile.TemporaryDirectory() as temporary:
            source, binary = Path(temporary) / 'check.c', Path(temporary) / 'check'
            source.write_text(program)
            subprocess.run([compiler, '-Wall', '-Werror', str(source), '-o', str(binary)], check=True)
            output = subprocess.run([str(binary), 'maps/City_Zones/V_City_01_02/V_City_01_02.txt',
                                     'C:/game/data/MAPS\\City_Zones/a/a_layer_b.txt',
                                     'object_library/streets/roadmaps.txt', 'object_library/maps', 'map', ''],
                                    check=True, capture_output=True, text=True).stdout
        self.assertEqual(output, '1100000')

    def test_ci_reports_each_load_from_the_client_log(self):
        host = load_host()
        log = '\n'.join([
            'ArmPort zone: 90 groups.files.done  tid=816',                      # before any map.start: ignored
            'ArmPort zone: 100 map.start maps/City_Zones/V_City_01_01/V_City_01_01.txt tid=816',
            'ArmPort zone: 150 library.begin maps/City_Zones/V_City_01_01/V_City_01_01.txt tid=816',
            'ArmPort zone: 2150 library.parsed maps/City_Zones/V_City_01_01/V_City_01_01.txt tid=816',
            'grp70466 Needed to be renamed. Only should happen when you\'re importing a file or hand editing a mapfile.',
            'ArmPort zone: 5150 library.done maps/City_Zones/V_City_01_01/V_City_01_01.txt tid=816',
            'ARMPORT_GROUP_LOAD_V1 total_ms=6600 start_ms=40 files=310 sent=310 known=0 bounds=309 bounds_ms=900'
            ' full=0 full_ms=0 map_ms=5000 defs=12 defs_ms=600 libs_ms=500 geo=3 geo_ms=1',
            'ArmPort zone: 6700 groups.files.done  tid=816',
            'ArmPort zone: 6702 groups.refs.done  tid=816',
            'ArmPort zone: 7300 map.finish.done  tid=816',
            'ArmPort zone: 7700 collision.done  tid=816',
            'ArmPort zone: 8100 textures.done  tid=816',
            'ArmPort zone: 8101 ready.sent  tid=816',
            'ArmPort zone: 8400 allents.done  tid=816',
            'ARMPORT_GROUP_LOAD_V1 total_ms=1 start_ms=0 files=0 sent=0 known=0 bounds=0 bounds_ms=0'
            ' full=0 full_ms=0 map_ms=0 defs=0 defs_ms=0 libs_ms=0 geo=0 geo_ms=0',   # no load open: ignored
            'ArmPort zone: 4294967290 map.start maps/City_Zones/V_City_01_02/V_City_01_02.txt tid=816',
            'ArmPort zone: 10 groups.files.done  tid=816',                    # the tick counter wrapped
        ])
        loads = host.client_zone_loads(log)
        self.assertEqual(len(loads), 2)
        first, second = loads
        self.assertEqual(first['map'], 'V_City_01_01.txt')
        self.assertEqual(first['ms'], {'groups.files.done': 6600, 'groups.refs.done': 6602, 'map.finish.done': 7200,
                                       'collision.done': 7600, 'textures.done': 8000, 'ready.sent': 8001})
        self.assertTrue(first['group_load'].startswith('total_ms=6600 start_ms=40 files=310 '))
        self.assertEqual(first['map_files'], [['begin', 'V_City_01_01.txt', 50], ['parsed', 'V_City_01_01.txt', 2050],
                                              ['done', 'V_City_01_01.txt', 5050]])
        self.assertEqual(second, {'map': 'V_City_01_02.txt', 'ms': {'groups.files.done': 16}, 'map_files': []})
        self.assertEqual(host.client_zone_loads(''), [])
        self.assertEqual(len(host.client_zone_loads('\n'.join([log] * 3))), 3)
        # Its own notice, apart from the other details, and nothing when no load was seen.
        lines = host.timing_notices({'reopen': {'proot_mode': None, 'client_zone_loads': loads}}, True, True)
        notice = [line for line in lines if 'client zone loads reopen' in line]
        self.assertEqual(len(notice), 1)
        self.assertEqual(json.loads(notice[0].split('::', 2)[2])['client_zone_loads'][0]['map'], 'V_City_01_01.txt')
        self.assertNotIn('client_zone_loads', lines[0])
        self.assertEqual([line for line in host.timing_notices({'reopen': {'proot_mode': None, 'client_zone_loads': []}},
                                                               True, True) if 'client zone loads' in line], [])


if __name__ == '__main__':
    unittest.main()
