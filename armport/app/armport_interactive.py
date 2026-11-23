"""ARM64 client option for the existing creation/reopen guest.

The existing x86 worktree remains the server's verified data source. Only the
graphical client's executable, current directory, bins, registry view and
diagnostic output differ. Existing login, SQL/save and cleanup checks remain.
"""
import datetime
import errno
import fcntl
import os
from pathlib import Path
import re
import shutil
import stat
import socket
import struct
import sys
import termios
import time

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


# 0.13.69: what does PRoot do with ioctl(2) here? Android builds of the pinned PRoot stop
# every ioctl of every guest task twice (entry and exit), which for this game includes
# each GPU call of the renderer; patch 0004 with PROOT_IOCTL_COMMANDS_ONLY=1 stops only
# the commands PRoot acts on. The probe times three calls on a private pipe: getppid
# (never stopped: the floor), FIONREAD (an ioctl PRoot does not act on) and TCGETS2
# (one it does act on; a pipe answers ENOTTY). A stop costs tens of microseconds, the
# calls themselves well under one, so the three readings tell the cases apart.
IOCTL_PROBE_CALLS = 400
IOCTL_PROBE_STOP_MICROSECONDS = 8.0
IOCTL_TCGETS2 = 0x802C542A


def proot_ioctl_probe(calls=IOCTL_PROBE_CALLS, clock=time.perf_counter):
    """Read-only timing of ioctl through PRoot; never the reason a launch fails."""
    # The launcher starts the guest with a clean environment, so PRoot's own switch is not
    # visible here; COH_PROOT_IOCTL_FILTER says whether the launcher set it (app and CI).
    record = {'format': 1, 'calls': calls, 'requested': os.environ.get('COH_PROOT_IOCTL_FILTER') == '1',
              'stop_threshold_microseconds': IOCTL_PROBE_STOP_MICROSECONDS, 'is_success_proof': False}
    try:
        reader, writer = os.pipe()
    except OSError as error:
        return dict(record, reading='unavailable', error_type=type(error).__name__)
    try:
        os.write(writer, b'abc')
        buffer = bytearray(4)

        def floor():
            os.getppid()

        def unlisted():
            fcntl.ioctl(reader, termios.FIONREAD, buffer)

        def listed():
            try:
                fcntl.ioctl(reader, IOCTL_TCGETS2, bytearray(44))
            except OSError as error:
                if error.errno not in (errno.ENOTTY, errno.EINVAL):
                    raise

        timings = {}
        for name, call in (('getppid', floor), ('fionread', unlisted), ('tcgets2', listed)):
            call()
            started = clock()
            for _ in range(calls):
                call()
            timings[name] = round((clock() - started) / calls * 1e6, 2)
        require(struct.unpack('i', buffer)[0] == 3, 'FIONREAD answered a wrong count')
    except (OSError, RuntimeError) as error:
        return dict(record, reading='unavailable', error_type=type(error).__name__)
    finally:
        os.close(reader)
        os.close(writer)
    slow = {name: timings[name] - timings['getppid'] >= IOCTL_PROBE_STOP_MICROSECONDS
            for name in ('fionread', 'tcgets2')}
    reading = ('every_ioctl_stops' if slow['fionread'] and slow['tcgets2'] else
               'listed_commands_only' if slow['tcgets2'] else
               'inconsistent' if slow['fionread'] else 'no_ioctl_stops')
    record = dict(record, reading=reading, microseconds_per_call=timings)
    # 0.13.70 (PRoot patch 0005): a socket option PRoot does not rewrite. With a fake id it stops
    # twice per call unless PROOT_GETSOCKOPT_PEERCRED_ONLY=1 is set. Recorded beside `reading`.
    try:
        left, right = socket.socketpair()
        try:
            left.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
            started = clock()
            for _ in range(calls):
                left.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
            timings['getsockopt'] = round((clock() - started) / calls * 1e6, 2)
        finally:
            left.close()
            right.close()
        record['getsockopt_stops'] = timings['getsockopt'] - timings['getppid'] >= IOCTL_PROBE_STOP_MICROSECONDS
    except OSError as error:
        record['getsockopt_error_type'] = type(error).__name__
    # 0.13.73 (PRoot patch 0007): PRoot asks for sendto, recvfrom and recvmsg only to serve
    # rtnetlink sockets. With PROOT_NETLINK_HIGH_FDS=1 those sockets get descriptor numbers
    # from 960 and the three calls stop only from that number, so an ordinary send and receive
    # cost what getppid costs. Thor 0.13.72: 38-49 % of all stops were these calls.
    record['socket_filter_requested'] = os.environ.get('COH_PROOT_SOCKET_FILTER') == '1'
    try:
        left, right = socket.socketpair()
        try:
            def exchange():
                left.send(b'x')
                right.recv(1)
            exchange()
            started = clock()
            for _ in range(calls):
                exchange()
            timings['send_recv'] = round((clock() - started) / calls * 1e6, 2)
        finally:
            left.close()
            right.close()
        record['socket_stops'] = timings['send_recv'] - 2 * timings['getppid'] >= IOCTL_PROBE_STOP_MICROSECONDS
    except OSError as error:
        record['socket_error_type'] = type(error).__name__
    try:
        route = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, socket.NETLINK_ROUTE)
        try:
            record['netlink_descriptor'] = route.fileno()
        finally:
            route.close()
    except (OSError, AttributeError) as error:
        record['netlink_error_type'] = type(error).__name__
    return record


CLIENT_MAP_LINE = re.compile(
    r'^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\] \[INFO\] '
    r'(?:Connecting to MapServer 127\.0\.0\.1:(\d{1,5}) \(UDP\)|(Established successful MapServer connection))', re.M)


def client_timeline(text, started_utc=None, observed_utc=None, limit=32):
    """When the client itself reached each zone server, from its own log (guest clock, UTC).

    Thor 0.13.69: the supervisor learns of a connection from the server log, which the game's
    log server holds for 60 s and the zone server sends in 30 s batches, so `connected` was
    reported 66-75 s after the client was in the world (20261113-012755: client 338.7 s after
    the guest started, observer 405.0 s). This record is the client's own time. Read-only.
    """
    def parsed(value):
        try:
            return datetime.datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    rows, pending = [], None
    for match in CLIENT_MAP_LINE.finditer(text):
        stamp = datetime.datetime.strptime(match[1], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=datetime.timezone.utc)
        if match[2]:
            pending = (int(match[2]), stamp)
        elif len(rows) < limit:
            rows.append({'port': pending[0] if pending else None,
                         'connecting_utc': pending[1].isoformat() if pending else None,
                         'connected_utc': stamp.isoformat()})
            pending = None
    record = {'format': 1, 'source': 'client_log_timestamps', 'is_success_proof': False, 'connections': rows}
    if rows:
        first = parsed(rows[0]['connected_utc'])
        started, observed = parsed(started_utc), parsed(observed_utc)
        if started is not None:
            record['first_connected_seconds_after_guest_start'] = round((first - started).total_seconds(), 1)
        if observed is not None:
            record['observer_seconds_after_client'] = round((observed - first).total_seconds(), 1)
    return record


CALL_PROFILE = {'counts': None}
CALL_PROFILE_NAMES = ('stat', 'lstat', 'open', 'scandir', 'listdir', 'waitpid', 'readlink', 'access', 'kill')


def install_call_profile(environ=os.environ, modules=None):
    """COH_CALL_PROFILE=1 (CI; the app since 0.13.73): count this supervisor's own file and child calls by caller.

    CI run 43383782947 (PRoot's stop counts by program): the guest's Python made 22 % of all
    stops in a reopen session and 34 % in a creation session, more than any other program but
    the zone server: 815 `stat` calls a second. PRoot's counts cannot say which line makes them.
    Each wrapped call adds one count for the first caller outside the standard library.
    """
    if environ.get('COH_CALL_PROFILE') != '1' or CALL_PROFILE['counts'] is not None:
        return CALL_PROFILE['counts']
    import collections
    import io
    counts = CALL_PROFILE['counts'] = collections.Counter()
    library = os.path.dirname(os.__file__) + os.sep

    def wrap(owner, name, label):
        original = getattr(owner, name)

        def counted(*args, **kwargs):
            # The first caller outside the standard library, then up to three of its callers:
            # run 43808003132 named diagnostic.py:326 without saying which loop reaches it.
            frame, chain = sys._getframe(1), []
            for _ in range(48):
                if not frame.f_code.co_filename.startswith(library):
                    chain.append(os.path.basename(frame.f_code.co_filename) + ':' + str(frame.f_lineno))
                if frame.f_back is None or len(chain) == 4:
                    break
                frame = frame.f_back
            head = (chain[0].rsplit(':', 1) if chain else ['?', '0'])
            counts[(label, head[0], int(head[1]), '<'.join(chain[1:]))] += 1
            return original(*args, **kwargs)
        setattr(owner, name, counted)

    for name in CALL_PROFILE_NAMES:
        wrap(modules['os'] if modules else os, name, 'os.' + name)
    wrap(modules['io'] if modules else io, 'open', 'open')
    # 0.13.73: Popen.poll() keeps its own reference to waitpid, so the wrapper above never saw
    # it (run 43823341031: 135,306 wait4 stops, no os.waitpid row). Thor 0.13.72: 418-581 a second.
    if modules is None or 'subprocess' in modules:
        import subprocess
        wrap((modules['subprocess'] if modules else subprocess).Popen, 'poll', 'Popen.poll')
    return counts


def call_profile_record(top=60):
    counts = CALL_PROFILE['counts']
    if counts is None:
        return None
    rows = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    by_call = {}
    for (label, _, _, _), count in rows:
        by_call[label] = by_call.get(label, 0) + count
    return {'format': 2, 'is_success_proof': False, 'total': sum(counts.values()), 'by_call': by_call,
            'columns': ['call', 'file', 'line', 'count', 'callers_of_that_line'],
            'callers': [[label, name, line, count, chain] for (label, name, line, chain), count in rows[:top]]}


GRAPHICS_PROFILES = ('standard', 'effects_off')
GRAPHICS_PROFILE_MARK = b'ARMPORT_GRAPHICS_PROFILE_V1 effects_off '


def armport_graphics_profile(environ=os.environ):
    """The ARM64 client's launch-only graphics profile (0.13.73, patch 0129).

    `effects_off`: water refraction and reflection, bloom, depth of field, desaturation,
    shadows, cubemaps, ambient occlusion, vertical sync and antialiasing off; detail,
    textures and resolution as the game has them. The app sends it for its "Use performance
    graphics" option, which did nothing with the ARM64 client before (the launch said
    `standard` whatever the option was). Thor 0.13.72: 19-26 frames a second looking one
    way and 35-59 another with the client under one core; whether these effects are the
    cause is what the option now lets a test show. Any other value is `standard`.

    The guest receives it as COH_ARMPORT_GRAPHICS_PROFILE and hands it to the client as
    ARMPORT_GRAPHICS_PROFILE. COH_CLIENT_GRAPHICS_PROFILE is the x86 client's (`performance`:
    minimum detail and a 0.75 render scale); the launcher program resets it to a value it
    knows, so it stays `standard` for the ARM64 client.
    """
    value = environ.get('COH_ARMPORT_GRAPHICS_PROFILE', 'standard')
    return value if value in GRAPHICS_PROFILES else 'standard'


def graphics_profile_confirmed(log, tail=b''):
    """Whether the client itself logged that it applied `effects_off` (its first megabyte, or `tail`)."""
    try:
        with open(log, 'rb') as source:
            head = source.read(1024 * 1024)
    except OSError:
        head = b''
    return GRAPHICS_PROFILE_MARK in head or GRAPHICS_PROFILE_MARK in tail


REALPATH_CACHE_ENVIRONMENT = 'COH_WINESERVER_PATH_CACHE'
REALPATH_CACHE_LIBRARY = 'libarmport_realpath.so'
REALPATH_CACHE_REPORT = 'report.txt'
REALPATH_CACHE_LINE = re.compile(r'ARMPORT_REALPATH_CACHE_V2 calls=(\d{1,18}) fast=(\d{1,18}) folders=(\d{1,18}) '
                                 r'refreshed=(\d{1,18}) passed=(\d{1,18}) probes=(\d{1,18})\n')


def realpath_cache_requested(environ=os.environ):
    """COH_WINESERVER_PATH_CACHE=1 (the app's default since 0.13.74; CI): see install_realpath_cache."""
    return environ.get(REALPATH_CACHE_ENVIRONMENT) == '1'


def install_realpath_cache(archive, folder, wine_env, requested):
    """Put the wineserver realpath cache in place before the session's first Wine process.

    Wine's server calls realpath() for every file it opens, glibc answers with one readlink()
    per path component, and PRoot stops twice for each (Thor 0.13.73, launch B: 505,539
    readlinkat calls for 27,423 opens, a quarter of all stops). The library
    (armport/wineserver/realpath_cache.c) remembers resolved folders inside wineserver only
    and follows links itself (the server folders are trees of links to the installed data).
    It is loaded with LD_PRELOAD, which the first Wine process hands to the server it starts.

    Returns the report record. Anything unexpected leaves the environment unchanged: the
    session then runs as before.
    """
    record = {'format': 1, 'requested': bool(requested), 'installed': False, 'reason': None}
    if not requested:
        record['reason'] = 'not_requested'
        return record
    try:
        folder = Path(folder)
        library = folder / REALPATH_CACHE_LIBRARY
        if not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(library)):
            record['reason'] = 'unsafe_path'        # LD_PRELOAD splits on spaces and colons
            return record
        if wine_env.get('LD_PRELOAD'):
            record['reason'] = 'ld_preload_in_use'
            return record
        if folder.exists() or folder.is_symlink():
            record['reason'] = 'folder_exists'
            return record
        folder.mkdir(mode=0o700)
        member = package.extract_member(archive, package.REALPATH_CACHE, library)
        if member is None:
            folder.rmdir()
            record['reason'] = 'not_in_package'
            return record
        wine_env.update(LD_PRELOAD=str(library), ARMPORT_REALPATH_CACHE='1',
                        ARMPORT_REALPATH_CACHE_REPORT=str(folder / REALPATH_CACHE_REPORT))
        record.update(installed=True, sha256=member['sha256'], bytes=member['size'])
    except Exception as error:      # an optimisation: never the reason a session fails
        record.update(reason='error', error_type=type(error).__name__)
    return record


def realpath_cache_counters(folder):
    """The library's own counters, one report file per wineserver process (bounded read)."""
    servers, best = 0, None
    try:
        names = sorted(os.listdir(folder))[:64]
    except OSError:
        return {'servers': 0, 'counters': None}
    for name in names:
        if not name.startswith(REALPATH_CACHE_REPORT + '.'):
            continue
        try:
            with open(Path(folder) / name, 'rb') as source:
                match = REALPATH_CACHE_LINE.fullmatch(source.read(512).decode('ascii', errors='replace'))
        except OSError:
            continue
        if match is None:
            continue
        servers += 1
        values = dict(zip(('calls', 'fast', 'folders', 'refreshed', 'passed', 'probes'), map(int, match.groups())))
        if best is None or values['calls'] > best['calls']:
            best = values
    return {'servers': servers, 'counters': best}


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


def client_keeps_library_bounds():
    """Patch 0132 (0.13.81, off unless COH_CLIENT_LIBRARY_BOUNDS=1): the client keeps the bounds
    of object library files it has loaded and does not load them again at a zone load."""
    value = os.environ.get('COH_CLIENT_LIBRARY_BOUNDS', '')
    require(value in ('', '0', '1'), 'COH_CLIENT_LIBRARY_BOUNDS must be empty, 0 or 1')
    return value == '1'


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
        try:
            install_call_profile()
        except Exception:               # a measurement only
            pass
        super().initialize()
        pins = self.ctx.report['asset_sha256']
        require({'armport-client.zip', 'armport_client_package.py', 'armport_interactive.py', 'client_stdio.py'} <= pins.keys(),
                'ARM64 client is not included in this runtime package')
        self.ctx.report['client_worktree']['purpose'] = 'retained_server_data_source_for_armport'
        try:
            self.ctx.report['armport_proot_ioctl'] = proot_ioctl_probe()
        except Exception as error:      # read-only evidence
            self.ctx.report['armport_proot_ioctl'] = {'format': 1, 'reading': 'unavailable',
                                                      'error_type': type(error).__name__, 'is_success_proof': False}
        self.armport_work = self.root / ('armport-client-' + self.args.session_id)
        # Before start_wine(): the first Wine process starts wineserver with this environment.
        self.realpath_cache_folder = self.root / ('armport-native-' + self.args.session_id)
        if realpath_cache_requested():
            try:
                record = install_realpath_cache(self.args.assets / package.ARCHIVE, self.realpath_cache_folder,
                                                self.wine_env, True)
            except Exception as error:      # an optimisation: never the reason a session fails
                record = {'format': 1, 'requested': True, 'installed': False, 'reason': 'error',
                          'error_type': type(error).__name__}
        else:
            record = install_realpath_cache(None, self.realpath_cache_folder, None, False)
        self.ctx.report['wineserver_path_cache'] = record
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
        graphics = armport_graphics_profile()
        self.ctx.report['armport_graphics_profile'] = {'format': 1, 'requested': graphics, 'client_confirmed': None,
                                                       'physical_fps_measured': False}
        environment = dict(self.wine_env, ARMPORT_LOOSE_DATA='1', ARMPORT_NO_VERSION_CHECK='1',
                           ARMPORT_STDIO_LOG='armport_stdio.txt', COH_CLIENT_GRAPHICS_PROFILE='standard',
                           # Patch 0129 reads this one; the launcher resets the one above.
                           ARMPORT_GRAPHICS_PROFILE=graphics,
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
        environment.update(self.client_library_bounds_environment(environment.get('ARMPORT_FOLDER_CACHE_SKIP', '')))
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

    def client_library_bounds_environment(self, skip):
        """Patch 0132: where the client keeps object library bounds, beside the saved file list.

        The file's name holds the identity of the client's data view (the one the saved file
        list uses: it changes when a source directory or link target changes), so bounds kept
        for other data are never read; files of other identities are removed. Without a
        complete identity, or on any error here, the client loads as before.
        """
        record = {'format': 1, 'requested': client_keeps_library_bounds(), 'applied': False, 'file': None,
                  'bytes_before_launch': None, 'removed_other_identities': 0, 'error': None}
        self.ctx.report['client_library_bounds'] = record
        if not record['requested']:
            return {}
        try:
            identity = package.folder_cache_identity(self.ctx.report['armport_client'], skip, CLIENT_LIVE_FOLDERS)
            require(isinstance(identity, str) and re.fullmatch(r'[0-9a-f]{64}', identity), 'Invalid data view identity')
            target = self.root / (package.LIBRARY_BOUNDS_PREFIX + identity[:24] + package.LIBRARY_BOUNDS_SUFFIX)
            require(not target.is_symlink() and (not target.exists() or target.is_file()),
                    'Linked client library bounds file refused')
            for other in sorted(self.root.glob(package.LIBRARY_BOUNDS_PREFIX + '*')):
                if other != target and other.is_file() and not other.is_symlink():
                    other.unlink()
                    record['removed_other_identities'] += 1
            record['file'] = target.name
            record['bytes_before_launch'] = target.stat().st_size if target.exists() else 0
            record['applied'] = True
            return {'ARMPORT_LIBRARY_BOUNDS_CACHE': base.windows_path(target)}
        except (KeyError, TypeError, ValueError, OSError, base.DiagnosticError) as exc:
            record['error'] = type(exc).__name__
            return {}

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
                    captured = source.read(4 * 1024 * 1024)
                (self.capture_dir / 'armport_stdio.txt').write_bytes(captured)
                try:
                    report = self.ctx.report
                    section = next((report[key] for key in ('character_reopen', 'character_creation')
                                    if isinstance(report.get(key), dict)), {})
                    report['armport_client_timeline'] = client_timeline(
                        captured.decode('utf-8', errors='replace'), report.get('started_utc'),
                        section.get('client_ready_observed_utc'))
                except Exception as error:      # a record only: never the reason a session fails
                    self.ctx.report['armport_client_timeline'] = {'format': 1, 'error_type': type(error).__name__}
                profile = self.ctx.report.get('armport_graphics_profile')
                if isinstance(profile, dict):
                    profile['client_confirmed'] = graphics_profile_confirmed(log, captured)
        cache = self.ctx.report.get('wineserver_path_cache')
        if isinstance(cache, dict) and cache.get('installed') is True:
            try:
                cache.update(realpath_cache_counters(self.realpath_cache_folder))
            except Exception as error:      # a record only
                cache['counters_error_type'] = type(error).__name__
                try:
                    profile = call_profile_record()
                    if profile is not None:
                        self.ctx.report['python_call_profile'] = profile
                except Exception:
                    pass

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
        folder = getattr(self, 'realpath_cache_folder', None)
        if folder is not None and folder.is_dir() and not folder.is_symlink() and all(self.cleanup_status.values()):
            require(folder.parent == self.root, 'Native library directory identity changed')
            shutil.rmtree(folder)
        return failures


def select(diagnostic_type):
    selected = os.environ.get('COH_CLIENT_ARCH', 'x86')
    require(selected in ('x86', 'arm64'), 'Unknown graphical client architecture')
    if selected == 'x86':
        return diagnostic_type
    return type('ArmPort' + diagnostic_type.__name__, (ArmPortClient, diagnostic_type), {})
