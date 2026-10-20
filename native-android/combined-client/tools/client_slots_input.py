"""Prepare the existing exact CLIENT slot image; never rebuild its dictionary."""
import gzip
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = 'native-android/engine/entities/qualification/costume-builder-20261017/offline-primary-slots.bin.gz'
ASSET = 'combined/client-slots.bin'
RAW_BYTES = 641477
RAW_SHA256 = '2e69212432d1b16a38f307aca16ac892cca56cf59128d5d8d25e71386da4af81'


def prepare_client_slots(assets):
    with gzip.open(ROOT / SOURCE, 'rb') as stream:
        raw = stream.read(RAW_BYTES + 1)
    if len(raw) != RAW_BYTES or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError('Retained CLIENT primary slot image identity differs')
    output = Path(assets) / ASSET
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {'asset': ASSET, 'bytes': RAW_BYTES, 'sha256': RAW_SHA256, 'source': SOURCE}
