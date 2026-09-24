#!/usr/bin/env python3
"""Own a loopback PostgreSQL cluster on Linux/Termux; no system service or root.

All data, credentials and generated DbServer settings remain inside --root.
init requires a NEW directory; restore requires a NEW database. Never deletes a
cluster or existing database. Requires initdb/pg_ctl/psql/pg_dump/pg_restore.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def identifier(value):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,47}', value):
        raise ValueError('Use a lower-case SQL identifier of at most 48 characters')
    return value


def private_write(path, text):
    with path.open('x', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        stream.write(text)


class Cluster:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.meta = json.loads((self.root/'cluster.json').read_text())
        self.secrets = json.loads((self.root/'credentials.json').read_text())

    def run(self, program, *args, input=None, user='coh_admin', database='postgres', check=True):
        env = os.environ.copy()
        # Do not let an unrelated shell's libpq settings redirect this cluster.
        for key in list(env):
            if key.startswith('PG'):
                del env[key]
        env.update(PGHOST='127.0.0.1', PGPORT=str(self.meta['port']), PGUSER=user,
                   PGDATABASE=database, PGPASSFILE=str(self.root/'pgpass'), PGCONNECT_TIMEOUT='10')
        command = [str(Path(self.meta['bin'])/program), *map(str, args)]
        result = subprocess.run(command, input=input, env=env, text=True, capture_output=True)
        if check and result.returncode:
            error = result.stderr + result.stdout
            for value in self.secrets.values():
                error = error.replace(value, '[redacted]')
            raise RuntimeError(program + ' failed: ' + error[-4000:])
        return result

    def sql(self, statement, user='coh_admin', database='postgres'):
        return self.run('psql', '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
                        input=statement, user=user, database=database).stdout.strip()

    def start(self):
        self.run('pg_ctl', '-D', self.root/'data', '-l', self.root/'postgres.log', '-w', 'start')

    def stop(self, immediate=False):
        self.run('pg_ctl', '-D', self.root/'data', '-w', '-m', 'immediate' if immediate else 'fast', 'stop')

    def create_database(self, name):
        name = identifier(name)
        # CREATE DATABASE itself rejects an existing database; no DROP or overwrite.
        self.sql(f'CREATE DATABASE {name} OWNER coh_game ENCODING \'UTF8\' TEMPLATE template0;')
        self.sql(f'REVOKE ALL ON DATABASE {name} FROM PUBLIC;')
        self.sql(f'ALTER DATABASE {name} SET search_path = dbo, pg_catalog;')
        self.sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC;', database=name)

    def connection_string(self, driver='PostgreSQL Unicode', database=None):
        if any(c in driver for c in '{};\r\n"'):
            raise ValueError('Invalid ODBC driver name')
        return (f'Driver={{{driver}}};Servername=127.0.0.1;Port={self.meta["port"]};'
                f'Username=coh_game;Password={self.secrets["game"]};'
                f'Database={identifier(database or self.meta["database"])};'
                'SSLmode=disable;ByteaAsLongVarBinary=0;UseServerSidePrepare=0;')

    def backup(self, destination):
        destination = Path(destination).resolve()
        # Reserve exclusively; pg_dump replaces contents only of our reserved file.
        with destination.open('xb'):
            os.chmod(destination, 0o600)
        try:
            self.run('pg_dump', '--format=custom', '--no-owner', '--file', destination,
                     user='coh_game', database=self.meta['database'])
        except Exception:
            destination.unlink()
            raise

    def restore(self, source, name):
        source = Path(source).resolve(strict=True)
        self.create_database(name)
        self.run('pg_restore', '--exit-on-error', '--no-owner', '--no-acl',
                 '--dbname', identifier(name), source, user='coh_game', database=name)
        # Restore as owner and reassert restricted function ACLs omitted by --no-acl.
        self.sql((HERE/'001-coh-compat.sql').read_text(), user='coh_game', database=name)


def initialize(root, pg_bin, port, database, driver):
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        raise ValueError('Run as a normal user; PostgreSQL does not run as root')
    if not 1024 <= port <= 65535:
        raise ValueError('Port must be 1024..65535')
    database = identifier(database)
    pg_bin = Path(pg_bin or Path(shutil.which('initdb') or '').parent).resolve()
    for name in ('initdb', 'pg_ctl', 'psql', 'pg_dump', 'pg_restore'):
        if not (pg_bin/(name + ('.exe' if os.name == 'nt' else ''))).is_file():
            raise ValueError('Missing PostgreSQL tool: ' + str(pg_bin/name))
    root = Path(root).resolve()
    # Unix socket paths are short on Android and Linux; TCP is used by clients.
    if len(os.fsencode(root/'socket')) > 85:
        raise ValueError('Choose a shorter cluster path for the Unix socket')
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    if os.name == 'nt':
        # PostgreSQL drops administrator group rights on Windows. An inherited
        # Administrators-only DACL can deny even this user's password file.
        # Grant only this user's SID and SYSTEM on our newly created directory.
        identity = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'],
                                  check=True, capture_output=True, text=True).stdout
        sid = next(csv.reader(io.StringIO(identity.strip())))[1]
        if not re.fullmatch(r'S-1-[0-9-]+', sid):
            raise ValueError('Cannot resolve the current Windows user SID')
        subprocess.run(['icacls', str(root), '/inheritance:r', '/grant:r',
                        f'*{sid}:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                       check=True, capture_output=True, text=True)
    (root/'socket').mkdir(mode=0o700)
    passwords = {'admin': secrets.token_hex(24), 'game': secrets.token_hex(24)}
    private_write(root/'cluster.json', json.dumps({'bin': str(pg_bin), 'port': port,
                  'database': database, 'format_version': 1}, indent=2)+'\n')
    private_write(root/'credentials.json', json.dumps(passwords)+'\n')
    private_write(root/'pgpass', ''.join(f'127.0.0.1:{port}:*:{role}:{passwords[key]}\n'
                  for role, key in [('coh_admin', 'admin'), ('coh_game', 'game')]))
    private_write(root/'init-password', passwords['admin']+'\n')
    cluster = Cluster(root)
    try:
        cluster.run('initdb', '-D', root/'data', '--username=coh_admin',
                    '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C',
                    '--pwfile', root/'init-password')
    finally:
        (root/'init-password').unlink()
    # Allow all 65 stock DbServer connections plus maintenance. Memory tuning
    # is provisional; benchmark on Thor before reducing the connection pool.
    socket_path = ('' if os.name == 'nt' else str(root/'socket')).replace("'", "''").replace('\\', '\\\\')
    with (root/'data/postgresql.conf').open('a') as config:
        config.write(f"\nlisten_addresses = '127.0.0.1'\nport = {port}\n"
                     f"unix_socket_directories = '{socket_path}'\n"
                     "max_connections = 80\nshared_buffers = '32MB'\nwork_mem = '2MB'\n"
                     "maintenance_work_mem = '32MB'\npassword_encryption = 'scram-sha-256'\n"
                     "fsync = on\nsynchronous_commit = on\nfull_page_writes = on\n")
    cluster.start()
    try:
        cluster.sql(f"CREATE ROLE coh_game LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '{passwords['game']}';")
        cluster.create_database(database)
        cluster.sql((HERE/'001-coh-compat.sql').read_text(), user='coh_game', database=database)
        connection = cluster.connection_string(driver)
        private_write(root/'odbc-connection.txt', connection+'\n')
        # DbServer appends Database itself; avoid duplicate keywords in SqlLogin.
        login = connection.replace(f'Database={database};', '')
        private_write(root/'dbserver-postgresql.cfg',
            '// Replace the existing SqlDbProvider/SqlDbName/SqlLogin/SqlInit lines.\n'
            '// Keep the remaining source-pinned server settings.\n'
            f'SqlDbProvider postgresql\nSqlDbName {database}\nSqlLogin "{login}"\n')
    except Exception:
        cluster.stop()
        raise
    return cluster


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'start', 'stop', 'status', 'backup', 'restore'])
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--bin', dest='pg_bin')
    parser.add_argument('--port', type=int, default=15432)
    parser.add_argument('--database', default='coh_local')
    parser.add_argument('--driver', default='PostgreSQL Unicode')
    parser.add_argument('--file', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.action == 'init':
            initialize(args.root, args.pg_bin, args.port, args.database, args.driver)
        else:
            cluster = Cluster(args.root)
            if args.action == 'start': cluster.start()
            elif args.action == 'stop': cluster.stop()
            elif args.action == 'status':
                print(cluster.run('pg_ctl', '-D', cluster.root/'data', 'status').stdout.strip())
                print('PostgreSQL', cluster.sql('SHOW server_version;'))
            elif args.action == 'backup':
                if not args.file: parser.error('backup requires --file')
                cluster.backup(args.file)
            elif args.action == 'restore':
                if not args.file: parser.error('restore requires --file and a NEW --database')
                cluster.restore(args.file, args.database)
        print(args.action + ' completed')
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error)+'\n')

if __name__ == '__main__':
    main()
