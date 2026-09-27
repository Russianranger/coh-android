#!/usr/bin/env python3
"""Exercise the guest's exact orphan cleanup under its real PRoot /proc view.

A detached helper ignores TERM and retains its initializer's stdout. A separate
same-UID sentinel has the same prefix but a different owner token and must live.
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
    return int(fields[19]) == identity['starttime'] and fields[0] not in ('Z', 'X')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
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
              'scope': 'synthetic_owned_process_cleanup_under_proot',
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
        sentinel = subprocess.Popen([sys.executable, '-c', sentinel_source], env=sentinel_env,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, start_new_session=True)
        helper = ('import os,signal,time\nfrom pathlib import Path\n'
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                  f'Path({str(identity)!r}).write_text(str(os.getpid()))\n'
                  'print("OWNED_HELPER_READY",flush=True)\n'
                  'time.sleep(60)\n')
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
                           and receipt.get('kill_signals', 0) >= 1,
                           'Ownership cleanup did not prove bounded TERM/KILL escalation')
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
