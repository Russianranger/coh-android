"""Regression for false rendered-world verdicts, including review's black frame."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import zone_frame

HUD = 'No Target Nav Map Contact Mission Clues Chat Empty Tray Slot'
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
                result = zone_frame.evaluate(png, window, DONE, lambda _: HUD)
                self.assertEqual(result['rendered'], source == 'pattern:checkerboard')
                self.assertFalse(zone_frame.evaluate(png, window, MAP, lambda _: HUD)['rendered'])
                self.assertFalse(zone_frame.evaluate(png, window, DONE, lambda _: 'Loading')['rendered'])
                self.assertFalse(zone_frame.evaluate(png, None, DONE, lambda _: HUD)['rendered'])
                # A readable zone name is diagnostic only, never the world verdict.
                named = zone_frame.evaluate(png, window, DONE, lambda _: 'Atlas Park Target Chat')
                self.assertFalse(named['rendered'])
                self.assertEqual(named['map_name_visible'], source == 'pattern:checkerboard')

    @unittest.skipUnless(shutil.which('convert'), 'ImageMagick required')
    def test_modal_or_blank_world_region_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / 'frame.png'
            window = (104, 130, 1024, 768)
            subprocess.run(['convert', '-size', '1600x1200', 'pattern:checkerboard', str(png)], check=True)
            helper = HUD + ' Welcome! This character is new and may need help'
            result = zone_frame.evaluate(png, window, DONE, lambda _: helper)
            self.assertTrue(result['helper_dialog_visible'] and result['world_region_visible'])
            self.assertFalse(result['rendered'])
            self.assertFalse(zone_frame.evaluate(png, window, DONE, lambda _: 'Target Chat')['rendered'])
            # HUD over a flat (unrendered) centre: whole frame nonblank, world region not.
            x, y, w, h = zone_frame.world_region(window)
            subprocess.run(['convert', str(png), '-fill', 'gray30', '-draw',
                            f'rectangle {x},{y} {x + w - 1},{y + h - 1}', str(png)], check=True)
            flat = zone_frame.evaluate(png, window, DONE, lambda _: HUD)
            self.assertTrue(zone_frame.nonblank(flat['frame']))
            self.assertFalse(flat['world_region_visible'] or flat['rendered'])

    @unittest.skipUnless(shutil.which('convert'), 'ImageMagick required')
    def test_map_ocr_receives_only_client_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / 'screen.png'
            subprocess.run(['convert', '-size', '1600x1200', 'pattern:checkerboard', str(png)], check=True)
            def ocr(crop):
                result = subprocess.run(['identify', '-format', '%wx%h', str(crop)],
                                        capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout, '1024x768')
                return HUD
            self.assertTrue(zone_frame.evaluate(png, (104, 130, 1024, 768), DONE, ocr)['rendered'])


if __name__ == '__main__':
    unittest.main()
