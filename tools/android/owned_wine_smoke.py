#!/usr/bin/env python3
"""Exercise the guest's exact orphan cleanup under its real PRoot /proc view.

A detached helper ignores TERM and retains its initializer's stdout. A separate
same-UID sentinel has the same prefix but a different owner token and must live.
An optional native fixture terminates its leader with pthread_exit while a
TERM-ignoring worker retains the pipe, exercising ownership through live tasks.
No Wine, database, Android acceptance or game execution is claimed by this test.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def alive(identity):
    try:
        raw = Path('/proc', str(identity['proc_pid']), 'stat').read_text()
    except FileNotFoundError:
        return False
    fields = raw.rsplit(') ', 1)[1].split()
    if int(fields[19]) != identity['starttime']:
        return False
    if fields[0] not in ('Z', 'X'):
        return True
    # A dead leader is not proof that every worker released its descriptors.
    try:
        for task in Path('/proc', str(identity['proc_pid']), 'task').iterdir():
            try:
                state = (task / 'stat').read_text().rsplit(') ', 1)[1].split()[0]
            except FileNotFoundError:
                continue
            if state not in ('Z', 'X'):
                return True
    except FileNotFoundError:
        pass
    return False


def thread_snapshot(identity, owner, initializer):
    """Independently observe the legacy zombie skip's retained-pipe case."""
    process = Path('/proc', str(identity['proc_pid']))
    leader = owner.process_stat(process)
    pipe = os.readlink(Path('/proc/self/fd', str(initializer.process.stdout.fileno())))
    live_workers, owned_workers, pipe_holders = 0, 0, 0
    for task in (process / 'task').iterdir():
        try:
            task_stat = owner.process_stat(task)
            if task_stat['state'] in ('Z', 'X'):
                continue
            live_workers += 1
            status = dict(line.split(':', 1) for line in (task / 'status').read_text().splitlines()
                          if ':' in line)
            if (int(status['Tgid']) != identity['proc_pid']
                    or int(status['Uid'].split()[0]) != owner.real_uid
                    or owner.needle not in (task / 'environ').read_bytes().split(b'\0')):
                continue
            owned_workers += 1
            fdinfo = dict(line.split(':', 1) for line in (task / 'fdinfo/1').read_text().splitlines()
                          if ':' in line)
            if (os.readlink(task / 'fd/1') == pipe
                    and int(fdinfo['flags'], 8) & os.O_ACCMODE != os.O_RDONLY):
                pipe_holders += 1
        except FileNotFoundError:
            continue
    return {'leader_state': leader['state'], 'live_worker_count': live_workers,
            'owned_live_worker_count': owned_workers, 'owned_stdout_pipe_holders': pipe_holders,
            'initializer_output_capture_open': initializer.reader.is_alive(),
            'legacy_zombie_skip_would_miss_group': leader['state'] == 'Z' and owned_workers > 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--thread-fixture', type=Path,
                        help='Native pthread_exit fixture for a dead leader with a live worker')
    args = parser.parse_args()
    if args.state.exists():
        raise RuntimeError('Ownership fixture requires a fresh private workspace')
    args.state.mkdir(mode=0o700, parents=True)
    spec = importlib.util.spec_from_file_location('coh_guest_diagnostic', args.diagnostic)
    diagnostic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diagnostic)
    context = diagnostic.Context(args.state, total_timeout=45)
    owner = diagnostic.WineProcessOwner(context)
    report = {'format': 1, 'status': 'failed', 'passed': False,
              'scope': ('synthetic_owned_thread_cleanup_under_proot' if args.thread_fixture
                        else 'synthetic_owned_process_cleanup_under_proot'),
              'android_execution_validated': False, 'gameplay_validated': False}
    identity = args.state / 'detached-helper.pid'
    sentinel_identity = args.state / 'sentinel.pid'
    helper_pid = None
    sentinel = None
    initializer = None
    try:
        owned_env = dict(os.environ, **owner.environment)
        owned_env['WINEPREFIX'] = str(args.state / 'same-prefix')
        sentinel_env = dict(owned_env, COH_WINE_SESSION='unrelated-sentinel-session')
        sentinel_source = ('import os,time\nfrom pathlib import Path\n'
                           f'Path({str(sentinel_identity)!r}).write_text(str(os.getpid()))\n'
                           'time.sleep(60)\n')
        sentinel_command = ([str(args.thread_fixture), '--sentinel'] if args.thread_fixture
                            else [sys.executable, '-c', sentinel_source])
        sentinel = subprocess.Popen(sentinel_command, env=sentinel_env,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, start_new_session=True)
        if args.thread_fixture:
            sentinel_identity.write_text(str(sentinel.pid))
        helper = ('import os,signal,time\nfrom pathlib import Path\n'
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                  f'Path({str(identity)!r}).write_text(str(os.getpid()))\n'
                  'print("OWNED_HELPER_READY",flush=True)\n'
                  'time.sleep(60)\n')
        if args.thread_fixture:
            source = ('import subprocess\nfrom pathlib import Path\n'
                      f'child=subprocess.Popen([{str(args.thread_fixture)!r}],start_new_session=True)\n'
                      f'Path({str(identity)!r}).write_text(str(child.pid))\n')
        else:
            source = ('import subprocess,sys,time\nfrom pathlib import Path\n'
                      f'subprocess.Popen([sys.executable,"-u","-c",{helper!r}],start_new_session=True)\n'
                      f'while not Path({str(identity)!r}).exists():time.sleep(.01)\n')
        result = context.run('detached-wine-initializer', [sys.executable, '-c', source],
                             env=owned_env, timeout=8, allow_background_output=True)
        initializer = context.children[-1]
        helper_pid = int(identity.read_text())
        candidates = owner.scan(time.monotonic() + 5)
        helper_identity = next((candidate for candidate in candidates if candidate['pid'] == helper_pid), None)
        diagnostic.require(helper_identity is not None, 'Detached helper ownership was not discoverable')
        if args.thread_fixture:
            deadline = time.monotonic() + 5
            while True:
                snapshot = thread_snapshot(helper_identity, owner, initializer)
                if snapshot['leader_state'] == 'Z' or time.monotonic() >= deadline:
                    break
                time.sleep(.02)
            report['before_cleanup'] = snapshot
            diagnostic.require(snapshot['leader_state'] == 'Z'
                               and snapshot['live_worker_count'] >= 1
                               and snapshot['owned_live_worker_count'] >= 1
                               and snapshot['owned_stdout_pipe_holders'] >= 1
                               and snapshot['initializer_output_capture_open'] is True
                               and snapshot['legacy_zombie_skip_would_miss_group'] is True,
                               'Native fixture did not reproduce a dead leader retaining stdout through a live owned worker')
        deadline = time.monotonic() + 3
        while not sentinel_identity.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        diagnostic.require(sentinel_identity.is_file() and sentinel.poll() is None,
                           'Unrelated sentinel was not running before cleanup')
        diagnostic.require(result['exit_code'] == 0 and initializer.reader.is_alive()
                           and alive(helper_identity) and os.getpgid(helper_pid) != initializer.process.pid,
                           'Detached helper did not retain the completed initializer pipe')
        report['detached_helper_retained_output'] = True
        receipt = owner.cleanup(time.monotonic() + 10)
        report['wine_process_cleanup'] = receipt
        initializer.reader.join(timeout=2)
        initializer.writer.join(timeout=1)
        context.record(initializer, refresh=True)
        diagnostic.require(not alive(helper_identity), 'Token-owned detached helper survived cleanup')
        diagnostic.require(not initializer.reader.is_alive() and not initializer.writer.is_alive(),
                           'Initializer output did not reach EOF after orphan cleanup')
        diagnostic.require(sentinel.poll() is None,
                           'Cleanup signalled the unrelated same-UID sentinel')
        diagnostic.require(receipt.get('complete') is True and receipt.get('remaining') == 0
                           and receipt.get('term_signals', 0) >= 1
                           and receipt.get('kill_signals', 0) >= 1,
                           'Ownership cleanup did not prove bounded TERM/KILL escalation')
        if args.thread_fixture:
            diagnostic.require(receipt.get('dead_leaders_with_live_tasks', 0) >= 1
                               and receipt.get('owned_live_workers', 0) >= 1,
                               'Cleanup did not report ownership of the dead leader\'s live worker')
            report.update(dead_leader_live_worker_reproduced=True,
                          owned_live_workers_reaped=True, same_executable_sentinel_preserved=True)
        report.update(status='passed', passed=True, detached_helper_reaped=True,
                      output_eof_observed=True, unrelated_sentinel_survived=True,
                      same_prefix_different_token_preserved=True)
    except Exception as error:
        report['failure'] = str(error)
        if 'wine_process_cleanup' in context.report:
            report['wine_process_cleanup'] = context.report['wine_process_cleanup']
        raise
    finally:
        # Test-owned fallback teardown is separate from the proof above. It
        # cannot convert a failed ownership check into a successful result.
        if sentinel is not None:
            if sentinel.poll() is None:
                sentinel.kill()
            sentinel.wait(timeout=3)
        # A failed orphan proof is left to the owning PRoot --kill-on-exit;
        # never signal a stale PID merely because the fixture once recorded it.
        if initializer is not None:
            initializer.stop()
        report['processes'] = context.report['processes']
        diagnostic.private_write(args.state / 'report.json',
                                 json.dumps(diagnostic.redacted_value(report, context.secrets), indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'report': str(args.state / 'report.json')}))


if __name__ == '__main__':
    main()
