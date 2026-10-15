#!/usr/bin/env python3
"""Owned server-only adapter for the native combined application.

The retained server stack is imported, not bundled here. No graphical CoH
client, fixture, account creation, character creation or relocation is called.
"""
import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
import signal
import shutil
import socket
import stat
import sys
import time

FORMAT = 1
APP_ID = 'org.coh.nativecombined'
GENERATION = re.compile(r'generation-[0-9a-f]{32}')
SESSION = re.compile(r'[0-9a-f]{32}')
BACKUP_MAX = 512 * 1024 * 1024
base = startup = character = zoning = login = None


class AdmissionError(RuntimeError):
    """A public constant code, never a process output or credential."""


def require(ok, code):
    if not ok:
        raise AdmissionError(code)


def real_private_path(path, *, directory=False, exists=True):
    path = Path(path)
    require(path.is_absolute() and path != Path('/') and '..' not in path.parts,
            'INVALID_PRIVATE_PATH')
    cursor = Path('/')
    for part in path.parts[1:]:
        cursor = cursor / part
        require(not cursor.is_symlink(), 'LINKED_PRIVATE_PATH')
    if exists:
        require(path.is_dir() if directory else path.is_file(), 'MISSING_PRIVATE_INPUT')
    return path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for part in iter(lambda: source.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def backup_identity(path):
    path = real_private_path(path)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and 16 <= before.st_size <= BACKUP_MAX, 'INVALID_LOGICAL_BACKUP')
    with path.open('rb') as source:
        require(source.read(5) == b'PGDMP', 'CUSTOM_LOGICAL_BACKUP_REQUIRED')
    result = {'bytes': before.st_size, 'sha256': digest(path)}
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            'BACKUP_CHANGED_DURING_VERIFICATION')
    return result


def select_destination(rows, *, empty_map=1):
    """Read-only saved-map admission. Never substitute Atlas for a saved map."""
    require(type(rows) is list and len(rows) <= 64, 'INVALID_CHARACTER_INVENTORY')
    if not rows:
        require(empty_map == 1, 'EMPTY_PROFILE_ATLAS_ONLY')
        return {'map_id': 1, 'map_port': 7001, 'character_count': 0,
                'saved_character_available': False, 'selection_authority': 'explicit_empty_profile_atlas'}
    # One local-development account and character are admitted. The source
    # TestClient chooses its actual name; imported THORHERO is also preserved.
    require(len(rows) == 1, 'ONE_ACCEPTED_CHARACTER_REQUIRED')
    row = rows[0]
    require(type(row) is dict and set(row) == {'containerid', 'authname', 'name',
                'authid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'}, 'INVALID_CHARACTER_FIELDS')
    require(type(row['containerid']) is int and row['containerid'] == 1
            and row['authname'] == 'COHLOCAL'
            and type(row['name']) is str and re.fullmatch(r'[A-Za-z0-9 _.-]{1,63}', row['name'])
            and type(row['authid']) is int and 0 < row['authid'] <= 0xffffffff,
            'CHARACTER_IDENTITY_OUTSIDE_ACCEPTED_SCOPE')
    target = row['staticmapid']
    require(type(target) is int and target in (1, 5), 'UNSUPPORTED_SAVED_DESTINATION')
    require(row['mapid'] is None or type(row['mapid']) is int and row['mapid'] == target,
            'INCONSISTENT_SAVED_DESTINATION')
    require(all(type(row[k]) in (int, float) and math.isfinite(row[k]) and abs(row[k]) <= 1e6
                for k in ('posx', 'posy', 'posz')), 'INVALID_SAVED_POSITION')
    return {'map_id': target, 'map_port': {1: 7001, 5: 7003}[target],
            'character_count': 1, 'saved_character_available': True,
            'selection_authority': 'preserved_postgresql_ents_staticmapid'}


def ready_document(args, destination, *, assets_sha256, import_receipt_sha256):
    require(SESSION.fullmatch(args.session_id) and GENERATION.fullmatch(args.import_generation),
            'INVALID_RUN_IDENTITY')
    require(re.fullmatch(r'[0-9a-f]{64}', assets_sha256)
            and re.fullmatch(r'[0-9a-f]{64}', import_receipt_sha256), 'INVALID_INPUT_HASH')
    require(destination['map_id'] in (1, 5)
            and destination['map_port'] == {1: 7001, 5: 7003}[destination['map_id']],
            'INVALID_READY_DESTINATION')
    return {'format': FORMAT, 'app_id': APP_ID, 'type': 'server_ready',
            'session_id': args.session_id, 'import_generation': args.import_generation,
            'assets_manifest_sha256': assets_sha256, 'import_receipt_sha256': import_receipt_sha256,
            'db_address': '127.0.0.1', 'db_port': 7000, 'map_address': '127.0.0.1',
            'map_port': destination['map_port'], 'map_id': destination['map_id'],
            'account': 'COHLOCAL', 'local_fake_auth': True, 'endpoint_policy': 'owned_loopback_only',
            'saved_character_available': destination['saved_character_available'],
            'character_count': destination['character_count'],
            'selection_authority': destination['selection_authority'],
            'native_client_started': False, 'conventional_client_started': False,
            'encrypted_authentication_verified': False, 'native_world_entry_verified': False,
            'observed_utc_ms': int(time.time() * 1000), 'heartbeat_max_age_ms': 15000}


def load_guest_modules(directory):
    """Only the manifest-verified donor modules may implement retained behavior."""
    global base, startup, character, zoning, login
    directory = real_private_path(directory, directory=True)
    for name in ('diagnostic.py', 'client_startup_diagnostic.py', 'local_character_server.py',
                 'character_zoning.py', 'local_login_server.py'):
        real_private_path(directory / name)
    sys.path.insert(0, str(directory))
    import diagnostic
    import client_startup_diagnostic
    import local_character_server
    import character_zoning
    import local_login_server
    base, startup = diagnostic, client_startup_diagnostic
    character, zoning, login = local_character_server, character_zoning, local_login_server


def runtime_classes():
    require(base is not None, 'GUEST_MODULES_NOT_LOADED')

    class Context(base.Context):
        """Retain private captures for parser use, expose no process/SQL output."""
        def __init__(self, args):
            super().__init__(args.state, args.timeout_seconds)
            self.session_id = args.session_id
            self.public_events = 0
            self.log_root = None

        log_paths = character.game.GameContext.log_paths

        def start(self, label, argv, *, env=None, input_text=None, cleanup=False):
            if not cleanup:
                self.check()
            # Retained map startup can use up to 160 actual status queries.
            # Match the accepted character-session finite child inventory.
            require(len(self.children) < 512, 'PROCESS_BUDGET_EXCEEDED')
            child = base.OwnedProcess(label, argv, env or os.environ.copy(), input_text)
            self.children.append(child)
            return child

        def event(self, kind, **fields):
            if kind == 'log':
                return
            self.public_events += 1
            require(self.public_events <= 20000, 'EVENT_BUDGET_EXCEEDED')
            value = {'type': 'stage', 'stage': self.stage_name[:100],
                     'session_id': self.session_id, 'time_utc': base.utc()}
            if fields.get('status') in ('running', 'passed', 'failed'):
                value['status'] = fields['status']
            # Library messages are fixed progress descriptions. Drop arbitrary
            # evidence and all child output, account IDs, cookies, and SQL rows.
            if kind == 'stage' and isinstance(fields.get('message'), str):
                value['message'] = base.redact(fields['message'], self.secrets)[:200]
            print(json.dumps(value, separators=(',', ':')), flush=True)

        def record(self, child, *, refresh=False):
            receipt = {'label': child.label, 'elapsed_seconds': round(time.monotonic() - child.started, 3),
                       'exit_code': child.process.poll(), 'forced_stop': child.forced_stop,
                       'output_capture_closed': not child.reader.is_alive(),
                       'input_closed': not child.writer.is_alive()}
            if child.recorded is None:
                self.report['processes'].append(receipt)
                child.recorded = receipt
            else:
                child.recorded.update(receipt)
            # Existing parsers need complete bounded output, but it is never
            # inserted into public reports or emitted on stdout.
            return dict(receipt, output=base.redact(child.text(), self.secrets)[-16384:])

    class Server(zoning.LocalCharacterZoningServer):
        requires_saved_character = False

        def initialize(self):
            # LocalLogin initializes only the private compatibility schema.
            # It neither creates an account/character nor starts a game client.
            # On first import the compatibility schema is supplied by PGDMP.
            self.initialize_private_profile()
            self.destination = self.read_destination()
            self.active_map_id = self.destination['map_id']
            self.creation_report['map_id'] = self.active_map_id
            self.creation_report['server_only'] = True

        def initialize_private_profile(self):
            d = self.owner
            self.ctx.stage('persistent_server_profile')
            self.payloads()
            real_private_path(self.profile, directory=True, exists=False)
            marker = self.profile / 'profile.json'
            if self.profile.exists():
                require(self.profile.is_dir(), 'INVALID_PROFILE_DIRECTORY')
                record = login.profile_record(marker)
                reused = record['initialized']
            else:
                self.profile.mkdir(mode=0o700)
                base.private_write(marker, json.dumps(dict(login.PROFILE_IDENTITY, initialized=False)) + '\n')
                reused = False
            d.pgdata = self.profile / 'pgdata'
            d.socket_dir = base.private_dir(self.profile / 'socket')
            real_private_path(d.pgdata, directory=True, exists=False)
            credentials_path = self.profile / 'credentials.json'
            real_private_path(credentials_path, exists=False)
            if credentials_path.exists():
                require(credentials_path.stat().st_nlink == 1 and credentials_path.stat().st_size <= 4096,
                        'INVALID_PROFILE_CREDENTIALS')
                credentials = json.loads(credentials_path.read_text())
                require(type(credentials) is dict and set(credentials) == {'cohdiag_admin', 'cohtest'}
                        and all(type(v) is str and re.fullmatch(r'[0-9a-f]{64}', v)
                                for v in credentials.values()), 'INVALID_PROFILE_CREDENTIALS')
            else:
                require(not d.pgdata.exists() and not reused, 'MISSING_PROFILE_CREDENTIALS')
                credentials = {role: secrets.token_hex(32) for role in ('cohdiag_admin', 'cohtest')}
                base.private_write(credentials_path, json.dumps(credentials) + '\n')
            credentials_path.chmod(0o600)
            d.credentials = credentials
            self.ctx.secrets.extend(credentials.values())
            for name in ('initdb', 'postgres', 'pg_ctl', 'psql', 'pg_restore'):
                base.arm64_elf(d.args.pg_bin / name)
            if not d.pgdata.exists():
                require(not reused, 'MISSING_INITIALIZED_CLUSTER')
                require(len(list(self.profile.glob('init-pending-*'))) < 8, 'TOO_MANY_INTERRUPTED_INITIALIZATIONS')
                pending = self.profile / ('init-pending-' + secrets.token_hex(8))
                password = self.profile / 'init-password'
                base.private_write(password, credentials['cohdiag_admin'] + '\n')
                try:
                    self.ctx.run('native-initdb', [d.pgtool('initdb'), '-D', pending, '-U', 'cohdiag_admin',
                        '--pwfile', password, '--auth-local=scram-sha-256', '--auth-host=scram-sha-256',
                        '--encoding=UTF8', '--locale=C', '-c', 'shared_memory_type=mmap',
                        '-c', 'dynamic_shared_memory_type=mmap'], timeout=90, env=d.base_env)
                    pending.rename(d.pgdata)
                finally:
                    password.unlink(missing_ok=True)
            require((d.pgdata / 'PG_VERSION').is_file(), 'INCOMPLETE_OWNED_CLUSTER')
            status = self.ctx.run('native-cluster-status', [d.pgtool('pg_ctl'), '-D', d.pgdata, 'status'],
                                  check=False, env=d.base_env)
            require(status['exit_code'] == 3, 'PROFILE_ALREADY_RUNNING_OR_UNREADABLE')
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                d.port = listener.getsockname()[1]
            d.database = login.DATABASE
            d.database_created = False  # Persistent profile is never fixture cleanup.
            self.report.update(profile_reused=reused, database_preserved_by_policy=True)
            d.start_postgres('postgres_native_combined')
            names = self.sql("SELECT datname FROM pg_database WHERE datname NOT IN ('postgres','template0','template1') ORDER BY datname;")
            require(names in ('', login.DATABASE), 'UNEXPECTED_PRIVATE_DATABASE')
            role = self.sql("SELECT count(*) FROM pg_roles WHERE rolname='cohtest';")
            if role == '0':
                require(not reused, 'MISSING_INITIALIZED_ROLE')
                self.sql("CREATE ROLE cohtest LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '"
                         + credentials['cohtest'] + "';")
            require(self.sql("SELECT (NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication)::int FROM pg_roles WHERE rolname='cohtest';") == '1',
                    'UNEXPECTED_ROLE_PRIVILEGES')
            if names == '':
                require(not reused, 'MISSING_INITIALIZED_DATABASE')
                self.sql('CREATE DATABASE "' + login.DATABASE + '" OWNER cohtest;')
            require(self.sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='"
                             + login.DATABASE + "';") == 'cohtest', 'UNEXPECTED_DATABASE_OWNER')
            if not reused:
                self.sql('REVOKE ALL ON DATABASE ' + login.DATABASE + ' FROM PUBLIC;')
                self.sql('ALTER DATABASE ' + login.DATABASE + ' SET search_path=dbo,pg_catalog;')
                self.sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC;', game=True)
                if d.args.logical_backup is not None:
                    self.restore_first_profile(d.args.logical_backup)
                else:
                    self.sql((d.args.assets / '001-coh-compat.sql').read_text(), game=True)
            elif d.args.logical_backup is not None:
                imported = self.profile / 'logical-import.json'
                require(imported.is_file() and not imported.is_symlink() and imported.stat().st_size <= 4096
                        and json.loads(imported.read_text()).get('backup') == backup_identity(d.args.logical_backup),
                        'REFUSING_REPLACEMENT_OF_INITIALIZED_PROFILE')
            require(self.sql("SELECT current_user || '|' || max(version) FROM coh_meta.schema_version;", game=True)
                    == 'cohtest|2', 'COMPATIBILITY_SCHEMA_IDENTITY_DIFFERS')
            if not reused and d.args.provision_test_character and d.args.logical_backup is None:
                base.private_write(self.profile / 'provision-requested.json',
                                   json.dumps({'format': 1, 'app_id': APP_ID}) + '\n')
            base.private_write(marker, json.dumps(dict(login.PROFILE_IDENTITY, initialized=True)) + '\n')
            self.report['profile_initialized'] = True
            self.ctx.passed(profile_initialized=True, profile_reused=reused)

        def restore_first_profile(self, backup):
            d = self.owner
            identity = backup_identity(backup)
            # A failed pg_restore transaction leaves no committed tables. A
            # completed import with its receipt is never repeated. If power
            # fails between PostgreSQL commit and receipt publication, retain
            # the nonempty database and require manual review; do not overwrite.
            marker = self.profile / 'logical-import.json'
            if marker.exists():
                require(not marker.is_symlink() and marker.stat().st_size <= 4096
                        and json.loads(marker.read_text()) == {'format': 1, 'backup': identity},
                        'LOGICAL_IMPORT_IDENTITY_DIFFERS')
                return
            count = self.sql("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%';", game=True)
            require(count == '0', 'LOGICAL_IMPORT_REQUIRES_EMPTY_OWNED_DATABASE')
            environment = dict(d.base_env, PGPASSWORD=d.credentials['cohtest'], PGCONNECT_TIMEOUT='5')
            self.ctx.stage('logical_profile_import')
            self.ctx.run('native-logical-restore', [d.pgtool('pg_restore'), '-h', str(d.socket_dir),
                '-p', str(d.port), '-U', 'cohtest', '-d', login.DATABASE,
                '--no-owner', '--no-privileges', '--exit-on-error', '--single-transaction',
                '--schema=dbo', '--schema=coh_meta', str(backup)],
                timeout=180, env=environment)
            require(backup_identity(backup) == identity, 'BACKUP_CHANGED_DURING_RESTORE')
            base.private_write(marker, json.dumps({'format': 1, 'backup': identity}) + '\n')
            self.ctx.passed(logical_backup_restored=True, original_profile_modified=False)

        def read_destination(self):
            presence = self.sql("SELECT CASE WHEN to_regclass('dbo.ents') IS NULL THEN 'missing' ELSE 'present' END;", game=True)
            require(presence in ('missing', 'present'), 'INVALID_CHARACTER_TABLE_PRESENCE')
            rows = [] if presence == 'missing' else self.sql_rows('ents',
                ('containerid', 'authname', 'name', 'authid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'),
                ('containerid',))
            return select_destination(rows)

        def capture_baseline(self):
            current = self.read_destination()
            require(current == self.destination, 'SAVED_DESTINATION_CHANGED_DURING_STARTUP')
            self.startup_preparation_map_id = self.active_map_id = current['map_id']

        def initial_map_preparation(self):
            self.qualify_monorail_preparation()
            self.capture_baseline()
            require(self.active_map_id != 5 or self.monorail_enabled(), 'SAVED_KINGS_ROW_REQUIRES_VERIFIED_ZONE_PACKAGE')
            return self.active_map_id

        def provision_if_requested(self):
            if not self.owner.args.provision_test_character:
                return
            require(self.owner.args.logical_backup is None, 'IMPORTED_PROFILE_PROVISIONING_FORBIDDEN')
            marker = self.profile / 'provision-complete.json'
            requested = self.profile / 'provision-requested.json'
            if marker.exists():
                require(not marker.is_symlink() and marker.stat().st_size <= 4096,
                        'INVALID_PROVISION_RECEIPT')
                self.provision = json.loads(marker.read_text())
                require(self.provision.get('format') == 1 and self.provision.get('app_id') == APP_ID
                        and self.provision.get('committed_sql_verified') is True
                        and self.provision.get('helper_reaped') is True
                        and self.provision.get('source_helper_used') is True
                        and self.provision.get('native_character_creation_verified') is False
                        and self.provision.get('implementation') == 'unchanged_source_TestClientCreate_bridge'
                        and re.fullmatch(r'[0-9a-f]{64}', self.provision.get('snapshot_sha256', '')),
                        'INVALID_PROVISION_RECEIPT')
                require(self.destination['saved_character_available'], 'PROVISIONED_CHARACTER_MISSING')
                return
            require(requested.is_file() and not requested.is_symlink() and requested.stat().st_size <= 4096
                    and json.loads(requested.read_text()) == {'format': 1, 'app_id': APP_ID},
                    'EXISTING_PROFILE_PROVISIONING_FORBIDDEN')
            require(not self.destination['saved_character_available'],
                    'INTERRUPTED_PROVISION_REQUIRES_REVIEW')
            require(self.sql("SELECT dbo.coh_container_high_water('dbo.ents'::regclass);", game=True) == '0',
                    'PREVIOUS_CHARACTER_ALLOCATION_FORBIDS_PROVISION')
            helper = Provisioner(self)
            self.owner.provisioner = helper
            session = helper.create_character()
            helper.live_currency(session)
            snapshot = helper.logout(session, 'first', 1)
            require(session.child.process.poll() is not None and not session.child.reader.is_alive()
                    and not session.child.writer.is_alive(), 'PROVISION_HELPER_NOT_REAPED')
            self.destination = self.read_destination()
            require(self.destination['saved_character_available'] and self.destination['map_id'] == 1,
                    'PROVISIONED_SAVED_CHARACTER_NOT_VERIFIED')
            self.provision = {'format': 1, 'app_id': APP_ID,
                'implementation': 'unchanged_source_TestClientCreate_bridge',
                'committed_sql_verified': True, 'helper_reaped': True,
                'native_character_creation_verified': False, 'source_helper_used': True,
                'snapshot_sha256': hashlib.sha256(json.dumps(snapshot, sort_keys=True,
                    separators=(',', ':')).encode()).hexdigest()}
            base.private_write(marker, json.dumps(self.provision) + '\n')
            # Account/cookie-bearing source-helper captures stay out of every
            # export and are removed after their hashes and save proof exist.
            for helper_session in helper.sessions:
                shutil.rmtree(helper_session.root)

        def start(self):
            # Skip LocalCharacterServer.start's graphical-character evidence;
            # retain its original server startup, preparation and native gates.
            login.LocalLoginServer.start(self)
            self.capture_baseline()
            self.start_map()
            self.provision_if_requested()

        def prepare_runtime(self):
            character.LocalCharacterServer.prepare_runtime(self)
            self.qualify_monorail_preparation()
            require(self.manual_atlas_startup is not None,
                    'MANUAL_SERVER_DBSERVER_SUPPLEMENT_REQUIRED')

        def persist_startup_observation(self):
            # The inherited implementation serializes all private context
            # observations. Export only the adapter's curated numeric receipt.
            pass

    class Provisioner:
        # These are the unchanged accepted source-helper control and SQL proof
        # functions. No serialized or mocked character is inserted by this adapter.
        game_module = character.game
        wait = game_module.GameDiagnostic.wait
        game_environment = game_module.GameDiagnostic.game_environment
        inventory = game_module.GameDiagnostic.inventory
        new_client = game_module.GameDiagnostic.new_client
        create_character = game_module.GameDiagnostic.create_character
        observe_client_listeners = game_module.GameDiagnostic.observe_client_listeners
        live_currency = game_module.GameDiagnostic.live_currency
        character_status = game_module.GameDiagnostic.character_status
        snapshot = game_module.GameDiagnostic.snapshot
        logout = game_module.GameDiagnostic.logout
        clean_logs = game_module.GameDiagnostic.clean_logs

        def __init__(self, server):
            self.server, self.ctx = server, server.ctx
            owner = server.owner
            self.root, self.runtime, self.args = owner.root, server.runtime, owner.args
            self.wine_env, self.package, self.schema = owner.wine_env, server.map_package, server.schema
            self.ctx.log_root = self.runtime
            self.game_listener_enabled = self.game_module.game_listener_contract(self.package) is not None
            require(self.game_listener_enabled, 'PROVISION_HELPER_LOOPBACK_CONTRACT_REQUIRED')
            self.loopback_enabled = False
            self.completed_logout = False
            self.sessions, self.snapshots = [], {}
            self.services = [server.process, server.map_process]
            self.game = {'account': 'COHLOCAL', 'character_samples': [],
                         'client_listener_observations': {}, 'sessions': {}}

        def sample_map_progress(self, reason):
            # Map readiness was independently proved by the retained completed
            # tick plus DbServer status gates before the helper is admitted.
            return self.server.sample_progress()

        def health(self):
            self.ctx.check()
            self.server.health()

        def query(self, arguments, label):
            return self.server.query(arguments, label)

        def sql_rows(self, *args, **kwargs):
            return self.server.sql_rows(*args, **kwargs)

    class Owner(base.Diagnostic):
        def __init__(self, args, context):
            super().__init__(args, context)
            self.work = None
            self.client = None
            self.server = Server(self)
            self.ready_path = args.state / 'server-ready.json'
            self.ready_receipt = None
            self.provisioner = None

        # DbServer's accepted helpers read complete bounded stdout, unlike the
        # short generic SQL report tail. No output is logged by our Context.
        def sql(self, text, *, game=False, cleanup=False):
            base.Diagnostic.sql(self, text, game=game, cleanup=cleanup)
            return self.ctx.children[-1].text().strip()

        def initialize(self):
            self.ctx.stage('server_only_input_admission')
            require(platform.machine().lower() in ('aarch64', 'arm64'), 'ARM64_GUEST_REQUIRED')
            require(os.geteuid() == 1000, 'PROOT_UID_1000_REQUIRED')
            self.ctx.report['asset_sha256'] = startup.verify_assets(self.args.assets)
            for name in ('wine', 'wineserver'):
                base.arm64_elf(getattr(self.args, name))
            identity = startup.import_identity(self.args.game_data)
            require(identity['generation'] == self.args.import_generation, 'IMPORT_GENERATION_DIFFERS')
            self.ctx.report['import_identity'] = identity
            self.ctx.passed(import_generation_verified=True)
            self.ctx.stage('prepare_private_server_inputs')
            self.work, receipt = startup.prepare_worktree(self.root, self.args.game_data,
                                                          self.args.assets, identity, self.ctx)
            self.ctx.report['client_worktree'] = receipt
            character.avatar.install(self.work, self.args.assets, self.ctx)
            character.world.install(self.work, self.args.assets, self.ctx)
            self.ctx.passed(original_game_data_preserved=True)
            self.server.initialize()

        def execute(self):
            self.initialize()
            # This owns a private headless X display required by retained Wine
            # registration/MSI; no CityOfHeroes.exe or client-launcher executes.
            self.start_wine()
            self.mark_wine_ready()
            self.server.start()
            self.server.health()
            require(self.server.report.get('server_ready') is True
                    and self.server.creation_report.get('map_ready') is True,
                    'NATIVE_SERVER_READINESS_NOT_PROVED')
            config = self.server.config.read_text()
            require(re.search(r'(?im)^\s*UseFakeAuth\s+1\s*$', config) is not None,
                    'LOCAL_FAKE_AUTH_POLICY_REQUIRED')
            self.ready_receipt = ready_document(self.args, self.server.destination,
                assets_sha256=base.file_hash(self.args.assets / 'client-manifest.json'),
                import_receipt_sha256=self.ctx.report['import_identity']['receipt_sha256'])
            version = self.server.map_package.get('client_version')
            require(type(version) is str and version.isascii() and 0 < len(version) <= 128
                    and all(32 <= ord(ch) <= 126 for ch in version), 'INVALID_SERVER_CLIENT_VERSION')
            self.ready_receipt['client_version'] = version
            self.ready_receipt['source_helper_used'] = hasattr(self.server, 'provision')
            self.ready_receipt['native_character_creation_verified'] = False
            self.publish_ready(announce=True)
            self.ctx.stage('server_running_manual_native_client')
            next_heartbeat = 0
            while True:
                self.ctx.check()
                self.server.health()
                require(self.xserver is not None and self.xserver.process.poll() is None,
                        'OWNED_HEADLESS_DISPLAY_EXITED')
                if time.monotonic() >= next_heartbeat:
                    current = self.server.sample_progress(force=True)
                    require(self.server.live_progress(current), 'MAP_DISPATCH_NOT_FRESH')
                    self.publish_ready()
                    next_heartbeat = time.monotonic() + 5
                time.sleep(.25)

        def publish_ready(self, *, announce=False):
            self.ready_receipt['observed_utc_ms'] = int(time.time() * 1000)
            base.private_write(self.ready_path, json.dumps(self.ready_receipt) + '\n')
            if announce:
                print(json.dumps(self.ready_receipt, separators=(',', ':')), flush=True)

        def cleanup(self):
            self.ready_path.unlink(missing_ok=True)
            failures = super().cleanup()
            if self.provisioner is not None:
                for helper_session in self.provisioner.sessions:
                    if helper_session.root.exists():
                        with contextlib.suppress(OSError):
                            shutil.rmtree(helper_session.root)
            try:
                self.server.cleanup_config()
            except Exception:
                failures.append('Private runtime configuration cleanup failed')
            return failures

    return Context, Owner


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guest-modules', type=Path, default=Path('/opt/coh'))
    parser.add_argument('--state', type=Path, default=Path('/state'))
    parser.add_argument('--assets', type=Path, default=Path('/opt/coh'))
    parser.add_argument('--game-data', type=Path, default=Path('/game/data'))
    parser.add_argument('--pg-bin', type=Path, default=Path('/opt/coh/pgsql/bin'))
    parser.add_argument('--wine', type=Path, default=Path('/opt/wine/bin/wine'))
    parser.add_argument('--wineserver', type=Path, default=Path('/opt/wine/bin/wineserver'))
    parser.add_argument('--xserver', type=Path, default=Path('/usr/bin/Xtigervnc'))
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--import-generation', required=True)
    parser.add_argument('--logical-backup', type=Path)
    parser.add_argument('--provision-test-character', action='store_true',
                        help='Fresh empty owned profile only: create/save one real character using source TestClient')
    parser.add_argument('--timeout-seconds', type=int, default=21600)
    args = parser.parse_args(argv)
    require(SESSION.fullmatch(args.session_id) and GENERATION.fullmatch(args.import_generation), 'INVALID_RUN_IDENTITY')
    require(600 <= args.timeout_seconds <= 21600, 'INVALID_RUNTIME_DURATION')
    require(args.guest_modules == args.assets, 'GUEST_MODULES_MUST_BE_VERIFIED_ASSETS')
    for name in ('guest_modules', 'state', 'assets', 'game_data', 'pg_bin', 'wine', 'wineserver', 'xserver'):
        real_private_path(getattr(args, name), directory=name in ('guest_modules', 'state', 'assets', 'game_data', 'pg_bin'),
                          exists=name != 'state')
    if args.logical_backup is not None:
        require(not args.provision_test_character, 'IMPORTED_PROFILE_PROVISIONING_FORBIDDEN')
        backup_identity(args.logical_backup)
    return args


def main(argv=None):
    os.umask(0o077)
    owner = context = args = None
    result = {'format': FORMAT, 'app_id': APP_ID, 'server_only': True,
              'conventional_client_started': False, 'native_client_started_by_guest': False,
              'encrypted_authentication_verified': False, 'native_world_entry_verified': False,
              'original_profile_modified': False, 'status': 'failed'}
    exit_code = 1
    try:
        args = arguments(argv)
        args.state.mkdir(mode=0o700, parents=True, exist_ok=True)
        load_guest_modules(args.guest_modules)
        Context, Owner = runtime_classes()
        context = Context(args)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
        owner = Owner(args, context)
        # Native endpoint admission is always tied to this running owner.
        owner.ready_path.unlink(missing_ok=True)
        owner.execute()
    except BaseException as exc:
        cancelled = context is not None and isinstance(exc, base.Cancelled)
        result['status'] = 'stopped' if cancelled else 'failed'
        result['failure_code'] = None if cancelled else (str(exc) if isinstance(exc, AdmissionError)
                                                        else 'RETAINED_GUEST_DEPENDENCY_FAILED')
        exit_code = 0 if cancelled else 1
    finally:
        cleanup = []
        if owner is not None:
            try:
                cleanup = owner.cleanup()
            except Exception:
                cleanup = ['Owned cleanup did not complete']
            result['cleanup'] = owner.cleanup_status
            result['profile_preserved'] = True
        result['cleanup_complete'] = owner is not None and not cleanup
        if cleanup:
            result['status'] = 'cleanup_failed'
            result['failure_code'] = 'OWNED_CLEANUP_INCOMPLETE'
            exit_code = 1
        if context is not None:
            result['last_stage'] = context.stage_name
            result['session_id'] = args.session_id
            result['import_generation'] = args.import_generation
            result['processes'] = context.report['processes']
            if owner is not None and owner.ready_receipt is not None:
                result['server_readiness'] = owner.ready_receipt
            raw = json.dumps(result, indent=2) + '\n'
            if len(raw.encode()) <= 256 * 1024:
                with contextlib.suppress(Exception):
                    base.private_write(args.state / 'latest-report.json', raw)
        print(json.dumps({'type': 'server_stopped', 'status': result['status'],
                          'failure_code': result.get('failure_code'),
                          'cleanup_complete': result['cleanup_complete']}, separators=(',', ':')), flush=True)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
