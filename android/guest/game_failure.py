"""Bounded failure-only inspection of the private game runtime before cleanup."""
import json
import re
import time
from pathlib import Path


def game_pids(text):
    """Wine 10 info proc uses hexadecimal PIDs and decimal thread counts."""
    found = []
    for line in text.splitlines():
        match = re.fullmatch(r"[ >]?([0-9a-fA-F]{8})\s+\d+\s+(?:\\_\s*)?'(DbServer|MapServer)\.exe'", line)
        if match:
            found.append((int(match[1], 16), match[2]))
    if (len(found) != 3 or len({pid for pid, _ in found}) != 3
            or any(pid <= 0 for pid, _ in found)
            or sorted(name for _, name in found) != ['DbServer', 'MapServer', 'MapServer']):
        raise ValueError('Expected one DbServer, Atlas and its outstanding query in the private Wine prefix')
    return found


def finish(ctx, child, deadline):
    while child.process.poll() is None or child.reader.is_alive():
        if child.overflow or time.monotonic() >= deadline:
            child.stop()
            break
        time.sleep(.05)
    ctx.record(child, refresh=True)


def inspect(diagnostic, failed_child):
    """A failed query stays failed. Debuggers share only the exclusively locked
    fresh prefix, and start together. No dumps, environments or locals are read.
    """
    ctx, base = diagnostic.ctx, diagnostic.ctx_base
    result = {'time_utc': base.utc(), 'trigger': failed_child.label,
              'query_alive_before_capture': failed_child.process.poll() is None,
              'before_cleanup': True, 'failures': [], 'stacks': [], 'stacks_available': False,
              'current_execution_validated': False,
              'context_limitation': 'Cross-process WOW64 contexts under the pinned FEX runtime may reflect '
                  'cached exception or thread-start state. Debugger output alone does not establish '
                  'the currently blocked function.'}
    ctx.report['game_failure_inspection'] = result
    ctx.event('stage', status='running', message='Capturing blocked game threads, sockets and SQL before cleanup')
    started = time.monotonic()
    try:
        env = diagnostic.base_env.copy()
        env.update(PGPASSWORD=diagnostic.credentials['cohdiag_admin'], PGCONNECT_TIMEOUT='2',
                   PGOPTIONS='-c statement_timeout=2000')
        query = """SELECT coalesce(json_agg(a),'[]'::json) FROM (
SELECT pid, state, wait_event_type, wait_event, client_addr, client_port,
       left(query,2048) AS query, length(query)>2048 AS query_truncated,
       query_start, xact_start
FROM pg_stat_activity WHERE datname=:'game_database' AND usename='cohtest'
ORDER BY pid LIMIT 80) a;"""
        child = ctx.start('game-failure-sql', [diagnostic.pgtool('psql'), '-X', '-w', '-A', '-t',
            '-v', 'ON_ERROR_STOP=1', '-v', 'game_database=' + diagnostic.database,
            '-h', str(diagnostic.socket_dir), '-p', str(diagnostic.port),
            '-U', 'cohdiag_admin', '-d', 'postgres'], env=env, input_text=query, cleanup=True)
        finish(ctx, child, time.monotonic() + 4)
        if child.process.returncode != 0 or child.overflow:
            raise ValueError('SQL inspection failed')
        rows = json.loads(child.text())
        if not isinstance(rows, list) or len(rows) > 80:
            raise ValueError('SQL inspection exceeded session bound')
        result['postgres_sessions'] = base.redacted_value(rows, ctx.secrets)
    except Exception as exc:
        result['failures'].append('SQL: ' + str(exc))
    try:
        sockets = {}
        for name in ('tcp', 'tcp6', 'udp', 'udp6'):
            with (Path('/proc/self/net') / name).open('rb') as stream:
                raw = stream.read(32 * 1024 + 1)
            if len(raw) > 32 * 1024:
                raise ValueError('Socket table exceeds bound')
            sockets[name] = raw.decode('ascii')
        result['private_network_sockets'] = sockets
    except Exception as exc:
        result['failures'].append('Sockets: ' + str(exc))
    debuggers = []
    try:
        env = diagnostic.wine_env.copy()
        # Game processes still disable automatic crash debugging. Only these
        # failure observers enable the pinned runtime's builtin debugger.
        env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe,mshtml,mscoree=;winedbg.exe=b'
        env['WINEDEBUG'] = '-all'
        # Wine 10's 32-bit debugger attaches before restart_if_wow64(), then
        # its 64-bit child attempts the same attachment and fails with error 5.
        # Start the native debugger directly; it supports the PE32 targets.
        command = [diagnostic.args.wine, r'C:\windows\system32\winedbg.exe']
        listing = ctx.start('game-failure-process-list', command + ['--command', 'info proc'],
                            env=env, cleanup=True)
        finish(ctx, listing, time.monotonic() + 12)
        result['wine_process_list'] = listing.text()[:32768]
        if listing.process.returncode != 0 or listing.overflow:
            raise ValueError('Wine process listing failed')
        targets = game_pids(listing.text())
        deadline = time.monotonic() + 25
        for pid, name in targets:
            script = 'info threads\nbt all\ninfo share\ndetach\nquit'
            child = ctx.start('game-failure-stack-' + str(pid),
                command + ['--command', script, str(pid)], env=env, cleanup=True)
            debuggers.append((pid, name, child))
        for pid, name, child in debuggers:
            finish(ctx, child, deadline)
            raw = child.text()
            result['stacks'].append({'wine_pid': pid, 'executable': name,
                'exit_code': child.process.poll(), 'forced_stop': child.forced_stop,
                'overflow': child.overflow, 'truncated': len(raw) > 128 * 1024,
                'output': base.redact(raw[:128 * 1024], ctx.secrets)})
            if (child.process.returncode != 0 or child.forced_stop or child.overflow
                    or len(raw) > 128 * 1024 or 'Backtrace:' not in raw):
                result['failures'].append('Stacks: incomplete or failed observer for ' + name + ' PID ' + str(pid))
        result['stacks_available'] = not any(value.startswith('Stacks:') for value in result['failures'])
    except Exception as exc:
        result['failures'].append('Stacks: ' + str(exc))
    finally:
        for _, _, child in debuggers:
            if child.process.poll() is None or child.reader.is_alive():
                child.stop()
            ctx.record(child, refresh=True)
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
