#!/usr/bin/env python3
"""Run the actual patched DbServer persistence pipeline against disposable PG."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pg_local import initialize, private_write


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bin',required=True)
    ap.add_argument('--dbserver',required=True,type=Path)
    ap.add_argument('--root',required=True,type=Path)
    ap.add_argument('--report',required=True,type=Path)
    ap.add_argument('--driver',required=True)
    args=ap.parse_args()
    exe=args.dbserver.resolve()
    cluster=initialize(args.root,args.bin,15433,'coh_test_fifo',args.driver)
    report={'status':'failed','executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
            'checks':[],'output':[],'limits':['Controlled templates, not asset-generated character templates',
                'No MapServer, gameplay, account services or Android runtime test',
                'Serialization/deadlock SQLSTATEs injected by real server triggers; not a load benchmark']}
    connection=cluster.root/'odbc-connection.txt'
    def sql(command): return cluster.sql(command,user='coh_game',database='coh_test_fifo')
    def run(mode,expected=0,file=connection,db='coh_test_fifo'):
        print('DbServer persistence phase: '+mode,flush=True)
        result=subprocess.run([str(exe),'-pgpersistencetest',str(file),db,mode],
                              cwd=cluster.root,stdin=subprocess.DEVNULL,capture_output=True,text=True,
                              encoding='utf-8',errors='replace',timeout=180)
        output=result.stdout+result.stderr
        for secret in cluster.secrets.values(): output=output.replace(secret,'[redacted]')
        markers=[line for line in output.splitlines() if 'PG_TEST_' in line or 'PG_FIFO_' in line]
        report['output'].append({'phase':mode,'exit_code':result.returncode,'markers':markers})
        print('\n'.join(markers),flush=True)
        if result.returncode != expected or (expected==0 and 'PG_TEST_COMPLETE '+mode not in output):
            print(output[-12000:],flush=True)
            raise RuntimeError('DbServer phase '+mode+' failed')
        if expected==3 and 'PG_FIFO_FAILED' not in output:
            raise AssertionError('Expected explicit failed-save termination')
        if expected==2 and 'PG_TEST_FATAL' not in output:
            raise AssertionError('Expected refused schema rebuild')
    try:
        sql('CREATE TABLE coh_meta.persistence_test_guard(id integer); INSERT INTO coh_meta.persistence_test_guard VALUES(1);')
        run('initial')
        report['checks']+=['real 64-worker SQL FIFO and container serialization',
            'multi-batch create and update with 512 child rows', 'ordered asynchronous read callback',
            '16 concurrent records and repeated same-record writes', 'Unicode and unsigned byte 255',
            'case-insensitive game cache and SQL name lookup',
            'whole-save retry for 40001 and 40P01', 'commit-time retry before acknowledgement',
            'atomic parent/child deletion']
        # Fail in the last child update, after earlier SQL batches executed.
        sql("CREATE SEQUENCE coh_meta.fifo_reject_count; CREATE FUNCTION coh_meta.fifo_reject() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN IF NEW.ContainerId=103 AND NEW.SubId=511 THEN PERFORM nextval('coh_meta.fifo_reject_count'); RAISE EXCEPTION 'injected permanent error' USING ERRCODE='23514'; END IF; RETURN NEW; END$$; CREATE TRIGGER fifo_reject BEFORE UPDATE ON dbo.PgFifoItems FOR EACH ROW EXECUTE FUNCTION coh_meta.fifo_reject();")
        run('fail',3)
        assert sql('SELECT count(*) FROM dbo.PgFifo WHERE ContainerId=103;')=='0'
        assert sql('SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=103;')=='0'
        assert sql('SELECT last_value FROM coh_meta.fifo_reject_count;')=='1'
        sql("ALTER SEQUENCE coh_meta.fifo_reject_count RESTART WITH 1; CREATE OR REPLACE FUNCTION coh_meta.fifo_reject() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN IF NEW.ContainerId=103 AND NEW.SubId=511 THEN PERFORM nextval('coh_meta.fifo_reject_count'); RAISE EXCEPTION 'injected retry exhaustion' USING ERRCODE='40001'; END IF; RETURN NEW; END$$;")
        run('exhaust',3)
        assert sql('SELECT count(*) FROM dbo.PgFifo WHERE ContainerId=103;')=='0'
        assert sql('SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=103;')=='0'
        assert sql('SELECT last_value FROM coh_meta.fifo_reject_count;')=='5'
        sql('DROP TRIGGER fifo_reject ON dbo.PgFifoItems;')
        sql("CREATE FUNCTION coh_meta.fifo_reject_delete() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'injected delete failure' USING ERRCODE='23503'; END$$; CREATE TRIGGER fifo_reject_delete BEFORE DELETE ON dbo.PgFifo FOR EACH ROW EXECUTE FUNCTION coh_meta.fifo_reject_delete();")
        run('delete-fail',3)
        assert sql('SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=101;')=='512'
        assert sql('SELECT count(*) FROM dbo.PgFifo WHERE ContainerId=101;')=='1'
        sql('DROP TRIGGER fifo_reject_delete ON dbo.PgFifo;')
        report['checks']+=['permanent failure rolls back all save batches', 'five-attempt retry limit without acknowledgement',
                          'failed delete restores previously deleted child rows']
        run('verify')
        cluster.stop(); cluster.start(); run('verify')
        cluster.stop(immediate=True); cluster.start(); run('verify')
        report['checks']+=['new-process container reload', 'clean PostgreSQL restart', 'WAL recovery of real saved containers']
        run('rebuild'); run('verify-rebuilt')
        original_oid=sql("SELECT 'dbo.PgFifo'::regclass::oid;")
        run('rebuild-fail',2)
        assert sql("SELECT 'dbo.PgFifo'::regclass::oid;")==original_oid
        # Failure after copying the replacement, when a view prevents DROP.
        sql('CREATE VIEW coh_meta.schema_guard AS SELECT Name FROM dbo.PgFifo;')
        run('rebuild-fail-view',2)
        assert sql("SELECT 'dbo.PgFifo'::regclass::oid;")==original_oid
        sql('DROP VIEW coh_meta.schema_guard;')
        assert sql("SELECT count(*) FROM pg_class WHERE relnamespace='dbo'::regnamespace AND relname LIKE 'coh_rebuild_%';")=='0'
        run('verify-rebuilt')
        report['checks']+=['real template reorder/add-column rebuild preserves high-water 9000',
            'inbound foreign keys and indexes survive table replacement',
            'failed data conversion and dependent-view rebuild preserve original table']
        dump=cluster.root/'fifo.backup'; cluster.backup(dump); cluster.restore(dump,'coh_test_fifo_restored')
        restored=cluster.root/'restored-connection.txt'
        private_write(restored,cluster.connection_string(args.driver,'coh_test_fifo_restored')+'\n')
        run('verify-rebuilt',file=restored,db='coh_test_fifo_restored')
        report['checks']+=['backup/restore reload through actual DbServer container reader']
        report.update(status='passed',server=cluster.sql('SELECT version();'))
    finally:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n')
        cluster.stop()

if __name__=='__main__': main()
