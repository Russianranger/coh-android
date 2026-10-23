"""Regression for false rendered-world verdicts, including review's black frame."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import zone_frame

MAP = 'ArmPort zone: 100 map.start maps/City_Zones/City_01_01/City_01_01.txt\n'
DONE = MAP + 'ArmPort zone: 101 textures.done \nArmPort zone: 102 ready.sent \n'


class ZoneFrameTests(unittest.TestCase):
    def test_requires_completion_after_latest_map(self):
        self.assertTrue(zone_frame.load_state(DONE)['load_complete'])
        for log in ('', MAP, DONE + MAP, DONE.replace('textures.done', 'textures.wait'),
                    DONE.replace('City_01_01', 'City_02_01')):
            self.assertFalse(zone_frame.load_state(log)['load_complete'])

    def test_thread_identity_does_not_change_map(self):
        self.assertEqual(zone_frame.load_state(DONE),
                         zone_frame.load_state(DONE.replace('\n', ' tid=128\n')))

    @unittest.skipUnless(shutil.which('convert'), 'ImageMagick required')
    def test_blank_frames_and_missing_map_name_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            for source in ('xc:black', 'xc:white', 'xc:gray50', 'pattern:checkerboard'):
                png = Path(tmp) / 'frame.png'
                subprocess.run(['convert', '-size', '1600x1200', source, str(png)], check=True)
                window = (104, 130, 1024, 768)
                result = zone_frame.evaluate(png, window, DONE, lambda _: 'Atlas Park')
                self.assertEqual(result['rendered'], source == 'pattern:checkerboard')
                self.assertFalse(zone_frame.evaluate(png, window, MAP, lambda _: 'Atlas Park')['rendered'])
                self.assertFalse(zone_frame.evaluate(png, window, DONE, lambda _: 'Loading')['rendered'])
                self.assertFalse(zone_frame.evaluate(png, None, DONE, lambda _: 'Atlas Park')['rendered'])


if __name__ == '__main__':
    unittest.main()
