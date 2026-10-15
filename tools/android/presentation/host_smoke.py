#!/usr/bin/env python3
"""Qualify exact APK guest frames through a host Unix RFB connection outside PRoot.

This proves the guest transport and pattern only. Android rendering, hardware
acceleration and game rendering remain explicitly unvalidated by this host job.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


assets_tool = load('presentation_assets_host', Path(__file__).with_name('prepare_assets.py'))
apk_tool = load('presentation_apk_host', Path(__file__).with_name('build_apk.py'))
base_tool = load('presentation_runtime_fetch', ROOT/'tools/android/prepare_assets.py')
require, digest = assets_tool.require, assets_tool.digest
WIDTH, HEIGHT = 800, 600


def extract_apk_assets(apk, output, build_report, repository_commit):
    require(not output.exists() and not output.is_symlink(), 'Fresh APK extraction destination required')
    report = assets_tool.read_json(build_report)
    require(report.get('repository_commit') == repository_commit and report.get('application_id') == apk_tool.APP_ID
            and report.get('version_name') == apk_tool.VERSION_NAME and report.get('signature_verified') is True
            and report.get('payload_bytes_verified') is True
            and {'bytes': report.get('bytes'), 'sha256': report.get('sha256')} == apk_tool.file_pin(apk),
            'Exact APK build receipt differs')
    sources = report.get('java_sources', {})
    with __import__('tempfile').TemporaryDirectory() as temporary:
        expected_sources = apk_tool.java_sources(ROOT/'android/presentation/src/main', Path(temporary))
    require(set(sources) == {p.relative_to(ROOT).as_posix() for p in expected_sources}, 'APK Java source inventory differs')
    require(all(apk_tool.file_pin(ROOT/name) == pin for name, pin in sources.items()), 'APK Java source differs from checkout')
    apk_tool.verify_packaged_payloads(apk, report['payloads'])
    with zipfile.ZipFile(apk) as archive:
        manifest_entry = archive.getinfo('assets/runtime/runtime-manifest.json')
        require(0 < manifest_entry.file_size <= 8*1024*1024, 'Oversized runtime manifest')
        manifest = json.loads(archive.read(manifest_entry))
        files = manifest.get('files', {})
        require(isinstance(files, dict) and 12 <= len(files) <= 40, 'Invalid APK runtime inventory')
        require(all(isinstance(name, str) and assets_tool.NAME.fullmatch(name) for name in files), 'Unsafe runtime path')
        expected = {'assets/runtime/'+name for name in (*files, 'runtime-manifest.json')}
        require({name for name in archive.namelist() if name.startswith('assets/')} == expected, 'Unexpected APK assets')
        entries, total = [], 0
        for name in sorted(expected):
            entry = archive.getinfo(name); mode = entry.external_attr >> 16
            require(not entry.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG) and not entry.flag_bits & 1
                    and 0 < entry.file_size <= assets_tool.MAX_FILE_BYTES, 'Unsafe APK entry')
            total += entry.file_size
            require(total <= 512*1024*1024, 'APK asset budget exceeded')
            entries.append(entry)
        output.mkdir(parents=True)
        for entry in entries:
            target = output/entry.filename.removeprefix('assets/runtime/')
            with archive.open(entry) as source, target.open('xb') as destination:
                shutil.copyfileobj(source, destination, 1024*1024)
    assets_tool.verify_device_assets(output, repository_commit=repository_commit)
    return manifest


def recv_exact(connection, size):
    require(0 <= size <= WIDTH*HEIGHT*4, 'RFB read exceeds bound')
    result = bytearray()
    while len(result) < size:
        block = connection.recv(size-len(result))
        if not block: raise EOFError('RFB peer closed')
        result.extend(block)
    return bytes(result)


def rfb_handshake(connection):
    banner = recv_exact(connection, 12)
    require(banner in (b'RFB 003.003\n', b'RFB 003.007\n', b'RFB 003.008\n'), 'Unsupported RFB protocol')
    connection.sendall(banner)
    if banner == b'RFB 003.003\n':
        require(struct.unpack('!I', recv_exact(connection, 4))[0] == 1, 'Expected private RFB None security')
    else:
        count = recv_exact(connection, 1)[0]
        require(0 < count <= 32, 'Invalid RFB security list')
        require(1 in recv_exact(connection, count), 'Private RFB None security unavailable')
        connection.sendall(b'\x01')
        if banner == b'RFB 003.008\n':
            require(recv_exact(connection, 4) == b'\0'*4, 'RFB security failed')
    connection.sendall(b'\x01')
    init = recv_exact(connection, 24)
    width, height = struct.unpack_from('!HH', init)
    require((width, height) == (WIDTH, HEIGHT), 'Unexpected RFB framebuffer geometry')
    name_size = struct.unpack_from('!I', init, 20)[0]
    require(name_size <= 4096, 'Oversized RFB desktop name')
    name = recv_exact(connection, name_size).decode('utf-8', 'replace')
    pixel_format = struct.pack('!BBBBHHHBBBxxx', 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
    connection.sendall(b'\x00\0\0\0'+pixel_format)
    connection.sendall(struct.pack('!BBHi', 2, 0, 1, 0))
    return name


def sample_rgb(pixels, x, y):
    offset = (y*WIDTH+x)*4
    return tuple(pixels[offset+i] for i in (2, 1, 0))


def bit(pixel):
    if all(channel < 30 for channel in pixel): return 0
    if all(channel > 225 for channel in pixel): return 1
    raise ValueError('Pattern bit pixel not black or white')


def decode_pattern(pixels, session):
    try:
        decoded = 0
        for index in range(128): decoded = (decoded << 1) | bit(sample_rgb(pixels, 6*index+3, 12))
        if f'{decoded:032x}' != session: return None
        frame = 0
        for index in range(16):
            value = bit(sample_rgb(pixels, 24*index+12, 44))
            if bit(sample_rgb(pixels, 24*index+396, 44)) != 1-value: return None
            frame = (frame << 1) | value
        if not 1 <= frame <= 240: return None
        even = ((255,0,0),(0,255,0),(0,0,255),(255,255,255))
        colors = tuple(reversed(even)) if frame % 2 else even
        for x, expected in zip((100,300,500,700), colors):
            if any(abs(a-b) > 20 for a,b in zip(sample_rgb(pixels,x,300), expected)): return None
        return frame
    except ValueError:
        return None


def observe_rfb(connection, session, process, deadline):
    desktop = rfb_handshake(connection)
    pixels = bytearray(WIDTH*HEIGHT*4)
    frames, updates = [], 0
    terminal_transport = None
    while process.poll() is None and time.monotonic() < deadline:
        try:
            connection.sendall(struct.pack('!BBHHHH', 3, 0, 0, 0, WIDTH, HEIGHT))
            message_type = recv_exact(connection, 1)[0]
            if message_type == 2: continue  # Bell
            if message_type == 3:
                header = recv_exact(connection, 7)
                length = struct.unpack_from('!I', header, 3)[0]
                require(length <= 65536, 'Oversized server cut text')
                recv_exact(connection, length); continue
            require(message_type == 0, 'Unexpected RFB message')
            header = recv_exact(connection, 3)
            rectangles = struct.unpack_from('!H', header, 1)[0]
            require(0 < rectangles <= 4096, 'Invalid RFB rectangle count')
            for _ in range(rectangles):
                x, y, width, height, encoding = struct.unpack('!HHHHi', recv_exact(connection, 12))
                require(encoding == 0 and width > 0 and height > 0 and x+width <= WIDTH and y+height <= HEIGHT,
                        'Invalid or unsupported RFB rectangle')
                raw = recv_exact(connection, width*height*4)
                for row in range(height):
                    start = ((y+row)*WIDTH+x)*4
                    pixels[start:start+width*4] = raw[row*width*4:(row+1)*width*4]
            updates += 1
            frame = decode_pattern(pixels, session)
            if frame is not None and frame not in frames: frames.append(frame)
            # Cap the observer rate to reduce transfer load; this is not game FPS.
            time.sleep(0.1)
        except (EOFError, BrokenPipeError, ConnectionResetError) as closure:
            # Xvnc closes during normal owned cleanup. Preserve complete frames
            # already observed; a short/failed producer still cannot pass the
            # independent frame threshold and complete guest/process gates below.
            terminal_transport = type(closure).__name__
            break
    require(len(frames) >= 6 and max(frames)-min(frames) >= 5
            and any(frame % 2 for frame in frames) and any(not frame % 2 for frame in frames),
            'External RFB observer did not prove changing session-bound frames')
    return {'scope': 'host_external_unix_rfb_observer', 'desktop': desktop, 'session_id': session,
            'updates': updates, 'distinct_native_frames': frames, 'native_pattern_verified': True,
            'terminal_transport': terminal_transport,
            'connected_outside_proot': True, 'android_surface_validated': False,
            'game_rendering_validated': False, 'hardware_acceleration_validated': False}


def make_command(work, assets, proot, session):
    lock = json.loads((assets/'runtime-lock.json').read_text())
    base = base_tool.fetch(lock['base'], ROOT/'out/android/cache/base.tar.gz')
    wine = base_tool.fetch(lock['wine'], ROOT/'out/android/cache/wine.tar.gz')
    root, win, pg = work/'rootfs', work/'wine', work/'pg'
    subprocess.run([sys.executable, str(ROOT/'tools/android/test_archive.py'), '--extract', str(base), str(root),
                    '--extract', str(wine), str(win), '--extract', str(assets/'postgresql-runtime.tar.gz'), str(pg)], check=True)
    require(digest(win/'lsb-fex.json') == lock['wine']['manifest_sha256'], 'Wine receipt differs')
    for name in ('state','tmp','socket'): (work/name).mkdir(mode=0o700)
    (work/'passwd').write_text('root:x:0:0:root:/root:/bin/sh\ncoh:x:1000:1000:COH:/state:/bin/sh\nnobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n')
    (work/'group').write_text('root:x:0:\ncoh:x:1000:\nnogroup:x:65534:\n')
    for name in ('opt/coh','opt/coh/pgsql','opt/wine','state','tmp','presentation-socket'):
        (root/name).mkdir(parents=True, exist_ok=True)
    for name in ('proot','proot-loader'): (proot/name).chmod(0o755)
    command = [str(proot/'proot'),'--link2symlink','--kill-on-exit','--sysvipc','-i','1000:1000','-r',str(root)]
    for source, destination in (('/dev','/dev'),('/proc','/proc'),('/sys','/sys'),(work/'state','/state'),
            (work/'tmp','/tmp'),(work/'socket','/presentation-socket'),(assets,'/opt/coh'),
            (pg/'opt/coh/pgsql','/opt/coh/pgsql'),(win,'/opt/wine'),(work/'passwd','/etc/passwd'),(work/'group','/etc/group')):
        command += ['-b',str(Path(source).resolve())+':'+destination]
    command += ['-w','/state','/usr/bin/env','-i','HOME=/state','USER=coh','LOGNAME=coh',
                'PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin','LANG=C.UTF-8','TZ=UTC','TMPDIR=/tmp','PYTHONUNBUFFERED=1',
                '/usr/bin/python3','/opt/coh/presentation_diagnostic.py','--state','/state','--assets','/opt/coh',
                '--pg-bin','/opt/coh/pgsql/bin','--wine','/opt/wine/bin/wine','--wineserver','/opt/wine/bin/wineserver',
                '--execution-platform','host','--session-id',session,'--duration-seconds','60','--socket-dir','/presentation-socket']
    env = os.environ.copy()
    env.update(PROOT_LOADER=str(proot/'proot-loader'), PROOT_TMP_DIR=str((work/'tmp').resolve()), PROOT_NO_SECCOMP='1')
    return command, env


def validate_report(report, session, manifest=None):
    require(report.get('passed') is True and report.get('failures') == [] and report.get('scope') == 'visible_presentation_guest'
            and report.get('status') == 'passed', 'Guest presentation report failed')
    require(report.get('session_id') == session, 'Guest session receipt differs')
    require(report.get('android_execution_validated') is False and report.get('gameplay_validated') is False,
            'Host report cannot claim Android execution/gameplay')
    cleanup = report.get('cleanup', {})
    require(cleanup.get('wine_prefix_stopped') is True and cleanup.get('owned_processes_reaped') is True
            and report.get('cleanup_complete') is True
            and report.get('wine_process_cleanup', {}).get('complete') is True
            and report.get('wine_process_cleanup', {}).get('remaining') == 0
            and report.get('wine_process_cleanup', {}).get('inspection_failures') == 0,
            'Guest cleanup incomplete')
    producer = report.get('producer', {})
    require(producer.get('status') == 'passed' and producer.get('session_id') == session
            and producer.get('width') == WIDTH and producer.get('height') == HEIGHT
            and producer.get('duration_seconds') == 60 and producer.get('frames') == 120
            and producer.get('pointer_bits') == 32 and producer.get('frame_contract') == 1
            and producer.get('readback_verified') is True
            and producer.get('android_surface_validated') is False and producer.get('game_validated') is False,
            'Guest native producer proof differs')

    stages = report.get('stages', [])
    require([stage.get('stage') for stage in stages] == ['presentation_inputs', 'presentation_display',
            'wine_initialization', 'win32_runtime_dll', 'visible_presentation_frames']
            and all(stage.get('status') == 'passed' for stage in stages), 'Guest presentation stages incomplete')
    display = stages[1]
    require(display.get('rfb_tcp') is False and display.get('x_tcp') is False
            and display.get('socket_path') == '/presentation-socket/view.sock'
            and display.get('socket_mode') == '0600' and report.get('presentation_socket_removed') is True,
            'Private presentation socket evidence incomplete')
    children = report.get('processes', [])
    execution = report.get('cleanup_execution', {})
    require(isinstance(children, list) and len(children) >= 4
            and execution.get('diagnostic_initialized') is True and execution.get('wine_started') is True
            and type(execution.get('owned_child_count')) is int and execution['owned_child_count'] == len(children)
            and all(type(child.get('exit_code')) is int and child.get('input_closed') is True
                    and child.get('output_capture_closed') is True for child in children),
            'Guest owned child closure evidence incomplete')
    for label in ('runtime-probe', 'presentation-probe'):
        matching = [child for child in children if child.get('label') == label]
        require(len(matching) == 1 and matching[0]['exit_code'] == 0, 'Required native child did not exit successfully')
    require(report.get('frames_emitted') == 120 and report.get('postgres_started') is False,
            'Unexpected producer count or server execution')
    if manifest is not None:
        expected = {name: manifest['files'][name]['sha256'] for name in assets_tool.PROBE_FILES}
        require(report.get('asset_sha256') == expected, 'Guest asset hashes differ from the exact APK')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('apk','build-report','proot','work','evidence'): parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True, help='Exact APK producer source commit')
    parser.add_argument('--verifier-commit', help='Current host verifier source commit when qualifying an existing APK')
    args = parser.parse_args()
    verifier_commit = apk_tool.source_commit(args.verifier_commit)
    require(platform.machine().lower() in ('aarch64','arm64'), 'Native ARM64 Linux is required')
    require(not args.work.exists() and not args.work.is_symlink(), 'Use a fresh owned smoke directory')
    args.work = args.work.resolve(); args.proot = args.proot.resolve()
    args.work.mkdir(parents=True); args.evidence.mkdir(parents=True, exist_ok=True)
    assets = args.work/'apk-assets'
    manifest = extract_apk_assets(args.apk, assets, args.build_report, args.repository_commit)
    session = secrets.token_hex(16)
    command, env = make_command(args.work, assets, args.proot, session)
    start = time.monotonic(); deadline = start+780
    observer = None; failure = None; process = None
    with (args.evidence/'host-presentation.log').open('w') as log:
        try:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            socket_path = args.work/'socket'/'view.sock'
            # Socket appears before Wine prefix boot. The external reader remains
            # attached throughout initialization and rejects unrelated frames.
            while not socket_path.exists():
                require(process.poll() is None and time.monotonic() < deadline, 'Guest exited or timed out before socket')
                time.sleep(0.1)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(90)
                connection.connect(str(socket_path))
                observer = observe_rfb(connection, session, process, deadline)
            code = process.wait(timeout=max(1,deadline-time.monotonic()))
            require(code == 0, 'Guest process exit status differs')
            report = json.loads((args.work/'state'/'latest-report.json').read_text())
            validate_report(report, session, manifest)
            require(not socket_path.exists(), 'Guest private RFB socket survived cleanup')
        except Exception as error:
            failure = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            if process is not None and process.poll() is None:
                (args.work/'state'/'stop-request').write_text('stop\n')
                try: process.wait(timeout=35)
                except subprocess.TimeoutExpired:
                    process.send_signal(signal.SIGQUIT)
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
            for name in ('latest-report.json','report.zip'):
                source = args.work/'state'/name
                if source.is_file(): shutil.copyfile(source, args.evidence/name)
            result = {'format':1,'status':'failed' if failure else 'passed','scope':'exact_apk_native_arm64_guest_external_rfb',
                      'repository_commit':args.repository_commit, 'apk_repository_commit':args.repository_commit,
                      'verifier_repository_commit':verifier_commit,'host_verifier_sha256':digest(Path(__file__)),
                      'apk_sha256':digest(args.apk),
                      'runtime_manifest_sha256':digest(assets/'runtime-manifest.json'),
                      'accepted_runtime_run_id':manifest['accepted_base_runtime']['run_id'],
                      'session_id':session,'external_observer':observer,'failure':failure,
                      'elapsed_seconds':round(time.monotonic()-start,3),
                      'android_execution_validated':False,'android_surface_validated':False,
                      'game_rendering_validated':False,'hardware_acceleration_validated':False,'gameplay_validated':False}
            (args.evidence/'host-presentation-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
