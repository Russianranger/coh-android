#!/usr/bin/env python3
"""Exercise the selected ARM64 creation/reopen guest with retained app assets."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
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


# Creator transition checks for the ARM64 lane (Astra review 5672637914, OCR
# evidence in PR #8 comment 6451908706). The shared host driver clicks fixed
# positions; a primary power click that did not register left the creator on
# the Powers page ("Choose Primary Power set and Power to continue") and later
# steps failed far downstream ("Rendered No button not found").
PRIMARY_HINT_REGION = (480, 530, 780, 565)
PRIMARY_RETRIES = 2
COSTUME_TOKENS = {'head', 'weapons', 'colors'}
COSTUME_ATTEMPTS = 5


def ocr_words(tsv):
    """Level-5 OCR words with confidence of at least 20, casefolded."""
    import csv, io
    words = set()
    for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
        try:
            if int(row['level']) == 5 and float(row['conf']) >= 20:
                text = (row.get('text') or '').strip().strip('.,:;!?[](){}<>|').casefold()
                if text: words.add(text)
        except (KeyError, TypeError, ValueError):
            continue
    return words


def primary_selection_pending(tsv):
    words = ocr_words(tsv)
    return 'choose' in words and 'primary' in words


def costume_page_shown(tsv):
    return bool(ocr_words(tsv) & COSTUME_TOKENS)


def armport_creation_actions():
    actions = list(character.creation_actions())
    names = [action[2] for action in actions]
    actions.insert(names.index('select_primary_power') + 1,
                   ('verify_primary', None, 'verify_primary_power_selected'))
    names = [action[2] for action in actions]
    actions.insert(names.index('body_next') + 1, ('verify_costume', None, 'verify_costume_page'))
    return tuple(actions)


class ArmPortCharacterInteraction(character.CharacterInteraction):
    """The shared creation script plus page-transition proof before later clicks."""
    ACTIONS = character.CharacterInteraction.LOGIN_ACTIONS + armport_creation_actions()

    def __init__(self, session, evidence, finish_path):
        super().__init__(session, evidence, finish_path)
        self.result['armport_transition_checks'] = []
        self.primary_retries = 0
        self.costume_attempts = 0

    def custom_action(self, kind, value, name, connection, frame, events, sequence, now):
        if kind not in ('verify_primary', 'verify_costume'):
            return super().custom_action(kind, value, name, connection, frame, events, sequence, now)
        if kind == 'verify_primary':
            tsv, stem = character.read_ocr(frame, self.evidence, name, self.primary_retries + 1, PRIMARY_HINT_REGION)
            pending = primary_selection_pending(tsv)
            self.result['armport_transition_checks'].append({'check': name, 'retry': self.primary_retries,
                'primary_selection_pending': pending, 'evidence': stem, 'frame_sequence': sequence})
            if pending:
                require(self.primary_retries < PRIMARY_RETRIES,
                        'Primary power selection did not register after %d retries; the creator is still on '
                        'the Powers page ("Choose Primary Power set and Power to continue")' % PRIMARY_RETRIES)
                self.primary_retries += 1
                # Replay the set and power selection; on_frame then advances to it.
                self.action = next(index for index, action in enumerate(self.ACTIONS)
                                   if action[2] == 'preposition_select_primary_set') - 1
            return True
        tsv, stem = character.read_ocr(frame, self.evidence, name, self.costume_attempts + 1, (0, 0, 800, 600))
        shown = costume_page_shown(tsv)
        self.costume_attempts += 1
        self.result['armport_transition_checks'].append({'check': name, 'attempt': self.costume_attempts,
            'costume_page_shown': shown, 'evidence': stem, 'frame_sequence': sequence})
        if not shown:
            require(self.costume_attempts < COSTUME_ATTEMPTS,
                    'Costume page (HEAD/WEAPONS/Colors) not reached after body_next; inspect retained creator frames')
            # Stay on this check: wait for later frames before trying again.
            self.action -= 1
        return True


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
    # The current installer reports legacy-link repair counters; the retained
    # host validator predates them. Only a proven no-repair receipt is eligible
    # for projection. All original pins, counts and preservation checks remain
    # in character.validate_report; unexpected fields still fail there.
    avatar = result.get('character_avatar_supplement', {})
    counters = ('legacy_repaired_files', 'legacy_backing_files_removed')
    if any(name in avatar for name in counters):
        require(all(type(avatar.get(name)) is int and avatar[name] == 0
                    for name in counters), 'Avatar legacy repair requires separate qualification')
        for name in counters:
            del avatar[name]
    world = result.get('atlas_world_supplement', {})
    metrics = ('reuse_validation', 'archive_read_bytes', 'decoded_files',
               'decoded_payload_bytes', 'preparation_elapsed_seconds')
    if any(name in world for name in metrics):
        contract = runtime_manifest.get('armport_world_contract') or character.host.assets_tool.world_tools().bundle_contract()
        fresh = world.get('reuse_validation') == 'pinned_content_verification'
        reused = world.get('reuse_validation') == 'unchanged_filesystem_receipt'
        require(fresh or reused, 'Unknown world verification method')
        expected_metrics = dict(archive_read_bytes=contract['archive_pin']['bytes'] if fresh else 0,
            decoded_files=contract['file_count'] if fresh else 0,
            decoded_payload_bytes=contract['payload_bytes'] if fresh else 0)
        require(all(type(world.get(k)) is int and world[k] == v for k, v in expected_metrics.items())
                and world.get('installed_files') == expected_metrics['decoded_files']
                and world.get('reused_files') == (0 if fresh else contract['file_count']),
                'World preparation metrics differ from complete fresh/reused staging')
        elapsed = world.get('preparation_elapsed_seconds')
        require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0,
                'Invalid world preparation timing')
        for name in metrics:
            del world[name]
    result['asset_sha256'] = {name: report['asset_sha256'][name]
                             for name in character.host.assets_tool.PROBE_FILES}
    return result



def validation_manifest(report, runtime_manifest):
    """Compute the current worktree identity from host-verified native inputs."""
    native = runtime_manifest['armport_server_native_closure']
    work = report['client_worktree']
    require(work['package_sha256'] == runtime_manifest['files']['client-runtime.zip']['sha256'],
            'Server data worktree package differs')
    for field, name in (('cache_archive_sha256', 'client-caches.zip'),
                        ('prerequisites_archive_sha256', 'client-prerequisites.zip')):
        require(work[field] == runtime_manifest['files'][name]['sha256'], 'Server data archive differs')
    data = {k: work[k] for k in ('format', 'source_data', 'import', 'cache_archive_sha256',
        'prerequisites_archive_sha256', 'prerequisites_manifest_sha256', 'normalized_mtime_epoch')}
    digest = hashlib.sha256(json.dumps({'data': data, 'native': native},
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    key = 'client-work-' + digest[:24]
    require(work.get('content_identity_sha256') == digest and work.get('worktree_key') == key,
            'Server data content identity differs')
    return dict(runtime_manifest, armport_expected_worktree_key=key)


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
                    reopen.ReopenInteraction if reopening else ArmPortCharacterInteraction,
                    reopen.ReopenEvents if reopening else None)
            require(observer.get('failure') is None, observer.get('failure') or 'ARM64 RFB observer failed')
            require(process.wait(timeout=max(1, deadline - time.monotonic())) == 0,
                    'ARM64 interactive guest exited unsuccessfully')
            report = json.loads((work / 'state/latest-report.json').read_text())
            projected = legacy_report(report, runtime_manifest, client_manifest)
            checked_manifest = validation_manifest(report, runtime_manifest)
            require(time.monotonic() <= deadline, 'ARM64 interactive host deadline exceeded')
            if reopening:
                finish_request = observer.get('interaction_script', {}).get('finish_request')
                require(finish_request is not None, 'Missing host explicit-finish request')
                reopen.validate_report(projected, session, checked_manifest, finish_request=finish_request)
            else:
                character.validate_report(projected, session, checked_manifest)
            if not reopening:
                reopen.validate_world_supplement(projected, checked_manifest)
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
        # stage() verified this archive against the retained donor's exact hash.
        with zipfile.ZipFile(assets / 'client-runtime.zip') as archive:
            native = json.loads(archive.read('client-package.json'))
        runtime_manifest['armport_server_native_closure'] = {
            key: native[key] for key in ('source_commit', 'data_commit', 'files')}
        world_tool = character.host.assets_tool.world_tools()
        world = json.loads((assets / world_tool.MANIFEST).read_text())
        runtime_manifest['armport_world_manifest'] = world
        runtime_manifest['armport_world_contract'] = dict(
            scope=world['scope'], manifest_pin=runtime_manifest['files'][world_tool.MANIFEST],
            archive_pin=runtime_manifest['files'][world_tool.ARCHIVE],
            file_count=world['file_count'], payload_bytes=world['payload_bytes'],
            files_sha256=hashlib.sha256(json.dumps(world['files'], sort_keys=True,
                separators=(',', ':')).encode()).hexdigest())
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
