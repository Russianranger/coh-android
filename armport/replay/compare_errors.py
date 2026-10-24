#!/usr/bin/env python3
"""Compare same-commit error evidence even when strict receiver jobs fail.

This diagnostic never grants replay or milestone credit and never fetches data.
Only paths absent from both actual runtimes and named by shared errors become
missing-file candidates; errors about files present remain visible separately.
"""
import argparse
import json
from pathlib import Path

import run_ci
import client_errors


def compare(root, commit):
    counts, lookups, assets = {}, {}, {}
    for target in ('arm64', 'i686'):
        folder = root / target
        report = json.loads((folder / 'report.json').read_text())
        if report.get('target') != target or report.get('source_commit') != commit:
            raise ValueError('Error comparison requires same source commit: ' + target)
        run = folder / 'id1-a'
        errors = client_errors.inventory(run / 'client-stdio.txt', run / 'client-errors.json',
                                         run / 'zone-trace.jsonl')
        counts[target] = {e['text']: e['count'] for e in errors['errors']}
        assets[target] = json.loads((run / 'error-assets.json').read_text())
        texture_requests = {name for text in counts[target] for name in client_errors.texture_names(text)}
        if set(assets[target]['textures']) != texture_requests:
            raise ValueError('Incomplete actual-runtime texture lookup: ' + target)
        lookups[target] = json.loads((run / 'error-geometry-files.json').read_text())
        requested = {name for text in counts[target] for name in client_errors.geometry_paths(text)}
        if set(lookups[target]) != requested:
            raise ValueError('Incomplete actual-runtime geometry lookup: ' + target)
    common = counts['arm64'].keys() & counts['i686'].keys()
    shared = [dict(text=text, arm64=counts['arm64'][text], i686=counts['i686'][text])
              for text in sorted(common)]
    paths = {name for text in common for name in client_errors.geometry_paths(text)}
    missing = [name for name in sorted(paths) if not lookups['arm64'][name] and not lookups['i686'][name]]
    textures = {name for text in common for name in client_errors.texture_names(text)}
    missing_textures = [name for name in sorted(textures)
                        if not assets['arm64']['textures'][name] and not assets['i686']['textures'][name]]
    return dict(shared_missing_textures=missing_textures, actual_assets=assets,
                source_commit=commit, scope='error_diagnostic_only', shared=shared,
                arm64_only=[dict(text=text, count=counts['arm64'][text])
                            for text in sorted(counts['arm64'].keys() - common)],
                i686_only=[dict(text=text, count=counts['i686'][text])
                           for text in sorted(counts['i686'].keys() - common)],
                shared_missing_geometry_files=missing, actual_geometry_files=lookups,
                error_free=not any(counts.values()), m3_replay_complete=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.root, args.commit)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    run_ci.notice('ArmPort error comparison diagnostic', dict(
        source_commit=args.commit, shared=len(result['shared']),
        arm64_only=len(result['arm64_only']), i686_only=len(result['i686_only']),
        shared_missing_geometry_files=len(result['shared_missing_geometry_files']),
        error_free=result['error_free'], m3_replay_complete=False))


if __name__ == '__main__':
    main()
