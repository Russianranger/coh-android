"""ARM64 client option for the existing creation/reopen guest.

The existing x86 worktree remains the server's verified data source. Only the
graphical client's executable, current directory, bins, registry view and
diagnostic output differ. Existing login, SQL/save and cleanup checks remain.
"""
import os
from pathlib import Path
import re
import shutil

import armport_client_package as package
import client_startup_diagnostic as startup
from client_stdio import read_stdio

base, require = startup.base, startup.require


class LoggedClient:
    def __init__(self, child, log):
        self.child, self.log = child, log
        self.size, self.cached = -1, ''

    def __getattr__(self, name):
        return getattr(self.child, name)

    def text(self):
        if self.log.exists():
            require(not self.log.is_symlink(), 'Linked ARM64 log refused')
            size = self.log.stat().st_size
            require(size <= 16 * 1024 * 1024, 'ARM64 diagnostic log exceeded 16 MiB')
            if size != self.size:
                self.cached = read_stdio(self.log)
                self.size = size
        return self.child.text() + '\n' + self.cached


class ArmPortClient:
    """Mixin ahead of the selected existing creation/reopen diagnostic."""
    def prepare_client_visual_inputs(self):
        # Retained app donors need the visual helper for server copy bounds,
        # but do not contain its newer optional visual/animation bundle.
        names = {'client_visual_assets.py', 'client_animation_package.py',
                 'client-visual-assets.zip', 'client-visual-manifest.json'}
        present = {name for name in names if (self.args.assets / name).exists()
                   or (self.args.assets / name).is_symlink()}
        if present == {'client_visual_assets.py'}:
            helper = self.args.assets / 'client_visual_assets.py'
            require(helper.is_file() and not helper.is_symlink(), 'Invalid server visual helper')
            return
        # Any payload or animation helper still invokes all original checks.
        return super().prepare_client_visual_inputs()

    def initialize(self):
        super().initialize()
        pins = self.ctx.report['asset_sha256']
        require({'armport-client.zip', 'armport_client_package.py', 'armport_interactive.py', 'client_stdio.py'} <= pins.keys(),
                'ARM64 client is not included in this runtime package')
        self.ctx.report['client_worktree']['purpose'] = 'retained_server_data_source_for_armport'
        self.armport_work = self.root / ('armport-client-' + self.args.session_id)
        # These receipts describe the retained x86 staging producer. Do not
        # present them as ARM64 performance/renderer qualification or enable
        # their opt-ins for a different client binary.
        producers = ('native_responsiveness_candidate', 'startup_bundle_client', 'client_loading',
                     'client_startup_followup', 'client_scene_performance', 'client_gameplay_performance',
                     'client_renderer_attribution', 'client_render_pipeline', 'client_render_queue')
        retained = {}
        for name in producers:
            if name in self.ctx.report:
                retained[name] = self.ctx.report.pop(name)
            setattr(self, name, False)
        self.ctx.report['armport_server_staging'] = retained

    def start_wine(self):
        super().start_wine()
        # The existing server must seal its inputs before client-only visual
        # supplements are installed. The ARM64 copy must include those files;
        # copying in initialize() would miss later animation/visual payloads.
        self.prepare_client_visual_inputs()
        self.ctx.stage('armport_client_data')
        self.ctx.report['armport_client'] = package.prepare(
            self.args.assets / package.ARCHIVE, self.work / 'data', self.armport_work)
        self.client_executable_sha256 = self.ctx.report['armport_client']['executable_sha256']
        self.ctx.passed(machine='ARM64', x86_bins_reused=False,
                        executable_sha256=self.client_executable_sha256)

    def launcher_command(self):
        command = super().launcher_command()
        require(command[-1] in ('--character-manual', '--character-creation'), 'Unsupported ARM64 launch mode')
        return [self.args.wine, base.windows_path(self.armport_work / 'armport-launcher.exe'),
                self.args.session_id, base.windows_path(self.armport_work / 'CityOfHeroes.exe'),
                base.windows_path(self.armport_work), command[-1]]

    def query_client_progress(self):
        return self.ctx.run('armport-progress-registry', [self.args.wine, 'reg', 'query',
            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/reg:64'],
            timeout=8, env=self.wine_env, check=False)['output']

    def reset_client_startup_inputs(self):
        # The original server's verified x86 data tree remains untouched.
        self.ctx.run('armport-progress-reset', [self.args.wine, 'reg', 'delete',
            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/f', '/reg:64'],
            timeout=8, env=self.wine_env, check=False)
        require(not re.search(r'(?mi)^\s*GameProgress\s+REG_SZ\s+', self.query_client_progress()),
                'Previous ARM64 progress value was not cleared')
        logs = self.armport_work / 'logs'
        require(not logs.is_symlink(), 'Linked ARM64 logs refused')
        if logs.exists(): shutil.rmtree(logs)
        (self.armport_work / 'armport_stdio.txt').unlink(missing_ok=True)

    def launch_client_attempt(self, *, label='actual-coh-client'):
        environment = dict(self.wine_env, ARMPORT_LOOSE_DATA='1', ARMPORT_NO_VERSION_CHECK='1',
                           ARMPORT_STDIO_LOG='armport_stdio.txt', COH_CLIENT_GRAPHICS_PROFILE='standard')
        # Client GPU selection remains Software until this ARM64 producer is
        # separately qualified. Do not reuse an x86 GPU-probe success receipt.
        command = ['/usr/bin/env', '-C', str(self.armport_work), *self.launcher_command()]
        child = self.ctx.start(label, command, env=environment)
        self.client = LoggedClient(child, self.armport_work / 'armport_stdio.txt')

    def save_evidence(self):
        super().save_evidence()
        if hasattr(self, 'armport_work'):
            log = self.armport_work / 'armport_stdio.txt'
            if log.is_file() and not log.is_symlink():
                with log.open('rb') as source:
                    source.seek(max(0, log.stat().st_size - 4 * 1024 * 1024))
                    (self.capture_dir / 'armport_stdio.txt').write_bytes(source.read(4 * 1024 * 1024))

    def cleanup(self):
        failures = super().cleanup()
        if hasattr(self, 'armport_work') and self.armport_work.exists() and all(self.cleanup_status.values()):
            require(self.armport_work.parent == self.root and not self.armport_work.is_symlink(),
                    'ARM64 staging directory identity changed')
            shutil.rmtree(self.armport_work)
        return failures


def select(diagnostic_type):
    selected = os.environ.get('COH_CLIENT_ARCH', 'x86')
    require(selected in ('x86', 'arm64'), 'Unknown graphical client architecture')
    if selected == 'x86':
        return diagnostic_type
    require(not getattr(diagnostic_type, 'ZONING', False), 'ARM64 zone travel is not yet qualified')
    return type('ArmPort' + diagnostic_type.__name__, (ArmPortClient, diagnostic_type), {})
