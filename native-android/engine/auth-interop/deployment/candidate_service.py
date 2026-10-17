#!/usr/bin/env python3
"""Strict inputs and numeric observations for the disposable corrected service."""
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil

import auth_readiness
import auth_service_profile as profile
import hosted_auth_stage as prior
import hosted_receive_candidate as receive_build

HERE = Path(__file__).resolve().parent


def admit_intact(directory, root):
    import hosted_auth_login as login
    pins = json.loads((HERE / 'intact-build-reuse-pins.json').read_text())
    for name, expected in pins['files'].items():
        path = directory / name
        if (path.is_symlink() or not path.is_file() or path.stat().st_size != expected['bytes']
                or path.stat().st_size > prior.LOG_LIMIT or prior.sha(path) != expected['sha256']):
            raise ValueError('intact_reuse_file_identity')
    receipt = json.loads((directory / 'receipt.json').read_text())
    if (receipt.get('schema') != 'coh-hosted-auth-only-intact-baseline-v1'
            or receipt.get('repository_commit') != pins['repository_commit']
            or receipt.get('original_source_tree') != prior.ORIGINAL_TREE
            or receipt.get('passed') is not False or receipt.get('failure') != 'original_authserver_listener_deadline'
            or receipt.get('encrypted_account_login_verified') is not False
            or receipt.get('source_inputs_unchanged') is not True
            or receipt.get('intact_probe_build') != pins['build']):
        raise ValueError('intact_reuse_scope')
    details = pins['build']
    for name, expected in details['source_files_sha256'].items():
        path = root / name
        if path.is_symlink() or not path.is_file() or prior.sha(path) != expected:
            raise ValueError('intact_reuse_source_identity')
    generators = {'historical_project_generator_sha256': login.prepare_probe_project,
                  'intact_project_generator_sha256': login.prepare_intact_probe_project,
                  'build_function_sha256': login.build_intact_probe}
    if (any(hashlib.sha256(inspect.getsource(function).encode()).hexdigest() != details[name]
            for name, function in generators.items()) or details['build_policy'] != login.PROBE_BUILD_POLICY
            or details['openssl_source']['sha256'] != login.OPENSSL_SHA256
            or details['send_cap'] != 1024 or details['receive_cap'] != 11
            or details['general_tcp_segmentation_accepted'] is not False):
        raise ValueError('intact_reuse_build_policy')
    # Reconstruct the generated fixture/project using the existing exact function.
    # Their paths are location-specific, so retained project SHA binds the original
    # build while function/source SHA binds the current generator contract.
    if details['fixture_header_sha256'] != hashlib.sha256(profile.fixture_header().encode('ascii').replace(b'\n', b'\r\n')).hexdigest():
        # text-mode writes in the original Windows run performed CRLF translation.
        raise ValueError('intact_reuse_fixture_header')
    for name in ('configure-intact-openssl','build-intact-openssl','configure-intact-probe','build-intact-probe'):
        commands = [row for row in receipt['commands'] if row.get('name') == name]
        if (len(commands) != 1 or type(commands[0].get('returncode')) is not int or commands[0]['returncode'] != 0
                or commands[0].get('log_sha256') != pins['files'][name + '.log']['sha256']
                or commands[0].get('log_truncated') is not False):
            raise ValueError('intact_reuse_build_receipt')
    binary = login.probe_identity(directory / 'coh-auth-intact.exe')
    if binary != details['binary']:
        raise ValueError('intact_reuse_binary_identity')
    manifest = json.loads((directory / 'intact-openssl-reuse/manifest.json').read_text())
    if (manifest.get('source') != details['openssl_source'] or manifest.get('build_policy') != details['build_policy']
            or manifest.get('files', {}).get('libcrypto.lib', {}).get('sha256') != details['openssl_static_library_sha256']):
        raise ValueError('intact_reuse_crypto_manifest')
    return {'run_id': pins['run_id'], 'binary': binary, 'receipt_sha256': prior.sha(directory / 'receipt.json'),
            'openssl_source': details['openssl_source'], 'openssl_static_library_sha256': details['openssl_static_library_sha256'],
            'crypto_manifest_sha256': prior.sha(directory / 'intact-openssl-reuse/manifest.json'),
            'crypto_rebuilt': False, 'prior_login_inherited': False}


def observe_sql(proof, phase, instance, expected_pid):
    if phase not in ('before_authserver','during_readiness','listener_timeout','after_listeners'):
        raise ValueError('candidate_readiness_phase')
    observations = proof.setdefault('independent_x86_odbc_readiness', {})
    if phase in observations:
        raise ValueError('candidate_readiness_repeated_phase')
    try:
        observation = auth_readiness.observe(instance, expected_pid)
    except Exception as error:
        # No driver messages or subprocess output leave this boundary.
        observations[phase] = {'healthy': False, 'observation_failed': True,
                               'failure_kind': type(error).__name__, 'encrypted_account_login_verified': False}
        raise ValueError('candidate_x86_odbc_observation_failed') from None
    observations[phase] = observation
    if observation['healthy'] is not True:
        raise ValueError('candidate_x86_odbc_not_ready')
    return observation


def copy_candidate(directory, receipt_sha256, binary_sha256, destination):
    admission = receive_build.admit(directory, receipt_sha256, binary_sha256)
    shutil.copy2(directory / receive_build.BINARY, destination)
    if prior.pe_identity(destination, 2) != admission['binary']:
        raise ValueError('candidate_service_binary_copy_identity')
    return admission


def run_probes(proof, runner, probes, port, runtime, output, ensure_owned):
    import hosted_auth_login as login
    if set(probes) != {'fragmented_7','normal_1024'}:
        raise ValueError('candidate_probe_schedules')
    proof['candidate_schedule_results'] = {}
    proof['encrypted_login_schedules'] = {}
    for schedule in ('fragmented_7','normal_1024'):
        results = proof['candidate_schedule_results'][schedule] = {}
        for case in login.CASES:
            ensure_owned()
            login.private_logs_bounded(runtime / 'logs')
            name = 'probe-candidate-' + schedule + '-' + case
            runner.run(name, [probes[schedule], str(port), case], cwd=runtime, timeout=25, allowed=(0,1,2,3))
            result = json.loads((output / (name + '.log')).read_text())
            proof.setdefault('candidate_probe_observations', {}).setdefault(schedule, {})[case] = result
            results[case] = login.admit_probe_result(result, case)
            ensure_owned()
            if case == 'valid':
                proof['encrypted_login_schedules'][schedule] = True
                proof['encrypted_account_login_verified'] = True
    proof['fragmented_and_normal_suite_complete'] = True
    proof['general_tcp_segmentation_accepted'] = False
