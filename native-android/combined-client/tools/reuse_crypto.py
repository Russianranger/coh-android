#!/usr/bin/env python3
"""Reuse the exact public crypto build only while all qualified sources match."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import zipfile
from prepare import safe_zip, verify

ARTIFACT_ID = '11980774730'
ARCHIVE_SHA = '99516e8cc5ea602e2596e4c6dd5e5e965c1dcd5979523e317f5e87698f38f30d'
ABIS = ('arm64-v8a', 'x86_64')


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path)
    p.add_argument('--crypto-root', type=Path, required=True)
    p.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.archive:
        verify(args.archive, ARCHIVE_SHA)
        with zipfile.ZipFile(args.archive) as z:
            safe_zip(z)
            if args.crypto_root.exists():
                raise ValueError('Refuse to overwrite an existing crypto build')
            for info in z.infolist():
                parts = PurePosixPath(info.filename).parts
                if len(parts) < 3 or parts[0] != 'crypto' or parts[1] not in ABIS or info.is_dir():
                    continue
                if info.file_size > 64 << 20:
                    raise ValueError('Crypto artifact member exceeds bound')
                destination = args.crypto_root.joinpath(*parts[1:])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(z.read(info))
    receipts = {}
    native = args.source_root / 'native-android'
    for abi in ABIS:
        root = args.crypto_root / abi
        receipt = json.loads((root / 'receipt.json').read_text())
        assert receipt['abi'] == abi and receipt['status'] == 'PASS'
        assert receipt['ndk_revision'] == '28.2.13676358'
        assert receipt['android_crypto_provider_linked'] is True
        assert receipt['source_pin_sha256'] == sha(native / 'engine/auth/android/openssl-source.json')
        for relative, digest in receipt['native_source_sha256'].items():
            assert sha(native / relative) == digest, 'Qualified crypto source changed: ' + relative
        for relative, digest in receipt['artifacts_sha256'].items():
            assert '..' not in PurePosixPath(relative).parts and not relative.startswith('/')
            assert sha(root / relative) == digest, 'Qualified crypto artifact changed: ' + relative
        receipts[abi] = {'receipt_sha256': sha(root / 'receipt.json'), 'native_source_sha256': receipt['native_source_sha256'], 'artifacts_sha256': receipt['artifacts_sha256']}
    value = {'format': 1, 'status': 'passed', 'reused_workflow_run': '38752076829', 'reused_artifact_id': ARTIFACT_ID, 'archive_sha256': ARCHIVE_SHA if args.archive else None, 'scope': 'Exact public crypto libraries reused after source and output hash verification; no new execution claim.', 'abis': receipts}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': 'passed', 'qualified_crypto_reused': list(receipts)}))


if __name__ == '__main__':
    main()
