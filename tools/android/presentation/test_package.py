"""Presentation package boundary and independently encoded RFB regression tests."""
import importlib.util
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
import warnings
import zipfile
from unittest import mock

HERE = Path(__file__).resolve().parent

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE/filename)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module); return module

package = load('presentation_test_assets', 'prepare_assets.py')
builder = load('presentation_test_builder', 'build_apk.py')
host = load('presentation_test_host', 'host_smoke.py')


class PackageTests(unittest.TestCase):
    def test_manifest_is_separate_private_client_and_sdk35(self):
        builder.verify_source_manifest(builder.ROOT/'android/presentation/src/main/AndroidManifest.xml')
        self.assertNotIn('cohatlastest', builder.APP_ID)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'manifest.xml'
            original = (builder.ROOT/'android/presentation/src/main/AndroidManifest.xml').read_text()
            for bad in (original.replace('cohpresentation','cohatlastest'),
                        original.replace('android:exported="false"','android:exported="true"'),
                        original.replace('android:allowBackup="false"','android:allowBackup="true"'),
                        original.replace('android:targetSdkVersion="35"','android:targetSdkVersion="34"'),
                        original.replace('FOREGROUND_SERVICE_DATA_SYNC','MANAGE_EXTERNAL_STORAGE')):
                target.write_text(bad)
                with self.assertRaises(ValueError): builder.verify_source_manifest(target)

    def test_original_app_components_excluded_from_java(self):
        with tempfile.TemporaryDirectory() as folder:
            sources = builder.java_sources(builder.ROOT/'android/presentation/src/main', Path(folder))
        self.assertIn('DiagnosticRuntime.java', {p.name for p in sources})
        self.assertNotIn('MainActivity.java', {p.name for p in sources})
        self.assertNotIn('DiagnosticService.java', {p.name for p in sources})
        self.assertIn('PresentationActivity.java', {p.name for p in sources})
        self.assertIn('PresentationService.java', {p.name for p in sources})

    def test_exact_inventory_rejects_links_extras_and_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); payload = root/'probe.exe'; payload.write_bytes(b'payload')
            inventory = {'probe.exe': package.file_pin(payload)}
            package.verify_inventory(root, inventory)
            payload.write_bytes(b'changed')
            with self.assertRaises(ValueError): package.verify_inventory(root, inventory)
            payload.write_bytes(b'payload'); (root/'extra').write_text('extra')
            with self.assertRaises(ValueError): package.verify_inventory(root, inventory)
            (root/'extra').unlink(); payload.unlink(); payload.symlink_to(__file__)
            with self.assertRaises(ValueError): package.verify_inventory(root, inventory)

    def test_exact_apk_payloads_reject_extra_server_and_duplicate_members(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); names = ['assets/runtime/runtime-manifest.json',
                'assets/runtime/presentation-probe.exe', *sorted(builder.NATIVE_MEMBERS)]
            files = []
            for index, name in enumerate(names):
                path = root/str(index); path.write_bytes(('test '+name).encode()); files.append((path,name))
            pins = {name:builder.file_pin(path) for path,name in files}
            apk = root/'test.apk'
            with zipfile.ZipFile(apk,'w') as archive:
                archive.writestr('classes.dex', b'dexfixture'); builder.append_payloads(archive,files)
            builder.verify_packaged_payloads(apk,pins)
            with zipfile.ZipFile(apk,'a') as archive: archive.writestr('assets/runtime/MapServer.exe',b'unexpected')
            with self.assertRaisesRegex(ValueError,'payload set'): builder.verify_packaged_payloads(apk,pins)
            with zipfile.ZipFile(apk,'a') as archive, warnings.catch_warnings():
                warnings.simplefilter('ignore'); archive.writestr('classes.dex',b'duplicate')
            with self.assertRaisesRegex(ValueError,'duplicate'): builder.verify_packaged_payloads(apk,pins)

    def test_donor_identity_and_guest_modules_are_explicit(self):
        self.assertEqual(36364550345,package.RUNTIME_RUN_ID)
        self.assertEqual('fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203',package.RUNTIME_MANIFEST_SHA256)
        self.assertIn('game_evidence.py',package.GUEST_SCRIPTS)
        self.assertNotIn('diagnostic.py',package.EXTRA_FILES)
        self.assertNotIn('game-package.tar.gz',package.EXTRA_FILES)
        self.assertFalse(package.bundle_contract()['game_assets_included'])


def encoded_frame(session, frame):
    """Fixture writer fills independent RGB scan regions from the documented pattern."""
    pixels = bytearray(800*600*4)
    def box(x,y,w,h,color):
        r,g,b = color; row = bytes((b,g,r,0))*w
        for line in range(y,y+h): pixels[(line*800+x)*4:(line*800+x+w)*4] = row
    for index, value in enumerate(f'{int(session,16):0128b}'):
        box(index*6,0,6,24,(255,255,255) if value=='1' else (0,0,0))
    for index, value in enumerate(f'{frame:016b}'):
        box(index*24,32,24,24,(255,255,255) if value=='1' else (0,0,0))
        box(384+index*24,32,24,24,(0,0,0) if value=='1' else (255,255,255))
    colors = ((255,0,0),(0,255,0),(0,0,255),(255,255,255))
    if frame % 2: colors = tuple(reversed(colors))
    for index,color in enumerate(colors): box(index*200,80,200,520,color)
    return pixels


class FrameTests(unittest.TestCase):
    SESSION = '0123456789abcdef0123456789abcdef'

    def test_native_pattern_rejects_stale_session_incoherent_frame_and_wrong_bars(self):
        frame = encoded_frame(self.SESSION,9)
        self.assertEqual(9,host.decode_pattern(frame,self.SESSION))
        self.assertIsNone(host.decode_pattern(frame,'f'*32))
        offset = (44*800+396)*4; frame[offset:offset+4] = b'\0'*4
        self.assertIsNone(host.decode_pattern(frame,self.SESSION))
        frame = encoded_frame(self.SESSION,9)
        offset = (300*800+100)*4; frame[offset:offset+4] = b'\0'*4
        self.assertIsNone(host.decode_pattern(frame,self.SESSION))

    def test_host_observer_decodes_fragmented_actual_rfb_stream(self):
        client, server = socket.socketpair(); self.addCleanup(client.close); self.addCleanup(server.close)
        client.settimeout(10); server.settimeout(10); errors=[]
        def producer():
            try:
                server.sendall(b'RFB 003.008\n'); self.assertEqual(host.recv_exact(server,12),b'RFB 003.008\n')
                server.sendall(b'\x01\x01'); self.assertEqual(host.recv_exact(server,1),b'\x01')
                server.sendall(b'\0'*4); host.recv_exact(server,1)
                init=struct.pack('!HH',800,600)+b'\0'*16+struct.pack('!I',4)+b'test'
                for chunk in (init[:5],init[5:]): server.sendall(chunk)
                self.assertEqual(host.recv_exact(server,20)[0],0)
                self.assertEqual(host.recv_exact(server,8)[0],2)
                for frame in range(1,7):
                    self.assertEqual(host.recv_exact(server,10)[0],3)
                    server.sendall(b'\0\0\0\x01'+struct.pack('!HHHHi',0,0,800,600,0)+encoded_frame(self.SESSION,frame))
                host.recv_exact(server,10); server.close()
            except Exception as exc: errors.append(exc)
        thread=threading.Thread(target=producer);thread.start()
        result=host.observe_rfb(client,self.SESSION,mock.Mock(poll=lambda:None),time.monotonic()+15)
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive()); self.assertEqual([],errors)
        self.assertEqual(list(range(1,7)),result['distinct_native_frames'])
        self.assertTrue(result['connected_outside_proot'])
        self.assertFalse(result['android_surface_validated'])

    def test_host_report_rejects_cleanup_failure_and_wrong_session(self):
        valid={'scope':'visible_presentation_guest','status':'passed','passed':True,'failures':[],
            'session_id':self.SESSION,'android_execution_validated':False,'gameplay_validated':False,
            'cleanup_complete':True,'cleanup':{'wine_prefix_stopped':True,'owned_processes_reaped':True},
            'wine_process_cleanup':{'complete':True,'remaining':0,'inspection_failures':0},
            'producer':{'status':'passed','session_id':self.SESSION,'width':800,'height':600,
                'duration_seconds':60,'frames':120,'pointer_bits':32,'frame_contract':1,
                'readback_verified':True,'android_surface_validated':False,'game_validated':False}}
        host.validate_report(valid,self.SESSION)
        with self.assertRaises(ValueError): host.validate_report(valid,'f'*32)
        valid['cleanup_complete']=False
        with self.assertRaisesRegex(ValueError,'cleanup'): host.validate_report(valid,self.SESSION)


if __name__ == '__main__': unittest.main()
