import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from world_draw_report import summarize

# Verbatim steady sample from run 40204814232, artifact 12605194825.
SAMPLE = 'ArmPort zone: 2349898 world.draw frame=600 refs=34 roots=34 root_models=0 vis=0 outside=1 zocc=0 fog=0 visits=4870 editor_skip=4534 distance_skip=307 frustum_skip=13 model_calls=0 not_loaded=0 alpha_zero=0 sort_requests=0 tid=36'

class WorldDrawReport(unittest.TestCase):
    def test_retained_sample_is_not_a_cause_or_rendering_verdict(self):
        r = summarize([SAMPLE])
        self.assertTrue(r['observations_valid'])
        self.assertEqual(r['samples'][0]['visited_after_first_three_checks'], 16)
        self.assertTrue(r['all_sampled_model_calls_zero'])
        self.assertFalse(r['cause_established'])
        self.assertFalse(r['rendering_acceptance_changed'])

    def test_missing_torn_duplicate_and_excess_samples_are_unknown(self):
        for lines in ([], [SAMPLE[:-4]], [SAMPLE, SAMPLE], [SAMPLE]*9,
                      [SAMPLE.replace('visits=4870', 'visits=1')],
                      [SAMPLE.replace('frame=600', 'frame=' + '9'*5000)]):
            with self.subTest(lines=len(lines)):
                r = summarize(lines)
                self.assertFalse(r['observations_valid'])
                self.assertIsNone(r['all_sampled_model_calls_zero'])

    def test_model_calls_do_not_imply_sort_or_visible_pixels(self):
        r = summarize([SAMPLE.replace('model_calls=0', 'model_calls=1')])
        self.assertFalse(r['all_sampled_model_calls_zero'])
        self.assertTrue(r['all_sampled_sort_requests_zero'])
        self.assertFalse(r['cause_established'])
