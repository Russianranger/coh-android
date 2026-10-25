import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import world_camera_report
import zone_report
from test_world_model_report import DRAW,MODEL,record

CAMERA='frame=600 camera=10,20,30 view0=1,0,0 view1=0,1,0 view2=0,0,1 view3=-10,-20,-30 player=1 player_svr_idx=1 player_pos=10,20,40 player_net_ipos=640,1280,2560'

def lines(text=CAMERA,tid=36):return [record('world.draw',DRAW),record('world.models',MODEL),record('world.camera',text,tid)]

class CameraReport(unittest.TestCase):
    def test_literal_coordinates_and_residuals_not_rendering_verdict(self):
        r=world_camera_report.summarize(lines());self.assertTrue(r['observations_valid'])
        self.assertEqual(r['samples'][0]['camera_in_view'],[0,0,0]);self.assertEqual(r['samples'][0]['camera_player_distance'],10)
        self.assertEqual(r['samples'][0]['player_net_ipos'],[640,1280,2560]);self.assertFalse(r['cause_established']);self.assertFalse(r['rendering_acceptance_changed'])
        r=world_camera_report.summarize(lines(CAMERA.replace('view3=-10,-20,-30','view3=0,0,0')))
        self.assertTrue(r['observations_valid']);self.assertEqual(r['samples'][0]['camera_in_view'],[10,20,30]);self.assertFalse(r['cause_established'])

    def test_no_player_and_exponents(self):
        r=world_camera_report.summarize(lines(CAMERA.replace('player=1','player=0').replace('camera=10','camera=1e1')))
        self.assertTrue(r['observations_valid']);self.assertIsNone(r['samples'][0]['camera_player_distance'])

    def test_torn_malformed_nonfinite_and_mismatched_observations(self):
        bad=[[],lines()[:-1],lines()+[lines()[-1]],lines()[:-1]+[lines()[-1][:-1]],lines(tid=True),lines(tid=37),lines(CAMERA.replace('frame=600','frame=601')),lines(CAMERA.replace('camera=10','camera=nan')),lines(CAMERA.replace('camera=10','camera=1e309')),lines(CAMERA.replace('player=1','player=2')),lines(CAMERA+' junk'),lines()+['[]\n']]
        for case in bad:self.assertFalse(world_camera_report.summarize(case)['observations_valid'],case)

    def test_eight_bounded_samples_and_bad_ninth(self):
        data=[]
        for i in range(1,9):data.extend(x.replace('frame=600',f'frame={i*600}') for x in lines())
        self.assertTrue(world_camera_report.summarize(data)['observations_valid'])
        self.assertFalse(world_camera_report.summarize(data+[record('world.camera',CAMERA.replace('frame=600','frame=5400'))])['observations_valid'])

    def test_report_caller_preserves_record_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for ending,expected in [('\n',True),('\r\n',True),('',False)]:
                (root/'zone-trace.jsonl').write_bytes((''.join(lines()).rstrip('\n')+ending).encode())
                sections=dict(zone_report.sections(root,root));self.assertEqual(json.loads(sections['ArmPort M3 camera/player inputs'])['observations_valid'],expected)
                self.assertEqual(json.loads((root/'world-camera-summary.json').read_text())['observations_valid'],expected)
