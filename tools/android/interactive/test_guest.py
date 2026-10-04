"""Session-bound interaction completion without repeating the startup workload."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'android/guest'))
import client_interactive_diagnostic as guest

SESSION='0123456789abcdef0123456789abcdef'


def request(session=SESSION,pid=44):
    return {'format':1,'session_id':session,'client_pid':pid,'action':'finish_interaction'}


class FinishRequestTests(unittest.TestCase):
    def test_exact_identity_regular_file_size_and_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'finish.json'
            self.assertIsNone(guest.read_finish_request(path,SESSION,44))
            path.write_text(json.dumps(request()))
            self.assertEqual(guest.read_finish_request(path,SESSION,44)['client_pid'],44)
            for value in [request('f'*32),request(pid=45),request(pid=True),dict(request(),format=True),
                          dict(request(),extra=1),dict(request(),action='stop')]:
                with self.subTest(value=value):
                    path.write_text(json.dumps(value))
                    with self.assertRaises(guest.base.DiagnosticError):guest.read_finish_request(path,SESSION,44)
            path.write_bytes(b'x'*4097)
            with self.assertRaises(guest.base.DiagnosticError):guest.read_finish_request(path,SESSION,44)
            path.unlink();path.symlink_to(Path(temp)/'missing')
            with self.assertRaises(OSError):guest.read_finish_request(path,SESSION,44)
            path.unlink();path.write_text(json.dumps(request()));os.link(path,Path(temp)/'alias')
            with self.assertRaises(guest.base.DiagnosticError):guest.read_finish_request(path,SESSION,44)


class InteractionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        self.elapsed=0.0
        def sleep(seconds):self.elapsed=round(self.elapsed+seconds,6)
        clock=SimpleNamespace(monotonic=lambda:self.elapsed,sleep=sleep)
        for target,name,value in [(guest,'time',clock),(guest.base,'validate_runtime_probe',Mock(return_value={}))]:
            patched=patch.object(target,name,value);patched.start();self.addCleanup(patched.stop)
        self.observer=Mock();self.observer.windows.return_value=[{
            'title':'City of Heroes : PID: 44','mapped':True,'width':800,'height':600}]
        patched=patch.object(guest,'XObserver',return_value=self.observer);patched.start();self.addCleanup(patched.stop)
        self.output=(guest.startup.LAUNCH_MARKER+json.dumps({'session_id':SESSION,'pid':44})+'\n'
            +guest.startup.CONSOLE_MARKER+json.dumps({'session_id':SESSION,'pid':44,'attached':True})
            +'\nRenderer initialization complete\nLoaded all data!\n')
        self.registry='    GameProgress    REG_SZ    game_mainLoop\n'
        d=guest.ClientInteractiveDiagnostic.__new__(guest.ClientInteractiveDiagnostic)
        d.args=SimpleNamespace(wine=root/'wine',assets=root,session_id=SESSION,
            startup_timeout_seconds=900,observation_seconds=30,interaction_seconds=180)
        d.finish_path=root/'interaction-finish.json';d.work=root;d.presentation_socket=root/'view.sock'
        d.capture_dir=root/'captures';d.capture_dir.mkdir();d.captures=[]
        d.wine_env={'DISPLAY':':100'};d.startup_complete=False
        d.initialize=Mock();d.start_wine=Mock();d.mark_wine_ready=Mock();d.save_evidence=Mock()
        self.blank_until=0
        def capture(path):
            blank=path.name=='client-observed.ppm' and self.elapsed<self.blank_until
            data=b'P6\n1 1\n255\n'+(b'\0\0\0' if blank else b'\xff\xff\xff')
            path.write_bytes(data)
            return {'path':path.name,'sha256':guest.hashlib.sha256(data).hexdigest(),
                    'distinct_colors_capped':1 if blank else 16,'width':800,'height':600}
        self.observer.capture.side_effect=capture
        d.xserver=Mock();d.xserver.process.poll.return_value=None
        child=Mock();child.process.poll.return_value=None;child.text.side_effect=lambda:self.output
        d.ctx=Mock(report={});d.ctx.start.return_value=child
        d.ctx.run.side_effect=lambda label,*a,**kw:{'output':self.registry if label=='client-progress-registry' else ''}
        self.events=[]
        d.ctx.event.side_effect=lambda kind,**fields:self.events.append((self.elapsed,kind,fields))
        self.d=d

    def finish_when_ready(self):
        original=self.d.ctx.event.side_effect
        def event(kind,**fields):
            original(kind,**fields)
            if kind=='client_interaction_ready':self.d.finish_path.write_text(json.dumps(request()))
        self.d.ctx.event.side_effect=event

    def test_no_finish_request_keeps_one_live_session_until_180_seconds(self):
        self.d.execute()
        self.assertEqual(self.elapsed,180)
        self.assertEqual(self.d.ctx.report['interaction_completion_reason'],'interaction_timeout')
        self.assertTrue(self.d.ctx.report['interaction_session_completed'])
        self.assertFalse(self.d.ctx.report['input_effect_verified'])
        self.assertEqual([e[1] for e in self.events].count('client_interaction_ready'),1)
        self.assertEqual(self.d.ctx.start.call_count,1)

    def test_early_finish_waits_30_seconds_and_passes_exact_session(self):
        self.finish_when_ready()
        self.d.execute()
        self.assertEqual(self.elapsed,30)
        self.assertEqual(self.d.ctx.report['interaction_completion_reason'],'finish_requested')
        self.assertEqual(self.d.ctx.report['interaction_finish_request']['session_id'],SESSION)
        self.assertTrue(self.d.ctx.passed.call_args.kwargs['bounded_live_observation'])

    def test_stale_request_never_launches_a_client(self):
        self.d.finish_path.write_text(json.dumps(request()))
        with self.assertRaisesRegex(guest.base.DiagnosticError,'Stale'):self.d.execute()
        self.d.ctx.start.assert_not_called()

    def test_window_loss_or_late_console_truncation_cannot_complete(self):
        def windows():
            return self.observer.windows.return_value if self.elapsed<5 else []
        self.observer.windows.side_effect=windows
        with self.assertRaisesRegex(guest.base.DiagnosticError,'disappeared'):self.d.execute()
        self.assertFalse(self.d.startup_complete)

    def test_live_client_menu_to_world_title_transition_keeps_interaction_alive(self):
        windows=self.observer.windows.return_value
        world='City of Heroes : City_Zones/City_01_01/City_01_01.txt  PID: 44'
        self.observer.windows.side_effect=lambda:windows if self.elapsed<5 else [dict(windows[0],title=world)]
        self.d.execute()
        self.assertEqual(self.elapsed,180)
        self.assertTrue(self.d.startup_complete)
        self.assertEqual(self.d.ctx.report['interaction_completion_reason'],'interaction_timeout')
        self.assertEqual(self.d.ctx.report['client_windows'][0]['title'],world)
        self.assertEqual([e[1] for e in self.events].count('client_interaction_ready'),1)

    def test_final_capture_rechecks_complete_console(self):
        original=self.observer.capture.side_effect
        def capture(path):
            result=original(path)
            if path.name=='client-observed.ppm':self.output+='COH_CLIENT_CONSOLE_TRUNCATED_V1\n'
            return result
        self.observer.capture.side_effect=capture
        with self.assertRaisesRegex(guest.base.DiagnosticError,'exceeded observation budget'):self.d.execute()
        self.assertFalse(self.d.startup_complete)
        self.assertFalse(any(call.kwargs.get('bounded_live_observation') for call in self.d.ctx.passed.call_args_list))

    def test_transient_blank_retries_fresh_frame_and_preserves_blank_evidence(self):
        self.finish_when_ready();self.blank_until=37
        self.d.execute()
        self.assertEqual(self.elapsed,40)
        settling=self.d.ctx.report['final_frame_settling']
        self.assertEqual(settling['status'],'settled')
        self.assertEqual(settling['elapsed_seconds'],10)
        self.assertEqual(settling['blank_capture_count'],2)
        self.assertEqual([s['elapsed_seconds'] for s in settling['captures']],[0,5,10])
        for shot in settling['captures']:
            self.assertEqual(guest.hashlib.sha256((self.d.capture_dir/shot['path']).read_bytes()).hexdigest(),shot['sha256'])
        self.assertEqual([s['path'] for s in self.d.ctx.report['screenshots']],
                         ['before-client.ppm','client-startup.ppm','client-observed.ppm'])
        self.assertTrue(self.d.startup_complete)
        self.assertEqual(self.d.ctx.report['observation_seconds'],40)

    def test_sustained_blank_never_extends_original_interaction_deadline(self):
        self.finish_when_ready();self.blank_until=1000
        with self.assertRaisesRegex(guest.base.DiagnosticError,'remained blank.*deadline'):self.d.execute()
        self.assertEqual(self.elapsed,180)
        settling=self.d.ctx.report['final_frame_settling']
        self.assertEqual(settling['status'],'failed')
        self.assertEqual(settling['elapsed_seconds'],150)
        self.assertEqual(settling['blank_capture_count'],30)
        retained=[shot for shot in settling['captures'] if shot['retained']]
        self.assertEqual([shot['path'] for shot in retained],
                         ['client-settling-001.ppm','client-settling-002.ppm','client-settling-030.ppm'])
        self.assertEqual(len(list(self.d.capture_dir.glob('client-settling-*.ppm'))),3)
        self.assertTrue(all((self.d.capture_dir/shot['path']).exists()==shot['retained']
                            for shot in settling['captures']))
        self.assertFalse(self.d.startup_complete)

    def test_blank_at_automatic_timeout_has_no_extra_recovery_budget(self):
        self.blank_until=1000
        with self.assertRaisesRegex(guest.base.DiagnosticError,'remained blank.*deadline'):self.d.execute()
        self.assertEqual(self.elapsed,180)
        self.assertEqual(self.d.ctx.report['final_frame_settling']['blank_capture_count'],1)

    def test_client_exit_during_blank_wait_is_fatal_without_waiting_for_next_capture(self):
        self.finish_when_ready();self.blank_until=37
        self.d.ctx.start.return_value.process.poll.side_effect=lambda:0 if self.elapsed>=31 else None
        with self.assertRaisesRegex(guest.base.DiagnosticError,'client exited'):self.d.execute()
        self.assertEqual(self.elapsed,31)
        self.assertFalse(self.d.startup_complete)

    def test_display_exit_during_blank_wait_is_fatal(self):
        self.finish_when_ready();self.blank_until=37
        self.d.xserver.process.poll.side_effect=lambda:0 if self.elapsed>=31 else None
        with self.assertRaisesRegex(guest.base.DiagnosticError,'presentation display exited'):self.d.execute()
        self.assertEqual(self.elapsed,31)
        self.assertFalse(self.d.startup_complete)

    def test_nonblank_recovery_finishing_after_deadline_cannot_pass(self):
        self.finish_when_ready();self.blank_until=175
        original=self.observer.capture.side_effect
        def capture(path):
            result=original(path)
            if path.name=='client-observed.ppm' and self.elapsed>=175:self.elapsed+=6
            return result
        self.observer.capture.side_effect=capture
        with self.assertRaisesRegex(guest.base.DiagnosticError,'frame exceeded.*deadline'):self.d.execute()
        self.assertFalse(self.d.startup_complete)

    def test_replacement_pid_window_cannot_satisfy_recovery(self):
        self.finish_when_ready();self.blank_until=37
        windows=self.observer.windows.return_value
        self.observer.windows.side_effect=lambda:windows if self.elapsed<35 else [dict(windows[0],title='City of Heroes : PID: 45')]
        with self.assertRaisesRegex(guest.base.DiagnosticError,'window.*disappeared'):self.d.execute()
        self.assertEqual(self.elapsed,35)
        self.assertFalse(self.d.startup_complete)

    def test_console_truncation_during_blank_wait_remains_fatal(self):
        self.finish_when_ready();self.blank_until=37
        self.d.ctx.start.return_value.text.side_effect=lambda:self.output+('COH_CLIENT_CONSOLE_TRUNCATED_V1\n' if self.elapsed>=35 else '')
        with self.assertRaisesRegex(guest.base.DiagnosticError,'exceeded observation budget'):self.d.execute()
        self.assertFalse(self.d.startup_complete)

    def test_client_window_loss_during_nonblank_capture_cannot_pass(self):
        original=self.observer.capture.side_effect
        def capture(path):
            result=original(path)
            if path.name=='client-observed.ppm':self.observer.windows.return_value=[]
            return result
        self.observer.capture.side_effect=capture
        with self.assertRaisesRegex(guest.base.DiagnosticError,'window.*disappeared'):self.d.execute()
        self.assertFalse(self.d.startup_complete)


if __name__=='__main__':unittest.main()
