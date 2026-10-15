import io
import json
import tempfile
from pathlib import Path
import unittest
import zipfile
import analyze_thor_performance as report


class PerformanceReportTests(unittest.TestCase):
    def data(self):
        android = {'app_version':'0.13.14','started_uptime_ms':1000,'login_observed_uptime_ms':13000,
            'character_connected_observed_uptime_ms':18000,'decoded_frame_count':120}
        guest = {'stages':[{'stage':'local_dbserver_startup','started_utc':'2026-10-06T03:00:00+00:00',
            'finished_utc':'2026-10-06T03:00:08+00:00'}, {'stage':'actual_client_startup',
            'started_utc':'2026-10-06T03:00:10+00:00','finished_utc':'2026-10-06T03:00:12+00:00'}],
            'character_reopen':{'private_map_data':{'preparation_elapsed_seconds':6,
            'server_data_cache':{'reused':False,'key':'current'}}},
            'texture_header_index':{'preparation_seconds':2}}
        return android,guest

    def test_subphases_not_counted_twice_or_frames_called_fps(self):
        result = report.summarize(*self.data())
        self.assertEqual(result['timing_seconds']['guest_to_client_ready'],12)
        self.assertEqual(result['timing_seconds']['unlabelled_preparation_and_gaps'],2)
        self.assertEqual(result['subphases_not_additive']['server_preparation']['remaining_stage_seconds'],2)
        self.assertEqual(result['timing_seconds']['login_to_world_observation'],5)
        self.assertIsNone(result['measured_game_fps'])

    def test_missing_observation_is_not_negative_elapsed(self):
        a,g=self.data();a['login_observed_uptime_ms']=-1
        self.assertIsNone(report.summarize(a,g)['timing_seconds']['operation_to_login_observation'])

    def test_overlap_or_impossible_preparation_rejected(self):
        a,g=self.data();g['stages'][1]['started_utc']='2026-10-06T03:00:07+00:00'
        with self.assertRaises(ValueError):report.summarize(a,g)
        a,g=self.data();g['character_reopen']['private_map_data']['preparation_elapsed_seconds']=9
        with self.assertRaises(ValueError):report.summarize(a,g)

    def test_nested_zip_and_duplicate_member_guard(self):
        a,g=self.data()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'support.zip';inner=io.BytesIO()
            with zipfile.ZipFile(inner,'w') as z:z.writestr('latest-report.json',json.dumps(g))
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('android-client-report.json',json.dumps(a));z.writestr('guest-report.zip',inner.getvalue())
            result=report.analyze(path);self.assertEqual(result['support_zip']['bytes'],path.stat().st_size)
            with zipfile.ZipFile(path) as z:
                with self.assertRaises(ValueError):report.read_member(z,'guest-report.zip',1)
            with zipfile.ZipFile(path,'a') as z:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore');z.writestr('android-client-report.json','{}')
            with self.assertRaises(ValueError):report.analyze(path)


if __name__=='__main__':unittest.main()
