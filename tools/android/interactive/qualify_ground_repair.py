#!/usr/bin/env python3
"""Focused observer regression/replay receipt; never claims physical gameplay."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
# The guest launches Wine/Python with TZ=UTC. Reproduce that clock basis for
# archived logger timestamps even if the qualification host uses another zone.
os.environ['TZ'] = 'UTC'
time.tzset()
import build_apk as package
import test_character_reopen_guest as existing
import test_ground_repair as ground

SOURCES = (
    'android/guest/local_character_server.py',
    'tools/android/interactive/test_character_reopen_guest.py',
    'tools/android/interactive/test_ground_repair.py',
    'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.log',
    'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json',
    'tools/android/interactive/qualify_ground_repair.py',
    'tools/android/interactive/build_ground_repair_apk.py',
    'tools/android/interactive/test_ground_repair_package.py',
    'tools/android/interactive/build_apk.py',
    '.github/workflows/android-ground-repair.yml',
)
DONOR_SHA256 = 'f4e30c728046771cb91beece46fb54663b0fcd57a28b8e055f6fc8918dd3c899'


def require(value, message):
    if not value:
        raise ValueError(message)


def qualify(commit):
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module)
                               for module in (existing, ground))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    require(result.wasSuccessful() and result.testsRun == 22,
                    'Focused observer regressions did not all pass')
    metadata = json.loads(ground.METADATA.read_text())
    require(metadata['fixture']['sha256'] == package.file_pin(ground.FIXTURE)['sha256']
                    and metadata['replay']['receipt_is_synthetic_for_parser_exercise_only'] is True
                    and metadata['replay']['synthetic_sent_utc_ms'] == ground.REPLAY_SENT_MS
                    and metadata['replay']['synthetic_now_utc_ms'] == ground.REPLAY_NOW_MS,
                    'Exact Thor replay bytes or labeled synthetic receipt differ')
    recovered = ground.replay()
    require(recovered is not None and recovered['position'] == ground.THOR_POSITION
                    and recovered['elapsed_ms'] == 30000
                    and recovered['full_collision_geometry_verified'] is False,
                    'Actual Thor samples did not pass the corrected observer')
    translations = metadata['map_source']['translation_chain']
    map_path = ROOT / metadata['map_source']['path']
    require(package.file_pin(map_path)['sha256'] == metadata['map_source']['sha256'],
                    'Authored Atlas spawn map source pin differs')
    composed = [sum(step['translation'][axis] for step in translations) for axis in range(3)]
    require(all(abs(a-b) < 0.00001 for a,b in zip(composed, ground.THOR_POSITION)),
                    'Authored City Hall spawn does not match the native recovered position')
    sources = {name: package.file_pin(ROOT/name) for name in SOURCES}
    return {
        'format': 1, 'status': 'passed', 'scope': 'thor_native_ground_observer_replay',
        'repository_commit': commit, 'donor_apk_sha256': DONOR_SHA256,
        'tests_run': result.testsRun,
        'source_files': sources,
        'helper_sha256': sources['android/guest/local_character_server.py']['sha256'],
        'qualifier_sha256': sources['tools/android/interactive/qualify_ground_repair.py']['sha256'],
        'checks': {
            'observer_regression_tests_passed': True,
            'thor_fixture_replay_passed': True,
            'entity_log_fallback_refused': True,
            'identity_freshness_stability_guards_preserved': True,
        },
        'replay': {'position': recovered['position'], 'accepted_as_native_log': True,
                   'synthetic_delivery': True, 'elapsed_ms': recovered['elapsed_ms'],
                   'fixture': metadata['fixture'], 'original_upload': metadata['original_upload'],
                   'authored_map_source': {'path': metadata['map_source']['path'],
                                          **package.file_pin(map_path)}},
        'physical_gameplay_validated': False,
        'limitations': 'Parser and save-observer regressions using actual archived native records '
                      'and a labeled synthetic receipt. No new native runtime session; physical '
                      'movement, collision, normal save and saved-position reopening remain pending.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository-commit')
    args = parser.parse_args()
    commit = package.source_commit(args.repository_commit)
    receipt = qualify(commit)
    require(not args.output.exists() and not args.output.is_symlink(),
                    'Fresh observer qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Focused observer replay qualified:', receipt['tests_run'], 'tests; physical gameplay pending')


if __name__ == '__main__':
    main()
