#!/usr/bin/env python3
"""Fetch the exact reviewed asset ZIP without exposing a private download URL.

Use a repository release asset ID (including a draft release), or put an HTTPS
download URL in COH_ASSET_BUNDLE_URL. Credentials never enter the receipt/log.
The committed receipt bounds both the transfer and the accepted SHA-256.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request


def https_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('An HTTPS URL without userinfo or fragment is required')
    return value


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        https_url(newurl)
        # Authorization is an unredirected header on the initial GitHub request.
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(receipt, output, release_asset_id=None, environment=None, opener=None):
    env = os.environ if environment is None else environment
    record = json.loads(Path(receipt).read_text(encoding='utf-8'))
    size, digest = record['archive_bytes'], record['archive_sha256']
    if not isinstance(size, int) or not 0 < size <= 2 * 1024**3 or not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('Invalid reviewed archive size or SHA-256')
    output = Path(output)
    temporary = output.with_name(output.name + '.part')
    if output.exists() or output.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise ValueError('Download output must be new')
    if release_asset_id:
        repo, token = env.get('GITHUB_REPOSITORY', ''), env.get('GH_TOKEN', '')
        if not str(release_asset_id).isdigit() or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not token:
            raise ValueError('Release download needs a numeric asset ID, repository and token')
        url = f'https://api.github.com/repos/{repo}/releases/assets/{release_asset_id}'
        request = urllib.request.Request(url, headers={'Accept': 'application/octet-stream', 'User-Agent': 'coh-runtime-validation'})
        request.add_unredirected_header('Authorization', 'Bearer ' + token)
    else:
        url = https_url(env.get('COH_ASSET_BUNDLE_URL', ''))
        request = urllib.request.Request(url, headers={'User-Agent': 'coh-runtime-validation'})
    opener = opener or urllib.request.build_opener(HTTPSRedirect())
    output.parent.mkdir(parents=True, exist_ok=True)
    received, checksum, started = 0, hashlib.sha256(), time.monotonic()
    try:
        with opener.open(request, timeout=60) as source, temporary.open('xb') as target:
            length = source.headers.get('Content-Length')
            if length is not None and int(length) != size:
                raise ValueError('Download length differs from reviewed archive')
            while True:
                if time.monotonic() - started > 900:
                    raise ValueError('Asset download exceeded 15 minutes')
                block = source.read(min(1024 * 1024, size - received + 1))
                if not block:
                    break
                received += len(block)
                if received > size:
                    raise ValueError('Asset download exceeded reviewed size')
                target.write(block)
                checksum.update(block)
        if received != size or checksum.hexdigest() != digest:
            raise ValueError('Downloaded asset size or SHA-256 mismatch')
        if output.exists():
            raise ValueError('Download destination appeared during transfer')
        temporary.rename(output)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return {'bytes': received, 'sha256': digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--release-asset-id')
    args = parser.parse_args()
    try:
        print(json.dumps(fetch(args.receipt, args.output, args.release_asset_id), sort_keys=True))
    except Exception as error:
        # urllib exceptions can include signed URLs. Never print their text.
        print('Asset download failed (' + type(error).__name__ + '); check access, expiry and the pinned receipt.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
