#!/usr/bin/env python3
"""Focused wrapper/file-owner controls; no original server or old qualifier."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    os.umask(0o077)
    core, fresh, probe, progress, summary, ledger = runtime.context()
    checks = 0
    processes = 0

    def need(ok):
        nonlocal checks
        checks += 1
        if not ok:
            raise AssertionError('FOCUSED_CONTROL_FAILED')

    def refuse(call):
        try:
            call()
        except (ValueError, OSError, probe.ProbeRefused):
            need(True)
            return
        need(False)

    # This callback intentionally doubles the producer parser. A's separately
    # pinned source/schema proof owns the production ledger format. These new
    # controls exercise B's actual file/child/GROUPS/public reconstruction.
    def parse(raw):
        value = json.loads(raw)
        ledger.require(type(value) is dict and set(value) == {'stage', 'groups_owner_bound'}
                       and value['stage'] in ('ACTIVE', 'FINAL_RETURN', 'REFUSED')
                       and type(value['groups_owner_bound']) is bool)
        return {'stage': value['stage'], 'groups_owner_bound': value['groups_owner_bound']}

    def report():
        return {'schema': 'coh-private-original-native-groups-run-v1', 'passed': True,
                'matching_groups_transaction_captured': True, 'cleanup_verified': True,
                'owned_process_groups_absent': True, 'private_character_state': True,
                'public_upload_permitted': False, 'source_generation_admitted': False,
                'world_authority': False, 'pair': {'schema': 'coh-original-native-groups-pair-v1',
                    'passed': True, 'exact_logical_packet_verified': True,
                    'same_source_selected_dbid_verified': True,
                    'actual_native_owned_receive_verified': True}}

    controls = []
    with tempfile.TemporaryDirectory(prefix='coh-initial-runtime-controls-') as name:
        base = Path(name)
        base.chmod(0o700)
        for index, body in enumerate((b'{"stage":"ACTIVE","groups_owner_bound":true}', b'')):
            directory = base / str(index)
            directory.mkdir(mode=0o700)
            owner = probe.precreate(directory / ledger.BASENAME)
            stdout = (directory / 'stdout').open('xb')
            stderr = (directory / 'stderr').open('xb')
            children, handles = [], [stdout, stderr]
            # OPEN_EXISTING writes one bounded synthetic numeric control. It is
            # an actual owned OS child, explicitly not an original Map PE.
            program = 'import os,sys;f=os.open(sys.argv[1],os.O_WRONLY);os.write(f,bytes.fromhex(sys.argv[2]));os.fsync(f);os.close(f);sys.stdin.buffer.read(1)'
            child = subprocess.Popen([sys.executable, '-c', program, str(owner.path), body.hex()],
                                     stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                     start_new_session=True)
            processes += 1
            children.append(child)
            try:
                probe.bind(owner, child, handles, children, handles)
                value, _, _ = ledger.collect(probe, parse, owner, child, report())
                need(value['state'] == 'REFUSED')  # actual child still live
                child.communicate(b'x', timeout=10)
                need(child.returncode == 0)
                value, _, _ = ledger.collect(probe, parse, owner, child, report())
                need(value['state'] == 'REFUSED')  # registered streams still open
                for stream in handles:
                    stream.close()
                value, binding, raw = ledger.collect(probe, parse, owner, child, report())
                need(value['state'] == ('VALID' if body else 'UNAVAILABLE'))
                if body:
                    need(value['ledger']['stage'] == 'ACTIVE')
                    need(raw == body and binding['retained_after_owned_cleanup'] is True)
                    need(not any(key in json.dumps(value) for key in ('owned_child_pid', 'file_inode', 'sha256')))
                    target = directory / 'retained'
                    target.mkdir(mode=0o700)
                    ledger.retain(target / ledger.BASENAME, raw, progress.read_private)
                    need(progress.read_private(target / ledger.BASENAME) == raw)
                    refuse(lambda: ledger.retain(target / ledger.BASENAME, raw, progress.read_private))
                    rollback = directory / 'rollback'
                    rollback.mkdir(mode=0o700)
                    def failed_read(*_):
                        raise ValueError('CONTROLLED_RETENTION_FAILURE')
                    refuse(lambda: ledger.retain(rollback / ledger.BASENAME, raw, failed_read))
                    need(not (rollback / ledger.BASENAME).exists()
                         and progress.read_private(target / ledger.BASENAME) == raw)
                    mutated = deepcopy(value)
                    mutated['private_path'] = 'CANARY_PRIVATE'
                    refuse(lambda: ledger.public(mutated, parse))
                    mutated = deepcopy(value)
                    mutated['world_authority'] = True
                    refuse(lambda: ledger.public(mutated, parse))
                    mutated = deepcopy(value)
                    mutated['same_precreated_file_verified'] = False
                    refuse(lambda: ledger.public(mutated, parse))
                    for field in ('cleanup_verified', 'owned_process_groups_absent', 'matching_groups_transaction_captured'):
                        failed = report()
                        failed[field] = False
                        need(ledger.collect(probe, parse, owner, child, failed)[0]['state'] == 'REFUSED')
                    failed = report()
                    failed['pair']['same_source_selected_dbid_verified'] = False
                    need(ledger.collect(probe, parse, owner, child, failed)[0]['state'] == 'REFUSED')
                    # An inode replacement with byte-identical contents is refused.
                    owner.path.rename(directory / 'retired-original')
                    owner.path.write_bytes(body)
                    owner.path.chmod(0o600)
                    need(ledger.collect(probe, parse, owner, child, report())[0]['state'] == 'REFUSED')
                    owner.path.unlink()
                    (directory / 'retired-original').rename(owner.path)
                    alias = directory / 'alias'
                    os.link(owner.path, alias)
                    need(ledger.collect(probe, parse, owner, child, report())[0]['state'] == 'REFUSED')
                    alias.unlink()
                    owner.path.write_bytes(b'x' * (ledger.MAXIMUM + 1))
                    need(ledger.collect(probe, parse, owner, child, report())[0]['state'] == 'REFUSED')
                    owner.path.write_bytes(b'{"stage":"ACTIVE","groups_owner_bound":false}')
                    need(ledger.collect(probe, parse, owner, child, report())[0]['state'] == 'REFUSED')
                controls.append(value['state'])
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=10)
                for stream in (*handles, child.stdin):
                    if stream is not None and not stream.closed:
                        stream.close()

    # Scoped bridge capability views must preserve the actual independently
    # admitted documents and restore every Python binding on all exits.
    marker = lambda *a, **k: None
    fake_core = SimpleNamespace(admit=SimpleNamespace(inspect=marker), native_input=marker,
                               orchestration_source_paths=marker, compiled_inputs_unchanged=marker,
                               start_owned=marker, finish_initial_observation=marker)
    fake_fresh = SimpleNamespace(precreate=marker, bind=marker, record=marker)
    actual_map = {'build_role': runtime.ACTUAL_MAP_ROLE,
                  'artifacts': {'MapServer.exe': {'bytes': 1, 'sha256': '0' * 64}}}
    actual_native = {'build_schema': runtime.ACTUAL_NATIVE_SCHEMA,
                     'initial_progress_compatibility_verified': True,
                     'build_receipt_sha256': '1' * 64}
    fake_recipe = SimpleNamespace(verify_artifact=lambda *a: (actual_map, {}))
    def optional_failure(*_):
        raise RuntimeError('CONTROLLED_OPTIONAL_FAILURE')
    fake_receive = SimpleNamespace(native_input=lambda *a: actual_native, finish=optional_failure)
    fake_core.initial_status = lambda state: {'state': state}
    fake_args = SimpleNamespace(compile_directory=Path('/control-map'), compile_receipt_sha256='0' * 64,
                                source_revision='0' * 40, native_capture=Path('/control-native'),
                                native_build_receipt=Path('/control-receipt'), native_build_receipt_sha256='1' * 64)
    try:
        with runtime.Bridge(fake_args, fake_core, fake_fresh, probe, progress, ledger,
                            fake_recipe, fake_receive, SimpleNamespace(parse=parse)) as bridge:
            mapped, _ = fake_core.admit.inspect(fake_args.compile_directory, runtime.ROOT, '0' * 64)
            need(mapped['build_role'] == runtime.MAP_CAPABILITY and actual_map['build_role'] == runtime.ACTUAL_MAP_ROLE)
            native = fake_core.native_input(fake_args.native_capture, fake_args.native_build_receipt, '1' * 64)
            need(native['build_schema'] == runtime.NATIVE_CAPABILITY
                 and actual_native['build_schema'] == runtime.ACTUAL_NATIVE_SCHEMA)
            refuse(lambda: fake_core.admit.inspect(Path('/wrong'), runtime.ROOT, '0' * 64))
            refuse(lambda: fake_core.native_input(fake_args.native_capture, fake_args.native_build_receipt, '2' * 64))
            bridge.diagnostic = {'untrusted': 'CANARY_PRIVATE'}
            finished = {}
            fake_core.finish_initial_observation(finished, native, Path('/received'), Path('/target'))
            need(finished['initial_observation'] == {'state': 'REFUSED'}
                 and finished['native_tool']['build_schema'] == runtime.ACTUAL_NATIVE_SCHEMA)
            need(finished['server_initial_diagnostic']['state'] == 'REFUSED'
                 and finished['server_initial_runtime']['server_build_role'] == runtime.ACTUAL_MAP_ROLE)
            raise RuntimeError('CONTROLLED_EXIT')
    except RuntimeError:
        pass
    need(not runtime.Bridge.active and fake_core.admit.inspect is marker)
    need(all(getattr(fake_core, name) is marker for name in ('native_input', 'orchestration_source_paths',
         'compiled_inputs_unchanged', 'start_owned', 'finish_initial_observation')))
    need(all(getattr(fake_fresh, name) is marker for name in ('precreate', 'bind', 'record')))
    # Integrate both actual source-owned production parsers/projectors against
    # synthetic fixed numeric fixtures; this does not execute their old mains.
    _, receive, source = runtime.suppliers()
    source_value = {'schema': source.SCHEMA, 'refusal': 'NONE', 'stop': 'ACTIVE',
                    'stage': 0, 'reached_mask': 0, 'last_ready': 0, 'ready_seen_mask': 0,
                    'pkt_send_result': -1, 'final_packet_bits': 0,
                    **{k: False for k in (*source.BOOLS, *source.FALSE)},
                    **{k: 0 for k in source.COUNTERS}}
    source_value.update(diagnostic_only=True, valid=True, groups_owner_bound=True)
    source_raw = json.dumps(source_value).encode()
    need(source.parse(source_raw) == source_value)
    receive_value = {'schema': receive.SCHEMA, 'diagnostic_only': True, 'refusal': 'NONE',
                     **{k: False for k in receive.FALSE}, **{k: 0 for k in (*receive.COUNTS, *receive.BOUNDS)},
                     **{k: True for k in receive.BOOLS}}
    receive_value['sample_count'] = 1
    receive_raw = json.dumps(receive_value).encode()
    need(receive.parse(receive_raw) == receive_value)
    with tempfile.TemporaryDirectory(prefix='coh-initial-projection-controls-') as name:
        directory = Path(name)
        directory.chmod(0o700)
        (directory / 'native').mkdir(mode=0o700)
        (directory / ledger.BASENAME).write_bytes(source_raw)
        (directory / 'native/receive-counters.json').write_bytes(receive_raw)
        full = report()
        full.update({k: True for k in summary.STATUS})
        full.update(capture_stage='COMPLETE', failure_stage='NONE', local_development_auth=True,
                    authserver_authenticated=False, private_canary='CANARY_PRIVATE')
        full['pair'].update(source_run_provenance_verified=False, cache_equivalence_verified=False,
                            source_generation_admitted=False, actor_identity_verified=False, world_authority=False)
        full['native_tool'] = actual_native
        full['source_sha256'] = {receive.RELATIVE: hashlib.sha256(Path(receive.__file__).read_bytes()).hexdigest()}
        full['initial_observation'] = {'same_groups_owner_verified': True,
                                       'retained_after_owned_cleanup': True}
        full['server_initial_runtime'] = {'schema': runtime.PRIVATE_SCHEMA,
            'server_build_role': runtime.ACTUAL_MAP_ROLE, 'native_build_schema': runtime.ACTUAL_NATIVE_SCHEMA,
            'source_revision': '0' * 40, 'compile_receipt_sha256': '0' * 64,
            'native_build_receipt_sha256': '1' * 64,
            'map_binary': actual_map['artifacts']['MapServer.exe'],
            'new_role_artifact_admission_verified': True,
            'compatibility_views_only_select_existing_lifecycle_hooks': True,
            'historical_artifact_equivalence_claimed': False, 'public_upload_permitted': False}
        full['compile_receipt_sha256'] = '0' * 64
        full['original_map_binary'] = actual_map['artifacts']['MapServer.exe']
        identity = {'schema': 'coh-private-original-native-groups-identity-v1',
                    'compile_receipt_sha256': '0' * 64, 'native_build_receipt_sha256': '1' * 64,
                    'source_sha256': full['source_sha256'], 'source_revision': '0' * 40,
                    'private_fresh_wine_prefix': True, 'private_fresh_pg_cluster': True,
                    'restored_existing_database_only': True, 'private_canary': 'CANARY_PRIVATE'}
        identity_raw = json.dumps(identity).encode()
        (directory / 'run-identity.json').write_bytes(identity_raw)
        full['run_identity_sha256'] = hashlib.sha256(identity_raw).hexdigest()
        diagnostic = ledger.empty('VALID')
        diagnostic.update({k: True for k in ledger.CONTEXT})
        diagnostic['ledger'] = source_value
        full['server_initial_diagnostic'] = diagnostic
        full['server_initial_private_binding'] = {'schema': 'coh-private-server-initial-ledger-binding-v1',
            'bytes': len(source_raw), 'sha256': hashlib.sha256(source_raw).hexdigest(),
            'retained_after_owned_cleanup': True, 'public_upload_permitted': False,
            'owned_child_pid': 999, 'private_canary': 'CANARY_PRIVATE'}
        full['receive_diagnostic'] = receive_value
        full['receive_private_binding'] = {'bytes': len(receive_raw), 'sha256': hashlib.sha256(receive_raw).hexdigest(),
            'retained_after_owned_cleanup': True, 'public_upload_permitted': False}
        projected = runtime.projection(full, directory, core, progress, summary, ledger, receive, source)
        need(projected['server_initial']['ledger']['stop'] == 'ACTIVE'
             and projected['native_receive'] == receive_value)
        need('CANARY_PRIVATE' not in json.dumps(projected)
             and 'owned_child_pid' not in json.dumps(projected))
        full['server_initial_runtime']['native_build_receipt_sha256'] = '2' * 64
        refuse(lambda: runtime.projection(full, directory, core, progress, summary, ledger, receive, source))
        full['server_initial_runtime']['native_build_receipt_sha256'] = '1' * 64
        full['server_initial_runtime']['compile_receipt_sha256'] = '2' * 64
        refuse(lambda: runtime.projection(full, directory, core, progress, summary, ledger, receive, source))
        full['server_initial_runtime']['compile_receipt_sha256'] = '0' * 64
        full['server_initial_runtime']['map_binary'] = {'bytes': 2, 'sha256': '0' * 64}
        refuse(lambda: runtime.projection(full, directory, core, progress, summary, ledger, receive, source))
        full['server_initial_runtime']['map_binary'] = actual_map['artifacts']['MapServer.exe']
        full['run_identity_sha256'] = '0' * 64
        refuse(lambda: runtime.projection(full, directory, core, progress, summary, ledger, receive, source))
        full['run_identity_sha256'] = hashlib.sha256(identity_raw).hexdigest()
        full['server_initial_private_binding']['sha256'] = '0' * 64
        refuse(lambda: runtime.projection(full, directory, core, progress, summary, ledger, receive, source))
        full['server_initial_private_binding']['sha256'] = hashlib.sha256(source_raw).hexdigest()
        full['receive_private_binding']['sha256'] = '0' * 64
        projected = runtime.projection(full, directory, core, progress, summary, ledger, receive, source)
        need(projected['native_receive']['state'] == 'REFUSED'
             and projected['server_initial']['state'] == 'VALID')
    names = [HERE_FILE for HERE_FILE in (Path(__file__), Path(runtime.__file__), Path(ledger.__file__),
             Path(core.__file__), Path(probe.__file__), Path(receive.__file__), Path(source.__file__))]
    result = {'schema': 'coh-server-initial-runtime-focused-controls-v1', 'passed': True,
              'checks': checks, 'actual_owned_synthetic_children': processes,
              'file_control_states': controls,
              'producer_schema_callback_doubled': True, 'original_server_executed': False,
              'actual_source_schema_and_receive_projector_synthetic_integration': True,
              'preliminary_harness_exception_catch_corrected_before_pass': True,
              'old_qualifier_entrypoints_executed': False, 'runtime_transaction_executed': False,
              'source_sha256': {p.resolve().relative_to(runtime.ROOT).as_posix():
                  hashlib.sha256(p.read_bytes()).hexdigest() for p in names},
              'world_authority': False}
    args.output.mkdir(mode=0o700, parents=True)
    (args.output / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('schema', 'passed', 'checks', 'actual_owned_synthetic_children', 'world_authority')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
