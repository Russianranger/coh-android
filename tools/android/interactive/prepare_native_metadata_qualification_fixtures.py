#!/usr/bin/env python3
"""Recover finite original host-test evidence without rebuilding native code.

The existing full Assets 1.0.0 qualification supplies cache components. This
stage never downloads an asset volume, opens a player profile, or creates
native execution/promotion authority. Failed historical runs stay failed.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(Path(__file__).parent)]
import native_startup_metadata_contract as contract
import native_startup_component_migration as migration

REPOSITORY = 'Russianranger/coh-android'
REPOSITORY_ID = 1368730125
API = 'https://api.github.com/repos/'+REPOSITORY
DONOR = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
REPORT = 'native-map-world-037-qualification.json'
MAX_JSON = 8*1024**2
MAX_EXPANDED = 32*1024**2
ARTIFACTS = {
    'preload': {'source': '9454e7892ac81cf4503fd8ad961dc36c27cfc152', 'run_id': 38352862725,
        'job_id': 115148990574, 'conclusion': 'success', 'artifact_id': 11791389599,
        'artifact_name': 'coh-map-prefetch-generated-fixture-Wine-evidence', 'filename': 'artifact-11791389599.zip',
        'archive': {'bytes': 281739, 'sha256': '5a5bf01b901e5c5398bb42f07e4c1737ac8b13ee90e90fb297ca01cd08dfa34b'},
        'members': 38, 'expanded_bytes': 1212190, 'report': 'native-startup-profile-qualification.json',
        'report_pin': {'bytes': 375375, 'sha256': 'a84aa918e89a8e4f60be80fc26ccd2960cffcac80c79ddf38d15619ffff5dfb7'},
        'report_status': 'passed'},
    'map_producer': {'source': '47e40d4d586d29e273e31ed4d0d51d160832b89d', 'run_id': 38350813669,
        'job_id': 115142552789, 'conclusion': 'success', 'artifact_id': 11790609618,
        'artifact_name': 'coh-nonshipping-map-metadata-prefetch', 'filename': 'source-audit-11790609618.zip',
        'archive': {'bytes': 3307410, 'sha256': '69bfc9f44e5304eae786d0668ba30f183f5b99a58586f8db7861f697d8e23aab'},
        'members': 4, 'expanded_bytes': 7650744, 'report': 'native-map-prefetch-package.json',
        'report_pin': {'bytes': 12283, 'sha256': '877207e8889a4e5c97e39aa8fb87f113592f062eb74b89d7a41a82faf1e6cafe'}},
    'failed_8a': {'source': '8a08a1927225fdaa334ae330b8c8c5d044306fc2', 'run_id': 38489822992,
        'job_id': 115613213713, 'conclusion': 'failure', 'artifact_id': 11862252874,
        'artifact_name': 'coh-native-world-037-executed-evidence', 'filename': 'map8a-world-evidence.zip',
        'archive': {'bytes': 372926, 'sha256': 'cffe248141252a3e9b72b663dacfce7dadb7c5a0f5cf6152a53af9785240292a'},
        'members': 18, 'expanded_bytes': 1489069, 'report': REPORT,
        'report_pin': {'bytes': 508237, 'sha256': '4d932850a02a132562e394677cc2596b82839009af27871078e72c22a8fd5b07'},
        'report_status': 'failed'},
    'failed_04b': {'source': '04b7a623ef21d7ad48774a58b3122c69ae07f46b', 'run_id': 38494199595,
        'job_id': 115627188579, 'conclusion': 'failure', 'artifact_id': 11864550716,
        'artifact_name': 'coh-native-world-037-executed-evidence', 'filename': 'map04b-world-evidence.zip',
        'archive': {'bytes': 3039985, 'sha256': '962d7517ca5d91dd00b797f5b428bdf5fce1975c6c4afc392f7dc9e0a24b06fc'},
        'members': 20, 'expanded_bytes': 5275843, 'report': REPORT,
        'report_pin': {'bytes': 1039965, 'sha256': 'c2c3d768a4269f665a0e3d8651054a63a188be9f815faea974fea98fe82207c7'},
        'report_status': 'failed'},
    'failed_b323': {'source': 'b3239ed001cd75a92910731710b7675506cf1944', 'run_id': 38499817621,
        'job_id': 115644491594, 'conclusion': 'failure', 'artifact_id': 11866634892,
        'artifact_name': 'coh-native-world-037-executed-evidence', 'filename': 'map-b323-world-evidence.zip',
        'archive': {'bytes': 4582240, 'sha256': 'f6d50773cbeab72ff9afd989e95348fd4481f1f9bc8ebdd67338661f835bde77'},
        'members': 42, 'expanded_bytes': 14293474, 'report': REPORT,
        'report_pin': {'bytes': 3151476, 'sha256': '44e48a3ec17a0930c72d6790f6dc8463035cc9f2720f29b010e1b562b353a364'},
        'report_status': 'failed'}}
# Canonical complete member inventories, derived from the exact five original
# whole-SHA authenticated ZIPs. A report pin alone cannot substitute other rows.
MEMBER_PIN_DIGESTS = {
    'preload': '965ca1760b010693d45cbb0aaa1571e4f5064672eae2e4fe8e54931ed174be24',
    'map_producer': 'abb4f85647360a84480ceea9a498db72f0351645d6842a0e56c47a8328d6ba49',
    'failed_8a': '4467a1d5b80e732d9fa75ba970a3676377644274b539b715deb03729cf2e42b1',
    'failed_04b': '03b2af8f09d96e1fbfe2bf43bb3d453c42a4f66111ad74bbf37243e433871771',
    'failed_b323': '6d3f886130e45010e5080a2e0ebe9bf2c5b63a7d06f8dd82b8e648778bc77b4b',
}
COMPONENTS = {
    'client-caches.zip': {'bytes': 27071659, 'sha256': '5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'},
    'server-caches.zip': {'bytes': 29825263, 'sha256': '7439d4557ae9fd74bb4bb4a324b6a676829387124be0817eb1da3c8adff10b17'},
    'client-prerequisites.zip': {'bytes': 18757, 'sha256': 'cc8bd66c482233a8d5ee7f33e51015bb5981f993cad014378b3861550b520e0e'}}
RESEARCH = {'path': 'docs/android-evidence/native-map-cache-subset-0.13.37-research.json',
    'pin': {'bytes': 70722, 'sha256': 'fa566ee62b2fa46d5d85a841ba0b6474bb8104da2da3d37364b5c90fbe90fbcb'}}
require = contract.require


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def validate_api(spec, value):
    require(type(value) is dict and set(value) == {'run', 'jobs', 'artifact'}, 'Exact actual API metadata closure required')
    run, jobs, artifact = (value[name] for name in ('run', 'jobs', 'artifact'))
    require(type(run) is dict and type(run.get('id')) is int and run['id'] == spec['run_id']
        and run.get('head_sha') == spec['source'] and run.get('status') == 'completed'
        and run.get('conclusion') == spec['conclusion']
        and run.get('repository', {}).get('full_name') == REPOSITORY,
        'Original run/source/conclusion/repository differs')
    require(type(jobs) is dict and type(jobs.get('jobs')) is list and 0 < len(jobs['jobs']) <= 100,
        'Bounded actual job metadata required')
    selected = [row for row in jobs['jobs'] if type(row) is dict and type(row.get('id')) is int and row['id'] == spec['job_id']]
    require(len(selected) == 1 and selected[0].get('run_id') == spec['run_id']
        and selected[0].get('head_sha', spec['source']) == spec['source'] and selected[0].get('status') == 'completed'
        and selected[0].get('conclusion') == spec['conclusion'], 'Original actual native job/source/conclusion differs')
    require(type(artifact) is dict, 'Actual original artifact API metadata required')
    workflow = artifact.get('workflow_run', {})
    require(type(artifact) is dict and type(artifact.get('id')) is int and artifact['id'] == spec['artifact_id']
        and artifact.get('name') == spec['artifact_name'] and artifact.get('expired') is False
        and type(artifact.get('size_in_bytes')) is int and artifact['size_in_bytes'] == spec['archive']['bytes']
        and artifact.get('digest') == 'sha256:'+spec['archive']['sha256']
        and workflow.get('id') == spec['run_id'] and workflow.get('head_sha') == spec['source']
        and workflow.get('repository_id') == workflow.get('head_repository_id') == REPOSITORY_ID,
        'Original actual artifact/source/digest/custody differs')
    return copy.deepcopy(value)


class ArtifactRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, *args, **kwargs):
        redirected = super().redirect_request(request, *args, **kwargs)
        if redirected is not None:
            location = urllib.parse.urlsplit(redirected.full_url)
            require(location.scheme == 'https' and location.hostname and (location.hostname == 'api.github.com'
                or location.hostname.endswith(('.blob.core.windows.net', '.githubusercontent.com', '.amazonaws.com'))),
                'Unrecognized artifact redirect destination')
            if location.hostname != 'api.github.com': redirected.remove_header('Authorization')
        return redirected


def request_bytes(url, maximum, token=None):
    allowed = {API+'/actions/'+suffix for spec in ARTIFACTS.values() for suffix in (
        'runs/'+str(spec['run_id']), 'runs/'+str(spec['run_id'])+'/jobs?per_page=100',
        'artifacts/'+str(spec['artifact_id']), 'artifacts/'+str(spec['artifact_id'])+'/zip')}
    require(type(url) is str and url in allowed, 'Only the finite original repository Actions endpoints may be requested')
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if token: headers['Authorization'] = 'Bearer '+token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.build_opener(ArtifactRedirect).open(request, timeout=60) as response:
        raw = response.read(maximum+1)
    require(type(raw) is bytes and 0 < len(raw) <= maximum, 'Bounded original Actions response required')
    return raw


def actual_api(spec, token):
    run = contract.unique_json(request_bytes(API+'/actions/runs/'+str(spec['run_id']), MAX_JSON, token))
    jobs = contract.unique_json(request_bytes(API+'/actions/runs/'+str(spec['run_id'])+'/jobs?per_page=100', MAX_JSON, token))
    artifact = contract.unique_json(request_bytes(API+'/actions/artifacts/'+str(spec['artifact_id']), MAX_JSON, token))
    return validate_api(spec, {'run': run, 'jobs': jobs, 'artifact': artifact})


def original_archive(raw, spec):
    require(pin(raw) == spec['archive'], 'Exact original '+spec['filename']+' whole ZIP differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        rows = archive.infolist(); names = [row.filename for row in rows]
        require(len(rows) == spec['members'] and len(set(names)) == len(names)
            and len({name.casefold() for name in names}) == len(names)
            and sum(row.file_size for row in rows) == spec['expanded_bytes'] <= MAX_EXPANDED
            and all(contract.material_member_name(name) for name in names), 'Original bounded archive inventory differs')
        members = {}
        for row in rows:
            require(not row.is_dir() and not row.flag_bits & 1
                and stat.S_IFMT(row.external_attr >> 16) in (0, stat.S_IFREG), 'Unsafe original native evidence member')
            body = archive.read(row); members[row.filename] = pin(body)
        body = archive.read(spec['report'])
    require(pin(body) == spec['report_pin'], 'Original native evidence report member differs')
    document = contract.unique_json(body)
    require(document.get('repository_commit') == spec['source'], 'Original report producer was relabelled')
    if 'report_status' in spec:
        require(document.get('status') == spec['report_status'], 'Original native pass/failure result was relabelled')
    return members, body


def source_audit(repository=ROOT):
    """Verify existing original Game recipe; staging does not compile or run it."""
    require(Path(repository).resolve() == ROOT.resolve(), 'Original recipe belongs to this exact checkout')
    import package_client_render_queue_native as queue
    receipt = queue.expected_receipt()
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    return {'checkout_repository_commit': source, 'retained_Game_build_input': receipt,
        'source_staging_and_reverse_patch_verified': True, 'native_binary_built': False,
        'Game_Map_Wine_process_executed': False}


def validate_proof(proof, *, repository_commit=None):
    require(type(proof) is dict and proof.get('format') == 1 and type(proof['format']) is int
        and proof.get('role') == 'original_native_metadata_host_qualification_fixture_recovery'
        and proof.get('status') == 'passed' and contract.same(proof.get('donor'), DONOR)
        and contract.same(proof.get('original_components'), COMPONENTS)
        and contract.same(proof.get('original_subset_research'), RESEARCH)
        and proof.get('full_final_world_descriptor') is None
        and all(proof.get(name) is False for name in ('native_binaries_rebuilt', 'native_processes_executed',
            'player_profile_opened', 'runtime_authority_created', 'failed_historical_runs_relabelled',
            'asset_volume_downloaded_by_this_stage', 'qualification_enabled', 'publication_enabled')),
        'Exact original fixture recovery scope required')
    original = proof.get('original_artifacts')
    require(type(original) is dict and set(original) == set(ARTIFACTS), 'Exact five original evidence artifacts required')
    for role, spec in ARTIFACTS.items():
        row = original[role]
        require(type(row) is dict and set(row) == {'original', 'actual_API', 'member_pins'}
            and contract.same(row['original'], spec), 'Original fixture source/artifact was substituted')
        validate_api(spec, row['actual_API'])
        members = row['member_pins']
        require(type(members) is dict and len(members) == spec['members']
            and all(contract.material_member_name(name) and type(value) is dict and set(value) == {'bytes', 'sha256'}
                and type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_EXPANDED
                and type(value['sha256']) is str and len(value['sha256']) == 64
                and all(letter in '0123456789abcdef' for letter in value['sha256']) for name,value in members.items())
            and sum(value['bytes'] for value in members.values()) == spec['expanded_bytes']
            and contract.same(members.get(spec['report']), spec['report_pin'])
            and len({name.casefold() for name in members}) == len(members)
            and contract.canonical_sha(members) == MEMBER_PIN_DIGESTS[role],
            'Original native evidence member boundary differs')
    source = proof.get('original_Game_source')
    require(type(source) is dict and source.get('source_staging_and_reverse_patch_verified') is True
        and source.get('native_binary_built') is False and source.get('Game_Map_Wine_process_executed') is False,
        'Original Game recipe/source staging scope differs')
    checkout = source.get('checkout_repository_commit')
    require(type(checkout) is str and len(checkout) == 40 and all(letter in '0123456789abcdef' for letter in checkout)
        and (repository_commit is None or checkout == repository_commit), 'Fixture source checkout identity differs')
    environment = proof.get('environment')
    require(type(environment) is dict and type(environment.get('COH_METADATA_RECOVERY')) is str
        and Path(environment['COH_METADATA_RECOVERY']).is_absolute(), 'Exact fixture environment root required')
    require(contract.same(environment, fixture_environment(Path(environment['COH_METADATA_RECOVERY']))),
        'Exact bounded fixture environment paths required')
    import package_client_render_queue_native as queue
    require(contract.same(source.get('retained_Game_build_input'), queue.expected_receipt()),
        'Original Game source/recipe closure differs')
    require(contract.same(proof.get('fixture_preparer_source'), {
        'path': 'tools/android/interactive/prepare_native_metadata_qualification_fixtures.py', 'pin': pin(Path(__file__).read_bytes())}),
        'Current source-bound fixture preparer differs')
    return proof


def fixture_environment(output):
    return {'COH_METADATA_RECOVERY': str(output),
        'COH_METADATA_TEST_PREREQUISITES_DONOR': str(output/'public-asset-cache-donor/client-prerequisites.zip'),
        'COH_METADATA_TEST_CLIENT_CACHE_DONOR': str(output/'public-asset-cache-donor/client-caches.zip'),
        'COH_METADATA_TEST_SERVER_CACHE_DONOR': str(output/'public-asset-cache-donor/server-caches.zip'),
        'COH_METADATA_TEST_PRELOAD_RESEARCH': str(output/'actual-preload-107-cache-subset-research.json'),
        'COH_METADATA_TEST_MAP_PRODUCER': str(output/'source-audit-11790609618.zip')}


def prepare(donor_apk, payloads, output, *, archive_paths=None, api_snapshots=None, token=None):
    output, payloads = Path(output).absolute(), Path(payloads).absolute()
    require(not output.exists() and not output.is_symlink()
        and not any(parent.is_symlink() for parent in output.parents), 'Fresh nonlinked owned fixture output required')
    donor = migration.read_regular(Path(donor_apk).absolute(), 64*1024**2)
    require(pin(donor) == DONOR, 'Exact audited public .36 APK fixture required')
    originals = migration.authenticated_donor(Path(donor_apk).absolute())
    with zipfile.ZipFile(io.BytesIO(donor)) as archive:
        prerequisites = archive.read('assets/runtime/client-prerequisites.zip')
    raw_components = {'client-prerequisites.zip': prerequisites}
    for name in ('client-caches.zip', 'server-caches.zip'):
        raw_components[name] = migration.read_regular(payloads/name, 64*1024**2)
    for name, raw in raw_components.items(): require(pin(raw) == COMPONENTS[name], 'Existing qualified component differs: '+name)
    research = migration.read_regular(ROOT/RESEARCH['path'], MAX_JSON)
    require(pin(research) == RESEARCH['pin'], 'Original committed subset research differs')
    require((archive_paths is None) == (api_snapshots is None), 'Offline originals require their actual API snapshots')
    if archive_paths is not None:
        require(type(archive_paths) is dict and type(api_snapshots) is dict
            and set(archive_paths) == set(api_snapshots) == set(ARTIFACTS), 'Exact finite original artifact set required')
    records, raw_archives, report_bodies = {}, {}, {}
    for role, spec in ARTIFACTS.items():
        actual = actual_api(spec, token) if api_snapshots is None else validate_api(spec, api_snapshots[role])
        raw = (request_bytes(API+'/actions/artifacts/'+str(spec['artifact_id'])+'/zip', spec['archive']['bytes'], token)
            if archive_paths is None else migration.read_regular(Path(archive_paths[role]).absolute(), 32*1024**2))
        members, body = original_archive(raw, spec)
        records[role] = {'original': copy.deepcopy(spec), 'actual_API': actual, 'member_pins': members}
        raw_archives[role] = raw; report_bodies[role] = body
    sources = source_audit()
    client_members, _ = migration.zip_members(originals['game'])
    retained = contract.unique_json(client_members['client-package.json'])['client_render_queue']['manifest']['build_input']
    require(contract.same(retained, sources['retained_Game_build_input']), 'Actual .36 Game/source recipe differs')
    environment = fixture_environment(output)
    proof = {'format': 1, 'role': 'original_native_metadata_host_qualification_fixture_recovery', 'status': 'passed',
        'donor': DONOR, 'original_artifacts': records, 'original_components': COMPONENTS,
        'original_subset_research': RESEARCH, 'original_Game_source': sources, 'environment': environment,
        'fixture_preparer_source': {'path': 'tools/android/interactive/prepare_native_metadata_qualification_fixtures.py',
            'pin': pin(Path(__file__).read_bytes())},
        'native_binaries_rebuilt': False, 'native_processes_executed': False,
        'player_profile_opened': False, 'runtime_authority_created': False,
        'failed_historical_runs_relabelled': False, 'asset_volume_downloaded_by_this_stage': False,
        'full_final_world_descriptor': None, 'qualification_enabled': False, 'publication_enabled': False}
    validate_proof(proof, repository_commit=sources['checkout_repository_commit'])
    output.mkdir(parents=True, mode=0o700)
    def write(name, raw):
        target = output/name; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream: stream.write(raw)
        target.chmod(0o400)
    for role, raw in raw_archives.items(): write(ARTIFACTS[role]['filename'], raw)
    for name, raw in raw_components.items(): write('public-asset-cache-donor/'+name, raw)
    write('actual-preload-107-cache-subset-research.json', research)
    write('map8a-world-evidence/'+REPORT, report_bodies['failed_8a'])
    for role, row in records.items():
        for kind, value in row['actual_API'].items(): write('api/'+role+'/'+kind+'.json', contract.encoded(value))
    write('fixture-recovery.json', contract.encoded(proof))
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--donor-apk', type=Path, required=True)
    parser.add_argument('--payload-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.donor_apk, args.payload_directory, args.output, token=os.environ.get('GH_TOKEN'))


if __name__ == '__main__': main()
