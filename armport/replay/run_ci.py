#!/usr/bin/env python3
"""Run the original receiver in isolated Wine; success is cursor-stage only."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import replay_inventory
import client_errors


def fixtures(destination):
    source = Path(__file__).resolve().parent / 'fixtures'
    for name, size, sha in (
        ('initial-replay.bin', 37994, replay_inventory.INITIAL_SHA),
        ('post-ready-replay.bin', 74416, replay_inventory.POST_SHA),
    ):
        with gzip.open(source / (name + '.gz'), 'rb') as stream:
            data = stream.read(size + 1)
        if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
            raise ValueError('fixture identity: ' + name)
        (destination / name).write_bytes(data)
    initial = replay_inventory.initial((destination / 'initial-replay.bin').read_bytes())
    post = replay_inventory.post_ready((destination / 'post-ready-replay.bin').read_bytes())
    return [initial] + post['records']


def check_wine_output(path):
    """Fail closed on game-process exceptions, including handled SEH.

    Bootstrap/registry commands have their own log. No exception allowlist is
    currently needed or approved for the game run, so startup is checked too.
    A handled exception can otherwise leave a plausible complete transcript.
    """
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Wine output exceeds replay evidence bound')
    failure = re.compile(
        r'(?:dispatch_exception|raise_exception)\s+code=|'
        r':err:seh:|unhandled (?:exception|page fault)|'
        r'wine(?: client| server)?:[^\n]*(?:fatal|could not load|failed to|unimplemented function)|'
        r'wine (?:client|server) error:|'
        r':err:module:(?:import_dll|LdrInitializeThunk)', re.IGNORECASE)
    with path.open(errors='replace') as stream:
        for number, line in enumerate(stream, 1):
            if failure.search(line):
                raise ValueError(f'Wine exception/fatal report at line {number}: {line.strip()[:300]}')


def notice(title, value):
    body = json.dumps(value, separators=(',', ':')).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::notice title={title}::{body}', flush=True)


def check_exception_control(path):
    text = path.read_text(errors='replace')
    if ('ARMPORT_HANDLED_SEH_CONTROL passed' not in text
            or not re.search(r'(?:dispatch_exception|raise_exception)\s+code=e0424242', text, re.I)):
        raise ValueError('Real handled-SEH control marker/trace missing')
    try:
        check_wine_output(path)
    except ValueError as error:
        if 'Wine exception/fatal report' not in str(error):
            raise
        return
    raise ValueError('Host failed to reject the real handled-SEH trace')


def check_client_output(path):
    errors = client_errors.inventory(path, path.with_name('client-errors.json'))
    if errors['count']:
        raise ValueError(f"Game error/assert: {errors['count']} reports, {errors['unique']} distinct; "
                         'see client-errors.json: ' + errors['errors'][0]['text'][:300])


def check_output(path, expected, initial_id, wine_output):
    check_wine_output(wine_output)
    check_client_output(path.parent / 'client-stdio.txt')
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('receiver output exceeds cursor-stage bound')
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if any(row['type'] in ('failure', 'unknown_game_command') for row in rows):
        raise ValueError('receiver reported a failure')
    configs = [r for r in rows if r['type'] == 'configuration']
    if len(configs) != 1 or configs[0]['initial_id'] != initial_id:
        raise ValueError('configuration mismatch')
    begins = [r for r in rows if r['type'] == 'dispatch_begin']
    ends = [r for r in rows if r['type'] == 'dispatch_end']
    cursors = [r for r in rows if r['type'] == 'cursor']
    if len(expected) != 117 or len(begins) != 117 or len(ends) != 117 or len(cursors) != 117:
        raise ValueError('expected all 117 receiver dispatches')
    for i, (want, begin, end, cursor) in enumerate(zip(expected, begins, ends, cursors)):
        packet_id = initial_id if i == 0 else want['packet_id']
        if (begin['index'], begin['id'], begin['command'], begin['logical_bits'], begin['cursor']) != (
                i, packet_id, want['command'], want['logical_bits'], want['post_command_cursor']):
            raise ValueError('dispatch metadata mismatch')
        if (end['count'], end['id'], end['cursor'], end['error_flags']) != (
                i + 1, packet_id, want['logical_bits'], 0):
            raise ValueError('dispatch end mismatch')
        if (cursor['index'], cursor['id'], cursor['expected'], cursor['actual'], cursor['error_flags']) != (
                i, packet_id, want['logical_bits'], want['logical_bits'], 0):
            raise ValueError('receiver cursor mismatch')
    acks = [r for r in rows if r['type'] == 'ack']
    states = [r for r in rows if r['type'] == 'state']
    if len(states) != 117:
        raise ValueError('expected all 117 partial state snapshots')
    native_entity = json.loads((Path(__file__).with_name('fixtures') / 'native-initial-entity.json').read_text())
    if native_entity['initial_file_sha256'] != replay_inventory.INITIAL_SHA:
        raise ValueError('native entity input identity mismatch')
    for i, (want, state) in enumerate(zip(expected, states)):
        name = f'state-{i:03d}.json'
        if (state['index'], state['id'], state['file'], state['state_schema_complete']) != (
                i, initial_id if i == 0 else want['packet_id'], name, False):
            raise ValueError('state snapshot metadata mismatch')
        snapshot = path.parent / name
        if snapshot.is_symlink() or not snapshot.is_file() or not 0 < snapshot.stat().st_size <= 16 * 1024 * 1024:
            raise ValueError('invalid state snapshot file')
        raw = snapshot.read_bytes()
        if hashlib.sha256(raw).hexdigest() != state['sha256']:
            raise ValueError('state snapshot digest mismatch')
        document = json.loads(raw)
        if (document.get('schema') != 'armport-receiver-state-v1-partial'
                or document.get('state_schema_complete') is not False):
            raise ValueError('partial state schema mismatch')
        indices = [e['svr_idx'] for e in document['entities']]
        if len(indices) != state['entities'] or indices != sorted(set(indices)):
            raise ValueError('state entity inventory mismatch')
        if i == 0:
            entity = next((e for e in document['entities'] if e['svr_idx'] == native_entity['svr_idx']), None)
            if (not entity or entity['type'] != native_entity['type'] or not entity['costume']
                    or entity['costume']['bodytype'] != native_entity['bodytype']
                    or entity['costume']['num_parts'] != native_entity['part_count']
                    or len(entity['costume']['parts']) < entity['costume']['num_parts']):
                raise ValueError('recorded native INITIAL entity subset differs')
    if [r['packet_id'] for r in acks] != [initial_id, 32]:
        raise ValueError('missing or unexpected full-update ACK')
    # The driver compares each outgoing ACK to the original incoming ACK ID.
    if rows[-1] != dict(type='result', dispatches=117, exact_cursors=True,
                        state_comparison_complete=False, m3_replay_complete=False):
        raise ValueError('missing explicit incomplete milestone result')
    baseline = json.loads((Path(__file__).with_name('fixtures') / 'native-initial-boundaries.json').read_text())
    if baseline['initial_file_sha256'] != replay_inventory.INITIAL_SHA:
        raise ValueError('native INITIAL baseline identity mismatch')
    initial = [r for r in rows if r.get('index') == 0]
    for stage, expected_cursor in (('entity_tail', baseline['tail_start_bit']),
                                   ('command_tail_end', baseline['tail_end_bit'])):
        boundary = [r for r in initial if r['type'] == 'receive_boundary' and r['stage'] == stage]
        if len(boundary) != 1 or boundary[0]['cursor'] != expected_cursor or boundary[0]['error_flags'] != 0:
            raise ValueError('native INITIAL boundary mismatch: ' + stage)
    starts = [r for r in initial if r['type'] == 'game_command_begin']
    stops = [r for r in initial if r['type'] == 'game_command_end' and r['command'] != 0]
    terminators = [r for r in initial if r['type'] == 'game_command_end' and r['command'] == 0]
    if len(starts) != baseline['tail_commands'] or len(stops) != len(starts):
        raise ValueError('native INITIAL tail command count mismatch')
    for start, stop in zip(starts, stops):
        if (start['command'] != stop['command'] or start['error_flags'] or stop['error_flags']
                or not baseline['tail_start_bit'] <= start['cursor'] <= stop['cursor'] <= baseline['tail_end_bit']):
            raise ValueError('native INITIAL command boundary mismatch')
    if (len(terminators) != 1 or terminators[0]['cursor'] != baseline['tail_end_bit']
            or terminators[0]['error_flags'] != 0):
        raise ValueError('native INITIAL zero terminator mismatch')
    return dict(dispatches=117, exact_cursors=True, ack_ids=[r['ack_id'] for r in acks],
                native_initial_command_boundaries_match=True,
                native_initial_entity_subset_match=True, game_errors=0,
                partial_state_snapshots=117, state_schema_complete=False,
                state_comparison_complete=False, m3_replay_complete=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--wine', type=Path, default=Path('/opt/wine/bin'))
    parser.add_argument('--target', choices=('arm64', 'i686'), required=True)
    parser.add_argument('--host-netns', required=True)
    parser.add_argument('--seh-control', type=Path, required=True)
    args = parser.parse_args()
    # sysfs can still expose the host's interfaces after unshare --net.
    # Query netlink in this process's actual namespace instead.
    links = json.loads(subprocess.check_output(['ip', '-j', 'link', 'show'], text=True))
    namespace = os.readlink('/proc/self/ns/net')
    if namespace == args.host_netns or {row['ifname'] for row in links} != {'lo'}:
        raise RuntimeError('replay requires a private loopback-only network namespace')
    if os.geteuid() == 0:
        raise RuntimeError('Wine must run as the unprivileged runner')
    args.runtime = args.runtime.resolve()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    report = dict(target=args.target, source_commit=os.getenv('GITHUB_SHA'),
                  scope='original_receiver_partial_state_stage', runs=[],
                  network_namespace=namespace, host_network_namespace=args.host_netns,
                  interfaces=[row['ifname'] for row in links],
                  state_comparison_complete=False, m3_replay_complete=False)
    display = ':98'
    xvfb = subprocess.Popen(['Xvfb', display, '-screen', '0', '1280x1024x24', '-nolisten', 'tcp'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(2)
        for label, initial_id in (('id1-a', 1), ('id1-b', 1), ('id31', 31)):
            folder = args.out / label
            folder.mkdir()
            expected = fixtures(folder)
            prefix = folder / 'wineprefix'
            env = dict(os.environ, DISPLAY=display, WINEPREFIX=str(prefix),
                       WINEDEBUG='err+all,fixme-all,+seh', WINEDLLOVERRIDES='mscoree,mshtml=',
                       ARMPORT_LOOSE_DATA='1', ARMPORT_STDIO_LOG='Z:' + str(folder / 'client-stdio.txt').replace('/', '\\'))
            # Bootstrap without the replay environment: only the actual game gets it.
            with (folder / 'bootstrap-output.txt').open('wb') as bootstrap, \
                    (folder / 'wine-output.txt').open('wb') as log:
                try:
                    subprocess.run([str(args.wine / 'wine'), 'wineboot', '-i'], env=env,
                                   stdout=bootstrap, stderr=subprocess.STDOUT, check=True, timeout=300)
                    subprocess.run([str(args.wine / 'wine'), 'reg', 'add',
                                    r'HKCU\Software\Wine\WineDbg', '/v', 'ShowCrashDialog',
                                    '/t', 'REG_DWORD', '/d', '0', '/f'], env=env,
                                   stdout=bootstrap, stderr=subprocess.STDOUT, check=True, timeout=60)
                    if label == 'id1-a':
                        control = args.out / 'handled-seh-control.txt'
                        with control.open('wb') as control_log:
                            subprocess.run([str(args.wine / 'wine'), str(args.seh_control.resolve())],
                                           env=env, stdout=control_log, stderr=subprocess.STDOUT,
                                           check=True, timeout=60)
                        check_exception_control(control)
                        report['real_handled_seh_rejected'] = True
                        notice('ArmPort handled SEH control', dict(target=args.target, rejected=True))
                    env.update(ARMPORT_REPLAY_DIR='Z:' + str(folder).replace('/', '\\'),
                               ARMPORT_REPLAY_INITIAL_ID=str(initial_id))
                    run = subprocess.run([str(args.wine / 'wine'), str(args.runtime / 'CityOfHeroes.exe'),
                                          '-fullscreen', '0', '-screen', '800', '600', '-verbose', '1'],
                                         cwd=args.runtime, env=env, stdout=log, stderr=subprocess.STDOUT,
                                         timeout=600)
                    if run.returncode != 2:
                        raise RuntimeError(f'{label}: expected incomplete-stage exit 2, got {run.returncode}')
                    result = check_output(folder / 'receiver.jsonl', expected, initial_id,
                                          folder / 'wine-output.txt')
                    report['runs'].append(dict(label=label, **result))
                    print(json.dumps(report['runs'][-1]), flush=True)
                    notice('ArmPort replay ' + args.target + ' ' + label, report['runs'][-1])
                finally:
                    subprocess.run([str(args.wine / 'wineserver'), '-k'], env=env, timeout=30, check=False)
                    subprocess.run([str(args.wine / 'wineserver'), '-w'], env=env, timeout=30, check=False)
                    # Prefixes contain mutable runtime data, not useful decoder evidence.
                    shutil.rmtree(prefix, ignore_errors=True)
        if (args.out / 'id1-a/receiver.jsonl').read_bytes() != (args.out / 'id1-b/receiver.jsonl').read_bytes():
            raise ValueError('same-ID cursor/ACK/state-hash repeat differs')
        report['cursor_stage_passed'] = True
        print('Receiver cursor/ACK stage passed; full state comparison and M3 remain incomplete.')
        return 0
    except Exception as error:
        notice('ArmPort replay failure', dict(target=args.target, error=str(error), m3_replay_complete=False))
        raise
    finally:
        xvfb.terminate()
        xvfb.wait(timeout=15)
        (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
