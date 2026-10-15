#!/usr/bin/env python3
"""Avoid rebuilding unchanged native producers; every uncertain scope runs them.

This only selects the historical native workflow. It grants no native consumer,
cache, runtime or publication authority and does not relabel inherited proofs.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

BASELINE = 'bc74b08e75d5da7187f99658d2c04dd509a325fb'
WORKFLOW = '.github/workflows/android-map-startup-native.yml'
HELPER = 'tools/android/interactive/classify_map_startup_native_change.py'
TEST = 'tools/android/interactive/test_map_startup_native_change.py'
CONTROL = frozenset({WORKFLOW, HELPER, TEST})
LEGACY_WORKFLOW_SHA256 = '8839a1ead01f21f08c5ed6f57c75a317d0da11033acf75d539ef9df727385f64'
GUARDED_WORKFLOW_SHA256 = 'ca8c768949d3d2617043e842ea1ce250573daaf7059ce3ed577fe34cac20d6c7'
PRE_RECOVERY_WORKFLOW_SHA256 = '2e40ecf1854dbd67bfe16b30f53d45f3427a4d3c45cd75a31dcf976b2926e63f'
NATIVE_BODY_SHA256 = '7465a7d83385c0e74535b68ce4aa47574bf3338697d3eabb416c946d6a3e0d6b'
# Frozen after the separate dormant-source import; only this exact predecessor
# may hand over the cancellation policy without re-running unchanged compilers.
RECOVERY_SOURCE_COMMIT = '8016b39ec213df6aee5c3032554abc7e21878cbd'
RECOVERY_SOURCE_BASE = '65c4d83a533400118932685b170c640a77bc9435'
RECOVERY_PREDECESSOR_PINS = {
    HELPER: '5fdf2ce86e02be4de29a8bb10b78ad1d391934d6002de1c3663022c19ce4ed30',
    TEST: '6616276258f6a1152071f09814075531322f3fa034cf52858a3414739ad12908',
}
RECOVERY_REVIEW_WORKFLOW = '.github/workflows/android-startup-recovery-review.yml'
RECOVERY_REVIEW_WORKFLOW_SHA256 = '9e57cd3eff1dab2a1c9c595fcd5afaec45c51b43d2f101ecf052b97729f9ea0f'
# One reviewed policy handover from the exact already introduced guard. It
# changes only host evidence routing; later helper/test edits still run native.
POLICY_CORRECTION_PARENT = 'f6aabde3a3438f58128359fa3f019664ae391b45'
POLICY_PREDECESSOR_PINS = {
    HELPER: '2e42ec6c9c4f7b1d4ad6c509ca3e65defcb011986635bda631338cd9f7e18e7d',
    TEST: '6fecf1686ec8e2b297c83cab32ae2cf3c297754d01f1a2038142fabed4e36066',
}
# A second independently reviewed handover admits only the two fixture source
# paths and the exact credential-scoped host qualification workflow update.
FIXTURE_POLICY_PARENT = '1d0f2373aa657f8ec3e8c3e5dcd4043643520cde'
FIXTURE_POLICY_PREDECESSOR_PINS = {
    HELPER: '141d41f1f208ebe832749b27d6dc826e4f96b4dde22c4853291206d497dc5dc9',
    TEST: 'f322813ffc0024f835c393a7ebd5682505318bef6d1d8229bca338816785c19b',
}
FIXTURE_WORKFLOW = '.github/workflows/android-client-zone-startup.yml'
FIXTURE_WORKFLOW_PREDECESSOR_SHA256 = '5d15be8c27418e90a2d97270b30d54fbbb4ce2ab9172dfed42e2d82cceef04c0'
FIXTURE_WORKFLOW_SHA256 = 'd6e068d84603dfcd8c7d552ddc21e4cfc168daba09f8fab4f1edadb42299e07f'
HOST_ONLY = frozenset({
    FIXTURE_WORKFLOW,
    RECOVERY_REVIEW_WORKFLOW,
    'android/guest/atlas_beacon_package.py',
    'android/guest/character_zoning.py',
    'android/guest/client_gpu_profile.py',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/game_device_diagnostic.py',
    'android/guest/game_diagnostic.py',
    'android/guest/local_character_server.py',
    'android/guest/native_map_startup_contract.py',
    'android/guest/native_startup_metadata_contract.py',
    'android/guest/server_animation_package.py',
    'android/guest/server_cache_package.py',
    'android/guest/server_fx_catalog.py',
    'android/guest/texture_header_index.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'docs/COH-Atlas-Gameplay-0.13.37-testing.txt',
    'docs/COH-CLIENT-STARTUP-PRIORITY-0.13.37.md',
    'docs/COH-STARTUP-0.13.37-PACKAGING-PLAN.md',
    'docs/COH-STARTUP-LATENCY-0.13.37.md',
    'docs/HANDOFF.md',
    'docs/android-evidence/client-startup-priority-investigation-0.13.37.json',
    'docs/android-evidence/client-zone-startup-0.13.37-host-tests.json',
    'docs/android-evidence/client-zone-startup-0.13.37-publication.json',
    'docs/android-evidence/coh-physical-startup-0.13.36-analysis.json',
    'docs/android-evidence/manual-report-cleanup-0.13.37-qualification.json',
    'docs/android-evidence/native-cache-normalizer-0.13.37-review.json',
    'docs/android-evidence/native-client-folder-sort-0.13.37-qualification.json',
    'docs/android-evidence/native-client-material-reader-0.13.37-review.json',
    'docs/android-evidence/native-client-metadata-adapter-0.13.37-review.json',
    'docs/android-evidence/native-client-metadata-census-0.13.37-prototype.json',
    'docs/android-evidence/native-map-cache-subset-0.13.37-research.json',
    'docs/android-evidence/native-map-metadata-adapter-0.13.37-host-tests.json',
    'docs/android-evidence/native-map-metadata-adapter-0.13.37-review.json',
    'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json',
    'docs/android-evidence/native-map-world-bounds-failure-0.13.37.json',
    'docs/android-evidence/native-map-world-buffering-failure-0.13.37.json',
    'docs/android-evidence/native-map-world-console-failure-0.13.37.json',
    'docs/android-evidence/native-metadata-adapter-0.13.37-root-integration.json',
    'docs/android-evidence/native-metadata-adapter-0.13.37-source-checkpoint.json',
    'docs/android-evidence/native-startup-metadata-0.13.37-dormant-review.json',
    'docs/android-evidence/native-startup-material-facts-0.13.37.json',
    'docs/android-evidence/original-cache-components-0.13.37-recovery.json',
    'tools/android/atlasgame/test_device_cleanup_lineage.py',
    'tools/android/interactive/build_client_zone_startup_apk.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_zone_startup_change.py',
    'tools/android/interactive/derive_native_metadata_cache_proof.py',
    'tools/android/interactive/fixtures/thor-manual-report-0.13.36-20261013.json',
    'tools/android/interactive/native_startup_component_migration.py',
    'tools/android/interactive/native_startup_metadata_admission.py',
    'tools/android/interactive/qualify_client_zone_startup.py',
    'tools/android/interactive/release-client-zone-startup-0.13.37.json',
    'tools/android/interactive/test_client_zone_startup_package.py',
    'tools/android/interactive/test_derive_native_metadata_cache_proof.py',
    'tools/android/interactive/test_manual_report_acceptance.py',
    'tools/android/interactive/test_native_metadata_map_activation.py',
    'tools/android/interactive/test_native_metadata_runtime_activation.py',
    'tools/android/interactive/test_native_startup_component_migration.py',
    'tools/android/interactive/test_native_startup_metadata_admission.py',
    'tools/android/interactive/test_native_startup_metadata_contract.py',
    'tools/android/interactive/prepare_native_metadata_qualification_fixtures.py',
    'tools/android/interactive/test_native_metadata_qualification_fixtures.py',
})


def git(repo, *arguments):
    return subprocess.check_output(['git', '-C', str(repo), *arguments], stderr=subprocess.DEVNULL)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def oid(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{40}', value) and value != '0'*40


def paths(repo, before, head):
    raw = git(repo, 'diff', '--no-renames', '--name-only', '-z', before, head)
    values = raw.rstrip(b'\0').split(b'\0') if raw else []
    return [value.decode('utf-8', errors='strict') for value in values]


def regular_blob(repo, commit, path):
    row = git(repo, 'ls-tree', commit, '--', path).decode('ascii').strip()
    prefix, found = row.split('\t')
    mode, kind, object_id = prefix.split()
    if mode != '100644' or kind != 'blob' or found != path or not oid(object_id):
        raise ValueError('Exact regular tracked source required: '+path)
    return git(repo, 'show', commit+':'+path)


def native_body(raw):
    text = raw.decode('utf-8', errors='strict')
    if text.count('  native:\n') != 1:
        raise ValueError('Unknown native workflow structure')
    body = text.split('  native:\n', 1)[1]
    wrapper = "    needs: change-scope\n    if: ${{ always() && (needs.change-scope.result != 'success' || needs.change-scope.outputs.native_required != 'false') }}\n"
    if body.startswith(wrapper):
        body = body[len(wrapper):]
    return body.encode('utf-8')


def frozen_recovery_scope(repo, head, names):
    """Inherited dormant files are exact bytes, never a future path allowance."""
    git(repo, 'merge-base', '--is-ancestor', RECOVERY_SOURCE_COMMIT, head)
    imported = set(paths(repo, RECOVERY_SOURCE_BASE, RECOVERY_SOURCE_COMMIT))
    if not names <= imported:
        raise ValueError('Cumulative unknown paths are outside the frozen recovery import')
    for path in names:
        if not path.startswith(('research/', 'database/client-live-directory/',
            'tools/native_live_directory/', 'docs/')):
            raise ValueError('Frozen recovery import includes a Map producer or active source')
        original = git(repo, 'ls-tree', RECOVERY_SOURCE_COMMIT, '--', path).decode('ascii').strip()
        current = git(repo, 'ls-tree', head, '--', path).decode('ascii').strip()
        prefix, found = original.split('\t')
        mode, kind, object_id = prefix.split()
        if (mode not in {'100644', '100755'} or kind != 'blob' or found != path
            or not oid(object_id) or current != original):
            raise ValueError('Frozen dormant recovery source was changed, aliased or removed')
    return sorted(names)


def classify(repo, event, before, head):
    result = {'format': 1, 'native_required': True,
        'qualification_scope': 'workflow_routing_only_not_native_qualification',
        'baseline_commit': BASELINE, 'event': event, 'before': before, 'head': head,
        'native_producer_relabelled': False, 'native_steps_or_SDK_flags_changed': False,
        'inherited_native_execution_claimed_fresh': False}
    try:
        if event != 'push' or not oid(before) or not oid(head):
            raise ValueError('Manual dispatch or unknown event/history requires native gate')
        actual = git(repo, 'rev-parse', 'HEAD').decode('ascii').strip()
        parents = git(repo, 'rev-parse', head+'^@').decode('ascii').strip().splitlines()
        if actual != head or parents != [before] or before == head:
            raise ValueError('Only an exact single direct-parent push may skip unchanged native code')
        git(repo, 'merge-base', '--is-ancestor', BASELINE, head)
        changed = paths(repo, before, head)
        cumulative = paths(repo, BASELINE, head)
        if not changed or not cumulative:
            raise ValueError('Empty or unavailable change scope requires native gate')
        result.update(changed_paths=changed, cumulative_paths=cumulative)
        if any(path not in HOST_ONLY | CONTROL for path in changed):
            raise ValueError('Unknown or native producer/build/fixture change requires native gate')
        inherited = set(cumulative) - (HOST_ONLY | CONTROL)
        if inherited:
            result['frozen_dormant_recovery_paths'] = frozen_recovery_scope(repo, head, inherited)
            result['frozen_dormant_recovery_commit'] = RECOVERY_SOURCE_COMMIT
        old = regular_blob(repo, before, WORKFLOW)
        current = regular_blob(repo, head, WORKFLOW)
        if sha(native_body(old)) != NATIVE_BODY_SHA256 or sha(native_body(current)) != NATIVE_BODY_SHA256:
            raise ValueError('Native/FX job body or compiler flags changed')
        if sha(old) not in {LEGACY_WORKFLOW_SHA256, PRE_RECOVERY_WORKFLOW_SHA256, GUARDED_WORKFLOW_SHA256} or sha(current) != GUARDED_WORKFLOW_SHA256:
            raise ValueError('Unknown workflow wrappers, checkout, policy or compiler scope')
        if RECOVERY_REVIEW_WORKFLOW in changed+cumulative:
            if sha(regular_blob(repo, head, RECOVERY_REVIEW_WORKFLOW)) != RECOVERY_REVIEW_WORKFLOW_SHA256:
                raise ValueError('Source-review CI differs from its exact read-only recipe')
        if FIXTURE_WORKFLOW in changed+cumulative:
            previous_fixture = sha(regular_blob(repo, before, FIXTURE_WORKFLOW))
            current_fixture = sha(regular_blob(repo, head, FIXTURE_WORKFLOW))
            if previous_fixture not in {FIXTURE_WORKFLOW_PREDECESSOR_SHA256, FIXTURE_WORKFLOW_SHA256} or current_fixture != FIXTURE_WORKFLOW_SHA256:
                raise ValueError('Host fixture workflow differs from its exact credential-scoped recipe')
        controls = set(changed) & CONTROL
        policy_correction = False
        fixture_policy_correction = False
        recovery_policy_correction = False
        if controls:
            if controls == CONTROL and before == RECOVERY_SOURCE_COMMIT and sha(old) == PRE_RECOVERY_WORKFLOW_SHA256:
                for path, expected in RECOVERY_PREDECESSOR_PINS.items():
                    if sha(regular_blob(repo, before, path)) != expected:
                        raise ValueError('Exact recovery predecessor helper/test bytes differ')
                    regular_blob(repo, head, path)
                recovery_policy_correction = True
            elif controls == {HELPER, TEST} and before == POLICY_CORRECTION_PARENT and sha(old) == GUARDED_WORKFLOW_SHA256:
                for path, expected in POLICY_PREDECESSOR_PINS.items():
                    if sha(regular_blob(repo, before, path)) != expected:
                        raise ValueError('Reviewed policy predecessor helper/test bytes differ')
                    regular_blob(repo, head, path)
                policy_correction = True
            elif controls == {HELPER, TEST} and before == FIXTURE_POLICY_PARENT and sha(old) == GUARDED_WORKFLOW_SHA256:
                for path, expected in FIXTURE_POLICY_PREDECESSOR_PINS.items():
                    if sha(regular_blob(repo, before, path)) != expected:
                        raise ValueError('Reviewed fixture policy predecessor helper/test bytes differ')
                    regular_blob(repo, head, path)
                fixture_policy_correction = True
            else:
                if controls != CONTROL or sha(old) != LEGACY_WORKFLOW_SHA256:
                    raise ValueError('Only the reviewed first introduction or exact one-time policy handover may skip')
                for path in (HELPER, TEST):
                    if git(repo, 'ls-tree', before, '--', path):
                        raise ValueError('Changed routing helper/test requires native gate')
                    regular_blob(repo, head, path)
        for path in set(changed+cumulative)-{WORKFLOW}-inherited:
            regular_blob(repo, head, path)
        result.update(native_required=False, reason='Complete known host-only scope; exact native and FX steps retained',
            retained_native_body_sha256=NATIVE_BODY_SHA256,
            workflow_sha256=sha(current), control_introduction=bool(controls) and not (policy_correction or fixture_policy_correction or recovery_policy_correction),
            cancellation_policy_recovery=recovery_policy_correction,
            source_only_scope_policy_correction=policy_correction,
            original_fixture_scope_policy_correction=fixture_policy_correction)
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError) as exc:
        result['reason'] = str(exc)
    return result


def main():
    repo = Path(__file__).resolve().parents[3]
    result = classify(repo, os.environ.get('GITHUB_EVENT_NAME'), os.environ.get('COH_PUSH_BEFORE'), os.environ.get('GITHUB_SHA'))
    output = Path('out/map-startup-change-scope.json'); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as stream:
        stream.write('native_required='+str(result['native_required']).lower()+'\n')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
