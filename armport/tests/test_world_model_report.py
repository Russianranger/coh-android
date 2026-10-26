import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import world_model_report
import zone_report

DRAW = 'frame=600 refs=34 roots=34 root_models=0 vis=0 outside=1 zocc=0 fog=0 visits=100 editor_skip=60 distance_skip=20 frustum_skip=10 model_calls=0 not_loaded=0 alpha_zero=0 sort_requests=0'
MODEL = 'frame=600 visits=8 editor_skip=4 distance_skip=2 frustum_skip=2 postchecks=0'


def record(stage, text, tid=36):
    return json.dumps(dict(stage=stage,text=text,tid=tid))+'\n'


class WorldModels(unittest.TestCase):
    def test_consistent_counts_do_not_prove_cause_or_pixels(self):
        result=world_model_report.summarize([record('world.draw',DRAW),record('world.models',MODEL)])
        self.assertTrue(result['observations_valid'])
        self.assertFalse(result['all_sampled_model_visits_zero'])
        self.assertTrue(result['all_sampled_postchecks_zero'])
        self.assertFalse(result['cause_established'])
        self.assertFalse(result['rendering_acceptance_changed'])

    def test_missing_torn_duplicate_and_excess_records_are_unknown(self):
        draw,model=record('world.draw',DRAW),record('world.models',MODEL)
        for lines in ([],[draw],[model],[draw,model[:-1]],[draw,model[:-5]],
                      [draw,model,model],[draw,model]*9,[draw,model,'{"stage":"world.models"'],
                      [draw,record('world.models',MODEL,True)],['[]\n',draw,model]):
            result=world_model_report.summarize(lines)
            self.assertFalse(result['observations_valid'])
            self.assertIsNone(result['all_sampled_postchecks_zero'])

    def test_arithmetic_frame_thread_and_subset_must_agree(self):
        bad=[MODEL.replace('postchecks=0','postchecks=1'),
             MODEL.replace('frame=600','frame=1200'),
             'frame=600 visits=100 editor_skip=80 distance_skip=10 frustum_skip=10 postchecks=0',
             'frame=600 visits=11 editor_skip=0 distance_skip=0 frustum_skip=0 postchecks=11']
        for text in bad:
            result=world_model_report.summarize([record('world.draw',DRAW),record('world.models',text)])
            self.assertFalse(result['observations_valid'])
        self.assertFalse(world_model_report.summarize([record('world.draw',DRAW),record('world.models',MODEL,37)])['observations_valid'])

    def test_zero_models_and_postcheck_survivors_are_separate(self):
        for counts,zero,postzero in [('visits=0 editor_skip=0 distance_skip=0 frustum_skip=0 postchecks=0',True,True),
                                     ('visits=1 editor_skip=0 distance_skip=0 frustum_skip=0 postchecks=1',False,False)]:
            result=world_model_report.summarize([record('world.draw',DRAW),record('world.models','frame=600 '+counts)])
            self.assertTrue(result['observations_valid'])
            self.assertEqual(result['all_sampled_model_visits_zero'],zero)
            self.assertEqual(result['all_sampled_postchecks_zero'],postzero)

    def test_caller_keeps_termination_and_writes_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);trace=root/'zone-trace.jsonl'
            for ending,expected in [('\n',True),('\r\n',True),('',False)]:
                trace.write_bytes((record('world.draw',DRAW)+record('world.models',MODEL).rstrip('\n')+ending).encode())
                sections=dict(zone_report.sections(root,root))
                self.assertEqual(json.loads(sections['ArmPort M3 model traversal'])['observations_valid'],expected)
                self.assertEqual(json.loads((root/'world-model-summary.json').read_text())['observations_valid'],expected)
