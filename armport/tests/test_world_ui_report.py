import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import world_ui_report
import zone_report
from test_world_model_report import DRAW, MODEL, record

UI = 'frame=600 compass_mode=2 map_mode=0 mission_map=0 selected_task=0 selected_type=3 name_present=0 map_present=1'


def lines(text=UI, tid=36):
    return [record('world.draw', DRAW), record('world.models', MODEL), record('world.ui', text, tid)]


class UIReport(unittest.TestCase):
    def test_literal_state_is_not_a_rendering_verdict(self):
        for name in (0, 1):
            r = world_ui_report.summarize(lines(UI.replace('name_present=0', f'name_present={name}')))
            self.assertTrue(r['observations_valid'])
            self.assertEqual(r['samples_without_destination_name'], 1-name)
            self.assertEqual(r['samples'][0]['map_mode'], 0)
            self.assertEqual(r['samples'][0]['selected_type'], 3)
            self.assertFalse(r['cause_established'])
            self.assertFalse(r['rendering_acceptance_changed'])

    def test_missing_torn_malformed_duplicate_and_mismatched_records(self):
        bad = [[], lines()[:-1], lines()+[lines()[-1]], lines()[:-1]+[lines()[-1][:-1]],
               lines(tid=True), lines(tid=37), lines(UI+' junk'), lines()+['[]\n'],
               lines(UI.replace('frame=600', 'frame=1200')),
               lines(UI.replace('name_present=0', 'name_present=2')),
               lines(UI.replace('selected_task=0', 'selected_task=-1')),
               lines(UI.replace('map_present=1', 'map_present=9')),
               lines(UI.replace('map_mode=0', 'map_mode=2147483648'))]
        for case in bad:
            r = world_ui_report.summarize(case)
            self.assertFalse(r['observations_valid'], case)
            self.assertIsNone(r['samples_without_destination_name'])

    def test_eight_samples_and_ninth_rejection(self):
        data = []
        for frame in (1, 600, 1200, 1800, 2400, 3000, 3600, 4200):
            data.extend(x.replace('frame=600', f'frame={frame}') for x in lines())
        self.assertTrue(world_ui_report.summarize(data)['observations_valid'])
        self.assertFalse(world_ui_report.summarize(data+[record('world.ui', UI)])['observations_valid'])

    def test_no_invented_meaning_for_signed_modes_or_types(self):
        r = world_ui_report.summarize(lines(UI.replace('map_mode=0', 'map_mode=-7').replace('selected_type=3', 'selected_type=-2147483648')))
        self.assertTrue(r['observations_valid'])
        self.assertEqual(r['samples'][0]['map_mode'], -7)
        self.assertFalse(r['cause_established'])

    def test_report_integration_preserves_endings_and_missing_old_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for ending, expected in [('\n', True), ('\r\n', True), ('', False)]:
                (root/'zone-trace.jsonl').write_bytes((''.join(lines()).rstrip('\n')+ending).encode())
                sections = dict(zone_report.sections(root, root))
                self.assertEqual(json.loads(sections['ArmPort M3 camera/player inputs'])['ui_inputs']['observations_valid'], expected)
                self.assertEqual(json.loads((root/'world-ui-summary.json').read_text())['observations_valid'], expected)
            (root/'zone-trace.jsonl').write_text(''.join(lines()[:-1]))
            list(zone_report.sections(root, root))
            self.assertFalse(json.loads((root/'world-ui-summary.json').read_text())['observations_valid'])
