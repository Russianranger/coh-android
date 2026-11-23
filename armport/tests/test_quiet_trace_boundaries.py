"""0.13.79: the device's quiet client log keeps the once-per-load boundaries of a zone load.

Thor 0.13.78 (export 20261121-053448): `map.start` to `textures.done` was 6.8-8.3 s of a
28-34 s trip through the spare zone server, and the quiet log (patch 0108) held nothing between
the two. Patch 0130 keeps the boundaries that occur once per load; per-file records stay dropped.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'armport/patches/0130-armport-quiet-trace-keeps-load-boundaries.patch'


class QuietTraceBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        added = '\n'.join(line[1:] for line in cls.patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        body = added[added.index('static const char *const keep[] = {'):]
        cls.keep = re.findall(r'"([^"]+)"', body[:body.index('};')])

    def kept(self, stage):
        return any(stage.startswith(prefix) for prefix in self.keep)

    def test_it_is_in_the_series_and_touches_only_the_trace_header(self):
        series = (ROOT / 'armport/patches/series').read_text().split()
        self.assertEqual(series[series.index(PATCH.name) + 1], '0131-armport-group-load-totals.patch')
        self.assertEqual(re.findall(r'^diff --git a/(\S+)', self.patch, re.M),
                         ['libs/UtilitiesLib/include/utilitieslib/utils/armport_zone_trace.h'])

    def test_the_boundaries_of_one_load_are_kept(self):
        for stage in ('map.start', 'groups.begin', 'groups.done', 'groups.files.done', 'groups.refs.done',
                      'map.finish.begin', 'map.finish.done', 'collision.begin', 'collision.done',
                      'scene.begin', 'scene.wait.done', 'allents.requested', 'allents.wait.done',
                      'textures.begin', 'geometry.wait', 'textures.wait', 'textures.done',
                      'texmodels.welded.begin', 'texmodels.done', 'ready.sent',
                      'client.error', 'client.fatal', 'dialog.alert.begin'):
            self.assertTrue(self.kept(stage), stage)

    def test_per_file_and_per_frame_records_stay_dropped(self):
        for stage in ('groupfile.begin', 'groupfile.loaded', 'groupfile.done', 'library.begin', 'library.parsed',
                      'texmodels.geo.begin', 'texmodels.geo.done', 'texqueue.start.apc', 'texqueue.drain.begin',
                      'world.def', 'world.draw', 'world.models', 'group.model', 'power.selected'):
            self.assertFalse(self.kept(stage), stage)


if __name__ == '__main__':
    unittest.main()
