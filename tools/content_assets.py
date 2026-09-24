#!/usr/bin/env python3
"""Acquire/record external PIGGs without Windows; never modify imported text data."""

import argparse
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'assets/catalog.json'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def probe(entry):
    result = {'name': entry['name'], 'url': entry['url']}
    try:
        request = urllib.request.Request(entry['url'], method='HEAD')
        with urllib.request.urlopen(request, timeout=15) as response:
            result.update(status=response.status,
                          bytes=response.headers.get('Content-Length'),
                          last_modified=response.headers.get('Last-Modified'))
    except urllib.error.HTTPError as error:
        result.update(status=error.code, error=str(error))
    except (OSError, urllib.error.URLError) as error:
        result.update(status=None, error=str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['probe', 'fetch', 'record', 'verify'])
    parser.add_argument('--directory', type=Path, default=ROOT / 'imports/piggs')
    parser.add_argument('--name', action='append', help='Select an archive; repeat as needed')
    parser.add_argument('--output', type=Path, help='Probe JSON output')
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text())
    entries = catalog['archives']
    for entry in entries:
        name = entry['name']
        if Path(name).name != name or '/' in name or '\\' in name or not name.endswith('.pigg'):
            parser.error('Invalid archive name in catalog')
        if not entry['url'].startswith('https://'):
            parser.error('Asset URLs must use HTTPS')
    if args.name:
        unknown = set(args.name) - {e['name'] for e in entries}
        if unknown:
            parser.error('Unknown archives: ' + ', '.join(sorted(unknown)))
        entries = [e for e in entries if e['name'] in args.name]
    catalog_hash = digest(CATALOG)
    if args.action == 'probe':
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(probe, entries))
        report = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'catalog_sha256': catalog_hash, 'method': 'HEAD', 'results': results,
                  'note': 'HTTP reachability only; no content or gameplay validation'}
        if args.output:
            write_json(args.output, report)
        for result in results:
            print(json.dumps(result), flush=True)
        # A probe records failures as data; fetching fails on errors below.
        return 0
    directory = args.directory.resolve()
    if args.action in ('fetch', 'record'):
        directory.mkdir(parents=True, exist_ok=True)
    receipt_path = directory / 'asset-receipt.json'
    receipt = {'schema_version': 1, 'catalog_sha256': catalog_hash,
               'assurance': 'Locally observed hashes, not upstream-authenticated checksums',
               'archives': {}}
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('catalog_sha256') != catalog_hash:
            raise SystemExit('Receipt belongs to a different catalog; use a separate directory')
    failures = []
    for entry in entries:
        name = entry['name']
        path = directory / name
        if path.is_symlink():
            raise SystemExit('Refusing symlink: ' + str(path))
        expected = receipt['archives'].get(name)
        if args.action == 'fetch':
            if path.exists():
                if expected and path.stat().st_size == expected['bytes'] and digest(path) == expected['sha256']:
                    print('Verified cached ' + name, flush=True)
                    continue
                raise SystemExit('Unverified existing archive: ' + str(path) +
                                 '; use record for an intentional local import or a fresh directory')
            temporary = path.with_name(name + '.part')
            if temporary.is_symlink():
                raise SystemExit('Refusing symlink: ' + str(temporary))
            print('Downloading ' + name, flush=True)
            with urllib.request.urlopen(entry['url'], timeout=60) as response, temporary.open('wb') as output:
                size = 0
                for chunk in iter(lambda: response.read(1024 * 1024), b''):
                    output.write(chunk)
                    size += len(chunk)
                declared = response.headers.get('Content-Length')
                if response.status != 200 or not size or (declared and size != int(declared)):
                    raise SystemExit('Incomplete download: ' + name)
            checksum = digest(temporary)
            if entry.get('sha256') and checksum != entry['sha256']:
                raise SystemExit('Upstream checksum mismatch: ' + name)
            temporary.replace(path)
        if not path.is_file() or not path.stat().st_size:
            failures.append('Missing/empty ' + name)
            continue
        checksum = digest(path)
        if args.action == 'verify':
            if not expected or path.stat().st_size != expected['bytes'] or checksum != expected['sha256']:
                failures.append('Missing receipt or changed bytes: ' + name)
            elif entry.get('sha256') and checksum != entry['sha256']:
                failures.append('Upstream checksum mismatch: ' + name)
        else:
            if entry.get('sha256') and checksum != entry['sha256']:
                raise SystemExit('Upstream checksum mismatch: ' + name)
            receipt['archives'][name] = {'url': entry['url'], 'bytes': path.stat().st_size,
                                         'sha256': checksum}
            write_json(receipt_path, receipt)
        print(args.action + ': ' + name, flush=True)
    for failure in failures:
        print(failure)
    print(f'{len(entries) - len(failures)}/{len(entries)} selected archives accounted for; '
          'this does not validate PIGG structure or source/data compatibility.')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
