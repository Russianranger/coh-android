#!/usr/bin/env python3
"""Stage exactly the eight composite leaves approved in comment 6389265419.

No new source downloads and no texture-error exception. The historical proposal
stays immutable; every invocation recomputes it from the original declarations,
the previous selection and the reviewed manifests, then verifies staged bytes.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import tempfile

from reviewed_asset_coverage import load_manifest, sha
from stage_atlas_supplement import digest, require
from stage_reviewed_files import stage_archive
from stage_approved_ranges import verify as verify_files

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = 'armport/evidence/m3-proposed-composite-dependencies.json'


def leaves(text, name):
    blocks = re.findall(r'^Texture\s+' + re.escape(name) + r'\s*\n(.*?)^End\s*$',
                        text, re.M | re.S | re.I)
    require(len(blocks) == 1, 'Missing or ambiguous composite declaration')
    return {value.casefold() for value in re.findall(
        r'^\s*(?:Base[12]|Multiply[12]|DualColor[12]|BumpMap[12]|Mask)\s+(\S+)', blocks[0], re.M)
        if value.casefold() not in ('none', 'swappable')}


def checked_plan(root=ROOT):
    plan = json.loads((root / PROPOSAL).read_text())
    evidence = json.loads((root / 'armport/evidence/m3-dispatch-errors-40113107670.json').read_text())
    previous = json.loads((root / 'armport/evidence/m3-reviewed-file-selection.json').read_text())
    prior = {name.casefold() for files in previous['selected'].values() for name in files}
    documents, sources = {}, {}
    # Fixed reviewed source set; a proposal cannot introduce another archive.
    for source in ('client-visual', 'zones-world-supplement'):
        name = 'assets/' + source + '-manifest.json'
        document, decoded = load_manifest(root / name)
        documents[source] = document
        sources[source] = dict(manifest=name, decoded=decoded, archive=document['archive'])
    selected = {}
    for name, definition in evidence['composite_definitions'].items():
        raw = (root / definition['source']).read_bytes()
        require(sha(raw) == definition['source_sha256'], 'Original declaration digest differs')
        actual = leaves(raw.decode('utf-8'), definition['texture_block'])
        require(actual == set(definition['leaves']), 'Composite leaf inventory differs')
        for leaf in sorted(actual):
            matches = []
            for source, document in documents.items():
                for path, pin in document['files'].items():
                    p = PurePosixPath(path)
                    if (path.casefold().startswith('data/texture_library/')
                            and p.suffix.casefold() == '.texture' and p.stem.casefold() == leaf):
                        matches.append((source, path, pin))
            require(len({(p.casefold(), pin['bytes'], pin['sha256']) for _, p, pin in matches}) <= 1,
                    'Ambiguous composite leaf')
            if matches:
                source, path, pin = matches[0]
                if path.casefold() not in prior:
                    selected[path] = dict(source=source, **pin, referenced_by=name)
    require(selected == plan['files'] and sources == plan['sources'],
            'Recomputed dependencies differ from approved proposal')
    require(len(selected) == plan['file_count'] == 8
            and sum(pin['bytes'] for pin in selected.values()) == plan['payload_bytes'] == 658461,
            'Approved count or bytes differ')
    return plan, documents


def verify(output, plan):
    verify_files(output, dict(files={name: {k: pin[k] for k in ('bytes', 'sha256')}
                                    for name, pin in plan['files'].items()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--visual', type=Path)
    parser.add_argument('--zones', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    plan, documents = checked_plan()
    require(args.visual is not None and args.zones is not None, 'Both reviewed archives required even on restore')
    # Re-open the exact original archives on every cache/artifact hit too.
    # A fresh private extraction verifies archive SHA, complete ZIP inventory
    # and selected payload SHA without modifying the restored layer.
    with tempfile.TemporaryDirectory(prefix='composite-verify-') as tmp:
        output = Path(tmp) if args.verify_only else args.output
        for source, archive in (('client-visual', args.visual), ('zones-world-supplement', args.zones)):
            selected = {name: {k: pin[k] for k in ('bytes', 'sha256')}
                        for name, pin in plan['files'].items() if pin['source'] == source}
            stage_archive(archive, documents[source], selected, output)
        verify(output, plan)
    verify(args.output, plan)
    print('::notice title=ArmPort approved composite dependencies::' + json.dumps(dict(
        files=8, payload_bytes=658461, proposal_sha256=digest(ROOT / PROPOSAL),
        approval_comment=6389265419, new_source_fetched=False, texture_exception_enabled=False)))


if __name__ == '__main__':
    main()
