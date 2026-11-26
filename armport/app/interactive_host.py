#!/usr/bin/env python3
"""Exercise the selected ARM64 creation/reopen guest with retained app assets."""
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import socket
import subprocess
import time
import zipfile

import mapserver_phases
import retained_assets
import stage_app_assets
import runtime_host
import server_pipeline
import trap_sampler

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'armport/audio'))
import audio_receiver
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
# 20 since 0.13.85: with every costume piece unlocked the page was not up within 5 checks (run 45582592008).
COSTUME_ATTEMPTS = 20
# After this many checks without the costume page the Next click of the Body page is sent again:
# in runs 45582592008 and 45595038618 the creator stayed on the Body page (its words: Body, HUGE
# read as HIDE, the hero's name) while the same script went through in three other runs.
COSTUME_RECLICK_AT = (3, 8)


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


def screen_words(tsv, limit=90, width=20):
    """The OCR words of a frame in reading order, bounded, for a failure notice."""
    import csv, io
    words = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
        try:
            if int(row['level']) == 5 and float(row['conf']) >= 20:
                text = ''.join(c for c in (row.get('text') or '').strip() if c.isalnum() or c in "-'/")
                if len(text) > 1: words.append(text[:width])
        except (KeyError, TypeError, ValueError):
            continue
    return words[:limit]


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
        # What the screen says, shown or not (read from the job log; frames are not downloadable).
        self.result['armport_transition_checks'][-1]['words'] = screen_words(tsv)
        if not shown:
            require(self.costume_attempts < COSTUME_ATTEMPTS,
                    'Costume page (HEAD/WEAPONS/Colors) not reached after body_next; inspect retained creator frames')
            if self.costume_attempts in COSTUME_RECLICK_AT:
                # The Next click did not register: move there and click again, then check again.
                self.result['armport_transition_checks'][-1]['reclick'] = True
                self.action = next(index for index, action in enumerate(self.ACTIONS)
                                   if action[2] == 'preposition_body_next') - 1
            else:
                # Stay on this check: wait for later frames before trying again.
                self.action -= 1
        return True


# 0.13.87 (CI only): several heroes in the one account. After the two ordinary sessions a third
# makes a second hero from the game's character list during a reopen ("Play"), and a fourth enters
# with the first hero while the second, played last, is the one the launch expects.
HEROES_PROBE_ENV = 'COH_HEROES_PROBE'
SECOND_HERO = 'HEROTWO'
# The second slot of the character list: uiLogin.c draws 13 slots in 660 units of its 1024x768
# layout (LINE_HEIGHT), 39.7 pixels each at 800x600; the first is clicked at (200, 72).
SECOND_SLOT = (200, 112)
CREATOR_ATTEMPTS = 12
HEROES_PROBE_SECONDS = 3000


def heroes_probe_requested():
    value = os.environ.get(HEROES_PROBE_ENV, '')
    require(value in ('', '0', '1'), HEROES_PROBE_ENV + ' must be empty, 0 or 1')
    return value == '1'


def creator_opened(tsv, listed=None):
    """The creator's first page: it names Primal Earth and Praetorian Earth, and the character
    list (with the first hero's name, which the reopen script finds by the same reading) is gone.
    None: neither is certain on this frame."""
    words = {word.casefold() for word in screen_words(tsv, limit=200)}
    if words & {'primal', 'praetorian', 'praetoria'}:
        return True
    if listed is not None and listed.casefold() in words:
        return False
    return None


def second_hero_actions(name):
    creation = list(armport_creation_actions())
    names = [action[2] for action in creation]
    body = [('text', name, action[2]) if action[2] == 'enter_character_name' else action
            for action in creation[names.index('preposition_select_primal_earth'):]]
    actions = [('login', None, 'wait_existing_character_list'),
               ('move', (600, 100), 'clear_cursor_before_second_slot')]
    actions += character.click_steps('open_second_character_creator', *SECOND_SLOT)
    actions += [('verify_creator', None, 'verify_creator_opened')]
    return tuple(actions + body)


class SecondHeroInteraction(ArmPortCharacterInteraction):
    """A reopen session in which the script makes a new hero in the second slot of the character list."""
    ACTIONS = character.CharacterInteraction.LOGIN_ACTIONS + second_hero_actions(SECOND_HERO)
    FIRST_HERO = None      # the name on the character list (set by the probe before the session)

    def __init__(self, session, evidence, finish_path):
        super().__init__(session, evidence, finish_path)
        self.creator_attempts = self.creator_unsure = 0
        self.result['character_name'] = SECOND_HERO

    def custom_action(self, kind, value, name, connection, frame, events, sequence, now):
        if kind != 'verify_creator':
            return super().custom_action(kind, value, name, connection, frame, events, sequence, now)
        tsv, stem = character.read_ocr(frame, self.evidence, name, self.creator_attempts + 1, (0, 0, 800, 600))
        shown = creator_opened(tsv, self.FIRST_HERO)
        self.creator_attempts += 1
        self.creator_unsure = self.creator_unsure + 1 if shown is None else 0
        self.result['armport_transition_checks'].append({'check': name, 'attempt': self.creator_attempts,
            'creator_opened': shown, 'evidence': stem, 'frame_sequence': sequence, 'words': screen_words(tsv)})
        # Two frames in a row without the character list count as the creator (its page words
        # are small print); a frame that still shows the list is a click that did not register.
        if shown is True or self.creator_unsure >= 2:
            return True
        require(self.creator_attempts < CREATOR_ATTEMPTS,
                'The character creator did not open from the second slot of the character list')
        if shown is False and self.creator_attempts in (4, 8):
            self.result['armport_transition_checks'][-1]['reclick'] = True
            self.action = next(index for index, action in enumerate(self.ACTIONS)
                               if action[2] == 'preposition_open_second_character_creator') - 1
        else:
            self.action -= 1
        return True


def heroes_probe_validate(report, *, created):
    """What the two extra sessions must show (the guest has already proved each save itself)."""
    proof = report.get('character_reopen') if isinstance(report, dict) else None
    require(isinstance(proof, dict) and report.get('passed') is True and proof.get('verified') is True,
            'Heroes probe: the session did not end with a verified save')
    heroes = proof.get('heroes')
    require(isinstance(heroes, dict), 'Heroes probe: the session has no record of the account\'s heroes')
    if created:
        require(proof.get('created_in_session') is True and proof.get('name') == SECOND_HERO
                and type(proof.get('character_id')) is int and proof['character_id'] > 1
                and heroes.get('count') == 1 and heroes.get('expected_character_id') == 1
                and heroes.get('chosen_character_id') == proof['character_id']
                and heroes.get('choice') == 'created_in_the_character_list'
                and 'baseline_character_id' not in proof and proof.get('saved_heroes_at_start') == 1,
                'Heroes probe: the second hero was not followed as a hero made in the character list: '
                + json.dumps({key: proof.get(key) for key in ('created_in_session', 'name', 'character_id',
                                                               'heroes', 'operation')})[:600])
    else:
        require(proof.get('created_in_session') is not True and proof.get('character_id') == 1
                and proof.get('baseline_character_id') == 1 and proof.get('before_character_id') == 1
                and heroes.get('count') == 2 and type(heroes.get('expected_character_id')) is int
                and heroes['expected_character_id'] > 1 and heroes.get('chosen_character_id') == 1
                and heroes.get('choice') == 'another_saved_hero'
                and proof.get('login_count') == proof.get('before_login_count', -2) + 1,
                'Heroes probe: the first hero was not followed as another saved hero: '
                + json.dumps({key: proof.get(key) for key in ('character_id', 'baseline_character_id',
                                                               'heroes', 'login_count', 'before_login_count')})[:600])
    return {'character_id': proof['character_id'], 'name': proof.get('name'), 'heroes': heroes,
            'created_in_session': proof.get('created_in_session') is True, 'map_id': proof.get('map_id')}


def armport_validate_observer(observer, report):
    """Prove the transition checks and their replays, then run the shared checks
    on the shared step sequence (one pass through each replayed segment)."""
    script = observer.get('interaction_script', {})
    checks = script.get('armport_transition_checks', [])
    primary = [c for c in checks if c.get('check') == 'verify_primary_power_selected']
    costume = [c for c in checks if c.get('check') == 'verify_costume_page']
    require(len(primary) + len(costume) == len(checks)
            and 1 <= len(primary) <= PRIMARY_RETRIES + 1
            and [c.get('retry') for c in primary] == list(range(len(primary)))
            and all(c.get('primary_selection_pending') is True for c in primary[:-1])
            and primary[-1].get('primary_selection_pending') is False
            and 1 <= len(costume) <= COSTUME_ATTEMPTS
            and [c.get('attempt') for c in costume] == list(range(1, len(costume) + 1))
            and all(c.get('costume_page_shown') is False for c in costume[:-1])
            and costume[-1].get('costume_page_shown') is True
            and all((c.get('reclick') is True) == (c['attempt'] in COSTUME_RECLICK_AT) for c in costume[:-1])
            and 'reclick' not in costume[-1]
            and all(isinstance(c.get('evidence'), str) and c['evidence'] for c in checks),
            'Missing creator transition evidence (primary power selection, costume page)')
    names = [action[2] for action in ArmPortCharacterInteraction.ACTIONS]
    retry_start, account_check = names.index('preposition_account'), names.index('verify_rendered_account')
    accounts = len(script.get('account_entry_checks', []))
    replay_start = names.index('preposition_select_primary_set')
    primary_check, costume_check = names.index('verify_primary_power_selected'), names.index('verify_costume_page')
    head = (names[:retry_start] + names[retry_start:account_check] * accounts
            + names[account_check:replay_start] + names[replay_start:primary_check + 1] * len(primary)
            + names[primary_check + 1:costume_check])
    # Each costume check, followed by the replayed Next click (move, click) where one was sent.
    tail, tail_kept = [], []
    for check in costume:
        again = names[costume_check - 2:costume_check] if check.get('reclick') else []
        tail += [names[costume_check]] + again
        tail_kept += [False] * (1 + len(again))
    tail += names[costume_check + 1:]
    tail_kept += [True] * len(names[costume_check + 1:])
    expected = head + tail
    steps = script.get('steps', [])
    require([step.get('action') for step in steps] == expected,
            'Graphical creator script did not finish (ARM64 transition-checked sequence)')
    # Keep the account replays (the shared validator checks them), the final
    # primary pass, and drop the ARM64-only check steps.
    before = len(names[:retry_start]) + len(names[retry_start:account_check]) * accounts + len(names[account_check:replay_start])
    segment = primary_check + 1 - replay_start
    final_pass = before + segment * (len(primary) - 1)
    keep = steps[:before] + steps[final_pass:len(head)] + [step for step, kept in zip(steps[len(head):], tail_kept)
                                                           if kept]
    projected = copy.deepcopy(observer)
    projected['interaction_script']['steps'] = [copy.deepcopy(step) for step in keep
        if step.get('action') not in ('verify_primary_power_selected', 'verify_costume_page')]
    character.validate_observer(projected, report)


def legacy_report(report, runtime_manifest, client_manifest):
    """Validate the ARM64 additions before using the existing persistence checks."""
    server_pipeline.guest_admission(report, runtime_manifest)
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


FAILURE_AUDIO_LINE = re.compile(r'(?i)alsa|dsound|winealsa|mmdevapi|audio')
FAILURE_LOGOUT_LINE = re.compile(r'(?i)logout|quit|disconnect|saving|saved')


def dbserver_sql_failure(lines):
    """The DbServer's first real SQL error (not a NOTICE) with the lines around it, bounded."""
    first = next((i for i, l in enumerate(lines) if 'SQLERROR' in l and ' NOTICE' not in l), None)
    if first is None:
        return {}
    return {'dbserver_first_sql_error': [l[:2400] for l in lines[max(0, first - 3):first + 5]]}


FAILURE_FRAME_MARK = 'ARMPORT_FAILURE_FRAME_V1 '


def creator_costume_line(observer):
    """One log line on the creator's costume page checks: how many, and the words of the last."""
    script = observer.get('interaction_script') if isinstance(observer, dict) else None
    checks = script.get('armport_transition_checks') if isinstance(script, dict) else None
    costume = [c for c in checks or [] if isinstance(c, dict) and c.get('check') == 'verify_costume_page']
    if not costume:
        return None
    last = costume[-1]
    return 'ARMPORT_CREATOR_COSTUME_V1 ' + json.dumps({
        'attempts': len(costume), 'shown': last.get('costume_page_shown'),
        'words': [str(word)[:20] for word in (last.get('words') or [])[:90]]}, separators=(',', ':'))


def failure_frame_lines(evidence, limit=160000):
    """The newest retained frame of a failed session as text lines for the job log.

    Evidence archives cannot always be fetched; a 32-colour PNG of the last frame the host kept
    (base64, in parts; half size when the full one is too large) shows which screen the client
    was on. Empty when there is none.
    """
    import base64, io
    try:
        frames = sorted((p for p in evidence.glob('*.png') if p.is_file() and not p.is_symlink()),
                        key=lambda p: (p.stat().st_mtime_ns, p.name))
        # The frame of the last screen check when there is one: the final frame is taken after the stop.
        frames = [p for p in frames if '-ocr-' in p.name] or frames
        if not frames:
            return []
        from PIL import Image
        text = None
        with Image.open(frames[-1]) as image:
            image = image.convert('RGB')
            for divisor in (1, 2):  # full size when it fits, else half size
                small = image if divisor == 1 else image.resize(
                    (max(1, image.width // divisor), max(1, image.height // divisor)), Image.Resampling.LANCZOS)
                raw = io.BytesIO()
                small.quantize(32).save(raw, format='PNG', optimize=True)
                text = base64.b64encode(raw.getvalue()).decode('ascii')
                if len(text) <= limit:
                    break
        if text is None or len(text) > limit:
            return []
        parts = [text[i:i + 3000] for i in range(0, len(text), 3000)]
        return ['%sname=%s part=%d/%d %s' % (FAILURE_FRAME_MARK, frames[-1].name[:80], index, len(parts), part)
                for index, part in enumerate(parts, 1)]
    except (OSError, ValueError, ImportError) as error:
        return [FAILURE_FRAME_MARK + 'error=' + str(error)[:160].replace('\n', ' ')]


def failure_detail(evidence, work, observer):
    """Failed sessions only: what the client, Atlas and the host input did last.

    A separate notice (never part of host-report.json, whose guest_failures
    schema is qualified): the client's last frame-rate windows and output, its
    audio lines, the logout request against the time of this summary, and the
    Atlas MapServer's last logout/save lines. Every field is bounded.
    """
    def tail(lines, count, width=240):
        return [line[:width] for line in lines if line.strip()][-count:]
    result = {'summary_utc_ms': int(time.time() * 1000)}
    try:
        path = work / 'state/character-logout.json'
        if path.is_file() and not path.is_symlink() and path.stat().st_size <= 2048:
            result['logout_request'] = json.loads(path.read_text())
        if isinstance(observer, dict):
            script = observer.get('interaction_script') if isinstance(observer.get('interaction_script'), dict) else {}
            steps = script.get('steps', observer.get('steps'))
            result['observer_last_steps'] = [str(step)[:300] for step in steps[-4:]] if isinstance(steps, list) else None
            checks = script.get('armport_transition_checks')
            if isinstance(checks, list) and any(isinstance(c, dict) and 'words' in c for c in checks):
                seen = [c for c in checks if isinstance(c, dict) and isinstance(c.get('words'), list)]
                result['creator_screen_words'] = {'checks': len(checks), 'first': seen[0]['words'][:90],
                                                  'last': seen[-1]['words'][:90]}
            arrivals = script.get('stock_travel_arrivals')
            if isinstance(arrivals, list):
                result['stock_travel_arrivals'] = [str(item)[:300] for item in arrivals[:4]]
            resends = script.get('stock_travel_resends')
            if isinstance(resends, list) and resends:
                result['stock_travel_resends'] = [str(item)[:160] for item in resends[:4]]
        path = evidence / 'report.zip'
        if path.is_file():
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                def text(member):
                    if member in names and archive.getinfo(member).file_size <= 16 * 1024 * 1024:
                        return archive.read(member).decode('utf-8', errors='replace').splitlines()
                    return None
                stdio = text('client-evidence/armport_stdio.txt')
                if stdio is not None:
                    result['client_fps_tail'] = tail([l for l in stdio if l.startswith('ARMPORT_FRAME_RATE_V1')], 3)
                    unique = [l for i, l in enumerate(stdio) if not l.startswith('ARMPORT_FRAME_RATE_V1')
                              and (i == 0 or l != stdio[i - 1])]
                    result['client_stdio_tail'] = tail(unique, 6, 160)
                    dialogs = [l for l in stdio if l.startswith('ArmPort dialog:')]
                    result['client_dialogs'] = {'count': len(dialogs), 'last': [l[:120] for l in dialogs[-3:]]}
                    result['client_logout_keys'] = client_logout_keys('\n'.join(stdio))
                console = text('client-evidence/client-console.log')
                if console is not None:
                    audio = [line for line in console if FAILURE_AUDIO_LINE.search(line)]
                    result['client_console_audio'] = {'count': len(audio), 'first': [l[:240] for l in audio[:4]],
                                                      'last': tail(audio, 2)}
                    result['client_console_tail'] = tail(console, 6)
                atlas = text('client-evidence/character-atlas-console.txt')
                if atlas is not None:
                    result['atlas_logout_lines'] = tail([l for l in atlas if FAILURE_LOGOUT_LINE.search(l)], 6)
                    result['atlas_console_tail'] = tail(atlas, 4)
                dbserver = text('client-evidence/local-dbserver-console.txt')
                if dbserver is not None:
                    # Skip the connect retries and Wine object dumps; keep its own last words.
                    result['dbserver_console_tail'] = tail([l for l in dbserver if "Can't connect to dbserver" not in l
                                                            and not l.startswith('0x')], 8)
                    result.update(dbserver_sql_failure(dbserver))
                zones = sorted(name for name in names if re.fullmatch(
                    r'client-evidence/character-zoning-generation-\d+-map-\d+-console-tail\.txt', name))
                result['zone_console_tails'] = {name.split('/')[-1][:80]: tail(text(name) or [], 3) for name in zones[-4:]}
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        result['evidence_read_error'] = str(error)[:300]
    return result


ZONE_NOISE = re.compile(r"Can't connect to dbserver|^0x[0-9a-f]+:|\[DEBUG\]|ARMPORT_SERVER_METRICS_V1|^\s*$")
ZONE_SIGNAL = re.compile(r'xfer|map ?ready|cookie|delink|MapFailed|MapNotRunning|Sending char|starting|'
                         r'connect|assert|error|\b101\b|Step [0-9]', re.I)
ZONE_LOG_NOISE = re.compile(r'SQLERROR|COMMAND:|StackWalk|Heap is NOT|Pigg Error|No windows SYSTEM')


def zone_diagnostics(evidence, limit=3800, parts=3):
    """Failed stock-travel sessions: what the DbServer, the zone servers and their logs said.

    Separate notices (each GitHub annotation keeps about 4 KB): the DbServer
    console's own last lines, every zone server console's last and signal lines,
    Atlas's transfer lines, and the exported server logs' transfer lines.
    """
    def clip(lines, count, width=170):
        return [line.strip()[:width] for line in lines][-count:]
    sections = []
    try:
        with zipfile.ZipFile(evidence / 'report.zip') as archive:
            names = set(archive.namelist())
            def text(member):
                if member in names and archive.getinfo(member).file_size <= 32 * 1024 * 1024:
                    return archive.read(member).decode('utf-8', errors='replace').splitlines()
                return []
            quiet = lambda lines: [line for line in lines if not ZONE_NOISE.search(line)]
            sections.append(('dbserver_console', clip(quiet(text('client-evidence/local-dbserver-console.txt')), 12)))
            atlas = quiet(text('client-evidence/character-atlas-console.txt'))
            sections.append(('atlas_signal', clip([l for l in atlas if ZONE_SIGNAL.search(l)], 8)))
            for name in sorted(n for n in names if re.fullmatch(
                    r'client-evidence/character-zoning-map-\d+-console\.txt', n))[:3]:
                lines = quiet(text(name))
                label = name.split('/')[-1][:-len('-console.txt')]
                sections.append((label + '_last', clip(lines, 6)))
                sections.append((label + '_signal', clip([l for l in lines if ZONE_SIGNAL.search(l)], 8)))
            logs = 'client-evidence/character-server-logs.zip'
            if logs in names and archive.getinfo(logs).file_size <= 32 * 1024 * 1024:
                import io
                with zipfile.ZipFile(io.BytesIO(archive.read(logs))) as inner:
                    rows = []
                    for member in sorted(inner.namelist()):
                        if member.endswith('.log') and inner.getinfo(member).file_size <= 32 * 1024 * 1024:
                            for line in inner.read(member).decode('utf-8', errors='replace').splitlines():
                                if ZONE_SIGNAL.search(line) and not ZONE_LOG_NOISE.search(line):
                                    rows.append(member.split('/')[-1].split('_')[0] + ': ' + line)
                    sections.append(('server_logs_signal', clip(rows, 16)))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        sections.append(('read_error', [str(error)[:300]]))
    result, current = [], {}
    for key, lines in sections:
        if len(json.dumps(dict(current, **{key: lines}))) > limit and current:
            result.append(current)
            current = {}
        while lines and len(json.dumps({key: lines})) > limit:
            lines = lines[1:]
        current[key] = lines
    if current:
        result.append(current)
    return result[:parts]


def stage_timeline(report, limit=24):
    """[stage, start offset s, duration s] from the guest's own UTC stage stamps; bounded."""
    rows, first = [], None
    for item in report.get('stages', []) if isinstance(report.get('stages'), list) else []:
        try:
            started = datetime.datetime.fromisoformat(item['started_utc'])
            finished = (datetime.datetime.fromisoformat(item['finished_utc'])
                        if item.get('finished_utc') else None)
        except (KeyError, TypeError, ValueError):
            continue
        first = started if first is None else first
        rows.append([str(item.get('stage'))[:48], round((started - first).total_seconds(), 1),
                     round((finished - started).total_seconds(), 1) if finished else None])
    return rows[:limit]


def client_folder_cache(text, limit=8):
    """The client's ARMPORT_FOLDER_CACHE_V1 phase lines (scan, hash, piggs), bounded."""
    return [line.split('ARMPORT_FOLDER_CACHE_V1 ', 1)[1][:160] for line in text.splitlines()
            if 'ARMPORT_FOLDER_CACHE_V1 ' in line][:limit]


SOUND_SCRIPT_MARKER = 'ARMPORT_SOUND_SCRIPT_ERRORS_V1'


def client_sound_scripts(text, limit=2):
    """Patch 0124: sound script errors the client logged instead of a modal dialog (bounded)."""
    lines = [line[:160] for line in text.splitlines() if line.startswith(SOUND_SCRIPT_MARKER)]
    return {'reports': len(lines), 'first': lines[:limit], 'modal_dialog_text': 'Sound Script Errors' in text}


LOGOUT_KEY_MARKER = 'ARMPORT_LOGOUT_KEY_V1'


def client_logout_keys(text, limit=2):
    """Patch 0127: keys pressed before the client's own quit request that it no
    longer lets cancel the logout, and the stock cancellations, bounded."""
    lines = text.splitlines()
    kept = [line[:120] for line in lines if line.startswith(LOGOUT_KEY_MARKER)]
    aborted = [line[:40] for line in lines if line.startswith('aborted by key: ')]
    return {'kept': len(kept), 'aborted': len(aborted), 'kept_last': kept[-limit:], 'aborted_last': aborted[-limit:]}


ZONE_LINE = re.compile(r'ArmPort zone: (\d+) (\S+) (.*?) ?tid=\d+$')
ZONE_LOAD_STAGES = ('groups.files.done', 'groups.refs.done', 'map.finish.done', 'collision.done', 'groups.done',
                    'allents.wait.done', 'textures.done', 'ready.sent')
GROUP_LOAD_MARKER = 'ARMPORT_GROUP_LOAD_V1 '


def client_zone_loads(text, limit=3):
    """0.13.80 (client patch 0131): the client's last zone loads, each counted from "map.start".

    `ms`: milliseconds to each boundary of the load; `group_load`: the client's own totals for
    the group files (Thor 0.13.79: 5.5-6.8 s of every load, with nothing recorded inside it);
    `map_files`: the map file's and its layers' load records (stage, file, ms);
    `transfer_ms_before`: a trip's "xfer." boundaries (client patch 0135), each as milliseconds
    before this load's "map.start". Evidence only.
    """
    loads, current, transfer = [], None, {}
    for line in text.splitlines():
        if line.startswith(GROUP_LOAD_MARKER):
            if current is not None:
                current['group_load'] = line[len(GROUP_LOAD_MARKER):][:420]
            continue
        match = ZONE_LINE.match(line)
        if match is None:
            continue
        tick, stage, detail = int(match.group(1)), match.group(2), match.group(3)
        if stage.startswith('xfer.'):
            if stage == 'xfer.wait':
                current, transfer = None, {}        # a trip begins: the last load is over
            if len(transfer) < 8:
                transfer.setdefault(stage[len('xfer.'):][:20], tick)
        elif stage == 'map.start':
            current = {'map': detail.replace('\\', '/').rsplit('/', 1)[-1][:60], 'began': tick, 'ms': {}, 'map_files': []}
            if transfer:
                current['transfer_ms_before'] = {name: (tick - began) & 0xffffffff for name, began in transfer.items()}
                transfer = {}
            loads.append(current)
        elif current is not None:
            elapsed = (tick - current['began']) & 0xffffffff
            if stage in ZONE_LOAD_STAGES:
                current['ms'].setdefault(stage, elapsed)
            elif stage.startswith('library.') and len(current['map_files']) < 12:
                current['map_files'].append([stage[len('library.'):][:20],
                                             detail.replace('\\', '/').rsplit('/', 1)[-1][:40], elapsed])
            if stage == 'ready.sent':
                current = None
    return [{key: value for key, value in load.items() if key != 'began'} for load in loads[-limit:]]


ZONE_CONSOLE = re.compile(r'client-evidence/character-(atlas-console|zoning-[a-z0-9-]{1,60}-console(?:-tail)?)\.txt')


def zone_server_loads(archive, names, limit=8):
    """0.13.81: every zone server console of the session, in a few numbers each.

    The Atlas console had its own summary; the consoles of zones travelled to (and of the
    spare that took a trip) had none in CI. `deferred`: the steps a zone start left until
    after "Server ready" (patches/mapserver-deferred-load). Evidence only.
    """
    rows = []
    for name in sorted(name for name in names if ZONE_CONSOLE.fullmatch(name))[:limit]:
        if archive.getinfo(name).file_size > 16 * 1024 * 1024:
            continue
        phases = mapserver_phases.summary(archive.read(name).decode('utf-8', errors='replace'), top=4)
        profile = phases.get('map_load_profile') or {}
        rows.append({'console': ZONE_CONSOLE.fullmatch(name).group(1)[:48],
                     'stamped_span_seconds': phases.get('stamped_span_seconds'),
                     'slowest': phases.get('slowest_self_timed'),
                     'map_load_ms': profile.get('total_ms'),
                     'deferred': phases.get('deferred_load')})
    return rows


TIMING_FIELDS = ('kind', 'map_id', 'request_to_map_ready_seconds', 'process_spawn_to_map_ready_seconds',
                 'dependency_start_seconds', 'request_to_client_world_ready_seconds')


def trusted_bins_requested():
    """CI A/B switch for the metrics MapServer's opt-in trusted-bin path."""
    value = os.environ.get('COH_TRUSTED_BINS', '')
    require(value in ('', '0', '1'), 'COH_TRUSTED_BINS must be empty, 0 or 1')
    return value == '1'


def client_group_bins_requested():
    """CI A/B input (0.13.81, client patch 0133): the client keeps prepared group files."""
    value = os.environ.get('COH_CLIENT_GROUP_BINS', '')
    require(value in ('', '0', '1'), 'COH_CLIENT_GROUP_BINS must be empty, 0 or 1')
    return value == '1'


def client_library_bounds_requested():
    """CI A/B input (0.13.81, client patch 0132): the client keeps object library bounds."""
    value = os.environ.get('COH_CLIENT_LIBRARY_BOUNDS', '')
    require(value in ('', '0', '1'), 'COH_CLIENT_LIBRARY_BOUNDS must be empty, 0 or 1')
    return value == '1'


def defer_zone_loads_requested():
    """CI A/B input (0.13.81): zone servers read beacons and start PhysX after they are ready."""
    value = os.environ.get('COH_DEFER_ZONE_LOADS', '')
    require(value in ('', '0', '1'), 'COH_DEFER_ZONE_LOADS must be empty, 0 or 1')
    return value == '1'


def server_emulation_requested():
    """CI A/B input (0.13.79): emulator settings for the zone servers, e.g. `tso`, `x87` or `tso,x87`.

    Passed to the guest as COH_SERVER_EMULATION in both sessions; the guest knows the names
    (local_character_server.SERVER_EMULATION_SETTINGS) and records what it set.
    """
    value = os.environ.get('COH_SERVER_EMULATION', '')
    require(re.fullmatch(r'[a-z0-9]{1,12}(,[a-z0-9]{1,12}){0,3}|', value) is not None,
            'COH_SERVER_EMULATION must be empty or up to four comma-separated names')
    return value


def shared_heap_requested():
    """Experiment (app default off): MapServers run without -nosharedmemory."""
    value = os.environ.get('COH_SHARED_HEAP', '')
    require(value in ('', '0', '1'), 'COH_SHARED_HEAP must be empty, 0 or 1')
    return value == '1'


def stock_travel_requested():
    """The game's own zone travel: needs the external-maps DbServer; the reopen runs the zoning flow."""
    value = os.environ.get('COH_STOCK_TRAVEL', '')
    require(value in ('', '0', '1'), 'COH_STOCK_TRAVEL must be empty, 0 or 1')
    return value == '1'


def early_zone_requested():
    """0.13.68: the reopened character's saved zone starts beside the client (needs stock travel)."""
    value = os.environ.get('COH_EARLY_ZONE', '')
    require(value in ('', '0', '1'), 'COH_EARLY_ZONE must be empty, 0 or 1')
    return value == '1'


def require_early_zone_decision(report):
    """With the early_zone input, the reopened session must have decided on an early start.

    0.13.68's chain (run 42955090151) passed with the input on while the guest never reached
    the call: its report held no `early_start` record. Memory is the only refusal a CI runner
    may meet; anything else, or no record, fails the run.
    """
    if not early_zone_requested():
        return
    zoning = report.get('character_zoning')
    early = (zoning.get('initial_zone') or {}).get('early_start') if isinstance(zoning, dict) else None
    require(isinstance(early, dict), 'The early zone start was requested but the guest never decided on it')
    require(early.get('started') is True or early.get('reason') in ('low_memory', 'available_memory_unknown'),
            'The early zone start was requested but not made: ' + str(early.get('reason'))[:120])
    if early.get('started') is True:
        require(early.get('failure') is None, 'The early zone start failed: ' + str(early.get('failure'))[:120])


NETLINK_DESCRIPTOR_FLOOR = 960      # SOCKET_FD_FLOOR in PRoot patch 0007 (socket_fd_filter.h)


def require_proot_ioctl_filter(report):
    """With the proot_ioctl_filter input the guest's own probe must show the filter at work.

    0.13.69: `armport_proot_ioctl` times an ioctl PRoot does not act on and one it does. With
    patch 0004 and PROOT_IOCTL_COMMANDS_ONLY=1 only the second stops in the tracer. A run that
    asked for the filter and shows anything else (no stops: the switch never reached PRoot;
    every ioctl stops: the filter was not installed) fails.
    """
    if not runtime_host.runtime.proot_ioctl_filter_requested():
        return
    probe = report.get('armport_proot_ioctl')
    require(isinstance(probe, dict), 'The ioctl filter was requested but the guest made no ioctl probe')
    require(probe.get('reading') == 'listed_commands_only' and probe.get('requested') is True,
            'The ioctl filter was requested but the probe reads: ' + str(probe.get('reading'))[:60])
    # 0.13.70 (patch 0005): the same launch sets PROOT_GETSOCKOPT_PEERCRED_ONLY=1.
    require(probe.get('getsockopt_stops') is False,
            'The call filter was requested but getsockopt still stops in PRoot')
    # 0.13.73 (patch 0007): the same launch sets PROOT_NETLINK_HIGH_FDS=1. An ordinary send and
    # receive must not stop, and a rtnetlink socket must sit where its calls still do.
    require(probe.get('socket_filter_requested') is True and probe.get('socket_stops') is False,
            'The call filter was requested but socket sends and receives still stop in PRoot')
    descriptor = probe.get('netlink_descriptor')
    require(descriptor is None or (type(descriptor) is int and descriptor >= NETLINK_DESCRIPTOR_FLOOR),
            'The call filter was requested but a rtnetlink socket got descriptor ' + str(descriptor)[:12])


STOP_COUNTS_NAME = 'proot-stop-counts.txt'      # run_isolated_network.STOP_COUNTS_NAME
def launch_receipts_line(report, session):
    """One log line with what each launch receipt decided in this session (0.13.73).

    Thor 0.13.72: the zone graph receipt answered "inputs_changed" on every launch, and
    no log said so. Evidence only; a receipt saves time and never gates.
    """
    steps = {}
    found = report.get('launch_receipts') if isinstance(report, dict) else None
    for step, record in sorted(found.items(), key=lambda item: str(item[0])) if isinstance(found, dict) else ():
        if isinstance(step, str) and isinstance(record, dict):
            steps[step[:48]] = [str(record.get('status'))[:24],
                                None if record.get('reason') is None else str(record.get('reason'))[:80],
                                record.get('elapsed_seconds') if type(record.get('elapsed_seconds')) in (int, float) else None]
        if len(steps) >= 32:
            break
    return 'LAUNCH_RECEIPTS_V1 ' + json.dumps({'format': 1, 'session': session, 'steps': steps}, separators=(',', ':'))


def thread_waits_line(report, session):
    """One log line: the guest's last burst of thread-wait samples in the world (0.13.73).

    The sampler exists for the phone's frame rate (Thor 0.13.72: 22 frames a second with the
    client under one core). CI shows that it runs and what it can read there. Evidence only.
    """
    zoning = report.get('character_zoning') if isinstance(report, dict) else None
    waits = zoning.get('thread_waits') if isinstance(zoning, dict) else None
    value = {'format': 1, 'session': session, 'bursts': None}
    if isinstance(waits, dict) and isinstance(waits.get('bursts'), list):
        bursts = [burst for burst in waits['bursts'] if isinstance(burst, dict)]
        value.update(bursts=len(bursts), skipped_not_in_world=waits.get('skipped_not_in_world'),
                     error=None if waits.get('error') is None else str(waits.get('error'))[:120])
        if bursts:
            last = bursts[-1]
            value['last'] = {key: last.get(key) for key in ('utc', 'rounds', 'seconds', 'call_files', 'wchan_files',
                                                             'unreadable')}
            programs = last.get('programs') if isinstance(last.get('programs'), dict) else {}
            value['last']['programs'] = {
                str(label)[:16]: {'threads': program.get('threads'), 'cpu_percent': program.get('cpu_percent'),
                                  'busiest': [[row.get('name'), row.get('cpu_percent'), row.get('running'),
                                               row.get('stopped_in_proot'), (row.get('waits') or [None])[0]]
                                              for row in (program.get('busiest') or [])[:4] if isinstance(row, dict)]}
                for label, program in sorted(programs.items())[:4] if isinstance(program, dict)}
    return 'THREAD_WAITS_V1 ' + json.dumps(value, separators=(',', ':'))[:6000]


def travel_input_line(observer, session):
    """One log line: the CI trips' travel commands that had to be typed again (0.13.79).

    Spare run 44732475821 lost a typed "/mapmove 1" (the server never logged it), so the host script
    asks again after 300 s and 450 s (character_reopen_host_smoke.STOCK_TRAVEL_RESEND_SECONDS). A
    passing run with a resend says the input was lost, not the trip. Evidence only.
    """
    script = observer.get('interaction_script') if isinstance(observer, dict) else None
    script = script if isinstance(script, dict) else {}
    resends, arrivals = script.get('stock_travel_resends'), script.get('stock_travel_arrivals')
    value = {'format': 1, 'session': session,
             'resends': [{key: item.get(key) for key in ('map_id', 'keys', 'seconds_after_submit')}
                         for item in resends[:4] if isinstance(item, dict)] if isinstance(resends, list) else None,
             'arrival_seconds': [item.get('host_seconds') for item in arrivals[:4] if isinstance(item, dict)]
                                if isinstance(arrivals, list) else None}
    return 'TRAVEL_INPUT_V1 ' + json.dumps(value, separators=(',', ':'))


def start_options_line(report, session):
    """One log line: the two start options of 0.13.74 as the guest recorded them.

    `server_quick_start` (the zone servers' config: animations attached on first use, no
    source-file date checks) and `wineserver_path_cache` (the realpath cache library and its
    own counters). Evidence only; neither gates a session.
    """
    value = {'format': 1, 'session': session, 'server_quick_start': None, 'wineserver_path_cache': None,
             'physx_cache': None, 'server_emulation': None, 'deferred_zone_load': None,
             'client_library_bounds': None, 'client_group_bins': None, 'keep_previous_zone': None,
             'ready_records': None}
    if isinstance(report, dict):
        for section in [report, *report.values()]:
            # 0.13.82: the owner's third zone server, and where the session read "the hero is in the zone".
            zoning = section.get('character_zoning') if isinstance(section, dict) else None
            if isinstance(zoning, dict):
                kept = (zoning.get('stock_travel') or {}).get('keep_previous_zone')
                if isinstance(kept, dict):
                    value['keep_previous_zone'] = {key: kept.get(key) for key in ('requested', 'applied', 'kept')}
                counts = zoning.get('ready_records')
                if isinstance(counts, dict):
                    value['ready_records'] = {key: counts.get(key) for key in ('from_console', 'from_entity_log')}
                break
        for section in [report, *report.values()]:
            bins = section.get('client_group_bins') if isinstance(section, dict) else None
            if isinstance(bins, dict):
                # 0.13.81: the folder the client keeps prepared group files in (patch 0133).
                value['client_group_bins'] = {key: bins.get(key) for key in (
                    'requested', 'applied', 'present_before_launch', 'error')}
                break
        for section in [report, *report.values()]:
            kept = section.get('client_library_bounds') if isinstance(section, dict) else None
            if isinstance(kept, dict):
                # 0.13.81: the file the client keeps object library bounds in (patch 0132).
                value['client_library_bounds'] = {key: kept.get(key) for key in (
                    'requested', 'applied', 'bytes_before_launch', 'error')}
                break
        for section in [report, *report.values()]:
            deferred = section.get('deferred_zone_load') if isinstance(section, dict) else None
            if isinstance(deferred, dict):
                # 0.13.81: whether the zone servers were told to finish their load after "Server ready".
                value['deferred_zone_load'] = {key: deferred.get(key) for key in ('requested', 'applied', 'reason')}
                break
        for section in [report, *report.values()]:
            emulation = section.get('server_emulation') if isinstance(section, dict) else None
            if isinstance(emulation, dict):
                # 0.13.79: the emulator variables the guest set for the zone servers.
                value['server_emulation'] = {key: emulation.get(key) for key in ('requested', 'ignored', 'environment')}
                break
        for section in [report, *report.values()]:
            cooked = section.get('physx_cache') if isinstance(section, dict) else None
            if isinstance(cooked, dict):
                # 0.13.75: the guest's record of the cooked mesh file it named for the zone servers.
                value['physx_cache'] = {key: cooked.get(key) for key in (
                    'requested', 'applied', 'reason', 'bytes_before_start')}
                break
        for section in report.values():
            quick = section.get('server_quick_start') if isinstance(section, dict) else None
            if isinstance(quick, dict):
                value['server_quick_start'] = {'requested': quick.get('requested'),
                                               'commands': [str(item)[:40] for item in (quick.get('commands') or [])[:4]]}
                break
        cache = report.get('wineserver_path_cache')
        if isinstance(cache, dict):
            value['wineserver_path_cache'] = {key: cache.get(key) for key in (
                'requested', 'installed', 'reason', 'error_type', 'servers', 'counters')}
    return 'START_OPTIONS_V1 ' + json.dumps(value, separators=(',', ':'))[:1500]


def start_options_sessions():
    """Which CI sessions run with the two start options of 0.13.74.

    The stock-travel run (the phone's flow: creation, a trip, reopen) uses them in both
    sessions. The other runs keep the creation session as it was, so one run shows the same
    Atlas server start with and without them (its `sequencer_info_done` phase).
    """
    return ('creation', 'reopen') if stock_travel_requested() else ('reopen',)


START_OPTIONS = ('COH_SERVER_QUICK_START=1', 'COH_WINESERVER_PATH_CACHE=1')
# 0.13.75: the cooked mesh file is asked for in both sessions of every run, so that the reopen
# session's Atlas start reads what the creation session's cooked. Only a server built with
# patches/mapserver-physx-cache uses it (the trusted run's); elsewhere the guest records why not.
BOTH_SESSION_OPTIONS = ('COH_PHYSX_CACHE=1',)


STOP_COUNTS_MARK = 'PROOT_STOP_COUNTS_V1 '


def proot_stop_counts(work, top=48):
    """PRoot's own count of the stops it served per call number (patch 0005), or None.

    CI's trap sampler counts time spent stopped; this is the number of stops. PRoot rewrites
    the file about every ten seconds and at exit, so it is complete once the guest has ended.
    """
    try:
        lines = (Path(work) / STOP_COUNTS_NAME).read_text(errors='replace')[:262144].splitlines()
    except OSError:
        return None
    head = lines[0].split() if lines else []
    if not head or head[0] != STOP_COUNTS_MARK.strip():
        return {'format': 1, 'valid': False}
    fields = dict(part.split('=', 1) for part in head[1:] if '=' in part)
    rows = [[int(part) for part in line.split()] for line in lines[1:]
            if len(line.split()) == 3 and all(part.isdigit() for part in line.split())]
    rows.sort(key=lambda row: (-(row[1] + row[2]), row[0]))
    number = lambda key: int(fields[key]) if fields.get(key, '').isdigit() else None
    # 0.13.71 (patch 0006): "P <thread name> <call number> <stops>" rows say whose stops they are.
    programs = [[parts[1][:16], int(parts[2]), int(parts[3])] for parts in (line.split() for line in lines[1:])
                if len(parts) == 4 and parts[0] == 'P' and parts[2].isdigit() and parts[3].isdigit()]
    programs.sort(key=lambda row: (-row[2], row[0], row[1]))
    # 0.13.73 (patch 0007): stat calls on a descriptor (no path to translate), and rtnetlink
    # sockets moved to a high descriptor number or refused one. None from an older PRoot.
    extra = {key: number(key) for key in ('fd_stats', 'moved_netlink_fds', 'failed_netlink_moves')}
    # 0.13.75 (patch 0008): missing path components of Wine's programs replaced by the entry in
    # another letter case, those with no such entry, and directories read for it.
    extra.update({key: number(key) for key in ('casefold_replaced', 'casefold_absent', 'casefold_listed')})
    return {'format': 1, 'valid': True, 'seconds': number('seconds'), 'stops': number('stops'), **extra,
            'columns': ['call_number', 'enter_stops', 'exit_stops'], 'calls': rows[:top],
            'other_stops': sum(row[1] + row[2] for row in rows[top:]),
            'program_columns': ['thread_name', 'call_number', 'stops'], 'programs': programs[:top]}


def require_proot_stop_counts(counts):
    """With the call filter the patched PRoot must also have written its stop counts."""
    if not runtime_host.runtime.proot_ioctl_filter_requested():
        return
    require(isinstance(counts, dict) and counts.get('valid') is True and (counts.get('stops') or 0) > 0
            and counts.get('calls'), 'The call filter was requested but PRoot wrote no stop counts')


def spare_zone_requested():
    """0.13.69: one pre-loaded zone server beside the current zone (needs stock travel and trusted bins' server)."""
    value = os.environ.get('COH_SPARE_ZONE', '')
    require(value in ('', '0', '1'), 'COH_SPARE_ZONE must be empty, 0 or 1')
    return value == '1'


def keep_previous_zone_requested():
    """0.13.82, owner's option: the zone the hero just left stays loaded (needs the spare zone server)."""
    value = os.environ.get('COH_KEEP_PREVIOUS_ZONE', '')
    require(value in ('', '0', '1'), 'COH_KEEP_PREVIOUS_ZONE must be empty, 0 or 1')
    return value == '1'


def mission_probe_requested():
    """0.13.84: CI's two trips are a mission, with the guest's mission maps on (Atlas tree: no zone pack in CI)."""
    value = os.environ.get('COH_MISSION_PROBE', '')
    require(value in ('', '0', '1'), 'COH_MISSION_PROBE must be empty, 0 or 1')
    return value == '1'


def single_player_probe_requested():
    """0.13.85: both CI sessions run with the Primalist archetype and "Unlock all content" on."""
    value = os.environ.get('COH_SINGLE_PLAYER_PROBE', '')
    require(value in ('', '0', '1'), 'COH_SINGLE_PLAYER_PROBE must be empty, 0 or 1')
    return value == '1'


def single_player_probe_options():
    """The guest switches of the probe; COH_SINGLE_PLAYER_PROBE_PART narrows it to one of the two."""
    part = os.environ.get('COH_SINGLE_PLAYER_PROBE_PART', '') or 'both'
    require(part in ('both', 'unlock', 'primalist'), 'COH_SINGLE_PLAYER_PROBE_PART must be both, unlock or primalist')
    return [name for name, wanted in (('COH_PRIMALIST=1', part != 'unlock'), ('COH_UNLOCK_ALL=1', part != 'primalist'))
            if wanted]


def single_player_summary(report):
    """Bounded view of the Primalist content and the account unlock in a session report."""
    result = {key: report.get(key) for key in ('primalist', 'unlock_all', 'client_account_unlock',
                                                'single_player_database')
              if isinstance(report.get(key), dict)}
    if 'single_player_database' in result:
        # Bounded again: this summary is one notice (4 KiB); the report keeps the longer text.
        result['single_player_database'] = {key: (value[:500] if isinstance(value, str) else value)
                                            for key, value in result['single_player_database'].items()}
    content = report.get('single_player_content')
    if isinstance(content, dict):
        result['content'] = {key: content.get(key) for key in ('identity', 'files', 'replaced', 'added')}
    for key in ('character_creation', 'character_reopen'):
        section = report.get(key)
        if not isinstance(section, dict):
            continue
        for name in ('single_player_stale_bins', 'account_unlock'):
            if isinstance(section.get(name), dict):
                result[name] = section[name]
        observation = section.get('map_startup_observation') or report.get('map_startup_observation')
        if isinstance(observation, dict):
            compiled = {str(map_id): row.get('single_player_class_compiled') for map_id, row in observation.items()
                        if isinstance(row, dict) and 'single_player_class_compiled' in row}
            if compiled:
                result['class_compiled'] = compiled
        # Was the kept zone data taken again (and its compiled files with it), or prepared anew?
        trees = {}
        for label, holder in (('atlas', section.get('private_map_data')),
                              ('zones', (report.get('zone_tree_preparation') or section.get('zone_tree_preparation')))):
            cache = holder.get('server_data_cache') if isinstance(holder, dict) else None
            if isinstance(cache, dict):
                trees[label] = {'reused': cache.get('reused'),
                                'reuse_refused': str(cache.get('reuse_refused'))[:120] if cache.get('reuse_refused') else None}
            stale = holder.get('single_player_stale_bins') if isinstance(holder, dict) else None
            if isinstance(stale, dict) and 'single_player_stale_bins' not in result:
                result['single_player_stale_bins'] = stale
        if trees:
            result['kept_data_trees'] = trees
        changes = section.get('unlock_all_changes')
        if changes is not None:
            result['unlock_all_changes'] = changes if not isinstance(changes, (list, dict)) else (
                list(changes)[:24] if isinstance(changes, list) else {str(k): v for k, v in list(changes.items())[:24]})
    return result or None


def serverdata_probe_requested():
    """CI-only probe level: 1 serves scripts.loc, 2 every folder no guest proof reads,
    through a linked shared read-only runtime/serverdata tree. 0 is off."""
    value = os.environ.get('COH_SERVERDATA_PROBE', '')
    require(value in ('', '0', '1', '2'), 'COH_SERVERDATA_PROBE must be empty, 0, 1 or 2')
    return int(value or 0)


def client_audio_requested():
    """Game audio (app default on): the guest plays through the plugin to a protocol sink.

    CI has no audio device; audio_receiver models the Android bridge with a
    real-time playback head. It is not evidence of audible Thor playback.
    """
    value = os.environ.get('COH_CLIENT_AUDIO', '')
    require(value in ('', '0', '1'), 'COH_CLIENT_AUDIO must be empty, 0 or 1')
    return value == '1'


# The guest's cleanup kills the client mid-stream (wineserver -k, then signals),
# so the sink's reply can meet a closed peer. That is teardown, not a protocol fault.
AUDIO_TEARDOWN = re.compile(r'\[Errno (32|104)\]')


def audio_summary(snapshot):
    streams = snapshot['streams']
    teardown = [error for error in snapshot['errors'] if AUDIO_TEARDOWN.match(error)]
    return {'format': 1, 'scope': 'ci_protocol_sink_not_audible_playback', 'streams': len(streams),
            'frames': sum(s['frames'] for s in streams),
            'nonzero_samples': sum(s['nonzero_samples'] for s in streams),
            'stereo_streams': sum(1 for s in streams if s['left_nonzero'] and s['right_nonzero']),
            'starts': sum(s['starts'] for s in streams), 'teardown_disconnects': len(teardown),
            'errors': [error for error in snapshot['errors'] if not AUDIO_TEARDOWN.match(error)]}


def shared_server_requested():
    """App default (on): both zone servers read the shared folders through runtime/serverdata."""
    value = os.environ.get('COH_SHARED_SERVER_DATA', '')
    require(value in ('', '0', '1'), 'COH_SHARED_SERVER_DATA must be empty, 0 or 1')
    return value == '1'


STORY_ARC_COUNTS = re.compile(r'(?m)^(\d+) arcs, (\d+) contacts, (\d+) tasks\b')


def story_arc_counts(text, limit=4):
    """MapServer story arc totals, e.g. Thor 0.13.x Atlas: 470 arcs, 957 contacts, 3528 tasks."""
    return [[int(value) for value in match.groups()] for match in STORY_ARC_COUNTS.finditer(text)][:limit]


EXTERNAL_MAPS_WORKFLOW = stage_app_assets.EXTERNAL_MAPS_WORKFLOW


def external_maps_build_run(run_json, directory):
    """The package comes from one successful run of its own workflow at its own commit."""
    return stage_app_assets.external_maps_build_run(run_json, directory)


def stock_travel_summary(report):
    """Bounded view of the game's own zone travel in the zoning report."""
    zoning = report.get('character_zoning')
    stock = zoning.get('stock_travel') if isinstance(zoning, dict) else None
    if not isinstance(stock, dict):
        return None
    keep = ('map_id', 'tree', 'port', 'evicted', 'ready', 'ready_seconds', 'failure', 'failed_seconds')
    return {'requested': stock.get('requested'), 'enabled': stock.get('enabled'),
            'arrivals': stock.get('arrivals'), 'transfer_wait_observed': stock.get('transfer_wait_observed'),
            'starts': [{key: row.get(key) for key in keep if key in row}
                       for row in stock.get('starts', [])[:6] if isinstance(row, dict)],
            'evictions': [row for row in stock.get('evictions', [])[:4] if isinstance(row, dict)],
            'decisions': [row for row in stock.get('decisions', [])[:6] if isinstance(row, dict)],
            'zone_tree_seconds': (report.get('zone_tree_preparation') or {}).get('elapsed_seconds'),
            # 0.13.84: mission maps (requested, started, refused, ended; in and out).
            'mission_maps': ({key: (value[:4] if isinstance(value, list) else value)
                              for key, value in stock['mission_maps'].items()}
                             if isinstance(stock.get('mission_maps'), dict) else None),
            # Which log route proved readiness, and where the DbServer last placed the hero.
            'ready_route': ((report.get('character_reopen') or {}).get('client_ready_evidence') or {}).get('log_route'),
            'last_samples': [{key: sample.get(key) for key in ('map_id', 'static_map_id', 'connected', 'loaded',
                                                                'in_map_transfer') if key in sample}
                             for sample in ((report.get('character_reopen') or {}).get('character_samples') or [])[-3:]
                             if isinstance(sample, dict)]}


def external_maps_summary(section):
    """Bounded view of the supervisor report and the installed DbServer layer."""
    record = section.get('external_maps')
    if not isinstance(record, dict):
        return None
    summary = {key: record.get(key) for key in ('requested', 'enabled', 'reason', 'dbserver_layer', 'weekly_tf_config')}
    supervisor = record.get('supervisor')
    if isinstance(supervisor, dict):
        summary.update({key: supervisor.get(key) for key in ('acknowledgement_observed', 'stopped', 'counts',
                                                             'session_maps', 'map_starts_executed')})
        requests = supervisor.get('requests') if isinstance(supervisor.get('requests'), list) else []
        summary['requests'] = [{key: item.get(key) for key in ('map_id', 'is_static', 'decision', 'reason',
                                                               'refused_option')}
                               | {'delink_passed': (item.get('delink') or {}).get('passed')}
                               for item in requests[:6] if isinstance(item, dict)]
        anomalies = supervisor.get('anomalies') if isinstance(supervisor.get('anomalies'), list) else []
        summary['anomalies'] = [str(item)[:160] for item in anomalies[:4]]
    manual = section.get('manual_atlas_startup')
    if isinstance(manual, dict):
        summary['manual_atlas_ack'] = manual.get('native_ack_observed')
    return summary


def guest_timing_summary(evidence):
    """Bounded A/B diagnostic (PRoot mode, map startup, preparation phases); never gates."""
    result = {}
    try:
        path = evidence / 'latest-report.json'
        if path.is_file() and path.stat().st_size <= 16 * 1024 * 1024:
            report = json.loads(path.read_text())
            result['proot_mode'] = report.get('proot_mode')
            probe = report.get('armport_proot_ioctl')
            if isinstance(probe, dict):
                result['proot_ioctl'] = {key: probe.get(key) for key in (
                    'reading', 'requested', 'microseconds_per_call', 'getsockopt_stops', 'error_type',
                    'socket_filter_requested', 'socket_stops', 'netlink_descriptor', 'netlink_error_type')
                    if probe.get(key) is not None}
            result['shared_server_data'] = next((section.get('shared_server_data') for section in
                (report.get('character_creation'), report.get('character_reopen'))
                if isinstance(section, dict) and section.get('shared_server_data') is not None),
                report.get('shared_server_data'))
            result['stage_timeline'] = stage_timeline(report)
            result['trusted_bins'] = next((section.get('trusted_bins') for section in
                (report.get('character_creation'), report.get('character_reopen'))
                if isinstance(section, dict) and section.get('trusted_bins') is not None), None)
            zoning = report.get('character_zoning')
            early = ((zoning.get('initial_zone') or {}).get('early_start') if isinstance(zoning, dict) else None)
            if isinstance(early, dict):
                result['early_zone'] = {key: early.get(key) for key in (
                    'requested', 'started', 'reason', 'failure', 'preparation_seconds', 'ready', 'ready_seconds',
                    'ready_before_the_game_asked', 'requested_after_seconds', 'available_memory_mib',
                    'available_memory_mib_at_ready') if early.get(key) is not None}
            spare = zoning.get('spare_zone') if isinstance(zoning, dict) else None
            if isinstance(spare, dict) and spare.get('requested') is True:
                result['spare_zone'] = {'layer_available': spare.get('layer_available'),
                    'waiting_reason': spare.get('waiting_reason'),
                    'starts': [{key: row.get(key) for key in ('ordinal', 'tree', 'warm', 'warm_seconds', 'outcome',
                                'reason', 'map_id', 'loaded_seconds_before_request', 'refused_request',
                                'available_memory_mib', 'available_memory_mib_when_warm') if row.get(key) is not None}
                               for row in (spare.get('starts') or [])[:4]]}
                ahead = spare.get('graphs_checked_ahead')
                if isinstance(ahead, list) and ahead:
                    # 0.13.79, 0.13.80: navigation graphs made ready while the warm spare waited.
                    result['spare_zone']['graphs_checked_ahead'] = [
                        {key: row.get(key) for key in ('map_id', 'status', 'seconds', 'error')
                         if row.get(key) is not None} for row in ahead[:8] if isinstance(row, dict)]
                    result['spare_zone']['graphs_ahead'] = {key: spare.get(key) for key in
                                                            ('graphs_ahead_done', 'graphs_ahead_stopped')}
            result['shared_heap'] = next((section.get('shared_heap') for section in
                (report.get('character_creation'), report.get('character_reopen'))
                if isinstance(section, dict) and section.get('shared_heap') is not None), None)
            result['external_maps'] = next((external_maps_summary(section) for section in
                (report.get('character_creation'), report.get('character_reopen'))
                if isinstance(section, dict) and section.get('external_maps') is not None), None)
            result['stock_travel'] = stock_travel_summary(report)
            result['single_player'] = single_player_summary(report)
            for key in ('character_creation', 'character_reopen'):
                section = report.get(key)
                if not isinstance(section, dict):
                    continue
                rows = [row for row in section.get('map_startup_timing', []) if isinstance(row, dict)][:4]
                observed = section.get('map_startup_observation')
                caches = section.get('prepared_server_caches')
                result[key] = {'map_startup': [{name: row.get(name) for name in TIMING_FIELDS} for row in rows],
                               'preparation_phase_seconds': section.get('server_preparation_phase_seconds'),
                               'prepared_server_caches': {name: (str(caches.get(name))[:200] if name == 'reason'
                                   else caches.get(name)) for name in ('status', 'reason', 'installed_files',
                                   'preserved_existing_files')} if isinstance(caches, dict) else None,
                               'native_bin_writes': {map_id: (value or {}).get('native_bin_writes')
                                   for map_id, value in list(observed.items())[:4]}
                                   if isinstance(observed, dict) else None}
        path = evidence / 'report.zip'
        if path.is_file():
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                # The ARM64 client writes its phase lines to armport_stdio.txt.
                for client in ('client-evidence/armport_stdio.txt', 'client-evidence/client-console.log'):
                    if client in names and archive.getinfo(client).file_size <= 16 * 1024 * 1024:
                        lines = client_folder_cache(archive.read(client).decode('utf-8', errors='replace'))
                        if lines:
                            result['client_folder_cache'] = lines
                            break
                member = 'client-evidence/armport_stdio.txt'
                if member in names and archive.getinfo(member).file_size <= 16 * 1024 * 1024:
                    stdio = archive.read(member).decode('utf-8', errors='replace')
                    result['client_sound_scripts'] = client_sound_scripts(stdio)
                    result['client_logout_keys'] = client_logout_keys(stdio)
                    result['client_zone_loads'] = client_zone_loads(stdio)
                member = 'client-evidence/character-atlas-console.txt'
                if member in names and archive.getinfo(member).file_size <= 16 * 1024 * 1024:
                    console = archive.read(member).decode('utf-8', errors='replace')
                    result['atlas_mapserver_phases'] = mapserver_phases.summary(console, top=6)
                    result['story_arc_counts'] = story_arc_counts(console)
                result['zone_server_loads'] = zone_server_loads(archive, names)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        result['evidence_read_error'] = str(error)[:300]
    return result


def timing_notices(timings, proot_seccomp, trusted_bins):
    """Per session: a timings notice, then detail notices (stage timeline and client
    folder-cache phases; rewritten bins; zone servers: shared heap decision and
    on-demand map requests). Each stays under the 4 KiB annotation limit."""
    lines = []
    for name, original in timings.items():
        summary, writes = {}, {}
        detail = {key: original[key] for key in ('stage_timeline', 'client_folder_cache', 'client_sound_scripts',
                                                 'client_logout_keys') if original.get(key)}
        servers = {key: original[key] for key in ('shared_heap', 'external_maps', 'stock_travel')
                   if original.get(key)}
        single_player = original.get('single_player')
        loads = original.get('client_zone_loads')
        zone_loads = original.get('zone_server_loads')
        for key, value in original.items():
            if key in detail or key in servers or key in ('client_zone_loads', 'zone_server_loads', 'single_player'):
                continue
            if key in ('character_creation', 'character_reopen') and isinstance(value, dict):
                value = dict(value)
                writes[key] = value.pop('native_bin_writes', None)
            summary[key] = value
        lines.append(ci_notice(dict(summary, session=name, proot_seccomp=proot_seccomp, trusted_bins_requested=trusted_bins))
                     .replace('interactive result', 'guest timings ' + name, 1))
        if any(value for value in writes.values()):
            lines.append(ci_notice({'session': name, 'native_bin_writes': writes})
                         .replace('interactive result', 'bin writes ' + name, 1))
        if detail:
            lines.append(ci_notice(dict(detail, session=name))
                         .replace('interactive result', 'startup detail ' + name, 1))
        if servers:
            lines.append(ci_notice(dict(servers, session=name))
                         .replace('interactive result', 'zone servers ' + name, 1))
        if single_player:
            # Its own notice: beside the zone server fields it was cut off at the 4 KiB limit.
            lines.append(ci_notice({'session': name, 'single_player': single_player})
                         .replace('interactive result', 'single player ' + name, 1))
        if loads:
            lines.append(ci_notice({'session': name, 'client_zone_loads': loads})
                         .replace('interactive result', 'client zone loads ' + name, 1))
        if zone_loads:
            lines.append(ci_notice({'session': name, 'zone_server_loads': zone_loads})
                         .replace('interactive result', 'zone server loads ' + name, 1))
    return lines


def ci_notice(result):
    text = json.dumps(result, separators=(',', ':'))
    text = text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    return '::notice title=ArmPort M4 interactive result::' + text


def run_session(command, work, evidence, proot, session, runtime_manifest, client_manifest,
                deadline, reopening=False, second_hero=False, heroes=1):
    evidence.mkdir(parents=True)
    isolated, environment, expected_network = runtime_host.runtime.isolate_command(
        command, evidence=evidence, proot=proot, work=work)
    process = observer = failure = report = sampler = None
    (work / STOP_COUNTS_NAME).unlink(missing_ok=True)
    with (evidence / 'host-client.log').open('w') as log:
        try:
            process = subprocess.Popen(isolated, env=environment, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            if trap_sampler.requested():
                # 0.13.69, CI only: which guest tasks wait on PRoot and at which system call.
                # Read as root where CI allows it: Wine's own processes are not below this one.
                sampler = trap_sampler.start(process.pid, 'reopen' if reopening else 'creation',
                                             work / 'trap-sampler.stop')
            endpoint = work / 'socket/view.sock'
            while not endpoint.exists():
                require(process.poll() is None and time.monotonic() < deadline,
                        'ARM64 guest exited or timed out before its private display')
                time.sleep(.1)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(90)
                connection.connect(str(endpoint))
                travel = reopening and stock_travel_requested()
                observer = character.observe_rfb(connection, session, process, deadline, evidence,
                    evidence / 'host-client.log', work / 'state/interaction-finish.json',
                    SecondHeroInteraction if second_hero else
                    (reopen.StockTravelReopenInteraction if travel else reopen.ReopenInteraction)
                    if reopening else ArmPortCharacterInteraction,
                    None if second_hero else
                    (reopen.StockTravelReopenEvents if travel else reopen.ReopenEvents) if reopening else None)
            require(observer.get('failure') is None, observer.get('failure') or 'ARM64 RFB observer failed')
            require(process.wait(timeout=max(1, deadline - time.monotonic())) == 0,
                    'ARM64 interactive guest exited unsuccessfully')
            report = json.loads((work / 'state/latest-report.json').read_text())
            if isinstance(report.get('python_call_profile'), dict):
                print('PYTHON_CALL_PROFILE_V1 ' + json.dumps(dict(report['python_call_profile'],
                      session='reopen' if reopening else 'creation'), separators=(',', ':')), flush=True)
            print('ARMPORT_GRAPHICS_PROFILE_V1 ' + json.dumps(dict(
                report.get('armport_graphics_profile') if isinstance(report.get('armport_graphics_profile'), dict)
                else {'requested': None}, session='reopen' if reopening else 'creation'), separators=(',', ':'))[:400],
                flush=True)
            print(launch_receipts_line(report, 'reopen' if reopening else 'creation'), flush=True)
            print(thread_waits_line(report, 'reopen' if reopening else 'creation'), flush=True)
            print(start_options_line(report, 'reopen' if reopening else 'creation'), flush=True)
            projected = legacy_report(report, runtime_manifest, client_manifest)
            checked_manifest = validation_manifest(report, runtime_manifest)
            require(time.monotonic() <= deadline, 'ARM64 interactive host deadline exceeded')
            if second_hero:
                # The script is a creation's inside a reopen session: neither session's fixed
                # report shape applies; heroes_probe_validate reads the guest's own proof.
                require(not endpoint.exists(), 'Private display survived guest cleanup')
                return report
            if reopening:
                finish_request = observer.get('interaction_script', {}).get('finish_request')
                require(finish_request is not None, 'Missing host explicit-finish request')
                reopen.validate_report(projected, session, checked_manifest, finish_request=finish_request,
                                       heroes=heroes)
            else:
                character.validate_report(projected, session, checked_manifest)
            if not reopening:
                reopen.validate_world_supplement(projected, checked_manifest)
            if reopening:
                reopen.validate_observer(observer, report, reopen.StockTravelReopenInteraction
                                         if stock_travel_requested() else reopen.ReopenInteraction)
                if stock_travel_requested():
                    print(travel_input_line(observer, 'reopen'), flush=True)
                require_early_zone_decision(report)
            else:
                armport_validate_observer(observer, report)
            require_proot_ioctl_filter(report)
            require_proot_stop_counts(proot_stop_counts(work))
            require(not endpoint.exists(), 'Private display survived guest cleanup')
            runtime_host.runtime.validate_network_receipt(
                json.loads((evidence / 'network-isolation.json').read_text()), expected_network)
        except Exception as error:
            failure = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            sampled = sampler.finish() if sampler is not None else None
            cleanup = character.stop_guest(process, work / 'state')
            counts = proot_stop_counts(work)
            if counts is not None:
                print(STOP_COUNTS_MARK + json.dumps(dict(counts, session='reopen' if reopening else 'creation'),
                                                    separators=(',', ':')), flush=True)
            exported = character.export_guest_evidence(work / 'state', evidence, session)
            (evidence / 'host-session-report.json').write_text(json.dumps({
                'scope': 'arm64_app_guest_reopen' if reopening else 'arm64_app_guest_creation',
                'session_id': session, 'passed': failure is None, 'failure': failure,
                'external_observer': observer, 'host_cleanup': cleanup, 'trap_sampler': sampled,
                'proot_stop_counts': counts,
                'guest_evidence_export': exported, 'guest_failure': guest_failure_summary(evidence)}, indent=2) + '\n')
            costume = creator_costume_line(observer)
            if costume:
                print(costume, flush=True)
            if failure is not None:
                detail = failure_detail(evidence, work, observer)
                (evidence / 'failure-detail.json').write_text(json.dumps(detail, indent=2) + '\n')
                # Wide fields first, as plain lines: a notice is cut at 4096 characters.
                wide = {key: detail.pop(key) for key in ('dbserver_first_sql_error', 'creator_screen_words')
                        if key in detail}
                if wide:
                    print('ARMPORT_FAILURE_WIDE_V1 ' + json.dumps(wide, separators=(',', ':')), flush=True)
                for line in failure_frame_lines(evidence):
                    print(line, flush=True)
                print(ci_notice(dict(detail, session='reopen' if reopening else 'creation'))
                      .replace('interactive result', 'failure detail', 1), flush=True)
                if stock_travel_requested():
                    for index, part in enumerate(zone_diagnostics(evidence), 1):
                        print(ci_notice(part).replace('interactive result', 'zone diagnostics %d' % index, 1),
                              flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('apk', 'build-report', 'armport', 'archive', 'proot', 'work', 'evidence'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--server-archive', type=Path)
    parser.add_argument('--server-run-id', type=int)
    parser.add_argument('--baseline-root', type=Path)
    parser.add_argument('--external-maps-dbserver', type=Path,
                        help='armport-external-maps-dbserver package: added to the CI donor and enabled')
    parser.add_argument('--external-maps-run-json', type=Path,
                        help='GitHub API record of the run that built --external-maps-dbserver')
    args = parser.parse_args()
    require((args.server_archive is None) == (args.server_run_id is None) == (args.baseline_root is None),
            'Server archive, exact build run and pinned baseline must be provided together')
    require((args.external_maps_dbserver is None) == (args.external_maps_run_json is None),
            'External map DbServer package and its build run must be provided together')
    if args.external_maps_dbserver is not None:
        external_maps_build_run(args.external_maps_run_json, args.external_maps_dbserver)
    for name, value in vars(args).items():
        if isinstance(value, Path): setattr(args, name, value.resolve())
    baseline = server_pipeline.native.baseline_root(args.baseline_root) if args.server_archive else ROOT
    require(platform.machine().lower() in ('aarch64', 'arm64'), 'Native ARM64 runner required')
    require(shutil.which('tesseract') is not None, 'Existing RFB driver requires tesseract')
    require(not args.work.exists() and not args.evidence.exists(), 'Fresh private work/evidence required')
    args.work.mkdir(mode=0o700)
    args.evidence.mkdir(parents=True)
    result = {'scope': 'arm64_app_guest_creation_and_reopen', 'passed': False,
              'm4_complete': False, 'apk_built': False, 'android_surface_validated': False,
              'repository_commit': args.repository_commit}
    started = time.monotonic()
    receiver = None
    try:
        donor = args.work / 'donor-assets'
        result['donor'] = retained_assets.extract(args.apk, args.build_report, donor)
        assets = args.work / 'armport-assets'
        result['armport_client'] = stage_app_assets.stage(donor / 'runtime', args.armport,
            assets, args.repository_commit, server_archive=args.server_archive,
            server_variant='retained_progress' if args.server_archive else None,
            server_run_id=args.server_run_id, upstream_root=baseline,
            dbserver=args.external_maps_dbserver, dbserver_ci_runtime=args.external_maps_dbserver is not None,
            zoning=stock_travel_requested())
        runtime_manifest = json.loads((assets / 'runtime-manifest.json').read_text())
        if args.external_maps_dbserver is not None:
            result['external_maps_dbserver'] = runtime_manifest[stage_app_assets.EXTERNAL_MAPS_KEY]
        client_manifest = json.loads((assets / 'client-manifest.json').read_text())
        if args.server_archive:
            binding = json.loads((assets / 'armport-server-metrics-binding.json').read_text())
            runtime_manifest['armport_server_metrics_build'] = json.loads(binding['build_manifest_utf8'])
            result['armport_server_metrics'] = runtime_manifest['armport_server_metrics']
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
        if client_audio_requested():
            # The guest's /presentation-socket is work/socket (0700, created above).
            receiver = audio_receiver.Receiver(args.work / 'socket/audio.sock')
            command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_AUDIO=1')
            command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_AUDIO_SOCKET=/presentation-socket/audio.sock')
        command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_ARCH=arm64')
        command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_GRAPHICS_PROFILE=standard')
        if runtime_host.runtime.proot_seccomp_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_PROOT_FAST_MODE=1')
        if runtime_host.runtime.proot_ioctl_filter_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_PROOT_IOCTL_FILTER=1')
            command.insert(command.index('/usr/bin/python3'), 'COH_PROOT_SOCKET_FILTER=1')
        if trap_sampler.requested():        # the same CI input also counts the supervisor's own calls
            command.insert(command.index('/usr/bin/python3'), 'COH_CALL_PROFILE=1')
        if trusted_bins_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_TRUSTED_BINS=1')
        if shared_heap_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_SHARED_HEAP=1')
        if server_emulation_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_SERVER_EMULATION=' + server_emulation_requested())
        if defer_zone_loads_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_DEFER_ZONE_LOADS=1')
        if client_library_bounds_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_LIBRARY_BOUNDS=1')
        if client_group_bins_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_GROUP_BINS=1')
        if args.external_maps_dbserver is not None:
            # The supervisor observes the DbServer's map requests and delinks
            # the ones this flow does not start itself (milestone 1).
            command.insert(command.index('/usr/bin/python3'), 'COH_EXTERNAL_MAPS=1')
        if stock_travel_requested():
            require(args.external_maps_dbserver is not None, 'Stock travel needs the external-maps DbServer')
            command.insert(command.index('/usr/bin/python3'), 'COH_STOCK_TRAVEL=1')
        if early_zone_requested():
            require(stock_travel_requested(), "The early zone start needs the game's own zone travel")
            command.insert(command.index('/usr/bin/python3'), 'COH_EARLY_ZONE=1')
        if spare_zone_requested():
            require(stock_travel_requested(), "The spare zone server needs the game's own zone travel")
            command.insert(command.index('/usr/bin/python3'), 'COH_SPARE_ZONE=1')
        if keep_previous_zone_requested():
            require(spare_zone_requested(), 'Keeping the previous zone needs the spare zone server')
            command.insert(command.index('/usr/bin/python3'), 'COH_KEEP_PREVIOUS_ZONE=1')
        if mission_probe_requested():
            require(stock_travel_requested(), "The mission probe needs the game's own zone travel")
            command.insert(command.index('/usr/bin/python3'), 'COH_MISSION_MAPS=1')
            command.insert(command.index('/usr/bin/python3'), 'COH_MISSION_MAPS_TREE=atlas')
        if single_player_probe_requested():
            for option in single_player_probe_options():
                command.insert(command.index('/usr/bin/python3'), option)
        if shared_server_requested():
            command.insert(command.index('/usr/bin/python3'), 'COH_SHARED_SERVER_DATA=1')
        if serverdata_probe_requested():
            command.insert(command.index('/usr/bin/python3'),
                           'COH_SERVERDATA_PROBE=' + str(serverdata_probe_requested()))
        for option in BOTH_SESSION_OPTIONS:
            command.insert(command.index('/usr/bin/python3'), option)
        deadline = time.monotonic() + character.OVERALL_SECONDS
        first_command = list(command)
        if 'creation' in start_options_sessions():
            for option in START_OPTIONS:
                first_command.insert(first_command.index('/usr/bin/python3'), option)
        created = run_session(first_command, args.work, args.evidence / 'creation', args.proot,
                              first, runtime_manifest, client_manifest, deadline)
        before = reopen.persistent_profile_identity(args.work)
        reopen.archive_completed_reports(args.work / 'state', first)
        reopen.reset_session_requests(args.work / 'state')
        next_command = reopen.reopen_command(command, first, second)
        # 0.13.73 (ArmPort patch 0129): the reopen session, the one the phone plays, runs with the
        # app's default graphics profile for the ARM64 client; creation keeps `standard`.
        next_command.insert(next_command.index('/usr/bin/python3'), 'COH_ARMPORT_GRAPHICS_PROFILE=effects_off')
        if 'reopen' in start_options_sessions():
            for option in START_OPTIONS:
                next_command.insert(next_command.index('/usr/bin/python3'), option)
        if stock_travel_requested():
            # The device's reopen: the zoning flow with the supervisor's start policy.
            next_command.insert(next_command.index('/opt/coh/character_reopen_diagnostic.py') + 1, '--zoning')
        reopened = run_session(next_command, args.work, args.evidence / 'reopen', args.proot,
                               second, runtime_manifest, client_manifest, deadline, reopening=True)
        after = reopen.persistent_profile_identity(args.work)
        reopen.validate_continuity(created, reopened, before, after)
        if heroes_probe_requested():
            require(stock_travel_requested(), "The heroes probe needs the game's own zone travel")
            first_hero = character.CHARACTER
            previous, summary = second, {}
            # Two more sessions: their own bound (the job's timeout covers all four).
            deadline = time.monotonic() + HEROES_PROBE_SECONDS
            for label, made in (('second-hero', True), ('first-hero', False)):
                session = secrets.token_hex(16)
                reopen.archive_completed_reports(args.work / 'state', previous)
                reopen.reset_session_requests(args.work / 'state')
                probe_command = reopen.reopen_command(command, first, session)
                probe_command.insert(probe_command.index('/usr/bin/python3'), 'COH_ARMPORT_GRAPHICS_PROFILE=effects_off')
                probe_command.insert(probe_command.index('/opt/coh/character_reopen_diagnostic.py') + 1, '--zoning')
                # The driver's checks follow one name: the new hero's while it is made.
                character.CHARACTER = SECOND_HERO if made else first_hero
                SecondHeroInteraction.FIRST_HERO = first_hero
                try:
                    probe_report = run_session(probe_command, args.work, args.evidence / label, args.proot,
                                               session, runtime_manifest, client_manifest, deadline,
                                               reopening=True, second_hero=made, heroes=1 if made else 2)
                finally:
                    character.CHARACTER = first_hero
                summary[label] = heroes_probe_validate(probe_report, created=made)
                previous = session
            result['heroes_probe'] = summary
            print('::notice title=ArmPort heroes probe::' + json.dumps(summary, separators=(',', ':'))[:3800],
                  flush=True)
        if receiver is not None:
            audio = audio_summary(receiver.snapshot())
            (args.evidence / 'audio-report.json').write_text(json.dumps(audio, indent=2) + '\n')
            # A connected stream without protocol faults proves Wine, ALSA and the plugin;
            # non-zero samples (reported) depend on what the scripted screens play.
            require(not audio['errors'] and audio['streams'] >= 1,
                    'Game audio reached no protocol sink: ' + json.dumps(audio))
        if args.server_archive:
            result['server_metrics_native_execution'] = {
                'creation': server_pipeline.guest_admission(created, runtime_manifest),
                'reopen': server_pipeline.guest_admission(reopened, runtime_manifest)}
        result.update(passed=True, same_persistent_profile=True, same_character_id=True,
                      creation_session_id=first, reopen_session_id=second)
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        if receiver is not None:
            if not (args.evidence / 'audio-report.json').exists():
                (args.evidence / 'audio-report.json').write_text(
                    json.dumps(audio_summary(receiver.snapshot()), indent=2) + '\n')
            receiver.close()
            print('::notice title=ArmPort game audio (CI protocol sink)::'
                  + (args.evidence / 'audio-report.json').read_text().replace('\n', ' '), flush=True)
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        result['guest_failures'] = {name: guest_failure_summary(args.evidence / name)
                                    for name in ('creation', 'reopen', 'second-hero', 'first-hero')
                                    if (args.evidence / name).exists()}
        (args.evidence / 'host-report.json').write_text(json.dumps(result, indent=2) + '\n')
        print(ci_notice({key: result.get(key) for key in
            ('passed', 'm4_complete', 'elapsed_seconds', 'error', 'guest_failures')}), flush=True)
        # Separate notice; host-report.json keeps its qualified schema.
        timings = {name: guest_timing_summary(args.evidence / name) for name in ('creation', 'reopen')
                   if (args.evidence / name).exists()}
        for line in timing_notices(timings, runtime_host.runtime.proot_seccomp_requested(),
                                   trusted_bins_requested()):
            print(line, flush=True)
        print(json.dumps(result), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
