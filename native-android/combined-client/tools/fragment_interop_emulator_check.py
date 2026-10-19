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

COUNTERS = ('udp_datagrams_received udp_peer_rejects udp_truncated udp_empty udp_malformed udp_unsupported '
            'udp_receive_budget_exhausted link_received link_duplicates link_malformed link_unsupported '
            'link_queue_limits link_fragment_expirations link_timeouts').split()
GAUGES = ('rx_pending fragment_groups decode_failure_kind decode_compressed_bytes decode_declared_raw_bytes '
          'decode_output_budget sample_count max_rx_pending_sampled max_fragment_groups_sampled').split()
REFUSED_AUTHORITY = ('command_specific_emission_proved server_receipt_proved source_generation_admitted '
                    'complete_initial_character actor_publication ack_permitted world_authority').split()


def current_snapshot(value):
    need(isinstance(value, dict) and 'receive_diagnostics' in value, 'new receive observation absent')
    legacy = dict(value)
    receive = legacy.pop('receive_diagnostics')
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
    def world(self, phase, label, seconds=60):
        report = self.wait_report('native-client-report.json', lambda x: x.get('connection_mode') == 'WORLD_HANDOFF' and x.get('world_handoff', {}).get('phase') in phase, label, seconds=seconds)
        need(report.get('preview_is_server_world') is False, 'preview became authoritative')
        current_snapshot(report['world_handoff'])
        return report

    def record_snapshot(self, label, report):
        value = current_snapshot(report['world_handoff'])
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
                    current_snapshot(exported['world_handoff'])
                    unchanged_observations(captured['world_handoff'], exported['world_handoff'])
                    need(exported['world_handoff']['receive_diagnostics'] == receive, 'SAF export changed new receive observation')
                    self.record('new receive projection survives actual SAF export', numeric_only=True, world_authority=False)
                self.tap('Disconnect client')
                closed = self.world({'CLOSED'}, label + ' explicit disconnect')
                unchanged_observations(captured['world_handoff'], closed['world_handoff'])
                need(closed['world_handoff']['cleanup_verified'] is True, 'new fragment owner left transport open')
            self.fragment_receipt(label, expected)
        self.native_fault_evidence('fragments-final')
        receipt = {'schema': 'coh-android-fragment-interop-focused-v1', 'passed': True, 'checks': self.proofs,
            'apk': self.package_receipt['apk'], 'package_receipt': self.package_receipt,
            'peer_receipt_sha256': sha(self.args.peer_receipt.read_bytes()), 'source_revision': self.source_revision,
            'driver_sha256': sha(Path(__file__).read_bytes()), 'device': {'api': 33, 'abi': 'x86_64', 'emulator': True, 'build_fingerprint': self.text('shell', 'getprop', 'ro.build.fingerprint').strip()},
            'actual_Android_JNI_and_OS_UDP': True, 'new_fragment_scenarios_only': True, 'source_compatible_envelopes_synthetic_ALLENTS_body': True,
            'original_Auth_Db_Map_service_execution': False, 'whole_original_ALLENTS_producer': False,
            'normal_version_checksum_policy_qualified': False, 'complete_initial_character': False, 'actor_publication': False,
            'ACK_authority': False, 'world_authority': False, 'physical_Thor_qualified': False,
            'whole_process_memory_measured': False, 'old_framework_suite_executed': False}
        (self.args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


def main():
    need(__debug__, 'Python assertions must be enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    for name in ('apk', 'peer', 'peer-receipt', 'package-receipt', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    need(not args.output.exists(), 'fresh output required')
    head = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', 'HEAD'], text=True).strip()
    peer = json.loads(args.peer_receipt.read_bytes())
    need(peer['passed'] is True and peer['abi'] == 'x86_64' and peer['fragment_compatibility_role'] is True and peer['scripted_source_layout'] is True and peer['real_server_interoperability'] is False and peer['source_revision'] == head, 'unadmitted fragment peer role')
    need(peer['peer'] == {'file': args.peer.name, 'bytes': args.peer.stat().st_size, 'sha256': sha(args.peer.read_bytes())}, 'peer executable differs')
    for name, digest in peer['source_sha256'].items():
        need(sha((ROOT / name).read_bytes()) == digest, 'peer source changed')
    package = json.loads(args.package_receipt.read_bytes())
    need(package['status'] == 'passed' and package['abi'] == 'x86_64' and package['package'] == PACKAGE and package['version_code'] == '10' and package['version_name'] == '0.1.9-gates25-27-test' and package['source_commit'] == head, 'new APK identity differs')
    need(package['apk']['bytes'] == args.apk.stat().st_size and package['apk']['sha256'] == sha(args.apk.read_bytes()), 'APK receipt differs')
    need(package['signer_certificate_sha256'] == '9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522', 'accepted signer changed')
    with zipfile.ZipFile(args.apk) as archive:
        data = archive.read('lib/x86_64/libcoh_combined_interop.so')
    need(data[:6] == b'\x7fELF\x02\x01' and int.from_bytes(data[18:20], 'little') == 62, 'wrong JNI ABI')
    driver = FragmentCheck(args)
    driver.package_receipt, driver.peer_receipt, driver.source_revision = package, peer, head
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
