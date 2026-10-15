#!/usr/bin/env python3
"""Stage only the native station clock for the bounded .32 Kings lifecycle.

The historical monorail source and receipt remain unchanged. This derivative
changes one pinned timeout literal; all identity, reply and stock-door checks
remain the exact retained source bytes.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import prepare_monorail_source as monorail
from prepare_resume_client_source import canonical_hash
from prepare_runtime import require, sha256

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'MapServer/src/svr/wine_monorail.c'
HEADER = 'MapServer/src/svr/wine_monorail.h'
RECEIPT = 'map-startup-monorail-budget.json'
BASE_SOURCE_SHA256 = '002957b67a841cb650c67412b7fcd3a159e02000a358c29c591d8049f23acf56'
BASE_CONTRACT_SHA256 = '28759432841c4c5571da75a067c56d7844ea0646a152f1093f3dcaa4a07d7733'
PATCHED_SOURCE_SHA256 = '3bd765cddc3975d2ca9c4f69f36b6cdd21ae0454068c33bd437a1fb3e21c57ad'
HEADER_SHA256 = 'e4fef174151cf1595275039e5155213ce3d2f1673b377a0cd606d31b35f6fba9'
OLD = b'(DWORD)(GetTickCount() - request_started) > 600000UL'
NEW = b'(DWORD)(GetTickCount() - request_started) > 720000UL'
CONTRACT = dict(monorail.CONTRACT, station_preparation_timeout_seconds=720)


def patch_source(original):
    require(isinstance(original, bytes) and hashlib.sha256(original).hexdigest() == BASE_SOURCE_SHA256
            and original.count(OLD) == 1 and NEW not in original,
            'Map startup native station budget source differs')
    result = original.replace(OLD, NEW, 1)
    require(hashlib.sha256(result).hexdigest() == PATCHED_SOURCE_SHA256,
            'Map startup native station budget patch differs')
    return result


def expected_receipt(root=ROOT):
    root = Path(root)
    original = monorail.overlay_bytes(root)
    require(hashlib.sha256(original[HEADER]).hexdigest() == HEADER_SHA256,
            'Map startup native station header differs')
    patched = patch_source(original[SOURCE])
    require(monorail.CONTRACT['station_preparation_timeout_seconds'] == 600
            and canonical_hash(monorail.CONTRACT) == BASE_CONTRACT_SHA256,
            'Historical native station contract differs')
    return {'schema_version': 1, 'build_role': 'map_startup_monorail_budget',
        'source_sha256': {SOURCE: hashlib.sha256(original[SOURCE]).hexdigest()},
        'patched_sha256': {SOURCE: hashlib.sha256(patched).hexdigest()},
        'retained_sources_sha256': {HEADER: HEADER_SHA256},
        'base_monorail_contract': json.loads(json.dumps(monorail.CONTRACT)),
        'base_monorail_contract_canonical_sha256': canonical_hash(monorail.CONTRACT),
        'contract': json.loads(json.dumps(CONTRACT)), 'build_targets': ['MapServer'],
        'patch_scope': 'one_exact_native_station_pending_timeout_literal_only',
        'elapsed_clock': 'DWORD_GetTickCount_unsigned_difference_from_native_request',
        'guest_absolute_cap_basis': 'validated_native_request_utc_ms_plus_720000',
        'expiry_comparison': 'strictly_greater_than_720000_milliseconds',
        'preserved': ['disabled_by_default', 'session_token_validation', 'main_thread_identity',
            'character_account_identity', 'station_map_pair', 'monotonic_request_sequence',
            '250ms_reply_poll_bound', 'exact_reply_bytes_pid_request_target_session',
            'reparse_and_directory_refusal', 'reply_length_limit', 'cancel_and_retry',
            'stock_door_validation_repeated_after_readiness'],
        'native_fixture_required': True, 'runtime_validation': 'unverified',
        'physical_startup_timing_validated': False}


def apply_budget_overlay(source, root=ROOT):
    source, root = Path(source).resolve(), Path(root).resolve()
    require(source != root and root / 'upstream' not in (source, *source.parents),
            'Immutable native station budget staging refused')
    target, receipt = source / SOURCE, source / RECEIPT
    require(not receipt.exists() and not receipt.is_symlink(), 'Native station budget already staged')
    previous = source / monorail.RECEIPT
    require(previous.is_file() and not previous.is_symlink()
            and json.loads(previous.read_text()) == monorail.expected_receipt(root),
            'Native station budget requires its exact historical monorail prerequisite')
    expected = expected_receipt(root)
    for name, digest in {**expected['source_sha256'], **expected['retained_sources_sha256']}.items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
                and sha256(path) == digest, 'Native station budget staged input differs: ' + name)
    target.write_bytes(patch_source(target.read_bytes()))
    require(sha256(target) == expected['patched_sha256'][SOURCE], 'Native station budget staged output differs')
    receipt.write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected
