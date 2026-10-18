#!/usr/bin/env python3
"""Run exact original Auth/DB shard activation with recovered accepted schema.

The default establishes only original interserver registration. Separate typed
scopes may admit selected-grant or provisional development DB-list probes. No
checksum reference alias, version override or MapServer is supplied.
"""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import ntpath
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import auth_readiness
import auth_service_profile
import db_startup_diagnostic
import db_modal_diagnostic
import hosted_auth_login as login
import hosted_auth_stage as prior
import hosted_candidate_login as service
import hosted_db_checksum_candidate as db_build
from manual_runtime_preflight import PE
from sql_readiness_diagnostic import RedactedCommands
from verify_auth_acceptance import authenticated_handoff_prerequisite

HERE = Path(__file__).resolve().parent
DB_ARCHIVE = 'native-android/engine/auth-interop/evidence/independent-db-build-39000395572/artifact.zip'
DB_ARCHIVE_SHA = '2eb66715cb8b35d82580971b60734a92b48c91e2a557cb253d39b7fdafef6ee7'
DB_RECEIPT_SHA = '51e72ef676b3db845ec4f72d1a0e856f5f34b4470050ee388087c06e843a3334'
DB_BINARY_SHA = '9dd91e456484c3fde1d9832163c2bbdad97d6a3f4db4db6a7773fddffe3319c3'
SCHEMA_SHA = 'b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92'
PLATFORM_DLLS = {'odbc32.dll','iphlpapi.dll','ws2_32.dll','winmm.dll','advapi32.dll','user32.dll','gdi32.dll','kernel32.dll'}


@dataclass(frozen=True)
class DbCandidateGeneration:
    """Explicit selected-probe binding to one separately admitted derivative."""
    binary_sha256: str
    build_receipt_sha256: str

    def __post_init__(self):
        if (any(not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value)
                for value in (self.binary_sha256,self.build_receipt_sha256))
                or self.binary_sha256==DB_BINARY_SHA):
            raise ValueError('shard_selected_candidate_generation_pin')


def admit_selected_candidate(selected_scope, db_candidate):
    # A generic/old selected scope cannot silently inherit a different PE.
    from hosted_selected_shard_play import SelectedScope
    from hosted_db_threadname_readiness import DbCandidate
    generation=getattr(selected_scope,'db_candidate_generation',None)
    if (type(db_candidate) is not DbCandidate or type(selected_scope) is not SelectedScope
            or type(generation) is not DbCandidateGeneration
            or generation!=DbCandidateGeneration(db_candidate.binary_sha256,
                                                db_candidate.admission.get('receipt_sha256'))):
        raise ValueError('shard_new_candidate_selected_scope_unqualified')
    return generation


def admit_development_candidate(development_scope,db_candidate):
    # This explicit new scope cannot impersonate the selected-grant scope.
    from hosted_auth_db_development import DevelopmentScope
    from hosted_db_threadname_readiness import DbCandidate
    generation=getattr(development_scope,'db_candidate_generation',None)
    if (type(db_candidate) is not DbCandidate or type(development_scope) is not DevelopmentScope
            or type(generation) is not DbCandidateGeneration
            or generation!=DbCandidateGeneration(db_candidate.binary_sha256,
                                                db_candidate.admission.get('receipt_sha256'))):
        raise ValueError('shard_development_candidate_scope_unqualified')
    return generation


def recover_schema(root, output):
    # Reuse the existing complete recovery/acceptance chain. Do not regenerate
    # templates or introduce a second archive decoder/payload implementation.
    path = root / 'tools/android/dbserver/prepare_dbserver_schema.py'
    spec = importlib.util.spec_from_file_location('coh_shard_existing_schema_recovery', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = module.prepare(output, root=root)
    if prior.sha(output / 'schema-manifest.json') != SCHEMA_SHA:
        raise ValueError('shard_accepted_schema_manifest_changed')
    return manifest


def recover_db(root, output):
    archive = root / DB_ARCHIVE
    if archive.is_symlink() or archive.stat().st_size != 1088820 or prior.sha(archive) != DB_ARCHIVE_SHA:
        raise ValueError('shard_db_archive_identity')
    output.mkdir()
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        if set(names) != db_build.FILES | {'receipt.json'} or len(names) != len(set(names)):
            raise ValueError('shard_db_archive_members')
        for item in source.infolist():
            if item.file_size > prior.LOG_LIMIT or item.filename != Path(item.filename).name:
                raise ValueError('shard_db_archive_file_bound')
            (output / item.filename).write_bytes(source.read(item))
    admission = db_build.admit(output, DB_RECEIPT_SHA, DB_BINARY_SHA)
    imports = PE((output / db_build.BINARY).read_bytes()).imports()
    if set(imports) != PLATFORM_DLLS:
        raise ValueError('shard_db_nonplatform_imports')
    return dict(admission, archive_sha256=DB_ARCHIVE_SHA,
                platform_imports=sorted(imports), separate_runtime_dlls_required=False)


def auth_configuration(instance, ports, log):
    value = auth_service_profile.configuration(instance, 'ODBC Driver 17 for SQL Server', ports, log)
    # supportReconnect=true prevents SetAddress from marking the shard active.
    # Only the original explicit AS_SET_CONNECT path can activate this fixture.
    for before, after in (('UserData = false;', 'UserData = true;'),
                          ('DBHasClientPorts = false;', 'DBHasClientPorts = true;'),
                          ('supportReconnect = false;', 'supportReconnect = true;')):
        if value.count(before) != 1:
            raise ValueError('shard_auth_profile_source_changed')
        value = value.replace(before, after)
    return value


def db_configuration(instance, database, auth_port, project):
    if (not re.fullmatch('cohauth-ci-[0-9a-f]{24}', instance)
            or not re.fullmatch('cohdb_ci_[0-9a-f]{24}', database)
            or not re.fullmatch('coh-ci-[0-9a-f]{24}', project)
            or type(auth_port) is not int or not 20000 <= auth_port <= 59999):
        raise ValueError('shard_disposable_db_profile')
    connection = 'Driver={ODBC Driver 17 for SQL Server};Server=(localdb)\\' + instance + ';Trusted_Connection=Yes;Encrypt=No;'
    return ('ShardName CohDisposable\nAdvertisedIp 127.0.0.1\nLocalIp 127.0.0.1\nLocale en\n'
        'SqlDbProvider mssql\nSqlDbName ' + database + '\nSqlLogin "' + connection + '"\n'
        'SqlAllowDDL 1\nSqlAddAttributes 1\nSqlAddColumnOrTable 1\nSqlDeleteColumnOrTable 1\n'
        'SqlRebuildTable 1\nSqlAlterColumn 1\nUseFakeAuth 0\nDefaultAccessLevel 0\n'
        'AuthServer 127.0.0.1 ' + str(auth_port) + '\nUseQueueServer 0\nUseLogServer 0\n'
        'MaxPlayers 2\nMinPlayers 0\nClientProject ' + project + '\nDoNotPreloadCrashReportDLL 1\n'
        'DoNotLaunchBeaconMasterServer 1\nDoNotLaunchBeaconClients 1\nDoNotLaunchMapServerTSR 1\n'
        'DisableContainerBackups 1\nNoStats 1\nAssertMode Exit\n')


def scalar(sql, query, directory, timeout=20):
    # Only stage-owned constant queries are passed here; never export SQL text
    # or provider diagnostics. This observes a small integer, never account data.
    with tempfile.TemporaryFile(dir=directory) as stream:
        result = subprocess.run([*map(str, sql), '-h','-1','-W','-Q',query],
            stdout=stream, stderr=subprocess.DEVNULL, timeout=timeout)
        size = os.fstat(stream.fileno()).st_size
        if result.returncode or size > 1024:
            raise ValueError('shard_private_sql_scalar_failed')
        stream.seek(0)
        value = stream.read(1025).decode('ascii', errors='strict').strip()
        if not re.fullmatch('[0-9]{1,6}', value):
            raise ValueError('shard_private_sql_scalar_shape')
        return int(value)


def firewall(runner, name, binary, direction, add):
    if (not re.fullmatch('coh-shard-[0-9a-f]{24}-(auth|db)-(in|out)', name)
            or direction not in ('Inbound','Outbound') or "'" in str(binary)):
        raise ValueError('shard_firewall_owned_input')
    if add:
        code = ("$ErrorActionPreference='Stop';if(@(Get-NetFirewallRule -Name '" + name + "' -ErrorAction SilentlyContinue).Count){throw 'exists'};"
            "if(@(Get-NetFirewallProfile|Where-Object Enabled -eq $false).Count){throw 'inactive'};"
            "New-NetFirewallRule -Name '" + name + "' -DisplayName '" + name + "' -Direction " + direction
            + " -Action Block -Program '" + str(binary) + "' -Protocol Any -RemoteAddress '0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255' -Profile Any|Out-Null;"
            "if(!(Get-NetFirewallRule -Name '" + name + "' -ErrorAction Stop).Enabled){throw 'disabled'}")
    else:
        code = ("$ErrorActionPreference='Stop';$rule=Get-NetFirewallRule -Name '" + name + "' -ErrorAction SilentlyContinue;"
            "if($rule){if(($rule|Get-NetFirewallApplicationFilter).Program -ne '" + str(binary)
            + "' -or $rule.Direction -ne '" + direction + "' -or $rule.Action -ne 'Block'){throw 'owner'};$rule|Remove-NetFirewallRule};"
            "if(@(Get-NetFirewallRule -Name '" + name + "' -ErrorAction SilentlyContinue).Count){throw 'remains'}")
    runner.run('firewall-' + name[-8:] + ('-add' if add else '-remove'),
               ['pwsh','-NoProfile','-NonInteractive','-Command',code], timeout=45)


def owned_channel(auth_pid, db_pid, auth_port):
    code = ("ConvertTo-Json -Compress -InputObject @(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue|"
        "Where-Object {($_.OwningProcess -eq " + str(auth_pid) + " -or $_.OwningProcess -eq " + str(db_pid)
        + ") -and ($_.LocalPort -eq " + str(auth_port) + " -or $_.RemotePort -eq " + str(auth_port)
        + ")}|ForEach-Object {@{pid=[int]$_.OwningProcess;local=[string]$_.LocalAddress;remote=[string]$_.RemoteAddress;lp=[int]$_.LocalPort;rp=[int]$_.RemotePort}})")
    return admit_channel(json.loads(prior.capture(['pwsh','-NoProfile','-NonInteractive','-Command',code])), auth_pid, db_pid, auth_port)


def admit_channel(rows, auth_pid, db_pid, auth_port):
    if (type(auth_pid) is not int or type(db_pid) is not int or auth_pid == db_pid
            or min(auth_pid,db_pid) < 1 or type(auth_port) is not int or not 20000 <= auth_port <= 59999
            or not isinstance(rows,list) or len(rows) != 2):
        raise ValueError('shard_owned_channel_shape')
    for row in rows:
        if (not isinstance(row,dict) or set(row) != {'pid','local','remote','lp','rp'}
                or any(type(row[key]) is not int for key in ('pid','lp','rp'))
                or row['local'] != '127.0.0.1' or row['remote'] != '127.0.0.1'
                or not 1 <= row['lp'] <= 65535 or not 1 <= row['rp'] <= 65535):
            raise ValueError('shard_owned_channel_endpoint')
    auth = [row for row in rows if row['pid'] == auth_pid]
    db = [row for row in rows if row['pid'] == db_pid]
    if (len(auth) != 1 or len(db) != 1 or auth[0]['lp'] != auth_port or db[0]['rp'] != auth_port
            or auth[0]['rp'] != db[0]['lp']):
        raise ValueError('shard_owned_channel_pair')
    return {'loopback_pair_verified':True, 'auth_pid':auth_pid, 'db_pid':db_pid,
            'auth_internal_port':auth_port, 'db_ephemeral_port':db[0]['lp']}


def game_listener(db_pid):
    code = ("ConvertTo-Json -Compress -InputObject @(Get-NetUDPEndpoint -LocalPort 7000 -ErrorAction SilentlyContinue|"
            "ForEach-Object {@{pid=[int]$_.OwningProcess;port=[int]$_.LocalPort;address=[string]$_.LocalAddress}})")
    rows=json.loads(prior.capture(['pwsh','-NoProfile','-NonInteractive','-Command',code]))
    if (not isinstance(rows,list) or len(rows)!=1 or set(rows[0])!={'pid','port','address'}
            or type(rows[0]['pid']) is not int or rows[0]['pid']!=db_pid
            or type(rows[0]['port']) is not int or rows[0]['port']!=7000
            or rows[0]['address'] not in ('0.0.0.0','127.0.0.1')):
        raise ValueError('shard_db_game_listener_owner')
    return {'udp_port':7000,'owner_pid':db_pid,'actual_bind_address':rows[0]['address'],
            'nonloopback_ipv4_access_blocked_by_owned_firewall':True}


def service_image_path(path):
    value=str(path)
    drive,tail=ntpath.splitdrive(value)
    if (not re.fullmatch('[A-Za-z]:',drive) or not tail.startswith(('\\','/'))
            or len(value)>4096 or any(c in value for c in ('\0','\r','\n'))):
        raise ValueError('shard_service_expected_image_path')
    normalized=ntpath.normcase(ntpath.normpath(value))
    if ntpath.basename(normalized) not in ('authserver.exe','dbserver.exe'):
        raise ValueError('shard_service_expected_image_name')
    return normalized


def admit_service_process(value, pid, expected_path, previous=None):
    expected=service_image_path(expected_path)
    expected_name=ntpath.basename(expected)[:-4]
    if (type(pid) is not int or not 1<=pid<=0xffffffff
            or not isinstance(value,dict)
            or set(value)!={'pid','exists','name','started_utc_ticks','executable_path'}
            or type(value.get('pid')) is not int or value['pid']!=pid
            or value.get('exists') is not True
            or type(value.get('name')) is not str or value['name'].casefold()!=expected_name
            or type(value.get('started_utc_ticks')) is not int
            or not 0<value['started_utc_ticks']<=3155378975999999999
            or type(value.get('executable_path')) is not str
            or service_image_path(value['executable_path'])!=expected):
        raise ValueError('shard_service_process_identity')
    # Do not export a private absolute runner path; retain its exact normalized
    # identity alongside PID/name/start time for the same owned process lifetime.
    result={'pid':pid,'exists':True,'name':expected_name,
        'started_utc_ticks':value['started_utc_ticks'],
        'executable_path_sha256':hashlib.sha256(expected.encode()).hexdigest()}
    if previous is not None and (type(previous) is not dict
            or json.dumps(previous,sort_keys=True)!=json.dumps(result,sort_keys=True)):
        raise ValueError('shard_service_process_generation_changed')
    return result


def service_process_snapshot(child, expected_path, previous=None, expected_binary_sha256=None):
    pid=child.pid
    expected=service_image_path(expected_path)
    if type(pid) is not int or not 1<=pid<=0xffffffff or child.poll() is not None:
        raise ValueError('shard_owned_service_not_running')
    code=("$ErrorActionPreference='Stop';$p=Get-Process -Id "+str(pid)+
          " -ErrorAction SilentlyContinue;if($p){ConvertTo-Json -Compress -InputObject @{pid=[long]$p.Id;exists=$true;name=[string]$p.ProcessName;started_utc_ticks=$p.StartTime.ToUniversalTime().Ticks;executable_path=[string]$p.Path}}"
          "else{ConvertTo-Json -Compress -InputObject @{pid="+str(pid)+";exists=$false}}")
    value=json.loads(prior.capture(['pwsh','-NoProfile','-NonInteractive','-Command',code]))
    result=admit_service_process(value,pid,expected_path,previous)
    binary_sha=service.BINARY_SHA if ntpath.basename(expected)=='authserver.exe' else DB_BINARY_SHA
    if expected_binary_sha256 is not None:
        if (ntpath.basename(expected)!='dbserver.exe'
                or type(expected_binary_sha256) is not str
                or not re.fullmatch('[a-f0-9]{64}',expected_binary_sha256)):
            raise ValueError('shard_db_candidate_binary_pin')
        binary_sha=expected_binary_sha256
    if child.poll() is not None or prior.sha(expected_path)!=binary_sha:
        raise ValueError('shard_service_process_or_binary_changed')
    return result


def close_streams(handles):
    complete=True
    for handle in handles:
        try:handle.close()
        except Exception:complete=False
    return complete


def run(args, selected_scope=None, db_candidate=None, *, development_scope=None):
    if development_scope is not None:
        if selected_scope is not None:raise ValueError('shard_client_scopes_mutually_exclusive')
        admit_development_candidate(development_scope,db_candidate)
    operation_scope=selected_scope if development_scope is None else development_scope
    root, output = args.source_root.resolve(), args.output.resolve()
    identity = prior.require_hosted(root, output, args.expected_commit)
    prerequisite = authenticated_handoff_prerequisite(root, args.auth_success_archive.resolve())
    auth_admission = service.candidate.admit(args.auth_candidate_stage.resolve(), service.RECEIPT_SHA, service.BINARY_SHA)
    output.mkdir(parents=True)
    runner = prior.Commands(output)
    temporary = Path(tempfile.mkdtemp(prefix='coh-db-shard-',dir=os.environ['RUNNER_TEMP']))
    sql_runner = RedactedCommands(runner.records, temporary)
    nonce = secrets.token_hex(12)
    instance, database = 'cohauth-ci-'+nonce, 'cohdb_ci_'+nonce
    proof = dict(identity,schema='coh-owned-original-db-shard-activation-v1',passed=False,
        prior_auth_qualification=asdict(prerequisite),auth_candidate_admission=auth_admission,
        commands=runner.records,auth_only_login_repeated=False,client_login_attempted=False,
        selected_shard_play_verified=False,authenticated_db_map_handoff_verified=False,
        nondevelopment_version_admitted=False,checksum_reference_installed=False,
        checksum_policy_relaxed=False,shipping_profiles_modified=False,
        original_interserver_shard_activation_verified=False,private_console_exported=False)
    created=False;localdb=sqlcmd=None;children=[];rules=[];handles=[];pending_jobs=[]
    db_child=db=db_start=sql=None
    def observe_db(child,path,previous=None):
        if db_candidate is None:return service_process_snapshot(child,path,previous)
        return service_process_snapshot(child,path,previous,expected_binary_sha256=db_binary_sha)
    try:
        db_binary_name=db_build.BINARY if db_candidate is None else db_candidate.binary_name
        db_binary_sha=DB_BINARY_SHA if db_candidate is None else db_candidate.binary_sha256
        if db_candidate is not None:
            proof.update(schema=db_candidate.receipt_schema,accepted_runtime_replaced=False,
                         new_db_candidate_admission=db_candidate.admission)
            if development_scope is not None:
                proof['development_db_candidate_generation']=asdict(admit_development_candidate(development_scope,db_candidate))
            elif selected_scope is not None:
                proof['selected_db_candidate_generation']=asdict(admit_selected_candidate(selected_scope,db_candidate))
        elif selected_scope is not None and getattr(selected_scope,'db_candidate_generation',None) is not None:
            raise ValueError('shard_selected_candidate_without_candidate')
        if development_scope is not None:
            proof.update(schema='coh-owned-mssql-db-threadname-development-player-list-v1',
                provisional_development_db_player_list_verified=False,
                source_inferred_development_exception_used=False,server_development_skip_observed=False)
        elif selected_scope is not None:
            proof['schema']=('coh-owned-original-selected-shard-play-v1' if db_candidate is None
                             else 'coh-owned-mssql-db-threadname-selected-shard-play-v1')
        schema_dir = temporary/'accepted-schema'
        schema_manifest = recover_schema(root,schema_dir)
        proof['accepted_schema'] = {'manifest_sha256':SCHEMA_SHA,'files':len(schema_manifest['files']),
            'source_commit':schema_manifest['source_commit'],'data_commit':schema_manifest['data_commit']}
        proof['db_build_admission'] = (recover_db(root,temporary/'db-build') if db_candidate is None
                                      else db_candidate.recover(root,temporary/'db-build'))
        localdb,sqlcmd,proof['x86_odbc_driver'] = service.tools()
        if instance.casefold() in {s.strip().casefold() for s in prior.capture([localdb,'info']).splitlines()}:
            raise ValueError('shard_instance_already_exists')
        created=True
        sql_runner.run('localdb-create',[localdb,'create',instance],timeout=60)
        sql_runner.run('localdb-start',[localdb,'start',instance],timeout=60)
        sql=[sqlcmd,'-S','(localdb)\\'+instance,'-E','-C','-b','-l','20','-t','120']
        proof['localdb_version']=sql_runner.numeric('localdb-version',[*sql,'-h','-1','-W','-Q',"SET NOCOUNT ON;SELECT CONVERT(varchar(100),SERVERPROPERTY('ProductVersion'));"],kind='version')
        sql_runner.run('localdb-memory-bound',[*sql,'-Q',"EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'max server memory (MB)',1024;RECONFIGURE;"],timeout=150)
        sql_runner.run('load-auth-schema',[*sql,'-i',root/'upstream/ouroboros/Assets/DBSchemas/cohauth.sql'],timeout=150)
        sql_runner.run('create-owned-game-db',[*sql,'-Q','CREATE DATABASE '+database+';'],timeout=150)
        seed=temporary/'public-shard.sql'
        seed.write_text("USE cohauth;SET NOCOUNT ON;INSERT dbo.server(id,name,ip,inner_ip,ageLimit,pk_flag,server_group_id,client_port) VALUES(1,'Owned actual DbServer','127.0.0.1','127.0.0.1',0,0,1,7000);INSERT dbo.worldstatus(idx,status) VALUES(1,0);",encoding='ascii')
        sql_runner.run('seed-owned-shard',[*sql,'-i',seed],timeout=150)
        if operation_scope is not None:
            operation_scope.prepare(root,temporary,output,runner,proof,sql,sql_runner)
        sql_pid=sql_runner.numeric('localdb-pid',[*sql,'-h','-1','-W','-Q',"SET NOCOUNT ON;SELECT CONVERT(int,SERVERPROPERTY('ProcessID'));"],kind='pid')
        proof['x86_sql_readiness']=auth_readiness.observe(instance,sql_pid)
        if proof['x86_sql_readiness']['healthy'] is not True:raise ValueError('shard_x86_sql_not_ready')
        sql_start=login.owned_process_snapshot(sql_pid)
        if not sql_start['exists']:raise ValueError('shard_sql_process_generation_missing')
        auth_runtime,db_runtime=temporary/'auth-runtime',temporary/'db-runtime'
        (auth_runtime/'etc').mkdir(parents=True);(auth_runtime/'logs').mkdir()
        shutil.copytree(schema_dir,db_runtime);(db_runtime/'tools').mkdir();(db_runtime/'logs').mkdir()
        auth=auth_runtime/'AuthServer.exe';db=db_runtime/'DbServer.exe'
        shutil.copy2(args.auth_candidate_stage/service.candidate.BINARY,auth)
        shutil.copy2(temporary/'db-build'/db_binary_name,db)
        if prior.sha(auth)!=service.BINARY_SHA or prior.sha(db)!=db_binary_sha:raise ValueError('shard_runtime_binary_copy')
        ports,reservations=login.reserve_ports()
        try:
            (auth_runtime/'etc/config.txt').write_text(auth_configuration(instance,ports,auth_runtime/'logs'),encoding='ascii')
            (db_runtime/'data/server/db/servers.cfg').write_text(db_configuration(instance,database,ports[0],'coh-ci-'+nonce),encoding='ascii')
            proof['runtime_config_sha256']={'auth':prior.sha(auth_runtime/'etc/config.txt'),'db':prior.sha(db_runtime/'data/server/db/servers.cfg')}
            for role,binary in (('auth',auth),('db',db)):
                for suffix,direction in (('in','Inbound'),('out','Outbound')):
                    name='coh-shard-'+nonce+'-'+role+'-'+suffix
                    rules.append((name,binary,direction))
                    firewall(runner,name,binary,direction,True)
        finally:
            for reservation in reservations:reservation.close()
        job=(login.OwnedJob() if development_scope is None else development_scope.new_service_job());pending_jobs.append(job)
        auth_launch=subprocess.Popen if development_scope is None else job.popen
        auth_child=auth_launch([str(auth)],cwd=auth_runtime,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        children.append((auth_child,job));pending_jobs.remove(job);job.assign(auth_child)
        auth_start=service_process_snapshot(auth_child,auth)
        proof['owned_service_generations_start']={'auth':auth_start,'sql':sql_start}
        deadline=time.monotonic()+90
        while login.inspect_listeners(auth_child.pid)!=set(ports):
            if auth_child.poll() is not None or time.monotonic()>deadline:raise ValueError('shard_auth_listener_readiness')
            time.sleep(.25)
        status_query="SET NOCOUNT ON;SELECT COUNT(*) FROM cohauth.dbo.worldstatus WHERE idx=1 AND status=1;"
        if scalar(sql,status_query,temporary)!=0:raise ValueError('shard_active_before_db_process')
        proof['shard_inactive_before_db_process']=True
        log_path=temporary/'private-db-console.log';log=log_path.open('wb');handles.append(log)
        db_job=(login.OwnedJob() if development_scope is None else development_scope.new_service_job());pending_jobs.append(db_job)
        db_launch=subprocess.Popen if development_scope is None else db_job.popen
        db_child=db_launch([str(db),'-start','0'],cwd=db_runtime,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        children.append((db_child,db_job));pending_jobs.remove(db_job);db_job.assign(db_child)
        db_start=observe_db(db_child,db)
        proof['owned_service_generations_start']['db']=db_start
        deadline=time.monotonic()+300;ready=False
        while time.monotonic()<deadline:
            if any(child.poll() is not None for child,_ in children):raise ValueError('shard_owned_service_exited')
            files=[p for p in temporary.rglob('*') if p.is_file()]
            if sum(p.stat().st_size for p in files)>64*1024*1024:raise ValueError('shard_private_working_files_bound')
            if log_path.stat().st_size>8*1024*1024:raise ValueError('shard_private_console_bound')
            if b'DbServer Ready.' in log_path.read_bytes():ready=True;break
            time.sleep(.25)
        if not ready:raise ValueError('shard_db_ready_deadline')
        proof['original_db_ready_marker_seen']=True
        if scalar(sql,status_query,temporary)!=1:raise ValueError('shard_original_activation_not_observed')
        proof['owned_interserver_channel']=owned_channel(auth_child.pid,db_child.pid,ports[0])
        proof['owned_db_game_listener']=game_listener(db_child.pid)
        tables=scalar(sql,"SET NOCOUNT ON;SELECT COUNT(*) FROM "+database+".sys.tables WHERE is_ms_shipped=0;",temporary)
        proof['actual_game_database_user_tables']=tables
        if tables!=99:raise ValueError('shard_game_database_table_count')
        selected_result=None
        if operation_scope is not None:
            selected_result=operation_scope.exercise(temporary,proof,sql,ports,
                auth_child,db_child,auth,db,auth_start,db_start,sql_pid,sql_start)
        proof['owned_processes_before_stop']={'auth':service_process_snapshot(auth_child,auth,auth_start),
            'db':observe_db(db_child,db,db_start),'sql':login.owned_process_snapshot(sql_pid)}
        if proof['owned_processes_before_stop']['sql']!=sql_start:raise ValueError('shard_sql_process_generation_changed')
        proof['original_interserver_shard_activation_verified']=True
        if operation_scope is not None:
            if selected_result is not True:raise ValueError('shard_selected_scope_not_complete')
            proof['selected_shard_play_verified']=True
            if development_scope is not None:
                proof.update(provisional_development_db_player_list_verified=True,
                    source_inferred_development_exception_used=True)
        proof['passed']=True
    except Exception as error:
        proof['failure']=service.safe_failure(error)
        # Diagnose an actual owned startup refusal before terminating services.
        # Observer failure cannot prevent the original cleanup sequence.
        if db_child is not None and db_start is not None and sql is not None:
            diagnostic={'read_only':True,'raw_console_or_sql_exported':False}
            try:
                diagnostic['generation_before']=observe_db(db_child,db,db_start)
                diagnostic['sql']=db_startup_diagnostic.observe_sql(sql,database,db_child.pid,temporary)
                diagnostic['process']=db_startup_diagnostic.observe_process(db_child.pid)
                diagnostic['generation_after']=observe_db(db_child,db,db_start)
                diagnostic['complete']=True
            except Exception as observed:
                diagnostic['complete']=False;diagnostic['failure']=service.safe_failure(observed)
            proof['owned_db_startup_diagnostic']=diagnostic
            modal={'read_only':True,'raw_titles_controls_or_stacks_exported':False}
            try:
                modal['generation_before']=observe_db(db_child,db,db_start)
                if db_candidate is None:
                    modal['observation']=db_modal_diagnostic.observe(root,db_child.pid,temporary)
                    modal['complete']=True
                else:
                    # The old classifier's filename aliases/source map are tied
                    # to its old PE. A derivative needs a separately admitted
                    # modal policy before those matches can be attributed.
                    modal['complete']=False
                    modal['not_run']='modal_policy_bound_to_prior_checksum_only_pe'
                modal['generation_after']=observe_db(db_child,db,db_start)
            except Exception as observed:
                modal['complete']=False;modal['failure']=service.safe_failure(observed)
            proof['owned_db_modal_diagnostic']=modal
    finally:
        cleanup=True
        for child,job in reversed(children):
            try:cleanup=job.stop(child) and not login.inspect_listeners(child.pid) and cleanup
            except Exception:cleanup=False
        for job in pending_jobs:
            try:
                if development_scope is None:
                    cleanup=bool(job.kernel.CloseHandle(job.handle)) and cleanup;job.handle=None
                else:cleanup=job.close_unassigned() and cleanup
            except Exception:cleanup=False
        cleanup=close_streams(handles) and cleanup
        proof['owned_service_cleanup_complete']=cleanup
        firewall_ok=True
        for name,binary,direction in reversed(rules):
            try:firewall(runner,name,binary,direction,False)
            except Exception:firewall_ok=False
        proof['owned_firewall_cleanup_complete']=firewall_ok
        sql_ok=True
        if created:
            try:sql_runner.run('drop-owned-game-db',[sqlcmd,'-S','(localdb)\\'+instance,'-E','-C','-b','-l','20','-t','30','-Q',"IF DB_ID('"+database+"') IS NOT NULL BEGIN ALTER DATABASE "+database+" SET SINGLE_USER WITH ROLLBACK IMMEDIATE;DROP DATABASE "+database+";END"],timeout=45)
            except Exception:sql_ok=False
            sql_ok=prior.cleanup_owned_instance(sql_runner,sqlcmd,localdb,instance) and sql_ok
        proof['owned_localdb_cleanup_complete']=sql_ok
        if (temporary/'private-db-console.log').exists():
            console=temporary/'private-db-console.log'
            with console.open('rb') as stream:body=stream.read(8*1024*1024)
            proof['private_db_console_summary']={'bytes':console.stat().st_size,'inspected_prefix_bytes':len(body),'content_exported':False,
                'source_markers':{key:needle in body for key,needle in (
                    ('db_ready',b'DbServer Ready.'),('auth_version_received',b'AuthServer Git Commit Hash:'),
                    ('sql_connected',b'SQL server '),('checksum_reference_missing',b'game checksum = 0'),
                    ('loading_templates',b'Loading templates...'),('update_tables',b'Update tables...'),
                    ('clearing_teamups',b'Clearing teamups and invalid characters...'),
                    ('waiting_for_launchers',b'Waiting for launchers to link up...'),
                    ('sql_connection_gave_up',b'Giving up.'),('missing_input_error',b"Can't open"),
                    ('bind_error',b'Error binding'))}}
        try:shutil.rmtree(temporary);proof['private_files_removed']=not temporary.exists()
        except Exception:proof['private_files_removed']=False
        try:
            proof['source_inputs_unchanged']=(prior.capture(['git','-C',root,'rev-parse','HEAD'])==args.expected_commit
                and not prior.capture(['git','-C',root,'status','--porcelain','--untracked-files=no','--','upstream','native-android','tools']))
        except Exception:proof['source_inputs_unchanged']=False
        proof['passed']=proof['passed'] and all(proof.get(key) is True for key in (
            'owned_service_cleanup_complete','owned_firewall_cleanup_complete','owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged'))
        (output/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','output','auth-success-archive','auth-candidate-stage'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--expected-commit',required=True)
    value=run(parser.parse_args())
    print(json.dumps({key:value.get(key) for key in ('passed','failure','original_interserver_shard_activation_verified','selected_shard_play_verified','authenticated_db_map_handoff_verified')}))
    raise SystemExit(0 if value['passed'] else 1)
