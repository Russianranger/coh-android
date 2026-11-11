"""ARM64 client option for the existing creation/reopen guest.

The existing x86 worktree remains the server's verified data source. Only the
graphical client's executable, current directory, bins, registry view and
diagnostic output differ. Existing login, SQL/save and cleanup checks remain.
"""
import os
from pathlib import Path
import re
import shutil
import stat

import armport_client_package as package
import client_startup_diagnostic as startup
from client_stdio import read_stdio

base, require = startup.base, startup.require
# Patch 0120 skip list for the client's folder scan; COH_CLIENT_SKIP_SERVER_FOLDERS=0
# (the app option unticked) keeps the full scan.
CLIENT_SKIPPED_FOLDERS = 'scripts.loc,server'
# Patch 0122: root folders the client always scans live beside its saved list:
# the writable cache roots (bin/ is the ARM64 overlay and is always live).
CLIENT_LIVE_FOLDERS = ','.join(sorted({Path(name).parts[0] for name in startup.PRIVATE_CACHE_ROOTS} - {'bin'}))
FPS_CAP_FILE = 'armport-fps-cap.txt'
# Game audio (0.13.53): Wine's ALSA driver plays through the TRASC plugin
# (armport/audio) to the app's AudioTrack bridge (ClientAudio.java).
AUDIO_CONFIG = 'armport-asound.conf'
ALSA_SYSTEM_CONFIG = Path('/usr/share/alsa/alsa.conf')


def client_audio_requested():
    """COH_CLIENT_AUDIO=1: the app's bridge listens on COH_CLIENT_AUDIO_SOCKET."""
    value = os.environ.get('COH_CLIENT_AUDIO', '')
    require(value in ('', '0', '1'), 'COH_CLIENT_AUDIO must be empty, 0 or 1')
    return value == '1'


def alsa_config(plugin):
    """ALSA plug converts Wine's format to the plugin's 48 kHz stereo S16_LE."""
    text = str(plugin)
    require(plugin.is_absolute() and re.fullmatch(r'[A-Za-z0-9_./-]+', text), 'Unsafe audio plugin path')
    return ('<' + str(ALSA_SYSTEM_CONFIG) + '>\n'
            'pcm_type.trasc { lib "' + text + '" }\n'
            'pcm.trasc { type trasc }\n'
            'pcm.!default { type plug slave { pcm "trasc" format S16_LE rate 48000 channels 2 } }\n')


# What join_texture_header_preparation publishes (character_creation_diagnostic).
TEXTURE_INDEX_ENVIRONMENT = ('COH_TEXTURE_HEADER_PACK', 'COH_TEXTURE_HEADER_ID', 'COH_TEXTURE_DIAGNOSTIC_DEDUP',
                             'COH_TEXTURE_HEADER_ROOT', 'COH_STARTUP_DIAGNOSTIC_BOUND')


def client_uses_folder_index():
    """Patch 0122: reuse the client's saved file list; COH_CLIENT_FOLDER_INDEX=0 turns it off."""
    value = os.environ.get('COH_CLIENT_FOLDER_INDEX', '')
    require(value in ('', '0', '1'), 'COH_CLIENT_FOLDER_INDEX must be empty, 0 or 1')
    return value != '0'


def client_skips_server_folders():
    value = os.environ.get('COH_CLIENT_SKIP_SERVER_FOLDERS', '')
    require(value in ('', '0', '1'), 'COH_CLIENT_SKIP_SERVER_FOLDERS must be empty, 0 or 1')
    return value != '0'


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
        # Cooperative telemetry shares the existing main-thread health cadence;
        # it adds no worker, subprocess or readiness/acceptance condition.
        try:
            import server_metrics
            self.armport_server_metrics = server_metrics.ServerMetrics(self)
            original_health = self.ctx.server_health
            def health_with_metrics():
                if original_health is not None:
                    original_health()
                try:
                    self.armport_server_metrics.observe()
                except Exception as exc:
                    self.armport_server_metrics.failure(exc)
            self.ctx.server_health = health_with_metrics
        except Exception as exc:
            self.ctx.report['armport_server_metrics'] = {'format': 1, 'is_success_proof': False,
                'available': False, 'initialization_error_type': type(exc).__name__}

    def start_wine(self):
        # Device startup: the saved-world server prepares and starts Atlas or
        # Kings Row while client supplements, the ARM64 link view and client
        # startup proceed; the existing main-thread join still admits input
        # only after native map readiness. Only the zoning reopen server
        # provides this supervised overlap (creation keeps its sequence).
        server = getattr(self, 'local_server', None)
        if callable(getattr(server, 'client_startup_assets_allowed', None)):
            server.overlap_client_initialization = True
        super().start_wine()
        # The existing server must seal its inputs before client-only visual
        # supplements are installed. The ARM64 copy must include those files;
        # copying in initialize() would miss later animation/visual payloads.
        self.prepare_client_visual_inputs()
        # 0.13.69: the saved character's own zone may start now, beside the ARM64 client's
        # data view, the texture list, the GPU probes and the client's start (COH_EARLY_ZONE).
        # 0.13.68 placed this call only in the x86 client's sequence
        # (character_creation_diagnostic.start_wine, after its early return), which this
        # launch does not take: CI run 42955090151 and the phone never reached it.
        early = getattr(getattr(self, 'local_server', None), 'start_early_zone', None)
        if callable(early):
            early()
        self.ctx.stage('armport_client_data')
        self.ctx.report['armport_client'] = package.prepare(
            self.args.assets / package.ARCHIVE, self.work / 'data', self.armport_work)
        self.client_executable_sha256 = self.ctx.report['armport_client']['executable_sha256']
        self.ctx.passed(machine='ARM64', x86_bins_reused=False,
                        executable_sha256=self.client_executable_sha256)
        self.start_texture_header_index()

    def start_texture_header_index(self):
        """Index texture headers for the ARM64 client (patch 0109) in the background.

        The existing worker reads the same immutable texture files the ARM64
        view links to and keys the pack to this executable; it is reused while
        neither changes. Any failure keeps the client's ordinary header reads.
        """
        import character_creation_diagnostic as creation
        if (getattr(self, 'texture_header_preparation', None) is not None
                or not hasattr(creation, 'TextureHeaderPreparation')
                or not {'import_identity', 'client_worktree'} <= self.ctx.report.keys()):
            return
        self.texture_header_preparation = creation.TextureHeaderPreparation(self)
        self.texture_header_preparation.start()

    def client_audio_environment(self, environment):
        """Route the client's DirectSound (Wine ALSA) to the app's AudioTrack bridge.

        Any missing piece keeps today's behaviour (the client starts without
        audio) and is recorded in client_audio; it never fails the session.
        """
        record = {'format': 1, 'requested': client_audio_requested(), 'enabled': False}
        self.ctx.report['client_audio'] = record
        if not record['requested']:
            return {}
        try:
            socket_path = Path(os.environ.get('COH_CLIENT_AUDIO_SOCKET', ''))
            require(socket_path.is_absolute() and len(str(socket_path)) < 108
                    and re.fullmatch(r'[A-Za-z0-9_./-]+', str(socket_path)), 'Invalid audio socket path')
            require(stat.S_ISSOCK(socket_path.lstat().st_mode), 'The app audio bridge is not listening')
            plugin = self.armport_work / package.AUDIO_PLUGIN
            require(plugin.is_file() and not plugin.is_symlink(), 'This client package has no audio plugin')
            require(ALSA_SYSTEM_CONFIG.is_file(), 'The guest has no ALSA configuration')
            config = self.armport_work / AUDIO_CONFIG
            require(not config.is_symlink(), 'Linked audio configuration refused')
            config.write_text(alsa_config(plugin))
            overrides = environment.get('WINEDLLOVERRIDES', '')
            record.update(enabled=True, socket=str(socket_path), plugin=package.AUDIO_PLUGIN,
                          plugin_sha256=package.digest(plugin), config=config.name)
            # Wine tries PulseAudio first; the guest has no server, so go straight to ALSA.
            return {'ALSA_CONFIG_PATH': str(config), 'TRASC_AUDIO_SOCKET': str(socket_path),
                    'WINEDLLOVERRIDES': (overrides + ';' if overrides else '') + 'winepulse.drv=d'}
        except (OSError, ValueError, base.DiagnosticError) as exc:
            record['error'] = type(exc).__name__ + ': ' + str(exc)
            return {}

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
        # 0.13.67: the texture header worker is joined in launch_client_attempt, after the GPU
        # probes. Thor 0.13.66 waited 19.7 s for it here and then 30.9 s for the probes; the
        # worker reads only the client's texture folders, so the two now overlap.
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
        # Device play: no per-exception SEH or power tracing and only boundary
        # zone records (patch 0108); CI qualification keeps its own tracing.
        environment = dict(self.wine_env, ARMPORT_LOOSE_DATA='1', ARMPORT_NO_VERSION_CHECK='1',
                           ARMPORT_STDIO_LOG='armport_stdio.txt', COH_CLIENT_GRAPHICS_PROFILE='standard',
                           WINEDEBUG='err+all,fixme-all', ARMPORT_TRACE_QUIET='1',
                           # The linked worktree is immutable for the session
                           # (patch 0111: no recursive change monitor).
                           ARMPORT_FIXED_DATA='1',
                           # Patch 0114: the game's own frame rate every 5 s.
                           ARMPORT_FPS_LOG='1',
                           # Patch 0123: the entity interpolation clock every 30 s.
                           ARMPORT_NET_CLOCK_LOG='1')
        if client_skips_server_folders():
            # Patch 0120: the client never reads these server-only folders
            # (52,149 scripts.loc files of 212,496); its upfront scan skips them.
            environment['ARMPORT_FOLDER_CACHE_SKIP'] = CLIENT_SKIPPED_FOLDERS
        environment.update(self.client_folder_index_environment(environment.get('ARMPORT_FOLDER_CACHE_SKIP', '')))
        environment.update(self.client_audio_environment(environment))
        # Patch 0121: zoning writes a lower frame cap here while a trip is
        # prepared (relative to the client's working directory).
        self.armport_fps_cap_file = self.armport_work / FPS_CAP_FILE
        self.armport_fps_cap_file.unlink(missing_ok=True)
        environment['ARMPORT_FPS_CAP_FILE'] = FPS_CAP_FILE
        environment = self.armport_gpu_environment(environment, label)
        environment = self.armport_gameplay_fps(environment)
        join = getattr(self, 'join_texture_header_preparation', None)
        if callable(join):
            # Publishes the index into self.wine_env once (a retry finds it already there).
            join()
            for key in TEXTURE_INDEX_ENVIRONMENT:
                environment.pop(key, None)
                if key in self.wine_env:
                    environment[key] = self.wine_env[key]
        command = ['/usr/bin/env', '-C', str(self.armport_work), *self.launcher_command()]
        child = self.ctx.start(label, command, env=environment)
        self.client = LoggedClient(child, self.armport_work / 'armport_stdio.txt')

    def client_folder_index_environment(self, skip):
        """Patch 0122: the saved file list lives beside the per-session worktrees."""
        index = self.root / package.FOLDER_INDEX
        record = {'format': 1, 'requested': client_uses_folder_index(), 'index': index.name,
                  'present_before_launch': index.is_file() and not index.is_symlink(),
                  'identity_sha256': None, 'error': None}
        self.ctx.report['client_folder_index'] = record
        if not record['requested']:
            return {}
        require(not index.is_symlink(), 'Linked client folder index refused')
        try:
            record['identity_sha256'] = package.folder_cache_identity(self.ctx.report['armport_client'], skip,
                                                                      CLIENT_LIVE_FOLDERS)
        except (KeyError, TypeError, ValueError) as exc:
            # Without a complete identity the client scans as before.
            record['error'] = type(exc).__name__
            return {}
        return {'ARMPORT_FOLDER_CACHE_INDEX': base.windows_path(index),
                'ARMPORT_FOLDER_CACHE_ID': record['identity_sha256'],
                'ARMPORT_FOLDER_CACHE_LIVE': CLIENT_LIVE_FOLDERS}

    def armport_gameplay_fps(self, environment):
        """Gameplay frame cap (patch 0113, the app's reviewed opt-in hook).

        The app launcher starts every client at 10 FPS; x86 raises gameplay to
        30 only through its separately qualified Game producer. The ARM64
        client asks for 30 only when the GPU renderer was selected after its
        probes; Software (default or fallback) keeps 10. Menu and background
        caps stay 10, and in-game /maxfps commands still apply.
        """
        gpu = self.ctx.report.get('client_gpu_profile') or {}
        fps = '30' if gpu.get('selected') == 'turnip' else '10'
        # 0.13.67: with the app's "60 FPS in the world" option the GPU renderer starts gameplay
        # at 60 (patch 0128). Thor 0.13.66 drew its first 75 s in the world at the 30 cap,
        # until the app had confirmed the connection and typed /maxfps 60.
        if fps == '30' and os.environ.get('COH_CLIENT_GAMEPLAY_60') == '1':
            fps = '60'
        environment = dict(environment, COH_CLIENT_GAMEPLAY_FPS=fps, COH_CLIENT_BOUNDED_TEXTURE_ERRORS='1')
        self.ctx.report['armport_gameplay_fps'] = {'format': 1, 'requested_cap': int(fps),
            'renderer_selected': gpu.get('selected', 'software'), 'menu_and_background_cap': 10,
            'physical_fps_measured': False}
        # 0.13.69 experiment (app option, off by default): Mesa's extra calling thread off for the
        # GPU renderer. Thor 0.13.67 in the world: the game's two threads, Mesa's `gl0` and `gdrv0`
        # at about 30% of a core each, their busy time adding up to the frame time (27 FPS), which
        # is what threads that wait for each other look like. `mesa_glthread` is Mesa's own user
        # switch (Mesa MR 21926); the game then calls the driver from its render thread.
        requested = os.environ.get('COH_CLIENT_GL_DIRECT') == '1'
        direct = requested and gpu.get('selected') == 'turnip'
        if direct:
            environment['mesa_glthread'] = 'false'
        self.ctx.report['armport_gl_threads'] = {'format': 1, 'direct_requested': requested,
            'mesa_glthread': 'false' if direct else 'driver_default', 'physical_fps_measured': False}
        return environment

    def armport_gpu_environment(self, environment, label):
        """Apply the app's existing GPU option (Turnip + Zink) to the ARM64 client.

        The same pinned driver and the same native Vulkan and Wine GL probes
        gate it; any probe failure falls back to Software before launch. The
        x86 Game producer pin is the only check replaced: the selected producer
        is this ARM64 executable. The renderer the client then reports is
        recorded by the existing startup evidence.
        """
        requested = self.wine_env.get('COH_CLIENT_GPU_PROFILE', os.environ.get('COH_CLIENT_GPU_PROFILE', 'software'))
        environment['COH_CLIENT_GPU_PROFILE'] = requested
        if requested == 'software':
            return environment
        import client_gpu_profile as gpu
        executable = self.client_executable_sha256
        original = gpu.current_game_producer
        gpu.current_game_producer = lambda owner: {'policy': 'armport_arm64_client_v1',
                                                   'client_executable_sha256': executable}
        try:
            return gpu.apply_profile(self, environment, label)
        finally:
            gpu.current_game_producer = original

    def save_evidence(self):
        # Base diagnostics read work/data caches and work/logs. During this
        # call they must observe the running ARM64 client, not the retained
        # x86 server-data tree. Restore the server root even on capture failure.
        server_work = self.work
        try:
            if hasattr(self, 'armport_work') and self.armport_work.exists():
                self.work = self.armport_work
            super().save_evidence()
        finally:
            self.work = server_work
        if hasattr(self, 'armport_work'):
            log = self.armport_work / 'armport_stdio.txt'
            if log.is_file() and not log.is_symlink():
                with log.open('rb') as source:
                    source.seek(max(0, log.stat().st_size - 4 * 1024 * 1024))
                    (self.capture_dir / 'armport_stdio.txt').write_bytes(source.read(4 * 1024 * 1024))

    def cleanup(self):
        metrics = getattr(self, 'armport_server_metrics', None)
        if metrics is not None:
            try:
                metrics.close()
            except Exception as exc:
                metrics.failure(exc)
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
    return type('ArmPort' + diagnostic_type.__name__, (ArmPortClient, diagnostic_type), {})
