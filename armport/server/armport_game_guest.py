#!/usr/bin/env python3
"""ArmPort M3 guest: the original server stack plus the ARM64 client.

Runs inside the app runtime's PRoot guest, next to the pinned
android/guest/game_diagnostic.py (copied to /opt/coh-m3 by the host driver).
The original steps are reused unchanged: private runtime, PostgreSQL, Wine,
fake-auth DbServer, Atlas MapServer, and a character created and saved by the
original TestClient. Then the ARM64 CityOfHeroes.exe (staged by the host in
/opt/armport-client) starts in the same Wine against 127.0.0.1. The host
driver types the login on the shared X display (armport_game_host.py); this
script watches the database until that character is connected on Atlas.

Coordination with the host is by small JSON files in /state:
  armport-client-started.json  written here: account, character, pid
  armport-atlas.json           written here: DB status once connected on Atlas
  armport-host-done.json       written by the host when its screenshots are taken
Environment (set by the host command): ARMPORT_CLIENT_DIR, ARMPORT_DISPLAY,
ARMPORT_CLIENT_SECONDS.
"""
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, '/opt/coh-m3')
import game_diagnostic as gd  # noqa: E402

base, require, evidence = gd.base, gd.require, gd.evidence
STATE = Path('/state')


def write_marker(name, value):
    path = STATE / name
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)


class ArmPortGame(gd.GameDiagnostic):
    def execute(self):
        # Same order as GameDiagnostic.execute up to the first saved logout.
        self.prepare_runtime()
        self.initialize()
        self.start_postgres('postgres_first_start')
        self.prepare_database()
        self.start_wine()
        self.ctx.stage('win32_runtime_dll')
        result = self.ctx.run('runtime-probe', [self.args.wine, base.windows_path(self.args.assets / 'runtime-probe.exe')],
                              timeout=60, env=self.wine_env)
        self.ctx.passed(**base.validate_runtime_probe(result['output']))
        self.mark_wine_ready()
        config = self.runtime / 'data/server/db/servers.cfg'
        base.private_write(config, gd.game_config(config.read_text(), self.database, self.connection_for(self.database)))
        self.private_connections.append(config)
        self.bind_fixed_inputs()
        self.game['account'] = 'CohA' + os.urandom(5).hex()
        self.start_services('first')
        self.observe_atlas()
        session = self.create_character()
        self.logout(session, 'first', 1)
        self.armport_client()
        self.game.update(status='passed', query_processes=self.query_count, readiness_queries=self.readiness_count)

    def armport_client(self):
        self.ctx.stage('armport_arm64_client_atlas')
        client_dir = Path(os.environ.get('ARMPORT_CLIENT_DIR', '/opt/armport-client'))
        exe = client_dir / 'CityOfHeroes.exe'
        require(exe.is_file(), 'ARM64 client is not staged')
        seconds = int(os.environ.get('ARMPORT_CLIENT_SECONDS', '1200'))
        env = dict(self.wine_env, DISPLAY=os.environ.get('ARMPORT_DISPLAY', ':99'),
                   ARMPORT_LOOSE_DATA='1', ARMPORT_STDIO_LOG='armport_stdio.txt',
                   LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe',
                   # Quiet: the guest fails any owned process past 2 MB of output; Wine
                   # still prints its unhandled-exception line with the address.
                   WINEDEBUG='-all')
        args = ['-fullscreen', '0', '-screen', '1024', '768', '-verbose', '1', '-db', '127.0.0.1']
        client = self.ctx.start('armport-client', ['/usr/bin/env', '--chdir=' + str(client_dir), self.args.wine,
                                base.windows_path(exe), *args], env=env)
        character = self.game['character']
        write_marker('armport-client-started.json', {
            'account': self.game['account'], 'character': character['name'],
            'container_id': character['container_id'], 'started_utc': base.utc(), 'args': args})
        record = {'args': args, 'connected_on_atlas': False, 'samples': []}
        self.game['armport_client'] = record
        deadline = time.monotonic() + seconds
        next_status = 0
        while time.monotonic() < deadline:
            self.health()
            if client.process.poll() is not None:
                record['client_exit'] = client.process.poll()
                break
            if time.monotonic() >= next_status:
                next_status = time.monotonic() + 10
                sample = self.character_status('armport', allow_missing=True)
                record['samples'] = (record['samples'] + [dict(sample, sampled_utc=base.utc())])[-20:]
                if evidence.connected_on_atlas(sample):
                    record.update(connected_on_atlas=True, atlas_status=sample, connected_utc=base.utc())
                    write_marker('armport-atlas.json', {'connected_on_atlas': True, 'status': sample})
                    break
            time.sleep(1)
        if record['connected_on_atlas']:
            # Let the host take its in-game screenshots, then keep the client
            # alive a little longer to show it stays connected.
            done = STATE / 'armport-host-done.json'
            limit = time.monotonic() + 300
            while time.monotonic() < limit and not done.exists():
                self.health()
                require(client.process.poll() is None, 'ARM64 client exited on Atlas')
                time.sleep(1)
            record['host_done'] = done.exists()
            sample = self.character_status('armport-final', allow_missing=True)
            record['final_status'] = sample
            record['still_connected'] = evidence.connected_on_atlas(sample)
        record['client_output_tail'] = client.text()[-4000:]
        if client.process.poll() is None:
            client.process.kill()
            client.process.wait(timeout=30)
        require(record['connected_on_atlas'], 'ARM64 client did not reach Atlas: ' + json.dumps(record['samples'][-1:]))
        require(record.get('still_connected'), 'ARM64 client did not stay connected on Atlas')
        self.ctx.passed(arm64_client_on_atlas=True, map_id=record['atlas_status'].get('map_id'))


def main(argv=None):
    gd.GameDiagnostic = ArmPortGame
    return gd.main(argv)


if __name__ == '__main__':
    sys.exit(main())
