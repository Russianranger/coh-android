#!/usr/bin/env python3
"""Bounded interactive menu session using the physically accepted client runtime.

The exact startup checks and input payload pins remain intact. A completed live
session does not prove an input effect; screenshots and physical interaction are
reviewed separately. No database/server is started.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_startup_diagnostic as startup
import client_attempt_retry as attempt_retry
from client_startup_diagnostic import (base, require, XObserver, startup_evidence,
    CLIENT_OUTPUT_LIMIT, persist_report)

SCOPE = 'actual_client_interaction_guest'
REQUIRED = startup.REQUIRED | {'client_interactive_diagnostic.py', 'client_attempt_retry.py'}
PROGRESS_POLL_SECONDS = 5


def validate_args(args):
    startup.validate_args(args)
    require(args.observation_seconds == 30, 'Interactive observation minimum must be 30 seconds')
    require(type(args.interaction_seconds) is int and args.interaction_seconds == 180,
            'Interactive session must be bounded to 180 seconds')


def read_finish_request(path, session, pid):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= 4096,
                'Invalid interaction finish request file')
        with os.fdopen(fd, 'rb', closefd=False) as source:
            raw = source.read(4097)
        require(len(raw) == info.st_size and len(raw) <= 4096, 'Interaction finish request changed or exceeded bound')
    finally:
        os.close(fd)
    value = json.loads(raw.decode('utf-8'))
    require(isinstance(value, dict) and set(value) == {'format', 'session_id', 'client_pid', 'action'}
            and type(value['format']) is int and value['format'] == 1
            and value['session_id'] == session and type(value['client_pid']) is int
            and value['client_pid'] == pid and value['action'] == 'finish_interaction',
            'Interaction finish request does not match the current client')
    return {'session_id': session, 'client_pid': pid, 'action': 'finish_interaction',
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'received_utc': base.utc()}


class ClientInteractiveDiagnostic(startup.ClientStartupDiagnostic):
    def __init__(self, args, context):
        super().__init__(args, context)
        self.finish_path = args.state / 'interaction-finish.json'

    def interaction_deadline(self, deadline, launch):
        """Modes may bound a validated phase; ordinary menu/creation stay fixed."""
        return deadline

    def record_observer_timing(self, name, started):
        metrics = self.ctx.report.setdefault('client_observer_metrics', {}).setdefault(name,
            {'calls': 0, 'total_ms': 0, 'max_ms': 0})
        elapsed_ms = round((time.monotonic() - started) * 1000, 3)
        metrics.update(calls=metrics['calls'] + 1, last_ms=elapsed_ms,
            total_ms=round(metrics['total_ms'] + elapsed_ms, 3), max_ms=max(metrics['max_ms'], elapsed_ms))

    def initialize(self):
        # The input contract deliberately retains its accepted startup scope;
        # verify_assets hashes every listed file, including this extra entry.
        super().initialize()
        require(REQUIRED <= set(self.ctx.report['asset_sha256']),
                'Interactive guest helper is missing from the pinned input inventory')

    def finish_observation(self, launch, registry_output, deadline):
        """Retain transient blank frames without extending the interaction window."""
        started = time.monotonic()
        settling = {'status': 'checking', 'captures': [], 'blank_capture_count': 0,
                    'initial_budget_seconds': round(max(0, deadline-started), 3),
                    'retry_interval_seconds': 5, 'retained_blank_capture_limit': 3}
        self.ctx.report['final_frame_settling'] = settling

        def processes_alive():
            self.ctx.check()
            require(self.client.process.poll() is None,
                    'Actual CoH client exited during startup or observation')
            require(self.xserver.process.poll() is None, 'Owned presentation display exited')

        def current_evidence():
            processes_alive()
            output, current_launch, console = self.observe_console()
            require(current_launch == launch and console is not None,
                    'Actual CoH client identity disappeared during final observation')
            windows = self.observer.windows()
            self.ctx.report['observed_windows'] = windows
            evidence = startup_evidence(output, registry_output, windows, current_launch)
            self.ctx.report.update(evidence)
            require(evidence['startup_observed'] and evidence['renderer_initialized']
                    and evidence['all_data_loaded'],
                    'Actual CoH window or startup evidence disappeared during observation')
            return evidence

        try:
            while True:
                current_evidence()
                # The normal terminal snapshot is still taken at the original
                # deadline. A retry must start and finish within that deadline.
                retry = bool(settling['captures'])
                require(not retry or time.monotonic() < deadline,
                        'Observed client desktop remained blank until the interaction deadline')
                target = self.capture_dir / 'client-observed.ppm'
                shot = self.observer.capture(target)
                shot.update(session_id=self.args.session_id, captured_utc=base.utc())
                nonblank = shot['distinct_colors_capped'] >= 8
                if not nonblank:
                    settling['blank_capture_count'] += 1
                    # Preserve the first two blanks and the latest blank. All
                    # attempt hashes/times stay in the report; raw PPM retention
                    # must fit the existing support archive's evidence reserve.
                    if settling['blank_capture_count'] > settling['retained_blank_capture_limit']:
                        previous_blank = settling['captures'][-1]
                        (self.capture_dir / previous_blank['path']).unlink()
                        previous_blank['retained'] = False
                    retained = self.capture_dir / ('client-settling-%03d.ppm' % settling['blank_capture_count'])
                    target.rename(retained)
                    shot['path'] = retained.name
                settling['captures'].append(dict(shot, retained=True,
                    elapsed_seconds=round(time.monotonic()-started, 3)))
                # Recheck the complete console, exact-PID window and live
                # processes after capture, including on a visually good frame.
                evidence = current_evidence()
                require(not retry or time.monotonic() <= deadline,
                        'Final client frame exceeded the interaction deadline')
                if nonblank:
                    self.captures.append(shot)
                    self.ctx.report['screenshots'] = self.captures
                    settling['status'] = 'settled'
                    return evidence
                require(time.monotonic() < deadline,
                        'Observed client desktop remained blank until the interaction deadline')
                settling['status'] = 'waiting_for_nonblank_frame'
                self.ctx.event('stage', status='running', message='Waiting for the client graphics to settle',
                               blank_captures=settling['blank_capture_count'])
                next_capture = min(deadline, time.monotonic() + 5)
                while time.monotonic() < next_capture:
                    processes_alive()
                    time.sleep(max(0, min(.1, next_capture-time.monotonic())))
        except Exception:
            settling['status'] = 'failed'
            raise
        finally:
            settling['elapsed_seconds'] = round(time.monotonic()-started, 3)

    def launcher_command(self):
        return [self.args.wine, base.windows_path(self.args.assets / 'client-launcher.exe'), self.args.session_id,
                base.windows_path(self.work / 'CityOfHeroes.exe'), base.windows_path(self.work)]

    def reset_client_startup_inputs(self):
        # Every attempt gets an empty registry watermark and private client logs.
        # Failed-attempt evidence is archived before this method is used again.
        self.ctx.run('client-progress-reset', [self.args.wine, 'reg', 'delete',
            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/f', '/reg:32'],
            timeout=8, env=self.wine_env, check=False)
        reset_query = self.ctx.run('client-progress-empty', [self.args.wine, 'reg', 'query',
            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/reg:32'],
            timeout=8, env=self.wine_env, check=False)
        require(not re.search(r'(?mi)^\s*GameProgress\s+REG_SZ\s+', reset_query['output']),
                'Prior client progress registry value could not be cleared')
        previous_logs = self.work / 'logs'
        require(not previous_logs.is_symlink(), 'Linked client logs refused')
        if previous_logs.exists():
            require(previous_logs.is_dir(), 'Client logs path must be a directory')
            shutil.rmtree(previous_logs)

    def launch_client_attempt(self, *, label='actual-coh-client'):
        previous = Path.cwd()
        try:
            os.chdir(self.work)
            self.client = self.ctx.start(label, self.launcher_command(), env=self.wine_env)
        finally:
            os.chdir(previous)

    def execute(self):
        require(not self.finish_path.exists() and not self.finish_path.is_symlink(),
                "Stale interaction finish request must be removed before launch")
        self.initialize()
        self.start_wine()
        self.ctx.stage('win32_runtime_dll')
        result = self.ctx.run('runtime-probe', [self.args.wine,
            base.windows_path(self.args.assets / 'runtime-probe.exe')], timeout=60, env=self.wine_env)
        self.ctx.passed(**base.validate_runtime_probe(result['output']))
        self.mark_wine_ready()
        self.reset_client_startup_inputs()
        self.ctx.stage('actual_client_startup')
        self.observer = XObserver(self.wine_env['DISPLAY'])
        self.capture('before-client')
        self.ctx.event('client_display_ready', session_id=self.args.session_id, width=800, height=600,
                       socket_path=str(self.presentation_socket), startup_timeout_seconds=self.args.startup_timeout_seconds)
        # The launcher's -nogui diagnostic-UI profile preserves the actual game
        # window, renderer and data validation, while suppressing native dialogs
        # and splash UI. It keeps inherited log pipes and observes the owned
        # child's console as a fallback; game code and assets remain unchanged.
        self.launch_client_attempt()
        started = time.monotonic()
        self.launcher_started_monotonic = started
        self.ctx.report['client_launcher_timing'] = {'started_utc': base.utc(),
            'started_monotonic': started, 'source': 'current_owned_launcher_start_returned',
            'startup_timeout_seconds': self.args.startup_timeout_seconds}
        deadline = started + self.args.startup_timeout_seconds
        retries = attempt_retry.ClientAttemptRetry(self, started, deadline)
        next_registry = next_progress = 0
        registry_output = ''
        self.ctx.report['client_progress_poll_policy'] = {
            'policy': 'query_after_current_console_renderer_and_data_ready',
            'deferred_checks': 0, 'registry_reset_before_launch': True,
            'current_pid_window_and_registry_main_loop_required': True}
        ready_at = None
        console = None
        finish_request = None
        try:
            while True:
                self.ctx.check()
                if self.client.process.poll() is not None:
                    if retries.prepare(ready_at):
                        next_registry = next_progress = 0
                        registry_output = ''
                        console = None
                        continue
                    require(False, 'Actual CoH client exited during startup or observation')
                require(self.xserver.process.poll() is None, 'Owned presentation display exited')
                now = time.monotonic()
                require(ready_at is not None or now < deadline,
                        'Actual CoH startup exceeded its bounded deadline')
                # Decoding and scanning a growing multi-MiB log at 10Hz steals
                # startup time. Use the existing five-second evidence poll;
                # stop/process/overall/overflow checks above remain at 100ms.
                # Refresh at the console deadline even between progress polls.
                poll_due = now >= next_progress
                if poll_due or (console is None and now - retries.started >= 120):
                    observed_at = time.monotonic()
                    output, launch, console = self.observe_console()
                    retries.observe_launch(launch)
                    self.record_observer_timing('console_and_native_readiness', observed_at)
                require(console is not None or now - retries.started < 120,
                        'Could not attach to actual client console within 120 seconds')
                if ready_at is not None:
                    deadline = self.interaction_deadline(deadline, launch)
                if poll_due or (ready_at is not None and time.monotonic() >= deadline):
                    window_started = time.monotonic()
                    windows = self.observer.windows()
                    self.record_observer_timing('window_identity', window_started)
                    self.ctx.report['observed_windows'] = windows
                    # Launching a translated reg.exe repeatedly competes with
                    # heavy client loading. Its only proof here is main-loop
                    # entry, so query after this attempt's console has both
                    # prerequisites. Keep the reset, live PID/window, ordinary
                    # registry proof and post-readiness checks intact.
                    registry_due = now >= next_registry
                    console_ready = ('Renderer initialization complete' in output
                                     and 'Loaded all data!' in output)
                    if registry_due and not console_ready:
                        self.ctx.report['client_progress_poll_policy']['deferred_checks'] += 1
                    if registry_due and console_ready:
                        registry_started = time.monotonic()
                        registry = self.ctx.run('client-progress-registry', [self.args.wine, 'reg', 'query',
                            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/reg:32'],
                            timeout=8, env=self.wine_env, check=False)
                        registry_output = registry['output']
                        self.record_observer_timing('progress_registry', registry_started)
                        next_registry = time.monotonic() + 20
                    evidence = startup_evidence(output, registry_output, windows, launch)
                    self.ctx.report.update(evidence)
                    if evidence['startup_observed'] and evidence['renderer_initialized'] and evidence['all_data_loaded']:
                        if ready_at is None:
                            ready_at = time.monotonic()
                            require(ready_at-started <= self.args.startup_timeout_seconds,
                                    'Actual CoH startup exceeded its bounded deadline')
                            deadline = ready_at + self.args.interaction_seconds
                            self.ctx.report['startup_elapsed_seconds'] = round(ready_at-started, 3)
                            shot = self.capture('client-startup')
                            require(shot and shot['distinct_colors_capped'] >= 8, 'Actual client desktop capture is blank')
                            self.ctx.event('client_startup_observed', session_id=self.args.session_id,
                                           client_pid=launch['pid'], menu_visual_validated=False)
                            self.ctx.passed(**evidence, startup_elapsed_seconds=round(ready_at-started, 3))
                            self.ctx.stage('actual_client_interaction')
                            self.ctx.event('client_interaction_ready', session_id=self.args.session_id,
                                client_pid=launch['pid'], minimum_observation_seconds=self.args.observation_seconds,
                                interaction_timeout_seconds=self.args.interaction_seconds)
                        deadline = self.interaction_deadline(deadline, launch)
                        if finish_request is None:
                            finish_request = read_finish_request(self.finish_path, self.args.session_id, launch['pid'])
                            if finish_request is not None:
                                self.ctx.report['interaction_finish_request'] = finish_request
                        elapsed = time.monotonic() - ready_at
                        if elapsed >= self.args.observation_seconds and (finish_request is not None or time.monotonic() >= deadline):
                            reason = 'finish_requested' if finish_request is not None else 'interaction_timeout'
                            self.ctx.event('client_interaction_finishing', session_id=self.args.session_id,
                                           client_pid=launch['pid'], completion_reason=reason)
                            self.ctx.report['observation_seconds'] = round(elapsed, 3)
                            evidence = self.finish_observation(launch, registry_output, deadline)
                            self.ctx.report['observation_seconds'] = round(time.monotonic()-ready_at, 3)
                            self.ctx.report.update(interaction_session_completed=True, input_effect_verified=False,
                                interaction_completion_reason=reason)
                            self.ctx.passed(**evidence, bounded_live_observation=True,
                                interaction_session_completed=True, input_effect_verified=False,
                                interaction_completion_reason=reason)
                            self.startup_complete = True
                            return
                    else:
                        require(ready_at is None, 'Actual CoH window or startup evidence disappeared during observation')
                    self.ctx.event('stage', status='running', message='Starting City of Heroes' if ready_at is None
                                   else 'Interactive City of Heroes menu session', elapsed_seconds=int(now-started),
                                   renderer_initialized=evidence['renderer_initialized'],
                                   client_main_loop_reached=evidence['client_main_loop_reached'])
                    # Keep the five-second cadence measured from poll start.
                    # A slow native query must not add another idle five seconds
                    # before the next current evidence inspection.
                    next_progress = now + PROGRESS_POLL_SECONDS
                time.sleep(.1)
        finally:
            self.save_evidence()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in [('state', '/state'), ('assets', '/opt/coh'), ('pg-bin', '/opt/coh/pgsql/bin'),
                          ('wine', '/opt/wine/bin/wine'), ('wineserver', '/opt/wine/bin/wineserver'),
                          ('xserver', '/usr/bin/Xtigervnc'), ('socket-dir', '/presentation-socket'),
                          ('game-data', '/game-import/data')]:
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--execution-platform', choices=('android', 'host'), default='host')
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--startup-timeout-seconds', type=int, default=900)
    parser.add_argument('--observation-seconds', type=int, default=30)
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    parser.add_argument('--interaction-seconds', type=int, default=180)
    args = parser.parse_args(argv)
    # This dedicated client invocation retains the full, verbose validation log
    # up to 128 MiB. Every owned child stays bounded and overflow remains fatal.
    # The accepted diagnostic.py payload itself stays byte-identical.
    base.OUTPUT_LIMIT = CLIENT_OUTPUT_LIMIT
    os.umask(0o077)
    context = base.Context(args.state, args.timeout_seconds)
    context.report.update(scope=SCOPE, diagnostic_mode='actual_client_interaction', session_id=args.session_id,
        execution_platform_requested=args.execution_platform, postgres_started=False,
        server_started=False, game_validated=False, menu_visual_validated=False,
        android_surface_validated=False, hardware_acceleration_validated=False,
        client_process_started=False, startup_observed=False,
        interaction_session_completed=False, input_effect_verified=False,
        interaction_timeout_seconds=args.interaction_seconds)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic = None
    validated = False
    try:
        validate_args(args); validated = True
        context.check()
        diagnostic = ClientInteractiveDiagnostic(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except base.Cancelled as exc:
        context.report.update(status='cancelled', failures=[str(exc)])
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        if diagnostic is not None:
            try: failures = diagnostic.cleanup()
            except Exception as exc: failures = ['Owned cleanup failed: ' + str(exc)]
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
            if not context.report['failures']: context.report['failures'].append('Required cleanup was not proved')
        if validated:
            try:
                persist_report(args, context, diagnostic.capture_dir if diagnostic else None)
            except Exception as exc:
                context.report.update(status='failed', passed=False)
                context.report['failures'].append('Cannot persist client report: ' + str(exc))
                try: base.private_write(args.state / 'latest-report.json', json.dumps(context.report, indent=2) + '\n')
                except Exception: pass
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['passed'] else 2 if context.report['status'] == 'cancelled' else 1


if __name__ == '__main__':
    sys.exit(main())
