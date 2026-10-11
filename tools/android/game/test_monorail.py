"""Native station transport, current-epoch identity and source-chain contracts."""
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'android/guest'));sys.path.insert(0,str(ROOT/'tools'))
import native_monorail_events as events
import native_monorail_contract as contract
import prepare_monorail_source as source
SESSION='0123456789abcdef0123456789abcdef';START=1791689000000
PROGRESS={'available':True,'windows_pid':44,'main_thread_id':55}

def line(sequence=1,kind='ready',**changes):
    v=dict(session=SESSION,pid=44,tid=55,sequence=sequence,kind=kind,utc_ms=START+sequence,
        map_id=5,db_id=1,auth_id=17,port=777 if kind=='ready' else 0,request=0,target=0,x=0,y=0,z=0)
    v.update(changes)
    return ('COH_ZONING_EVENT_V1 session={session} pid={pid} tid={tid} sequence={sequence} kind={kind} '
        'utc_ms={utc_ms} map_id={map_id} db_id={db_id} auth_id={auth_id} name=THORHERO account=COHLOCAL '
        'peer=127.0.0.1:{port} request={request} target={target} position=<{x},{y},{z}>\n').format(**v)
def parse(text,**changes):
    k=dict(session=SESSION,progress=PROGRESS,launch_utc_ms=START,now_utc_ms=START+100000,db_id=1,auth_id=17,map_id=5)
    k.update(changes);return events.records(text,**k)

class ObserverTests(unittest.TestCase):
    def test_ready_is_bound_to_actual_kings_map_and_immediate_timestamp(self):
        result=parse(line()+line(2,'position',x=20,y=-20,z=40))
        self.assertEqual(events.latest_ready(result)['map_id'],5)
        self.assertEqual(events.positions_after_ready(result)[0]['position'],[20,-20,40])
        for change in ({'pid':45},{'tid':56},{'map_id':1},{'db_id':2},{'auth_id':18},
            {'sequence':2},{'session':'a'*32},{'port':0},{'utc_ms':START+101001}):
            with self.subTest(change=change),self.assertRaises(events.base.DiagnosticError):parse(line(**change))
    def test_station_request_departure_require_matching_sequence_target(self):
        request=line(kind='station_request',map_id=1,request=1,target=5)
        departure=line(2,'station_departure',map_id=1,request=1,target=5)
        result=parse(request+departure,map_id=1)
        self.assertEqual(events.reply(result[0]),f'COH_MONORAIL_REPLY_V1 session={SESSION} pid=44 request=1 target=5 ready=1\n')
        for bad in (departure,request+departure.replace('request=1','request=2'),request.replace('target=5','target=1')):
            with self.assertRaises(events.base.DiagnosticError):parse(bad,map_id=1)
    def test_split_lines_scanned_once_without_decoding_large_console(self):
        output=bytearray(b'ordinary binary console\xff\n'*100000);owned={'process':SimpleNamespace(output=output)}
        self.assertEqual(events.console_events(owned),'\n')
        raw=line().encode();output.extend(raw[:17]);self.assertEqual(events.console_events(owned),'\n')
        output.extend(raw[17:]);self.assertEqual(events.console_events(owned),line())
        self.assertEqual(events.console_events(owned),line())
        del output[:10]
        with self.assertRaises(events.base.DiagnosticError):events.console_events(owned)
    def test_new_source_preserves_original_event_contract_and_only_mapserver(self):
        receipt=source.expected_receipt()
        self.assertEqual(receipt['contract'],contract.CONTRACT)
        self.assertEqual(receipt['build_targets'],['MapServer'])
        self.assertEqual(receipt['events_build_input']['events_contract']['identity']['map_id'],1)
        self.assertTrue(all(n.startswith('MapServer/') for n in receipt['patched_sha256']))

@unittest.skipUnless(os.name=='nt','genuine Win32 transport fixture')
class WindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cl'):raise RuntimeError('x86 MSVC required')
        cls.temp=tempfile.TemporaryDirectory(prefix='coh-monorail-native-');cls.directory=Path(cls.temp.name)
        cls.binary=cls.directory/'monorail.exe';overlay=ROOT/'database/monorail/overlay/MapServer/src/svr'
        subprocess.run(['cl','/nologo','/W4','/WX','/O2','/MT','/D_CRT_SECURE_NO_WARNINGS',f'/I{overlay}',
            str(overlay/'wine_monorail.c'),str(ROOT/'database/monorail/tests/monorail_contract.c'),
            f'/Fe:{cls.binary}'],cwd=cls.directory,check=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def start(self,token=SESSION):
        env=os.environ.copy();env.pop(events.ENVIRONMENT,None);env.pop(events.REPLY_ENVIRONMENT,None)
        reply=self.directory/('reply-'+str(time.time_ns())+'.txt')
        if token is not None:env[events.ENVIRONMENT]=token;env[events.REPLY_ENVIRONMENT]=str(reply)
        p=subprocess.Popen([str(self.binary)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        p.lines=queue.Queue()
        def read():
            for row in p.stdout:
                if row.strip():p.lines.put(row.strip())
        p.reader=threading.Thread(target=read,daemon=True);p.reader.start();self.addCleanup(self.close,p)
        return p,reply,self.receive(p).split()
    def close(self,p):
        if p.poll() is None:p.terminate()
        p.wait(timeout=10);p.reader.join(timeout=10)
        for s in (p.stdin,p.stdout,p.stderr):s.close()
    def receive(self,p):
        try:return p.lines.get(timeout=5)
        except queue.Empty:raise AssertionError('Native station event was not immediately flushed')
    def send(self,p,cmd):p.stdin.write(cmd+'\n');p.stdin.flush();return self.receive(p)
    def test_exact_reply_only_releases_pending_stock_station_request(self):
        p,path,status=self.start();self.assertEqual(status[1],'1')
        request=self.send(p,'request');self.assertIn('kind=station_request',request);self.assertEqual(self.receive(p),'REQUEST 1')
        self.assertEqual(self.send(p,'request'),'REQUEST 0')
        self.assertEqual(self.send(p,'poll'),'POLL 0')
        correct=f'COH_MONORAIL_REPLY_V1 session={SESSION} pid={status[2]} request=1 target=5 ready=1\n'
        for bad in (correct.replace('target=5','target=1'),correct.replace('request=1','request=2'),correct+'x',correct.replace(SESSION,'a'*32)):
            path.write_bytes(bad.encode());time.sleep(.27);self.assertEqual(self.send(p,'poll'),'POLL 0')
        path.write_bytes(correct.encode());time.sleep(.27);departure=self.send(p,'poll');self.assertIn('kind=station_departure',departure)
        self.assertEqual(self.receive(p),'POLL 1');self.assertEqual(self.send(p,'poll'),'POLL 0')
    def test_non_atlas_ready_and_position_flush_with_foreign_identity_filtered(self):
        p,path,status=self.start();self.assertIn('map_id=5',self.send(p,'ready5'));self.assertEqual(self.receive(p),'READY')
        self.assertIn('kind=position',self.send(p,'position5'));self.assertEqual(self.receive(p),'POSITION')
        self.assertEqual(self.send(p,'foreign'),'FILTERED');self.assertEqual(self.send(p,'reinit'),'REINIT -1')
    def test_disabled_and_bad_tokens_never_emit_request(self):
        for token,expected in ((None,'0'),('bad','-1'),('F'*32,'-1')):
            p,path,status=self.start(token);self.assertEqual(status[1],expected)
            self.assertEqual(self.send(p,'request'),'REQUEST 0')

if __name__=='__main__':
    if '--require-windows' in sys.argv:
        sys.argv.remove('--require-windows')
        if os.name!='nt' or not shutil.which('cl'):raise SystemExit('real initialized x86 MSVC required')
    unittest.main()
