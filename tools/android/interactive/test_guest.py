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
        d.wine_env={'DISPLAY':':100'};d.startup_complete=False
        d.initialize=Mock();d.start_wine=Mock();d.mark_wine_ready=Mock();d.save_evidence=Mock()
        d.capture=Mock(return_value={'distinct_colors_capped':16})
        d.xserver=Mock();d.xserver.process.poll.return_value=None
        child=Mock();child.process.poll.return_value=None;child.text.side_effect=lambda:self.output
        d.ctx=Mock(report={});d.ctx.start.return_value=child
        d.ctx.run.side_effect=lambda label,*a,**kw:{'output':self.registry if label=='client-progress-registry' else ''}
        self.events=[]
        d.ctx.event.side_effect=lambda kind,**fields:self.events.append((self.elapsed,kind,fields))
        self.d=d

    def test_no_finish_request_keeps_one_live_session_until_180_seconds(self):
        self.d.execute()
        self.assertEqual(self.elapsed,180)
        self.assertEqual(self.d.ctx.report['interaction_completion_reason'],'interaction_timeout')
        self.assertTrue(self.d.ctx.report['interaction_session_completed'])
        self.assertFalse(self.d.ctx.report['input_effect_verified'])
        self.assertEqual([e[1] for e in self.events].count('client_interaction_ready'),1)
        self.assertEqual(self.d.ctx.start.call_count,1)

    def test_early_finish_waits_30_seconds_and_passes_exact_session(self):
        original=self.d.ctx.event.side_effect
        def event(kind,**fields):
            original(kind,**fields)
            if kind=='client_interaction_ready':self.d.finish_path.write_text(json.dumps(request()))
        self.d.ctx.event.side_effect=event
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

    def test_final_capture_rechecks_complete_console(self):
        def capture(label):
            if label=='client-observed':self.output+='COH_CLIENT_CONSOLE_TRUNCATED_V1\n'
            return {'distinct_colors_capped':16}
        self.d.capture.side_effect=capture
        with self.assertRaisesRegex(guest.base.DiagnosticError,'exceeded observation budget'):self.d.execute()
        self.assertFalse(self.d.startup_complete)
        self.assertFalse(any(call.kwargs.get('bounded_live_observation') for call in self.d.ctx.passed.call_args_list))


if __name__=='__main__':unittest.main()
