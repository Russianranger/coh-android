#!/usr/bin/env python3
"""Verify public crypto provenance before a combined APK links it."""
import hashlib
import json
from pathlib import Path
import sys

root, abi, pin_path = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3])
receipt = json.loads((root / 'receipt.json').read_text())
pin = json.loads(pin_path.read_text())
def require(condition, message):
    if not condition:
        raise ValueError(message)

require(abi in ('arm64-v8a', 'x86_64') and receipt['abi'] == abi, 'ABI mismatch')
require(receipt['status'] == 'PASS' and receipt['android_crypto_provider_linked'] is True, 'Unqualified provider')
require(receipt['openssl_version'] == pin['version'], 'Dependency version differs')
require(receipt['openssl_archive_sha256'] == pin['sha256'], 'Dependency source pin differs')
require(receipt['private_android_crypto_dependency'] is False, 'Private dependency prohibited')
require(receipt['dynamic_openssl_dependency'] is False, 'Dynamic dependency prohibited')
for name, expected in receipt['artifacts_sha256'].items():
    path = (root / name).resolve()
    require(root in path.parents and path.is_file(), 'Invalid dependency path')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Dependency artifact hash differs')
require('lib/libcrypto.a' in receipt['artifacts_sha256'], 'Public crypto library missing')
print('Pinned public Android crypto verified for ' + abi)
