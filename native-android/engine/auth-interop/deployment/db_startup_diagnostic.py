"""Read-only numeric diagnostics for an owned original DbServer startup refusal.

Never return SQL text, connection/user names, thread IDs, stacks, account data,
window titles or raw service console. All SQL runs in the already owned instance.
"""
import json
import os
import re
import subprocess
import tempfile

import hosted_auth_stage as prior

SQL_FIELDS=('user_tables','attribute_tables','dbserver_sessions','sleeping_sessions',
    'active_requests','waiting_requests','blocked_requests','wait_lock','wait_network',
    'wait_io','wait_memory','wait_threadpool','wait_other')


def sql_query(database,pid):
    if not re.fullmatch('cohdb_ci_[0-9a-f]{24}',database) or type(pid) is not int or not 1<=pid<=0xffffffff:
        raise ValueError('db_startup_diagnostic_owned_input')
    # host_process_id and original App=DBSERVER bind sessions to this process.
    # Only counts and fixed wait categories escape; no submitted query text.
    counts=["(SELECT COUNT(*) FROM "+database+".sys.tables WHERE is_ms_shipped=0)",
        "(SELECT COUNT(*) FROM "+database+".sys.tables WHERE name IN ('Attributes','BadgeStatsAttributes','PopHelpAttributes'))",
        'COUNT(s.session_id)',"COALESCE(SUM(CASE WHEN s.status='sleeping' THEN 1 ELSE 0 END),0)",
        'COUNT(r.session_id)','COALESCE(SUM(CASE WHEN r.wait_type IS NOT NULL THEN 1 ELSE 0 END),0)',
        'COALESCE(SUM(CASE WHEN r.blocking_session_id>0 THEN 1 ELSE 0 END),0)']
    categories=("r.wait_type LIKE 'LCK[_]%'","r.wait_type='ASYNC_NETWORK_IO'",
        "(r.wait_type LIKE 'PAGEIOLATCH[_]%' OR r.wait_type IN ('WRITELOG','IO_COMPLETION','ASYNC_IO_COMPLETION'))",
        "r.wait_type LIKE 'RESOURCE_SEMAPHORE%'","r.wait_type='THREADPOOL'")
    counts += ['COALESCE(SUM(CASE WHEN '+value+' THEN 1 ELSE 0 END),0)' for value in categories]
    counts += ['COALESCE(SUM(CASE WHEN r.wait_type IS NOT NULL AND NOT ('+' OR '.join(categories)+') THEN 1 ELSE 0 END),0)']
    return ("SET NOCOUNT ON;SELECT "+"+'|'+".join('CONVERT(varchar(12),'+value+')' for value in counts)
        +" FROM sys.dm_exec_sessions s LEFT JOIN sys.dm_exec_requests r ON s.session_id=r.session_id "
        +"WHERE s.is_user_process=1 AND s.program_name='DBSERVER' AND s.host_process_id="+str(pid)+';')


def admit_sql(text):
    if not re.fullmatch('[0-9]{1,6}(\\|[0-9]{1,6}){12}',text):
        raise ValueError('db_startup_diagnostic_sql_shape')
    result=dict(zip(SQL_FIELDS,map(int,text.split('|'))))
    if (result['attribute_tables']>3 or result['attribute_tables']>result['user_tables']
            or result['dbserver_sessions']>4096 or result['active_requests']>result['dbserver_sessions']
            or result['sleeping_sessions']>result['dbserver_sessions']
            or result['waiting_requests']>result['active_requests']
            or result['blocked_requests']>result['active_requests']
            or sum(result[k] for k in SQL_FIELDS[7:])!=result['waiting_requests']):
        raise ValueError('db_startup_diagnostic_sql_counts')
    return result


def observe_sql(sql,database,pid,directory):
    query=sql_query(database,pid)
    with tempfile.TemporaryFile(dir=directory) as output:
        result=subprocess.run([*map(str,sql),'-h','-1','-W','-Q',query],stdout=output,
            stderr=subprocess.DEVNULL,timeout=20)
        if result.returncode or os.fstat(output.fileno()).st_size>1024:
            raise ValueError('db_startup_diagnostic_sql_failed')
        output.seek(0)
        return admit_sql(output.read(1025).decode('ascii',errors='strict').strip())


def admit_process(value,pid):
    if (type(pid) is not int or not isinstance(value,dict)
            or set(value)!={'pid','cpu_ms','threads'} or type(value.get('pid')) is not int or value['pid']!=pid
            or type(value.get('cpu_ms')) is not int or not 0<=value['cpu_ms']<=86400000
            or not isinstance(value.get('threads'),list) or not 1<=len(value['threads'])<=4096):
        raise ValueError('db_startup_diagnostic_process_shape')
    states={str(i):0 for i in range(8)};reasons={str(i):0 for i in range(14)}
    for row in value['threads']:
        if (not isinstance(row,dict) or set(row)!={'state','wait_reason'}
                or type(row.get('state')) is not int or not 0<=row['state']<=7
                or type(row.get('wait_reason')) is not int
                or (row['state']==5 and not 0<=row['wait_reason']<=13)
                or (row['state']!=5 and row['wait_reason']!=-1)):
            raise ValueError('db_startup_diagnostic_thread_shape')
        states[str(row['state'])]+=1
        if row['state']==5:reasons[str(row['wait_reason'])]+=1
    return {'pid':pid,'cpu_ms':value['cpu_ms'],'thread_count':len(value['threads']),
        'thread_state_enum_counts':states,'wait_reason_enum_counts':reasons,
        'thread_ids_or_stacks_exported':False}


def observe_process(pid):
    if type(pid) is not int or not 1<=pid<=0xffffffff:raise ValueError('db_startup_diagnostic_owned_input')
    code=("$ErrorActionPreference='Stop';$p=Get-Process -Id "+str(pid)+
        ";$rows=@($p.Threads|ForEach-Object {$state=[int]$_.ThreadState;$reason=-1;"
        "if($state -eq 5){$reason=[int]$_.WaitReason};@{state=$state;wait_reason=$reason}});"
        "ConvertTo-Json -Compress -Depth 4 -InputObject @{pid=[long]$p.Id;cpu_ms=[long]($p.TotalProcessorTime.Ticks/10000);threads=$rows}")
    return admit_process(json.loads(prior.capture(['pwsh','-NoProfile','-NonInteractive','-Command',code])),pid)
