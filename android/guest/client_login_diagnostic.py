#!/usr/bin/env python3
"""One graphical local-login session with a persistent private server profile."""
import argparse
import json
from pathlib import Path
import os
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_interactive_diagnostic as interactive
import local_login_server as server

base, require = interactive.base, interactive.require
SCOPE = 'actual_client_login_guest'
REQUIRED = interactive.REQUIRED | {'client_login_diagnostic.py', 'local_login_server.py',
    'dbserver-package.tar.gz', 'dbserver-schema.tar.gz', '001-coh-compat.sql', 'psqlodbc_x86.msi'}


class LoginContext(base.Context):
    server_health = None
    def check(self):
        super().check()
        if self.server_health is not None: self.server_health()


class ClientLoginDiagnostic(interactive.ClientInteractiveDiagnostic):
    def __init__(self, args, context):
        super().__init__(args, context)
        self.local_server = server.LocalLoginServer(self)
        self.login_announced = False
        self.local_server.report['version_policy'] = {
            'mode': 'explicit_dev_stamp_comparison_skipped',
            'native_launcher_mode': '--local-login', 'client_option': '-noversioncheck 1',
            'protocol_version_check_retained': True,
            'protocol_check_basis': 'reviewed_pinned_DbServer_handleLogin_source',
            'source_binary_pin_verified': False,
            'scope': 'private_loopback_fake_auth_only',
        }

    def launcher_command(self):
        return super().launcher_command() + ['--local-login']

    def sql(self, text, *, game=False, cleanup=False):
        # The inherited cleanup is intentionally used, but it can never drop
        # this profile, even if a future caller accidentally changes a flag.
        require('DROP DATABASE' not in ' '.join(text.upper().split()), 'Persistent profile forbids database deletion')
        return base.Diagnostic.sql(self, text, game=game, cleanup=cleanup)

    def initialize(self):
        super().initialize()
        require(REQUIRED <= set(self.ctx.report['asset_sha256']), 'Local login inputs missing from the pinned client inventory')
        self.local_server.initialize()
        self.local_server.report['version_policy']['source_binary_pin_verified'] = True
        self.ctx.server_health = self.local_server.health

    def start_wine(self):
        super().start_wine()
        self.local_server.start()

    def observe_console(self):
        output, launch, console = super().observe_console()
        if (not self.login_announced and launch and console and self.observer is not None
                and self.ctx.report.get('startup_observed')):
            proof = self.local_server.login_evidence()
            if proof is not None:
                # The fresh image may still be a transition. This only enables
                # a new Android capture watermark; no pixels are classified.
                windows = self.observer.windows()
                identity = interactive.startup_evidence(output, '', windows, launch)
                require(identity['client_window_observed'], 'Actual client identity disappeared during local login')
                shot = self.observer.capture(self.capture_dir / 'client-local-login.ppm')
                shot.update(session_id=self.args.session_id, captured_utc=base.utc())
                if shot['distinct_colors_capped'] < 8:
                    (self.capture_dir / shot['path']).unlink()
                else:
                    self.local_server.report.update(proof, client_pid=launch['pid'],
                        verified_utc=base.utc(), client_capture=shot)
                    self.login_announced = True
                    self.ctx.event('client_login_ready', session_id=self.args.session_id,
                        client_pid=launch['pid'], character_list_sent=True, character_selection_visual_validated=False)
        return output, launch, console

    def finish_observation(self, launch, registry_output, deadline):
        require(self.login_announced and self.local_server.report.get('character_list_sent') is True
                and self.local_server.report.get('client_pid') == launch['pid'],
                'Local login and character-list response were not observed; export this session without repeating boot')
        return super().finish_observation(launch, registry_output, deadline)

    def save_evidence(self):
        super().save_evidence()
        self.local_server.collect(self.capture_dir)

    def cleanup(self):
        self.ctx.server_health = None
        try:
            failures = super().cleanup()
        finally:
            self.local_server.cleanup_config()
        # Proven shutdown and the intact owned PG_VERSION/profile marker are
        # persistence evidence; a subsequent restart verifies logical reuse.
        profile = self.local_server.profile
        preserved = (self.cleanup_status['postgres_graceful']
            and (profile / 'pgdata/PG_VERSION').is_file()
            and (profile / 'profile.json').is_file() and not self.database_created)
        self.local_server.report['database_preserved'] = bool(preserved)
        if self.ctx.report.get('postgres_started') and not preserved:
            failures.append('Persistent profile preservation or PostgreSQL shutdown was not proved')
        return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in [('state', '/state'), ('assets', '/opt/coh'), ('pg-bin', '/opt/coh/pgsql/bin'),
                          ('wine', '/opt/wine/bin/wine'), ('wineserver', '/opt/wine/bin/wineserver'),
                          ('xserver', '/usr/bin/Xtigervnc'), ('socket-dir', '/presentation-socket'),
                          ('game-data', '/game-import/data')]:
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--execution-platform', choices=('android', 'host'), default='host')
    parser.add_argument('--profile', choices=(server.PROFILE,), required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--startup-timeout-seconds', type=int, default=900)
    parser.add_argument('--observation-seconds', type=int, default=30)
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    parser.add_argument('--interaction-seconds', type=int, default=180)
    args = parser.parse_args(argv)
    base.OUTPUT_LIMIT = interactive.CLIENT_OUTPUT_LIMIT
    os.umask(0o077)
    context = LoginContext(args.state, args.timeout_seconds)
    context.report.update(scope=SCOPE, diagnostic_mode='actual_client_login', session_id=args.session_id,
        execution_platform_requested=args.execution_platform, postgres_started=False, server_started=False,
        mapserver_started=False, game_validated=False, menu_visual_validated=False,
        android_surface_validated=False, hardware_acceleration_validated=False,
        client_process_started=False, startup_observed=False, interaction_session_completed=False,
        input_effect_verified=False, interaction_timeout_seconds=args.interaction_seconds)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic, validated = None, False
    try:
        interactive.validate_args(args); validated = True
        context.check()
        diagnostic = ClientLoginDiagnostic(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except base.Cancelled as exc:
        context.report.update(status='cancelled', failures=[str(exc)])
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        context.server_health = None
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
            and closed and all(context.report['cleanup'].values())
            and context.report.get('local_login', {}).get('character_list_sent') is True
            and context.report.get('local_login', {}).get('database_preserved') is True)
        if context.report['status'] == 'passed' and not context.report['passed']:
            context.report['status'] = 'failed'
            if not context.report['failures']: context.report['failures'].append('Required local login or cleanup was not proved')
        if validated:
            try: interactive.persist_report(args, context, diagnostic.capture_dir if diagnostic else None)
            except Exception as exc:
                context.report.update(status='failed', passed=False)
                context.report['failures'].append('Cannot persist client report: ' + str(exc))
                try: base.private_write(args.state / 'latest-report.json', json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n')
                except Exception: pass
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['passed'] else 2 if context.report['status'] == 'cancelled' else 1


if __name__ == '__main__': sys.exit(main())
