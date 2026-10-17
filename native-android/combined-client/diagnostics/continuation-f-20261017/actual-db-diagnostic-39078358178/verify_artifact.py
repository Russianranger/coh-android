"""Read-only byte/source audit of the retained public diagnostic artifact."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

REVISION = '6a6809d07a130af60129f569b59a627420b6bf54'
ARCHIVE_SHA = 'd0af1d607cabf054a9c7fc10e58fcd3f587ad34aa3bd75ddb1b123683a3788f4'
RECEIPT_SHA = 'e6b0bf7ac0e476ad60ad393ca3aa1a5e994b4f19f787d287e3c98fb61e4846ab'
PRIOR_REVIEW = 'native-android/combined-client/diagnostics/continuation-f-20261017/db-finite-catalog-review-20261017/review.json'
PRIOR_SHA = '79f3bd74272135ca59378720a1f2e9e0f8bee01ec0d233c6cd9e79948d67a58e'


def digest(body):
    return hashlib.sha256(body).hexdigest()


def audit(root, archive, prior_review):
    def blob(name):
        return subprocess.check_output(['git', 'show', REVISION + ':' + name], cwd=root)

    def tree(ref):
        return subprocess.check_output(['git', 'rev-parse', ref], cwd=root, text=True).strip()

    raw = archive.read_bytes()
    assert len(raw) == 13239 and digest(raw) == ARCHIVE_SHA
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
        assert len(infos) == len({item.filename for item in infos}) == 9
        assert source.testzip() is None
        assert all(item.filename == Path(item.filename).name and not item.is_dir() for item in infos)
        assert all(item.file_size == 0 for item in infos if item.filename != 'receipt.json')
        receipt = source.read('receipt.json')
    assert len(receipt) == 37369 and digest(receipt) == RECEIPT_SHA
    result = json.loads(receipt)
    assert result['repository_commit'] == REVISION and result['github_run_id'] == '39078358178'
    assert result['repository_tree'] == tree(REVISION + '^{tree}')
    assert result['original_source_tree'] == tree(REVISION + ':upstream/ouroboros')
    observation = result['owned_db_modal_diagnostic']['observation']
    pins = {'upstream/ouroboros/' + name: value for name, value in observation['original_source_sha256'].items()}
    pins.update(observation['classifier_source_sha256'])
    different_current = []
    for name, value in pins.items():
        assert digest(blob(name)) == value, name
        if digest((root / name).read_bytes()) != value:
            different_current.append(name)
    prior_bytes = prior_review.read_bytes()
    assert digest(prior_bytes) == PRIOR_SHA
    prior = json.loads(prior_bytes)
    assert all(observation[key] == value for key, value in prior['independently_recomputed_policy_identity'].items())
    for key in ('owned_db_startup_diagnostic', 'owned_db_modal_diagnostic'):
        block = result[key]
        assert block['complete'] is True
        assert block['generation_before'] == block['generation_after'] == result['owned_service_generations_start']['db']
    assert result['passed'] is False and result['failure'] == 'shard_db_ready_deadline'
    cleanup = {key: result[key] for key in (
        'owned_service_cleanup_complete', 'owned_firewall_cleanup_complete',
        'owned_localdb_cleanup_complete', 'private_files_removed', 'source_inputs_unchanged')}
    assert all(value is True for value in cleanup.values())
    assert observation['raw_titles_controls_or_stacks_exported'] is False
    assert result['private_console_exported'] is False
    matches = observation['source_matches']
    assert len(matches) == 1 and matches[0]['source_site_enum'] == 'pe_source_file_108_assert_001'
    assert all(matches[0][key] is True for key in (
        'source_assertion_line_verified', 'source_file_verified',
        'source_call_site_verified', 'source_expression_match'))
    catalog_name = 'native-android/engine/auth-interop/deployment/db_modal_pe_source_catalog.json'
    catalog = json.loads(blob(catalog_name))
    entry = next(item for item in catalog['upstream_files'] if item['enum'] == 'pe_source_file_108')
    assert entry['source_path'] == 'libs/UtilitiesLib/src/utils/quick_sprintf.c'
    source = blob('upstream/ouroboros/' + entry['source_path']).decode()
    assert 'assert((size_t)(tail-buf+1) <= buf_size);' in source.splitlines()[100]
    pe_archive_name = 'native-android/engine/auth-interop/evidence/independent-db-build-39000395572/artifact.zip'
    pe_archive = root / pe_archive_name
    assert digest(pe_archive.read_bytes()) == observation['compiled_variant_archive_sha256']
    with zipfile.ZipFile(pe_archive) as package:
        binary = package.read('DbServer-checksum-candidate.exe')
    assert digest(binary) == observation['compiled_variant_pe_sha256']
    workflow = '.github/workflows/native-original-db-startup.yml'
    return {
        'schema': 'coh-f-actual-db-diagnostic-review-v1',
        'source_revision': REVISION, 'source_tree': result['repository_tree'],
        'run_id': 39078358178, 'run_conclusion': 'failure',
        'artifact_id': 12118500733, 'artifact_bytes': len(raw), 'artifact_sha256': digest(raw),
        'receipt_bytes': len(receipt), 'receipt_sha256': digest(receipt),
        'public_archive_members': [{'name': item.filename, 'bytes': item.file_size} for item in infos],
        'all_nonreceipt_members_are_empty_firewall_command_streams': True,
        'workflow_sha256': digest(blob(workflow)), 'source_pin_count': len(pins),
        'source_pins_match_exact_run_revision': True,
        'source_pins_different_from_current_root': different_current,
        'prior_independent_policy_review_sha256': digest(prior_bytes),
        'all_prior_recomputed_policy_identity_fields_match': True,
        'pinned_original_pe_archive_and_binary_rechecked': True,
        'exact_source_match': matches[0], 'source_path': entry['source_path'],
        'source_line': 101, 'source_expression': '(size_t)(tail-buf+1) <= buf_size',
        'caller_or_root_cause_identified': False,
        'observation_generation_matches_actual_owned_service_start_and_after': True,
        'cleanup': cleanup, 'raw_dialog_or_console_exported': False,
        'qualifier_or_test_or_service_replayed': False,
        'interserver_activation_verified': False, 'world_authority': False, 'actor_authority': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--prior-review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = audit(args.source_root.resolve(), args.artifact, args.prior_review)
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'source_pins': value['source_pin_count'], 'current_differences': value['source_pins_different_from_current_root'], 'verification_sha256': digest(args.output.read_bytes())}))
