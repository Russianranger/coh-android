#!/usr/bin/env python3
"""Read-only cache/resource detail over the existing bounded Combined ZIP parser.

No runtime, profile, cache, device or APK mutation. Unknown cache outcomes stay
unknown. Only fixed enums, booleans, numbers and existing content hashes leave
this boundary; private identifiers, paths and raw exception text never do.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

_BASE_PATH = Path(__file__).resolve().parents[1] / 'diagnostics/continuation-20261016/analyze_startup.py'
_spec = importlib.util.spec_from_file_location('bounded_startup_base', _BASE_PATH)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
SCHEMA = 'coh-offline-startup-resources-v1'
GEOMETRY_STATUS = frozenset(('reused_verified_required_geometry', 'installed_verified_required_geometry'))
GRAPH_STATUS = frozenset(('reused_verified_graph', 'installed_verified_graph'))
DEFINITION_STATUS = frozenset(('installed', 'preserved_existing_native_caches', 'skipped_native_fallback'))
# Fixed source messages are mapped, never copied. Any OS error/path stays unknown.
REFUSALS = {
    'invalid_cache_pointer': 'invalid_cache_pointer',
    'cache_generation_limit_reached': 'generation_limit',
    'Atlas cache identity differs or prior owner did not prove cleanup': 'identity_or_cleanup',
    'Invalid Atlas cache marker': 'marker_invalid',
    'Atlas cache inventory differs': 'inventory_invalid',
    'Atlas cache data root changed': 'root_changed',
    'Atlas immutable anchor changed': 'anchor_changed',
    'Changed Atlas directory validation bound exceeded': 'directory_bound',
    'Changed Atlas directory entry bound exceeded': 'directory_entry_bound',
    'Private Atlas cache entry bound exceeded': 'private_entry_bound',
    'Private Atlas cache byte bound exceeded': 'private_byte_bound',
}
DATA_COUNTS = ('immutable_directory_checks', 'immutable_anchor_checks',
    'immutable_directory_metadata_queries', 'private_entries_checked', 'private_bytes',
    'changed_parent_directory_checks', 'changed_parent_entry_checks')
GRAPH_COUNTS = ('installed_files', 'input_files_checked', 'input_payload_bytes_hashed',
    'input_full_byte_proof_reused_files', 'input_full_byte_proof_reused_bytes')
SHARED_PROOF_POLICIES = frozenset(('no_current_process_owned_atlas_proof',
    'owned_source_generation_or_contract_missing', 'owned_source_generation_or_contract_changed',
    'exact_full_byte_proved_owned_immutable_provider'))
DEFINITION_REFUSALS = frozenset(('donor_absent', 'Linked server cache ancestor refused',
    'Case-conflicting server cache directory', 'Invalid server cache directory',
    'Case-conflicting server cache leaf', 'Invalid existing server cache leaf'))


def enum(value, choices):
    return value if type(value) is str and value in choices else 'unknown'


def projected_caches(report):
    """Pure projection contract for ORIGINAL creation_report fields.

    Current Combined reports omit most fields. This function does not recover
    them, infer them from elapsed time, or install a new producer. The numeric
    projection can be reused by a separately qualified producer later.
    """
    data = base.obj(base.obj(report.get('private_map_data')).get('server_data_cache'))
    graph = base.obj(report.get('atlas_beacon_graph'))
    definitions = base.obj(report.get('prepared_server_caches'))
    reason = data.get('reuse_refused')
    return {
        'server_data_receipt_present': bool(data),
        'server_data': {'reused': base.boolean(data.get('reused')),
            'refusal_present': 'reuse_refused' in data,
            'refusal_code': REFUSALS.get(reason, 'unknown') if type(reason) is str else 'unknown',
            **{key: base.number(data.get(key)) for key in DATA_COUNTS}},
        'definition_receipt_present': bool(definitions),
        'definitions': {'status': enum(definitions.get('status'), DEFINITION_STATUS),
            'installed_files': base.number(definitions.get('installed_files')),
            'preserved_existing_files': base.number(definitions.get('preserved_existing_files')),
            'fallback_reason_present': 'reason' in definitions,
            'fallback_reason_code': enum(definitions.get('reason'), DEFINITION_REFUSALS),
            'native_cache_consumption_proven': False},
        'beacon_receipt_present': bool(graph),
        'beacon': {'status': enum(graph.get('status'), GRAPH_STATUS),
            'archive_decoded': base.boolean(graph.get('archive_decoded')),
            **{key: base.number(graph.get(key)) for key in GRAPH_COUNTS},
            'input_inventory_walk': base.boolean(graph.get('input_inventory_walk')),
            'fingerprint_walk': base.boolean(graph.get('fingerprint_walk')),
            'shared_proof_policy': enum(graph.get('input_full_byte_proof_reuse_policy'), SHARED_PROOF_POLICIES),
            'preparation_elapsed_seconds': base.seconds(graph.get('preparation_elapsed_seconds')),
            'native_graph_consumption_proven': False}}


def cache_operations(projection):
    """Attribute reported operations without treating a decoder as a writer.

    A successful original cold beacon path always decodes the archive, even
    when every graph file already exists. Its final marker write is distinct
    from graph-payload writes. Missing fields remain unknown. These are source
    report statements, not fresh verification of cache or native consumption.
    """
    graph = projection['beacon']
    status, written = graph['status'], graph['installed_files']
    hashed, decoded = graph['input_payload_bytes_hashed'], graph['archive_decoded']
    reused_files, reused_bytes = (graph['input_full_byte_proof_reused_files'],
                                 graph['input_full_byte_proof_reused_bytes'])
    base.need(not (status == 'reused_verified_graph' and
        (written not in (None, 0) or hashed not in (None, 0) or decoded is True)), 'CACHE_RECEIPT_CONFLICT')
    base.need(not (status == 'installed_verified_graph' and decoded is False), 'CACHE_RECEIPT_CONFLICT')
    base.need(not (reused_files == 0 and reused_bytes not in (None, 0)), 'CACHE_RECEIPT_CONFLICT')
    base.need(not (reused_files is not None and graph['input_files_checked'] is not None
                  and reused_files > graph['input_files_checked']), 'CACHE_RECEIPT_CONFLICT')
    definitions = projection['definitions']
    base.need(not (definitions['status'] in ('preserved_existing_native_caches', 'skipped_native_fallback')
                  and definitions['installed_files'] not in (None, 0)), 'CACHE_RECEIPT_CONFLICT')
    return {'beacon': {
        'input_inventory_walk_reported': graph['input_inventory_walk'],
        'input_fingerprint_walk_reported': graph['fingerprint_walk'],
        'input_files_checked': graph['input_files_checked'],
        'input_payload_bytes_hashed': hashed,
        'full_byte_proof_reused_files': reused_files, 'full_byte_proof_reused_bytes': reused_bytes,
        'shared_proof_policy': graph['shared_proof_policy'],
        'archive_decode_reported': decoded,
        'graph_payload_files_written': written,
        'decoded_without_graph_payload_write': (decoded is True and written == 0)
                                               if decoded is not None and written is not None else None,
        'marker_write_source_implied': True if status == 'installed_verified_graph' else
                                       False if status == 'reused_verified_graph' else None,
        'source_path': 'warm_receipt' if status == 'reused_verified_graph' else
                       'archive_validation' if status == 'installed_verified_graph' else 'unknown',
        'suboperation_elapsed_seconds': None,
        'elapsed_seconds': graph['preparation_elapsed_seconds']},
        'definitions': {'payload_files_written': definitions['installed_files'],
            'preserved_existing_files': definitions['preserved_existing_files'],
            'fallback_reason_code': definitions['fallback_reason_code'],
            'archive_payload_bytes_hashed': None, 'suboperation_elapsed_seconds': None},
        'scope': 'existing_report_fields_and_pinned_producer_control_flow_not_fresh_cache_validation',
        'suboperation_time_inferred_from_phase_duration': False,
        'native_cache_consumption_proven': False}


def resource_boundaries(app):
    """Pair adjacent receiver-timestamped boundaries, never sum high waters.

    The ring contains at most 32 observations. A matching entered/leaving pair
    measures the Python coordinator's VmRSS delta, not MapServer RSS, PSS or
    Android+server overlap. Missing/disordered rows cannot fabricate a pair.
    """
    samples = base.rows(app.get('guest_resources', []), 32)
    pairs, pending, previous, clocks, unknown = [], None, -1, [], 0
    for row in samples:
        clock = base.number(row.get('elapsed_ms'))
        # Older fixtures/reports can omit clocks; retain their existing maxima
        # but refuse to create a paired interval across an unknown timestamp.
        if clock is None:
            pending = None; unknown += 1; continue
        base.need(clock >= previous, 'RESOURCE_CLOCK_ORDER')
        previous = clock; clocks.append(clock)
        stage, boundary = enum(row.get('stage'), base.STAGES), row.get('boundary')
        if stage == 'unknown' or boundary not in ('entered', 'leaving'):
            pending = None; unknown += 1; continue
        if boundary == 'entered':
            pending = (stage, clock, base.number(row.get('rss_kib')))
        elif pending is not None:
            if pending[0] == stage:
                after = base.number(row.get('rss_kib'))
                pairs.append({'stage': stage, 'entered_ms': pending[1], 'leaving_ms': clock,
                    'receiver_boundary_interval_ms': clock - pending[1],
                    'coordinator_rss_entered_kib': pending[2], 'coordinator_rss_leaving_kib': after,
                    'coordinator_rss_delta_kib': after - pending[2] if after is not None and pending[2] is not None else None,
                    'coordinator_peak_rss_high_water_kib': base.number(row.get('peak_rss_kib')),
                    'reaped_children_peak_rss_high_water_kib': base.number(row.get('children_peak_rss_kib'))})
            pending = None
    return {'retained_samples': len(samples), 'unusable_boundary_samples': unknown,
        'clocked_samples': len(clocks), 'paired_stages': pairs,
        'retained_span_ms': clocks[-1] - clocks[0] if len(clocks) >= 2 else None,
        'largest_adjacent_sample_gap_ms': max((b-a for a, b in zip(clocks, clocks[1:])), default=None),
        'scope': 'coordinator_self_rss_at_received_boundaries_not_server_process_tree',
        'whole_process_tree_transient_peak_measured': False, 'android_server_overlap_measured': False,
        'high_waters_summed': False}


def guest_detail(guest):
    if guest is None:
        return None
    base.guest_summary(guest)  # Reuse the existing schema/type/phase guards.
    geometry = base.obj(guest.get('geometry_preparation'))
    processes = base.rows(guest.get('processes', []), 512)
    sizes = [base.number(p.get('output_bytes')) for p in processes]
    base.need(all(v is not None and v <= base.LIMIT for v in sizes), 'PROCESS_OUTPUT_BOUND')
    geometry_time = geometry.get('elapsed_seconds')
    base.need(geometry_time is None or base.seconds(geometry_time) is not None, 'GEOMETRY_TIME')
    stages = base.rows(guest.get('stage_history', []), 128)
    normalized = []
    for row in stages:
        value = row.get('elapsed_seconds')
        base.need(value is None or base.seconds(value) is not None, 'GUEST_STAGE_TIME')
        normalized.append({'stage': enum(row.get('stage'), base.STAGES),
            'elapsed_seconds': value,
            'status': enum(row.get('status'), frozenset(('passed', 'failed', 'running')))})
    return {'geometry': {'status': enum(geometry.get('status'), GEOMETRY_STATUS),
            'elapsed_seconds': geometry_time,
            'input_files_checked': base.number(geometry.get('input_files_checked')),
            **{k: base.boolean(geometry.get(k)) for k in
               ('worker_used', 'worker_reaped', 'before_postgresql', 'before_wine')}},
        'cache_projection': projected_caches(guest),
        'cache_operations': cache_operations(projected_caches(guest)),
        'process_output': {'records': len(processes), 'sum_recorded_bytes': sum(sizes),
            'maximum_recorded_bytes': max(sizes) if sizes else None,
            'overflow_records': sum(p.get('output_overflow') is True for p in processes),
            'closed_capture_records': sum(p.get('output_capture_closed') is True for p in processes),
            'aggregate_live_peak_measured': False,
            'concurrent_process_overlap_measured': False},
        'guest_stages': normalized}


def timing(summary):
    ready = summary['ready_boundary_ms']
    values = {}
    # Fail closed on duplicate names: never sum duplicate/start-again events.
    for stage in ('local_dbserver_startup', 'local_atlas_startup'):
        candidates = [row['next_boundary_delta_ms'] for row in summary['stages'] if row['stage'] == stage]
        values[stage + '_ms'] = candidates[0] if len(candidates) == 1 else None
    known = all(v is not None for v in values.values()) and ready is not None and ready > 0
    combined = sum(values.values()) if known else None
    base.need(not known or combined <= ready, 'STAGE_TOTAL_EXCEEDS_READY')
    return {**values, 'db_and_atlas_ms': combined,
        'db_and_atlas_fraction': round(combined / ready, 6) if known else None,
        'other_startup_boundary_ms': ready - combined if known else None,
        'elapsed_is_received_stage_boundary_not_native_cpu': True}


def analyze(docs, provenance):
    result = base.analyze(docs, provenance)
    app = docs['combined-report.json']
    session = base.obj(app.get('server')).get('session_id')
    guests = [g for name in ('combined-server-latest-report.json', 'previous-session-combined-server-latest-report.json')
              if (g := docs.get(name)) is not None and base.guest_matches(g, session)]
    history = base.rows(base.obj(docs.get('combined-server-previous-attempts.json')).get('attempts', []), 4)
    summaries = [result['current'], *result['historical_attempts']]
    details = [guest_detail(guests[0] if guests else None)]
    for item in history:
        guest = base.obj(item.get('guest'))
        details.append(guest_detail(guest) if base.guest_matches(guest, item.get('session_id')) else None)
    attempts = []
    apps = [app, *[base.obj(item.get('app')) for item in history]]
    for index, (summary, detail) in enumerate(zip(summaries, details)):
        classification = base.obj(summary['guest_detail']).get('cache_classification', 'unknown')
        attempts.append({'scope': 'current' if index == 0 else 'historical',
            'history_index': None if index == 0 else index - 1,
            'version_code': summary['version_code'],
            'ready_boundary_ms': summary['ready_boundary_ms'],
            'cache_classification': classification,
            'timing': timing(summary), 'memory': summary['memory'],
            'guest_resources': summary['guest_resources'],
            'resource_boundaries': resource_boundaries(apps[index]),
            'preparation_seconds': base.obj(summary['guest_detail']).get('preparation_seconds', {}),
            'detail': detail})
    cohorts = {}
    for classification in ('warm_schema_restore_observed', 'cold_mirror_observed', 'unknown'):
        selected = [a for a in attempts if a['cache_classification'] == classification and a['ready_boundary_ms'] is not None]
        durations = [a['ready_boundary_ms'] for a in selected]
        cohorts[classification] = {'observations': len(selected),
            'minimum_ready_ms': min(durations) if durations else None,
            'maximum_ready_ms': max(durations) if durations else None,
            'same_version_code': len(set(a['version_code'] for a in selected)) <= 1 if selected else None}
    return {'schema': SCHEMA, 'provenance': provenance, 'attempts': attempts,
        'observational_cohorts': cohorts,
        'interpretation': {'cohorts_are_matched_repeatable_experiments': False,
            'missing_cache_receipts_inferred_from_timing': False,
            'startup_improvement_measured': False, 'whole_server_peak_memory_established': False,
            'allocation_cause_established': False, 'runtime_modified': False,
            'android_execution_required_for_offline_tool': False}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export_zip', type=Path)
    args = parser.parse_args(argv)
    try:
        docs, provenance = base.read_archive(args.export_zip)
        out = analyze(docs, provenance)
    except base.Rejected as error:
        print(json.dumps({'schema': SCHEMA, 'error': str(error)})); return 2
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print(json.dumps({'schema': SCHEMA, 'error': 'INPUT_UNAVAILABLE_OR_INVALID'})); return 2
    print(json.dumps(out, indent=2, sort_keys=True, allow_nan=False)); return 0


if __name__ == '__main__':
    sys.exit(main())
