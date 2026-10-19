#!/usr/bin/env python3
"""Two new scripted original-form fragment transactions over host OS UDP only."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tarfile
import tempfile
from build_interop_peer import produce_fixtures, module, ROOT, NATIVE, HERE
from fragment_fixture import produce


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(ok, label):
    if not ok:
        raise ValueError('FRAGMENT_PEER_' + label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(__debug__ and not args.output.exists(), 'FRESH_OUTPUT')
    args.output.mkdir(parents=True)
    sources = [NATIVE / name for name in module(HERE / 'check_local_initial_capture.py').RELATIVE]
    receiver = HERE / 'capture_local_initial.c'
    peer = NATIVE / 'engine/initial-capture/test_initial_fragment_peer.c'
    inputs = {Path(__file__).resolve(), HERE / 'fragment_fixture.py', HERE / 'build_interop_peer.py'}
    results = {}
    with tempfile.TemporaryDirectory(prefix='coh-fragment-peer-') as temporary:
        work = Path(temporary)
        produce_fixtures(work)
        fixture = produce(work)
        flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I' + str(NATIVE / 'include'), '-I' + str(work)]

        def run(command, label):
            child = subprocess.run(list(map(str, command)), capture_output=True, timeout=120)
            (args.output / (label + '.stdout')).write_bytes(child.stdout)
            (args.output / (label + '.stderr')).write_bytes(child.stderr)
            need(child.returncode == 0, label)
            return child

        for source in [*sources, receiver, peer]:
            dependencies = run(['cc', *flags, '-MM', source], 'deps-' + source.stem).stdout.decode().replace('\\\n', ' ').partition(':')[2]
            for name in dependencies.split():
                path = Path(name).resolve()
                if path.is_relative_to(ROOT):
                    inputs.add(path)
                else:
                    need(path.is_relative_to(work), 'DEPENDENCY_ROOT')
        pins = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in sorted(inputs)}
        objects = []
        for index, source in enumerate(sources):
            obj = work / (str(index) + '.o')
            original = ['-O0'] if source.name in ('coh_protocol.c', 'coh_blowfish.c') else []
            run(['cc', *flags, *original, '-c', source, '-o', obj], 'compile-' + source.stem)
            objects.append(obj)
        binaries = {}
        for label, source in [('receiver', receiver), ('peer', peer)]:
            binary = work / label
            run(['cc', *flags, source, *objects, '-lz', '-lm', '-lcrypto', '-o', binary], 'link-' + label)
            binaries[label] = binary
        account = work / 'account'
        account.write_text('Fixture\n')
        account.chmod(0o600)
        for mode, expected in fixture['cases'].items():
            report = work / (mode + '-peer.json')
            child = subprocess.Popen([str(binaries['peer']), '--serve', '--report', str(report), '--mode', mode], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                with selectors.DefaultSelector() as ready:
                    ready.register(child.stdout, selectors.EVENT_READ)
                    need(bool(ready.select(10)), 'READINESS')
                    port = json.loads(child.stdout.readline())['db_port']
                target = work / mode
                completed = run([binaries['receiver'], port, 0, account, target, 1000, 5, 0, 0], mode + '-receiver')
                public = json.loads(completed.stdout)
                initial = json.loads((target / 'initial-observation.json').read_bytes())
                need(public['passed'] is True and public['initial_packet_observed'] is True and public['status'] == 2, 'RAW_OBSERVATION')
                need(public['opened_sockets'] == public['closed_sockets'] == 2 and public['reqallents_sent'] == 1, 'TRANSPORT_CLEANUP')
                need(initial['ordered'] == initial['ordered_id'] == 1 and initial['bytes'] == 65536 and initial['failure_code'] == 'NONE', 'ORDERED_INITIAL')
                need(sha((target / 'initial-update.bin').read_bytes()) == expected['decoded_sha256'], 'BODY_BYTES')
                need(all(initial[key] is False for key in ('complete_initial_character', 'actor_publication', 'ack_permitted', 'world_authority')), 'AUTHORITY')
            finally:
                if child.poll() is None:
                    child.send_signal(signal.SIGTERM)
                stdout, stderr = child.communicate(timeout=10)
                (args.output / (mode + '-peer.stdout')).write_text(stdout)
                (args.output / (mode + '-peer.stderr')).write_text(stderr)
                need(child.returncode == 0 and not stderr, 'PEER_EXIT')
            peer_report = json.loads(report.read_bytes())
            need(peer_report['failed'] is False and peer_report['opened_sockets'] == peer_report['closed_sockets'] == 2, 'PEER_CLEANUP')
            need(peer_report['fragment_parts'] == expected['sibling_count'] and peer_report['fragment_later_zero_order_ids'] == expected['sibling_count'] - 1 and peer_report['fragment_wire_bytes'] == expected['compressed_bytes'], 'FRAGMENT_FORM')
            need(peer_report['fragment_part_zero_sent_last'] == int(expected['part_zero_sent_last']) and peer_report['fragment_single_sibling'] == int(expected['sibling_count'] == 1), 'ARRIVAL_ORDER')
            need(all(peer_report[key] == 0 for key in ('forbidden_application_commands', 'ready_commands', 'received_character_commands', 'full_update_ack_commands')), 'NO_APPLICATION_ACK')
            (args.output / (mode + '-peer.json')).write_bytes(report.read_bytes())
            results[mode] = {'passed': True, 'ordered_id': 1, 'decoded_bytes': 65536, 'decoded_sha256': expected['decoded_sha256'], 'siblings': expected['sibling_count'], 'later_zero_order_ids': expected['sibling_count'] - 1, 'compressed_bytes': expected['compressed_bytes'], 'client_sockets_closed': 2, 'peer_sockets_closed': 2, 'world_authority': False}
        need(pins == {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in sorted(inputs)}, 'SOURCE_CHANGED')
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode='w') as archive:
            for name, raw in {**{name: path.read_bytes() for name, path in binaries.items()}, 'fragment-fixtures.h': (work / 'fragment-fixtures.h').read_bytes()}.items():
                entry = tarfile.TarInfo(name)
                entry.size = len(raw)
                entry.mode = 0o700 if name in binaries else 0o600
                entry.mtime = 0
                archive.addfile(entry, io.BytesIO(raw))
        raw = gzip.compress(payload.getvalue(), mtime=0)
        (args.output / 'executed-host-proof.tar.gz').write_bytes(raw)
    receipt = {'schema': 'coh-new-fragment-peer-host-v1', 'passed': True, 'source_sha256': pins, 'source_inputs_unchanged': True, 'fixture': fixture, 'scenarios': results, 'executed_host_proof': {'bytes': len(raw), 'sha256': sha(raw)}, 'actual_host_OS_UDP': True, 'actual_Android_JNI_or_device_execution': False, 'old_qualifier_entrypoints_executed': False, 'whole_original_ALLENTS_producer': False, 'world_authority': False}
    (args.output / 'qualification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': True, 'new_host_scenarios': len(results), 'android_executed': False}))


if __name__ == '__main__':
    main()
