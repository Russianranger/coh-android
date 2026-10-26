"""Exact, opt-in original-data exception approved in PR #6 comment 6387467359.

This never handles Wine, integrity, exit, cursor, ACK or state failures. The
caller must complete those checks first. A changed or absent occurrence fails.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from itemize_dispatch_errors import itemize

ROOT = Path(__file__).resolve().parents[2]
POLICY = Path(__file__).with_name('fixtures') / 'original-data-errors.json'
ALLOWED_NAMES = frozenset(('face_skin_head_09', 'hips_miniskirt_1', 'hips_skin_tights',
                          'x_enforcer_glove_01_mask', 'x_gear_pads', 'x_imperialdefense_belt_01'))
PROOF_FILES = frozenset(('assets/catalog.json', 'assets/zones-audio-metadata.json',
    'armport/evidence/m3-audio-file-tables.json', 'armport/evidence/m3-approved-range-assets.json',
    'armport/evidence/m3-six-run-texture-exception-40203125375.json'))


def load_policy(path=POLICY, root=ROOT):
    document = json.loads(path.read_text())
    if (document.get('format') != 1 or document.get('approval_comment') != 6387467359
            or set(document.get('proof_sha256', {})) != PROOF_FILES):
        raise ValueError('Original-data exception policy identity differs')
    for name, expected in document['proof_sha256'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Original-data exception proof changed: ' + name)
    rows = document.get('occurrences')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Original-data exception list is empty')
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or
                set(row) != {'text', 'dispatch_index', 'after_dispatch_index', 'count'} or
                not isinstance(row['text'], str)):
            raise ValueError('Original-data exception row shape differs')
        match = re.fullmatch(r'CUSTOM TEXTURE ERROR: \w+ wants nonexistent texture (\w+) as texture [12] on bone \w+\.', row['text'])
        if (not match or match[1].casefold() not in ALLOWED_NAMES
                or type(row['count']) is not int or row['count'] < 1
                or type(row['dispatch_index']) is not int or not 0 <= row['dispatch_index'] < 117
                or row['after_dispatch_index'] is not None):
            raise ValueError('Original-data exception exceeds approved texture scope')
        key = (row['text'], row['dispatch_index'], row['after_dispatch_index'])
        if key in seen:
            raise ValueError('Duplicate original-data exception')
        seen.add(key)
    return document


def check(trace, error_count, *, policy=None):
    policy = load_policy() if policy is None else policy
    observed = itemize(trace)
    actual = Counter((r['text'], r['dispatch_index'], r['after_dispatch_index'])
                     for r in observed['occurrences'])
    expected = Counter({(r['text'], r['dispatch_index'], r['after_dispatch_index']): r['count']
                        for r in policy['occurrences']})
    if observed['count'] != error_count or actual != expected:
        raise ValueError('Original-data texture errors differ from committed literal texts/counts/indices')
    return [dict(row) for row in policy['occurrences']]
