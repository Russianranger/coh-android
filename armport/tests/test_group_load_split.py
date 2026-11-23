"""Patch 0134: where a group file's load time goes on the client. Evidence only.

CI run 45175868959 (0.13.81, prepared group files on): a zone load that read all 541 group
files from their .bin still spent 5.6 s loading 341 object library files, against 6.4-7.5 s
when every file was parsed. So parsing was about a second of it. The patch times the three
leaf costs of the loader (reading a file, writing its .bin, loading its geometry file) and
adds them to patch 0131's line, so the next run says what the rest is.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'armport/patches/0134-armport-group-load-split.patch'
LOADER = 'Common/group/groupfileload.c'
TOTALS = 'Game/src/group/armport_group_load_log.h'
RECEIVE = 'Game/src/group/groupnetrecv.c'


def sections(patch):
    found, name = {}, None
    for line in patch.splitlines():
        match = re.match(r'diff --git a/(\S+)', line)
        if match:
            name = match.group(1); found[name] = {'added': [], 'removed': []}
        elif name is None or line.startswith(('+++', '---', '@@', 'index ')):
            continue
        elif line.startswith('+'):
            found[name]['added'].append(line[1:])
        elif line.startswith('-'):
            found[name]['removed'].append(line[1:])
    return found


class GroupLoadSplit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = sections(PATCH.read_text())

    def test_it_is_in_the_series_and_touches_the_loader_and_the_totals(self):
        series = (ROOT / 'armport/patches/series').read_text().split()
        self.assertEqual(series[series.index(PATCH.name) + 1], '0135-armport-transfer-boundaries.patch')
        self.assertEqual(sorted(self.sections), sorted([LOADER, TOTALS, RECEIVE]))

    def test_the_loader_only_gains_timers_around_the_same_calls(self):
        loader = self.sections[LOADER]
        # Two calls are replaced by a helper that makes the same call with the same arguments.
        self.assertEqual([line.strip() for line in loader['removed']], [
            'geoLoad(dir, LOAD_NOW, GEO_INIT_FOR_DRAWING | GEO_USED_BY_WORLD);',
            'geoLoad(gf->name, LOAD_NOW, GEO_INIT_FOR_DRAWING | GEO_USED_BY_WORLD);'])
        added = [line.strip() for line in loader['added']]
        self.assertIn('geoLoad(name, LOAD_NOW, GEO_INIT_FOR_DRAWING | GEO_USED_BY_WORLD);', added)
        self.assertEqual(added.count('armportGroupGeoLoad(dir);'), 1)
        self.assertEqual(added.count('armportGroupGeoLoad(gf->name);'), 1)
        # Every other added statement is a declaration, a clock read or a sum of clock reads.
        calls = set()
        for line in added:
            if line.startswith('//'):
                continue
            calls.update(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\(', line))
        self.assertEqual(calls, {'armportGroupSplitNow', 'armportGroupGeoLoad', 'QueryPerformanceCounter',
                                 'geoLoad'})
        text = '\n'.join(loader['added'])
        self.assertNotIn('getenv', text)
        self.assertNotIn('printf', text)
        # The server has no geoLoad: the helper exists only where its callers do.
        self.assertRegex(text, r'#if CLIENT\nstatic void armportGroupGeoLoad\(const char \*name\)\n\{[^}]*\}\n#endif')

    def test_the_three_costs_are_leaves_and_never_contain_one_another(self):
        text = '\n'.join(self.sections[LOADER]['added'])
        # The text read ends before the .bin write begins, at one clock value.
        self.assertIn('armport_text_done = armportGroupSplitNow();\n'
                      '        armport_group_read_ticks += armport_text_done - armport_text_began;', text)
        self.assertIn('armport_group_write_ticks += armportGroupSplitNow() - armport_text_done;', text)
        self.assertIn('armport_group_read_ticks += armportGroupSplitNow() - armport_read_began;', text)
        self.assertEqual(text.count('armport_group_geo_ticks +='), 1)

    def test_the_line_gains_four_fields_at_its_end(self):
        totals = '\n'.join(self.sections[TOTALS]['added'])
        self.assertIn('" read_ms=%u write_ms=%u geoload=%u geoload_ms=%u\\n",', totals)
        self.assertIn('char line[520];', totals)
        self.assertEqual([line.strip() for line in self.sections[TOTALS]['removed'] if 'cached=%u' in line],
                         ['" cached=%u cached_ms=%u kept=%u bin=%u text=%u wrote=%u\\n",'])
        receive = '\n'.join(self.sections[RECEIVE]['added'])
        self.assertEqual(self.sections[RECEIVE]['removed'], [])
        for name, ticks in (('read_time', 'armport_group_read_ticks'), ('write_time', 'armport_group_write_ticks'),
                            ('geoload_time', 'armport_group_geo_ticks')):
            self.assertIn('armport_group_load.%s = %s;' % (name, ticks), receive)
            self.assertIn('armport_group_load.%s = %s - armport_group_load.%s;' % (name, ticks, name), receive)


if __name__ == '__main__':
    unittest.main()
