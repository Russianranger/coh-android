#!/usr/bin/env python3
"""Nonshipping receive-candidate account suite; no builds or DB/Map services.

Requires separately admitted exact candidate and already-built normal/capped
probes. Fresh x86 ODBC readiness is mandatory before starting AuthServer.
"""
import argparse
import hashlib
import inspect
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
import hosted_auth_login as login
import hosted_receive_candidate as candidate

prior = login.prior
RECEIPT_SHA = '25ee2415a280e7b3800808824d95d05b862acca9d4d4879f5fccb5605d6a2451'
BINARY_SHA = '9cd262dd862d14bf2d696de65cb70f155f25473503d7fd0968de9969e0ac8003'
ARCHIVE_SHA = 'da7fa3172867eabd9a652d36a4545cb78e91983123f85d894d18a9b3bac8d04d'
INTACT_RECEIPT_SHA = 'd857ef8fd309149e92de8a8abe6423d0a8d13c338adc64990fbf8dcccefcfe5e'
INTACT_BINARY_SHA = '7cb5672c32c1d304efea9590366250437687e3b0c8c1fafae5e4ec7cf536f29c'
INTACT_ARCHIVE_SHA = 'aa7a1badbeb8926cec15009f7f87ebb797aa2345c0c97a183cd1e23866a3499b'


def admit_intact(directory, receipt_sha, binary_sha, root):
    """Caller pins reviewed historical receipt/binary; rebind source and build policy."""
    if (receipt_sha, binary_sha) != (INTACT_RECEIPT_SHA, INTACT_BINARY_SHA):
        raise ValueError('intact_reviewed_hashes_required')
    receipt, binary = directory / 'receipt.json', directory / 'coh-auth-intact.exe'
    if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size > 1024*1024 or prior.sha(receipt) != receipt_sha:
        raise ValueError('intact_receipt_identity')
    proof = json.loads(receipt.read_text())
    details = proof.get('intact_probe_build', {})
    pins = json.loads((login.HERE / 'probe-build-reuse-pins.json').read_text())
    names = set(pins['source_files_sha256']) | {'native-android/engine/auth-interop/deployment/windows/intact_probe.c'}
    actual_sources = {name: prior.sha(root / name) for name in names}
    if (proof.get('schema') != 'coh-hosted-auth-only-intact-baseline-v1'
            or proof.get('original_source_tree') != prior.ORIGINAL_TREE
            or details.get('source_files_sha256') != actual_sources
            or details.get('build_policy') != login.PROBE_BUILD_POLICY
            or details.get('send_cap') != 1024 or details.get('receive_cap') != 11
            or details.get('receiver_segmentation_controlled') is not False
            or details.get('openssl_source', {}).get('sha256') != login.OPENSSL_SHA256
            # Original write_text ran on Windows and retained CRLF file bytes.
            or details.get('fixture_header_sha256') != hashlib.sha256(login.profile.fixture_header().replace('\n', '\r\n').encode()).hexdigest()):
        raise ValueError('intact_source_policy_admission')
    for field, function in [('historical_project_generator_sha256', login.prepare_probe_project),
                            ('intact_project_generator_sha256', login.prepare_intact_probe_project),
                            ('build_function_sha256', login.build_intact_probe)]:
        if details.get(field) != hashlib.sha256(inspect.getsource(function).encode()).hexdigest():
            raise ValueError('intact_generator_admission')
    identity = login.probe_identity(binary)
    if identity['sha256'] != binary_sha or identity != details.get('binary'):
        raise ValueError('intact_binary_identity')
    return {'receipt_sha256': receipt_sha, 'binary': identity, 'prior_login_inherited': False,
            'source_files_sha256': actual_sources, 'rebuilt': False}


def safe_failure(error):
    return str(error) if isinstance(error, ValueError) and re.fullmatch('[a-z0-9_]+', str(error)) else type(error).__name__


def check_live(child, ports):
    if child.poll() is not None or login.inspect_listeners(child.pid) != set(ports):
        raise ValueError('candidate_owned_listeners_unavailable')


def exercise(probes, child, ports, runtime, proof):
    """Eight actual account cases; every result admitted before success advances."""
    for mode in ('normal', 'capped'):
        proof['probe_results'][mode] = {}
        for case in login.CASES:
            check_live(child, ports)
            login.private_logs_bounded(runtime / 'logs')
            # Only the fixed probe's exact numeric schema may enter an artifact.
            result = subprocess.run([str(probes[mode]), str(ports[1]), case], cwd=runtime,
                                    capture_output=True, timeout=25)
            if result.returncode not in (0, 1, 2, 3) or len(result.stdout) > 8192:
                raise ValueError('candidate_probe_child_failed')
            observation = json.loads(result.stdout)
            # Preserve only bounded known numeric fields from failed probes;
            # never serialize arbitrary child strings, extra fields or stderr.
            if isinstance(observation, dict):
                numeric = {k: observation[k] for k in ('state', 'protocol', 'received_frames', 'sent_bytes', 'failure_command', 'failure_reason', 'system_error', 'elapsed_ms')
                           if type(observation.get(k)) is int and -(2**31) <= observation[k] <= 2**32-1}
                proof.setdefault('probe_numeric_observations', {}).setdefault(mode, {})[case] = numeric
            accepted = login.admit_probe_result(observation, case)
            if result.returncode != 0:
                raise ValueError('candidate_probe_success_exit_mismatch')
            proof['probe_results'][mode][case] = accepted
            check_live(child, ports)
            if case == 'valid':
                proof['positive_modes_verified'].append(mode)
    proof['account_normal_and_capped_sends_verified'] = True


def stop_owned(child, job, sql_pid, proof):
    """Diagnostic failure never skips owned-job termination/handle cleanup."""
    okay = True
    proof['candidate_exit_code_before_stop'] = child.poll()
    try:
        proof['owned_job_members_before_stop'] = job.process_ids()
        proof['owned_sql_in_auth_job'] = sql_pid in proof['owned_job_members_before_stop']
        okay = not proof['owned_sql_in_auth_job']
    except Exception:
        proof['owned_job_member_diagnostic_complete'] = False
        okay = False
    try:
        proof['owned_authserver_job_stop_complete'] = job.stop(child)
    except Exception:
        proof['owned_authserver_job_stop_complete'] = False
    try:
        proof['owned_authserver_listeners_absent'] = not login.inspect_listeners(child.pid)
    except Exception:
        proof['owned_authserver_listeners_absent'] = False
    if not proof['owned_authserver_job_stop_complete']:
        try:
            child.kill(); child.wait(timeout=5)
        except Exception:
            pass
        # Close a still-owned handle even when stop raised before CloseHandle.
        try:
            if job is not None and job.handle:
                job.kernel.CloseHandle(job.handle); job.handle = None
        except Exception:
            pass
    return okay and proof['owned_authserver_job_stop_complete'] and proof['owned_authserver_listeners_absent']


def tools():
    """Retain exact previously qualified x86 driver; fail changed hosted images."""
    import winreg
    base = Path(os.environ['ProgramFiles'])
    def locate(name, pattern):
        candidates = sorted(base.glob(pattern), reverse=True)
        path = Path(shutil.which(name) or (str(candidates[0]) if candidates else ''))
        if not path.is_file():
            raise ValueError('qualified_localdb_tools_unavailable')
        return path
    localdb = locate('SqlLocalDB.exe', 'Microsoft SQL Server/*/Tools/Binn/SqlLocalDB.exe')
    sqlcmd = locate('sqlcmd.exe', 'Microsoft SQL Server/Client SDK/ODBC/*/Tools/Binn/SQLCMD.EXE')
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\ODBC\\ODBCINST.INI\\ODBC Driver 17 for SQL Server',
                        0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
        driver = Path(os.path.expandvars(winreg.QueryValueEx(key, 'Driver')[0]))
    identity = prior.pe_identity(driver, None)
    if identity['sha256'] != '319b6c3b0ab08dd92dc1e5ee6daf3def82503ebbc85944fc1c614cd7a1c7b729':
        raise ValueError('qualified_x86_odbc_driver_identity_changed')
    return localdb, sqlcmd, identity


def run(args):
    root, output = args.source_root.resolve(), args.output.resolve()
    identity = prior.require_hosted(root, output, args.expected_commit)
    admission = candidate.admit(args.candidate_stage.resolve(), RECEIPT_SHA, BINARY_SHA)
    odbc = login.admit_odbc_receipt(args.reuse_odbc_stage.resolve())
    fragment = login.admit_probe_reuse(args.reuse_probe_stage.resolve(), root)
    intact = admit_intact(args.intact_stage.resolve(), args.intact_receipt_sha256, args.intact_binary_sha256, root)
    # All artifact/source admission completes before service, firewall or SQL effects.
    output.mkdir(parents=True)
    runner = prior.Commands(output)
    proof = dict(identity, schema='coh-hosted-candidate-auth-only-v1', passed=False,
                 candidate_admission=admission, qualified_odbc_reuse=odbc,
                 capped_probe_admission=fragment, normal_probe_admission=intact,
                 positive_modes_verified=[], probe_results={}, candidate_started=False,
                 account_normal_and_capped_sends_verified=False,
                 encrypted_account_login_verified=False, authenticated_db_map_handoff_verified=False,
                 shipping_server_modified=False, db_checksum_policy_modified=False,
                 general_tcp_segmentation_accepted=False, receiver_segmentation_controlled=False,
                 private_service_logs_exported=False, private_credential_files_exported=False,
                 commands=runner.records, no_binary_rebuilt=True)
    instance = 'cohauth-ci-' + secrets.token_hex(12)
    temporary = Path(tempfile.mkdtemp(prefix='coh-candidate-login-', dir=os.environ['RUNNER_TEMP']))
    created, firewall_attempted, child, job, sql_pid = False, False, None, None, None
    localdb, sqlcmd, auth = None, None, None
    try:
        localdb, sqlcmd, proof['x86_odbc_driver'] = tools()
        proof['listener_projection_controls'] = login.qualify_listener_projection()
        archive = temporary / 'original.tar'
        runner.run('archive-original-source', ['git', '-C', root, 'archive', '--format=tar', '--output='+str(archive),
                                              args.expected_commit, 'upstream/ouroboros'], timeout=120)
        with tarfile.open(archive) as value:
            value.extractall(temporary / 'source', filter='data')
        source = temporary / 'source/upstream/ouroboros'
        proof['profile'] = login.profile.audit(root, source)
        if instance.casefold() in {v.strip().casefold() for v in prior.capture([localdb, 'info']).splitlines()}:
            raise ValueError('generated_instance_already_exists')
        created = True
        runner.run('localdb-create', [localdb, 'create', instance], timeout=60)
        runner.run('localdb-start', [localdb, 'start', instance], timeout=60)
        sql = [sqlcmd, '-S', '(localdb)\\' + instance, '-E', '-C', '-b', '-l', '20', '-t', '120']
        runner.run('localdb-version', [*sql, '-Q', "SET NOCOUNT ON;SELECT CONVERT(varchar(100),SERVERPROPERTY('ProductVersion'));"], timeout=150)
        if '17.0.4025.3' not in (output / 'localdb-version.log').read_text(errors='replace'):
            raise ValueError('qualified_localdb_version_changed')
        runner.run('localdb-memory-bound', [*sql, '-Q', "EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'max server memory (MB)',256;RECONFIGURE;"], timeout=150)
        # Schema tool errors can repeat source text; discard its output as private.
        login.private_command([*sql, '-i', source / 'Assets/DBSchemas/cohauth.sql'], timeout=150)
        runner.run('localdb-owned-process-id', [*sql, '-h', '-1', '-W', '-Q', "SET NOCOUNT ON;SELECT CONVERT(int,SERVERPROPERTY('ProcessID'));"], timeout=150)
        number = (output / 'localdb-owned-process-id.log').read_text().strip()
        if not re.fullmatch('[1-9][0-9]{0,9}', number) or int(number) > 0xffffffff:
            raise ValueError('owned_sql_process_id_shape')
        sql_pid = int(number)
        proof['owned_sql_before_start'] = login.owned_process_snapshot(sql_pid)
        if not proof['owned_sql_before_start']['exists']:
            raise ValueError('owned_sql_not_running')
        credentials = temporary / 'credentials'
        login.password_fixture.write_private_fixture(credentials)
        (credentials / 'account.sql').write_text(login.profile.account_sql(), encoding='ascii')
        for name in ('credential.sql', 'account.sql'):
            login.private_command([*sql, '-i', credentials / name], timeout=150)
        proof['x86_readiness_before_start'] = auth_readiness.observe(instance, sql_pid)
        if proof['x86_readiness_before_start']['healthy'] is not True:
            raise ValueError('candidate_x86_sql_not_ready')
        runtime = temporary / 'runtime'
        (runtime / 'etc').mkdir(parents=True); (runtime / 'logs').mkdir()
        auth = runtime / 'AuthServer.exe'
        shutil.copy2(args.candidate_stage / candidate.BINARY, auth)
        if prior.sha(auth) != BINARY_SHA:
            raise ValueError('candidate_runtime_copy_identity')
        probes = {'capped': args.reuse_probe_stage / 'coh-auth-only.exe', 'normal': args.intact_stage / 'coh-auth-intact.exe'}
        # Recheck probes immediately before execution; no source compilation.
        if prior.sha(probes['capped']) != fragment['native_probe']['sha256'] or prior.sha(probes['normal']) != intact['binary']['sha256']:
            raise ValueError('candidate_probe_copy_identity')
        ports, reservations = login.reserve_ports()
        try:
            (runtime / 'etc/config.txt').write_text(login.profile.configuration(instance, 'ODBC Driver 17 for SQL Server', ports, runtime / 'logs'), encoding='ascii')
            proof['configuration_sha256'] = prior.sha(runtime / 'etc/config.txt')
            firewall_attempted = True
            login.firewall_rule(runner, instance, auth, True)
            job = login.OwnedJob()
        finally:
            for sock in reservations:
                sock.close()
        child = subprocess.Popen([str(auth)], cwd=runtime, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proof['candidate_started'] = True
        job.assign(child)
        deadline = time.monotonic() + 90
        while True:
            login.private_logs_bounded(runtime / 'logs')
            if child.poll() is not None:
                raise ValueError('candidate_exited_before_readiness')
            listening = login.inspect_listeners(child.pid)
            if listening == set(ports):
                break
            if listening - set(ports):
                raise ValueError('candidate_unexpected_listener')
            if time.monotonic() >= deadline:
                try:
                    proof['x86_readiness_at_listener_timeout'] = auth_readiness.observe(instance, sql_pid)
                except Exception as error:
                    proof['x86_readiness_timeout_diagnostic_failure'] = safe_failure(error)
                raise ValueError('candidate_listener_deadline')
            time.sleep(.25)
        proof['owned_listener_ports'] = ports
        exercise(probes, child, ports, runtime, proof)
        proof['encrypted_account_login_verified'] = True
        proof['passed'] = True
    except Exception as error:
        proof['failure'] = safe_failure(error)
    finally:
        cleanup = True
        if child is not None:
            cleanup = stop_owned(child, job, sql_pid, proof)
        elif job is not None and job.handle:
            try:
                cleanup = bool(job.kernel.CloseHandle(job.handle)); job.handle = None
            except Exception:
                cleanup = False
        proof['owned_authserver_cleanup_complete'] = cleanup
        if sql_pid is not None:
            try:
                proof['owned_sql_after_auth_stop'] = login.owned_process_snapshot(sql_pid)
            except Exception as error:
                proof['owned_sql_after_stop_failure'] = safe_failure(error)
        try:
            if firewall_attempted:
                login.firewall_rule(runner, instance, auth, False)
            proof['owned_firewall_cleanup_complete'] = True
        except Exception:
            proof['owned_firewall_cleanup_complete'] = False
        try:
            proof['owned_localdb_cleanup_complete'] = not created or prior.cleanup_owned_instance(runner, sqlcmd, localdb, instance)
        except Exception:
            proof['owned_localdb_cleanup_complete'] = False
        try:
            shutil.rmtree(temporary)
            proof['private_files_removed'] = not temporary.exists()
        except Exception:
            proof['private_files_removed'] = False
        try:
            proof['source_inputs_unchanged'] = not prior.capture(['git', '-C', root, 'status', '--porcelain', '--untracked-files=no', '--', 'upstream/ouroboros', 'native-android'])
        except Exception:
            proof['source_inputs_unchanged'] = False
        proof['passed'] = proof['passed'] and all(proof.get(k) is True for k in ('owned_authserver_cleanup_complete', 'owned_firewall_cleanup_complete', 'owned_localdb_cleanup_complete', 'private_files_removed', 'source_inputs_unchanged'))
        (output / 'receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'output', 'candidate-stage', 'reuse-odbc-stage', 'reuse-probe-stage', 'intact-stage'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('expected-commit', 'intact-receipt-sha256', 'intact-binary-sha256'):
        parser.add_argument('--'+name, required=True)
    value = run(parser.parse_args())
    print(json.dumps({k: value.get(k) for k in ('passed', 'failure', 'encrypted_account_login_verified', 'authenticated_db_map_handoff_verified')}))
    raise SystemExit(0 if value['passed'] else 1)
