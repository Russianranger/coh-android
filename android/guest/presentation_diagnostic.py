#!/usr/bin/env python3
"""Bounded visible Win32 presentation producer, with no database/game services.

The guest proves producer frames and strict process cleanup. Only the Android
wrapper can additionally prove that those frames reached its native surface.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import signal
import stat
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic as base
from game_device_diagnostic import DeviceWineProcessOwner

require = base.require
MARKER = 'COH_PRESENTATION_PROBE_V1 '
FRAME_MARKER = 'COH_PRESENTATION_FRAME_V1 '
SCOPE = 'visible_presentation_guest'
REQUIRED = {'runtime-lock.json', 'runtime-probe.exe', 'probe.dll', 'presentation-probe.exe',
    'diagnostic.py', 'presentation_diagnostic.py', 'dbserver_diagnostic.py', 'game_diagnostic.py',
    'game_device_diagnostic.py', 'game_evidence.py', 'game_hang_evidence.py', 'game_map_progress.py'}


def validate_args(args):
    require(re.fullmatch(r'[0-9a-f]{32}', args.session_id) is not None, 'Session must be 32 lowercase hex characters')
    require(type(args.duration_seconds) is int and 30 <= args.duration_seconds <= 120,
            'Presentation duration must be 30 to 120 seconds')
    require(180 <= args.timeout_seconds <= 1200, 'Timeout must be 180 to 1200 seconds')
    for path in (args.state, args.assets, args.socket_dir):
        require(path.is_absolute() and '..' not in path.parts and path != Path('/') and not path.is_symlink(),
                'Expected absolute unlinked private paths')


def verify_assets(assets):
    manifest_path = assets / 'presentation-manifest.json'
    require(manifest_path.is_file() and not manifest_path.is_symlink() and manifest_path.stat().st_size <= 65536,
            'Missing or invalid presentation manifest')
    manifest = json.loads(manifest_path.read_text())
    require(type(manifest.get('format')) is int and manifest['format'] == 1
            and manifest.get('scope') == SCOPE, 'Presentation manifest scope differs')
    files = manifest.get('files')
    require(isinstance(files, dict) and REQUIRED <= set(files) and len(files) <= 64,
            'Presentation payload inventory differs')
    hashes = {}
    for name, record in files.items():
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name)
                and name not in ('.', '..') and isinstance(record, dict), 'Unsafe presentation inventory entry')
        path = assets / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 64*1024*1024,
                'Missing, linked or oversized payload: ' + name)
        digest = record.get('sha256')
        require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest), 'Missing payload digest')
        require(base.file_hash(path) == digest, 'Presentation payload digest differs: ' + name)
        if 'bytes' in record:
            require(type(record['bytes']) is int and path.stat().st_size == record['bytes'], 'Payload size differs')
        if 'size' in record:
            require(type(record['size']) is int and path.stat().st_size == record['size'], 'Payload size differs')
        hashes[name] = digest
    for name in ('runtime-probe.exe', 'probe.dll', 'presentation-probe.exe'):
        base.verify_pe32(assets / name)
    return hashes


def validate_producer(output, session, duration):
    lines = output.splitlines()
    results = [line[len(MARKER):] for line in lines if line.startswith(MARKER)]
    require(len(results) == 1, 'Expected exactly one presentation producer result')
    value = json.loads(results[0])
    require(isinstance(value, dict) and type(value.get('format')) is int
            and value['format'] == 1 and value.get('status') == 'passed'
            and value.get('failure_stage') == '' and value.get('session_id') == session,
            'Presentation producer failed or belongs to another session')
    for field, expected in {'width': 800, 'height': 600, 'frames': duration*2,
            'duration_seconds': duration, 'pointer_bits': 32, 'frame_contract': 1}.items():
        require(type(value.get(field)) is int and value[field] == expected, 'Producer field differs: ' + field)
    require(value.get('readback_verified') is True and value.get('android_surface_validated') is False
            and value.get('game_validated') is False, 'Producer exceeded its evidence scope')
    require(type(value.get('software_rendering')) is bool, 'Producer renderer classification missing')
    for field in ('renderer', 'vendor', 'gl_version'):
        require(isinstance(value.get(field), str) and 0 < len(value[field]) <= 512,
                'Producer identity missing or oversized: ' + field)
    frame_records = [json.loads(line[len(FRAME_MARKER):]) for line in lines if line.startswith(FRAME_MARKER)]
    require(len(frame_records) == duration*2, 'Producer frame trace is incomplete')
    require(all(isinstance(row, dict) and row == {'session_id': session, 'frame': i}
                and type(row.get('frame')) is int for i, row in enumerate(frame_records, 1)),
            'Producer frames must be complete, ordered and session-bound')
    return value


class PresentationDiagnostic(base.Diagnostic):
    def __init__(self, args, context):
        super().__init__(args, context)
        self.wine_owner = DeviceWineProcessOwner(context)
        self.wine_env.update(self.wine_owner.environment)
        self.cleanup_status = {'postgres_graceful': True, 'wine_prefix_stopped': False,
                               'owned_processes_reaped': False}
        self.presentation_socket = args.socket_dir / 'view.sock'
        self.presentation_socket_identity = None

    def initialize(self):
        self.ctx.stage('presentation_inputs')
        require(platform.machine().lower() in ('aarch64', 'arm64'), 'Guest must execute on ARM64')
        require(os.geteuid() == 1000, 'Guest requires PRoot -i 1000:1000')
        self.ctx.report['asset_sha256'] = verify_assets(self.args.assets)
        base.arm64_elf(self.args.wine)
        base.arm64_elf(self.args.wineserver)
        require(self.args.socket_dir.is_dir() and not self.args.socket_dir.is_symlink(),
                'Missing private bound presentation socket directory')
        require(stat.S_IMODE(self.args.socket_dir.stat().st_mode) == 0o700,
                'Presentation socket directory must have mode 0700')
        require(not self.presentation_socket.exists() and not self.presentation_socket.is_symlink(),
                'Presentation socket path already exists')
        self.ctx.passed(machine=platform.machine(), guest_uid=os.geteuid(), postgres_started=False)

    def start_wine(self):
        self.ctx.stage('presentation_display')
        number = next((n for n in range(100, 300) if not Path('/tmp/.X11-unix/X' + str(n)).exists()
                       and not Path('/tmp/.X' + str(n) + '-lock').exists()), None)
        require(number is not None, 'No free owned X display')
        self.wine_env['DISPLAY'] = ':' + str(number)
        self.xserver = self.ctx.start('private-presentation-x', [self.args.xserver, ':' + str(number),
            '-geometry', '800x600', '-depth', '24', '-ac', '-nolisten', 'tcp', '-rfbport', '-1',
            '-rfbunixpath', self.presentation_socket, '-rfbunixmode', '0600', '-SecurityTypes', 'None',
            '-localhost'], env=self.base_env)
        deadline = time.monotonic() + 30
        while not self.presentation_socket.exists() or not Path('/tmp/.X11-unix/X' + str(number)).exists():
            self.ctx.check()
            require(self.xserver.process.poll() is None, 'Presentation display exited before readiness')
            require(time.monotonic() < deadline, 'Presentation display startup timed out')
            time.sleep(.05)
        info = self.presentation_socket.lstat()
        require(stat.S_ISSOCK(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600,
                'Presentation endpoint must be a private mode-0600 Unix socket')
        self.presentation_socket_identity = (info.st_dev, info.st_ino)
        self.ctx.passed(width=800, height=600, rfb_tcp=False, x_tcp=False,
                        socket_path=str(self.presentation_socket), socket_mode='0600')
        self.ctx.stage('wine_initialization')
        self.wine_started = True
        self.initialize_wine()
        self.ctx.passed(**self.wine_initialization)

    def execute(self):
        self.initialize()
        self.start_wine()
        self.ctx.stage('win32_runtime_dll')
        result = self.ctx.run('runtime-probe', [self.args.wine,
            base.windows_path(self.args.assets / 'runtime-probe.exe')], timeout=60, env=self.wine_env)
        self.ctx.passed(**base.validate_runtime_probe(result['output']))
        self.mark_wine_ready()
        self.ctx.stage('visible_presentation_frames')
        self.ctx.event('presentation_ready', session_id=self.args.session_id, width=800, height=600,
                       duration_seconds=self.args.duration_seconds, socket_path=str(self.presentation_socket))
        child = self.ctx.start('presentation-probe', [self.args.wine,
            base.windows_path(self.args.assets / 'presentation-probe.exe'), self.args.session_id,
            str(self.args.duration_seconds)], env=self.wine_env)
        deadline = time.monotonic() + self.args.duration_seconds + 60
        progress = 0
        while child.process.poll() is None or child.reader.is_alive():
            self.ctx.check()
            require(self.xserver.process.poll() is None, 'Presentation display exited during frame production')
            require(time.monotonic() < deadline, 'Presentation producer timed out')
            if time.monotonic() >= progress:
                count = child.text().count(FRAME_MARKER)
                self.ctx.event('stage', status='running', message='Displaying test frames', frames_emitted=count)
                progress = time.monotonic() + 5
            time.sleep(.05)
        child.writer.join(timeout=1)
        self.ctx.record(child)
        require(child.process.returncode == 0, 'Presentation producer failed')
        producer = validate_producer(child.text(), self.args.session_id, self.args.duration_seconds)
        self.ctx.report.update(producer=producer, frames_emitted=producer['frames'],
            renderer=producer['renderer'], software_rendering=producer['software_rendering'])
        self.ctx.passed(frames_emitted=producer['frames'], producer=producer)

    def cleanup(self):
        failures = super().cleanup()
        owner = self.wine_owner.receipt
        if self.wine_started and (owner['inspection_failures'] != 0 or owner['remaining'] != 0 or not owner['complete']):
            failures.append('Wine ownership inspection or descendant cleanup was not complete')
        if self.presentation_socket_identity is not None:
            try:
                if self.presentation_socket.exists() or self.presentation_socket.is_symlink():
                    info = self.presentation_socket.lstat()
                    require(stat.S_ISSOCK(info.st_mode)
                            and (info.st_dev, info.st_ino) == self.presentation_socket_identity,
                            'Presentation endpoint identity changed during cleanup')
                    require(self.xserver.process.poll() is not None and not self.xserver.reader.is_alive(),
                            'Cannot remove endpoint of a live presentation display')
                    self.presentation_socket.unlink()
                self.ctx.report['presentation_socket_removed'] = True
            except Exception as exc:
                failures.append('Presentation socket cleanup: ' + str(exc))
                self.ctx.report['presentation_socket_removed'] = False
        return failures


def persist_report(args, context):
    document = json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n'
    require(len(document.encode()) <= 2*1024*1024, 'Presentation report exceeded bound')
    base.private_write(args.state / 'latest-report.json', document)
    target = args.state / 'report.zip'
    require(not target.is_symlink(), 'Refusing linked support archive')
    temporary = target.with_name('report.zip.tmp-' + base.secrets.token_hex(8))
    require(not temporary.exists() and not temporary.is_symlink(), 'Support staging path already exists')
    try:
        with open(temporary, 'xb') as handle:
            os.chmod(temporary, 0o600)
            with zipfile.ZipFile(handle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('latest-report.json', document)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=Path('/state'))
    parser.add_argument('--assets', type=Path, default=Path('/opt/coh'))
    parser.add_argument('--pg-bin', type=Path, default=Path('/opt/coh/pgsql/bin'))
    parser.add_argument('--wine', type=Path, default=Path('/opt/wine/bin/wine'))
    parser.add_argument('--wineserver', type=Path, default=Path('/opt/wine/bin/wineserver'))
    parser.add_argument('--xserver', type=Path, default=Path('/usr/bin/Xtigervnc'))
    parser.add_argument('--execution-platform', choices=('android', 'host'), default='host')
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--duration-seconds', type=int, default=60)
    parser.add_argument('--socket-dir', type=Path, default=Path('/presentation-socket'))
    parser.add_argument('--timeout-seconds', type=int, default=900)
    args = parser.parse_args(argv)
    os.umask(0o077)
    context = base.Context(args.state, args.timeout_seconds)
    context.report.update(scope=SCOPE, diagnostic_mode='visible_presentation', session_id=args.session_id,
        execution_platform_requested=args.execution_platform, postgres_started=False,
        game_validated=False, android_surface_validated=False, hardware_acceleration_validated=False,
        frames_emitted=0)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic = None
    validated = False
    try:
        validate_args(args)
        validated = True
        context.check()
        diagnostic = PresentationDiagnostic(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except base.Cancelled as exc:
        context.report.update(status='cancelled', failures=[str(exc)])
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        if diagnostic is not None:
            try:
                failures = diagnostic.cleanup()
            except Exception as exc:
                failures = ['Owned cleanup failed: ' + str(exc)]
            context.report['failures'].extend(failures)
        closed = all(c.process.poll() is not None and not c.reader.is_alive() and not c.writer.is_alive()
                     for c in context.children)
        context.report.update(finished_utc=base.utc(), cleanup_complete=closed,
            cleanup_execution={'diagnostic_initialized': diagnostic is not None,
                'wine_started': bool(diagnostic is not None and diagnostic.wine_started),
                'owned_child_count': len(context.children)},
            cleanup=diagnostic.cleanup_status if diagnostic else {'postgres_graceful': True,
                'wine_prefix_stopped': False, 'owned_processes_reaped': closed})
        context.report['passed'] = (context.report['status'] == 'passed' and not context.report['failures']
                                    and closed and all(context.report['cleanup'].values()))
        if context.report['status'] == 'passed' and not context.report['passed']:
            context.report['status'] = 'failed'
            if not context.report['failures']:
                context.report['failures'].append('Required owned cleanup was not proved')
        try:
            if validated:
                persist_report(args, context)
        except Exception as exc:
            context.report.update(status='failed', passed=False)
            context.report['failures'].append('Cannot persist presentation report: ' + str(exc))
            # A ZIP failure after the JSON write must not leave a passed receipt
            # as this failed process's apparent final result.
            if validated:
                try:
                    failure_text = json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n'
                    require(len(failure_text.encode()) <= 2*1024*1024, 'Failure report exceeded bound')
                    base.private_write(args.state / 'latest-report.json', failure_text)
                except Exception:
                    pass
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['status'] == 'passed' else 2 if context.report['status'] == 'cancelled' else 1


if __name__ == '__main__':
    sys.exit(main())
