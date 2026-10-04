#!/usr/bin/env python3
"""Persistent private PostgreSQL and the exact qualified loopback DbServer.

This is a launcher profile, not a disposable fixture. Nothing in this module
runs a stock SQL probe, drops a database, or starts a MapServer.
"""
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import socket
import stat
import tarfile
import time

import diagnostic as base
import dbserver_diagnostic as dbserver
import game_diagnostic as game
import game_hang_evidence as dispatch

require = base.require
PROFILE = 'android-local-login'
DATABASE = 'coh_local_android'
ACCOUNT = 'COHLOCAL'
PROFILE_IDENTITY = {'format': 1, 'purpose': 'persistent_local_login', 'profile': PROFILE,
    'database': DATABASE, 'source_commit': '0b75ade0c801735e10c5798f641948a45cc50488',
    'data_commit': 'd51533ec8e6a9cf726b9214968077a05fdcf19f3',
    'package_manifest_sha256': dbserver.DEVICE_PACKAGE_MANIFEST,
    'schema_manifest_sha256': dbserver.DEVICE_SCHEMA_MANIFEST}


def extract_regular(archive_path, destination):
    """Canonical qualified tar payloads only; no path/link or size surprises."""
    require(not destination.exists() and not destination.is_symlink(), 'Payload extraction target already exists')
    destination.mkdir(mode=0o700)
    with tarfile.open(archive_path, 'r:gz') as archive:
        members = archive.getmembers()
        require(0 < len(members) <= 4096 and sum(m.size for m in members) <= 256*1024*1024,
                'Server payload archive exceeded bounds')
        names = [m.name for m in members]
        require(names == sorted(set(names)) and len({n.casefold() for n in names}) == len(names),
                'Server payload has unordered or colliding paths')
        for member in members:
            name = PurePosixPath(member.name)
            require(name.parts and not name.is_absolute() and name.as_posix() == member.name
                    and all(p not in ('', '.', '..') for p in name.parts)
                    and '\\' not in member.name and '\x00' not in member.name,
                    'Unsafe server archive path')
            require(member.isfile() and 0 <= member.size <= 200*1024*1024
                    and member.mode == 0o644 and member.uid == member.gid == member.mtime == 0
                    and member.uname == member.gname == '' and not member.linkname and not member.pax_headers,
                    'Server payload archive metadata differs')
            target = destination / member.name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, 1024*1024)
            target.chmod(0o600)


def profile_record(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_nlink == 1
            and 0 < path.stat().st_size <= 4096, 'Invalid persistent profile marker')
    record = json.loads(path.read_text())
    require(type(record) is dict and set(record) == set(PROFILE_IDENTITY) | {'initialized'}
            and all(type(record[k]) is type(v) and record[k] == v for k, v in PROFILE_IDENTITY.items())
            and type(record['initialized']) is bool, 'Persistent profile identity differs')
    return record


class LocalLoginServer:
    require_empty_account = True
    def __init__(self, owner):
        self.owner, self.ctx = owner, owner.ctx
        self.profile = owner.root / PROFILE
        self.process = None
        self.runtime = None
        self.report = {'profile': PROFILE, 'account': ACCOUNT, 'database': DATABASE,
            'session_id': owner.args.session_id, 'database_preserved': False,
            'character_list_sent': False, 'character_selection_visual_validated': False,
            'mapserver_started': False, 'server_listener_policy': 'loopback_only'}
        self.ctx.report['local_login'] = self.report
        self.schema = None
        self.last_log_check = 0

    def sql(self, text, *, game=False, cleanup=False):
        require(not re.search(r'\bDROP\s+DATABASE\b', text, re.I), 'Persistent profile forbids database deletion')
        return self.owner.sql(text, game=game, cleanup=cleanup)

    sql_hash = dbserver.DbServerDiagnostic.sql_hash
    schema_snapshot = dbserver.DbServerDiagnostic.schema_snapshot

    def payloads(self):
        destination = self.owner.root / ('local-login-payloads-' + dbserver.DEVICE_PACKAGE_MANIFEST[:16])
        require(not destination.is_symlink(), 'Linked server payload refused')
        if not destination.exists():
            pending = self.owner.root / ('local-login-payload-pending-' + secrets.token_hex(6))
            pending.mkdir(mode=0o700)
            try:
                extract_regular(self.owner.args.assets / 'dbserver-package.tar.gz', pending / 'package')
                extract_regular(self.owner.args.assets / 'dbserver-schema.tar.gz', pending / 'schema')
                dbserver.verify_device_payload(pending / 'package', pending / 'schema')
                dbserver.verify_inputs(pending / 'package', pending / 'schema')
                pending.rename(destination)
            finally:
                if pending.exists(): shutil.rmtree(pending)
        self.package_dir, self.schema_dir = destination / 'package', destination / 'schema'
        provenance = dbserver.verify_device_payload(self.package_dir, self.schema_dir)
        self.package, self.schema = dbserver.verify_inputs(self.package_dir, self.schema_dir)
        self.report['inputs'] = provenance

    def initialize(self):
        d = self.owner
        self.ctx.stage('persistent_server_profile')
        self.payloads()
        require(not self.profile.is_symlink(), 'Linked persistent profile refused')
        marker = self.profile / 'profile.json'
        if self.profile.exists():
            require(self.profile.is_dir(), 'Persistent profile is not a directory')
            record = profile_record(marker)
            reused = record['initialized']
        else:
            self.profile.mkdir(mode=0o700)
            record = dict(PROFILE_IDENTITY, initialized=False)
            base.private_write(marker, json.dumps(record) + '\n')
            reused = False
        d.pgdata = self.profile / 'pgdata'
        d.socket_dir = base.private_dir(self.profile / 'socket')
        require(not d.pgdata.is_symlink(), 'Linked persistent cluster refused')
        credentials_path = self.profile / 'credentials.json'
        require(not credentials_path.is_symlink(), 'Linked persistent credentials refused')
        if credentials_path.exists():
            require(credentials_path.is_file() and credentials_path.stat().st_nlink == 1
                    and credentials_path.stat().st_size <= 4096, 'Invalid persistent credentials')
            credentials = json.loads(credentials_path.read_text())
            require(set(credentials) == {'cohdiag_admin', 'cohtest'}
                    and all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) for v in credentials.values()),
                    'Invalid persistent credentials')
        else:
            require(not d.pgdata.exists() and not reused, 'Refusing cluster without owned credentials')
            credentials = {role: secrets.token_hex(32) for role in ('cohdiag_admin', 'cohtest')}
            base.private_write(credentials_path, json.dumps(credentials) + '\n')
        d.credentials = credentials
        self.ctx.secrets.extend(credentials.values())
        credentials_path.chmod(0o600)
        for name in ('initdb', 'postgres', 'pg_ctl', 'psql'): base.arm64_elf(d.args.pg_bin / name)
        if not d.pgdata.exists():
            require(not reused, 'Initialized persistent profile lost its cluster')
            require(len(list(self.profile.glob('init-pending-*'))) < 8, 'Too many interrupted cluster initializations')
            pending = self.profile / ('init-pending-' + secrets.token_hex(8))
            password = self.profile / 'init-password'
            base.private_write(password, credentials['cohdiag_admin'] + '\n')
            try:
                self.ctx.run('local-initdb', [d.pgtool('initdb'), '-D', pending, '-U', 'cohdiag_admin',
                    '--pwfile', password, '--auth-local=scram-sha-256', '--auth-host=scram-sha-256',
                    '--encoding=UTF8', '--locale=C', '-c', 'shared_memory_type=mmap',
                    '-c', 'dynamic_shared_memory_type=mmap'], timeout=90, env=d.base_env)
                pending.rename(d.pgdata)
            finally:
                password.unlink(missing_ok=True)
        require((d.pgdata / 'PG_VERSION').is_file(), 'Persistent cluster is incomplete')
        status = self.ctx.run('local-cluster-status', [d.pgtool('pg_ctl'), '-D', d.pgdata, 'status'],
                              check=False, env=d.base_env)
        require(status['exit_code'] == 3, 'Refusing an already running or unreadable persistent cluster')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); d.port = listener.getsockname()[1]
        d.database = DATABASE
        # Intentionally never enroll this database in diagnostic fixture cleanup.
        d.database_created = False
        self.report.update(profile_reused=reused, cluster_path=str(d.pgdata))
        self.ctx.passed(profile=PROFILE, profile_reused=reused, database_preserved_by_policy=True)
        d.start_postgres('postgres_local_login')
        self.ctx.report['postgres_started'] = True
        names = self.sql("SELECT datname FROM pg_database WHERE datname NOT IN ('postgres','template0','template1') ORDER BY datname;")
        require(names in ('', DATABASE), 'Persistent cluster contains an unexpected database')
        role = self.sql("SELECT count(*) FROM pg_roles WHERE rolname='cohtest';")
        if role == '0':
            require(not reused, 'Initialized persistent profile lost its database role')
            self.sql("CREATE ROLE cohtest LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '" + credentials['cohtest'] + "';")
        require(self.sql("SELECT (NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication)::int FROM pg_roles WHERE rolname='cohtest';") == '1',
                'Persistent database role gained privileged rights')
        if names == '':
            require(not reused, 'Initialized persistent profile lost its database')
            self.sql('CREATE DATABASE "' + DATABASE + '" OWNER cohtest;')
        if not reused:
            # Initialization is retriable at every statement boundary, including
            # cancellation immediately after CREATE DATABASE was committed.
            self.sql('REVOKE ALL ON DATABASE ' + DATABASE + ' FROM PUBLIC;')
            self.sql('ALTER DATABASE ' + DATABASE + ' SET search_path=dbo,pg_catalog;')
            self.sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC;', game=True)
        require(self.sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='" + DATABASE + "';") == 'cohtest',
                'Persistent database ownership differs')
        if not reused:
            self.sql((d.args.assets / '001-coh-compat.sql').read_text(), game=True)
        require(self.sql("SELECT current_user || '|' || max(version) FROM coh_meta.schema_version;", game=True) == 'cohtest|2',
                'Persistent compatibility migration identity/version differs')
        base.private_write(marker, json.dumps(dict(PROFILE_IDENTITY, initialized=True)) + '\n')
        self.report['profile_initialized'] = True

    def prepare_runtime(self):
        """Make a fresh owned server tree; subclasses may add game data here."""
        d = self.owner
        self.runtime = d.root / ('local-login-server-' + d.args.session_id)
        require(not self.runtime.exists() and not self.runtime.is_symlink(), 'Server session path already exists')
        self.runtime.mkdir(mode=0o700)
        (self.runtime / 'data').mkdir(mode=0o700); (self.runtime / 'tools').mkdir(mode=0o700)
        for name in self.package['variants']['normal']['files']:
            shutil.copyfile(self.package_dir / 'normal' / name, self.runtime / name)
        for name in self.schema['files']:
            target = self.runtime / name; target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(self.schema_dir / name, target)

    def start(self):
        d = self.owner
        self.ctx.stage('local_login_odbc')
        installer = d.wineprefix / 'drive_c/windows/syswow64/msiexec.exe'
        base.verify_pe32(installer)
        self.ctx.run('local-install-x86-psqlodbc', [d.args.wine, r'C:\windows\syswow64\msiexec.exe', '/i',
            base.windows_path(d.args.assets / 'psqlodbc_x86.msi'), '/qn', '/norestart'], timeout=150, env=d.wine_env)
        result = self.ctx.run('local-odbc-driver', [d.args.wine, base.windows_path(d.args.assets / 'runtime-probe.exe'),
            '--odbc-driver'], timeout=60, env=d.wine_env)
        driver = base.validate_odbc_driver(result['output'])
        self.ctx.report['odbc_driver'] = driver
        connection = ('Driver={' + driver['driver_name'] + '};Servername=127.0.0.1;Port=' + str(d.port)
            + ';Database=' + DATABASE + ';Username=cohtest;Password=' + d.credentials['cohtest']
            + ';SSLmode=disable;ByteaAsLongVarBinary=0;UseServerSidePrepare=0;')
        self.ctx.passed(**driver)
        self.ctx.stage('local_dbserver_startup')
        self.prepare_runtime()
        config = self.runtime / 'data/server/db/servers.cfg'
        base.private_write(config, game.game_config(config.read_text(), DATABASE, connection))
        self.config = config
        self.progress_path = self.runtime / 'coh-db-progress.bin'
        for port, protocol in ((6997, socket.SOCK_STREAM), (7000, socket.SOCK_DGRAM)):
            game.check_game_port(port, protocol)
        environment = dict(d.wine_env, COH_WINE_DB_FIXED_INPUTS='1', COH_WINE_DB_LOOPBACK_ONLY='1',
                           COH_WINE_DB_PROGRESS=base.windows_path(self.progress_path))
        environment = self.dbserver_environment(environment)
        self.process = self.ctx.start('local-dbserver', ['/usr/bin/env', '--chdir=' + str(self.runtime), d.args.wine,
            base.windows_path(self.runtime / 'DbServer.exe'), '-start', '0'], env=environment)
        self.ctx.report['server_started'] = True
        deadline, next_progress = min(self.ctx.deadline, time.monotonic() + 600), 0
        stages = self.package['wine_build_input']['dispatch_progress']['stages']
        endpoints = dbserver.loopback_expectations(self.package['wine_build_input']['normal_schema_listeners'])
        while True:
            self.ctx.check(); self.health()
            text = self.process.text()
            fixed = game.fixed_inputs_acknowledgement(self.process)
            loopback = game.loopback_acknowledgement(self.process, endpoints)
            startup_policy_ready = self.dbserver_startup_policy_ready(text)
            progress = None
            if fixed and loopback:
                try: progress = dispatch.read_dispatch_record(self.progress_path, stages)
                except (FileNotFoundError, dispatch.DispatchPublicationPending): pass
            if fixed and loopback and progress and progress['loop_count'] > 0 and startup_policy_ready:
                break
            require(time.monotonic() < deadline, 'Local DbServer startup timed out')
            if time.monotonic() >= next_progress:
                self.ctx.event('stage', status='running', message='Preparing local City of Heroes server')
                next_progress = time.monotonic() + 5
            time.sleep(.2)
        snapshot = self.schema_snapshot()
        self.report.update(server_ready=True, fixed_inputs=fixed, loopback_only=loopback,
                           dispatch_progress=progress, schema=snapshot)
        self.ctx.passed(local_dbserver_ready=True, mapserver_started=False, **snapshot)
        self.ctx.event('local_server_ready', session_id=d.args.session_id, profile=PROFILE, account=ACCOUNT)

    def dbserver_environment(self, environment):
        # A host environment cannot accidentally request a manual Atlas profile
        # for the stock persistent login service.
        environment.pop('COH_WINE_DB_MANUAL_ATLAS', None)
        return environment

    def dbserver_startup_policy_ready(self, console):
        return True

    def health(self):
        d = self.owner
        require(d.pg is not None and d.pg.process.poll() is None, 'Persistent PostgreSQL exited during login')
        if self.process is not None:
            require(self.process.process.poll() is None, 'Local DbServer exited during login')
            require(not self.process.overflow, 'Local DbServer output overflowed')

    def current_logs(self):
        paths = [] if self.runtime is None else sorted(self.runtime.rglob('*.log'))
        require(len(paths) <= 128, 'Local DbServer log count exceeded bound')
        total, records = 0, []
        for path in paths:
            require(path.is_file() and not path.is_symlink(), 'Linked local DbServer log refused')
            size = path.stat().st_size; total += size
            require(size <= 16*1024*1024 and total <= 64*1024*1024, 'Local DbServer logs exceeded bound')
            records.append((path.relative_to(self.runtime).as_posix(), path.read_text(errors='replace')))
        return records

    def collect(self, target):
        if self.process is not None:
            text = base.redact(self.process.text(), self.ctx.secrets)
            require(len(text.encode()) <= 2*1024*1024, 'Server console evidence exceeded bound')
            base.private_write(target / 'local-dbserver-console.txt', text)
        logs = self.current_logs()
        text = '\n'.join('\nFILE ' + name + '\n' + base.redact(value, self.ctx.secrets) for name, value in logs)
        require(len(text.encode()) <= 2*1024*1024, 'Server log evidence exceeded bound')
        if text: base.private_write(target / 'local-dbserver-logs.txt', text)

    def cleanup_config(self):
        if getattr(self, 'config', None) is not None:
            self.config.unlink(missing_ok=True)

    def login_evidence(self):
        """Prove this launch sent the list; visual receipt is reviewed separately."""
        logs = self.current_logs()
        # Buffering can expose a partial final line; only complete records count.
        complete = [(name, text[:text.rfind('\n') + 1]) for name, text in logs]
        debug = '\n'.join(text for name, text in complete if Path(name).name.casefold().startswith('debug_'))
        specs = '\n'.join(text for name, text in complete if Path(name).name.casefold().startswith('systemspecs_'))
        matches = re.findall(r'(?m)^\d{6} \d{2}:\d{2}:\d{2} -?\d+ 127\.0\.0\.1 successful login for "COHLOCAL" AuthID ([1-9][0-9]*) Cookie 0\s*$', debug)
        response = re.search(r'(?m)^\d{6} \d{2}:\d{2}:\d{2} -?\d+ IP,127\.0\.0\.1,AuthName,COHLOCAL,SystemSpecs,[^\r\n]*$', specs)
        if not matches or response is None: return None
        require(len(set(matches)) == 1, 'Local account login identity changed within the session')
        auth_id = int(matches[-1])
        require(auth_id <= 4294967295, 'Invalid local account auth identity')
        row = self.sql("SELECT containerid || '|' || authname FROM dbo.shardaccounts WHERE lower(authname)=lower('COHLOCAL') ORDER BY containerid;", game=True)
        require(row == str(auth_id) + '|' + ACCOUNT, 'Local account SQL identity differs from current login')
        count = self.sql('SELECT count(*) FROM dbo.ents WHERE authid=' + str(auth_id) + ';', game=True)
        require(re.fullmatch(r'[0-9]+', count) is not None, 'Invalid local account character count')
        require(not self.require_empty_account or count == '0', 'Local login milestone requires an empty character account')
        return {'auth_id': auth_id, 'account': ACCOUNT, 'character_count': int(count),
            'local_login_verified': True, 'local_account_verified': True,
            'character_list_sent': True, 'character_list_response_sent': True,
            'character_selection_visual_pending': True, 'character_selection_visual_validated': False,
            'evidence_scope': 'current_owned_dbserver_successful_login_and_post_send_system_specs_plus_sql',
            'log_paths': [name for name, _ in logs if Path(name).name.casefold().startswith(('debug_', 'systemspecs_'))]}
