#!/usr/bin/env python3
"""Map observed missing files to exact reviewed manifests; never fetch data."""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath

SOURCES = ('client-visual', 'character-avatar-defaults', 'zones-world-supplement')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_manifest(path):
    raw = path.read_bytes()
    document = json.loads(raw)
    if document.get('encoding') == 'gzip+base64':
        compressed = base64.b64decode(document['data'], validate=True)
        if document['gzip'] != dict(bytes=len(compressed), sha256=sha(compressed)):
            raise ValueError('Compressed manifest identity differs: ' + str(path))
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            raw = stream.read(32 * 1024 * 1024 + 1)
        if len(raw) > 32 * 1024 * 1024 or document['decoded'] != dict(bytes=len(raw), sha256=sha(raw)):
            raise ValueError('Decoded manifest identity differs: ' + str(path))
        document = json.loads(raw)
    files = document['files']
    if len(files) != document['file_count'] or sum(p['bytes'] for p in files.values()) != document['payload_bytes']:
        raise ValueError('Manifest totals differ')
    folded = set()
    for name, pin in files.items():
        p = PurePosixPath(name)
        if (not name.startswith('data/') or p.as_posix() != name or '..' in p.parts
                or '\\' in name or ':' in name or name.casefold() in folded
                or type(pin.get('bytes')) is not int or pin['bytes'] <= 0
                or len(pin.get('sha256', '')) != 64):
            raise ValueError('Invalid/ambiguous manifest member: ' + name)
        folded.add(name.casefold())
    return document, dict(bytes=len(raw), sha256=sha(raw))


def coverage(evidence, assets):
    manifests, identities = {}, {}
    for source in SOURCES:
        path = assets / (source + '-manifest.json')
        manifests[source], decoded = load_manifest(path)
        identities[source] = dict(path=path.name, encoded_sha256=sha(path.read_bytes()),
                                  decoded=decoded, archive=manifests[source]['archive'])
    results = {}
    selected = {source: {} for source in SOURCES}
    for kind in ('missing_geometry', 'missing_textures'):
        matches = {}
        for request in evidence[kind]:
            candidates = []
            for source, document in manifests.items():
                for name, pin in document['files'].items():
                    p = PurePosixPath(name)
                    hit = (name.casefold() == 'data/' + request.casefold()) if kind == 'missing_geometry' else (
                        name.casefold().startswith('data/texture_library/') and p.suffix.casefold() == '.texture'
                        and p.stem.casefold() == request.casefold())
                    if hit:
                        candidates.append(dict(source=source, path=name, **pin))
            # Stem lookup is diagnostic only. Stage only a unique exact path and
            # identity across all reviewed sources; never guess between aliases.
            unique = {(c['path'].casefold(), c['bytes'], c['sha256']) for c in candidates}
            matches[request] = dict(candidates=candidates, ambiguous=len(unique) > 1)
            if len(unique) == 1:
                chosen = candidates[0]
                selected[chosen['source']][chosen['path']] = dict(bytes=chosen['bytes'], sha256=chosen['sha256'])
        results[kind] = matches
    return dict(scope='reviewed_missing_file_selection_only', source_run=evidence['run'],
                source_commit=evidence['source_commit'], sources=identities, coverage=results,
                selected=selected, uncovered={k: [n for n, v in rows.items() if not v['candidates']]
                                            for k, rows in results.items()},
                ambiguous={k: [n for n, v in rows.items() if v['ambiguous']] for k, rows in results.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--assets', type=Path, default=Path('assets'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = coverage(json.loads(args.evidence.read_text()), args.assets)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(selected={k: len(v) for k, v in result['selected'].items()},
                          uncovered=result['uncovered'], ambiguous=result['ambiguous'])))


if __name__ == '__main__':
    main()
