#!/usr/bin/env python3
"""Only new ordered-fragment + receive-report scenarios on Android13/JNI/UDP.

The prior driver supplies bounded ADB/UI/SAF/peer cleanup helpers. Neither its
run_focused() nor any historical framework or native test suite is called.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile
from interop_emulator_check import InteropCheck, numeric_snapshot, unchanged_observations, IDLE_REPORT, sha, need, ROOT
from emulator_check import PACKAGE, MAIN, installed_apk_contract
from package_check import BUILD_PROFILES, check_build_identity
from interop_probe_contract import separate_current_probes
from report_diagnostic_contract import separate_report_extension

COUNTERS = ('udp_datagrams_received udp_peer_rejects udp_truncated udp_empty udp_malformed udp_unsupported '
            'udp_receive_budget_exhausted link_received link_duplicates link_malformed link_unsupported '
            'link_queue_limits link_fragment_expirations link_timeouts').split()
GAUGES = ('rx_pending fragment_groups decode_failure_kind decode_compressed_bytes decode_declared_raw_bytes '
          'decode_output_budget sample_count max_rx_pending_sampled max_fragment_groups_sampled').split()
REFUSED_AUTHORITY = ('command_specific_emission_proved server_receipt_proved source_generation_admitted '
                    'complete_initial_character actor_publication ack_permitted world_authority').split()
MEMORY_PHASES = {'COLD_STARTUP', 'SERVER_READY', 'NATIVE_CONNECTION', 'DIAGNOSTIC', 'RETURN', 'PAUSE', 'RESUME', 'FINAL_CLEANUP', 'SERVER_STOPPED'}


def admit_runtime_revision(head, candidate, proof_path):
    if candidate is None and proof_path is None:
        return head, None
    need(candidate is not None and proof_path is not None and re.fullmatch('[0-9a-f]{40}', candidate) is not None, 'exact package reuse requires candidate revision and source admission')
    raw = proof_path.read_bytes()
    need(len(raw) <= 16 * 1024 * 1024, 'source admission exceeds bound')
    proof = json.loads(raw)
    need(proof.get('schema') == 'coh-combined-exact-apk-requalification-v1' and proof.get('passed') is True, 'source admission schema/status differs')
    need(proof.get('candidate_source_revision') == candidate and proof.get('qualification_source_revision') == head and proof.get('runtime_and_build_inputs_unchanged') is True, 'source admission does not bind exact unchanged runtime and current driver')
    return candidate, sha(raw)


def app_uid_cgroup(value, uid):
    need(isinstance(value,dict) and value.get('uid')==uid and value.get('status') in ('observed','unavailable'), 'UID cgroup observation')
    need(value.get('source')=='proc/self/cgroup and proc/self/mountinfo'
         and value.get('scope')=='kernel UID-named cgroup charge; not same-UID RSS/PSS or whole-device RAM', 'cgroup accounting scope')
    if value['status']=='unavailable':
        need(value.get('charge_bytes') is None and type(value.get('reason')) is str
             and re.fullmatch('[A-Z_]{1,80}',value['reason']) is not None, 'unknown cgroup charge invented')
        return
    need(type(value.get('charge_bytes')) is int and 0 <= value['charge_bytes'] < 1<<63, 'cgroup charge units/domain')
    need(value.get('counter') in ('memory.current','memory.usage_in_bytes')
         and (value.get('hierarchical_accounting') is None or type(value['hierarchical_accounting']) is bool), 'cgroup memory controller')
    paths={}
    for key in ('counter_path','membership_path','mount_point','mount_root'):
        item=value.get(key);need(type(item) is str and item.startswith('/') and len(item)<=512
             and all(32<=ord(c)<=126 for c in item) and '..' not in Path(item).parts and '.' not in item.split('/'), 'cgroup source path')
        paths[key]=Path(item)
    prefixes=paths['membership_path'].parents
    group=paths['membership_path'] if paths['membership_path'].name=='uid_'+str(uid) else next((p for p in prefixes if p.name=='uid_'+str(uid)),None)
    need(group is not None and (group==paths['mount_root'] or paths['mount_root'] in group.parents), 'UID cgroup root association')
    expected=paths['mount_point']/group.relative_to(paths['mount_root'])/value['counter']
    need(paths['counter_path']==expected, 'cgroup mount mapping')
    if value['counter']=='memory.current':
        need(value.get('counter_semantics')=='v2_hierarchical_charge_bytes' and value['hierarchical_accounting'] is True, 'v2 cgroup semantics')
    else:need(value.get('counter_semantics')=='v1_approximate_charge_bytes', 'v1 cgroup semantics')


def process_aggregation(value, rows):
    aggregate=value.get('aggregation')
    need(isinstance(aggregate,dict) and aggregate.get('scope')=='all_scanned_same_uid_processes', 'process aggregation scope')
    need(aggregate.get('directory_entry_limit')==8192 and type(aggregate.get('directory_entries_scanned')) is int
         and 0 <= aggregate['directory_entries_scanned'] <= 8192, 'process scan bound')
    categories=aggregate.get('categories');roles=('ANDROID_APP_AND_NATIVE_CLIENT','WINE_SERVERS','POSTGRESQL','OTHER_APP_UID')
    need(isinstance(categories,dict) and set(categories)==set(roles), 'process categories')
    unclassified=aggregate.get('role_unclassified_processes')
    need(type(unclassified) is int and 0 <= unclassified <= 8193, 'process role completeness')
    total=aggregate.get('total')
    for name,summary in [('total',total)]+list(categories.items()):
        need(isinstance(summary,dict), 'process summary')
        need(all(type(summary.get(k)) is int and 0 <= summary[k] <= 8193 for k in
                 ('process_count','missing_rss_processes','missing_pss_processes','zombie_processes')), 'process category count domain')
        count=summary['process_count'];flags=summary.get('reason_flags')
        need(type(flags) is int and 0 <= flags <= 127, 'process category reason flags')
        need(all(summary[k] <= count for k in ('missing_rss_processes','missing_pss_processes','zombie_processes')), 'process category missing count')
        for metric,bit in [('rss',2),('pss',4)]:
            observed=summary.get('observed_'+metric+'_bytes');measured=summary.get(metric+'_bytes');complete=summary.get(metric+'_complete')
            need(observed is None or type(observed) is int and 0 <= observed < 1<<63, 'process aggregate sum domain')
            known_count=count-summary['missing_'+metric+'_processes']
            need(known_count>=8192 if observed is None else observed<=known_count*(1<<50), 'aggregate exceeds measured process domains')
            expected=(value['scan_complete'] and value['expected_roles_observed'] and summary['missing_'+metric+'_processes']==0
                      and observed is not None and (name=='total' or unclassified==0))
            need(type(complete) is bool and complete==expected, 'process aggregate completeness')
            need((type(measured) is int and measured==observed) if complete else measured is None, 'process aggregate total')
            need(bool(flags&bit)==(summary['missing_'+metric+'_processes']>0), 'process metric absence reason')
        need(bool(flags&1)==(not value['scan_complete']) and bool(flags&64)==(not value['expected_roles_observed'])
             and bool(flags&32)==(name!='total' and unclassified>0)
             and bool(flags&8)==(summary['observed_rss_bytes'] is None or summary['observed_pss_bytes'] is None), 'process completeness reason')
    need(total['process_count']==sum(c['process_count'] for c in categories.values()) and unclassified<=total['process_count'], 'process category partition')
    need(value.get('detail_rows_omitted')==total['process_count']-len(rows)
         and value.get('omitted_same_uid_processes')==value['detail_rows_omitted'], 'detail omission accounting')
    need(value['expected_roles_observed']==(not value['server_process_expected'] or categories['WINE_SERVERS']['process_count']>0 and categories['POSTGRESQL']['process_count']>0), 'aggregate expected roles')
    for role in roles:
        detail=[row for row in rows if row['role']==role];category=categories[role]
        need(category['process_count']>=len(detail), 'detail exceeds category')
        for metric in ('rss','pss'):
            known=[row[metric+'_bytes'] for row in detail if row[metric+'_bytes'] is not None]
            need(category['missing_'+metric+'_processes']>=len(detail)-len(known), 'detail unknown absent from aggregate')
            observed=category['observed_'+metric+'_bytes']
            need(observed is None or observed>=sum(known), 'aggregate loses retained measurement')
    for metric in ('rss','pss'):
        sums=[c['observed_'+metric+'_bytes'] for c in categories.values()]
        result=None if any(x is None for x in sums) or sum(sums)>=1<<63 else sum(sums)
        need(total['observed_'+metric+'_bytes']==result and value.get('observed_'+metric+'_sum_bytes')==result, 'streaming aggregate conservation')
        need(value.get('total_'+metric+'_bytes')==total[metric+'_bytes'], 'top-level aggregate total differs')
        need(total['missing_'+metric+'_processes']==sum(c['missing_'+metric+'_processes'] for c in categories.values()), 'aggregate missing metrics')
    return aggregate


def process_identities(value, rows, aggregate):
    fields = value.get('process_identity_fields')
    identities = value.get('process_identities')
    if fields is None and identities is None:
        return  # Older numeric-only reports remain readable.
    need(fields == ['pid', 'start_ticks', 'comm', 'exe', 'argv', 'reason_flags']
         and value.get('identity_detail_limit') == 4 and isinstance(identities, list) and len(identities) <= 4,
         'process identity table bound/legend')
    detail = {(row['pid'], row['start_ticks']): row for row in rows}
    seen = set()
    def text(item, cap):
        return isinstance(item, str) and len(item) <= cap and all(32 <= ord(c) <= 126 for c in item)
    for raw in identities:
        need(isinstance(raw, list) and len(raw) == len(fields), 'process identity row width')
        row = dict(zip(fields, raw));key = (row['pid'], row['start_ticks'])
        need(key in detail and key not in seen and detail[key]['identity_stable']
             and detail[key]['role'] == 'WINE_SERVERS', 'process identity missing/stale numeric row')
        seen.add(key)
        flags = row['reason_flags']
        need(type(flags) is int and 0 <= flags <= 2047 and text(row['comm'], 64)
             and (row['exe'] is None or text(row['exe'], 192)), 'process identity string/reason bound')
        args = row['argv']
        need(args is None or isinstance(args, list) and len(args) <= 16
             and all(text(arg, 96) for arg in args) and sum(map(len, args)) <= 384, 'process identity argv bound')
        need(row['exe'] is not None or flags & (32 | 64 | 1024), 'missing executable reason')
        need(args is not None or flags & (8 | 16 | 1024), 'missing cmdline reason')
        if flags & 1024:
            need(row['comm'] == '' and row['exe'] is None and args is None, 'changed executable retained a label')
    count = aggregate['categories']['WINE_SERVERS']['process_count'] if aggregate is not None else value['wine_processes']
    need(value.get('wine_identity_rows_omitted') == count-len(identities), 'identity detail omission count')


def process_set_snapshot(value):
    need(isinstance(value, dict) and value.get('schema') == 'coh-same-uid-process-memory-v1', 'process-set schema')
    if value.get('status') == 'not_sampled':
        need(value.get('total_rss_bytes') is None and value.get('total_pss_bytes') is None, 'unobserved process total fabricated')
        return value
    rows = value.get('processes')
    fields = value.get('process_row_fields')
    if fields is not None:
        need(fields == ['pid', 'start_ticks', 'role', 'rss_bytes', 'pss_bytes', 'identity_stable', 'unavailable', 'zombie_no_address_space']
             and isinstance(rows, list) and all(isinstance(row, list) and len(row) == len(fields) for row in rows), 'compact process row shape')
        rows = [dict(zip(fields, row)) for row in rows]
        for row in rows:
            need(type(row['unavailable']) is int and 0 <= row['unavailable'] <= 63
                 and type(row['zombie_no_address_space']) is bool, 'compact process status type')
            if row['unavailable'] == 0:
                del row['unavailable']
            if row['zombie_no_address_space'] is False:
                del row['zombie_no_address_space']
    need(value.get('process_limit') in (32, 64) and isinstance(rows, list) and 1 <= len(rows) <= value['process_limit']
         and value.get('process_count') == len(rows), 'process-set bound')
    need(all(type(value.get(k)) is int and value[k] >= 0 for k in
             ('begin_elapsed_ms', 'end_elapsed_ms', 'sample_window_ms', 'uid', 'self_pid', 'process_count',
              'wine_processes', 'postgresql_processes', 'incomplete_process_metrics', 'unreadable_status_count', 'samples')),
         'process-set scalar type')
    need(value['end_elapsed_ms'] >= value['begin_elapsed_ms']
         and value['sample_window_ms'] == value['end_elapsed_ms'] - value['begin_elapsed_ms'], 'process-set sample window')
    need(type(value.get('scan_complete')) is bool and type(value.get('expected_roles_observed')) is bool
         and type(value.get('server_process_expected')) is bool, 'process-set boolean')
    pids = set()
    for row in rows:
        need(isinstance(row, dict) and {'pid', 'start_ticks', 'role', 'rss_bytes', 'pss_bytes', 'identity_stable'} <= set(row) <= {'pid', 'start_ticks', 'role', 'rss_bytes', 'pss_bytes', 'identity_stable', 'unavailable', 'zombie_no_address_space'}, 'process-set private/unknown fields')
        need(type(row['pid']) is int and 0 < row['pid'] <= 0x7fffffff and row['pid'] not in pids, 'process-set PID duplicate/domain')
        pids.add(row['pid'])
        need(row['role'] in ('ANDROID_APP_AND_NATIVE_CLIENT', 'WINE_SERVERS', 'POSTGRESQL', 'OTHER_APP_UID')
             and type(row['identity_stable']) is bool, 'process-set role/identity')
        need(all(row[k] is None or type(row[k]) is int and 0 <= row[k] <= 1 << 50
                 for k in ('start_ticks', 'rss_bytes', 'pss_bytes')), 'process-set metric domain')
        if 'unavailable' in row:
            need(type(row['unavailable']) is int and 1 <= row['unavailable'] <= 63, 'process metric failure reason')
        if 'zombie_no_address_space' in row:
            need(row['zombie_no_address_space'] is True and row['identity_stable'] and row['rss_bytes'] == 0 and row['pss_bytes'] == 0 and row.get('unavailable', 0) in (0, 32), 'zombie zero is not source-state derived')
        if not row['identity_stable']:
            need(all(row[k] is None for k in ('start_ticks', 'rss_bytes', 'pss_bytes')), 'unstable process supplied old metrics')
        else:
            need(row['start_ticks'] is not None, 'stable process missing lifetime identity')
    need(sum(row['role'] == 'ANDROID_APP_AND_NATIVE_CLIENT' and row['pid'] == value['self_pid'] for row in rows) == 1,
         'app/native-client overlap was double-counted or lost')
    need(value['wine_processes'] == sum(row['role'] == 'WINE_SERVERS' for row in rows)
         and value['postgresql_processes'] == sum(row['role'] == 'POSTGRESQL' for row in rows), 'role counts differ')
    aggregate=process_aggregation(value,rows) if 'aggregation' in value else None
    process_identities(value,rows,aggregate)
    if 'app_uid_cgroup' in value:app_uid_cgroup(value['app_uid_cgroup'],value['uid'])
    for metric in ('rss', 'pss'):
        if aggregate is None:
            known = [row[metric + '_bytes'] for row in rows if row[metric + '_bytes'] is not None]
            need(value.get('observed_' + metric + '_sum_bytes') == sum(known), 'observed process sum differs')
            total = value.get('total_' + metric + '_bytes')
            if value['scan_complete'] and value['expected_roles_observed'] and len(known) == len(rows):
                need(type(total) is int and total == sum(known), 'complete process sum differs')
            else:
                need(total is None, 'partial process set fabricated complete total')
        total=value.get('total_'+metric+'_bytes');peak=value.get('sampled_peak_total_'+metric+'_bytes')
        maximum=(1<<63)-1 if aggregate is not None else value['process_limit']<<50
        need(peak is None or type(peak) is int and 0 <= peak <= maximum, 'process-set peak domain')
        need(total is None or peak is not None and peak >= total, 'sampled process peak lost')
    need(value.get('atomic_snapshot') is False and value.get('rss_sum_includes_repeated_shared_pages') is True
         and value.get('pss_is_proportional') is True, 'process memory scope mislabeled')
    return value


def memory_snapshot(report):
    value = report.get('memory_diagnostics')
    need(isinstance(value, dict) and value.get('schema') == 'coh-combined-phase-memory-v1', 'phase memory schema absent')
    report_limit = 128 * 1024 if report.get('schema') == 'coh-native-combined-app-v1' else 2 * 1024 * 1024
    need(len(json.dumps(value, indent=2).encode()) < 24 * 1024 and len(json.dumps(report, indent=2).encode()) < report_limit, 'phase/app report exceeds preserved readers')
    need(value.get('phase_limit') == 9 and value.get('sample_interval_ms') == 1000 and value.get('admission_authority') is False and value.get('server_policy_thresholds_changed') is False, 'observation claimed policy authority')
    need(type(value.get('sampler_failures')) is int and 0 <= value['sampler_failures'] <= (1 << 63) - 1, 'sampler failure counter absent or invalid')
    need(type(value.get('snapshot_elapsed_ms')) is int and type(value.get('latest_sample_elapsed_ms')) is int and 0 <= value['latest_sample_elapsed_ms'] <= value['snapshot_elapsed_ms'], 'sample timestamp absent/stale ordering')
    need(value.get('latest_sample_age_ms') == value['snapshot_elapsed_ms'] - value['latest_sample_elapsed_ms'], 'sample age differs')
    if 'same_uid_process_set' in value:
        process_set_snapshot(value['same_uid_process_set'])
    rows = value.get('phases')
    need(isinstance(rows, list) and 0 < len(rows) <= 9 and len({x.get('phase') for x in rows}) == len(rows), 'unbounded or duplicate phase rows')
    for row in rows:
        need(row.get('phase') in MEMORY_PHASES and 0 <= row['requested_elapsed_ms'] <= row['sampled_elapsed_ms'] <= value['latest_sample_elapsed_ms'], 'phase timestamp or identity differs')
        need(type(row.get('sequence')) is int and 0 < row['sequence'] <= value['samples'], 'phase sample sequence differs')
        for field, source in [('process_rss_bytes', 'process_rss_source'), ('process_pss_bytes', 'process_pss_source')]:
            metric = row.get(field)
            need(metric is None or type(metric) is int and metric >= 0, 'negative or fabricated process measurement')
            need((metric is None) == (row.get(source) == 'unavailable'), 'unknown process value mislabeled known')
        need(row['process_pss_source'] in ('unavailable', 'proc_self_smaps_rollup'), 'guessed PSS fallback')
        if not row.get('system_sample_valid'):
            need(all(row.get(k) is None for k in ('available_bytes', 'total_bytes', 'threshold_bytes', 'android_low_memory', 'java_heap_used_bytes', 'java_heap_limit_bytes', 'system_headroom_bytes', 'java_heap_headroom_bytes')), 'unknown system measurement exposed as numeric')
    for key in ('owned_guest_process_memory', 'native_owner_memory', 'graphics_memory'):
        need('unavailable' in value.get(key, ''), 'unmeasured owner total fabricated')
    states = report.get('diagnostic_states', {})
    need(states.get('catalog') == 'MISSING_CATALOG_GENERATION' and states.get('world_resource') == 'UNRESOLVED_RESOURCE_IDENTITY' and states.get('character') == 'INCOMPLETE_CHARACTER_DATA', 'unsupported state mislabeled admitted')
    need(states.get('world_authority') is False and states.get('application_ack_permitted') is False, 'typed diagnostics granted authority')
    return {row['phase']: row for row in rows}


def current_snapshot(value, require_current_probes=False, require_report_extension=False):
    need(isinstance(value, dict) and 'receive_diagnostics' in value, 'new receive observation absent')
    legacy = separate_report_extension(value, required=require_report_extension)
    receive = legacy.pop('receive_diagnostics')
    legacy = separate_current_probes(legacy, required=require_current_probes)
    numeric_snapshot(legacy)
    booleans = ['diagnostic_only', 'valid', 'observation_retired', 'cleanup_transport_counters_equal', *REFUSED_AUTHORITY]
    need(isinstance(receive, dict) and set(receive) == set(COUNTERS + GAUGES + booleans + ['schema', 'refusal']), 'receive observation fields differ')
    need(receive['schema'] == 'coh-initial-receive-counters-v1' and receive['refusal'] in ('NONE', 'INPUT', 'LIMIT'), 'receive schema/refusal differs')
    need(all(type(receive[k]) is bool for k in booleans) and receive['diagnostic_only'] is True, 'receive boolean differs')
    need(all(receive[k] is False for k in REFUSED_AUTHORITY), 'receive observation granted authority')
    need(all(type(receive[k]) is int and 0 <= receive[k] <= 1000000 for k in COUNTERS), 'receive counter bound')
    need(all(type(receive[k]) is int and 0 <= receive[k] <= 0xffffffff for k in GAUGES), 'receive gauge bound')
    need(receive['rx_pending'] <= 16 and receive['max_rx_pending_sampled'] <= 16 and receive['fragment_groups'] <= 4 and receive['max_fragment_groups_sampled'] <= 4, 'receive queue policy changed')
    need(receive['decode_failure_kind'] <= 4 and receive['decode_compressed_bytes'] <= 16384 and receive['decode_output_budget'] <= 4194304 and receive['sample_count'] <= 1000000, 'receive decode policy changed')
    need(receive['udp_datagrams_received'] == value['map_protocol']['udp']['datagrams_received'] and receive['link_received'] == value['map_protocol']['udp']['link']['received'], 'receive projection differs from producer counters')
    return value


class FragmentCheck(InteropCheck):
    def memory_phase(self, phase, after=0, filename='native-client-report.json'):
        def ready(report):
            rows = report.get('memory_diagnostics', {}).get('phases', [])
            return any(row.get('phase') == phase and row.get('sequence', 0) > after for row in rows)
        report = self.wait_report(filename, ready, 'bounded memory phase ' + phase, seconds=45)
        rows = memory_snapshot(report)
        need(report['memory_diagnostics']['sampler_failures'] == 0, 'normal Android candidate recorded a sampler failure')
        (self.args.output / ('memory-' + phase.lower() + '.json')).write_text(json.dumps(report['memory_diagnostics'], indent=2) + '\n')
        return report, rows[phase]

    def world(self, phase, label, seconds=60):
        report = self.wait_report('native-client-report.json', lambda x: x.get('connection_mode') == 'WORLD_HANDOFF' and x.get('world_handoff', {}).get('phase') in phase, label, seconds=seconds)
        need(report.get('preview_is_server_world') is False, 'preview became authoritative')
        current_snapshot(report['world_handoff'], self.args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'), self.args.build_profile in ('report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'))
        if self.args.build_profile in ('catalog-diagnostic', 'entity-diagnostic'):
            observation = report['world_handoff']
            need('catalog_boundary' in observation and observation['catalog_boundary'] is None,
                 'synthetic early-boundary fixture fabricated or lost catalog observation')
        if self.args.build_profile in ('report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'):
            observation = report['world_handoff']
            expected = ('INITIAL_PACKET_OBSERVED' if observation['initial_observed'] else 'NOT_OBSERVED') if observation['initial_observation_known'] else 'UNKNOWN'
            need(report.get('diagnostic_states', {}).get('initial_packet') == expected, 'Android initial packet observation differs from independent native control')
        return report

    def record_snapshot(self, label, report):
        value = current_snapshot(report['world_handoff'], self.args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'), self.args.build_profile in ('report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'))
        (self.args.output / (label + '-world-handoff.json')).write_text(json.dumps(value, indent=2) + '\n')
        return value

    def fragment_receipt(self, label, expected):
        peer = json.loads((self.args.output / (label + '-peer.json')).read_bytes())
        count = expected['sibling_count']
        need(peer['fragment_ordered'] is True and peer['fragment_parts'] == count and peer['fragment_later_zero_order_ids'] == count - 1, 'peer ordered sibling form differs')
        need(peer['fragment_wire_bytes'] == expected['compressed_bytes'] and peer['fragment_fixture_decoded_bytes'] == 65536, 'peer fixture bytes differ')
        need(peer['fragment_single_sibling'] == int(count == 1) and peer['fragment_part_zero_sent_last'] == int(count > 1), 'peer delivery order differs')
        self.record('new original-form ordered sibling socket scenario', scenario=label, siblings=count, later_zero_order_ids=count - 1, compressed_bytes=expected['compressed_bytes'], part_zero_sent_last=count > 1, original_server=False, world_authority=False)

    def run_fragments(self):
        need(self.text('shell', 'getprop', 'ro.boot.qemu').strip() == '1' and self.text('shell', 'getprop', 'ro.product.cpu.abi').strip() == 'x86_64' and self.text('shell', 'getprop', 'ro.build.version.sdk').strip() == '33', 'fresh Android13x86_64 emulator required')
        need(not self.text('shell', 'pm', 'list', 'packages', '--user', '0', PACKAGE).strip(), 'never clear an existing app')
        time.sleep(30)
        need(re.search(r'^Success\s*$', self.text('install', '-g', self.args.apk), re.M) is not None, 'APK install failed')
        self.launch(MAIN)
        initial = self.wait_report('combined-report.json', lambda x: x.get('installed_apk_status') == 'ready', 'new APK installed identity')
        installed_apk_contract(initial, sha(self.args.apk.read_bytes()), self.args.apk.stat().st_size)
        self.tap('Launch native client')
        native = self.wait_report('native-client-report.json', lambda x: x.get('assets_verified') is True and x.get('native', {}).get('frames', 0) >= 30, 'native Activity available')
        need(native['world_handoff'] == IDLE_REPORT, 'handoff began without explicit action')
        if self.args.build_profile in ('report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'):
            need(native.get('diagnostic_states', {}).get('initial_packet') == 'UNKNOWN', 'idle owner fabricated a negative initial packet observation')
            self.record('initial packet observation remains unknown before the first owner begins', initial_packet='UNKNOWN')
        if self.args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'):
            before = max((row.get('sequence', 0) for row in native.get('memory_diagnostics', {}).get('phases', [])), default=0)
            self.tap('Sample memory')
            sampled, row = self.memory_phase('DIAGNOSTIC', before)
            need(row['process_observer_status'] == 'native_observer_returned', 'actual processMemory JNI did not return a bounded observation')
            need(row['system_sample_valid'] is True, 'emulator ActivityManager/Java memory unavailable')
            self.record('actual Android memory button, system/heap and bounded self-process JNI observation', phase='DIAGNOSTIC', rss_available=row['process_rss_bytes'] is not None, pss_available=row['process_pss_bytes'] is not None, total_guest_memory_measured=False)
        for label in ('fragment-multi', 'fragment-single'):
            expected = self.peer_receipt['fragment_fixture']['cases'][label]
            with self.peer(label, label):
                self.choose(label)
                captured = self.observed(label)
                receive = captured['world_handoff']['receive_diagnostics']
                need(receive['valid'] is True and receive['refusal'] == 'NONE' and receive['observation_retired'] is True and receive['cleanup_transport_counters_equal'] is True, 'new receive observation not valid/retired')
                need(receive['sample_count'] > 0 and receive['decode_failure_kind'] == 0 and receive['decode_compressed_bytes'] == expected['compressed_bytes'] and receive['decode_declared_raw_bytes'] == 65536, 'ordered streaming decode observation differs')
                need(all(receive[k] == 0 for k in ('udp_peer_rejects', 'udp_truncated', 'udp_empty', 'udp_malformed', 'udp_unsupported', 'link_malformed', 'link_unsupported', 'link_queue_limits', 'link_fragment_expirations', 'link_timeouts')), 'new fixture refused or timed out')
                self.mapped_interop()
                if label == 'fragment-multi':
                    self.export_native()
                    exported = json.loads((self.args.output / 'exported-native-report.json').read_bytes())
                    current_snapshot(exported['world_handoff'], self.args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'), self.args.build_profile in ('report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'))
                    unchanged_observations(captured['world_handoff'], exported['world_handoff'])
                    if self.args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'):
                        memory_snapshot(exported)
                    need(exported['world_handoff']['receive_diagnostics'] == receive, 'SAF export changed new receive observation')
                    self.record('new receive projection survives actual SAF export', numeric_only=True, world_authority=False)
                self.tap('Disconnect client')
                closed = self.world({'CLOSED'}, label + ' explicit disconnect')
                unchanged_observations(captured['world_handoff'], closed['world_handoff'])
                need(closed['world_handoff']['cleanup_verified'] is True, 'new fragment owner left transport open')
            self.fragment_receipt(label, expected)
        if self.args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'):
            connected, connection = self.memory_phase('NATIVE_CONNECTION')
            session = connected['session_id']
            before = connected['memory_diagnostics']['samples']
            self.adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
            paused, pause = self.memory_phase('PAUSE', before, 'combined-report.json')
            self.resume_recents(session)
            resumed, resume = self.memory_phase('RESUME', pause['sequence'])
            need(resumed['world_handoff']['phase'] == 'CLOSED', 'Home resume silently reconnected')
            self.tap('Return to launcher')
            returned, ret = self.memory_phase('RETURN', resume['sequence'], 'combined-report.json')
            cleaned, cleanup = self.memory_phase('FINAL_CLEANUP', resume['sequence'], 'combined-report.json')
            need(ret['requested_elapsed_ms'] <= cleanup['requested_elapsed_ms'], 'final owner sample preceded Return')
            self.record('event memory observations survive Home/resume and explicit Return after both owner retirements', phases=['NATIVE_CONNECTION', 'PAUSE', 'RESUME', 'RETURN', 'FINAL_CLEANUP'], sample_bytes=len(json.dumps(cleaned['memory_diagnostics'], indent=2).encode()), runtime_stop_not_exercised_on_x86_64=True)
        self.native_fault_evidence('fragments-final')
        receipt = {'schema': 'coh-android-fragment-interop-focused-v1', 'passed': True, 'checks': self.proofs,
            'apk': self.package_receipt['apk'], 'package_receipt': self.package_receipt,
            'peer_receipt_sha256': sha(self.args.peer_receipt.read_bytes()), 'source_revision': self.source_revision,
            'candidate_runtime_source_revision': self.runtime_revision, 'source_admission_sha256': self.source_admission_sha,
            'driver_sha256': sha(Path(__file__).read_bytes()), 'device': {'api': 33, 'abi': 'x86_64', 'emulator': True, 'build_fingerprint': self.text('shell', 'getprop', 'ro.build.fingerprint').strip()},
            'actual_Android_JNI_and_OS_UDP': True, 'new_fragment_scenarios_only': True, 'source_compatible_envelopes_synthetic_ALLENTS_body': True,
            'original_Auth_Db_Map_service_execution': False, 'whole_original_ALLENTS_producer': False,
            'normal_version_checksum_policy_qualified': False, 'complete_initial_character': False, 'actor_publication': False,
            'ACK_authority': False, 'world_authority': False, 'physical_Thor_qualified': False,
            'whole_process_memory_measured': False, 'app_self_process_memory_observer_executed': self.args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'), 'old_framework_suite_executed': False}
        (self.args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


def main():
    need(__debug__, 'Python assertions must be enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--build-profile', choices=BUILD_PROFILES, default='original-fragment', help='Exact APK version pair; preserve the canonical 0.1.9 default')
    parser.add_argument('--candidate-source-revision', help='Exact audited package revision, only with source admission proof')
    parser.add_argument('--source-admission', type=Path, help='Bound proof that current driver changes leave candidate runtime/build inputs byte-identical')
    for name in ('apk', 'peer', 'peer-receipt', 'package-receipt', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    need(not args.output.exists(), 'fresh output required')
    head = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', 'HEAD'], text=True).strip()
    runtime_revision, source_admission_sha = admit_runtime_revision(head, args.candidate_source_revision, args.source_admission)
    peer = json.loads(args.peer_receipt.read_bytes())
    need(peer['passed'] is True and peer['abi'] == 'x86_64' and peer['fragment_compatibility_role'] is True and peer['scripted_source_layout'] is True and peer['real_server_interoperability'] is False and peer['source_revision'] == runtime_revision, 'unadmitted fragment peer role')
    need(peer['peer'] == {'file': args.peer.name, 'bytes': args.peer.stat().st_size, 'sha256': sha(args.peer.read_bytes())}, 'peer executable differs')
    for name, digest in peer['source_sha256'].items():
        need(sha((ROOT / name).read_bytes()) == digest, 'peer source changed')
    package = json.loads(args.package_receipt.read_bytes())
    need(package['status'] == 'passed' and package['abi'] == 'x86_64' and package['package'] == PACKAGE and package['source_commit'] == runtime_revision, 'new APK identity differs')
    check_build_identity(package['version_code'], package['version_name'], args.build_profile)
    if args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'):
        need(package.get('build_profile') == args.build_profile and package.get('process_memory_jni_entrypoint') == 'Java_org_coh_nativecombined_LocalNative_processMemory', 'memory diagnostic package audit absent')
    need(package['apk']['bytes'] == args.apk.stat().st_size and package['apk']['sha256'] == sha(args.apk.read_bytes()), 'APK receipt differs')
    need(package['signer_certificate_sha256'] == '9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522', 'accepted signer changed')
    with zipfile.ZipFile(args.apk) as archive:
        data = archive.read('lib/x86_64/libcoh_combined_interop.so')
    need(data[:6] == b'\x7fELF\x02\x01' and int.from_bytes(data[18:20], 'little') == 62, 'wrong JNI ABI')
    driver = FragmentCheck(args)
    driver.package_receipt, driver.peer_receipt, driver.source_revision = package, peer, head
    driver.runtime_revision, driver.source_admission_sha = runtime_revision, source_admission_sha
    driver.interop_sha, driver.interop_bytes = sha(data), len(data)
    try:
        driver.run_fragments()
    except Exception as failure:
        (args.output / 'failure.json').write_text(json.dumps({'type': type(failure).__name__, 'message': str(failure)[:3000], 'scripted_only': True, 'world_authority': False}, indent=2) + '\n')
        for label, command in (('anr', ('shell', 'dumpsys', 'activity', 'lastanr')), ('crash', ('logcat', '-d', '-b', 'crash'))):
            try:
                (args.output / ('failure-' + label + '.txt')).write_bytes(driver.adb(*command, check=False).stdout)
            except Exception:
                pass
        raise


if __name__ == '__main__':
    main()
