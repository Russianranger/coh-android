#!/usr/bin/env python3
"""Run real PE32 DbServer persistence and accepted schema tests in owned PRoot.

This hosted milestone reuses the accepted ARM64 PostgreSQL/Wine lifecycle. It
does not establish Android execution, gameplay, or generated character saves.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import signal
import sys
import time

# Hosted runs bind the immutable, accepted lifecycle at /opt/coh. Local tests
# import the adjacent source; this extension never substitutes its own lifecycle.
sys.path.insert(0, '/opt/coh' if Path('/opt/coh/diagnostic.py').is_file()
                else str(Path(__file__).resolve().parent))
import diagnostic as base

require = base.require
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
COMMIT = re.compile(r'[0-9a-f]{40}\Z')
IDENTIFIER = re.compile(r'[a-z_][a-z0-9_]*\Z')
FIXTURE_MODES = ('initial', 'fail', 'exhaust', 'delete-fail', 'disconnect',
                 'verify', 'verify', 'verify', 'rebuild', 'verify-rebuilt',
                 'rebuild-fail', 'rebuild-fail-view', 'verify-rebuilt', 'verify-rebuilt')
FIXTURE_CHECKS = (
    'real 64-worker SQL FIFO and container serialization',
    'foreign-key removal before table creation and when constraint is absent',
    'multi-batch create and update with 512 child rows', 'ordered asynchronous read callback',
    '16 concurrent records and repeated same-record writes', 'Unicode and unsigned byte 255',
    'case-insensitive game cache and SQL name lookup', 'whole-save retry for 40001 and 40P01',
    'commit-time retry before acknowledgement', 'atomic parent/child deletion',
    'permanent failure rolls back all save batches', 'five-attempt retry limit without acknowledgement',
    'failed delete restores previously deleted child rows',
    'connection loss stops without replay or acknowledgement; in-flight write rolled back',
    'new-process container reload', 'clean PostgreSQL restart', 'WAL recovery of real saved containers',
    'real template reorder/add-column rebuild preserves high-water 9000',
    'inbound foreign keys and indexes survive table replacement',
    'failed data conversion and dependent-view rebuild preserve original table',
    'backup/restore reload through actual DbServer container reader')
FAILURE = re.compile(r'\b(?:fatal|assertion failed|SQL_ERROR|SQLERROR|PG_FIFO_FAILED|'
                     r'INVALID PARAMETER|Giving up|Bad output file|Error binding|'
                     r'SQLSTATE|ODBC error|SQL error)\b|^\s*ERROR[:\s]', re.I)
BENIGN_CATALOG_NOTICE = re.compile(
    r'(?:\d{6} \d{2}:\d{2}:\d{2} -?\d+ )?SQLERROR: -1 (?:'
    r'00000 NOTICE: (?:relation "(?:ents|ents2)" does not exist, skipping|'
    r'constraint "fk_ents2_leaguesid_leagues" of relation "ents2" does not exist, skipping|'
    r'constraint "fk_ents_teamupsid_teamups" of relation "ents" does not exist, skipping)|'
    r'42P07 NOTICE: relation "coh_[0-9a-f]{32}" already exists, skipping)')
LOG_LIMIT = 16 * 1024 * 1024
FIXED_INPUTS_ENV = 'COH_WINE_DB_FIXED_INPUTS'
FIXED_INPUTS_ACK = ('COH_WINE_DB_FIXED_INPUTS=1 active: directory monitoring disabled; '
                    'initial reads and lookup mode preserved')
FIXED_INPUTS_METADATA = {
    'environment_variable': FIXED_INPUTS_ENV, 'enabled_value': '1', 'disabled_by_default': True,
    'activation': 'before_first_folder_cache_create', 'watcher_registration': 'disabled',
    'notification_updates': 'disabled', 'initial_reads': 'preserved', 'lookup_mode': 'preserved',
    'startup_acknowledgement': FIXED_INPUTS_ACK, 'proves_generic_notification_fix': False}


def validate_fixed_inputs_metadata(value):
    require(isinstance(value, dict) and value == FIXED_INPUTS_METADATA
            and value.get('disabled_by_default') is True
            and value.get('proves_generic_notification_fix') is False,
            'DbServer fixed-input build contract differs')


def validate_fixed_inputs(output, enabled):
    markers = [line for line in output.splitlines() if FIXED_INPUTS_ENV in line]
    require(markers == ([FIXED_INPUTS_ACK] if enabled else []),
            'DbServer fixed-input startup acknowledgement differs from requested mode')
    return {'requested': enabled, 'startup_acknowledgement': FIXED_INPUTS_ACK if enabled else None}


def load_json(path, limit=32 * 1024 * 1024):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit,
            'Missing, linked or oversized manifest: ' + str(path))
    def unique(pairs):
        result = {}
        for name, value in pairs:
            require(name not in result, 'Duplicate manifest key: ' + name)
            result[name] = value
        return result
    value = json.loads(path.read_text(), object_pairs_hook=unique)
    require(isinstance(value, dict), 'Manifest must be an object')
    return value


def verify_inventory(root, files, *, manifest=None, binary=False):
    require(root.is_dir() and not root.is_symlink() and isinstance(files, dict)
            and 0 < len(files) <= 256, 'Invalid payload directory or inventory')
    seen, total = set(), 0
    for name, record in files.items():
        require(isinstance(name, str) and '\\' not in name and '\x00' not in name,
                'Invalid payload path')
        path = PurePosixPath(name)
        require(not path.is_absolute() and path.parts and all(p not in ('.', '..') for p in path.parts)
                and str(path) == name and name.casefold() not in seen, 'Unsafe or duplicate payload path')
        seen.add(name.casefold())
        if binary:
            require(len(path.parts) == 1 and re.fullmatch(r'[A-Za-z0-9_.-]+\.(?:exe|dll)', name, re.I),
                    'Unexpected binary package member')
        else:
            require(name.startswith('data/'), 'Schema payload must remain under data/')
        require(isinstance(record, dict) and type(record.get('bytes')) is int
                and 0 <= record['bytes'] <= 200 * 1024 * 1024
                and isinstance(record.get('sha256'), str) and HEX64.fullmatch(record['sha256']),
                'Invalid payload digest record')
        target = root
        for part in path.parts:
            target /= part
            require(not target.is_symlink(), 'Linked payload component refused')
        require(target.is_file() and target.stat().st_size == record['bytes']
                and base.file_hash(target) == record['sha256'], 'Payload hash/size mismatch: ' + name)
        total += record['bytes']
    require(total <= 300 * 1024 * 1024, 'Payload exceeds total bound')
    actual = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Linked payload entry refused')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
        else:
            require(path.is_dir(), 'Nonregular payload entry refused')
    require(actual == set(files) | ({manifest} if manifest else set()), 'Unexpected or missing payload files')


def verify_inputs(package, schema):
    package_receipt = load_json(package / 'package-manifest.json')
    require(package_receipt.get('format') == 1
            and COMMIT.fullmatch(package_receipt.get('repository_commit', ''))
            and COMMIT.fullmatch(package_receipt.get('source_commit', ''))
            and package_receipt.get('android_execution_validated') is False
            and package_receipt.get('gameplay_validated') is False,
            'Invalid DbServer package provenance or scope')
    validate_fixed_inputs_metadata(package_receipt.get('wine_build_input', {}).get('fixed_inputs'))
    variants = package_receipt.get('variants', {})
    require(set(variants) == {'fixture', 'normal'}, 'Both DbServer build variants are required')
    for variant, enabled in (('fixture', True), ('normal', False)):
        record = variants[variant]
        require(record.get('postgresql_persistence_fixture') is enabled,
                'DbServer fixture build mode differs')
        files = record.get('files', {})
        require('DbServer.exe' in files, 'Missing real DbServer executable')
        verify_inventory(package / variant, files, binary=True)
        for name in files:
            base.verify_pe32(package / variant / name)
    receipt = load_json(schema / 'schema-manifest.json')
    require(receipt.get('format') == 1 and receipt.get('scope') == 'accepted_generated_schema_inputs'
            and receipt.get('schema_status') == 'schema_data_only_outputs_checked_runtime_unvalidated'
            and receipt.get('source_commit') == package_receipt['source_commit']
            and COMMIT.fullmatch(receipt.get('data_commit', ''))
            and receipt.get('android_execution_validated') is False
            and receipt.get('gameplay_validated') is False,
            'Schema provenance or scope differs from DbServer package')
    for name in ('schema_report_sha256', 'schema_archive_sha256'):
        require(isinstance(receipt.get(name), str) and HEX64.fullmatch(receipt[name]),
                'Missing accepted schema digest: ' + name)
    verify_inventory(schema, receipt.get('files'), manifest='schema-manifest.json')
    tables, attrs = receipt.get('expected_tables'), receipt.get('expected_attributes')
    require(isinstance(tables, dict) and 0 < len(tables) <= 512
            and isinstance(attrs, dict) and attrs.get('attributes'), 'Empty schema contract')
    for table, columns in tables.items():
        require(IDENTIFIER.fullmatch(table) and isinstance(columns, list) and 0 < len(columns) <= 8192
                and len(columns) == len(set(columns))
                and all(isinstance(c, str) and IDENTIFIER.fullmatch(c) for c in columns),
                'Invalid expected table or ordered columns')
    for table, rows in attrs.items():
        require(table in tables and tables[table] == ['id', 'name'] and isinstance(rows, list)
                and len(rows) <= 100000, 'Invalid expected attribute table')
        names = set()
        for number, row in enumerate(rows, 1):
            require(isinstance(row, dict) and set(row) == {'id', 'name'}
                    and type(row['id']) is int and row['id'] == number
                    and isinstance(row['name'], str) and len(row['name']) <= 8192
                    and row['name'] not in names, 'Invalid expected attribute identity')
            names.add(row['name'])
    for entry in receipt.get('optional_inputs', []):
        name = entry['path'] if isinstance(entry, dict) else entry
        require(name in ('data/server/db/weeklyTF.cfg', 'data/server/db/Doors.db')
                and not (schema / name).exists(), 'Unexpected optional schema input')
    private_config((schema / 'data/server/db/servers.cfg').read_text(), 'coh_test_' + '0' * 16,
                   'Driver={PostgreSQL Unicode};Database=coh_test_' + '0' * 16 + ';')
    return package_receipt, receipt


def validate_fixture_phase(mode, expected, code, output):
    lines = [line.strip() for line in output.splitlines()]
    require(code == expected and not any('PG_TEST_FAILED' in line for line in lines),
            'DbServer fixture phase failed: ' + mode)
    complete = [line for line in lines if line.startswith('PG_TEST_COMPLETE ')]
    if expected == 0:
        require(complete == ['PG_TEST_COMPLETE ' + mode]
                and not any('PG_TEST_FATAL' in line or 'PG_FIFO_FAILED' in line for line in lines),
                'DbServer phase did not prove clean completion: ' + mode)
    else:
        marker = 'PG_FIFO_FAILED' if expected == 3 else 'PG_TEST_FATAL'
        require(expected in (2, 3) and not complete and any(marker in line for line in lines),
                'DbServer failure phase did not prove its expected refusal: ' + mode)
    return [line[:1500] for line in lines if 'PG_TEST_' in line or 'PG_FIFO_' in line][-150:]


def private_config(original, database, connection):
    import shlex
    kept, settings = [], {}
    for line in original.splitlines():
        if line.split() and line.split()[0].lower() in ('sqldbprovider', 'sqldbname', 'sqllogin', 'sqlinit'):
            continue
        kept.append(line)
        if line.strip() and not line.lstrip().startswith(('//', '#')):
            tokens = shlex.split(line, comments=False)
            if len(tokens) >= 2:
                settings[tokens[0].lower()] = tokens[1]
    require(settings.get('usefakeauth') == '1' and settings.get('usequeueserver') == '0'
            and settings.get('sqlallowddl') == '1' and 'authserver' not in settings,
            'Generated schema config would enable an external service or disable DDL')
    login = connection.replace('Database=' + database + ';', '').strip()
    require('Database=' not in login and '"' not in login and '\n' not in login,
            'Invalid private DbServer login')
    return '\n'.join(kept) + '\nSqlDbProvider postgresql\nSqlDbName ' + database + '\nSqlLogin "' + login + '"\n'


def attribute_digest(rows):
    return hashlib.sha256(''.join(str(row['id']) + ':' + row['name'].encode().hex() + '\n'
                                  for row in rows).encode()).hexdigest()


def column_digest(tables):
    return hashlib.sha256(''.join(table.encode().hex() + ':' + name.encode().hex() + '\n'
                                  for table in sorted(tables) for name in tables[table]).encode()).hexdigest()


class DbServerContext(base.Context):
    def __init__(self, state, total_timeout):
        super().__init__(state, total_timeout)
        self.log_root = None
        self.next_log_check = 0

    def log_paths(self):
        paths = [] if self.log_root is None else list(self.log_root.rglob('*.log'))
        require(len(paths) <= 128 and all(p.is_file() and not p.is_symlink() for p in paths),
                'Invalid or excessive DbServer internal logs')
        sizes = [p.stat().st_size for p in paths]
        require(all(size <= LOG_LIMIT for size in sizes) and sum(sizes) <= 64 * 1024 * 1024,
                'DbServer internal log capture exceeded bound')
        return paths

    def check(self):
        super().check()
        if time.monotonic() >= self.next_log_check:
            self.log_paths()
            self.next_log_check = time.monotonic() + 1


class DbServerDiagnostic(base.Diagnostic):
    def __init__(self, args, context):
        package, schema = verify_inputs(args.package, args.schema)
        super().__init__(args, context)
        self.created_databases = []
        self.private_connections = []
        self.package, self.schema = package, schema
        context.report['inputs'] = {
            'runtime_manifest_sha256': base.file_hash(args.assets / 'runtime-manifest.json'),
            'package_manifest_sha256': base.file_hash(args.package / 'package-manifest.json'),
            'schema_manifest_sha256': base.file_hash(args.schema / 'schema-manifest.json'),
            'fixture_executable_sha256': self.package['variants']['fixture']['files']['DbServer.exe']['sha256'],
            'normal_executable_sha256': self.package['variants']['normal']['files']['DbServer.exe']['sha256'],
            'repository_commit': self.package['repository_commit'],
            'source_commit': self.package['source_commit'], 'data_commit': self.schema['data_commit']}
        self.fixture_report = {'status': 'running', 'check_count': 0, 'checks': [], 'phases': []}
        self.schema_report = {'status': 'not_started', 'fixture_enabled': False, 'phases': [], 'reload_stable': False}
        context.report.update(fixture=self.fixture_report, generated_schema=self.schema_report)

    def sql(self, sql, *, game=False, cleanup=False):
        if cleanup and sql.startswith('DROP DATABASE '):
            for name in self.created_databases:
                require(re.fullmatch(r'coh_test_[0-9a-f]{16}', name), 'Unowned database in cleanup inventory')
            sql = '\n'.join('DROP DATABASE "' + name + '";' for name in self.created_databases)
        super().sql(sql, game=game, cleanup=cleanup)
        created = re.fullmatch(r'CREATE DATABASE "(coh_test_[0-9a-f]{16})" OWNER cohtest;', sql)
        if created:
            self.created_databases.append(created[1])
        # Context keeps a small report tail; catalog checks consume the complete
        # bounded capture rather than silently accepting that truncated tail.
        return self.ctx.children[-1].text().strip()

    def connection_for(self, database):
        driver = self.ctx.report['odbc_driver']['driver_name']
        return ('Driver={' + driver + '};Servername=127.0.0.1;Port=' + str(self.port)
                + ';Database=' + database + ';Username=cohtest;Password=' + self.credentials['cohtest']
                + ';SSLmode=disable;ByteaAsLongVarBinary=0;UseServerSidePrepare=0;')

    def stage_variant(self, variant):
        target = self.root / ('dbserver-' + variant + '-' + secrets.token_hex(6))
        target.mkdir(mode=0o700)
        # UtilitiesLib/file.c:addAppropriateDataDirs recognizes a local data
        # root only when BOTH data/ and tools/ exist. Without these markers the
        # fixture's first threaded SQL notice triggers game-data discovery and
        # fallback cache initialization. The fixture needs no data payload;
        # normal_schema subsequently copies only the accepted manifest files.
        for name in ('data', 'tools'):
            (target / name).mkdir(mode=0o700)
        for name in self.package['variants'][variant]['files']:
            shutil.copyfile(self.args.package / variant / name, target / name)
        return target

    def run_windows(self, label, executable, arguments, cwd, *, timeout, expected=0, fixed_inputs=False):
        environment = self.wine_env.copy()
        environment.pop(FIXED_INPUTS_ENV, None)
        if fixed_inputs:
            environment[FIXED_INPUTS_ENV] = '1'
        result = self.ctx.run(label, ['/usr/bin/env', '--chdir=' + str(cwd), self.args.wine,
                                    base.windows_path(executable), *arguments],
                              timeout=timeout, env=environment, check=False,
                              before_stop=self.observe_odbc_failure,
                              progress_message='Running real DbServer ' + label)
        child = self.ctx.children[-1]
        require(result['exit_code'] == expected, 'DbServer exit code differs: ' + label)
        return result, child.text()

    def phase(self, mode, expected=0, *, connection=None, database=None, evidence=None):
        self.ctx.stage('dbserver_' + mode.replace('-', '_'))
        result, output = self.run_windows('dbserver-' + mode, self.fixture_runtime / 'DbServer.exe',
            ['-pgpersistencetest', base.windows_path(connection or self.connection), database or self.database, mode],
            self.fixture_runtime, timeout=180, expected=expected)
        validate_fixed_inputs(output, False)
        markers = validate_fixture_phase(mode, expected, result['exit_code'], output)
        item = {'mode': mode, 'exit_code': result['exit_code'], 'expected_exit_code': expected,
                'markers': markers, 'output_sha256': hashlib.sha256(base.redact(output, self.ctx.secrets).encode()).hexdigest()}
        if evidence:
            item['evidence'] = evidence
        self.fixture_report['phases'].append(item)
        self.ctx.passed(mode=mode, expected_exit_code=expected)

    def expect_sql(self, query, expected):
        require(self.sql(query, game=True) == expected, 'DbServer persistence SQL postcondition failed')

    def crash_restart(self):
        self.ctx.stage('postgres_immediate_restart')
        pg = self.pg
        self.ctx.run('postgres-immediate-stop', [self.pgtool('pg_ctl'), '-D', self.pgdata,
                     '-m', 'immediate', '-w', '-t', '20', 'stop'], timeout=25, env=self.base_env)
        pg.process.wait(timeout=5)
        pg.reader.join(timeout=2)
        require(pg.process.returncode == 0 and not pg.reader.is_alive(), 'Immediate PostgreSQL stop did not complete')
        self.ctx.record(pg)
        self.pg = None
        self.cleanup_status['postgres_graceful'] = False
        self.ctx.passed(immediate_shutdown=True)
        self.start_postgres('postgres_wal_recovery_ready')

    def fixture(self):
        self.fixture_runtime = self.stage_variant('fixture')
        self.ctx.log_root = self.fixture_runtime
        sql = lambda command: self.sql(command, game=True)
        sql('CREATE TABLE coh_meta.persistence_test_guard(id integer); INSERT INTO coh_meta.persistence_test_guard VALUES(1);')
        self.phase('initial')
        sql("CREATE SEQUENCE coh_meta.fifo_reject_count; CREATE FUNCTION coh_meta.fifo_reject() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN IF NEW.ContainerId=103 AND NEW.SubId=511 THEN PERFORM nextval('coh_meta.fifo_reject_count'); RAISE EXCEPTION 'injected permanent error' USING ERRCODE='23514'; END IF; RETURN NEW; END$$; CREATE TRIGGER fifo_reject BEFORE UPDATE ON dbo.PgFifoItems FOR EACH ROW EXECUTE FUNCTION coh_meta.fifo_reject();")
        self.phase('fail', 3)
        for query, expected in (('SELECT count(*) FROM dbo.PgFifo WHERE ContainerId=103;', '0'),
                                ('SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=103;', '0'),
                                ('SELECT last_value FROM coh_meta.fifo_reject_count;', '1')):
            self.expect_sql(query, expected)
        sql("ALTER SEQUENCE coh_meta.fifo_reject_count RESTART WITH 1; CREATE OR REPLACE FUNCTION coh_meta.fifo_reject() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN IF NEW.ContainerId=103 AND NEW.SubId=511 THEN PERFORM nextval('coh_meta.fifo_reject_count'); RAISE EXCEPTION 'injected retry exhaustion' USING ERRCODE='40001'; END IF; RETURN NEW; END$$;")
        self.phase('exhaust', 3)
        for query, expected in (('SELECT count(*) FROM dbo.PgFifo WHERE ContainerId=103;', '0'),
                                ('SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=103;', '0'),
                                ('SELECT last_value FROM coh_meta.fifo_reject_count;', '5')):
            self.expect_sql(query, expected)
        sql('DROP TRIGGER fifo_reject ON dbo.PgFifoItems;')
        sql("CREATE FUNCTION coh_meta.fifo_reject_delete() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'injected delete failure' USING ERRCODE='23503'; END$$; CREATE TRIGGER fifo_reject_delete BEFORE DELETE ON dbo.PgFifo FOR EACH ROW EXECUTE FUNCTION coh_meta.fifo_reject_delete();")
        self.phase('delete-fail', 3)
        self.expect_sql('SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=101;', '512')
        self.expect_sql('SELECT count(*) FROM dbo.PgFifo WHERE ContainerId=101;', '1')
        sql('DROP TRIGGER fifo_reject_delete ON dbo.PgFifo;')
        self.phase('disconnect', 3)
        self.expect_sql('SELECT Score FROM dbo.PgFifo WHERE ContainerId=101;', '555')
        self.phase('verify')
        self.stop_postgres()
        self.start_postgres('postgres_clean_restart_ready')
        self.phase('verify', evidence='clean_postgres_restart')
        self.crash_restart()
        self.phase('verify', evidence='postgres_wal_recovery')
        self.phase('rebuild')
        self.phase('verify-rebuilt')
        original = sql("SELECT 'dbo.PgFifo'::regclass::oid;")
        self.phase('rebuild-fail', 2)
        self.expect_sql("SELECT 'dbo.PgFifo'::regclass::oid;", original)
        sql('CREATE VIEW coh_meta.schema_guard AS SELECT Name FROM dbo.PgFifo;')
        self.phase('rebuild-fail-view', 2)
        self.expect_sql("SELECT 'dbo.PgFifo'::regclass::oid;", original)
        sql('DROP VIEW coh_meta.schema_guard;')
        self.expect_sql("SELECT count(*) FROM pg_class WHERE relnamespace='dbo'::regnamespace AND relkind='r' AND relname LIKE 'coh_rebuild_%';", '0')
        self.phase('verify-rebuilt')
        self.backup_restore()
        require(tuple(p['mode'] for p in self.fixture_report['phases']) == FIXTURE_MODES,
                'DbServer persistence phase coverage differs')
        self.fixture_report.update(status='passed', checks=list(FIXTURE_CHECKS), check_count=len(FIXTURE_CHECKS))

    def backup_restore(self):
        self.ctx.stage('dbserver_backup_restore')
        dump = self.root / ('fifo-' + secrets.token_hex(6) + '.backup')
        with dump.open('xb'):
            pass
        env = dict(self.base_env, PGPASSWORD=self.credentials['cohtest'], PGCONNECT_TIMEOUT='5')
        connection = ['-h', str(self.socket_dir), '-p', str(self.port), '-U', 'cohtest']
        self.ctx.run('dbserver-pg-dump', [self.pgtool('pg_dump'), *connection, '--format=custom',
                     '--no-owner', '--file', dump, self.database], timeout=90, env=env)
        restored = 'coh_test_' + secrets.token_hex(8)
        self.sql('CREATE DATABASE "' + restored + '" OWNER cohtest;')
        self.sql('REVOKE ALL ON DATABASE ' + restored + ' FROM PUBLIC;')
        self.sql('ALTER DATABASE ' + restored + ' SET search_path=dbo,pg_catalog;')
        self.ctx.run('dbserver-pg-restore', [self.pgtool('pg_restore'), *connection, '--exit-on-error',
                     '--no-owner', '--no-acl', '--dbname', restored, dump], timeout=90, env=env)
        previous = self.database
        try:
            self.database = restored
            self.sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC;', game=True)
            self.sql((self.args.assets / '001-coh-compat.sql').read_text(), game=True)
        finally:
            self.database = previous
        target = self.root / 'restored-connection.txt'
        base.private_write(target, self.connection_for(restored) + '\n')
        self.private_connections.append(target)
        self.ctx.passed(backup_sha256=base.file_hash(dump), new_owned_database=True)
        self.phase('verify-rebuilt', connection=target, database=restored, evidence='backup_restore')

    def sql_hash(self, expression):
        value = self.sql("SELECT encode(sha256(convert_to((" + expression + ")::text,'UTF8')),'hex');", game=True)
        require(HEX64.fullmatch(value), 'Invalid PostgreSQL catalog digest')
        return value

    def schema_snapshot(self):
        # Fingerprint full ordered values in PostgreSQL to keep 56k attribute
        # rows and 5935 columns within the existing capture/report bounds.
        columns = self.sql_hash("SELECT coalesce(string_agg(encode(convert_to(table_name,'UTF8'),'hex') || ':' || encode(convert_to(column_name,'UTF8'),'hex') || E'\\n','' ORDER BY table_name COLLATE \"C\",ordinal_position),'') FROM information_schema.columns WHERE table_schema='dbo'")
        require(columns == column_digest(self.schema['expected_tables']), 'Generated table/ordered-column identities differ')
        attrs, counts = {}, {}
        for table, rows in self.schema['expected_attributes'].items():
            value = self.sql_hash("SELECT coalesce(string_agg(id::text || ':' || encode(convert_to(name,'UTF8'),'hex') || E'\\n','' ORDER BY id),'') FROM dbo." + table)
            count = self.sql('SELECT count(*) FROM dbo.' + table + ';', game=True)
            require(count == str(len(rows)) and value == attribute_digest(rows), 'Generated attribute IDs/names differ: ' + table)
            attrs[table], counts[table] = value, len(rows)
        catalog = {}
        queries = {
            'columns': "SELECT coalesce(json_agg(x ORDER BY table_name,ordinal_position),'[]'::json) FROM (SELECT table_name,column_name,ordinal_position,data_type,udt_name,character_maximum_length,is_nullable,column_default FROM information_schema.columns WHERE table_schema='dbo') x",
            'indexes': "SELECT coalesce(json_agg(x ORDER BY tablename,indexname),'[]'::json) FROM (SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='dbo') x",
            'constraints': "SELECT coalesce(json_agg(x ORDER BY table_name,name),'[]'::json) FROM (SELECT c.relname AS table_name,k.conname AS name,k.contype AS type,pg_get_constraintdef(k.oid) AS definition FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='dbo') x"}
        for name, query in queries.items():
            catalog[name] = self.sql_hash(query)
        return {'catalog_sha256': catalog, 'attribute_sha256': attrs, 'attribute_counts': counts,
                'ordered_columns_sha256': columns, 'table_count': len(self.schema['expected_tables']),
                'column_count': sum(len(value) for value in self.schema['expected_tables'].values())}

    def normal_schema(self):
        self.database = 'coh_test_' + secrets.token_hex(8)
        self.prepare_database()
        self.normal_runtime = self.stage_variant('normal')
        for name in self.schema['files']:
            target = self.normal_runtime / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(self.args.schema / name, target)
        config = self.normal_runtime / 'data/server/db/servers.cfg'
        base.private_write(config, private_config(config.read_text(), self.database, self.connection_for(self.database)))
        self.private_connections.append(config)
        self.ctx.log_root = self.normal_runtime
        self.schema_report['status'] = 'running'
        self.expect_sql("SELECT count(*) FROM information_schema.columns WHERE table_schema='dbo';", '0')
        migration_query = "SELECT coalesce(json_agg(x ORDER BY version),'[]'::json) FROM coh_meta.schema_version x;"
        migration = self.sql(migration_query, game=True)
        require(any(row['version'] == 2 for row in json.loads(migration)), 'Compatibility migration 2 missing')
        previous = None
        # Cover stock default startup and the opt-in fixed-input reload without
        # adding more real server launches or changing the accepted input bytes.
        for number, fixed_inputs in ((1, False), (2, True)):
            self.ctx.stage('normal_dbserver_schema_' + str(number))
            dump = self.root / ('schema-export-' + str(number) + '-' + secrets.token_hex(6) + '.dump')
            require(not dump.exists(), 'Normal DbServer export was not fresh')
            result, output = self.run_windows('normal-schema-' + str(number), self.normal_runtime / 'DbServer.exe',
                ['-exportdump', base.windows_path(dump)], self.normal_runtime, timeout=600,
                fixed_inputs=fixed_inputs)
            fixed_input_evidence = validate_fixed_inputs(output, fixed_inputs)
            errors, notices, logs = [], [], []
            texts = [output]
            for path in sorted(self.ctx.log_paths()):
                text = base.redact(path.read_text(encoding='utf-8', errors='replace'), self.ctx.secrets)
                texts.append(text)
                logs.append({'path': path.relative_to(self.normal_runtime).as_posix(),
                             'redacted_sha256': hashlib.sha256(text.encode()).hexdigest(), 'bytes': len(text.encode())})
            for text in texts:
                for line in text.splitlines():
                    if BENIGN_CATALOG_NOTICE.fullmatch(line.strip()):
                        notices.append(line[:1500])
                    elif FAILURE.search(line):
                        errors.append(base.redact(line[:1500], self.ctx.secrets))
            phase = {'number': number, 'exit_code': result['exit_code'], 'failure_diagnostic_lines': errors[:100],
                     'benign_catalog_notices': {'count': len(notices), 'lines': notices[:100]}, 'logs': logs,
                     'fixed_inputs': fixed_input_evidence}
            self.schema_report['phases'].append(phase)
            require(not errors, 'Normal DbServer emitted failure diagnostics')
            require(dump.is_file() and not dump.is_symlink() and dump.stat().st_size == 0,
                    'Normal DbServer did not create a fresh empty database export')
            snapshot = self.schema_snapshot()
            require(self.sql(migration_query, game=True) == migration, 'Normal DbServer changed compatibility migration')
            if previous is not None:
                require(snapshot == previous, 'Normal DbServer reload changed catalog or attributes')
            previous = snapshot
            phase.update(snapshot, export_sha256=base.file_hash(dump), export_bytes=0,
                         input_manifest_sha256=self.ctx.report['inputs']['schema_manifest_sha256'])
            self.ctx.passed(table_count=snapshot['table_count'], attribute_counts=snapshot['attribute_counts'],
                            fixed_inputs=fixed_input_evidence)
        self.schema_report.update(status='passed', reload_stable=True)

    def execute(self):
        self.initialize()
        for name in ('pg_dump', 'pg_restore'):
            base.arm64_elf(self.args.pg_bin / name)
        self.start_postgres('postgres_first_start')
        self.prepare_database()
        self.start_wine()
        self.ctx.stage('win32_runtime_dll')
        result = self.ctx.run('runtime-probe', [self.args.wine, base.windows_path(self.args.assets / 'runtime-probe.exe')],
                              timeout=60, env=self.wine_env)
        self.ctx.passed(**base.validate_runtime_probe(result['output']))
        self.mark_wine_ready()
        self.fixture()
        self.normal_schema()

    def cleanup(self):
        try:
            return super().cleanup()
        finally:
            for path in self.private_connections:
                path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in (('state', '/state'), ('assets', '/opt/coh'), ('package', '/opt/coh-dbserver'),
                          ('schema', '/opt/coh-schema'), ('pg-bin', '/opt/coh/pgsql/bin'),
                          ('wine', '/opt/wine/bin/wine'), ('wineserver', '/opt/wine/bin/wineserver'),
                          ('xserver', '/usr/bin/Xtigervnc')):
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    parser.add_argument('--execution-platform', choices=('host',), default='host')
    args = parser.parse_args(argv)
    args.client_probe = False
    os.umask(0o077)
    context = DbServerContext(args.state, args.timeout_seconds)
    context.report.update(diagnostic_mode='dbserver_persistence_and_generated_schema',
        scope='Real fixture-ON DbServer persistence and fixture-OFF accepted schema startup/reload through Wine/FEX on ARM64',
        execution_platform_requested='host', android_execution_validated=False,
        gameplay_validated=False, generated_character_persistence_validated=False,
        android_listener_binding_validated=False)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic = None
    try:
        require(60 <= args.timeout_seconds <= 3600, 'Timeout must be 60 to 3600 seconds')
        context.check()
        diagnostic = DbServerDiagnostic(args, context)
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
            if failures and context.report['status'] == 'passed':
                context.report['status'] = 'failed'
        context.report['finished_utc'] = base.utc()
        context.report['cleanup_complete'] = all(child.process.poll() is not None
            and not child.reader.is_alive() and not child.writer.is_alive() for child in context.children)
        context.report['cleanup'] = diagnostic.cleanup_status if diagnostic else {
            'postgres_graceful': False, 'wine_prefix_stopped': False, 'owned_processes_reaped': False}
        context.report['passed'] = context.report['status'] == 'passed' and not context.report['failures'] \
            and all(context.report['cleanup'].values()) and context.report['cleanup_complete']
        if context.report['status'] == 'passed' and not context.report['passed']:
            context.report['status'] = 'failed'
            context.report['failures'].append('Required owned cleanup was not proved')
        try:
            text = json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n'
            require(len(text.encode()) <= 2 * 1024 * 1024, 'Report exceeded bound')
            base.private_write(args.state / 'latest-report.json', text)
        except Exception as exc:
            context.report.update(status='failed', passed=False)
            context.report['failures'].append('Cannot persist diagnostic report: ' + str(exc))
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['passed'] else 2 if context.report['status'] == 'cancelled' else 1


if __name__ == '__main__':
    sys.exit(main())
