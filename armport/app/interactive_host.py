#!/usr/bin/env python3
"""Exercise the selected ARM64 creation/reopen guest with retained app assets."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import platform
import secrets
import shutil
import socket
import subprocess
import time
import zipfile

import retained_assets
import stage_app_assets
import runtime_host

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('armport_existing_reopen_host',
    ROOT / 'tools/android/interactive/character_reopen_host_smoke.py')
reopen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reopen)
character, require = reopen.character, reopen.require


def legacy_report(report, runtime_manifest, client_manifest):
    """Validate the ARM64 additions before using the existing persistence checks."""
    expected = runtime_manifest['armport_client']
    observed = report.get('armport_client', {})
    require(observed.get('machine') == 'ARM64' and observed.get('x86_bins_reused') is False
            and all(observed.get(key) == expected[key] for key in
                    ('archive_sha256', 'executable_sha256', 'client_run_id', 'data_run_id')),
            'Selected ARM64 client identity differs')
    require(report.get('asset_sha256') == {name: pin['sha256']
            for name, pin in client_manifest['files'].items()}, 'Complete ARM64 guest input hashes differ')
    stages = report.get('stages', [])
    found = [(i, item) for i, item in enumerate(stages) if item.get('stage') == 'armport_client_data']
    require(len(found) == 1 and found[0][0] == len(stages) - 4
            and found[0][1].get('status') == 'passed'
            and found[0][1].get('machine') == 'ARM64'
            and found[0][1].get('x86_bins_reused') is False
            and found[0][1].get('executable_sha256') == expected['executable_sha256'],
            'ARM64 preparation was missing, failed, misordered or for another executable')
    result = copy.deepcopy(report)
    result['stages'].pop(found[0][0])
    result['asset_sha256'] = {name: report['asset_sha256'][name]
                             for name in character.host.assets_tool.PROBE_FILES}
    return result



def guest_failure_summary(evidence):
    """Bounded diagnostic only; never changes ownership/cleanup validation."""
    result = {}
    try:
        path = evidence / 'latest-report.json'
        if path.is_file() and path.stat().st_size <= 16 * 1024 * 1024:
            report = json.loads(path.read_text())
            result['failures'] = [str(item)[:400] for item in report.get('failures', [])[:6]]
            result['failed_stages'] = [item.get('stage') for item in report.get('stages', [])
                                       if item.get('status') == 'failed'][:8]
        path = evidence / 'report.zip'
        if path.is_file():
            with zipfile.ZipFile(path) as archive:
                info = archive.getinfo('client-evidence/client-console.log')
                if info.file_size <= 8 * 1024 * 1024:
                    lines = archive.read(info).decode('utf-8', errors='replace').splitlines()
                    result['client_faults'] = [line[:500] for line in lines
                        if 'Unhandled' in line or 'unhandled exception' in line.lower()
                        or 'page fault' in line.lower()][:3]
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        result['evidence_read_error'] = str(error)[:300]
    return result


def ci_notice(result):
    text = json.dumps(result, separators=(',', ':'))
    text = text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    return '::notice title=ArmPort M4 interactive result::' + text


def run_session(command, work, evidence, proot, session, runtime_manifest, client_manifest,
                deadline, reopening=False):
    evidence.mkdir(parents=True)
    isolated, environment, expected_network = runtime_host.runtime.isolate_command(
        command, evidence=evidence, proot=proot, work=work)
    process = observer = failure = report = None
    with (evidence / 'host-client.log').open('w') as log:
        try:
            process = subprocess.Popen(isolated, env=environment, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            endpoint = work / 'socket/view.sock'
            while not endpoint.exists():
                require(process.poll() is None and time.monotonic() < deadline,
                        'ARM64 guest exited or timed out before its private display')
                time.sleep(.1)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(90)
                connection.connect(str(endpoint))
                observer = character.observe_rfb(connection, session, process, deadline, evidence,
                    evidence / 'host-client.log', work / 'state/interaction-finish.json',
                    reopen.ReopenInteraction if reopening else None,
                    reopen.ReopenEvents if reopening else None)
            require(observer.get('failure') is None, observer.get('failure') or 'ARM64 RFB observer failed')
            require(process.wait(timeout=max(1, deadline - time.monotonic())) == 0,
                    'ARM64 interactive guest exited unsuccessfully')
            report = json.loads((work / 'state/latest-report.json').read_text())
            projected = legacy_report(report, runtime_manifest, client_manifest)
            (reopen.validate_report if reopening else character.validate_report)(projected, session, runtime_manifest)
            if not reopening:
                reopen.validate_world_supplement(projected, runtime_manifest)
            (reopen.validate_observer if reopening else character.validate_observer)(observer, report)
            require(not endpoint.exists(), 'Private display survived guest cleanup')
            runtime_host.runtime.validate_network_receipt(
                json.loads((evidence / 'network-isolation.json').read_text()), expected_network)
        except Exception as error:
            failure = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            cleanup = character.stop_guest(process, work / 'state')
            exported = character.export_guest_evidence(work / 'state', evidence, session)
            (evidence / 'host-session-report.json').write_text(json.dumps({
                'scope': 'arm64_app_guest_reopen' if reopening else 'arm64_app_guest_creation',
                'session_id': session, 'passed': failure is None, 'failure': failure,
                'external_observer': observer, 'host_cleanup': cleanup,
                'guest_evidence_export': exported, 'guest_failure': guest_failure_summary(evidence)}, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('apk', 'build-report', 'armport', 'archive', 'proot', 'work', 'evidence'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path): setattr(args, name, value.resolve())
    require(platform.machine().lower() in ('aarch64', 'arm64'), 'Native ARM64 runner required')
    require(shutil.which('tesseract') is not None, 'Existing RFB driver requires tesseract')
    require(not args.work.exists() and not args.evidence.exists(), 'Fresh private work/evidence required')
    args.work.mkdir(mode=0o700)
    args.evidence.mkdir(parents=True)
    result = {'scope': 'arm64_app_guest_creation_and_reopen', 'passed': False,
              'm4_complete': False, 'apk_built': False, 'android_surface_validated': False,
              'repository_commit': args.repository_commit}
    started = time.monotonic()
    try:
        donor = args.work / 'donor-assets'
        result['donor'] = retained_assets.extract(args.apk, args.build_report, donor)
        assets = args.work / 'armport-assets'
        result['armport_client'] = stage_app_assets.stage(donor / 'runtime', args.armport,
                                                        assets, args.repository_commit)
        runtime_manifest = json.loads((assets / 'runtime-manifest.json').read_text())
        client_manifest = json.loads((assets / 'client-manifest.json').read_text())
        # The imported data uses the existing Java importer and exact donor contract.
        data = character.host.import_game_data(donor / 'atlas', args.archive, args.work, args.evidence)
        first, second = secrets.token_hex(16), secrets.token_hex(16)
        require(first != second, 'Distinct session identities required')
        command, _ = character.make_command(args.work, assets, args.proot, first, data, 900)
        command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_ARCH=arm64')
        command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_GRAPHICS_PROFILE=standard')
        deadline = time.monotonic() + character.OVERALL_SECONDS
        created = run_session(command, args.work, args.evidence / 'creation', args.proot,
                              first, runtime_manifest, client_manifest, deadline)
        before = reopen.persistent_profile_identity(args.work)
        reopen.archive_completed_reports(args.work / 'state', first)
        reopen.reset_session_requests(args.work / 'state')
        next_command = reopen.reopen_command(command, first, second)
        reopened = run_session(next_command, args.work, args.evidence / 'reopen', args.proot,
                               second, runtime_manifest, client_manifest, deadline, reopening=True)
        after = reopen.persistent_profile_identity(args.work)
        reopen.validate_continuity(created, reopened, before, after)
        result.update(passed=True, same_persistent_profile=True, same_character_id=True,
                      creation_session_id=first, reopen_session_id=second)
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        result['guest_failures'] = {name: guest_failure_summary(args.evidence / name)
                                    for name in ('creation', 'reopen')
                                    if (args.evidence / name).exists()}
        (args.evidence / 'host-report.json').write_text(json.dumps(result, indent=2) + '\n')
        print(ci_notice({key: result.get(key) for key in
            ('passed', 'm4_complete', 'elapsed_seconds', 'error', 'guest_failures')}), flush=True)
        print(json.dumps(result), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
