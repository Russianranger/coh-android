#!/usr/bin/env python3
"""ArmPort M3 guest: the original server stack plus the ARM64 client.

Runs inside the app runtime's PRoot guest, next to the pinned
android/guest/game_diagnostic.py (copied to /opt/coh-m3 by the host driver).
The original steps are reused unchanged: private runtime, PostgreSQL, Wine,
fake-auth DbServer, Atlas MapServer, and a character created and saved by the
original TestClient. Then the host starts the ARM64 CityOfHeroes.exe inside
this run's network namespace against 127.0.0.1 and types the login on its X
display (armport_game_host.py); this
script watches the database until that character is connected on Atlas.

Coordination with the host is by small JSON files in /state:
  armport-ready.json           here: servers up, TestClient character saved
  armport-client-started.json  host: client launched in this network namespace
  armport-play-sent.json       host: Play pressed on character select
  armport-client-exited.json   host: client process ended (exit status)
  armport-atlas.json           here: DB status once connected on Atlas
  armport-host-done.json       host: in-game screenshots taken
  armport-guest-finished.json  here: client phase over
  armport-client-stopped.json  host: client and its wineserver stopped
Environment (set by the host command): ARMPORT_CLIENT_SECONDS.
"""
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, '/opt/coh-m3')
import game_diagnostic as gd  # noqa: E402
import server_atlas_data  # noqa: E402

base, require, evidence = gd.base, gd.require, gd.evidence
STATE = Path('/state')
# This longer-lived M3 stack exceeded the stock 2 MiB capture in 40176407354
# before the 25-minute client observation ended. Keep all output and the
# original fatal overflow check, with a finite 8 MiB per-child capture.
# This is confined to this invocation, like the app interactive host's own
# larger capture budget; no filtering or server executable change is made.
SERVER_OUTPUT_LIMIT = 8 * 1024 * 1024
base.OUTPUT_LIMIT = SERVER_OUTPUT_LIMIT
CLIENT_QUERY_LIMIT = 40
# The client phase adds up to CLIENT_QUERY_LIMIT status queries (plus a final
# one) to the original flow's budget of 80.
gd.QUERY_LIMIT = 120


def write_marker(name, value):
    path = STATE / name
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)


class ArmPortGame(gd.GameDiagnostic):
    def execute(self):
        # Same order as GameDiagnostic.execute up to the first saved logout.
        self.game['owned_output_limit_bytes'] = SERVER_OUTPUT_LIMIT
        self.prepare_runtime()
        self.ctx.stage('armport_server_atlas_supplement')
        self.game['atlas_supplement'] = server_atlas_data.stage(
            Path('/opt/coh-m3/atlas-supplement'), self.runtime / 'data',
            Path('/opt/coh-m3/atlas-world-supplement-manifest.json'))
        self.ctx.passed(**self.game['atlas_supplement'])
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
        # Lowercase letters and digits only: typed into the client's login
        # screen key by key (no Shift handling needed).
        self.game['account'] = 'coha' + os.urandom(5).hex()
        self.start_services('first')
        self.observe_atlas()
        session = self.create_character()
        # live_currency sets influence 12345, which logout's saved snapshot
        # is validated against; keep the original order.
        self.live_currency(session)
        self.logout(session, 'first', 1)
        self.armport_client()
        self.game.update(status='passed', query_processes=self.query_count, readiness_queries=self.readiness_count)

    def observe_atlas(self):
        """The original 30 s observation; repeated once in full if Atlas
        missed a heartbeat (seen in 3 of 4 runs on 2026-10-23 before any
        ArmPort step). Recorded as atlas_observation_retry."""
        try:
            return super().observe_atlas()
        except base.DiagnosticError as exc:
            if 'lost current readiness' not in str(exc):
                raise
            self.game['atlas_observation_retry'] = {'first_failure': str(exc), 'failed_utc': base.utc()}
        next_status = 0

        def ready():
            nonlocal next_status
            if time.monotonic() < next_status:
                return False
            next_status = time.monotonic() + 20
            return evidence.map_ready_current(self.map_status('retry-ready', timeout=90))
        self.wait(ready, 300, 'Atlas current readiness before the repeated observation')
        result = super().observe_atlas()
        self.game['atlas_observation_retry']['second_observation_passed'] = True
        return result

    def armport_client(self):
        """The host runs the ARM64 client (as in M2, with the host's Wine,
        Xvfb and Mesa) inside this run's private network namespace; this
        side only tells it when the servers are ready and watches the
        database for the character on Atlas."""
        self.ctx.stage('armport_arm64_client_atlas')
        seconds = int(os.environ.get('ARMPORT_CLIENT_SECONDS', '1500'))
        character = self.game['character']
        write_marker('armport-ready.json', {
            'account': self.game['account'], 'character': character['name'],
            'container_id': character['container_id'], 'ready_utc': base.utc()})
        record = {'connected_on_atlas': False, 'samples': []}
        self.game['armport_client'] = record
        started, exited, play_sent = (STATE / name for name in (
            'armport-client-started.json', 'armport-client-exited.json', 'armport-play-sent.json'))
        self.wait(lambda: started.exists() or exited.exists(), 600, 'ARM64 client start on the host')
        deadline = time.monotonic() + seconds
        next_status = 0
        queries = 0
        while time.monotonic() < deadline:
            self.health()
            if exited.exists():
                record['client_exit'] = json.loads(exited.read_text())
                break
            # Each status query is a MapServer -dbquery process within the
            # run's budget: once a minute until the host has pressed Play,
            # then every 15 s, at most CLIENT_QUERY_LIMIT in this phase.
            if time.monotonic() >= next_status and queries < CLIENT_QUERY_LIMIT:
                next_status = time.monotonic() + (15 if play_sent.exists() else 60)
                queries += 1
                record['status_queries'] = queries
                sample = self.character_status('armport', allow_missing=True)
                record['samples'] = (record['samples'] + [dict(sample, sampled_utc=base.utc())])[-20:]
                if evidence.connected_on_atlas(sample):
                    record.update(connected_on_atlas=True, atlas_status=sample, connected_utc=base.utc())
                    write_marker('armport-atlas.json', {'connected_on_atlas': True, 'status': sample})
                    break
            time.sleep(1)
        if record['connected_on_atlas']:
            # Let the host take its in-game screenshots, then check the
            # character is still connected.
            done = STATE / 'armport-host-done.json'
            # Allow the host's 1500 s loading budget plus excluded debugger
            # pauses, the last capture/OCR iteration and final observation.
            # This is coordination headroom, not extra loading-success time.
            self.wait(lambda: done.exists() or exited.exists(), 2100, 'Host in-game screenshots')
            record['host_done'] = done.exists()
            require(not exited.exists(), 'ARM64 client exited on Atlas')
            sample = self.character_status('armport-final', allow_missing=True)
            record['final_status'] = sample
            record['still_connected'] = evidence.connected_on_atlas(sample)
        self.stop_host_client()
        record['client_stopped_before_cleanup'] = True
        require(record['connected_on_atlas'], 'ARM64 client did not reach Atlas: ' + json.dumps(record['samples'][-1:]))
        require(record.get('still_connected'), 'ARM64 client did not stay connected on Atlas')
        self.ctx.passed(arm64_client_on_atlas=True, map_id=record['atlas_status'].get('map_id'))

    def stop_host_client(self):
        # Also used after health()/overflow raises: self.wait would call health
        # again and abort before the host can stop its same-UID sudo/Wine tree.
        write_marker('armport-guest-finished.json', {'client_phase_finished': True})
        stopped = STATE / 'armport-client-stopped.json'
        deadline = time.monotonic() + 180
        while not stopped.exists():
            require(time.monotonic() < deadline, 'Host did not stop the ARM64 client before cleanup')
            time.sleep(1)
        receipt = json.loads(stopped.read_text())
        require(isinstance(receipt, dict) and receipt.get('stopped') is True
                and receipt.get('errors') == [],
                'Host ARM64 client teardown failed: ' + json.dumps(receipt))

    def cleanup(self):
        failures = []
        # No host launch is possible before ready. Once ready exists the host
        # may be launching, even if its started marker has not arrived yet.
        if (STATE / 'armport-ready.json').exists():
            try:
                self.stop_host_client()
            except Exception as exc:
                failures.append('Host client cleanup coordination: ' + str(exc))
        # Preserve the original ownership audit and all service cleanup even
        # when coordination fails; the original execution error stays recorded.
        return failures + super().cleanup()


def main(argv=None):
    gd.GameDiagnostic = ArmPortGame
    return gd.main(argv)


if __name__ == '__main__':
    sys.exit(main())
