#!/usr/bin/env python3
"""Observe the owned disposable SQL instance through x86 ODBC; never start services.

Only fixed numeric/Boolean results and SQLSTATE/native numbers leave the child.
This is a connection-health diagnostic, not encrypted account qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def script(instance):
    if not isinstance(instance, str) or not re.fullmatch(r'cohauth-ci-[0-9a-f]{24}', instance):
        raise ValueError('owned_instance_name_invalid')
    # Keep three connections open concurrently: initial login plus a two-member
    # pool. This observes connectivity without calling any auth stored procedure.
    return r'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';
$result=@{schema='coh-auth-x86-odbc-readiness-v1';pointer_bytes=[IntPtr]::Size;
 attempted_connections=0;opened_connections=0;query_succeeded=$false;
 sql_process_id=0;connections_closed=$false;diagnostic_completed=$false;errors=@()};
$connections=@();
try {
 if ([IntPtr]::Size -ne 4) { throw 'architecture' }
 for ($i=0;$i -lt 3;$i++) {
  $result.attempted_connections++;
  $connection=New-Object System.Data.Odbc.OdbcConnection;
  $connections+=,$connection;
  $connection.ConnectionString='Driver={ODBC Driver 17 for SQL Server};Server=(localdb)\INSTANCE;Database=cohauth;Trusted_Connection=Yes;Encrypt=No;';
  $connection.Open();$result.opened_connections++;
 }
 $command=$connections[2].CreateCommand();$command.CommandTimeout=5;
 try {$command.CommandText="SELECT CONVERT(int,SERVERPROPERTY('ProcessID'));";
  $result.sql_process_id=[int]$command.ExecuteScalar();$result.query_succeeded=$true;
 } finally {$command.Dispose()}
 $result.diagnostic_completed=$true;
} catch [System.Data.Odbc.OdbcException] {
 foreach ($item in $_.Exception.Errors) {
  if ($result.errors.Count -lt 16) {
   $state=[string]$item.SQLState;
   if ($state -cmatch '^[A-Z0-9]{5}$') {
    $result.errors+=@{sqlstate=$state;native_error=[int]$item.NativeError};
   }
  }
 }
 $result.diagnostic_completed=$true;
} catch { $result.diagnostic_completed=$false;
} finally {
 $closed=$true;
 foreach ($connection in $connections) {
  try {$connection.Close();$connection.Dispose()} catch {$closed=$false}
 }
 $result.connections_closed=$closed;
}
$result | ConvertTo-Json -Depth 4 -Compress;
'''.replace('INSTANCE', instance)


def admit(value, expected_pid):
    keys = {'schema', 'pointer_bytes', 'attempted_connections', 'opened_connections',
            'query_succeeded', 'sql_process_id', 'connections_closed', 'diagnostic_completed', 'errors'}
    if (type(expected_pid) is not int or not 1 <= expected_pid <= 0xffffffff
            or not isinstance(value, dict) or set(value) != keys
            or value['schema'] != 'coh-auth-x86-odbc-readiness-v1'
            or any(type(value[k]) is not int for k in ('pointer_bytes', 'attempted_connections', 'opened_connections', 'sql_process_id'))
            or any(type(value[k]) is not bool for k in ('query_succeeded', 'connections_closed', 'diagnostic_completed'))
            or value['pointer_bytes'] != 4
            or not 1 <= value['attempted_connections'] <= 3
            or not 0 <= value['opened_connections'] <= value['attempted_connections']
            or not 0 <= value['sql_process_id'] <= 0xffffffff
            or type(value['errors']) is not list or len(value['errors']) > 16):
        raise ValueError('x86_sql_readiness_receipt_shape')
    for error in value['errors']:
        if (not isinstance(error, dict) or set(error) != {'sqlstate', 'native_error'}
                or not isinstance(error['sqlstate'], str) or not re.fullmatch(r'[A-Z0-9]{5}', error['sqlstate'])
                or type(error['native_error']) is not int or not -(2**31) <= error['native_error'] < 2**31):
            raise ValueError('x86_sql_readiness_error_shape')
    healthy = (value['diagnostic_completed'] and value['connections_closed']
               and value['attempted_connections'] == value['opened_connections'] == 3
               and value['query_succeeded'] and value['sql_process_id'] == expected_pid
               and not value['errors'])
    return {'healthy': healthy, 'observation': value, 'expected_sql_process_id': expected_pid,
            'authserver_internal_pool_observed': False, 'encrypted_account_login_verified': False}


def observe(instance, expected_pid):
    program = script(instance)
    if type(expected_pid) is not int or not 1 <= expected_pid <= 0xffffffff:
        raise ValueError('owned_sql_process_id_invalid')
    if os.name != 'nt':
        raise ValueError('windows_x86_odbc_execution_required')
    shell = Path(os.environ['WINDIR']) / 'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
    # No arbitrary log output or exception text is retained, including on timeout.
    result = subprocess.run([str(shell), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', program],
                            capture_output=True, timeout=50)
    if result.returncode or len(result.stdout) > 8192:
        raise ValueError('x86_sql_readiness_child_failed')
    proof = admit(json.loads(result.stdout), expected_pid)
    proof['script_sha256'] = hashlib.sha256(program.encode()).hexdigest()
    proof['shell_sha256'] = hashlib.sha256(shell.read_bytes()).hexdigest()
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', required=True)
    parser.add_argument('--expected-sql-pid', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = observe(args.instance, args.expected_sql_pid)
    if args.output.exists():
        raise ValueError('new_readiness_receipt_required')
    args.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'healthy': proof['healthy'], 'encrypted_account_login_verified': False}))
    raise SystemExit(0 if proof['healthy'] else 1)
