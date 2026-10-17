#!/usr/bin/env python3
"""Audit retained hosted constructor receipts; never rerun a qualifier."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
COMMIT = 'b3fbacf90626e29542e878313c2812eba1e1375b'
TREE = '55f87f9f1b37c09d8250fcbfee473a6608e5dd01'
RUN = 39075900689
JOB = 117522870673
ARTIFACT = 12115829917
ARCHIVE_SHA = '0c34fc5263eac57905de7baa7fa1fc46771d60a725d1b15255b052b657a66ca0'
WORKFLOW = '.github/workflows/native-source-constructors.yml'
WORKFLOW_SHA = 'e1768092f970bade3e89958820be099874211d2608005b9eb2895ebe16373d16'
SPECS = {
    'tex-seed.json': (15871, '6abe5cd933605a551c4d645f2ddf68657278ee208e1a399dc3916d5710f520d8',
        'native-android/engine/world-render-adapter/qualification/texture-seed-eligibility-20261017/host.json',
        '4ee743d49b406866a07de03dc5d351f90a64adc5abce64f4f5d86d4590deec6c', 36),
    'initial-power-slots.json.gz': (11459, '27a1c817e5d42dcf71c6cb4987c018e35423817d1db158305531339a11af8913',
        'native-android/engine/character-dictionary/qualification/initial-power-slots-20261017-final.json.gz',
        'ede04085e64b6f3aaa47139bf25863fb17eb70deb9ff51465f4e9e2f99729397', 65),
}


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *arguments):
    result = subprocess.run(['git', *arguments], cwd=root, capture_output=True, timeout=60)
    require(result.returncode == 0, 'EXACT_GIT_INPUT_UNAVAILABLE')
    return result.stdout


def parse(name, raw):
    return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)


def verify(root):
    info = json.loads((HERE / 'run.json').read_bytes())
    require(info['id'] == RUN and info['head_sha'] == COMMIT and info['head_branch'] == 'native-android'
            and info['head_commit']['tree_id'] == TREE and info['path'] == WORKFLOW
            and info['run_attempt'] == 1 and info['event'] == 'push'
            and info['status'] == 'completed' and info['conclusion'] == 'success', 'RUN_IDENTITY')
    jobs = json.loads((HERE / 'jobs.json').read_bytes())['jobs']
    require(len(jobs) == 1 and jobs[0]['id'] == JOB and jobs[0]['run_id'] == RUN
            and jobs[0]['status'] == 'completed' and jobs[0]['conclusion'] == 'success'
            and all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in jobs[0]['steps']),
            'COMPLETE_HOSTED_JOB')
    artifacts = json.loads((HERE / 'artifacts.json').read_bytes())['artifacts']
    require(len(artifacts) == 1, 'ARTIFACT_COUNT')
    item = artifacts[0]
    require(item['id'] == ARTIFACT and item['size_in_bytes'] == 16877
            and item['name'] == 'source-constructor-contracts-' + COMMIT
            and item['digest'] == 'sha256:' + ARCHIVE_SHA and item['expired'] is False
            and item['workflow_run']['id'] == RUN and item['workflow_run']['head_sha'] == COMMIT,
            'ARTIFACT_IDENTITY')
    archive = (HERE / 'artifact.zip').read_bytes()
    require(len(archive) == 16877 and sha(archive) == ARCHIVE_SHA, 'ARCHIVE_BYTES')
    require(git(root, 'rev-parse', COMMIT + '^{tree}').decode().strip() == TREE, 'EXACT_SOURCE_TREE')
    require(sha(git(root, 'show', COMMIT + ':' + WORKFLOW)) == WORKFLOW_SHA, 'REVIEWED_WORKFLOW')
    receipts = {}
    exact_sources = {}
    current_differences = {}
    with zipfile.ZipFile(HERE / 'artifact.zip') as zipped:
        rows = zipped.infolist()
        require(len(rows) == 2 and {v.filename for v in rows} == set(SPECS)
                and zipped.testzip() is None, 'EXACT_MEMBER_SET')
        for row in rows:
            name = row.filename
            size, digest, baseline_path, baseline_sha, source_count = SPECS[name]
            require(row.file_size == size and not row.flag_bits & 1
                    and stat.S_IFMT(row.external_attr >> 16) in (0, stat.S_IFREG), 'MEMBER_METADATA')
            body = zipped.read(row)
            require(len(body) == size and sha(body) == digest and body == (HERE / name).read_bytes(),
                    'EXACT_MEMBER_BYTES')
            proof = parse(name, body)
            require(proof['passed'] is True and proof['source_revision'] == COMMIT
                    and len(proof['source_sha256']) == source_count, 'PROOF_SOURCE_IDENTITY')
            for path, pin in proof['source_sha256'].items():
                require(not Path(path).is_absolute() and '..' not in Path(path).parts, 'SOURCE_PATH')
                source = git(root, 'show', COMMIT + ':' + path)
                require(sha(source) == pin, 'PUBLISHED_SOURCE_HASH')
                require(path not in exact_sources or exact_sources[path] == pin, 'SHARED_SOURCE_HASH')
                exact_sources[path] = pin
                current = root / path
                if not current.is_file() or sha(current.read_bytes()) != pin:
                    current_differences[path] = None if not current.is_file() else sha(current.read_bytes())
            baseline = git(root, 'show', COMMIT + ':' + baseline_path)
            require(sha(baseline) == baseline_sha, 'INDEPENDENTLY_REVIEWED_OWNER_PROOF')
            expected = parse(name, baseline)
            ignored = ({'source_revision', 'binary_sha256', 'standalone_public_exports',
                        'actual_C_object_CPP_call_link', 'host_release_stack_usage'} if name == 'tex-seed.json'
                       else {'source_revision', 'modes', 'native_stack'})
            require(set(proof) == set(expected)
                    and all(proof[k] == expected[k] for k in proof if k not in ignored),
                    'ALL_STABLE_SEMANTICS_EQUAL_REVIEWED_PROOF')
            if name == 'tex-seed.json':
                require(set(proof['modes']) == {'release', 'address', 'undefined'}, 'B_MODES')
                for mode, values in proof['modes'].items():
                    require(values['passed'] is True and values['checks'] == 211909
                            and values['original_comparisons'] == 32166
                            and values['actual_create_candidates'] == 0, 'B_MODE_RESULTS')
                    require(proof['standalone_public_exports'][mode]['symbols'] == ['coh_wr_tex_seed'],
                            'B_PUBLIC_EXPORT')
                cpp = proof['actual_C_object_CPP_call_link']
                require(cpp['passed'] is True and cpp['executed'] is True
                        and cpp['actual_C_object_sha256'] == proof['standalone_public_exports']['release']['actual_C_object_sha256']
                        and cpp['source_sha256'] == expected['actual_C_object_CPP_call_link']['source_sha256'], 'B_CPP_LINK')
                require([line.split('\t')[1:] for line in proof['host_release_stack_usage']]
                        == [line.split('\t')[1:] for line in expected['host_release_stack_usage']], 'B_HOST_STACK')
            else:
                require(set(proof['modes']) == {'release', 'asan', 'ubsan'}, 'C_MODES')
                for mode, values in proof['modes'].items():
                    require(values['checks'] == expected['modes'][mode]['checks']
                            and len(values['checks']) == 13 and sum(v['checks'] for v in values['checks']) == 537556,
                            'C_MODE_RESULTS')
                # Temporary-directory glob order may differ between hosts.
                # Compare the full function/size/kind multiset, not row order.
                require(sorted((v['function'].rsplit(':', 1)[-1], v['bytes'], v['kind']) for v in proof['native_stack'])
                        == sorted((v['function'].rsplit(':', 1)[-1], v['bytes'], v['kind']) for v in expected['native_stack']),
                        'C_HOST_STACK')
            receipts[name] = {'bytes': size, 'sha256': digest, 'source_entries_verified': source_count,
                'source_sha256': proof['source_sha256'], 'reviewed_owner_receipt_path': baseline_path,
                'reviewed_owner_receipt_sha256': baseline_sha, 'all_stable_semantics_match_reviewed_owner_proof': True}
    log = (HERE / 'job.log').read_text(encoding='utf-8-sig')
    require(all(value in log for value in (COMMIT, str(ARTIFACT), ARCHIVE_SHA, '211909', '32166', '537556', '20241')),
            'HOSTED_LOG_BINDING')
    return {'schema': 'coh-independent-hosted-source-constructors-audit-v1', 'passed': True,
        'run_id': RUN, 'job_id': JOB, 'artifact_id': ARTIFACT, 'source_commit': COMMIT, 'source_tree': TREE,
        'archive': {'bytes': len(archive), 'sha256': ARCHIVE_SHA}, 'receipts': receipts,
        'total_receipt_source_entries_verified': sum(v['source_entries_verified'] for v in receipts.values()),
        'unique_published_source_entries_verified': len(exact_sources),
        'current_worktree_differences_no_current_requalification_claim': current_differences,
        'reviewed_workflow_sha256': WORKFLOW_SHA,
        'B_checks_per_mode': 211909, 'B_original_comparisons_per_mode': 32166, 'B_authentic_create_candidates': 0,
        'C_checks_per_mode': 537556, 'C_profiles_per_mode': 13,
        'C_original_fresh_constructors': 20241, 'C_original_slot_append_calls': 24732,
        'host_memory': {'B_persistent_bytes': 0, 'B_copied_result_bytes': 2816,
            'B_own_and_nested_reservation_bytes': [32768, 16384],
            'C_fresh_owner_including_scalar_bytes': 16464, 'C_embedded_scalar_not_additional_bytes': 64,
            'C_workspace_including_record_workspace_bytes': 82000, 'C_own_plus_nested_reservation_bytes': 32768,
            'C_host_stack_sum_times4_bytes': 4064},
        'former_qualifiers_or_hosted_tests_rerun_by_reviewer': False,
        'actual_global_parent_budget_admitted': False, 'android_abi_or_rss_qualified': False,
        'current_client_generation_admitted': False, 'world_authority': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = verify(args.source_root.resolve())
    with args.output.open('x') as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write('\n')
    print(json.dumps({'passed': True, 'receipt_source_entries_verified': 101, 'world_authority': False}))
