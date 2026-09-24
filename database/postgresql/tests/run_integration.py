#!/usr/bin/env python3
"""Disposable real-PostgreSQL integration, lifecycle, concurrency and restore test."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from pg_local import initialize, private_write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin', required=True)
    parser.add_argument('--probe', required=True, type=Path)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    cluster = initialize(args.root, args.bin, 15432, 'coh_test_local', 'PostgreSQL Unicode')
    connection = cluster.root/'odbc-connection.txt'
    evidence = []
    def probe(*commands, file=connection):
        result = subprocess.run([str(args.probe.resolve()), str(file), *commands],
                                text=True, capture_output=True, timeout=120)
        # Do not copy secrets into output if a driver includes them in diagnostics.
        output = result.stdout+result.stderr
        for secret in cluster.secrets.values(): output = output.replace(secret, '[redacted]')
        print(output, end='', flush=True)
        if result.returncode: raise RuntimeError('ODBC probe failed')
        evidence.append(output)
    running = True
    try:
        # Reapplying the actual migration must preserve objects and data.
        cluster.sql((HERE.parent/'001-coh-compat.sql').read_text(), user='coh_game', database='coh_test_local')
        probe()
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda value: probe('reserve', str(value)), [3100,1200,2700,1600,2200,3000]))
        assert cluster.sql("SELECT dbo.coh_container_high_water('dbo.pgprobe');", user='coh_game', database='coh_test_local')=='3100'
        probe('verify')
        cluster.stop(); running=False
        cluster.start(); running=True
        probe('verify')
        # PostgreSQL's immediate mode forces WAL recovery on the next startup.
        # Only this disposable, script-owned cluster is ever stopped this way.
        cluster.stop(immediate=True); running=False
        cluster.start(); running=True
        probe('verify')
        dump = cluster.root/'game.backup'
        cluster.backup(dump)
        cluster.restore(dump, 'coh_test_restored')
        restored = cluster.root/'restored-connection.txt'
        private_write(restored, cluster.connection_string(database='coh_test_restored')+'\n')
        probe('verify', file=restored)
        try:
            cluster.restore(dump, 'coh_test_restored')
        except RuntimeError:
            pass
        else:
            raise AssertionError('Restore must refuse an existing database')
        # Verify loopback binding, durability and absence of superuser game rights.
        for setting, expected in [('listen_addresses','127.0.0.1'),('fsync','on'),('synchronous_commit','on'),('full_page_writes','on')]:
            assert cluster.sql('SHOW '+setting+';')==expected
        assert cluster.sql("SELECT rolcreatedb OR rolsuper OR rolcreaterole FROM pg_roles WHERE rolname='coh_game';")=='f'
        for name in ('credentials.json','pgpass','odbc-connection.txt','dbserver-postgresql.cfg'):
            assert (cluster.root/name).stat().st_mode & 0o077 == 0
        version = cluster.sql('SELECT version();')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({'status':'passed','server':version,
            'checks':['shared DbServer dialect via real ODBC', 'six concurrent writers',
                      'monotonic sequence reservations', 'clean restart', 'WAL recovery',
                      'backup and restore to new database', 'refuse restore overwrite',
                      'SCRAM credentials and restricted role', 'loopback and durable settings'],
            'probe_output':evidence,
            'limits':['No complete DbServer boot or character gameplay test',
                      'No Android or Wine runtime test', 'No SQL Server data migration']}, indent=2)+'\n')
        print('PASS lifecycle, concurrent writers, WAL recovery, backup/restore, restricted role and private credentials')
    finally:
        if running: cluster.stop()

if __name__ == '__main__':
    main()
