#!/usr/bin/env python3
"""ARM64 client boot on the Android app's PRoot/Xtigervnc display path.

This probe reuses the app's Wine initialization, display and cleanup code.
It qualifies startup/transport only, not Atlas, Android surface delivery or M4.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import signal
import stat
import struct
import sys
import time

sys.path.insert(0, '/opt/coh-guest')
import presentation_diagnostic as presentation
from client_startup_diagnostic import XObserver, parse_launch, console_identity

base, require = presentation.base, presentation.require


def arm64_pe(path):
    with path.open('rb') as stream:
        dos = stream.read(64)
        require(len(dos) == 64 and dos[:2] == b'MZ', 'Missing DOS header: ' + path.name)
        offset = struct.unpack_from('<I', dos, 60)[0]
        require(64 <= offset <= 1024 * 1024, 'PE header offset')
        stream.seek(offset)
        header = stream.read(26)
    require(len(header) == 26 and header[:4] == b'PE\0\0'
            and struct.unpack_from('<H', header, 4)[0] == 0xaa64
            and struct.unpack_from('<H', header, 24)[0] == 0x20b,
            'Expected ARM64 PE32+: ' + path.name)


class ArmPortRuntime(presentation.PresentationDiagnostic):
    def initialize(self):
        self.ctx.stage('armport_runtime_inputs')
        require(platform.machine().lower() in ('aarch64', 'arm64'), 'ARM64 guest required')
        require(os.geteuid() == 1000, 'PRoot uid must be 1000')
        for binary in (self.args.wine, self.args.wineserver):
            base.arm64_elf(binary)
        require(self.args.socket_dir.is_dir() and not self.args.socket_dir.is_symlink()
                and stat.S_IMODE(self.args.socket_dir.stat().st_mode) == 0o700,
                'Private presentation socket directory required')
        require(not self.presentation_socket.exists(), 'Presentation endpoint already exists')
        executable = self.args.client / 'CityOfHeroes.exe'
        binaries = [executable, self.args.client / 'armport-launcher.exe',
                    *sorted(self.args.client.glob('*.dll'))]
        for binary in binaries:
            require(binary.is_file() and not binary.is_symlink(), 'Missing/linked client binary')
            arm64_pe(binary)
        self.ctx.report['client_binaries'] = {p.name: base.file_hash(p) for p in binaries}
        self.ctx.passed(machine=platform.machine(), pointer_bits=64, pe_machine='ARM64')

    def execute(self):
        self.initialize()
        self.start_wine()
        self.ctx.stage('armport_login_screen')
        environment = dict(self.wine_env, ARMPORT_LOOSE_DATA='1',
                           ARMPORT_STDIO_LOG='armport_stdio.txt', WINEDEBUG='err+all,fixme-all,+seh')
        command = ['/usr/bin/env', '-C', str(self.args.client), str(self.args.wine),
                   base.windows_path(self.args.client / 'armport-launcher.exe'), self.args.session_id,
                   base.windows_path(self.args.client / 'CityOfHeroes.exe'),
                   base.windows_path(self.args.client), '--character-manual']
        child = self.ctx.start('armport-client', command, env=environment)
        observer = XObserver(self.wine_env['DISPLAY'])
        stdio = self.args.client / 'armport_stdio.txt'
        deadline = time.monotonic() + self.args.startup_seconds
        try:
            while True:
                self.ctx.check()
                require(child.process.poll() is None, 'ARM64 client exited: ' + child.text()[-4096:])
                require(self.xserver.process.poll() is None, 'Display exited')
                require(time.monotonic() < deadline, 'ARM64 login screen startup timed out')
                text = ''
                if stdio.exists():
                    with stdio.open('rb') as stream:
                        stream.seek(max(0, stdio.stat().st_size - 1024 * 1024))
                        text = stream.read(1024 * 1024).decode('utf-8', 'replace')
                windows = observer.windows()
                visible = [w for w in windows if w['mapped'] and w['width'] >= 640
                           and w['height'] >= 480 and 'City of Heroes' in w['title']]
                require(not any(w['mapped'] and ('Fatal Error' in w['title'] or 'Assertion' in w['title'])
                                for w in windows), 'Client error dialog')
                launch = parse_launch(child.text(), self.args.session_id)
                console = console_identity(child.text(), launch)
                if visible and launch and console and re.search(r'ArmPort login: stage 0\b', text):
                    self.ctx.report.update(login_stage=0, client_windows=visible,
                                           client_launch=launch, client_console_observation=console)
                    base.private_write(self.args.state / 'armport-app-ready.json',
                                       json.dumps({'login_stage': 0, 'windows': visible}) + '\n')
                    break
                time.sleep(1)
            # The host must collect a fresh RFB frame after the ready marker.
            deadline = time.monotonic() + 90
            while not (self.args.state / 'armport-app-frame.json').exists():
                self.ctx.check()
                require(child.process.poll() is None, 'Client exited before external frame')
                require(time.monotonic() < deadline, 'External RFB frame was not collected')
                time.sleep(.2)
            self.ctx.report['client_alive_after_frame'] = child.process.poll() is None
            require(self.ctx.report['client_alive_after_frame'], 'Client exited after external frame')
            self.ctx.passed(login_stage=0, client_alive=True, rfb_frame_acknowledged=True)
        finally:
            observer.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in [('state', '/state'), ('assets', '/opt/coh'),
                          ('client', '/opt/armport-client'), ('pg-bin', '/unused'),
                          ('wine', '/opt/wine/bin/wine'), ('wineserver', '/opt/wine/bin/wineserver'),
                          ('xserver', '/usr/bin/Xtigervnc'), ('socket-dir', '/presentation-socket')]:
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--startup-seconds', type=int, default=600)
    parser.add_argument('--session-id', default='a' * 32)
    args = parser.parse_args()
    require(30 <= args.startup_seconds <= 900, 'Startup budget out of bounds')
    require(re.fullmatch('[0-9a-f]{32}', args.session_id) is not None, 'Invalid session')
    os.umask(0o077)
    context = base.Context(args.state, 1500)
    context.report.update(scope='armport_app_runtime_boot', m4_complete=False,
                          android_surface_validated=False, gameplay_validated=False)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: setattr(context, 'cancel_requested', True))
    diagnostic = None
    try:
        diagnostic = ArmPortRuntime(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        if diagnostic:
            try:
                context.report['failures'].extend(diagnostic.cleanup())
            except Exception as exc:
                context.report['failures'].append('Cleanup: ' + str(exc))
            context.report['cleanup'] = diagnostic.cleanup_status
        context.report['passed'] = (context.report['status'] == 'passed'
            and not context.report['failures'] and diagnostic is not None
            and all(diagnostic.cleanup_status.values()))
        if not context.report['passed']:
            context.report['status'] = 'failed'
        context.report['finished_utc'] = base.utc()
        base.private_write(args.state / 'armport-app-report.json', json.dumps(context.report, indent=2) + '\n')
        context.event('result', passed=context.report['passed'], failures=context.report['failures'])
    return 0 if context.report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
