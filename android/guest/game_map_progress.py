#!/usr/bin/env python3
"""Bounded, opt-in MapServer main-thread observations; never readiness proof."""
import hashlib
import json
import math
import os
import stat
import struct
import time

import diagnostic as base

ENVIRONMENT = 'COH_WINE_MAP_PROGRESS'
PROFILE = 'dispatch_progress_v1'
RECORD_BYTES = 128
MAPPING_BYTES = 4096
HEADER = struct.Struct('<8s10I')
HISTORY_LIMIT = 128
INITIAL_HISTORY = 16
EXPORT_LIMIT = 512 * 1024
SAMPLE_INTERVAL = 5
STAGES = {str(index): name for index, name in enumerate((
    'INITIALIZED', 'STARTUP', 'MAP_LOAD', 'DB_SETUP', 'READY_PUBLISH', 'READY_PUBLISHED',
    'RUNTIME_PRIORITY', 'RUNTIME_PRIORITY_DONE', 'HEAP_VALIDATE', 'HEAP_VALIDATED',
    'SG_VERIFY', 'SG_VERIFIED', 'CALLBACKS_ENABLE', 'CALLBACKS_ENABLED', 'RANDOM_SEED',
    'ITEM_POWER_REQUEST', 'ITEM_POWER_REQUESTED', 'ERROR_QUEUE_DRAIN', 'ERROR_QUEUE_DRAINED',
    'READY_STDOUT', 'LAUNCHER_CONTACT', 'LATE_STARTUP_DONE', 'LOOP_PRE_TICK', 'TICK_BEGIN',
    'TICK_TOP', 'DB_COMM', 'DB_COMM_DONE', 'FOLDER_CALLBACKS', 'FOLDER_CALLBACKS_DONE',
    'TICK_TOP_DONE', 'ENTITY_UPDATE', 'GAME_LOGIC', 'TICK_BOTTOM', 'TICK_DONE',
    'LOOP_POST_TICK', 'SLEEP', 'SLEEP_DONE'), 1)}


class PublicationPending(base.DiagnosticError):
    """No stable, positive even publication was available within the read bound."""


def validate_contract(contract, *, source=False):
    base.require(isinstance(contract, dict)
                 and contract.get('environment_variable') == ENVIRONMENT
                 and type(contract.get('format')) is int and contract['format'] == 1
                 and type(contract.get('record_bytes')) is int and contract['record_bytes'] == RECORD_BYTES
                 and type(contract.get('mapping_bytes')) is int and contract['mapping_bytes'] == MAPPING_BYTES
                 and contract.get('stages') == STAGES,
                 'MapServer progress contract differs')
    if source:
        metadata = {'magic_hex': b'COHMAP1\0'.hex(), 'byte_order': 'little',
            'offsets': {'magic': 0, 'format': 8, 'record_bytes': 12, 'process_id': 16,
                        'main_thread_id': 20, 'sequence': 24, 'stage': 28,
                        'tick_started': 32, 'tick_completed': 36, 'flags': 40,
                        'stage_count': 44, 'reserved': 48},
            'reserved_bytes': 80, 'disabled_by_default': True, 'writer': 'mapserver_main_thread',
            'stage_semantics': 'operation_about_to_run_unless_DONE_or_ED',
            'sequence_semantics': 'positive_even_stable_odd_updating_no_wrap',
            'tick_started_stage': 24, 'tick_completed_stage': 34,
            'counter_semantics': 'monotonic_no_wrap_completed_not_greater_than_started',
            'flags': {'1': 'sequence_or_counter_saturated_samples_unavailable'},
            'initialization_failure': 'requested_launch_exits_nonzero',
            'file_creation': 'new_absolute_drive_path_private_parent_required',
            'proves_readiness_or_game_success': False}
        base.require(all(type(contract.get(key)) is type(value) and contract[key] == value
                         for key, value in metadata.items()),
                     'MapServer progress source publication semantics differ')
    return contract


def decode_record(raw):
    base.require(isinstance(raw, bytes) and len(raw) == RECORD_BYTES,
                 'MapServer progress record size differs')
    magic, version, size, pid, tid, sequence, stage, started, completed, flags, count = HEADER.unpack(raw[:HEADER.size])
    base.require(magic == b'COHMAP1\0' and version == 1 and size == RECORD_BYTES
                 and pid > 0 and tid > 0 and count == len(STAGES) and str(stage) in STAGES
                 and not any(raw[HEADER.size:]),
                 'MapServer progress format, identity, stage or reserved bytes differ')
    base.require(flags == 0, 'MapServer progress counters saturated or flags differ')
    base.require(sequence > 0 and sequence % 2 == 0, 'MapServer progress publication is not stable')
    base.require(completed <= started <= completed + 1, 'MapServer progress tick counters differ')
    return {'format': version, 'windows_pid': pid, 'main_thread_id': tid, 'sequence': sequence,
            'stage_id': stage, 'stage': STAGES[str(stage)], 'tick_started': started,
            'tick_completed': completed, 'flags': flags, 'stage_count': count,
            'raw_record_hex': raw.hex(), 'raw_record_sha256': hashlib.sha256(raw).hexdigest()}


def compare_records(value, previous):
    base.require(all(value[key] == previous[key] for key in
                     ('windows_pid', 'main_thread_id', 'file_identity')),
                 'MapServer progress process, main thread or file identity changed')
    base.require(all(value[key] >= previous[key] for key in ('sequence', 'tick_started', 'tick_completed')),
                 'MapServer progress monotonic counters regressed')
    base.require(value['sequence'] != previous['sequence']
                 or value['raw_record_hex'] == previous['raw_record_hex'],
                 'MapServer progress payload changed without a fresh publication')
    return value['sequence'] > previous['sequence']


def read_record(path, previous=None):
    """Double-read the seqlock, bind the inode, and distinguish a stall from freshness."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        identity = os.fstat(descriptor)
        base.require(stat.S_ISREG(identity.st_mode) and identity.st_size == MAPPING_BYTES
                     and identity.st_uid == os.getuid() and identity.st_nlink == 1,
                     'MapServer progress is not an owned bounded regular file')
        raw = None
        for _ in range(16):
            first = os.pread(descriptor, RECORD_BYTES, 0)
            second = os.pread(descriptor, RECORD_BYTES, 0)
            if len(first) == RECORD_BYTES and first == second:
                sequence = HEADER.unpack_from(first)[5]
                if sequence and sequence % 2 == 0:
                    raw = first
                    break
            time.sleep(.001)
        current = os.stat(path, follow_symlinks=False)
        base.require(stat.S_ISREG(current.st_mode) and current.st_nlink == 1
                     and (current.st_dev, current.st_ino, current.st_size, current.st_uid) ==
                     (identity.st_dev, identity.st_ino, MAPPING_BYTES, os.getuid()),
                     'MapServer progress file changed identity during observation')
        if raw is None:
            raise PublicationPending('MapServer progress publication is incomplete or changing')
        value = dict(decode_record(raw), available=True, sampled_utc=base.utc(),
                     observed_monotonic=time.monotonic(),
                     file_identity={'device': identity.st_dev, 'inode': identity.st_ino},
                     source='opt-in MapServer main-thread publication', is_success_proof=False)
        advanced = compare_records(value, previous) if previous is not None else False
        value['freshness'] = 'initial' if previous is None else 'advanced' if advanced else 'unchanged'
        value['last_advance_monotonic'] = (value['observed_monotonic'] if previous is None or advanced
                                          else previous['last_advance_monotonic'])
        value['unchanged_seconds'] = round(value['observed_monotonic'] - value['last_advance_monotonic'], 3)
        return value
    finally:
        os.close(descriptor)


def evidence(producer):
    return {'enabled': True, 'format': 1, 'environment_variable': ENVIRONMENT,
            'record_bytes': RECORD_BYTES, 'mapping_bytes': MAPPING_BYTES, 'stages': dict(STAGES),
            'producer': producer, 'history_limit_per_phase': HISTORY_LIMIT,
            'initial_history_per_phase': INITIAL_HISTORY, 'sample_interval_seconds': SAMPLE_INTERVAL,
            'phases': {}, 'is_success_proof': False}


def append_sample(phase, sample):
    """Keep the initial startup window and a rolling tail, with explicit loss counts."""
    phase['sample_count'] += 1
    sample['sample_number'] = phase['sample_count']
    phase['samples'].append(sample)
    if len(phase['samples']) > HISTORY_LIMIT:
        del phase['samples'][INITIAL_HISTORY]
        phase['dropped_samples'] += 1


def validate_evidence(value, expected_producer, require_phase_progress=True):
    """Independently qualify exported raw observations without granting readiness."""
    validate_contract(value)
    base.require(value.get('enabled') is True and value.get('is_success_proof') is False
                 and value.get('producer') == expected_producer
                 and value.get('history_limit_per_phase') == HISTORY_LIMIT
                 and value.get('initial_history_per_phase') == INITIAL_HISTORY,
                 'MapServer progress producer or observation contract differs')
    phases = value.get('phases')
    base.require(isinstance(phases, dict) and set(phases) <= {'first', 'restart'}
                 and (not require_phase_progress or set(phases) == {'first', 'restart'}),
                 'MapServer progress phases differ')
    identities, paths = set(), set()
    def finite_clock(clock):
        return type(clock) in (int, float) and math.isfinite(clock) and clock >= 0

    for label, phase in phases.items():
        base.require(isinstance(phase, dict) and phase.get('fresh_path_before_launch') is True
                     and phase.get('process_label') == label + '-atlas'
                     and isinstance(phase.get('path_name'), str) and '/' not in phase['path_name']
                     and '\\' not in phase['path_name'] and len(phase['path_name']) <= 128
                     and phase['path_name'].startswith('coh-map-progress-' + label + '-')
                     and phase['path_name'].endswith('.bin') and phase['path_name'] not in paths
                     and finite_clock(phase.get('launch_monotonic')),
                     'MapServer progress fresh launch identity differs')
        paths.add(phase['path_name'])
        samples = phase.get('samples')
        base.require(isinstance(samples, list) and 0 < len(samples) <= HISTORY_LIMIT
                     and type(phase.get('sample_count')) is int
                     and type(phase.get('dropped_samples')) is int and phase['dropped_samples'] >= 0
                     and phase['sample_count'] == len(samples) + phase['dropped_samples'],
                     'MapServer progress history bounds differ')
        first = previous = None
        last_time, last_number = phase['launch_monotonic'], 0
        for sample in samples:
            base.require(isinstance(sample, dict) and sample.get('is_success_proof') is False
                         and type(sample.get('available')) is bool
                         and type(sample.get('sample_number')) is int
                         and last_number < sample['sample_number'] <= phase['sample_count']
                         and finite_clock(sample.get('observed_monotonic'))
                         and sample['observed_monotonic'] >= last_time
                         and isinstance(sample.get('reason'), str) and len(sample['reason']) <= 128,
                         'MapServer progress sample scope differs')
            last_number, last_time = sample['sample_number'], sample['observed_monotonic']
            if sample.get('available') is not True:
                continue
            try:
                decoded = decode_record(bytes.fromhex(sample.get('raw_record_hex', '')))
            except (TypeError, ValueError) as exc:
                raise base.DiagnosticError('MapServer progress raw record encoding differs') from exc
            base.require(all(type(sample.get(key)) is type(item) and sample[key] == item
                             for key, item in decoded.items()),
                         'MapServer progress decoded fields or digest differ')
            identity = sample.get('file_identity')
            base.require(isinstance(identity, dict) and set(identity) == {'device', 'inode'}
                         and all(type(item) is int and item >= 0 for item in identity.values()),
                         'MapServer progress file identity differs')
            base.require(sample.get('freshness') in ('initial', 'advanced', 'unchanged')
                         and finite_clock(sample.get('last_advance_monotonic'))
                         and phase['launch_monotonic'] <= sample['last_advance_monotonic'] <= sample['observed_monotonic']
                         and finite_clock(sample.get('unchanged_seconds'))
                         and sample['unchanged_seconds'] == round(sample['observed_monotonic'] - sample['last_advance_monotonic'], 3)
                         and (sample['freshness'] == 'unchanged'
                              or sample['last_advance_monotonic'] == sample['observed_monotonic']),
                         'MapServer progress sample freshness differs')
            if previous is not None:
                advanced = compare_records(sample, previous)
                base.require(sample['freshness'] != 'initial'
                             and sample['last_advance_monotonic'] >= previous['last_advance_monotonic'],
                             'MapServer progress advance time regressed')
                # A retained-history gap can hide an intervening advance. For
                # adjacent reads the exact classification must be reproducible.
                if sample['sample_number'] == previous['sample_number'] + 1:
                    base.require(sample['freshness'] == ('advanced' if advanced else 'unchanged')
                                 and (advanced or sample['last_advance_monotonic'] == previous['last_advance_monotonic']),
                                 'MapServer progress freshness is inconsistent with raw sequence')
            first = first or sample
            previous = sample
        base.require(last_number == phase['sample_count'], 'MapServer progress latest sample is missing')
        if first is not None:
            file_identity = tuple(first['file_identity'][key] for key in ('device', 'inode'))
            base.require(file_identity not in identities, 'MapServer progress phases reused a file identity')
            identities.add(file_identity)
        if require_phase_progress:
            base.require(first is not None and previous['tick_started'] > first['tick_started']
                         and previous['tick_completed'] > first['tick_completed'],
                         'MapServer progress has no separately observed completed tick advance: ' + label)
    base.require(len((json.dumps(value, indent=2) + '\n').encode()) <= EXPORT_LIMIT,
                 'MapServer progress export exceeds bound')
    return value
