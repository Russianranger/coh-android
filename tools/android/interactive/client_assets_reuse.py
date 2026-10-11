#!/usr/bin/env python3
"""Authenticate independent .28 artifact owners without treating a failed run as complete.

The completed resources, shipping MapServer, compiled host generator and finished
beacon graph have separate owners. Reuse never waives packaging, native graph
readback, PostgreSQL, signer, payload or public-byte qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = 'Russianranger/coh-android'
WORKFLOW = '.github/workflows/android-client-assets.yml'
BRANCH = 'codex/character-persistence-continuation'
ROLES = {
    'resource': ('resources', ('coh-assets-resource-inputs', 'coh-assets-audio-inputs'), None),
    'native': ('monorail', ('coh-monorail-native',), None),
    'generator': ('beacons', ('coh-kings-row-host-generator',),
                  'Retain completed host compile for exact reuse if later generation fails'),
    'beacon': ('beacons', ('coh-kings-row-beacons',), None),
}
# These may change while retaining the old native/resource producer source. Any
# other changed path fails closed. Native and generator receipts are also checked
# against the current source after downloading the authenticated artifacts.
RECOVERY_ONLY = frozenset({
    WORKFLOW, '.github/workflows/android-kings-row-native.yml',
    'tools/android/interactive/release-client-assets-0.13.28.json',
    'tools/android/interactive/client_assets_reuse.py',
    'tools/android/interactive/test_client_assets_reuse.py',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/qualify_client_assets.py',
    'tools/android/interactive/build_client_assets_apk.py',
    'tools/android/interactive/generate_kings_row_beacons.py',
    'tools/android/interactive/test_kings_row_beacons.py',
    'tools/android/interactive/test_character_reopen_guest.py',
    'tools/android/interactive/test_client_startup_followup_limits.py',
    'tools/android/interactive/test_generate_atlas_beacons.py',
    'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.28-testing.txt',
    'docs/COH-ASSETS-0.13.28.md',
    'docs/android-evidence/client-assets-0.13.28-publication.json',
})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def api(path):
    request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def marker_values(marker, commit):
    require(marker.get('version') == '0.13.28' and marker.get('asset_version') == '1.0.0',
            'Publication version differs')
    require(re.fullmatch('[0-9a-f]{40}', commit or ''), 'Exact packaging commit required')
    values = {}
    for role in ROLES:
        owner = str(marker.get(role + '_run_id', ''))
        source = marker.get(role + '_commit', '' if owner else commit)
        require(not owner or re.fullmatch('[1-9][0-9]*', owner), 'Invalid ' + role + ' artifact owner')
        require(re.fullmatch('[0-9a-f]{40}', source or ''), 'Explicit ' + role + ' source commit required')
        require(owner or source == commit, 'Fresh ' + role + ' source must be the current commit')
        values.update({role + '_run_id': owner, role + '_commit': source})
    # Never infer complete beacons from a successfully compiled MapServer.
    return values


def authenticate_reuse(values, commit, request=api):
    runs, comparisons, evidence = {}, {}, {}
    for role, (job_name, names, required_step) in ROLES.items():
        owner, source = values[role + '_run_id'], values[role + '_commit']
        if not owner:
            continue
        if source != commit and source not in comparisons:
            comparison = request('/compare/' + source + '...' + commit)
            files = comparison.get('files', [])
            require(comparison.get('status') in ('ahead', 'identical') and len(files) < 300,
                    'Artifact source must be an ancestor with a complete bounded diff')
            changed = {row['filename'] for row in files}
            changed.update(row['previous_filename'] for row in files if 'previous_filename' in row)
            require(changed <= RECOVERY_ONLY, 'Producer source changed since compile: ' + ', '.join(sorted(changed - RECOVERY_ONLY)))
            comparisons[source] = sorted(changed)
        if owner not in runs:
            run = request('/actions/runs/' + owner)
            require(str(run.get('id')) == owner and run.get('repository', {}).get('full_name') == REPOSITORY
                    and run.get('head_repository', {}).get('full_name') == REPOSITORY
                    and run.get('head_branch') == BRANCH and run.get('path') == WORKFLOW
                    and run.get('status') == 'completed', 'Artifact workflow owner differs or is unfinished')
            jobs = request('/actions/runs/' + owner + '/jobs?per_page=100&filter=latest')
            artifacts = request('/actions/runs/' + owner + '/artifacts?per_page=100')
            require(jobs.get('total_count', 101) <= 100 and artifacts.get('total_count', 101) <= 100,
                    'Artifact owner inventory requires complete pagination')
            runs[owner] = run, jobs['jobs'], artifacts['artifacts']
        run, jobs, artifacts = runs[owner]
        require(run.get('head_sha') == source, role + ' source commit does not own the named run')
        matches = [job for job in jobs if job.get('name') == job_name
                   or job.get('name', '').endswith(' / ' + job_name)]
        require(len(matches) == 1, 'Missing or ambiguous ' + role + ' producer job')
        job = matches[0]
        if required_step:
            steps = [step for step in job.get('steps', []) if step.get('name') == required_step]
            require(len(steps) == 1 and steps[0].get('conclusion') == 'success',
                    'Host generator compile/upload was not completed')
        else:
            require(job.get('conclusion') == 'success', role + ' producer job did not complete successfully')
        selected = []
        for name in names:
            found = [row for row in artifacts if row.get('name') == name and not row.get('expired')]
            require(len(found) == 1 and found[0].get('size_in_bytes', 0) > 0,
                    'Missing, expired or ambiguous reusable artifact: ' + name)
            artifact = found[0]
            require(artifact.get('workflow_run', {}).get('id') == int(owner)
                    and artifact.get('workflow_run', {}).get('head_sha') == source,
                    'Artifact is not owned by the authenticated source run')
            selected.append({key: artifact.get(key) for key in ('id', 'name', 'size_in_bytes', 'digest')})
        evidence[role] = {'run_id': int(owner), 'repository_commit': source,
            'job_id': job['id'], 'job_conclusion': job['conclusion'], 'artifacts': selected,
            'recovery_only_changed_paths': comparisons.get(source, []),
            'physical_thor_validated': False}
    return evidence


def gate(args):
    import build_client_assets_apk as package
    marker = json.loads(args.marker.read_text())
    values = marker_values(marker, args.commit)
    try:
        release = api('/releases/tags/' + package.RELEASE_TAG)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        required = True
    else:
        package.validate_existing_release(release)
        required = False
    # A complete release should not depend on expired historical CI artifacts.
    owners = authenticate_reuse(values, args.commit) if required else {}
    document = {'format': 1, 'repository_commit': args.commit, 'publication_required': required,
                'owners': owners, 'physical_thor_validated': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + '\n')
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        for name, value in dict(values, required=str(required).lower()).items():
            output.write(name + '=' + value + '\n')
    print(json.dumps(document, indent=2))


def generator(args):
    sys.path.insert(0, str(ROOT / 'tools'))
    import prepare_kings_row_beacon_generator_source as producer
    require(re.fullmatch('[0-9a-f]{40}', args.commit) and re.fullmatch('[1-9][0-9]*', args.run_id),
            'Exact retained generator source and owner required')
    receipt = args.directory / producer.RECEIPT
    executable = args.directory / 'out/build/vs2026/bin/OptDebug/MapServer.exe'
    require(json.loads(receipt.read_bytes()) == producer.expected(), 'Retained generator source differs')
    require(executable.is_file() and not executable.is_symlink() and executable.stat().st_size > 0,
            'Retained generator is absent')
    document = {'format': 1, 'role': 'reused_host_only_kings_row_beacon_generator',
                'repository_commit': args.commit, 'run_id': int(args.run_id),
                'run_url': 'https://github.com/' + REPOSITORY + '/actions/runs/' + args.run_id,
                'files': {str(path.relative_to(args.directory)): {
                    'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                    for path in (receipt, executable)}, 'source_receipt_matches_current_source': True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + '\n')
    print(json.dumps(document, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    entry = commands.add_parser('gate')
    entry.add_argument('--marker', type=Path, required=True)
    entry.add_argument('--commit', required=True)
    entry.add_argument('--output', type=Path, required=True)
    entry = commands.add_parser('generator')
    entry.add_argument('--directory', type=Path, required=True)
    entry.add_argument('--commit', required=True)
    entry.add_argument('--run-id', required=True)
    entry.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    (gate if args.command == 'gate' else generator)(args)
