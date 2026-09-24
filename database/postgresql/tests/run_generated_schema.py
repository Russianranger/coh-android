#!/usr/bin/env python3
"""Load accepted generated templates with fixture-OFF DbServer on disposable PG.

No MapServer/client is launched. The existing -exportdump path calls dbInit(-1),
then normal export and clean shutdown. Run it twice; compare template-derived
columns, attribute IDs, SQL catalog and compatibility migration. A new private
work directory contains credentials/raw logs; only --output is publishable.
This is a schema startup/reload test, not character persistence or gameplay.

Source: DBServer/src/{dbinit,dbimport,container_tplt,container_tplt_utils}.c.
The template reader models table/column naming only, not the C type system.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'database/postgresql'))
from pg_local import initialize, private_write
from prepare_runtime import require, sha256, safe_relative, verify_binaries
from prepare_schema_source import expected_schema_receipt
from run_schema_generation import SUCCESS as SCHEMA_SUCCESS, bounded_process
import generate_runtime_data as generation

SUPPLEMENTAL = (
    'data/server/db/servers.cfg', 'data/server/db/loadBalanceDefault.cfg',
    'data/server/db/loadBalanceShardSpecific.cfg', 'data/server/db/maps.db',
    'data/defs/account/loyaltyrewardtree.def', 'data/defs/account/product_catalog.def',
)
OPTIONAL = ('data/server/db/weeklyTF.cfg', 'data/server/db/Doors.db')
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
FAILURE = re.compile(r'\b(?:fatal|assertion failed|SQL_ERROR|PG_FIFO_FAILED|'
                     r'INVALID PARAMETER|Giving up|Bad output file|Error binding|'
                     r'SQLSTATE|ODBC error|SQL error)\b|^\s*ERROR[:\s]', re.I)
LOG_LIMIT = 16 * 1024 * 1024


def ascii_lower(value):
    return value.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))


def sql_name(value):
    require(bool(IDENTIFIER.fullmatch(value)), 'Unsupported SQL identifier: ' + value)
    return ascii_lower(value)


def without_comments(source):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)


def schema_contract(source):
    """Derive the templates actually updated and the attributes loaded by dbInit."""
    section = source[source.index('void dbInit(int start_static)'):source.index('static void startupInfo', source.index('void dbInit(int start_static)'))]
    section = without_comments(section)
    registered = dict(re.findall(r'(\w+)\s*=\s*containerListRegister\([^,]+,\s*"([^"]+)"', section))
    updated = re.findall(r'tpltUpdateSqlcolumns\((\w+)->tplt\)', section)
    require(updated and len(updated) == len(set(updated)), 'Unrecognized DbServer template-update source')
    require(all(name in registered for name in updated), 'Unregistered template update')
    templates = {sql_name(registered[name]): 'data/server/db/templates/' + ascii_lower(registered[name]) + '.template'
                 for name in updated}
    attributes = {sql_name(table): 'data/' + first for first, alternate, table in
                  re.findall(r'tpltLoadAttributes\("([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\)', section)}
    require(attributes, 'No source-derived attribute tables found')
    return templates, attributes


def template_columns(text, root_table):
    """Follow ctnrLineGet's persistent table state and tpltLoad implicit fields."""
    tables = {}
    current = sql_name(root_table)
    for number, line in enumerate(text.splitlines(), 1):
        line = line.split('//', 1)[0].strip()
        if not line:
            continue
        tokens = shlex.split(line)
        require(len(tokens) in (2, 3) and (len(tokens) == 2 or tokens[2].lower() == 'indexed'),
                f'Unsupported template syntax at {root_table}:{number}')
        field = tokens[0]
        if '[' in field:
            match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)\[[^\]\r\n]+\]\.([A-Za-z_][A-Za-z0-9_]*)', field)
            require(match is not None, f'Unsupported template field: {field}')
            current, field = sql_name(match[1]), match[2]
        field = sql_name(field)
        columns = tables.setdefault(current, ['containerid', 'active' if current == sql_name(root_table) else 'subid'])
        require(field not in columns, f'Duplicate template column: {current}.{field}')
        columns.append(field)
    return tables


def attribute_rows(text):
    values, seen_names = {}, set()
    for line in text.splitlines():
        if not line.strip():
            continue
        tokens = shlex.split(line)
        require(len(tokens) == 2 and tokens[0].isdigit(), 'Malformed generated attribute line')
        number, name = int(tokens[0]), ascii_lower(tokens[1])
        require(number > 0 and number not in values and name not in seen_names,
                'Duplicate/nonpositive attribute ID or duplicate name')
        values[number] = name
        seen_names.add(name)
    require(not values or set(values) == set(range(1, max(values) + 1)),
            'Sparse attributes need a separate loader-semantics review')
    return [{'id': key, 'name': values[key]} for key in sorted(values)]


def redact(text, secrets=()):
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[redacted]')
    return re.sub(r'(?i)\b(password|pwd)\s*=\s*[^;\r\n"]+', r'\1=[redacted]', text)


def private_config(original, fragment):
    replacements = {'sqldbprovider', 'sqldbname', 'sqllogin', 'sqlinit'}
    kept = [line for line in original.splitlines()
            if not line.split() or line.split()[0].lower() not in replacements]
    settings = {}
    for line in kept:
        if not line.strip() or line.lstrip().startswith(('//', '#')):
            continue
        tokens = shlex.split(line, comments=False)
        if len(tokens) >= 2 and not tokens[0].startswith('//'):
            settings[tokens[0].lower()] = tokens[1]
    require(settings.get('usefakeauth') == '1' and settings.get('usequeueserver') == '0',
            'This disposable test requires UseFakeAuth 1 and UseQueueServer 0')
    require('authserver' not in settings, 'External AuthServer is incompatible with this test')
    require(settings.get('sqlallowddl') == '1', 'Schema DDL must be enabled')
    return '\n'.join(kept) + '\n' + fragment


def payload(source):
    return source if isinstance(source, bytes) else source.read_bytes()


def payload_hash(source):
    return hashlib.sha256(payload(source)).hexdigest()


def archive_payloads(path, archive_record):
    require(path.is_file() and not path.is_symlink(), 'Missing accepted schema archive')
    require(path.stat().st_size == archive_record.get('bytes') and sha256(path) == archive_record.get('sha256'),
            'Schema archive hash/size mismatch')
    records = archive_record.get('files', [])
    require(records, 'Accepted schema report has no archived outputs')
    expected = {}
    for record in records:
        name = record['path']
        safe_relative(name)
        require(name.startswith(('data/server/db/templates/', 'data/server/db/schemas/')) or
                (name.startswith('data/defs/') and name.endswith('.dbidmap')), 'Unexpected generated schema path')
        require(name.casefold() not in expected, 'Duplicate generated path')
        expected[name.casefold()] = record
    result = {}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(len(entries) == len(expected) and sum(p.file_size for p in entries) <= 200 * 1024 * 1024,
                'Archive entry count/expanded size exceeds accepted output bounds')
        for entry in entries:
            safe_relative(entry.filename)
            key = entry.filename.casefold()
            require(key in expected and key not in result and not entry.is_dir() and
                    (entry.external_attr >> 16) & 0o170000 != 0o120000, 'Unexpected/unsafe schema archive member')
            record = expected[key]
            require(entry.filename == record['path'] and entry.file_size == record['bytes'],
                    'Archive member differs from accepted output record')
            data = archive.read(entry)
            require(payload_hash(data) == record['sha256'], 'Generated schema file hash mismatch: ' + entry.filename)
            result[key] = (entry.filename, data)
    return result


def accepted_inputs(runtime, report_path, reference, root=ROOT, archive_path=None):
    """All acceptance/hash checks precede cluster creation or credential writing."""
    require(runtime.is_dir() and not runtime.is_symlink(), 'Runtime must be a real staged directory')
    require(not (runtime / 'gamedatadir.txt').exists(), 'External data roots are not allowed')
    inputs = json.loads((runtime / 'runtime-inputs.json').read_text())
    require(inputs.get('source_commit') == generation.SOURCE_COMMIT and
            inputs.get('data_commit') == generation.DATA_COMMIT, 'Wrong staged source/data pins')
    require(inputs.get('binary_assets_supplied') is False, 'Use a text-only staged schema runtime')
    report = json.loads(report_path.read_text())
    require(report.get('status') == SCHEMA_SUCCESS and report.get('exit_code') == 0 and
            report.get('failures') == [] and report.get('queued_error_counts') and
            all(count == 0 for count in report['queued_error_counts']),
            'Schema generation has not passed acceptance; refusing database startup')
    require(report.get('source_commit') == generation.SOURCE_COMMIT and
            report.get('data_commit') == generation.DATA_COMMIT, 'Schema report source/data pin mismatch')
    receipt = report.get('schema_build_input', {})
    require(receipt == expected_schema_receipt(root, postgresql_build_input=receipt.get('postgresql_build_input')),
            'Schema source receipt mismatch')
    files = archive_payloads(archive_path or report_path.parent / 'schema-outputs.zip',
                             report.get('schema_outputs_archive', {}))
    templates, attrs = schema_contract((root / 'upstream/ouroboros/DBServer/src/dbinit.c').read_text())
    expected_tables, expected_attrs = {}, {}
    for table, name in templates.items():
        require(name.casefold() in files, 'Missing accepted template: ' + name)
        for name_, columns in template_columns(payload(files[name.casefold()][1]).decode('utf-8'), table).items():
            require(name_ not in expected_tables, 'Overlapping generated table: ' + name_)
            expected_tables[name_] = columns
    for table, name in attrs.items():
        require(name.casefold() in files, 'Missing accepted attribute: ' + name)
        expected_attrs[table] = attribute_rows(payload(files[name.casefold()][1]).decode('utf-8'))
        expected_tables[table] = ['id', 'name']
    require(expected_tables and expected_attrs.get('attributes'), 'Generated database schema is empty')
    # Bind supplemental text to the immutable pins, rather than trusting a stage label.
    for name in SUPPLEMENTAL:
        path = runtime / name
        pinned = root / ('upstream/ouroboros/' if name.endswith('.cfg') else 'upstream/i24/') / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == sha256(pinned),
                'Supplemental text differs from pinned source: ' + name)
        files[name.casefold()] = (name, path)
    optional = []
    for name in OPTIONAL:
        path = runtime / name
        require(not path.exists(), 'Optional test input unexpectedly present; review separately: ' + name)
        optional.append({'path': name, 'status': 'absent_in_pinned_data',
                         'handling': 'left absent; missing-file diagnostics captured explicitly'})
    lock = json.loads((root / 'upstream-lock.json').read_text())
    package, binary_files, hashes = verify_binaries(reference, root, lock)
    require(package['postgresql_persistence_fixture'] is False, 'Fixture-enabled DbServer is not accepted')
    return files, expected_tables, expected_attrs, optional, package, binary_files, hashes


def query_json(cluster, sql):
    return json.loads(cluster.sql(sql, user='coh_game', database=cluster.meta['database']))


def catalog_snapshot(cluster):
    columns = query_json(cluster, "SELECT coalesce(json_agg(x ORDER BY table_name, ordinal_position),'[]'::json) FROM (SELECT table_name,column_name,ordinal_position,data_type,udt_name,character_maximum_length,is_nullable,column_default FROM information_schema.columns WHERE table_schema='dbo') x;")
    indexes = query_json(cluster, "SELECT coalesce(json_agg(x ORDER BY tablename,indexname),'[]'::json) FROM (SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='dbo') x;")
    constraints = query_json(cluster, "SELECT coalesce(json_agg(x ORDER BY table_name,name),'[]'::json) FROM (SELECT c.relname AS table_name,k.conname AS name,k.contype AS type,pg_get_constraintdef(k.oid) AS definition FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='dbo') x;")
    return {'columns': columns, 'indexes': indexes, 'constraints': constraints}


def validate_catalog(catalog, expected):
    actual = {}
    for row in catalog['columns']:
        actual.setdefault(row['table_name'], []).append(row['column_name'])
    require(actual == expected, 'SQL tables/ordered columns differ from generated templates and attributes')


def collect_logs(runtime, private_logs, output, secrets):
    texts, records = [], []
    candidates = list(private_logs.glob('*.log'))
    candidates += [p for p in runtime.rglob('*.log') if p.is_file() and not p.is_symlink()]
    for index, source in enumerate(sorted(candidates)):
        require(source.stat().st_size <= LOG_LIMIT, 'Internal log exceeds capture bound')
        value = redact(source.read_text(encoding='utf-8', errors='replace'), secrets)
        target = output / f'log-{index:03d}.txt'
        target.write_text(value, encoding='utf-8')
        label = ('raw-logs/' + source.name if source.parent == private_logs else
                 'runtime/' + source.relative_to(runtime).as_posix())
        records.append({'file': target.name, 'source': label, 'sha256': sha256(target), 'bytes': target.stat().st_size})
        texts.append(value)
    return '\n'.join(texts), records


def make_private_directory(path):
    path.mkdir(parents=True, mode=0o700)
    if os.name == 'nt':
        identity = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'],
                                  check=True, capture_output=True, text=True).stdout
        sid = next(csv.reader(io.StringIO(identity.strip())))[1]
        require(re.fullmatch(r'S-1-[0-9-]+', sid), 'Cannot resolve private work directory owner')
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
                        f'*{sid}:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                       check=True, capture_output=True, text=True)


def run(runtime, schema_report, reference, work, output, pg_bin, driver,
        port=15434, timeout=600, root=ROOT, schema_archive=None):
    runtime, reference = Path(runtime).resolve(), Path(reference).resolve()
    work, output = Path(work).resolve(), Path(output).resolve()
    for path in (work, output):
        require(not path.exists(), 'Work and output directories must be new')
        require(path not in (runtime, reference, root.resolve()) and runtime not in path.parents and
                reference not in path.parents and (root / 'upstream').resolve() not in path.parents,
                'Output overlaps protected input')
    require(work != output and work not in output.parents and output not in work.parents,
            'Private work and public evidence must be separate')
    require(0 < timeout <= 3600, 'Timeout must be between 0 and 3600 seconds')
    files, expected, attrs, optional, package, binaries, hashes = accepted_inputs(
        runtime, Path(schema_report), reference, root, Path(schema_archive) if schema_archive else None)
    # Check private config semantics before starting PostgreSQL.
    private_config(files['data/server/db/servers.cfg'][1].read_text(), '')
    make_private_directory(work)
    output.mkdir(parents=True)
    isolated = work / 'runtime'
    isolated.mkdir()
    private_logs = work / 'raw-logs'
    private_logs.mkdir()
    report = {'status': 'generated_schema_database_validation_failed',
              'scope': 'fixture-OFF normal DbServer schema startup/export/reload on disposable PostgreSQL',
              'source_commit': generation.SOURCE_COMMIT, 'data_commit': generation.DATA_COMMIT,
              'schema_report_sha256': sha256(Path(schema_report)),
              'reference_repository_commit': package['repository_commit'],
              'dbserver_sha256': hashes['DbServer.exe'], 'input_sha256': {},
              'optional_inputs': optional, 'phases': [], 'failures': [],
              'console_capture_limit': 'Legacy DbServer may reopen CONOUT$; engine logs, SQL state and fresh export are checked independently',
              'character_persistence_validated': False, 'gameplay_validated': False,
              'serializer_equivalence': 'unverified', 'started_utc': datetime.now(timezone.utc).isoformat()}
    cluster, secrets = None, []
    try:
        for name, path in files.values():
            report['input_sha256'][name] = payload_hash(path)
            if name == 'data/server/db/servers.cfg':
                continue
            target = isolated / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload(path))
        for name, path in binaries.items():
            if name == 'DbServer.exe' or name.lower().endswith('.dll'):
                shutil.copy2(path, isolated / name)
        cluster = initialize(work / 'pg', pg_bin, port, 'coh_schema_test', driver)
        secrets = list(cluster.secrets.values())
        config = private_config(files['data/server/db/servers.cfg'][1].read_text(),
                                (cluster.root / 'dbserver-postgresql.cfg').read_text())
        private_write(isolated / 'data/server/db/servers.cfg', config)
        migration_query = "SELECT coalesce(json_agg(x ORDER BY version),'[]'::json) FROM coh_meta.schema_version x;"
        migration = query_json(cluster, migration_query)
        require(any(row['version'] == 2 for row in migration), 'Compatibility migration 2 missing')
        require(catalog_snapshot(cluster)['columns'] == [], 'Disposable dbo schema was not initially empty')
        previous = None
        for index in (1, 2):
            dump = work / f'export-{index}.dump'
            stdout, stderr = private_logs / f'{index}-stdout.log', private_logs / f'{index}-stderr.log'
            phase = bounded_process([str(isolated / 'DbServer.exe'), '-exportdump', str(dump)],
                                    isolated, stdout, stderr, timeout, LOG_LIMIT)
            phase['number'] = index
            report['phases'].append(phase)
            text, logs = collect_logs(isolated, private_logs, output, secrets)
            report['redacted_logs'] = logs
            phase['optional_diagnostic_lines'] = [line[:1500] for line in text.splitlines()
                if re.search(r'weeklytf\.cfg|(?:server[/\\]db[/\\])?doors\.db', line, re.I)]
            errors = [line[:1500] for line in text.splitlines() if FAILURE.search(line)]
            phase['failure_diagnostic_lines'] = errors[:100]
            require(phase.get('exit_code') == 0 and not phase.get('timed_out') and
                    not phase.get('log_limit_exceeded') and not phase.get('capture_error'),
                    'DbServer did not exit cleanly within process/log bounds')
            require(not errors, 'DbServer emitted failure diagnostics; inspect redacted logs')
            require(dump.is_file() and dump.stat().st_size == 0, 'Fresh disposable database export must exist and be empty')
            phase['dump_sha256'] = sha256(dump)
            catalog = catalog_snapshot(cluster)
            validate_catalog(catalog, expected)
            values = {}
            for table, rows in attrs.items():
                values[table] = query_json(cluster, f"SELECT coalesce(json_agg(x ORDER BY id),'[]'::json) FROM (SELECT id,name FROM dbo.{sql_name(table)}) x;")
                require(values[table] == rows, 'Attribute IDs/names differ from generated file: ' + table)
            require(query_json(cluster, migration_query) == migration, 'Compatibility migration changed during DbServer startup')
            state = {'catalog': catalog, 'attributes': values}
            if previous is not None:
                require(state == previous, 'Second normal startup changed the SQL catalog or attribute mapping')
            previous = state
            evidence = output / f'catalog-{index}.json'
            evidence.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
            phase.update(catalog_sha256=sha256(evidence), table_count=len(expected),
                         attribute_counts={name: len(rows) for name, rows in values.items()},
                         checks='template table/column names, exact attribute IDs, stable migration and SQL catalog')
        report['status'] = 'generated_schema_startup_and_reload_passed_gameplay_unvalidated'
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.SubprocessError) as error:
        report['failures'].append(redact(str(error), secrets))
    finally:
        if cluster is not None:
            try:
                cluster.stop()
            except Exception as error:
                report['status'] = 'generated_schema_database_validation_failed'
                report['failures'].append('Cluster shutdown: ' + redact(str(error), secrets))
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'generated-schema-database-report.json').write_text(
            redact(json.dumps(report, indent=2) + '\n', secrets), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--schema-report', type=Path, required=True)
    parser.add_argument('--schema-archive', type=Path, help='Defaults to schema-outputs.zip beside the report')
    parser.add_argument('--reference-binaries', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True, help='NEW private directory; use a short absolute path')
    parser.add_argument('--output', type=Path, required=True, help='NEW redacted evidence directory, separate from work')
    parser.add_argument('--bin', required=True, help='PostgreSQL tools directory')
    parser.add_argument('--driver', default='PostgreSQL Unicode')
    parser.add_argument('--port', type=int, default=15434)
    parser.add_argument('--timeout-seconds', type=float, default=600)
    args = parser.parse_args()
    report = run(args.runtime, args.schema_report, args.reference_binaries, args.work,
                 args.output, args.bin, args.driver, args.port, args.timeout_seconds,
                 schema_archive=args.schema_archive)
    print(report['status'])
    return 0 if report['status'].endswith('_passed_gameplay_unvalidated') else 1


if __name__ == '__main__':
    sys.exit(main())
