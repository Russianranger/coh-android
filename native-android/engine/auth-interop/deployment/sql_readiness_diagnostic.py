#!/usr/bin/env python3
"""Readiness-only LocalDB transport diagnosis; never start AuthServer or run login."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tarfile
import tempfile
import time

import auth_readiness
import hosted_candidate_login as service

prior = service.prior
INSTANCE = r'cohauth-ci-[0-9a-f]{24}'
PIPE = r'np:\\\\\.\\pipe\\LOCALDB#[A-Za-z0-9_-]{1,64}\\tsql\\query'


class RedactedCommands:
    """Never retain SQL/LocalDB console text; numeric queries stay private."""
    def __init__(self, records, private_directory, deadline=None):
        self.records, self.directory, self.deadline = records, private_directory, deadline

    def remaining(self, requested=150):
        if self.deadline is None:
            return requested
        available = self.deadline - time.monotonic()
        if available < 1:
            raise ValueError('sql_diagnostic_experiment_deadline')
        return min(requested, available)

    def run(self, name, command, cwd=None, timeout=120, allowed=(0,)):
        started = time.monotonic()
        record = {'name': name, 'console_output_suppressed': True, 'returncode': None}
        self.records.append(record)
        try:
            result = subprocess.run(list(map(str,command)), cwd=cwd, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=self.remaining(timeout))
            record['returncode'] = result.returncode
            if result.returncode not in allowed:
                raise ValueError('private_sql_command_failed')
            return result.returncode
        except subprocess.TimeoutExpired:
            record['timeout'] = True
            raise ValueError('private_sql_command_timeout') from None
        finally:
            record['elapsed_ms'] = int((time.monotonic()-started)*1000)

    def numeric(self, name, command, kind, timeout=150):
        if (name,kind) not in (('localdb-version','version'),('localdb-pid','pid')):
            raise ValueError('private_sql_query_kind')
        started=time.monotonic(); record={'name':name,'console_output_suppressed':True,'returncode':None}
        self.records.append(record)
        deadline=started+self.remaining(timeout)
        # Private transient file bounds memory and is removed before returning;
        # only a validated numeric scalar can reach the caller or receipt.
        with tempfile.TemporaryFile(dir=self.directory) as stream:
            process=subprocess.Popen(list(map(str,command)),stdout=stream,stderr=subprocess.DEVNULL)
            try:
                while process.poll() is None:
                    if time.monotonic()>=deadline or os.fstat(stream.fileno()).st_size>8192:
                        process.kill();process.wait(timeout=5)
                        raise ValueError('private_sql_query_timeout_or_output_bound')
                    time.sleep(.05)
                record['returncode']=process.returncode
                if process.returncode or os.fstat(stream.fileno()).st_size>8192:
                    raise ValueError('private_sql_query_failed')
                stream.seek(0);text=stream.read(8193).decode('ascii',errors='strict').strip()
                if kind=='version' and text=='17.0.4025.3':value=text
                elif kind=='pid' and re.fullmatch('[1-9][0-9]{0,9}',text) and int(text)<=0xffffffff:value=int(text)
                else:raise ValueError('private_sql_numeric_result_shape')
                record['numeric_result']=value
                return value
            finally:
                if process.poll() is None:
                    process.kill();process.wait(timeout=5)
                record['elapsed_ms']=int((time.monotonic()-started)*1000)


def pipe_from_info(text):
    # Never retain the info text (it includes the private runner user identity).
    matches = re.findall(PIPE, text)
    if len(matches) != 1:
        raise ValueError('owned_localdb_pipe_shape')
    return matches[0]


def observer_script(instance, endpoint, architecture, database):
    if (not re.fullmatch(INSTANCE, instance) or architecture not in (32,64) or database not in ('master','cohauth')
            or endpoint != '(localdb)\\' + instance and not re.fullmatch(PIPE, endpoint)):
        raise ValueError('readiness_transport_input')
    original = auth_readiness.script(instance)
    before = 'Server=(localdb)\\' + instance + ';Database=cohauth;'
    if original.count(before) != 1 or original.count('[IntPtr]::Size -ne 4') != 1:
        raise ValueError('readiness_original_script_changed')
    # Same three-connection/query/driver/security policy. Only endpoint, database
    # and required shell architecture vary in this separate diagnostic.
    return original.replace(before, 'Server='+endpoint+';Database='+database+';').replace(
        '[IntPtr]::Size -ne 4', '[IntPtr]::Size -ne '+str(architecture//8))


def observe(instance, endpoint, architecture, database, expected_pid, timeout=50):
    script = observer_script(instance,endpoint,architecture,database)
    shell = Path(os.environ['WINDIR']) / ('SysWOW64' if architecture==32 else 'System32') / 'WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([shell,'-NoLogo','-NoProfile','-NonInteractive','-Command',script],capture_output=True,timeout=timeout)
    if result.returncode or len(result.stdout)>8192:
        raise ValueError('transport_observer_child_failed')
    value=json.loads(result.stdout)
    # Reuse the strict numeric x86 schema validation for both architectures;
    # verify observed real pointer size before normalizing its validation field.
    if not isinstance(value,dict) or type(value.get('pointer_bytes')) is not int or value['pointer_bytes']!=architecture//8:
        raise ValueError('transport_observer_architecture')
    validation=dict(value,pointer_bytes=4)
    proof=auth_readiness.admit(validation,expected_pid)
    proof['observation']=value
    proof.update(architecture_bits=architecture,database=database,script_sha256=hashlib.sha256(script.encode()).hexdigest(),
                 shell_sha256=prior.sha(shell),transport='named_instance' if endpoint.startswith('(localdb)') else 'owned_named_pipe',
                 endpoint_sha256=hashlib.sha256(endpoint.encode()).hexdigest())
    return proof


def classify_errorlog(data):
    if not isinstance(data,bytes) or len(data)>2*1024*1024:
        raise ValueError('owned_sql_errorlog_bound')
    # SQL logs may be UTF16-LE. Only fixed Boolean categories and numeric error
    # tuples leave this parser; no SQL/account/path/exception text is exported.
    text=data.decode('utf-16-le' if b'\0' in data[:128] else 'utf-8',errors='replace')
    numbers=re.findall(r'Error:\s*(\d{1,10}),\s*Severity:\s*(\d{1,2}),\s*State:\s*(\d{1,3})',text)
    lower=text.lower()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
        'numeric_errors':[{'number':int(a),'severity':int(b),'state':int(c)} for a,b,c in numbers[-64:]],
        'ready_marker':'ready for client connections' in lower,
        'termination_marker':'sql server is terminating' in lower,
        'insufficient_memory_marker':any(x in lower for x in ('insufficient system memory','insufficient memory','not enough memory')),
        'content_exported':False}


def process_snapshot(pid):
    proof=service.login.owned_process_snapshot(pid)
    if proof['exists']:
        code=("$p=Get-Process -Id "+str(pid)+" -ErrorAction Stop;ConvertTo-Json -Compress -InputObject @{working_set=[long]$p.WorkingSet64;private_bytes=[long]$p.PrivateMemorySize64;cpu_ticks=[long]$p.TotalProcessorTime.Ticks;threads=[int]$p.Threads.Count}")
        value=json.loads(prior.capture(['pwsh','-NoProfile','-NonInteractive','-Command',code]))
        if not isinstance(value,dict) or set(value)!={'working_set','private_bytes','cpu_ticks','threads'} or any(type(n) is not int or not 0<=n<2**63 for n in value.values()):
            raise ValueError('owned_sql_memory_shape')
        proof['memory']=value
    return proof


def run(args):
    if type(args.memory_limit_mb) is not int or args.memory_limit_mb not in (256,1024):
        raise ValueError('diagnostic_memory_policy')
    root,output=args.source_root.resolve(),args.output.resolve()
    identity=prior.require_hosted(root,output,args.expected_commit)
    output.mkdir(parents=True);runner=prior.Commands(output)
    proof=dict(identity,schema='coh-sql-readiness-transport-only-v1',passed=False,commands=runner.records,observations=[],
               authserver_started=False,encrypted_account_login_verified=False,shipping_server_modified=False,
               service_guard_disabled=False,connectivity_qualified=False,memory_limit_mb=args.memory_limit_mb,
               experiment_budget_seconds=1200,cleanup_reserved_seconds=300)
    instance='cohauth-ci-'+secrets.token_hex(12);created=False;localdb=sqlcmd=None
    temporary=Path(tempfile.mkdtemp(prefix='coh-sql-readiness-',dir=os.environ['RUNNER_TEMP']))
    private=RedactedCommands(runner.records,temporary,time.monotonic()+20*60)
    try:
        localdb,sqlcmd,proof['x86_odbc_driver']=service.tools()
        archive=temporary/'source.tar';runner.run('archive-original-source',['git','-C',root,'archive','--format=tar','--output='+str(archive),args.expected_commit,'upstream/ouroboros'],timeout=120)
        with tarfile.open(archive) as tar:tar.extractall(temporary/'source',filter='data')
        source=temporary/'source/upstream/ouroboros'
        if instance.casefold() in {x.strip().casefold() for x in prior.capture([localdb,'info']).splitlines()}:
            raise ValueError('owned_instance_already_exists')
        created=True;private.run('localdb-create',[localdb,'create',instance],timeout=60);private.run('localdb-start',[localdb,'start',instance],timeout=60)
        sql=[sqlcmd,'-S','(localdb)\\'+instance,'-E','-C','-b','-l','20','-t','120']
        proof['localdb_version']=private.numeric('localdb-version',[*sql,'-h','-1','-W','-Q',"SET NOCOUNT ON;SELECT CONVERT(varchar(100),SERVERPROPERTY('ProductVersion'));"],kind='version',timeout=150)
        pid=private.numeric('localdb-pid',[*sql,'-h','-1','-W','-Q',"SET NOCOUNT ON;SELECT CONVERT(int,SERVERPROPERTY('ProcessID'));"],kind='pid',timeout=150)
        proof['owned_sql_initial']=process_snapshot(pid)
        info=prior.capture([localdb,'info',instance]);pipe=pipe_from_info(info)
        proof['owned_pipe_sha256']=hashlib.sha256(pipe.encode()).hexdigest()
        def phase(name,database):
            private.remaining()
            entry={'phase':name,'process_before':process_snapshot(pid),'transports':[]}
            if not entry['process_before']['exists'] or entry['process_before']['started_utc_ticks'] != proof['owned_sql_initial']['started_utc_ticks']:
                raise ValueError('owned_sql_generation_changed')
            proof['observations'].append(entry)
            for architecture in (32,64):
                for endpoint in ('(localdb)\\'+instance,pipe):
                    observer_timeout=private.remaining(50)  # Budget expiry must abort the experiment.
                    try:observation=observe(instance,endpoint,architecture,database,pid,timeout=observer_timeout)
                    except Exception as error:observation={'healthy':False,'failure_kind':type(error).__name__,'architecture_bits':architecture,'database':database,'transport':'named_instance' if endpoint.startswith('(localdb)') else 'owned_named_pipe'}
                    entry['transports'].append(observation)
            private.remaining()
            entry['process_after']=process_snapshot(pid)
            if not entry['process_after']['exists'] or entry['process_after']['started_utc_ticks'] != proof['owned_sql_initial']['started_utc_ticks']:
                raise ValueError('owned_sql_generation_changed')
            log=Path(os.environ['LOCALAPPDATA'])/'Microsoft/Microsoft SQL Server Local DB/Instances'/instance/'error.log'
            if log.is_file() and not log.is_symlink():
                with log.open('rb') as stream:entry['sql_errorlog']=classify_errorlog(stream.read(2*1024*1024+1))
        phase('default_memory_before_schema','master')
        private.run('localdb-memory-bound',[*sql,'-Q',"EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'max server memory (MB)',"+str(args.memory_limit_mb)+";RECONFIGURE;"],timeout=150)
        phase('configured_memory_before_schema','master')
        private.run('original-schema-private', [*sql,'-i',source/'Assets/DBSchemas/cohauth.sql'],timeout=150)
        phase('after_original_schema','cohauth')
        credentials=temporary/'credentials';service.login.password_fixture.write_private_fixture(credentials)
        (credentials/'account.sql').write_text(service.login.profile.account_sql(),encoding='ascii')
        for file in ('credential.sql','account.sql'):private.run('public-seed-private-'+file.split('.')[0],[*sql,'-i',credentials/file],timeout=150)
        phase('after_original_public_seed','cohauth')
        private.remaining()
        proof['experiment_completed']=True
        proof['passed']=True
    except Exception as error:proof['failure']=service.safe_failure(error)
    finally:
        private.deadline=None  # Reserve the final five job minutes for bounded cleanup/receipt.
        try:proof['owned_localdb_cleanup_complete']=not created or prior.cleanup_owned_instance(private,sqlcmd,localdb,instance)
        except Exception:proof['owned_localdb_cleanup_complete']=False
        try:shutil.rmtree(temporary);proof['private_files_removed']=not temporary.exists()
        except Exception:proof['private_files_removed']=False
        try:proof['source_inputs_unchanged']=not prior.capture(['git','-C',root,'status','--porcelain','--untracked-files=no','--','upstream/ouroboros','native-android/engine/auth-interop'])
        except Exception:proof['source_inputs_unchanged']=False;proof['source_status_observation_failed']=True
        proof['passed']=proof['passed'] and all(proof.get(k) is True for k in ('owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged'))
        (output/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--expected-commit',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--memory-limit-mb',type=int,choices=(256,1024),default=256)
    result=run(parser.parse_args());print(json.dumps({'passed':result['passed'],'failure':result.get('failure'),'authserver_started':False}));raise SystemExit(0 if result['passed'] else 1)
