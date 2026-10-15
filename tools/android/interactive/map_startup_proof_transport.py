#!/usr/bin/env python3
"""Preserve historical receipt bytes in .32 fresh-process host proof transport.

The accepted FX producer pins both original workers. Their worker and validator
functions remain unchanged; this entry point preserves nested JSON key order
when their complete proof crosses a process boundary.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
WORKERS = {
    'runtime_assets': ('qualify_runtime_asset_preflight',
        {'bytes': 28071, 'sha256': '032b5ea3cd2503d883bcca97b1122757adab84b6c7f2bdea7993dfa0dc0d11b6'}),
    'full_startup': ('qualify_full_startup_preflight',
        {'bytes': 35872, 'sha256': '8bded2764ef32a8f8e86ee18e49977878a8c97e12f56bda4594dd8cf6e3e8002'}),
}
TIMEOUT_SECONDS = {'runtime_assets': 900, 'full_startup': 1800}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def worker_module(kind):
    require(kind in WORKERS, 'Only the two accepted preflight workers may execute')
    for name, expected in WORKERS.values():
        path = ROOT/'tools/android/interactive'/(name+'.py')
        require(path.is_file() and not path.is_symlink(), 'Preflight worker source is missing or linked')
        raw = path.read_bytes()
        require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected,
                'Accepted preflight worker source changed: '+name)
    name = WORKERS[kind][0]
    module = importlib.import_module(name)
    require(Path(module.__file__).resolve() == ROOT/'tools/android/interactive'/(name+'.py'),
            'Preflight worker import was shadowed')
    return module


def encoded(value):
    # Canonical digests inside the proof still use the original validators.
    # Sorting transport keys would change their nested historical LF/CRLF bytes.
    return (json.dumps(value, separators=(',', ':'), allow_nan=False)+'\n').encode()


def preflight(kind, runtime_assets, payloads):
    module = worker_module(kind)
    with tempfile.TemporaryDirectory(prefix='coh-map-startup-proof-') as temporary:
        output = Path(temporary)/'proof.json'
        command = [sys.executable, str(Path(__file__).resolve()), '--kind', kind,
            '--runtime-assets', str(Path(runtime_assets).resolve()),
            '--payloads', str(Path(payloads).resolve()), '--output', str(output)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=TIMEOUT_SECONDS[kind], check=False)
        require(result.returncode == 0, 'Actual original preflight worker failed:\n'+result.stderr[-18000:])
        require(output.is_file() and not output.is_symlink() and 0 < output.stat().st_size <= 16*1024**2,
                'Fresh bounded preflight proof required')
        return module.validate_proof(json.loads(output.read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', required=True, choices=tuple(WORKERS))
    for name in ('runtime-assets', 'payloads', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    module = worker_module(args.kind)
    value = module.worker(args.runtime_assets, args.payloads)
    module.validate_proof(value)
    raw = encoded(value)
    module.validate_proof(json.loads(raw))
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh proof output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)


if __name__ == '__main__':
    main()
