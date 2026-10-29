#!/usr/bin/env python3
"""Exercise app runtime files and private RFB transport without building an APK."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/android/dbserver'))
import host_dbserver_smoke as runtime

spec = importlib.util.spec_from_file_location('armport_rfb', ROOT / 'tools/android/client/host_smoke.py')
rfb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rfb)
require = runtime.require


def prepare(work, evidence, client, proot, link_source=None):
    require(platform.machine().lower() in ('aarch64', 'arm64'), 'ARM64 runner required')
    require(not work.exists(), 'Use a fresh runtime work directory')
    work.mkdir(mode=0o700)
    lock_path = ROOT / 'android/runtime-lock.json'
    lock = json.loads(lock_path.read_text())
    archives = {}
    for name in ('base', 'wine'):
        archives[name] = runtime.fetch(lock[name], ROOT / 'out/android/cache' / (name + '.tar.gz'))
    subprocess.run([sys.executable, str(ROOT / 'tools/android/test_archive.py'),
                    '--extract', str(archives['base']), str(work / 'rootfs'),
                    '--extract', str(archives['wine']), str(work / 'wine')], check=True)
    require(runtime.digest(work / 'wine/lsb-fex.json') == lock['wine']['manifest_sha256'],
            'Wine manifest differs from app runtime lock')
    for name in ('state', 'tmp', 'socket', 'assets', 'guest', 'probe'):
        (work / name).mkdir(mode=0o700)
    shutil.copyfile(lock_path, work / 'assets/runtime-lock.json')
    for source in (ROOT / 'android/guest').glob('*.py'):
        shutil.copyfile(source, work / 'guest' / source.name)
    shutil.copyfile(Path(__file__).with_name('runtime_guest.py'), work / 'probe/runtime_guest.py')
    shutil.copyfile(Path(__file__).with_name('client_stdio.py'), work / 'probe/client_stdio.py')
    (work / 'passwd').write_text('root:x:0:0:root:/root:/bin/sh\ncoh:x:1000:1000:COH:/state:/bin/sh\n')
    (work / 'group').write_text('root:x:0:\ncoh:x:1000:\n')
    runtime.prepare_guest_hosts(work, evidence, os.uname().nodename)
    bindings = {'state': '/state', 'tmp': '/tmp', 'socket': '/presentation-socket',
                'assets': '/opt/coh', 'guest': '/opt/coh-guest', 'probe': '/opt/armport',
                'wine': '/opt/wine', 'passwd': '/etc/passwd', 'group': '/etc/group',
                'hosts': '/etc/hosts'}
    # The packaged stage exposes data as links to its source tree (the same
    # case-merged view the app guest builds). Bind that source at its own path
    # so the links resolve unchanged inside PRoot.
    extra = [] if link_source is None else [str(link_source)]
    for destination in (*bindings.values(), '/opt/armport-client', *extra):
        path = work / 'rootfs' / destination.lstrip('/')
        path.parent.mkdir(parents=True, exist_ok=True)
        if not destination.startswith('/etc/'):
            path.mkdir(parents=True, exist_ok=True)
    command = [str(proot / 'proot'), '--link2symlink', '--kill-on-exit', '--sysvipc',
               '-i', '1000:1000', '-r', str(work / 'rootfs'), '-b', '/dev', '-b', '/proc', '-b', '/sys']
    for name, destination in bindings.items():
        command += ['-b', str(work / name) + ':' + destination]
    for source in extra:
        command += ['-b', source + ':' + source]
    command += ['-b', str(client) + ':/opt/armport-client', '-w', '/state', '/usr/bin/env', '-i',
                'HOME=/state', 'USER=coh', 'LOGNAME=coh', 'PATH=/usr/local/bin:/usr/bin:/bin',
                'LANG=C.UTF-8', 'TZ=UTC', 'TMPDIR=/tmp', 'PYTHONUNBUFFERED=1',
                'PYTHONDONTWRITEBYTECODE=1', '/usr/bin/python3', '/opt/armport/runtime_guest.py']
    return command, {'runtime_lock_sha256': runtime.digest(lock_path),
                     'base_sha256': lock['base']['sha256'], 'wine_sha256': lock['wine']['sha256'],
                     'wine_manifest_sha256': lock['wine']['manifest_sha256']}


def capture(process, work, evidence):
    deadline = time.monotonic() + 1400
    endpoint = work / 'socket/view.sock'
    while not endpoint.exists():
        require(process.poll() is None, 'Guest exited before RFB endpoint')
        require(time.monotonic() < deadline, 'RFB endpoint timed out')
        time.sleep(.5)
    frames = []
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(str(endpoint))
        desktop = rfb.client_rfb_handshake(connection)
        frame = rfb.ClientFramebuffer()
        while len(frames) < 3:
            require(process.poll() is None, 'Guest exited before frame capture')
            require(time.monotonic() < deadline, 'RFB login frame timed out')
            ready = (work / 'state/armport-app-ready.json').exists()
            connection.sendall(struct.pack('!BBHHHH', 3, 0, 0, 0, frame.width, frame.height))
            while True:
                kind = rfb.transport.recv_exact(connection, 1)[0]
                if kind == 2:
                    continue
                if kind == 3:
                    header = rfb.transport.recv_exact(connection, 7)
                    size = struct.unpack_from('!I', header, 3)[0]
                    require(size <= 4096, 'RFB cut text too large')
                    rfb.transport.recv_exact(connection, size)
                    continue
                require(kind == 0, 'Unexpected RFB message')
                changed, resized = frame.read_update(connection)
                break
            if ready and changed and not resized:
                colors = {bytes(frame.pixels[n:n+3]) for n in range(0, len(frame.pixels), 400)}
                require(len(colors) >= 32, 'Login framebuffer appears blank')
                path = evidence / ('login-rfb-' + str(len(frames)) + '.png')
                rfb.save_png(path, frame.pixels, frame.width, frame.height)
                frames.append({'path': path.name, 'sha256': runtime.digest(path),
                               'width': frame.width, 'height': frame.height,
                               'after_login_marker': True})
            time.sleep(1 if ready else 5)
    result = {'transport': 'private_unix_rfb', 'desktop': desktop, 'frames': frames}
    (work / 'state/armport-app-frame.json').write_text(json.dumps(result) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('client', 'proot', 'work', 'evidence'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--link-source', type=Path)
    args = parser.parse_args()
    client, proot, work, evidence = (getattr(args, n).resolve() for n in ('client', 'proot', 'work', 'evidence'))
    link_source = args.link_source.resolve() if args.link_source else None
    require(not evidence.exists(), 'Use a fresh evidence directory')
    evidence.mkdir(parents=True)
    report = {'scope': 'armport_app_runtime_boot', 'passed': False, 'm4_complete': False}
    report['artifact_runs'] = {name: os.environ.get(name) for name in ('CLIENT_RUN_ID', 'DATA_RUN_ID')}
    process = None
    try:
        command, report['runtime'] = prepare(work, evidence, client, proot, link_source)
        command, environment, expected = runtime.isolate_command(command, evidence=evidence, proot=proot, work=work)
        with (evidence / 'guest.log').open('wb') as log:
            process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
            report['rfb'] = capture(process, work, evidence)
            report['guest_exit'] = process.wait(timeout=90)
        guest = json.loads((work / 'state/armport-app-report.json').read_text())
        report['guest'] = guest
        isolation = json.loads((evidence / 'network-isolation.json').read_text())
        runtime.validate_network_receipt(isolation, expected)
        require(report['guest_exit'] == 0 and guest.get('passed') is True, 'Guest qualification failed')
        report['passed'] = True
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        if process is not None and process.poll() is None:
            report['stop'] = runtime.stop_guest(process, work / 'state')
        for source, destination in ((work / 'state/armport-app-report.json', 'guest-report.json'),
                                    (client / 'armport_stdio.txt', 'armport_stdio.txt')):
            if source.is_file():
                with source.open('rb') as stream:
                    stream.seek(max(0, source.stat().st_size - 8 * 1024 * 1024))
                    (evidence / destination).write_bytes(stream.read(8 * 1024 * 1024))
        (evidence / 'host-report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({key: report.get(key) for key in ('passed', 'm4_complete', 'guest_exit', 'error')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
