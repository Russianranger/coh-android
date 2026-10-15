#!/usr/bin/env python3
"""Restore two original donor receipt byte orders without changing native inputs.

The public .28 game archive recursively sorted embedded historical JSON receipts.
The unchanged guest correctly checks the original receipt bytes.  This packaging
repair restores authenticated original key orders; it changes no receipt values,
native members, runtime validators, or public external asset volumes.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'android/guest')]
import game_diagnostic as game
import local_character_server as server
from local_login_server import extract_regular
from package_monorail_native import write_game_archive

EVIDENCE = 'docs/android-evidence/'
DONOR_GAME_FIXTURE = EVIDENCE+'client-receipt-repair-0.13.29-donor-game-package.json'
CANDIDATE_FIXTURE = EVIDENCE+'client-receipt-repair-0.13.29-native-responsiveness.json'
EVENTS_FIXTURE = EVIDENCE+'client-receipt-repair-0.13.29-mapserver-progress-original.json'
LISTENER_FIXTURE = EVIDENCE+'game-listeners-package-36510836956.json'
SOURCE_FILES = ('tools/android/interactive/repair_game_receipt_order.py',
    'tools/android/interactive/test_game_receipt_order.py', DONOR_GAME_FIXTURE,
    CANDIDATE_FIXTURE, EVENTS_FIXTURE, LISTENER_FIXTURE)
DONOR_ARCHIVE = {'bytes': 10942769,
    'sha256': 'b6023faf7fad044e8bff05776bd5596354bb9877bda21de60f83f66384918262'}
DONOR_MANIFEST = {'bytes': 162281,
    'sha256': 'ae18958a1f66228bd3ff6593480449eda568b15e8c801be5a6bc634ab4a32e25'}
CANDIDATE_RECEIPT = {'bytes': 40754,
    'sha256': 'e3005754339365b88a41af12dadc2afd540033ba9ee927a18f9e353387e41fc3'}
RECEIPTS = {
    'loopback_game': 'd10e61be69555da91cea1f5b4a0f9852f0c564f9a768a91896b485f0774c0791',
    'mapserver_progress': 'e6234deaa55931551efca0e9450cfaea93f2462b194a2ebfa9a638d097c63c94',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def original_receipts():
    listener = json.loads((ROOT/LISTENER_FIXTURE).read_bytes())['inputs']['loopback_game']['manifest']
    listener_raw = (json.dumps(listener, indent=2)+'\n').replace('\n', '\r\n').encode()
    require(pin(listener_raw)['sha256'] == RECEIPTS['loopback_game'],
            'Original supporting listener receipt bytes differ')
    events_raw = (ROOT/EVENTS_FIXTURE).read_bytes()
    require(pin(events_raw)['sha256'] == RECEIPTS['mapserver_progress'],
            'Original character-events receipt bytes differ')
    events = json.loads(events_raw)
    require((json.dumps(events, indent=2)+'\n').encode() == events_raw,
            'Original character-events receipt serialization differs')
    return {'loopback_game': listener, 'mapserver_progress': events}


def repair_manifest(raw):
    """Accept only the published .28 manifest, preserving every semantic value."""
    require(pin(raw) == DONOR_MANIFEST, 'Exact public .28 game manifest required')
    package = json.loads(raw)
    before = copy.deepcopy(package)
    for name, original in original_receipts().items():
        donor = package['inputs'][name]
        require(donor['manifest_sha256'] == RECEIPTS[name] and donor['manifest'] == original,
                'Historical donor receipt content differs: '+name)
        donor['manifest'] = original
    # Do not recursively sort: the nested dictionaries represent original bytes.
    encoded = json.dumps(package, separators=(',', ':')).encode()
    serialized = json.loads(encoded)
    require(serialized == before, 'Receipt repair changed game package values')
    game.game_loopback_contract(serialized)
    game.game_listener_contract(serialized)
    game.mapserver_progress_contract(serialized)
    return encoded


def archive_members(path):
    with tarfile.open(path, 'r:gz') as archive:
        rows = archive.getmembers()
        require(all(row.isfile() and '/' not in row.name and '\\' not in row.name
                    and row.name not in ('.', '..') for row in rows)
                and len({row.name.casefold() for row in rows}) == len(rows),
                'Unexpected game archive inventory')
        return {row.name: archive.extractfile(row).read() for row in rows}


def validate_archive(game_archive_path, candidate_receipt_path):
    """Run both actual guest startup gates on independently extracted final bytes."""
    game_archive_path, candidate_receipt_path = Path(game_archive_path), Path(candidate_receipt_path)
    candidate_raw = candidate_receipt_path.read_bytes()
    require(pin(candidate_raw) == CANDIDATE_RECEIPT, 'Exact retained native receipt required')
    candidate = json.loads(candidate_raw)
    expected_manifest = repair_manifest((ROOT/DONOR_GAME_FIXTURE).read_bytes())
    expected = json.loads(expected_manifest)
    members = archive_members(game_archive_path)
    require(members.get('game-package.json') == expected_manifest,
            'Repaired game manifest bytes differ')
    require(set(members) == set(expected['files']) | {'game-package.json'},
            'Repaired game archive closure differs')
    native_members = {name: pin(raw) for name, raw in sorted(members.items()) if name != 'game-package.json'}
    for name, record in expected['files'].items():
        require(native_members[name] == {'bytes': record.get('bytes', record.get('size')),
                                        'sha256': record['sha256']},
                'Repair changed native member: '+name)
    with tempfile.TemporaryDirectory(prefix='coh-receipt-guest-preflight-') as temporary:
        for name, owner in (('fresh-create', server.LocalCharacterServer),
                            ('saved-reopen', server.LocalCharacterReopenServer)):
            destination = Path(temporary)/name
            extract_regular(game_archive_path, destination)
            require(owner.verify_map_payload(destination, candidate) == expected,
                    'Actual guest payload validation differs: '+name)
    return {'format': 1, 'status': 'passed', 'repaired_archive': pin(game_archive_path.read_bytes()),
        'repaired_manifest': pin(expected_manifest), 'repaired_receipts': dict(RECEIPTS),
        'native_members': native_members, 'fresh_create_payload_verified': True,
        'saved_reopen_payload_verified': True}


def repair_archive(game_archive_path, candidate_receipt_path):
    """Replace the archive in place only after complete unchanged guest validation."""
    game_archive_path = Path(game_archive_path)
    require(pin(game_archive_path.read_bytes()) == DONOR_ARCHIVE, 'Exact public .28 game archive required')
    members = archive_members(game_archive_path)
    original_members = dict(members)
    members['game-package.json'] = repair_manifest(members['game-package.json'])
    require(all(members[name] == raw for name, raw in original_members.items()
                if name != 'game-package.json'), 'Repair changed native bytes')
    with tempfile.TemporaryDirectory(prefix='coh-receipt-order-', dir=game_archive_path.parent) as temporary:
        output = Path(temporary)/game_archive_path.name
        write_game_archive(output, members)
        proof = validate_archive(output, candidate_receipt_path)
        require(archive_members(output) == members, 'Repair serialization changed archive members')
        output.replace(game_archive_path)
    return dict(proof, original_archive=dict(DONOR_ARCHIVE), original_manifest=dict(DONOR_MANIFEST),
                semantic_manifest_unchanged=True)
