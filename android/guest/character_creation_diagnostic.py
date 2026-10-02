#!/usr/bin/env python3
"""Graphical character creation, ordinary logout and committed private SQL save."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_login_diagnostic as login
import local_character_server as character
import character_avatar_assets as avatar

base, require, interactive = login.base, login.require, login.interactive
SCOPE = 'actual_character_creation_guest'
CHARACTER_NAME = 'THORHERO'
INTERACTION_SECONDS = 1200
OVERALL_SECONDS = 5400
MAX_CHILDREN = 512
CHARACTER_EVIDENCE_LIMIT = 256 * 1024 * 1024
REQUIRED = login.REQUIRED | {'character_creation_diagnostic.py', 'local_character_server.py',
    'character_server_data_cache.py', 'texture_header_index.py',
    'game-package.tar.gz', 'character_avatar_assets.py', avatar.ARCHIVE, avatar.MANIFEST,
    'atlas_world_assets.py', 'atlas-world-supplement.zip', 'atlas-world-supplement-manifest.json'}


def validate_args(args):
    # The accepted menu/login entry points keep their short fixed budgets.
    # This separate mode bounds Atlas startup plus a twenty-minute creator.
    require(isinstance(args.session_id, str) and re.fullmatch(r'[0-9a-f]{32}', args.session_id),
            'Invalid session identity')
    require(type(args.startup_timeout_seconds) is int and 60 <= args.startup_timeout_seconds <= 900,
            'Startup bound must be 60 to 900 seconds')
    require(type(args.observation_seconds) is int and args.observation_seconds == 30,
            'Character observation minimum must be 30 seconds')
    require(type(args.interaction_seconds) is int and args.interaction_seconds == INTERACTION_SECONDS,
            'Character creation window must be bounded to 1200 seconds')
    require(type(args.timeout_seconds) is int and args.timeout_seconds == OVERALL_SECONDS,
            'Character creation operation must be bounded to 5400 seconds')
    require(args.profile == login.server.PROFILE, 'Character creation requires the existing private profile')
    for path in (args.state, args.assets, args.socket_dir, args.game_data):
        require(path.is_absolute() and '..' not in path.parts and path != Path('/') and not path.is_symlink(),
                'Expected absolute unlinked private paths')


def positive_int(value):
    return type(value) is int and 0 < value <= 4294967295


def character_identity(proof, session):
    return (isinstance(proof, dict) and proof.get('session_id') == session
        and proof.get('name') == CHARACTER_NAME and proof.get('account') == login.server.ACCOUNT
        and positive_int(proof.get('character_id')) and positive_int(proof.get('auth_id'))
        and type(proof.get('map_id')) is int and proof['map_id'] == 1
        and proof.get('connected_on_atlas') is True)


def save_verified(proof, session):
    return (character_identity(proof, session) and proof.get('verified') is True
        and proof.get('committed_sql_verified') is True and proof.get('requested_logout_observed') is True
        and proof.get('logout_timer_observed') is True
        and proof.get('disconnected_before_sql') is True and proof.get('forced_stop_before_save') is False)


class CharacterContext(login.LoginContext):
    def start(self, label, argv, *, env=None, input_text=None, cleanup=False):
        # Longer observation adds bounded independent protocol/SQL queries and
        # registry reads. Every child still uses the same ownership/capture code.
        if not cleanup:
            self.check()
        require(len(self.children) < MAX_CHILDREN, 'Character session process count exceeded bound')
        child = base.OwnedProcess(label, argv, env or os.environ.copy(), input_text)
        self.children.append(child)
        return child


class CharacterCreationDiagnostic(login.ClientLoginDiagnostic):
    REPORT_KEY = 'character_creation'
    REQUIRED = REQUIRED
    identity_verified = staticmethod(character_identity)
    proof_verified = staticmethod(save_verified)

    def make_server(self):
        return character.LocalCharacterServer(self)

    def __init__(self, args, context):
        super().__init__(args, context)
        version_policy = dict(self.local_server.report['version_policy'])
        version_policy['native_launcher_mode'] = '--character-creation'
        self.local_server = self.make_server()
        self.local_server.report['version_policy'] = version_policy
        self.connected_announced = False
        self.saved_announced = False
        self.connected_identity = None

    def launcher_command(self):
        return interactive.ClientInteractiveDiagnostic.launcher_command(self) + ['--character-creation']

    def initialize(self):
        request = self.args.state / 'character-logout.json'
        require(not request.exists() and not request.is_symlink(), 'Stale character logout delivery receipt')
        super().initialize()
        require(self.REQUIRED <= set(self.ctx.report['asset_sha256']),
                'Character creation inputs missing from the pinned inventory')
        self.ctx.report['character_avatar_supplement'] = avatar.install(self.work, self.args.assets, self.ctx)
        # Missing world inputs are installed in this private client tree. Atlas
        # staging mirrors them into the private server tree before map launch.
        import atlas_world_assets as world
        self.ctx.report['atlas_world_supplement'] = world.install(self.work, self.args.assets, self.ctx)
        # Only the explicit new executable can consume this optional index.
        # The preserved stock startup/creation entry points keep their path.
        if not self.ctx.report.get('native_responsiveness_candidate'):
            return
        import texture_header_index
        try:
            index_receipt, index_env = texture_header_index.prepare(self.work,
                self.ctx.report['import_identity'], self.client_executable_sha256, self.ctx)
            self.ctx.report['texture_header_index'] = index_receipt
            self.wine_env.update(index_env)
        except (ValueError, OSError) as error:
            # Optional optimization failure retains the ordinary native path.
            for key in ('COH_TEXTURE_HEADER_PACK', 'COH_TEXTURE_HEADER_ID', 'COH_TEXTURE_DIAGNOSTIC_DEDUP'):
                self.wine_env.pop(key, None)
            self.ctx.report['texture_header_index'] = {'enabled': False, 'native_fallback_available': True,
                                                       'reason': str(error)[:300]}
            self.ctx.event('log', label='texture-header-index', message='Ordinary texture header reads: ' + str(error)[:300])

    def observe_console(self):
        output, launch, console = super().observe_console()
        if (self.saved_announced or not self.login_announced or not launch or not console
                or self.observer is None or not self.ctx.report.get('startup_observed')):
            return output, launch, console
        proof = self.local_server.character_evidence()
        current = self.ctx.report.get(self.REPORT_KEY, {})
        if current.get('connected_on_atlas') is True and not self.connected_announced:
            require(self.identity_verified(current, self.args.session_id), 'Connected character identity differs')
            require(current['auth_id'] == self.local_server.report.get('auth_id'),
                    'Created character does not belong to this local login')
            self.connected_identity = (current['character_id'], current['auth_id'])
            current['client_pid'] = launch['pid']
            self.connected_announced = True
            self.ctx.event('character_connected', session_id=self.args.session_id, client_pid=launch['pid'],
                character_id=current['character_id'], name=CHARACTER_NAME, account=login.server.ACCOUNT,
                map_id=1, **self.connected_event_data(current))
        if proof is not None:
            require(self.connected_announced and self.proof_verified(proof, self.args.session_id),
                    'Graphical character protocol save is incomplete')
            require((proof['character_id'], proof['auth_id']) == self.connected_identity,
                    'Saved character differs from the observed graphical connection')
            require(self.ctx.report.get('mapserver_started') is True,
                    'Character save lacks the owned MapServer')
            windows = self.observer.windows()
            identity = interactive.startup_evidence(output, '', windows, launch)
            require(identity['client_window_observed'], 'Actual client identity disappeared after character save')
            shot = self.observer.capture(self.capture_dir / 'client-character-saved.ppm')
            shot.update(session_id=self.args.session_id, captured_utc=base.utc())
            if shot['distinct_colors_capped'] < 8:
                (self.capture_dir / shot['path']).unlink()
            else:
                current.update(proof, client_pid=launch['pid'], verified_utc=base.utc(), client_capture=shot)
                self.saved_announced = True
                self.ctx.event('character_saved', session_id=self.args.session_id, client_pid=launch['pid'],
                    character_id=proof['character_id'], name=CHARACTER_NAME, committed_sql_verified=True,
                    **self.saved_event_data(proof))
        return output, launch, console

    def finish_observation(self, launch, registry_output, deadline):
        proof = self.ctx.report.get(self.REPORT_KEY, {})
        require(self.saved_announced and self.proof_verified(proof, self.args.session_id)
                and proof.get('client_pid') == launch['pid'],
                'Character save was not verified; export this session without another boot')
        return super().finish_observation(launch, registry_output, deadline)

    def connected_event_data(self, proof):
        return {}

    def saved_event_data(self, proof):
        return {}


def run(argv, diagnostic_type, scope, mode):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in [('state', '/state'), ('assets', '/opt/coh'), ('pg-bin', '/opt/coh/pgsql/bin'),
                          ('wine', '/opt/wine/bin/wine'), ('wineserver', '/opt/wine/bin/wineserver'),
                          ('xserver', '/usr/bin/Xtigervnc'), ('socket-dir', '/presentation-socket'),
                          ('game-data', '/game-import/data')]:
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--execution-platform', choices=('android', 'host'), default='host')
    parser.add_argument('--profile', choices=(login.server.PROFILE,), required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--startup-timeout-seconds', type=int, default=900)
    parser.add_argument('--observation-seconds', type=int, default=30)
    parser.add_argument('--timeout-seconds', type=int, default=OVERALL_SECONDS)
    parser.add_argument('--interaction-seconds', type=int, default=INTERACTION_SECONDS)
    args = parser.parse_args(argv)
    base.OUTPUT_LIMIT = interactive.CLIENT_OUTPUT_LIMIT
    os.umask(0o077)
    context = CharacterContext(args.state, args.timeout_seconds)
    context.report.update(scope=scope, diagnostic_mode=mode, session_id=args.session_id,
        execution_platform_requested=args.execution_platform, postgres_started=False, server_started=False,
        mapserver_started=False, game_validated=False, menu_visual_validated=False,
        android_surface_validated=False, hardware_acceleration_validated=False,
        client_process_started=False, startup_observed=False, interaction_session_completed=False,
        input_effect_verified=False, interaction_timeout_seconds=args.interaction_seconds)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic, validated = None, False
    try:
        validate_args(args); validated = True
        context.check()
        diagnostic = diagnostic_type(args, context)
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
            # Atlas can fail before the inherited client observation block
            # starts. Preserve the closed server consoles and flushed logs too.
            try: diagnostic.local_server.collect(diagnostic.capture_dir)
            except Exception as exc: context.report['failures'].append('Cannot retain server evidence: ' + str(exc))
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
            and context.report.get('local_login', {}).get('database_preserved') is True
            and context.report.get('mapserver_started') is True
            and diagnostic_type.proof_verified(context.report.get(diagnostic_type.REPORT_KEY), args.session_id))
        if context.report['status'] == 'passed' and not context.report['passed']:
            context.report['status'] = 'failed'
            if not context.report['failures']: context.report['failures'].append('Required character save or cleanup was not proved')
        if validated:
            try: interactive.persist_report(args, context, diagnostic.capture_dir if diagnostic else None,
                                            evidence_limit=CHARACTER_EVIDENCE_LIMIT)
            except Exception as exc:
                context.report.update(status='failed', passed=False)
                context.report['failures'].append('Cannot persist character report: ' + str(exc))
                try: base.private_write(args.state / 'latest-report.json', json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n')
                except Exception: pass
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['passed'] else 2 if context.report['status'] == 'cancelled' else 1


def main(argv=None):
    return run(argv, CharacterCreationDiagnostic, SCOPE, 'actual_character_creation')


if __name__ == '__main__': sys.exit(main())
