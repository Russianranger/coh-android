#!/usr/bin/env python3
"""Stage exactly the six plaza/statue textures approved on 2026-10-26.

Approval: PR #6 comment 6419236533 (the user, relayed in the Claude lead
session). The selection is `evidence/m3-proposed-plaza-statue-materials.json`;
every file must be the identical entry of the reviewed client-visual manifest,
taken from the pinned client-visual-assets archive. No other files, no new
download source and no error exception.
"""
import argparse
import json
from pathlib import Path
import tempfile

from reviewed_asset_coverage import load_manifest
from stage_atlas_supplement import digest, require
from stage_reviewed_files import stage_archive
from stage_approved_ranges import verify as verify_files

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = 'armport/evidence/m3-proposed-plaza-statue-materials.json'
APPROVAL = 6419236533


def checked_plan(root=ROOT):
    plan = json.loads((root / PROPOSAL).read_text())
    document, decoded = load_manifest(root / 'assets/client-visual-manifest.json')
    source = plan['sources']['client-visual']
    require(set(plan['sources']) == {'client-visual'} and source['decoded'] == decoded
            and source['archive'] == document['archive'], 'Proposal source differs from reviewed manifest')
    files = {}
    for name, pin in plan['files'].items():
        require(pin['source'] == 'client-visual', 'Unapproved source')
        entry = document['files'].get(name)
        require(entry is not None and entry['bytes'] == pin['bytes'] and entry['sha256'] == pin['sha256'],
                'Selected file differs from reviewed manifest: ' + name)
        files[name] = dict(bytes=pin['bytes'], sha256=pin['sha256'])
    require(len(files) == plan['file_count'] == 6
            and sum(p['bytes'] for p in files.values()) == plan['payload_bytes'] == 2306838,
            'Approved count or bytes differ')
    return files, document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--visual', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    files, document = checked_plan()
    # Re-open the pinned archive on every restore; verify the restored layer.
    with tempfile.TemporaryDirectory(prefix='plaza-verify-') as tmp:
        output = Path(tmp) if args.verify_only else args.output
        stage_archive(args.visual, document, files, output)
        verify_files(output, dict(files=files))
    verify_files(args.output, dict(files=files))
    print('::notice title=ArmPort approved plaza/statue materials::' + json.dumps(dict(
        files=len(files), payload_bytes=sum(p['bytes'] for p in files.values()),
        proposal_sha256=digest(ROOT / PROPOSAL), approval_comment=APPROVAL,
        new_source_fetched=False, texture_exception_enabled=False)))


if __name__ == '__main__':
    main()
